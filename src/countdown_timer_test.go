package countdown

import (
	"errors"
	"testing"
	"time"
)

func TestVotesReplaceBySubsystemAndRequireAllGo(t *testing.T) {
	ct := NewCountdownTimer(time.Now().Add(time.Minute))
	if ct.IsGoForLaunch() {
		t.Fatal("empty vote set must not be go")
	}
	ct.RecordVote("weather", VoteNoGo, "fixture")
	if ct.IsGoForLaunch() {
		t.Fatal("no-go must block")
	}
	ct.RecordVote("weather", VoteGo, "cleared")
	if !ct.IsGoForLaunch() {
		t.Fatal("replacement go vote should clear previous no-go")
	}
}

func TestHoldFreezesAndResumeShiftsTarget(t *testing.T) {
	ct := NewCountdownTimer(time.Now().Add(500 * time.Millisecond))
	ct.Hold("test")
	frozen := ct.TMinus()
	time.Sleep(20 * time.Millisecond)
	stillFrozen := ct.TMinus()
	if delta := stillFrozen - frozen; delta < -2*time.Millisecond || delta > 2*time.Millisecond {
		t.Fatalf("hold did not freeze countdown: delta=%s", delta)
	}
	ct.Resume()
	remaining := ct.TMinus()
	if remaining < frozen-20*time.Millisecond {
		t.Fatalf("resume failed to preserve held time: frozen=%s remaining=%s", frozen, remaining)
	}
}

func TestStatsDoesNotDeadlockAndCarriesEvidenceState(t *testing.T) {
	ct := NewCountdownTimer(time.Now().Add(time.Minute))
	ct.RecordVote("local", VoteGo, "fixture")
	done := make(chan map[string]interface{}, 1)
	go func() { done <- ct.Stats() }()
	select {
	case stats := <-done:
		if stats["evidence_state"] != EvidenceState {
			t.Fatalf("unexpected evidence state: %v", stats["evidence_state"])
		}
	case <-time.After(time.Second):
		t.Fatal("Stats deadlocked")
	}
}

func TestMilestoneHandlerMayReenterTimerWithoutDeadlock(t *testing.T) {
	ct := NewCountdownTimer(time.Now().Add(-time.Millisecond))
	ct.AddMilestone("reentrant", 0, true, func() error {
		_ = ct.Stats()
		ct.RecordVote("handler", VoteGo, "fixture")
		return nil
	})

	done := make(chan error, 1)
	go func() {
		_, err := ct.ExecuteNextMilestone()
		done <- err
	}()

	select {
	case err := <-done:
		if err != nil {
			t.Fatalf("unexpected handler error: %v", err)
		}
	case <-time.After(time.Second):
		t.Fatal("reentrant handler deadlocked")
	}
}

func TestCriticalFailureCanRetryAfterResume(t *testing.T) {
	ct := NewCountdownTimer(time.Now().Add(-time.Millisecond))
	attempts := 0
	ct.AddMilestone("retry", 0, true, func() error {
		attempts++
		if attempts == 1 {
			return errors.New("fixture failure")
		}
		return nil
	})

	milestone, err := ct.ExecuteNextMilestone()
	if err == nil || milestone.Status != StatusHold {
		t.Fatalf("first failure must hold: status=%v err=%v", milestone.Status, err)
	}
	ct.Resume()
	if milestone.Status != StatusPending {
		t.Fatalf("resume must re-arm held milestone: %v", milestone.Status)
	}
	milestone, err = ct.ExecuteNextMilestone()
	if err != nil || milestone.Status != StatusComplete {
		t.Fatalf("retry must complete: status=%v err=%v", milestone.Status, err)
	}
}

func TestOptionalFailureReturnsErrorAndSkippedStatus(t *testing.T) {
	ct := NewCountdownTimer(time.Now().Add(-time.Millisecond))
	ct.AddMilestone("optional", 0, false, func() error {
		return errors.New("fixture failure")
	})

	milestone, err := ct.ExecuteNextMilestone()
	if err == nil {
		t.Fatal("optional handler failure must be visible to caller")
	}
	if milestone.Status != StatusSkipped {
		t.Fatalf("optional failure must retain skipped status: %v", milestone.Status)
	}
}
