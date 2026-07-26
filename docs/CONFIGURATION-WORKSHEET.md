# Configuration Worksheet — EDU Financial Aid Assistant

*Gate-B deliverable. This is the human-readable companion to `config/institution.config.json` (the
machine-readable single source of truth). Every institution-controlled value the assistant uses is
listed here with its owner, where it is set, its authoritative source, and an approval line the aid
office signs before go-live. `tests/test_config_schema.py` fails CI if a required value is missing,
unlabeled, or has drifted from the code constant it mirrors.*

---

## How configuration works

Two kinds of settings:

1. **Deploy-time switches** (CDK context) — infrastructure posture: `env`, `retention_profile`,
   `kms=customer-managed`, `network_mode=private`, `identity_mode=pilot`, `tenant`. Owned by IT/security,
   set on the `cdk deploy` command, documented in `DEPLOYMENT-GUIDE.md`.
2. **Award-year / policy constants** — the values below. Each has a single home in code and a mirror in
   `config/institution.config.json`; the CI drift gate proves the two agree.

No configuration value is accepted from a request body at runtime. The tenant is derived from the
verified identity and signed into artifacts at deploy time; policy constants are read from code.

## Institution-controlled values

| Value | Default (2026-27) | Owner | Where set | Authoritative source | Approved by |
|---|---|---|---|---|---|
| Pell maximum | $7,395 | Aid office | `assess_aid.py::MAX_PELL` | FSA DCL 2026-01-30 | ☐ |
| Pell minimum | $740 | Aid office | `assess_aid.py::MIN_PELL` | FSA DCL 2026-01-30 | ☐ |
| SAP GPA floor | 2.0 | Aid office | `assess_aid.py::SAP_GPA_MIN` | 34 CFR 668.34 + institution SAP policy | ☐ |
| SAP pace floor | 67% | Aid office | `assess_aid.py::SAP_PACE_MIN` | 34 CFR 668.34 + institution SAP policy | ☐ |
| Verification groups in scope | V1, V4, V5 | Aid office | `verify_documents.py` required-item sets | 34 CFR 668.56 + annual Federal Register verification notice | ☐ |
| COA basis | Reference (College Scorecard) | Aid office | `lookup_coa.py` + `coa_basis` label | ED College Scorecard (api.data.gov) | ☐ |
| Comms reading-grade target | 8.0 | Aid office | `readability.py::TARGET_GRADE` | Section 508 / plain-language policy | ☐ |
| PJ documentation checklist | circumstance, docs, rationale, signature | Aid office | `professional_judgment.py` (prepare-only) | HEA 479A / 34 CFR 668 | ☐ |
| Retention profile | (deploy choice) | IT/security | CDK `-c retention_profile=…` | Institution retention schedule + state law | ☐ |

**COA is reference data, not institutional COA.** The assistant labels every estimate accordingly; an
institution wiring its own COA/packaging is an adopter integration, out of pilot scope.

## Change procedure

Any change to a value above is a change-managed event (`docs/CHANGE-MANAGEMENT.md`): update the code
constant AND `config/institution.config.json` in the same commit (the drift gate enforces this), record
the approver in the `approved_by` field, run the suite, and deploy through a tagged release. For the
annual roll-forward specifically, follow `docs/AWARD-YEAR-UPDATE-RUNBOOK.md`.

## Sign-off

We, the financial aid office, confirm the values above reflect our institution's policy for award year
______ and authorize their use in the pilot.

Aid office (name / title / date): __________________________
IT / security (name / title / date): __________________________
