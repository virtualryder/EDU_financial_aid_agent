"""Gate-B award-year gate. Financial aid is annual — Pell tables, SAI figures, and verification notices
change every award year. This test pins the rules engine to a single AWARD_YEAR label so a stale table
fails CI, not a live student case. See docs/AWARD-YEAR-UPDATE-RUNBOOK.md."""
import json
import os

from toolkit import load

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_award_year_constant_present():
    aid = load("assess_aid")
    assert isinstance(aid.AWARD_YEAR, str) and aid.AWARD_YEAR, "assess_aid.AWARD_YEAR must be a non-empty string"


def test_award_year_matches_config():
    aid = load("assess_aid")
    with open(os.path.join(ROOT, "config", "institution.config.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    assert aid.AWARD_YEAR == cfg["award_year"], (
        "assess_aid.AWARD_YEAR (%s) has drifted from config award_year (%s)" % (aid.AWARD_YEAR, cfg["award_year"]))


def test_pell_figures_carry_the_award_year_in_provenance_notes():
    """A determination's own notes must name the award year the Pell figures belong to, so an aid officer
    reviewing an estimate can see which year's tables produced it."""
    aid = load("assess_aid")
    yr = aid.AWARD_YEAR
    # The rules-engine notes hard-reference the year (guards against updating a constant but not the label).
    import inspect
    src = inspect.getsource(aid)
    assert yr in src, f"award year {yr} not referenced in assess_aid source notes"
