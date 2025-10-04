#!/usr/bin/env python3
from typing import List, Dict, Set, Optional

from elevator_saga.client.base_controller import ElevatorController
from elevator_saga.client.proxy_models import ProxyElevator, ProxyFloor, ProxyPassenger
from elevator_saga.core.models import Direction, SimulationEvent


def _to_dir_enum(d) -> Optional[Direction]:
    """将传入的方向（'up'/'down'/Direction）标准化为 Direction 枚举；无法识别则返回 None"""
    if isinstance(d, Direction):
        return d
    if d is None:
        return None
    s = str(d).strip().upper()
    if s.startswith("UP"):
        return Direction.UP
    if s.startswith("DOWN"):
        return Direction.DOWN
    return None


class ElevatorBusExampleController(ElevatorController):
    def __init__(self) -> None:
        # 链接到本地服务器，启用调试模式
        super().__init__("http://127.0.0.1:8000", True)
        # 初始化所有乘客列表
        self.all_passengers: List[ProxyPassenger] = []
        # 初始化最大楼层
        self.max_floor = 0

        # —— 新增：每台电梯独立的停靠集合 & 待接集合 ——
        self.up_stops: Dict[int, Set[int]] = {}
        self.down_stops: Dict[int, Set[int]] = {}
        self.pending_up_floors: Set[int] = set()
        self.pending_down_floors: Set[int] = set()

        # —— 新增：缓存与去重辅助 ——
        self.all_elevators: List[ProxyElevator] = []
        self.all_floors: List[ProxyFloor] = []
        self.last_target: Dict[int, Optional[int]] = {}  # 记录上一次派给电梯的目标层，避免重复派单

    # 初始化电梯和楼层信息
    def on_init(self, elevators: List[ProxyElevator], floors: List[ProxyFloor]) -> None:
        self.all_elevators = elevators
        self.all_floors = floors
        self.max_floor = max(floor.floor for floor in floors)

        # 初始化容器
        for e in elevators:
            self.up_stops[e.id] = set()
            self.down_stops[e.id] = set()
            self.last_target[e.id] = None

        # 均匀铺开（保留上版策略）
        if len(elevators) > 1:
            for i, e in enumerate(elevators):
                target = round(i * self.max_floor / (len(elevators) - 1))
                self._dispatch_if_new(e, target, immediate=True, label=f"初始分布至 F{target}")

    def on_event_execute_start(self, tick: int, events: List[SimulationEvent], elevators: List[ProxyElevator], floors: List[ProxyFloor]) -> None:
        """事件执行前的回调"""
        pass

    def on_event_execute_end(self, tick: int, events: List[SimulationEvent], elevators: List[ProxyElevator], floors: List[ProxyFloor]) -> None:
        """事件执行后的回调"""
        pass

    def on_passenger_call(self, passenger: ProxyPassenger, floor: ProxyFloor, direction: str) -> None:
        """乘客呼叫时的回调"""
        print(f"[呼叫] 乘客{passenger.id} 在 F{floor.floor} 呼叫（{direction}）")

        dir_enum = _to_dir_enum(direction)
        idle_es = [e for e in self.all_elevators if e.is_idle]

        if idle_es:
            # 最近空闲电梯
            nearest = min(idle_es, key=lambda e: abs(e.current_floor - floor.floor))
            if dir_enum == Direction.UP:
                self.up_stops[nearest.id].add(floor.floor)
            elif dir_enum == Direction.DOWN:
                self.down_stops[nearest.id].add(floor.floor)
            else:
                # 无法识别方向，按就近直接派
                pass

            # 若最近电梯“当前就站在该层”，不要再派同层命令，直接等停靠事件处理
            if nearest.current_floor == floor.floor:
                # 清掉同层标记，防止后续空闲时反复派同层
                self.up_stops[nearest.id].discard(floor.floor)
                self.down_stops[nearest.id].discard(floor.floor)
                return

            if self._dispatch_if_new(nearest, floor.floor, label=f"E{nearest.id} 前往 F{floor.floor}（最近空闲）"):
                print(f"[派单] E{nearest.id} 前往 F{floor.floor}（最近空闲）")
        else:
            # 无空闲电梯 → 登记待接（大小写已标准化）
            if dir_enum == Direction.UP:
                self.pending_up_floors.add(floor.floor)
            elif dir_enum == Direction.DOWN:
                self.pending_down_floors.add(floor.floor)
            else:
                # 方向异常时，先放入两个集合之一都可以；这里选择 down 以保持与日志一致
                self.pending_down_floors.add(floor.floor)
            print(f"[排队] 暂无空闲电梯，F{floor.floor}（{direction}）加入待接")

    def on_elevator_idle(self, elevator: ProxyElevator) -> None:
        """电梯空闲时的回调"""
        print(f"[空闲] E{elevator.id} 空闲于 F{elevator.current_floor}")

        eid = elevator.id
        cf = elevator.current_floor

        # 自身登记目标
        own_targets = set(self.up_stops[eid]) | set(self.down_stops[eid])
        if own_targets:
            nxt = min(own_targets, key=lambda x: abs(x - cf))
            # 关键：同层目标直接清理，不派重复指令
            if nxt == cf:
                self.up_stops[eid].discard(cf)
                self.down_stops[eid].discard(cf)
                return
            if self._dispatch_if_new(elevator, nxt, label=f"E{eid} 前往登记点 F{nxt}"):
                print(f"[派单] E{eid} 前往登记点 F{nxt}")
            return

        # 消化全局待接
        if self.pending_up_floors or self.pending_down_floors:
            all_pending = list(self.pending_up_floors | self.pending_down_floors)
            nxt = min(all_pending, key=lambda x: abs(x - cf))
            if nxt == cf:
                # 站在待接层：清待接并交给停靠事件处理
                self.pending_up_floors.discard(cf)
                self.pending_down_floors.discard(cf)
                return
            # 将该点记录到对应方向集合，便于“顺路停”
            if nxt > cf:
                self.up_stops[eid].add(nxt)
            else:
                self.down_stops[eid].add(nxt)
            self.pending_up_floors.discard(nxt)
            self.pending_down_floors.discard(nxt)
            if self._dispatch_if_new(elevator, nxt, label=f"E{eid} 领取待接点 F{nxt}"):
                print(f"[消化] E{eid} 领取待接点 F{nxt}")
            return

        # 无任务 → 回 0 层（避免反复派同层）
        if cf != 0 and self._dispatch_if_new(elevator, 0, label=f"E{eid} 返回大厅 F0"):
            print(f"[待命] E{eid} 返回大厅 F0")

    def on_elevator_stopped(self, elevator: ProxyElevator, floor: ProxyFloor) -> None:
        """电梯停靠时的回调"""
        print(f"[停靠] E{elevator.id} 到站 F{floor.floor}")

        eid = elevator.id
        cf = elevator.current_floor
        self.up_stops[eid].discard(cf)
        self.down_stops[eid].discard(cf)

        last_dir = elevator.last_tick_direction
        nxt = None

        def pick_upward():
            higher = [f for f in self.up_stops[eid] if f > cf]
            return min(higher) if higher else None

        def pick_downward():
            lower = [f for f in self.down_stops[eid] if f < cf]
            return max(lower) if lower else None

        if last_dir == Direction.UP:
            nxt = pick_upward() or pick_downward()
        elif last_dir == Direction.DOWN:
            nxt = pick_downward() or pick_upward()
        else:
            candidates = list(self.up_stops[eid] | self.down_stops[eid])
            if candidates:
                nxt = min(candidates, key=lambda x: abs(x - cf))

        if nxt is not None and nxt != cf:
            if self._dispatch_if_new(elevator, nxt, label=f"E{eid} 目标 F{nxt}"):
                print(f"[续行] E{eid} 目标 F{nxt}")
        # 没有下一站则保持空闲，交给 on_elevator_idle 处理

    def on_passenger_board(self, elevator: ProxyElevator, passenger: ProxyPassenger) -> None:
        """乘客上梯时的回调"""
        print(f"[上梯] 乘客{passenger.id} 进入 E{elevator.id}（目的 F{passenger.destination}）")
        eid = elevator.id
        cf = elevator.current_floor
        dest = passenger.destination
        if dest > cf:
            self.up_stops[eid].add(dest)
        elif dest < cf:
            self.down_stops[eid].add(dest)
        # 若等于当前层，交给停靠事件处理

    def on_passenger_alight(self, elevator: ProxyElevator, passenger: ProxyPassenger, floor: ProxyFloor) -> None:
        """乘客下车时的回调"""
        print(f"[下梯] 乘客{passenger.id} 在 F{floor.floor} 下车（E{elevator.id}）")

    def on_elevator_passing_floor(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        """电梯经过楼层时的回调"""
        eid = elevator.id
        cur_dir = elevator.target_floor_direction
        if cur_dir is None:
            return

        fl = floor.floor
        need_stop = False

        if cur_dir == Direction.UP:
            if fl in self.up_stops[eid] or (len(floor.up_queue) > 0 and not elevator.is_full):
                need_stop = True
        elif cur_dir == Direction.DOWN:
            if fl in self.down_stops[eid] or (len(floor.down_queue) > 0 and not elevator.is_full):
                need_stop = True

        # 避免同层/同目标的重复插停
        if need_stop and fl != elevator.current_floor and fl != elevator.target_floor:
            if self._dispatch_if_new(elevator, fl, immediate=True, label=f"E{eid} 临停 F{fl}"):
                print(f"[顺停] E{eid} 将在 F{fl} 临停（{cur_dir.value}）")

        # 清理全局待接中该层，避免后续重复登记
        self.pending_up_floors.discard(fl)
        self.pending_down_floors.discard(fl)

    def on_elevator_approaching(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        """电梯即将到达时的回调"""
        pass

    # —— 新增：派单防抖/去重工具 —— #
    def _dispatch_if_new(self, elevator: ProxyElevator, target: int, *, immediate: bool = False, label: str = "") -> bool:
        """仅在目标与当前层、现有目标、上次目标都不相同时才真正发送 go_to_floor；返回是否真的派单"""
        eid = elevator.id
        if target is None:
            return False
        # 同层不派
        if target == elevator.current_floor:
            return False
        # 目标未变化不派（避免刷屏/重复停靠）
        if target == elevator.target_floor or target == self.last_target.get(eid):
            return False
        elevator.go_to_floor(target, immediate=immediate)
        self.last_target[eid] = target
        # 可选：这里不打印，统一由调用方打印精简日志
        return True


if __name__ == "__main__":
    algorithm = ElevatorBusExampleController()
    algorithm.start()
