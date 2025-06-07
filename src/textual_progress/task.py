"""
Task - Universal progress tracking with automatic aggregation.

A reactive task system that automatically aggregates child progress
and supports async context managers for automatic lifecycle management.
"""

from __future__ import annotations

from time import time
from typing import Dict, Optional
from threading import RLock

from textual.dom import DOMNode
from textual.reactive import reactive
from rich.progress import Task as RichTask, TaskID
from rich.spinner import SPINNERS


class Task(DOMNode):
    """A task that tracks progress and automatically aggregates from children.

    Supports both manual control and automatic lifecycle management via async context managers.
    Tasks can be nested and will automatically aggregate progress from children.

    Attributes:
        completed: Current completed steps/units
        total: Total steps/units (None for indeterminate progress)
        title: Display title for this task
        start_time: When this task was started (Unix timestamp)
        last_updated: When this was last modified (Unix timestamp)
    """

    # Core progress attributes
    completed = reactive(0.0)
    """Current completed steps/units"""
    total = reactive[Optional[float]](None)
    """Total steps/units (None for indeterminate progress)"""
    title = reactive("")
    """Display title for this task"""
    start_time = reactive[Optional[float]](None)
    """When this task was started (Unix timestamp)"""
    last_updated = reactive[Optional[float]](None)
    """When this was last modified (Unix timestamp)"""

    # Local values (not including children)
    _local_completed = reactive(0.0)
    _local_total = reactive[Optional[float]](None)

    def __init__(self, title: str = "", total: Optional[float] = None, **kwargs):
        """Initialize a task.

        Args:
            title: Display title for this task
            total: Total number of steps/units (None for indeterminate)
            **kwargs: Additional DOMNode arguments
        """
        # Initialize children dict before calling super() to avoid any reactive issues
        self._children: Dict[str, Task] = {}

        super().__init__(**kwargs)
        self.title = title

        # Set initial values (may trigger watchers, so _children must exist first)
        self._local_total = total
        self.total = total

        # Initial aggregation
        self._update_aggregation()

    def __getitem__(self, key: str) -> Task:
        """Get or create a child task.

        Args:
            key: Identifier for the child task

        Returns:
            The child Task (created if it doesn't exist)
        """
        if key not in self._children:
            child = Task(title=key)
            self._children[key] = child
            self.mount(child)  # Add to DOM tree

            # Watch child for changes to aggregate up
            child.watch("progress", self._update_aggregation)
            child.watch("total", self._update_aggregation)
            child.watch("title", self._update_aggregation)

        return self._children[key]

    def __setitem__(self, key: str, node: "Task") -> None:
        """Set a child task.

        Args:
            key: Identifier for the child task
            node: The Task to set as child
        """
        if key in self._children:
            # Remove old child
            old_child = self._children[key]
            old_child.remove()

        self._children[key] = node
        self.mount(node)

        # Watch for changes
        node.watch("progress", self._update_aggregation)
        node.watch("total", self._update_aggregation)
        node.watch("title", self._update_aggregation)

    def __contains__(self, key: str) -> bool:
        """Check if a child task exists.

        Args:
            key: Identifier to check

        Returns:
            True if child exists
        """
        return key in self._children

    def __iter__(self):
        """Iterate over child keys."""
        return iter(self._children)

    def items(self):
        """Get (key, task) pairs for children."""
        return self._children.items()

    def values(self):
        """Get child tasks."""
        return self._children.values()

    @property
    def percentage(self) -> Optional[float]:
        """Progress percentage (0.0 to 1.0), or None if indeterminate.

        Returns:
            Percentage complete, or None if total is unknown
        """
        if self.total is None or self.total == 0:
            return None
        return min(1.0, max(0.0, self.completed / self.total))

    @property
    def is_indeterminate(self) -> bool:
        """Check if this progress is indeterminate (unknown total).

        Returns:
            True if total is unknown
        """
        return self.total is None

    @property
    def local_completed(self) -> float:
        """This task's completed amount excluding children."""
        return self._local_completed

    @local_completed.setter
    def local_completed(self, value: float) -> None:
        """Set this task's local completed amount."""
        self._local_completed = value

    @property
    def local_total(self) -> Optional[float]:
        """This task's total excluding children."""
        return self._local_total

    @local_total.setter
    def local_total(self, value: Optional[float]) -> None:
        """Set this task's local total."""
        self._local_total = value

    @property
    def current_task(self) -> str:
        """Title of the most recently active task (bubbles up from children).

        Returns:
            The title of the most recently updated active item in the tree
        """
        if not self._children:
            return self.title

        # Find most recently updated child
        active_children = [
            child for child in self._children.values() if child.last_updated is not None and child.completed > 0
        ]

        if active_children:
            most_recent = max(active_children, key=lambda c: c.last_updated or 0)
            return most_recent.current_task  # Recursive

        return self.title

    def watch__local_completed(self, value: float) -> None:
        """Handle local completed changes."""
        self.last_updated = time()
        self._update_aggregation()

    def watch__local_total(self, value: Optional[float]) -> None:
        """Handle local total changes."""
        if value is not None and self.start_time is None:
            self.start_time = time()
        self._update_aggregation()

    def _update_aggregation(self, *args) -> None:
        """Update aggregated completed and total from local values and children."""
        # Calculate aggregated completed
        child_completed = sum(child.completed for child in self._children.values())
        self.completed = self._local_completed + child_completed

        # Calculate aggregated total
        if not self._children:
            self.total = self._local_total
        else:
            # If any child is indeterminate, we become indeterminate
            child_totals = []
            for child in self._children.values():
                if child.total is None:
                    self.total = None  # Indeterminate child makes parent indeterminate
                    return
                child_totals.append(child.total)

            local_total = self._local_total or 0
            self.total = local_total + sum(child_totals)

        # Update state classes and bubble up to parent
        self._update_state_classes()

        # Update timestamp to reflect activity
        child_timestamps = [child.last_updated for child in self._children.values() if child.last_updated]
        if child_timestamps:
            latest_child = max(child_timestamps)
            if not self.last_updated or latest_child > self.last_updated:
                self.last_updated = latest_child

    def _update_state_classes(self) -> None:
        """Update CSS classes based on current state."""
        # Clear existing state classes
        self.remove_class("pending", "active", "complete", "indeterminate")

        # Set appropriate state class
        if self.is_indeterminate:
            self.add_class("indeterminate")
        elif self.completed == 0:
            self.add_class("pending")
        elif self.percentage and self.percentage >= 1.0:
            self.add_class("complete")
        else:
            self.add_class("active")

    def advance(self, amount: float = 1.0) -> None:
        """Advance local completed by the given amount.

        Args:
            amount: Amount to advance completed by
        """
        self.local_completed += amount

    def reset(self) -> None:
        """Reset local completed to zero and clear timing."""
        self._local_completed = 0.0
        self.start_time = None
        self.last_updated = None
        self.remove_class("active", "complete", "failed")
        self.add_class("pending")

    def complete(self) -> None:
        """Mark this task as complete."""
        if self._local_total is not None:
            self._local_completed = self._local_total
        self.remove_class("pending", "active", "failed")
        self.add_class("complete")

    def fail(self, reason: str = "") -> None:
        """Mark this task as failed.

        Args:
            reason: Optional failure reason
        """
        self.remove_class("pending", "active", "complete")
        self.add_class("failed")
        # Note: Store reason in a custom attribute if needed

    def subtask(self, key: str, total: Optional[float] = None) -> "Task":
        """Get or create a subtask in pending state.

        Args:
            key: Identifier for the subtask
            total: Total steps for the subtask (None for indeterminate)

        Returns:
            The subtask (created if it doesn't exist)
        """
        if key not in self._children:
            child = Task(title=key, total=total)
            self._children[key] = child
            self.mount(child)

            # Watch child for changes to aggregate up
            child.watch("completed", self._update_aggregation)
            child.watch("total", self._update_aggregation)
            child.watch("title", self._update_aggregation)

        return self._children[key]

    async def __aenter__(self):
        """Mark task as active when entering async context."""
        self.remove_class("pending", "complete", "failed")
        self.add_class("active")
        if self.start_time is None:
            self.start_time = time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Mark complete or failed when exiting async context."""
        if exc_type is None:
            self.complete()
        else:
            self.fail(str(exc_val) if exc_val else "Task failed")
        # Don't suppress exceptions
        return False

    def to_rich_task(self, task_id: Optional[int] = None) -> RichTask:
        """Create a Rich Task that mirrors this Task's state.

        Args:
            task_id: Optional task ID (will generate one if not provided)

        Returns:
            Rich Task instance with current state
        """
        # Create a Rich Task with our current state
        rich_task = RichTask(
            id=TaskID(task_id or hash(self) % 1000000),
            description=self.title,
            total=self.total,
            completed=self.completed,
            _get_time=time,
            visible=True,
            fields={},
            _lock=RLock(),
        )

        return rich_task

    @staticmethod
    def get_rich_spinner_names() -> list[str]:
        """Get all available Rich spinner names.

        Returns:
            List of spinner names
        """
        return list(SPINNERS.keys())

    @staticmethod
    def get_rich_spinner_frames(name: str) -> tuple[list[str], int]:
        """Get frames and interval for a Rich spinner.

        Args:
            name: Spinner name

        Returns:
            Tuple of (frames, interval_ms)
        """
        if name not in SPINNERS:
            raise ValueError(f"Unknown spinner: {name}. Available: {list(SPINNERS.keys())[:5]}...")

        spinner_data = SPINNERS[name]
        return spinner_data["frames"], spinner_data.get("interval", 80)
