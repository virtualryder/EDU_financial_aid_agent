// no_self_professional_judgment  (kind: forbid  ·  validation: IGNORE_ALL_FINDINGS)
// Committing a Professional Judgment (HEA 479A) adjustment is a CONSEQUENTIAL, SENIOR-HUMAN-ONLY act.
// The agent can never commit a PJ; commit_professional_judgment is forbidden outright and hidden from the
// agent's tool list. Same deny-by-default pattern as no_self_commit.
forbid(
  principal,
  action == AgentCore::Action::"fa-core___commit_professional_judgment",
  resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-financial-aid-gw"
);
