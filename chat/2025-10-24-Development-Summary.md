# Elevator Scheduling System - Development Summary (2025-10-24)

## Project Overview

This is an **Elevator Scheduling System** that supports two independent modes:
1. **GUI Mode (Visualization)** - Real-time Web interface showing elevator movement
2. **Algorithm Mode (Headless)** - Pure algorithm execution without visualization

Both modes connect to a shared simulator server and can run simultaneously for inter-group collaboration.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Simulator Server                      │
│                (port 8000)                              │
│  Manages elevator physics, passenger flows, events      │
└─────────────────────────────────────────────────────────┘
                         ↑
        ┌────────────────┴────────────────┐
        │                                  │
   ┌────▼──────┐                  ┌──────▼───────┐
   │   GUI     │                  │  Algorithm   │
   │ Controller│                  │ Controller   │
   │(registers │                  │(registers as │
   │  as "gui")│                  │"algorithm")  │
   └────┬──────┘                  └──────┬───────┘
        │                                │
   ┌────▼────────────────────────────┐   │
   │  FastAPI Web Server (5173)      │   │
   │  ┌──────────────────────────┐   │   │
   │  │ WebSocket /ws            │   │   │
   │  │ Real-time updates        │   │   │
   │  └──────────────────────────┘   │   │
   └────┬─────────────────────────────┘   │
        │                                  │
   ┌────▼──────────────────────────────┐  │
   │   Frontend (HTML/JS/CSS)          │  │
   │   ├─ index.html                   │  │
   │   ├─ app.js (Main logic)          │  │
   │   └─ style.css                    │  │
   └───────────────────────────────────┘  │
                                          │
        ┌─────────────────────────────────┘
        │
   ┌────▼────────────────┐
   │ Algorithm Execution │
   │ (LOOK V2 or custom) │
   └─────────────────────┘
```

---

## Key Components & Recent Changes

### 1. **base_controller.py** (Line 236)
**Problem Fixed**: Hardcoded `register_client("algorithm")` prevented GUI mode from registering correctly.

**Solution**: Now reads environment variable `ELEVATOR_CLIENT_TYPE`:
```python
client_type = os.environ.get("ELEVATOR_CLIENT_TYPE", "algorithm").lower()
if not self.api_client.register_client(client_type):
    print(f"Failed to register as {client_type} client, but continuing...")
```

**Impact**:
- ✅ GUI mode now registers as "gui" client
- ✅ Algorithm mode registers as "algorithm" client
- ✅ Enables independent operation or collaboration

---

### 2. **GUIController** (gui_controller.py)

**Changes Made**:
1. **on_init()** - Now pushes "init" message to event queue
   ```python
   message = {
       "type": "init",
       "data": {
           "elevators_count": len(elevators),
           "floors_count": len(floors),
           "tick": 0
       }
   }
   if self.event_queue:
       self.event_queue.put(message)
   ```

2. **on_event_execute_start()** - Now includes events in state_update message
   ```python
   events_data = []
   if events:
       for event in events:
           events_data.append({
               "type": event.type.value,
               "data": event.data
           })
   message = {
       "type": "state_update",
       "data": {
           "tick": tick,
           "elevators": elevators_data,
           "floors": floors_data,
           "events": events_data,  # ← NEW
       }
   }
   ```

**Impact**:
- ✅ Frontend immediately receives initialization info
- ✅ Frontend gets complete state including events each tick
- ✅ Real-time visualization works properly

---

### 3. **Frontend (app.js)** - Critical Changes

#### Problem 1: No Initial UI Display
**Root Cause**: Frontend waited for state_update to initialize. If no events in first tick, nothing displayed.

**Solution**: Handle "init" message type
```javascript
case 'init':
    // Create initial state with elevator and floor structures
    const initialState = {
        tick: 0,
        elevators: Array(message.data.elevators_count).fill(null).map((_, i) => ({
            id: i,
            current_floor: 0,
            direction: 'stopped',
            passengers: [],
        })),
        floors: Array(message.data.floors_count).fill(null).map((_, i) => ({
            floor: i,
            up_queue: [],
            down_queue: [],
        })),
        events: []
    };
    this.history = [initialState];
    this.updateProgressBar();
    this.renderCurrentState();
