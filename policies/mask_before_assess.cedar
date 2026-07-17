// mask_before_assess  (kind: forbid  ·  validation: IGNORE_ALL_FINDINGS)
// No aid determination on un-masked data. assess_aid is forbidden unless the caller passes
// deidentified == true (set only by mask_pii). forbid wins over any permit.
forbid(
  principal,
  action == AgentCore::Action::"assess-aid___assess_aid",
  resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-financial-aid-gw"
)
unless { context.input.deidentified == true };
