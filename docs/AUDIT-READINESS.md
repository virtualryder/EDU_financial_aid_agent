# Audit Readiness — Control-to-Evidence Matrix

*Gate-B deliverable. This maps each regulatory obligation the assistant touches to the specific
artifact, test, or log that demonstrates the control — written so a Title IV program reviewer, a
GLBA/bank-style examiner, or an institutional auditor can follow it. Evidence to date is **author-produced
and synthetic**; independent testing and governance signatures are Gate-D items (see
`EDU-PILOT-READINESS-PLAN.md`).*

---

## Regulatory frame

FERPA (student records) · GLBA Safeguards Rule 16 CFR 314 (Title IV makes institutions financial
institutions) · NIST SP 800-171 (protecting controlled unclassified information) · Title IV / 34 CFR 668
(verification, SAP) · HEA 479A / 34 CFR 668 (Professional Judgment documentation) · IRS Pub 4557 (FAFSA-
derived federal tax information).

## Control-to-evidence matrix

| Obligation | Control in the assistant | Evidence (artifact / test / log) |
|---|---|---|
| **FERPA** — limit access to student records; account for disclosures | Cedar deny-by-default authz; identity-derived tenant; WORM audit ledger records every consequential action | `tests/test_signoff_identity.py`; Cedar policy tests; audit hash-chain `verify_chain`; `docs/THREAT-MODEL.md` T4/T6 |
| **GLBA Safeguards 16 CFR 314.4** — access controls, encryption, monitoring, IR | MFA-enforced identity; customer-managed KMS over data/secrets/logs; PII-telemetry canary + guard-failure alarms; documented IR | `evidence/EP1-VALIDATION.md` (MFA, KMS, canary PASS); `docs/INCIDENT-RESPONSE.md`; ObservabilityStack alarms |
| **GLBA — encryption in transit/at rest** | KMS CMK on tables/secrets/logs; private networking; TLS to Scorecard | EP1 stack proofs (fa-*-data CMK); `docs/Production-Network-Hardening.md` |
| **NIST 800-171 — access control, audit, config mgmt, IR** | Least-privilege IAM (exact ARNs, no prefix lookup); tamper-evident audit; CDK config-as-code; IR runbook | `tests/test_token_boundary.py::test_no_role_lookup_by_name_prefix...`; `test_audit_chain.py`; `cdk/`; `docs/INCIDENT-RESPONSE.md` |
| **Title IV verification (34 CFR 668.51–.61)** | VerificationHold terminal state; document-flag logic; groups V1/V4/V5 configurable | `tests/` verification path; `docs/SME-REVIEW-PACKET.md` §4; `config/institution.config.json` |
| **Title IV SAP (34 CFR 668.34)** | Deterministic SAP test; hold-don't-deny on failure | `assess_aid.py` SAP logic; SME packet §3 |
| **HEA 479A — Professional Judgment is human-only, documented** | Cedar `no_self_professional_judgment` + tool refusal; prepare-only; PJ checklist | `tests/test_tools.py::test_core_commit_pj_refused`, `::test_professional_judgment_requires_rationale`; THREAT-MODEL T8 |
| **Data provenance — no fabricated authority** | HMAC-signed Scorecard provenance; verify-before-use; unverified → NEEDS_REVIEW | `tests/test_provenance_gate.py`; `docs/DATA-SOURCE-POLICY.md`; `docs/KEY-MANAGEMENT.md` |
| **De-identification before model/audit** | Deterministic masking proven by signed `sanitized_ref` (boolean never accepted) | `tests/test_sanitized_artifact.py`; THREAT-MODEL T1/T2 |
| **IRS Pub 4557 (FTI)** — safeguard FAFSA-derived tax info | Masking + zero-PII pass-by-reference (raw content never in workflow state); telemetry canary | `docs/INCIDENT-RESPONSE.md` R1; R3-2 pass-by-reference; canary evidence |
| **Records retention** | Configurable retention profile + WORM Object Lock | `docs/RETENTION-PROFILES.md`; `config` `retention_profile` |
| **Change integrity** | RELEASE single-source + consistency CI gate; tagged releases; award-year + config drift gates | `tests/test_release_consistency.py`, `test_config_schema.py`, `test_award_year.py`; `docs/CHANGE-MANAGEMENT.md` |

## How to run an audit dry-run

1. Pull the latest tagged release and the `evidence/` pack. 2. For each row above, open the cited
artifact/test and confirm it demonstrates the control. 3. Walk the §13 leadership Q&A in
`EDU-PILOT-READINESS-PLAN.md` as a mock question set and capture answers with links. 4. Record gaps as
issues; the honest open items are listed in the readiness plan §15.

## What this does not yet prove

No independent audit, penetration test, or third-party assessment has been performed; all evidence is
author-produced on synthetic data. Those are Gate-D prerequisites and are tracked as such.
