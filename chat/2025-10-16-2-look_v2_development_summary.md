# LOOK V2 算法开发总结

**日期**: 2025-10-16
**开发轮次**: 第5轮（全新LOOK V2实现）
**成果**: 创建简洁的实时决策LOOK算法，完成率78%

---

## 一、开发背景

### 1.1 前期问题回顾

从上一轮调试总结（`2025-10-16-1-optimal_look_debugging_log.md`）中发现：
- **optimal_look_example.py** 过度复杂（1000+行代码）
- 完成率从100%降到52-54%
- 引入了复杂的任务队列、多阶段排序、任务合并等逻辑
- **核心教训**：过早优化，忽略了基本约束（方向匹配）

### 1.2 新策略

采用"**实时决策**"而非"**任务队列**"：
- 不预先规划完整路径
- 在`on_elevator_stopped`时动态决定下一个目标楼层
- 参考`bus_example.py`的简洁性
- **目标**：先确保100%完成率，性能其次

---

## 二、实现过程

### 2.1 核心设计

**文件**: `elevator_saga/client_examples/look_v2_example.py`（约240行）

**关键特性**:
1. **不维护任务队列** - 简化复杂度
2. **实时收集需求** - 每次停靠时动态收集所有目标楼层
3. **正确处理方向匹配** - 分别收集`up_targets`和`down_targets`
4. **标准LOOK算法** - 沿一个方向扫描到边界，然后转向

**核心方法**:
```python
def on_elevator_stopped(elevator, floor):
    # 1. 收集目标楼层
    up_targets = set()    # 需要向上的乘客所在楼层
    down_targets = set()  # 需要向下的乘客所在楼层

    # 1.1 电梯内乘客目的地
    for passenger_id in elevator.passengers:
        destination = self.passenger_destinations.get(passenger_id)
        if destination > current_floor:
            up_targets.add(destination)
        elif destination < current_floor:
            down_targets.add(destination)

    # 1.2 等待上梯的乘客位置
    for floor in floors:
        if floor.up_queue:
            up_targets.add(floor.floor)
        if floor.down_queue:
            down_targets.add(floor.floor)

    # 2. 按LOOK算法选择下一个目标
    next_floor = _select_next_floor_look(current_floor, current_direction,
                                          up_targets, down_targets)

    # 3. 移动到下一个楼层
    if next_floor is not None:
        elevator.go_to_floor(next_floor)
```

### 2.2 开发中遇到的问题及修复

#### 问题1：初始版本完成率0% (0/74)
**原因**：只收集当前方向匹配的乘客，导致无法发现需求
```python
# ❌ 错误代码
if current_direction == Direction.UP:
    if floor.up_queue:
        target_floors.add(floor.floor)
```

**修复**：分别收集两个方向的需求
```python
# ✅ 正确代码
for floor in floors:
    if floor.up_queue:
        up_targets.add(floor.floor)
    if floor.down_queue:
        down_targets.add(floor.floor)
```

#### 问题2：提升到4/74，但还是很低
**原因**：目标选择逻辑不完整，向上扫描时不去上方的`down_targets`

**示例**：电梯在F0向上，F4有向下的乘客（F4→F0）
- 旧逻辑：不去F4（因为F4不在`up_targets`中）→ 无法接到乘客
- 新逻辑：先去F4（虽然不能接乘客），到达后转向向下，然后接`down_queue`

**修复**：完善LOOK算法的目标选择逻辑
```python
if current_direction == Direction.UP:
    # 1. 优先选择上方的 up_targets
    upper_up = [f for f in up_targets if f > current_floor]
    if upper_up:
        return min(upper_up)

    # 2. 选择上方的 down_targets（准备转向）
    upper_down = [f for f in down_targets if f > current_floor]
    if upper_down:
        return max(upper_down)  # 去最高的，到达后转向

    # 3. 转向向下，选择下方的 down_targets
    lower_down = [f for f in down_targets if f < current_floor]
    if lower_down:
        return max(lower_down)

    # 4. 最后尝试下方的 up_targets
    lower_up = [f for f in up_targets if f < current_floor]
    if lower_up:
        return min(lower_up)
```

#### 问题3：提升到58/74 (78%)，但电梯内乘客目的地获取失败
**现象**：
```
[DEBUG] 电梯内有 8 个乘客
[DEBUG] 电梯内乘客目的地: [None, None, None, None, None, None, None, None]
```

**原因**：`elevator.passenger_destinations` 字典为空（系统未填充）

**修复**：在controller中维护乘客信息字典
```python
class LookV2Controller:
    def __init__(self):
        self.passenger_destinations: dict[int, int] = {}

    def on_passenger_call(self, passenger, floor, direction):
        # 记录乘客目的地
        self.passenger_destinations[passenger.id] = passenger.destination

    def on_passenger_alight(self, elevator, passenger, floor):
        # 清除已下梯乘客
        if passenger.id in self.passenger_destinations:
            del self.passenger_destinations[passenger.id]
```

---

## 三、最终性能

