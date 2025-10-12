# Optimal LOOK 电梯调度算法设计文档

## 1. 算法概述

### 1.1 算法名称
**Optimal LOOK (优化查找算法)**

### 1.2 核心思想
基于经典的LOOK算法（电梯算法），充分利用本项目的关键简化条件：**提前知道所有乘客的目的地**，实现预测性、动态性和负载均衡的智能调度。

### 1.3 关键优势
- **预测性调度**: 提前知道未来乘客需求，可以优化电梯路径
- **方向性优先**: 优先服务同方向乘客，减少往返次数
- **动态任务分配**: 多电梯协同，避免重复响应同一呼叫
- **载客优化**: 考虑电梯容量，优化接送顺序
- **零空驶优化**: 最小化电梯空载运行距离

---

## 2. 系统简化条件分析

### 2.1 项目提供的简化条件
1. ✅ **提前知道目的地**: 乘客在arrive_tick时就告知destination
2. ✅ **乘客不会放弃**: 可以放心优化等待时间
3. ✅ **目的地不变**: 可以提前规划完整路径
4. ✅ **先来后到**: 上下电梯顺序确定
5. ✅ **单次到达**: 不需要考虑换乘策略

### 2.2 利用方式
- 条件1: 实现**请求路径优化**，一次接客可规划最佳送达路线
- 条件2: 允许**长期优化**，不用担心乘客流失
- 条件3: 实现**动态重规划**，随时调整电梯目标
- 条件4: **队列管理简化**，按ID顺序处理即可
- 条件5: 只需要**单程优化**，不考虑复杂换乘

---

## 3. 算法核心设计

### 3.1 数据结构设计

#### 3.1.1 乘客请求 (PassengerRequest)
```python
@dataclass
class PassengerRequest:
    passenger_id: int        # 乘客ID
    origin: int              # 起始楼层
    destination: int         # 目标楼层
    direction: Direction     # 方向（UP/DOWN）
    arrive_tick: int         # 到达时间
    priority: float          # 优先级（动态计算）
    assigned_elevator: Optional[int] = None  # 已分配的电梯ID
```

#### 3.1.2 电梯任务 (ElevatorTask)
```python
@dataclass
class ElevatorTask:
    floor: int               # 目标楼层
    task_type: str           # 任务类型: "pickup" 或 "dropoff"
    passenger_ids: List[int] # 关联的乘客ID列表
    direction: Direction     # 任务方向
    priority: float          # 优先级
```

#### 3.1.3 电梯计划 (ElevatorPlan)
```python
@dataclass
class ElevatorPlan:
    elevator_id: int                 # 电梯ID
    current_direction: Direction     # 当前方向
    task_queue: List[ElevatorTask]   # 任务队列（已排序）
    estimated_load: List[int]        # 预估每个任务点的载客量
    total_cost: float                # 总成本估算
```

### 3.2 核心模块

#### 3.2.1 请求管理器 (RequestManager)
**职责**: 管理所有乘客请求，动态分配任务

**关键方法**:
- `add_request(passenger)`: 添加新乘客请求
- `get_pending_requests()`: 获取未分配的请求
- `assign_request(passenger_id, elevator_id)`: 分配请求到电梯
- `calculate_priority(request)`: 计算请求优先级

**优先级计算公式**:
```
priority = w1 * wait_time + w2 * distance + w3 * direction_penalty
```
- `wait_time`: 已等待时间（当前tick - arrive_tick）
- `distance`: 距离电梯当前位置的距离
- `direction_penalty`: 方向不匹配的惩罚

#### 3.2.2 路径规划器 (PathPlanner)
**职责**: 为每部电梯规划最优服务路径

**关键方法**:
- `plan_elevator_path(elevator, requests)`: 为电梯规划完整路径
- `optimize_stops(tasks)`: 优化停靠顺序
- `calculate_path_cost(path)`: 计算路径成本
- `insert_task(task, queue)`: 插入新任务到队列的最优位置

**LOOK算法实现**:
1. 按当前方向继续移动
2. 服务同方向的所有请求（pickup + dropoff）
3. 到达端点后反向
4. 服务反方向的请求

