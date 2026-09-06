import json

import sanitized   # P0-1 verification + server-side content channel
import os
import boto3
from botocore.exceptions import BotoCoreError, ClientError
import re

# Financial-aid core tools behind the `fa-core` Gateway target:
#   - draft_award_notice -> REAL Bedrock (Converse) award/determination notice from a de-identified case
#   - finalize_award     -> deny-only stub (the human sign-off gate owns the real commit)
# Branch on the input shape (finalize carries award_id; draft carries case/deidentified).

DRAFT_MODEL_ID = os.environ.get("DRAFT_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")
GUARDRAIL_ID = os.environ.get("GUARDRAIL_ID", "")
GUARDRAIL_VERSION = os.environ.get("GUARDRAIL_VERSION", "DRAFT")

_SYSTEM = (
    "You draft a federal student-aid AWARD/DETERMINATION NOTICE for a financial-aid officer to review. "
    "You are given an ALREADY DE-IDENTIFIED case plus an aid determination. Write a clear, plain-language "
    "notice (roughly 120-250 words). Rules: (1) Preserve every [REDACTED:...] placeholder verbatim; never "
    "guess redacted values. (2) State the determination (eligible/ineligible/needs review), the estimated "
    "Pell award, and the plain reason. (3) Note the Satisfactory Academic Progress status and any "
    "verification hold. (4) Include a short, neutral statement of the student's right to appeal / request "
    "review. (5) This is a DRAFT estimate for human review, not a final award. Output the notice text only."
)
# #190 (PAR-1 port, 2026-09-06): with a guardrail bound, the model generates ONLY the GROUNDED FACTUAL CORE
# (determination + estimated award + plain reason, strictly from the case + the deterministic aid
# determination) tagged guardContent grounding_source + query, so the guardrail's CONTEXTUAL GROUNDING
# filter scores the model's factual claims. The fixed notice boilerplate (appeal/review right, DRAFT
# framing, COA basis) is appended DETERMINISTICALLY after the call so it never sinks the grounding score.
_SYSTEM_GROUNDED_CORE = (
    "You write ONLY the factual core of a federal student-aid award/determination notice, for a "
    "financial-aid officer to review. You are given an ALREADY DE-IDENTIFIED case plus its deterministic "
    "aid determination. Output 2-4 plain-language sentences stating (a) the determination (eligible / "
    "ineligible / needs review), (b) the estimated Pell award and the Satisfactory Academic Progress status "
    "if present, and (c) the reason, using ONLY facts present in the provided case and determination. "
    "Preserve every [REDACTED:...] placeholder verbatim; never guess redacted values. Do NOT add appeal "
    "rights, deadlines, dates, or any detail not in the case - those are appended separately. Output the "
    "factual core text only."
)
_NOTICE_BOILERPLATE = (
    "\n\nRight to review: you may request a review of this determination or appeal per institutional "
    "policy [aid officer to insert process and deadline].\n"
    "Cost-of-attendance basis: estimate on College Scorecard REFERENCE data - institutional COA is "
    "required for any award.\n"
    "This is a DRAFT estimate for financial-aid officer review, not a final award."
)

# L14 (benefits full-portfolio gate, 2026-09-06): the grounded drafter may state ONLY a determination that is
# IN its grounding source. The deterministic engine's output is therefore a REQUIRED input under a
# guardrail, rendered into the source from an ALLOWLIST of fields (never caller free text).
_DETERMINATION_FIELDS = ("determination", "eligible", "aid_track", "sap_status", "pell_award",
                         "enrollment_status", "cost_of_attendance", "student_aid_index", "reason", "assessed_by")
_DET_OK = re.compile(r"[^a-zA-Z0-9\s:_@$#=/+,\-.%()\[\]']")


def _determination_text(d):
    if isinstance(d, str):
        try:
            d = json.loads(d)
        except Exception:
            return _DET_OK.sub("_", d.strip())[:600]
    if not isinstance(d, dict):
        return ""
    parts = []
    for k in _DETERMINATION_FIELDS:
        if d.get(k) is not None and d.get(k) != "":
            parts.append("%s=%s" % (k, _DET_OK.sub("_", str(d[k]))[:300]))
    return "; ".join(parts)


