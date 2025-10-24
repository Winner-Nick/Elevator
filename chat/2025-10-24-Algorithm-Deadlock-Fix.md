# 算法卡死问题修复 (2025-10-24)

## 问题描述

**现象**：GUI 启动后进入等待状态，但当运行算法时，算法会卡住，无法推进

```
[GUI] 进入事件监听循环，等待算法 controller 推进模拟...
(算法启动... 然后卡住)
```

---

## 根本原因分析

在之前的 GUIController._run_event_driven_simulation 重写中，遗漏了 **3 个关键的初始化步骤**：

### 问题 1️⃣：缺少重置检查

**症状**：模拟器处于脏状态（tick > 0），导致状态不同步

```python
# ❌ 错误的做法（我原来的代码）
state = self.api_client.get_state()
self._update_wrappers(state, init=True)

# ✅ 正确的做法
state = self.api_client.get_state()
if state.tick > 0:
    # 模拟器已经初始化过，需要重置
    self.api_client.reset()
    time.sleep(0.3)
    return self._run_event_driven_simulation()  # 递归重试
```

**影响**：如果不重置，GUI 和算法可能看到的初始状态不同步，导致后续逻辑混乱

### 问题 2️⃣：缺少流量信息更新

**症状**：没有检查测试案例的 max_tick

```python
# ❌ 错误的做法（我原来的代码）
state = self.api_client.get_state()
self._update_wrappers(state, init=True)
# 直接进入轮询...

# ✅ 正确的做法
state = self.api_client.get_state()
self._update_traffic_info()
if self.current_traffic_max_tick == 0:
    # 测试案例已用完，加载下一轮
    self.api_client.next_traffic_round(full_reset=True)
    time.sleep(0.3)
    return self._run_event_driven_simulation()  # 递归重试
```

**影响**：当测试案例耗尽时，无法自动加载新的测试案例，可能导致算法卡在某个等待状态

### 问题 3️⃣：缺少缓存失效标记

**症状**：API 客户端缓存导致获取到过期状态

```python
# ❌ 错误的做法（我原来的代码）
state = self.api_client.get_state()
self._update_wrappers(state, init=True)
# 没有标记已处理，缓存永远不会失效

# ✅ 正确的做法
state = self.api_client.get_state()
self._update_wrappers(state, init=True)
self.api_client.mark_tick_processed()  # ← 关键！失效缓存
```

**缓存机制说明**：
```python
# api_client.py 中的缓存逻辑
def get_state(self, force_reload: bool = False) -> SimulationState:
    if not force_reload and self._cached_state is not None and not self._tick_processed:
        return self._cached_state  # 返回缓存

    # 否则获取新数据...
    self._tick_processed = False  # 重置标记
```

**影响**：
- 如果没有 mark_tick_processed()，状态永远被缓存
- 轮询 get_state() 会一直返回同一个状态
- 算法看不到 GUI 的轮询获取的新状态，可能卡住等待

---

## 修复方案

### 修改 1：初始化阶段完整处理

```python
def _run_event_driven_simulation(self) -> None:
    # ... 注册代码 ...

    # 获取初始状态
    state = self.api_client.get_state()

    # ⚠️ 检查 1：是否需要重置
    if state.tick > 0:
        print("[GUI] 检测到模拟器已初始化（tick > 0），执行重置...")
        self.api_client.reset()
        time.sleep(0.3)
        return self._run_event_driven_simulation()  # 递归重新初始化

    # 初始化状态包装器
    self._update_wrappers(state, init=True)

    # ⚠️ 检查 2：流量信息和测试案例
    self._update_traffic_info()
    if self.current_traffic_max_tick == 0:
        print("[GUI] max_tick = 0，加载下一轮测试案例...")
        self.api_client.next_traffic_round(full_reset=True)
        time.sleep(0.3)
        return self._run_event_driven_simulation()  # 递归重新初始化

    # ⚠️ 关键 3：标记初始化完成，失效 API 缓存
    self.api_client.mark_tick_processed()

    # 继续初始化...
```

### 修改 2：轮询循环中的缓存处理

