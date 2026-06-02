from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Label

from gitgud.models import Task


class TaskCard(Vertical):
    DEFAULT_CSS = """
    TaskCard {
        height: auto;
        width: 1fr;
        border: round $panel-lighten-2;
        padding: 0 1;
        margin-bottom: 1;
    }
    TaskCard:focus {
        border: round $accent;
        background: $boost;
    }
    TaskCard .task-title { text-style: bold; }
    TaskCard .task-meta  { color: $text-muted; }
    """

    can_focus = True

    def __init__(self, task: Task) -> None:
        super().__init__()
        self.task_data = task  # NB: `task` is a reserved property on Textual widgets

    def compose(self) -> ComposeResult:
        yield Label(self.task_data.title, classes="task-title")
        yield Label(f"#{self.task_data.number}", classes="task-meta")
