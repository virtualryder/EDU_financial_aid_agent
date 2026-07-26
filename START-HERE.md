# START HERE — Financial Aid Verification & Student Communication Assistant

*One page. What this is, what's proven, how to evaluate it, and what a pilot looks like. Target
validated release: **[`v0.1.0-pilot-rc1`](https://github.com/virtualryder/EDU_financial_aid_agent/releases/tag/v0.1.0-pilot-rc1)** (cut after the EP1 live validation; deploy tags, never
`main`). Supported deployment path: **AWS CDK** (`cdk/`); the shell engine is legacy/internal.*

## What this is (and is not)

A **governed AI accelerator** for the financial-aid office: FAFSA summarization, verification-
document completeness (with a real **VerificationHold work queue** per 34 CFR 668), deterministic
Pell/SAP **estimation** on verified College Scorecard **reference** data, Professional Judgment
documentation assistance, and guarded draft student communications — every consequential action
human-approved, exactly once, with a tamper-evident audit trail.

It is **NOT an awarding agent**: no award commitment, disbursement, COD write-back, autonomous PJ,
or adverse action — Cedar-forbidden, tool-refused, and human-gated ([`PILOT-SCOPE.md`](PILOT-SCOPE.md)).
Scorecard figures are reference data, never institutional COA
([`docs/DATA-SOURCE-POLICY.md`](docs/DATA-SOURCE-POLICY.md)).

## Evidence provenance — read this honestly

The control plane is a PORT of the Housing pattern (github.com/virtualryder/Housing_eligibility_agent
`v0.9.4`), which carries five external review cycles and three live clean-account validations
including a strict zero-PII telemetry canary. **EDU's own live validation (EP1) has not run yet** —
current proof is the offline suite (132 tests incl. full CDK assertions). Nothing on this page
claims live evidence EDU hasn't captured.

## Reading order by role

| You are | Read, in order |
|---|---|
| **Solution Architect** | [`DEPLOYMENT-GUIDE.md`](DEPLOYMENT-GUIDE.md) → [`cdk/README.md`](cdk/README.md) → [`EDU-PRODUCTION-PLAN.md`](EDU-PRODUCTION-PLAN.md) |
| **CISO / security** | [`docs/THREAT-MODEL.md`](docs/THREAT-MODEL.md) → [`docs/GATE-B-CHECKLIST.md`](docs/GATE-B-CHECKLIST.md) → [`docs/KEY-MANAGEMENT.md`](docs/KEY-MANAGEMENT.md) → [`docs/DATA-SOURCE-POLICY.md`](docs/DATA-SOURCE-POLICY.md) |
| **CIO / VP Enrollment / FA Director** | [`PILOT-SCOPE.md`](PILOT-SCOPE.md) → README §controls → the pilot offer below |
| **Auditor / compliance** | [`VALIDATED_RELEASE.md`](VALIDATED_RELEASE.md) → `docs/Financial-Aid-AgentCore-Regulatory-Adherence.docx` → [`docs/RETENTION-PROFILES.md`](docs/RETENTION-PROFILES.md) |

**Regulatory frame:** FERPA (education records) · GLBA Safeguards Rule (Title IV → the institution
is a financial institution for FAFSA data) · NIST SP 800-171 (FSA expectation for FAFSA/FTI data)
· 34 CFR 668 (verification, SAP) · HEA 479A (PJ documentation). Mapping: `EDU-PRODUCTION-PLAN.md` §1.

## The pilot offer

**Scope:** one institution · one award year · synthetic/retrospective cases first, then shadow mode
· read-only everything · every output human-approved. Phases mirror the Housing engagement:
workshop (~1 wk) → deploy + validate (~1 wk; machine verdict + strict canary) → scoped pilot
(4–6 wks; measured metrics: verification handling time, draft edit rate, Pell/SAP agreement,
hold-queue throughput, overrides + reasons) → production scoping (SIS/ISIR integration, identity,
institutional COA/rules, authorization). **Customer provides:** AWS account, IdP admin, FA
director + 2–3 officers for reviews, privacy/security participation, retrospective de-identified
cases for shadow phase. SIS/COD integration is EXCLUDED from the pilot and is the dominant
production cost.

## Status in one line

EP0 (control-plane + CDK port of the proven pattern): **complete, 132/132 tests.** Next: EP1 live
clean-account validation (all Gate-B switches, strict canary, VerificationHold path) → tag
`v0.1.0-pilot-rc1` with captured evidence → GTM refresh (EP2). Adopter work and governance
signatures: [`docs/GATE-B-CHECKLIST.md`](docs/GATE-B-CHECKLIST.md).
