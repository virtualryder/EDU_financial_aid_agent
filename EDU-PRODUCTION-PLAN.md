# EDU Financial Aid Agent — Production-Grade Build Plan

*Living plan. Takes this agent from **Demonstrated** (32-check shell-era demo) to **customer-pilot
depth** by porting the PROVEN Housing pattern (Housing_eligibility_agent `v0.9.4` — five external
review cycles, three live clean-account validations, strict zero-PII canary PASS) and adapting it to
the financial-aid domain and its regulations. Updated every cycle. Four audiences: the university
**CIO** (SIS reality, deployability), **CISO** (FERPA/GLBA posture, evidence), **AWS SA** (IaC,
operability), **Director of Financial Aid** (scope honesty, PJ discretion).*

## 0. Positioning (adopted from the external review — verified accurate)

**Product framing:** **Financial Aid Verification & Student Communication Assistant** — FAFSA/ISIR
summarization, verification-document completeness, SAP packet preparation, aid ESTIMATION for case
preparation, Professional Judgment documentation assistance, and drafted student communications —
every consequential action human-approved. It is **NOT an awarding agent**: no award commitment, no
disbursement, no COD write-back, no autonomous Professional Judgment — ever (Cedar-forbidden).

**The one domain-semantic correction (review finding, adopted):** College Scorecard is **verified
REFERENCE data, not institutional cost of attendance.** The signature proves integrity + source
(anti-fabrication) — it does not make Scorecard averages an award-package COA. Every output that
uses it says `coa_basis: "College Scorecard reference data - institutional COA required for awards"`
and the deterministic result is an **`AID_ESTIMATE`**, never an award.

**ORIGINAL baseline (2026-07-24, at the START of this build — since REMEDIATED, kept for provenance):**
shell-era spine, 57 offline tests, 32-check live demo. Already solved even then: signed Scorecard
provenance; deterministic Pell/SAP with fail-closed NEEDS_REVIEW paths; PJ human-only
(`no_self_professional_judgment.cedar` + tool refusal + rationale requirement); mask-before forbids;
`no_self_commit`. Defects THEN (all now fixed, see below): spoofable `deidentified` boolean;
`access_token` in the `request_signoff` manifest schema; model-orchestrated workflow; shell-only
deployment; no pass-by-reference; no Gate-B posture.

**CURRENT state (2026-07-26, `v0.1.0-pilot-rc1`) — every baseline defect above is CLOSED:** signed
`sanitized_ref` replaces the spoofable boolean (P0-1); `access_token` removed from the schema +
runtime token boundary (P0-3); **deterministic Step Functions controller** with fail-closed guards
replaces model orchestration (P0-2); **AWS CDK** is the supported deployment path (P0-5), shell is
legacy/internal; **zero-PII pass-by-reference** orchestration (R3-2); **full Gate-B posture** —
private networking, `.api.data.gov`-only egress firewall, customer-managed KMS, MFA-enforced identity,
tenant pinning — **validated live in EP1** (7 stacks, strict canary PASS, 10/10 load, exactly-once
storm). Suite **190 tests**. Single authoritative count matrix: `RELEASE-MANIFEST.md`.

## 1. Regulatory frame (what a university CISO will test against)

- **FERPA** (education records; disclosure limits; annual notification) — student aid records ARE
  education records; the de-identification boundary + WORM audit are the FERPA story.
- **GLBA Safeguards Rule** (16 CFR 314) — Title IV participation makes the institution a financial
  institution for FAFSA data; FSA enforces via the audit guide. Our controls map: encryption at rest
  (CMK), access control (Cedar deny-by-default + MFA), monitoring (guard metrics), IR plan,
  qualified individual = customer-side.
- **NIST SP 800-171** — the stated FSA expectation for protecting Controlled Unclassified
  Information (FTI/FAFSA data); Gate-B posture (private networking, CMK, MFA, zero-PII telemetry)
  is the technical core of that mapping.
- **Title IV / 34 CFR 668** (verification, SAP, PJ documentation under HEA 479A) — the workflow's
  verification-hold path and PJ rationale requirement come straight from here.
- **IRS Pub 4557 / FTI handling** — FAFSA tax data never enters the model unmasked and never enters
  telemetry (strict canary is the proof).

## 2. The port (Housing v0.9.4 → EDU), phased

### EP0 — port the proven control plane (offline-proven before any deploy)

