"""
Textual Progress - Universal progress tracking and visualization for Textual applications.

This package provides a flexible progress tracking system with automatic aggregation
and a variety of visualization widgets.
"""

from .task import Task, Tasks
from .widgets import Spinner, TaskInfo, ProgressBar

__version__ = "0.1.0"
__all__ = ["Task", "Tasks", "Spinner", "TaskInfo", "ProgressBar"]
