package countdown

import (
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