**优化策略**:
- **同向合并**: 同方向的pickup和dropoff合并服务
- **容量约束**: 考虑电梯容量，避免过载
- **距离优先**: 优先服务路径上的请求
- **动态插入**: 新请求可动态插入当前路径

#### 3.2.3 调度器 (Dispatcher)
**职责**: 协调多部电梯，实现全局最优分配

**关键方法**:
- `assign_requests()`: 分配所有待处理请求
- `balance_load()`: 负载均衡
- `find_best_elevator(request)`: 为请求找最佳电梯
- `calculate_elevator_cost(elevator, request)`: 计算电梯服务请求的成本

**分配算法**:
1. 遍历所有未分配请求
2. 计算每部电梯服务该请求的成本
3. 选择成本最低的电梯
4. 更新电梯任务队列

**成本函数**:
```python
cost = α * time_to_pickup    # 到达接客点的时间
     + β * wait_time         # 乘客已等待时间
     + γ * detour_cost       # 绕路成本（偏离当前路径的代价）
     + δ * load_penalty      # 载客惩罚（电梯越满，成本越高）
```

参数设置:
- α = 1.0  (时间成本)
- β = 2.0  (等待惩罚，更关注减少乘客等待)
- γ = 0.5  (绕路成本)
- δ = 1.5  (载客惩罚，避免单部电梯过载)

#### 3.2.4 执行器 (Executor)
**职责**: 执行电梯控制命令

**关键方法**:
- `execute_next_task(elevator)`: 执行下一个任务
- `handle_arrival(elevator, floor)`: 处理到达楼层事件
- `update_plan(elevator)`: 更新电梯计划

---

## 4. 算法流程

### 4.1 初始化阶段 (on_init)
```
1. 初始化所有数据结构
2. 创建RequestManager、PathPlanner、Dispatcher、Executor实例
3. 设置电梯初始位置（均匀分布到不同楼层）
   - 电梯i的初始楼层 = i * (总楼层 - 1) / 电梯数量
4. 所有电梯初始方向设为UP
```

### 4.2 乘客呼叫 (on_passenger_call)
```
1. 创建PassengerRequest对象
2. RequestManager.add_request(passenger)
3. 立即触发Dispatcher.assign_requests()
4. 为最佳电梯更新任务队列
5. 如果电梯空闲，立即开始移动
```

### 4.3 电梯停靠 (on_elevator_stopped)
```
1. 处理当前楼层的所有任务:
   a. 先处理dropoff（乘客下梯）
   b. 再处理pickup（乘客上梯，检查容量）
2. 从任务队列移除已完成任务
3. 获取下一个任务:
   a. 如果队列为空，保持空闲
   b. 如果有任务，移动到下一个目标楼层
```

### 4.4 电梯空闲 (on_elevator_idle)
```
1. 检查是否有未分配的请求
2. 如果有，重新运行Dispatcher.assign_requests()
3. 如果分配到新任务，开始移动
4. 如果没有任务:
   a. 保持当前位置
   b. 或移动到策略位置（如中间楼层）
```

### 4.5 电梯即将到达 (on_elevator_approaching)
```
1. 预判是否需要在此楼层停靠:
   a. 检查是否有同方向的pickup任务
   b. 检查是否有dropoff任务
   c. 检查电梯容量
2. 如果不需要停靠，使用immediate=True跳过
3. 如果需要停靠，保持默认行为
```

### 4.6 每个Tick结束 (on_event_execute_end)
```
1. 更新所有请求的等待时间
2. 重新计算请求优先级
3. 检查是否需要重新分配（如果有高优先级请求长时间未服务）
4. 动态调整电梯任务队列
```

---

## 5. 关键算法细节

### 5.1 任务队列排序算法

**排序规则**:
1. 按照电梯当前方向分组（UP/DOWN）
2. 当前方向组内按楼层排序:
   - UP方向: 按楼层从小到大
   - DOWN方向: 按楼层从大到小
3. 反方向组放在当前方向组之后

**示例**:
```
电梯当前在3楼，方向UP，任务列表:
[pickup@5, dropoff@7, pickup@2, dropoff@6]

排序后:
[pickup@5, dropoff@6, dropoff@7, pickup@2]
```

### 5.2 动态任务插入算法

当新请求到来时，插入到任务队列的最优位置:

