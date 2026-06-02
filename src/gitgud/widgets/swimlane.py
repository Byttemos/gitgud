from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Label

from gitgud.models import Column
from gitgud.widgets.task_card import TaskCard


class Swimlane(Vertical):
    """One Kanban column: header + scrollable list of task cards."""

    DEFAULT_CSS = """
    Swimlane {
        height: 1fr;
        width: 45;
        margin: 0 1;
    }
    Swimlane > .lane-title {
        text-style: bold;
        text-align: center;
        width: 1fr;
        padding: 1 0;
        background: $panel;
    }
    Swimlane > VerticalScroll {
        height: 1fr;
        border: round $panel;
        padding: 0 1;
    }
    """

    def __init__(self, column: Column) -> None:
        super().__init__()
        self.column = column

    def compose(self) -> ComposeResult:
        yield Label(self.column.name, classes="lane-title")
        with VerticalScroll():
            for task in self.column.tasks:
                yield TaskCard(task)
