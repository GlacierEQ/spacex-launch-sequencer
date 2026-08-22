#!/usr/bin/env python3
"""Execute a synthetic hold/recycle/complete mission sequence and emit a receipt."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.mission_sequence_controller import (  # noqa: E402
    GateObservation,
    GateState,
    MissionSequenceController,
)


def evidence(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def gate(name: str, *, state: GateState = GateState.GO, observed_at: float = 100.0, source: str = "synthetic"):
    return GateObservation(name, state, observed_at, source, evidence(f"{name}:{source}:{state.value}"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    controller = MissionSequenceController(max_evidence_age=30)
    timeline = []
    timeline.append(controller.evaluate([], now=1).as_dict())

    incomplete = [gate("vehicle"), gate("ground")]
    timeline.append(controller.evaluate(incomplete, now=100).as_dict())

    readiness = [gate("vehicle"), gate("ground"), gate("weather")]
    timeline.append(controller.evaluate(readiness, now=100).as_dict())

    disagreement = [
        gate("vehicle"),
        gate("ground"),
        gate("weather"),
        gate("range", source="primary"),
        gate("range", state=GateState.HOLD, source="secondary"),
    ]
    timeline.append(controller.evaluate(disagreement, now=100).as_dict())

    commit_ready = [
        gate("vehicle"), gate("ground"), gate("weather"), gate("range")
    ]
    timeline.append(controller.evaluate(commit_ready, now=100).as_dict())
    timeline.append(controller.recycle("READINESS_REVIEW").as_dict())
    timeline.append(controller.evaluate(readiness, now=100).as_dict())
    timeline.append(controller.evaluate(commit_ready, now=100).as_dict())
    final_ready = commit_ready + [gate("mission")]
    timeline.append(controller.evaluate(final_ready, now=100).as_dict())

    actions = [row["action"] for row in timeline]
    expected = [
        "ADVANCE",
        "HOLD",
        "ADVANCE",
        "HOLD",
        "ADVANCE",
        "RECYCLE",
        "ADVANCE",
        "ADVANCE",
        "COMPLETE",
    ]
    if actions != expected:
        raise SystemExit(f"unexpected mission-sequence path: {actions}")

    payload = {
        "schema": "glaciereq.spacex-mission-sequence-scenario.v1",
        "evidence_state": "DETERMINISTIC_PORTFOLIO_MISSION_SEQUENCE_MODEL",
        "timeline": timeline,
        "expected_actions": expected,
        "claims_not_established": [
            "SpaceX affiliation or internal launch procedure",
            "launch hardware control",
            "vehicle or range command authority",
            "real mission readiness",
            "production launch sequencing",
        ],
    }
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(encoded)
    artifact_sha = hashlib.sha256(encoded).hexdigest()

    receipt = {
        "schema": "glaciereq.spacex-mission-sequence-receipt.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository": os.environ.get("GITHUB_REPOSITORY", "GlacierEQ/spacex-launch-sequencer"),
        "commit": os.environ.get("GITHUB_SHA", "local"),
        "artifact": str(args.output),
        "artifact_sha256": artifact_sha,
        "verified_state": "MISSION_SEQUENCE_SCENARIO_EXECUTED",
        "terminal_stage": timeline[-1]["stage_after"],
        "terminal_action": timeline[-1]["action"],
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
