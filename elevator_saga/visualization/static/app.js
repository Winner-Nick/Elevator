/**
 * 电梯调度可视化 - 前端应用
 */

class ElevatorVisualization {
    constructor() {
        this.ws = null;
        this.history = [];
        this.metadata = null;
        this.currentIndex = 0;
        this.isPlaying = false;
        this.playbackSpeed = 1.0;
        this.playbackInterval = null;
        this.baseTickDuration = 500; // 基础每tick持续时间（毫秒）

        this.initUI();
        this.connectWebSocket();
        this.loadRecordingList();
    }

    /**
     * 初始化UI
     */
    initUI() {
        // 播放控制按钮
        document.getElementById('btnPlay').addEventListener('click', () => this.play());
        document.getElementById('btnPause').addEventListener('click', () => this.pause());
        document.getElementById('btnReset').addEventListener('click', () => this.reset());

        // 速度控制
        document.getElementById('speedControl').addEventListener('input', (e) => {
            this.playbackSpeed = parseFloat(e.target.value);
            document.getElementById('speedValue').textContent = this.playbackSpeed.toFixed(1) + 'x';
        });

        // 进度条
        document.getElementById('progressBar').addEventListener('input', (e) => {
            const index = parseInt(e.target.value);
            this.seekTo(index);
        });

        // 加载记录按钮
        document.getElementById('btnLoadRecording').addEventListener('click', () => {
            const filename = document.getElementById('recordingSelect').value;
            if (filename) {
                this.loadRecording(filename);
            }
        });

        // 下拉框选择变化时也自动加载
        document.getElementById('recordingSelect').addEventListener('change', (e) => {
            const filename = e.target.value;
            if (filename) {
                this.loadRecording(filename);
            }
        });

        // 刷新记录列表按钮
        document.getElementById('btnRefreshRecordings').addEventListener('click', () => {
            this.loadRecordingList();
        });
    }

