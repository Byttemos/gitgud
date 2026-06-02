import asyncio
import sys

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, HorizontalScroll
from textual.screen import Screen
from textual.widgets import Footer, Label, Static

from gitgud.config import config_path, load_config, update_config
from gitgud.github import (
    GitHubError,
    add_draft_issue,
    current_login,
    fetch_board,
    list_projects,
    reorder_item,
    set_item_status,
)
from gitgud.models import Column
from gitgud.theme import THEMES
from gitgud.widgets.card_modal import CardModal
from gitgud.widgets.modals import AddCardModal, ConfirmModal
from gitgud.widgets.project_description import ProjectDescription
from gitgud.widgets.project_picker import ProjectPickerModal
from gitgud.widgets.swimlane import Swimlane
from gitgud.widgets.task_card import TaskCard
from gitgud.widgets.theme_picker import ThemePicker
from gitgud.widgets.toc_modal import TocModal


class Header(Static):
    DEFAULT_CSS = """
        Header {
            height: 3;
            dock: top;
            content-align: center middle;
            text-style: bold;
            background: $primary;
            color: $background;
        }
        """


class Body(Horizontal):
    DEFAULT_CSS = """
        Body {
            layout: horizontal;
        }
        """


class ProjectContainer(Container):
    DEFAULT_CSS = """
        ProjectContainer {
            width: 1fr;
            height: 1fr;
            border: solid grey;
        }
        ProjectContainer:focus-within {
            border: solid $accent;
        }
        """


class TaskContainer(Horizontal):
    DEFAULT_CSS = """
        TaskContainer {
            width: 1fr;
            height: 1fr;
            border: solid grey;
        }
        TaskContainer:focus-within {
            border: solid $accent;
        }
        """


