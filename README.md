# Elevator Scheduling System

🏢 **Elevator Dispatch Model** - Efficient passenger transportation through precise elevator control algorithms

---

## Quick Start

### Windows

**Visualization Mode** (with Web Interface):
```bash
start.bat
```

**Headless Mode** (Algorithm Only):
```bash
start_no_gui.bat
```

### Linux/Mac

**Visualization Mode**:
```bash
chmod +x start.sh
./start.sh
```

**Headless Mode**:
```bash
chmod +x start_no_gui.sh
./start_no_gui.sh
```

The startup scripts will automatically:
1. Check Python version (requires 3.10+)
2. Install all dependencies
3. Launch the elevator controller

---

## Running Modes

### 1️⃣ Visualization Mode (GUI)

```bash
start.bat
```

**Features**:
- Launches FastAPI Web server (port 5173)
- Real-time elevator status visualization via WebSocket
- Shows elevator position, direction, passenger queues
- Supports pause, speed control, and other playback features

**Access**: http://127.0.0.1:5173

**Workflow**:
```
GUI Launch
  ↓
Web Server Startup (FastAPI)
  ↓
GUIController connects to simulator (registers as "gui" client)
  ↓
Receives simulator callbacks, pushes real-time data to WebSocket
  ↓
Frontend displays live elevator movement
```

### 2️⃣ Algorithm Mode (Headless)

```bash
start_no_gui.bat
```

**Features**:
- Pure algorithm execution, no Web interface
- Directly connects to simulator (registers as "algorithm" client)
- Executes LOOK V2 scheduling algorithm
- Real-time floor decision making for each elevator

**Workflow**:
```
Algorithm Launch
  ↓
LookV2Controller connects to simulator
  ↓
Immediately starts LOOK V2 algorithm
  ↓
Dynamically decides next target floor for each elevator
```

---

## Project Structure

```
.
├── controller.py                 # Main entry point - launches GUI or Algorithm based on env var
├── start.bat / start.sh          # Launcher (GUI Mode)
├── start_no_gui.bat / start_no_gui.sh  # Launcher (Algorithm Mode)
├── CLAUDE.md                     # Coding standards
├── README.md                     # This document
│
├── elevator/                     # Core modules
│   ├── client/
│   │   ├── api_client.py        # HTTP client (communicates with simulator)
│   │   ├── base_controller.py   # Controller base class
│   │   ├── gui_controller.py    # GUI mode (listen-only)
│   │   └── proxy_models.py      # Data proxy objects
│   ├── core/
│   │   └── models.py            # Data models and enums
│   ├── utils/
│   │   └── debug.py             # Debug utilities
│   └── visualization/
│       ├── web_server.py        # FastAPI Web server
│       ├── recorder.py          # Simulation recorder
│       └── static/
│           ├── index.html       # Frontend page
│           ├── app.js           # Frontend logic
│           └── style.css        # Styles
│
├── client_examples/             # User-defined algorithm examples
│   └── simple_example.py        # Simple algorithm example
│
├── traffic/                     # Traffic files
│   └── *.json                   # Passenger arrival schedules
│
└── requirements.txt             # Python dependencies
```

---

## LOOK V2 Algorithm

### Core Concept

A real-time decision-making variant of the classic LOOK elevator scheduling algorithm:

1. **Idle Priority**: When elevator is empty, move to the nearest floor with waiting passengers
2. **LOOK Scanning**: When elevator has passengers, follow the scanning direction (up/down)
3. **Direction Matching**: Only pick up passengers going in the current direction
4. **Natural Cycling**: Avoids complex direction switching logic

### Implementation

- Algorithm Controller: `LookV2Controller` in `controller.py`
- Core Logic: `_select_next_floor_look()` method in `on_elevator_stopped()`

### Key Features

- ✅ No deadlocks
- ✅ Minimized wait times
- ✅ Clean and understandable code

---

## Multi-Controller Scenarios (Inter-Group Collaboration)

The system supports running two different controllers simultaneously:

### Scenario 1: Your GUI + Someone Else's Algorithm

**Step 1**: Launch your visualization
```bash
set ELEVATOR_CLIENT_TYPE=gui
python controller.py
```

**Step 2**: Launch their algorithm (in another terminal)
```bash
cd /path/to/other_repo
set ELEVATOR_CLIENT_TYPE=algorithm
python controller.py
```

