# demo_extra.sh (financial-aid) — agent-specific payloads + content checks.
# Sourced by lib/engine/demo.sh; shares: REV, OUT, REV_U, call(), check(), pass, fail.
T_INTAKE="intake-fafsa___intake_fafsa"
T_COA="lookup-coa___lookup_coa"
T_MASK="mask-pii___mask_pii"
T_ASSESS="assess-aid___assess_aid"
T_DRAFT="fa-core___draft_award_notice"
T_AUDIT="write-audit___write_audit"
T_FINAL="fa-core___finalize_award"

echo "  -- deny-by-default (identity -> Cedar) --"
check "aid_officer intake_fafsa" ALLOW "$(call "$REV" "$T_INTAKE" '{"application":"Student requests federal aid. SAI: 3000. Cost of attendance: 25000. Enrollment: full-time. GPA 3.2, pace 85%."}')"
check "outsider    intake_fafsa" DENY  "$(call "$OUT" "$T_INTAKE" '{"application":"SAI: 3000. Cost of attendance: 25000."}')"

echo "  -- authoritative COA via College Scorecard (LIVE federal API, governed) --"
COA_OUT="$(call "$REV" "$T_COA" '{"school":"University of Michigan-Ann Arbor"}')"
check "aid_officer lookup_coa" ALLOW "$COA_OUT"
# P0-3: a real lookup returns authoritative:true + a SIGNED coa_source token. If College Scorecard is
# unavailable (found:false, no signed token) we do NOT fabricate a COA; the assess step below then
# correctly refuses to issue an authoritative determination.
if echo "$COA_OUT" | grep -q '"found": *true' && echo "$COA_OUT" | grep -q '"authoritative": *true'; then
  echo "  PASS | lookup_coa returned an AUTHORITATIVE COA + a SIGNED provenance token"; pass=$((pass+1))
else
  echo "  INFO | live College Scorecard unavailable — demonstrating the P0-3 NEEDS_REVIEW path below (no fabricated COA)"
fi

echo "  -- fail-closed PII de-identification (mask_pii) --"
MASK_OUT="$(call "$REV" "$T_MASK" '{"case":"Applicant Jane Doe, SSN 123-45-6789, 42 Main St, FAFSA for federal aid; SAI 3000, COA 25000, full-time."}')"
check "aid_officer mask_pii" ALLOW "$MASK_OUT"
if echo "$MASK_OUT" | grep -q 'REDACTED' && ! echo "$MASK_OUT" | grep -q 'Jane Doe'; then echo "  PASS | mask_pii redacted PII (name/SSN removed)"; pass=$((pass+1)); else echo "  FAIL | mask_pii did NOT redact -> $MASK_OUT"; fail=$((fail+1)); fi

echo "  -- forbid: mask-before-assess (aid determination) --"
check "aid_officer assess (UN-masked)" DENY "$(call "$REV" "$T_ASSESS" '{"student_aid_index":3000,"cost_of_attendance":25000,"deidentified":false}')"

echo "  -- P0-3: assess trusts ONLY a lookup-signed COA provenance token (never a fabricated source) --"
# A hand-typed College-Scorecard-looking COA + source string, WITHOUT a valid lookup signature, must NOT
# produce an aid determination — the fabrication the old demo committed (fallback COA + a source label ->
# ELIGIBLE). Now it routes to NEEDS_REVIEW, authoritative:false.
FAB_OUT="$(call "$REV" "$T_ASSESS" '{"student_aid_index":3000,"cost_of_attendance":25000,"enrollment_status":"full","sap_gpa":3.2,"sap_pace":85,"coa_source":"US Dept of Education - College Scorecard","deidentified":true}')"
check "aid_officer assess (fabricated provenance)" ALLOW "$FAB_OUT"
if echo "$FAB_OUT" | grep -q '"determination": *"NEEDS_REVIEW"' && echo "$FAB_OUT" | grep -q '"authoritative": *false'; then echo "  PASS | fabricated/unsigned COA -> NEEDS_REVIEW, authoritative:false (no fabricated aid determination)"; pass=$((pass+1)); else echo "  FAIL | fabricated COA provenance was trusted -> $FAB_OUT"; fail=$((fail+1)); fi
if echo "$FAB_OUT" | grep -q '"determination": *"ELIGIBLE"'; then echo "  FAIL | UNVERIFIED COA produced an ELIGIBLE determination -> $FAB_OUT"; fail=$((fail+1)); else echo "  PASS | no aid issued on an unverified COA (P0-3)"; pass=$((pass+1)); fi

