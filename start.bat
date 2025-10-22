@echo off
REM ====================================================================
REM Elevator Saga - Visual Look V2 Algorithm Launcher (Windows GUI Mode)
REM ====================================================================
REM This script:
REM 1. Checks Python installation
REM 2. Installs project dependencies using pip
REM 3. Runs the Visual Look V2 algorithm with visualization
REM ====================================================================

echo ========================================
echo Elevator Saga - Visual Look V2
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

echo [STEP 1/3] Installing project dependencies...
echo Installing elevator-py package in editable mode...
pip install -e . >NUL 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install project dependencies
    echo Please check your pip installation and network connection
    pause
    exit /b 1
)
echo [SUCCESS] Dependencies installed
echo.

echo [STEP 2/3] Checking required packages...
python -c "import numpy, flask" >NUL 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Required packages (numpy, flask) are not available
    echo Attempting to install again...
    pip install numpy flask
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install required packages
        pause
        exit /b 1
    )
)
echo [SUCCESS] All required packages are available
echo.

echo [STEP 3/3] Starting LOOK V2 Algorithm...
echo ========================================
echo Running elevator scheduling algorithm
echo Algorithm: LOOK V2 (Real-time Decision Making)
echo ========================================
echo.

REM Run the LOOK V2 algorithm
python -m elevator_saga.client_examples.look_v2_example

REM Check if the algorithm ran successfully
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Algorithm execution failed
    echo Please check the error messages above
    pause
    exit /b 1
)

echo.
echo ========================================
echo [SUCCESS] Algorithm completed
echo ========================================
pause
