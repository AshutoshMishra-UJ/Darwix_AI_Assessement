# TESTING.md — Complete Evaluator Testing Guide

**Project:** Aegis Conversation Studio  
**Assessment:** AI Engineer Assessment — Arogya Shield Plus  
**Last updated:** 2026-09-22

This guide walks through every test scenario for all four questions. Follow steps in order for the cleanest demo.

---

## Prerequisites

```powershell
# 1. Activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Build the knowledge base (first time only, ~30s)
python q2-knowledge-base\ingest.py

# 4. Start the main server
python app.py
# → Server running at http://127.0.0.1:8002
```

---

## Quick Verification (All 4 Questions, ~2 minutes)

Run these commands to verify the full submission in one pass:

```powershell
# Python syntax check — all scripts
python -m py_compile app.py scripts\ingest_kb.py scripts\nudge_engine.py scripts\verify_submission.py scripts\verify_nudges.py q1-voice-agent\crm_mock.py q1-voice-agent\local_voice_agent.py q2-knowledge-base\ingest.py q2-knowledge-base\retrieval.py q3-multilingual\local_multilingual_agent.py q4-live-insights\pipeline.py q4-live-insights\replay_audio.py
# Expected: no output = all clear

# KB verification (schema + 5 retrieval tests)
python q2-knowledge-base\verify_kb.py
# Expected: ✅ VERIFICATION PASSED

# Nudge engine verification
python scripts\verify_nudges.py
# Expected: all nudge controls working

# Submission verification
python scripts\verify_submission.py
# Expected: all checks pass
```

---

## Q1 — Voice Agent Testing

### 1A — Web Browser Interface (Recommended for Demo)

1. Open **http://127.0.0.1:8002**
2. Click **"Conversation lab"** in the left nav (tab 02)
3. Ensure **Aria / English** is selected in the agent dropdown
4. Click **"Start call"**

**Test Scenario 1 — Cooperative qualification:**
```
Type: "I'm 34 years old, live in Bangalore, looking for individual health coverage"
Expected: Aria asks for budget, recommends Gold plan, shows KB evidence card on right
```

**Test Scenario 2 — KB retrieval:**
```
Type: "Is cataract surgery covered?"
Expected: Response cites "day-care procedures" KB record (KB-005), evidence card appears
```

**Test Scenario 3 — Human escalation:**
```
Type: "I want to speak to a human agent"
Expected: Aria acknowledges, offers callback, CRM count increments in top-right metric
```

**Test Scenario 4 — Objection:**
```
Type: "The premium is too expensive"
Expected: Groq generates objection response citing Section 80D tax benefit and hospital cost
```

**Test Scenario 5 — Out-of-scope:**
```
Type: "Do you offer motor insurance?"
Expected: Aria redirects to helpline, does NOT attempt to answer motor insurance question
```

### 1B — Voice Input (Chrome required)
1. Click the **🎤 Mic** button
2. Speak: *"Tell me about the Gold plan waiting period"*
3. Expected: STT captures speech, sends to API, evidence card shows KB-004 (PED waiting period)

### 1C — TTS Output
1. Click **🔊 TTS** button to enable (turns green)
2. Send a message
3. Expected: Browser speaks the agent's response aloud

### 1D — Terminal Agent (Optional)
```powershell
python q1-voice-agent\local_voice_agent.py
# Speak into microphone when prompted
# Expected: Aria responds via pyttsx3 TTS
```

---

## Q2 — Knowledge Base Testing

### 2A — Web Evidence Explorer

1. Click **"Evidence index"** (tab 03)
2. Run the pre-filled query: *"What is the waiting period for pre-existing conditions?"*
3. Expected: KB-004 returned with citation and score ≥ 0.42

**Test 5 additional queries:**

| Query | Expected Record | Category |
|---|---|---|
| `"How much does Gold plan cost for 34 year old?"` | KB-002 | pricing |
| `"Is cataract surgery covered?"` | KB-005 | coverage |
| `"How do I file a cashless claim?"` | KB-011 | claim_process |
| `"Why is health insurance worth buying?"` | KB-018 | objection |
| `"What is the no-claim bonus?"` | KB-010 | coverage |

### 2B — API Test (curl / Postman)

```powershell
# Health check
Invoke-RestMethod -Uri "http://127.0.0.1:8002/api/health" -Method GET

# KB query
$body = '{"query": "waiting period for diabetes"}'
Invoke-RestMethod -Uri "http://127.0.0.1:8002/api/query" -Method POST -Body $body -ContentType "application/json"
# Expected: {"found": true, "results": [...KB-004...]}

# All KB records
Invoke-RestMethod -Uri "http://127.0.0.1:8002/api/records" -Method GET
# Expected: {"records": [...40 records...]}
```

### 2C — KB Verification Script

```powershell
python q2-knowledge-base\verify_kb.py
# Expected output:
# ✅ Record count: 40 (≥ 40 required)
# ✅ All 40 records pass schema validation
# ✅ All 8 required categories present
# ✅ 5/5 queries returned results
# ✅ VERIFICATION PASSED — KB is ready for production
```

---

## Q3 — Multilingual Agent Testing

### 3A — Web Browser (Taglish — Maya)

