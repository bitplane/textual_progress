"""
Task information widget that displays ProgressNode attributes.

This widget provides a detailed view of a ProgressNode's current state,
including progress values, percentages, and CSS classes.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from textual.widget import Widget
from textual.reactive import reactive

if TYPE_CHECKING:
    from ..task import Task


class TaskInfo(Widget):
    """A widget that displays detailed information about a Task.

    Shows key attributes like title, progress, total, percentage, and state classes.

    Attributes:
        task: The Task to display information for
    """

    DEFAULT_CSS = """
    TaskInfo {
        height: auto;
        padding: 0 1;
        border: solid;
        background: $surface;
    }
    """

    # Reactive attributes
    task = reactive[Optional["Task"]](None)

    def __init__(self, task: Optional["Task"] = None, **kwargs):
        """Initialize the task info widget.

        Args:
            task: Task to display information for
            **kwargs: Additional widget arguments
        """
        super().__init__(**kwargs)

        if task is not None:
            self.task = task

    def render(self) -> str:
        """Render the task information.

        Returns:
            Formatted string showing task details
        """
        if not self.task:
            return "No task selected"

        # Create compact single-line display like Textual's ProgressBar
        title = f"[bold]{self.task.title}[/bold]"

        if self.task.is_indeterminate:
            progress_info = "[dim]indeterminate[/dim]"
        else:
            pct = self.task.percentage
            if pct is not None:
                progress_info = f"{self.task.completed}/{self.task.total} ([cyan]{pct:.0%}[/cyan])"
            else:
                progress_info = f"{self.task.completed}/{self.task.total}"

        # State indicator
        state_colors = {
            "pending": "[dim]●[/dim]",
            "active": "[yellow]●[/yellow]",
            "complete": "[green]●[/green]",
            "failed": "[red]●[/red]",
            "indeterminate": "[blue]●[/blue]",
        }

        state_indicator = "[dim]○[/dim]"  # Default
        for state, indicator in state_colors.items():
            if self.task.has_class(state):
                state_indicator = indicator
                break

        return f"{state_indicator} {title} {progress_info}"

    def watch_task(self, task: Optional["Task"]) -> None:
        """Handle changes to the task being watched.

        Args:
            task: New task to watch, or None to stop
        """
        if task is None:
            self.refresh()
        else:
            # Watch for changes that should trigger a refresh
            self.watch(task, "title", self._on_task_change)
            self.watch(task, "completed", self._on_task_change)
            self.watch(task, "total", self._on_task_change)
            self.refresh()

    def _on_task_change(self, *args) -> None:
        """Handle changes in the watched task."""
        self.refresh()
