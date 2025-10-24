#!/usr/bin/env python3
"""
GUI Controller - 纯可视化控制器
只接收事件，不发送命令，与具体算法实现无关
"""
from typing import List
from elevator.client.base_controller import ElevatorController
from elevator.client.proxy_models import ProxyElevator, ProxyFloor, ProxyPassenger
from elevator.core.models import SimulationEvent


class GUIController(ElevatorController):
    """GUI 控制器 - 纯可视化，只监听事件不控制电梯"""

    def __init__(self, server_url: str = "http://127.0.0.1:8000", debug: bool = False):
        super().__init__(server_url, debug, enable_recording=False)
        # 导入全局事件队列
        try:
            from elevator.visualization.web_server import get_event_queue
            self.event_queue = get_event_queue()
        except ImportError:
            self.event_queue = None
            print("[GUI] 警告: 无法导入事件队列，实时推送将不可用")
        # 初始化事件回调函数（备用，默认为None）
        self.event_callback = None
        print("[GUI] GUI Controller 初始化完成")

    def set_event_callback(self, callback):
        """设置事件回调函数"""
        self.event_callback = callback

    def on_init(self, elevators: List[ProxyElevator], floors: List[ProxyFloor]) -> None:
        """初始化 - GUI 接收初始配置"""
        print(f"[GUI] 初始化: {len(elevators)} 部电梯，{len(floors)} 层楼")
        if self.event_callback:
            self.event_callback({
                "type": "init",
                "data": {
                    "elevators": len(elevators),
                    "floors": len(floors)
                }
            })

    def on_passenger_call(self, passenger: ProxyPassenger, floor: ProxyFloor, direction: str) -> None:
        """乘客呼叫"""
        pass

    def on_elevator_stopped(self, elevator: ProxyElevator, floor: ProxyFloor) -> None:
        """电梯停靠"""
        pass

    def on_elevator_idle(self, elevator: ProxyElevator) -> None:
        """电梯空闲"""
        pass

    def on_passenger_board(self, elevator: ProxyElevator, passenger: ProxyPassenger) -> None:
        """乘客上梯"""
        pass

    def on_passenger_alight(self, elevator: ProxyElevator, passenger: ProxyPassenger, floor: ProxyFloor) -> None:
        """乘客下梯"""
        pass

    def on_event_execute_start(
        self, tick: int, events: List[SimulationEvent], elevators: List[ProxyElevator], floors: List[ProxyFloor]
    ) -> None:
        """事件执行开始 - GUI 接收状态快照"""
        # 构建状态数据推送给前端
        # 收集电梯信息
        elevators_data = []
        for elevator in elevators:
            elevators_data.append({
                "id": elevator.id,
                "current_floor": elevator.current_floor,
                "direction": elevator.last_tick_direction.value,
                "passengers": list(elevator.passengers),
            })

        # 收集楼层信息
        floors_data = []
        for floor in floors:
            floors_data.append({
                "floor": floor.floor,
                "up_queue": list(floor.up_queue),
                "down_queue": list(floor.down_queue),
            })

        # 构建消息
        message = {
            "type": "state_update",
            "data": {
                "tick": tick,
                "elevators": elevators_data,
                "floors": floors_data,
            }
        }

        # 推送到事件队列（给 WebSocket 转发给前端）
        if self.event_queue:
            self.event_queue.put(message)

        # 调用回调函数（备用）
        if self.event_callback:
            self.event_callback(message)

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
