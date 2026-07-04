# HELIX Architecture — spacex-launch-sequencer

## Double Helix Pattern

**Alpha (What)** — Pure physics models, stateless computation
- countdown

**Omega (How)** — Controllers, orchestration, stateful management  
- abort_controller,probabilistic_abort

## Design Principles

- Zero external dependencies (stdlib only)
- Stateless alpha, stateful omega
- SHA-256 file integrity verification
- Shadow watchdog daemon monitoring
- Mastermind sidecar coordination

## Data Flow

```
Alpha Models → Omega Controllers → Mastermind Sidecar → Shadow Infrastructure
```
