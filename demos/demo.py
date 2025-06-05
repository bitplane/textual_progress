#!/usr/bin/env python3
"""
Simple progress tracking demo with logging.
"""

import sys
import asyncio
import logging
from textual.app import App, ComposeResult
from textual.widgets import Static, Button, ListView, ListItem, Label, RichLog
from textual.containers import Vertical, Horizontal
from textual.reactive import reactive

from textual_progress import ProgressNode, Spinner


# Task factory functions
def create_manual_task(title: str) -> ProgressNode:
    """Create a manual task that needs user control."""
    task = ProgressNode(title)
    task.local_total = None  # Indeterminate
    logging.info(f"Created manual task: {title}")
    return task


def create_auto_task(title: str) -> ProgressNode:
    """Create an auto task that starts immediately."""
    task = ProgressNode(title)
    task.local_total = None  # Indeterminate
    task.add_class("active")
    logging.info(f"Created auto task (active): {title}")
    return task


def create_percent_task(title: str, total: int = 100) -> ProgressNode:
    """Create a percentage task that can be started."""
    task = ProgressNode(title)
    task.local_total = total
    task.local_progress = 0
    logging.info(f"Created percent task: {title} (0/{total})")
    return task


def create_none_task() -> None:
    """Create no task - returns None to clear selection."""
    logging.info("Cleared task selection")
    return None


def start_percent_task(task: ProgressNode, app_instance) -> None:
    """Start a percentage task with automatic progress updates."""
    task.add_class("active")
    logging.info(f"Starting percent task: {task.title}")

    async def update_progress():
        total = int(task.local_total or 100)
        for i in range(total + 1):
            if not task or task.has_class("failed"):
                logging.info(f"Percent task stopped: {task.title}")
                break
            task.local_progress = i
            if i % 10 == 0:  # Log every 10%
                logging.info(f"Percent task progress: {task.title} {i}/{total}")
            await asyncio.sleep(0.1)

        if task and not task.has_class("failed"):
            task.complete()
            logging.info(f"Percent task completed: {task.title}")

    asyncio.create_task(update_progress())


# Task registry: name -> (factory_function, args, start_function)
TASK_REGISTRY = {
    "None": (create_none_task, (), None),
    "Manual": (create_manual_task, ("Manual Task",), None),
    "Auto": (create_auto_task, ("Auto Task",), None),
    "Percent": (create_percent_task, ("Percent Task", 100), start_percent_task),
}


class TaskItem(ListItem):
    """A task item in the list."""

    def __init__(self, task_name: str, **kwargs):
        super().__init__(**kwargs)
        self.task_name = task_name

    def compose(self) -> ComposeResult:
        yield Label(self.task_name)


class ProgressDemo(App):
    """Simple progress demo with logging."""

    CSS = """
    Screen {
        layout: horizontal;
    }

    #tasks {
        width: 20;
        padding: 1;
    }

    #main-content {
        layout: vertical;
        width: 1fr;
    }

    #spinners {
        height: 2fr;
        padding: 1;
    }

    #log-panel {
        height: 1fr;
        padding: 0;
    }

    .controls {
        height: 3;
        width: 100%;
        dock: bottom;
    }

    .controls Button {
        width: 3;
        height: 3;
        margin: 0;
        min-width: 3;
        padding: 0;
        content-align: center middle;
    }

    ListView {
        height: 1fr;
    }

    Spinner {
        width: 5;
        height: 3;
        margin: 0 1;
        content-align: center middle;
    }

    RichLog {
        height: 100%;
        border: solid;
        padding: 1;
        margin: 0;
    }
    """

    # Reactive task that all spinners will watch
    task = reactive[ProgressNode | None](None)

    def compose(self) -> ComposeResult:
        """Create the app layout."""
        # Tasks panel (left side)
        with Vertical(id="tasks"):
            items = [TaskItem(name) for name in TASK_REGISTRY.keys()]
            yield ListView(*items, id="task-list")

            # Controls
            with Horizontal(classes="controls"):
                yield Button("▶", id="play")
                yield Button("⏹", id="stop")
                yield Button("⏮", id="reset")
                yield Button("⏭", id="done")

        # Main content area (right side)
        with Vertical(id="main-content"):
            # Spinners panel
            with Vertical(id="spinners"):
                yield Static("Spinner:")
                yield Spinner(id="spinner")

            # Log panel
            with Vertical(id="log-panel"):
                yield RichLog(id="log")

    def on_mount(self) -> None:
        """Set up logging when the app starts."""
        # Get the RichLog widget
        self.log_widget = self.query_one("#log", RichLog)

        # Set up logging to use the RichLog widget directly
        class RichLogHandler(logging.Handler):
            def __init__(self, rich_log_widget):
                super().__init__()
                self.rich_log = rich_log_widget

            def emit(self, record):
                message = self.format(record)
                self.rich_log.write(message)

        # Configure logging
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        # Remove any existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # Add our custom handler
        handler = RichLogHandler(self.log_widget)
        handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s", "%H:%M:%S"))
        logger.addHandler(handler)

        logging.info("App started, waiting for task selection...")
        logging.info("Testing file change detection...")

    def watch_task(self, task: ProgressNode | None) -> None:
        """Watch for task changes and update spinner."""
        logging.info(f"Task changed to: {task.title if task else None}")

        # Update spinner with the new task
        spinner = self.query_one("#spinner", Spinner)
        spinner.task = task
        logging.info(f"Updated spinner with task: {task.title if task else None}")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle task selection."""
        if isinstance(event.item, TaskItem):
            task_name = event.item.task_name
            logging.info(f"Selected task: {task_name}")

            # Get task config from registry
            factory_func, args, start_func = TASK_REGISTRY[task_name]

            # Create the task using factory function and args
            self.task = factory_func(*args)
            logging.info(f"Created and assigned task: {self.task.title if self.task else 'None'}")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if not self.task:
            logging.warning("No task selected, button press ignored")
            return

        button_id = event.button.id
        logging.info(f"Button pressed: {button_id}")

        if button_id == "play":
            # Check if this task has a start function in the registry
            task_name = None
            for name, (_, _, start_func) in TASK_REGISTRY.items():
                if self.task.title in name or name in self.task.title:
                    task_name = name
                    break

            if task_name and TASK_REGISTRY[task_name][2]:
                # Call the start function from registry
                start_func = TASK_REGISTRY[task_name][2]
                start_func(self.task, self)
            else:
                self.task.add_class("active")
                logging.info(f"Started task: {self.task.title}")

        elif button_id == "stop":
            self.task.fail()
            logging.info(f"Stopped task: {self.task.title}")

        elif button_id == "reset":
            self.task.reset()
            self.task.remove_class("active", "complete", "failed")
            logging.info(f"Reset task: {self.task.title}")

        elif button_id == "done":
            self.task.complete()
            logging.info(f"Completed task: {self.task.title}")


if __name__ == "__main__":
    app = ProgressDemo()
    app.run()
    sys.exit(app.return_code or 0)