| # | Item | Source (Housing) | EDU adaptation |
|---|---|---|---|
| EP0-1 | Signed sanitized-artifact ref replaces the `deidentified` boolean | `lib/controls/sanitized.py` + tests | verbatim port; tenant = institution |
| EP0-2 | GA-2 domain-split signing keys | `provenance.py` domains | domains: `deid` + `scorecard` (IAM-split: masker can't sign reference data, lookup can't mint masking proofs) |
| EP0-3 | Token boundary — no credential in any tool schema | `lib/runtime/token_boundary.py` | port + strip `access_token` from `manifest.yaml`; scrub + out-of-band inject |
| EP0-4 | Deterministic Step Functions controller | `workflow_stack.py` + `workflow_guards.py` | pipeline: Ingest(ref) → Extract(FAFSA fields) → GuardExtracted → LookupCOA → **GuardReferenceCOA** (verifies signature; stamps reference-basis) → Mask → GuardDeidentified → AssessAid → GuardRules(`AID_ESTIMATE\|NEEDS_REVIEW\|VERIFICATION_HOLD` legal set) → **VerificationGate** (docs incomplete → `VerificationHold` terminal state — the pilot's core value path) → DraftComm → AuditIntent → HumanSignoff (SoD + content-hash) → Finalize (exactly-once) |
| EP0-5 | Pass-by-reference from day one | `case_store.py`, `ingest_case.py`, R3-2 pattern | verbatim port — FAFSA/tax content NEVER enters Step Functions state; strict canary is the acceptance bar from the first live run |
| EP0-6 | GA-5 exactly-once finalize + duplicate/replay protection | `finalize_signoff.py`, `signoff_register.py` | verbatim port |
| EP0-7 | CDK stacks (data/network/compute/workflow/identity/observability/gateway) | `cdk/` | prefix `fa-`; same Gate-B switches (`kms`, `network_mode` — egress allowlist = `.api.data.gov` only, `identity_mode`, `tenant`=institution); AgentCore gateway/Cedar as IaC with all live-run fixes inherited (AZ literals, *Authorize* family, unique provider names, orphan-engine cleanup) |
| EP0-8 | Security metrics + observability | `observability_stack.py` + guard EMF | port; add VerificationHold-backlog + PJ-pending metrics |
| EP0-9 | Harnesses + gates | `pii_canary.py`, `load_replay_test.py`, `validate_deployment.py`, `cleanup_retained.py`, `test_release_consistency.py` + `RELEASE`, release-validation OIDC workflow | prefix-parameterized ports; release gate active from the FIRST tag |
| EP0-10 | Regulatory + ops docs | THREAT-MODEL, DATA-SOURCE-POLICY, RETENTION-PROFILES, PILOT-SCOPE, KEY-MANAGEMENT, GATE-B-CHECKLIST, DEPLOYMENT-GUIDE, START-HERE | rewritten for FERPA/GLBA/800-171/34 CFR 668 (frame in §1); PILOT-SCOPE = the review's recommended pilot verbatim; DATA-SOURCE-POLICY leads with the Scorecard reference-data correction |

### EP1 — live validation (one clean-account cycle, Housing GA-4/Gate-B style)

Deploy all-switches (`fa-val1`) → happy path to `HumanSignoff` → approve → exactly-once →
**verification-hold path** (missing docs → `VerificationHold`, no determination) → strict PII canary
(zero hits everywhere incl. SFN history) → 10-way load + replay storm → teardown + sweep →
`evidence/EP1-VALIDATION.md` → tag `v0.1.0-pilot-rc1` + GitHub release with manifest.

### EP2 — GTM + docs refresh

README (supported-path banner, validated-vs-not, known-open-issues), decks + regulatory docx
regenerated with captured proof points and the assistant (not awarding-agent) naming.

**Honesty boundary (unchanged, stated everywhere):** ISIR intake (`verify_isir`), SIS
(Banner/PeopleSoft/Workday) and COD integration, institutional COA and packaging rules, state/
institutional aid, R2T4, overaward logic, and enterprise IdP federation are ADOPTER work. Until a
read-only SIS/ISIR integration exists, real-data use is shadow-mode only.

## 3. Status log

- **2026-07-24 — plan committed.** Review verified against the repo (accurate). Baseline: 57 tests.
- **2026-07-24 — CYCLE 1 DONE (EP0-1,2,3,5-partial,6): control plane ported, suite 57 → 108/108.** <!-- count-gate:historical -->

  Sanitized-artifact refs live in assess/PJ/drafter (boolean dead); GA-2 domain keys `deid` +
  `scorecard` (IAM split comes with CDK); pass-by-reference plumbing in intake/mask/drafter
  (case_store + ingest_case + notice_ref); exactly-once finalize + duplicate-register ported;
  `access_token` STRIPPED from the manifest schema and the runtime wired through token_boundary
  (scrub + out-of-band inject); Scorecard repositioned as verified REFERENCE data (`coa_basis` label
  in lookup/assess/drafter outputs); Scorecard API key Secrets Manager path (DEMO_KEY fallback —
  honest for reference data); guards adapted: `extracted` (SAI + school), `reference_coa`,
  `deidentified`, `rules_executed`, NEW `verification` (hold path); `_obs_setup.sh` P0-7 fix.
  Test matrices ported+adapted: sanitized-artifact, secrets-path (+ cross-domain forgery +
  key-version), tenancy, pass-by-reference, exactly-once, token-boundary, canary/load verdicts.
