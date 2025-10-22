#!/bin/bash
# ====================================================================
# Elevator Saga - Visual Look V2 Algorithm Launcher (Linux GUI Mode)
# ====================================================================
# This script:
# 1. Checks Python installation
# 2. Installs project dependencies using pip
# 3. Runs the Visual Look V2 algorithm with visualization
# ====================================================================

set -e  # Exit on error

echo "========================================"
echo "Elevator Saga - Visual Look V2"
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

echo "[STEP 1/3] Installing project dependencies..."
echo "Installing elevator-py package in editable mode..."
python3 -m pip install -e . --quiet
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install project dependencies"
    echo "Please check your pip installation and network connection"
    exit 1
fi
echo "[SUCCESS] Dependencies installed"
echo ""

echo "[STEP 2/3] Checking required packages..."
python3 -c "import numpy, flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[ERROR] Required packages (numpy, flask) are not available"
    echo "Attempting to install again..."
    python3 -m pip install numpy flask --quiet
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to install required packages"
        exit 1
    fi
fi
echo "[SUCCESS] All required packages are available"
echo ""

echo "[STEP 3/3] Starting LOOK V2 Algorithm..."
echo "========================================"
echo "Running elevator scheduling algorithm"
echo "Algorithm: LOOK V2 (Real-time Decision Making)"
echo "========================================"
echo ""

# Run the LOOK V2 algorithm
# Try using python first (which might be in the venv), then fall back to python3
if command -v python >/dev/null 2>&1; then
    python -m elevator_saga.client_examples.look_v2_example
else
    python3 -m elevator_saga.client_examples.look_v2_example
fi

# Check if the algorithm ran successfully
if [ $? -ne 0 ]; then
    echo ""
    echo "[ERROR] Algorithm execution failed"
    echo "Please check the error messages above"
    exit 1
fi

echo ""
echo "========================================"
echo "[SUCCESS] Algorithm completed"
echo "========================================"
