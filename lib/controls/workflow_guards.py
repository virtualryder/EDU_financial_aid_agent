import json

import provenance
import sanitized

# workflow_guards — the machine-verifiable transition evidence for the DETERMINISTIC workflow
# controller (P0-2). The Step Functions controller (cdk/ WorkflowStack) invokes this single Lambda
# between pipeline stages; each guard returns {"guard", "ok", "reason"} and the state machine BRANCHES
# on `ok` — a stage cannot be skipped, reordered, or passed on asserted (unverified) state, because the
# transition itself demands cryptographic or structural proof:
#
#   extracted      -> the intake actually produced the decision fields
#   authoritative  -> the HUD limits carry a VERIFIED lookup-minted provenance signature (P0-3 pattern)
#   deidentified   -> a VERIFIED mask_pii-signed sanitized_ref exists (P0-1; boolean never accepted)
#   rules_executed -> the deterministic rules engine ran and yielded a legal determination
#
# Fail-closed: any missing/forged/tampered evidence -> ok:false; the controller routes to ManualReview
# (NEEDS_REVIEW) — never onward. Pure logic + the shared verifiers, fully unit-testable offline.

_LEGAL_DETERMINATIONS = {"ELIGIBLE", "INELIGIBLE", "NEEDS_REVIEW"}


def _coerce(e):
    e = e or {}
    if isinstance(e, str):
        try:
            e = json.loads(e)
        except Exception:
            e = {}
    return e


def _num(v):
    try:
        return float(v)
    except Exception:
        return None


def guard_extracted(e):
    """FAFSA intake must yield the decision fields: a Student Aid Index and a school identifier."""
    f = e.get("fields") or {}
    ok = _num(f.get("student_aid_index")) is not None and bool(f.get("school") or f.get("unitid"))
    return ok, ("decision fields present" if ok else
                "intake did not yield student_aid_index + school/unitid")


def guard_reference_coa(e):
    """EDU adaptation of the Housing authoritative-source guard. Verifies the lookup-minted
    signature over the EXACT cost-of-attendance figure the workflow will use — anti-fabrication —
    while being honest about SEMANTICS: College Scorecard is verified REFERENCE data, not the
    institutional COA (review finding, adopted). A verified signature proves the number came from
    the real Scorecard API unaltered; it does NOT make it an award-package COA — every downstream
    output carries the reference-basis label and the result is an AID ESTIMATE.

    Accepts the WHOLE lookup output under `lookup` (a source-down lookup returns found:false with NO
    coa keys, and judging that is THIS guard's job — never a JSONPath error in the state machine)."""
    if isinstance(e.get("lookup"), dict):
        e = dict(e["lookup"])
    if e.get("found") is False:
        return False, "reference COA source unavailable (lookup found:false) — manual review"
    src = e.get("coa_source")
    if isinstance(src, str):
        try:
            src = json.loads(src)
        except Exception:
            src = None
    if not isinstance(src, dict):
        return False, "no provenance token (coa_source) from lookup_coa"
    coa = _num(e.get("cost_of_attendance"))
    if coa is None:
        return False, "cost_of_attendance missing/invalid"
    fields = {"unitid": str(src.get("unitid") or ""), "school": str(src.get("school") or ""),
              "cost_of_attendance": int(coa)}
    ok = provenance.verify(src.get("source", ""), fields, src, domain="scorecard")   # GA-2 domain key
    return ok, ("Scorecard REFERENCE COA carries a verified lookup signature (estimate basis only; "
                "institutional COA required for awards)" if ok else
                "reference COA is NOT verified (missing/forged/tampered signature)")


def guard_deidentified(e):
    ok = sanitized.verify_ref(e.get("sanitized_ref"))
    return ok, ("masking proven by a verified mask_pii-signed sanitized_ref" if ok else
                "de-identification not proven (no valid sanitized_ref; a boolean is not proof)")


def guard_rules_executed(e):
    r = e.get("assessment") or {}
    if isinstance(r, str):
        try:
            r = json.loads(r)
        except Exception:
            r = {}
    ok = r.get("assessed") is True and r.get("determination") in _LEGAL_DETERMINATIONS
    return ok, ("deterministic rules engine produced a legal determination" if ok else
                "rules engine did not run or returned no legal determination")


def guard_verification(e):
    """EDU pilot-core path: if the case is selected for verification (or documents are incomplete),
    the workflow must HOLD — no estimate proceeds to drafting until documentation clears. This guard
    returns ok=False for a hold, which the controller routes to the VerificationHold terminal state
    (a WORK QUEUE for the aid office, not an error)."""
    a = e.get("assessment") or {}
    if isinstance(a, str):
        try:
            a = json.loads(a)
        except Exception:
            a = {}
    docs = e.get("documents") or {}
    missing = docs.get("missing") if isinstance(docs, dict) else None
    held = a.get("aid_track") == "VERIFICATION_HOLD" or bool(missing)
    return (not held), ("no verification hold" if not held else
                        "case held for verification: selected and/or documents incomplete%s"
                        % (f" (missing: {', '.join(missing)})" if missing else ""))


_GUARDS = {
    "extracted": guard_extracted,
    "reference_coa": guard_reference_coa,
    "deidentified": guard_deidentified,
    "rules_executed": guard_rules_executed,
    "verification": guard_verification,
}


def _emit_metric(guard, ok):
    """R3-3 security telemetry: every guard evaluation emits a CloudWatch EMF metric
    (Housing/Governance :: GuardFailed{Guard}). A failed guard is a SECURITY SIGNAL — forged
    sanitized_ref, tampered provenance, spoofed boolean — not just an ops event; the
    ObservabilityStack alarms on any nonzero sum. Metric only (no payload content), so this adds
    nothing to the telemetry PII surface."""
    import json as _json
    import time as _time
    try:
        print(_json.dumps({
            "_aws": {"Timestamp": int(_time.time() * 1000),
                     "CloudWatchMetrics": [{"Namespace": "Housing/Governance",
                                            "Dimensions": [["Guard"]],
                                            "Metrics": [{"Name": "GuardFailed", "Unit": "Count"}]}]},
            "Guard": guard, "GuardFailed": 0 if ok else 1}))
    except Exception:
        pass   # metrics must never affect the control decision


def handler(event, context):
    e = _coerce(event)
    name = str(e.get("guard", ""))
    fn = _GUARDS.get(name)
    if fn is None:
        _emit_metric(name or "unknown", False)
        return {"guard": name, "ok": False, "reason": "unknown guard (fail-closed)"}
    try:
        ok, reason = fn(e)
    except Exception as exc:  # any guard error is a fail-closed deny, never a pass
        ok, reason = False, "guard error (fail-closed): %s" % type(exc).__name__
    _emit_metric(name, ok)
    return {"guard": name, "ok": bool(ok), "reason": reason}