echo "  -- forbid: mask-before-model (award notice) --"
check "aid_officer draft (UN-masked)" DENY "$(call "$REV" "$T_DRAFT" '{"case":"x","deidentified":false}')"
DRAFT_OUT="$(call "$REV" "$T_DRAFT" '{"case":"De-identified student [REDACTED:NAME], SAI 3000, COA 25000, full-time. Determination: ELIGIBLE, estimated Pell 4395, SAP satisfactory, standard disbursement.","deidentified":true}')"
check "aid_officer draft (de-identified)" ALLOW "$DRAFT_OUT"
if echo "$DRAFT_OUT" | grep -qE '"chars": *[1-9]' && ! echo "$DRAFT_OUT" | grep -q '"error"'; then echo "  PASS | draft_award_notice produced a real Bedrock notice"; pass=$((pass+1)); else echo "  FAIL | draft -> $DRAFT_OUT"; fail=$((fail+1)); fi
if echo "$DRAFT_OUT" | grep -q '"guardrail_applied": *true'; then echo "  PASS | notice passed the fail-closed guardrail"; pass=$((pass+1)); else echo "  FAIL | guardrail not applied -> $DRAFT_OUT"; fail=$((fail+1)); fi

echo "  -- immutable WORM audit --"
NONCE="$RANDOM$RANDOM"
AUDIT_IN="{\"icsr_id\":\"AID-2026-0002\",\"action\":\"award_determination\",\"phase\":\"INTENT\",\"actor\":\"$REV_U\",\"payload\":\"run-$NONCE\"}"
A1="$(call "$REV" "$T_AUDIT" "$AUDIT_IN")"
check "aid_officer write_audit (1st)" ALLOW "$A1"
if echo "$A1" | grep -q '"stored": *true' && echo "$A1" | grep -q '"worm": *true'; then echo "  PASS | audit -> append-only ledger + WORM"; pass=$((pass+1)); else echo "  FAIL | audit not stored/worm -> $A1"; fail=$((fail+1)); fi
A2="$(call "$REV" "$T_AUDIT" "$AUDIT_IN")"
if echo "$A2" | grep -q '"stored": *false' && echo "$A2" | grep -qi 'append-only'; then echo "  PASS | duplicate rejected (immutable)"; pass=$((pass+1)); else echo "  FAIL | dup not rejected -> $A2"; fail=$((fail+1)); fi

echo "  -- forbid: no self-commit --"
check "aid_officer finalize_award" DENY "$(call "$REV" "$T_FINAL" '{"award_id":"AID-2026-0002"}')"

echo "  == STEP TWO: deeper caseload workflows =="
T_VERIFY="verify-docs___verify_documents"
T_PJ="record-pj___record_professional_judgment"
T_PJCOMMIT="fa-core___commit_professional_judgment"

echo "  -- Title IV verification hold --"
VER_OUT="$(call "$REV" "$T_VERIFY" '{"required_documents":"tax_return,verification_worksheet,w2","received_documents":"tax_return"}')"
check "aid_officer verify_documents" ALLOW "$VER_OUT"
if echo "$VER_OUT" | grep -q 'PENDING' && echo "$VER_OUT" | grep -q '"hold": *true'; then echo "  PASS | verification incomplete -> aid HELD pending documents"; pass=$((pass+1)); else echo "  FAIL | verify -> $VER_OUT"; fail=$((fail+1)); fi

echo "  -- professional judgment: documented, human-approved (HEA 479A) --"
check "aid_officer record_pj (UN-masked)" DENY "$(call "$REV" "$T_PJ" '{"circumstance":"job loss","rationale":"documented layoff reduces income","deidentified":false}')"
PJ_OUT="$(call "$REV" "$T_PJ" '{"circumstance":"parent job loss","proposed_adjustment":"reduce AGI","rationale":"Documented 2026 layoff; income reduced 40 percent per severance letter","deidentified":true}')"
check "aid_officer record_pj (de-identified)" ALLOW "$PJ_OUT"
if echo "$PJ_OUT" | grep -q '"status": *"PREPARED"' && echo "$PJ_OUT" | grep -q '"requires_senior_approval": *true'; then echo "  PASS | PJ prepared + documented -> a DIFFERENT senior officer must approve"; pass=$((pass+1)); else echo "  FAIL | record_pj -> $PJ_OUT"; fail=$((fail+1)); fi
PJ_NORAT="$(call "$REV" "$T_PJ" '{"circumstance":"job loss","deidentified":true}')"
if echo "$PJ_NORAT" | grep -qi 'requires a documented'; then echo "  PASS | PJ refused without a documented rationale (mandatory)"; pass=$((pass+1)); else echo "  FAIL | PJ no-rationale not refused -> $PJ_NORAT"; fail=$((fail+1)); fi

echo "  -- forbid: no self professional-judgment commit (senior-human-only) --"
check "aid_officer commit_professional_judgment" DENY "$(call "$REV" "$T_PJCOMMIT" '{"pj_id":"PJ-2026-0002"}')"
