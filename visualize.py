#!/usr/bin/env python3
"""
电梯调度可视化系统 - 启动可视化Web界面

这个脚本启动可视化服务器，允许用户通过Web界面：
1. 选择算法和流量文件
2. 运行模拟
3. 查看运行结果的可视化

使用方法：
    python visualize.py              # 启动可视化服务器
"""

if __name__ == "__main__":
    from elevator.visualization.web_server import VisualizationServer

    server = VisualizationServer()
    server.run(host="127.0.0.1", port=8080)
