#!/usr/bin/env python3
"""
Optimal LOOK 电梯调度算法
基于LOOK算法，充分利用"提前知道乘客目的地"的优势，实现预测性、动态性和负载均衡的智能调度
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

from elevator_saga.client.base_controller import ElevatorController
from elevator_saga.client.proxy_models import ProxyElevator, ProxyFloor, ProxyPassenger
from elevator_saga.core.models import Direction, SimulationEvent


# ==================== 核心数据结构 ====================


@dataclass
class PassengerRequest:
    """乘客请求"""

    passenger_id: int
    origin: int
    destination: int
    direction: Direction
    arrive_tick: int
    priority: float = 0.0
    assigned_elevator: Optional[int] = None


@dataclass
class ElevatorTask:
    """电梯任务"""

    floor: int
    task_type: str  # "pickup" 或 "dropoff"
    passenger_ids: List[int]
    direction: Direction
    priority: float = 0.0

    def __repr__(self) -> str:
        return f"Task({self.task_type}@F{self.floor}, {len(self.passenger_ids)}p, dir={self.direction.value})"


@dataclass
class ElevatorPlan:
    """电梯计划"""

    elevator_id: int
    current_direction: Direction
    task_queue: List[ElevatorTask] = field(default_factory=list)
    estimated_load: List[int] = field(default_factory=list)
    total_cost: float = 0.0


# ==================== 配置参数 ====================


class Config:
    """算法配置参数"""

    # 成本函数权重
    WEIGHT_TIME_TO_PICKUP = 1.0
    WEIGHT_WAIT_TIME = 2.0
    WEIGHT_DETOUR = 0.5
    WEIGHT_LOAD = 1.5
    BONUS_DIRECTION = -5.0

    # 系统参数
    STOP_TIME = 3  # 每次停靠时间（ticks）
    TICKS_PER_FLOOR = 2  # 每层楼移动时间（ticks）
    REALLOCATION_THRESHOLD = 100  # 重新分配等待时间阈值
    CAPACITY_RESERVE = 0.2  # 容量预留比例


# ==================== 请求管理器 ====================


class RequestManager:
    """管理所有乘客请求"""

    def __init__(self, controller: "OptimalLookController"):
        self.controller = controller
        self.requests: Dict[int, PassengerRequest] = {}  # passenger_id -> request

    def add_request(self, passenger: ProxyPassenger, arrive_tick: int) -> None:
        """添加新乘客请求"""
        # 确定方向
        if passenger.destination > passenger.origin:
            direction = Direction.UP
        elif passenger.destination < passenger.origin:
            direction = Direction.DOWN
        else:
            direction = Direction.STOPPED

        request = PassengerRequest(
            passenger_id=passenger.id,
            origin=passenger.origin,
            destination=passenger.destination,
            direction=direction,
            arrive_tick=arrive_tick,
        )

        self.requests[passenger.id] = request

    def get_pending_requests(self) -> List[PassengerRequest]:
        """获取未分配的请求"""
        return [req for req in self.requests.values() if req.assigned_elevator is None]

    def assign_request(self, passenger_id: int, elevator_id: int) -> None:
        """分配请求到电梯"""
        if passenger_id in self.requests:
            self.requests[passenger_id].assigned_elevator = elevator_id

    def remove_request(self, passenger_id: int) -> None:
        """移除请求（乘客已送达）"""
        if passenger_id in self.requests:
            del self.requests[passenger_id]

    def calculate_priority(self, request: PassengerRequest, current_tick: int) -> float:
        """计算请求优先级（值越大优先级越高）"""
        wait_time = current_tick - request.arrive_tick
        # 优先级随等待时间线性增长
        priority = wait_time * 1.0
        return priority

    def update_priorities(self, current_tick: int) -> None:
        """更新所有请求的优先级"""
        for request in self.requests.values():
            request.priority = self.calculate_priority(request, current_tick)


# ==================== 路径规划器 ====================


class PathPlanner:
    """为电梯规划最优服务路径"""

    def __init__(self, controller: "OptimalLookController"):
        self.controller = controller

    def plan_elevator_path(
        self, elevator: ProxyElevator, new_requests: List[PassengerRequest]
    ) -> ElevatorPlan:
        """为电梯规划完整路径"""
        plan = ElevatorPlan(
            elevator_id=elevator.id, current_direction=elevator.target_floor_direction
        )

        # 1. 收集所有任务（现有乘客的dropoff + 新请求的pickup + dropoff）
        all_tasks = []

        # 现有乘客的dropoff任务
        for passenger_id in elevator.passengers:
            destination = elevator.passenger_destinations.get(passenger_id)
            if destination is not None:
                direction = Direction.UP if destination > elevator.current_floor else Direction.DOWN
                task = ElevatorTask(
                    floor=destination,
                    task_type="dropoff",
                    passenger_ids=[passenger_id],
                    direction=direction,
                )
                all_tasks.append(task)

        # 新请求的pickup和dropoff任务
        for request in new_requests:
            # Pickup任务
            pickup_task = ElevatorTask(
                floor=request.origin,
                task_type="pickup",
                passenger_ids=[request.passenger_id],
                direction=request.direction,
            )
            all_tasks.append(pickup_task)

            # Dropoff任务
            dropoff_task = ElevatorTask(
                floor=request.destination,
                task_type="dropoff",
                passenger_ids=[request.passenger_id],
                direction=request.direction,
            )
            all_tasks.append(dropoff_task)

        # 2. 按LOOK算法排序任务
        sorted_tasks = self.sort_tasks_look(all_tasks, elevator)

        # 3. 合并相同楼层的任务
        merged_tasks = self.merge_tasks(sorted_tasks)

        # 4. 验证容量约束
        valid, estimated_load = self.validate_capacity(merged_tasks, elevator)
        if not valid:
            # 如果违反容量约束，需要调整（简化：移除部分pickup任务）
            merged_tasks, estimated_load = self.adjust_for_capacity(merged_tasks, elevator)

        plan.task_queue = merged_tasks
        plan.estimated_load = estimated_load
        plan.total_cost = self.calculate_path_cost(merged_tasks, elevator)

        return plan

    def sort_tasks_look(self, tasks: List[ElevatorTask], elevator: ProxyElevator) -> List[ElevatorTask]:
        """使用LOOK算法排序任务"""
        if not tasks:
            return []

        current_floor = elevator.current_floor
        current_direction = elevator.target_floor_direction

        # 如果电梯停止，选择最近任务的方向
        if current_direction == Direction.STOPPED:
            if tasks:
                nearest_task = min(tasks, key=lambda t: abs(t.floor - current_floor))
                current_direction = (
                    Direction.UP if nearest_task.floor >= current_floor else Direction.DOWN
                )

        # 分组：当前方向的任务 和 反方向的任务
        same_direction_tasks = []
        opposite_direction_tasks = []

        for task in tasks:
            if current_direction == Direction.UP and task.floor >= current_floor:
                same_direction_tasks.append(task)
            elif current_direction == Direction.DOWN and task.floor <= current_floor:
                same_direction_tasks.append(task)
            else:
                opposite_direction_tasks.append(task)

        # 当前方向：按楼层排序
        if current_direction == Direction.UP:
            same_direction_tasks.sort(key=lambda t: t.floor)
            opposite_direction_tasks.sort(key=lambda t: t.floor, reverse=True)
        else:
            same_direction_tasks.sort(key=lambda t: t.floor, reverse=True)
            opposite_direction_tasks.sort(key=lambda t: t.floor)

        return same_direction_tasks + opposite_direction_tasks

    def merge_tasks(self, tasks: List[ElevatorTask]) -> List[ElevatorTask]:
        """合并相同楼层的任务"""
        if not tasks:
            return []

        merged = []
        floor_tasks: Dict[int, Dict[str, List[int]]] = {}

        # 按楼层分组
        for task in tasks:
            if task.floor not in floor_tasks:
                floor_tasks[task.floor] = {"pickup": [], "dropoff": []}
            floor_tasks[task.floor][task.task_type].extend(task.passenger_ids)

        # 按照原始任务顺序创建合并任务
        seen_floors = []
        for task in tasks:
            if task.floor not in seen_floors:
                seen_floors.append(task.floor)
                # 先dropoff，再pickup
                if floor_tasks[task.floor]["dropoff"]:
                    merged.append(
                        ElevatorTask(
                            floor=task.floor,
                            task_type="dropoff",
                            passenger_ids=floor_tasks[task.floor]["dropoff"],
                            direction=task.direction,
                        )
                    )
                if floor_tasks[task.floor]["pickup"]:
                    merged.append(
                        ElevatorTask(
                            floor=task.floor,
                            task_type="pickup",
                            passenger_ids=floor_tasks[task.floor]["pickup"],
                            direction=task.direction,
                        )
                    )

        return merged

    def validate_capacity(self, tasks: List[ElevatorTask], elevator: ProxyElevator) -> Tuple[bool, List[int]]:
        """验证容量约束"""
        current_load = len(elevator.passengers)
        estimated_load = []
        max_capacity = elevator.max_capacity

        for task in tasks:
            if task.task_type == "pickup":
                current_load += len(task.passenger_ids)
            elif task.task_type == "dropoff":
                current_load -= len(task.passenger_ids)

            estimated_load.append(current_load)

            if current_load > max_capacity:
                return False, estimated_load

        return True, estimated_load

    def adjust_for_capacity(
        self, tasks: List[ElevatorTask], elevator: ProxyElevator
    ) -> Tuple[List[ElevatorTask], List[int]]:
        """调整任务以满足容量约束"""
        # 简化策略：移除最后的pickup任务直到满足容量
        adjusted_tasks = []
        current_load = len(elevator.passengers)
        estimated_load = []

        for task in tasks:
            if task.task_type == "pickup":
                new_load = current_load + len(task.passenger_ids)
                if new_load <= elevator.max_capacity:
                    adjusted_tasks.append(task)
                    current_load = new_load
                else:
                    # 部分接客或跳过
                    available = elevator.max_capacity - current_load
                    if available > 0:
                        partial_task = ElevatorTask(
                            floor=task.floor,
                            task_type="pickup",
                            passenger_ids=task.passenger_ids[:available],
                            direction=task.direction,
                        )
                        adjusted_tasks.append(partial_task)
                        current_load = elevator.max_capacity
            else:
                adjusted_tasks.append(task)
                current_load -= len(task.passenger_ids)

            estimated_load.append(current_load)

        return adjusted_tasks, estimated_load

    def calculate_path_cost(self, tasks: List[ElevatorTask], elevator: ProxyElevator) -> float:
        """计算路径总成本（总时间）"""
        if not tasks:
            return 0.0

        current_floor = elevator.current_floor
        total_time = 0.0

        for task in tasks:
            # 移动时间
            travel_time = abs(task.floor - current_floor) * Config.TICKS_PER_FLOOR
            # 停靠时间
            stop_time = Config.STOP_TIME

            total_time += travel_time + stop_time
            current_floor = task.floor

        return total_time


# ==================== 调度器 ====================


class Dispatcher:
    """协调多部电梯，实现全局最优分配"""

    def __init__(self, controller: "OptimalLookController"):
        self.controller = controller
        self.path_planner = controller.path_planner

    def assign_requests(
        self, elevators: List[ProxyElevator], pending_requests: List[PassengerRequest], current_tick: int
    ) -> None:
        """分配所有待处理请求"""
        if not pending_requests:
            return

        # 按优先级排序（高优先级优先分配）
        sorted_requests = sorted(pending_requests, key=lambda r: r.priority, reverse=True)

        for request in sorted_requests:
            # 为每个请求找到最佳电梯
            best_elevator, best_cost = self.find_best_elevator(request, elevators, current_tick)

            if best_elevator is not None:
                # 分配请求
                self.controller.request_manager.assign_request(request.passenger_id, best_elevator.id)
                # 更新电梯计划
                self.controller.executor.add_request_to_elevator(best_elevator, request)

    def find_best_elevator(
        self, request: PassengerRequest, elevators: List[ProxyElevator], current_tick: int
    ) -> Tuple[Optional[ProxyElevator], float]:
        """为请求找到最佳电梯"""
        best_elevator = None
        min_cost = float("inf")

        for elevator in elevators:
            cost = self.calculate_elevator_cost(elevator, request, current_tick)

            if cost < min_cost:
                min_cost = cost
                best_elevator = elevator

        return best_elevator, min_cost

    def calculate_elevator_cost(
        self, elevator: ProxyElevator, request: PassengerRequest, current_tick: int
    ) -> float:
        """计算电梯服务请求的成本"""
        # 1. 到达接客点的时间
        time_to_pickup = self.estimate_arrival_time(elevator, request.origin)

        # 2. 乘客已等待时间
        wait_time = current_tick - request.arrive_tick

        # 3. 绕路成本（偏离当前路径的代价）
        detour_cost = self.calculate_detour(elevator, request)

        # 4. 载客惩罚（电梯越满，成本越高）
        load_penalty = elevator.load_factor * 10

        # 5. 方向匹配奖励
        direction_bonus = 0.0
        if elevator.target_floor_direction == request.direction:
            direction_bonus = Config.BONUS_DIRECTION

        # 总成本
        cost = (
            Config.WEIGHT_TIME_TO_PICKUP * time_to_pickup
            + Config.WEIGHT_WAIT_TIME * wait_time
            + Config.WEIGHT_DETOUR * detour_cost
            + Config.WEIGHT_LOAD * load_penalty
            + direction_bonus
        )

        return cost

    def estimate_arrival_time(self, elevator: ProxyElevator, target_floor: int) -> float:
        """估算电梯到达某楼层的时间"""
        # 如果电梯空闲，直接计算距离
        if elevator.is_idle:
            return abs(target_floor - elevator.current_floor) * Config.TICKS_PER_FLOOR

        # 如果电梯忙碌，需要遍历任务队列
        plan = self.controller.executor.elevator_plans.get(elevator.id)
        if plan is None or not plan.task_queue:
            return abs(target_floor - elevator.current_floor) * Config.TICKS_PER_FLOOR

        current_floor = elevator.current_floor
        total_time = 0.0

        for task in plan.task_queue:
            # 移动时间
            travel_time = abs(task.floor - current_floor) * Config.TICKS_PER_FLOOR
            # 停靠时间
            stop_time = Config.STOP_TIME

            total_time += travel_time + stop_time
            current_floor = task.floor

            # 如果任务楼层等于目标楼层，返回累计时间
            if task.floor == target_floor:
                return total_time

        # 如果目标楼层不在任务队列中，加上从最后任务到目标的距离
        final_distance = abs(target_floor - current_floor) * Config.TICKS_PER_FLOOR
        return total_time + final_distance

    def calculate_detour(self, elevator: ProxyElevator, request: PassengerRequest) -> float:
        """计算绕路成本"""
        # 简化：如果请求在电梯当前方向上，绕路成本为0
        current_floor = elevator.current_floor
        target_floor = elevator.target_floor
        request_floor = request.origin

        # 如果电梯空闲，无绕路成本
        if elevator.is_idle:
            return 0.0

        # 如果请求在电梯当前路径上
        if elevator.target_floor_direction == Direction.UP:
            if current_floor <= request_floor <= target_floor:
                return 0.0
        elif elevator.target_floor_direction == Direction.DOWN:
            if target_floor <= request_floor <= current_floor:
                return 0.0

        # 否则有绕路成本
        return abs(request_floor - current_floor)


# ==================== 执行器 ====================


class Executor:
    """执行电梯控制命令"""

    def __init__(self, controller: "OptimalLookController"):
        self.controller = controller
        self.elevator_plans: Dict[int, ElevatorPlan] = {}  # elevator_id -> plan

    def add_request_to_elevator(self, elevator: ProxyElevator, request: PassengerRequest) -> None:
        """添加请求到电梯的任务队列"""
        # 创建pickup和dropoff任务
        pickup_task = ElevatorTask(
            floor=request.origin,
            task_type="pickup",
            passenger_ids=[request.passenger_id],
            direction=request.direction,
        )
        dropoff_task = ElevatorTask(
            floor=request.destination,
            task_type="dropoff",
            passenger_ids=[request.passenger_id],
            direction=request.direction,
        )

        # 获取或创建电梯计划
        if elevator.id not in self.elevator_plans:
            self.elevator_plans[elevator.id] = ElevatorPlan(
                elevator_id=elevator.id, current_direction=elevator.target_floor_direction
            )

        plan = self.elevator_plans[elevator.id]

        # 智能插入任务，而不是重新排序整个队列
        # 这样可以保持电梯当前的运行方向和计划
        if not plan.task_queue:
            # 队列为空，直接添加
            plan.task_queue.append(pickup_task)
            plan.task_queue.append(dropoff_task)
        else:
            # 队列不为空，根据 LOOK 算法找到合适的插入位置
            self._insert_task_look(plan, pickup_task, elevator)
            self._insert_task_look(plan, dropoff_task, elevator)

        # 合并相同楼层的任务
        planner = self.controller.path_planner
        plan.task_queue = planner.merge_tasks(plan.task_queue)

        # 验证容量约束
        valid, estimated_load = planner.validate_capacity(plan.task_queue, elevator)
        if not valid:
            plan.task_queue, estimated_load = planner.adjust_for_capacity(plan.task_queue, elevator)
        plan.estimated_load = estimated_load

    def _insert_task_look(self, plan: ElevatorPlan, new_task: ElevatorTask, elevator: ProxyElevator) -> None:
        """根据 LOOK 算法将任务插入到合适的位置"""
        if not plan.task_queue:
            plan.task_queue.append(new_task)
            return

        current_floor = elevator.current_floor
        current_direction = elevator.target_floor_direction

        # 如果电梯停止，使用任务的方向
        if current_direction == Direction.STOPPED:
            current_direction = Direction.UP if new_task.floor >= current_floor else Direction.DOWN

        # 找到插入位置
        inserted = False
        for i, task in enumerate(plan.task_queue):
            # 如果新任务和现有任务在同一楼层，插入到该任务前面（稍后会合并）
            if task.floor == new_task.floor:
                plan.task_queue.insert(i, new_task)
                inserted = True
                break

            # LOOK 逻辑：按方向顺序插入
            if current_direction == Direction.UP:
                # 向上时，按楼层从低到高排序
                if new_task.floor < current_floor:
                    # 新任务在当前楼层下方，应该在反方向时处理
                    if task.floor < current_floor or task.floor > new_task.floor:
                        plan.task_queue.insert(i, new_task)
                        inserted = True
                        break
                else:
                    # 新任务在当前楼层上方，应该在当前方向时处理
                    if task.floor > new_task.floor and task.floor >= current_floor:
                        plan.task_queue.insert(i, new_task)
                        inserted = True
                        break
            else:  # Direction.DOWN
                # 向下时，按楼层从高到低排序
                if new_task.floor > current_floor:
                    # 新任务在当前楼层上方，应该在反方向时处理
                    if task.floor > current_floor or task.floor < new_task.floor:
                        plan.task_queue.insert(i, new_task)
                        inserted = True
                        break
                else:
                    # 新任务在当前楼层下方，应该在当前方向时处理
                    if task.floor < new_task.floor and task.floor <= current_floor:
                        plan.task_queue.insert(i, new_task)
                        inserted = True
                        break

        # 如果没有插入，添加到队列末尾
        if not inserted:
            plan.task_queue.append(new_task)

    def execute_next_task(self, elevator: ProxyElevator) -> None:
        """执行下一个任务"""
        plan = self.elevator_plans.get(elevator.id)
        if plan is None or not plan.task_queue:
            return

        # 找到第一个不是当前楼层的任务
        current_floor = elevator.current_floor
        next_floor = None
        for task in plan.task_queue:
            if task.floor != current_floor:
                next_floor = task.floor
                break

        # 移动到目标楼层（不使用 immediate=True，让系统先处理乘客）
        if next_floor is not None:
            elevator.go_to_floor(next_floor)

    def handle_arrival(self, elevator: ProxyElevator, floor: ProxyFloor) -> None:
        """处理到达楼层事件"""
        plan = self.elevator_plans.get(elevator.id)
        if plan is None or not plan.task_queue:
            return

        # 移除当前楼层的已完成任务
        current_floor = floor.floor
        plan.task_queue = [task for task in plan.task_queue if task.floor != current_floor]

    def get_next_floor(self, elevator: ProxyElevator) -> Optional[int]:
        """获取下一个目标楼层"""
        plan = self.elevator_plans.get(elevator.id)
        if plan is None or not plan.task_queue:
            return None
        return plan.task_queue[0].floor

    def has_tasks(self, elevator: ProxyElevator) -> bool:
        """检查电梯是否有待执行任务"""
        plan = self.elevator_plans.get(elevator.id)
        return plan is not None and len(plan.task_queue) > 0


# ==================== 主控制器 ====================


class OptimalLookController(ElevatorController):
    """Optimal LOOK 电梯调度控制器"""

    def __init__(self, server_url: str = "http://127.0.0.1:8000", debug: bool = False):
        super().__init__(server_url, debug)

        # 初始化模块
        self.request_manager = RequestManager(self)
        self.path_planner = PathPlanner(self)
        self.dispatcher = Dispatcher(self)
        self.executor = Executor(self)

        # 系统状态
        self.current_tick = 0
        self.max_floor = 0

    def on_init(self, elevators: List[ProxyElevator], floors: List[ProxyFloor]) -> None:
        """初始化"""
        print("[Optimal LOOK] 算法初始化")
        print(f"   管理 {len(elevators)} 部电梯")
        print(f"   服务 {len(floors)} 层楼")

        self.max_floor = len(floors) - 1

        # 初始化电梯计划
        for elevator in elevators:
            self.executor.elevator_plans[elevator.id] = ElevatorPlan(
                elevator_id=elevator.id, current_direction=Direction.UP
            )

        # 将电梯均匀分布到不同楼层
        for i, elevator in enumerate(elevators):
            target_floor = (i * self.max_floor) // len(elevators)
            elevator.go_to_floor(target_floor, immediate=True)
            print(f"   电梯 E{elevator.id} 移动到初始位置 F{target_floor}")

    def on_passenger_call(self, passenger: ProxyPassenger, floor: ProxyFloor, direction: str) -> None:
        """乘客呼叫"""
        print(f"[CALL] 乘客 {passenger.id} 在 F{passenger.origin} 呼叫，目标 F{passenger.destination}")

        # 添加请求
        self.request_manager.add_request(passenger, self.current_tick)

        # 立即分配
        pending_requests = self.request_manager.get_pending_requests()
        self.dispatcher.assign_requests(self.elevators, pending_requests, self.current_tick)

        # 启动空闲电梯
        for elevator in self.elevators:
            if elevator.is_idle and self.executor.has_tasks(elevator):
                self.executor.execute_next_task(elevator)

    def on_elevator_stopped(self, elevator: ProxyElevator, floor: ProxyFloor) -> None:
        """电梯停靠"""
        print(f"[STOP] 电梯 E{elevator.id} 停靠在 F{floor.floor}")

        # 设置下一个目标楼层（不使用 immediate=True，让系统先处理乘客）
        # 在 on_passenger_board/alight 中也会设置目标，但如果没有乘客上下梯，
        # 这里的设置会确保电梯继续移动
        plan = self.executor.elevator_plans.get(elevator.id)
        if plan and plan.task_queue:
            # 找到第一个不是当前楼层的任务
            next_floor = None
            for task in plan.task_queue:
                if task.floor != floor.floor:
                    next_floor = task.floor
                    break

            # 设置下一个目标（不使用 immediate，系统会在处理完乘客后移动）
            if next_floor is not None:
                elevator.go_to_floor(next_floor)

    def on_elevator_idle(self, elevator: ProxyElevator) -> None:
        """电梯空闲"""
        print(f"[IDLE] 电梯 E{elevator.id} 在 F{elevator.current_floor} 空闲")

        # 检查是否有待分配的请求
        pending_requests = self.request_manager.get_pending_requests()
        if pending_requests:
            self.dispatcher.assign_requests(self.elevators, pending_requests, self.current_tick)

        # 如果有新任务，开始执行
        if self.executor.has_tasks(elevator):
            self.executor.execute_next_task(elevator)

    def on_passenger_board(self, elevator: ProxyElevator, passenger: ProxyPassenger) -> None:
        """乘客上梯"""
        print(f"  [BOARD] 乘客 {passenger.id} 上梯 E{elevator.id} 在 F{elevator.current_floor}")

        # 删除该乘客的 pickup 任务
        plan = self.executor.elevator_plans.get(elevator.id)
        if plan:
            # 从任务队列中移除该乘客的 pickup 任务
            new_queue = []
            for task in plan.task_queue:
                if task.task_type == "pickup" and passenger.id in task.passenger_ids:
                    # 移除该乘客
                    task.passenger_ids.remove(passenger.id)
                    # 如果任务还有其他乘客，保留任务
                    if task.passenger_ids:
                        new_queue.append(task)
                    # 否则丢弃空任务
                else:
                    new_queue.append(task)
            plan.task_queue = new_queue

        # 不在这里设置目标，让 on_elevator_stopped 统一处理
        # 这样可以避免频繁改变目标，保持 LOOK 算法的连续性

    def on_passenger_alight(self, elevator: ProxyElevator, passenger: ProxyPassenger, floor: ProxyFloor) -> None:
        """乘客下梯"""
        print(f"  [ALIGHT] 乘客 {passenger.id} 下梯 E{elevator.id} 在 F{floor.floor}")

        # 移除请求
        self.request_manager.remove_request(passenger.id)

        # 删除该乘客的 dropoff 任务
        plan = self.executor.elevator_plans.get(elevator.id)
        if plan:
            # 从任务队列中移除该乘客的 dropoff 任务
            new_queue = []
            for task in plan.task_queue:
                if task.task_type == "dropoff" and passenger.id in task.passenger_ids:
                    # 移除该乘客
                    task.passenger_ids.remove(passenger.id)
                    # 如果任务还有其他乘客，保留任务
                    if task.passenger_ids:
                        new_queue.append(task)
                    # 否则丢弃空任务
                else:
                    new_queue.append(task)
            plan.task_queue = new_queue

        # 不在这里设置目标，让 on_elevator_stopped 统一处理
        # 这样可以避免频繁改变目标，保持 LOOK 算法的连续性

    def on_event_execute_start(
        self, tick: int, events: List[SimulationEvent], elevators: List[ProxyElevator], floors: List[ProxyFloor]
    ) -> None:
        """事件执行开始"""
        self.current_tick = tick
        if self.debug:
            print(f"\n[TICK {tick}] {len(events)} 个事件")

    def on_event_execute_end(
        self, tick: int, events: List[SimulationEvent], elevators: List[ProxyElevator], floors: List[ProxyFloor]
    ) -> None:
        """事件执行结束"""
        # 更新请求优先级
        self.request_manager.update_priorities(tick)

        # 检查是否有长时间等待的请求需要重新分配
        pending_requests = self.request_manager.get_pending_requests()
        high_priority_requests = [
            req for req in pending_requests if (tick - req.arrive_tick) > Config.REALLOCATION_THRESHOLD
        ]

        if high_priority_requests:
            print(f"[WARNING] 发现 {len(high_priority_requests)} 个高优先级请求，重新分配")
            self.dispatcher.assign_requests(elevators, high_priority_requests, tick)

    def on_elevator_approaching(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        """电梯即将到达"""
        if self.debug:
            print(f"[APPROACHING] 电梯 E{elevator.id} 即将到达 F{floor.floor}")

    def on_elevator_passing_floor(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        """电梯经过楼层"""
        if self.debug:
            print(f"[PASSING] 电梯 E{elevator.id} 经过 F{floor.floor}")


if __name__ == "__main__":
    # 启动Optimal LOOK控制器
    controller = OptimalLookController(debug=True)
    controller.start()
