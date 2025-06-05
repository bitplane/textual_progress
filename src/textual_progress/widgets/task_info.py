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
        height: 5;
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

        lines = []

        # Title
        lines.append(f"Title: {self.task.title}")

        # Progress info
        if self.task.is_indeterminate:
            lines.append("Progress: Indeterminate")
        else:
            pct = self.task.percentage
            pct_str = f" ({pct:.1%})" if pct is not None else ""
            lines.append(f"Progress: {self.task.progress}/{self.task.total}{pct_str}")

        # Local progress (if different from total)
        if self.task.local_progress != self.task.progress or self.task.local_total != self.task.total:
            if self.task.local_total is None:
                lines.append(f"Local: {self.task.local_progress} (indeterminate)")
            else:
                local_pct = self.task.local_progress / self.task.local_total if self.task.local_total > 0 else 0
                lines.append(f"Local: {self.task.local_progress}/{self.task.local_total} ({local_pct:.1%})")

        # State classes
        classes = []
        for cls in ["pending", "active", "complete", "failed", "indeterminate"]:
            if self.task.has_class(cls):
                classes.append(cls)

        if classes:
            lines.append(f"State: {', '.join(classes)}")
        else:
            lines.append("State: none")

        return "\n".join(lines)

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
            self.watch(task, "progress", self._on_task_change)
            self.watch(task, "total", self._on_task_change)
            self.refresh()

    def _on_task_change(self, *args) -> None:
        """Handle changes in the watched task."""
        self.refresh()
