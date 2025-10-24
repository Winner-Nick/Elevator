#!/bin/bash
# ====================================================================
# Elevator Saga - Algorithm Mode (Headless)
# ====================================================================
# 启动电梯调度算法（无GUI）
# 1. 检查Python环境
# 2. 安装必要依赖
# 3. 设置环境变量
# 4. 启动controller（Algorithm模式）
# ====================================================================

set -e

echo "========================================"
echo "Elevator Saga - Algorithm Mode (纯算法)"
echo "========================================"
echo ""

# 检查Python是否安装
if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERROR] Python3 未安装"
    echo "请安装 Python 3.10 或更高版本"
    exit 1
fi

echo "[INFO] Python 版本:"
python3 --version
echo ""

# 检查Python版本
python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[ERROR] 需要 Python 3.10 或更高版本"
    exit 1
fi

# 检查pip
if ! command -v pip3 >/dev/null 2>&1 && ! python3 -m pip --version >/dev/null 2>&1; then
    echo "[ERROR] pip 未安装"
    exit 1
fi

# 安装依赖
echo "[STEP 1/2] 安装依赖..."
python3 -m pip install -q -r requirements.txt
if [ $? -ne 0 ]; then
    echo "[ERROR] 安装依赖失败"
    exit 1
fi
echo "[SUCCESS] 依赖安装完成"
echo ""

# 启动controller
echo "[STEP 2/2] 启动 Algorithm 模式..."
echo "========================================"
echo "运行纯调度算法（无可视化界面）"
echo "按 Ctrl+C 停止"
echo "========================================"
echo ""

export ELEVATOR_CLIENT_TYPE=algorithm
python3 controller.py