1. Go to **Conversation lab** (tab 02)
2. Select **🌺 Maya / Taglish (PH)** from agent dropdown
3. Type: *"Magkano po ang premium?"* (How much is the premium?)
4. Expected: Maya responds in Taglish with "po" markers, KB evidence on right

### 3B — Web Browser (Bahasa Indonesia — Dewi)

1. Select **🌸 Dewi / Bahasa Indonesia (ID)**
2. Type: *"Berapa DP minimum untuk motor?"* (What is the minimum DP for a motorcycle?)
3. Expected: Dewi responds in natural Bahasa Indonesian

### 3C — Voice with Correct Language STT (Chrome)
1. Select Maya, click **🎤 Mic** — recognition automatically sets to `fil-PH`
2. Select Dewi, click **🎤 Mic** — recognition automatically sets to `id-ID`

### 3D — Terminal Agents (Optional)
```powershell
# Philippines — Maya (Taglish)
python q3-multilingual\local_multilingual_agent.py --agent maya

# Indonesia — Dewi (Bahasa ID)
python q3-multilingual\local_multilingual_agent.py --agent dewi
```

### 3E — Localization Evidence
See: `q3-multilingual/philippines/script.md` — 3 Taglish localization examples  
See: `q3-multilingual/indonesia/script.md` — 3 Bahasa Indonesia localization examples

---

## Q4 — Live Insights Testing

### 4A — Static Nudge Replay (No Deepgram needed)

1. Click **"Live signals"** (tab 04)
2. Click **"↻ Replay signal window"**
3. Expected: 4 nudge cards appear with:
   - Type label (compliance_gap, missed_cross_sell, buying_signal, payment_difficulty)
   - Confidence percentage bar
   - Evidence text
   - Next action recommendation
   - Latency in milliseconds

### 4B — Live Demo Mode (Groq required)

```powershell
# Start Q4 standalone pipeline first
python q4-live-insights\pipeline.py
# → Running on http://localhost:8001

# In another terminal:
python -c "import httpx; print(httpx.get('http://localhost:8001/demo').json())"
# → {"message": "Demo started!", "call_id": "demo-xxx"}
```

Watch **http://localhost:8001** — transcript appears in right panel, nudge cards in left panel as the scripted call plays.

### 4C — API Test

```powershell
# Nudge API
Invoke-RestMethod -Uri "http://127.0.0.1:8002/api/nudges" -Method GET
# Expected: {"nudges": [...], "metrics": {"emitted": N}}
```

### 4D — WebSocket Transcript Feed (Live Signals tab)
The right panel in **Live signals** tab shows a live transcript feed via WebSocket (`/ws/dashboard`). Every turn in the Conversation lab is broadcast there automatically.

### 4E — Latency Evidence
See: `q4-live-insights/latency_report.md`  
- P50 E2E: ~1,300ms | P95 E2E: ~2,100ms
- False positive rate: ~7% (1/14 signals)

### 4F — Replay Audio File

```powershell
# Generate test WAV and replay (requires Q4 pipeline running)
python q4-live-insights\replay_audio.py --generate-test --call-id test-001
```

---

## CRM Leads — Testing

### 5A — Trigger a Lead Event

1. In **Conversation lab**, send: *"I want to speak to a specialist"*
2. Expected: CRM count in **Command Centre** increments

### 5B — View All Leads

1. Click **"CRM leads"** (tab 05)
2. Click **"↻ Refresh"**
3. Expected: Table shows lead events with ID, agent, message, type, status, timestamp

### 5C — API

```powershell
# Get all CRM events
Invoke-RestMethod -Uri "http://127.0.0.1:8002/api/crm" -Method GET

# Get qualified leads
Invoke-RestMethod -Uri "http://127.0.0.1:8002/api/leads" -Method GET

# Manually save a lead
$body = '{"name":"Test User","agent":"aria","lead_type":"callback","channel":"test"}'
Invoke-RestMethod -Uri "http://127.0.0.1:8002/api/lead" -Method POST -Body $body -ContentType "application/json"
```

---

## Full API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Browser UI (index.html) |
| GET | `/api/health` | System status, mode, record count |
| GET | `/api/records` | All 40 KB records |
| POST | `/api/query` | Knowledge base search `{"query": "..."}` |
| POST | `/api/turn` | Agent conversation turn `{"message":"...","agent":"aria"}` |
| POST | `/api/lead` | Save CRM lead `{"name":"...","agent":"..."}` |
| GET | `/api/crm` | All CRM events |
| GET | `/api/leads` | All leads (combined) |
| GET | `/api/nudges` | Live signal nudges with metrics |
| GET | `/demo` | Trigger scripted demo call |
| WS | `/ws/dashboard` | Real-time transcript + nudge broadcast |

---

## Expected Outputs Checklist

- [ ] Server starts on port 8002 without errors
- [ ] `/api/health` returns `{"status":"ok","mode":"groq","records":8}` (or 40 with ChromaDB)
- [ ] Conversation returns grounded answer with evidence card
- [ ] KB query for "waiting period" returns KB-004 with citation
- [ ] Maya responds in Taglish with "po" markers
- [ ] Dewi responds in Bahasa Indonesian
- [ ] Nudge desk shows ≥3 signal cards on replay
- [ ] CRM leads tab shows events after escalation trigger
- [ ] `verify_kb.py` outputs "VERIFICATION PASSED"
- [ ] `verify_nudges.py` outputs all checks passing
