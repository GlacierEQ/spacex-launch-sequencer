from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "LOCAL_COUNTDOWN_SIMULATION_NOT_LAUNCH_COMMAND_AUTHORITY"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def main() -> None:
    readme = read("README.md")
    python_countdown = read("src/alpha/countdown.py")
    go_countdown = read("src/countdown_timer.go")
    capabilities = json.loads(read("machine/capabilities.json"))
    target = json.loads(read("machine/target-contract.json"))
    planes = json.loads(read("machine/capability-planes.json"))
    excellence = json.loads(read("machine/excellence-state.json"))

    assert TOKEN in readme
    assert TOKEN in python_countdown
    assert TOKEN in go_countdown
    assert "not affiliated with, endorsed by" in readme
    assert "SpaceX Launch Director" not in readme
    assert "high-precision launch countdown timer" not in readme.lower()
    assert "sub-millisecond jitter" not in readme.lower()
    assert "Fully wired into APEX Highway mesh" not in readme
    assert "real-time countdown state for orchestrator agents" not in readme
    assert "hyper-scaling" not in capabilities["capabilities"]

    evidence = target["evidence_checkpoint"]
    assert evidence["evidence_token"] == TOKEN
    assert evidence["verified_capability"] == "deterministic-local-countdown-orchestration"
    assert evidence["canonical_proof_head"] == "f931665de0d91b3a5a52748a30a76716d65bbe0a"
    assert target["implementation_checkpoint"]["deployed"] is False
    assert target["target_architecture"]["status"] == "PRESERVED_UNVERIFIED_TARGET_ARCHITECTURE"
    assert len(target["target_architecture"]["objectives"]) >= 8

    assert planes["projection"]["projection_may_overwrite_canonical_or_target"] is False
    assert planes["target"]["status"] == "PRESERVED_UNVERIFIED_TARGET_ARCHITECTURE"
    assert len(planes["target"]["items"]) >= 8
    target_states = {item["state"] for item in planes["target"]["items"]}
    assert "UNVERIFIED_TARGET" in target_states
    assert "PARTIALLY_IMPLEMENTED_TARGET" in target_states

    targets = {item["capability"] for item in planes["target"]["items"]}
    assert "timing-jitter and real-time scheduling benchmark research" in targets
    assert "weather-window optimization research" in targets
    assert "hold-risk prediction research" in targets
    assert "countdown anomaly-detection research" in targets
    assert "programmatic countdown-status service" in targets
    assert "governed milestone-event publication into an orchestration mesh" in targets

    assert excellence["product_state"] == "FUNCTIONAL_LOCAL_COUNTDOWN_ORCHESTRATOR"
    assert excellence["evidence_state"] == "EXACT_HEAD_VERIFIED"
    assert excellence["projection_state"] == TOKEN
    assert excellence["target_state"] == "PRESERVED_UNVERIFIED_TARGET_ARCHITECTURE"
    assert excellence["evidence_checkpoint"]["head_sha"] == "f931665de0d91b3a5a52748a30a76716d65bbe0a"
    assert "HYPER_VALIDATED" not in json.dumps(excellence, sort_keys=True)

    print(TOKEN)


if __name__ == "__main__":
    main()
