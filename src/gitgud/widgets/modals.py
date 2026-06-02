from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, TextArea


class ConfirmModal(ModalScreen[bool]):
    """Yes/no confirmation; dismisses with True (y) or False (n/escape)."""

    BINDINGS = [
        Binding("y", "confirm(True)", "Yes"),
        Binding("n,escape", "confirm(False)", "No"),
    ]
    DEFAULT_CSS = """
    ConfirmModal { align: center middle; }
    ConfirmModal > Vertical {
        width: auto;
        height: auto;
        max-width: 60%;
        padding: 1 2;
        border: round $warning;
        background: $surface;
    }
    ConfirmModal .hint { color: $text-muted; padding-top: 1; }
    """

    def __init__(self, prompt: str) -> None:
        super().__init__()
        self.prompt = prompt

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self.prompt)
            yield Label("[b]y[/b]es  /  [b]n[/b]o", classes="hint")

    def action_confirm(self, ok: bool) -> None:
        self.dismiss(ok)


class AddCardModal(ModalScreen["tuple[str, str] | None"]):
    """Form for a new draft card; dismisses with (title, body) or None."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "submit", "Save"),
    ]
    DEFAULT_CSS = """
    AddCardModal { align: center middle; }
    AddCardModal > Vertical {
        width: 70%;
        height: auto;
        padding: 1 2;
        border: round $accent;
        background: $surface;
    }
    AddCardModal .modal-title { text-style: bold; padding-bottom: 1; }
    AddCardModal Input { margin-bottom: 1; }
    AddCardModal TextArea { height: 8; margin-bottom: 1; }
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("New draft card", classes="modal-title")
            yield Input(placeholder="Title", id="title")
            yield TextArea(id="body")
            yield Button("Add (ctrl+s)", variant="primary", id="add")

    def on_mount(self) -> None:
        self.query_one("#title", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.action_submit()

    def action_submit(self) -> None:
        title = self.query_one("#title", Input).value.strip()
        if title:  # title is required
            self.dismiss((title, self.query_one("#body", TextArea).text))

    def action_cancel(self) -> None:
        self.dismiss(None)
