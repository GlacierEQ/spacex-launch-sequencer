"""Evidence-bound mission sequencing model with holds, recycle, and receipts.

Portfolio-only control logic. It evaluates synthetic readiness evidence and does
not command launch hardware, vehicles, propellant systems, range assets, or
external services.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from math import isfinite
from typing import Iterable

EVIDENCE_STATE = "DETERMINISTIC_PORTFOLIO_MISSION_SEQUENCE_MODEL"


class GateState(str, Enum):
    GO = "GO"
    HOLD = "HOLD"
    UNKNOWN = "UNKNOWN"


class SequenceAction(str, Enum):
    ADVANCE = "ADVANCE"
    HOLD = "HOLD"
    RECYCLE = "RECYCLE"
    COMPLETE = "COMPLETE"


STAGES = (
    "IDLE",
    "READINESS_REVIEW",
    "COMMIT_REVIEW",
    "FINAL_READY",
    "COMPLETE",
)

REQUIRED_GATES = {
    "IDLE": (),
    "READINESS_REVIEW": ("vehicle", "ground", "weather"),
    "COMMIT_REVIEW": ("vehicle", "ground", "weather", "range"),
    "FINAL_READY": ("vehicle", "ground", "weather", "range", "mission"),
    "COMPLETE": (),
}


@dataclass(frozen=True)
class GateObservation:
    gate: str
    state: GateState
    observed_at: float
    source: str
    evidence_digest: str

    def __post_init__(self) -> None:
        if not self.gate.strip() or not self.source.strip():
            raise ValueError("gate and source must be non-empty")
        if not isfinite(self.observed_at) or self.observed_at < 0:
            raise ValueError("observed_at must be finite and non-negative")
        if len(self.evidence_digest) != 64 or any(
            c not in "0123456789abcdef" for c in self.evidence_digest.lower()
        ):
            raise ValueError("evidence_digest must be a SHA-256 hex digest")


@dataclass(frozen=True)
class SequenceDecision:
    stage_before: str
    stage_after: str
    action: SequenceAction
    active_holds: tuple[str, ...]
    missing_gates: tuple[str, ...]
    stale_gates: tuple[str, ...]
    evidence_fingerprint: str
    evidence_state: str = EVIDENCE_STATE

    def as_dict(self) -> dict[str, object]:
        row = asdict(self)
        row["action"] = self.action.value
        return row

    @property
    def fingerprint(self) -> str:
        encoded = json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode()).hexdigest()


class MissionSequenceController:
    """Advance only when required evidence is present, fresh, and unanimous GO."""

    def __init__(self, *, max_evidence_age: float = 120.0) -> None:
        if not isfinite(max_evidence_age) or max_evidence_age <= 0:
            raise ValueError("max_evidence_age must be finite and positive")
        self.max_evidence_age = float(max_evidence_age)
        self.stage = "IDLE"
        self._manual_holds: set[str] = set()
        self._history: list[str] = []

    @staticmethod
    def _evidence_fingerprint(observations: tuple[GateObservation, ...]) -> str:
        rows = [
            {
                "gate": row.gate,
                "state": row.state.value,
                "observed_at": row.observed_at,
                "source": row.source,
                "evidence_digest": row.evidence_digest,
            }
            for row in sorted(observations, key=lambda item: (item.gate, item.source))
        ]
        return hashlib.sha256(
            json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    def add_hold(self, reason: str) -> None:
        normalized = reason.strip()
        if not normalized:
            raise ValueError("hold reason must be non-empty")
        self._manual_holds.add(normalized)

    def clear_hold(self, reason: str) -> None:
        self._manual_holds.discard(reason.strip())

    def recycle(self, target_stage: str = "READINESS_REVIEW") -> SequenceDecision:
        if target_stage not in STAGES[:-1]:
            raise ValueError("recycle target must be a non-terminal stage")
        before = self.stage
        if STAGES.index(target_stage) > STAGES.index(before):
            raise ValueError("recycle cannot advance the sequence")
        self.stage = target_stage
        self._history.append(self.stage)
        return SequenceDecision(
            stage_before=before,
            stage_after=self.stage,
            action=SequenceAction.RECYCLE,
            active_holds=tuple(sorted(self._manual_holds)),
            missing_gates=(),
            stale_gates=(),
            evidence_fingerprint=hashlib.sha256(b"recycle").hexdigest(),
        )

    def evaluate(
        self,
        observations: Iterable[GateObservation],
        *,
        now: float,
    ) -> SequenceDecision:
        if not isfinite(now) or now < 0:
            raise ValueError("now must be finite and non-negative")
        rows = tuple(observations)
        fingerprint = self._evidence_fingerprint(rows)
        if self.stage == "COMPLETE":
            return SequenceDecision(
                stage_before=self.stage,
                stage_after=self.stage,
                action=SequenceAction.COMPLETE,
                active_holds=tuple(sorted(self._manual_holds)),
                missing_gates=(),
                stale_gates=(),
                evidence_fingerprint=fingerprint,
            )

        next_stage = STAGES[STAGES.index(self.stage) + 1]
        required = set(REQUIRED_GATES[next_stage])
        by_gate: dict[str, list[GateObservation]] = {}
        for row in rows:
            by_gate.setdefault(row.gate, []).append(row)

        missing = sorted(gate for gate in required if gate not in by_gate)
        stale: set[str] = set()
        evidence_holds: set[str] = set()
        for gate in required:
            gate_rows = by_gate.get(gate, [])
            for row in gate_rows:
                if now - row.observed_at > self.max_evidence_age:
                    stale.add(gate)
                if row.state is not GateState.GO:
                    evidence_holds.add(f"{gate}:{row.state.value}")
            if gate_rows and len({row.state for row in gate_rows}) > 1:
                evidence_holds.add(f"{gate}:DISAGREEMENT")

        all_holds = set(self._manual_holds) | evidence_holds
        if missing:
            all_holds.update(f"{gate}:MISSING" for gate in missing)
        if stale:
            all_holds.update(f"{gate}:STALE" for gate in stale)

        before = self.stage
        if all_holds:
            action = SequenceAction.HOLD
            after = before
        else:
            self.stage = next_stage
            self._history.append(self.stage)
            action = (
                SequenceAction.COMPLETE
                if self.stage == "COMPLETE"
                else SequenceAction.ADVANCE
            )
            after = self.stage

        return SequenceDecision(
            stage_before=before,
            stage_after=after,
            action=action,
            active_holds=tuple(sorted(all_holds)),
            missing_gates=tuple(missing),
            stale_gates=tuple(sorted(stale)),
            evidence_fingerprint=fingerprint,
        )
