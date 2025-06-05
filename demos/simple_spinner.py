#!/usr/bin/env python3
"""
Simple spinner demo showing the basic Spinner widget in action.
"""

import sys
from pathlib import Path

# Add the src directory to the path so we can import our package
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from textual.app import App, ComposeResult
from textual.widgets import Static, Button
from textual.containers import Vertical, Horizontal

from textual_progress import ProgressNode, Spinner


class SpinnerDemo(App):
    """Demo app showing a simple spinner."""

    CSS = """
    Screen {
        align: center middle;
    }

    Vertical {
        width: 40;
        height: auto;
        border: solid $primary;
        padding: 2;
    }

    Static {
        text-align: center;
        margin-bottom: 1;
    }

    Spinner {
        margin: 1 0;
    }

    Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Create the demo layout."""
        # Create a progress task
        self.task = ProgressNode("Demo Task")

        with Vertical():
            yield Static("Spinner Demo", classes="title")
            yield Static("Watch the Braille spinner animate:")
            yield Spinner(task=self.task, id="spinner")

            with Horizontal():
                yield Button("Start Task", id="start", variant="success")
                yield Button("Complete Task", id="complete", variant="primary")
                yield Button("Reset", id="reset", variant="error")

            yield Static("The spinner will animate until the task is complete", classes="help")

    def on_mount(self) -> None:
        """Start with a spinning task."""
        # Set task to active state (indeterminate progress)
        self.task.add_class("active")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        if event.button.id == "start":
            # Start an active task
            self.task.remove_class("pending", "complete", "failed")
            self.task.add_class("active")
            self.task.local_total = 100
            self.task.local_progress = 0

        elif event.button.id == "complete":
            # Complete the task
            self.task.complete()

        elif event.button.id == "reset":
            # Reset to pending state
            self.task.reset()
            self.task.remove_class("active", "complete", "failed")
            self.task.add_class("pending")


if __name__ == "__main__":
    app = SpinnerDemo()
    app.run()
