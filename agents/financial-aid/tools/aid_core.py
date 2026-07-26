import json

import sanitized   # P0-1 verification + server-side content channel
import os
import boto3
from botocore.exceptions import BotoCoreError, ClientError

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


def _coerce(event):
    e = event or {}
    if isinstance(e, str):
        try:
            e = json.loads(e)
        except Exception:
            e = {"_raw": e}
    return e


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
    kwargs = dict(
        modelId=DRAFT_MODEL_ID,
        system=[{"text": _SYSTEM}],
        messages=[{"role": "user", "content": [{"text": "De-identified case + determination:\n" + case}]}],
        inferenceConfig={"maxTokens": 700, "temperature": 0.2},
    )
    if GUARDRAIL_ID:
        kwargs["guardrailConfig"] = {"guardrailIdentifier": GUARDRAIL_ID, "guardrailVersion": GUARDRAIL_VERSION}
    try:
        br = boto3.client("bedrock-runtime")
        resp = br.converse(**kwargs)
        notice = resp["output"]["message"]["content"][0]["text"].strip()
        if resp.get("stopReason") == "guardrail_intervened" and not notice:
            return {"error": "output guardrail blocked the draft (fail-closed)", "drafted_by": None, "guardrail": "BLOCKED"}
        out = {"drafted_by": DRAFT_MODEL_ID, "chars": len(notice),
               "guardrail_applied": bool(GUARDRAIL_ID), "deidentified_input": True,
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


def handler(event, context):
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
