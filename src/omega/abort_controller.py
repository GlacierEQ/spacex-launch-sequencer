"""Abort controller — monitors vehicle health and triggers automatic abort.

Implements 3-tier abort: hold, hold-down release, in-flight escape.
Each tier has independent sensor checks and voting logic.
"""

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Optional


class AbortTier(Enum):
    HOLD = auto()
    HOLD_DOWN_RELEASE = auto()
    IN_FLIGHT_ESCAPE = auto()


@dataclass
class SensorCheck:
    name: str
    read: Callable[[], float]
    min_val: float = float("-inf")
    max_val: float = float("inf")
    window_size: int = 5
    _values: list[float] = field(default_factory=list)

    def sample(self) -> float:
        val = self.read()
        self._values.append(val)
        if len(self._values) > self.window_size:
            self._values.pop(0)
        return val

    @property
    def mean(self) -> float:
        return sum(self._values) / len(self._values) if self._values else 0.0

    @property
    def healthy(self) -> bool:
        if not self._values:
            return True
        return self.min_val <= self.mean <= self.max_val


@dataclass
class AbortRule:
    name: str
    tier: AbortTier
    required_votes: int
    checks: list[SensorCheck]
    active: bool = True
    _current_votes: int = 0

    def evaluate(self) -> bool:
        if not self.active:
            return False
        failing = sum(1 for c in self.checks if not c.healthy)
        self._current_votes = failing
        return failing >= self.required_votes


class AbortController:
    def __init__(self):
        self.rules: list[AbortRule] = []
        self._abort_callbacks: list[Callable] = []
        self._abort_history: list[dict] = []
        self._active_abort: Optional[AbortTier] = None
        self._abort_time: float = 0.0
        self._sensor_log: list[dict] = []

    def add_rule(self, rule: AbortRule):
        self.rules.append(rule)

    def on_abort(self, callback: Callable):
        self._abort_callbacks.append(callback)

    def sample_all(self) -> dict:
        readings = {}
        for rule in self.rules:
            for check in rule.checks:
                val = check.sample()
                readings[check.name] = {
                    "value": val,
                    "mean": check.mean,
                    "healthy": check.healthy,
                }
        self._sensor_log.append({"time": time.time(), "readings": readings})
        return readings

    def evaluate(self) -> Optional[dict]:
        if self._active_abort is not None:
            return None

        for tier in [AbortTier.HOLD, AbortTier.HOLD_DOWN_RELEASE, AbortTier.IN_FLIGHT_ESCAPE]:
            for rule in self.rules:
                if rule.tier != tier:
                    continue
                if rule.evaluate():
                    abort_event = {
                        "time": time.time(),
                        "tier": tier.name,
                        "rule": rule.name,
                        "failing_checks": [
                            c.name for c in rule.checks if not c.healthy
                        ],
                        "votes": rule._current_votes,
                        "required": rule.required_votes,
                    }
                    self._active_abort = tier
                    self._abort_time = time.time()
                    self._abort_history.append(abort_event)

                    for cb in self._abort_callbacks:
                        cb(abort_event)

                    return abort_event

        return None

    def reset(self):
        self._active_abort = None
        self._abort_time = 0.0
        for rule in self.rules:
            rule._current_votes = 0

    @property
    def is_aborted(self) -> bool:
        return self._active_abort is not None

    @property
    def abort_tier(self) -> Optional[AbortTier]:
        return self._active_abort

    @property
    def abort_history(self) -> list[dict]:
        return list(self._abort_history)

    @property
    def system_health(self) -> dict:
        total_checks = sum(len(r.checks) for r in self.rules)
        healthy_checks = sum(
            sum(1 for c in r.checks if c.healthy)
            for r in self.rules
        )
        return {
            "total_checks": total_checks,
            "healthy_checks": healthy_checks,
            "health_ratio": healthy_checks / total_checks if total_checks else 1.0,
            "active_abort": self._active_abort.name if self._active_abort else None,
            "abort_count": len(self._abort_history),
        }


def create_f9_abort_controller() -> AbortController:
    """Pre-configured abort controller for Falcon 9 first stage."""
    controller = AbortController()

    engine_checks = [
        SensorCheck("chamber_pressure_1", lambda: 0.0, 10000, 12000),
        SensorCheck("chamber_pressure_2", lambda: 0.0, 10000, 12000),
        SensorCheck("chamber_pressure_3", lambda: 0.0, 10000, 12000),
        SensorCheck("turbopump_speed_1", lambda: 0.0, 30000, 36000),
    ]

    controller.add_rule(AbortRule(
        name="engine_out",
        tier=AbortTier.HOLD,
        required_votes=1,
        checks=engine_checks[:2],
    ))

    tank_checks = [
        SensorCheck("lox_level", lambda: 1.0, 0.05, 1.0),
        SensorCheck("rp1_level", lambda: 1.0, 0.05, 1.0),
        SensorCheck("tank_pressure", lambda: 0.0, 100, 400),
    ]

    controller.add_rule(AbortRule(
        name="propellant_anomaly",
        tier=AbortTier.HOLD_DOWN_RELEASE,
        required_votes=2,
        checks=tank_checks,
    ))

    return controller
