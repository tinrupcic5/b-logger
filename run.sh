#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

spinner() {
    local message="$1"
    local duration="${2:-1}"
    local frames=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')
    local i=0
    local end=$((SECONDS + duration))

    while [ "$SECONDS" -lt "$end" ]; do
        printf "\r%s %s" "${frames[i]}" "$message"
        i=$(( (i + 1) % ${#frames[@]} ))
        sleep 0.1
    done
    printf "\r\033[K"
}

run_with_spinner() {
    local message="$1"
    shift
    local frames=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')
    local i=0
    local tmp_status
    tmp_status=$(mktemp)

    ("$@" > /dev/null 2>&1; echo $? > "$tmp_status") &
    local pid=$!

    while kill -0 "$pid" 2>/dev/null; do
        printf "\r%s %s" "${frames[i]}" "$message"
        i=$(( (i + 1) % ${#frames[@]} ))
        sleep 0.1
    done
    wait "$pid" 2>/dev/null

    local status
    status=$(cat "$tmp_status")
    rm -f "$tmp_status"
    printf "\r\033[K"
    return "$status"
}

if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$SCRIPT_DIR/venv"
fi

source "$SCRIPT_DIR/venv/bin/activate"

if [ -z "$VIRTUAL_ENV" ]; then
    echo "Failed to activate virtual environment"
    exit 1
fi

spinner "Checking dependencies..." 1

if ! "$SCRIPT_DIR/venv/bin/python3" -c "import blessed" 2>/dev/null; then
    install_deps() {
        "$SCRIPT_DIR/venv/bin/python3" -m pip install --upgrade pip &&
        "$SCRIPT_DIR/venv/bin/python3" -m pip install -r "$SCRIPT_DIR/requirements.txt"
    }

    if ! run_with_spinner "Installing dependencies..." install_deps; then
        echo "Error: Failed to install dependencies"
        install_deps
        exit 1
    fi

    spinner "Installing dependencies..." 1
    printf "Dependencies installed successfully! 🍺 🍺"
    sleep 1
    printf "\r\033[K"
else
    printf "Dependencies already installed 🍺 🍺"
    sleep 1
    printf "\r\033[K"
fi

"$SCRIPT_DIR/venv/bin/python3" "$SCRIPT_DIR/b_logger.py"
