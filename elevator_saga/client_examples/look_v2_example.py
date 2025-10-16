#!/usr/bin/env python3
"""
LOOK V2 电梯调度算法 - 实时决策版本
简化策略：不维护任务队列，在每次停靠时动态决定下一个目标楼层
关键：正确处理方向匹配约束，确保100%完成率
"""
from typing import List, Optional, Set
from elevator_saga.client.base_controller import ElevatorController
from elevator_saga.client.proxy_models import ProxyElevator, ProxyFloor, ProxyPassenger
from elevator_saga.core.models import Direction, SimulationEvent


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

        # 检查当前楼层是否有方向不匹配的乘客
        current_floor_status = []
        if current_floor in up_targets:
            current_floor_status.append(f"up_queue({len(floor.up_queue)})")
        if current_floor in down_targets:
            current_floor_status.append(f"down_queue({len(floor.down_queue)})")
        if current_floor_status:
            print(f"  [!] 当前楼层F{current_floor}仍有等待: {', '.join(current_floor_status)} (可能方向不匹配)")

        # 不移除当前楼层，改为在选择逻辑中智能处理
        # 注意：如果当前楼层仍在targets中，说明有方向不匹配的乘客等待

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

            # 移动到下一个楼层
            elevator.go_to_floor(next_floor)
            print(f"  -> E{elevator.id} 前往 F{next_floor} (方向: {self.elevator_scan_direction[elevator.id].value})")
        else:
            print(f"  -> E{elevator.id} 无目标，保持空闲")

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

        改进：
        1. 如果电梯为空（is_empty=True），直接去接最近的乘客，不遵循LOOK方向
        2. 否则按标准LOOK算法选择目标
        3. 特殊处理当前楼层有反方向乘客的情况

        LOOK算法核心：
        1. 沿当前方向扫描，到达边界后转向
        2. 优先选择当前方向上最近的目标
        3. 如果当前方向没有目标，转向并选择反方向最近的目标

        关键：只有方向匹配的乘客才能上梯
        - 向上扫描时，只能去接需要向上的乘客（up_targets）
        - 向下扫描时，只能去接需要向下的乘客（down_targets）
        """
        # === 策略1：空闲优先 - 直接去接最近的乘客 ===
        if is_empty:
            # 合并所有目标
            all_targets = up_targets | down_targets
            # 移除当前楼层（避免原地不动）
            all_targets.discard(current_floor)

            if not all_targets:
                return None

            # 选择距离最近的楼层
            nearest = min(all_targets, key=lambda f: abs(f - current_floor))
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
            #    首先检查当前楼层是否有down_queue（方向不匹配的情况）
            if current_floor in down_targets:
                if self.debug:
                    print(f"  [方向转换] 当前楼层F{current_floor}有down_queue，需要转向向下")
                # 向下移动一层后再回来接乘客，或者直接选择下方的目标
                lower_down = [f for f in down_targets if f < current_floor]
                if lower_down:
                    # 有下方的down_targets，直接去最近的
                    return max(lower_down)
                elif current_floor > 0:
                    # 只有当前楼层有down_queue，去下一层然后回来
                    return current_floor - 1
                else:
                    # 在底层且只有当前楼层，去上一层然后回来
                    return current_floor + 1

            #    选择下方的 down_targets（从高到低扫描）
            lower_down = [f for f in down_targets if f < current_floor]
            if lower_down:
                return max(lower_down)  # 最高的下层楼层

            # 4. 最后尝试下方的 up_targets
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
            #    首先检查当前楼层是否有up_queue（方向不匹配的情况）
            if current_floor in up_targets:
                if self.debug:
                    print(f"  [方向转换] 当前楼层F{current_floor}有up_queue，需要转向向上")
                # 向上移动一层后再回来接乘客，或者直接选择上方的目标
                upper_up = [f for f in up_targets if f > current_floor]
                if upper_up:
                    # 有上方的up_targets，直接去最近的
                    return min(upper_up)
                elif current_floor < self.max_floor:
                    # 只有当前楼层有up_queue，去上一层然后回来
                    return current_floor + 1
                else:
                    # 在顶层且只有当前楼层，去下一层然后回来
                    return current_floor - 1

            #    选择上方的 up_targets（从低到高扫描）
            upper_up = [f for f in up_targets if f > current_floor]
            if upper_up:
                return min(upper_up)  # 最低的上层楼层

            # 4. 最后尝试上方的 down_targets
            upper_down = [f for f in down_targets if f > current_floor]
            if upper_down:
                return max(upper_down)  # 最高的上层楼层

        return None

    def on_elevator_idle(self, elevator: ProxyElevator) -> None:
        """
        电梯空闲 - 重新扫描是否有需求

        可能有新请求到来，但电梯已经空闲
        """
        if self.debug:
            print(f"[IDLE] E{elevator.id} 在 F{elevator.current_floor} 空闲")

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
    # 启动LOOK V2控制器
    controller = LookV2Controller(debug=False)
    controller.start()
