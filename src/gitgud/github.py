"""Data layer: fetch a GitHub Project (v2) by shelling out to the `gh` CLI.

Relies on the user's `gh auth` session (needs the `read:project` scope).
Statuses are dynamic: the board's columns are the options of the project's
`Status` single-select field, in the order defined on GitHub.
"""

import json
import subprocess

from gitgud.models import Board, Column, Task

NO_STATUS = "No Status"

# Probe both owner roots: a project may be user- or org-owned. The shared
# fragment works because both User and Organization implement ProjectV2Owner.
# Exactly one root resolves; the other returns null + a (harmless) NOT_FOUND.
_PROJECT_QUERY = """
query($owner: String!, $number: Int!) {
  user(login: $owner)         { ...proj }
  organization(login: $owner) { ...proj }
}
fragment proj on ProjectV2Owner {
  projectV2(number: $number) {
    id
    url
    title
    shortDescription
    readme
    field(name: "Status") {
      ... on ProjectV2SingleSelectField { id options { id name } }
    }
    items(first: 100) {
      nodes {
        id
        content {
          ... on Issue       { number title body }
          ... on PullRequest { number title body }
          ... on DraftIssue  { title body }
        }
        fieldValueByName(name: "Status") {
          ... on ProjectV2ItemFieldSingleSelectValue { name optionId }
        }
      }
    }
  }
}
"""


class GitHubError(RuntimeError):
    """Raised when the gh CLI call fails or the project can't be found."""


def current_login() -> str | None:
    """The authenticated gh user's login, or None if unavailable."""
    proc = subprocess.run(
        ["gh", "api", "user", "--jq", ".login"], capture_output=True, text=True
    )
    login = proc.stdout.strip()
    return login if proc.returncode == 0 and login else None


def _run_graphql(owner: str, number: int) -> dict:
    """Call `gh api graphql` and return the parsed JSON envelope.

    The query probes both owner roots, so gh always exits non-zero with a
    partial NOT_FOUND error for the root that didn't match. That's expected:
    as long as stdout holds valid JSON we use it (fetch_board decides whether
    a project actually resolved). A genuine failure leaves stdout unparseable.
    """
    proc = subprocess.run(
        [
            "gh", "api", "graphql",
            "-f", f"owner={owner}",
            "-F", f"number={number}",      # -F sends a typed (Int) variable
            "-f", f"query={_PROJECT_QUERY}",
        ],
        capture_output=True,
        text=True,
    )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise GitHubError(proc.stderr.strip() or "gh api graphql failed") from None


def build_columns(options: list[dict], tasks: list[Task]) -> list[Column]:
    """One column per Status option (GitHub order); unstatused items go last."""
    columns = [Column(name=o["name"], option_id=o["id"]) for o in options]
    by_name = {c.name: c for c in columns}
    backlog = Column(name=NO_STATUS)
    for task in tasks:
        column = by_name.get(task.status) if task.status else backlog
        (column or backlog).tasks.append(task)
    if backlog.tasks:
        columns.append(backlog)
    return columns


def _parse_items(nodes: list[dict]) -> list[Task]:
    tasks = []
    for node in nodes:
        content = node.get("content") or {}
        if not content:
            continue  # items the token can't resolve (e.g. private cross-refs)
        status = node.get("fieldValueByName") or {}
        tasks.append(
            Task(
                number=content.get("number"),       # None for draft issues
                title=content.get("title") or "(untitled)",
                body=content.get("body") or "",
                status=status.get("name"),           # None when unset
                item_id=node.get("id"),              # ProjectV2Item id
            )
        )
    return tasks


