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
| Commit SHA | ☐ (the commit carrying the tag) |
| Test count at tag | **132/132** as of EP0 completion (offline + CDK assertions); re-run at tag time |
| Validation date | ☐ EP1 |
| Region | us-east-1 (target) |
| Deployment configuration | CDK `--all`; EP1 target: `retention_profile=sandbox-demo kms=customer-managed network_mode=private identity_mode=pilot tenant=<institution-id>` |
| Known limitations | preliminary income screening + verification/communication assistance only (never awarding/adjudication — `PILOT-SCOPE.md`); ISIR/SIS/COD stubbed; enterprise-IdP round-trip, independent security testing, production-scale load = open |
| Evidence links | ☐ `evidence/EP1-VALIDATION.md` (happy path · VerificationHold path · strict PII canary · load + replay storm · teardown sweep) |
| Security scan status | CI on push: unit+eval suite, lint; CodeQL/bandit/pip-audit+SBOM per `.github/workflows` |
| Independent reproduction | ☐ pending (validation account + `AWS_VALIDATION_ROLE_ARN`) |

## EP1 clean-account validation run — ☐ NOT YET CAPTURED

Planned captures (per `EDU-PRODUCTION-PLAN.md` EP1): full ref-based pipeline SUCCEEDED live inside
the Gate-B posture · `FINAL#<case>` exactly-once · VerificationHold path (incomplete docs → work
queue, no estimate proceeds) · strict canary PASS (0 marker hits in Logs/X-Ray/DLQs AND Step
Functions history) · 10-way load all-legal-terminal · replay storm `FIRST:1` · residual sweep clean.

## Known boundaries at this release

Reference accelerator, not a certified system. See `PILOT-SCOPE.md` honesty boundary and
`docs/GATE-B-CHECKLIST.md` for the customer-owned governance items.
