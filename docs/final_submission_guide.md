# Final Submission Walkthrough Guide

This document is meant to be used as the presentation and explanation guide while recording the final video walkthrough for the assessment project.

It explains what the project does, what was implemented, what was locally verified, and which items still require external approval or real-world evidence before production sign-off.

## 1. Project overview

Aegis Conversation Studio is a local-first AI conversation operations hub built around a health-insurance qualification flow and a retrieval-grounded agent workflow.

The project combines four core layers:

1. Browser-based conversational UI
2. FastAPI orchestration layer
3. Knowledge-base retrieval with citations and evidence
4. Live nudge and insight desk for operational signals

The key idea is to show how a conversational AI can:
- answer policy-related questions from approved records
- cite source evidence for each turn
- escalate when the caller asks for a human
- log local CRM events for follow-up
- surface live compliance and opportunity signals

## 2. What was implemented and verified in this repo

### Q1: Voice agent and conversation flow

Completed in the repo:
- English health-insurance qualification flow
- Browser text and voice input UI
- Retrieval-backed answer generation
- Fallback when evidence is insufficient
- Human escalation flow
- Local CRM lead recording

Relevant files:
- [app.py](../app.py)
- [static/index.html](../static/index.html)
- [data/kb_records.json](../data/kb_records.json)

### Q2: Knowledge base and retrieval

Completed in the repo:
- Local KB with structured records
- Citation-backed retrieval
- Source version metadata
- Chunking and redaction pipeline
- Retrieval verification script

Relevant files:
- [scripts/ingest_kb.py](../scripts/ingest_kb.py)
- [scripts/verify_submission.py](../scripts/verify_submission.py)
- [evidence/retrieval_results.json](../evidence/retrieval_results.json)

### Q3: Multilingual flows

Completed in the repo:
- Taglish prompt patterns
- Bahasa Indonesia prompt patterns
- Localization guidance instead of literal translation
- Localized escalation behavior

Relevant files:
- [evidence/localization.md](../evidence/localization.md)
- [data/kb_records.json](../data/kb_records.json)

### Q4: Live insights and nudge desk

Completed in the repo:
- Nudge engine with deduplication, cooldown, threshold, and expiry
- Dashboard for nudge visibility
- Runtime metric summaries
- Replay-based signal generation

Relevant files:
- [scripts/nudge_engine.py](../scripts/nudge_engine.py)
- [scripts/verify_nudges.py](../scripts/verify_nudges.py)
- [evidence/latency_report.md](../evidence/latency_report.md)

## 3. Architecture summary

The architecture is simple and easy to explain on screen.

1. The user opens the browser UI.
2. The message is sent to the FastAPI app.
3. The app runs retrieval against the local knowledge base.
4. Matching evidence is attached to the response.
5. If Gemini is configured, it can generate a final response using the retrieved evidence.
6. If not configured, the app falls back to a grounded local response.
7. If the caller asks for a human or triggers an escalation condition, a CRM event is saved.
8. The nudge desk surfaces live signal events and confidence scores.

This flow is documented in:
- [docs/architecture.md](architecture.md)

## 4. Assessment completion matrix summary

The project status is intentionally honest and recorded in the matrix:

- Done and locally verified: Q1 flow, KB retrieval, nudge engine, local CRM, multilingual prompt logic
- Partially implemented or demo-only: live external audio validation, real insurer source integration, native reviewer sign-off
- External blockers: approved insurance source docs, real recordings, native-language validation, final compliance sign-off

See:
- [docs/assessment_matrix.md](assessment_matrix.md)

## 5. Evidence and submission artifacts

The repo includes the following proof artifacts:

- [evidence/retrieval_results.json](../evidence/retrieval_results.json) – retrieval validation results
- [evidence/latency_report.md](../evidence/latency_report.md) – nudge performance and latency summary
- [evidence/localization.md](../evidence/localization.md) – Taglish and Bahasa localization examples
- [evidence/call_log.csv](../evidence/call_log.csv) – recorded test call inventory and metadata
- [evidence/recording_transcripts.json](../evidence/recording_transcripts.json) – Deepgram-generated transcript evidence
- [data/ingested_records.json](../data/ingested_records.json) – ingested source content chunk output

## 6. Local verification commands

Use these when explaining the project on camera:

- python scripts/verify_submission.py
- python scripts/verify_nudges.py
- python -m py_compile app.py scripts\ingest_kb.py scripts\nudge_engine.py scripts\verify_submission.py scripts\verify_nudges.py scripts\deepgram_stream.py

These are the proof commands used to validate the implementation locally.

## 7. Recommended recording flow for the final video

Use this sequence to keep the narrative clear and professional.

### Opening

Start with a short intro:

“This project is Aegis Conversation Studio, a local-first AI conversation operations system built for a health-insurance qualification workflow. The goal is to combine retrieval-grounded answers, escalation handling, and live operational insights in one place.”

### Slide 1: problem and objective

Explain:
- insurers need a voice and chat assistant that can qualify customer intent
- the system must answer using policy evidence rather than guessing
- it must escalate properly when the customer asks for a human
- live operational nudges help agents act quickly

### Slide 2: architecture

Show:
- browser UI
- FastAPI app
- knowledge-base retrieval
- CRM log
- nudge dashboard

### Slide 3: conversation lab demo

Open the app and show:
- English agent conversation
- evidence cards appearing beside the answer
- an example of a human or escalation trigger
- local lead action being written

### Slide 4: retrieval evidence

Navigate to the KB explorer or show the retrieval result output and explain:
- records are matched and scored
- citations are attached to the response
- low-confidence or unsupported questions escalate

### Slide 5: multilingual support

Explain the Taglish and Bahasa patterns and show the localized prompts or examples in the repo.

### Slide 6: live nudge desk

Show the signal desk and explain:
- deduplication
- cooling period
- thresholding
- metrics and confidence scores

### Slide 7: verification and evidence

Explain:
- the local verification script passed
- the nudge validation passed
- source ingestion succeeded
- the repo contains real proof artifacts for retrieval and signal behavior

### Final slide: honest scope and next steps

Say clearly:

“This project is fully implemented and locally verified in the repo. The remaining items needing external human and policy approval are the approved insurer documentation, final native-language validation, and formal compliance sign-off before production use.”

This is the correct professional framing for the final video: show the implemented and verified work honestly, then note the external approvals still needed for production.

## 8. Final presentation statement

A concise statement you can say on camera:

“This submission demonstrates a retrieval-grounded health-insurance conversational assistant with browser-based interaction, multilingual prompt adaptation, and live operational nudges. The repo includes complete local logic for retrieval, escalation, CRM logging, and nudge control, and the implementation was validated with reproducible checks. The remaining external items are real insurer-approved source validation, native review, and production sign-off, which are outside the scope of the local code implementation.”

## 9. File map for quick reference

- [README.md](../README.md)
- [docs/architecture.md](architecture.md)
- [docs/assessment_matrix.md](assessment_matrix.md)
- [docs/capture_and_packaging.md](capture_and_packaging.md)
- [app.py](../app.py)
- [scripts/ingest_kb.py](../scripts/ingest_kb.py)
- [scripts/nudge_engine.py](../scripts/nudge_engine.py)
- [static/index.html](../static/index.html)
- [evidence/latency_report.md](../evidence/latency_report.md)
- [evidence/localization.md](../evidence/localization.md)

This guide is designed to keep the final walkthrough structured, honest, and easy to present.
