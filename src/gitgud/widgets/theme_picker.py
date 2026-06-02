from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import OptionList
from textual.widgets.option_list import Option


class ThemePicker(ModalScreen["str | None"]):
    """Pick a theme with live preview; dismisses with the chosen name or None.

    Previews each theme as the cursor moves; commits on select, reverts to the
    original theme on cancel.
    """

    BINDINGS = [
        Binding("j,down", "cursor_down", "Down"),
        Binding("k,up", "cursor_up", "Up"),
        Binding("escape,q", "cancel", "Cancel"),
    ]
    DEFAULT_CSS = """
    ThemePicker { align: center middle; }
    ThemePicker > OptionList {
        width: 50%;
        max-height: 80%;
        border: round $accent;
        background: $surface;
    }
    """

    def __init__(self, themes: list[str], current: str) -> None:
        super().__init__()
        self._themes = themes
        self._original = current

    def compose(self) -> ComposeResult:
        yield OptionList(*(Option(name, id=name) for name in self._themes))

    def on_mount(self) -> None:
        option_list = self.query_one(OptionList)
        if self._original in self._themes:
            option_list.highlighted = self._themes.index(self._original)

    def on_option_list_option_highlighted(
        self, event: OptionList.OptionHighlighted
    ) -> None:
        if event.option.id:  # live preview
            self.app.theme = event.option.id

    def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        self.dismiss(event.option.id)

    def action_cursor_down(self) -> None:
        self.query_one(OptionList).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one(OptionList).action_cursor_up()

    def action_cancel(self) -> None:
        self.app.theme = self._original  # revert the preview
        self.dismiss(None)
