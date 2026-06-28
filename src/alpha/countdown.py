"""Launch countdown sequencer — state machine for automated countdown.

Manages T-minus timeline, step dependencies, and hold logic.
Each step has a callable check, timeout, and abort trigger.
Zero external dependencies.
"""

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Optional


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
        end = self.completed_at if self.completed_at > 0 else time.time()
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
        self.t0 = t0
        self.state = CountdownState.IDLE
        self.steps: list[CountdownStep] = []
        self.abort_conditions: list[AbortCondition] = []
        self._hold_start: float = 0.0
        self._hold_total: float = 0.0
        self._event_log: list[tuple[float, str]] = []
        self._callbacks: dict[str, list[Callable]] = {}

    def add_step(self, step: CountdownStep):
        self.steps.append(step)
        self.steps.sort(key=lambda s: s.t_minus, reverse=True)

    def add_abort_condition(self, condition: AbortCondition):
        self.abort_conditions.append(condition)

    def on(self, event: str, callback: Callable):
        self._callbacks.setdefault(event, []).append(callback)

    def _emit(self, event: str, data: dict):
        for cb in self._callbacks.get(event, []):
            cb(data)
        self._event_log.append((time.time(), f"{event}: {data}"))

    @property
    def t_minus(self) -> float:
        if self.t0 == 0:
            return 0.0
        return self.t0 - (time.time() - self._hold_total)

    def start(self):
        if self.state != CountdownState.IDLE:
            return False
        self.state = CountdownState.COUNTING
        self.t0 = time.time()
        self._hold_total = 0.0
        self._emit("countdown_started", {"t0": self.t0})
        return True

    def hold(self) -> bool:
        if self.state != CountdownState.COUNTING:
            return False
        self.state = CountdownState.HOLDED
        self._hold_start = time.time()
        self._emit("hold", {"t_minus": self.t_minus})
        return True

    def resume(self) -> bool:
        if self.state != CountdownState.HOLDED:
            return False
        self._hold_total += time.time() - self._hold_start
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
        for ac in self.abort_conditions:
            if not ac.triggered and ac.check():
                ac.triggered = True
                ac.trigger_time = time.time()
                return ac
        return None

    def tick(self) -> dict:
        if self.state != CountdownState.COUNTING:
            return {"state": self.state.name, "t_minus": self.t_minus}

        triggered = self._check_aborts()
        if triggered:
            self.abort(f"auto: {triggered.name} - {triggered.message}")
            return {"state": "ABORTED", "trigger": triggered.name}

        current_t = self.t_minus
        results = []

        for step in self.steps:
            if step.status != StepStatus.PENDING:
                continue
            if step.t_minus < current_t:
                continue

            step.status = StepStatus.RUNNING
            step.started_at = time.time()
            self._emit("step_started", {"step": step.name})

            try:
                passed = step.check()
            except Exception as e:
                passed = False
                step.error = str(e)

            if passed:
                step.status = StepStatus.PASSED
                step.completed_at = time.time()
                self._emit("step_passed", {"step": step.name})
            else:
                if step.required:
                    step.status = StepStatus.FAILED
                    self._emit("step_failed", {"step": step.name, "error": step.error})
                    if not self.abort(f"step failed: {step.name}"):
                        pass
                else:
                    step.status = StepStatus.SKIPPED
                    self._emit("step_skipped", {"step": step.name})

            results.append({"step": step.name, "status": step.status.name})

        all_done = all(
            s.status in (StepStatus.PASSED, StepStatus.SKIPPED)
            for s in self.steps if s.required
        )
        if all_done and current_t <= 0:
            self.state = CountdownState.LIFTOFF
            self._emit("liftoff", {"time": time.time()})

        return {
            "state": self.state.name,
            "t_minus": round(current_t, 3),
            "steps": results,
        }

    def get_timeline(self) -> list[dict]:
        return [
            {
                "name": s.name,
                "t_minus": s.t_minus,
                "required": s.required,
                "status": s.status.name,
            }
            for s in self.steps
        ]

    @property
    def event_log(self) -> list[tuple[float, str]]:
        return list(self._event_log)
