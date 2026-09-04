# Phase 111 — consolidated post-SaaS validation gate on the financial-aid (EDU) pack at governed-core **1.9.0** (2026-09-04) — **PASS**

**What this is.** ONE from-zero multi-tenant deployment of the EDU financial-aid pack after its re-pin from
governed-core 1.5.0 to **1.9.0** (GAP-1 of the 2026-09-03 platform review): env `fa-mt` — 8 CDK stacks
(`-c env=mt -c retention_profile=sandbox-demo -c tenants=sp-a,sp-b -c model_logging=1 -c budget_usd=5`),
two tenants `sp-a` / `sp-b`, Bedrock model-invocation logging on, the AgentCore Runtime
(`financial_aid_runtime_agent`, Strands, `MULTITENANT=1`) launched from the toolkit — on which the three
111 proofs ran back to back, followed by the kill-switch gate, the budget gate and an end-to-end regression
sweep for unexpected errors; then torn down. Product tree: the offline port (governed-core 1.9.0 parity with
benefits) plus the fixes listed under *Run history* below, to be tagged `v0.3.0-pilot-rc1`. The proofs are
the benefits pack's harnesses ported to the EDU workflow's shape (Extract → GuardExtracted →
SelectedProvided → HasInstitution → LookupCOA → GuardReferenceCOA → MaskPii → AssessAid → VerifyDocuments →
GuardVerification → DraftNotice → AuditIntent → **HumanSignoff** → Finalize → Committed; `aid_officer`
reviewer group; `/fa-mt-aid/` SSM root; College Scorecard as the authoritative COA reference source).

All account ids redacted to `111122223333`.

## Verdict (final run, image `financial_aid_runtime_agent:20260904-183415`)

| gate step | result | detail |
|---|---|---|
| 1. Isolation + per-tenant audit routing (`scripts/mt_two_tenant_proof.py`) | **PASS 12/12** in 104 s | cw-a / cw-b allowed (9 tools listed, `mask_pii` executed) and routed only to their own sanitized store, ledger and WORM vault (base 0 writes); cw-none 0 tools + 403; `ingest_case` refuses without a verified token; the workflow hop with the signed pair reached `HumanSignoff` writing INTENT evidence + a pending approval to sp-a only; the same execution without the pair FAILED at `Extract` |
| 2. Full transparency through the real AgentCore Runtime (`scripts/obs_two_tenant_proof.py`) | **PASS 13/13 per tenant** in 278 s | sp-a: 1 agent / 18 model / 22 tool spans, 12 Lambda `aegis.call` lines, 9 model invocations (all tenant-tagged, joined to spans, masked-before-model True), 1 WORM record; sp-b: 1 / 12 / 14 spans, 8 Lambda calls, 6 model invocations (all tenant-tagged, masked True), 1 WORM record; other tenant's ledger empty for both; 0 cross-tenant WORM rows |
| 3. Strict PII telemetry canary, workflow path (`scripts/pii_canary.py --strict`) | **PASS** in 164 s | synthetic marker: 0 hits in CloudWatch Logs (all `/aws/lambda/fa-mt-*` + the gateway request log + `/aws/states/fa-mt-determination-workflow`), X-Ray, DLQs and Step Functions history; the model-invocation log is swept and reported (not gated) — the model-path control is `masked_before_model` in `trace_case`, True for every model invocation of every run |
| 4. Kill switch on the AgentCore path (`scripts/kill_switch_proof.py`) | **PASS 29/29**, time-to-effect 4.2 s | IAM SoD (engage/disengage split), actor from the verified IAM principal not the body, WORM-audited engage, interceptor 403 on list+call, tool-Lambda direct refuse, workflow FAILED at `Extract`, fresh runtime invocation refused, **in-flight runtime session stopped mid-session**, second-identity release, code-SoD same-identity refused; record `AGENTCORE-KILL-SWITCH-2026-09-04.md` |
| 5. Per-tenant token + USD budget (`scripts/budget_proof.py`) | **PASS 24/24** | meter == model-invocation log (tokens_in/out, USD against the pinned price table); tenant B capped → gateway 403 + runtime refused + the workflow drafter (`draft_award_notice`) fail-closed to `ManualReview` with a DENIED ledger row; tenant A mid-session **stopped by the reservation that would breach**; per-tenant 60/85/100 % alarms; AWS Budgets USD ceiling wired; record `AGENTCORE-BUDGET-2026-09-04.md` |
| 6. End-to-end regression sweep (`scripts/e2e_regression.py`) | **PASS — 0 unexpected** | window scoped to the fixed-image run; every `/aws/lambda/fa-mt-*` group, the controller, the gateway vended log and the runtime log swept for ERROR / Traceback / timeout / exception shapes; 26 warnings, all the deliberate governed-refusal envelopes (the containment MCP-session teardown, the gateway/strands tool-isError envelopes); every execution's terminal state explained; DLQs empty; no alarm in ALARM except the deliberate budget 60/85 alarms. Record `AGENTCORE-111-GATE-2026-09-04-regression.json` |

