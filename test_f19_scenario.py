#!/usr/bin/env python3
"""
测试F19场景：电梯到达后方向不匹配的情况
"""
import sys
sys.path.insert(0, "E:\\wood\\wps\\1728956286\\WPS企业云盘\\北京中关村学院\\我的企业文档\\wood\\project\\Elevator")

from elevator_saga.client_examples.look_v2_example import LookV2Controller

# 启动测试
print("=" * 60)
print("测试场景：15人在F19等待向下，电梯从F0出发")
print("=" * 60)

controller = LookV2Controller(debug=True)

# 模拟场景
print("\n注意：这个测试只能通过实际运行模拟器来验证")
print("请在主程序中观察电梯行为：")
print("1. 电梯应该从F0上升到F19")
print("2. 到达F19时方向是UP，但乘客是down_queue")
print("3. 电梯空闲，触发idle")
print("4. idle应该检测到方向不匹配，移动到F18")
print("5. 从F18回到F19，此时方向是DOWN，可以接乘客")

# 启动控制器（连接到模拟器）
controller.start()
