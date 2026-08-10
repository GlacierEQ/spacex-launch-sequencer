"""Tests drive shipped sequencer.Sequencer — no magic ANSWER constants."""
from __future__ import annotations

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from sequencer import Sequencer  # noqa: E402


class SequencerTests(unittest.TestCase):
    def test_advance_path_from_idle(self) -> None:
        s = Sequencer()
        r = s.advance()
        self.assertTrue(r["ok"])
        self.assertEqual(r["stage"], "T-CHECKS")

    def test_hold_blocks_advance(self) -> None:
        s = Sequencer()
        s.advance()
        s.hold("wx")
        r = s.advance()
        self.assertFalse(r["ok"])
        self.assertEqual(r.get("error"), "holds_active")
        self.assertIn("wx", r.get("holds", []))


if __name__ == "__main__":
    unittest.main()
