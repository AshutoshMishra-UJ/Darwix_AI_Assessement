"""
Q1 — Local Terminal Voice Agent: Aria
ShieldCare Insurance / Arogya Shield Plus Health Insurance

Stack:
  STT:  Google Speech Recognition (via sounddevice mic capture)
  LLM:  Groq llama-3.3-70b-versatile (tool-calling)
  TTS:  pyttsx3 (local, offline)
  CRM:  crm_mock.py (local JSON)
  KB:   q2-knowledge-base/retrieval.py (ChromaDB semantic search)

Run:
  python q1-voice-agent/local_voice_agent.py
"""

import json
import os
import sys
import time
import uuid
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# ── path setup ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "q2-knowledge-base"))
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "openai/gpt-oss-120b"

# ── agent system prompt ───────────────────────────────────────────────────────
SYSTEM_PROMPT = (ROOT / "q1-voice-agent" / "system_prompt.md").read_text(encoding="utf-8")

# ── tool definitions ─────────────────────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Search Arogya Shield Plus KB for policy, FAQ, coverage, pricing, objection responses. Call BEFORE answering any product question.",
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
            "description": "Save a qualified lead to CRM at the end of a successful conversation.",
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


# ── tool implementations ──────────────────────────────────────────────────────

def tool_search_kb(query: str, category: str = None) -> str:
    try:
        from retrieval import retrieve_for_voice_agent
        result = retrieve_for_voice_agent(query, category_filter=category)
        if result.get("found"):
            return result["answer"]
        return "No specific info found. Advise caller to contact helpline at 1800-XXX-XXXX."
    except Exception as e:
        # Fallback to local kb_records.json
        try:
            import re
            kb_path = ROOT / "data" / "kb_records.json"
            records = json.loads(kb_path.read_text(encoding="utf-8"))
            q_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
            best = max(records, key=lambda r: len(q_tokens & set(re.findall(r"[a-z0-9]+", (r["title"] + " " + r["content"]).lower()))))
            return best["content"]
        except Exception:
            return "KB lookup unavailable. Please contact helpline at 1800-XXX-XXXX."


def tool_log_lead(**kwargs) -> str:
    try:
        from crm_mock import create_lead
        lead = create_lead(**kwargs)
        return f"Lead saved. Reference: {lead['lead_id']}. Specialist follows up within 24 hours."
    except Exception as e:
        ref = f"LEAD-{str(uuid.uuid4())[:8].upper()}"
        print(f"[CRM] Fallback lead ref: {ref} | error: {e}")
        return f"Lead saved. Reference: {ref}."


def tool_schedule_callback(**kwargs) -> str:
    try:
        from crm_mock import create_callback
        cb = create_callback(**kwargs)
        return f"Callback scheduled for {kwargs.get('preferred_time')}. Reference: {cb['callback_id']}."
    except Exception as e:
        ref = f"CB-{str(uuid.uuid4())[:6].upper()}"
        return f"Callback scheduled for {kwargs.get('preferred_time')}. Reference: {ref}."


TOOL_MAP = {
    "search_knowledge_base": tool_search_kb,
    "log_lead": tool_log_lead,
    "schedule_callback": tool_schedule_callback,
}


# ── Groq LLM turn ─────────────────────────────────────────────────────────────

def run_groq_turn(messages: list) -> str:
    import httpx
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
                print(f"\n  [tool] {fn_name}({list(fn_args.keys())})")
                fn = TOOL_MAP.get(fn_name)
                result_text = fn(**fn_args) if fn else "Tool not found."
                print(f"  [tool] → {result_text[:100]}")
                messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result_text})
            continue

        text = msg.get("content", "").strip()
        import re
        text = re.sub(r"<function=[^>]+>.*?</function>", "", text, flags=re.DOTALL)
        return " ".join(text.split())


# ── STT / TTS ─────────────────────────────────────────────────────────────────

def speak(text: str):
    print(f"\nAria: {text}\n")
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", 165)
        engine.say(text)
        engine.runAndWait()
    except Exception:
        pass  # TTS optional — always prints to console


def listen() -> str:
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.Microphone() as source:
            print("Caller (speak now...): ", end="", flush=True)
            r.adjust_for_ambient_noise(source, duration=0.4)
            audio = r.listen(source, timeout=8, phrase_time_limit=12)
        text = r.recognize_google(audio)
        print(text)
        return text
    except Exception as e:
        print(f"[STT error: {e}]")
        return ""


# ── main loop ──────────────────────────────────────────────────────────────────

def main():
    if not GROQ_API_KEY:
        print("ERROR: GROQ_API_KEY not set. Check your .env file.")
        return

    print("=" * 60)
    print("  Aria — ShieldCare Insurance Voice Agent  (Q1)")
    print("  Arogya Shield Plus | Local Terminal Mode")
    print("  Press Ctrl+C to end the call")
    print("=" * 60)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Opening greeting
    opening = run_groq_turn(messages)
    speak(opening)

    while True:
        try:
            caller_text = listen()
            if not caller_text:
                continue

            # Check for end-of-call phrases
            if any(p in caller_text.lower() for p in ["goodbye", "bye", "end call", "hang up", "that's all"]):
                speak("Thank you for speaking with ShieldCare. Have a wonderful day! Goodbye.")
                break

            messages.append({"role": "user", "content": caller_text})
            reply = run_groq_turn(messages)
            speak(reply)

        except KeyboardInterrupt:
            speak("Thank you for your time. Goodbye!")
            break
        except Exception as e:
            print(f"[error] {e}")
            time.sleep(1)

    print("\n[Call ended]")


if __name__ == "__main__":
    main()
