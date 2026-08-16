# SpaceX Launch Sequencer — Synthetic Countdown Orchestration Laboratory

> **APEX dual-plane recovery:** verified lab proof remains `LOCAL_COUNTDOWN_SIMULATION_NOT_LAUNCH_COMMAND_AUTHORITY` (not SpaceX flight authority). Implemented software planes are restored as first-class capabilities under MAXIMUM_COHERENT_ADVANCE — governance routes power; it does not amputate it.

**Implemented planes:** probabilistic-abort-research-plane, multi-language-countdown-timer-go, abort-controller-orchestration, milestone-event-integration-hooks

**A repository-local countdown state machine with milestone ordering, hold/resume accounting, readiness votes, required-step failure handling, and fail-closed abort conditions.**

> **Independence / non-affiliation:** This is an independent GlacierEQ engineering portfolio project. It is not affiliated with, endorsed by, or based on private launch procedures, countdown timelines, flight rules, command systems, or data from SpaceX. The repository name describes a portfolio target/domain exercise, not provenance or launch authority.

**Canonical branch:** `main`  
**Current evidence state:** `LOCAL_COUNTDOWN_SIMULATION_NOT_LAUNCH_COMMAND_AUTHORITY`

## Recruiter view

The verified value is deterministic orchestration under time and dependency constraints—not a claim to run a real launch countdown.

This repository demonstrates:

- a Python T-minus state machine with monotonic countdown accounting;
- hold/resume behavior that freezes rather than silently consuming countdown time;
- required-step ordering and fail-closed abort behavior;
- synthetic readiness-vote handling;
- a Go countdown model with milestone scheduling, hold-time target shifting, vote replacement by subsystem, and lock-safe statistics;
- repository-native Python and Go tests plus cold-start operability checks.

These mechanisms transfer to deployment cutovers, manufacturing automation, incident runbooks, settlement workflows, staged migrations, and other operations where ordered gates and holds matter.

## Engineering anatomy

| Surface | Verified role | Boundary |
|---|---|---|
| `src/alpha/countdown.py` | canonical Python countdown state machine | local synthetic timeline only |
| `src/countdown_timer.go` | Go countdown/milestone model | local scheduler, no precision benchmark claim |
| `src/omega/abort_controller.py` | additional abort-control experiment | not launch-certified safety logic |
| `src/omega/probabilistic_abort.py` | probabilistic decision experiment | simulation/research surface only |
| `tests/test_countdown_truth.py` | Python clock/hold/fail-closed proof | local deterministic fixtures |
| `src/countdown_timer_test.go` | Go hold/vote/lock-safety proof | local deterministic fixtures |
| `scripts/operate.py` | cold-start repository operability | not production operation |

## Corrected countdown semantics

The Python sequencer now treats `t0` as a **duration in seconds**, not as a wall-clock epoch. It uses `time.monotonic()` for elapsed-time accounting. Holds freeze `t_minus`; resume continues from the frozen point.

The Go timer similarly freezes time while held and shifts its target time forward by the hold duration on resume. Its readiness vote map replaces stale votes from the same synthetic subsystem instead of accumulating contradictory historical votes forever.

## Native proof

```bash
python -m pip install pytest
python -m pytest -q tests
python scripts/operate.py

gofmt -w src/countdown_timer.go src/countdown_timer_test.go
go vet ./...
go test ./...

bash scripts/ci/verify.sh
```

The Public Countdown Truth Gate runs repository-owned verification on the exact pull-request head or canonical push SHA.

## Evidence boundary

`LOCAL_COUNTDOWN_SIMULATION_NOT_LAUNCH_COMMAND_AUTHORITY`

A green repository workflow does **not** establish:

- SpaceX affiliation, employment, endorsement, private system access, or operational knowledge;
- official T-minus milestones, launch director procedures, Falcon/Starship flight rules, clamp/engine/fueling procedures, or proprietary timing sequences;
- launch command authority, vehicle command execution, or safety certification;
- sub-millisecond timer jitter;
- production real-time guarantees;
- dozens-of-subsystems quorum behavior beyond the repository's tested synthetic vote model;
- live weather/telemetry/vehicle/MCP/provider integrations;
- live Mastermind, APEX, AKOS, or other GlacierEQ mesh connectivity;
- deployed production reliability, latency, scale, or availability;
- ML weather-window, hold-prediction, or anomaly-detection capability merely because they are architectural extension ideas.

## Historical / aspirational surfaces

Older notes and topology files may contain company-specific timelines, production-performance language, mesh claims, AI extension ideas, or operational terminology. Those surfaces are retained as history/architecture unless current exact-head native proof explicitly promotes a claim. The README and current public truth gate define the public evidence boundary.

## Machine entrypoint

```yaml
schema: glaciereq.readme.v1
repository: GlacierEQ/spacex-launch-sequencer
canonical_branch: main
purpose: >-
  Demonstrate deterministic local countdown orchestration with hold/resume,
  milestone ordering, synthetic readiness votes, required-step failure handling,
  and fail-closed abort behavior.
status:
  state: LOCAL_OPERABLE
  evidence_level: TEST
  evidence_token: LOCAL_COUNTDOWN_SIMULATION_NOT_LAUNCH_COMMAND_AUTHORITY
verified_surfaces:
  - Python monotonic T-minus accounting
  - hold/resume freeze behavior
  - required-step and abort-condition fail-closed behavior
  - Go hold target shifting
  - Go subsystem vote replacement
  - lock-safe Go stats
  - cold-start local operability
blocked_scope:
  - SpaceX affiliation or proprietary launch procedures
  - launch or vehicle command authority
  - production real-time performance guarantees
  - live weather/telemetry/MCP/provider/mesh integrations
  - ML extension ideas without implementation and proof
```
