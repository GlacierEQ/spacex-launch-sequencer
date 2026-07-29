# SpaceX Launch Sequencer — Automated Countdown & Hold Management 🚀

> **Deterministic state-machine countdown sequencer with automated hold/recycle and Go/No-Go polling.**

[![Python](https://img.shields.io/badge/Python-3.9+-blue)]()
[![Go](https://img.shields.io/badge/Go-1.21+-00ADD8)]()
[![Domain](https://img.shields.io/badge/Domain-Launch%20Operations-red)]()

---

## 🎯 For Recruiters & Hiring Managers

This repository implements an **automated launch countdown sequencer** — the orchestration software that manages the precise timeline of events from T-45:00 through liftoff. It demonstrates:

- **Deterministic state machines** with strict temporal ordering guarantees
- **Automated Go/No-Go polling** across dozens of subsystems with consensus logic
- **Hold and recycle management** with configurable recycle windows and abort criteria
- **Event-driven architecture** with sub-second timing precision for critical milestones

**Why this matters**: Launch sequencing is a masterclass in **orchestration under constraints** — the same discipline used in manufacturing automation, surgical robotics, and financial settlement systems where timing, ordering, and consensus are non-negotiable.

---

## 🔬 For Engineers & Technical Reviewers

### Countdown Timeline

```
T-45:00  Prop systems pressurization begins
T-35:00  LOX loading begins
T-16:00  RP-1/CH4 loading begins
T-07:00  Engine chill sequence
T-05:00  SpaceX Launch Director poll
T-01:00  Flight computer to startup config
T-00:45  SpaceX Launch Director final Go
T-00:03  Engine ignition sequence
T-00:00  LIFTOFF — clamp release
```

### Core Components

| Component | Language | Purpose |
|---|---|---|
| `src/sequencer_engine.py` | Python | Countdown FSM, milestone management, Go/No-Go logic |
| `src/countdown_timer.go` | Go | High-precision timer with goroutine-per-milestone scheduling |
| `tests/` | Python | Deterministic countdown simulation with hold/recycle scenarios |

### Key Design

- **Go for timing**: `time.NewTicker` with goroutine scheduling achieves <1ms jitter
- **Consensus polling**: Quorum-based Go/No-Go with configurable veto authority
- **Idempotent transitions**: Every state change is logged and replayable

---

## 🤖 ML/AI & Programmatic Mesh Integration

### Agent Mesh Connectivity

- **MCP Tool**: `countdown_status()` — real-time countdown state for orchestrator agents
- **Mastermind Sidecar**: Publishes milestone events to APEX Highway mesh
- **SHA-256 Integrity**: `.integrity/file_hashes.json` cryptographic verification

### AI/ML Extension Points

- **Weather Window Optimization**: ML model predicts optimal launch windows from forecast ensembles
- **Hold Prediction**: Classification model predicts hold probability from pre-launch telemetry
- **Anomaly Detection**: Unsupervised clustering on countdown telemetry for early fault detection

```python
# Agent mesh query
status = await mcp_client.call_tool("launch-sequencer", "countdown_status")
# Returns: {"t_minus_s": 120, "phase": "TERMINAL_COUNT", "holds": 0, "go_nogo": "GO"}
```

---

## ⚡ Quick Start

```bash
python3 src/sequencer_engine.py
python3 tests/test_sequencer.py
```
