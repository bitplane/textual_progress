#!/usr/bin/env python3
"""
Simple progress tracking demo with logging.
"""

import sys
import asyncio
import logging
from textual.app import App, ComposeResult
from textual.widgets import Static, Button, ListView, ListItem, Label, RichLog, OptionList
from textual.containers import Vertical, Horizontal
from textual.reactive import reactive

from textual_progress import Task, Spinner, TaskInfo


# Task factory functions
def create_manual_task(title: str) -> Task:
    """Create a manual task that needs user control."""
    task = Task(title, total=5)  # 5 steps
    logging.info(f"Created: {title}")
    return task


def create_auto_task(title: str) -> Task:
    """Create an auto task that starts immediately."""
    task = Task(title, total=None)  # Indeterminate
    task.add_class("active")
    logging.info(f"Created: {title} (active)")
    return task


def create_percent_task(title: str, total: int = 100) -> Task:
    """Create a percentage task that can be started."""
    task = Task(title, total=total)
    logging.info(f"Created: {title} (0/{total})")
    return task


def create_none_task() -> None:
    """Create no task - returns None to clear selection."""
    logging.info("Cleared selection")
    return None


def start_percent_task(task: Task, app_instance) -> None:
    """Start a percentage task with automatic progress updates."""
    task.add_class("active")
    logging.info(f"Starting percent task: {task.title}")

    async def update_progress():
        total = int(task.total or 100)
        for i in range(total + 1):
            if not task or task.has_class("failed"):
                logging.info(f"Percent task stopped: {task.title}")
                break
            task.local_completed = i
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

    #spinners {
        width: 1fr;
        padding: 1;
        overflow-y: auto;
    }

    #textual-spinner-row, #rich-spinner-row {
        height: 3;
        align: left middle;
    }

    #rich-spinner {
        height: 3;
    }

    .heading {
        text-style: bold underline;
    }

    .subheading {
        text-style: bold;
    }

    #textual-label {
        margin-left: 2;
        content-align: left middle;
        color: $text-muted;
    }

    #spinner-list {
        width: auto;
        margin-right: 2;
        height: 3;
        border: none;
        min-width: 25;
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

    Spinner {
        height: 3;
        margin: 0 1;
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
                    yield Button("⏹", id="stop")
                    yield Button("⏮", id="reset")
                    yield Button("⏭", id="done")

            # Spinners panel (right side)
            with Vertical(id="spinners"):
                yield TaskInfo(id="task-info")

                # Main heading
                yield Static()
                yield Label("Spinners", classes="heading")

                # Rich Spinner section
                yield Static()
                yield Label("Rich", classes="subheading")
                with Horizontal(id="rich-spinner-row"):
                    # Get available Rich spinners for the list (filter out problematic ones)
                    from rich.spinner import SPINNERS

                    # Get all available Rich spinners
                    spinner_names = list(SPINNERS.keys())
                    from textual.widgets.option_list import Option

                    yield OptionList(*[Option(name, id=name) for name in spinner_names], id="spinner-list")
                    yield Spinner(id="rich-spinner")

                # Multi-line Spinner section
                yield Static()
                yield Label("Multi-line", classes="subheading")
                with Horizontal(id="textual-spinner-row"):
                    yield Spinner(id="textual-spinner")
                    yield Static("[Built-in]", id="textual-label")

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
        """Watch for task changes and update spinner."""
        logging.info(f"Task changed to: {task.title if task else None}")

        # Update widgets with the new task
        textual_spinner = self.query_one("#textual-spinner", Spinner)
        textual_spinner.task = task

        rich_spinner = self.query_one("#rich-spinner", Spinner)
        rich_spinner.task = task

        task_info = self.query_one("#task-info", TaskInfo)
        task_info.task = task

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

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        """Handle spinner option highlighting (navigation)."""
        if event.option_list.id == "spinner-list":
            spinner_name = str(event.option.id)
            logging.info(f"Changed spinner to: {spinner_name}")

            # Update the Rich spinner
            rich_spinner = self.query_one("#rich-spinner", Spinner)
            try:
                rich_spinner.set_rich_spinner(spinner_name)
                logging.info(f"Rich spinner changed to {spinner_name} with {len(rich_spinner.frames)} frames")
            except ValueError as e:
                logging.error(f"Failed to set Rich spinner: {e}")


if __name__ == "__main__":
    app = ProgressDemo()
    app.run()
    sys.exit(app.return_code or 0)
