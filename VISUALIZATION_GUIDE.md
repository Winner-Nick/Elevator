# 电梯调度可视化系统 - 使用指南

## 概述
修复后的可视化系统支持两种运行模式：
- **GUI 模式** (`ELEVATOR_CLIENT_TYPE=gui`): 纯查看模式，仅显示回放历史记录
- **Algorithm 模式** (`ELEVATOR_CLIENT_TYPE=algorithm`): 完整模式，支持运行算法和查看结果

## 安装与启动

### 方式 1: GUI 模式（仅查看已有记录）

```bash
# 设置环境变量为 gui
export ELEVATOR_CLIENT_TYPE=gui

# 启动可视化服务器
python -m elevator.visualization.web_server

# 或者
python elevator/visualization/web_server.py
```

访问 http://127.0.0.1:8080 即可查看和播放记录。

### 方式 2: Algorithm 模式（运行算法并记录）

```bash
# 设置环境变量为 algorithm
export ELEVATOR_CLIENT_TYPE=algorithm

# 启动可视化服务器
python -m elevator.visualization.web_server

# 或者
python elevator/visualization/web_server.py
```

访问 http://127.0.0.1:8080 可以选择算法和流量文件进行仿真，并查看结果。

### Windows 上的设置方式

```cmd
# CMD
set ELEVATOR_CLIENT_TYPE=gui
python elevator/visualization/web_server.py

# PowerShell
$env:ELEVATOR_CLIENT_TYPE="gui"
python elevator/visualization/web_server.py
```

## 功能说明

### 共有功能（两种模式都支持）

#### 播放控制
- **▶️ 播放**: 自动播放历史记录
- **⏸️ 暂停**: 暂停当前播放
- **⏮️ 重置**: 回到第一帧
- **播放速度**: 拖动滑块调整速度（0.1x ~ 5x）
- **进度条**: 拖动可跳转到任意时刻

#### 记录管理
- **选择记录文件**: 下拉菜单选择已有的记录文件
- **加载**: 手动加载选中的记录文件
- **🔄 刷新列表**: 刷新记录文件列表

#### 可视化显示
- **建筑视图**: 显示电梯井道、楼层和等待队列
  - 上行电梯: 蓝色渐变
  - 下行电梯: 橙红渐变
  - 停止电梯: 浅色渐变
- **统计信息**: 显示乘客统计和平均等待时间
- **事件日志**: 实时显示关键事件，支持按类型筛选

### Algorithm 模式专有功能

#### 仿真运行
- **选择算法**: 从下拉菜单选择要运行的算法
- **选择流量文件**: 从下拉菜单选择流量文件
- **▶️ 运行仿真**: 执行选中的算法和流量文件组合
- **状态显示**: 实时显示运行状态（运行中、成功、失败）

运行完成后，新的记录会自动加载到记录列表中。

## 新增功能

### 环境变量支持
- `ELEVATOR_CLIENT_TYPE`: 设置客户端类型
  - `gui`: 纯查看模式（默认）
  - `algorithm`: 完整模式

### API 端点
- `GET /api/client_type`: 获取当前客户端类型
  ```json
  {
    "client_type": "gui"
  }
  ```

## 文件结构

```
elevator/visualization/
├── __init__.py
├── web_server.py           # FastAPI 服务器（已修改）
├── recorder.py             # 运行记录器
├── README.md               # 原始文档
├── recordings/             # 记录文件目录
│   └── *.json             # 仿真记录
└── static/                # 前端文件
    ├── index.html         # 主页面（已更新）
    ├── app.js             # 前端应用（已更新）
    └── style.css          # 样式表（已添加）
```

## 修改概览

### web_server.py 的改动
- ✅ 导入 `os` 模块获取环境变量
- ✅ 读取 `ELEVATOR_CLIENT_TYPE` 环境变量
- ✅ 添加 `/api/client_type` API 端点

### app.js 的改动
- ✅ 添加 `checkClientType()` 方法
- ✅ 修改 constructor 使其异步初始化
- ✅ 在 `initUI()` 中根据客户端类型隐藏/显示运行算法功能

### index.html 和 style.css
- ✅ 替换为参考版本的完整前端代码
- ✅ 支持完整的电梯可视化和控制功能

## 故障排除

### 问题: 运行算法功能没有显示
**解决**: 确保环境变量 `ELEVATOR_CLIENT_TYPE` 设置为 `algorithm` 或其他非 `gui` 的值

### 问题: WebSocket 连接失败
**解决**:
1. 确认可视化服务器正常运行
2. 检查浏览器控制台错误信息
3. 确保端口 8080 没有被其他应用占用

### 问题: 记录文件为空
**解决**:
1. 确保有正确的仿真记录被保存到 `recordings/` 目录
2. 点击 "🔄 刷新列表" 重新加载列表

## 下一步改进

根据用户需求，后续可能的改进方向：

1. **实时数据接收**: 从运行中的模拟器实时接收数据（目前是运行完成后保存）
2. **数据可视化增强**: 添加性能指标图表（折线图、柱状图）
3. **对比分析**: 支持对比多个算法的运行结果
4. **导出功能**: 支持导出为视频或 GIF

## 技术栈

- **后端**: Python, FastAPI, WebSocket, Uvicorn
- **前端**: 原生 HTML5/CSS3/JavaScript (无框架依赖)
- **通信**: WebSocket 实时推送 + HTTP REST API

## 支持

如有问题，请检查：
1. 环境变量设置是否正确
2. 端口 8080 是否被占用
3. 静态文件 (html, css, js) 是否完整存在
4. 记录目录 `recordings/` 是否有权限读写
