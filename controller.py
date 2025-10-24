#!/usr/bin/env python3
"""
电梯调度控制器 - 支持 GUI 和 Algorithm 两种模式

使用环境变量 ELEVATOR_CLIENT_TYPE 来控制运行模式：
- gui: 启动可视化界面（纯监听模式）
- algorithm: 启动调度算法（决策模式）

LOOK V2 电梯调度算法 - 简化版本

核心特点：
1. 实时决策：每次停靠时动态选择下一个目标楼层，不维护任务队列
2. 双策略：
   - 空闲优先：电梯为空时，去最近的有需求楼层
   - LOOK扫描：电梯有乘客时，遵循扫描方向（向上/向下）
3. 方向匹配：严格遵守LOOK算法的方向匹配约束
   - 向上扫描时只接向上的乘客（up_queue）
   - 向下扫描时只接向下的乘客（down_queue）
4. 简洁性：避免复杂的方向转换逻辑，让算法自然循环

设计原则：
- 代码简洁，逻辑清晰
- 避免死循环和卡死
- 不返回当前楼层（会导致死循环）
- 让电梯按LOOK算法自然移动，最终会服务所有乘客
"""
from typing import List, Optional, Set
from elevator.client.base_controller import ElevatorController
from elevator.client.gui_controller import GUIController
from elevator.client.proxy_models import ProxyElevator, ProxyFloor, ProxyPassenger
from elevator.core.models import Direction, SimulationEvent


