# GitGud

A [Textual](https://textual.textualize.io/) TUI for working with **GitHub Projects (v2)** from your terminal — a keyboard-driven kanban board with swimlanes, card editing, drag-free reordering, and theming.

## Requirements

- Python ≥ 3.11
- The [GitHub CLI](https://cli.github.com/) (`gh`), authenticated with the `read:project` and `project` scopes:

  ```sh
  gh auth login
  gh auth refresh -s read:project -s project
  ```

GitGud shells out to `gh` and reuses its auth session — there are no tokens to configure.

## Install

Install as an isolated tool straight from the repository:

```sh
# with pipx
pipx install git+https://github.com/Byttemos/gitgud.git

# or with uv
uv tool install git+https://github.com/Byttemos/gitgud.git
```

## Usage

```sh
gitgud                      # uses configured owner + default project
gitgud <owner>              # pick a project interactively for that owner/org
gitgud <owner> <number>     # open a specific project board
```

On first run GitGud seeds the owner from your authenticated `gh` user. Press `p` to pick a project, `T` to change theme, `?`/`a`/`space` etc. for the rest — bindings are shown in the footer.

Config lives at `$XDG_CONFIG_HOME/gitgud/config.json` (default `~/.config/gitgud/config.json`).

## Development

```sh
python -m venv .venv && source .venv/bin/activate
pip install -e .
gitgud            # or: python -m gitgud
```