def fetch_board(owner: str, number: int) -> Board:
    """Fetch a project (user- or org-owned) as a Board."""
    data = _run_graphql(owner, number).get("data") or {}
    owner_node = data.get("user") or data.get("organization")
    project = owner_node.get("projectV2") if owner_node else None
    if project is None:
        raise GitHubError(
            f"No project #{number} found for '{owner}' "
            "(checked both user and organization owners)."
        )

    field = project.get("field") or {}
    tasks = _parse_items(project["items"]["nodes"])
    columns = build_columns(field.get("options", []), tasks)

    markdown = (
        project.get("readme")
        or project.get("shortDescription")
        or "_No description set._"
    )
    return Board(
        project_id=project["id"],
        status_field_id=field.get("id"),
        columns=columns,
        markdown=markdown,
        title=project.get("title") or "",
        url=project.get("url") or "",
    )


_PROJECTS_QUERY = """
query($owner: String!) {
  user(login: $owner)         { projectsV2(first: 50) { nodes { number title } } }
  organization(login: $owner) { projectsV2(first: 50) { nodes { number title } } }
}
"""


def list_projects(owner: str) -> list[tuple[int, str]]:
    """List (number, title) for an owner's projects (user or org)."""
    proc = subprocess.run(
        ["gh", "api", "graphql", "-f", f"owner={owner}", "-f", f"query={_PROJECTS_QUERY}"],
        capture_output=True,
        text=True,
    )
    try:
        data = (json.loads(proc.stdout).get("data")) or {}
    except json.JSONDecodeError:
        raise GitHubError(proc.stderr.strip() or "gh api graphql failed") from None
    node = data.get("user") or data.get("organization")
    nodes = ((node or {}).get("projectsV2") or {}).get("nodes") or []
    return [(n["number"], n["title"]) for n in nodes]


# --- Write-back mutations (require the `project` scope) -----------------------


def _mutate(query: str, **variables: str) -> dict:
    """Run a GraphQL mutation via gh; raise GitHubError on failure."""
    args = ["gh", "api", "graphql", "-f", f"query={query}"]
    for key, value in variables.items():
        args += ["-f", f"{key}={value}"]
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        raise GitHubError(proc.stderr.strip() or "gh api graphql mutation failed")
    return json.loads(proc.stdout)


def set_item_status(
    project_id: str, item_id: str, field_id: str, option_id: str
) -> None:
    """Move an item to a different Status (single-select) option."""
    _mutate(
        """mutation($p: ID!, $i: ID!, $f: ID!, $o: String!) {
          updateProjectV2ItemFieldValue(input: {
            projectId: $p, itemId: $i, fieldId: $f,
            value: { singleSelectOptionId: $o }
          }) { projectV2Item { id } }
        }""",
        p=project_id, i=item_id, f=field_id, o=option_id,
    )


def reorder_item(project_id: str, item_id: str, after_id: str | None = None) -> None:
    """Reposition an item; after_id=None moves it to the top of the project."""
    variables = {"p": project_id, "i": item_id}
    if after_id is not None:
        variables["a"] = after_id
    _mutate(
        """mutation($p: ID!, $i: ID!, $a: ID) {
          updateProjectV2ItemPosition(input: {
            projectId: $p, itemId: $i, afterId: $a
          }) { clientMutationId }
        }""",
        **variables,
    )


def add_draft_issue(project_id: str, title: str, body: str = "") -> str:
    """Create a draft issue in the project; return the new ProjectV2Item id."""
    data = _mutate(
        """mutation($p: ID!, $t: String!, $b: String) {
          addProjectV2DraftIssue(input: { projectId: $p, title: $t, body: $b }) {
            projectItem { id }
          }
        }""",
        p=project_id, t=title, b=body,
    )
    return data["data"]["addProjectV2DraftIssue"]["projectItem"]["id"]


if __name__ == "__main__":
    import sys

    owner_arg, number_arg = sys.argv[1], int(sys.argv[2])
    board = fetch_board(owner_arg, number_arg)
    for col in board.columns:
        print(f"[{col.name}] ({len(col.tasks)})")
        for task in col.tasks:
            print(f"   #{task.number} {task.title}")
    print("\n--- description ---")
    print(board.markdown)