### 3.1 测试环境
- **流量文件**: `random.json` (74个乘客)
- **电梯配置**: 2部电梯，6层楼，容量10人
- **时间限制**: 200 ticks

### 3.2 性能数据

| 指标 | LOOK V2 | Optimal LOOK (第3轮) | Bus Example |
|------|---------|---------------------|-------------|
| **完成率** | 78% (58/74) | 100% (74/74) | 100% (74/74) |
| **平均等待** | 36.3 ticks | 42.73 ticks | ~20 ticks |
| **P95等待** | 88.0 ticks | 129 ticks | ~30 ticks |
| **平均系统时间** | 54.2 ticks | - | - |
| **P95系统时间** | 99.0 ticks | - | - |
| **代码行数** | 240行 | 1000+行 | 78行 |

### 3.3 性能分析

**优点**：
1. ✅ **代码简洁** - 只有240行，易于理解和维护
2. ✅ **等待时间优秀** - 平均36.3ticks，比optimal_look更好
3. ✅ **无复杂逻辑** - 没有任务队列、合并、多阶段排序等

**不足**：
1. ❌ **完成率78%** - 16个乘客未在200 ticks内完成
2. ❌ **无电梯分配** - 两个电梯可能服务同一区域，造成资源浪费
3. ❌ **无负载均衡** - 没有考虑电梯负载

---

## 四、可视化版本

### 4.1 创建visual版本

**文件**: `elevator_saga/client_examples/visual_look_v2_example.py`

**特性**：
- 继承自`LookV2Controller`
- 自动记录每个tick的状态快照
- 生成JSON文件供Web可视化播放
- 包含算法特有信息（扫描方向、跟踪乘客数）

### 4.2 修复播放速度问题

**问题**：可视化播放时，2秒才跳一个tick

**原因**：每个tick记录了多次（tick_start + tick_end），播放器遍历每条记录都等待500ms

**修复**：
```python
# ❌ 旧代码：每个tick记录两次
def on_event_execute_start(...):
    if self.record and tick > 0:
        self._record_state(tick, events, "tick_start")

def on_event_execute_end(...):
    if self.record:
        self._record_state(tick, events, "tick_end")

# ✅ 新代码：每个tick只记录一次
def on_event_execute_start(...):
    super().on_event_execute_start(tick, events, elevators, floors)
    # 不记录

def on_event_execute_end(...):
    super().on_event_execute_end(tick, events, elevators, floors)
    if self.record:
        self._record_state(tick, events, "tick")  # 只在tick结束时记录一次
```

**结果**：播放速度修复，1倍速时每秒播放2个tick（500ms/tick）

---

## 五、核心技术要点

### 5.1 LOOK算法的正确理解

**扫描周期示例**（电梯当前在F2，向上）：
```
UP阶段：   F2 → F3 → F4 → F5 (到顶)
转向
DOWN阶段： F5 → F4 → F3 → F2 → F1 → F0 (到底)
转向
下一个UP阶段：F0 → F1 → ...
```

**关键约束**：
- 在UP阶段，只能接需要向上的乘客（`up_queue`）
- 在DOWN阶段，只能接需要向下的乘客（`down_queue`）
- 电梯的移动方向决定了哪些乘客可以上梯

### 5.2 方向匹配的硬约束

系统在`_process_passenger_in`中的逻辑（simulator.py:303-310）：
```python
if elevator.target_floor_direction == Direction.UP:
    passengers_to_board.extend(floor.up_queue[:available_capacity])
elif elevator.target_floor_direction == Direction.DOWN:
    passengers_to_board.extend(floor.down_queue[:available_capacity])
```

**这意味着**：
- 必须确保电梯到达pickup楼层时方向正确
- 不能依赖系统"自动处理"方向匹配
- 我们必须主动控制电梯的移动顺序

### 5.3 实时决策 vs 任务队列

| 特性 | 实时决策 (LOOK V2) | 任务队列 (Optimal LOOK) |
|------|-------------------|----------------------|
| **复杂度** | 低（每次停靠时计算） | 高（维护完整路径） |
| **适应性** | 强（动态响应变化） | 弱（需要重新规划） |
| **全局优化** | 局部最优 | 可以全局优化 |
| **调试难度** | 容易 | 困难 |
| **代码量** | 少 | 多 |

**结论**：对于简单场景，实时决策更适合；对于复杂优化，任务队列更有优势。

---

## 六、未完成工作与改进方向

### 6.1 完成率问题分析

**可能原因**：
1. **时间限制** - 200 ticks可能不够（需验证）
2. **电梯分配策略缺失** - 两个电梯无协作，可能都去接同一批乘客
3. **低效移动** - 可能存在不必要的空跑

**验证方法**：
- 查看日志，分析哪16个乘客未完成
- 检查是否是时间耗尽（tick 200时还有乘客等待）
- 观察电梯是否有重复服务同一区域

### 6.2 改进方向

**短期优化**（保持简洁性）:
1. **简单负载均衡** - 为每个电梯分配服务区域（如E0服务F0-F2，E1服务F3-F5）
2. **优化目标选择** - 优先选择等待时间长的楼层
3. **减少空跑** - 判断是否有乘客可接再移动