    /**
     * 连接WebSocket
     */
    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('✅ WebSocket连接成功');
            this.addEventLog('系统', 'WebSocket连接成功');
        };

        this.ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            this.handleWebSocketMessage(message);
        };

        this.ws.onclose = () => {
            console.log('🔌 WebSocket连接关闭');
            this.addEventLog('系统', 'WebSocket连接关闭');
        };

        this.ws.onerror = (error) => {
            console.error('❌ WebSocket错误:', error);
            this.addEventLog('系统', 'WebSocket连接错误');
        };
    }

    /**
     * 处理WebSocket消息
     */
    handleWebSocketMessage(message) {
        switch (message.type) {
            case 'metadata':
                this.metadata = message.data;
                this.addEventLog('系统', `加载记录: ${message.filename}`);
                break;

            case 'history':
                this.history = message.data;
                this.currentIndex = 0;
                this.updateProgressBar();
                this.renderCurrentState();
                this.addEventLog('系统', `历史数据加载完成，共 ${this.history.length} 帧`);
                break;

            case 'error':
                console.error('服务器错误:', message.message);
                this.addEventLog('错误', message.message);
                break;

            case 'pong':
                // 心跳响应
                break;
        }
    }

    /**
     * 加载记录列表
     */
    async loadRecordingList(autoLoadLatest = true) {
        try {
            const response = await fetch('/api/recordings');
            const data = await response.json();

            if (data.success) {
                const select = document.getElementById('recordingSelect');
                const currentValue = select.value; // 保存当前选择
                select.innerHTML = '<option value="">选择记录文件...</option>';

                data.recordings.forEach(recording => {
                    const option = document.createElement('option');
                    option.value = recording.filename;
                    option.textContent = `${recording.filename} (${recording.metadata.total_ticks || 0} ticks)`;
                    select.appendChild(option);
                });

                // 优先恢复之前的选择，否则自动加载最新的
                if (currentValue && data.recordings.find(r => r.filename === currentValue)) {
                    select.value = currentValue;
                } else if (autoLoadLatest && data.recordings.length > 0) {
                    select.value = data.recordings[0].filename;
                    this.loadRecording(data.recordings[0].filename);
                }
            }
        } catch (error) {
            console.error('加载记录列表失败:', error);
            this.addEventLog('错误', '加载记录列表失败');
        }
    }

    /**
     * 加载指定记录
     */
    loadRecording(filename) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.pause();
            this.ws.send(JSON.stringify({
                command: 'load_recording',
                filename: filename
            }));
        }
    }

    /**
     * 播放
     */
    play() {
        if (this.isPlaying || !this.history.length) return;

        this.isPlaying = true;
        document.getElementById('btnPlay').disabled = true;
        document.getElementById('btnPause').disabled = false;

        this.playbackInterval = setInterval(() => {
            if (this.currentIndex < this.history.length - 1) {
                this.currentIndex++;
                this.renderCurrentState();
                this.updateProgressBar();
            } else {
                this.pause();
            }
        }, this.baseTickDuration / this.playbackSpeed);
    }

    /**
     * 暂停
     */
    pause() {
        this.isPlaying = false;
        document.getElementById('btnPlay').disabled = false;
        document.getElementById('btnPause').disabled = true;

        if (this.playbackInterval) {
            clearInterval(this.playbackInterval);
            this.playbackInterval = null;
        }
    }

    /**
     * 重置
     */
    reset() {
        this.pause();
        this.currentIndex = 0;
        this.renderCurrentState();
        this.updateProgressBar();
    }

    /**
     * 跳转到指定帧
     */
    seekTo(index) {
        this.pause();
        this.currentIndex = Math.max(0, Math.min(index, this.history.length - 1));
        this.renderCurrentState();
    }

    /**
     * 更新进度条
     */
    updateProgressBar() {
        const progressBar = document.getElementById('progressBar');
        progressBar.max = this.history.length - 1;
        progressBar.value = this.currentIndex;
    }

    /**
     * 渲染当前状态
     */
    renderCurrentState() {
        if (!this.history.length) return;

        const state = this.history[this.currentIndex];

        // 更新Tick显示
        document.getElementById('currentTick').textContent = state.tick;

        // 渲染建筑物
        this.renderBuilding(state);

        // 更新统计信息
        this.updateStats(state);

        // 更新事件日志（只添加新事件）
        if (state.events && state.events.length > 0) {
            state.events.forEach(event => {
                const desc = this.formatEventDescription(event);
                if (desc) {
                    this.addEventLog(`Tick ${state.tick}`, desc);
                }
            });
        }
    }

    /**
     * 渲染建筑物视图
     */
    renderBuilding(state) {
        const buildingView = document.getElementById('buildingView');

        // 确定楼层数
        const numFloors = state.floors.length;
        const numElevators = state.elevators.length;

        // 清空并重建
        buildingView.innerHTML = '';

        // 从高到低渲染每一层
        for (let floorNum = numFloors - 1; floorNum >= 0; floorNum--) {
            const floorData = state.floors.find(f => f.floor === floorNum);
            const floorRow = document.createElement('div');
            floorRow.className = 'floor-row';

            // 楼层标签
            const floorLabel = document.createElement('div');
            floorLabel.className = 'floor-label';
            floorLabel.textContent = `F${floorNum}`;
            floorRow.appendChild(floorLabel);

            // 电梯井道区
            const shafts = document.createElement('div');
            shafts.className = 'elevator-shafts';

            // 为每部电梯创建井道
            for (let i = 0; i < numElevators; i++) {
                const elevator = state.elevators[i];
                const shaft = document.createElement('div');
                shaft.className = 'elevator-shaft';

                // 井道轨道
                const track = document.createElement('div');
                track.className = 'shaft-track';
                shaft.appendChild(track);

                // 检查电梯是否在当前楼层
                const elevatorFloor = Math.floor(elevator.current_floor_float);
                if (elevatorFloor === floorNum) {
                    const car = document.createElement('div');
                    car.className = `elevator-car ${elevator.direction}`;

                    const elevatorId = document.createElement('div');
                    elevatorId.className = 'elevator-id';
                    elevatorId.textContent = `E${elevator.id}`;
                    car.appendChild(elevatorId);

                    const direction = document.createElement('div');
                    direction.className = 'elevator-direction';
                    direction.textContent = this.getDirectionSymbol(elevator.direction);
                    car.appendChild(direction);

                    if (elevator.passengers.length > 0) {
                        const passengers = document.createElement('div');
                        passengers.className = 'elevator-passengers';
                        passengers.textContent = '👤'.repeat(Math.min(elevator.passengers.length, 5));
                        if (elevator.passengers.length > 5) {
                            passengers.textContent += `+${elevator.passengers.length - 5}`;
                        }
                        car.appendChild(passengers);

                        // 添加悬停提示
                        const destinations = Object.values(elevator.passenger_destinations);
                        car.title = `乘客目的地: ${destinations.join(', ')}`;
                    }

                    shaft.appendChild(car);
                }

                shafts.appendChild(shaft);
            }

            floorRow.appendChild(shafts);

            // 等待队列区
            const waitingArea = document.createElement('div');
            waitingArea.className = 'waiting-area';

            if (floorData) {
                // 上行等待队列
                if (floorData.up_queue.length > 0) {
                    const upDiv = document.createElement('div');
                    upDiv.className = 'waiting-direction';
                    upDiv.innerHTML = '<span class="direction-icon">↑</span>';

                    floorData.up_queue.forEach(passengerId => {
                        const passenger = state.passengers[passengerId];
                        if (passenger) {
                            const badge = document.createElement('span');
                            badge.className = 'passenger-badge';
                            badge.textContent = `P${passengerId}→F${passenger.destination}`;
                            badge.title = `到达时间: Tick ${passenger.arrive_tick}`;
                            upDiv.appendChild(badge);
                        }
                    });

                    waitingArea.appendChild(upDiv);
                }

                // 下行等待队列
                if (floorData.down_queue.length > 0) {
                    const downDiv = document.createElement('div');
                    downDiv.className = 'waiting-direction';
                    downDiv.innerHTML = '<span class="direction-icon">↓</span>';

                    floorData.down_queue.forEach(passengerId => {
                        const passenger = state.passengers[passengerId];
                        if (passenger) {
                            const badge = document.createElement('span');
                            badge.className = 'passenger-badge';
                            badge.textContent = `P${passengerId}→F${passenger.destination}`;
                            badge.title = `到达时间: Tick ${passenger.arrive_tick}`;
                            downDiv.appendChild(badge);
                        }
                    });

                    waitingArea.appendChild(downDiv);
                }
            }

            floorRow.appendChild(waitingArea);
            buildingView.appendChild(floorRow);
        }
    }

    /**
     * 获取方向符号
     */
    getDirectionSymbol(direction) {
        switch (direction) {
            case 'up': return '↑';
            case 'down': return '↓';
            case 'stopped': return '◆';
            default: return '•';
        }
    }

    /**
     * 更新统计信息
     */
    updateStats(state) {
        const metrics = state.metrics || {};
        const passengers = state.passengers || {};

        // 计算统计数据
        let total = Object.keys(passengers).length;
        let delivered = 0;
        let inTransit = 0;
        let waiting = 0;

        Object.values(passengers).forEach(p => {
            if (p.status === 'completed') delivered++;
            else if (p.status === 'in_elevator') inTransit++;
            else if (p.status === 'waiting') waiting++;
        });

        document.getElementById('statTotal').textContent = total;
        document.getElementById('statDelivered').textContent = delivered;
        document.getElementById('statInTransit').textContent = inTransit;
        document.getElementById('statWaiting').textContent = waiting;
        document.getElementById('statAvgWait').textContent =
            (metrics.average_wait_time || 0).toFixed(1);
    }

    /**
     * 格式化事件描述
     */
    formatEventDescription(event) {
        const data = event.data;
        switch (event.type) {
            case 'up_button_pressed':
                return `乘客P${data.passenger}在F${data.floor}按下上行按钮`;
            case 'down_button_pressed':
                return `乘客P${data.passenger}在F${data.floor}按下下行按钮`;
            case 'stopped_at_floor':
                return `电梯E${data.elevator}停靠在F${data.floor}`;
            case 'passenger_board':
                return `乘客P${data.passenger}登上电梯E${data.elevator}`;
            case 'passenger_alight':
                return `乘客P${data.passenger}从电梯E${data.elevator}下车，到达F${data.floor}`;
            case 'idle':
                return `电梯E${data.elevator}进入空闲状态`;
            default:
                return null;
        }
    }

    /**
     * 添加事件日志
     */
    addEventLog(tick, description) {
        const eventList = document.getElementById('eventList');
        const eventItem = document.createElement('div');
        eventItem.className = 'event-item';
        eventItem.innerHTML = `<span class="event-tick">[${tick}]</span> ${description}`;

        eventList.insertBefore(eventItem, eventList.firstChild);

        // 限制日志数量
        while (eventList.children.length > 50) {
            eventList.removeChild(eventList.lastChild);
        }
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.app = new ElevatorVisualization();
});
