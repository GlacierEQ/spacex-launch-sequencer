# SpaceX Launch Sequencer

Automated countdown state machine and abort controller for Falcon 9 / Starship.

## Architecture

**Double Helix (Alpha + Omega)**

- **Alpha** (`src/alpha/countdown.py`): Countdown state machine — T-minus timeline, step dependencies, hold/resume/abort transitions.
- **Omega** (`src/omega/abort_controller.py`): Abort logic — sensor health monitoring, 3-tier abort (hold, hold-down release, in-flight escape), voting rules.

## Features

- State machine: IDLE → COUNTING → HOLDED → ABORTED → LIFTOFF
- Configurable steps with required/optional flags
- Auto-abort on sensor threshold breaches
- 3-tier abort system matching flight phases
- Event callbacks for telemetry integration
- Zero external dependencies

## Usage

```python
from src.alpha.countdown import LaunchSequencer, CountdownStep
from src.omega.abort_controller import create_f9_abort_controller

seq = LaunchSequencer()
seq.add_step(CountdownStep("fueling", t_minus=300, check=lambda: True))
seq.add_step(CountdownStep("ignition", t_minus=0, check=lambda: True))
seq.start()
seq.tick()

ac = create_f9_abort_controller()
ac.sample_all()
ac.evaluate()
```
