import json

# record_professional_judgment — PREPARE a documented Professional Judgment (PJ) recommendation.
# Under HEA Sec. 479A, a financial-aid officer may, on a case-by-case basis and with adequate
# documentation, adjust data elements for special circumstances (job loss, unusual medical expenses,
# etc.). PJ is the highest-risk discretionary act in aid: it must be DOCUMENTED and it is a HUMAN
# decision. This tool only PREPARES the recommendation — it requires a written rationale and returns a
# record that a DIFFERENT senior aid officer must approve. It never commits the adjustment; committing a
# PJ is forbidden to the agent (Cedar no_self_professional_judgment) and goes through the human gate.
#
# Fail-closed: refuses non-de-identified input, and refuses without a documented rationale.


def _coerce(e):
    e = e or {}
    if isinstance(e, str):
        try:
            e = json.loads(e)
        except Exception:
            e = {"_raw": e}
    return e


def handler(event, context):
    e = _coerce(event)
    if e.get("deidentified") is not True:
        return {"prepared": False, "error": "refused: case is not de-identified (deidentified must be true)",
                "deidentified_input": e.get("deidentified")}

    circumstance = str(e.get("circumstance", "")).strip()
    proposed_adjustment = str(e.get("proposed_adjustment", "")).strip()
    rationale = str(e.get("rationale", "")).strip()

    # PJ MUST be documented. No rationale -> refuse to prepare (documentation is a legal requirement).
    if len(rationale) < 10:
        return {"prepared": False,
                "error": "refused: professional judgment requires a documented, case-specific rationale",
                "requires": "rationale (>= 10 chars)"}
    if not circumstance:
        return {"prepared": False, "error": "refused: a special circumstance must be stated"}

    # Short proof fields FIRST (MCP client truncates ~200 chars).
    return {
        "prepared": True,
        "status": "PREPARED",                        # PREPARED (awaiting senior approval); never COMMITTED here
        "requires_senior_approval": True,            # a DIFFERENT senior aid officer must approve
        "committed": False,
        "deidentified_input": True,
        "circumstance": circumstance[:80],
        "proposed_adjustment": proposed_adjustment[:80],
        "rationale_recorded": True,
        "note": ("PJ recommendation documented and PREPARED. A DIFFERENT senior aid officer must approve; "
                 "the agent cannot commit a professional-judgment adjustment (forbidden by policy)."),
    }
