#!/usr/bin/env python3
"""
Auto-restart program when source files change.
Usage: python run.py <command> [args...]
"""

import sys
import subprocess
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class RestartHandler(FileSystemEventHandler):
    def __init__(self, restart_callback):
        self.restart_callback = restart_callback
        super().__init__()

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(".py"):
            print(f"\nFile changed: {event.src_path}")
            self.restart_callback()


class AppRunner:
    def __init__(self, command, watch_dirs):
        self.command = command
        self.watch_dirs = watch_dirs
        self.process = None
        self.should_restart = False
        self.running = True

    def restart_app(self):
        """Called when files change - signal for restart."""
        self.should_restart = True
        if self.process:
            print("Killing app for restart...")
            try:
                # Send SIGTERM to process
                self.process.terminate()
            except ProcessLookupError:
                pass  # Process already dead

    def _reset_terminal(self):
        """Reset terminal state in case app was killed in alternate screen mode."""
        try:
            # Send escape sequences to restore normal terminal state
            print("\033[?1049l", end="")  # Exit alternate screen
            print("\033[?25h", end="")  # Show cursor
            print("\033[0m", end="")  # Reset colors/attributes
            sys.stdout.flush()
        except Exception as _:
            pass  # Ignore any errors

    def run_app(self):
        """Run the app, handling crashes by sleeping forever."""
        while self.running:
            self.should_restart = False
            print(f"Starting: {' '.join(self.command)}")
            print("=" * 40)

            try:
                # Start process normally so it gets terminal signals
                self.process = subprocess.Popen(self.command)

                # Wait for process to finish
                exit_code = self.process.wait()
                self.process = None

                # Reset terminal in case app was killed in alt screen mode
                self._reset_terminal()

                if self.should_restart:
                    print("Restarting due to file change...")
                    time.sleep(0.5)
                    continue
                elif exit_code == 0:
                    print("App exited normally")
                    break
                else:
                    print(f"App crashed with exit code {exit_code}")
                    print("Waiting for file changes to restart...")
                    # Sleep until restart is requested
                    while not self.should_restart and self.running:
                        time.sleep(0.1)
                    if self.should_restart:
                        print("File changed, restarting after crash...")
                        time.sleep(0.5)

            except KeyboardInterrupt:
                print("\nShutting down...")
                self.running = False
                if self.process:
                    try:
                        self.process.terminate()
                        self.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self.process.kill()  # Force kill if it doesn't respond
                break


def main():
    if len(sys.argv) < 2:
        print("Usage: python run.py <command> [args...]")
        print("Example: python run.py python ./demo/demo.py --dev")
        sys.exit(1)

    command = sys.argv[1:]
    watch_dirs = ["src", "demo"]

    # Check if watch directories exist
    existing_dirs = [d for d in watch_dirs if Path(d).exists()]
    if not existing_dirs:
        print(f"Warning: None of the watch directories exist: {watch_dirs}")
        print("Watching current directory instead")
        existing_dirs = ["."]

    print(f"Command: {' '.join(command)}")
    print(f"Watching: {existing_dirs}")
    print("Press Ctrl+C to stop")

    # Set up file watcher
    runner = AppRunner(command, existing_dirs)
    event_handler = RestartHandler(runner.restart_app)
    observer = Observer()

    for directory in existing_dirs:
        observer.schedule(event_handler, directory, recursive=True)

    observer.start()

    try:
        # Run the app (this blocks)
        runner.run_app()
    finally:
        observer.stop()
        observer.join()


if __name__ == "__main__":
    main()
