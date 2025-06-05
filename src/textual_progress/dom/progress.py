"""
Progress DOM Node - Universal progress tracking with automatic aggregation.

This module provides a DOMNode-based progress system that automatically 
aggregates child progress and integrates with Textual's reactive system.
"""

from __future__ import annotations

from time import time
from typing import Dict, Optional, TYPE_CHECKING

from textual.dom import DOMNode
from textual.reactive import reactive

if TYPE_CHECKING:
    pass


class ProgressNode(DOMNode):
    """A DOM node that tracks progress and automatically aggregates from children.
    
    This class provides a universal progress protocol that aligns with Textual's
    ProgressBar while supporting hierarchical aggregation. Any widget can watch
    these nodes for changes and update their display accordingly.
    
    Attributes:
        progress: Current completed steps/units
        total: Total steps/units (None for indeterminate progress)
        title: Display title for this progress item
        start_time: When this progress started (Unix timestamp)
        last_updated: When this was last modified (Unix timestamp)
    """
    
    # Core progress attributes (align with Textual ProgressBar)
    progress = reactive(0.0)
    total = reactive[Optional[float]](None)
    title = reactive("")
    start_time = reactive[Optional[float]](None)
    last_updated = reactive[Optional[float]](None)
    
    # Local values (not including children)
    _local_progress = reactive(0.0)
    _local_total = reactive[Optional[float]](None)
    
    def __init__(
        self,
        title: str = "",
        total: Optional[float] = None,
        **kwargs
    ):
        """Initialize a progress node.
        
        Args:
            title: Display title for this progress item
            total: Total number of steps/units (None for indeterminate)
            **kwargs: Additional DOMNode arguments
        """
        super().__init__(**kwargs)
        self.title = title
        self._local_total = total
        self._children: Dict[str, ProgressNode] = {}
        
        if total is not None:
            self.start_time = time()
        
        # Update timestamp and aggregation when local values change
        self.watch("_local_progress", self._on_local_progress_change)
        self.watch("_local_total", self._on_local_total_change)
        
        # Initial aggregation
        self._update_aggregation()
    
    def __getitem__(self, key: str) -> ProgressNode:
        """Get or create a child progress node.
        
        Args:
            key: Identifier for the child node
            
        Returns:
            The child ProgressNode (created if it doesn't exist)
        """
        if key not in self._children:
            child = ProgressNode(title=key)
            self._children[key] = child
            self.mount(child)  # Add to DOM tree
            
            # Watch child for changes to aggregate up
            child.watch("progress", lambda: self._update_aggregation())
            child.watch("total", lambda: self._update_aggregation())
            child.watch("title", lambda: self._update_aggregation())
            
        return self._children[key]
    
    def __setitem__(self, key: str, node: ProgressNode) -> None:
        """Set a child progress node.
        
        Args:
            key: Identifier for the child node
            node: The ProgressNode to set as child
        """
        if key in self._children:
            # Remove old child
            old_child = self._children[key]
            old_child.remove()
            
        self._children[key] = node
        self.mount(node)
        
        # Watch for changes
        node.watch("progress", lambda: self._update_aggregation())
        node.watch("total", lambda: self._update_aggregation())
        node.watch("title", lambda: self._update_aggregation())
    
    def __contains__(self, key: str) -> bool:
        """Check if a child progress node exists.
        
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
        """Get (key, node) pairs for children."""
        return self._children.items()
    
    def values(self):
        """Get child nodes."""
        return self._children.values()
    
    @property
    def percentage(self) -> Optional[float]:
        """Progress percentage (0.0 to 1.0), or None if indeterminate.
        
        Returns:
            Percentage complete, or None if total is unknown
        """
        if self.total is None or self.total == 0:
            return None
        return min(1.0, max(0.0, self.progress / self.total))
    
    @property
    def is_indeterminate(self) -> bool:
        """Check if this progress is indeterminate (unknown total).
        
        Returns:
            True if total is unknown
        """
        return self.total is None
    
    @property
    def local_progress(self) -> float:
        """This node's progress excluding children."""
        return self._local_progress
    
    @local_progress.setter
    def local_progress(self, value: float) -> None:
        """Set this node's local progress."""
        self._local_progress = value
    
    @property
    def local_total(self) -> Optional[float]:
        """This node's total excluding children."""
        return self._local_total
    
    @local_total.setter  
    def local_total(self, value: Optional[float]) -> None:
        """Set this node's local total."""
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
            child for child in self._children.values() 
            if child.last_updated is not None and child.progress > 0
        ]
        
        if active_children:
            most_recent = max(active_children, key=lambda c: c.last_updated or 0)
            return most_recent.current_task  # Recursive
        
        return self.title
    
    def _on_local_progress_change(self, value: float) -> None:
        """Handle local progress changes."""
        self.last_updated = time()
        self._update_aggregation()
    
    def _on_local_total_change(self, value: Optional[float]) -> None:
        """Handle local total changes."""
        if value is not None and self.start_time is None:
            self.start_time = time()
        self._update_aggregation()
    
    def _update_aggregation(self) -> None:
        """Update aggregated progress and total from local values and children."""
        # Calculate aggregated progress
        child_progress = sum(child.progress for child in self._children.values())
        self.progress = self._local_progress + child_progress
        
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
        elif self.progress == 0:
            self.add_class("pending")
        elif self.percentage and self.percentage >= 1.0:
            self.add_class("complete")
        else:
            self.add_class("active")
    
    def advance(self, amount: float = 1.0) -> None:
        """Advance local progress by the given amount.
        
        Args:
            amount: Amount to advance progress by
        """
        self.local_progress += amount
    
    def reset(self) -> None:
        """Reset local progress to zero and clear timing."""
        self._local_progress = 0.0
        self.start_time = None
        self.last_updated = None
    
    def complete(self) -> None:
        """Mark this progress as complete."""
        if self._local_total is not None:
            self._local_progress = self._local_total
        self.add_class("complete")
    
    def fail(self, reason: str = "") -> None:
        """Mark this progress as failed.
        
        Args:
            reason: Optional failure reason
        """
        self.add_class("failed")
        if reason:
            self.set_attribute("data-error", reason)