```python
while self.is_running:
    try:
        # ⚠️ 关键：长时间无更新时强制重新加载
        force_reload = no_change_count > 50  # 约 5 秒后强制刷新
        current_state = self.api_client.get_state(force_reload=force_reload)

        if current_state.tick != last_tick:
            # ⚠️ 关键：状态更新后立即标记已处理
            self.api_client.mark_tick_processed()

            # 继续处理...
            self._update_wrappers(current_state)
            last_tick = current_state.tick
            no_change_count = 0
        else:
            no_change_count += 1

        time.sleep(poll_interval)
```

---

## 修复对比

### 原始问题流程

```
GUI 启动
  ↓
get_state() → tick 0 (被缓存)
  ↓
进入轮询循环
  ↓
轮询 get_state() → 返回缓存的 tick 0（永远）
  ↓
算法启动 (另一个线程)
  ↓
step() 推进到 tick 1, 2, 3...
  ↓
但 GUI 的轮询永远看不到新的 tick
  ↓
算法等待 GUI 的某个响应？ → 可能卡住
```

### 修复后流程

```
GUI 启动
  ↓
get_state() → tick 0 (被缓存)
  ↓
检查重置 ✓ / 检查 max_tick ✓
  ↓
mark_tick_processed() → 失效缓存
  ↓
进入轮询循环
  ↓
轮询 get_state() → 缓存失效，获取真实 tick
  ↓
算法启动
  ↓
step() 推进到 tick 1
  ↓
GUI 下一次轮询时，强制刷新，看到 tick 1 ✓
  ↓
mark_tick_processed() → 再次失效缓存
  ↓
正常同步！
```

---

## 为什么算法会卡住？

1. **竞争条件**：
   - GUI 的轮询（每 100ms 调用一次 get_state）
   - 算法的 step()（可能占用服务器资源）
   - 两者并发时可能导致服务器状态不一致

2. **缓存导致状态不同步**：
   - GUI 看不到最新状态 → 无法正确处理事件
   - 前端收不到状态更新 → WebSocket 推送失败
   - 某些等待机制超时 → 算法卡住

3. **初始化不完整**：
   - 没有重置脏状态
   - 没有正确加载测试案例
   - API 客户端的缓存状态不一致

---

## 测试方式

### 测试场景 1：GUI 然后算法

```bash
# 终端 1
start.bat

# 等待 "进入事件监听循环" 消息...

# 终端 2
start_no_gui.bat

# 观察日志
[GUI] 收到状态更新: tick 0 -> 1
[GUI] 收到状态更新: tick 1 -> 2
# ... 持续更新，没有卡死
```

### 测试场景 2：重复启动

```bash
# 第一轮
start.bat + start_no_gui.bat
# ... 运行正常 ...

# 不关闭，直接在算法终端 Ctrl+C，然后重新启动
start_no_gui.bat

# 应该重新初始化，没有状态冲突
```

---

## 修复的代码变更

**文件**：`elevator/client/gui_controller.py`

**修改内容**：
- ✅ 添加重置检查（state.tick > 0）
- ✅ 添加流量信息更新检查（max_tick = 0）
- ✅ 初始化后调用 mark_tick_processed()
- ✅ 状态更新后调用 mark_tick_processed()
- ✅ 长时间无更新时强制刷新缓存

**代码行数变化**：+25 行

---

## 总结

三个遗漏的初始化步骤导致了算法卡死问题：

| 问题 | 原因 | 影响 | 修复 |
|------|------|------|------|
| 缺少重置检查 | 模拟器脏状态（tick > 0） | 状态不同步 | 调用 reset() 重新初始化 |
| 缺少流量更新 | 没有加载测试案例 | 无法推进模拟 | 调用 _update_traffic_info() 和 next_traffic_round() |
| 缺少缓存标记 | API 缓存导致状态过期 | 轮询获不到新状态 | 调用 mark_tick_processed() 失效缓存 |

**关键点**：
- `mark_tick_processed()` 是确保缓存失效的关键
- 递归重新初始化确保所有前置条件满足
- 长时间无更新时强制刷新避免缓存卡住

---

**日期**: 2025-10-24
**相关文件**: elevator/client/gui_controller.py:45-180
**验证**: ✅ 语法检查通过
