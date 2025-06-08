"""
Spinners tab content for the demo application.
"""

from textual.app import ComposeResult
from textual.widgets import Static, Button, Label, OptionList
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive

from textual_progress import Spinner


class SpinnersTab(Vertical):
    """Tab containing spinner demonstrations and controls."""

    DEFAULT_CSS = """
    SpinnersTab {
        padding: 1;
        overflow-y: auto;
    }

    #rich-spinner-row, #textual-spinner-row {
        height: 3;
        align: left middle;
    }

    #rich-spinner {
        height: 3;
    }

    .subheading {
        text-style: bold;
    }

    #speed-controls {
        height: 1;
    }

    #speed-down, #speed-up {
        max-width: 3;
        max-height: 1;
        width: 3;
        height: 1;
        padding: 0;
        border: none;
        margin-left: 1;
    }

    #speed-display {
        width: auto;
        height: 1;
    }

    #textual-label {
        margin-left: 2;
        content-align: left middle;
        color: $text-muted;
    }

    #spinner-list {
        width: auto;
        margin-right: 2;
        height: 3;
        border: none;
        min-width: 25;
    }

    Spinner {
        height: 3;
        margin: 0 1;
    }
    """

    # Track current speed for spinners
    current_speed = reactive(0.08)

    def compose(self) -> ComposeResult:
        """Create the spinners tab content."""
        # Rich Spinner section
        yield Static()
        yield Label("Rich", classes="subheading")
        with Horizontal(id="rich-spinner-row"):
            # Get available Rich spinners for the list
            from rich.spinner import SPINNERS

            # Get all available Rich spinners
            spinner_names = list(SPINNERS.keys())
            from textual.widgets.option_list import Option

            yield OptionList(*[Option(name, id=name) for name in spinner_names], id="spinner-list")
            yield Spinner(id="rich-spinner")

        # Speed control
        yield Static()
        with Horizontal(id="speed-controls"):
            yield Static("Speed: 0.080/sec", id="speed-display")
            yield Button("-", id="speed-down")
            yield Button("+", id="speed-up")

        # Multi-line Spinner section
        yield Static()
        yield Label("Multi-line", classes="subheading")
        with Horizontal(id="textual-spinner-row"):
            yield Spinner(id="textual-spinner")
            yield Static("[Built-in]", id="textual-label")

    def on_mount(self) -> None:
        """Set up initial spinner states."""
        # Set initial task for spinners if available
        app = self.app
        if hasattr(app, "task") and app.task:
            self.update_spinners_task(app.task)

    def update_spinners_task(self, task):
        """Update all spinners with new task."""
        try:
            rich_spinner = self.query_one("#rich-spinner", Spinner)
            rich_spinner.task = task
        except Exception:
            pass

        try:
            textual_spinner = self.query_one("#textual-spinner", Spinner)
            textual_spinner.task = task
        except Exception:
            pass

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        """Handle spinner option highlighting (navigation)."""
        if event.option_list.id == "spinner-list":
            spinner_name = str(event.option.id)

            # Update the Rich spinner
            rich_spinner = self.query_one("#rich-spinner", Spinner)
            try:
                rich_spinner.set_rich_spinner(spinner_name)
                # Log to app if available
                if hasattr(self.app, "log_info"):
                    self.app.log_info(f"Rich spinner changed to {spinner_name} with {len(rich_spinner.frames)} frames")
            except ValueError as e:
                if hasattr(self.app, "log_error"):
                    self.app.log_error(f"Failed to set Rich spinner: {e}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle speed control button presses."""
        button_id = event.button.id

        if button_id == "speed-up":
            # Decrease time (speed up) by 0.01s, min 0.01s
            self.current_speed = max(0.01, self.current_speed - 0.01)
        elif button_id == "speed-down":
            # Increase time (slow down) by 0.01s, max 0.5s
            self.current_speed = min(0.5, self.current_speed + 0.01)

    def watch_current_speed(self, speed: float) -> None:
        """Update spinner speeds and display when current_speed changes."""
        # Update both spinners
        try:
            rich_spinner = self.query_one("#rich-spinner", Spinner)
            rich_spinner.speed = speed
        except Exception:
            pass

        try:
            textual_spinner = self.query_one("#textual-spinner", Spinner)
            textual_spinner.speed = speed
        except Exception:
            pass

        # Update display
        try:
            speed_display = self.query_one("#speed-display", Static)
            speed_display.update(f"Speed: {speed:.3f}/sec")
        except:
            pass

        # Log to app if available
        if hasattr(self.app, "log_info"):
            self.app.log_info(f"Speed changed to: {speed:.3f}s")
