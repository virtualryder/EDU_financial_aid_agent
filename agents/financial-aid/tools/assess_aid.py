import json

# assess_aid — deterministic Title IV federal student-aid determination.
# NO licensed data and NO model call: a rules engine over PUBLIC Title IV formulas — the Pell Grant
# scheduled-award calculation (Cost of Attendance minus Student Aid Index, prorated by enrollment
# intensity), the Satisfactory Academic Progress (SAP) test, and the verification track. Runs AFTER
# mask_pii (fail-closed: refuses un-masked input, mirroring the mask-before-model control). The specific
# figures are a per-year CONFIGURATION item (customer engagement) — these are widely used federal
# defaults and are labeled illustrative.
#
# Pell (illustrative, 2024-25): maximum scheduled award ~$7,395; minimum ~$740 (~10% of max). Award =
# min(COA, MAX_PELL) - SAI, floored at 0, prorated by enrollment intensity; awards below the minimum
# round to 0 unless SAI qualifies for the minimum. SAP: cumulative GPA >= 2.0 AND completion pace >= 67%.
# Confirm current figures for the intended award year and institution.

MAX_PELL = 7395        # annual maximum scheduled Pell award (illustrative)
MIN_PELL = 740         # annual minimum award (~10% of max) (illustrative)
SAP_GPA_MIN = 2.0      # cumulative GPA floor for Satisfactory Academic Progress
SAP_PACE_MIN = 67.0    # completion-pace floor (percent) for SAP
ENROLL = {"full": 1.0, "three_quarter": 0.75, "half": 0.5, "less_than_half": 0.25}


def _coerce(e):
    e = e or {}
    if isinstance(e, str):
        try:
            e = json.loads(e)
        except Exception:
            e = {"_raw": e}
    return e


def _num(v, default=None):
    try:
        return float(v)
    except Exception:
        return default


def handler(event, context):
    e = _coerce(event)
    # Fail-closed: refuse to operate on non-de-identified input. Cedar's mask_before_assess forbid blocks
    # this at the gateway; the body refuses too (defense in depth).
    if e.get("deidentified") is not True:
        return {"assessed": False, "error": "refused: case is not de-identified (deidentified must be true)",
                "deidentified_input": e.get("deidentified")}

    sai = _num(e.get("student_aid_index"))
    coa = _num(e.get("cost_of_attendance"))
    enroll = str(e.get("enrollment_status") or "full").lower()
    intensity = ENROLL.get(enroll, 1.0)
    gpa = _num(e.get("sap_gpa"))
    pace = _num(e.get("sap_pace"))
    selected = bool(e.get("selected_for_verification"))
    coa_source = e.get("coa_source")  # provenance from lookup_coa (College Scorecard), echoed for the audit

    if sai is None or coa is None:
        return {"assessed": True, "determination": "NEEDS_REVIEW", "eligible": None,
                "reason": "insufficient data (need student_aid_index and cost_of_attendance)",
                "deidentified_input": True, "assessed_by": "rules:TitleIV/Pell+SAP(illustrative)"}

    # ---- Pell scheduled award ----
    base = min(coa, MAX_PELL) - sai
    scheduled = base if base > 0 else 0.0
    pell = round(scheduled * intensity)
    if 0 < pell < MIN_PELL:
        pell = MIN_PELL if sai <= (MAX_PELL - MIN_PELL) else 0

    # ---- Satisfactory Academic Progress ----
    if gpa is None or pace is None:
        sap_status = "UNKNOWN"
    elif gpa >= SAP_GPA_MIN and pace >= SAP_PACE_MIN:
        sap_status = "SATISFACTORY"
    else:
        sap_status = "NOT_SATISFACTORY"

    # ---- verification track (the processing-clock analog) ----
    aid_track = "VERIFICATION_HOLD" if selected else "STANDARD"

    # ---- overall determination ----
    if sap_status == "NOT_SATISFACTORY":
        determination, eligible, reason = "NEEDS_REVIEW", None, ("Title IV aid held: SAP not met (GPA %s / pace %s%%); SAP appeal or academic plan required" % (gpa, pace))
    elif selected:
        determination, eligible, reason = "NEEDS_REVIEW", None, ("selected for verification; award held pending documentation (estimated Pell %d)" % pell)
    elif pell > 0:
        determination, eligible, reason = "ELIGIBLE", True, ("estimated Pell %d = min(COA, %d) - SAI %.0f, prorated for %s enrollment" % (pell, MAX_PELL, sai, enroll))
    else:
        determination, eligible, reason = "INELIGIBLE", False, ("SAI %.0f yields no Pell at this COA; may qualify for other Title IV aid (loans/work-study) on review" % sai)

    # Pell maximum/minimum are the AUTHORITATIVE 2026-27 figures (FSA Dear Colleague Letter, 2026-01-30:
    # max $7,395, min $740). The cost of attendance should come from lookup_coa (College Scorecard) rather
    # than an illustrative value; coa_source records where it came from for the audit trail.
    notes = ["Pell max/min are authoritative 2026-27 figures (FSA DCL 2026-01-30); SAP thresholds are configurable per institution"]
    if not coa_source:
        notes.append("cost_of_attendance provenance not supplied — use lookup_coa for an authoritative COA")
    if determination == "ELIGIBLE":
        notes.append("Pell estimate only; loan/work-study packaging and final COA remain for aid-officer review")

    # Short proof fields FIRST (the MCP client truncates long results ~200 chars); detail LAST.
    return {
        "assessed": True,
        "determination": determination,        # ELIGIBLE | INELIGIBLE | NEEDS_REVIEW
        "eligible": eligible,
        "aid_track": aid_track,                 # STANDARD | VERIFICATION_HOLD
        "sap_status": sap_status,               # SATISFACTORY | NOT_SATISFACTORY | UNKNOWN
        "pell_award": pell,
        "enrollment_status": enroll,
        "cost_of_attendance": int(coa),
        "coa_provenance": coa_source or "not supplied",
        "deidentified_input": True,
        "assessed_by": "rules:TitleIV/Pell(2026-27 authoritative)+SAP",
        "pell_max_source": "FSA DCL 2026-01-30 (max 7395 / min 740)",
        "reason": reason,
        "notes": notes,
    }
