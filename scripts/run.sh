#!/bin/bash

# Auto-restart Python program when source files change
# Usage: ./scripts/run.sh <python_script>

if [ $# -eq 0 ]; then
    echo "Usage: $0 <python_script>"
    echo "Example: $0 ./demos/simple_spinner.py"
    exit 1
fi

SCRIPT="$1"
WATCH_DIRS="src demos"
SHOULD_RESTART=0

# Check if inotify-tools is available
if ! command -v inotifywait &> /dev/null; then
    echo "Error: inotifywait not found. Install inotify-tools:"
    echo "  sudo apt-get install inotify-tools"
    exit 1
fi

# Function to run the script
run_script() {
    reset
    echo "Starting: $SCRIPT"
    echo "Watching: $WATCH_DIRS"
    echo "Press Ctrl+C to stop"
    echo "----------------------------------------"
}

# Function to handle file changes
handle_change() {
    SHOULD_RESTART=1
    # Send SIGINT to the Python process (child of this script)
    kill -INT 0 2>/dev/null
}

# Function to cleanup
cleanup() {
    # Kill watcher if running
    if [ -n "$WATCH_PID" ]; then
        kill "$WATCH_PID" 2>/dev/null
    fi
    exit 0
}

# Set up signal handlers
trap cleanup EXIT
trap handle_change USR1

# Start file watcher in background
(
    while true; do
        # shellcheck disable=SC2086
        inotifywait -r -e modify,create,delete --include='.*\.py$' $WATCH_DIRS 2>/dev/null
        # Send USR1 to parent to trigger restart
        kill -USR1 $$ 2>/dev/null
    done
) &
WATCH_PID=$!

# Main loop
while true; do
    SHOULD_RESTART=0
    run_script

    # Run Python script in foreground (no &)
    python "$SCRIPT"

    # Check if we should restart or exit
    if [ $SHOULD_RESTART -eq 1 ]; then
        echo
        echo "Files changed, restarting..."
        sleep 0.5
    else
        # Normal exit or Ctrl+C without file change
        break
    fi
done