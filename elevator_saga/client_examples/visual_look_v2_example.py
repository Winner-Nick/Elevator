#!/usr/bin/env python3
"""
可视化LOOK V2电梯调度示例
基于look_v2_example，增加状态记录和Web可视化功能
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from elevator_saga.client_examples.look_v2_example import LookV2Controller
from elevator_saga.client.proxy_models import ProxyElevator, ProxyFloor, ProxyPassenger
from elevator_saga.core.models import SimulationEvent
from elevator_saga.client.base_controller import ElevatorController


class VisualLookV2Controller(LookV2Controller):
    """
    可视化LOOK V2电梯调度控制器
    在look_v2_example基础上增加状态记录功能，用于Web可视化
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
            self.recording_path = str(recordings_dir / f"look_v2_simulation_{timestamp}.json")
            print(f"📹 开始记录LOOK V2调度到: {self.recording_path}")

            # 记录初始状态
            self._record_state(0, [], "init")

    def on_event_execute_start(
        self, tick: int, events: List[SimulationEvent], elevators: List[ProxyElevator], floors: List[ProxyFloor]
    ) -> None:
        """事件执行前 - 不记录，避免每个tick记录多次"""
        super().on_event_execute_start(tick, events, elevators, floors)

    def on_event_execute_end(
        self, tick: int, events: List[SimulationEvent], elevators: List[ProxyElevator], floors: List[ProxyFloor]
    ) -> None:
        """事件执行后记录状态 - 每个tick只记录一次"""
        super().on_event_execute_end(tick, events, elevators, floors)
        if self.record:
            self._record_state(tick, events, "tick")

    def _record_state(self, tick: int, events: List[SimulationEvent], phase: str) -> None:
        """
        记录当前状态快照

        Args:
            tick: 当前tick
            events: 事件列表
            phase: 阶段标识（init/tick_start/tick_end）
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
            # LOOK V2特有信息
            "algorithm_state": {
                "elevator_scan_directions": {
                    str(eid): direction.value
                    for eid, direction in self.elevator_scan_direction.items()
                },
                "tracked_passengers": len(self.passenger_destinations),
            }
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
                # 添加LOOK V2的扫描方向
                "scan_direction": self.elevator_scan_direction.get(elevator_state.id, "STOPPED").value if elevator_state.id in self.elevator_scan_direction else "STOPPED",
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
            # 计算最终指标
            final_metrics = self.history[-1]["metrics"] if self.history else {}

            # 构建完整记录数据
            recording_data = {
                "metadata": {
                    "controller": self.__class__.__name__,
                    "algorithm": "LOOK V2 (实时决策版)",
                    "description": "简洁的实时决策LOOK算法，动态选择下一个目标楼层",
                    "start_time": self.history[0]["timestamp"] if self.history else "",
                    "end_time": self.history[-1]["timestamp"] if self.history else "",
                    "total_ticks": len(self.history),
                    "num_elevators": len(self.elevators),
                    "num_floors": len(self.floors),
                    "final_metrics": final_metrics,
                },
                "history": self.history,
            }

            # 保存到JSON文件
            with open(self.recording_path, "w", encoding="utf-8") as f:
                json.dump(recording_data, f, ensure_ascii=False, indent=2)

            print(f"✅ LOOK V2调度记录已保存: {self.recording_path}")
            print(f"   共记录 {len(self.history)} 个状态快照")

            # 打印性能总结
            if final_metrics:
                print(f"\n📊 性能总结:")
                print(f"   完成乘客: {final_metrics.get('done', 0)}/{final_metrics.get('total', 0)}")
                print(f"   平均等待: {final_metrics.get('avg_wait', 0):.1f} ticks")
                print(f"   P95等待: {final_metrics.get('p95_wait', 0):.1f} ticks")
                print(f"   平均系统时间: {final_metrics.get('avg_system', 0):.1f} ticks")
                print(f"   P95系统时间: {final_metrics.get('p95_system', 0):.1f} ticks")
        except Exception as e:
            print(f"❌ 保存记录失败: {e}")


if __name__ == "__main__":
    # 启动可视化LOOK V2控制器
    algorithm = VisualLookV2Controller(debug=False, record=True)
    algorithm.start()

    # 提示用户
    print("\n" + "=" * 60)
    print("✅ LOOK V2调度模拟完成！")
    print(f"📁 记录文件: {algorithm.recording_path}")
    print("🌐 请运行 Web 服务器查看可视化界面:")
    print("   python -m elevator_saga.visualization.web_server")
    print("=" * 60)
