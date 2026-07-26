"""Gate-B configuration schema gate. config/institution.config.json is the single source of truth for
institution-controlled values (docs/CONFIGURATION-WORKSHEET.md). This test fails CI if a required key is
missing or unlabeled, or if a declared value has DRIFTED from the code constant it claims to mirror — so
a stale Pell table or an unowned config knob cannot ship silently."""
import json
import os
import sys

import pytest
from toolkit import load  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "config", "institution.config.json")

REQUIRED_KEYS = {
    "pell_max", "pell_min", "sap_gpa_min", "sap_pace_min", "verification_groups",
    "coa_basis", "comms_reading_grade_target", "pj_documentation_checklist", "retention_profile",
}
REQUIRED_FIELDS = {"value", "label", "owner", "where_set", "authoritative_source", "approved_by"}
VALID_OWNERS = {"aid_office", "it_security", "registrar", "privacy_office"}


@pytest.fixture(scope="module")
def cfg():
    with open(CONFIG, encoding="utf-8") as f:
        return json.load(f)


def test_config_file_parses_and_has_award_year(cfg):
    assert isinstance(cfg.get("award_year"), str) and cfg["award_year"], "award_year must be a non-empty string"


def test_all_required_keys_present(cfg):
    missing = REQUIRED_KEYS - set(cfg.get("keys", {}))
    assert not missing, f"required config keys missing: {sorted(missing)}"


def test_every_key_is_fully_labeled(cfg):
    for name, entry in cfg["keys"].items():
        missing = REQUIRED_FIELDS - set(entry)
        assert not missing, f"config key '{name}' missing required fields: {sorted(missing)}"
        assert entry["owner"] in VALID_OWNERS, f"config key '{name}' has invalid owner {entry['owner']!r}"
        assert entry["label"], f"config key '{name}' has an empty label"
        assert entry["where_set"], f"config key '{name}' has an empty where_set"


def test_config_values_match_code_constants(cfg):
    """Drift gate: the numbers declared in config must equal the constants the rules engine actually uses."""
    aid = load("assess_aid")
    keys = cfg["keys"]
    assert keys["pell_max"]["value"] == aid.MAX_PELL
    assert keys["pell_min"]["value"] == aid.MIN_PELL
    assert keys["sap_gpa_min"]["value"] == aid.SAP_GPA_MIN
    assert keys["sap_pace_min"]["value"] == aid.SAP_PACE_MIN
    read = load("readability")
    assert keys["comms_reading_grade_target"]["value"] == read.TARGET_GRADE


def test_award_year_matches_code(cfg):
    aid = load("assess_aid")
    assert cfg["award_year"] == aid.AWARD_YEAR, "config award_year has drifted from assess_aid.AWARD_YEAR"
