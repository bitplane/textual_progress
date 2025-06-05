#!/bin/bash

# Auto-restart Python program when source files change
# Usage: ./scripts/run.sh <python_script>

if [ $# -eq 0 ]; then
    echo "Usage: $0 <python_script>"
    echo "Example: $0 ./demos/demo.py"
    exit 1
fi

SCRIPT="$1"
WATCH_DIRS="src demos"

# Check if inotify-tools is available
if ! command -v inotifywait &> /dev/null; then
    echo "Error: inotifywait not found. Install inotify-tools:"
    echo "  sudo apt-get install inotify-tools"
    exit 1
fi

# Function to cleanup
cleanup() {
    echo
    echo "Shutting down..."

    # Kill all child processes
    jobs -p | xargs -r kill 2>/dev/null

    # Wait for processes to exit
    wait

    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM EXIT

# Start file watcher in background
echo "Starting file watcher..."
(
    while true; do
        # shellcheck disable=SC2086
        inotifywait -r -e modify,create,delete --include='.*\.py$' $WATCH_DIRS 2>/dev/null
        echo
        echo "Files changed, restarting..."
        # Kill all Python processes in this process group
        pkill -TERM -P $$ python 2>/dev/null
    done
) &

# Main loop
while true; do
    reset
    echo "Starting: $SCRIPT"
    echo "Watching: $WATCH_DIRS"
    echo "Press Ctrl+C to stop"
    echo "----------------------------------------"

    # Run Python script in foreground
    python "$SCRIPT"
    PYTHON_EXIT=$?

    # If Python exited normally (not killed), break
    if [ $PYTHON_EXIT -ne 143 ] && [ $PYTHON_EXIT -ne 137 ]; then
        echo
        echo "App exited with code: $PYTHON_EXIT"
        break
    fi

    # Brief pause before restart
    sleep 0.5
done