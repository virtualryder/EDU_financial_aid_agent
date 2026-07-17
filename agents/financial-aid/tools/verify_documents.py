import json

# verify_documents — Title IV VERIFICATION workflow. When an application is selected for verification
# (34 CFR 668.51-.61), federal aid is HELD until the required documents are received and reconciled.
# This tool tracks verification status and returns whether aid is on HOLD. It operates on document-type
# flags (which items are required vs received) — not on document CONTENT — so it does not need masking;
# the governance point here is the HOLD state, not de-identification: no disbursement while PENDING.
#
# The agent can track and report verification, but clearing verification and releasing the hold is an
# aid-officer action recorded through the normal determination path.


def _coerce(e):
    e = e or {}
    if isinstance(e, str):
        try:
            e = json.loads(e)
        except Exception:
            e = {"_raw": e}
    return e


def _as_set(v):
    if v is None:
        return None
    if isinstance(v, (list, tuple)):
        return set(str(x).strip().lower() for x in v if str(x).strip())
    if isinstance(v, str):
        return set(p.strip().lower() for p in v.split(",") if p.strip())
    return None


def handler(event, context):
    e = _coerce(event)

    required = _as_set(e.get("required_documents"))
    received = _as_set(e.get("received_documents")) or set()

    # Also accept simple counts if lists aren't provided.
    if required is None:
        try:
            req_n = int(e.get("required_count"))
        except Exception:
            req_n = None
        try:
            rec_n = int(e.get("received_count"))
        except Exception:
            rec_n = 0
        if req_n is None:
            return {"verified": False, "error": "provide required_documents (list) or required_count"}
        missing_n = max(0, req_n - rec_n)
        complete = missing_n == 0
        status = "COMPLETE" if complete else "PENDING"
        return {
            "verified": True,
            "verification_status": status,          # COMPLETE | PENDING
            "hold": (not complete),                  # aid is held while PENDING
            "missing_count": missing_n,
            "note": ("verification complete; hold released for aid-officer review"
                     if complete else
                     "AID HELD: %d document(s) outstanding; no disbursement until verification clears" % missing_n),
        }

    missing = sorted(required - received)
    complete = len(missing) == 0
    status = "COMPLETE" if complete else "PENDING"

    # Short proof fields FIRST (MCP client truncates ~200 chars).
    return {
        "verified": True,
        "verification_status": status,              # COMPLETE | PENDING
        "hold": (not complete),                      # aid is held while PENDING
        "missing": missing,
        "missing_count": len(missing),
        "note": ("verification complete; hold released for aid-officer review"
                 if complete else
                 "AID HELD pending verification: missing " + ", ".join(missing)),
    }
