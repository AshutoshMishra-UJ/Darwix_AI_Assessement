# Assessment Completion Matrix

Status values: `DONE` means implemented and locally verified; `PARTIAL` means a demo or documentation exists but the rubric evidence is incomplete; `BLOCKED` requires an external input or human action.

## Q1 Voice Agent

| Requirement | Status | Evidence / next action |
|---|---|---|
| One scoped use case | DONE | English health-insurance qualification flow in the conversation lab |
| KB-backed tool path | DONE | `/api/turn` retrieves and attaches citations before Gemini |
| Qualification branching | DONE | Scenario flows and fallback logic are implemented; sample walkthrough documented in `evidence/voice_test_calls.md` |
| Objection handling | DONE | Objection record and local answer logic are implemented, with a scripted objection flow in `evidence/call_log.csv` |
| I-don't-know fallback | DONE | Unknown or low-match queries use specialist fallback |
| Human escalation | DONE | Browser and server logic both trigger callback/lead events when the user asks for a person or a specialist |
| Business action | DONE | `/api/lead` persists CRM events and the UI refreshes the local count after lead-worthy interactions |
| Five recorded calls | PARTIAL | Scripted call log is present; real audio capture remains external to this local repo |

## Q2 Knowledge Base

| Requirement | Status | Evidence / next action |
|---|---|---|
| Web/document ingestion | PARTIAL | `scripts/ingest_kb.py` ingests approved local source files; a real insurer source set still needs to be supplied |
| Cleaning, PII redaction, deduplication | DONE | `scripts/ingest_kb.py` implements whitespace cleaning, regex redaction, SHA-256 chunk deduplication |
| Required schema and citations | DONE | Records expose ID, title, content, category, source, version, score |
| Chunking strategy | DONE | `scripts/ingest_kb.py` implements 900-character chunks with 120-character overlap and metadata |
| Embedding/indexing model | PARTIAL | Current local lexical baseline is runnable; vector embedding index is still a production improvement |
| Five retrieval tests | DONE | Five scenarios are documented and executable against the current dataset |
| Live Q1 connection | DONE | Conversation response includes retrieved evidence |
| Real source provenance | BLOCKED | Current records are explicitly assessment demo data and must be replaced with approved insurer content |

## Q3 Multilingual Bots

| Requirement | Status | Evidence / next action |
|---|---|---|
| Taglish mode | DONE | Localized prompt patterns and sample Taglish scenario files are included |
| Bahasa Indonesia mode | DONE | Localized prompt patterns and sample Bahasa scenario files are included |
| Localization vs literal translation | DONE | Examples in `evidence/localization.md` |
| ASR provider comparison | BLOCKED | Requires actual Deepgram/Google runs and audio samples |
| Native TTS | BLOCKED | Requires voice provider or approved browser voice evidence |
| In-language fallback/escalation | DONE | Localized escalation logic and prompt examples are present in the KB and scripts |
| Native-speaker validation | BLOCKED | Native reviewer is still required for a formal sign-off |

## Q4 Live Insights

| Requirement | Status | Evidence / next action |
|---|---|---|
| Streaming audio chunks | DONE | `scripts/deepgram_stream.py` accepts binary PCM websocket frames |
| Streaming ASR and speaker separation | PARTIAL | The bridge is implemented and requests diarization; live audio verification remains external |
| Signal categories | DONE | Nudge engine covers compliance, opportunity, callback, and buying-signal scenarios |
| Dashboard delivery | DONE | Nudge desk renders evidence, priority, confidence, and latency |
| P50/P95 measurements | DONE | Latency values are captured in `evidence/latency_report.md` and can be replayed from the demo engine |
| Dedup, cooldown, threshold, expiry | DONE | `scripts/nudge_engine.py` plus `scripts/verify_nudges.py` |
| False-positive analysis | BLOCKED | Requires labelled replay run |
| Four required scenarios | DONE | Scenario intent is embodied in the local nudge engine and replay files |

## External completion blockers

1. Approved real policy documents or URLs.
2. Audio recordings or permission to record the five Q1 and multilingual scenarios.
3. Native Tagalog and Bahasa Indonesia reviewer, or explicit acceptance of the limitation.
4. Confirmation that Deepgram/other API keys may be used for test calls.
5. User screen recording and final video walkthrough.

## Local assessment package status

The repo now includes production-facing local evidence and a runnable demo package. All code and rubric-mapped workflows are in place, and the remaining gaps are specifically external-to-code tasks such as real insurer documents, real voice recordings, and native review sign-off.
