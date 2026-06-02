"""Tiny JSON config at $XDG_CONFIG_HOME/gitgud/config.json.

Holds the default owner, the default project number, and the preferred layout.
CLI args override the config; the project picker writes back the chosen default.
"""

import json
import os
from pathlib import Path

_DEFAULTS: dict = {
    "owner": None,
    "default_project": None,
    "layout": "split",
    "theme": "cyberpunk",
}


def config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "gitgud" / "config.json"


def load_config() -> dict:
    path = config_path()
    data: dict = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
    return {**_DEFAULTS, **data}


def save_config(config: dict) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def update_config(**changes) -> dict:
    """Load, apply changes, persist, and return the merged config."""
    config = load_config()
    config.update(changes)
    save_config(config)
    return config
