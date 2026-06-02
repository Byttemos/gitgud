from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import OptionList
from textual.widgets.option_list import Option


class TocModal(ModalScreen["str | None"]):
    """On-demand table of contents; dismisses with the chosen section id."""

    BINDINGS = [
        Binding("j,down", "cursor_down", "Down"),
        Binding("k,up", "cursor_up", "Up"),
        Binding("escape,q,t", "cancel", "Close"),
    ]
    DEFAULT_CSS = """
    TocModal { align: center middle; }
    TocModal > OptionList {
        width: 60%;
        max-height: 80%;
        border: round $accent;
        background: $surface;
    }
    """

    def __init__(self, headings: list[tuple[int, str, str]]) -> None:
        super().__init__()
        self._headings = headings

    def compose(self) -> ComposeResult:
        options = [
            Option(f"{'  ' * (level - 1)}{text}", id=section_id)
            for level, text, section_id in self._headings
        ]
        if not options:
            options = [Option("(no headings in description)", disabled=True)]
        yield OptionList(*options)

    def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        self.dismiss(event.option.id)

    def action_cursor_down(self) -> None:
        self.query_one(OptionList).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one(OptionList).action_cursor_up()

    def action_cancel(self) -> None:
        self.dismiss(None)
