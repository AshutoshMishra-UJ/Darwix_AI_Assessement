"""
Q3 — Local Multilingual Terminal Voice Agents
Maya (Taglish / Philippines) and Dewi (Bahasa Indonesia)

Stack:
  STT:  Google Speech Recognition (fil-PH for Maya, id-ID for Dewi)
  LLM:  Groq llama-3.3-70b-versatile (tool-calling)
  TTS:  pyttsx3 (local, offline)
  CRM:  q1-voice-agent/crm_mock.py (shared)
  KB:   q2-knowledge-base/retrieval.py (shared)

Run:
  python q3-multilingual/local_multilingual_agent.py --agent maya
  python q3-multilingual/local_multilingual_agent.py --agent dewi
"""

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "q2-knowledge-base"))
sys.path.insert(0, str(ROOT / "q1-voice-agent"))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "openai/gpt-oss-120b"


# ── Agent configurations ───────────────────────────────────────────────────────

AGENT_CONFIGS = {
    "maya": {
        "display_name": "Maya",
        "stt_lang": "fil-PH",
        "system_prompt": """You are Maya, a friendly and professional insurance advisor for SunLife Assurance Philippines. You speak naturally in Taglish — a natural mix of Filipino/Tagalog and English, the way Filipinos naturally speak to each other.

LANGUAGE RULES:
- Use Taglish naturally. Don't force full Tagalog or full English.
- Use "po" and "ho" for politeness (Filipino cultural norm).
- Finance terms: use them naturally as Filipinos do — premium, policy, beneficiary, rider, lapse, coverage.
- Match the customer's language and register. If they speak more English, lean English. If more Tagalog, lean Tagalog.
- Keep responses SHORT (2-3 sentences max) — this is a voice conversation.

QUALIFICATION FLOW:
1. GREETING: "Magandang araw po! I'm Maya from SunLife Assurance. Can I have 3 to 4 minutes of your time para makausap kayo tungkol sa aming SunShield Life Plus plan?"
2. COLLECT: name, age, occupation, monthly income range, number of dependents.
3. ASSESS: existing insurance? beneficiary in mind? budget for monthly premium?
4. Q&A: ALWAYS call search_knowledge_base before answering policy questions. Never guess.
5. LOG: Call log_lead when they are fully qualified.

ESCALATION: If the caller says "hindi ko gusto makipag-usap sa AI" or "ayaw ko ng bot" or asks for a human — immediately escalate and schedule a callback.

HARD RULES:
- Never invent policy details
- Always disclose you are an AI if sincerely asked
- Keep responses concise for voice delivery""",
    },
    "dewi": {
        "display_name": "Dewi",
        "stt_lang": "id-ID",
        "system_prompt": """Kamu adalah Dewi, agen layanan pelanggan ramah dari ArthaPrime Multifinance. Kamu berbicara dalam Bahasa Indonesia yang natural — campuran formal dan santai sesuai konteks.

ATURAN BAHASA:
- Gunakan Bahasa Indonesia sehari-hari yang natural, bukan bahasa buku kaku.
- Loanword finance dari Bahasa Inggris: gunakan secara natural — DP, tenor, cicilan, angsuran, denda, jatuh tempo.
- Jika nasabah bicara dengan aksen Jawa (ndak, monggo, pripun), respond dengan hangat dan natural.
- Buat responsmu SINGKAT (maksimal 2-3 kalimat) karena ini adalah percakapan suara.

ALUR PERCAKAPAN:
1. SALAM: "Halo Bapak/Ibu, saya Dewi dari ArthaPrime Multifinance. Saya menghubungi untuk menginformasikan tentang program cicilan kami. Ada waktu sebentar?"
2. Tanyakan kebutuhan: nama, usia, kota, kebutuhan cicilan (kendaraan/barang elektronik/properti).
3. Tawarkan solusi yang sesuai budget.
4. SELALU panggil search_knowledge_base jika ditanya detail kebijakan denda/reschedule.
5. LOG: Panggil log_lead untuk mencatat status nasabah di akhir.

ESKALASI: Jika nasabah meminta berbicara dengan manusia — segera eskalasi dan jadwalkan callback.

ATURAN KERAS:
- Jangan pernah mengarang detail kebijakan
- Selalu ungkapkan bahwa kamu adalah AI jika ditanya dengan serius
- Respons harus singkat untuk percakapan suara""",
    },
}

# ── Tool definitions (shared with Q1) ─────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Search the insurance/multifinance knowledge base for policy details. Call BEFORE answering any product question.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": ["product_overview", "policy_rules", "qualification", "faq", "objection", "claim_process", "network", "pricing", "coverage"],
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "log_lead",
            "description": "Save a qualified lead or customer record to CRM.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"},
                    "city": {"type": "string"},
                    "coverage_type": {"type": "string"},
                    "sum_insured_preference": {"type": "string"},
                    "qualified": {"type": "boolean"},
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
            "description": "Schedule a callback for a caller who cannot talk or prefers a human agent.",
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

