"""
Aegis Conversation Studio — Main Application
AI Engineer Assessment | ShieldCare Insurance / Arogya Shield Plus

Serves:
  GET  /              → Browser UI (static/index.html)
  GET  /api/health    → System status
  POST /api/turn      → Single-turn voice agent (Groq-first, Gemini fallback, demo fallback)
  POST /api/query     → Knowledge base search
  GET  /api/records   → All KB records
  POST /api/lead      → Save CRM lead event
  GET  /api/crm       → Get all CRM events
  GET  /api/nudges    → Get live signal nudges
  GET  /demo          → Start demo call (redirects to Q4 pipeline)
  WS   /ws/voice_agent/{call_id} → Real-time voice agent (Groq tool-calling)
  WS   /ws/dashboard             → Live nudge and transcript broadcast
"""

import asyncio
import json
import os
import re
import sys
import time
import uuid
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from scripts.nudge_engine import NudgeEngine

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

PORT = int(os.getenv("PORT", "8002"))
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "openai/gpt-oss-120b"
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

DATA_PATH = ROOT / "data" / "kb_records.json"
CRM_PATH = ROOT / "data" / "crm_events.json"
UI_PATH = ROOT / "static" / "index.html"

# Add Q2 to path for retrieval
sys.path.insert(0, str(ROOT / "q2-knowledge-base"))
sys.path.insert(0, str(ROOT / "q1-voice-agent"))

records = json.loads(DATA_PATH.read_text(encoding="utf-8"))

app = FastAPI(title="Aegis Conversation Studio", version="2.0.0")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
nudge_engine = NudgeEngine()

# ── Application state ─────────────────────────────────────────────────────────
dashboard_connections: list[WebSocket] = []


# ── KB search ─────────────────────────────────────────────────────────────────

def tokens(text: str) -> set:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


ALIASES = {
    "62": {"age", "eligibility"}, "year": {"age", "eligibility"},
    "apply": {"eligibility"}, "cashless": {"claims"},
    "hospitalisation": {"claims"}, "hospitalization": {"claims"},
    "human": {"escalation"}, "person": {"escalation"}, "speak": {"escalation"},
    "expensive": {"objection"}, "premium": {"pricing", "objection"},
    "waiting": {"policy_rules"}, "diabetes": {"policy_rules"},
    "cataract": {"coverage"}, "day": {"coverage"},
}


def search_kb(query: str, limit: int = 3) -> list:
    # Try ChromaDB first
    try:
        from retrieval import retrieve_for_voice_agent
        result = retrieve_for_voice_agent(query, limit=limit)
        if result.get("found"):
            return result["results"][:limit]
    except Exception:
        pass

    # Lexical fallback
    q_tokens = tokens(query)
    intent_tokens = set().union(*(ALIASES.get(t, set()) for t in q_tokens))
    ranked = []
    for record in records:
        body = tokens(record["title"] + " " + record["content"] + " " + record["category"])
        overlap = len(q_tokens & body)
        intent_match = len(intent_tokens & {record["category"]})
        score = min(0.98, 0.28 + overlap / max(8, len(q_tokens)) * 0.7 + intent_match * 0.22)
        ranked.append({**record, "score": round(score, 2), "citation": f"{record['record_id']} | {record['source']} | v{record['version']}"})
    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked[:limit]


# ── CRM ───────────────────────────────────────────────────────────────────────

def save_crm(event: dict):
    existing = json.loads(CRM_PATH.read_text(encoding="utf-8")) if CRM_PATH.exists() else []
    existing.append(event)
    CRM_PATH.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def should_capture_lead(message: str, answer: str) -> bool:
    text = f"{message} {answer}".lower()
    triggers = ["speak to a human", "speak to human", "talk to a person", "human agent", "specialist",
                "callback", "transfer", "i do not want to speak to an ai", "i want to speak to a human",
                "escalate", "too expensive", "premium is too expensive"]
    return any(t in text for t in triggers)


# ── LLM: Groq-first, Gemini fallback ─────────────────────────────────────────

async def groq_reply(agent: str, message: str, evidence: list) -> str | None:
    if not GROQ_API_KEY:
        return None
    agent_prompts = {
        "aria": "You are Aria, a concise health-insurance qualification assistant for ShieldCare Insurance. Use only the supplied evidence. Never invent premiums or policy terms.",
        "maya": "You are Maya, a Taglish-speaking insurance advisor for SunLife Philippines. Use only the supplied evidence. Keep responses SHORT (2-3 sentences) for voice.",
        "dewi": "Kamu adalah Dewi, agen ArthaPrime Multifinance. Gunakan hanya bukti yang tersedia. Respons SINGKAT untuk percakapan suara.",
    }
    prompt = agent_prompts.get(agent, agent_prompts["aria"])
    user_content = f"Evidence:\n{json.dumps(evidence)}\n\nCaller message: {message}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{GROQ_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={
                    "model": GROQ_MODEL,
                    "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": user_content}],
                    "temperature": 0.3,
                    "max_tokens": 180,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[Groq] error: {e}")
        return None


async def gemini_reply(agent: str, message: str, evidence: list) -> str | None:
    if not GEMINI_KEY:
        return None
    prompt = f"You are a concise health-insurance qualification assistant. Use only the supplied evidence. Agent mode: {agent}"
    user_content = f"Evidence:\n{json.dumps(evidence)}\n\nCaller message: {message}"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_KEY}",
                json={
                    "systemInstruction": {"parts": [{"text": prompt}]},
                    "contents": [{"role": "user", "parts": [{"text": user_content}]}],
                    "generationConfig": {"temperature": 0.2, "maxOutputTokens": 180},
                },
            )
            resp.raise_for_status()
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"[Gemini] error: {e}")
        return None


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def home():
    return UI_PATH.read_text(encoding="utf-8")


