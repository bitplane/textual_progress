#!/usr/bin/env python3
"""
Simple spinner demo showing the basic Spinner widget in action.
"""

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
        # Create a progress task and store it for button handlers
        self._task = ProgressNode("Demo Task")

        with Vertical():
            yield Static("Spinner Demo", classes="title")
            yield Static("Watch the Braille spinner animate:")
            yield Spinner(task=self._task, id="spinner")

            with Horizontal():
                yield Button("Start Task", id="start", variant="success")
                yield Button("Complete Task", id="complete", variant="primary")
                yield Button("Reset", id="reset", variant="error")

            yield Static("The spinner will animate until the task is complete", classes="help")

    def on_mount(self) -> None:
        """Start with a spinning task."""
        # Set task to active state (indeterminate progress)
        self._task.add_class("active")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        if event.button.id == "start":
            # Start an active task
            self._task.remove_class("pending", "complete", "failed")
            self._task.add_class("active")
            self._task.local_total = 100
            self._task.local_progress = 0

        elif event.button.id == "complete":
            # Complete the task
            self._task.complete()

        elif event.button.id == "reset":
            # Reset to pending state
            self._task.reset()
            self._task.remove_class("active", "complete", "failed")
            self._task.add_class("pending")


if __name__ == "__main__":
    app = SpinnerDemo()
    app.run()
