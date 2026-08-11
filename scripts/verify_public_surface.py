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

    assert TOKEN in readme
    assert TOKEN in python_countdown
    assert TOKEN in go_countdown
    assert target["evidence_token"] == TOKEN
    assert "not affiliated with, endorsed by" in readme
    assert "SpaceX Launch Director" not in readme
    assert "sub-millisecond" not in readme.lower()
    assert "Fully wired into APEX Highway mesh" not in readme
    assert "real-time countdown state for orchestrator agents" not in readme
    assert "hyper-scaling" not in capabilities["capabilities"]
    assert target["current"]["deployed"] is False
    assert target["verified_capability"] == "deterministic-local-countdown-orchestration"

    print(TOKEN)


if __name__ == "__main__":
    main()