class MainScreen(Screen):
    BINDINGS = [
        Binding("h,left", "focus_lane(-1)", "Prev column"),
        Binding("j,down", "focus_card('next')", "Next card"),
        Binding("k,up", "focus_card('previous')", "Prev card"),
        Binding("l,right", "focus_lane(1)", "Next column"),
        Binding("a", "add_card", "Add card"),
        Binding("space", "open_card", "Open card", key_display="󱁐"),
        Binding("shift+left,H", "move_lane(-1)", "Move ←", key_display="󰘶+h"),
        Binding("shift+down,J", "reorder(1)", "Move down", key_display="󰘶+j"),
        Binding("shift+up,K", "reorder(-1)", "Move up", key_display="󰘶+k"),
        Binding("shift+right,L", "move_lane(1)", "Move →", key_display="󰘶+l"),
        Binding("tab", "toggle_pane", "Switch pane", key_display="󰌒"),
        Binding("shift+tab", "toggle_pane", show=False),
        Binding("t", "open_toc", "Outline"),
        Binding("p", "pick_project", "Projects"),
        Binding("c", "toggle_layout", "Toggle compact"),
        Binding("T", "pick_theme", "Themes", key_display="󰘶+t"),
        Binding("o", "open_in_browser", ""),
        Binding("r", "refresh_board", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, owner: str, number: int | None) -> None:
        super().__init__()
        self.owner = owner
        self.number: int | None = number
        self.project_id: str = ""
        self.status_field_id: str | None = None
        self.columns: list[Column] = []
        self.tabbed: bool = load_config().get("layout") == "tabbed"
        self.active_pane: str = "board"  # which pane shows in tabbed layout
        self.project_url: str = ""

    def compose(self) -> ComposeResult:
        yield Header("GitGud", id="Header")
        yield Footer(id="Footer")
        with Body(id="Body"):
            with TaskContainer(id="TaskContainer"):
                yield HorizontalScroll(id="lanes")
            with ProjectContainer():
                yield ProjectDescription()

    def on_mount(self) -> None:
        self._apply_layout()
        if self.number is None:
            self.action_pick_project()  # no default project yet — let the user choose
        else:
            self.load_board()

    @work(exclusive=True)
    async def load_board(self, focus_item_id: str | None = None) -> None:
        number = self.number
        if number is None:
            return
        lanes = self.query_one("#lanes", HorizontalScroll)
        await lanes.remove_children()
        await lanes.mount(Label("Loading project..."))
        try:
            board = await asyncio.to_thread(fetch_board, self.owner, number)
        except GitHubError as exc:
            await lanes.remove_children()
            await lanes.mount(Label(f"Failed to load: {exc}"))
            return
        self.project_id = board.project_id
        self.status_field_id = board.status_field_id
        self.columns = board.columns
        self.project_url = board.url
        await lanes.remove_children()
        await lanes.mount_all(Swimlane(column) for column in board.columns)
        await self.query_one(ProjectDescription).set_markdown(board.markdown)
        self.query_one(Header).update(board.title or "GitGud")
        cards = list(self.query(TaskCard))
        target = next((c for c in cards if c.task_data.item_id == focus_item_id), None)
        if target is not None:
            target.focus()
        elif cards:
            cards[0].focus()

    def action_focus_card(self, direction: str) -> None:
        if direction == "next":
            self.focus_next("TaskCard")
        else:
            self.focus_previous("TaskCard")

    def action_focus_lane(self, direction: int) -> None:
        lanes = list(self.query(Swimlane))
        if not lanes:
            return
        current = 0
        if self.focused is not None:
            for node in self.focused.ancestors_with_self:
                if isinstance(node, Swimlane):
                    current = lanes.index(node)
                    break
        target = lanes[(current + direction) % len(lanes)]
        cards = list(target.query(TaskCard))
        if cards:
            cards[0].focus()

    def action_toggle_pane(self) -> None:
        # Cycle focus between board and description. In tabbed layout this also
        # swaps which pane is shown. No manual refresh_bindings() — Textual does
        # it on focus change, and it's costly on a large description.
        to_desc = not isinstance(self.focused, ProjectDescription)
        if self.tabbed:
            self.active_pane = "desc" if to_desc else "board"
            self._apply_layout()
        if to_desc:
            self.query_one(ProjectDescription).focus()
        else:
            cards = list(self.query(TaskCard))
            (cards[0] if cards else self).focus()

    def _apply_layout(self) -> None:
        task = self.query_one(TaskContainer)
        desc = self.query_one(ProjectContainer)
        if self.tabbed:
            task.display = self.active_pane == "board"
            desc.display = self.active_pane == "desc"
        else:
            task.display = True
            desc.display = True

    def action_toggle_layout(self) -> None:
        self.tabbed = not self.tabbed
        if self.tabbed:  # entering tabbed: show whichever pane has focus
            self.active_pane = (
                "desc" if isinstance(self.focused, ProjectDescription) else "board"
            )
        update_config(layout="tabbed" if self.tabbed else "split")
        self._apply_layout()

    def action_open_in_browser(self) -> None:
        if self.project_url:
            self.app.open_url(self.project_url)
        else:
            self.notify(
                "No project URL yet — load a project first.", severity="warning"
            )

    def action_pick_theme(self) -> None:
        names = sorted(self.app.available_themes)

        def picked(name: str | None) -> None:
            if name is not None:
                update_config(theme=name)

        self.app.push_screen(ThemePicker(names, self.app.theme), picked)

    def action_open_card(self) -> None:
        if isinstance(self.focused, TaskCard):
            self.app.push_screen(CardModal(self.focused.task_data))

    def action_open_toc(self) -> None:
        desc = self.query_one(ProjectDescription)

        def jump(section_id: str | None) -> None:
            if section_id is not None:
                desc.focus()
                desc.jump_to(section_id)

        self.app.push_screen(TocModal(desc.headings), jump)

    def action_pick_project(self) -> None:
        self._pick_project()

    @work
    async def _pick_project(self) -> None:
        try:
            projects = await asyncio.to_thread(list_projects, self.owner)
        except GitHubError as exc:
            self.notify(f"Couldn't list projects: {exc}", severity="error")
            return
        number = await self.app.push_screen_wait(ProjectPickerModal(projects))
        if number is None:
            return
        self.number = number
        update_config(default_project=number)
        self.load_board()

    def _focused_swimlane(self) -> Swimlane | None:
        if self.focused is None:
            return None
        for node in self.focused.ancestors_with_self:
            if isinstance(node, Swimlane):
                return node
        return None

    def action_move_lane(self, direction: int) -> None:
        self._move_lane(direction)

    @work
    async def _move_lane(self, direction: int) -> None:
        card = self.focused
        lane = self._focused_swimlane()
        if not isinstance(card, TaskCard) or lane is None:
            return
        target = list(self.query(Swimlane)).index(lane) + direction
        if not (0 <= target < len(self.columns)):
            return  # boundary lane
        column = self.columns[target]
        item_id = card.task_data.item_id
        field_id = self.status_field_id
        option_id = column.option_id
        if item_id is None or field_id is None or option_id is None:
            return  # "No Status" lane or draft without ids
        if not await self.app.push_screen_wait(
            ConfirmModal(f"Move '{card.task_data.title}' to {column.name}?")
        ):
            return
        await asyncio.to_thread(
            set_item_status, self.project_id, item_id, field_id, option_id
        )
        self.load_board(item_id)

    def action_reorder(self, direction: int) -> None:
        self._reorder(direction)

    @work
    async def _reorder(self, direction: int) -> None:
        card = self.focused
        lane = self._focused_swimlane()
        if not isinstance(card, TaskCard) or lane is None:
            return
        item_id = card.task_data.item_id
        if item_id is None:
            return
        siblings = list(lane.query(TaskCard))
        i = siblings.index(card)
        new_i = i + direction
        if not (0 <= new_i < len(siblings)):
            return  # already at the lane's top/bottom
        if direction > 0:
            after_id = siblings[i + 1].task_data.item_id
        else:
            after_id = siblings[i - 2].task_data.item_id if i - 2 >= 0 else None
        await asyncio.to_thread(reorder_item, self.project_id, item_id, after_id)
        self.load_board(item_id)

    def action_add_card(self) -> None:
        self._add_card()

    @work
    async def _add_card(self) -> None:
        result = await self.app.push_screen_wait(AddCardModal())
        if result is None:
            return
        title, body = result
        new_id = await asyncio.to_thread(add_draft_issue, self.project_id, title, body)
        self.load_board(new_id)

    def action_refresh_board(self) -> None:
        self.load_board()

    def action_quit(self) -> None:
        self.app.exit()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        on_card = isinstance(self.focused, TaskCard)
        if action in {
            "focus_card",
            "focus_lane",
            "open_card",
            "move_lane",
            "reorder",
        }:
            return True if on_card else False
        return True


class LayoutApp(App):
    def __init__(self, owner: str, number: int | None) -> None:
        super().__init__()
        self.owner = owner
        self.number = number

    def on_mount(self) -> None:
        for theme in THEMES:
            self.register_theme(theme)
        requested = load_config().get("theme") or "cyberpunk"
        self.theme = requested if requested in self.available_themes else "cyberpunk"
        self.push_screen(MainScreen(self.owner, self.number))


def _resolve_owner_number() -> tuple[str | None, int | None]:
    cfg = load_config()
    owner = sys.argv[1] if len(sys.argv) > 1 else cfg.get("owner")
    if not owner:  # first run: seed the owner from the authenticated gh user
        owner = current_login()
        if owner:
            update_config(owner=owner)
    number = int(sys.argv[2]) if len(sys.argv) > 2 else cfg.get("default_project")
    return owner, number


def main() -> None:
    """Console entry point for the ``gitgud`` command."""
    resolved_owner, resolved_number = _resolve_owner_number()
    if not resolved_owner:
        print(
            f"No owner configured. Set 'owner' in {config_path()} or pass it as "
            "the first argument: gitgud <owner> [project_number]"
        )
        raise SystemExit(1)
    LayoutApp(resolved_owner, resolved_number).run()


if __name__ == "__main__":
    main()
