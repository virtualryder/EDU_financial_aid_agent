# demo_extra.sh (financial-aid) — agent-specific payloads + content checks.
# Sourced by lib/engine/demo.sh; shares: REV, OUT, REV_U, call(), check(), pass, fail.
T_INTAKE="intake-fafsa___intake_fafsa"
T_MASK="mask-pii___mask_pii"
T_ASSESS="assess-aid___assess_aid"
T_DRAFT="fa-core___draft_award_notice"
T_AUDIT="write-audit___write_audit"
T_FINAL="fa-core___finalize_award"

echo "  -- deny-by-default (identity -> Cedar) --"
check "aid_officer intake_fafsa" ALLOW "$(call "$REV" "$T_INTAKE" '{"application":"Student requests federal aid. SAI: 3000. Cost of attendance: 25000. Enrollment: full-time. GPA 3.2, pace 85%."}')"
check "outsider    intake_fafsa" DENY  "$(call "$OUT" "$T_INTAKE" '{"application":"SAI: 3000. Cost of attendance: 25000."}')"

echo "  -- fail-closed PII de-identification (mask_pii) --"
MASK_OUT="$(call "$REV" "$T_MASK" '{"case":"Applicant Jane Doe, SSN 123-45-6789, 42 Main St, FAFSA for federal aid; SAI 3000, COA 25000, full-time."}')"
check "aid_officer mask_pii" ALLOW "$MASK_OUT"
if echo "$MASK_OUT" | grep -q 'REDACTED' && ! echo "$MASK_OUT" | grep -q 'Jane Doe'; then echo "  PASS | mask_pii redacted PII (name/SSN removed)"; pass=$((pass+1)); else echo "  FAIL | mask_pii did NOT redact -> $MASK_OUT"; fail=$((fail+1)); fi

echo "  -- forbid: mask-before-assess (aid determination) --"
check "aid_officer assess (UN-masked)" DENY "$(call "$REV" "$T_ASSESS" '{"student_aid_index":3000,"cost_of_attendance":25000,"deidentified":false}')"
ASSESS_OUT="$(call "$REV" "$T_ASSESS" '{"student_aid_index":3000,"cost_of_attendance":25000,"enrollment_status":"full","sap_gpa":3.2,"sap_pace":85,"deidentified":true}')"
check "aid_officer assess (de-identified)" ALLOW "$ASSESS_OUT"
if echo "$ASSESS_OUT" | grep -q 'ELIGIBLE' && echo "$ASSESS_OUT" | grep -qE '"aid_track"'; then echo "  PASS | assess_aid returned a determination + aid track"; pass=$((pass+1)); else echo "  FAIL | assess -> $ASSESS_OUT"; fail=$((fail+1)); fi

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
