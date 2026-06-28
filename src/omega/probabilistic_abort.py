"""Probabilistic abort decision — maximize mission success, not just safety.

Standard abort: binary threshold → abort or don't.
Innovation: Compute probability distribution of outcomes for each decision
(abort, continue, hold) and choose the path that maximizes expected
mission success.

The wheel: abort conditions
The vehicle: expected value optimization under uncertainty

Key insight: Sometimes aborting is MORE dangerous than continuing.
If you're 30 seconds from orbit and an engine degrades, aborting means
a ballistic reentry (dangerous). Continuing means reaching orbit with
reduced margin (risky but survivable). The probabilistic approach
computes which path has higher expected success.
"""

import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SystemState:
    engine_health: list[float]
    fuel_remaining_kg: float
    altitude_m: float
    velocity_ms: float
    flight_path_angle_deg: float
    time_to_orbit_s: float
    time_to_ground_s: float
    max_g_tolerance: float
    current_g_load: float


@dataclass
class AbortDecision:
    decision: str
    expected_success_prob: float
    abort_success_prob: float
    continue_success_prob: float
    hold_success_prob: float
    reasoning: str
    risk_factors: list[str]


class OutcomePredictor:
    """Predicts mission outcomes for each decision path.

    Uses Monte Carlo simulation with perturbed initial conditions
    to estimate success probability for abort, continue, and hold.
    """

    def __init__(self, num_samples: int = 200, seed: int = 42):
        self.num_samples = num_samples
        self._rng_state = seed

    def _random(self) -> float:
        self._rng_state = (1103515245 * self._rng_state + 12345) & 0x7FFFFFFF
        return self._rng_state / 0x7FFFFFFF

    def _gaussian(self, mean: float, std: float) -> float:
        u1 = max(self._random(), 1e-10)
        u2 = self._random()
        z = math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
        return mean + std * z

    def predict_abort_outcome(self, state: SystemState) -> dict:
        successes = 0
        landing_sites = []

        for _ in range(self.num_samples):
            alt = state.altitude_m
            vel = state.velocity_ms
            g_load = state.current_g_load

            vel_perturbed = vel * (1 + self._gaussian(0, 0.02))
            g_perturbed = g_load * (1 + self._gaussian(0, 0.05))

            if alt > 100000:
                reentry_g = 3.0 + self._gaussian(0, 0.5)
            elif alt > 40000:
                reentry_g = 5.0 + self._gaussian(0, 1.0)
            else:
                reentry_g = 8.0 + self._gaussian(0, 2.0)

            survived = reentry_g < state.max_g_tolerance
            if survived:
                successes += 1

            landing_sites.append({
                "g_load": reentry_g,
                "survived": survived,
            })

        return {
            "success_rate": successes / self.num_samples,
            "avg_g_load": sum(s["g_load"] for s in landing_sites) / len(landing_sites),
            "max_g_load": max(s["g_load"] for s in landing_sites),
        }

    def predict_continue_outcome(self, state: SystemState) -> dict:
        successes = 0

        for _ in range(self.num_samples):
            engines = [h * (1 + self._gaussian(0, 0.02)) for h in state.engine_health]
            fuel = state.fuel_remaining_kg * (1 + self._gaussian(0, 0.01))

            active_engines = sum(1 for h in engines if h > 0.5)
            min_health = min(engines) if engines else 0

            thrust_ratio = active_engines / len(engines) if engines else 0
            fuel_ratio = fuel / state.fuel_remaining_kg if state.fuel_remaining_kg > 0 else 0

            time_to_orbit = state.time_to_orbit_s * (1 / max(thrust_ratio, 0.1))
            fuel_needed = time_to_orbit * 50

            reached_orbit = (
                fuel > fuel_needed and
                thrust_ratio > 0.5 and
                min_health > 0.3
            )

            if reached_orbit:
                successes += 1

        return {
            "success_rate": successes / self.num_samples,
            "thrust_margin": sum(1 for h in state.engine_health if h > 0.5) / len(state.engine_health),
            "fuel_margin": state.fuel_remaining_kg / max(state.time_to_orbit_s * 50, 1),
        }

    def predict_hold_outcome(self, state: SystemState) -> dict:
        successes = 0

        for _ in range(self.num_samples):
            engines = [h * (1 + self._gaussian(0, 0.01)) for h in state.engine_health]
            fuel = state.fuel_remaining_kg * (1 - self._gaussian(0.001, 0.0005))

            degraded = sum(1 for h in engines if h < 0.7)
            recovery_prob = 0.3 if degraded > 0 else 0.8

            recovered = self._random() < recovery_prob
            fuel_sufficient = fuel > state.time_to_orbit_s * 50

            if recovered and fuel_sufficient:
                successes += 1

        return {
            "success_rate": successes / self.num_samples,
            "recovery_probability": 0.3 if any(h < 0.7 for h in state.engine_health) else 0.8,
            "fuel_bleed_rate_kg_s": 0.001 * state.fuel_remaining_kg,
        }


