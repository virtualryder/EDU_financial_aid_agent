# EDU Financial Aid Assistant — Pilot Readiness Plan

**Product:** Financial Aid Verification & Student Communication **Assistant** (never an awarding /
adjudication agent — it prepares work for aid officers; humans commit every consequential action).
**Repo:** `github.com/virtualryder/EDU_financial_aid_agent` · **Release:** `v0.1.0-pilot-rc1` ·
**Build state:** EP0 (control-plane port) + EP1 (author-produced clean-account live validation) complete;
suite **190 tests**. **Owner:** David Ryder (AWS HCLS SA). **Last updated:** 2026-07-26.

---

## 0. How to read this plan

An external reviewer assessed the agent and named a set of shortfalls across the **operating model**
(configuration, SME validation, training, change management, accessibility, support, model/prompt
maintenance, annual award-year updates, incident response, audit preparation), asked for a **pilot
metrics** framework, listed the **AWS leadership pushback** questions to expect, and defined **staged
required-work** before each promotion. This document answers all of them and is the single place the
work is tracked. Each section states *what exists today*, *the gap*, and *the action* with a priority.

**Priority key.** **P0** = blocks sharing internally at AWS. **P1** = blocks a synthetic-data pilot.
**P2** = blocks a real-data shadow pilot. **P3** = blocks production. Items are additive: a P2 gate
assumes all P0/P1 items are closed.

**Honesty guardrails carried into every claim below.**
- The agent is an **assistant**: it prepares verification worklists, aid **estimates**, and draft
  student communications. It never awards, disburses, writes back to COD, or commits Professional
  Judgment. Those are Cedar-forbidden and human-gated.
- **College Scorecard is verified REFERENCE data**, labeled `coa_basis` — never the institutional
  cost of attendance. Every downstream output is an **estimate** and says so.
- **Evidence is author-produced** and synthetic-only until an institution runs it on real data in
  shadow mode. We do not present author-produced results as independent assurance.
