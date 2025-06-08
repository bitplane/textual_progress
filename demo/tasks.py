"""
Task definitions and factory functions for the demo application.
"""

import asyncio
import logging
from textual_progress import Task


def create_manual_task(title: str) -> Task:
    """Create a manual task that needs user control."""
    task = Task(title, total=5)  # 5 steps
    logging.info(f"Created: {title}")
    return task


def create_forever_task(title: str) -> Task:
    """Create a forever task that runs indefinitely for spinners."""
    task = Task(title, total=None)  # Indeterminate
    task.add_class("active")
    logging.info(f"Created: {title} (active)")
    return task


def create_percent_task(title: str, total: int = 100) -> Task:
    """Create a percentage task that can be started."""
    task = Task(title, total=total)
    logging.info(f"Created: {title} (0/{total})")
    return task


def create_none_task() -> None:
    """Create no task - returns None to clear selection."""
    logging.info("Cleared selection")
    return None


def start_percent_task(task: Task, app_instance) -> None:
    """Start a percentage task with automatic progress updates."""
    task.add_class("active")
    logging.info(f"Starting percent task: {task.title}")

    async def update_progress():
        total = int(task.total or 100)
        for i in range(total + 1):
            if not task or task.has_class("failed"):
                logging.info(f"Percent task stopped: {task.title}")
                break
            task.local_completed = i
            if i % 10 == 0:  # Log every 10%
                logging.info(f"Percent task progress: {task.title} {i}/{total}")
            await asyncio.sleep(0.1)

        if task and not task.has_class("failed"):
            task.complete()
            logging.info(f"Percent task completed: {task.title}")

    asyncio.create_task(update_progress())


# Task registry: name -> (factory_function, args, start_function)
TASK_REGISTRY = {
    "None": (create_none_task, (), None),
    "Manual": (create_manual_task, ("Manual Task",), None),
    "Forever": (create_forever_task, ("Forever Task",), None),
    "Percent": (create_percent_task, ("Percent Task", 100), start_percent_task),
}
