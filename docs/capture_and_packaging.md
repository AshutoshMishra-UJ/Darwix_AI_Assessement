# Final Capture and Packaging Runbook

## Human-only evidence

The following cannot be generated truthfully by code alone:

- Five Q1 call recordings.
- Two Philippines and two Indonesia call recordings.
- Native-speaker Tagalog and Bahasa review.
- Final screen-recorded walkthrough video.
- Real approved policy-document provenance.

## Recording checklist

Use the browser at `http://127.0.0.1:8002` and screen-record each scenario. Keep the transcript and browser evidence visible.

1. English cooperative caller: age, city, cover type, existing cover, condition, budget, lead action.
2. English objection: expensive premium, evidence retrieval, callback/human option.
3. English conflict: age 67 then 62, underwriting escalation.
4. English out-of-scope: vehicle insurance question and specialist fallback.
5. English human request: explicit transfer request and CRM event.
6. Taglish cooperative and escalation calls.
7. Bahasa Indonesia cooperative and regional-register calls.

Save recordings under `evidence/recordings/` and write the date, model, browser, input language, outcome, and reviewer in `evidence/call_log.csv`.

## Native review

Ask a Tagalog and Bahasa Indonesia reviewer to mark each transcript as `natural`, `needs_edit`, or `unsafe`. Record the reviewer name/role and edits in `evidence/native_review.csv`. Do not claim native quality without this review.

## Video sequence

1. Architecture and connected Q1-Q4 path.
2. English call with KB citation.
3. Retrieval explorer and five-query verifier.
4. Taglish and Bahasa calls with localization examples.
5. Live nudge replay, latency and runtime metrics.
6. Fallback, escalation, and noisy-call behavior.
7. Limitations and production plan.

## GitHub packaging

Before publishing:

- Ensure `.env` is ignored and absent from Git history.
- Remove `__pycache__`, generated CRM data, and private recordings.
- Run `python scripts/verify_submission.py`.
- Run `python scripts/verify_nudges.py`.
- Run `python -m py_compile app.py scripts/*.py`.
- Update the README with the actual source URLs, retrieval date, API model, measured latency, and video link.
- Do not label demo records or deterministic nudge data as real production evidence.
