from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Label, Markdown

from gitgud.models import Task


class CardModal(ModalScreen[None]):
    BINDINGS = [
        Binding("j,down", "scroll(3)", "Down"),
        Binding("k,up", "scroll(-3)", "Up"),
        Binding("space,escape,q", "close", "Close"),
    ]
    DEFAULT_CSS = """
    CardModal { align: center middle; }
    CardModal > VerticalScroll {
        width: 80%; height: 80%;
        border: round $accent; background: $surface; padding: 1 2;
    }
    CardModal .modal-title { text-style: bold; padding-bottom: 1; }
    """

    def __init__(self, task: Task) -> None:
        super().__init__()
        self.task_data = task

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            heading = self.task_data.title
            if self.task_data.number is not None:
                heading = f"#{self.task_data.number}  {heading}"
            yield Label(heading, classes="modal-title")
            yield Markdown(self.task_data.body or "_No description._")

    def action_scroll(self, dy: int) -> None:
        self.query_one(VerticalScroll).scroll_relative(y=dy, animate=False)

    def action_close(self) -> None:
        self.dismiss()
