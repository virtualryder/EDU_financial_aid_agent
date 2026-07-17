// mask_before_draft  (kind: forbid  ·  validation: IGNORE_ALL_FINDINGS)
// No award-notice drafting on un-masked data. draft_award_notice is forbidden unless deidentified == true,
// so the model only ever sees de-identified case text.
forbid(
  principal,
  action == AgentCore::Action::"fa-core___draft_award_notice",
  resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-financial-aid-gw"
)
unless { context.input.deidentified == true };
