"""Generate and install a personalized Claude skill from the generic template.

The generated SKILL.md contains *paths only* (engine, profile, data dir, python),
never profile contents. The skill reads the live profile at runtime, so profile
edits take effect without regenerating the skill.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import shutil
import sys
from pathlib import Path

from . import __version__, paths, profile as profile_mod

TEMPLATE = paths.SKILLS_DIR / "local-scene" / "SKILL.md.tmpl"
ONBOARDING_SRC = paths.ENGINE_ROOT / "onboarding"
REFERENCE_FILES = ["research.md", "evaluation.md", "digest.md", "tonight.md", "plan-ahead.md",
                   "field-notes.md", "venue-upkeep.md", "scheduled-runs.md", "profile-updates.md"]
MANIFEST = "lsa-skill.json"


def default_skill_name(user_id: str) -> str:
    others = [u for u in paths.list_users() if u != user_id]
    return "local-scene" if not others else f"local-scene-{user_id}"


def _posix(p: Path) -> str:
    return str(p).replace("\\", "/")


def render(user_id: str, skill_name: str) -> str:
    prof_path = paths.profile_path(user_id)
    prof = profile_mod.load(prof_path)
    values = {
        "SKILL_NAME": skill_name,
        "USER_ID": user_id,
        "DISPLAY_NAME": prof["user"].get("preferred_name") or prof["user"]["name"].split()[0],
        "ENGINE_ROOT": _posix(paths.ENGINE_ROOT),
        "PROFILE_PATH": _posix(prof_path),
        "DATA_DIR": _posix(paths.user_dir(user_id)),
        "PYTHON": _posix(Path(sys.executable)),
        "LSA_HOME": _posix(paths.data_home()),
        "VERSION": __version__,
    }
    text = TEMPLATE.read_text(encoding="utf-8")
    text = re.sub(r"\{\{(\w+)\}\}", lambda m: values[m.group(1)], text)
    leftover = re.findall(r"\{\{\w+\}\}", text)
    if leftover:
        raise ValueError(f"Unfilled template placeholders: {leftover}")
    return text


def install(user_id: str, skill_name: str | None = None, force: bool = False, skills_dir: Path | None = None) -> Path:
    prof_path = paths.profile_path(user_id)
    if not prof_path.exists():
        raise SystemExit(f"No profile for '{user_id}'. Run onboarding first.")
    prof = profile_mod.load(prof_path)
    errors = profile_mod.validate(prof)
    if errors:
        raise SystemExit("Profile has errors:\n  " + "\n  ".join(errors))
    if prof["profile_status"] != "approved":
        raise SystemExit("Profile isn't approved yet. Review the summary with the user, then run `lsa profile approve`.")

    name = skill_name or default_skill_name(user_id)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", name):
        raise SystemExit("Skill names must be lowercase letters, digits and hyphens.")
    dest = (skills_dir or paths.claude_skills_dir()) / name
    manifest_path = dest / MANIFEST
    if dest.exists():
        owner = json.loads(manifest_path.read_text()).get("user_id") if manifest_path.exists() else None
        if owner != user_id and not force:
            raise SystemExit(f"{dest} already exists and isn't this user's local-scene skill. Use --name or --force.")

    text = render(user_id, name)
    refs = dest / "references"
    refs.mkdir(parents=True, exist_ok=True)
    (dest / "SKILL.md").write_text(text, encoding="utf-8")
    for fname in REFERENCE_FILES:
        shutil.copy2(paths.WORKFLOWS_DIR / fname, refs / fname)
    shutil.copy2(paths.ENGINE_ROOT / "docs" / "safety.md", refs / "safety.md")
    manifest_path.write_text(json.dumps({
        "user_id": user_id, "skill_name": name, "profile_path": str(prof_path),
        "engine_root": str(paths.ENGINE_ROOT), "engine_version": __version__,
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
    }, indent=2), encoding="utf-8")
    return dest


def uninstall(skill_name: str, skills_dir: Path | None = None) -> bool:
    dest = (skills_dir or paths.claude_skills_dir()) / skill_name
    if not (dest / MANIFEST).exists():
        raise SystemExit(f"{dest} wasn't created by local-scene-agent; not removing it.")
    shutil.rmtree(dest)
    return True


def install_onboarding(skills_dir: Path | None = None, name: str = "local-scene-setup") -> Path:
    """Install the onboarding skill, with the engine path baked in so it can call the CLI."""
    dest = (skills_dir or paths.claude_skills_dir()) / name
    dest.mkdir(parents=True, exist_ok=True)
    values = {"ENGINE_ROOT": _posix(paths.ENGINE_ROOT), "PYTHON": _posix(Path(sys.executable)),
              "LSA_HOME": _posix(paths.data_home()), "VERSION": __version__}
    for src in ONBOARDING_SRC.glob("*.md"):
        text = src.read_text(encoding="utf-8")
        text = re.sub(r"\{\{(\w+)\}\}", lambda m: values.get(m.group(1), m.group(0)), text)
        (dest / src.name).write_text(text, encoding="utf-8")
    (dest / MANIFEST).write_text(json.dumps({"user_id": None, "skill_name": name, "kind": "onboarding",
                                             "engine_root": str(paths.ENGINE_ROOT)}, indent=2), encoding="utf-8")
    return dest


def installed_skills(skills_dir: Path | None = None) -> list[dict]:
    root = skills_dir or paths.claude_skills_dir()
    out = []
    if root.is_dir():
        for m in root.glob(f"*/{MANIFEST}"):
            try:
                out.append(json.loads(m.read_text()))
            except ValueError:
                pass
    return out
