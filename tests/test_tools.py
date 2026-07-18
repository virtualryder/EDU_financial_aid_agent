"""Unit tests for the financial-aid governed tools — contract + fail-closed behavior. No AWS."""
from toolkit import call


def test_intake_extracts_fields():
    r = call("intake_fafsa", {"application": "SAI: 3000. Cost of attendance: 25000. Enrollment: full-time. GPA 3.2, pace 85%."})
    assert r["fields"]["student_aid_index"] == 3000
    assert r["fields"]["cost_of_attendance"] == 25000


def test_assess_fail_closed_on_unmasked():
    r = call("assess_aid", {"student_aid_index": 3000, "cost_of_attendance": 25000, "deidentified": False})
    assert r["assessed"] is False


def test_assess_eligible_pell():
    r = call("assess_aid", {"student_aid_index": 3000, "cost_of_attendance": 25000, "enrollment_status": "full",
                            "sap_gpa": 3.2, "sap_pace": 85, "deidentified": True})
    assert r["determination"] == "ELIGIBLE"
    assert r["pell_award"] == 4395


def test_verify_documents_hold():
    r = call("verify_documents", {"required_documents": "tax_return,w2", "received_documents": "tax_return"})
    assert r["verification_status"] == "PENDING"
    assert r["hold"] is True


def test_professional_judgment_requires_rationale():
    r = call("professional_judgment", {"circumstance": "job loss", "deidentified": True})
    assert r["prepared"] is False


def test_professional_judgment_prepared():
    r = call("professional_judgment", {"circumstance": "job loss", "proposed_adjustment": "reduce AGI",
                                       "rationale": "Documented 2026 layoff reduced income 40 percent", "deidentified": True})
    assert r["status"] == "PREPARED"
    assert r["requires_senior_approval"] is True


def test_core_finalize_refused():
    assert call("aid_core", {"award_id": "AID-1"})["committed"] is False


def test_core_commit_pj_refused():
    assert call("aid_core", {"pj_id": "PJ-1"})["committed"] is False
