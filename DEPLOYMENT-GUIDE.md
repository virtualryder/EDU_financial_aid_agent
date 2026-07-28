# Deployment Guide — CDK (the only supported customer path)

*GA-7 (Review-2). Deploys the Financial Aid Verification & Student Communication Assistant. Estimated time:
30–45 min. Estimated pilot cost: < $5/day idle + ~$0.09 per governed transaction (see
`docs/Cost-and-Latency-One-Pager.md`).*

## 1. Prerequisites
- **Account/org:** a dedicated sandbox or pilot account (one institution per account — no multi-tenancy);
  Control Tower/SCPs must allow: CloudFormation, Lambda, DynamoDB, S3 (+Object Lock), Step Functions,
  Cognito, Secrets Manager, SNS, CloudWatch, Comprehend, Bedrock (model access enabled for the
  configured Claude model), Bedrock AgentCore (for the gateway attachment).
- **Region:** any Region with Bedrock AgentCore + the chosen model (validated in us-east-1).
- **Quotas:** default quotas suffice for a pilot (≤ 13 Lambdas, 1 state machine, 4 DynamoDB tables
  — audit ledger, sanitized artifacts, case store, pending approvals — 1 bucket).
- **Tooling:** Node 18+, `npx --yes aws-cdk@2` (or `npm i -g aws-cdk`; without `--yes` npx stops at an interactive install prompt and hangs silently), Python 3.12, `pip install -r cdk/requirements.txt`.
- **Deployment role:** CloudFormation service-role pattern; least-privilege statement list in
  `cdk/README.md` (or use CDK bootstrap's deploy role). `npx --yes aws-cdk@2 bootstrap aws://<acct>/<region>` once.

## 2. Configure (environment matrix)
| Context | dev | pilot | production-reference |
|---|---|---|---|
| `-c env=` | dev | pilot | prod |
| `-c retention_profile=` | sandbox-demo | pilot | production-reference (COMPLIANCE — customer-approved schedule ONLY) |
| `-c kms=` | aws-managed | customer-managed | customer-managed |
| `-c network_mode=` | public | **private** (Gate-B B1: isolated subnets + Network Firewall egress allowlist = `.api.data.gov` only) | private |
| `-c identity_mode=` | sandbox | **pilot** (Gate-B B3: MFA REQUIRED software-token-only, threat protection ENFORCED) | pilot |
| `-c tenant=` | *(unset)* | **`<institution-id>`** (Gate-B B5: deployment-pinned tenant, HMAC-signed into every sanitized artifact) | `<institution-id>` |

Optional enterprise-OIDC federation as IaC: `-c oidc_issuer_url=… -c oidc_client_id=…
-c oidc_client_secret_arn=<SecretsManager ARN>` (the client secret enters the template only as a
CloudFormation dynamic reference). The Gate-B posture was validated live in EDU's own EP1 run (evidence/EP1-VALIDATION.md). See
[`evidence/GATE-B-VALIDATION.md`](evidence/GATE-B-VALIDATION.md).

Secrets (created by the compute stack, values operator-managed):
- `fa-<env>/provenance-signing-deid` — generated automatically; signs mask_pii sanitized-artifact refs ONLY (GA-2 trust-domain key; never plaintext anywhere).
- `fa-<env>/provenance-signing-scorecard` — generated automatically; signs College Scorecard REFERENCE-data provenance ONLY (GA-2; IAM prevents the masker reading this key and the lookup reading the deid key).
- `fa-<env>/scorecard-api-key` — OPTIONAL api.data.gov key (register free at api.data.gov); without it the lookup uses DEMO_KEY (rate-limited but functional — acceptable for reference data). Fill: `aws secretsmanager put-secret-value --secret-id fa-<env>/scorecard-api-key --secret-string "<key>"`.

Identity: the pool ships with ZERO users. Federate your IdP per `docs/IdP-Federation-Reference.md`
(Entra ID / Okta / Ping), map groups to `aid_officer`, enforce MFA at the IdP.

## 3. Deploy
```bash
git checkout v0.1.3-pilot-rc1        # always deploy a validated release tag, never main
cd cdk && pip install -r requirements.txt
npx --yes aws-cdk@2 deploy --all --require-approval never -c env=pilot -c retention_profile=pilot -c kms=customer-managed \
  -c network_mode=private -c identity_mode=pilot -c tenant=<institution-id>
```
`--all` includes EVERYTHING — the AgentCore Gateway/Cedar attachment (`fa-<env>-gateway`) deploys
as IaC with the rest; there are no post-deployment shell steps (see the stack table in
`cdk/README.md`).
Ordering notes (from the live Gate-B run): the **observability stack imports the workflow stack's
export — deploy it after workflow** (CDK orders this automatically; if driving CloudFormation
directly, sequence it yourself). The Network Firewall adds ~8–10 min to network-stack create, and
VPC-attached Lambda stacks take longer to DELETE (ENI release) — plan windows accordingly.

## 4. Validate (must PASS before any use)

> **Validating and then tearing down? Deploy with `-c retention_profile=sandbox-demo`, not `pilot`.**
> The `pilot` profile applies **90-day GOVERNANCE** Object Lock to the WORM vault — right for a real
> pilot, but on a throwaway environment it leaves locked objects you cannot clear (the audit writer is
> deliberately DENIED `s3:BypassGovernanceRetention`). `sandbox-demo` is GOVERNANCE / 1 day.

```bash
python scripts/validate_deployment.py --env pilot --region <region>
python scripts/pii_canary.py --prefix fa-<env> --execute --strict   # expect verdict: PASS, leaks: {}
```

> **Both scripts run for minutes and print NOTHING until they exit — that is not a hang.** The
> validator polls the Step Functions execution (~2–3 min); the canary waits 120s for telemetry to
> settle before sweeping (~3 min). Redirected to a file, Python buffers, so the log stays 0 bytes
> until the process finishes. Do not kill them early.

Emits the machine-readable verdict, e.g.:
```json
{"deployment_status":"PASS","release":"<tag>","stacks":"COMPLETE","secrets":"PRESENT",
 "masking_control":"PASS","guard_genuine":"PASS","forged_ref_denied":"PASS",
 "ingest_pass_by_reference":"PASS","workflow_fail_closed":"PASS",
 "coa_lookup":"CONFIGURED|NOT-CONFIGURED (fail-closed to ManualReview)"}
```
Any FAIL blocks the pilot. Attach the JSON to the deployment record. For INDEPENDENT verification,
run the GitHub-OIDC release-validation workflow (`.github/workflows/release-validation.yml`) instead
of trusting a local run.

## 5. Run a case (operator flow — pass-by-reference)

Raw applicant content never enters Step Functions state: it goes in ONCE through the ingest Lambda,
and only an opaque `case_ref` starts the workflow.

```bash
P=fa-pilot; R=us-east-1
# 1. INGEST the application (the only door for raw content; response is content-free)
aws lambda invoke --function-name $P-ingest-case --region $R \
  --cli-binary-format raw-in-base64-out \
  --payload '{"case_id":"FA-2026-0001","application":"<raw application text>"}' /tmp/ing.json
CASE_REF=$(python -c "import json;print(json.load(open('/tmp/ing.json'))['case_ref'])")

# 2. START the governed workflow with the REF (never the text)
aws stepfunctions start-execution --region $R \
  --state-machine-arn arn:aws:states:$R:<acct>:stateMachine:$P-determination-workflow \
  --name fa-2026-0001 \
  --input "{\"case_id\":\"FA-2026-0001\",\"requester\":\"<intake-operator>\",\"case_ref\":\"$CASE_REF\"}"

# 3. The pipeline pauses at HumanSignoff (~1 min). The aid officer reviews:
aws dynamodb get-item --table-name $P-pending-approvals --region $R \
  --key '{"case_id":{"S":"FA-2026-0001"}}'          # -> task_token + content_hash
#    - the DRAFT NOTICE is in the case store under the draft step's notice_ref (execution history
#      shows the ref; fetch: aws dynamodb get-item --table-name $P-case-store --key '{"case_ref":{"S":"<notice_ref>"}}')
#    - the assessment (non-PII) is in the execution history AssessRules output

# 4. A DIFFERENT person than the requester APPROVES (content_hash binds the approval to what they saw)
aws stepfunctions send-task-success --region $R --task-token "<task_token>" \
  --task-output '{"approved":true,"decision":"APPROVE","approver":"<specialist>","content_hash":"<content_hash>","case_id":"FA-2026-0001"}'

# 5. Finalize runs EXACTLY ONCE; verify the committed record + marker:
aws dynamodb get-item --table-name $P-audit-ledger --region $R \
  --key '{"audit_id":{"S":"FINAL#FA-2026-0001"}}'
```

A rejected case: send `"approved":false,"decision":"REJECT"` — nothing commits. A case the guards
refuse (unverifiable reference COA, unproven masking) never reaches the gate: it ends in `ManualReview`
for ordinary human processing. Synthetic test cases with expected results: `data/synthetic/`.

## 6. Operate
Subscribe ops to the `fa-<env>-ops-alarms` SNS topic; dashboard `fa-<env>-operations`. Runbooks:
`docs/THREAT-MODEL.md` (security events), `docs/DATA-SOURCE-POLICY.md` (Scorecard outage → NEEDS_REVIEW),
`docs/RETENTION-PROFILES.md` (retention/break-glass).

## 7. Upgrade / rollback / uninstall
- **Upgrade:** deploy a NEW tagged release via `npx --yes aws-cdk@2 deploy` (change-sets are
  reviewable); never patch in place.
- **Rollback:** redeploy the previous tag (stateless compute; data stacks are additive).
- **Uninstall — `cdk destroy` alone does NOT reach zero residual.** Verified on `fa-val2`, 2026-07-28:

  **1. Stop executions parked at the human sign-off gate first** — a RUNNING execution blocks
  state-machine deletion and the destroy stalls:

  ```bash
  E=pilot; SM=$(aws stepfunctions list-state-machines \
    --query "stateMachines[?contains(name,'fa-$E')].stateMachineArn" --output text)
  aws stepfunctions list-executions --state-machine-arn "$SM" --status-filter RUNNING \
    --query 'executions[].executionArn' --output text | tr '\t' '\n' \
    | xargs -r -n1 -I{} aws stepfunctions stop-execution --execution-arn {} --cause teardown
  ```

  **2. Destroy**, then delete the RETAIN'd audit table + WORM vault **only per the customer's
  records-disposition procedure**:

  ```bash
  npx --yes aws-cdk@2 destroy --all --force -c env=$E -c retention_profile=sandbox-demo
  ```

  **3. Clear what `destroy` deliberately leaves** (validation environments only — on a real pilot the
  ledger and vault ARE the evidence you keep). Leftover log groups also **block a future redeploy that
  reuses the same `-c env=` value**:

  ```bash
  aws dynamodb    delete-table     --table-name fa-$E-audit-ledger
  aws cognito-idp delete-user-pool --user-pool-id "$(aws cognito-idp list-user-pools --max-results 50 \
                     --query "UserPools[?contains(Name,'fa-$E')].Id" --output text)"
  aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/fa-$E" \
    --query 'logGroups[].logGroupName' --output text | tr '\t' '\n' \
    | xargs -r -n1 -I{} aws logs delete-log-group --log-group-name {}
  aws s3api       delete-bucket    --bucket "$(aws s3api list-buckets \
                     --query "Buckets[?contains(Name,'fa-$E-data-wormvault')].Name" --output text)"
  ```

  **4. Sweep every resource type, not just stacks** — an empty `describe-stacks` is **not** proof of
  zero residual:

  ```bash
  python scripts/validate_deployment.py --env $E --expect-absent   # residual_stacks: []
  for q in "cloudformation list-stacks" "lambda list-functions" "dynamodb list-tables" \
           "s3api list-buckets" "logs describe-log-groups"; do aws $q | grep -c "fa-$E"; done   # all 0
  ```

## 8. Troubleshooting
| Symptom | Cause / fix |
|---|---|
| Execution → ManualReview at GuardAuthoritative | Scorecard key missing/invalid (by design, fail-closed) — fill the secret |
| assess refuses "de-identification not proven" | caller skipped mask_pii or forged the ref (by design) |
| register raises "duplicate submission" | a PENDING approval already exists for the case (by design) |
| finalize returns idempotent:true | case already finalized — original submission returned (by design) |
| Stack delete leaves table/bucket | RETAIN by design — records disposition is a human decision |

**Known limitations:** verification + estimation + communication assistance only (see `PILOT-SCOPE.md`); SIS/ISIR/COD integration is adopter work;
AgentCore attachment steps in `cdk/README.md`; enterprise IdP is engagement work.
**Support:** pilot operated by the deploying SA/partner; escalation owner named in the pilot SOW
(`CONFIG-WORKSHEET.md` §ownership).