```

#### Problem 2: JavaScript Errors on Render
**Error Messages**:
```
Cannot read properties of undefined (reading 'length')
Cannot read properties of undefined (reading '1')
```

**Root Causes**:
1. `floorData` could be undefined when looking up floor in state.floors
2. `state.passengers[passengerId]` accessing invalid indices

**Solutions**:

a) **In renderBuilding()** - Add defensive checks:
```javascript
if (!state || !state.elevators || !state.floors) {
    console.error('Invalid state data:', state);
    return;
}

// Safe floor lookup
let floorData = state.floors.find(f => f.floor === floorNum);
if (!floorData) {
    floorData = {
        floor: floorNum,
        up_queue: [],
        down_queue: []
    };
}
```

b) **In queue rendering** - Validate passengerId:
```javascript
floorData.up_queue.forEach(passengerId => {
    if (passengerId === undefined || passengerId === null) {
        return;
    }

    const badge = document.createElement('span');
    // ... rest of logic with null checks

    if (state.passengers && typeof state.passengers === 'object' && state.passengers[passengerId]) {
        // Use passenger data
    } else {
        badge.textContent = `P${passengerId}`;
    }
});
```

c) **Added debugging logs**:
```javascript
console.log(`[WebSocket] Received message type: ${message.type}`, message);
console.log(`[Render] Tick ${state.tick}, Floors: ${state.floors ? state.floors.length : 0}, Elevators: ${state.elevators ? state.elevators.length : 0}`);
```

#### Problem 3: Old JSON Loading UI
**Issue**: HTML had controls to load JSON recording files that are no longer used.

**Solution**:
- Deleted `control-recording` div from HTML
- Removed `loadRecordingList()` and `loadRecording()` functions from JS
- Removed json-related event listeners from `initUI()`

**Files Cleaned**:
- Deleted: `MODIFICATIONS.md`, `USAGE.md`, `VERIFICATION.md`
- Kept: `README.md` (updated with English), `CLAUDE.md` (coding standards)

---

## Important Implementation Details

### Environment Variables

| Variable | Value | Effect |
|----------|-------|--------|
| `ELEVATOR_CLIENT_TYPE` | `gui` | Launches GUIController, starts FastAPI server |
| `ELEVATOR_CLIENT_TYPE` | `algorithm` | Launches LookV2Controller, runs algorithm |

**How it works**:
1. `start.bat` sets `ELEVATOR_CLIENT_TYPE=gui`
2. `start_no_gui.bat` sets `ELEVATOR_CLIENT_TYPE=algorithm`
3. Both execute `controller.py`
4. `controller.py` reads env var and imports appropriate controller

---

### WebSocket Message Flow

**GUI Mode**:
```
1. GUIController.on_init()
   → Pushes "init" message to event queue
   → Frontend receives: { type: "init", data: { elevators_count: X, floors_count: Y } }

2. GUIController.on_event_execute_start() (every tick)
   → Collects elevator positions, queues, and events
   → Pushes "state_update" message to event queue
   → Frontend receives: { type: "state_update", data: { tick, elevators[], floors[], events[] } }

3. app.js receives messages via WebSocket
   → Handles "init": Creates initial state structure
   → Handles "state_update": Appends to history, renders latest

4. renderCurrentState() triggers renderBuilding()
   → Iterates through floors from top to bottom
   → Draws elevator cars, passenger queues, direction indicators
   → Updates stats and event log
