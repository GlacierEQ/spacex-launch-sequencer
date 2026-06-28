"""Tests for spacex-launch-sequencer — the voice that counts down.

3 tests. Because every second matters.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import math
from alpha.countdown import LaunchSequencer, CountdownStep, AbortCondition, CountdownState
from omega.probabilistic_abort import ProbabilisticAbortController, OutcomePredictor, SystemState


def test_sequencer_starts():
    seq = LaunchSequencer()
    assert seq.state == CountdownState.IDLE

def test_sequencer_tick():
    seq = LaunchSequencer()
    seq.start()
    result = seq.tick()
    assert result["state"] == "COUNTING"

def test_probabilistic_abort():
    pac = ProbabilisticAbortController()
    state = SystemState(
        engine_health=[0.9, 0.8, 0.85],
        fuel_remaining_kg=50000,
        altitude_m=50000,
        velocity_ms=5000,
        flight_path_angle_deg=-1.0,
        time_to_orbit_s=120,
        time_to_ground_s=300,
        max_g_tolerance=10,
        current_g_load=3,
    )
    decision = pac.make_decision(state)
    assert decision.decision in ("ABORT", "CONTINUE", "HOLD")
    assert 0 <= decision.expected_success_prob <= 1


# T-minus 10, 9, 8...
# The countdown is a promise.
# We keep it.
T_ZERO = 0
assert T_ZERO == 0, "The countdown begins"
