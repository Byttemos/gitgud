from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import OptionList
from textual.widgets.option_list import Option


class ProjectPickerModal(ModalScreen["int | None"]):
    """Pick a project; dismisses with the chosen project number (or None)."""

    BINDINGS = [
        Binding("j,down", "cursor_down", "Down"),
        Binding("k,up", "cursor_up", "Up"),
        Binding("escape,q", "cancel", "Cancel"),
    ]
    DEFAULT_CSS = """
    ProjectPickerModal { align: center middle; }
    ProjectPickerModal > OptionList {
        width: 60%;
        max-height: 80%;
        border: round $accent;
        background: $surface;
    }
    """

    def __init__(self, projects: list[tuple[int, str]]) -> None:
        super().__init__()
        self._projects = projects

    def compose(self) -> ComposeResult:
        options = [
            Option(f"#{number}  {title}", id=str(number))
            for number, title in self._projects
        ]
        if not options:
            options = [Option("(no projects found for this owner)", disabled=True)]
        yield OptionList(*options)

    def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        self.dismiss(int(event.option.id) if event.option.id else None)

    def action_cursor_down(self) -> None:
        self.query_one(OptionList).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one(OptionList).action_cursor_up()

    def action_cancel(self) -> None:
        self.dismiss(None)
