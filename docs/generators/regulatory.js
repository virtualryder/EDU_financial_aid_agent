const G = require("./guides.js");
const { H1, H2, H3, P, bold, code, bullet, num, codeBlock, callout, table, spacer, coverAndToc, makeDoc, Packer } = G;

const cover = coverAndToc(
  ["Regulatory-Adherence Guide"],
  "Financial Aid Agent on Amazon Bedrock AgentCore",
  "How the governed Title IV financial-aid accelerator maps to the Higher Education Act, FERPA, the GLBA Safeguards Rule, and IRS Publication 1075 — the controls it provides, the evidence it produces, and the validation that remains the institution's responsibility. Accelerator reference; not a compliance certification or legal advice. Version 1.0 · 2026.",
  ["1. Purpose & scope", "2. The regulated workflow", "3. Frameworks in scope", "4. Title IV program-integrity mapping", "5. FERPA mapping", "6. GLBA Safeguards & IRS Pub 1075 mapping", "7. Separation of duties & the human gate", "8. Shared responsibility", "9. Disclaimer"]
);

const body = [
  H1("1. Purpose & scope"),
  P("This guide maps the controls implemented in the Title IV financial-aid accelerator to the requirements a college or university financial-aid office must satisfy. It is written for the compliance, privacy, information-security, and financial-aid leadership who decide whether an AI-assisted awarding workflow can be adopted."),
  P([bold("What this guide is: "), "a control-to-requirement mapping showing how the accelerator supports adherence, what evidence it produces, and where the institution's own validation is required."]),
  P([bold("What this guide is not: "), "a certification, an attestation, or legal/regulatory advice. Adopting this accelerator does not by itself make a system compliant or an award determination correct. Program participation, the accuracy of award rules, and the lawfulness of the process remain the institution's responsibility (§8)."]),
  callout("Design principle", [["Every control below follows one rule from the regulated workflow: a qualified financial-aid officer makes the award determination and commits it — the agent intakes, de-identifies, screens, and drafts, but never self-adjudicates. The security design exists to enforce that rule and to produce the program-integrity evidence trail."]], G.colors.TEAL),

  H1("2. The regulated workflow"),
  P("Title IV awarding decides whether a student qualifies for the Pell Grant and other federal aid, whether they meet Satisfactory Academic Progress (SAP), and how verification is handled. When a FAFSA/ISIR arrives, a regulated workflow runs: intake the application, de-identify PII/education records, determine Pell eligibility, SAP, and the verification track, draft an award/determination notice, obtain a qualified aid officer's review and sign-off, and commit the award to the system of record."),
  P("The accelerator automates the intake, de-identification, screening, and drafting steps under governance, and pauses at a human sign-off gate before any award is committed. Four regulatory areas bear on this workflow, mapped in §§4–6."),

  H1("3. Frameworks in scope"),
  table(["Framework", "Relevance to the workflow"], [
    [[bold("Title IV / Higher Education Act")], "Federal student-aid program rules — Pell need analysis, Satisfactory Academic Progress, and verification (34 CFR Parts 668, 690); the qualified-aid-officer determination and professional judgment."],
    [[bold("FERPA")], "The Family Educational Rights and Privacy Act — protection of, and controlled access to, student education records."],
    [[bold("GLBA Safeguards Rule")], "The FTC Safeguards Rule — Title IV participants must protect student financial information with a written security program and technical safeguards."],
    [[bold("IRS Publication 1075")], "Safeguarding Federal Tax Information where tax data is used for income (e.g. via the FUTURE Act direct data exchange) — access, audit, and disclosure controls."],
  ], [2900, 7540]),

  H1("4. Title IV program-integrity mapping"),
  P("Title IV requires accurate need determination, SAP monitoring, verification, and an auditable award trail, with a qualified official making the determination. The accelerator produces the determination and the tamper-evident record a program review or audit depends on; the authoritative rules and their correctness remain the institution's responsibility."),
  table(["Title IV requirement", "How the accelerator addresses it", "Evidence / institution responsibility"], [
    ["Need determination (Pell)", "assess_aid computes an estimated Pell award deterministically from the Student Aid Index and cost of attendance, prorated by enrollment intensity, using the AUTHORITATIVE 2026-27 Pell figures (max $7,395 / min $740, FSA DCL 2026-01-30). The cost of attendance is fetched LIVE from the U.S. Dept of Education College Scorecard API (lookup_coa), and its provenance is stamped into the determination — a real, cited, reproducible basis.", [{ text: "Institution: ", bold: true }, "packaging rules; a free api.data.gov key for College Scorecard."]],
    ["Satisfactory Academic Progress", "assess_aid evaluates SAP (cumulative GPA and completion pace) and returns SATISFACTORY / NOT_SATISFACTORY, holding aid and routing to review when SAP is not met.", "The SAP status output; institution owns its published SAP policy and appeal process."],
    ["Verification (34 CFR 668.51-.61)", "verify_documents tracks required vs received documents and returns a HOLD while verification is PENDING — no disbursement until it clears. assess_aid also returns the verification track.", "The document checklist; institution owns its verification procedures and reconciliation."],
    ["Professional judgment (HEA 479A)", "record_professional_judgment PREPARES a documented PJ recommendation — it REQUIRES a written rationale and returns a record a DIFFERENT senior aid officer must approve. commit_professional_judgment is forbidden to the agent (no_self_professional_judgment); a PJ is a senior-human decision.", "The senior-approval workflow and the documented rationale for the file."],
    ["A defensible, reproducible determination", "assess_aid is a deterministic rules engine (no model) with the stated Pell/SAP basis, so an aid officer can defend it on appeal.", "The auditable determination basis; institution owns the authoritative rules."],
    ["An auditable award trail", "Append-only DynamoDB ledger plus an S3 Object Lock (WORM) copy of each decision (including the COA source and any PJ record); the writing principal is denied delete, update, and retention bypass.", "Object Lock configuration; IAM deny policy. Institution sets the retention period."],
    ["The determination is made by a qualified official", "The commit is performed by an aid officer at the human sign-off gate; the agent cannot finalize (Cedar no-self-commit).", "Enforced by the Step Functions gate + the forbid (see §7)."],
  ], [2650, 4090, 3700]),

  H1("5. FERPA mapping"),
  P("FERPA protects student education records and limits their disclosure. The accelerator de-identifies PII/education-record identifiers before the model or the audit sees them, and constrains access by least privilege. The institution's FERPA program and its determination of school officials with a legitimate educational interest remain prerequisites."),
  table(["FERPA area", "How the accelerator addresses it", "Evidence / institution responsibility"], [
    ["Protect education records / PII", "The mask_pii tool runs Amazon Comprehend DetectPiiEntities to remove PII (name, SSN, address, date of birth, and more) before drafting and before the audit — fail-closed: if masking cannot run, no draft is produced.", "Comprehend detection; demo proves name/SSN redaction and the fail-closed path."],
    ["Control access (legitimate educational interest)", "Amazon Cognito authentication with AgentCore Policy (Cedar) deny-by-default; every tool call is authorized against the aid officer's identity and group.", "Cognito pool + Cedar policies; institution maps school-official roles."],
    ["Audit access to records", "Every governed action writes a tamper-evident record capturing INTENT → COMMITTED with a content hash and timestamp; duplicates are rejected.", "The fa-audit ledger + WORM bucket; demo proves write-once + duplicate rejection."],
    ["Least privilege / minimum necessary", "The agent acts only within the intersection of its own and the aid officer's permissions; the finalize action is forbidden to the agent entirely.", "Cedar least-privilege permit/forbid policies."],
    ["Protect records in transit and at rest", "Runs inside the institution's AWS account; PII is masked before any model call; records are Object-Lock protected.", [{ text: "Institution: ", bold: true }, "KMS/encryption, network controls, FERPA program & annual notification."]],
  ], [2500, 4240, 3700]),

  H1("6. GLBA Safeguards & IRS Pub 1075 mapping"),
  P("The GLBA Safeguards Rule requires Title IV participants to protect student financial information with technical safeguards; where Federal Tax Information is used for income, Pub 1075 adds strict access and audit controls. The accelerator implements the access-control, audit, and de-identification safeguards; the written information-security program and the safeguard security report are the institution's."),
  table(["Safeguards / Pub 1075 area", "How the accelerator addresses it", "Status / institution responsibility"], [
    ["Access controls", "Deny-by-default Cedar authorization at the Gateway; authenticated identity via Cognito/IdP; least-privilege permits scoped to the aid-officer group.", "Live in ENFORCE; institution federates its IdP and maps roles."],
    ["Encryption & data protection", "PII is masked before any model call; the audit copy is Object-Lock protected; runs inside the institution's account.", [{ text: "Institution: ", bold: true }, "KMS keys, TLS, and network segmentation."]],
    ["Audit & monitoring", "Immutable WORM audit of every decision and state change, with identity-tagged, OTel-correlated logs.", "Live; institution sets retention and log aggregation."],
    ["Minimize / safeguard FTI", "mask_pii removes SSN and other identifiers before the model and the audit; least-privilege limits who and what can process it.", [{ text: "Institution: ", bold: true }, "the Pub 1075 safeguarding program and safeguard security report, where FTI is used."]],
    ["Written security program & assessment", "Reproducible, manifest-driven infrastructure-as-code and a 32-check governance test harness that runs in enforcement mode.", [{ text: "Institution: ", bold: true }, "the WISP, risk assessment, and qualified individual per the Safeguards Rule."]],
  ], [2500, 4240, 3700]),

  H1("7. Separation of duties & the human sign-off gate"),
  P("The single most important control for Title IV program integrity is that a qualified financial-aid officer — not the agent — makes and commits the award. The accelerator enforces this structurally:"),
  bullet([bold("The agent cannot commit. "), "The finalize_award action is forbidden by a Cedar policy and is hidden from the agent entirely; it is not reachable as a tool."]),
  bullet([bold("Commitment runs only through the gate. "), "The sanctioned path is a request for sign-off that starts a Step Functions workflow, which pauses until an aid officer approves."]),
  bullet([bold("The approver must differ from the requester. "), "A separation-of-duties check rejects self-approval."]),
  bullet([bold("Approvals are single-use. "), "The approval token is consumed against a durable ledger; it cannot be replayed."]),
  bullet([bold("Both ends are audited. "), "An INTENT record is written when sign-off is requested and a COMMITTED record when the award is finalized."]),
  callout("Proven live", [["In enforcement mode: an aid officer's request to self-approve is blocked as a separation-of-duties violation; a different qualified aid officer's approval succeeds; the award finalizes only after approval; and re-using the token is rejected. The generic agent also runs on AgentCore Runtime with these controls intact."]], G.colors.MINT, "E9F5EF"),

  H1("8. Shared responsibility"),
  P("The accelerator provides the pattern, the controls, and the evidence. Program participation and the connection to the institution's real systems and rules remain the institution's."),
  table(["The accelerator provides", "The institution is responsible for"], [
    ["The governed agent, Cedar policies, and tools", "Title IV program participation and authorization to operate"],
    ["Fail-closed PII de-identification", "IdP federation and aid-officer role mapping to school officials"],
    ["The human sign-off workflow (separation of duties)", "Validated connectors to the SIS / Common Origination & Disbursement"],
    ["The deterministic aid rules engine (illustrative defaults)", "The authoritative award rules/thresholds and their compliance review"],
    ["The immutable WORM audit design", "Record-retention policy and program-review readiness"],
    ["Reproducible IaC + the 32-check governance harness", "The GLBA written information-security program and Pub 1075 SSR (where FTI is used)"],
    ["Documentation (this guide, the runbook, maintenance)", "Notice language, SAP appeal rights, and the student appeal process"],
  ], [5220, 5220]),

  H1("9. Disclaimer"),
  P([{ text: "This document describes how an accelerator's technical controls map to selected regulatory requirements. It is provided for evaluation and architecture purposes only. It is not legal, regulatory, or compliance advice, and it is not a certification or attestation of compliance with Title IV of the Higher Education Act, FERPA, the GLBA Safeguards Rule, IRS Publication 1075, or any other authority. Award determinations have direct consequences for students; the correctness of award rules, thresholds, and notices, and the lawfulness of the process, depend on the institution's validated implementation, policies, compliance review, and use. The Pell figures and SAP thresholds shipped with the accelerator are illustrative federal defaults, not authoritative award rules. Consult your compliance, privacy, and financial-aid leadership before processing real student data.", italics: true, color: G.colors.MUTED, size: 19 }]),
];

const doc = makeDoc(cover, body, "Financial Aid AgentCore · Regulatory-Adherence Guide");
Packer.toBuffer(doc).then((b) => { require("fs").writeFileSync("Financial-Aid-AgentCore-Regulatory-Adherence.docx", b); console.log("wrote regulatory"); });
