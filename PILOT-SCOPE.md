# Pilot Scope — Financial Aid Verification & Student Communication Assistant

*The narrow, defensible first pilot (adopted from the external readiness review). This page is the
scope contract: anything not listed under "In scope" is out of scope, and the exclusions are
enforced by Cedar policy and tool refusals, not just by this document.*

## In scope (one institution · one award year · synthetic/retrospective first, then shadow mode)

- **FAFSA/ISIR summarization** — deterministic extraction of decision fields (SAI, enrollment
  status, SAP inputs, dependency) from intake content; PII de-identified with cryptographic proof
  before any model sees it.
- **Verification-document completeness** (34 CFR 668.51–.61) — required-vs-received checking; a
  selected or incomplete case routes to the **VerificationHold work queue**, never onward.
- **Aid ESTIMATION for case preparation** — deterministic Pell + SAP classification against
  **College Scorecard REFERENCE cost data** (`coa_basis` labeled on every output; the signature
  proves the figure came from the real API unaltered — it does NOT make it the institutional COA).
- **SAP review packet preparation** and **Professional Judgment documentation assistance** (HEA
  479A) — PJ preparation REQUIRES a documented case-specific rationale; the agent can never commit
  a PJ (Cedar `no_self_professional_judgment` + tool refusal).
- **Drafted student communications** — guarded Bedrock drafts on de-identified content only,
  returned by reference, approved by a human before any use.
- **Human approval of every consequential output** — separation of duties (approver ≠ requester),
  approval content-hash-bound, exactly-once finalization.

## Explicitly OUT of scope (enforced, not aspirational)

No award commitment · no disbursement · no COD write-back · no autonomous Professional Judgment ·
no adverse action (denial/termination) · no fraud referral · no writes to any system of record
(shadow mode reads nothing and writes nothing into the official case record) · no institutional or
state aid packaging · no R2T4 · no overaward logic.

**Not an eligibility engine:** household composition, citizenship/immigration status, SSN match,
student restrictions, assets/deductions/adjusted income, criminal-history rules, local preferences,
waiting lists, reasonable accommodation, VAWA, EIV discrepancies, hearings, recertification, and
institutional administrative-plan provisions are institution-owned and NOT implemented.

## Adopter work (stated in every customer conversation)

Validated ISIR intake · SIS (Banner/PeopleSoft/Workday Student) read integration · COD ·
institutional COA and packaging rules · enterprise IdP federation · privacy/security review and
governance signatures (docs/GATE-B-CHECKLIST.md) · FERPA/GLBA program ownership (qualified
individual, IR plan) · accessibility review of student communications.

## Pilot success gates

Zero consequential security bypasses · zero PII in telemetry (strict canary, incl. Step Functions
history) · ~100% agreement of the deterministic Pell/SAP classification on institution-approved test
cases · zero duplicate finalizations · measured (not assumed) staff-time deltas on verification and
communication drafting · documented override reasons · a written go/no-go production business case.
