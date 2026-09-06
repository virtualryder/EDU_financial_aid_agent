// consent_purpose_before_assess_aid  (kind: forbid  ·  validation: IGNORE_ALL_FINDINGS  ·  scope: perimeter)
// CONSENT + PURPOSE (#161) on the governed decision. Aid determination is FERPA-adjacent processing of a student's record: the student's recorded consent/authorization and an authorized purpose (aid_determination or verification) must both be on record before the determination runs.
// consent/purpose are OPTIONAL context.input fields, so each access is presence-guarded
// (`context.input has ...`) - the GA engine rejects an unguarded optional-attribute access and a missing
// field fails the guard, so the forbid fires (fail-closed). Both values are AUTHORITATIVE: the gateway
// interceptor strips any caller-supplied copy and the authoritative_context resolver injects them from
// the server-side authz store (the record ingest wrote from the verified operator's attestation).
// These are COARSE gateway gates layered on the server-side controls; forbid wins over aid_officer_permit.
forbid(
  principal,
  action == AgentCore::Action::"assess-aid___assess_aid",
  resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-aid-gw"
)
unless {
  context.input has consent && context.input.consent == true
  && context.input has purpose
  && (context.input.purpose == "aid_determination" || context.input.purpose == "verification")
};