class ProbabilisticAbortController:
    """Full probabilistic abort decision system.

    The wheel: abort conditions
    The vehicle: expected value optimization

    Instead of "abort if X > threshold", this computes:
    P(success | abort), P(success | continue), P(success | hold)
    and picks the maximum.

    This captures cases where:
    - Aborting is more dangerous than continuing (late-flight abort)
    - Holding allows recovery (transient sensor glitch)
    - Continuing has acceptable risk (degraded but functional)
    """

    def __init__(self):
        self.predictor = OutcomePredictor()
        self._decision_log: list[dict] = []

    def make_decision(self, state: SystemState) -> AbortDecision:
        abort_result = self.predictor.predict_abort_outcome(state)
        continue_result = self.predictor.predict_continue_outcome(state)
        hold_result = self.predictor.predict_hold_outcome(state)

        abort_prob = abort_result["success_rate"]
        continue_prob = continue_result["success_rate"]
        hold_prob = hold_result["success_rate"]

        probs = {
            "ABORT": abort_prob,
            "CONTINUE": continue_prob,
            "HOLD": hold_prob,
        }
        decision = max(probs, key=probs.get)

        risk_factors = []
        if abort_prob < 0.7:
            risk_factors.append(f"Abort survival only {abort_prob:.0%}")
        if continue_prob < 0.7:
            risk_factors.append(f"Continue success only {continue_prob:.0%}")
        if state.time_to_orbit_s < 60 and decision == "ABORT":
            risk_factors.append("Late-flight abort — high reentry loads")
        if any(h < 0.5 for h in state.engine_health):
            risk_factors.append("Engine degraded below 50%")

        reasoning = self._build_reasoning(
            decision, abort_prob, continue_prob, hold_prob, state
        )

        result = AbortDecision(
            decision=decision,
            expected_success_prob=probs[decision],
            abort_success_prob=abort_prob,
            continue_success_prob=continue_prob,
            hold_success_prob=hold_prob,
            reasoning=reasoning,
            risk_factors=risk_factors,
        )

        self._decision_log.append({
            "decision": decision,
            "probabilities": probs,
            "altitude_m": state.altitude_m,
            "velocity_ms": state.velocity_ms,
            "engine_health": state.engine_health,
        })

        return result

    def _build_reasoning(
        self,
        decision: str,
        abort_p: float,
        continue_p: float,
        hold_p: float,
        state: SystemState,
    ) -> str:
        if decision == "ABORT":
            if state.time_to_orbit_s < 120:
                return f"Aborting despite proximity to orbit ({state.time_to_orbit_s:.0f}s). Abort survival {abort_p:.0%} exceeds continue success {continue_p:.0%}."
            return f"Abort gives {abort_p:.0%} success vs continue {continue_p:.0%}. Safest path."
        elif decision == "CONTINUE":
            if state.time_to_orbit_s < 60:
                return f"Continuing — {state.time_to_orbit_s:.0f}s to orbit. Abort would mean high-g reentry. Continue success {continue_p:.0%}."
            return f"Continue gives {continue_p:.0%} success. Degraded but functional."
        else:
            return f"Holding — {hold_p:.0%} success. Transient issue may recover. Fuel bleed acceptable."

    @property
    def decision_statistics(self) -> dict:
        if not self._decision_log:
            return {"total_decisions": 0}

        recent = self._decision_log[-20:]
        return {
            "total_decisions": len(self._decision_log),
            "abort_rate": sum(1 for d in recent if d["decision"] == "ABORT") / len(recent),
            "continue_rate": sum(1 for d in recent if d["decision"] == "CONTINUE") / len(recent),
            "hold_rate": sum(1 for d in recent if d["decision"] == "HOLD") / len(recent),
        }
