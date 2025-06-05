"""
Textual Progress - Universal progress tracking and visualization for Textual applications.

This package provides a flexible progress tracking system with automatic aggregation
and a variety of visualization widgets.
"""

from .dom.progress import ProgressNode
from .widgets import Spinner

__version__ = "0.1.0"
__all__ = ["ProgressNode", "Spinner"]
