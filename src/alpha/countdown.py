"""Repository-local countdown state-machine laboratory.

Manages a synthetic T-minus timeline, step dependencies, hold/resume accounting,
and abort conditions. This is not a SpaceX, Falcon, Starship, or production
launch procedure and has no external command authority.
"""

import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, Optional

EVIDENCE_STATE = "LOCAL_COUNTDOWN_SIMULATION_NOT_LAUNCH_COMMAND_AUTHORITY"


class CountdownState(Enum):
    IDLE = auto()
    COUNTING = auto()
    HOLDED = auto()
    ABORTED = auto()
    LIFTOFF = auto()
    COMPLETED = auto()


class StepStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    PASSED = auto()
    FAILED = auto()
    SKIPPED = auto()


@dataclass
class CountdownStep:
    name: str
    t_minus: float
    check: Callable[[], bool] = lambda: True
    timeout: float = 30.0
    required: bool = True
    status: StepStatus = StepStatus.PENDING
    started_at: float = 0.0
    completed_at: float = 0.0
    error: str = ""

    @property
    def elapsed(self) -> float:
        if self.started_at == 0:
            return 0.0
        end = self.completed_at if self.completed_at > 0 else time.monotonic()
        return end - self.started_at


@dataclass
class AbortCondition:
    name: str
    check: Callable[[], bool]
    severity: str = "CRITICAL"
    message: str = ""
    triggered: bool = False
    trigger_time: float = 0.0


class LaunchSequencer:
    def __init__(self, t0: float = 0.0):
        if t0 < 0:
            raise ValueError("initial T-minus must be non-negative")
        self.initial_t_minus = float(t0)
        self.state = CountdownState.IDLE
        self.steps: list[CountdownStep] = []
        self.abort_conditions: list[AbortCondition] = []
        self._started_at: float = 0.0
        self._hold_start: float = 0.0
        self._hold_total: float = 0.0
        self._event_log: list[tuple[float, str]] = []
        self._callbacks: dict[str, list[Callable]] = {}

    def add_step(self, step: CountdownStep):
        self.steps.append(step)
        self.steps.sort(key=lambda step: step.t_minus, reverse=True)

    def add_abort_condition(self, condition: AbortCondition):
        self.abort_conditions.append(condition)

    def on(self, event: str, callback: Callable):
        self._callbacks.setdefault(event, []).append(callback)

    def _emit(self, event: str, data: dict):
        payload = {**data, "evidence_state": EVIDENCE_STATE}
        for callback in self._callbacks.get(event, []):
            callback(payload)
        self._event_log.append((time.time(), f"{event}: {payload}"))

    @property
    def t_minus(self) -> float:
        if self._started_at == 0:
            return self.initial_t_minus
        now = self._hold_start if self.state == CountdownState.HOLDED else time.monotonic()
        elapsed = max(0.0, now - self._started_at - self._hold_total)
        return self.initial_t_minus - elapsed

    def start(self):
        if self.state != CountdownState.IDLE:
            return False
        self.state = CountdownState.COUNTING
        self._started_at = time.monotonic()
        self._hold_total = 0.0
        self._hold_start = 0.0
        self._emit("countdown_started", {"initial_t_minus": self.initial_t_minus})
        return True

    def hold(self) -> bool:
        if self.state != CountdownState.COUNTING:
            return False
        self._hold_start = time.monotonic()
        frozen = self.t_minus
        self.state = CountdownState.HOLDED
        self._emit("hold", {"t_minus": frozen})
        return True

    def resume(self) -> bool:
        if self.state != CountdownState.HOLDED:
            return False
        now = time.monotonic()
        self._hold_total += now - self._hold_start
        self._hold_start = 0.0
        self.state = CountdownState.COUNTING
        self._emit("resume", {"t_minus": self.t_minus})
        return True

    def abort(self, reason: str = "manual") -> bool:
        if self.state in (CountdownState.ABORTED, CountdownState.LIFTOFF):
            return False
        self.state = CountdownState.ABORTED
        self._emit("abort", {"reason": reason, "t_minus": self.t_minus})
        return True

    def _check_aborts(self) -> Optional[AbortCondition]:
        for condition in self.abort_conditions:
            if condition.triggered:
                continue
            try:
                triggered = condition.check()
            except Exception:
                triggered = True
                condition.message = condition.message or "abort condition check failed"
            if triggered:
                condition.triggered = True
                condition.trigger_time = time.time()
                return condition
        return None

    def tick(self) -> dict:
        if self.state != CountdownState.COUNTING:
            return {
                "state": self.state.name,
                "t_minus": self.t_minus,
                "evidence_state": EVIDENCE_STATE,
            }

        triggered = self._check_aborts()
        if triggered:
            self.abort(f"auto: {triggered.name} - {triggered.message}")
            return {
                "state": "ABORTED",
                "trigger": triggered.name,
                "evidence_state": EVIDENCE_STATE,
            }

        current_t = self.t_minus
        results = []

        for step in self.steps:
            if step.status != StepStatus.PENDING:
                continue
            if step.t_minus < current_t:
                continue

            step.status = StepStatus.RUNNING
            step.started_at = time.monotonic()
            self._emit("step_started", {"step": step.name})

            try:
                passed = step.check()
            except Exception:
                passed = False
                step.error = "check_error"

            if passed:
                step.status = StepStatus.PASSED
                step.completed_at = time.monotonic()
                self._emit("step_passed", {"step": step.name})
            else:
                if step.required:
                    step.status = StepStatus.FAILED
                    self._emit("step_failed", {"step": step.name, "error": step.error})
                    self.abort(f"step failed: {step.name}")
                else:
                    step.status = StepStatus.SKIPPED
                    self._emit("step_skipped", {"step": step.name})

            results.append({"step": step.name, "status": step.status.name})
            if self.state == CountdownState.ABORTED:
                break

        required = [step for step in self.steps if step.required]
        all_done = bool(required) and all(
            step.status == StepStatus.PASSED for step in required
        )
        if all_done and current_t <= 0 and self.state == CountdownState.COUNTING:
            self.state = CountdownState.LIFTOFF
            self._emit("liftoff", {"time": time.time()})

        return {
            "state": self.state.name,
            "t_minus": round(current_t, 3),
            "steps": results,
            "evidence_state": EVIDENCE_STATE,
        }

    def get_timeline(self) -> list[dict]:
        return [
            {
                "name": step.name,
                "t_minus": step.t_minus,
                "required": step.required,
                "status": step.status.name,
            }
            for step in self.steps
        ]

    @property
    def event_log(self) -> list[tuple[float, str]]:
        return list(self._event_log)
