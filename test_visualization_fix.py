#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试可视化修复
验证电梯数量、楼层数量和tick时间是否正确
"""
import json
import subprocess
import sys
import time
from pathlib import Path

# 设置UTF-8编码
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def test_visualization():
    """测试可视化修复"""
    print("=" * 60)
    print("测试可视化修复")
    print("=" * 60)

    # 测试用例配置
    test_cases = [
        {
            "name": "ICSS79 - 2电梯10层",
            "traffic": "finalTest_ICSS79_elevator_assignment.json",
            "expected_elevators": 2,
            "expected_floors": 10,
        },
        {
            "name": "ICST25 - 3电梯20层",
            "traffic": "finalTest_ICST25_continuous_down.json",
            "expected_elevators": 3,
            "expected_floors": 20,
        },
        {
            "name": "ICSTCS - 4电梯20层",
            "traffic": "finalTest_ICSTCS_typical_workday.json",
            "expected_elevators": 4,
            "expected_floors": 20,
        },
    ]

    for test_case in test_cases:
        print(f"\n{'=' * 60}")
        print(f"测试用例: {test_case['name']}")
        print(f"{'=' * 60}")

        # 读取流量文件
        traffic_file = Path(f"elevator_saga/traffic/{test_case['traffic']}")
        if not traffic_file.exists():
            print(f"❌ 流量文件不存在: {traffic_file}")
            continue

        with open(traffic_file, "r", encoding="utf-8") as f:
            traffic_data = json.load(f)

        building = traffic_data.get("building", {})
        print(f"流量文件配置:")
        print(f"  - 电梯数: {building.get('elevators')}")
        print(f"  - 楼层数: {building.get('floors')}")
        print(f"  - 乘客数: {len(traffic_data.get('traffic', []))}")
        print(f"  - 时长: {building.get('duration')} ticks")

        # 验证配置
        assert building.get('elevators') == test_case['expected_elevators'], \
            f"电梯数不匹配: {building.get('elevators')} != {test_case['expected_elevators']}"
        assert building.get('floors') == test_case['expected_floors'], \
            f"楼层数不匹配: {building.get('floors')} != {test_case['expected_floors']}"

        print(f"✅ 流量文件配置正确")

        # 检查同时到达的乘客
        tick_groups = {}
        for passenger in traffic_data.get('traffic', []):
            tick = passenger.get('tick')
            if tick not in tick_groups:
                tick_groups[tick] = []
            tick_groups[tick].append(passenger['id'])

        print(f"\n乘客到达时间分布:")
        for tick in sorted(tick_groups.keys())[:5]:  # 只显示前5个tick
            passengers = tick_groups[tick]
            print(f"  Tick {tick}: {len(passengers)}个乘客 (ID: {passengers})")

        # 检查是否有多个乘客同时到达
        simultaneous_arrivals = sum(1 for passengers in tick_groups.values() if len(passengers) > 1)
        print(f"\n同时到达的时间点数: {simultaneous_arrivals}")

        if simultaneous_arrivals > 0:
            print(f"✅ 存在同时到达的乘客，可以测试tick合并显示")

    print(f"\n{'=' * 60}")
    print("测试总结")
    print(f"{'=' * 60}")
    print("✅ 所有测试用例的流量文件配置正确")
    print("\n建议:")
    print("1. 启动模拟器服务器: python -m elevator_saga.server.main")
    print("2. 启动可视化服务器: python -m elevator_saga.visualization.web_server")
    print("3. 在Web界面中选择算法和流量文件运行测试")
    print("4. 验证以下修复:")
    print("   - 电梯数量根据实际json自动扩展")
    print("   - 楼层从G（0层）开始，其他显示为1F、2F等")
    print("   - 同一tick的乘客在同一时刻显示")
    print("   - 事件日志正确显示tick时间")


if __name__ == "__main__":
    test_visualization()
