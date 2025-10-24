# 电梯调度系统 - 完整使用指南

## 概述

本系统支持两种运行模式，通过 `ELEVATOR_CLIENT_TYPE` 环境变量控制：

| 模式 | 环境变量 | 说明 | 端口 |
|------|--------|------|------|
| **GUI 模式** | `ELEVATOR_CLIENT_TYPE=gui` | 启动可视化 Web 界面 + 算法控制器 | 5173 |
| **Algorithm 模式** | `ELEVATOR_CLIENT_TYPE=algorithm` | 纯算法模式（无 GUI） | - |

## 快速开始

### 前置条件

确保已安装必要的依赖：
```bash
pip install fastapi uvicorn websockets pydantic
```

### 方式一：GUI 模式（启动可视化）

```bash
# 设置环境变量为 GUI 模式
export ELEVATOR_CLIENT_TYPE=gui

# 启动控制器（自动启动 Web 服务）
python controller.py
```

输出示例：
```
[MAIN] 启动 GUI 模式（带可视化）
[MAIN] 启动可视化 Web 服务器...
[GUI] 启动可视化服务器...
[GUI] 访问地址: http://127.0.0.1:5173
[GUI] 记录目录: elevator/visualization/recordings
[MAIN] Web 服务器已启动，访问 http://127.0.0.1:5173
[MAIN] 启动电梯调度控制器...
[LOOK V2] 算法初始化...
```

然后在浏览器中打开：**http://127.0.0.1:5173**

### 方式二：Algorithm 模式（纯算法）

```bash
# 设置环境变量为 Algorithm 模式
export ELEVATOR_CLIENT_TYPE=algorithm

# 启动控制器（仅运行算法，无 Web 服务）
python controller.py
```

输出示例：
```
[MAIN] 启动 Algorithm 模式（纯算法）
[MAIN] 启动电梯调度控制器...
[LOOK V2] 算法初始化...
```

## Windows 上的设置

### CMD 命令行
```cmd
set ELEVATOR_CLIENT_TYPE=gui
python controller.py
```

### PowerShell
```powershell
$env:ELEVATOR_CLIENT_TYPE="gui"
python controller.py
```

## 详细说明

### GUI 模式的工作流程

1. **启动阶段**
   - 设置环境变量：`ELEVATOR_CLIENT_TYPE=gui`
   - 运行：`python controller.py`
   - 系统自动在后台启动 Web 服务器（端口 5173）

2. **Web 界面功能**
   - **播放控制**：▶️ 播放、⏸️ 暂停、⏮️ 重置
   - **速度调节**：0.1x ~ 5x 可调
   - **电梯可视化**：实时显示电梯位置和方向
   - **乘客队列**：显示各楼层等待的乘客
   - **统计信息**：总人数、已送达、运送中、等待中
   - **事件日志**：实时显示系统事件

3. **记录管理**
   - 每次仿真运行后自动保存记录到 `elevator/visualization/recordings/`
   - 可在 Web 界面选择历史记录查看

### Algorithm 模式的工作流程

1. **启动阶段**
   - 设置环境变量：`ELEVATOR_CLIENT_TYPE=algorithm`
   - 运行：`python controller.py`
   - 系统仅运行算法，不启动 Web 服务

2. **与模拟器交互**
   - 控制器连接到模拟器（默认 `http://127.0.0.1:8000`）
   - 接收电梯事件和乘客信息
   - 决策和发送命令给模拟器

## 多控制器场景（组间对接）

### 场景：运行自己的 GUI 和其他组的 Algorithm

**步骤 1：启动自己的 GUI**
```bash
export ELEVATOR_CLIENT_TYPE=gui
python controller.py
```

**步骤 2：启动其他组的 Algorithm（在另一个终端）**
```bash
cd /path/to/other_group_repo
export ELEVATOR_CLIENT_TYPE=algorithm
python controller.py
```

**结果**：
- 模拟器检测到两个控制器连接
- 自己的 GUI 控制器只接收事件（不响应命令）
- 其他组的 Algorithm 控制器正常交互
- Web 界面（5173 端口）显示实时可视化

