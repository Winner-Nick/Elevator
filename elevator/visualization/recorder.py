#!/usr/bin/env python3
"""
运行记录器 - 自动记录电梯调度过程
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from elevator.core.models import SimulationState, SimulationEvent


class SimulationRecorder:
    """模拟运行记录器 - 记录所有事件和状态变化"""

    def __init__(self, output_dir: Optional[Path] = None):
        """
        初始化记录器

        Args:
            output_dir: 输出目录，默认为visualization/recordings
        """
        if output_dir is None:
            output_dir = Path(__file__).parent / "recordings"

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 记录数据
        self.metadata: Dict[str, Any] = {
            "start_time": datetime.now().isoformat(),
            "algorithm": "Unknown",
            "elevators": 0,
            "floors": 0,
            "total_passengers": 0,
            "completed_passengers": 0,
        }

        self.history: List[Dict[str, Any]] = []
        self.building_config: Dict[str, Any] = {}

    def set_metadata(
        self,
        algorithm: str,
        elevators: int,
        floors: int,
        total_passengers: int = 0,
    ):
        """设置元数据"""
        self.metadata["algorithm"] = algorithm
        self.metadata["elevators"] = elevators
        self.metadata["floors"] = floors
        self.metadata["total_passengers"] = total_passengers

    def record_state(self, state: SimulationState, events: List[SimulationEvent] = None):
        """
        记录状态快照

        Args:
            state: 模拟状态
            events: 发生的事件列表
        """
        if events is None:
            events = []

        # 提取电梯信息
        elevators_data = []
        for elevator in state.elevators:
            # 处理position可能是dict或Position对象的情况
            position = elevator.position
            if isinstance(position, dict):
                current_floor = position.get("current_floor", 0)
                target_floor = position.get("target_floor", 0)
            else:
                current_floor = position.current_floor
                target_floor = position.target_floor

            elevators_data.append(
                {
                    "id": elevator.id,
                    "current_floor": current_floor,
                    "target_floor": target_floor,
                    "direction": elevator.last_tick_direction.value,
                    "status": elevator.run_status.value,
                    "passengers": elevator.passengers,
                    "load": len(elevator.passengers),
                }
            )

        # 提取楼层信息
        floors_data = []
        for floor in state.floors:
            floors_data.append(
                {
                    "floor": floor.floor,
                    "up_waiting": len(floor.up_queue),
                    "down_waiting": len(floor.down_queue),
                }
            )

        # 提取事件信息
        events_data = []
        for event in events:
            events_data.append(
                {
                    "type": event.type.value,
                    "data": event.data,
                }
            )

        # 创建快照
        snapshot = {
            "tick": state.tick,
            "timestamp": datetime.now().isoformat(),
            "elevators": elevators_data,
            "floors": floors_data,
            "metrics": {
                "completed_passengers": state.metrics.completed_passengers,
                "total_passengers": state.metrics.total_passengers,
                "average_wait_time": state.metrics.average_wait_time,
                "p95_wait_time": state.metrics.p95_wait_time,
                "average_system_time": state.metrics.average_system_time,
                "p95_system_time": state.metrics.p95_system_time,
            },
            "events": events_data,
        }

        self.history.append(snapshot)
        # 更新元数据
        self.metadata["completed_passengers"] = state.metrics.completed_passengers
        self.metadata["total_passengers"] = state.metrics.total_passengers

    def save(self, filename: Optional[str] = None) -> Path:
        """
        保存记录到JSON文件

        Args:
            filename: 文件名，如不提供则自动生成

        Returns:
            保存的文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            algorithm_name = self.metadata.get("algorithm", "unknown").replace(" ", "_")
            filename = f"{algorithm_name}_{timestamp}.json"

        file_path = self.output_dir / filename

        # 添加元数据
        data = {
            "metadata": {
                **self.metadata,
                "end_time": datetime.now().isoformat(),
                "total_ticks": len(self.history),
            },
            "history": self.history,
        }

        # 保存为JSON
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 使用 ensure_ascii=True 来避免编码问题
        print(f"[OK] Recording saved: {file_path}", flush=True)
        return file_path
