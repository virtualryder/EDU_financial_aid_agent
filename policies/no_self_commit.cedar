// no_self_commit  (kind: forbid  ·  validation: IGNORE_ALL_FINDINGS)
// The agent can never commit an award. finalize_award is forbidden outright and hidden from the agent's
// tool list; the only path to commit is the human sign-off gate (Step Functions), where a DIFFERENT
// qualified aid officer approves with a single-use token.
forbid(
  principal,
  action == AgentCore::Action::"fa-core___finalize_award",
  resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/fa-financial-aid-gw"
);
