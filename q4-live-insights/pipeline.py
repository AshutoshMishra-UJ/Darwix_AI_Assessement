"""
Q4 — Live Insights: Real-Time Call Analysis Pipeline
Streams voice → Groq signal extraction → WebSocket nudge delivery

Architecture:
  Browser voice (Web Speech API)
    | WebSocket /ws/voice_agent/{call_id}?agent=aria|maya|dewi
  Groq LLM (llama-3.3-70b) — agent turn + signal extraction
    | Signal: {type, confidence, evidence, nudge}
  Nudge Filter (dedup, cooldown, confidence threshold, expiry)
    | WebSocket /ws/dashboard
  Browser dashboard (transcript feed + nudge cards + CRM leads)

Audio streaming (Deepgram):
  /ws/audio/{call_id} — raw PCM → Deepgram ASR → signal extraction

Demo mode (no Deepgram needed):
  GET /demo — pre-scripted call replay through full signal pipeline
"""

import asyncio
import json
import os
import sys
import time
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# ── Path setup ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "q2-knowledge-base"))
sys.path.insert(0, str(ROOT / "q1-voice-agent"))

load_dotenv(ROOT / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "openai/gpt-oss-120b"
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
PORT = int(os.getenv("PORT", "8001"))

DEEPGRAM_WS_URL = (
    "wss://api.deepgram.com/v1/listen"
    "?encoding=linear16"
    "&sample_rate=16000"
    "&channels=1"
    "&diarize=true"
    "&punctuate=true"
    "&language=en-IN"
    "&model=nova-2"
    "&interim_results=true"
    "&utterance_end_ms=1000"
)

# ── Nudge configuration ────────────────────────────────────────────────────────

SIGNAL_TYPES = {
    "missed_cross_sell": {"cooldown_s": 60, "confidence_threshold": 0.75, "priority": "medium", "expiry_s": 90},
    "compliance_gap":    {"cooldown_s": 300, "confidence_threshold": 0.80, "priority": "high", "expiry_s": 120},
    "rising_frustration":{"cooldown_s": 45, "confidence_threshold": 0.70, "min_consecutive_windows": 2, "priority": "high", "expiry_s": 60},
    "payment_difficulty":{"cooldown_s": 60, "confidence_threshold": 0.75, "priority": "medium", "expiry_s": 90},
    "out_of_scope":      {"cooldown_s": 30, "confidence_threshold": 0.75, "priority": "low", "expiry_s": 60},
    "buying_signal":     {"cooldown_s": 90, "confidence_threshold": 0.80, "priority": "high", "expiry_s": 120},
}

SIGNAL_EXTRACTION_PROMPT = """You are a real-time call analysis engine. Analyze the following call transcript window and detect any of these signals:

1. missed_cross_sell: Customer mentions another product, family member, vehicle, loan, or second property
2. compliance_gap: Required disclosures (waiting periods, exclusions, co-payment) have NOT been mentioned yet
3. rising_frustration: Customer expresses repeated dissatisfaction, anger, impatience, or frustration
4. payment_difficulty: Customer mentions affordability concerns, budget constraints, or inability to pay
5. out_of_scope: Customer asks about products/services outside the agent's scope
6. buying_signal: Customer expresses interest, asks about next steps, enrollment, or pricing

IMPORTANT RULES:
- Only flag signals you are confident about (confidence must be genuine, not inflated)
- For noisy or ambiguous audio, return an empty list
- Return at most 2 signals per window
- For rising_frustration: only flag if clearly sustained, not a single word

Return ONLY valid JSON:
{
  "signals": [
    {
      "type": "signal_type_here",
      "confidence": 0.85,
      "evidence": "brief quote or paraphrase from transcript",
      "nudge": "short actionable recommendation for the agent (max 15 words)"
    }
  ]
}

If no signals detected, return: {"signals": []}

TRANSCRIPT WINDOW (last 30 seconds):
"""

# ── Agent configurations ───────────────────────────────────────────────────────

AGENT_CONFIGS = {
    "aria": {
        "display_name": "Aria",
        "emoji": "🤖",
        "stt_lang": "en-IN",
        "prompt": """You are Aria, a warm and professional health insurance advisor for ShieldCare Insurance, representing the Arogya Shield Plus plan.

## Goal
Qualify callers as potential Arogya Shield Plus customers through natural, friendly conversation.

## Conversation Steps
1. GREETING: "Hello! I'm Aria from ShieldCare Insurance. I'm reaching out about our Arogya Shield Plus health insurance plan. Do you have about 3 to 4 minutes?"
2. QUALIFICATION: Naturally collect: full name, age, city, individual or family coverage need, existing insurance, pre-existing conditions, annual budget.
3. NEEDS ASSESSMENT: Recommend Silver (budget), Gold (mid-range), or Platinum (comprehensive).
4. Q&A: ALWAYS call search_knowledge_base BEFORE answering any product question. Never guess.
5. WRAP UP: For qualified leads (age 18-65), call log_lead. For unqualified, thank them warmly.

## Eligibility Rules
- ELIGIBLE: Age 18-65, Indian resident or NRI
- INELIGIBLE: Under 18 or over 65

## Hard Rules
- Keep responses SHORT (2-3 sentences) — this is a voice conversation
- Never invent policy details, premiums, or terms
- Always search KB before answering policy questions
- Disclose you are an AI if sincerely asked
- Never collect payment information""",
    },
    "maya": {
        "display_name": "Maya",
        "emoji": "🌺",
        "stt_lang": "fil-PH",
        "prompt": """You are Maya, a friendly insurance advisor for SunLife Assurance Philippines. You speak naturally in Taglish — a natural mix of Filipino/Tagalog and English.

Use "po" and "ho" for politeness. Finance terms (premium, policy, beneficiary, rider) are used naturally in English. Keep responses SHORT (2-3 sentences max) for voice delivery.

FLOW: Greet, collect name/age/occupation/dependents, assess budget, search KB before any product questions, log_lead when qualified.""",
    },
    "dewi": {
        "display_name": "Dewi",
        "emoji": "🌸",
        "stt_lang": "id-ID",
        "prompt": """Kamu adalah Dewi, agen layanan pelanggan ramah dari ArthaPrime Multifinance. Berbicara dalam Bahasa Indonesia yang natural.

Gunakan istilah keuangan natural: DP, tenor, cicilan, angsuran. Respons SINGKAT (2-3 kalimat). Panggil search_knowledge_base sebelum menjawab pertanyaan produk. Panggil log_lead untuk nasabah yang qualified.""",
    },
}

# ── Tool definitions ───────────────────────────────────────────────────────────

VOICE_AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Search Arogya Shield Plus KB for policy, FAQ, coverage, pricing, objection responses.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "category": {"type": "string", "enum": ["product_overview", "policy_rules", "qualification", "faq", "objection", "claim_process", "network", "pricing", "coverage"]},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "log_lead",
            "description": "Save a qualified lead to CRM.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"},
                    "city": {"type": "string"},
                    "coverage_type": {"type": "string", "enum": ["individual", "family"]},
                    "sum_insured_preference": {"type": "string"},
                    "pre_existing_conditions": {"type": "string"},
                    "qualified": {"type": "boolean"},
                    "recommended_plan": {"type": "string", "enum": ["Silver", "Gold", "Platinum"]},
                    "notes": {"type": "string"},
                },
                "required": ["name", "age", "city", "coverage_type", "sum_insured_preference", "qualified"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_callback",
            "description": "Schedule a callback for a caller who cannot talk right now.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "phone": {"type": "string"},
                    "preferred_time": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["name", "preferred_time"],
            },
        },
    },
]

