# Financial Aid Agent — AgentCore-Native Architecture

*Target architecture for the Title IV / federal student-aid eligibility & awarding hero agent, built natively on Amazon Bedrock AgentCore. This note is the anchor design — it doubles as the opening of the leadership deck and the first section of the SA runbook. It is the Higher-Education (EDU) counterpart to the pharmacovigilance (HCLS) and benefits-eligibility (SLG) agents — the **third vertical** produced from the same reusable governed-hero-agent template. Draft v1.0 · 2026-07.*

---

## 1. What this agent does (the regulated workflow)

Federal student-aid processing is high-volume, deadline-driven work: determining a student's eligibility for the Pell Grant and other Title IV aid, checking Satisfactory Academic Progress (SAP), handling verification, and packaging an award. When a FAFSA/ISIR arrives, a regulated workflow must run end to end:

**intake the FAFSA/aid application → de-identify PII/education records → determine Pell eligibility, SAP status, and the verification track → draft an award/determination notice → a qualified aid officer reviews and signs off → the award is committed to the student information system.**

Under Title IV of the Higher Education Act and program regulations (34 CFR Parts 668, 690), and under FERPA and the GLBA Safeguards Rule, **a qualified financial-aid officer must make and commit the award determination** — applying professional judgment, SAP appeals, and verification, and preserving the student's right to appeal. The agent intakes, de-identifies, screens, and drafts; it never self-adjudicates. That single rule drives the whole security design.

## 2. Design thesis

AWS ships, in Amazon Bedrock AgentCore, the governance primitives a regulated agent needs. So we don't build a parallel governance platform — we become **the regulated-industry pattern implemented natively on AgentCore**: governed agentic AI built on AWS-native services, plus the three last-mile controls regulated customers need that AgentCore doesn't provide out of the box. This financial-aid agent is the third proof of that pattern: it was produced from the same manifest-driven template as the pharmacovigilance and benefits agents, by swapping the domain tools, the Cedar policies, and the workflow — the governance spine, runtime, and control library were reused unchanged, and it passed the same 21-check governance proof in ENFORCE.

## 3. Native on AgentCore vs. built alongside

| Control (governed-agent requirement) | Native? | AgentCore component / how |
|---|---|---|
| Verified human + agent identity | Native | **AgentCore Identity** — inbound JWT authorizer (Cognito / institution IdP) |
| Deny-by-default tool authorization | Native | **AgentCore Policy (Cedar)** — default-deny + forbid-wins, enforced at the Gateway |
| Least-privilege intersection (agent ∩ aid officer) | Native | Cedar principal with JWT group claim (`aid_officer`) as a tag + tool-parameter conditions |
| Tools as governed endpoints | Native | **AgentCore Gateway** — Lambda → MCP tools; every call passes Policy |
| Agent hosting / runtime | Native | **AgentCore Runtime** — hosts the Strands agent, serverless, session-isolated |
| Tracing / observability | Native | **AgentCore Observability** — OpenTelemetry spans per agent/tool step |
| Fail-closed PII de-identification | Build | `mask_pii` Gateway tool: Comprehend `DetectPiiEntities` (name, SSN, address, DOB…), before model + before audit |
| Human sign-off gate (separation of duties) | Build | Step Functions `waitForTaskToken` — bound, single-use approval; AgentCore has no native human gate |
| Immutable WORM audit (Title IV / program-integrity evidence) | Build | Append-only DynamoDB + S3 Object Lock; Observability traces are for ops, not tamper-proof evidence |

## 4. Target architecture (components)

**AgentCore Runtime** hosts the Strands financial-aid agent (`financial_aid_runtime_agent`), containerized (ARM64 via CodeBuild) and deployed with the AgentCore starter toolkit. The agent is generic — its workflow prompt is rendered from the manifest, so the same runtime image serves any agent built from the template.

**AgentCore Gateway** (`fa-financial-aid-gw`) exposes each capability as an MCP tool backed by a Lambda target: `intake_fafsa`, `mask_pii` (fail-closed), `assess_aid`, `draft_award_notice`, `write_audit`, and `request_signoff`. Every tool call is a Gateway call, so Policy gates all of them uniformly. The consequential `finalize_award` action exists only behind the human gate.

