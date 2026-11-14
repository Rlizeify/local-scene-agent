"""Every shipped profile validates, and the validator catches the mistakes onboarding is likely to make."""
import copy

import pytest

from conftest import EXAMPLE_PROFILE, EXAMPLES
from localscene_agent import profile

ALL = sorted(EXAMPLES.glob("*.yaml")) + [EXAMPLE_PROFILE]


@pytest.mark.parametrize("path", ALL, ids=lambda p: p.stem)
def test_shipped_profiles_validate(path):
    assert profile.validate(profile.load(path)) == []


@pytest.fixture
def good():
    return profile.load(EXAMPLE_PROFILE)


@pytest.mark.parametrize("mutate,expect", [
    (lambda p: p["permissions"]["require_approval"].remove("buy_tickets"), "require_approval"),
    (lambda p: p["interests"].append(dict(p["interests"][0])), "duplicate ids"),
    (lambda p: p["venues"][0].update(interests=["nope"]), "unknown interest"),
    (lambda p: p["venues"][0].update(area="Mars"), "isn't one of home.areas"),
    (lambda p: p["recurring"].append({"name": "x", "rule": "monthly"}), "recurring"),
    (lambda p: p["evaluation"]["criteria"].append({"id": "vibes", "weight": 1}), "custom criterion"),
    (lambda p: p.update(profile_status="approved", approved_at=None), "approved_at"),
    (lambda p: p.update(profile_status="approved", approved_at="x", gaps=[{"field": "f", "note": "n", "blocking": True}]), "blocking gaps"),
    (lambda p: p["user"].update(id="Has Spaces"), "user/id"),
    (lambda p: p.update(surprise=1), "Additional properties"),
])
def test_validator_catches(good, mutate, expect):
    p = copy.deepcopy(good)
    mutate(p)
    errors = profile.validate(p)
    assert errors and any(expect in e for e in errors), errors


def test_skeleton_is_valid_draft_with_blocking_gaps():
    s = profile.new_skeleton("newbie", "New Person")
    assert profile.validate(s) == []
    assert {g["field"] for g in s["gaps"] if g["blocking"]} == {"interests", "home", "sources"}


def test_bad_yaml_reports_line(tmp_path):
    f = tmp_path / "p.yaml"
    f.write_text("user: {id: x\n  name: [", encoding="utf-8")
    with pytest.raises(ValueError, match="line"):
        profile.load(f)
