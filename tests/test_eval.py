"""Eval / regression harness for the Title IV financial-aid rules engine (assess_aid).

Golden cases pin the Pell/SAP DETERMINATION so a rules change fails CI. Rules basis: authoritative
2026-27 Pell max 7395 / min 740; SAP GPA >= 2.0 and pace >= 67%.

P0-3: assess_aid only issues an authoritative determination on a COA that carries a signature minted by
lookup_coa, so every golden case supplies a genuine signed coa_source token. The unsigned/fabricated
path is covered in test_provenance_gate.
"""
import json
import os

os.environ.setdefault("PROVENANCE_SECRET", "p0-unit-provenance-secret")

import pytest  # noqa: E402
from toolkit import call, CONTROLS  # noqa: E402
import sys  # noqa: E402
sys.path.insert(0, str(CONTROLS))
import provenance  # noqa: E402

SOURCE = "US Dept of Education — College Scorecard"


def _coa_source(unitid="170976", school="Test University", coa=25000):
    fields = {"unitid": str(unitid), "school": school, "cost_of_attendance": coa}
    tok = provenance.sign(SOURCE, fields)
    return json.dumps({"source": SOURCE, "school": school, "unitid": unitid,
                       "authoritative": tok["authoritative"], "sig": tok["sig"], "alg": tok["alg"]})


COA = _coa_source(coa=25000)

GOLDEN = [
    ("eligible_full_time",
     {"student_aid_index": 3000, "cost_of_attendance": 25000, "enrollment_status": "full",
      "sap_gpa": 3.2, "sap_pace": 85, "coa_source": COA, "deidentified": True},
     {"determination": "ELIGIBLE", "eligible": True, "pell_award": 4395, "sap_status": "SATISFACTORY"}),
    ("half_time_proration",
     {"student_aid_index": 0, "cost_of_attendance": 25000, "enrollment_status": "half",
      "sap_gpa": 3.0, "sap_pace": 80, "coa_source": COA, "deidentified": True},
     {"determination": "ELIGIBLE", "pell_award": 3698}),  # 7395 * 0.5, rounded
    ("sap_not_met_needs_review",
     {"student_aid_index": 1000, "cost_of_attendance": 25000, "enrollment_status": "full",
      "sap_gpa": 1.0, "sap_pace": 40, "coa_source": COA, "deidentified": True},
     {"determination": "NEEDS_REVIEW", "sap_status": "NOT_SATISFACTORY"}),
    ("verification_hold",
     {"student_aid_index": 2000, "cost_of_attendance": 25000, "enrollment_status": "full",
      "sap_gpa": 3.0, "sap_pace": 80, "selected_for_verification": True, "coa_source": COA, "deidentified": True},
     {"determination": "NEEDS_REVIEW", "aid_track": "VERIFICATION_HOLD"}),
]

NEGATIVE = [
    ("assess_unmasked", "assess_aid",
     {"student_aid_index": 3000, "cost_of_attendance": 25000, "deidentified": False},
     lambda r: r["assessed"] is False),
    ("assess_unsigned_coa", "assess_aid",
     {"student_aid_index": 3000, "cost_of_attendance": 25000, "enrollment_status": "full",
      "sap_gpa": 3.2, "sap_pace": 85, "deidentified": True},
     lambda r: r["determination"] == "NEEDS_REVIEW" and r["authoritative"] is False),
    ("pj_unmasked", "professional_judgment",
     {"circumstance": "job loss", "rationale": "documented layoff cut income", "deidentified": False},
     lambda r: r["prepared"] is False),
]


@pytest.mark.parametrize("label,inp,expected", GOLDEN, ids=[g[0] for g in GOLDEN])
def test_golden_determination(label, inp, expected):
    r = call("assess_aid", inp)
    for k, v in expected.items():
        assert r.get(k) == v, f"{label}: {k} expected {v!r}, got {r.get(k)!r}"


@pytest.mark.parametrize("label,tool,inp,check", NEGATIVE, ids=[n[0] for n in NEGATIVE])
def test_negative_fail_closed(label, tool, inp, check):
    assert check(call(tool, inp)), f"{label}: fail-closed guard did not hold"


def test_pell_figures_authoritative():
    mod = __import__("toolkit").load("assess_aid")
    assert mod.MAX_PELL == 7395 and mod.MIN_PELL == 740, "Pell constants drifted from 2026-27"