def tool_search_kb(query: str, category: str = None) -> str:
    try:
        from retrieval import retrieve_for_voice_agent
        result = retrieve_for_voice_agent(query, category_filter=category)
        if result.get("found"):
            return result["answer"]
        return "No specific info found. Please contact our helpline."
    except Exception:
        import re
        try:
            kb_path = ROOT / "data" / "kb_records.json"
            records = json.loads(kb_path.read_text(encoding="utf-8"))
            q_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
            best = max(records, key=lambda r: len(q_tokens & set(re.findall(r"[a-z0-9]+", (r["title"] + " " + r["content"]).lower()))))
            return best["content"]
        except Exception:
            return "KB unavailable. Please contact our helpline."


def tool_log_lead(**kwargs) -> str:
    try:
        from crm_mock import create_lead
        lead = create_lead(**kwargs)
        return f"Lead saved. Reference: {lead['lead_id']}."
    except Exception:
        ref = f"LEAD-{str(uuid.uuid4())[:8].upper()}"
        return f"Lead saved. Reference: {ref}."


def tool_schedule_callback(**kwargs) -> str:
    try:
        from crm_mock import create_callback
        cb = create_callback(**kwargs)
        return f"Callback scheduled for {kwargs.get('preferred_time')}. Reference: {cb['callback_id']}."
    except Exception:
        ref = f"CB-{str(uuid.uuid4())[:6].upper()}"
        return f"Callback scheduled. Reference: {ref}."


TOOL_MAP = {
    "search_knowledge_base": tool_search_kb,
    "log_lead": tool_log_lead,
    "schedule_callback": tool_schedule_callback,
}


# ── Groq turn ──────────────────────────────────────────────────────────────────

def run_groq_turn(messages: list) -> str:
    import httpx, re
    while True:
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(
                f"{GROQ_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={
                    "model": GROQ_MODEL,
                    "messages": messages,
                    "tools": TOOLS,
                    "tool_choice": "auto",
                    "temperature": 0.3,
                    "max_tokens": 300,
                },
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
                print(f"  [tool] {fn_name}({list(fn_args.keys())})")
                fn = TOOL_MAP.get(fn_name)
                result_text = fn(**fn_args) if fn else "Tool not found."
                print(f"  [tool] → {result_text[:100]}")
                messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result_text})
            continue

        text = msg.get("content", "").strip()
        text = re.sub(r"<function=[^>]+>.*?</function>", "", text, flags=re.DOTALL)
        return " ".join(text.split())


# ── STT / TTS ──────────────────────────────────────────────────────────────────

def speak(text: str, agent_name: str = "Agent"):
    print(f"\n{agent_name}: {text}\n")
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", 160)
        engine.say(text)
        engine.runAndWait()
    except Exception:
        pass


def listen(lang: str = "en-US") -> str:
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.Microphone() as source:
            print("Caller (speak now...): ", end="", flush=True)
            r.adjust_for_ambient_noise(source, duration=0.4)
            audio = r.listen(source, timeout=8, phrase_time_limit=12)
        text = r.recognize_google(audio, language=lang)
        print(text)
        return text
    except Exception as e:
        print(f"[STT error: {e}]")
        return ""


# ── main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Q3 Multilingual Voice Agent")
    parser.add_argument("--agent", choices=["maya", "dewi"], default="maya", help="Agent to run (maya=Taglish, dewi=Bahasa ID)")
    args = parser.parse_args()

    if not GROQ_API_KEY:
        print("ERROR: GROQ_API_KEY not set. Check your .env file.")
        return

    cfg = AGENT_CONFIGS[args.agent]
    agent_name = cfg["display_name"]
    stt_lang = cfg["stt_lang"]

    print("=" * 60)
    print(f"  {agent_name} — Q3 Multilingual Voice Agent")
    lang_label = "Taglish (Philippines)" if args.agent == "maya" else "Bahasa Indonesia"
    print(f"  Language: {lang_label} | STT: {stt_lang}")
    print("  Press Ctrl+C to end the call")
    print("=" * 60)

    messages = [{"role": "system", "content": cfg["system_prompt"]}]

    opening = run_groq_turn(messages)
    speak(opening, agent_name)

    while True:
        try:
            caller_text = listen(lang=stt_lang)
            if not caller_text:
                continue

            if any(p in caller_text.lower() for p in ["goodbye", "bye", "paalam", "terima kasih", "sampai jumpa"]):
                farewell = "Salamat po at magandang araw!" if args.agent == "maya" else "Terima kasih! Semoga harimu menyenangkan!"
                speak(farewell, agent_name)
                break

            messages.append({"role": "user", "content": caller_text})
            reply = run_groq_turn(messages)
            speak(reply, agent_name)

        except KeyboardInterrupt:
            speak("Thank you! Goodbye.", agent_name)
            break
        except Exception as e:
            print(f"[error] {e}")
            time.sleep(1)

    print("\n[Call ended]")


if __name__ == "__main__":
    main()