- **We do not promise a productivity percentage.** No efficiency claim (e.g. "cuts verification time
  X%") is made until it is measured in a customer environment. The metrics in §12 are the instrument
  for producing that number honestly, not a substitute for it.

---

## 1. Doc-integrity fixes (P0 — done this cycle)

The reviewer required these before any internal share; all are now closed:

| Defect | Fix | Status |
|---|---|---|
| START-HERE said EP1 hadn't run | Updated to "EP1 captured 2026-07-26"; test count 137 | ✅ |
| Threat model titled/rowed for Housing | Title → Financial Aid; **T8** rewritten from Housing fraud-referral to the EDU **autonomous-Professional-Judgment** threat (`no_self_professional_judgment` + `test_core_commit_pj_refused`) | ✅ |
| HUD/EIV references in deployment + network docs | → reference COA / SIS / ISIR / COD; egress sources → **College Scorecard (api.data.gov) only** | ✅ |
| Guard metric namespace `Housing/Governance` | → `FinancialAid/Governance` in code, CDK ObservabilityStack, and KEY-MANAGEMENT | ✅ |
| `provenance.py` / `workflow_guards.py` headers used Housing/HUD examples | Rewritten to the EDU assess_aid / Scorecard example (Housing named only as honest lineage) | ✅ |
| `cdk/app.py` titled "Housing eligibility agent" | → EDU Financial Aid Assistant | ✅ |
| Key-version example `hud:sm:` | → `scorecard:sm:` (matches GA-2 `scorecard` domain) | ✅ |
| `cdk/cdk.out` synth artifacts (with Housing lambda copies) tracked in git | Untracked + gitignored | ✅ |
| Test counts reconciled | 137/137 stated everywhere at the close of that cycle <!-- count-gate:historical --> | ✅ |
| Evidence not labeled as author-produced | Added explicit author-produced/synthetic-only disclaimer to `evidence/EP1-VALIDATION.md` | ✅ |

---

## 1b. Gate B P1 bundle — build status (this cycle)

The operating-model docs, the plain-language control, and the config/award-year CI gates were built
this cycle. That cycle closed with the suite at **153 tests** (137 + 13 + 3 CI-completeness gates) <!-- count-gate:historical -->;
the current authoritative count is **190 tests** (`RELEASE-MANIFEST.md`). Remaining Gate-B items are engagement actions
(SME red-line, accessibility-office review), not build items.

| Item | Deliverable | Status |
|---|---|---|
| Configuration (§2) | `docs/CONFIGURATION-WORKSHEET.md` + `config/institution.config.json` + `tests/test_config_schema.py` (drift gate) | ✅ built |
| SME validation (§3) | `docs/SME-REVIEW-PACKET.md` (ready for a credentialed aid officer to sign) | ✅ packet ready · ☐ signature |
| Accessibility (§6) | `docs/ACCESSIBILITY.md` + `lib/controls/readability.py` plain-language check + `tests/test_readability.py` | ✅ built |
| Support (§7) | `docs/SUPPORT.md` (pilot support model) | ✅ built |
| Model/prompt maint. (§8) | Covered by change-mgmt + redteam regression (doc pointer) | ◐ pointer |
| Award-year (§9) | `docs/AWARD-YEAR-UPDATE-RUNBOOK.md` + `AWARD_YEAR` constant + `tests/test_award_year.py` | ✅ built |
| Incident response (§10) | `docs/INCIDENT-RESPONSE.md` (EDU-specific FERPA/GLBA/FTI) | ✅ built |
| Audit readiness (§11) | `docs/AUDIT-READINESS.md` (control-to-evidence matrix) | ✅ built |
| Pilot metrics (§12) | Framework table (below); baselines captured at the pilot site | ✅ defined |
| MCP gateway + portability (§13) | `docs/MCP-GATEWAY.md` | ✅ built |

---

## 2. Configuration (P1)

**Today.** Deployment is parameterized by CDK context switches (`env`, `retention_profile`, `kms`,
`network_mode`, `identity_mode`, `tenant`); the tenant is HMAC-signed into artifacts at deploy time;
verification-item lists and SAP thresholds live in the rules engine.

**Gap.** An institution's *award-year* constants (verification tracking groups, SAP standards, COA
components, PJ documentation checklist) are code-adjacent, not a reviewed configuration surface a
financial-aid office signs off on. No documented config worksheet maps each institution-controlled
value to where it is set and who approves it.

**Action (P1).** Ship `docs/CONFIGURATION-WORKSHEET.md`: one row per institution-controlled value
(verification groups V1/V4/V5 item sets per 34 CFR 668.56, SAP quantitative/qualitative thresholds,
COA component basis, PJ checklist, comms tone/templates, retention profile), each with *default*,
*owner (aid office vs IT)*, *where set*, *approval sign-off line*. Add a `test_config_schema.py` that
fails CI if a required config key is missing or unlabeled.

---

## 3. Financial-aid SME validation (P1 → P2)

**Today.** The rules engine encodes Title IV / Pell / SAP logic and the VerificationHold path
(34 CFR 668) as interpreted by the builder; synthetic cases exercise the branches.

**Gap.** No **credentialed financial-aid SME** (a working Director/Associate Director of Financial
Aid, or a NASFAA-trained aid officer) has reviewed the rules, the verification item logic, the SAP
determination, the PJ boundary, or the draft student-communication language for regulatory accuracy
and tone. This is the single biggest substantive gap: the domain correctness is asserted, not
attested.

**Action.**
- **P1:** Produce an SME review packet — the rule set in plain English, the verification decision
  table, sample outputs per branch, and the PJ human-only boundary — formatted for a financial-aid
  professional to red-line.
- **P2:** Engage at least one credentialed aid officer (design-partner institution or NASFAA
  contact) to sign the packet; capture their corrections and re-validate. **No real-data pilot until
  an SME has signed the rule set and the communication templates.**

---

## 4. Training (P2)

