import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from sequencer import Sequencer, ANSWER

def test_hold_blocks():
    s = Sequencer()
    s.advance()
    s.hold("wx")
    r = s.advance()
    assert r["ok"] is False and r["answer"]==ANSWER

def test_advance_path():
    s = Sequencer()
    assert s.advance()["stage"]=="T-CHECKS"

if __name__=="__main__":
    test_hold_blocks(); test_advance_path(); print("ok")
