// amount_cap_assess_aid  (kind: forbid  ·  validation: IGNORE_ALL_FINDINGS  ·  scope: perimeter)
// QUANTITATIVE (#161): A cost of attendance above the institutional ceiling is not an automated determination: the aid officer must review it, so the gate refuses the tool call. The field is a tool-schema `number`, which Cedar sees as a DECIMAL, so
// the comparison uses the decimal extension (never the Long <=/>= operators - the GA engine rejects
// those on a decimal). Optional field -> presence-guarded -> a missing value fails closed.
forbid(
  principal,
  action == AgentCore::Action::"assess-aid___assess_aid",
  resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-aid-gw"
)
unless {
  context.input has cost_of_attendance
  && context.input.cost_of_attendance.lessThanOrEqual(decimal("100000.0"))
};
