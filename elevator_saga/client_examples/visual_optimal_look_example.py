#!/usr/bin/env python3
"""
可视化 Optimal LOOK 电梯调度示例
基于optimal_look_example，增加状态记录和Web可视化功能
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from elevator_saga.client_examples.optimal_look_example import OptimalLookController
from elevator_saga.client.proxy_models import ProxyElevator, ProxyFloor
from elevator_saga.core.models import SimulationEvent


class VisualOptimalLookController(OptimalLookController):
    """
    可视化 Optimal LOOK 电梯调度控制器
    在optimal_look_example基础上增加状态记录功能，用于Web可视化
    """

    def __init__(self, server_url: str = "http://127.0.0.1:8000", debug: bool = False, record: bool = True):
        """
        初始化可视化控制器

        Args:
            server_url: 服务器URL
            debug: 是否启用debug模式
            record: 是否记录状态历史
        """
        super().__init__(server_url, debug)

        self.record = record
        self.history: List[Dict[str, Any]] = []  # 状态历史记录
        self.recording_path: str = ""  # 记录文件路径

    def on_init(self, elevators: List[ProxyElevator], floors: List[ProxyFloor]) -> None:
        """初始化并开始记录"""
        super().on_init(elevators, floors)

        if self.record:
            # 创建记录文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            recordings_dir = Path(__file__).parent.parent / "visualization" / "recordings"
            recordings_dir.mkdir(parents=True, exist_ok=True)
            self.recording_path = str(recordings_dir / f"optimal_look_{timestamp}.json")
            print(f"[RECORD] 开始记录 Optimal LOOK 调度到: {self.recording_path}")

            # 记录初始状态
            self._record_state(0, [], "init")

    def on_event_execute_end(
        self, tick: int, events: List[SimulationEvent], elevators: List[ProxyElevator], floors: List[ProxyFloor]
    ) -> None:
        """事件执行后记录状态"""
        super().on_event_execute_end(tick, events, elevators, floors)

        if self.record:
            self._record_state(tick, events, "tick_end")

    def _record_state(self, tick: int, events: List[SimulationEvent], phase: str) -> None:
        """
        记录当前状态快照

        Args:
            tick: 当前tick
            events: 事件列表
            phase: 阶段标识（init/tick_end）
        """
        # 获取当前状态（强制刷新，避免缓存问题）
        state = self.api_client.get_state(force_reload=True)

        # 构建状态快照
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

        # 记录电梯状态
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

        # 记录楼层状态
        for floor_state in state.floors:
            floor_data = {
                "floor": floor_state.floor,
                "up_queue": floor_state.up_queue,
                "down_queue": floor_state.down_queue,
            }
            snapshot["floors"].append(floor_data)

        # 记录乘客信息
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
            # 构建完整记录数据
            recording_data = {
                "metadata": {
                    "controller": self.__class__.__name__,
                    "algorithm": "Optimal LOOK (优化查找算法)",
                    "start_time": self.history[0]["timestamp"] if self.history else "",
                    "end_time": self.history[-1]["timestamp"] if self.history else "",
                    "total_ticks": len(self.history),
                    "num_elevators": len(self.elevators),
                    "num_floors": len(self.floors),
                },
                "history": self.history,
            }

            # 保存到JSON文件
            with open(self.recording_path, "w", encoding="utf-8") as f:
                json.dump(recording_data, f, ensure_ascii=False, indent=2)

            print(f"[SUCCESS] Optimal LOOK 调度记录已保存: {self.recording_path}")
            print(f"   共记录 {len(self.history)} 个状态快照")

            # 获取最终性能指标
            if self.history:
                final_metrics = self.history[-1]["metrics"]
                print(f"\n[METRICS] 性能指标:")
                print(f"   完成乘客数: {final_metrics.get('completed_passengers', 0)}")
                print(f"   平均等待时间: {final_metrics.get('average_wait_time', 0):.2f} ticks")
                print(f"   P95等待时间: {final_metrics.get('p95_wait_time', 0):.2f} ticks")
                print(f"   平均系统时间: {final_metrics.get('average_system_time', 0):.2f} ticks")
                print(f"   P95系统时间: {final_metrics.get('p95_system_time', 0):.2f} ticks")

        except Exception as e:
            print(f"[ERROR] 保存记录失败: {e}")


if __name__ == "__main__":
    # 启动可视化 Optimal LOOK 控制器
    algorithm = VisualOptimalLookController(debug=True, record=True)
    algorithm.start()

    # 提示用户
    print("\n" + "=" * 60)
    print("[COMPLETE] Optimal LOOK 调度模拟完成！")
    print(f"[FILE] 记录文件: {algorithm.recording_path}")
    print("[WEB] 请运行 Web 服务器查看可视化界面:")
    print("   python -m elevator_saga.visualization.web_server")
    print("=" * 60)
