"""
Task system with clean separation between leaf tasks and branch containers.

- Task: A leaf node that tracks individual progress
- Tasks: A branch node that aggregates multiple Task nodes
"""

from __future__ import annotations

from time import time
from typing import Dict, Optional

from textual.dom import DOMNode
from textual.reactive import reactive
from rich.progress import Task as RichTask, TaskID
from rich.spinner import SPINNERS


class Task(DOMNode):
    """A leaf task that tracks individual progress.

    This is a simple, focused node that only manages its own progress
    without any child aggregation complexity.
    """

    # Core progress
    completed = reactive(0.0)
    """Current completed steps/units"""
    total = reactive[Optional[float]](None)
    """Total steps/units (None for indeterminate)"""

    # Metadata
    title = reactive("")
    """Display title for this task"""
    start_time = reactive[Optional[float]](None)
    """When this task was started"""
    last_updated = reactive[Optional[float]](None)
    """When this was last modified"""
    stop_time = reactive[Optional[float]](None)
    """When this task was stopped/finished"""
    finished_time = reactive[Optional[float]](None)
    """When this task was completed successfully"""

    # Progress tracking for speed
    _samples = reactive(list, always_update=True)
    """List of (timestamp, completed) tuples for speed calculation"""

    # Transfer context (optional)
    transfer_unit: Optional[str] = None
    transfer_total_size: Optional[int] = None

    def __init__(
        self,
        title: str = "",
        total: Optional[float] = None,
        transfer_unit: Optional[str] = None,
        transfer_total_size: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.title = title
        self.total = total
        self.transfer_unit = transfer_unit
        self.transfer_total_size = transfer_total_size

        # Initialize samples
        self._samples = [(time(), 0.0)]

    # Computed properties
    @property
    def percentage(self) -> Optional[float]:
        """Progress percentage (0.0-1.0)."""
        if self.total is None or self.total == 0:
            return None
        return min(1.0, max(0.0, self.completed / self.total))

    @property
    def indeterminate(self) -> bool:
        """Whether progress is indeterminate."""
        return self.total is None

    @property
    def elapsed(self) -> Optional[float]:
        """Time elapsed since start."""
        if self.start_time is None:
            return None
        end_time = self.stop_time or time()
        return end_time - self.start_time

    @property
    def remaining(self) -> Optional[float]:
        """Steps remaining to complete."""
        if self.total is None:
            return None
        return max(0.0, self.total - self.completed)

    @property
    def finished(self) -> bool:
        """Whether task is complete or failed."""
        return self.has_class("complete") or self.has_class("failed")

    @property
    def speed(self) -> float:
        """Current speed in steps per second."""
        return self._calculate_speed()

    @property
    def time_remaining(self) -> Optional[float]:
        """Estimated time to completion."""
        if self.speed <= 0 or self.remaining is None:
            return None
        return self.remaining / self.speed

    def _calculate_speed(self) -> float:
        """Calculate speed from recent samples."""
        if len(self._samples) < 2:
            return 0.0

        # Use last second of samples
        now = time()
        cutoff = now - 1.0
        recent = [(t, c) for t, c in self._samples if t >= cutoff]

        if len(recent) < 2:
            # Fall back to all samples
            recent = self._samples
            if len(recent) < 2:
                return 0.0

        # Calculate from first to last
        time_delta = recent[-1][0] - recent[0][0]
        if time_delta <= 0:
            return 0.0

        progress_delta = recent[-1][1] - recent[0][1]
        return progress_delta / time_delta

    def _add_sample(self, completed: float):
        """Add a progress sample."""
        now = time()
        # Keep last 999 samples + new one
        samples = list(self._samples[-999:])
        samples.append((now, completed))
        self._samples = samples

    def _update_state_classes(self):
        """Update CSS classes based on state."""
        self.remove_class("pending", "active", "complete", "indeterminate", "failed")

        if self.indeterminate:
            self.add_class("indeterminate")
        elif self.completed == 0:
            self.add_class("pending")
        elif self.percentage and self.percentage >= 1.0:
            self.add_class("complete")
        else:
            self.add_class("active")

    # Watchers
    def watch_completed(self, value: float):
        """Handle completed changes."""
        self.last_updated = time()
        self._add_sample(value)
        self._update_state_classes()

        # Notify parent if it's a Tasks container
        if isinstance(self.parent, Tasks):
            self.parent._on_child_changed()

    def watch_total(self, value: Optional[float]):
        """Handle total changes."""
        if value is not None and self.start_time is None:
            self.start_time = time()
        self._update_state_classes()

        # Notify parent
        if isinstance(self.parent, Tasks):
            self.parent._on_child_changed()

    # Task control
    def advance(self, amount: float = 1.0):
        """Advance completed by amount."""
        self.completed += amount

    def reset(self):
        """Reset to initial state."""
        self.completed = 0.0
        self.start_time = None
        self.last_updated = None
        self.stop_time = None
        self.finished_time = None
        self._samples = [(time(), 0.0)]
        self._update_state_classes()

    def complete(self):
        """Mark as complete."""
        if self.total is not None:
            self.completed = self.total

        now = time()
        self.finished_time = now
        if self.stop_time is None:
            self.stop_time = now

        self.remove_class("pending", "active", "failed")
        self.add_class("complete")

    def fail(self, reason: str = ""):
        """Mark as failed."""
        if self.stop_time is None:
            self.stop_time = time()

        self.remove_class("pending", "active", "complete")
        self.add_class("failed")

    # Rich integration
    def to_rich_task(self, task_id: Optional[int] = None) -> RichTask:
        """Create Rich Task."""
        rich_task = RichTask(
            id=TaskID(task_id or hash(self) % 1000000),
            description=self.title,
            total=self.total,
            completed=self.completed,
            _get_time=time,
            visible=True,
            fields={},
            _lock=None,
        )

        # Add timing
        if self.start_time is not None:
            rich_task.start_time = self.start_time
        if self.stop_time is not None:
            rich_task.stop_time = self.stop_time
        if self.finished_time is not None:
            rich_task.finished_time = self.finished_time

        # Add computed fields
        rich_task.fields.update(
            {
                "elapsed": self.elapsed,
                "speed": self.speed,
                "time_remaining": self.time_remaining,
                "finished": self.finished,
                "remaining": self.remaining,
            }
        )

        # Transfer context
        if self.transfer_unit:
            rich_task.fields["transfer_unit"] = self.transfer_unit
        if self.transfer_total_size:
            rich_task.fields["transfer_total_size"] = self.transfer_total_size
            if self.percentage is not None:
                rich_task.fields["transfer_completed_size"] = int(self.transfer_total_size * self.percentage)

        return rich_task

    # Async context manager
    async def __aenter__(self):
        """Start task."""
        self.remove_class("pending", "complete", "failed")
        self.add_class("active")
        if self.start_time is None:
            self.start_time = time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """End task."""
        if exc_type is None:
            self.complete()
        else:
            self.fail(str(exc_val) if exc_val else "Task failed")
        return False


class Tasks(DOMNode):
    """A branch node that aggregates multiple Task nodes.

    This container manages a collection of Task nodes and provides
    aggregated progress information.
    """

    # Aggregated values (cached from children)
    completed = reactive(0.0)
    """Total completed from all children"""
    total = reactive[Optional[float]](None)
    """Total from all children"""
    percentage = reactive[Optional[float]](None)
    """Overall progress percentage"""
    speed = reactive(0.0)
    """Combined speed from all children"""
    elapsed = reactive[Optional[float]](None)
    """Time elapsed since first child started"""
    time_remaining = reactive[Optional[float]](None)
    """Estimated time to completion"""
    remaining = reactive[Optional[float]](None)
    """Total remaining work"""
    finished = reactive(False)
    """Whether all children are finished"""
    indeterminate = reactive(True)
    """Whether progress is indeterminate"""

    # Metadata
    title = reactive("")
    """Display title for this task group"""

    def __init__(self, title: str = "", **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self._children: Dict[str, Task] = {}

    def _on_child_changed(self):
        """Called when a child task changes."""
        self._update_aggregated_values()

    def _update_aggregated_values(self):
        """Update aggregated values from children."""
        children = list(self._children.values())

        if not children:
            self.completed = 0.0
            self.total = None
            self.percentage = None
            self.speed = 0.0
            self.elapsed = None
            self.time_remaining = None
            self.remaining = None
            self.finished = False
            self.indeterminate = True
            return

        # Aggregate completed
        self.completed = sum(child.completed for child in children)

        # Aggregate total (None if any child is indeterminate)
        child_totals = [child.total for child in children]
        if any(t is None for t in child_totals):
            self.total = None
            self.indeterminate = True
            self.percentage = None
            self.remaining = None
        else:
            self.total = sum(child_totals)
            self.indeterminate = False
            if self.total > 0:
                self.percentage = min(1.0, self.completed / self.total)
                self.remaining = max(0.0, self.total - self.completed)
            else:
                self.percentage = 1.0
                self.remaining = 0.0

        # Aggregate speed
        self.speed = sum(child.speed for child in children)

        # Earliest start time
        start_times = [child.start_time for child in children if child.start_time]
        if start_times:
            earliest = min(start_times)
            self.elapsed = time() - earliest
        else:
            self.elapsed = None

        # Time remaining
        if self.speed > 0 and self.remaining is not None:
            self.time_remaining = self.remaining / self.speed
        else:
            self.time_remaining = None

        # Finished if all children finished
        self.finished = all(child.finished for child in children)

    # Child management
    def add_task(self, key: str, task: Task) -> Task:
        """Add a child task."""
        if key in self._children:
            old_task = self._children[key]
            old_task.remove()

        self._children[key] = task
        self.mount(task)
        self._update_aggregated_values()
        return task

    def create_task(self, key: str, title: str = "", total: Optional[float] = None) -> Task:
        """Create and add a new task."""
        task = Task(title=title or key, total=total)
        return self.add_task(key, task)

    def __getitem__(self, key: str) -> Task:
        """Get task by key."""
        return self._children[key]

    def __setitem__(self, key: str, task: Task):
        """Set task by key."""
        self.add_task(key, task)

    def __contains__(self, key: str) -> bool:
        """Check if task exists."""
        return key in self._children

    def __iter__(self):
        """Iterate over task keys."""
        return iter(self._children)

    def items(self):
        """Get (key, task) pairs."""
        return self._children.items()

    def values(self):
        """Get tasks."""
        return self._children.values()

    def keys(self):
        """Get task keys."""
        return self._children.keys()

    @property
    def current_task(self) -> str:
        """Title of most recently active task."""
        if not self._children:
            return self.title

        # Find most recently updated
        active = [child for child in self._children.values() if child.last_updated is not None and child.completed > 0]

        if active:
            most_recent = max(active, key=lambda c: c.last_updated or 0)
            return most_recent.title

        return self.title


# Spinner support (kept for compatibility)
def get_rich_spinner_names() -> list[str]:
    """Get all available Rich spinner names."""
    return list(SPINNERS.keys())


def get_rich_spinner_frames(name: str) -> tuple[list[str], int]:
    """Get frames and interval for a Rich spinner."""
    if name not in SPINNERS:
        raise ValueError(f"Unknown spinner: {name}")

    spinner_data = SPINNERS[name]
    return spinner_data["frames"], spinner_data.get("interval", 80)
