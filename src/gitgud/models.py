from dataclasses import dataclass, field


@dataclass
class Task:
    number: int | None
    title: str
    body: str = ""
    status: str | None = None
    item_id: str | None = None  # ProjectV2Item id, needed for write-back mutations


@dataclass
class Column:
    name: str
    option_id: str | None = None
    tasks: list[Task] = field(default_factory=list)


@dataclass
class Board:
    project_id: str
    status_field_id: str | None
    columns: list[Column]
    markdown: str
    title: str = ""
    url: str = ""
