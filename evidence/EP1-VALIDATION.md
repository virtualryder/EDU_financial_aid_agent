> ## Re-validation — `fa-val2`, 2026-07-28 (supersedes the EP1 run below)
>
> `DEPLOYMENT-GUIDE.md` was walked end to end as a Solution Architect would, on a clean account.
> **It found two blocking defects. Both are fixed and the re-run passes.**
>
> ### Defect 1 — the repo could not be deployed at all (P0)
> `cdk/cdk.json` carried `@aws-cdk/core:enableStackNameDuplicates`, a CDK **v1** feature flag REMOVED
> in v2. On the pinned CDK the CLI aborts:
> `RuntimeError: Unsupported feature flag ... has been removed in CDKv2`. **`cdk synth` and
> `cdk deploy` both failed**, so the documented path was impossible to follow.
> *Why the suite missed it:* `Template.from_stack()` builds constructs in-process and **never reads
> `cdk.json`** — only the CLI does. All 152 tests passed while the shipped artifact was undeployable. <!-- count-gate:historical -->
> Fixed; `tests/test_cdk_context_flags.py` now gates it (and is in all four sibling repos).
>
> ### Defect 2 — the documented execution input crashed the controller (P0)
> `LookupCOA` read `$.school` / `$.unitid` straight off execution state, but the documented contract
> is `{case_id, requester, case_ref}` (§2). Every execution started with the guide's own command died:
> `The JSONPath '$.school' ... could not be found in the input` — a **hard failure, not a fail-closed
> outcome**: no ManualReview, no audit intent, the governed pipeline simply crashed.
> **Two more states had the identical bug**, masked because LookupCOA crashed first: `AssessAid`
> (`$.selected_for_verification`) and `VerifyDocuments` (`$.required_documents`,
> `$.received_documents`). A `SeedInstitution` Pass state now defaults all of them —
> `selected_for_verification` defaults **TRUE** so a missing value routes through 34 CFR 668
> verification rather than skipping it (defaulting false would fail OPEN).
> Gated by `tests/test_workflow_input_contract.py`.
>
> ### Re-run result — all gates PASS
>
> | Check | Result |
> |---|---|
> | 7/7 CDK stacks | `CREATE_COMPLETE`, **1073s (~18 min)** |
> | `validate_deployment.py --env val2` | **PASS** (`masking_control`, `guard_genuine`, `forged_ref_denied`, `ingest_pass_by_reference`, `workflow_fail_closed`) |
> | Controller terminal | `Extract → GuardExtracted → ExtractedOk → SeedInstitution → LookupCOA → GuardReferenceCOA → ReferenceCoaOk → **ManualReview**` — no institution identifier ⇒ unsigned lookup ⇒ guard fails ⇒ **fail CLOSED**, now reachable instead of crashing |
> | Strict PII canary | **PASS**, `leaks: {}` |
> | Identity | MFA `ON`, **0 users**, admin-create-only |
> | Egress | 1 Network Firewall (College Scorecard allowlist) · 11 VPC endpoints |
>
> Offline suite **157 tests at the time of this run** (156 + 1 CI-only gate). Account IDs redacted to `111122223333`.
> Torn down with a full residual sweep.

---

# EP1 validation run — ALL SWITCHES ON ✅ (2026-07-26, us-east-1, account redacted `111122223333`)

*First clean-account live validation of the EDU financial-aid agent, exercising the full Gate-B
posture ported from Housing v0.9.4 + the EDU-specific VerificationHold path. Deploy context:
`-c env=val1 retention_profile=sandbox-demo kms=customer-managed network_mode=private
identity_mode=pilot tenant=uni-example-state`.*

> **Provenance of this evidence.** This is **author-produced** validation: the builder deployed to a
> clean AWS account, exercised the pipeline, and captured the results below. It has **not** been
> independently audited, penetration-tested, or reviewed by a third-party assessor, and it uses
> **synthetic** data only — no real student records (FERPA/PII) were processed. Independent security
> testing and a real-data shadow run are tracked as pre-production gates in `EDU-PILOT-READINESS-PLAN.md`.

## Deployment — 7 stacks, CDK-synthesized templates via CloudFormation

| Stack | Status | Proof carried |
|---|---|---|
| fa-val1-data | ✅ CREATE_COMPLETE | CMK (rotation on) over tables + WORM vault + case store |
| fa-val1-network | ✅ CREATE_COMPLETE | VPC 2-AZ; Network Firewall **ALLOWLIST = `.api.data.gov` ONLY**; 9 endpoints; per-AZ firewall routes |
| fa-val1-identity | ✅ CREATE_COMPLETE | pilot posture (below) |
| fa-val1-compute | ✅ CREATE_COMPLETE | governed tool Lambdas in ISOLATED subnets; GA-2 split keys `deid`+`scorecard`; CMK env+logs; `TENANT_ID=uni-example-state` |
| fa-val1-workflow | ✅ CREATE_COMPLETE | deterministic controller incl. VerifyDocuments + VerificationHold |
| fa-val1-observability | ✅ CREATE_COMPLETE | CMK-encrypted SNS ops topic + guard-failure security metrics |
| fa-val1-gateway | ✅ CREATE_COMPLETE | AgentCore attachment: `Enforcement=ENFORCE`, GatewayUrl `…fa-val1-aid-gw…/mcp`, PolicyEngineId `fa_val1_aid_authz-ljs667z8tb`, 9 targets + 6 Cedar policies |

