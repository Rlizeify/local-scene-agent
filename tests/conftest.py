import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

EXAMPLES = ROOT / "examples" / "hypothetical-profiles"
EXAMPLE_PROFILE = ROOT / "configuration" / "example-profile.yaml"
FIXTURES = ROOT / "tests" / "fixtures"


@pytest.fixture
def home(tmp_path, monkeypatch):
    """Isolated data home + skills dir for every test (never touches the real ~/.claude)."""
    data = tmp_path / "lsa-home"
    skills = tmp_path / "claude-skills"
    monkeypatch.setenv("LSA_HOME", str(data))
    monkeypatch.setenv("LSA_SKILLS_DIR", str(skills))
    monkeypatch.delenv("LSA_USER", raising=False)
    return data


@pytest.fixture
def fixture_events():
    return json.loads((FIXTURES / "events.json").read_text(encoding="utf-8"))


def install_profile(src: Path, approve: bool = True) -> str:
    """Copy a profile into the current LSA_HOME; returns the user id."""
    from localscene_agent import paths, profile
    prof = profile.load(src)
    uid = prof["user"]["id"]
    if approve and prof["profile_status"] != "approved":
        prof["profile_status"] = "approved"
        prof["approved_at"] = "2026-01-10T10:00:00"
    dest = paths.profile_path(uid)
    profile.save(prof, dest)
    return uid


def install_example(name: str) -> str:
    return install_profile(EXAMPLES / f"{name}.yaml")


def run_cli(*argv):
    from localscene_agent.cli import main
    main(list(argv))
