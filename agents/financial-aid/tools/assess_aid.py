import json

import provenance  # shared verifier (bundled beside this handler at deploy; on sys.path in tests)

# assess_aid — deterministic Title IV federal student-aid determination.
# NO licensed data and NO model call: a rules engine over PUBLIC Title IV formulas — the Pell Grant
# scheduled-award calculation (Cost of Attendance minus Student Aid Index, prorated by enrollment
# intensity), the Satisfactory Academic Progress (SAP) test, and the verification track. Runs AFTER
# mask_pii (fail-closed: refuses un-masked input, mirroring the mask-before-model control).
#
# P0-3 — NEVER fabricate authority. The Cost of Attendance and its provenance arrive in the call body, so
# this tool cannot take a caller's word that the COA is College Scorecard's. It requires a SIGNED
# provenance token minted by lookup_coa (which alone reached the API and holds the per-deploy secret) and
# VERIFIES that signature against the COA it is about to use. Missing, unsigned, forged, or a COA that was
# altered after the lookup -> the COA is UNVERIFIED: determination NEEDS_REVIEW with authoritative:false,
# no aid determination made on an unverified COA. A hand-typed "College Scorecard" string buys no
# authority. (SAI comes from the FAFSA/intake and is the applicant's own datum, not an external source.)
#
# Pell (authoritative 2026-27): maximum scheduled award $7,395; minimum $740 (~10% of max) (FSA DCL
# 2026-01-30). Award = min(COA, MAX_PELL) - SAI, floored at 0, prorated by enrollment intensity; awards
# below the minimum round to 0 unless SAI qualifies for the minimum. SAP: cumulative GPA >= 2.0 AND
# completion pace >= 67%.

MAX_PELL = 7395        # annual maximum scheduled Pell award (authoritative 2026-27)
MIN_PELL = 740         # annual minimum award (~10% of max) (authoritative 2026-27)
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


def _parse_coa_source(raw):
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            v = json.loads(raw)
            return v if isinstance(v, dict) else None
        except Exception:
            return None
    return None


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
    coa_source = _parse_coa_source(e.get("coa_source"))  # signed provenance token from lookup_coa

    # ---- P0-3: verify COA provenance. Rebuild the signed field set from the COA WE will use. ----
    prov_verified = False
    if coa_source is not None and coa is not None:
        fields = {"unitid": str(coa_source.get("unitid") or ""),
                  "school": str(coa_source.get("school") or ""),
                  "cost_of_attendance": coa}
        prov_verified = provenance.verify(coa_source.get("source", ""), fields, coa_source)

    prov_src = coa_source.get("source") if isinstance(coa_source, dict) else None

    if sai is None or coa is None:
        return {"assessed": True, "determination": "NEEDS_REVIEW", "authoritative": False,
                "provenance_verified": False, "eligible": None,
                "reason": "insufficient data (need student_aid_index and cost_of_attendance)",
                "deidentified_input": True, "assessed_by": "rules:TitleIV/Pell+SAP(needs COA)",
                "coa_provenance": {"authoritative": False, "verified": False, "source": prov_src}}

    if not prov_verified:
        # Unverified COA: caller-supplied or a fabricated/forged source. Never issue an authoritative
        # aid determination on it — route to a human. (P0-3 anti-fabrication path.)
        return {
            "assessed": True,
            "determination": "NEEDS_REVIEW",
            "authoritative": False,
            "provenance_verified": False,
            "eligible": None,
            "aid_track": "STANDARD",
            "cost_of_attendance": int(coa),
            "deidentified_input": True,
            "assessed_by": "rules:TitleIV(unverified-COA->review)",
            "reason": ("cost of attendance is not from a verified authoritative source (no valid College "
                       "Scorecard provenance signature) — no aid determination made on an unverified COA; "
                       "run lookup_coa and pass its signed coa_source"),
            "coa_provenance": {"authoritative": False, "verified": False, "source": prov_src},
            "notes": ["Pell max/min are authoritative 2026-27 figures (FSA DCL 2026-01-30)",
                      "P0-3: assess requires a lookup-signed COA provenance token; a caller-supplied source label is not trusted"],
        }

    # ---- COA provenance VERIFIED -> authoritative determination ----
    base = min(coa, MAX_PELL) - sai
    scheduled = base if base > 0 else 0.0
    pell = round(scheduled * intensity)
    if 0 < pell < MIN_PELL:
        pell = MIN_PELL if sai <= (MAX_PELL - MIN_PELL) else 0

    if gpa is None or pace is None:
        sap_status = "UNKNOWN"
    elif gpa >= SAP_GPA_MIN and pace >= SAP_PACE_MIN:
        sap_status = "SATISFACTORY"
    else:
        sap_status = "NOT_SATISFACTORY"

    aid_track = "VERIFICATION_HOLD" if selected else "STANDARD"

    if sap_status == "NOT_SATISFACTORY":
        determination, eligible, reason = "NEEDS_REVIEW", None, ("Title IV aid held: SAP not met (GPA %s / pace %s%%); SAP appeal or academic plan required" % (gpa, pace))
    elif selected:
        determination, eligible, reason = "NEEDS_REVIEW", None, ("selected for verification; award held pending documentation (estimated Pell %d)" % pell)
    elif pell > 0:
        determination, eligible, reason = "ELIGIBLE", True, ("estimated Pell %d = min(COA, %d) - SAI %.0f, prorated for %s enrollment" % (pell, MAX_PELL, sai, enroll))
    else:
        determination, eligible, reason = "INELIGIBLE", False, ("SAI %.0f yields no Pell at this COA; may qualify for other Title IV aid (loans/work-study) on review" % sai)

    notes = ["Pell max/min are authoritative 2026-27 figures (FSA DCL 2026-01-30); SAP thresholds are configurable per institution"]
    if determination == "ELIGIBLE":
        notes.append("Pell estimate only; loan/work-study packaging and final COA remain for aid-officer review")

    # Short proof fields FIRST (the MCP client truncates long results ~220 chars); detail LAST.
    return {
        "assessed": True,
        "determination": determination,        # ELIGIBLE | INELIGIBLE | NEEDS_REVIEW
        "authoritative": True,
        "provenance_verified": True,
        "eligible": eligible,
        "aid_track": aid_track,                 # STANDARD | VERIFICATION_HOLD
        "sap_status": sap_status,               # SATISFACTORY | NOT_SATISFACTORY | UNKNOWN
        "pell_award": pell,
        "enrollment_status": enroll,
        "cost_of_attendance": int(coa),
        "coa_provenance": {"authoritative": True, "verified": True, "source": prov_src,
                           "unitid": coa_source.get("unitid"), "school": coa_source.get("school")},
        "deidentified_input": True,
        "assessed_by": "rules:TitleIV/Pell(2026-27 authoritative)+SAP",
        "pell_max_source": "FSA DCL 2026-01-30 (max 7395 / min 740)",
        "reason": reason,
        "notes": notes,
    }
