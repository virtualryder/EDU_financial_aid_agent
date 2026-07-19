"""P0-3 — authoritative-source provenance gate (financial-aid). assess_aid issues an authoritative Title
IV determination ONLY on a Cost of Attendance that carries a signature minted by lookup_coa (which alone
reached College Scorecard and holds the shared secret); otherwise NEEDS_REVIEW, never a fabricated
answer. Pure logic; the College Scorecard call in lookup_coa is monkeypatched."""
import importlib.util
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTROLS = ROOT / "lib" / "controls"
TOOLS = ROOT / "agents" / "financial-aid" / "tools"
for _p in (str(CONTROLS), str(TOOLS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

SECRET = os.environ.setdefault("PROVENANCE_SECRET", "p0-unit-provenance-secret")

import provenance  # noqa: E402

SOURCE = "US Dept of Education — College Scorecard"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _assess():
    return _load("assess_aid_ut", TOOLS / "assess_aid.py")


def _lookup():
    return _load("lookup_coa_ut", TOOLS / "lookup_coa.py")


def _signed_coa_source(unitid="170976", school="Test University", coa=25000):
    fields = {"unitid": str(unitid), "school": school, "cost_of_attendance": coa}
    tok = provenance.sign(SOURCE, fields)
    return json.dumps({"source": SOURCE, "school": school, "unitid": unitid,
                       "authoritative": tok["authoritative"], "sig": tok["sig"], "alg": tok["alg"]})


def test_assess_needs_review_without_provenance():
    r = _assess().handler({"student_aid_index": 3000, "cost_of_attendance": 25000, "enrollment_status": "full",
                           "sap_gpa": 3.2, "sap_pace": 85, "deidentified": True}, None)
    assert r["determination"] == "NEEDS_REVIEW" and r["authoritative"] is False


def test_assess_needs_review_with_fabricated_source_string():
    r = _assess().handler({"student_aid_index": 3000, "cost_of_attendance": 25000, "enrollment_status": "full",
                           "sap_gpa": 3.2, "sap_pace": 85,
                           "coa_source": "US Dept of Education — College Scorecard", "deidentified": True}, None)
    assert r["determination"] == "NEEDS_REVIEW" and r["authoritative"] is False


def test_assess_needs_review_when_coa_tampered_after_signing():
    src = _signed_coa_source(coa=25000)          # signed for 25000
    r = _assess().handler({"student_aid_index": 3000, "cost_of_attendance": 9000, "enrollment_status": "full",
                           "sap_gpa": 3.2, "sap_pace": 85, "coa_source": src, "deidentified": True}, None)
    assert r["determination"] == "NEEDS_REVIEW" and r["authoritative"] is False


def test_assess_authoritative_with_signed_source():
    src = _signed_coa_source(coa=25000)
    r = _assess().handler({"student_aid_index": 3000, "cost_of_attendance": 25000, "enrollment_status": "full",
                           "sap_gpa": 3.2, "sap_pace": 85, "coa_source": src, "deidentified": True}, None)
    assert r["determination"] == "ELIGIBLE"
    assert r["authoritative"] is True and r["provenance_verified"] is True and r["pell_award"] == 4395


def test_lookup_signs_and_assess_verifies(monkeypatch):
    lk = _lookup()
    fixture = {"results": [{"id": 170976, "school.name": "University of Michigan-Ann Arbor",
                            "school.state": "MI", "latest.cost.attendance.academic_year": 32000}]}
    monkeypatch.setattr(lk, "_query", lambda params: fixture)
    out = lk.handler({"school": "University of Michigan-Ann Arbor"}, None)
    assert out["found"] is True and out["authoritative"] is True and isinstance(out["coa_source"], str)

    r = _assess().handler({"student_aid_index": 3000, "cost_of_attendance": out["cost_of_attendance"],
                           "enrollment_status": "full", "sap_gpa": 3.2, "sap_pace": 85,
                           "coa_source": out["coa_source"], "deidentified": True}, None)
    assert r["provenance_verified"] is True and r["authoritative"] is True and r["determination"] == "ELIGIBLE"


def test_lookup_source_down_yields_review(monkeypatch):
    lk = _lookup()
    def _boom(params):
        raise TimeoutError("scorecard down")
    monkeypatch.setattr(lk, "_query", _boom)
    out = lk.handler({"school": "Anywhere U"}, None)
    assert out["found"] is False and not out.get("authoritative")
    r = _assess().handler({"student_aid_index": 3000, "cost_of_attendance": 25000, "deidentified": True}, None)
    assert r["determination"] == "NEEDS_REVIEW" and r["authoritative"] is False
