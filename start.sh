#!/bin/bash
# ====================================================================
# Elevator Saga - Visualization Web Interface (Linux GUI Mode)
# ====================================================================
# This script:
# 1. Checks Python installation
# 2. Installs project dependencies using pip
# 3. Starts the Visualization Web Server
# ====================================================================

set -e  # Exit on error

echo "========================================"
echo "Elevator Saga - Visualization System"
echo "========================================"
echo ""

# Function to check command existence
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if Python3 is installed
if ! command_exists python3; then
    echo "[ERROR] Python3 is not installed"
    echo "Please install Python 3.10 or higher"
    echo "Ubuntu/Debian: apt install python3"
    echo "Fedora: dnf install python3"
    exit 1
fi

echo "[INFO] Python version:"
python3 --version
echo ""

# Check Python version (must be 3.10+)
python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[ERROR] Python 3.10 or higher is required"
    echo "Current Python version is too old"
    exit 1
fi

# Check if pip is installed
if ! command_exists pip3 && ! python3 -m pip --version >/dev/null 2>&1; then
    echo "[ERROR] pip is not installed"
    echo "Please install pip3"
    echo "Ubuntu/Debian: apt install python3-pip"
    echo "Fedora: dnf install python3-pip"
    exit 1
fi

echo "[STEP 1/3] Installing project dependencies (with visualization support)..."
echo "Installing elevator-py package with visualization extras..."
python3 -m pip install -e ".[visualization]" --quiet
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install project dependencies"
    echo "Please check your pip installation and network connection"
    exit 1
fi
echo "[SUCCESS] Dependencies installed"
echo ""

echo "[STEP 2/3] Verifying visualization packages..."
python3 -c "import fastapi, uvicorn, httpx, pydantic" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[WARNING] Some visualization packages missing, installing..."
    python3 -m pip install fastapi uvicorn httpx pydantic --quiet
    if [ $? -ne 0 ]; then
        echo "[WARNING] Some packages failed to install, but continuing..."
    fi
fi
echo "[SUCCESS] All packages verified"
echo ""

echo "[STEP 3/3] Starting Visualization Web Server..."
echo "========================================"
echo "Visualization Server is starting on port 8080"
echo "Web UI URL: http://127.0.0.1:8080"
echo "Press Ctrl+C to stop the server"
echo "========================================"
echo ""

# Run the visualization web server
# Try using python first (which might be in the venv), then fall back to python3
if command -v python >/dev/null 2>&1; then
    python visualize.py
else
    python3 visualize.py
fi

# Check if the server started successfully
if [ $? -ne 0 ]; then
    echo ""
    echo "[ERROR] Visualization server failed to start"
    echo "Please check the error messages above"
    exit 1
fi
