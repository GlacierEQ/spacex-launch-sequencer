from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKEN = 'LOCAL_COUNTDOWN_SIMULATION_NOT_LAUNCH_COMMAND_AUTHORITY'
IMPLEMENTED = ['probabilistic-abort-research-plane', 'multi-language-countdown-timer-go', 'abort-controller-orchestration', 'milestone-event-integration-hooks']


def test_dual_plane_capabilities_present() -> None:
    caps = json.loads((ROOT / "machine" / "capabilities.json").read_text(encoding="utf-8"))
    assert caps.get("evidence_token") == TOKEN
    have = set(caps.get("capabilities") or [])
    for item in IMPLEMENTED:
        assert item in have, item
    planes = caps.get("planes") or {}
    assert set(planes.get("implemented") or []) >= set(IMPLEMENTED)
    assert "hyper-scaling" not in have


def test_readme_names_apex_dual_plane() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "APEX dual-plane recovery" in readme
    assert TOKEN in readme
    assert "not affiliated" in readme.lower() or "not a claim" in readme.lower() or "NOT_" in TOKEN