**Result**:
- Your GUI controller only receives events (listen-only)
- Their algorithm controller controls the elevators
- Web interface (5173) displays their algorithm's results

### Scenario 2: Someone Else's GUI + Your Algorithm

**Step 1**: Launch their visualization
```bash
cd /path/to/other_repo
set ELEVATOR_CLIENT_TYPE=gui
python controller.py
# Visit their web interface
```

**Step 2**: Launch your algorithm (in another terminal)
```bash
set ELEVATOR_CLIENT_TYPE=algorithm
python controller.py
```

**Result**:
- Their GUI controller only receives events
- Your algorithm controller controls the elevators
- Their web interface displays your algorithm's results

---

## Implementing Custom Algorithms

### Basic Template

```python
from elevator.client.base_controller import ElevatorController
from elevator.client.proxy_models import ProxyElevator, ProxyFloor, ProxyPassenger
from elevator.core.models import Direction, SimulationEvent
from typing import List

class MyAlgorithmController(ElevatorController):
    """My custom elevator scheduling algorithm"""

    def on_init(self, elevators: List[ProxyElevator], floors: List[ProxyFloor]) -> None:
        """Initialize algorithm"""
        print(f"Initialized: {len(elevators)} elevators, {len(floors)} floors")

    def on_elevator_stopped(self, elevator: ProxyElevator, floor: ProxyFloor) -> None:
        """Decide next target floor when elevator stops"""
        next_floor = self.decide_next_floor(elevator, floor)
        elevator.go_to_floor(next_floor)

    def on_passenger_call(self, passenger: ProxyPassenger, floor: ProxyFloor, direction: str) -> None:
        """Handle new passenger call"""
        pass

    def on_elevator_idle(self, elevator: ProxyElevator) -> None:
        """Handle idle elevator"""
        pass

    def on_passenger_board(self, elevator: ProxyElevator, passenger: ProxyPassenger) -> None:
        """Handle passenger boarding"""
        pass

    def on_passenger_alight(self, elevator: ProxyElevator, passenger: ProxyPassenger, floor: ProxyFloor) -> None:
        """Handle passenger alighting"""
        pass

    def on_event_execute_start(self, tick: int, events: List[SimulationEvent],
                              elevators: List[ProxyElevator], floors: List[ProxyFloor]) -> None:
        """Before event processing"""
        pass

    def on_event_execute_end(self, tick: int, events: List[SimulationEvent],
                            elevators: List[ProxyElevator], floors: List[ProxyFloor]) -> None:
        """After event processing"""
        pass

    def on_elevator_passing_floor(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        """Optional: handle elevator passing floor"""
        pass

    def on_elevator_approaching(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        """Optional: handle elevator approaching floor"""
        pass
```

### Using Custom Algorithm

1. Place your algorithm in `client_examples/` directory
2. Modify `controller.py` to import your algorithm class
3. Run `start_no_gui.bat`

---

## Dependencies

### Required
- Python >= 3.10
- fastapi >= 0.100.0
- uvicorn >= 0.23.0
- websockets >= 11.0.0
- pydantic >= 2.0.0

All dependencies are automatically installed when running the startup scripts.

---

## Environment Variables

| Variable | Value | Description |
|----------|-------|-------------|
| `ELEVATOR_CLIENT_TYPE` | `gui` | Launch visualization mode |
| `ELEVATOR_CLIENT_TYPE` | `algorithm` | Launch algorithm mode |
| `ELEVATOR_SERVER_URL` | Default: `http://127.0.0.1:8000` | Simulator server address |

---

## Troubleshooting

### Issue 1: Web interface won't open

1. Check if Python process is running
2. Ensure port 5173 is not in use
3. Check firewall settings
4. Open browser developer tools (F12) to check Console for errors

### Issue 2: Simulator not responding

1. Confirm simulator service is running (usually at http://127.0.0.1:8000)
2. Check network connection
3. Look for connection errors in command line output

### Issue 3: Elevators not moving

1. Ensure both controllers are connected to the same simulator
2. Verify correct client type registration (gui or algorithm)
3. Check command line logs for error messages

---

## Documentation

See also:
- `CLAUDE.md` - Coding standards and design principles
- Code comments - Key functions have detailed explanations

---

## License

MIT License - See LICENSE file for details

---

<div align="center">

Made with ❤️ by the Team

</div>
