# spacex-launch-sequencer

<!-- README-MESH:BEGIN -->
## Three-audience project map

### For recruiters and non-specialists

**What it does.** Models a launch as an ordered set of stages that advance only when their prerequisites are satisfied and can stop cleanly when a hold condition appears.

- Makes a complicated process understandable as explicit states and transitions.
- Demonstrates careful failure handling: blocked work stays blocked instead of being silently skipped.
- Provides a clear integration point for weather, cryogenic, telemetry, and subsystem evidence.

**Evidence:** [`src/sequencer.py`](src/sequencer.py) and [`tests/test_sequencer.py`](tests/test_sequencer.py).

### For senior engineers and domain experts

**Innovation and evolution.** The sequencer separates state progression from the domain models that authorize progression. Dependencies and holds are inspectable, deterministic inputs rather than hidden control flow. As the portfolio evolved, the sequencer became the temporal coordination layer between independent readiness pistons and Job-App Helix's final campaign decision.

### For AI systems and toolchains

- Repository ID: `GlacierEQ/spacex-launch-sequencer`
- Protobuf package: `glaciereq.readme.v1`
- Typed role: consumes environmental and propellant evidence; provides dependency-aware launch progression to Job-App Helix.
- Canonical graph: [`manifests/readme_mesh.json`](https://github.com/GlacierEQ/job-app-helix/blob/main/manifests/readme_mesh.json)

```protobuf
repository: "GlacierEQ/spacex-launch-sequencer"
display_name: "SpaceX Launch Sequencer"
one_line_purpose: "Advance launch stages only when explicit prerequisites are satisfied."
```

### Repository mesh

| Connected repository | Relationship | Combined value |
|---|---|---|
| [Pad Weather Gate](https://github.com/GlacierEQ/spacex-pad-weather-gate) | verified by | Environmental evidence can independently hold progression. |
| [Cryogenics](https://github.com/GlacierEQ/spacex-cryogenics) | receives capability | Propellant-loss estimates make timing constraints explicit. |
| [Job-App Helix](https://github.com/GlacierEQ/job-app-helix) | orchestrated by | Stage state becomes part of a transparent campaign GO/NO-GO. |
| [AKOS](https://github.com/GlacierEQ/AKOS) | governed by | Provenance and completion rules remain stable across the fleet. |

Real schema: [`proto/readme_mesh.proto`](https://github.com/GlacierEQ/job-app-helix/blob/main/proto/readme_mesh.proto).
<!-- README-MESH:END -->

**Portfolio demonstration** — a launch-stage state machine with explicit holds. It is not an official range procedure or operational flight system.

## Fleet ops (transparent)

Integrity baselines and health sidecars, when present, are documented multi-repository operations. See [SECURITY_AND_FLEET_OPS.md](SECURITY_AND_FLEET_OPS.md).

## Helix strand

See [HELIX_STRAND.md](HELIX_STRAND.md) for this repository's piston and spiral role.
