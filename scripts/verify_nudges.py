"""Verify threshold, cooldown, duplicate suppression, and expiry behavior."""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from nudge_engine import NudgeEngine


def main():
    engine = NudgeEngine(expiry_seconds=10)
    signal = {"type": "compliance_gap", "priority": "high", "confidence": 0.9, "evidence": "waiting period not disclosed"}
    emitted = engine.accept(signal, now=1000)
    duplicate = engine.accept(signal, now=1001)
    cooldown = engine.accept({**signal, "evidence": "different evidence"}, now=1010)
    expired = engine.expire(now=1011)
    after_expiry = engine.accept(signal, now=1301)
    result = {"first_emitted": emitted is not None, "duplicate_suppressed": duplicate is None, "cooldown_suppressed": cooldown is None, "expired": expired, "after_cooldown_emitted": after_expiry is not None, "metrics": engine.report()}
    print(json.dumps(result, indent=2))
    return 0 if all([result["first_emitted"], result["duplicate_suppressed"], result["cooldown_suppressed"], result["expired"] == 1, result["after_cooldown_emitted"]]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
