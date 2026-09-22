"""
Q2 — Knowledge Base Verification Script
Standalone script to verify KB integrity and retrieval quality.

Run:
  python q2-knowledge-base/verify_kb.py
"""

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).parent.parent

REQUIRED_FIELDS = {"record_id", "category", "title", "content", "source", "version"}
REQUIRED_CATEGORIES = {
    "product_overview", "policy_rules", "qualification", "faq",
    "objection", "claim_process", "network", "pricing", "coverage",
}

DATA_FILE = Path(__file__).parent / "data" / "arogya_shield_plus.json"


def verify_schema(records: list) -> int:
    """Check all records have required fields and valid categories."""
    errors = 0
    for rec in records:
        missing = REQUIRED_FIELDS - set(rec.keys())
        if missing:
            print(f"  ❌ {rec.get('record_id', '?')} missing fields: {missing}")
            errors += 1
        if rec.get("category") not in REQUIRED_CATEGORIES:
            print(f"  ❌ {rec.get('record_id', '?')} invalid category: {rec.get('category')}")
            errors += 1
    return errors


def verify_coverage(records: list) -> dict:
    """Verify at least 1 record per required category."""
    by_cat = {}
    for rec in records:
        cat = rec.get("category", "unknown")
        by_cat.setdefault(cat, []).append(rec["record_id"])
    return by_cat


def verify_retrieval(records: list) -> int:
    """Run 5 quick retrieval checks using the retrieval module."""
    sys.path.insert(0, str(Path(__file__).parent))
    try:
        from retrieval import retrieve_for_voice_agent
        queries = [
            "What is the waiting period for pre-existing conditions?",
            "How much does the Gold plan cost?",
            "Is cataract surgery covered?",
            "How do I make a cashless claim?",
            "Why is health insurance worth the premium?",
        ]
        passed = 0
        for q in queries:
            res = retrieve_for_voice_agent(q)
            if res["found"]:
                passed += 1
                print(f"  ✅ '{q[:50]}...' → {res['results'][0]['record_id']}")
            else:
                print(f"  ❌ '{q[:50]}...' → no result")
        return passed
    except Exception as e:
        print(f"  ⚠️  Retrieval module error: {e}")
        return 0


def main():
    print("=" * 60)
    print("  Q2 Knowledge Base Verification")
    print("=" * 60)

    # 1. Load
    if not DATA_FILE.exists():
        print(f"❌ Data file not found: {DATA_FILE}")
        sys.exit(1)
    records = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    print(f"\n[1] Loaded {len(records)} records from {DATA_FILE.name}")
    assert len(records) >= 40, f"Expected >= 40 records, got {len(records)}"
    print(f"  ✅ Record count: {len(records)} (≥ 40 required)")

    # 2. Schema validation
    print("\n[2] Schema validation ...")
    schema_errors = verify_schema(records)
    if schema_errors == 0:
        print(f"  ✅ All {len(records)} records pass schema validation")
    else:
        print(f"  ❌ {schema_errors} schema errors found")

    # 3. Category coverage
    print("\n[3] Category coverage ...")
    by_cat = verify_coverage(records)
    all_cats_present = True
    for cat in sorted(REQUIRED_CATEGORIES):
        count = len(by_cat.get(cat, []))
        status = "✅" if count > 0 else "❌"
        print(f"  {status} {cat}: {count} records")
        if count == 0:
            all_cats_present = False
    if all_cats_present:
        print(f"  ✅ All {len(REQUIRED_CATEGORIES)} required categories present")

    # 4. Retrieval test
    print("\n[4] Retrieval verification (5 queries) ...")
    passed = verify_retrieval(records)
    print(f"\n  Retrieval: {passed}/5 queries returned results")

    # 5. Summary
    print("\n" + "=" * 60)
    total_ok = schema_errors == 0 and all_cats_present and passed >= 4
    if total_ok:
        print("  ✅ VERIFICATION PASSED — KB is ready for production")
    else:
        print("  ⚠️  VERIFICATION PARTIAL — review issues above")
    print("=" * 60)


if __name__ == "__main__":
    main()
