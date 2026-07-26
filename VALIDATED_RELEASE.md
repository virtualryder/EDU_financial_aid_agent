# VALIDATED_RELEASE — evidence of the release actually working

*Every release ships with this file filled in. A customer deploys an immutable tagged release with
captured evidence — never "whatever is on main." Fields marked ☐ are captured during the release's
clean-account validation run (EP1) and MUST NOT be asserted before capture.*

> **Evidence provenance:** captures are produced by this project (author-run), recorded with dates,
> commit SHAs, raw values, and teardown verification — not independent certification. Independent
> reproduction = `.github/workflows/release-validation.yml` (GitHub-OIDC, publishes under a run ID).

## Release manifest

| Field | Value |
|---|---|
| Tag | `v0.1.0-pilot-rc1` (target; cut AFTER the EP1 validation capture). Single source of truth: repo-root `RELEASE`, enforced by `tests/test_release_consistency.py` |
| Commit SHA | the commit carrying tag `v0.1.0-pilot-rc1` (`git rev-list -n1 v0.1.0-pilot-rc1`) |
| Test count at tag | **132/132** as of EP0 completion (offline + CDK assertions); re-run at tag time |
| Validation date | 2026-07-26 (EP1 clean-account run) |
| Region | us-east-1 (target) |
| Deployment configuration | CDK `--all`; EP1 target: `retention_profile=sandbox-demo kms=customer-managed network_mode=private identity_mode=pilot tenant=<institution-id>` |
| Known limitations | preliminary income screening + verification/communication assistance only (never awarding/adjudication — `PILOT-SCOPE.md`); ISIR/SIS/COD stubbed; enterprise-IdP round-trip, independent security testing, production-scale load = open |
| Evidence links | ✅ [`evidence/EP1-VALIDATION.md`](evidence/EP1-VALIDATION.md) (happy path · VerificationHold path · strict PII canary · load + replay storm · teardown sweep) |
| Security scan status | CI on push: unit+eval suite, lint; CodeQL/bandit/pip-audit+SBOM per `.github/workflows` |
| Independent reproduction | ☐ pending (author-produced EP1 capture; the OIDC workflow is the independent path) (validation account + `AWS_VALIDATION_ROLE_ARN`) |

## EP1 clean-account validation run — ✅ CAPTURED 2026-07-26

| Field | Value |
|---|---|
| Posture | 7 stacks CREATE_COMPLETE; private networking (Network Firewall ALLOWLIST = `.api.data.gov` only), customer-managed KMS, pilot identity (MFA ON/ENFORCED/0 users), pinned tenant `uni-example-state`, AgentCore gateway in ENFORCE |
| Happy path | `val1-happy-3` → SUCCEEDED end-to-end inside the private network; live College Scorecard lookup THROUGH the firewall (University of Florida, COA $22,523, provenance signed+verified as REFERENCE data); `FINAL#FA-VAL1-0003` exactly-once |
| VerificationHold | `val1-hold-1` → terminated at the VerificationHold work-queue state (selected + missing tax-transcript); no estimate drafted (34 CFR 668) |
| Load | 10/10 concurrent SUCCEEDED, one FINAL# per case |
| Replay storm | 10 concurrent identical finalize → FIRST:1, IDEMPOTENT:9 (exactly-once live) |
| PII canary | STRICT PASS — 0 hits in Logs / X-Ray / DLQs / Step Functions history |
| Defect found + fixed | 1 (guard_extracted over-required school/unitid; fixed to require only student_aid_index) |
| Teardown | all stacks deleted; RETAIN'd resources removed; CMK scheduled for deletion; residual sweep clean |

## Known boundaries at this release

Reference accelerator, not a certified system. See `PILOT-SCOPE.md` honesty boundary and
`docs/GATE-B-CHECKLIST.md` for the customer-owned governance items.
