"""Where the engine, schemas and per-user data live.

Data home resolution order:
1. the LSA_HOME environment variable
2. ~/.local-scene-agent

Each user gets <home>/users/<user_id>/ containing profile.yaml, log.csv (everything
suggested, planned or attended), history.jsonl, digests/, documents/ and backups/.
"""
from __future__ import annotations

import os
from pathlib import Path


def _engine_root() -> Path:
    """The repository checkout (schemas/, skills/, workflows/ live there, not inside the package).

    Works when run from a clone (`python lsa.py`) or after `pip install -e .`. A plain
    `pip install .` copies only the package, so point LSA_ENGINE_ROOT at the clone instead.
    """
    env = os.environ.get("LSA_ENGINE_ROOT")
    candidate = Path(env).expanduser() if env else Path(__file__).resolve().parents[2]
    if not (candidate / "schemas" / "user-profile.schema.json").is_file():
        raise SystemExit(
            f"Can't find the local-scene-agent repository files at {candidate}. Run from a clone "
            "(python lsa.py ...), install with `pip install -e <clone>`, or set LSA_ENGINE_ROOT to the clone."
        )
    return candidate


ENGINE_ROOT = _engine_root()
SCHEMA_DIR = ENGINE_ROOT / "schemas"
SKILLS_DIR = ENGINE_ROOT / "skills"
WORKFLOWS_DIR = ENGINE_ROOT / "workflows"


def data_home() -> Path:
    env = os.environ.get("LSA_HOME")
    return Path(env).expanduser() if env else Path.home() / ".local-scene-agent"


def user_dir(user_id: str) -> Path:
    return data_home() / "users" / user_id


def profile_path(user_id: str) -> Path:
    return user_dir(user_id) / "profile.yaml"


def log_path(user_id: str) -> Path:
    return user_dir(user_id) / "log.csv"


def history_path(user_id: str) -> Path:
    return user_dir(user_id) / "history.jsonl"


def claude_skills_dir() -> Path:
    """Personal Claude skills directory (overridable for tests)."""
    env = os.environ.get("LSA_SKILLS_DIR")
    return Path(env).expanduser() if env else Path.home() / ".claude" / "skills"


def list_users() -> list[str]:
    root = data_home() / "users"
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if (p / "profile.yaml").is_file())


def resolve_user(user_id: str | None) -> str:
    """Pick the user: explicit id, else LSA_USER, else the only existing user."""
    if user_id:
        return user_id
    env = os.environ.get("LSA_USER")
    if env:
        return env
    users = list_users()
    if len(users) == 1:
        return users[0]
    if not users:
        raise SystemExit("No user profile found. Run onboarding first (lsa --user <id> init).")
    raise SystemExit(f"Several users exist ({', '.join(users)}). Pass --user <id>.")
