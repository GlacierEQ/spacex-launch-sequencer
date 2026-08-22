import hashlib
import unittest

from src.mission_sequence_controller import (
    GateObservation,
    GateState,
    MissionSequenceController,
    SequenceAction,
)


def digest(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def gate(name: str, *, state=GateState.GO, observed_at=100.0, source="sim"):
    return GateObservation(name, state, observed_at, source, digest(f"{name}:{source}"))


class MissionSequenceControllerTests(unittest.TestCase):
    def test_readiness_advances_only_with_required_fresh_go_evidence(self):
        controller = MissionSequenceController(max_evidence_age=30)
        first = controller.evaluate([], now=100)
        self.assertEqual(first.action, SequenceAction.ADVANCE)
        self.assertEqual(first.stage_after, "READINESS_REVIEW")
        second = controller.evaluate(
            [gate("vehicle"), gate("ground"), gate("weather")], now=110
        )
        self.assertEqual(second.action, SequenceAction.ADVANCE)
        self.assertEqual(second.stage_after, "COMMIT_REVIEW")

    def test_missing_gate_holds_fail_closed(self):
        controller = MissionSequenceController()
        controller.evaluate([], now=1)
        decision = controller.evaluate([gate("vehicle"), gate("ground")], now=100)
        self.assertEqual(decision.action, SequenceAction.HOLD)
        self.assertEqual(decision.stage_after, "READINESS_REVIEW")
        self.assertIn("weather", decision.missing_gates)
        self.assertIn("weather:MISSING", decision.active_holds)

    def test_stale_evidence_holds(self):
        controller = MissionSequenceController(max_evidence_age=10)
        controller.evaluate([], now=1)
        decision = controller.evaluate(
            [gate("vehicle", observed_at=1), gate("ground", observed_at=100), gate("weather", observed_at=100)],
            now=100,
        )
        self.assertEqual(decision.action, SequenceAction.HOLD)
        self.assertIn("vehicle", decision.stale_gates)

    def test_disagreement_holds_even_if_one_source_says_go(self):
        controller = MissionSequenceController()
        controller.evaluate([], now=1)
        rows = [
            gate("vehicle", source="a"),
            gate("vehicle", state=GateState.HOLD, source="b"),
            gate("ground"),
            gate("weather"),
        ]
        decision = controller.evaluate(rows, now=100)
        self.assertEqual(decision.action, SequenceAction.HOLD)
        self.assertIn("vehicle:DISAGREEMENT", decision.active_holds)
        self.assertIn("vehicle:HOLD", decision.active_holds)

    def test_manual_hold_survives_good_evidence_until_explicit_clear(self):
        controller = MissionSequenceController()
        controller.evaluate([], now=1)
        controller.add_hold("operator-review")
        rows = [gate("vehicle"), gate("ground"), gate("weather")]
        held = controller.evaluate(rows, now=100)
        self.assertEqual(held.action, SequenceAction.HOLD)
        controller.clear_hold("operator-review")
        advanced = controller.evaluate(rows, now=100)
        self.assertEqual(advanced.action, SequenceAction.ADVANCE)

    def test_recycle_cannot_silently_advance(self):
        controller = MissionSequenceController()
        controller.evaluate([], now=1)
        controller.evaluate(
            [gate("vehicle"), gate("ground"), gate("weather")], now=100
        )
        recycled = controller.recycle("READINESS_REVIEW")
        self.assertEqual(recycled.action, SequenceAction.RECYCLE)
        self.assertEqual(recycled.stage_after, "READINESS_REVIEW")
        with self.assertRaises(ValueError):
            controller.recycle("FINAL_READY")

    def test_sequence_completes_only_after_each_required_review(self):
        controller = MissionSequenceController()
        self.assertEqual(controller.evaluate([], now=1).stage_after, "READINESS_REVIEW")
        self.assertEqual(
            controller.evaluate(
                [gate("vehicle"), gate("ground"), gate("weather")], now=100
            ).stage_after,
            "COMMIT_REVIEW",
        )
        self.assertEqual(
            controller.evaluate(
                [gate("vehicle"), gate("ground"), gate("weather"), gate("range")],
                now=100,
            ).stage_after,
            "FINAL_READY",
        )
        complete = controller.evaluate(
            [
                gate("vehicle"),
                gate("ground"),
                gate("weather"),
                gate("range"),
                gate("mission"),
            ],
            now=100,
        )
        self.assertEqual(complete.action, SequenceAction.COMPLETE)
        self.assertEqual(complete.stage_after, "COMPLETE")
        terminal = controller.evaluate([], now=101)
        self.assertEqual(terminal.action, SequenceAction.COMPLETE)

    def test_decision_receipt_fingerprint_is_deterministic(self):
        controller = MissionSequenceController()
        decision = controller.evaluate([], now=1)
        self.assertEqual(len(decision.fingerprint), 64)
        self.assertEqual(decision.fingerprint, decision.fingerprint)
        self.assertEqual(
            decision.evidence_state,
            "DETERMINISTIC_PORTFOLIO_MISSION_SEQUENCE_MODEL",
        )


if __name__ == "__main__":
    unittest.main()
