# Incident Response — EDU Financial Aid Assistant

*Gate-B deliverable. EDU-specific IR procedure for the pilot. Financial-aid data is protected by FERPA
and, because Title IV makes institutions "financial institutions," by the GLBA Safeguards Rule
(16 CFR 314); FAFSA-derived federal tax information additionally falls under IRS Pub 4557. This document
defines who does what when something goes wrong, mapped to the controls that detect it. It complements
the ported Gate-B ops pack (PIA, access review, retention approval).*

---

## Roles

| Role | Responsibility |
|---|---|
| **Incident lead** | Aid-office compliance lead — owns the incident, decides notification |
| **Technical responder** | IT/security — contains, rotates keys, pulls logs |
| **Privacy officer** | Owns FERPA/GLBA breach determination + notification content |
| **Builder/SA** | Supports diagnosis of the assistant/pipeline (best-effort, pilot) |

Keep current contact details in the institution's IR contact sheet (not in this repo).

## Detection sources (already built)

- **PII-in-telemetry canary** — a strict canary asserts 0 PII across Logs/X-Ray/DLQ/Step Functions
  history; a nonzero hit is a security signal.
- **Guard-failure metric** (`FinancialAid/Governance :: GuardFailed`) — a forged/tampered-evidence spike.
- **WORM audit ledger** — tamper-evident hash chain (`verify_chain`) for after-the-fact integrity checks.
- **CloudWatch alarms** on the above (ObservabilityStack).

## Runbooks

### R1 — Suspected PII in telemetry
1. Canary alarm fires (or manual report). **Contain:** disable the affected Lambda/version if leakage is
   ongoing. 2. **Assess:** pull the flagged log/trace; determine what fields, whose data, how many records.
3. **Rotate:** rotate the affected KMS-encrypted secrets/keys if credentials or signing material may be
   exposed. 4. **Purge** the offending telemetry per the log-retention/legal-hold policy. 5. **Notify:**
privacy officer makes the FERPA/GLBA determination (below). 6. **Fix:** add the failing case to the
canary/redaction test suite so it cannot recur.

### R2 — A wrong estimate reached a student
1. **Retract/correct:** issue a corrected communication; the assistant's outputs are drafts, so trace the
human approval that sent it. 2. **Root cause:** stale award-year table (see award-year runbook), an
unverified COA that should have held, or an officer override — identify which. 3. **Log** the correction
in the audit ledger. 4. If systemic, **hold** the affected cohort until the rule is fixed and redeployed.

### R3 — Forged/tampered evidence (guard spike)
1. Guard-failure metric spikes. **Investigate** whether it is an attack (forged `sanitized_ref`, tampered
provenance) or a bug. 2. The pipeline already **fails closed** to ManualReview on a failed guard — confirm
no case advanced on unverified state. 3. **Verify** the audit chain (`verify_chain`) for integrity.
4. Rotate signing keys if compromise is suspected.

### R4 — Unauthorized access / identity compromise
1. Disable the affected pilot identity (MFA-enforced Cognito). 2. Review access via the ported access-review
procedure. 3. Check the audit ledger for actions taken under the identity. 4. Rotate credentials.

## Breach determination & notification

The privacy officer determines whether an incident is a reportable breach:
- **GLBA Safeguards Rule (16 CFR 314.4(j))** — notification obligations for qualifying events affecting
  customer information; follow the institution's GLBA notification procedure and timeline.
- **FERPA** — record the disclosure; FERPA does not itself mandate individual breach notice but the
  institution's policy and any **state student-data-breach law** may. Involve counsel.
- **IRS Pub 4557 / FTI** — if FAFSA-derived federal tax information is involved, follow the institution's
  FTI incident procedure.

This document does not make categorical promises about who is or isn't notified — that is the privacy
officer's determination under the applicable rule and the facts.

## Before real data: tabletop

Run a tabletop of R1 and R2 with the aid office, IT/security, and privacy officer before the assistant
touches real student records (Gate C). Record the date and participants in the change log.