### 场景：运行其他组的 GUI 和自己的 Algorithm

**步骤 1：启动其他组的 GUI**
```bash
cd /path/to/other_group_repo
export ELEVATOR_CLIENT_TYPE=gui
python controller.py
# 访问他们的 Web 界面
```

**步骤 2：启动自己的 Algorithm（在另一个终端）**
```bash
export ELEVATOR_CLIENT_TYPE=algorithm
python controller.py
```

## 端口说明

| 服务 | 端口 | 说明 |
|------|------|------|
| GUI Web 界面 | **5173** | 可视化界面，HTTP |
| GUI WebSocket | **5173** | 实时数据推送，WS/WSS |
| 模拟器 | 8000 | 默认模拟器地址 |

## 环境变量参考

```bash
# 设置客户端类型
export ELEVATOR_CLIENT_TYPE=gui       # 启用 GUI 模式
export ELEVATOR_CLIENT_TYPE=algorithm # 启用 Algorithm 模式

# 可选：设置模拟器地址（如果需要）
export ELEVATOR_SERVER_URL=http://127.0.0.1:8000
```

## 故障排除

### 问题 1：Web 界面打不开

**症状**：浏览器访问 http://127.0.0.1:5173 无响应

**检查清单**：
1. 确认环境变量设置正确：`echo $ELEVATOR_CLIENT_TYPE`（应显示 `gui`）
2. 检查控制台输出是否有 Web 服务启动的日志
3. 检查端口 5173 是否被占用：
   ```bash
   # Linux/Mac
   lsof -i :5173
   # Windows
   netstat -ano | findstr :5173
   ```

**解决方案**：
- 如果端口被占用，关闭占用的程序或修改代码中的端口号
- 如果 Web 服务启动失败，检查控制台错误信息

### 问题 2：Algorithm 无法连接模拟器

**症状**：Algorithm 模式启动但无任何输出或错误

**检查清单**：
1. 确认模拟器已启动（应在 http://127.0.0.1:8000）
2. 确认环境变量设置正确：`echo $ELEVATOR_CLIENT_TYPE`（应显示 `algorithm`）

**解决方案**：
- 启动模拟器（通常由比赛方提供）
- 确保网络连接正常

### 问题 3：两个控制器都无法启动

**症状**：启动第二个控制器时报错

**原因**：模拟器可能已经有两个控制器连接，不允许第三个

**解决方案**：
- 停止其中一个控制器
- 确保只有两个控制器同时运行

## 性能指标

系统会记录以下关键性能指标：

- **总能耗**：
  - 电梯 1-3：每次移动消耗 1
  - 电梯 4：每次移动消耗 2

- **等待时间**：
  - 平均等待时间（Tick）
  - 95 分位等待时间
  - 最大等待时间

- **系统时间**：
  - 平均系统时间（从呼叫到送达）
  - 95 分位系统时间

## 技术栈

- **后端**：Python, FastAPI, Uvicorn
- **前端**：HTML5, CSS3, JavaScript (原生)
- **通信**：WebSocket (实时推送) + HTTP (REST API)
- **并发**：Multiprocessing (Web 服务后台运行)

## 常见命令

```bash
# 运行 GUI 模式
export ELEVATOR_CLIENT_TYPE=gui && python controller.py

# 运行 Algorithm 模式
export ELEVATOR_CLIENT_TYPE=algorithm && python controller.py

# 同时运行两个模式（两个终端）
# 终端 1：
export ELEVATOR_CLIENT_TYPE=gui && python controller.py

# 终端 2：
export ELEVATOR_CLIENT_TYPE=algorithm && python controller.py

# 查看帮助信息（如果支持）
python controller.py --help
```

## 下一步

1. **配置模拟器**：确保模拟器服务器正常运行
2. **测试 GUI**：访问 http://127.0.0.1:5173 验证界面
3. **运行仿真**：启动 Algorithm 模式进行调度
4. **分析结果**：查看 Web 界面中的可视化和指标

## 支持

如有问题，请：
1. 检查环境变量设置
2. 查看控制台输出中的错误信息
3. 确保所有必要的依赖已安装
4. 验证网络连接和防火墙设置
