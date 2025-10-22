@echo off
REM ====================================================================
REM Elevator Saga - Visualization Web Interface (Windows GUI Mode)
REM ====================================================================
REM This script:
REM 1. Checks Python installation
REM 2. Installs project dependencies using pip
REM 3. Starts the Visualization Web Server
REM 4. Opens the web interface in browser
REM ====================================================================

echo ========================================
echo Elevator Saga - Visualization System
echo ========================================
echo.

REM Check if Python is installed
python --version >NUL 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.10 or higher from https://www.python.org/
    pause
    exit /b 1
)

echo [INFO] Python version:
python --version
echo.

REM Check Python version (must be 3.10+)
python -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" >NUL 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python 3.10 or higher is required
    echo Current Python version is too old
    pause
    exit /b 1
)

echo [STEP 1/3] Installing project dependencies (with visualization support)...
echo Installing elevator-py package with visualization extras...
pip install -e ".[visualization]" >NUL 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install project dependencies
    echo Please check your pip installation and network connection
    pause
    exit /b 1
)
echo [SUCCESS] Dependencies installed
echo.

echo [STEP 2/3] Verifying visualization packages...
python -c "import fastapi; import uvicorn; import httpx; import pydantic" >NUL 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Some visualization packages missing, installing...
    pip install fastapi uvicorn httpx pydantic
    if %errorlevel% neq 0 (
        echo [WARNING] Some packages failed to install, but continuing...
    )
)
echo [SUCCESS] All packages verified
echo.

echo [STEP 3/3] Starting Visualization Web Server...
echo ========================================
echo Visualization Server is starting on port 8080
echo Web UI URL: http://127.0.0.1:8080
echo Press Ctrl+C to stop the server
echo ========================================
echo.

REM Start the visualization web server
python visualize.py

REM Check if the server started successfully
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Visualization server failed to start
    echo Please check the error messages above
    pause
    exit /b 1
)

pause
