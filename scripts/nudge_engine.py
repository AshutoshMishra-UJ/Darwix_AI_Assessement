"""Runtime nudge controls: threshold, cooldown, deduplication, expiry, and metrics."""

import time
from collections import Counter


class NudgeEngine:
    def __init__(self, thresholds=None, cooldowns=None, expiry_seconds=120):
        self.thresholds = thresholds or {"high": 0.8, "medium": 0.7, "low": 0.6}
        self.cooldowns = cooldowns or {"compliance_gap": 300, "rising_frustration": 45, "missed_opportunity": 60, "buying_signal": 90}
        self.expiry_seconds = expiry_seconds
        self.last_emitted = {}
        self.active = {}
        self.metrics = Counter()

    def accept(self, signal, now=None):
        now = time.time() if now is None else now
        signal_type = signal["type"]
        confidence = float(signal.get("confidence", 0))
        priority = signal.get("priority", "medium")
        if confidence < self.thresholds.get(priority, 0.7):
            self.metrics["below_threshold"] += 1
            return None
        if now - self.last_emitted.get(signal_type, 0) < self.cooldowns.get(signal_type, 60):
            self.metrics["cooldown_suppressed"] += 1
            return None
        evidence_key = (signal_type, signal.get("evidence", "").strip().lower())
        if evidence_key in self.active and self.active[evidence_key]["expires_at"] > now:
            self.metrics["duplicate_suppressed"] += 1
            return None
        emitted = {**signal, "emitted_at": now, "expires_at": now + self.expiry_seconds, "status": "active"}
        self.last_emitted[signal_type] = now
        self.active[evidence_key] = emitted
        self.metrics["emitted"] += 1
        return emitted

    def expire(self, now=None):
        now = time.time() if now is None else now
        expired = 0
        for item in self.active.values():
            if item["status"] == "active" and item["expires_at"] <= now:
                item["status"] = "expired"
                expired += 1
        self.metrics["expired"] += expired
        return expired

    def report(self):
        return dict(self.metrics)
