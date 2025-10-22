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
3. Run the LOOK V2 algorithm (connects to existing simulator server)

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
- Main algorithm: `elevator_saga/client_examples/look_v2_example.py`
- Visualization version (optional): `elevator_saga/client_examples/visual_look_v2_example.py`

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
# Start the backend simulator (Terminal #1)
python -m elevator_saga.server.simulator
```

```bash
# Start the LOOK V2 client (Terminal #2)
python -m elevator_saga.client_examples.look_v2_example
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