## B1 — locked egress, captured live

`describe-rule-group fa-val1-egress-allowlist`:
```
GeneratedRulesType: ALLOWLIST
Targets:            [".api.data.gov"]
TargetTypes:        [TLS_SNI, HTTP_HOST]
```
The governed Lambdas have NO direct internet path; the live College Scorecard lookup below succeeded
**through** this firewall — the single sanctioned external destination works, and only it is
permitted.

## B3 — pilot identity, captured live (`describe-user-pool us-east-1_d3QF0ei4Q`)

```
MfaConfiguration:         ON          (REQUIRED)
AdvancedSecurityMode:     ENFORCED    (Cognito threat protection)
AllowAdminCreateUserOnly: true        (no self-signup)
EstimatedNumberOfUsers:   0           (zero users shipped by IaC)
```

## Happy path through the FULL Gate-B posture — `val1-happy-3` → **SUCCEEDED**

Visited exactly: `Extract → GuardExtracted → LookupCOA → GuardReferenceCOA → MaskPii →
GuardDeidentified → AssessAid → GuardRulesExecuted → VerifyDocuments → GuardVerification →
VerificationClear → DraftNotice → AuditIntent → HumanSignoff (paused) → approve → Finalize →
Committed`. Reached the human gate inside the private network; exactly-once
`FINAL#FA-VAL1-0003` marker after approval.

- **LIVE College Scorecard lookup** (real api.data.gov call THROUGH the firewall): University of
  Florida, COA $22,523, provenance HMAC-signed with the `scorecard` domain key and verified by
  GuardReferenceCOA — stamped as REFERENCE data (estimate basis; institutional COA still required
  for awards).
- **Real Comprehend masking** → sanitized_ref minted with the Secrets Manager `deid` key.
- **B5 tenant proof (live):** the sanitized artifact carries `tenant: uni-example-state` — the
  deployment-pinned tenant, HMAC-signed into the ref; approval bound to `content_hash ded1ed65…`.
- **GA-2 (live):** two separate Secrets Manager keys (`fa-val1/provenance-signing-{deid,scorecard}`),
  IAM-split.

## VerificationHold path — `val1-hold-1` → **SUCCEEDED to the work queue**

A case selected for verification with a missing tax transcript
(`received=[verification-worksheet]`, `required=[tax-transcript, verification-worksheet]`) visited
`… → VerifyDocuments → GuardVerification → VerificationClear → VerificationHold` and TERMINATED at
the **VerificationHold work-queue state** — NO estimate drafted, no determination committed (34 CFR
668.51-.61). This is the pilot's core value path, proven live.

## B6 — load + replay storm, captured live

- **Load:** 10 concurrent executions → **10/10 SUCCEEDED**, one `FINAL#` marker each.
- **Replay storm:** 10 concurrent identical finalize replays on `FA-VAL1-STORM` →
  **`FIRST: 1, IDEMPOTENT: 9`** — exactly one commit, one `FINAL#FA-VAL1-STORM` marker; every
  replay returned the ORIGINAL submission (GA-5 exactly-once confirmed live under race). Ledger
  total: 11 FINAL markers, one per case.

## B4 — PII telemetry-leak canary, captured live (`scripts/pii_canary.py --strict`)

Marker `CANARY-C1BE57C577E6-TELEMETRYPROBE` (name + SSN-shaped + address) ran through the pipeline;
strict sweep verdict:
```
verdict: PASS    leaks: {}    <- CloudWatch Logs 0 · X-Ray 0 · DLQs 0 · Step Functions history 0
```
Zero FAFSA/PII content in ANY telemetry destination including Step Functions execution history — the
pass-by-reference orchestration holds on live financial-aid data from the first run (the FERPA/GLBA/
IRS Pub 4557 telemetry story).

## Live-run finding (found → fixed → committed, this run)

1. **`guard_extracted` over-required a school/unitid in the EXTRACTED fields** — FAFSA free-text
   yields the Student Aid Index but the school identifier comes from the SIS/execution input, so a
   valid case fail-closed to ManualReview. Fixed: the guard requires only `student_aid_index`; the
   reference-COA lookup uses the input-supplied unitid. (Also surfaced the correct fail-closed
   behavior — a fake unitid genuinely routes to ManualReview, no estimate on unverifiable data.)

## Teardown

All 7 stacks deleted (reverse order). The `fa-val1-compute` (VPC-attached Lambdas) delete took ~30
min on the final `ingest-case` Hyperplane-ENI release — a known AWS-managed window, not a code
issue. RETAIN'd resources removed (audit ledger, WORM vault, identity pool; secrets removed with the
data stack); the customer-managed CMK was RETAIN'd by policy (its alias deletes with the stack) so it
was found by tag (`env=val1`) and **scheduled for deletion (7-day KMS minimum)**; bootstrap `faval1/`
artifacts removed. **Final residual sweep: 0 stacks, 0 Lambdas, 0 tables, 0 state machines, 0 pools,
0 VPCs/firewalls, 0 gateways, 0 `fa_val1` policy engines.** The staging Scorecard key used DEMO_KEY
(no real secret staged).
