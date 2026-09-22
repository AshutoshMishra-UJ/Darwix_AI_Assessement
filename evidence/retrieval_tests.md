# Retrieval Test Evidence

Dataset: `data/kb_records.json`  
Mode: local lexical baseline, with optional Gemini response generation  
Important: these records are assessment demo content, not a real insurer policy.

| Query | Expected topic | Top record | Result |
|---|---|---|---|
| Can a 62 year old apply? | eligibility | `demo-eligibility-01` | PASS |
| What is the waiting period for pre-existing conditions? | policy | `demo-waiting-01` | PASS |
| How does cashless hospitalisation work? | claims | `demo-claims-01` | PASS |
| The premium is too expensive | objection | `demo-objection-01` | PASS |
| I want to speak to a human | escalation | `demo-escalation-01` | PASS |

Every returned result exposes `record_id`, `source`, `version`, and a numeric match score in the UI and `/api/query` response.