# ── Tool implementations ───────────────────────────────────────────────────────

def va_search_kb(query: str, category: str = None) -> str:
    try:
        from retrieval import retrieve_for_voice_agent
        result = retrieve_for_voice_agent(query, category_filter=category)
        if result.get("found"):
            return result["answer"]
        return "No specific info found. Advise caller to contact helpline at 1800-XXX-XXXX."
    except Exception:
        import re
        try:
            kb_path = ROOT / "data" / "kb_records.json"
            records = json.loads(kb_path.read_text(encoding="utf-8"))
            q_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
            best = max(records, key=lambda r: len(q_tokens & set(re.findall(r"[a-z0-9]+", (r["title"] + " " + r["content"]).lower()))))
            return best["content"]
        except Exception:
            return "KB lookup unavailable. Advise caller to contact helpline at 1800-XXX-XXXX."


def va_log_lead(**kwargs) -> str:
    ref = f"LEAD-{str(uuid.uuid4())[:8].upper()}"
    try:
        from crm_mock import create_lead
        lead = create_lead(**kwargs)
        ref = lead["lead_id"]
    except Exception:
        pass
    return f"Lead saved. Reference: {ref}. Specialist follows up within 24 hours."


def va_schedule_callback(**kwargs) -> str:
    ref = f"CB-{str(uuid.uuid4())[:6].upper()}"
    try:
        from crm_mock import create_callback
        cb = create_callback(**kwargs)
        ref = cb["callback_id"]
    except Exception:
        pass
    return f"Callback scheduled for {kwargs.get('preferred_time')}. Reference: {ref}."


