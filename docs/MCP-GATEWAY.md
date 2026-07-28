# MCP Secure Gateway & Portability

*Gate-B deliverable (readiness plan §13). How the assistant's tools are exposed to the agent through a
secured MCP gateway, how auth works, and what stays portable if you run off Amazon Bedrock AgentCore.*

---

## Why a gateway at all

The agent never calls a tool Lambda directly. Every governed tool (intake, lookup, assess, verify,
professional-judgment prepare, draft, sign-off) is exposed as an **MCP target** behind a gateway that
authenticates the caller, authorizes the specific action with Cedar, and invokes only the exact tool
Lambda by ARN. This is the choke point where "which identity may call which tool on which resource" is
decided — deny-by-default, forbid-wins.

## How it is built (as IaC)

`cdk/fa_stacks/gateway_stack.py` provisions the AgentCore/Gateway/Cedar attachment as CloudFormation via
a custom-resource provider (`cdk/gateway_provider/handler.py`), running the proven sequence and reversing
it on stack delete:

1. **Policy engine** created first (Cedar). 2. **MCP gateway** created with **CUSTOM_JWT** authorization
bound to the identity pool. 3. **SSM discovery param** published. 4. **One target per governed tool
Lambda**, wired by **exact ARN, never by name** (P0-7). 5. **Every Cedar policy** loaded with the gateway
ARN injected into the forbids. 6. Gateway flipped to **ENFORCE**.

Targets are generated **at synth from the tool manifest** (the single source of truth), so the gateway's
advertised tool schemas can never drift from the tools the agent actually ships. The gateway execution
role is scoped to invoke **only** the governed tool Lambdas; the provider's own IAM is scoped to the
AgentCore control plane, the one SSM param, and PassRole of the one gateway role.

## Auth model

- **Caller → gateway:** CUSTOM_JWT. The agent presents a JWT from the pilot identity pool
  (MFA-enforced Cognito; enterprise IdP federation is the Gate-D round-trip). The gateway validates it
  before any tool is reachable.
- **Gateway → tool:** the gateway assumes its scoped role and invokes the exact tool Lambda ARN.
- **Authorization:** Cedar evaluates the action against deny-by-default policies — `aid_officer` permit,
  `mask_before_{assess,pj,draft}`, `no_self_commit` (finalize_award), `no_self_professional_judgment`.
  A new tool with no explicit permit is denied (proved by the Cedar "new-tool-fails-CI" gate).
- **Token hygiene:** no bearer token appears in any tool schema or telemetry; credential-shaped args are
  scrubbed; the runtime injects the sign-off token out-of-band (P0-3, `test_token_boundary.py`).

The end-to-end MCP auth pattern (token-exchange, IdP federation, least-privilege intersection) is the
same one proven in the portfolio's MCP auth demo; EDU applies it to the financial-aid tool set.

## Portability — AgentCore vs. portable

The **governance is not AgentCore-specific.** The load-bearing controls — deterministic masking + signed
`sanitized_ref`, HMAC-signed provenance, the deterministic Step Functions controller with fail-closed
guards, the human sign-off gate, the WORM audit ledger — run as plain Lambdas and shared Python modules
and are exercised fully offline by the test suite (153 tests, no AgentCore needed).

AgentCore/Gateway/Cedar provides the **managed MCP gateway + policy enforcement plane**. If an institution
cannot use AgentCore, the same tools can sit behind an alternative MCP gateway (or an API Gateway +
Lambda authorizer) enforcing the same Cedar policies; the tool contracts and the governance controls are
unchanged. What you would re-implement is the gateway wiring in `gateway_stack.py`, not the agent or its
guarantees. See the portfolio `GATEWAY-MODES` guidance for the AgentCore-vs-portable decision.

## What an evaluator should check

The gateway is ENFORCE (not permissive), targets resolve to exact ARNs, the gateway role can invoke only
the tool Lambdas, every Cedar forbid carries the gateway ARN, and a hypothetical new tool is denied by
default. These are asserted in the CDK stack tests and the Cedar policy tests.
