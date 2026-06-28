"""Launch sequencer and abort controller tests."""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from alpha.countdown import (
    LaunchSequencer, CountdownStep, CountdownState, StepStatus,
)
from omega.abort_controller import (
    AbortController, AbortRule, AbortTier, SensorCheck, create_f9_abort_controller,
)


def test_sequencer_lifecycle():
    seq = LaunchSequencer()
    assert seq.state == CountdownState.IDLE

    seq.add_step(CountdownStep("fueling", t_minus=300, check=lambda: True))
    seq.add_step(CountdownStep("ignition", t_minus=0, check=lambda: True))

    assert seq.start()
    assert seq.state == CountdownState.COUNTING

    assert seq.hold()
    assert seq.state == CountdownState.HOLDED

    assert seq.resume()
    assert seq.state == CountdownState.COUNTING

    assert seq.abort("test")
    assert seq.state == CountdownState.ABORTED
    assert not seq.abort("double")


def test_step_execution():
    seq = LaunchSequencer()
    executed = []
    seq.add_step(CountdownStep(
        "check_tank", t_minus=300,
        check=lambda: (executed.append(True), True)[-1],
    ))

    seq.start()
    result = seq.tick()
    assert any(s["step"] == "check_tank" for s in result.get("steps", []))
    assert len(executed) == 1


def test_step_failure_aborts():
    seq = LaunchSequencer()
    seq.add_step(CountdownStep("bad_step", t_minus=0, check=lambda: False))

    seq.start()
    seq.tick()
    assert seq.state == CountdownState.ABORTED


def test_optional_step_skipped():
    seq = LaunchSequencer()
    seq.add_step(CountdownStep("optional", t_minus=300, check=lambda: False, required=False))
    seq.add_step(CountdownStep("required", t_minus=300, check=lambda: True))

    seq.start()
    result = seq.tick()
    step_result = next((s for s in result["steps"] if s["step"] == "optional"), None)
    assert step_result["status"] == "SKIPPED"
    assert seq.state != CountdownState.ABORTED


def test_event_callbacks():
    seq = LaunchSequencer()
    events = []
    seq.on("countdown_started", lambda d: events.append("started"))
    seq.on("hold", lambda d: events.append("held"))

    seq.start()
    seq.hold()
    assert "started" in events
    assert "held" in events


def test_timeline():
    seq = LaunchSequencer()
    seq.add_step(CountdownStep("a", t_minus=300))
    seq.add_step(CountdownStep("b", t_minus=10))

    timeline = seq.get_timeline()
    assert timeline[0]["name"] == "a"
    assert timeline[1]["name"] == "b"


def test_abort_controller():
    ac = AbortController()
    aborts = []
    ac.on_abort(lambda e: aborts.append(e))

    ac.add_rule(AbortRule(
        name="pressure_high",
        tier=AbortTier.HOLD,
        required_votes=1,
        checks=[SensorCheck("p1", lambda: 99999.0, 0, 100)],
    ))

    ac.sample_all()
    result = ac.evaluate()

    assert result is not None
    assert result["tier"] == "HOLD"
    assert len(aborts) == 1
    assert ac.is_aborted


def test_abort_controller_voting():
    ac = AbortController()
    ac.add_rule(AbortRule(
        name="voting_rule",
        tier=AbortTier.HOLD,
        required_votes=2,
        checks=[
            SensorCheck("s1", lambda: 99999.0, 0, 100),
            SensorCheck("s2", lambda: 99999.0, 0, 100),
            SensorCheck("s3", lambda: 50.0, 0, 100),
        ],
    ))

    ac.sample_all()
    result = ac.evaluate()
    assert result is not None
    assert result["votes"] == 2


def test_f9_abort_controller():
    ac = create_f9_abort_controller()
    assert len(ac.rules) == 2
    health = ac.system_health
    assert health["total_checks"] == 5


def test_abort_history():
    ac = AbortController()
    ac.add_rule(AbortRule(
        name="test_abort",
        tier=AbortTier.HOLD,
        required_votes=1,
        checks=[SensorCheck("s1", lambda: 99999.0, 0, 100)],
    ))

    ac.sample_all()
    ac.evaluate()
    assert len(ac.abort_history) == 1

    ac.reset()
    assert not ac.is_aborted


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