**Today.** START-HERE, DEPLOYMENT-GUIDE, the SA Runbook, and the negative-demo script exist for the
*deployer*. Nothing exists for the *aid-office end user* who will triage the worklist and edit drafts.

**Action (P2).** `docs/OPERATOR-TRAINING.md` + a 20-minute walkthrough: how a case enters
VerificationHold, how to read the missing-documents worklist, how to review/edit a draft
communication before it is sent, when to escalate to Professional Judgment (human-only), and the
"the assistant never awards" boundary. Include a one-page laminated quick-reference and a 10-question
competency check the office completes before go-live.

---

## 5. Change management (P2)

**Today.** Git history, `RELEASE` single-source-of-truth, and a release-consistency CI gate govern
*code* change. There is no institution-facing change process for the humans.

**Action (P2).** `docs/CHANGE-MANAGEMENT.md`: the RACI for a change (who requests a rule/template
change, who approves, who tests, who signs the deploy), the communication plan to students/staff when
behavior changes, a rollback procedure (redeploy the prior tagged release), and a change log the aid
office co-signs. Tie every rule/template change to the §2 config sign-off.

---

## 6. Accessibility review (P1)

**Today.** Student-facing output is drafted text handed to a human before sending; no rendered UI
ships in the pilot. But the drafted communications themselves must meet accessibility and plain-
language standards (Section 508 / WCAG 2.1 AA for any institution portal; plain-language for
financial-aid comms).

