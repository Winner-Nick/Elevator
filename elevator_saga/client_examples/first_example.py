#!/usr/bin/env python3
from typing import List, Dict, Set

from elevator_saga.client.base_controller import ElevatorController
from elevator_saga.client.proxy_models import ProxyElevator, ProxyFloor, ProxyPassenger
from elevator_saga.core.models import Direction, SimulationEvent


class ElevatorBusExampleController(ElevatorController):
    def __init__(self) -> None:
        # 链接到本地服务器，启用调试模式
        super().__init__("http://127.0.0.1:8000", True)
        # 初始化所有乘客列表
        self.all_passengers: List[ProxyPassenger] = []
        # 初始化最大楼层
        self.max_floor = 0

        # ===== 新增：运行期容器（每台电梯的停靠集合 & 全局待接集合） =====
        self.up_stops: Dict[int, Set[int]] = {}
        self.down_stops: Dict[int, Set[int]] = {}
        # 当没有空闲电梯时，先把呼叫放入全局待接集合，等有电梯路过或空闲再处理
        self.pending_up_floors: Set[int] = set()
        self.pending_down_floors: Set[int] = set()

        # ===== 新增：缓存电梯与楼层 =====
        self.all_elevators: List[ProxyElevator] = []
        self.all_floors: List[ProxyFloor] = []

    # 初始化电梯和楼层信息
    def on_init(self, elevators: List[ProxyElevator], floors: List[ProxyFloor]) -> None:
        self.all_elevators = elevators
        self.all_floors = floors
        self.max_floor = max(floor.floor for floor in floors)

        # ===== 新增：为每部电梯准备独立的上下行停靠集合 =====
        for e in elevators:
            self.up_stops[e.id] = set()
            self.down_stops[e.id] = set()

        # （可选）把电梯均匀铺开，减少初始重叠
        if len(elevators) > 1:
            for i, e in enumerate(elevators):
                target = round(i * self.max_floor / (len(elevators) - 1))
                e.go_to_floor(target, immediate=True)

    def on_event_execute_start(self, tick: int, events: List[SimulationEvent], elevators: List[ProxyElevator], floors: List[ProxyFloor]) -> None:
        """事件执行前的回调"""
        pass  # 保持安静，避免冗余输出；需要时可自行打开日志

    def on_event_execute_end(self, tick: int, events: List[SimulationEvent], elevators: List[ProxyElevator], floors: List[ProxyFloor]) -> None:
        """事件执行后的回调"""
        pass

    def on_passenger_call(self, passenger: ProxyPassenger, floor: ProxyFloor, direction: str) -> None:
        """乘客呼叫时的回调"""
        # 简洁输出：谁、哪层、往哪
        print(f"[呼叫] 乘客{passenger.id} 在 F{floor.floor} 呼叫（{direction}）")

        # ===== 新增：只派给“最近的空闲电梯”；若没有空闲，则登记为待接 =====
        idle_es = [e for e in self.all_elevators if e.is_idle]
        if idle_es:
            # 最近空闲电梯
            nearest = min(idle_es, key=lambda e: abs(e.current_floor - floor.floor))
            if direction == Direction.UP.value:
                self.up_stops[nearest.id].add(floor.floor)
            else:
                self.down_stops[nearest.id].add(floor.floor)
            # 若这台电梯当前没有目标，则立刻指派过去
            if nearest.is_idle:
                nearest.go_to_floor(floor.floor)
                print(f"[派单] E{nearest.id} 前往 F{floor.floor}（最近空闲）")
        else:
            # 无空闲电梯，登记到全局待接集合，等路过/空闲时吸附
            if direction == Direction.UP.value:
                self.pending_up_floors.add(floor.floor)
            else:
                self.pending_down_floors.add(floor.floor)
            print(f"[排队] 暂无空闲电梯，F{floor.floor}（{direction}）加入待接")

    def on_elevator_idle(self, elevator: ProxyElevator) -> None:
        """电梯空闲时的回调"""
        # 简洁输出
        print(f"[空闲] E{elevator.id} 空闲于 F{elevator.current_floor}")

        # ===== 新增：空闲时就近处理本电梯登记的停靠点；没有则尝试消化全局待接；再无则回 0 层 =====
        eid = elevator.id
        cf = elevator.current_floor

        # 合并自身登记的所有停靠点
        own_targets = set(self.up_stops[eid]) | set(self.down_stops[eid])
        if own_targets:
            nxt = min(own_targets, key=lambda x: abs(x - cf))
            elevator.go_to_floor(nxt)
            print(f"[派单] E{eid} 前往登记点 F{nxt}")
            return

        # 消化全局待接（选择与当前位置最近的）
        if self.pending_up_floors or self.pending_down_floors:
            all_pending = list(self.pending_up_floors | self.pending_down_floors)
            nxt = min(all_pending, key=lambda x: abs(x - cf))
            # 为了后续路过能停，把最近的待接点登记到正确方向集合
            if nxt >= cf:
                self.up_stops[eid].add(nxt)
            else:
                self.down_stops[eid].add(nxt)
            # 同时从全局待接里移除该点
            self.pending_up_floors.discard(nxt)
            self.pending_down_floors.discard(nxt)
            elevator.go_to_floor(nxt)
            print(f"[消化] E{eid} 领取待接点 F{nxt}")
            return

        # 无任务：回 0 层（也可改为 self.max_floor // 2 作为中位待命层）
        if cf != 0:
            elevator.go_to_floor(0)
            print(f"[待命] E{eid} 返回大厅 F0")

    def on_elevator_stopped(self, elevator: ProxyElevator, floor: ProxyFloor) -> None:
        """电梯停靠时的回调"""
        print(f"[停靠] E{elevator.id} 到站 F{floor.floor}")

        # ===== 新增：清理本层标记，并选择下一站（优先“同向最近”） =====
        eid = elevator.id
        cf = elevator.current_floor
        self.up_stops[eid].discard(cf)
        self.down_stops[eid].discard(cf)

        # 依据上一刻方向优先择路
        last_dir = elevator.last_tick_direction
        nxt = None

        def pick_upward():
            higher = [f for f in self.up_stops[eid] if f > cf]
            return min(higher) if higher else None

        def pick_downward():
            lower = [f for f in self.down_stops[eid] if f < cf]
            return max(lower) if lower else None

        if last_dir == Direction.UP:
            nxt = pick_upward()
            if nxt is None:
                # 反向兜底
                nxt = pick_downward()
        elif last_dir == Direction.DOWN:
            nxt = pick_downward()
            if nxt is None:
                nxt = pick_upward()
        else:
            # 首次或无方向：就近
            candidates = list(self.up_stops[eid] | self.down_stops[eid])
            if candidates:
                nxt = min(candidates, key=lambda x: abs(x - cf))

        if nxt is not None:
            elevator.go_to_floor(nxt)
            print(f"[续行] E{eid} 目标 F{nxt}")
        # 若没有下一站，不做处理，等 on_elevator_idle 触发统一调度

    def on_passenger_board(self, elevator: ProxyElevator, passenger: ProxyPassenger) -> None:
        """乘客上梯时的回调"""
        print(f"[上梯] 乘客{passenger.id} 进入 E{elevator.id}（目的 F{passenger.destination}）")

        # ===== 新增：把乘客目的层加入当前电梯的对应方向停靠集合（让其被顺路直送）=====
        eid = elevator.id
        cf = elevator.current_floor
        dest = passenger.destination
        if dest > cf:
            self.up_stops[eid].add(dest)
        elif dest < cf:
            self.down_stops[eid].add(dest)

    def on_passenger_alight(self, elevator: ProxyElevator, passenger: ProxyPassenger, floor: ProxyFloor) -> None:
        """乘客下车时的回调"""
        print(f"[下梯] 乘客{passenger.id} 在 F{floor.floor} 下车（E{elevator.id}）")

    def on_elevator_passing_floor(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        """电梯经过楼层时的回调"""
        # ===== 新增：若方向匹配且需要停（登记点或该层存在同向等待且未满），立即插队停靠 =====
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

        if need_stop:
            elevator.go_to_floor(fl, immediate=True)
            print(f"[顺停] E{eid} 将在 F{fl} 临停（{cur_dir.value}）")

        # 顺便把全局待接里该层清掉（避免重复）
        self.pending_up_floors.discard(fl)
        self.pending_down_floors.discard(fl)

    def on_elevator_approaching(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        """电梯即将到达时的回调"""
        pass  # 保持安静，避免多余输出


if __name__ == "__main__":
    algorithm = ElevatorBusExampleController()
    algorithm.start()
