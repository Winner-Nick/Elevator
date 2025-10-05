#!/usr/bin/env python3
"""
可视化完整调度示例
基于first_example，增加状态记录和Web可视化功能
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from elevator_saga.client_examples.first_example import ElevatorBusExampleController as FirstExampleController
from elevator_saga.client.base_controller import ElevatorController
from elevator_saga.client.proxy_models import ProxyElevator, ProxyFloor
from elevator_saga.core.models import SimulationEvent


class VisualFirstExampleController(FirstExampleController):
    """
    可视化完整调度控制器
    在first_example基础上增加状态记录功能，用于Web可视化
    """

    def __init__(self, server_url: str = "http://127.0.0.1:8000", debug: bool = False, record: bool = True):
        """
        初始化可视化控制器

        Args:
            server_url: 服务器URL
            debug: 是否启用debug模式
            record: 是否记录状态历史
        """
        # 不能直接调用super().__init__()，需要手动初始化
        ElevatorController.__init__(self, server_url, debug)

        # 从FirstExampleController复制初始化
        self.all_passengers = []
        self.max_floor = 0
        self.up_stops = {}
        self.down_stops = {}
        self.pending_up_floors = set()
        self.pending_down_floors = set()
        self.all_elevators = []
        self.all_floors = []
        self.last_target = {}

        # 可视化记录相关
        self.record = record
        self.history: List[Dict[str, Any]] = []
        self.recording_path: str = ""

    def on_init(self, elevators: List[ProxyElevator], floors: List[ProxyFloor]) -> None:
        """初始化并开始记录"""
        super().on_init(elevators, floors)

        if self.record:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            recordings_dir = Path(__file__).parent.parent / "visualization" / "recordings"
            recordings_dir.mkdir(parents=True, exist_ok=True)
            self.recording_path = str(recordings_dir / f"first_example_{timestamp}.json")
            print(f"📹 开始记录完整调度到: {self.recording_path}")
            self._record_state(0, [], "init")

    def on_event_execute_end(
        self, tick: int, events: List[SimulationEvent], elevators: List[ProxyElevator], floors: List[ProxyFloor]
    ) -> None:
        """事件执行后记录状态"""
        super().on_event_execute_end(tick, events, elevators, floors)
        if self.record:
            self._record_state(tick, events, "tick_end")

    def _record_state(self, tick: int, events: List[SimulationEvent], phase: str) -> None:
        """记录当前状态快照"""
        state = self.api_client.get_state(force_reload=True)

        snapshot = {
            "tick": tick,
            "phase": phase,
            "timestamp": datetime.now().isoformat(),
            "elevators": [],
            "floors": [],
            "passengers": {},
            "events": [{"type": e.type.value, "data": e.data} for e in events],
            "metrics": state.metrics.to_dict() if state.metrics else {},
        }

        for elevator_state in state.elevators:
            elevator_data = {
                "id": elevator_state.id,
                "current_floor": elevator_state.current_floor,
                "current_floor_float": elevator_state.current_floor_float,
                "target_floor": elevator_state.target_floor,
                "direction": elevator_state.target_floor_direction.value,
                "status": elevator_state.run_status.value,
                "passengers": elevator_state.passengers,
                "passenger_destinations": elevator_state.passenger_destinations,
            }
            snapshot["elevators"].append(elevator_data)

        for floor_state in state.floors:
            floor_data = {
                "floor": floor_state.floor,
                "up_queue": floor_state.up_queue,
                "down_queue": floor_state.down_queue,
            }
            snapshot["floors"].append(floor_data)

        for passenger_id, passenger_info in state.passengers.items():
            snapshot["passengers"][str(passenger_id)] = {
                "id": passenger_info.id,
                "origin": passenger_info.origin,
                "destination": passenger_info.destination,
                "status": passenger_info.status.value,
                "arrive_tick": passenger_info.arrive_tick,
                "pickup_tick": passenger_info.pickup_tick,
                "dropoff_tick": passenger_info.dropoff_tick,
                "elevator_id": passenger_info.elevator_id,
            }

        self.history.append(snapshot)

    def on_stop(self) -> None:
        """停止时保存记录"""
        super().on_stop()
        if self.record and self.history:
            self._save_recording()

    def _save_recording(self) -> None:
        """保存记录到文件"""
        try:
            recording_data = {
                "metadata": {
                    "controller": self.__class__.__name__,
                    "algorithm": "First Example (完整调度算法)",
                    "start_time": self.history[0]["timestamp"] if self.history else "",
                    "end_time": self.history[-1]["timestamp"] if self.history else "",
                    "total_ticks": len(self.history),
                    "num_elevators": len(self.elevators),
                    "num_floors": len(self.floors),
                },
                "history": self.history,
            }

            with open(self.recording_path, "w", encoding="utf-8") as f:
                json.dump(recording_data, f, ensure_ascii=False, indent=2)

            print(f"✅ 完整调度记录已保存: {self.recording_path}")
            print(f"   共记录 {len(self.history)} 个状态快照")
        except Exception as e:
            print(f"❌ 保存记录失败: {e}")


if __name__ == "__main__":
    algorithm = VisualFirstExampleController(debug=True, record=True)
    algorithm.start()

    print("\n" + "=" * 60)
    print("✅ 完整调度模拟完成！")
    print(f"📁 记录文件: {algorithm.recording_path}")
    print("🌐 请运行 Web 服务器查看可视化界面:")
    print("   python -m elevator_saga.visualization.web_server")
    print("=" * 60)
