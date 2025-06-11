"""
Spinner widget that displays animated progress indicators.

This module provides a simple spinner widget that cycles through character frames
to indicate ongoing progress. It watches a ProgressNode for completion state.
"""

from __future__ import annotations

import asyncio
from typing import Optional, TYPE_CHECKING

from textual.widget import Widget
from textual.reactive import reactive
from rich.spinner import SPINNERS
from rich.text import Text

if TYPE_CHECKING:
    from ..task import Task


class Spinner(Widget):
    """A spinning animation widget that indicates ongoing progress.

    The spinner cycles through a list of character frames to show activity.
    It automatically stops when the associated task is complete.

    Attributes:
        task: The ProgressNode to watch for completion
        frames: List of characters to cycle through
        speed: Time between frame changes in seconds
    """

    DEFAULT_CSS = """
    Spinner {
        width: 21;
        height: 1;
        text-align: left;
        content-align: left middle;
    }
    """

    # Reactive attributes
    task = reactive[Optional["Task"]](None)
    frames = reactive(["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"])  # Braille spinner
    speed = reactive(0.08)

    def __init__(
        self, task: Optional["Task"] = None, frames: Optional[list[str]] = None, speed: float = 0.08, **kwargs
    ):
        """Initialize the spinner widget.

        Args:
            task: Task to watch for completion
            frames: List of characters to animate through
            speed: Time between frame changes in seconds
            **kwargs: Additional widget arguments
        """
        # Animation state - initialize before super() to avoid reactive issues
        self._current_frame = 0
        self._animation_task: Optional[asyncio.Task] = None
        self._is_spinning = False

        super().__init__(**kwargs)

        if task is not None:
            self.task = task
        if frames is not None:
            self.frames = frames
        self.speed = speed

    def render(self) -> Text:
        """Render the current spinner frame.

        Returns:
            The current character to display as a Text object
        """
        if not self.frames:
            return Text(" ")
        if not self._is_spinning:
            if self.task is None:
                return Text("○")  # Show placeholder when no task
            else:
                return Text("●")  # Show filled circle when task is stopped/complete
        # Return frame as Text object to avoid markup parsing issues
        return Text(self.frames[self._current_frame])

    def watch_task(self, task: Optional["Task"]) -> None:
        """Handle changes to the task being watched.

        Args:
            task: New task to watch, or None to stop
        """
        if task is None:
            self._stop_spinning()
        else:
            # Watch for task completion
            self.watch(task, "progress", self._on_task_progress)
            self.watch(task, "total", self._on_task_progress)
            self._update_spinning_state()

    def watch_frames(self, frames: list[str]) -> None:
        """Handle changes to the animation frames.

        Args:
            frames: New list of frames to animate
        """
        self._current_frame = 0  # Reset to first frame
        if self._is_spinning:
            self.refresh()

    def watch_speed(self, speed: float) -> None:
        """Handle changes to animation speed.

        Args:
            speed: New animation speed in seconds
        """
        if self._is_spinning:
            # Restart animation with new speed
            self._stop_spinning()
            self._start_spinning()

    def _on_task_progress(self, *args) -> None:
        """Handle progress changes in the watched task."""
        self._update_spinning_state()

    def _update_spinning_state(self) -> None:
        """Update whether the spinner should be active."""
        if self.task is None:
            self._stop_spinning()
            return

        # Spin if task is not complete
        is_complete = (
            self.task.has_class("complete")
            or self.task.has_class("failed")
            or (self.task.percentage is not None and self.task.percentage >= 1.0)
        )

        if is_complete:
            self._stop_spinning()
        else:
            self._start_spinning()

    def _start_spinning(self) -> None:
        """Start the spinner animation."""
        if self._is_spinning or not self.frames:
            return

        self._is_spinning = True
        self._animation_task = asyncio.create_task(self._animation_loop())

    def _stop_spinning(self) -> None:
        """Stop the spinner animation."""
        if not self._is_spinning:
            return

        self._is_spinning = False
        if self._animation_task:
            self._animation_task.cancel()
            self._animation_task = None
        self.refresh()

    async def _animation_loop(self) -> None:
        """Main animation loop that cycles through frames."""
        try:
            while self._is_spinning and self.frames:
                await asyncio.sleep(self.speed)
                if self._is_spinning:  # Check again after sleep
                    self._current_frame = (self._current_frame + 1) % len(self.frames)
                    self.refresh()
        except asyncio.CancelledError:
            pass

    def on_mount(self) -> None:
        """Handle widget mounting - start spinning if we have a task."""
        self._update_spinning_state()

    def on_unmount(self) -> None:
        """Handle widget unmounting - stop spinning."""
        self._stop_spinning()

    def set_rich_spinner(self, name: str) -> None:
        """Set the spinner to use a Rich spinner by name.

        Args:
            name: Name of the Rich spinner to use
        """
        if name not in SPINNERS:
            available = list(SPINNERS.keys())[:5]
            raise ValueError(f"Unknown spinner '{name}'. Available: {available}...")

        spinner_data = SPINNERS[name]
        self.frames = spinner_data["frames"]
        # Convert interval from milliseconds to seconds
        interval_ms = spinner_data.get("interval", 80)
        self.speed = interval_ms / 1000.0
