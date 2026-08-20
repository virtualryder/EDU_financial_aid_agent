# Financial Aid Agent — Governed Agentic AI on Amazon Bedrock AgentCore

**New here? → [`START-HERE.md`](START-HERE.md)** — one page: what this is, evidence provenance,
reading order by role, and the pilot offer.

> **SUPPORTED DEPLOYMENT PATH — read this first.** The ONE supported path is **AWS CDK at the
> validated release tag [`v0.1.3-pilot-rc1`](https://github.com/virtualryder/EDU_financial_aid_agent/releases/tag/v0.1.3-pilot-rc1)**
> (`cdk/` — includes the AgentCore Gateway/Cedar attachment as IaC), per
> [`DEPLOYMENT-GUIDE.md`](DEPLOYMENT-GUIDE.md) and [`VALIDATED_RELEASE.md`](VALIDATED_RELEASE.md);
> the tag was cut AFTER the EP1 live validation captured its evidence (2026-07-26 — see
> [`RELEASE-MANIFEST.md`](RELEASE-MANIFEST.md)). The shell engine (`lib/engine/`) is **legacy/internal
> reference only**. Product framing: a **Financial Aid Verification & Student Communication Assistant**
> — verification, estimation, and drafting support; NOT an awarding or eligibility-adjudication agent
> (`PILOT-SCOPE.md`).


[![CI](https://github.com/virtualryder/EDU_financial_aid_agent/actions/workflows/ci.yml/badge.svg)](https://github.com/virtualryder/EDU_financial_aid_agent/actions/workflows/ci.yml)

> **Part of the Governed Agent Platform.** This agent is being consolidated into the [governed-agent-platform](https://github.com/virtualryder/governed-agent-platform) monorepo, where all four verticals share one versioned governance core (`governed-core`) and deploy via AWS CDK infrastructure-as-code (deployed + validated live). **The one supported deployment path is AWS CDK** (`cdk/`); the shell engine (`lib/engine/`) is a legacy internal reference only and is not a customer deployment path.

> **Continuous validation.** On every push CI runs the **governance-core integrity gate** (`lib/verify_core.py`, so the shared core must match its pinned `core.lock` and drift cannot merge unnoticed), manifest render, the unit + eval suite, and a bug-class lint, plus a **supply-chain job** that audits the pinned runtime dependencies (`pip-audit`) and emits a CycloneDX SBOM. An **opt-in** end-to-end job (`.github/workflows/e2e.yml`, manual `workflow_dispatch`) deploys the spine to a sandbox AWS account, proves it live with the demo in ENFORCE, and tears it down — see the workflow header for one-time setup.


A **governed** Financial Aid Verification & Student Communication **Assistant** for the Title IV aid
office in Higher Education. It intakes a FAFSA/aid application, de-identifies PII, checks
verification-document completeness (34 CFR 668), produces a **Pell/SAP aid estimate** on verified
College Scorecard **reference** data (an estimate for case preparation — never an institutional
cost-of-attendance or a final award), prepares Professional Judgment documentation, and drafts a
**human-reviewed student communication** — then **pauses at a human sign-off gate**. A financial-aid
officer reviews and commits every consequential action; the assistant never awards, disburses, writes
back to COD, adjudicates eligibility, or commits a Professional Judgment. Built on the same
governed-hero-agent pattern as the pharmacovigilance and benefits agents, from a reusable,
manifest-driven template — this is the **third vertical** proven on the pattern.

> **Accelerator, not a certification.** Reference implementation of the *pattern*. Not a
> production-certified system. Computer-system validation, IdP federation, connectors to the student
> information system / COD, the authoritative award rules, and authorization to operate (StateRAMP /
> ATO where applicable) remain the adopter's responsibility. Pell figures and SAP thresholds here are
> **illustrative federal defaults** — configure per award year and institution.


## Validated evidence (EP1 live run, captured 2026-07-26)

One clean-account validation with every Gate-B switch on, torn down afterward — raw capture in
[`evidence/EP1-VALIDATION.md`](evidence/EP1-VALIDATION.md):

- **Full governed pipeline SUCCEEDED end-to-end inside the private network** — a live College
  Scorecard lookup THROUGH the `.api.data.gov`-only egress firewall (University of Florida, COA
  $22,523, provenance signed and verified as **reference** data), real Comprehend masking, the
  VerifyDocuments gate, a guarded Bedrock draft, the human sign-off pause, and **exactly-once**
  finalize.
- **The VerificationHold work-queue path** — a case selected for verification with a missing tax
  transcript terminated at `VerificationHold`, no estimate drafted (34 CFR 668).
- **Zero FAFSA/PII in telemetry** — strict canary PASS across CloudWatch Logs, X-Ray, DLQs, and
  Step Functions execution history (the FERPA/GLBA/IRS Pub 4557 story).
- **Concurrency + replay** — 10/10 concurrent executions SUCCEEDED; a 10-way replay storm committed
  exactly once (`FIRST:1, IDEMPOTENT:9`).
- **Pilot identity + tenant** — MFA ON / threat-protection ENFORCED / 0 IaC users; the deployment
  tenant HMAC-signed into the live sanitized artifact.
- **Validation found + fixed a real defect** — `guard_extracted` over-required a school id that
  actually comes from the SIS/execution input; fixed to require only the Student Aid Index.

Not yet done (honestly): independent third-party reproduction (the OIDC release-validation workflow
is the path), enterprise-IdP round-trip, independent security testing, and the customer-owned SIS/
ISIR/COD integration that any real-data use requires. See [`docs/GATE-B-CHECKLIST.md`](docs/GATE-B-CHECKLIST.md).

## Why this agent

Federal student-aid processing is high-volume, deadline-driven, and heavily regulated (Title IV of the
Higher Education Act, FERPA for education records, the GLBA Safeguards Rule, and IRS Pub 1075 where tax
data is used). It's an obvious place for an AI agent — but a financial-aid office cannot adopt an
ungoverned one: PII and education records must never leak, every determination needs a tamper-evident
audit, tool access must be least-privilege, and a **qualified aid officer must make and record the
award decision** in the authoritative system. This assistant keeps the human in charge and makes the
platform enforce it.

## The governed workflow

```
intake_fafsa -> lookup_coa -> mask_pii -> assess_aid -> draft_award_notice -> write_audit -> request_signoff
                                                                                                  |
                                                  aid officer (a DIFFERENT person) approves -> finalize_award
```

- **intake_fafsa** — extract the non-PII decision fields (Student Aid Index, institution, enrollment
  status, SAP GPA and pace, dependency) from the raw FAFSA/ISIR or application.
- **lookup_coa** — fetch the institution-level **reference Cost of Attendance** from the U.S. Department
  of Education **College Scorecard API** (verified REFERENCE data, live — never the student's
  institutional COA). The institution is non-PII, so this runs before masking; the reference COA drives
  the Pell **estimate** and its **provenance is signed into the audit** — even reaching real federal
  data is a Cedar-authorized, audited Gateway tool, not a side-channel.
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
system with Cedar in **ENFORCE**, and reports `32 passed, 0 failed / GOVERNANCE DEMO: PASS`:
deny-by-default (aid-officer ALLOW / outsider DENY), a **live REFERENCE COA lookup from College
Scorecard** (reference data, never institutional COA) with provenance carried into the estimate,
fail-closed PII masking, the mask-before forbids firing *by name*, the aid **estimate** (estimated Pell
+ SAP + track), a real guarded
Bedrock notice, the append-only, tamper-evident WORM audit (write-once + duplicate rejection), `no_self_commit`, and the
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

All are proven live in the EP1 validation run ([`evidence/EP1-VALIDATION.md`](evidence/EP1-VALIDATION.md)).

## Deploy / validate / run / tear down (the supported CDK path)

Full step-by-step: [`DEPLOYMENT-GUIDE.md`](DEPLOYMENT-GUIDE.md). Short version:

```bash
git checkout v0.1.3-pilot-rc1            # deploy a VALIDATED RELEASE TAG, never main
cd cdk && pip install -r requirements.txt
cdk deploy --all -c env=pilot -c retention_profile=pilot -c kms=customer-managed \
  -c network_mode=private -c identity_mode=pilot -c tenant=<institution-id>
# stage the OPTIONAL Scorecard key (DEMO_KEY works without it), then:
python scripts/validate_deployment.py --env pilot   # machine PASS/FAIL — any FAIL blocks use
# run a case: ingest (raw FAFSA -> opaque ref) -> start execution with the ref -> aid officer approves
#   (DEPLOYMENT-GUIDE §5 has the exact commands)
cdk destroy --all -c env=pilot                       # teardown; RETAIN'd evidence per records policy
```

Independent verification without trusting a laptop: the **GitHub-OIDC release-validation workflow**
([`.github/workflows/release-validation.yml`](.github/workflows/release-validation.yml)).

<details>
<summary><b>Legacy shell engine</b> (internal reference only — NOT for customer deployments)</summary>

```bash
bash lib/engine/deploy.sh  agents/financial-aid   # spine -> gateway -> policies -> ENFORCE
bash lib/engine/demo.sh    agents/financial-aid   # legacy governance demo
bash lib/engine/destroy.sh agents/financial-aid   # teardown
```
Shell-path test-user passwords are env-driven `ChangeMe-*` placeholders — sandbox only (the CDK path
ships ZERO users).
</details>

## Pilot readiness (Gate B operating model)

Beyond the code and the EP1 validation, the operating model a pilot needs is documented and, where it
can be, enforced in CI (suite **175 tests**). Start with the plan, then the specific docs:

- [`EDU-PILOT-READINESS-PLAN.md`](EDU-PILOT-READINESS-PLAN.md) — the whole picture: operating model, pilot metrics (no productivity % until measured), leadership Q&A, staged gates.
- [`docs/CONFIGURATION-WORKSHEET.md`](docs/CONFIGURATION-WORKSHEET.md) — institution-controlled values + `config/institution.config.json` (CI drift gate: `test_config_schema.py`).
- [`docs/SME-REVIEW-PACKET.md`](docs/SME-REVIEW-PACKET.md) — for a credentialed financial-aid officer to sign (Gate-C blocker).
- [`docs/AWARD-YEAR-UPDATE-RUNBOOK.md`](docs/AWARD-YEAR-UPDATE-RUNBOOK.md) — annual roll-forward + `test_award_year.py`.
- [`docs/ACCESSIBILITY.md`](docs/ACCESSIBILITY.md) — plain-language check (`readability.py` + `test_readability.py`) + 508/WCAG mapping.
- [`docs/INCIDENT-RESPONSE.md`](docs/INCIDENT-RESPONSE.md) · [`docs/AUDIT-READINESS.md`](docs/AUDIT-READINESS.md) · [`docs/SUPPORT.md`](docs/SUPPORT.md) · [`docs/MCP-GATEWAY.md`](docs/MCP-GATEWAY.md).

Honest status: build items are done; the remaining Gate-B/-C work is engagement-side (SME red-line,
accessibility-office review) and the independent testing/governance signatures at Gate D.

## Layout

```
lib/engine/     manifest-driven engine: render.py + deploy/demo/destroy + deploy_identity + signoff.asl.tmpl
lib/controls/   shared control tools: mask_pii, write_audit, request/approve/finalize sign-off, mcp_client
lib/runtime/    generic Strands agent on AgentCore Runtime (agent.py + Dockerfile + toolkit helpers)
lib/connector/  reusable governed OAuth connector: verify_source (token via AgentCore Identity, no stored secret) + deploy/prove scripts + RS256/JWKS-verified mock SoR
agents/financial-aid/
                manifest.yaml (single source of truth) + tools/ (intake_fafsa, lookup_coa, assess_aid, verify_documents, professional_judgment, aid_core) + demo_extra.sh
policies/       the six Cedar policies (rendered from the manifest), human-readable + a README
docs/           architecture note + Word guides (regulatory-adherence, SA runbook, maintenance, depth-evidence, cost/latency one-pager, IdP-federation reference; generators/ regenerates the guides & decks) + decks
                + Gate-B operating model: CONFIGURATION-WORKSHEET, SME-REVIEW-PACKET, AWARD-YEAR-UPDATE-RUNBOOK, ACCESSIBILITY, INCIDENT-RESPONSE, AUDIT-READINESS, SUPPORT, MCP-GATEWAY
config/         institution.config.json — single source of truth for institution-controlled values (CI drift gate)
```

## Honesty boundary

The accelerator owns the governed agent, the Cedar policies, the tools, the fail-closed masking, the
human-gate workflow, the WORM audit design, the deterministic aid rules engine, the IaC, the tests. The
adopter owns: IdP federation to their own provider (a working OIDC/SAML → Cognito → Cedar reference ships as `lib/engine/deploy_federation.sh` + `docs/IdP-Federation-Reference.md`, so federated users hit the same deny-by-default policies as the built-in users) and aid-officer role mapping; validated connectors to the student
information system / COD; the authoritative award rules/thresholds and their compliance review; computer-
system validation; and production authorization to operate. `verify_isir` and connectors to the production student-information system / COD remain adopter work; the repo does ship a **real** governed OAuth connector — `verify_source` authenticates to a mock system of record via AgentCore Identity (no stored secret) and the SoR verifies the token's RS256 signature against the Cognito JWKS — as the reference pattern. Pell figures and SAP thresholds are illustrative federal defaults.


## License

Apache-2.0 — see [LICENSE](LICENSE).
