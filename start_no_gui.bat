@echo off
REM ====================================================================
REM Elevator Saga - Algorithm Mode (Headless)
REM ====================================================================
REM 启动电梯调度算法（无GUI）
REM 1. 检查Python环境
REM 2. 安装必要依赖
REM 3. 设置环境变量
REM 4. 启动controller（Algorithm模式）
REM ====================================================================

setlocal enabledelayedexpansion

echo ========================================
echo Elevator Saga - Algorithm Mode (纯算法)
echo ========================================
echo.

REM 检查Python
python --version >NUL 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python 未安装
    echo 请安装 Python 3.10 或更高版本
    exit /b 1
)

echo [INFO] Python 版本:
python --version
echo.

REM 检查Python版本
python -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" >NUL 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 需要 Python 3.10 或更高版本
    exit /b 1
)

REM 安装依赖
echo [STEP 1/2] 安装依赖...
python -m pip install -q -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] 安装依赖失败
    exit /b 1
)
echo [SUCCESS] 依赖安装完成
echo.

REM 启动controller
echo [STEP 2/2] 启动 Algorithm 模式...
echo ========================================
echo 运行纯调度算法（无可视化界面）
echo 按 Ctrl+C 停止
echo ========================================
echo.

set ELEVATOR_CLIENT_TYPE=algorithm
python controller.py