VA_TOOL_MAP = {
    "search_knowledge_base": va_search_kb,
    "log_lead": va_log_lead,
    "schedule_callback": va_schedule_callback,
}

# ── Application state ──────────────────────────────────────────────────────────

class CallSession:
    def __init__(self, call_id: str):
        self.call_id = call_id
        self.start_time = time.time()
        self.transcript_buffer: list[dict] = []
        self.signal_cooldowns: dict[str, float] = defaultdict(float)
        self.frustration_window_count = 0
        self.emitted_signals: list[dict] = []
        self.latency_log: list[dict] = []
        self.last_extraction_time = 0.0
        self.extraction_interval_s = 3.0

    def get_transcript_window(self, seconds: int = 30) -> str:
        now = time.time()
        cutoff = now - seconds
        recent = [t for t in self.transcript_buffer if t["ts"] >= cutoff]
        lines = [f"{'AGENT' if t.get('speaker') == '0' else 'CUSTOMER'}: {t['text']}" for t in recent]
        return "\n".join(lines) if lines else "[No transcript yet]"

    def can_emit(self, signal_type: str) -> bool:
        cooldown = SIGNAL_TYPES.get(signal_type, {}).get("cooldown_s", 60)
        return time.time() - self.signal_cooldowns[signal_type] >= cooldown

    def record_emission(self, signal_type: str):
        self.signal_cooldowns[signal_type] = time.time()


session_store: dict[str, CallSession] = {}
dashboard_connections: list[WebSocket] = []
va_histories: dict[str, list] = {}

# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(title="Aegis Live Insights — Q4 Pipeline", version="2.0.0")

dashboard_dir = Path(__file__).parent / "dashboard"
if dashboard_dir.exists():
    app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static_q4")


@app.get("/")
async def root():
    dash = dashboard_dir / "index.html"
    if dash.exists():
        return HTMLResponse(dash.read_text(encoding="utf-8"))
    static_html = ROOT / "static" / "index.html"
    if static_html.exists():
        return HTMLResponse(static_html.read_text(encoding="utf-8"))
    return {"message": "Q4 Live Insights Pipeline running", "port": PORT}


@app.get("/health")
async def health():
    return {"status": "ok", "active_calls": len(session_store), "groq": bool(GROQ_API_KEY), "deepgram": bool(DEEPGRAM_API_KEY)}


