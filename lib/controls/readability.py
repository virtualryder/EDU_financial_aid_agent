import re

# readability.py — plain-language + required-element check for student-facing draft communications
# (Gate-B accessibility control, docs/ACCESSIBILITY.md). Financial-aid notices must be understandable:
# the target is a reading grade <= 8 and the four elements a student needs to act — what the outcome is,
# what they must do next, by when, and who to contact / how to appeal.
#
# This is DETERMINISTIC and DEPENDENCY-FREE (no model call, no packages): a Flesch-Kincaid grade-level
# estimate plus keyword-anchored element detection. It is ADVISORY, not a gate — the draft is always
# human-reviewed before it reaches a student — so a hard sentence or a missing keyword flags the draft
# for the officer's attention, it never blocks or rewrites. [REDACTED:...] masking placeholders are
# stripped before scoring so masking never inflates the reading grade.

_REDACTION = re.compile(r"\[REDACTED:[^\]]*\]", re.IGNORECASE)
_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]*")
_SENT = re.compile(r"[.!?]+")

TARGET_GRADE = 8.0

# Element -> the signals that show the notice covers it. Deliberately broad so ordinary aid-notice
# language matches; the point is to catch a draft that OMITS an element, not to grade phrasing.
_ELEMENTS = {
    "outcome": ("eligible", "ineligible", "estimated", "estimate", "award", "determination",
                "pell", "needs review", "not eligible"),
    "next_step": ("submit", "provide", "complete", "upload", "verify", "verification",
                  "required document", "you must", "please", "next step", "action"),
    "deadline": ("deadline", "by ", "days", "due", "no later than", "within", "before"),
    "contact_appeal": ("contact", "financial aid office", "appeal", "request a review",
                       "right to", "questions", "reach out", "call ", "email"),
}


def _syllables(word):
    w = word.lower()
    vowels = "aeiouy"
    count, prev = 0, False
    for ch in w:
        is_v = ch in vowels
        if is_v and not prev:
            count += 1
        prev = is_v
    if w.endswith("e") and count > 1:
        count -= 1
    return max(count, 1)


def grade_level(text):
    """Flesch-Kincaid grade-level estimate. Returns a float; 0.0 for empty/no-sentence text."""
    clean = _REDACTION.sub(" ", text or "")
    words = _WORD.findall(clean)
    if not words:
        return 0.0
    sentences = max(len([s for s in _SENT.split(clean) if s.strip()]), 1)
    syll = sum(_syllables(w) for w in words)
    w, s = len(words), sentences
    # FK grade = 0.39*(words/sentences) + 11.8*(syllables/words) - 15.59
    return round(0.39 * (w / s) + 11.8 * (syll / w) - 15.59, 1)


def required_elements(text):
    """Which of the four student-action elements the notice appears to cover."""
    low = (text or "").lower()
    return {name: any(sig in low for sig in sigs) for name, sigs in _ELEMENTS.items()}


def assess(text, target_grade=TARGET_GRADE):
    """Advisory plain-language assessment of a drafted notice. Never raises; never blocks."""
    grade = grade_level(text)
    elements = required_elements(text)
    missing = sorted([k for k, present in elements.items() if not present])
    return {
        "reading_grade": grade,
        "target_grade": target_grade,
        "grade_ok": grade <= target_grade,
        "elements_present": elements,
        "missing_elements": missing,
        "plain_language_ok": (grade <= target_grade and not missing),
    }
