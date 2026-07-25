#!/usr/bin/env python3
"""Launch go/no-go sequencer — state machine with holds (portfolio)."""
from __future__ import annotations
from dataclasses import dataclass, field

STAGES = ["T-0_IDLE", "T-CHECKS", "T-FUEL", "T-ARM", "T-GO", "LIFTOFF"]

@dataclass
class Sequencer:
    stage: str = "T-0_IDLE"
    holds: list[str] = field(default_factory=list)

    def hold(self, reason: str) -> dict:
        if reason not in self.holds:
            self.holds.append(reason)
        return {"stage": self.stage, "holds": list(self.holds)}

    def clear(self, reason: str) -> dict:
        self.holds = [h for h in self.holds if h != reason]
        return {"stage": self.stage, "holds": list(self.holds)}

    def advance(self) -> dict:
        if self.holds:
            return {"ok": False, "error": "holds_active", "holds": list(self.holds)}
        i = STAGES.index(self.stage)
        if i >= len(STAGES) - 1:
            return {"ok": False, "error": "terminal", "stage": self.stage}
        self.stage = STAGES[i + 1]
        return {"ok": True, "stage": self.stage}

if __name__ == "__main__":
    s = Sequencer()
    print(s.advance())
    print(s.hold("weather"))
    print(s.advance())
    print(s.clear("weather"))
    print(s.advance())