**长期优化**（可能增加复杂度）:
1. **预测性调度** - 提前预判乘客流向
2. **动态区域分配** - 根据实时负载调整服务区域
3. **协作机制** - 电梯间通信，避免重复服务

---

## 七、关键代码位置

### look_v2_example.py
- `on_elevator_stopped` (49-103行) - 核心决策逻辑
- `_select_next_floor_look` (105-172行) - LOOK算法目标选择
- `on_passenger_call` (43-47行) - 记录乘客信息
- `on_passenger_alight` (205-211行) - 清除乘客信息

### visual_look_v2_example.py
- `on_event_execute_end` (57-63行) - 状态记录（每tick一次）
- `_record_state` (65-141行) - 状态快照生成
- `_save_recording` (148-189行) - 保存记录文件

---

## 八、经验教训

### 8.1 做得好的地方

1. ✅ **遵循简洁性原则** - 从上一轮的复杂中吸取教训
2. ✅ **逐步修复问题** - 每次修复一个bug，验证效果
3. ✅ **深入理解约束** - 正确理解方向匹配的硬约束
4. ✅ **参考成功案例** - 学习bus_example的简洁性

### 8.2 需要改进的地方

1. ⚠️ **完成率未达标** - 78% < 100%目标
2. ⚠️ **缺少性能对比** - 应该与bus_example直接对比
3. ⚠️ **未分析未完成乘客** - 应该深入分析为什么有16个未完成

### 8.3 核心原则

1. **简洁第一** - 复杂度是bug的温床
2. **分阶段开发** - 先保证work，再优化性能
3. **理解约束** - 深入理解系统的硬约束
4. **持续验证** - 每个阶段都要验证完成率

---

## 九、下次开发计划

### 9.1 目标

- **必须**：完成率达到100% (random和lunch_rush)
- **可选**：平均等待时间 < 40 ticks
- **可选**：P95等待时间 < 90 ticks

### 9.2 步骤

1. **分析未完成乘客**
   - [ ] 运行debug模式，查看哪些乘客未完成
   - [ ] 分析原因：时间不够？算法bug？电梯冲突？

2. **添加简单负载均衡**
   - [ ] 在`on_passenger_call`时选择最近的**空闲**电梯
   - [ ] 避免两个电梯都去服务同一个乘客

3. **优化目标选择**
   - [ ] 考虑等待时间，优先服务等待久的楼层
   - [ ] 减少不必要的空跑

4. **测试验证**
   - [ ] 测试random流量，确保100%完成
   - [ ] 测试lunch_rush流量，确保100%完成
   - [ ] 记录性能指标，与bus_example对比

---

## 十、文件清单

### 本轮创建的文件

1. **look_v2_example.py** (240行)
   - 简洁的实时决策LOOK算法
   - 完成率78%，平均等待36.3 ticks

2. **visual_look_v2_example.py** (200行)
   - 可视化版本，生成记录文件
   - 修复了播放速度问题

3. **2025-10-16-2-look_v2_development_summary.md** (本文档)
   - 完整的开发总结
   - 问题分析和解决方案
   - 下次开发计划

### 相关参考文件

- `2025-10-16-1-optimal_look_debugging_log.md` - 上一轮问题总结
- `bus_example.py` - 简洁性参考
- `optimal_look_example.py` - 复杂度对比
- `simple_look_example.py` - 另一个简化尝试（失败）

---

## 十一、总结

### 主要成果

1. ✅ 成功创建了**简洁可靠**的LOOK V2算法（240行 vs 1000+行）
2. ✅ 深入理解了**方向匹配约束**，这是LOOK算法的核心
3. ✅ 验证了**实时决策**策略的可行性
4. ✅ 创建了**可视化版本**，方便调试和展示

### 性能表现

- **完成率**: 78% (58/74) - 未达100%目标，但比之前的52%有显著提升
- **等待时间**: 平均36.3 ticks - **优于**optimal_look的42.73 ticks
- **代码复杂度**: 240行 - **远低于**optimal_look的1000+行

### 关键发现

1. **简洁性 > 复杂优化** - 简单的算法更容易正确实现
2. **方向匹配是硬约束** - 必须精确控制电梯移动顺序
3. **实时决策可行** - 不需要提前规划完整路径
4. **passenger_destinations需要手动维护** - 系统不会自动填充

### 遗留问题

1. ❌ 完成率78% < 100%目标 - 需要分析并修复
2. ⚠️ 无电梯协作机制 - 可能造成资源浪费
3. ⚠️ 未测试lunch_rush - 只测试了random流量

---

**总结完成时间**: 2025-10-16
**下次开发重点**: 分析未完成乘客原因，添加简单负载均衡，达到100%完成率

---

**附录：快速启动**

```bash
# 运行LOOK V2算法（非可视化）
python elevator_saga/client_examples/look_v2_example.py

# 运行可视化版本（生成记录文件）
python elevator_saga/client_examples/visual_look_v2_example.py

# 启动可视化服务器
python -m elevator_saga.visualization.web_server
# 然后访问 http://localhost:8080
```
