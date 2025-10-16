# Bug: Traffic file switching fails when elevator/floor count changes

**Version Information**

- elevator-py version: v0.1.4
- Python version: 3.11
- File: `elevator_saga/client/base_controller.py`

---

## Bug Description

When switching between traffic files with different elevator or floor counts (e.g., 2 elevators → 3 elevators), the controller crashes with `ValueError: Elevator number mismatch`.

---

## Steps to Reproduce

1. Run an algorithm with a traffic file (e.g., `finalTest_ICSS67` with 2 elevators, 10 floors)
2. Let it complete successfully
3. Switch to a traffic file with different configuration (e.g., `finalTest_ICSSDJ` with 3 elevators, 10 floors)
4. Controller crashes in `_reset_and_reinit()`

---

## Expected Behavior

The controller should successfully reset and reinitialize with the new traffic file configuration, allowing different elevator/floor counts.

---

## Actual Behavior

```
ValueError: Elevator number mismatch: 2 != 3
```

**Stack trace:**
```python
File "elevator_saga/client/base_controller.py", line 281, in _run_event_driven_simulation
    self._reset_and_reinit()
File "elevator_saga/client/base_controller.py", line 396, in _reset_and_reinit
    self._update_wrappers(state)
File "elevator_saga/client/base_controller.py", line 293, in _update_wrappers
    raise ValueError(f"Elevator number mismatch: {len(self.elevators)} != {len(state.elevators)}")
```

---

## Root Cause

In `base_controller.py`, the `_reset_and_reinit()` method calls `_update_wrappers(state)` without the `init=True` flag (line 396), which prevents recreating elevator/floor proxies when configuration changes.

---

## Suggested Fix

**File:** `elevator_saga/client/base_controller.py`
**Line:** 396

```python
# Current (incorrect):
def _reset_and_reinit(self) -> None:
    """重置并重新初始化"""
    try:
        self.api_client.reset()
        self.current_tick = 0
        state = self.api_client.get_state()
        self._update_wrappers(state)  # ❌ Missing init=True
        ...

# Fixed:
def _reset_and_reinit(self) -> None:
    """重置并重新初始化"""
    try:
        self.api_client.reset()
        self.current_tick = 0
        state = self.api_client.get_state()
        self._update_wrappers(state, init=True)  # ✅ Allow reconfiguration
        ...
```

---

## Impact

This bug prevents:
- Running multiple test cases with different configurations sequentially
- Using the web visualization interface to run different traffic files
- Any scenario involving `next_traffic_round()` with configuration changes

---

## Test Cases

After the fix, these scenarios should work:

| From | To | Status |
|------|------|--------|
| 2 elevators, 10 floors | 3 elevators, 10 floors | ✅ Should pass |
| 3 elevators, 10 floors | 3 elevators, 20 floors | ✅ Should pass |
| 3 elevators, 20 floors | 4 elevators, 20 floors | ✅ Should pass |

---

## Additional Context

This issue was discovered while testing the web visualization feature with the finalTest suite. The fix is minimal (one parameter) and has been verified to work correctly without affecting other functionality.
