"""Progress bar widget that displays task progress using Rich progress bars."""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from textual.widget import Widget
from textual.reactive import reactive
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
    SpinnerColumn,
    ProgressColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
)
from rich.text import Text
from rich.console import RenderResult

if TYPE_CHECKING:
    from ..task import Task


class ProgressBar(Widget):
    """A progress bar widget that tracks task progress.

    This widget wraps Rich's Progress display to show progress bars,
    spinners, and other progress indicators based on task state.
    """

    DEFAULT_CSS = """
    ProgressBar {
        height: 1;
        width: 100%;
    }
    """

    task = reactive[Optional["Task"]](None)
    """The task to track progress for"""

    show_speed = reactive(True)
    """Whether to show speed/throughput"""

    show_elapsed = reactive(True)
    """Whether to show elapsed time"""

    show_remaining = reactive(True)
    """Whether to show time remaining"""

    show_percentage = reactive(True)
    """Whether to show percentage complete"""

    compact = reactive(False)
    """Use compact display mode"""

    def __init__(
        self,
        task: Optional["Task"] = None,
        show_speed: bool = True,
        show_elapsed: bool = True,
        show_remaining: bool = True,
        show_percentage: bool = True,
        compact: bool = False,
        **kwargs,
    ):
        """Initialize the progress bar.

        Args:
            task: Optional task to track
            show_speed: Whether to show speed/throughput
            show_elapsed: Whether to show elapsed time
            show_remaining: Whether to show time remaining
            show_percentage: Whether to show percentage complete
            compact: Use compact display mode
            **kwargs: Additional widget arguments
        """
        super().__init__(**kwargs)
        self.task = task
        self.show_speed = show_speed
        self.show_elapsed = show_elapsed
        self.show_remaining = show_remaining
        self.show_percentage = show_percentage
        self.compact = compact

        # Initialize task tracking
        self._task_id = None

        # Create Rich Progress instance with appropriate columns
        self._create_progress()

    def _create_progress(self):
        """Create the Rich Progress instance with appropriate columns."""
        columns = []

        if self.compact:
            # Compact mode: just spinner, description, and bar
            columns.extend(
                [
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                ]
            )
            if self.show_percentage:
                columns.append(TextColumn("[progress.percentage]{task.percentage:>3.0f}%"))
        else:
            # Full mode with all requested columns
            columns.extend(
                [
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                ]
            )

            if self.show_percentage:
                columns.append(TaskProgressColumn())

            if self.show_elapsed:
                columns.append(TimeElapsedColumn())

            if self.show_remaining:
                columns.append(TimeRemainingColumn())

            if self.show_speed and not self.compact:
                # Add custom speed column if task has transfer info
                columns.append(TransferSpeedColumn())

        self._progress = Progress(*columns, expand=True)

    def watch_task(self, task: Optional["Task"]) -> None:
        """Handle task changes."""
        # Remove old task if any
        if hasattr(self, "_task_id") and self._task_id is not None:
            self._progress.remove_task(self._task_id)
            self._task_id = None

        # Add new task if provided
        if task is not None:
            # Convert our Task to Rich task parameters
            self._task_id = self._progress.add_task(
                description=task.title or "Working...",
                total=task.total,
                completed=task.completed,
            )

            # Immediately update progress to current state
            self._update_progress()

    def on_mount(self):
        """Set up update timer when mounted."""
        # Set up periodic refresh to update progress
        self.set_interval(0.1, self._update_progress)

    def _update_progress(self):
        """Update progress from task."""
        if self.task is None or self._task_id is None:
            return

        # Update the Rich task with current values
        self._progress.update(
            self._task_id,
            completed=self.task.completed,
            total=self.task.total,
            description=self.task.title or "Working...",
        )

        # Force refresh to display updates
        self.refresh()

    def render(self) -> RenderResult:
        """Render the progress bar."""
        if self.task is None or self._task_id is None:
            return Text("No task", style="dim")

        # Get a fresh renderable from the progress bar
        return self._progress


class TransferSpeedColumn(ProgressColumn):
    """Custom column for showing transfer speeds."""

    def render(self, task) -> Text:
        """Render the transfer speed."""
        speed = task.fields.get("speed", 0)
        unit = task.fields.get("transfer_unit", "it")

        if speed == 0:
            return Text("--", style="progress.data.speed")

        # Format speed nicely
        if unit == "bytes":
            # Convert to appropriate unit
            if speed >= 1024 * 1024:
                return Text(f"{speed / (1024 * 1024):.1f} MB/s", style="progress.data.speed")
            elif speed >= 1024:
                return Text(f"{speed / 1024:.1f} KB/s", style="progress.data.speed")
            else:
                return Text(f"{speed:.0f} B/s", style="progress.data.speed")
        else:
            return Text(f"{speed:.1f} {unit}/s", style="progress.data.speed")
