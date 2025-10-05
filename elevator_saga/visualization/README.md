# 电梯调度可视化系统

基于Web的电梯调度算法可视化工具，支持录制回放、速度控制、历史记录管理。

## 功能特性

- ✅ 实时记录电梯调度过程
- ✅ 美观的Web界面展示
- ✅ 可调速度回放（0.1x ~ 5x）
- ✅ 历史记录自动保存
- ✅ 支持多个记录文件管理
- ✅ 详细的事件日志
- ✅ 统计信息面板

## 使用方法

### 1. 运行模拟并记录

```bash
# 方法1: 直接运行可视化示例
python -m elevator_saga.client_examples.visual_example

# 方法2: 使用命令行
python elevator_saga/client_examples/visual_example.py
```

运行后会：
- 执行电梯调度模拟
- 自动记录每个tick的状态
- 保存到 `elevator_saga/visualization/recordings/` 目录

### 2. 启动Web服务器

```bash
# 方法1: 使用模块方式
python -m elevator_saga.visualization.web_server

# 方法2: 直接运行
python elevator_saga/visualization/web_server.py
```

默认访问地址: http://127.0.0.1:8080

### 3. 查看可视化

1. 在浏览器中打开 http://127.0.0.1:8080
2. 选择要查看的记录文件
3. 点击"加载"按钮
4. 使用播放控制按钮控制回放

## 界面说明

### 控制面板
- **▶️ 播放**: 开始自动播放
- **⏸️ 暂停**: 暂停播放
- **⏮️ 重置**: 回到第一帧
- **播放速度**: 拖动滑块调整速度（0.1x ~ 5x）
- **进度条**: 拖动可跳转到任意时刻

### 主视图
- **楼层标签**: 左侧显示楼层号（F0, F1, ...）
- **电梯井道**: 中间显示每部电梯的实时位置和状态
  - 蓝色渐变: 上行
  - 橙红渐变: 下行
  - 浅色渐变: 停止
- **等待队列**: 右侧显示每层等待的乘客
  - ↑ 上行队列
  - ↓ 下行队列
  - 格式: `P乘客ID→F目的地`

### 统计面板
- 总乘客数
- 已送达人数
- 运送中人数
- 等待中人数
- 平均等待时间

### 事件日志
- 实时显示关键事件
- 包括按钮按下、电梯停靠、乘客上下等

## 文件结构

```
elevator_saga/visualization/
├── __init__.py
├── web_server.py           # FastAPI WebSocket服务器
├── README.md               # 本文件
├── recordings/             # 记录文件目录（自动创建）
│   └── simulation_YYYYMMDD_HHMMSS.json
└── static/                 # 前端静态文件
    ├── index.html
    ├── style.css
    └── app.js
```

## 记录文件格式

JSON格式，包含以下信息：

```json
{
  "metadata": {
    "controller": "VisualElevatorController",
    "start_time": "2025-10-05T10:00:00",
    "end_time": "2025-10-05T10:05:00",
    "total_ticks": 500,
    "num_elevators": 2,
    "num_floors": 6
  },
  "history": [
    {
      "tick": 0,
      "phase": "init",
      "elevators": [...],
      "floors": [...],
      "passengers": {...},
      "events": [...],
      "metrics": {...}
    },
    ...
  ]
}
```

## 技术栈

- **后端**: Python, FastAPI, WebSocket
- **前端**: 原生 HTML/CSS/JavaScript
- **通信**: WebSocket实时推送

## 配置说明

### 修改播放速度范围

编辑 `static/index.html` 中的速度控制滑块：

```html
<input type="range" id="speedControl" min="0.1" max="5" step="0.1" value="1.0">
```

### 修改基础Tick持续时间

编辑 `static/app.js` 中的 `baseTickDuration`：

```javascript
this.baseTickDuration = 500; // 毫秒，默认500ms
```

### 修改服务器端口

```python
server = VisualizationServer()
server.run(host="127.0.0.1", port=8080)  # 修改端口号
```

## 常见问题

### Q: 记录文件太大怎么办？
A: 记录文件大小取决于模拟时长。可以定期清理旧记录，或者修改代码只记录关键帧。

### Q: 如何支持更多楼层/电梯？
A: 前端CSS已做响应式设计，会自动适配。如果楼层很多，建议调整CSS中的楼层高度。

### Q: WebSocket连接失败？
A: 检查服务器是否正常运行，防火墙是否允许8080端口。

## 扩展建议

- [ ] 增加暂停/跳转到特定事件的功能
- [ ] 支持对比多个算法的运行结果
- [ ] 添加性能指标图表（折线图）
- [ ] 支持导出视频/GIF
- [ ] 添加实时模拟模式（不只是回放）