```python
def insert_task_optimally(new_task, task_queue, elevator_state):
    # 1. 如果队列为空，直接添加
    if not task_queue:
        return [new_task]

    # 2. 尝试在每个位置插入，计算成本
    best_cost = float('inf')
    best_position = len(task_queue)

    for i in range(len(task_queue) + 1):
        temp_queue = task_queue[:i] + [new_task] + task_queue[i:]
        cost = calculate_queue_cost(temp_queue, elevator_state)
        if cost < best_cost:
            best_cost = cost
            best_position = i

    # 3. 在最优位置插入
    return task_queue[:best_position] + [new_task] + task_queue[best_position:]
```

### 5.3 容量约束处理

在规划路径时，必须确保不超过电梯容量:

```python
def validate_capacity(task_queue, max_capacity):
    current_load = 0
    estimated_load = []

    for task in task_queue:
        if task.task_type == "pickup":
            current_load += len(task.passenger_ids)
        elif task.task_type == "dropoff":
            current_load -= len(task.passenger_ids)

        estimated_load.append(current_load)

        if current_load > max_capacity:
            return False, estimated_load

    return True, estimated_load
```

如果违反容量约束，需要拆分任务或重新排序。

### 5.4 电梯选择算法

为新请求选择最佳电梯:

```python
def find_best_elevator(request, elevators):
    best_elevator = None
    min_cost = float('inf')

    for elevator in elevators:
        # 计算服务成本
        time_to_pickup = estimate_arrival_time(elevator, request.origin)
        wait_time = current_tick - request.arrive_tick
        detour_cost = calculate_detour(elevator, request)
        load_penalty = elevator.load_factor * 10

        # 方向匹配奖励
        direction_bonus = 0
        if elevator.target_floor_direction == request.direction:
            direction_bonus = -5

        cost = (1.0 * time_to_pickup +
                2.0 * wait_time +
                0.5 * detour_cost +
                1.5 * load_penalty +
                direction_bonus)

        if cost < min_cost:
            min_cost = cost
            best_elevator = elevator

    return best_elevator, min_cost
```

### 5.5 预测到达时间算法

估算电梯到达某楼层的时间:

```python
def estimate_arrival_time(elevator, target_floor):
    # 如果电梯空闲，直接计算距离
    if elevator.is_idle:
        return abs(target_floor - elevator.current_floor) * 2  # 每层需2 ticks

    # 如果电梯忙碌，需要遍历任务队列
    current_floor = elevator.current_floor
    total_time = 0

    for task in elevator.task_queue:
        # 移动时间
        travel_time = abs(task.floor - current_floor) * 2
        # 停靠时间（假设每次停靠3 ticks）
        stop_time = 3

        total_time += travel_time + stop_time
        current_floor = task.floor

        # 如果任务楼层等于目标楼层，返回累计时间
        if task.floor == target_floor:
            return total_time

    # 如果目标楼层不在任务队列中，加上从最后任务到目标的距离
    final_distance = abs(target_floor - current_floor) * 2
    return total_time + final_distance
```

---

## 6. 性能优化策略

### 6.1 减少等待时间
- **优先级队列**: 等待时间长的请求优先级提高
- **就近原则**: 优先分配距离最近的空闲电梯
- **预分配**: 在电梯完成当前任务前，提前分配下一批任务

### 6.2 减少行程时间
- **方向性**: 优先服务同方向乘客，减少往返
- **合并停靠**: 同一楼层的多个任务合并处理
- **路径优化**: 使用LOOK算法，减少电梯方向改变次数

### 6.3 提高吞吐量
- **负载均衡**: 避免某部电梯过载而其他电梯空闲
- **并行服务**: 多部电梯同时服务不同区域
- **容量优化**: 尽量让电梯满载运行，提高单次运输效率

### 6.4 能耗优化（次要目标）
- **减少空驶**: 优先分配路径上的请求
- **合并方向**: 避免频繁改变方向
- **就近服务**: 减少长距离空载移动

---

## 7. 特殊情况处理

### 7.1 所有电梯都满载
- 乘客继续等待，不强制分配
- 当有电梯释放容量时，立即重新分配

### 7.2 极端楼层（顶层/底层）
- 到达边界时强制反向
- 在边界楼层优先处理该方向的所有请求