```

---

### Data Structure Flow

**Initial State** (after "init" message):
```javascript
{
    tick: 0,
    elevators: [
        { id: 0, current_floor: 0, direction: 'stopped', passengers: [] },
        { id: 1, current_floor: 0, direction: 'stopped', passengers: [] },
        ...
    ],
    floors: [
        { floor: 0, up_queue: [], down_queue: [] },
        { floor: 1, up_queue: [], down_queue: [] },
        ...
    ],
    events: []
}
```

**Updated State** (from "state_update" message):
```javascript
{
    tick: 5,
    elevators: [
        { id: 0, current_floor: 2, direction: 'up', passengers: [1, 3, 5] },
        { id: 1, current_floor: 1, direction: 'down', passengers: [2] },
        ...
    ],
    floors: [
        { floor: 0, up_queue: [7, 8], down_queue: [] },
        { floor: 1, up_queue: [], down_queue: [4, 6] },
        ...
    ],
    events: [
        { type: 'passenger_board', data: { elevator: 0, passenger: 1 } },
        { type: 'stopped_at_floor', data: { elevator: 0, floor: 2 } },
        ...
    ]
}
```

---

## Common Pitfalls & Solutions

### 1. Frontend Shows No Elevator Structure
**Symptoms**: Page loads but no building/elevators visible

**Causes**:
- Browser cache not cleared
- "init" message not received
- JavaScript errors in console

**Solutions**:
1. Clear browser cache: `Ctrl+Shift+Delete`
2. Use private/incognito mode
3. Check browser console (F12) for JavaScript errors
4. Verify WebSocket connection shows in Network tab
5. Look for `[WebSocket]` logs in console

### 2. JavaScript Errors During Rendering
**Symptoms**: Console shows `Cannot read properties of undefined`

**Root Causes**:
- `state.floors` is empty array → `find()` returns undefined
- `passengerId` is null/undefined
- `state.passengers` is not an object

**Prevention**:
- Always validate objects before accessing properties: `if (obj && typeof obj === 'object')`
- Check array length before accessing: `if (arr && arr.length > 0)`
- Add console.log debug statements in critical functions

### 3. WebSocket Connection Drops
**Symptoms**: Data stops updating after some time

**Causes**:
- Server crashed/restarted
- Network issues
- Browser closed/navigated away

**Solutions**:
- Check Python process is still running
- Look at server logs for errors
- Restart start.bat

### 4. Algorithm and GUI Both Running But GUI Doesn't Show Algorithm Results
**Symptoms**: Algorithm running (console shows control messages) but Web interface blank

**Causes**:
- Both registered as "algorithm" instead of correct types
- GUIController not connected to event queue

**Solutions**:
- Verify `ELEVATOR_CLIENT_TYPE` environment variables are set correctly
- Check that GUIController successfully imports `get_event_queue()`
- Monitor that `on_init()` and `on_event_execute_start()` are called

---

## Testing Checklist

- [ ] Start GUI mode: `start.bat` → Web page opens at http://127.0.0.1:5173
- [ ] See console message: `[GUI] 初始化: X 部电梯，Y 层楼`
- [ ] Browser console shows `[WebSocket] Received message type: init`
- [ ] Building structure renders with elevator cars and floor labels
- [ ] Start algorithm mode: `start_no_gui.bat` → Console shows algorithm decisions
- [ ] When algorithm runs, GUI updates in real-time
- [ ] No JavaScript errors in browser console
- [ ] Elevator positions, directions, and passenger counts update correctly

---

## For Next Developer

### Quick Start
1. Read `README.md` for project overview
2. Read `CLAUDE.md` for coding standards
3. Run `start.bat` for GUI or `start_no_gui.bat` for algorithm
4. Check browser console (F12) for debug logs

### Key Files to Understand (In Order)
1. `controller.py` - Entry point, reads env var, launches controller
2. `elevator/client/base_controller.py` - Event-driven loop, connects to simulator
3. `elevator/client/gui_controller.py` - Implements GUI mode (listen-only)
4. `elevator/visualization/web_server.py` - FastAPI server with WebSocket
5. `elevator/visualization/static/app.js` - Frontend logic, message handling, rendering
6. `elevator/visualization/static/index.html` - UI structure

### If You Need to Add Features
- **New Elevator Algorithm**: Extend `ElevatorController`, override `on_elevator_stopped()`
- **Custom Event Handler**: Add method to `base_controller.py` or `gui_controller.py`
- **Frontend Visualization Change**: Modify `renderBuilding()` in `app.js`
- **New WebSocket Message Type**: Add case in `handleWebSocketMessage()` and broadcast from backend

### Common Modifications
```python
# To change port
# gui_controller.py: super().__init__("http://127.0.0.1:XXXX")
# web_server.py: uvicorn.run(..., port=XXXX)

