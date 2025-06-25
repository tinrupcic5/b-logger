#!/bin/bash

# Get the absolute path of the script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$SCRIPT_DIR/venv"
fi

# Activate virtual environment and ensure it's activated
source "$SCRIPT_DIR/venv/bin/activate"

# Verify we're in the virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Failed to activate virtual environment"
    exit 1
fi

# Check if dependencies are already installed
if [ ! -f "$SCRIPT_DIR/venv/lib/python*/site-packages/blessed" ]; then
    echo "Installing dependencies..."
    "$SCRIPT_DIR/venv/bin/python3" -m pip install --upgrade pip > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "Error: Failed to upgrade pip"
        "$SCRIPT_DIR/venv/bin/python3" -m pip install --upgrade pip
        exit 1
    fi
    
    "$SCRIPT_DIR/venv/bin/python3" -m pip install -r "$SCRIPT_DIR/requirements.txt" > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install dependencies"
        "$SCRIPT_DIR/venv/bin/python3" -m pip install -r "$SCRIPT_DIR/requirements.txt"
        exit 1
    fi
    
    echo "Dependencies installed successfully! 🍺"
else
    echo "Enjoy the app 🍺"
fi

# Run the application using the virtual environment's Python
"$SCRIPT_DIR/venv/bin/python3" "$SCRIPT_DIR/b_logger.py"
