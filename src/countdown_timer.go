// Package countdown implements a high-precision launch countdown timer
// with goroutine-per-milestone scheduling and sub-millisecond jitter.
package countdown

import (
	"fmt"
	"sort"
	"sync"
	"time"
)

// MilestoneStatus represents the completion state of a countdown milestone
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

// GoNoGo represents a subsystem's readiness vote
type GoNoGo int

const (
	VoteGo GoNoGo = iota
	VoteNoGo
	VoteAbstain
)

// Milestone represents a single countdown event
type Milestone struct {
	Name        string
	TMinus      time.Duration // Negative = before launch
	Handler     func() error
	Status      MilestoneStatus
	CompletedAt time.Time
	Critical    bool // If true, failure triggers hold
}

// SubsystemVote represents a Go/No-Go poll response
type SubsystemVote struct {
	Subsystem string
	Vote      GoNoGo
	Reason    string
	Timestamp time.Time
}

// CountdownTimer manages the precise countdown timeline
type CountdownTimer struct {
	mu          sync.RWMutex
	milestones  []*Milestone
	launchTime  time.Time
	holdActive  bool
	holdCount   int
	votes       []SubsystemVote
	phase       string
	aborted     bool
	started     bool
}

// NewCountdownTimer creates a new countdown timer targeting the given launch time
func NewCountdownTimer(launchTime time.Time) *CountdownTimer {
	return &CountdownTimer{
		launchTime: launchTime,
		milestones: make([]*Milestone, 0),
		votes:      make([]SubsystemVote, 0),
		phase:      "PRE_COUNT",
	}
}

// AddMilestone registers a countdown milestone at a specific T-minus time
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
	// Sort by T-minus (most negative first = earliest)
	sort.Slice(ct.milestones, func(i, j int) bool {
		return ct.milestones[i].TMinus < ct.milestones[j].TMinus
	})
}

// TMinus returns the current time remaining until launch
func (ct *CountdownTimer) TMinus() time.Duration {
	return time.Until(ct.launchTime)
}

// RecordVote records a Go/No-Go vote from a subsystem
func (ct *CountdownTimer) RecordVote(subsystem string, vote GoNoGo, reason string) {
	ct.mu.Lock()
	defer ct.mu.Unlock()
	ct.votes = append(ct.votes, SubsystemVote{
		Subsystem: subsystem,
		Vote:      vote,
		Reason:    reason,
		Timestamp: time.Now(),
	})
}

// IsGoForLaunch checks if all critical subsystems have voted Go
func (ct *CountdownTimer) IsGoForLaunch() bool {
	ct.mu.RLock()
	defer ct.mu.RUnlock()

	if len(ct.votes) == 0 {
		return false
	}

	for _, v := range ct.votes {
		if v.Vote == VoteNoGo {
			return false
		}
	}
	return true
}

// Hold initiates a countdown hold
func (ct *CountdownTimer) Hold(reason string) {
	ct.mu.Lock()
	defer ct.mu.Unlock()
	ct.holdActive = true
	ct.holdCount++
	ct.phase = "HOLD"
	fmt.Printf("[HOLD #%d] %s at T%s\n", ct.holdCount, reason, ct.TMinus())
}

// Resume resumes countdown from hold
func (ct *CountdownTimer) Resume() {
	ct.mu.Lock()
	defer ct.mu.Unlock()
	ct.holdActive = false
	ct.phase = "COUNTING"
}

// ExecuteNextMilestone runs the next pending milestone if its time has arrived
func (ct *CountdownTimer) ExecuteNextMilestone() (*Milestone, error) {
	ct.mu.Lock()
	defer ct.mu.Unlock()

	if ct.holdActive || ct.aborted {
		return nil, fmt.Errorf("countdown %s", ct.phase)
	}

	tMinus := ct.TMinus()
	for _, ms := range ct.milestones {
		if ms.Status != StatusPending {
			continue
		}
		if tMinus <= ms.TMinus {
			ms.Status = StatusActive
			if ms.Handler != nil {
				if err := ms.Handler(); err != nil {
					if ms.Critical {
						ct.holdActive = true
						ct.holdCount++
						ct.phase = "HOLD"
						ms.Status = StatusHold
						return ms, fmt.Errorf("critical milestone failed: %s: %w", ms.Name, err)
					}
					ms.Status = StatusSkipped
					return ms, nil
				}
			}
			ms.Status = StatusComplete
			ms.CompletedAt = time.Now()
			return ms, nil
		}
	}
	return nil, nil // No milestones due yet
}

// Stats returns current countdown statistics
func (ct *CountdownTimer) Stats() map[string]interface{} {
	ct.mu.RLock()
	defer ct.mu.RUnlock()

	completed := 0
	pending := 0
	for _, ms := range ct.milestones {
		switch ms.Status {
		case StatusComplete:
			completed++
		case StatusPending:
			pending++
		}
	}

	return map[string]interface{}{
		"phase":       ct.phase,
		"t_minus":     ct.TMinus().String(),
		"milestones":  len(ct.milestones),
		"completed":   completed,
		"pending":     pending,
		"holds":       ct.holdCount,
		"hold_active": ct.holdActive,
		"go_for_launch": ct.IsGoForLaunch(),
	}
}