**Action.**
- **P1:** Add a plain-language + reading-level check to the draft-generation path (target ≤ grade 8;
  define required elements: what's missing, what to do, the deadline, who to contact) and document it
  in `docs/ACCESSIBILITY.md` with the 508/WCAG mapping for any institution-hosted surface.
- **P2:** Have the institution's accessibility/ADA office review sample drafts before go-live.

---

## 7. Support (P1)

**Today.** `docs/SUPPORT.md`-equivalent statement exists in the release; on-call ownership for a
live pilot is not defined.

**Action (P1).** Define the pilot support model in `docs/SUPPORT.md`: severity definitions, response
targets, the escalation path (SA → builder → AWS support for infra), business hours vs after-hours
for a pilot, and a named backup owner. Explicitly state pilot support is best-effort (this is a
pilot, not a supported GA product) so expectations are set honestly.

---

## 8. Model & prompt maintenance (P2)

**Today.** Deterministic guards, Cedar policies, and the rules engine are the load-bearing controls;
the model is used for extraction and drafting behind those controls. No cadence governs prompt/model
version drift.

**Action (P2).** `docs/MODEL-PROMPT-MAINTENANCE.md`: pin the model version; a regression suite of
prompt-injection and drafting cases (extend the existing `redteam`/negative-demo set) that must pass
before any model or prompt change; a quarterly review cadence; and a statement that a model change is
a §5 change-managed event, not a silent update. The guards mean a model regression fails closed to
ManualReview rather than producing a bad award — document that as the safety net.

---

## 9. Annual award-year updates (P1)

**Today.** Pell tables and SAP references are stamped for the current award year in the rules engine.

**Gap.** Financial aid is inherently annual — Pell maximums, SAI formula tables, verification
tracking groups, and COA components change every award year. There is no documented, owned annual
update procedure.

**Action (P1).** `docs/AWARD-YEAR-UPDATE-RUNBOOK.md`: the checklist of everything that changes each
award year, the authoritative source for each (Federal Register / Dear Colleague Letters / ED
guidance), who owns the update, the test that must be added for the new year, and the deploy/sign-off
gate. Add `test_award_year.py` asserting the active award-year constant matches the deployed rules so
a stale table fails CI.

---

## 10. Incident response (P1)

**Today.** Gate-B ops docs (PIA, IR outline, access review, retention approval) were ported from the
Housing engagement; a PII-telemetry canary and WORM audit ledger exist.

**Action (P1).** EDU-specific `docs/INCIDENT-RESPONSE.md`: the FERPA/GLBA breach-notification path
(who is notified, in what window — GLBA Safeguards Rule notification and any state student-data-breach
law), the "suspected PII in telemetry" runbook (the canary alarm → contain → rotate keys → notify),
the "bad estimate reached a student" runbook (retract, correct, log), roles and contacts, and the
tabletop exercise to run before real data. Map each control to the threat-model row it answers.

---

## 11. Audit preparation (P1 → P2)

**Today.** WORM tamper-evident ledger with hash-chain + `verify_chain`, Cedar deny-by-default,
signed provenance, and the threat model provide the raw material an auditor needs.

**Action.**
- **P1:** `docs/AUDIT-READINESS.md` — a control-to-evidence matrix mapping each obligation (FERPA
  access controls, GLBA Safeguards 16 CFR 314, NIST 800-171 families, Title IV verification records,
  IRS Pub 4557 for FTI) to the specific artifact/test/log that demonstrates it, written so a program
  reviewer or bank-style examiner can follow it.
- **P2:** Dry-run the matrix against a mock audit question set (the §13 pushback list) and capture the
  answers with links to evidence.

---

## 12. Pilot metrics framework (P1 to define, P2 to measure)

The instrument for producing an **honest, measured** efficiency number in a customer environment.
Baseline each metric *before* the assistant is switched on, then measure with it on. **No productivity
percentage is claimed until these are measured at a pilot site.**

| # | Metric | Definition | Baseline source | Direction |
|---|---|---|---|---|
| 1 | Verification handling time | Median minutes from case open to verification decision | Current SIS/manual timing | ↓ |
| 2 | Time-to-identify-missing-docs | Minutes from case intake to a complete missing-item list | Manual review timing | ↓ |
| 3 | Repeated student contacts | # of back-and-forth contacts to resolve one verification | Ticket/CRM history | ↓ |
| 4 | Draft material-edit rate | % of drafted communications materially edited before send | Human-review log | ↓ (quality proxy) |
| 5 | Pell/SAP estimate agreement | % of assistant estimates matching the officer's independent figure | Officer spot-check | ↑ |
| 6 | Verification-hold accuracy | % of holds that were correct (truly needed docs/selection) | Officer adjudication | ↑ |
| 7 | Override rate + reason | % of cases an officer overrides, with categorized reason | Override log | tracked |
| 8 | Cases per officer | Throughput per FTE per period | Current staffing data | ↑ |
| 9 | Student response time | Time from student-facing comms to student action | CRM timestamps | ↓ |
| 10 | Fully-loaded cost per case | Staff time + infra cost per completed verification | Finance + AWS cost | ↓ |

**Method.** Pre/post with the same officer cohort; a held-out sample double-checked by a human for
metrics 5/6; overrides (7) reviewed weekly to catch systematic errors early. Only after a full pilot
cycle do we compute and publish a productivity figure — with confidence intervals and the caveat that
it is site-specific.

---

## 13. AWS leadership pushback — anticipated questions & answers

**Security / CISO.**
- *"Where does student PII go, and can the model or its telemetry leak it?"* — Raw FAFSA content never
  enters Step Functions state (zero-PII pass-by-reference); masking is deterministic and proven by a
  signed `sanitized_ref` (a boolean is never accepted); a strict telemetry canary asserts 0 PII hits
  across Logs/X-Ray/DLQ/SFN history; output guardrail anonymizes. Evidenced in EP1.
- *"What stops the agent from awarding or adjudicating on its own?"* — Cedar deny-by-default with
  `no_self_commit` and `no_self_professional_judgment`; consequential tools hidden from the model and
  refused at the Lambda; human `waitForTaskToken` sign-off gate bound to a content hash; approver ≠
  requester on a verified identity. Threat-model T4/T8.
- *"Data poisoning of the reference figures?"* — HMAC-signed provenance minted only by the real
  Scorecard lookup; verifier rebuilds fields from the values it will use; unverified → NEEDS_REVIEW.
- *"Blast radius / egress?"* — Private networking, Network Firewall **allowlist = `.api.data.gov`
  only**, customer-managed KMS, MFA-enforced pilot identity, tenant signed into artifacts.

**Architecture / Director of Architecture.**
- *"Is this real IaC or a script?"* — CDK is the supported path (7 stacks, `fa-` prefix); shell is
  legacy. Deterministic Step Functions controller with fail-closed guards between every stage.
- *"MCP — how is the gateway secured?"* — AgentCore/Gateway + Cedar are defined as IaC; auth is a
  secure gateway with token-exchange/IdP federation and least-privilege intersection (portfolio MCP
  auth pattern). Document the EDU gateway targets and the authz engine explicitly in the arch doc
  (P1 doc action).
- *"Exactly-once / idempotency?"* — GA-5 exactly-once finalize; storm test shows FIRST:1 / IDEMPOTENT:9.
- *"Portability off AgentCore?"* — Covered by GATEWAY-MODES (AgentCore vs portable) at portfolio level;
  port the clarity note into this repo (P1 doc action).

**GTM / field leadership.**
- *"What's the customer problem and cost of inaction?"* — Verification backlogs delay disbursement,
  drive repeated student contact, and risk Title IV compliance findings; state the pain and the
  regulatory exposure, not a fabricated dollar figure.
- *"What can we claim?"* — Only what's evidenced: an assistant that prepares verification worklists,
  reference-based estimates, and draft comms under a governed, auditable platform. **No productivity
  percentage until measured** (§12). Reference the "What we will not claim" page.
- *"Is the GTM on-brand?"* — AWS logo/color/trademark hygiene already applied portfolio-wide; re-verify
  the EDU one-pagers before internal share (P1 check).

---

## 14. Staged required-work (gates)

**Gate A — before sharing internally at AWS (P0).** ✅ Complete this cycle.
Doc contradictions fixed · cross-vertical Housing/HUD terminology removed from source + docs · test
counts reconciled · START-HERE reflects EP1 · assistant-not-awarding positioning universal ·
evidence labeled author-produced/synthetic · guard-metric namespace corrected. Remaining P0 nicety:
re-verify EDU GTM one-pagers render on-brand (visual check).

**Gate B — before a synthetic-data pilot (P1).**
Configuration worksheet (§2) · SME review packet prepared (§3) · plain-language/accessibility check on
drafts (§6) · support model (§7) · award-year update runbook + CI test (§9) · EDU incident-response
doc (§10) · audit-readiness matrix (§11) · pilot-metrics framework defined with baselines identified
(§12) · MCP gateway + portability notes ported into the repo arch doc (§13).

**Gate C — before a real-data shadow pilot (P2).**
Credentialed financial-aid SME has **signed** the rule set + communication templates (§3) · operator
training delivered + competency check passed (§4) · change-management process live (§5) · accessibility
office review of sample drafts (§6) · model/prompt maintenance regression + cadence (§8) · IR tabletop
run · **read-only** SIS/ISIR integration only; assistant runs alongside, never in front of, the
officer · legal/privacy sign-off (FERPA/GLBA) on the data-handling design.

**Gate D — before production (P3).**
Independent security testing / pen test · governance sign-off signatures captured on the audit matrix ·
enterprise IdP round-trip validated · production-scale load test · measured pilot metrics published with
the honest, site-specific productivity figure · institutional COD/SIS write paths remain out of scope
unless separately scoped, SME-signed, and re-gated.

---

## 15. Open, explicitly-not-yet-true items (say these out loud)

- No independent audit or pen test yet (Gate D).
- No credentialed financial-aid SME sign-off yet (Gate C).
- No real student data has been processed — synthetic only (Gate C).
- Institutional COA, packaging rules, and COD write-back are **adopter/out-of-scope**, not built.
- Efficiency/productivity numbers are **unmeasured** until a pilot site runs §12.

These are tracked, not hidden. The platform's job is to make each one safe to close in sequence.
