// mask_before_pj  (kind: forbid  ·  validation: IGNORE_ALL_FINDINGS)
// No professional-judgment recommendation on un-masked data. record_professional_judgment is forbidden
// unless deidentified == true (set only by mask_pii). forbid wins over any permit.
forbid(
  principal,
  action == AgentCore::Action::"record-pj___record_professional_judgment",
  resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-financial-aid-gw"
)
unless { context.input.deidentified == true };
