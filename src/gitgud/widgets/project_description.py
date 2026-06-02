import re

from rich.markdown import Markdown as RichMarkdown
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widgets import Static

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def _split_sections(markdown: str) -> list[tuple[tuple[int, str] | None, str]]:
    """Split markdown into (heading | None, section_text) chunks at headings."""
    sections: list[tuple[tuple[int, str] | None, str]] = []
    head: tuple[int, str] | None = None
    lines: list[str] = []
    for line in markdown.split("\n"):
        m = _HEADING.match(line)
        if m:
            if lines or head is not None:
                sections.append((head, "\n".join(lines)))
            head = (len(m.group(1)), m.group(2))
            lines = [line]
        else:
            lines.append(line)
    if lines or head is not None:
        sections.append((head, "\n".join(lines)))
    return sections or [(None, markdown)]


class ProjectDescription(VerticalScroll):
    """Right-hand pane.

    Renders markdown as one Rich-rendered Static per heading-delimited section
    (a handful of widgets instead of one-per-block), so focus switches stay
    snappy even for very long descriptions. The table of contents is on-demand:
    `headings` feeds the TocModal, which calls `jump_to` to scroll to a section.
    """

    can_focus = True
    BINDINGS = [
        Binding("j,down", "scroll_down", "Scroll down"),
        Binding("k,up", "scroll_up", "Scroll up"),
    ]
    DEFAULT_CSS = """
    ProjectDescription { padding: 0 1; }
    """

    def __init__(self, markdown: str = "") -> None:
        super().__init__()
        self._markdown = markdown
        self.headings: list[tuple[int, str, str]] = []  # (level, text, section_id)

    def compose(self) -> ComposeResult:
        yield from self._build(self._markdown)

    def _build(self, markdown: str):
        self.headings = []
        for idx, (head, text) in enumerate(_split_sections(markdown)):
            section_id = f"section-{idx}"
            if head is not None:
                self.headings.append((head[0], head[1], section_id))
            yield Static(RichMarkdown(text), id=section_id)

    async def set_markdown(self, markdown: str) -> None:
        self._markdown = markdown
        await self.remove_children()
        await self.mount_all(list(self._build(markdown)))

    def jump_to(self, section_id: str) -> None:
        for node in self.query(f"#{section_id}"):
            node.scroll_visible(top=True, animate=False)
            break