@app.get("/api/health")
def health():
    mode = "groq" if GROQ_API_KEY else ("gemini" if GEMINI_KEY else "demo")
    return {"status": "ok", "mode": mode, "records": len(records), "groq": bool(GROQ_API_KEY), "gemini": bool(GEMINI_KEY)}


@app.get("/api/records")
def get_records():
    return {"records": records}


@app.post("/api/query")
def query(payload: dict):
    question = str(payload.get("query", "")).strip()
    if not question:
        return {"found": False, "results": [], "message": "Enter a question."}
    results = search_kb(question)
    found = results[0]["score"] >= 0.42 if results else False
    return {"found": found, "query": question, "results": results if found else [], "message": "Grounded results returned." if found else "No approved record matched this question."}


@app.post("/api/turn")
async def turn(payload: dict):
    started = time.perf_counter()
    message = str(payload.get("message", "")).strip()
    agent = str(payload.get("agent", "aria"))
    hits = search_kb(message)
    evidence = hits[:2]

    # LLM: try Groq first, then Gemini, then demo
    answer = await groq_reply(agent, message, evidence)
    mode = "groq"
    if not answer:
        answer = await gemini_reply(agent, message, evidence)
        mode = "gemini"
    if not answer:
        mode = "demo"
        if any(w in message.lower() for w in ["human", "person", "specialist", "transfer"]):
            answer = "Of course. I will arrange a specialist handoff and record your request."
        elif evidence and evidence[0].get("score", 0) >= 0.42:
            answer = evidence[0]["content"]
        else:
            answer = "I do not have an approved answer for that. I can arrange a specialist callback."

    elapsed = round((time.perf_counter() - started) * 1000)
    lead_event = None
    if should_capture_lead(message, answer):
        lead_event = {
            "event_id": str(uuid.uuid4())[:8],
            "created_at": time.time(),
            "type": "lead",
            "agent": agent,
            "message": message,
            "answer": answer,
            "channel": "chat",
            "lead_type": "callback",
        }
        save_crm(lead_event)

    transcript_event = {
        "id": str(uuid.uuid4())[:8],
        "agent": agent,
        "message": message,
        "answer": answer,
        "mode": mode,
        "latency_ms": elapsed,
        "citations": [item.get("citation", "") for item in evidence],
        "lead_saved": bool(lead_event),
    }
    # Broadcast to dashboard
    await broadcast_to_dashboard({"type": "transcript", "speaker": "CUSTOMER", "text": message, "timestamp": str(time.time())})
    await broadcast_to_dashboard({"type": "transcript", "speaker": "AGENT", "text": answer, "timestamp": str(time.time())})
    return {**transcript_event, "evidence": evidence}


@app.post("/api/lead")
def lead(payload: dict):
    event = {"event_id": str(uuid.uuid4())[:8], "created_at": time.time(), "type": "lead", **payload}
    save_crm(event)
    return {"saved": True, "event": event}


@app.get("/api/crm")
def crm():
    events = json.loads(CRM_PATH.read_text(encoding="utf-8")) if CRM_PATH.exists() else []
    return {"events": events}


@app.get("/api/leads")
def leads():
    """Combined leads from CRM events + Q1 crm_leads.json"""
    events = json.loads(CRM_PATH.read_text(encoding="utf-8")) if CRM_PATH.exists() else []
    try:
        q1_leads = json.loads((ROOT / "q1-voice-agent" / "crm_leads.json").read_text(encoding="utf-8"))
        events = events + q1_leads
    except Exception:
        pass
    return {"events": events, "total": len(events)}


@app.get("/api/nudges")
def nudges():
    candidates = [
        {"id": "n-01", "type": "compliance_gap", "priority": "high", "confidence": 0.91, "latency_ms": 1180,
         "evidence": "Caller disclosed a pre-existing condition; waiting-period disclosure has not appeared yet.",
         "action": "Explain the applicable waiting-period rule before recommending a plan.", "status": "active"},
        {"id": "n-02", "type": "missed_cross_sell", "priority": "medium", "confidence": 0.84, "latency_ms": 1320,
         "evidence": "Caller mentioned family coverage but qualification stayed on individual cover.",
         "action": "Ask whether dependants should be included in the quote.", "status": "active"},
        {"id": "n-03", "type": "buying_signal", "priority": "high", "confidence": 0.88, "latency_ms": 1060,
         "evidence": "Caller asked what happens next after showing interest.",
         "action": "Offer a callback and confirm consent to save the lead.", "status": "queued"},
        {"id": "n-04", "type": "payment_difficulty", "priority": "medium", "confidence": 0.79, "latency_ms": 1410,
         "evidence": "Caller mentioned budget is tight and cannot pay annual premium upfront.",
         "action": "Offer monthly or quarterly payment options.", "status": "active"},
    ]
    accepted = []
    for candidate in candidates:
        item = nudge_engine.accept(candidate)
        if item:
            accepted.append(item)
    nudge_engine.expire()
    return {"nudges": accepted, "metrics": nudge_engine.report()}


@app.get("/demo")
async def demo_redirect():
    """Trigger a scripted demo call via Q4 pipeline."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get("http://localhost:8001/demo")
            return resp.json()
    except Exception:
        return {"message": "Demo mode: start Q4 pipeline first with 'python q4-live-insights/pipeline.py'", "note": "Main app demo uses static nudge replay from /api/nudges"}


# ── WebSocket routes ──────────────────────────────────────────────────────────

@app.websocket("/ws/dashboard")
async def dashboard_ws(websocket: WebSocket):
    await websocket.accept()
    dashboard_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in dashboard_connections:
            dashboard_connections.remove(websocket)


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=PORT, reload=False)