def _coerce(event):
    e = event or {}
    if isinstance(e, str):
        try:
            e = json.loads(e)
        except Exception:
            e = {"_raw": e}
    return e


_META_OK = re.compile(r"[^a-zA-Z0-9\s:_@$#=/+,\-.]")


def _request_metadata(tenant):
    r"""Converse.requestMetadata: <= 16 items, keys/values <= 256 chars from [a-zA-Z0-9\s:_@$#=/+,-.] (API
    reference). Correlation keys only - the same set telemetry puts on the aegis.call line."""
    meta = {"component": "draft_award_notice"}
    if tenant:
        meta["tenant"] = tenant
    try:
        import telemetry
        cur = telemetry.current()
        for k in ("trace_id", "session_id", "execution_arn", "request_id"):
            if cur.get(k):
                meta[k] = cur[k]
    except Exception:
        pass
    return {k: _META_OK.sub("_", str(v))[:256] for k, v in meta.items() if v}


def _metered_tenant():
    """The tenant the meter charges: the request-bound one (multi-tenant) or the pinned silo id."""
    try:
        return tenancy.resolve_tenant()
    except Exception:
        return os.environ.get("TENANT_ID") or "default"


def _draft(e):
    ref = sanitized.parse_ref(e.get("sanitized_ref"))
    if not sanitized.verify_ref(ref):
        return {"error": "refused: de-identification not proven - a valid sanitized_ref signed by mask_pii is required",
                "drafted_by": None, "deidentified_input": e.get("deidentified")}
    raw_case = e.get("case", "")
    if not isinstance(raw_case, str):
        raw_case = json.dumps(raw_case, ensure_ascii=False)
    # content binding: the text used MUST hash to the signed digest; preferred channel is the
    # server-side artifact store (content never re-enters the model context via the caller).
    case = sanitized.load_text(ref, candidate_text=raw_case)
    if case is None:
        return {"error": "refused: case content does not match the signed sanitized artifact",
                "drafted_by": None, "sanitized_ref_verified": True, "content_bound": False}
    # L14: the determination the notice states comes from the deterministic engine and MUST be in the
    # grounding source; without it the drafter refuses fail-closed BEFORE any model spend.
    det_text = _determination_text(e.get("determination"))
    if GUARDRAIL_ID and not det_text:
        return {"error": "refused: determination required - the grounded drafter states only a determination "
                         "present in its grounding source; pass assess_aid's output as `determination`",
                "drafted_by": None, "determination_present": False, "guardrail_applied": True}
    source = case + ("\n\nDeterministic aid determination (rules engine, not the model): " + det_text
                     if det_text else "")
    if GUARDRAIL_ID:
        system = [{"text": _SYSTEM_GROUNDED_CORE}]
        content = [
            {"guardContent": {"text": {"text": source, "qualifiers": ["grounding_source"]}}},
            {"guardContent": {"text": {"text": "What is the aid determination, the estimated award and the "
                                               "reason, based only on these case facts?", "qualifiers": ["query"]}}},
        ]
    else:
        system = [{"text": _SYSTEM}]
        content = [{"text": "De-identified case + determination:\n" + source}]
    kwargs = dict(
        modelId=DRAFT_MODEL_ID,
        system=system,
        messages=[{"role": "user", "content": content}],
        inferenceConfig={"maxTokens": 700, "temperature": 0.2},
    )
    # task 128 (governed-core 1.9.0): the budget meter on the SERVER-SIDE model call. reserve() before the
    # spend (the workflow hop has no gateway interceptor, so this is where a capped tenant is stopped on
    # the DraftNotice state -> ManualReview, fail-closed); commit() the real Converse usage after. The
    # drafter's model-invocation log row is tagged with requestMetadata {tenant, component, trace/
    # execution/session ids} (never content, never a case id - R3-2) so it joins the tenant's meter.
    tenant = _metered_tenant()
    meta = _request_metadata(tenant)
    if meta:
        kwargs["requestMetadata"] = meta
    try:
        reservation = budget.reserve(tenant)
    except budget.BudgetExceeded as exc:
        audit = budget.record_denial(exc.decision, {"case_id": e.get("case_id"), "tool": "draft_award_notice"}, None, component="draft_award_notice")
        budget.log_line(exc.decision, component="draft_award_notice", audit=audit)
        return {"error": "refused: budget exceeded - the tenant's period cap is reached (hard cap); no draft was generated",
                "drafted_by": None, "guardrail_action": budget.GUARDRAIL_ACTION, "budget": budget.refusal(exc.decision)}
    if GUARDRAIL_ID:
        kwargs["guardrailConfig"] = {"guardrailIdentifier": GUARDRAIL_ID, "guardrailVersion": GUARDRAIL_VERSION}
    try:
        br = boto3.client("bedrock-runtime")
        resp = br.converse(**kwargs)
        metered = budget.commit(tenant, resp.get("usage"), DRAFT_MODEL_ID, reserved=reservation.get("reserved", 0))
        notice = resp["output"]["message"]["content"][0]["text"].strip()
        if resp.get("stopReason") == "guardrail_intervened":
            # ANY intervention is fail-closed - including when the guardrail substitutes its configured
            # blocked message (non-empty text). No notice_ref is minted for a blocked draft.
            return {"error": "output guardrail blocked the draft (fail-closed)", "drafted_by": None,
                    "guardrail": "BLOCKED", "guardrail_version": GUARDRAIL_VERSION}
        # #190: the model output is the GROUNDING-passed factual core; append the fixed notice boilerplate
        # deterministically (not model-generated, not grounding-scored) to form the full notice.
        if GUARDRAIL_ID:
            notice = notice + _NOTICE_BOILERPLATE
        out = {"drafted_by": DRAFT_MODEL_ID, "chars": len(notice),
               "guardrail_applied": bool(GUARDRAIL_ID), "deidentified_input": True,
               "budget": {k: metered.get(k) for k in ("metered", "tokens", "usd_micro", "used_tokens", "pct_tokens", "price_version")},
               "coa_basis": "estimate on College Scorecard REFERENCE data - institutional COA required for any award"}
        # Gate-B accessibility: advisory plain-language check on the drafted notice (docs/ACCESSIBILITY.md).
        # Non-blocking — surfaces reading grade + any missing student-action element for the reviewing
        # officer; the human gate still owns whether the notice is sent.
        try:
            import readability
            out["plain_language"] = readability.assess(notice)
        except Exception:
            pass   # accessibility advisory must never affect the draft result
        # R3-2 pass-by-reference: with a case store configured, the notice returns as an opaque
        # notice_ref (content stored server-side); inline text only in dev/direct mode.
        import os
        if os.environ.get("CASE_TABLE"):
            import case_store
            out["notice_ref"] = case_store.put_case(notice, kind="notice")
        else:
            out["notice"] = notice
        return out
    except (BotoCoreError, ClientError, KeyError, IndexError) as exc:
        return {"error": "draft failed: " + type(exc).__name__ + ": " + str(exc), "drafted_by": None}


