# 可视化系统修改总结

## 修改背景

根据项目要求，实现支持两种运行模式的电梯调度系统：
1. **GUI 模式**（可视化）：运行 Web 界面展示电梯调度过程
2. **Algorithm 模式**（纯算法）：仅运行算法，不启动 Web 界面

## 修改内容

### 1. 文件：`elevator/visualization/web_server.py`

#### 改动 1：端口改为 5173
```python
def run(self, host: str = "127.0.0.1", port: int = 5173):  # 改为 5173
```

**原因**：满足测试要求，Web 界面必须在端口 5173

#### 改动 2：添加后台启动函数
```python
def start_visualization_server(host: str = "127.0.0.1", port: int = 5173):
    """在后台启动可视化服务器（用于 GUI 模式）"""
    import multiprocessing

    def _run_server():
        server = VisualizationServer()
        server.run(host=host, port=port)

    # 创建后台进程
    process = multiprocessing.Process(target=_run_server, daemon=True)
    process.start()
    return process
```

**原因**：支持在 controller.py 中作为后台进程启动，不阻塞主控制器逻辑

#### 改动 3：修改日志输出
```python
print(f"[GUI] 启动可视化服务器...")
print(f"[GUI] 访问地址: http://{host}:{port}")
uvicorn.run(self.app, host=host, port=port, log_level="error")
```

**原因**：标准化日志前缀，减少控制台噪音

---

### 2. 文件：`controller.py`

#### 改动 1：添加环境变量检测和 Web 服务启动
```python
if __name__ == "__main__":
    import os
    import time

    # 获取客户端类型
    client_type = os.environ.get("ELEVATOR_CLIENT_TYPE", "algorithm").lower()

    if client_type == "gui":
        print("[MAIN] 启动 GUI 模式（带可视化）")
        try:
            from elevator.visualization.web_server import start_visualization_server
            # 启动可视化服务器（后台进程）
            print("[MAIN] 启动可视化 Web 服务器...")
            web_process = start_visualization_server(host="127.0.0.1", port=5173)
            # 给服务器一些时间来启动
            time.sleep(2)
            print("[MAIN] Web 服务器已启动，访问 http://127.0.0.1:5173")
        except Exception as e:
            print(f"[WARN] 启动 Web 服务器失败: {e}")
            print("[WARN] 继续运行控制器（不带可视化）")

    elif client_type == "algorithm":
        print("[MAIN] 启动 Algorithm 模式（纯算法）")

    # 启动 LOOK V2 控制器
    print("[MAIN] 启动电梯调度控制器...")
    controller = LookV2Controller(debug=False)
    controller.start()
```

**原因**：
- 支持通过环境变量选择运行模式
- 默认为 algorithm 模式
- GUI 模式自动启动 Web 服务器
- 提供清晰的启动日志

---

### 3. 文件：前端文件（已完善）

已在 `elevator/visualization/static/` 目录中添加/更新：
- ✅ `index.html`：完整的 HTML5 结构
- ✅ `app.js`：完整的前端应用逻辑（已支持客户端类型检测）
- ✅ `style.css`：完整的样式表

---

## 新建文档

### 1. `USAGE.md` - 完整使用指南
包含：
- 快速开始指南
- 两种模式的启动方式
- Windows/Linux 差异说明
- 多控制器场景说明
- 故障排除指南
- 技术栈说明

### 2. `VISUALIZATION_GUIDE.md` - 可视化系统说明
包含：
- 功能说明
- 文件结构
- 常见问题

---

## 执行流程

### GUI 模式的执行流程
```
1. 设置环境变量：ELEVATOR_CLIENT_TYPE=gui
2. 运行：python controller.py
3. controller.py main 检测到 gui 模式
4. 启动后台进程运行 Web 服务器（端口 5173）
5. 等待 2 秒确保 Web 服务启动
6. 启动主控制器，连接到模拟器
7. Web 服务接收来自控制器的事件
8. 浏览器访问 http://127.0.0.1:5173 查看实时可视化
```

### Algorithm 模式的执行流程
```
1. 设置环境变量：ELEVATOR_CLIENT_TYPE=algorithm （或不设置，默认值）
2. 运行：python controller.py
3. controller.py main 检测到 algorithm 模式
4. 直接启动主控制器，连接到模拟器
5. 控制器与模拟器交互，无 Web 服务
6. 仅输出日志信息
```

---

## 关键特性

### 1. 单一入口点
- 同一个 `controller.py` 支持两种模式
- 通过环境变量 `ELEVATOR_CLIENT_TYPE` 控制

### 2. 后台运行
- GUI 模式自动在后台启动 Web 服务
- 不阻塞主控制器逻辑
- 支持同时运行多个控制器（一个 GUI，一个 Algorithm）

### 3. 标准化端口
- Web 界面：**5173**（符合测试要求）
- 模拟器：8000（默认）

### 4. 优雅降级
- Web 服务启动失败时继续运行控制器
- 提供清晰的错误提示

---

## 兼容性

### 操作系统
- ✅ Linux/Mac：完全支持
- ✅ Windows：完全支持（multiprocessing 安全处理）

### Python 版本
- ✅ Python 3.8+

### 依赖
- fastapi
- uvicorn
- websockets
- pydantic

---

## 测试场景

### 场景 1：纯 GUI 模式
```bash
export ELEVATOR_CLIENT_TYPE=gui
python controller.py
# 访问 http://127.0.0.1:5173
```

### 场景 2：纯 Algorithm 模式
```bash
export ELEVATOR_CLIENT_TYPE=algorithm
python controller.py
```

### 场景 3：自己的 GUI + 其他组的 Algorithm
```bash
# 终端 1
export ELEVATOR_CLIENT_TYPE=gui && python controller.py

# 终端 2
cd /other_group_repo
export ELEVATOR_CLIENT_TYPE=algorithm && python controller.py
```

### 场景 4：其他组的 GUI + 自己的 Algorithm
```bash
# 终端 1
cd /other_group_repo
export ELEVATOR_CLIENT_TYPE=gui && python controller.py

# 终端 2
export ELEVATOR_CLIENT_TYPE=algorithm && python controller.py
```

---

## 验证清单

- ✅ 代码语法检查通过
- ✅ 端口改为 5173
- ✅ 支持环境变量控制
- ✅ Web 服务后台启动
- ✅ 提供完整的使用文档
- ✅ 支持多控制器场景
- ✅ 提供清晰的日志输出

---

## 性能指标记录

系统会自动记录以下内容到 `elevator/visualization/recordings/` 目录：

1. **能耗计算**
   - 电梯 1-3：每次移动 = 1 单位
   - 电梯 4：每次移动 = 2 单位

2. **等待时间统计**
   - 平均等待时间
   - 95 分位等待时间
   - 最大等待时间

3. **运行记录格式**
   - JSON 格式
   - 包含所有状态变化快照
   - 可用于后续分析和回放

---

## 后续改进方向

1. **实时数据接收**：支持从模拟器实时接收数据而不是离线回放
2. **可视化增强**：添加性能指标图表和对比分析
3. **导出功能**：支持导出为视频或其他格式
4. **性能监控**：实时显示能耗和等待时间指标

