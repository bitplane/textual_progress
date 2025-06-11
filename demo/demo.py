#!/usr/bin/env python3
"""
Simple progress tracking demo with logging.
"""

import sys
import logging
from textual.app import App, ComposeResult
from textual.widgets import Button, ListView, ListItem, Label, RichLog, TabbedContent, TabPane
from textual.containers import Vertical, Horizontal
from textual.reactive import reactive

from textual_progress import Task, TaskInfo
from spinners import SpinnersTab
from progress_tab import ProgressTab
from tasks import TASK_REGISTRY


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
        layout: vertical;
    }

    #top-area {
        layout: horizontal;
        height: 2fr;
    }

    #tasks {
        width: 22;
        padding: 1;
    }

    #right-panel {
        width: 1fr;
        padding: 1;
    }

    .heading {
        text-style: bold underline;
    }

    #log-panel {
        height: 1fr;
        padding: 0;
    }

    .controls {
        height: 3;
        width: 100%;
        dock: bottom;
        layout: horizontal;
    }

    .controls Button {
        width: 1fr;
        height: 3;
        margin: 0;
        padding: 0;
        content-align: center middle;
        max-width: 5;
    }

    ListView {
        height: 1fr;
    }


    RichLog {
        height: 100%;
        border: solid;
        padding: 0 1;
        margin: 0;
    }
    """

    # Reactive task that all spinners will watch
    task = reactive[Task | None](None)

    def compose(self) -> ComposeResult:
        """Create the app layout."""
        # Top area with tasks and spinners
        with Horizontal(id="top-area"):
            # Tasks panel (left side)
            with Vertical(id="tasks"):
                items = [TaskItem(name) for name in TASK_REGISTRY.keys()]
                yield ListView(*items, id="task-list")

                # Controls
                with Horizontal(classes="controls"):
                    yield Button("▶", id="play")
                    yield Button("■", id="stop")
                    yield Button("⏮", id="reset")
                    yield Button("⏭", id="done")

            # Right panel with TaskInfo header and tabs
            with Vertical(id="right-panel"):
                # Task info header
                yield TaskInfo(id="task-info")

                # Tabbed content
                with TabbedContent(id="main-tabs"):
                    with TabPane("Spinners", id="spinners-tab"):
                        yield SpinnersTab(id="spinners-content")
                    with TabPane("Progress", id="progress-tab"):
                        yield ProgressTab(id="progress-content")

        # Log panel (bottom, full width)
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

    def watch_task(self, task: Task | None) -> None:
        """Watch for task changes and update spinners."""
        logging.info(f"Task changed to: {task.title if task else None}")

        # Update task info widget
        task_info = self.query_one("#task-info", TaskInfo)
        task_info.task = task

        # Update spinners in the SpinnersTab
        try:
            spinners_tab = self.query_one("#spinners-content", SpinnersTab)
            spinners_tab.update_spinners_task(task)
        except Exception:
            pass

        # Update progress bars in the ProgressTab
        try:
            progress_tab = self.query_one("#progress-content", ProgressTab)
            progress_tab.update_task(task)
        except Exception:
            pass

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Handle task navigation - create task when highlighted."""
        if isinstance(event.item, TaskItem):
            task_name = event.item.task_name

            # Get task config from registry
            factory_func, args, start_func = TASK_REGISTRY[task_name]

            # Create the task using factory function and args
            self.task = factory_func(*args)

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

    def log_info(self, message: str) -> None:
        """Log info message."""
        logging.info(message)

    def log_error(self, message: str) -> None:
        """Log error message."""
        logging.error(message)


if __name__ == "__main__":
    app = ProgressDemo()
    app.run()
    sys.exit(app.return_code or 0)
