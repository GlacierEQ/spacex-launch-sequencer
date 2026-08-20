#!/usr/bin/env python3
"""Execute the selected local countdown capability and emit a deterministic receipt."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from alpha.countdown import CountdownStep, EVIDENCE_STATE, LaunchSequencer  # noqa: E402


def _stable(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def build_receipt() -> dict:
    sequencer = LaunchSequencer(t0=10.0)
    sequencer.add_step(CountdownStep("synthetic-readiness", 10.0, check=lambda: True))
    started = sequencer.start()
    held = sequencer.hold()
    frozen_t_minus = round(sequencer.t_minus, 6)
    resumed = sequencer.resume()
    tick = sequencer.tick()
    timeline = sequencer.get_timeline()
    body = {
        "schema": "glaciereq.countdown-operate-receipt.v1",
        "selection_mode": "CURRENT_BEST_REVISABLE",
        "capability": "deterministic-local-countdown-orchestration",
        "evidence_state": EVIDENCE_STATE,
        "started": started,
        "held": held,
        "resumed": resumed,
        "frozen_t_minus": frozen_t_minus,
        "tick": tick,
        "timeline": timeline,
        "event_count": len(sequencer.event_log),
        "external_actions_executed": 0,
    }
    return {**body, "receipt_sha256": hashlib.sha256(_stable(body)).hexdigest()}


def main() -> int:
    receipt = build_receipt()
    print(json.dumps(receipt, indent=2, sort_keys=True))
    valid = (
        receipt["evidence_state"] == EVIDENCE_STATE
        and receipt["selection_mode"] == "CURRENT_BEST_REVISABLE"
        and receipt["started"] is True
        and receipt["held"] is True
        and receipt["resumed"] is True
        and receipt["tick"]["evidence_state"] == EVIDENCE_STATE
        and receipt["timeline"][0]["status"] == "PASSED"
        and receipt["event_count"] >= 5
        and receipt["external_actions_executed"] == 0
        and len(receipt["receipt_sha256"]) == 64
    )
    return 0 if valid else 2


if __name__ == "__main__":
    raise SystemExit(main())
