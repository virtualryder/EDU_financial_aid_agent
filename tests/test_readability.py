"""Gate-B accessibility gate for the plain-language check on student-facing drafts (docs/ACCESSIBILITY.md).
The check is ADVISORY at runtime (never blocks a human-reviewed draft) but its logic is unit-tested here so
the reading-grade estimate and the required-element detection are trustworthy."""
from toolkit import load

read = load("readability")


def test_plain_notice_scores_low_grade_and_passes():
    text = (
        "You are eligible for an estimated Pell award of $3,200. "
        "To finish, please submit your tax form by March 1. "
        "If you have questions, contact the financial aid office. You may appeal this if it seems wrong."
    )
    r = read.assess(text)
    assert r["grade_ok"], f"expected plain text to meet the grade target, got {r['reading_grade']}"
    assert not r["missing_elements"], f"unexpected missing elements: {r['missing_elements']}"
    assert r["plain_language_ok"]


def test_dense_text_flags_high_grade():
    text = (
        "Notwithstanding the aforementioned determination, the institutional adjudication of your "
        "eligibility necessitates supplementary documentation substantiating the extraordinary "
        "circumstances precipitating the reconsideration of your previously calculated contribution."
    )
    r = read.assess(text)
    assert r["reading_grade"] > read.TARGET_GRADE, f"expected a high grade, got {r['reading_grade']}"
    assert not r["grade_ok"]


def test_missing_elements_are_detected():
    text = "You are eligible for an estimated Pell award."   # no next step, deadline, or contact/appeal
    r = read.assess(text)
    assert "next_step" in r["missing_elements"]
    assert "deadline" in r["missing_elements"]
    assert "contact_appeal" in r["missing_elements"]
    assert not r["plain_language_ok"]


def test_redaction_placeholders_do_not_inflate_grade():
    a = read.grade_level("Please submit your form by June 1. Contact the office with questions.")
    b = read.grade_level("[REDACTED:NAME], please submit your form by June 1. Contact the office with questions.")
    assert abs(a - b) < 1.5, "masking placeholders should not materially change the reading grade"


def test_assess_never_raises_on_empty():
    r = read.assess("")
    assert r["reading_grade"] == 0.0
    assert "outcome" in r["missing_elements"]
