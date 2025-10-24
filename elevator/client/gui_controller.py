#!/usr/bin/env python3
"""
GUI Controller - 纯可视化控制器
只接收事件，不发送命令，与具体算法实现无关

关键特性：
- 不调用 step() 方法（只有算法模式应该调用）
- 只轮询 get_state() 来获取状态变化
- 通过事件队列实时推送状态给前端
"""
import os
import time
from typing import List
from elevator.client.base_controller import ElevatorController
from elevator.client.proxy_models import ProxyElevator, ProxyFloor, ProxyPassenger
from elevator.core.models import SimulationEvent


class GUIController(ElevatorController):
    """
    GUI 控制器 - 纯可视化，只监听事件不控制电梯

    ⚠️ 重要：这个类重写了 _run_event_driven_simulation()，以避免调用 step()
    原因：step() 只应该由算法 controller 调用，GUI 模式只需要轮询状态
    """

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

    def _run_event_driven_simulation(self) -> None:
        """
        GUI 的简单事件循环 - 不调用 step()

        核心逻辑：
        1. 注册为 gui 客户端
        2. 获取初始状态，初始化 UI
        3. 进入轮询循环：强制获取最新状态 → 检测变化 → 推送更新
        4. 等待算法 controller 调用 step() 来推进模拟
        """
        try:
            client_type = os.environ.get("ELEVATOR_CLIENT_TYPE", "algorithm").lower()

            # 注册为 gui 客户端
            if not self.api_client.register_client(client_type):
                print(f"Failed to register as {client_type} client, but continuing...")

            # 获取初始状态
            try:
                state = self.api_client.get_state()
            except Exception as e:
                print(f"模拟器可能未启动，请检查 {self.api_client.base_url}")
                print(f"错误: {e}")
                os._exit(1)

            # 初始化状态包装器
            self._update_wrappers(state, init=True)

            # 调用初始化回调（推送 init 消息给前端）
            self._internal_init(self.elevators, self.floors)

            print("[GUI] 进入轮询循环，监听状态变化...")

            last_tick = state.tick
            poll_interval = 0.1  # 100ms 轮询间隔

            while self.is_running:
                try:
                    # ⚠️ 关键：强制每次都获取最新状态（不使用缓存）
                    current_state = self.api_client.get_state(force_reload=True)

                    # 检查是否有状态变化
                    if current_state.tick != last_tick:
                        print(f"[GUI] 收到状态更新: tick {last_tick} -> {current_state.tick}")

                        # 更新状态包装器
                        self._update_wrappers(current_state)

                        # 推送状态更新给前端
                        elevators_data = []
                        for elevator in self.elevators:
                            elevators_data.append({
                                "id": elevator.id,
                                "current_floor": elevator.current_floor,
                                "direction": elevator.last_tick_direction.value,
                                "passengers": list(elevator.passengers),
                            })

                        floors_data = []
                        for floor in self.floors:
                            floors_data.append({
                                "floor": floor.floor,
                                "up_queue": list(floor.up_queue),
                                "down_queue": list(floor.down_queue),
                            })

                        # 推送状态更新消息
                        message = {
                            "type": "state_update",
                            "data": {
                                "tick": current_state.tick,
                                "elevators": elevators_data,
                                "floors": floors_data,
                                "events": [
                                    {
                                        "type": event.type.value,
                                        "data": event.data
                                    }
                                    for event in (current_state.events or [])
                                ],
                            }
                        }

                        if self.event_queue:
                            self.event_queue.put(message)

                        last_tick = current_state.tick

                    # 轮询间隔
                    time.sleep(poll_interval)

                except Exception as e:
                    print(f"[GUI] 轮询错误: {e}")
                    time.sleep(0.5)

        except Exception as e:
            print(f"[GUI] 事件循环出错: {e}")
            raise

    def on_init(self, elevators: List[ProxyElevator], floors: List[ProxyFloor]) -> None:
        """初始化 - 立刻推送初始化消息给前端"""
        print(f"[GUI] 初始化: {len(elevators)} 部电梯，{len(floors)} 层楼")

        # 构建初始化消息
        message = {
            "type": "init",
            "data": {
                "elevators_count": len(elevators),
                "floors_count": len(floors),
                "tick": 0
            }
        }

        # 推送到事件队列（给 WebSocket 转发给前端）
        if self.event_queue:
            self.event_queue.put(message)

        # 调用回调函数（备用）
        if self.event_callback:
            self.event_callback(message)

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

        # 转换events为字典格式（用于前端显示）
        events_data = []
        if events:
            for event in events:
                events_data.append({
                    "type": event.type.value,
                    "data": event.data
                })

        # 构建消息
        message = {
            "type": "state_update",
            "data": {
                "tick": tick,
                "elevators": elevators_data,
                "floors": floors_data,
                "events": events_data,
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
