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

            // 如果正在播放，重新设置播放间隔以应用新速度
            if (this.isPlaying) {
                this.pause();
                this.play();
            }
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

        // 事件筛选
        this.eventFilterType = 'all';
        document.getElementById('eventFilter').addEventListener('change', (e) => {
            this.eventFilterType = e.target.value;
            this.filterEventLog();
        });

        // 算法和流量文件选择变化
        document.getElementById('algorithmSelect').addEventListener('change', () => {
            this.updateRunButtonState();
        });
        document.getElementById('trafficSelect').addEventListener('change', () => {
            this.updateRunButtonState();
        });

        // 运行算法按钮
        document.getElementById('btnRunAlgorithm').addEventListener('click', () => {
            this.runAlgorithm();
        });

        // 加载算法和流量文件列表
        this.loadAlgorithmList();
        this.loadTrafficFileList();
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
     * 加载算法列表
     */
    async loadAlgorithmList() {
        try {
            const response = await fetch('/api/algorithms');
            const data = await response.json();

            if (data.success) {
                const select = document.getElementById('algorithmSelect');
                select.innerHTML = '<option value="">选择算法...</option>';

                data.algorithms.forEach(algorithm => {
                    const option = document.createElement('option');
                    option.value = algorithm.filename;
                    option.textContent = `${algorithm.name} - ${algorithm.description}`;
                    select.appendChild(option);
                });
            }
        } catch (error) {
            console.error('加载算法列表失败:', error);
            this.addEventLog('错误', '加载算法列表失败');
        }
    }

    /**
     * 加载流量文件列表
     */
    async loadTrafficFileList() {
        try {
            const response = await fetch('/api/traffic_files');
            const data = await response.json();

            if (data.success) {
                const select = document.getElementById('trafficSelect');
                select.innerHTML = '<option value="">选择流量文件...</option>';

                data.traffic_files.forEach(traffic => {
                    const option = document.createElement('option');
                    option.value = traffic.filename;
                    const info = traffic.passengers ?
                        `${traffic.name} (${traffic.passengers}人, ${traffic.elevators}梯, ${traffic.floors}层)` :
                        traffic.name;
                    option.textContent = info;
                    select.appendChild(option);
                });
            }
        } catch (error) {
            console.error('加载流量文件列表失败:', error);
            this.addEventLog('错误', '加载流量文件列表失败');
        }
    }

    /**
     * 更新运行按钮状态
     */
    updateRunButtonState() {
        const algorithmSelect = document.getElementById('algorithmSelect');
        const trafficSelect = document.getElementById('trafficSelect');
        const runButton = document.getElementById('btnRunAlgorithm');

        // 只有当两个都选择了才启用运行按钮
        runButton.disabled = !algorithmSelect.value || !trafficSelect.value;
    }

    /**
     * 运行算法
     */
    async runAlgorithm() {
        const algorithmSelect = document.getElementById('algorithmSelect');
        const trafficSelect = document.getElementById('trafficSelect');
        const runStatus = document.getElementById('runStatus');
        const runButton = document.getElementById('btnRunAlgorithm');

        const algorithm = algorithmSelect.value;
        const trafficFile = trafficSelect.value;

        if (!algorithm || !trafficFile) {
            return;
        }

        try {
            // 显示运行状态
            runStatus.textContent = '⏳ 运行中...';
            runStatus.className = 'run-status running';
            runButton.disabled = true;

            this.addEventLog('系统', `开始运行: ${algorithm} + ${trafficFile}`);

            // 发送运行请求
            const response = await fetch('/api/run_algorithm', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    algorithm: algorithm,
                    traffic_file: trafficFile,
                }),
            });

            const data = await response.json();

            if (data.success) {
                // 运行成功
                runStatus.textContent = '✅ 运行成功';
                runStatus.className = 'run-status success';
                this.addEventLog('系统', `运行成功: ${data.recording}`);

                // 刷新记录列表并自动加载新生成的记录
                await this.loadRecordingList(false);

                // 选中并加载新生成的记录
                const recordingSelect = document.getElementById('recordingSelect');
                recordingSelect.value = data.recording;
                this.loadRecording(data.recording);

            } else {
                // 运行失败
                runStatus.textContent = '❌ 运行失败';
                runStatus.className = 'run-status error';
                this.addEventLog('错误', `运行失败: ${data.error}`);
            }

            // 3秒后清空状态
            setTimeout(() => {
                runStatus.textContent = '';
                runStatus.className = 'run-status';
                this.updateRunButtonState();
            }, 3000);

        } catch (error) {
            console.error('运行算法失败:', error);
            runStatus.textContent = '❌ 运行失败';
            runStatus.className = 'run-status error';
            this.addEventLog('错误', `运行算法失败: ${error.message}`);

            // 3秒后清空状态
            setTimeout(() => {
                runStatus.textContent = '';
                runStatus.className = 'run-status';
                this.updateRunButtonState();
            }, 3000);
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
                const result = this.formatEventDescription(event);
                if (result) {
                    this.addEventLog(`Tick ${state.tick}`, result.description, result.type);
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
        let description = null;
        let type = 'system';

        switch (event.type) {
            case 'up_button_pressed':
            case 'down_button_pressed':
            case 'passenger_board':
            case 'passenger_alight':
                type = 'passenger';
                break;
            case 'stopped_at_floor':
            case 'idle':
            case 'passing_floor':
            case 'elevator_approaching':
                type = 'elevator';
                break;
        }

        switch (event.type) {
            case 'up_button_pressed':
                description = `乘客P${data.passenger}在F${data.floor}按下上行按钮`;
                break;
            case 'down_button_pressed':
                description = `乘客P${data.passenger}在F${data.floor}按下下行按钮`;
                break;
            case 'stopped_at_floor':
                description = `电梯E${data.elevator}停靠在F${data.floor}`;
                break;
            case 'passenger_board':
                description = `乘客P${data.passenger}登上电梯E${data.elevator}`;
                break;
            case 'passenger_alight':
                description = `乘客P${data.passenger}从电梯E${data.elevator}下车，到达F${data.floor}`;
                break;
            case 'idle':
                description = `电梯E${data.elevator}进入空闲状态`;
                break;
            default:
                return null;
        }

        return { description, type };
    }

    /**
     * 添加事件日志
     */
    addEventLog(tick, description, type = 'system') {
        const eventList = document.getElementById('eventList');
        const eventItem = document.createElement('div');
        eventItem.className = 'event-item';
        eventItem.setAttribute('data-event-type', type);
        eventItem.innerHTML = `<span class="event-tick">[${tick}]</span> ${description}`;

        // 根据筛选条件决定是否显示
        if (this.eventFilterType === 'all' || this.eventFilterType === type) {
            eventItem.style.display = 'block';
        } else {
            eventItem.style.display = 'none';
        }

        eventList.insertBefore(eventItem, eventList.firstChild);

        // 限制日志数量
        while (eventList.children.length > 50) {
            eventList.removeChild(eventList.lastChild);
        }
    }

    /**
     * 筛选事件日志
     */
    filterEventLog() {
        const eventList = document.getElementById('eventList');
        const items = eventList.querySelectorAll('.event-item');

        items.forEach(item => {
            const eventType = item.getAttribute('data-event-type');
            if (this.eventFilterType === 'all' || this.eventFilterType === eventType) {
                item.style.display = 'block';
            } else {
                item.style.display = 'none';
            }
        });
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.app = new ElevatorVisualization();
});
