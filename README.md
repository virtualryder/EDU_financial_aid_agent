# Financial Aid Agent — Governed Agentic AI on Amazon Bedrock AgentCore

[![CI](https://github.com/virtualryder/EDU_financial_aid_agent/actions/workflows/ci.yml/badge.svg)](https://github.com/virtualryder/EDU_financial_aid_agent/actions/workflows/ci.yml)

> **Continuous validation.** CI runs render + unit + eval on every push. An **opt-in** end-to-end job (`.github/workflows/e2e.yml`, manual `workflow_dispatch`) deploys the spine to a sandbox AWS account, proves it live with the demo in ENFORCE, and tears it down — see the workflow header for one-time setup.


A **governed** Title IV / federal student-aid eligibility & awarding agent for Higher Education. It
intakes a FAFSA/aid application, de-identifies PII, determines Pell eligibility, Satisfactory Academic
Progress (SAP), and the verification track, drafts an award/determination notice, and **pauses at a
human sign-off gate** — a financial-aid officer makes and commits the award; the agent never
self-adjudicates. Built on the same governed-hero-agent pattern as the pharmacovigilance and benefits
agents, from a reusable, manifest-driven template — this is the **third vertical** proven on the pattern.

> **Accelerator, not a certification.** Reference implementation of the *pattern*. Not a
> production-certified system. Computer-system validation, IdP federation, connectors to the student
> information system / COD, the authoritative award rules, and authorization to operate (StateRAMP /
> ATO where applicable) remain the adopter's responsibility. Pell figures and SAP thresholds here are
> **illustrative federal defaults** — configure per award year and institution.

## Why this agent

Federal student-aid processing is high-volume, deadline-driven, and heavily regulated (Title IV of the
Higher Education Act, FERPA for education records, the GLBA Safeguards Rule, and IRS Pub 1075 where tax
data is used). It's an obvious place for an AI agent — but a financial-aid office cannot adopt an
ungoverned one: PII and education records must never leak, every determination needs a tamper-evident
audit, tool access must be least-privilege, and a **qualified aid officer must make and commit the
award**. This agent keeps the human in charge and makes the platform enforce it.

## The governed workflow

```
intake_fafsa -> lookup_coa -> mask_pii -> assess_aid -> draft_award_notice -> write_audit -> request_signoff
                                                                                                  |
                                                  aid officer (a DIFFERENT person) approves -> finalize_award
```

- **intake_fafsa** — extract the non-PII decision fields (Student Aid Index, institution, enrollment
  status, SAP GPA and pace, dependency) from the raw FAFSA/ISIR or application.
- **lookup_coa** — fetch the student's **real Cost of Attendance** from the U.S. Department of Education
  **College Scorecard API** (authoritative, live). The institution is non-PII, so this runs before
  masking; the real COA drives the Pell math and its **provenance is written into the audit** — even
  reaching real federal data is a Cedar-authorized, audited Gateway tool, not a side-channel.
- **mask_pii** — fail-closed PII de-identification (Amazon Comprehend `DetectPiiEntities`: name, SSN,
  address, DOB…). If masking can't run, nothing downstream proceeds.
- **assess_aid** — a deterministic rules engine (public Title IV formulas: Pell scheduled award =
  min(COA, max) − SAI, prorated by enrollment; the SAP test) returning ELIGIBLE / INELIGIBLE /
  NEEDS_REVIEW, the estimated Pell award, the SAP status, and the **verification track**. Uses the
  **authoritative 2026-27 Pell maximum ($7,395) / minimum ($740)** (FSA DCL 2026-01-30) and the real COA
  from `lookup_coa`, and echoes the COA provenance. No model, no licensed data.
- **draft_award_notice** — a real Bedrock (Claude) award/determination notice, through a fail-closed
  output guardrail, on de-identified data only.
- **write_audit** — append-only DynamoDB ledger + S3 Object Lock (WORM) copy of every decision. Each record is **hash-chained** to the prior one (`chain_hash = SHA-256(prev_hash + entry_hash)`), so the ledger is tamper-evident by construction — not just un-deletable but provably un-editable — and `lib/controls/verify_chain.py` replays the links to prove INTACT (or name the first broken record).
- **request_signoff** — starts a Step Functions separation-of-duties gate; a *different* aid officer
  approves with a single-use token before `finalize_award` ever runs.

Authorization is **Cedar deny-by-default** at the AgentCore Gateway: `aid_officer_permit` (role-gated),
`mask_before_assess` and `mask_before_draft` forbids (no processing/drafting on un-masked data), and
`no_self_commit` (the agent can never finalize an award). See `policies/`.

## Tests — proven live in ENFORCE

`bash lib/engine/demo.sh agents/financial-aid` exercises the full governed workflow against the deployed
system with Cedar in **ENFORCE**, and reports `31 passed, 0 failed / GOVERNANCE DEMO: PASS`:
deny-by-default (aid-officer ALLOW / outsider DENY), a **live authoritative COA lookup from College
Scorecard** with provenance carried into the determination, fail-closed PII masking, the mask-before
forbids firing *by name*, the aid determination (ELIGIBLE, estimated Pell + SAP + track), a real guarded
Bedrock notice, the immutable WORM audit (write-once + duplicate rejection), `no_self_commit`, and the
human sign-off gate (separation of duties + single-use token). The generic Strands agent also runs on
**AgentCore Runtime**: an aid officer runs the full governed workflow; an outsider gets ACCESS DENIED.

### Deeper caseload workflows (each a governed tool + its own Cedar control)

The higher-risk the action, the stronger the governance. Beyond intake/awarding, the agent adds:

- **`verify_documents`** — Title IV verification (34 CFR 668.51–.61): tracks required vs received
  documents and returns a **HOLD** while verification is PENDING (no disbursement until it clears).
- **`record_professional_judgment`** — prepares a documented Professional Judgment (HEA §479A)
  recommendation. It **requires a written rationale** (refuses without one) and returns a record a
  **different senior aid officer must approve**. Fail-closed (`mask_before_pj`).
- **`commit_professional_judgment`** — a **consequential, senior-human-only** action: the agent can
  **never** commit a professional-judgment adjustment. Forbidden by Cedar `no_self_professional_judgment`
  — the same deny-by-default pattern as `no_self_commit`, showing the model scales to every new
  high-risk action.

All are proven live in the 31-check demo.

## Deploy / prove / run / tear down

Requirements: AWS CLI v2 (admin, us-east-1), Python 3.12 + `pyyaml`, Bedrock model access, Bash
(Git-Bash on Windows). One agent = one manifest (`agents/financial-aid/manifest.yaml`) + domain tool
bodies + Cedar policies; the engine, control library, and runtime are reused.

```bash
bash lib/engine/deploy.sh  agents/financial-aid   # spine: engine -> gateway -> targets -> policies -> ENFORCE
bash lib/engine/demo.sh    agents/financial-aid   # 31-check governance proof
bash lib/engine/redteam.sh agents/financial-aid   # adversarial proof: governance holds under attack
# Runtime (from a fresh venv):
bash lib/runtime/setup_venv.sh
bash lib/runtime/_obs_setup.sh  agents/financial-aid
bash lib/runtime/_configure.sh  agents/financial-aid
bash lib/runtime/_launch.sh     agents/financial-aid
bash lib/runtime/_invoke.sh     agents/financial-aid aid_officer   # or: bash invoke_demo.sh (with sample data)
# Optional depth add-on — the governed OAuth connector (real outbound auth via AgentCore Identity, no stored secret):
bash lib/connector/deploy_connector.sh agents/financial-aid   # mock OAuth SoR (MOCK-SIS-COD) + Identity provider + verify_source
bash lib/connector/prove_connector.sh  agents/financial-aid   # proves OAuth + RS256/JWKS signature check + no secret + deny-by-default
bash lib/engine/destroy.sh agents/financial-aid   # zero-residual teardown (identity preserved)
```

Test-user passwords are env-driven with placeholder defaults (`ChangeMe-*1!`) — rotate before shared
use. Region/account resolve dynamically.

## Layout

```
lib/engine/     manifest-driven engine: render.py + deploy/demo/destroy + deploy_identity + signoff.asl.tmpl
lib/controls/   shared control tools: mask_pii, write_audit, request/approve/finalize sign-off, mcp_client
lib/runtime/    generic Strands agent on AgentCore Runtime (agent.py + Dockerfile + toolkit helpers)
lib/connector/  reusable governed OAuth connector: verify_source (token via AgentCore Identity, no stored secret) + deploy/prove scripts + RS256/JWKS-verified mock SoR
agents/financial-aid/
                manifest.yaml (single source of truth) + tools/ (intake_fafsa, lookup_coa, assess_aid, verify_documents, professional_judgment, aid_core) + demo_extra.sh
policies/       the six Cedar policies (rendered from the manifest), human-readable + a README
docs/           architecture note + Word guides (regulatory-adherence, SA runbook, maintenance, depth-evidence, cost/latency one-pager; generators/ regenerates the guides & decks) + decks
```

## Honesty boundary

The accelerator owns the governed agent, the Cedar policies, the tools, the fail-closed masking, the
human-gate workflow, the WORM audit design, the deterministic aid rules engine, the IaC, the tests. The
adopter owns: IdP federation and aid-officer role mapping; validated connectors to the student
information system / COD; the authoritative award rules/thresholds and their compliance review; computer-
system validation; and production authorization to operate. `verify_isir` and connectors to the production student-information system / COD remain adopter work; the repo does ship a **real** governed OAuth connector — `verify_source` authenticates to a mock system of record via AgentCore Identity (no stored secret) and the SoR verifies the token's RS256 signature against the Cognito JWKS — as the reference pattern. Pell figures and SAP thresholds are illustrative federal defaults.


## License

Apache-2.0 — see [LICENSE](LICENSE).