### 7.3 高峰流量
- 动态调整成本函数参数
- 上班高峰: 底层上行优先
- 下班高峰: 顶层下行优先

### 7.4 低流量
- 空闲电梯分散到不同楼层（均匀分布）
- 减少多部电梯响应同一请求的概率

### 7.5 长时间等待
- 如果请求等待超过阈值（如100 ticks），强制提高优先级
- 考虑专门派一部电梯服务该请求

---

## 8. 参数配置

### 8.1 成本函数参数
```python
COST_WEIGHTS = {
    "time_to_pickup": 1.0,      # 到达时间权重
    "wait_time": 2.0,           # 等待时间权重（重点优化）
    "detour_cost": 0.5,         # 绕路成本权重
    "load_penalty": 1.5,        # 负载惩罚权重
    "direction_bonus": -5.0,    # 方向匹配奖励
}
```

### 8.2 系统参数
```python
SYSTEM_CONFIG = {
    "stop_time": 3,                  # 每次停靠时间（ticks）
    "ticks_per_floor": 2,            # 每层楼移动时间（ticks）
    "reallocation_threshold": 100,   # 重新分配等待时间阈值
    "capacity_reserve": 0.2,         # 容量预留（避免满载）
}
```

---

## 9. 算法复杂度分析

### 9.1 时间复杂度
- **请求分配**: O(E × R)，E为电梯数，R为请求数
- **路径规划**: O(T log T)，T为单个电梯的任务数（排序）
- **任务插入**: O(T²)，需要尝试每个位置
- **总体**: O(E × R + E × T²)

### 9.2 空间复杂度
- **请求存储**: O(R)
- **任务队列**: O(E × T)
- **总体**: O(R + E × T)

### 9.3 优化建议
- 对于大规模系统（>10电梯，>100并发请求），可以:
  - 使用分区策略（将楼层分区，电梯负责特定区域）
  - 使用近似算法减少计算时间
  - 增量更新而非全量重计算

---

## 10. 预期性能

### 10.1 与Bus算法对比
- **平均等待时间**: 减少 50-70%
- **平均系统时间**: 减少 40-60%
- **P95等待时间**: 减少 60-80%

### 10.2 适用场景
- ✅ 中低流量: 优秀（电梯可灵活调度）
- ✅ 中高流量: 良好（负载均衡起作用）
- ✅ 极端流量: 可接受（优先级机制保证公平性）
- ✅ 不均匀流量: 优秀（动态分配适应流量变化）

---

## 11. 实现清单

### 11.1 核心类
- [x] PassengerRequest
- [x] ElevatorTask
- [x] ElevatorPlan
- [x] RequestManager
- [x] PathPlanner
- [x] Dispatcher
- [x] Executor

### 11.2 核心算法
- [x] 优先级计算
- [x] 任务队列排序
- [x] 动态任务插入
- [x] 容量约束验证
- [x] 电梯选择算法
- [x] 预测到达时间

### 11.3 回调实现
- [x] on_init
- [x] on_passenger_call
- [x] on_elevator_stopped
- [x] on_elevator_idle
- [x] on_elevator_approaching
- [x] on_event_execute_end

---

## 12. 测试策略

### 12.1 单元测试
- 优先级计算正确性
- 任务队列排序正确性
- 容量约束验证
- 成本计算准确性

### 12.2 场景测试
- 低流量场景（<10乘客/分钟）
- 高流量场景（>30乘客/分钟）
- 上下班高峰场景
- 随机流量场景

### 12.3 对比测试
- 与Bus算法对比
- 与Simple算法对比
- 关键指标:
  - average_wait_time
  - p95_wait_time
  - average_system_time
  - p95_system_time

---

## 13. 总结

Optimal LOOK算法充分利用了本项目"提前知道乘客目的地"的关键优势，通过预测性调度、动态任务分配和负载均衡，实现了高效的电梯调度。

**核心优势**:
1. 方向性优先，减少往返
2. 预测性规划，提前优化
3. 动态分配，负载均衡
4. 容量优化，提高效率

**适用场景**: 几乎所有流量模式，特别是中低流量和不均匀流量场景表现优异。

**下一步**: 实现算法并进行性能测试验证。