import budget  # noqa: E402  (task 128: per-tenant token + USD meter, governed-core 1.9.0)
import tenancy  # noqa: E402  (phase 107: interceptor-injected, HMAC-signed tenant)
import telemetry  # noqa: E402  (phase 110: correlation keys -> one aegis.call log line per invocation)


@telemetry.instrument('aid_core')
def handler(event, context):
    # Phase 107 (hybrid multi-tenant): bind the gateway-interceptor-injected, HMAC-SIGNED tenant for
    # per-tenant store routing. Unsigned/forged values are refused; multi-tenant mode fails closed.
    tenancy.bind_tenant_from_args(event)
    e = _coerce(event)
    if "pj_id" in e:
        # commit_professional_judgment is a consequential, HUMAN-ONLY discretionary action. The agent can
        # never commit a professional-judgment adjustment; a senior aid officer does, through the human
        # gate. Forbidden to the agent by Cedar (no_self_professional_judgment); refused here too.
        return {"error": "refused: committing a professional-judgment adjustment is a senior-aid-officer decision; the agent cannot commit",
                "pj_id": e.get("pj_id"), "committed": False}
    if "award_id" in e and "case" not in e:
        # finalize_award is never a real inline call — the human sign-off gate owns it.
        return {"error": "refused: finalize_award must go through the human sign-off gate",
                "award_id": e.get("award_id"), "committed": False}
    if "case" in e or "deidentified" in e or "sanitized_ref" in e:
        return _draft(e)
    return {"ok": True, "received": e, "note": "financial-aid core tool"}
