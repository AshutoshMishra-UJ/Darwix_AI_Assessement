"""
CRM Mock — shared lead and callback store.
Reads/writes crm_leads.json and callbacks.json in this directory.
Used by both local terminal agents (Q1, Q3) and the web pipeline (Q4).
"""

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

LEADS_FILE = Path(__file__).parent / "crm_leads.json"
CALLBACKS_FILE = Path(__file__).parent / "callbacks.json"


def _load(path: Path) -> list:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save(path: Path, data: list) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Leads
# ---------------------------------------------------------------------------

def create_lead(
    name: str,
    age: int,
    city: str,
    coverage_type: str,
    sum_insured_preference: str,
    qualified: bool,
    recommended_plan: str = "Gold",
    pre_existing_conditions: str = "None",
    notes: str = "",
    agent: str = "aria",
) -> dict:
    lead_id = f"LEAD-{str(uuid.uuid4())[:8].upper()}"
    lead = {
        "lead_id": lead_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "timestamp": time.time(),
        "agent": agent,
        "name": name,
        "age": age,
        "city": city,
        "coverage_type": coverage_type,
        "sum_insured_preference": sum_insured_preference,
        "qualified": qualified,
        "recommended_plan": recommended_plan,
        "pre_existing_conditions": pre_existing_conditions,
        "notes": notes,
        "status": "new",
    }
    leads = _load(LEADS_FILE)
    leads.append(lead)
    _save(LEADS_FILE, leads)
    print(f"[CRM] Lead saved: {lead_id} — {name} ({city})")
    return lead


def get_leads() -> list:
    return _load(LEADS_FILE)


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

def create_callback(
    name: str,
    preferred_time: str,
    phone: str = "not provided",
    reason: str = "",
    callback_id: str = None,
    agent: str = "aria",
) -> dict:
    cb_id = callback_id or f"CB-{str(uuid.uuid4())[:6].upper()}"
    callback = {
        "callback_id": cb_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "timestamp": time.time(),
        "agent": agent,
        "name": name,
        "phone": phone,
        "preferred_time": preferred_time,
        "reason": reason,
        "status": "scheduled",
    }
    callbacks = _load(CALLBACKS_FILE)
    callbacks.append(callback)
    _save(CALLBACKS_FILE, callbacks)
    print(f"[CRM] Callback scheduled: {cb_id} — {name} at {preferred_time}")
    return callback


def get_callbacks() -> list:
    return _load(CALLBACKS_FILE)


# ---------------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("--- CRM smoke test ---")
    lead = create_lead(
        name="Test User",
        age=32,
        city="Bangalore",
        coverage_type="individual",
        sum_insured_preference="10L",
        qualified=True,
        recommended_plan="Gold",
    )
    print(f"Lead created: {lead['lead_id']}")
    cb = create_callback(name="Test User", preferred_time="5 PM today", reason="Wants quote details")
    print(f"Callback created: {cb['callback_id']}")
    print(f"Total leads: {len(get_leads())}")
    print(f"Total callbacks: {len(get_callbacks())}")
