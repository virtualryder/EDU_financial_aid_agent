import json
import re

# intake_fafsa — extract the decision-relevant, NON-PII fields from a raw FAFSA/ISIR or aid application
# (free text or JSON): Student Aid Index (SAI), cost of attendance, enrollment status, SAP GPA and pace,
# dependency. Deterministic and fail-soft. PII (name, SSN, address, DOB) is NOT needed downstream for the
# determination and is redacted separately by mask_pii before drafting/audit.

_ENROLL = {
    "full": "full", "full-time": "full", "fulltime": "full", "ft": "full",
    "three": "three_quarter", "three-quarter": "three_quarter", "3/4": "three_quarter",
    "half": "half", "half-time": "half", "1/2": "half",
    "less": "less_than_half", "less-than-half": "less_than_half",
}


def _coerce(e):
    e = e or {}
    if isinstance(e, str):
        try:
            return json.loads(e)
        except Exception:
            return {"application": e}
    return e


def _num(s):
    m = re.search(r"[-+]?\d[\d,]*(?:\.\d+)?", str(s))
    return float(m.group(0).replace(",", "")) if m else None


def handler(event, context):
    e = _coerce(event)
    text = e.get("application", "")
    if not isinstance(text, str):
        text = json.dumps(text)
    low = text.lower()

    sai = e.get("student_aid_index")
    if sai is None:
        m = re.search(r"(?:student\s+aid\s+index|sai|efc)[^0-9\-]{0,12}(-?[\d,]+(?:\.\d+)?)", low)
        sai = _num(m.group(1)) if m else None
    coa = e.get("cost_of_attendance")
    if coa is None:
        m = re.search(r"(?:cost\s+of\s+attendance|coa)[^0-9$]{0,12}\$?([\d,]+(?:\.\d+)?)", low)
        coa = _num(m.group(1)) if m else None
    enroll = e.get("enrollment_status")
    if enroll is None:
        enroll = None
        for k, v in _ENROLL.items():
            if k in low:
                enroll = v
                break
    gpa = e.get("sap_gpa")
    if gpa is None:
        m = re.search(r"(?:gpa)[^0-9]{0,8}([0-4](?:\.\d+)?)", low)
        gpa = _num(m.group(1)) if m else None
    pace = e.get("sap_pace")
    if pace is None:
        m = re.search(r"(?:pace|completion(?:\s+rate)?)[^0-9]{0,8}([\d,]+(?:\.\d+)?)\s*%?", low)
        pace = _num(m.group(1)) if m else None
    dependency = e.get("dependency")
    if dependency is None:
        if "independent" in low:
            dependency = "independent"
        elif "dependent" in low:
            dependency = "dependent"

    fields = {"student_aid_index": sai, "cost_of_attendance": coa, "enrollment_status": enroll,
              "sap_gpa": gpa, "sap_pace": pace, "dependency": dependency}
    missing = [k for k in ("student_aid_index", "cost_of_attendance") if fields.get(k) is None]
    return {"structured": True, "fields": fields, "missing_required": missing,
            "note": "non-PII decision fields; PII/education-record identifiers are redacted separately by mask_pii"}