# To add GUI event
# 1. Add to GUIController.on_XXX() method
# 2. Construct message dict
# 3. self.event_queue.put(message)
# 4. Handle in app.js handleWebSocketMessage()

# To modify rendering
# app.js: renderBuilding() → renderCurrentState() → updateStats()
```

---

## Architecture Decisions Explained

### Why GUIController is Listen-Only
- **Reason**: Allows independent GUI or Algorithm controllers to connect
- **Benefit**: Either can register with simulator, whichever wins gets control
- **Trade-off**: GUI can't actively control elevators (by design)

### Why WebSocket Instead of HTTP Polling
- **Reason**: Eliminates polling latency, perfect for real-time visualization
- **Benefit**: Server pushes updates immediately to all connected clients
- **Trade-off**: Slightly more complex server code

### Why Environment Variables Instead of Config File
- **Reason**: Easy to set in batch scripts, clear separation of concerns
- **Benefit**: No file I/O needed, works on all platforms (Windows/Linux/Mac)
- **Trade-off**: Can't pass complex configuration

### Why Message Queue Between GUIController and WebSocket
- **Reason**: Decouples controller from server, allows async pushing
- **Benefit**: Controller doesn't block waiting for WebSocket connections
- **Trade-off**: Extra indirection, slight memory overhead

---

## Performance Notes

- **Frontend Rendering**: O(floors × elevators) per frame, acceptable up to 20 elevators
- **Message Queue Size**: Monitor if many queued messages → possible slow consumer
- **WebSocket**: Can handle ~100 messages/sec without issues
- **Python Event Loop**: Single-threaded, don't block in callbacks

---

## Known Limitations

1. **No Persistence**: Elevator state lost if server restarts
2. **No Multiple Simultanerous Simulations**: Only one simulator instance supported
3. **No User Authentication**: Open access to all APIs
4. **No Data Validation**: Frontend trusts all data from backend
5. **Limited Mobile Support**: Web UI optimized for desktop browsers

---

## Future Improvements

- [ ] Add historical data storage (PostgreSQL)
- [ ] Implement user accounts and simulation sharing
- [ ] Add real-time statistics dashboard
- [ ] Support multiple elevator systems
- [ ] Add AI-powered algorithm recommendations
- [ ] Mobile-responsive UI redesign

---

## Emergency Debug Commands

```bash
# Check if simulator is running
curl http://127.0.0.1:8000/api/status

# Check if Web server is running
curl http://127.0.0.1:5173/

# Kill Python process (Windows)
taskkill /IM python.exe /F

# Check port usage (Windows)
netstat -ano | findstr :5173

# Test WebSocket connection (from browser console)
ws = new WebSocket('ws://127.0.0.1:5173/ws')
ws.onmessage = (e) => console.log(JSON.parse(e.data))
```

---

## Contact Points With Simulator

All communication via HTTP to `http://127.0.0.1:8000`:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/client/register` | POST | Register as gui or algorithm |
| `/api/state` | GET | Get current simulation state |
| `/api/step` | POST | Advance simulation by N ticks |
| `/api/elevators/{id}/go_to_floor` | POST | Command elevator to floor |
| `/api/reset` | POST | Reset simulation |
| `/api/traffic/next` | POST | Load next traffic file |
| `/api/traffic/info` | GET | Get current traffic info |

---

## Document Generation Date

**2025-10-24** - After major refactoring to support independent GUI and Algorithm modes with real-time WebSocket visualization.

---

## Questions?

- Check code comments - every major function is documented
- Search for `console.log` statements in browser for debug info
- Review git history to see what changed and why
- Test with `start.bat` first to ensure basic setup works

Happy coding! 🚀
