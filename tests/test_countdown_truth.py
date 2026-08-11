from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from alpha.countdown import (
    EVIDENCE_STATE,
    AbortCondition,
    CountdownState,
    CountdownStep,
    LaunchSequencer,
    StepStatus,
)


def test_countdown_uses_duration_not_wall_clock_epoch() -> None:
    sequencer = LaunchSequencer(t0=1.0)
    assert sequencer.t_minus == 1.0
    assert sequencer.start() is True
    first = sequencer.t_minus
    time.sleep(0.01)
    second = sequencer.t_minus
    assert 0.0 < second < first <= 1.0


def test_hold_freezes_countdown_and_resume_continues() -> None:
    sequencer = LaunchSequencer(t0=0.1)
    sequencer.start()
    time.sleep(0.005)
    assert sequencer.hold() is True
    frozen = sequencer.t_minus
    time.sleep(0.015)
    assert abs(sequencer.t_minus - frozen) < 0.003
    assert sequencer.resume() is True
    time.sleep(0.005)
    assert sequencer.t_minus < frozen


def test_abort_condition_exception_fails_closed() -> None:
    sequencer = LaunchSequencer(t0=10)

    def broken_check() -> bool:
        raise RuntimeError("private detail")

    sequencer.add_abort_condition(AbortCondition("broken", broken_check))
    sequencer.start()
    result = sequencer.tick()
    assert result["state"] == "ABORTED"
    assert result["evidence_state"] == EVIDENCE_STATE
    assert "private detail" not in str(sequencer.event_log)


def test_required_step_failure_aborts_without_exception_text() -> None:
    sequencer = LaunchSequencer(t0=0)

    def broken_step() -> bool:
        raise RuntimeError("sensitive handler detail")

    step = CountdownStep("required", t_minus=0, check=broken_step)
    sequencer.add_step(step)
    sequencer.start()
    result = sequencer.tick()
    assert sequencer.state == CountdownState.ABORTED
    assert step.status == StepStatus.FAILED
    assert step.error == "check_error"
    assert "sensitive handler detail" not in str(sequencer.event_log)
    assert result["evidence_state"] == EVIDENCE_STATE


def test_callback_failure_cannot_erase_event_or_break_state_transition() -> None:
    sequencer = LaunchSequencer(t0=1.0)

    def broken_callback(_: dict) -> None:
        raise RuntimeError("observer detail")

    sequencer.on("countdown_started", broken_callback)
    assert sequencer.start() is True
    assert sequencer.state == CountdownState.COUNTING
    rendered = str(sequencer.event_log)
    assert "countdown_started" in rendered
    assert "callback_failed" in rendered
    assert "observer detail" not in rendered


def test_liftoff_uses_post_check_t_minus_without_extra_tick() -> None:
    sequencer = LaunchSequencer(t0=0.02)

    def slow_success() -> bool:
        time.sleep(0.03)
        return True

    sequencer.add_step(CountdownStep("slow", t_minus=0.02, check=slow_success))
    sequencer.start()
    result = sequencer.tick()
    assert result["state"] == "LIFTOFF"
    assert result["t_minus"] <= 0
