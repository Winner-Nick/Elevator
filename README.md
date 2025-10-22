# Elevator Saga

<div align="center">

[![PyPI version](https://badge.fury.io/py/elevator-py.svg)](https://badge.fury.io/py/elevator-py)
[![Python versions](https://img.shields.io/pypi/pyversions/elevator-py.svg)](https://pypi.org/project/elevator-py/)
[![Build Status](https://github.com/ZGCA-Forge/Elevator/actions/workflows/ci.yml/badge.svg)](https://github.com/ZGCA-Forge/Elevator/actions)
[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-brightgreen)](https://zgca-forge.github.io/Elevator/)

[![GitHub stars](https://img.shields.io/github/stars/ZGCA-Forge/Elevator.svg?style=social&label=Star)](https://github.com/ZGCA-Forge/Elevator)
[![GitHub forks](https://img.shields.io/github/forks/ZGCA-Forge/Elevator.svg?style=social&label=Fork)](https://github.com/ZGCA-Forge/Elevator/fork)
[![GitHub issues](https://img.shields.io/github/issues/ZGCA-Forge/Elevator.svg)](https://github.com/ZGCA-Forge/Elevator/issues)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/ZGCA-Forge/Elevator/blob/main/LICENSE)

</div>

---

Elevator Saga is a Python implementation of an elevator [simulation game](https://play.elevatorsaga.com/) with a event-driven architecture Design and optimize elevator control algorithms to efficiently transport passengers in buildings.

### Features

- 🏢 **Realistic Simulation**: Physics-based elevator movement with acceleration, deceleration, and realistic timing

## Quick Start (One-Click Launch)

### Windows

**GUI Mode** (with visualization):
```bash
start.bat
```

**Headless Mode** (no GUI):
```bash
start_no_gui.bat
```

### Linux

**GUI Mode** (with visualization):
```bash
chmod +x start.sh
./start.sh
```

**Headless Mode** (no GUI):
```bash
chmod +x start_no_gui.sh
./start_no_gui.sh
```

The start scripts will automatically:
1. Check Python installation (requires Python 3.10+)
2. Install all dependencies via pip
3. Run the LOOK V2 algorithm controller (connects to running simulator server)

## Project Structure

```
.
├── controller.py              # Main entry point - LOOK V2 algorithm controller
├── start.bat / start.sh       # One-click launcher (GUI mode)
├── start_no_gui.bat / start_no_gui.sh  # One-click launcher (headless mode)
├── elevator/                  # Core elevator control module
│   ├── __init__.py
│   ├── client/                # Client API and controller base class
│   │   ├── api_client.py      # HTTP client for simulator API
│   │   ├── base_controller.py # Base class for algorithm implementation
│   │   └── proxy_models.py    # Data models for elevator, floor, passenger
│   ├── core/                  # Core simulation data models
│   │   └── models.py          # Enums and data structures
│   ├── utils/                 # Utility modules
│   │   └── debug.py           # Debugging utilities
│   └── visualization/         # Optional visualization server
│       └── web_server.py      # FastAPI-based web visualization
├── tests/                     # Test suite
├── docs/                      # Documentation
├── pyproject.toml             # Project configuration
└── README.md                  # This file
```

## Algorithm Design Overview

### LOOK V2 Algorithm

This project implements the **LOOK V2** elevator scheduling algorithm, which is a real-time decision-making variant of the classic LOOK disk scheduling algorithm.

#### Core Design Principles:

1. **Real-time Decision Making**: Dynamically selects the next target floor at each stop, without maintaining a pre-planned task queue

2. **Dual Strategy Approach**:
   - **Idle Priority**: When elevator is empty, go to the nearest floor with waiting passengers
   - **LOOK Scanning**: When elevator has passengers, follow the scanning direction (up/down)

3. **Direction Matching**: Strictly adheres to LOOK algorithm constraints:
   - During upward scan: only pick up passengers going up (up_queue)
   - During downward scan: only pick up passengers going down (down_queue)

4. **Simplicity**: Avoids complex direction switching logic, allowing natural algorithm cycling

#### Key Features:
- Prevents deadlocks and elevator stalling
- Efficient passenger service with minimal wait times
- Natural bidirectional scanning pattern
- State recording for visualization and analysis

#### Implementation:
- Main algorithm controller: `controller.py`
- Core modules: `elevator/client/` (API client, base controller, proxy models)
- Data models: `elevator/core/models.py`

## Dependencies

### Required

- **Python**: 3.10 or higher
- **numpy**: >= 1.20.0 (for numerical computations)
- **flask**: >= 2.0.0 (for web server)

### Optional (for visualization)

- **fastapi**: >= 0.100.0
- **uvicorn**: >= 0.23.0
- **websockets**: >= 11.0.0

All dependencies are automatically installed when using the start scripts.

## Installation

### Basic Installation

```bash
pip install elevator-py
```

### Manual Installation

```bash
# Clone the repository
git clone https://github.com/ZGCA-Forge/Elevator.git
cd Elevator

# Install in editable mode
pip install -e .
```

## Running the Algorithm

### Method 1: Use Start Scripts (Recommended)

See [Quick Start](#quick-start-one-click-launch) section above.

### Method 2: Manual Execution

```bash
# Ensure simulator server is running (runs automatically in background)
# Then run the LOOK V2 controller:
python controller.py
```

The simulator server typically runs on port 8000 by default.

## Implementing Your Own Algorithm

To implement your own elevator scheduling algorithm:

1. **Extend the base controller**:
```python
from elevator.client.base_controller import ElevatorController
from elevator.client.proxy_models import ProxyElevator, ProxyFloor, ProxyPassenger
from elevator.core.models import Direction, SimulationEvent

class MyAlgorithmController(ElevatorController):
    def on_init(self, elevators, floors):
        # Initialize your algorithm
        pass

    def on_passenger_call(self, passenger, floor, direction):
        # Handle new passenger call
        pass

    def on_elevator_stopped(self, elevator, floor):
        # Decide next target floor for elevator
        elevator.go_to_floor(next_floor)

    def on_event_execute_start(self, tick, events, elevators, floors):
        # Called before processing events
        pass

    def on_event_execute_end(self, tick, events, elevators, floors):
        # Called after processing events
        pass
```

2. **Update controller.py** to use your algorithm class instead of LookV2Controller

3. **Run the algorithm**:
```bash
python controller.py
```

## Documentation

For detailed documentation, please visit: [https://zgca-forge.github.io/Elevator/](https://zgca-forge.github.io/Elevator/)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=ZGCA-Forge/Elevator&type=Date)](https://star-history.com/#ZGCA-Forge/Elevator&Date)

## License

This project is licensed under MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

Made with ❤️ by the ZGCA-Forge Team

</div>
