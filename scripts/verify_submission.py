"""Run reproducible local checks and write retrieval evidence.

Usage from the submission directory:
    python scripts/verify_submission.py
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app  # noqa: E402

QUERIES = [
    ("Can a 62 year old apply?", "demo-eligibility-01"),
    ("What is the waiting period for pre-existing conditions?", "demo-waiting-01"),
    ("How does cashless hospitalisation work?", "demo-claims-01"),
    ("The premium is too expensive", "demo-objection-01"),
    ("I want to speak to a human", "demo-escalation-01"),
]


def main():
    results = []
    for query, expected_id in QUERIES:
        top = app.search_kb(query, limit=1)[0]
        results.append({
            "query": query,
            "expected_record_id": expected_id,
            "actual_record_id": top["record_id"],
            "score": top["score"],
            "citation": top["citation"],
            "pass": top["record_id"] == expected_id,
        })
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "local_lexical_baseline",
        "records": len(app.records),
        "passed": sum(item["pass"] for item in results),
        "total": len(results),
        "results": results,
    }
    target = ROOT / "evidence" / "retrieval_results.json"
    target.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps({"passed": output["passed"], "total": output["total"], "output": str(target)}, indent=2))
    return 0 if output["passed"] == output["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
