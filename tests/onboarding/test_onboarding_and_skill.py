"""The first-run path: status says onboarding is needed, init, fill, approve, install the skill, use it."""
import json

import pytest

from conftest import EXAMPLE_PROFILE, ROOT, install_profile, run_cli
from localscene_agent import paths, profile, schedule, skillgen


def _status(capsys):
    run_cli("status")
    return json.loads(capsys.readouterr().out)


def test_new_user_needs_onboarding(home, capsys):
    s = _status(capsys)
    assert s["onboarding_required"] is True and s["users"] == []


def test_install_onboarding_skill_bakes_in_paths(home):
    dest = skillgen.install_onboarding()
    text = (dest / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\nname: local-scene-setup\n")
    assert "{{ENGINE_ROOT}}" not in text and "lsa.py" in text
    assert (dest / "interview-framework.md").exists() and (dest / "profile-generation.md").exists()


def test_full_onboarding_flow(home, capsys):
    run_cli("--user", "maya", "init", "--name", "Maya Okafor")
    assert "Created draft profile" in capsys.readouterr().out
    s = _status(capsys)
    assert s["onboarding_required"] is False
    assert s["users"][0]["profile_status"] == "draft" and s["users"][0]["blocking_gaps"]

    # The skeleton can't be approved or installed: it has blocking gaps.
    with pytest.raises(SystemExit):
        run_cli("--user", "maya", "profile", "approve")
    with pytest.raises(SystemExit):
        skillgen.install("maya")

    # Claude writes the interviewed profile (here: the annotated example), then the user approves.
    prof = profile.load(EXAMPLE_PROFILE)
    profile.save(prof, paths.profile_path("maya"))
    run_cli("--user", "maya", "profile", "validate")
    run_cli("--user", "maya", "profile", "summary")
    assert "What you're into (ranked)" in capsys.readouterr().out
    run_cli("--user", "maya", "profile", "approve")
    assert profile.load(paths.profile_path("maya"))["profile_status"] == "approved"

    dest = skillgen.install("maya")
    assert dest.name == "local-scene"
    skill = (dest / "SKILL.md").read_text(encoding="utf-8")
    assert skill.startswith("---\nname: local-scene\n") and "Maya" in skill
    assert "{{" not in skill
    # paths only: no profile contents baked in
    for leaked in ("Temescal", "Yoshi's", "bottle service", "Lake Merritt"):
        assert leaked not in skill
    refs = {p.name for p in (dest / "references").iterdir()}
    assert set(skillgen.REFERENCE_FILES) | {"safety.md"} <= refs
    assert json.loads((dest / skillgen.MANIFEST).read_text())["user_id"] == "maya"


def test_edit_drops_back_to_draft(home):
    uid = install_profile(EXAMPLE_PROFILE)
    profile.mark_changed(paths.profile_path(uid), "Added a venue")
    p = profile.load(paths.profile_path(uid))
    assert p["profile_status"] == "draft" and p["changelog"][-1]["change"] == "Added a venue"
    with pytest.raises(SystemExit):
        run_cli("--user", uid, "digest")  # digests need an approved profile


def test_second_user_gets_own_skill(home):
    a = install_profile(EXAMPLE_PROFILE)
    skillgen.install(a)
    b = install_profile(ROOT / "examples" / "hypothetical-profiles" / "outdoors-denver.yaml")
    dest = skillgen.install(b)
    assert dest.name == f"local-scene-{b}"
    with pytest.raises(SystemExit):
        skillgen.install(b, skill_name="local-scene")  # owned by the other user


def test_uninstall_only_removes_own_skills(home, tmp_path):
    other = paths.claude_skills_dir() / "someone-elses-skill"
    other.mkdir(parents=True)
    with pytest.raises(SystemExit):
        skillgen.uninstall("someone-elses-skill")
    assert other.exists()


def test_schedule_prompts(home):
    uid = install_profile(EXAMPLE_PROFILE)
    local = schedule.render("weekend-digest", uid, "local")
    assert "lsa.py" in local and "digest --events-file" in local and "must NOT buy tickets" in local
    assert "Temescal" not in local  # local prompts read the live profile instead of copying it
    cloud = schedule.render("weekend-digest", uid, "cloud")
    assert "lsa.py" not in cloud and "Temescal" in cloud and "Live jazz" in cloud
    assert cloud.index("1. Live jazz") < cloud.index("2. Punk")
    assert "Closed, skip: Old Warehouse Bar" in cloud
    assert "PushNotification" in cloud  # push is configured in the example
    assert "Friday 17:00 to Sunday 22:00" in cloud  # the profile's own weekend, not a hardcoded one
    for task in schedule.TASKS:
        assert schedule.render(task, uid, "local") and schedule.render(task, uid, "cloud")