@app.get("/api/leads")
async def get_leads():
    leads_file = ROOT / "q1-voice-agent" / "crm_leads.json"
    callbacks_file = ROOT / "q1-voice-agent" / "callbacks.json"
    leads, callbacks = [], []
    if leads_file.exists():
        try:
            leads = json.loads(leads_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    if callbacks_file.exists():
        try:
            callbacks = json.loads(callbacks_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"leads": leads, "callbacks": callbacks, "total": len(leads)}


# ── Dashboard WebSocket ───────────────────────────────────────────────────────

@app.websocket("/ws/dashboard")
async def dashboard_ws(websocket: WebSocket):
    await websocket.accept()
    dashboard_connections.append(websocket)
    print(f"[dashboard] Connected. Total: {len(dashboard_connections)}")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in dashboard_connections:
            dashboard_connections.remove(websocket)
        print(f"[dashboard] Disconnected. Total: {len(dashboard_connections)}")


async def broadcast_to_dashboard(data: dict):
    dead = []
    for ws in dashboard_connections:
        try:
            await ws.send_text(json.dumps(data))
        except Exception:
            dead.append(ws)
    for ws in dead:
        if ws in dashboard_connections:
            dashboard_connections.remove(ws)


# ── Groq LLM turn ────────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    import re
    text = re.sub(r"<function=[^>]+>.*?</function>", "", text, flags=re.DOTALL)
    return " ".join(text.split()).strip()


async def va_run_turn(messages: list, tools: list = None) -> str:
    if tools is None:
        tools = VOICE_AGENT_TOOLS
    while True:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{GROQ_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={"model": GROQ_MODEL, "messages": messages, "tools": tools, "tool_choice": "auto", "temperature": 0.3, "max_tokens": 250},
            )
        resp.raise_for_status()
        result = resp.json()
        choice = result["choices"][0]
        msg = choice["message"]
        messages.append(msg)

        if choice["finish_reason"] == "tool_calls" and msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                fn_name = tc["function"]["name"]
                fn_args = json.loads(tc["function"]["arguments"])
                print(f"[VA-tool] {fn_name}({list(fn_args.keys())})")
                fn = VA_TOOL_MAP.get(fn_name)
                tool_result = await asyncio.get_event_loop().run_in_executor(
                    None, lambda f=fn, a=fn_args: f(**a) if f else "Tool not found."
                )
                print(f"[VA-tool] → {str(tool_result)[:80]}")
                messages.append({"role": "tool", "tool_call_id": tc["id"], "content": tool_result})
            continue

        return _clean(msg.get("content", "").strip())


# ── Voice Agent WebSocket ─────────────────────────────────────────────────────

@app.websocket("/ws/voice_agent/{call_id}")
async def voice_agent_ws(websocket: WebSocket, call_id: str, agent: str = "aria"):
    await websocket.accept()
    cfg = AGENT_CONFIGS.get(agent.lower(), AGENT_CONFIGS["aria"])
    agent_name = cfg["display_name"]
    agent_emoji = cfg["emoji"]
    print(f"[VA] Session: {call_id} | Agent: {agent_name}")

    session = CallSession(call_id)
    session_store[call_id] = session
    history = [{"role": "system", "content": cfg["prompt"]}]
    va_histories[call_id] = history

    await broadcast_to_dashboard({"type": "call_started", "call_id": call_id, "agent": agent_name, "timestamp": datetime.utcnow().isoformat()})

    try:
        opening = await va_run_turn(history, VOICE_AGENT_TOOLS)
        await websocket.send_text(json.dumps({"type": "agent", "text": opening, "agent_name": agent_name, "emoji": agent_emoji}))
        session.transcript_buffer.append({"text": opening, "speaker": "0", "ts": time.time(), "confidence": 1.0})
        await broadcast_to_dashboard({"type": "transcript", "call_id": call_id, "speaker": "AGENT", "text": opening, "timestamp": datetime.utcnow().isoformat()})

        while True:
            raw = await websocket.receive_text()
            msg_data = json.loads(raw)
            if msg_data.get("type") == "end":
                break
            user_text = msg_data.get("text", "").strip()
            if not user_text:
                continue

            session.transcript_buffer.append({"text": user_text, "speaker": "1", "ts": time.time(), "confidence": 1.0})
            await broadcast_to_dashboard({"type": "transcript", "call_id": call_id, "speaker": "CUSTOMER", "text": user_text, "timestamp": datetime.utcnow().isoformat()})

            history.append({"role": "user", "content": user_text})
            reply = await va_run_turn(history, VOICE_AGENT_TOOLS)
            await websocket.send_text(json.dumps({"type": "agent", "text": reply, "agent_name": agent_name, "emoji": agent_emoji}))

            now = time.time()
            session.transcript_buffer.append({"text": reply, "speaker": "0", "ts": now, "confidence": 1.0})
            await broadcast_to_dashboard({"type": "transcript", "call_id": call_id, "speaker": "AGENT", "text": reply, "timestamp": datetime.utcnow().isoformat()})

            if now - session.last_extraction_time >= session.extraction_interval_s:
                session.last_extraction_time = now
                asyncio.create_task(extract_and_emit_signals(session, now))

    except WebSocketDisconnect:
        print(f"[VA] Disconnected: {call_id}")
    except Exception as e:
        print(f"[VA] Error: {e}")
    finally:
        session_store.pop(call_id, None)
        va_histories.pop(call_id, None)
        await broadcast_to_dashboard({"type": "call_ended", "call_id": call_id, "duration_s": round(time.time() - session.start_time, 1), "timestamp": datetime.utcnow().isoformat()})


# ── Audio WebSocket (Deepgram) ────────────────────────────────────────────────

@app.websocket("/ws/audio/{call_id}")
async def audio_ingest_ws(websocket: WebSocket, call_id: str):
    await websocket.accept()
    session = CallSession(call_id)
    session_store[call_id] = session
    await broadcast_to_dashboard({"type": "call_started", "call_id": call_id, "timestamp": datetime.utcnow().isoformat()})

    try:
        import websockets as ws_lib
        async with ws_lib.connect(DEEPGRAM_WS_URL, additional_headers={"Authorization": f"Token {DEEPGRAM_API_KEY}"}) as dg_ws:
            async def forward_audio():
                try:
                    while True:
                        chunk = await websocket.receive_bytes()
                        await dg_ws.send(chunk)
                except Exception as e:
                    await dg_ws.send(json.dumps({"type": "CloseStream"}))

            async def process_transcripts():
                async for dg_msg in dg_ws:
                    dg_data = json.loads(dg_msg)
                    if dg_data.get("type") != "Results" or not dg_data.get("is_final"):
                        continue
                    alts = dg_data.get("channel", {}).get("alternatives", [])
                    if not alts:
                        continue
                    text = alts[0].get("transcript", "").strip()
                    if not text:
                        continue
                    words = alts[0].get("words", [])
                    speaker = str(words[0].get("speaker", 0)) if words else "0"
                    asr_ts = time.time()
                    session.transcript_buffer.append({"text": text, "speaker": speaker, "ts": asr_ts, "confidence": alts[0].get("confidence", 1.0)})
                    await broadcast_to_dashboard({"type": "transcript", "call_id": call_id, "speaker": "AGENT" if speaker == "0" else "CUSTOMER", "text": text, "timestamp": datetime.utcnow().isoformat()})
                    now = time.time()
                    if now - session.last_extraction_time >= session.extraction_interval_s:
                        session.last_extraction_time = now
                        asyncio.create_task(extract_and_emit_signals(session, asr_ts))

            await asyncio.gather(forward_audio(), process_transcripts())
    except Exception as e:
        print(f"[pipeline] Error for {call_id}: {e}")
    finally:
        session_store.pop(call_id, None)
        await broadcast_to_dashboard({"type": "call_ended", "call_id": call_id, "duration_s": round(time.time() - session.start_time, 1), "timestamp": datetime.utcnow().isoformat()})


# ── Signal extraction ─────────────────────────────────────────────────────────

async def extract_and_emit_signals(session: CallSession, asr_ts: float):
    window = session.get_transcript_window(seconds=30)
    if window == "[No transcript yet]" or len(window) < 50:
        return

    llm_start = time.time()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{GROQ_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={
                    "model": GROQ_MODEL,
                    "messages": [{"role": "user", "content": SIGNAL_EXTRACTION_PROMPT + window}],
                    "temperature": 0.1,
                    "max_tokens": 300,
                    "response_format": {"type": "json_object"},
                },
            )
        result = resp.json()
    except Exception as e:
        print(f"[signal] LLM error: {e}")
        return

    llm_latency_ms = round((time.time() - llm_start) * 1000)

    try:
        content = result["choices"][0]["message"]["content"]
        signals = json.loads(content).get("signals", [])
    except Exception as e:
        print(f"[signal] Parse error: {e}")
        return

    for signal in signals:
        signal_type = signal.get("type")
        confidence = float(signal.get("confidence", 0))
        config = SIGNAL_TYPES.get(signal_type)
        if not config:
            continue
        if confidence < config["confidence_threshold"]:
            continue
        if not session.can_emit(signal_type):
            continue

        # Frustration gate
        if signal_type == "rising_frustration":
            session.frustration_window_count += 1
            if session.frustration_window_count < config.get("min_consecutive_windows", 2):
                continue
        else:
            session.frustration_window_count = 0

        e2e_latency_ms = round((time.time() - asr_ts) * 1000)
        nudge = {
            "id": f"nudge-{str(uuid.uuid4())[:8]}",
            "type": signal_type,
            "confidence": confidence,
            "evidence": signal.get("evidence", ""),
            "nudge": signal.get("nudge", ""),
            "priority": config["priority"],
            "latency_ms": e2e_latency_ms,
            "llm_latency_ms": llm_latency_ms,
            "expires_at": time.time() + config["expiry_s"],
            "call_id": session.call_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        session.record_emission(signal_type)
        session.emitted_signals.append(nudge)
        session.latency_log.append({"type": signal_type, "e2e_ms": e2e_latency_ms, "llm_ms": llm_latency_ms})
        await broadcast_to_dashboard({"type": "nudge", **nudge})
        print(f"[nudge] {signal_type} | conf={confidence:.2f} | e2e={e2e_latency_ms}ms")


# ── Demo mode ─────────────────────────────────────────────────────────────────

DEMO_TRANSCRIPT = [
    (3,  "0", "Good afternoon, this is Aria from ShieldCare. Am I speaking with Priya?"),
    (6,  "1", "Yes, this is Priya. I got a message about my Arogya Shield Plus renewal?"),
    (10, "0", "That is right! Your policy renews next month. Can I confirm your current family floater plan with 10 lakh sum insured?"),
    (14, "1", "Yes, my husband and I are on it. But honestly, the premium keeps going up every year. This is getting too expensive for us."),
    (19, "0", "I understand your concern completely. Great news though — you've earned a no-claim bonus this year which reduces your premium by 10 percent."),
    (24, "1", "Oh I did not know that. But still, my sister found a cheaper plan elsewhere. Why should I stay with you?"),
    (29, "0", "Unlike budget plans, Arogya Shield Plus includes day-care procedures, no room rent cap, and full AYUSH treatment coverage."),
    (34, "1", "My son just turned 18 last month. Can he still be on our family floater?"),
    (38, "0", "Yes, dependent children are covered up to age 25 under your family floater plan. Your son is fully covered."),
    (43, "1", "We also just bought a car last month. Do you have any vehicle insurance as well?"),
    (47, "0", "We specialize in health insurance so vehicle insurance is not something we offer, but I can connect you with a partner."),
    (52, "1", "Okay. My budget is really tight this month. I don't think I can pay the full annual premium right now."),
    (57, "0", "No problem at all. We offer quarterly and monthly payment options so you don't have to pay the full year upfront."),
    (62, "1", "That is very helpful. And what about pre-existing conditions? My husband has type 2 diabetes."),
    (67, "0", "Since your policy has been active for over 3 years, his diabetes is fully covered with no waiting period at renewal."),
    (72, "1", "Oh that is a relief! I actually want to increase our sum insured to 15 lakhs. How do I do that?"),
    (78, "0", "I can process that upgrade right now. There is no fresh waiting period since you are an existing customer."),
    (83, "1", "Yes please send the details to my email. I am very interested in renewing now."),
    (88, "0", "Perfect Priya! I will send the detailed quote with the no-claim discount applied. Thank you for choosing ShieldCare!"),
]


@app.get("/demo")
async def start_demo():
    call_id = f"demo-{int(time.time())}"
    asyncio.create_task(run_demo_session(call_id))
    return {"message": "Demo started! Open the dashboard to watch live nudges.", "call_id": call_id, "dashboard": f"http://localhost:{PORT}/"}


async def run_demo_session(call_id: str):
    session = CallSession(call_id)
    session_store[call_id] = session
    print(f"[demo] Starting: {call_id}")
    await broadcast_to_dashboard({"type": "call_started", "call_id": call_id, "timestamp": datetime.utcnow().isoformat()})

    prev_ts = 0
    for (ts, speaker, text) in DEMO_TRANSCRIPT:
        await asyncio.sleep(ts - prev_ts)
        prev_ts = ts
        asr_ts = time.time()
        session.transcript_buffer.append({"text": text, "speaker": speaker, "ts": asr_ts, "confidence": 1.0})
        speaker_label = "AGENT" if speaker == "0" else "CUSTOMER"
        print(f"[demo] {speaker_label}: {text[:70]}")
        await broadcast_to_dashboard({"type": "transcript", "call_id": call_id, "speaker": speaker_label, "text": text, "timestamp": datetime.utcnow().isoformat()})
        now = time.time()
        if now - session.last_extraction_time >= session.extraction_interval_s:
            session.last_extraction_time = now
            asyncio.create_task(extract_and_emit_signals(session, asr_ts))

    await asyncio.sleep(4)
    asyncio.create_task(extract_and_emit_signals(session, time.time()))
    await asyncio.sleep(6)

    session_store.pop(call_id, None)
    await broadcast_to_dashboard({"type": "call_ended", "call_id": call_id, "duration_s": 93, "timestamp": datetime.utcnow().isoformat()})
    print(f"[demo] Complete: {call_id}")


if __name__ == "__main__":
    print(f"Starting Q4 Live Insights Pipeline on port {PORT}")
    uvicorn.run("pipeline:app", host="0.0.0.0", port=PORT, reload=False)
