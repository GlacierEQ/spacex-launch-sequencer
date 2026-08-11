// Package countdown implements a repository-local countdown scheduling model.
// It is a simulation/reference surface, not a SpaceX launch procedure or
// production timing/command system.
package countdown

import (
	"fmt"
	"sort"
	"sync"
	"time"
)

const EvidenceState = "LOCAL_COUNTDOWN_SIMULATION_NOT_LAUNCH_COMMAND_AUTHORITY"

// MilestoneStatus represents the completion state of a countdown milestone.
type MilestoneStatus int

const (
	StatusPending MilestoneStatus = iota
	StatusActive
	StatusComplete
	StatusHold
	StatusSkipped
)

func (s MilestoneStatus) String() string {
	return []string{"PENDING", "ACTIVE", "COMPLETE", "HOLD", "SKIPPED"}[s]
}

// GoNoGo represents a synthetic subsystem readiness vote.
type GoNoGo int

const (
	VoteGo GoNoGo = iota
	VoteNoGo
	VoteAbstain
)

// Milestone represents one repository-local countdown event.
type Milestone struct {
	Name        string
	TMinus      time.Duration
	Handler     func() error
	Status      MilestoneStatus
	CompletedAt time.Time
	Critical    bool
}

// SubsystemVote represents one synthetic readiness vote.
type SubsystemVote struct {
	Subsystem string
	Vote      GoNoGo
	Reason    string
	Timestamp time.Time
}

// CountdownTimer manages a local countdown timeline.
type CountdownTimer struct {
	mu          sync.RWMutex
	milestones  []*Milestone
	launchTime  time.Time
	holdActive  bool
	holdStarted time.Time
	holdCount   int
	votes       map[string]SubsystemVote
	phase       string
	aborted     bool
}

// NewCountdownTimer creates a local countdown timer targeting launchTime.
func NewCountdownTimer(launchTime time.Time) *CountdownTimer {
	return &CountdownTimer{
		launchTime: launchTime,
		milestones: make([]*Milestone, 0),
		votes:      make(map[string]SubsystemVote),
		phase:      "PRE_COUNT",
	}
}

// AddMilestone registers a milestone at a specific relative time.
func (ct *CountdownTimer) AddMilestone(name string, tMinus time.Duration, critical bool, handler func() error) {
	ct.mu.Lock()
	defer ct.mu.Unlock()
	ct.milestones = append(ct.milestones, &Milestone{
		Name:     name,
		TMinus:   tMinus,
		Handler:  handler,
		Status:   StatusPending,
		Critical: critical,
	})
	sort.Slice(ct.milestones, func(i, j int) bool {
		return ct.milestones[i].TMinus < ct.milestones[j].TMinus
	})
}

// TMinus returns wall-clock duration remaining until the local target time.
func (ct *CountdownTimer) TMinus() time.Duration {
	ct.mu.RLock()
	defer ct.mu.RUnlock()
	return ct.tMinusLocked()
}

func (ct *CountdownTimer) tMinusLocked() time.Duration {
	now := time.Now()
	if ct.holdActive && !ct.holdStarted.IsZero() {
		now = ct.holdStarted
	}
	return ct.launchTime.Sub(now)
}

// RecordVote records or replaces a synthetic readiness vote for one subsystem.
func (ct *CountdownTimer) RecordVote(subsystem string, vote GoNoGo, reason string) {
	ct.mu.Lock()
	defer ct.mu.Unlock()
	ct.votes[subsystem] = SubsystemVote{
		Subsystem: subsystem,
		Vote:      vote,
		Reason:    reason,
		Timestamp: time.Now(),
	}
}

func (ct *CountdownTimer) isGoForLaunchLocked() bool {
	if len(ct.votes) == 0 {
		return false
	}
	for _, vote := range ct.votes {
		if vote.Vote != VoteGo {
			return false
		}
	}
	return true
}

// IsGoForLaunch returns true only when at least one vote exists and every
// currently recorded synthetic subsystem vote is Go.
func (ct *CountdownTimer) IsGoForLaunch() bool {
	ct.mu.RLock()
	defer ct.mu.RUnlock()
	return ct.isGoForLaunchLocked()
}

// Hold freezes the local countdown until Resume is called.
func (ct *CountdownTimer) Hold(reason string) {
	ct.mu.Lock()
	defer ct.mu.Unlock()
	if ct.holdActive {
		return
	}
	ct.holdActive = true
	ct.holdStarted = time.Now()
	ct.holdCount++
	ct.phase = "HOLD"
	fmt.Printf("[HOLD #%d] %s at T%s\n", ct.holdCount, reason, ct.tMinusLocked())
}

// Resume shifts the target time by the duration spent on hold.
func (ct *CountdownTimer) Resume() {
	ct.mu.Lock()
	defer ct.mu.Unlock()
	if !ct.holdActive {
		return
	}
	heldFor := time.Since(ct.holdStarted)
	ct.launchTime = ct.launchTime.Add(heldFor)
	ct.holdStarted = time.Time{}
	ct.holdActive = false
	ct.phase = "COUNTING"
}

// ExecuteNextMilestone runs the next pending due milestone.
func (ct *CountdownTimer) ExecuteNextMilestone() (*Milestone, error) {
	ct.mu.Lock()
	defer ct.mu.Unlock()

	if ct.holdActive || ct.aborted {
		return nil, fmt.Errorf("countdown %s", ct.phase)
	}

	tMinus := ct.tMinusLocked()
	for _, milestone := range ct.milestones {
		if milestone.Status != StatusPending || tMinus > milestone.TMinus {
			continue
		}
		milestone.Status = StatusActive
		if milestone.Handler != nil {
			if err := milestone.Handler(); err != nil {
				if milestone.Critical {
					ct.holdActive = true
					ct.holdStarted = time.Now()
					ct.holdCount++
					ct.phase = "HOLD"
					milestone.Status = StatusHold
					return milestone, fmt.Errorf("critical milestone failed: %s", milestone.Name)
				}
				milestone.Status = StatusSkipped
				return milestone, nil
			}
		}
		milestone.Status = StatusComplete
		milestone.CompletedAt = time.Now()
		return milestone, nil
	}
	return nil, nil
}

// Stats returns current local countdown state without benchmark claims.
func (ct *CountdownTimer) Stats() map[string]interface{} {
	ct.mu.RLock()
	defer ct.mu.RUnlock()

	completed := 0
	pending := 0
	for _, milestone := range ct.milestones {
		switch milestone.Status {
		case StatusComplete:
			completed++
		case StatusPending:
			pending++
		}
	}

	return map[string]interface{}{
		"phase":          ct.phase,
		"t_minus":        ct.tMinusLocked().String(),
		"milestones":     len(ct.milestones),
		"completed":      completed,
		"pending":        pending,
		"holds":          ct.holdCount,
		"hold_active":    ct.holdActive,
		"go_for_launch":  ct.isGoForLaunchLocked(),
		"evidence_state": EvidenceState,
	}
}