**AgentCore Identity** provides inbound auth — a JWT authorizer (Amazon Cognito or the institution's IdP) authenticates the aid officer on whose behalf the agent acts — and outbound auth for the credentials the Gateway uses to reach connectors (the student information system / COD, delivered as a labeled stub).

**AgentCore Policy (Cedar)** is the deny-by-default authorization engine (`fa_financial_aid_authz`). Default-deny and forbid-wins are automatic. Principal = the OAuth user (JWT `cognito:groups` surfaced as a tag); Action = the specific tool invocation; Resource = the Gateway; conditions can test both user claims and tool input parameters. This is simultaneously the deny-by-default gateway and the least-privilege intersection — natively.

**AgentCore Observability** emits OpenTelemetry spans for every agent and tool step.

**Built alongside — the regulated last mile:**
- **Fail-closed PII de-identification:** `mask_pii` de-identifies the application (Amazon Comprehend `DetectPiiEntities` — name, SSN, address, DOB, and more) before the model drafts and before anything is written to the audit. Fail-closed — if masking can't run, the call stops rather than exposing PII or education records.
- **Human sign-off gate (separation of duties):** `request_signoff` starts a Step Functions execution that pauses on `waitForTaskToken`; a *different* qualified aid officer approves with a bound, single-use token. The agent cannot finalize an award itself.
- **Immutable WORM audit:** an append-only, tamper-evident record (append-only DynamoDB + S3 Object Lock) capturing `INTENT → COMMITTED` for the Title IV program-integrity and audit trail.

## 5. How one governed action flows

1. The aid officer authenticates (Cognito/IdP) and receives a JWT.
2. The agent (on AgentCore Runtime) decides to call a tool.
3. The call goes through AgentCore Gateway; **Inbound Auth** validates the JWT.
4. The **Policy Engine** evaluates Cedar: principal (user claims) + action (the tool) + resource (the gateway) + conditions (group, tool parameters), default-deny. A deny means the tool never runs — and the denial is auditable.
5. The allowed tool runs. For assessment and drafting, `mask_pii` runs first (fail-closed), so the model only ever sees de-identified text.
6. The consequential step never executes inline: `request_signoff` opens the Step Functions human gate; a second aid officer approves; only then does `finalize_award` run.
7. Every decision and state change is written to the WORM audit, and every step is traced in Observability.

## 6. The aid rules engine (deterministic, illustrative)

`assess_aid` is a **deterministic rules engine**, not a model. It applies the public Title IV formulas — the Pell scheduled-award calculation (min(Cost of Attendance, maximum award) − Student Aid Index, prorated by enrollment intensity) and the Satisfactory Academic Progress test (cumulative GPA and completion pace) — to the de-identified decision fields, and returns a determination (ELIGIBLE / INELIGIBLE / NEEDS_REVIEW), the estimated Pell award, the SAP status, and the **verification track** (STANDARD vs. VERIFICATION_HOLD). It uses the **authoritative 2026‑27 Pell figures** (maximum $7,395 / minimum $740, FSA Dear Colleague Letter 2026‑01‑30). It fails closed if the case is not marked de-identified. The SAP GPA/pace floors remain configurable per institution. This is the financial-aid counterpart to the PV agent's seriousness/reporting-clock step and the benefits agent's FPL engine: a transparent, auditable, non-model determination a financial-aid officer can defend on appeal.

### 6a. Authoritative Cost of Attendance — a live, governed federal source

The cost of attendance is not a hardcoded number: a governed Gateway tool, **`lookup_coa`**, calls the **U.S. Department of Education College Scorecard API** (`api.data.gov/ed/collegescorecard/v1`) and returns the student's institution's **real academic-year Cost of Attendance** (field `COSTT4_A`), with a fallback to reported tuition. The institution identifier is non‑PII, so `lookup_coa` runs *before* masking; the real COA then drives the Pell math, and its **provenance (source, school, IPEDS unitid, field) is written into the WORM audit** so a determination is traceable to a named, authoritative source — not a magic number. The point for an adopter: even "reach out to real federal data" is a Cedar‑authorized, audited tool, not an ungoverned side‑channel. (Evaluation uses College Scorecard's shared `DEMO_KEY`; a pilot sets a free `api.data.gov` key via `SCORECARD_API_KEY`.)

## 6b. Deeper caseload workflows (step two)

Beyond intake, lookup, and awarding, the agent adds the workflows a real aid office needs — each a **new governed tool with its own Cedar control**, following one rule: the higher-risk the action, the stronger the governance.

- **`verify_documents`** — Title IV verification (34 CFR 668.51–.61). Tracks required vs received documents and returns a **HOLD** while verification is PENDING; no disbursement until it clears.
- **`record_professional_judgment`** — Professional Judgment (HEA §479A), the highest-risk discretionary act in aid. It **requires a documented rationale** (refuses without one), prepares the recommendation, and returns a record that a **different senior aid officer must approve**. Fail-closed (`mask_before_pj`).
- **`commit_professional_judgment`** — a **consequential, senior-human-only** action. The agent can **never** commit a PJ adjustment; it is forbidden outright by `no_self_professional_judgment`, exactly mirroring `no_self_commit`.

The governance model scales to new workflows with no new plumbing — a tool body plus a deny-by-default forbid — and each new forbid fires *by name* in ENFORCE.

## 7. Cedar policy model for financial aid (illustrative)

Default-deny is automatic; we author explicit permits plus a few targeted forbids. Illustrative — final syntax is pinned against the account during deploy:

```cedar
// A financial-aid officer may intake, mask, assess, and draft — gated on the group claim.
permit(principal, action, resource is AgentCore::Gateway)
when { principal.hasTag("cognito:groups") &&
       principal.getTag("cognito:groups") like "*aid_officer*" };

// No aid determination on un-masked data: assess requires the de-identified flag.
forbid(principal, action == AgentCore::Action::"assess-aid___assess_aid",
       resource == AgentCore::Gateway::"<gateway-arn>")
unless { context.input.deidentified == true };

// No drafting on un-masked data.
forbid(principal, action == AgentCore::Action::"fa-core___draft_award_notice",
       resource == AgentCore::Gateway::"<gateway-arn>")
unless { context.input.deidentified == true };

// The award is never a direct tool call — only the approval workflow can finalize.
forbid(principal, action == AgentCore::Action::"fa-core___finalize_award",
       resource == AgentCore::Gateway::"<gateway-arn>");
```

The shape is the point: a group-scoped permit, two forbids that enforce masking-before-processing and masking-before-model, and no path for the agent to self-commit an award.

## 8. Build order

1. **Governance spine first** — Cedar policies + Policy Engine + Gateway, deny-by-default proven before anything else.
2. **Tools as Gateway Lambda targets** — `intake_fafsa`, `mask_pii`, `assess_aid`, `draft_award_notice`, `write_audit`, `request_signoff`.
3. **Runtime + Identity** — the generic Strands agent onto AgentCore Runtime; Cognito inbound JWT wired to the Cedar principal.
4. **Human sign-off gate** — Step Functions `waitForTaskToken` wired to `request_signoff` and `finalize_award`.
5. **WORM audit + Observability.**
6. **Manifest + validate** — the whole agent is one manifest; deploy; end-to-end run (Cedar allow/deny, masking, aid determination, real Bedrock notice, immutable audit) + negative tests; teardown.

## 9. What's ours vs. the customer's (honesty boundary)

The accelerator owns: the agent, the Cedar policies, the tools, the fail-closed masking, the human-gate workflow, the WORM audit design, the deterministic aid rules engine, the IaC/manifest, and the docs. The institution owns: IdP federation and aid-officer role mapping; validated connectors to the student information system / COD; the authoritative award rules and thresholds and their compliance review; computer-system validation; and production authorization to operate. Pell figures and SAP thresholds here are illustrative federal defaults, and `verify_isir` / system-of-record connectors ship as labeled stubs. Nothing here is production-certified on day one — and saying so is part of the credibility.

## 10. Regulatory anchors (full mapping is a separate guide)

- **Title IV / Higher Education Act** (34 CFR 668/690 — Pell, SAP, need analysis, verification) → `assess_aid` rules engine; the **qualified-aid-officer determination** → the human gate.
- **FERPA** (protection of education records) → fail-closed masking + least-privilege Cedar + immutable audit.
- **GLBA Safeguards Rule** (safeguarding student financial information) → deny-by-default access control, encryption, audit, and the reproducible control evidence.
- **IRS Publication 1075** (safeguarding Federal Tax Information used in income/verification via the FA-DDX) → fail-closed masking + least-privilege + WORM audit.

Each of these becomes a control-to-requirement line in the regulatory-adherence guide.
