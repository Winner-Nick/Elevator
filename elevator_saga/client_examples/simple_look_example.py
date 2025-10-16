#!/usr/bin/env python3
"""
极简LOOK电梯调度算法
学习bus_example的简洁性，避免过度复杂化
"""
from typing import List, Set
from elevator_saga.client.base_controller import ElevatorController
from elevator_saga.client.proxy_models import ProxyElevator, ProxyFloor, ProxyPassenger
from elevator_saga.core.models import Direction, SimulationEvent


class SimpleLookController(ElevatorController):
    """简单LOOK算法：维护目标楼层集合，按LOOK顺序服务"""

    def __init__(self) -> None:
        super().__init__("http://127.0.0.1:8000", True)
        self.target_floors: List[Set[int]] = []  # 每个电梯的目标楼层集合
        self.max_floor = 0

    def on_init(self, elevators: List[ProxyElevator], floors: List[ProxyFloor]) -> None:
        """初始化"""
        print("[Simple LOOK] 算法初始化")
        print(f"   管理 {len(elevators)} 部电梯")
        print(f"   服务 {len(floors)} 层楼")

        self.max_floor = len(floors) - 1

        # 初始化每个电梯的目标楼层集合
        for _ in elevators:
            self.target_floors.append(set())

    def on_passenger_call(self, passenger: ProxyPassenger, floor: ProxyFloor, direction: str) -> None:
        """乘客呼叫 - 分配给最合适的电梯"""
        print(f"[CALL] 乘客 {passenger.id} 在 F{passenger.origin} 呼叫，目标 F{passenger.destination}")

        # 简单策略：分配给最近的电梯
        best_elevator = self._find_best_elevator(passenger.origin)

        # 添加pickup和dropoff楼层到目标集合
        self.target_floors[best_elevator].add(passenger.origin)
        self.target_floors[best_elevator].add(passenger.destination)

        # 启动电梯（如果空闲）
        elevator = self.elevators[best_elevator]
        if elevator.is_idle and self.target_floors[best_elevator]:
            self._move_to_next_floor(elevator)

    def _find_best_elevator(self, floor: int) -> int:
        """找到最合适的电梯（简单策略：距离最近）"""
        best_idx = 0
        min_distance = float('inf')

        for idx, elevator in enumerate(self.elevators):
            distance = abs(elevator.current_floor - floor)
            if distance < min_distance:
                min_distance = distance
                best_idx = idx

        return best_idx

    def on_elevator_stopped(self, elevator: ProxyElevator, floor: ProxyFloor) -> None:
        """电梯停靠 - 移除当前楼层，移动到下一个目标"""
        print(f"[STOP] 电梯 E{elevator.id} 停靠在 F{floor.floor}")

        # 移除当前楼层
        self.target_floors[elevator.id].discard(floor.floor)

        # 移动到下一个目标
        if self.target_floors[elevator.id]:
            self._move_to_next_floor(elevator)

    def on_elevator_idle(self, elevator: ProxyElevator) -> None:
        """电梯空闲 - 如果有目标则继续移动"""
        print(f"[IDLE] 电梯 E{elevator.id} 在 F{elevator.current_floor} 空闲")

        if self.target_floors[elevator.id]:
            self._move_to_next_floor(elevator)

    def _move_to_next_floor(self, elevator: ProxyElevator) -> None:
        """按LOOK算法选择下一个目标楼层"""
        if not self.target_floors[elevator.id]:
            return

        current_floor = elevator.current_floor
        current_direction = elevator.target_floor_direction

        # 如果电梯停止，选择最近的目标
        if current_direction == Direction.STOPPED:
            next_floor = min(self.target_floors[elevator.id], key=lambda f: abs(f - current_floor))
            elevator.go_to_floor(next_floor)
            return

        # LOOK算法：优先选择当前方向的目标
        targets = sorted(self.target_floors[elevator.id])

        if current_direction == Direction.UP:
            # 向上扫描：选择当前楼层以上最近的目标
            upper_targets = [f for f in targets if f > current_floor]
            if upper_targets:
                elevator.go_to_floor(upper_targets[0])
            else:
                # 没有向上的目标，转向向下
                lower_targets = [f for f in targets if f < current_floor]
                if lower_targets:
                    elevator.go_to_floor(lower_targets[-1])
                else:
                    # 只有当前楼层，应该已经被移除了
                    pass
        else:  # Direction.DOWN
            # 向下扫描：选择当前楼层以下最近的目标
            lower_targets = [f for f in targets if f < current_floor]
            if lower_targets:
                elevator.go_to_floor(lower_targets[-1])
            else:
                # 没有向下的目标，转向向上
                upper_targets = [f for f in targets if f > current_floor]
                if upper_targets:
                    elevator.go_to_floor(upper_targets[0])

    def on_passenger_board(self, elevator: ProxyElevator, passenger: ProxyPassenger) -> None:
        """乘客上梯"""
        print(f"  [BOARD] 乘客 {passenger.id} 上梯 E{elevator.id} 在 F{elevator.current_floor}")

    def on_passenger_alight(self, elevator: ProxyElevator, passenger: ProxyPassenger, floor: ProxyFloor) -> None:
        """乘客下梯"""
        print(f"  [ALIGHT] 乘客 {passenger.id} 下梯 E{elevator.id} 在 F{floor.floor}")

    def on_event_execute_start(
        self, tick: int, events: List[SimulationEvent], elevators: List[ProxyElevator], floors: List[ProxyFloor]
    ) -> None:
        """事件执行开始"""
        if self.debug:
            print(f"\n[TICK {tick}] {len(events)} 个事件")

    def on_event_execute_end(
        self, tick: int, events: List[SimulationEvent], elevators: List[ProxyElevator], floors: List[ProxyFloor]
    ) -> None:
        """事件执行结束"""
        pass

    def on_elevator_approaching(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        """电梯即将到达"""
        if self.debug:
            print(f"[APPROACHING] 电梯 E{elevator.id} 即将到达 F{floor.floor}")

    def on_elevator_passing_floor(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        """电梯经过楼层"""
        if self.debug:
            print(f"[PASSING] 电梯 E{elevator.id} 经过 F{floor.floor}")


if __name__ == "__main__":
    controller = SimpleLookController()
    controller.start()