Raw records: `AGENTCORE-111-GATE-2026-09-04.json` (the gate driver: commands, exit codes, seconds, git state),
`AGENTCORE-111-GATE-2026-09-04-sp-a.md` / `-sp-b.md` (the per-tenant correlated timelines from `trace_case`),
`-mt.json`, `-obs.json`.

## Run history — what the gate found (all product/harness defects the port had left latent)

| Area | Result | What it found and the fix |
|---|---|---|
| Runtime environment | stale `fa-financial` deploy | The runtime was launched against a stale spine-state, so its `GATEWAY_URL`, `GATEWAY_SSM_PARAM`, `KILL_SWITCH_PARAMS` and `BUDGET_TABLE` all pointed at the single-tenant `fa-financial` demo (gateway 404, obs 500s). Fixed the spine-state to the `fa-mt` gateway + `/fa-mt-aid/gateway-url`; every derived env now resolves to `fa-mt`. |
| Runtime exec role | no SSM/budget grant | `fa-obs.ps1` never exported `RUNTIME_EXEC_ROLE`, so `_obs_setup.sh` fail-closed and skipped the grant — the role could not read the kill-switch / gateway SSM params or write the budget meter. Fixed the launcher to pass the exact role; the `agent-runtime-ssm` inline policy now covers `/fa-mt-aid/*`, `fa-mt-budgets` and the `Aegis/Budget` metric namespace. |
| Runtime agent | not at 1.9.0 parity | `lib/runtime/agent.py` was still the pre-1.9.0 generic agent (no session-tenant binding, no per-call budget reserve/commit, no runtime kill-switch, no `requestMetadata` tenant tagging → model invocations untagged). Ported the full benefits 1.9.0 runtime, keeping EDU's `token_boundary` credential boundary (P0-3). New unit tests `tests/test_runtime_kill_switch.py` (offline suite 174 → 190). |
| Workflow | could never reach sign-off | Both seed states hard-coded `selected_for_verification = True`, so `assess_aid` set `VERIFICATION_HOLD` and `GuardVerification` routed **every** case to the hold queue — no case could reach `HumanSignoff`. Made `selected_for_verification` a caller input (from the ISIR/CPS), normalized by a `SelectedProvided` choice that defaults TRUE when absent (the stricter 34 CFR 668 path). |
| Runtime containment | MCP teardown masked the stop | When the kill-switch stopped the in-flight session, the AgentCore MCP client's teardown raised `RuntimeError: Connection to the MCP server was closed`, which masked the governed mid-session refusal → a 500 instead of a clean stop. `invoke()` now captures the outcome and never lets a teardown artifact overwrite a decided governance outcome; 3 regression tests added. |
| External reference source | Scorecard rate-limit | `lookup_coa` hit a College Scorecard `DEMO_KEY` rate-limit (403/429) exhausted by earlier runs — the documented source-down path (fail-closed to `ManualReview`). The limit reset; a single COA lookup per run is well within `DEMO_KEY` limits. For a pilot, provision a free api.data.gov key in the `SCORECARD_API_KEY` secret. |
| Harness | proof calibration | The budget/mid-session proofs pre-ingest the case and drive the full tool workflow (a data-cautious Sonnet otherwise asks for the raw FAFSA and makes one model call); the kill-switch in-flight workload was lengthened to 24 tool calls so containment reliably takes effect while the agent is still running; the drafter-denial check was corrected to EDU's `draft_award_notice` actor name; the e2e sweep classifies the containment MCP-teardown envelopes. |

## Teardown

Runtime `financial_aid_runtime_agent-*` deleted; `cdk destroy --all` for `mt` (all 8 stacks); retained
ledgers / vaults swept by `scripts/cleanup_retained.py --prefix fa-mt`; the pre-created CodeBuild / Runtime
roles and the ECR repo removed; the account's previous model-invocation logging configuration re-applied and
verified. Residual by design: none (sandbox-demo retention profile).