class LookV2Controller(ElevatorController):
    """LOOK V2 控制器 - 实时决策版本"""

    def __init__(self, server_url: str = "http://127.0.0.1:8000", debug: bool = False):
        super().__init__(server_url, debug)
        self.max_floor = 0
        self.floors: List[ProxyFloor] = []
        self.current_tick = 0

        # 记录每个电梯的当前扫描方向（用于LOOK算法）
        # 注意：这个方向可能与elevator.target_floor_direction不同
        # 因为elevator.target_floor_direction在停靠时会变成STOPPED
        self.elevator_scan_direction: dict[int, Direction] = {}

        # 存储乘客信息：passenger_id -> destination
        self.passenger_destinations: dict[int, int] = {}

    def on_init(self, elevators: List[ProxyElevator], floors: List[ProxyFloor]) -> None:
        """初始化"""
        print("[LOOK V2] 算法初始化（实时决策版本）")
        print(f"  管理 {len(elevators)} 部电梯，服务 {len(floors)} 层楼")

        self.max_floor = len(floors) - 1
        self.floors = floors

        # 初始化电梯扫描方向为UP
        for elevator in elevators:
            self.elevator_scan_direction[elevator.id] = Direction.UP
            print(f"  电梯 E{elevator.id} 初始化，扫描方向: UP")

    def on_passenger_call(self, passenger: ProxyPassenger, floor: ProxyFloor, direction: str) -> None:
        """乘客呼叫 - 记录乘客目的地信息"""
        print(f"[CALL] 乘客 {passenger.id}: F{passenger.origin} -> F{passenger.destination}")
        # 记录乘客目的地
        self.passenger_destinations[passenger.id] = passenger.destination

    def on_elevator_stopped(self, elevator: ProxyElevator, floor: ProxyFloor) -> None:
        """
        电梯停靠 - 核心决策逻辑

        实时收集所有需求楼层，按LOOK算法选择下一个目标
        """
        print(f"[STOP] E{elevator.id} 停靠在 F{floor.floor} | 载客:{len(elevator.passengers)} | 方向:{self.elevator_scan_direction.get(elevator.id, Direction.UP).value}")

        # 获取电梯当前扫描方向
        current_direction = self.elevator_scan_direction.get(elevator.id, Direction.UP)
        current_floor = elevator.current_floor

        # === 第一步：收集所有有需求的楼层 ===
        # 分别收集两个方向的需求楼层
        up_targets: Set[int] = set()    # 需要向上的乘客所在楼层
        down_targets: Set[int] = set()  # 需要向下的乘客所在楼层

        # 1. 电梯内乘客的目的地（没有方向限制，两个方向都算）
        for passenger_id in elevator.passengers:
            destination = self.passenger_destinations.get(passenger_id)
            if destination is not None:
                if destination > current_floor:
                    up_targets.add(destination)
                elif destination < current_floor:
                    down_targets.add(destination)

        if self.debug and elevator.passengers:
            print(f"  [DEBUG] 电梯内有 {len(elevator.passengers)} 个乘客")
            print(f"  [DEBUG] 电梯内乘客目的地: {[self.passenger_destinations.get(p) for p in elevator.passengers]}")

        # 2. 等待上梯的乘客位置（分别收集）
        waiting_floors = []  # 用于输出等待乘客的楼层信息
        for f in self.floors:
            if f.up_queue:  # 有向上的乘客
                up_targets.add(f.floor)
                waiting_floors.append(f"F{f.floor}↑({len(f.up_queue)})")
                if self.debug:
                    print(f"  [DEBUG] F{f.floor} up_queue: {f.up_queue}")
            if f.down_queue:  # 有向下的乘客
                down_targets.add(f.floor)
                waiting_floors.append(f"F{f.floor}↓({len(f.down_queue)})")
                if self.debug:
                    print(f"  [DEBUG] F{f.floor} down_queue: {f.down_queue}")

        if waiting_floors:
            print(f"  等待乘客: {', '.join(waiting_floors)}")

        if self.debug:
            print(f"  当前方向: {current_direction.value}, UP目标: {sorted(up_targets)}, DOWN目标: {sorted(down_targets)}")

        # 检查电梯是否为空（空闲状态）
        is_empty = len(elevator.passengers) == 0

        if self.debug and is_empty:
            print(f"  [DEBUG] 电梯为空，采用空闲优先策略")

        # === 第二步：按LOOK算法选择下一个目标楼层 ===
        next_floor = self._select_next_floor_look(
            current_floor,
            current_direction,
            up_targets,
            down_targets,
            is_empty
        )

        if next_floor is not None:
            # 更新扫描方向
            if next_floor > current_floor:
                self.elevator_scan_direction[elevator.id] = Direction.UP
            elif next_floor < current_floor:
                self.elevator_scan_direction[elevator.id] = Direction.DOWN
            #  next_floor == current_floor 的情况已在选择逻辑中处理

            # 移动到下一个楼层
            elevator.go_to_floor(next_floor)
            print(f"  -> E{elevator.id} 前往 F{next_floor} (方向: {self.elevator_scan_direction[elevator.id].value})")
        else:
            # 没有任何目标时，给电梯分配待命位置
            # 这对于流水线测试环境至关重要，避免服务器停滞在"no tick"状态
            if current_floor == 0:
                # 在底层，向上移动
                elevator.go_to_floor(1)
                print(f"  -> E{elevator.id} 无目标，待命移动到F1")
            else:
                # 在其他楼层，返回底层
                elevator.go_to_floor(0)
                print(f"  -> E{elevator.id} 无目标，待命返回F0")

    def _select_next_floor_look(
        self,
        current_floor: int,
        current_direction: Direction,
        up_targets: Set[int],
        down_targets: Set[int],
        is_empty: bool
    ) -> Optional[int]:
        """
        按LOOK算法选择下一个目标楼层

        参数：
            current_floor: 电梯当前所在楼层
            current_direction: 电梯当前扫描方向（UP/DOWN）
            up_targets: 需要向上的乘客所在楼层集合
            down_targets: 需要向下的乘客所在楼层集合
            is_empty: 电梯是否为空

        返回：
            下一个目标楼层，如果没有目标则返回None

        策略说明：
        1. 空闲优先（is_empty=True）：
           - 去最近的有需求楼层（不考虑方向）
           - 避免返回当前楼层（会死循环）

        2. LOOK扫描（is_empty=False）：
           - 向上扫描：优先去上方的up_targets，然后是上方的down_targets
           - 向下扫描：优先去下方的down_targets，然后是下方的up_targets
           - 当前方向没有目标时，转向扫描反方向
           - 严格遵守方向匹配：只接与扫描方向一致的乘客

        关键约束：
        - 永远不返回当前楼层（current_floor），避免死循环
        - 让电梯自然移动，按LOOK算法循环服务所有乘客
        """
        # === 策略1：空闲优先 - 直接去接最近的乘客 ===
        if is_empty:
            # 合并所有目标
            all_targets = up_targets | down_targets

            if not all_targets:
                return None

            # 选择距离最近的楼层
            nearest = min(all_targets, key=lambda f: abs(f - current_floor))

            # 特殊处理：如果最近的楼层是当前楼层，需要移动一层触发方向改变
            if nearest == current_floor:
                # 检查当前楼层的需求方向
                if current_floor in down_targets and current_floor > 0:
                    # 有向下需求，去下一层
                    if self.debug:
                        print(f"  [IDLE策略] 当前楼层F{nearest}有down需求，先去F{current_floor-1}")
                    return current_floor - 1
                elif current_floor in up_targets and current_floor < self.max_floor:
                    # 有向上需求，去上一层
                    if self.debug:
                        print(f"  [IDLE策略] 当前楼层F{nearest}有up需求，先去F{current_floor+1}")
                    return current_floor + 1

            if self.debug:
                print(f"  [IDLE策略] 选择最近楼层: F{nearest} (距离={abs(nearest - current_floor)})")
            return nearest

        # === 策略2：LOOK算法 - 电梯内有乘客时遵循扫描方向 ===
        if current_direction == Direction.UP:
            # 当前向上扫描
            # 1. 优先选择上方的 up_targets（可以立即接到乘客）
            upper_up = [f for f in up_targets if f > current_floor]
            if upper_up:
                return min(upper_up)  # 最近的上层楼层

            # 2. 如果上方没有 up_targets，选择上方的 down_targets
            #    虽然到达时不能接乘客，但可以准备转向
            upper_down = [f for f in down_targets if f > current_floor]
            if upper_down:
                return max(upper_down)  # 去最高的，到达后转向向下

            # 3. 上方都没有需求，转向向下
            #    选择下方的 down_targets（从高到低扫描），排除当前楼层
            lower_down = [f for f in down_targets if f < current_floor]
            if lower_down:
                return max(lower_down)  # 最高的下层楼层

            # 4. 最后尝试下方的 up_targets，排除当前楼层
            lower_up = [f for f in up_targets if f < current_floor]
            if lower_up:
                return min(lower_up)  # 最低的下层楼层

        else:  # current_direction == Direction.DOWN
            # 当前向下扫描
            # 1. 优先选择下方的 down_targets（可以立即接到乘客）
            lower_down = [f for f in down_targets if f < current_floor]
            if lower_down:
                return max(lower_down)  # 最近的下层楼层

            # 2. 如果下方没有 down_targets，选择下方的 up_targets
            #    虽然到达时不能接乘客，但可以准备转向
            lower_up = [f for f in up_targets if f < current_floor]
            if lower_up:
                return min(lower_up)  # 去最低的，到达后转向向上

            # 3. 下方都没有需求，转向向上
            #    选择上方的 up_targets（从低到高扫描），排除当前楼层
            upper_up = [f for f in up_targets if f > current_floor]
            if upper_up:
                return min(upper_up)  # 最低的上层楼层

            # 4. 最后尝试上方的 down_targets，排除当前楼层
            upper_down = [f for f in down_targets if f > current_floor]
            if upper_down:
                return max(upper_down)  # 最高的上层楼层

        return None

    def on_elevator_idle(self, elevator: ProxyElevator) -> None:
        """
        电梯空闲 - 重新扫描是否有需求

        特殊处理：如果当前楼层有乘客等待但方向不匹配，移动一层后回来接乘客
        这样可以触发方向改变，避免死循环
        """
        if self.debug:
            print(f"[IDLE] E{elevator.id} 在 F{elevator.current_floor} 空闲")

        current_floor = elevator.current_floor
        current_floor_obj = self.floors[current_floor]
        current_direction = self.elevator_scan_direction.get(elevator.id, Direction.UP)

        # 检查当前楼层是否有方向不匹配的乘客
        has_up_queue = len(current_floor_obj.up_queue) > 0
        has_down_queue = len(current_floor_obj.down_queue) > 0

        # 如果当前楼层有乘客，但方向不匹配，移动一层后回来
        if has_up_queue and current_direction == Direction.DOWN and current_floor < self.max_floor:
            # 需要向上，但当前方向向下，去上一层
            target = current_floor + 1
            self.elevator_scan_direction[elevator.id] = Direction.UP
            elevator.go_to_floor(target)
            print(f"  [方向修正] F{current_floor}有up_queue，去F{target}后回来 (切换为UP)")
            return
        elif has_down_queue and current_direction == Direction.UP and current_floor > 0:
            # 需要向下，但当前方向向上，去下一层
            target = current_floor - 1
            self.elevator_scan_direction[elevator.id] = Direction.DOWN
            elevator.go_to_floor(target)
            print(f"  [方向修正] F{current_floor}有down_queue，去F{target}后回来 (切换为DOWN)")
            return

        # 复用停靠逻辑，重新扫描需求
        floor = self.floors[elevator.current_floor]
        self.on_elevator_stopped(elevator, floor)

    def on_passenger_board(self, elevator: ProxyElevator, passenger: ProxyPassenger) -> None:
        """乘客上梯"""
        if self.debug:
            print(f"  [BOARD] 乘客 {passenger.id} 上梯 E{elevator.id}")

    def on_passenger_alight(self, elevator: ProxyElevator, passenger: ProxyPassenger, floor: ProxyFloor) -> None:
        """乘客下梯"""
        if self.debug:
            print(f"  [ALIGHT] 乘客 {passenger.id} 下梯 E{elevator.id}")
        # 清除乘客信息
        if passenger.id in self.passenger_destinations:
            del self.passenger_destinations[passenger.id]

    def on_event_execute_start(
        self, tick: int, events: List[SimulationEvent], elevators: List[ProxyElevator], floors: List[ProxyFloor]
    ) -> None:
        """事件执行开始"""
        self.current_tick = tick
        if self.debug:
            print(f"\n=== TICK {tick} ===")

    def on_event_execute_end(
        self, tick: int, events: List[SimulationEvent], elevators: List[ProxyElevator], floors: List[ProxyFloor]
    ) -> None:
        """事件执行结束"""
        pass

    def on_elevator_approaching(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        """电梯即将到达"""
        pass

    def on_elevator_passing_floor(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        """电梯经过楼层"""
        pass


if __name__ == "__main__":
    import os
    import time

    # 获取客户端类型
    client_type = os.environ.get("ELEVATOR_CLIENT_TYPE", "algorithm").lower()

    if client_type == "gui":
        print("[MAIN] 启动 GUI 模式（纯可视化，监听事件）")
        try:
            from elevator.visualization.web_server import start_visualization_server
            # 启动可视化服务器（后台线程）
            print("[MAIN] 启动可视化 Web 服务器...")
            web_thread = start_visualization_server(host="127.0.0.1", port=5173)
            # 给服务器一些时间来启动
            time.sleep(2)
            print("[MAIN] Web 服务器已启动，访问 http://127.0.0.1:5173")
        except Exception as e:
            print(f"[WARN] 启动 Web 服务器失败: {e}")
            print("[WARN] 继续运行控制器（不带可视化）")

        # 启动 GUI 控制器（纯监听，不控制电梯）
        print("[MAIN] 启动 GUI 控制器...")
        controller = GUIController(debug=False)
        controller.start()

    elif client_type == "algorithm":
        print("[MAIN] 启动 Algorithm 模式（纯算法，决策电梯）")
        # 启动 LOOK V2 控制器（决策算法）
        print("[MAIN] 启动电梯调度控制器...")
        controller = LookV2Controller(debug=False)
        controller.start()
