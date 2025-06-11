"""Progress bars tab for the demo."""

from typing import Optional
from textual.app import ComposeResult
from textual.containers import Vertical, Container
from textual.widgets import Static, Label
from textual.reactive import reactive

from textual_progress import Task
from textual_progress.widgets import ProgressBar


class ProgressTab(Static):
    """Tab showing various progress bar demos."""

    CSS = """
    ProgressTab {
        width: 100%;
        height: 100%;
        padding: 1;
    }

    .demo-section {
        margin-bottom: 2;
        padding: 1;
        border: dashed $surface;
    }

    .section-title {
        text-style: bold;
        margin-bottom: 1;
    }

    ProgressBar {
        margin-bottom: 1;
    }

    .no-task {
        text-align: center;
        text-style: italic dim;
        margin-top: 4;
    }
    """

    task = reactive[Optional[Task]](None)
    """The currently selected task from the main demo"""

    def compose(self) -> ComposeResult:
        """Create the progress demos."""
        with Container():
            yield Label("Progress Bar Views", classes="section-title")

            # Standard progress bar
            with Vertical(classes="demo-section"):
                yield Label("Standard Progress Bar:", classes="section-title")
                yield ProgressBar(id="standard-progress")

            # Compact progress bar
            with Vertical(classes="demo-section"):
                yield Label("Compact Progress Bar:", classes="section-title")
                yield ProgressBar(id="compact-progress", compact=True)

            # Minimal progress bar (no time info)
            with Vertical(classes="demo-section"):
                yield Label("Minimal Progress Bar:", classes="section-title")
                yield ProgressBar(id="minimal-progress", show_elapsed=False, show_remaining=False, show_speed=False)

            # No percentage progress bar
            with Vertical(classes="demo-section"):
                yield Label("No Percentage Progress Bar:", classes="section-title")
                yield ProgressBar(id="no-percent-progress", show_percentage=False)

            yield Label("Select a task from the left panel to see progress bars", classes="no-task")

    def update_task(self, task: Optional[Task]) -> None:
        """Update all progress bars with the new task."""
        self.task = task

        # Update all progress bars
        self.query_one("#standard-progress", ProgressBar).task = task
        self.query_one("#compact-progress", ProgressBar).task = task
        self.query_one("#minimal-progress", ProgressBar).task = task
        self.query_one("#no-percent-progress", ProgressBar).task = task

        # Show/hide the no-task message
        no_task_label = self.query(".no-task").first()
        if no_task_label:
            no_task_label.display = task is None
