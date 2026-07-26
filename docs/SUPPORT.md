# Support Model — EDU Financial Aid Assistant (Pilot)

*Gate-B deliverable. This defines how the pilot is supported. It is a **pilot**, not a supported GA
product — support is **best-effort** and expectations are set honestly below.*

---

## Scope

Support covers the assistant and its AWS pipeline as deployed from a tagged release. It does **not**
cover the institution's SIS/ISIR/COD systems, network, or identity provider beyond the documented
integration points.

## Severity and response targets (business hours, pilot best-effort)

| Severity | Definition | Target first response |
|---|---|---|
| **Sev-1** | Suspected PII exposure, security incident, or the assistant producing wrong estimates that reached students | Immediate — invoke `docs/INCIDENT-RESPONSE.md` |
| **Sev-2** | Pipeline down or a governance guard failing open (it should fail closed) | Same business day |
| **Sev-3** | A single case mis-routed; a draft-quality issue | Next business day |
| **Sev-4** | Question, doc gap, enhancement request | Best-effort |

These are pilot targets, not a contractual SLA.

## Escalation path

1. **Aid-office operator** triages: is it a case-handling question (training) or a system fault?
2. **IT/security** for infrastructure faults (deploy, identity, network, KMS).
3. **Builder/SA** for assistant/pipeline logic — best-effort during the pilot.
4. **AWS Support** for underlying AWS service issues, via the institution's support plan.

Security or PII incidents go straight to Sev-1 and the incident lead, in parallel with the above.

## Hours and ownership

- **Business hours:** institution's standard business hours, the operator's local time.
- **After-hours:** Sev-1 only, via the incident lead; all other severities next business day.
- **Named owner + backup:** recorded in the institution's pilot contact sheet (kept out of this repo).

## What to include in a support request

The tagged release/version, the deployment env, the case or run identifier (never raw student PII), the
observed vs expected behavior, and any alarm that fired. For anything touching student data, follow the
IR runbook rather than emailing details.

## Known limitations (set expectations)

Best-effort pilot support; synthetic data only until SME sign-off (Gate C); no 24/7 coverage; SIS/ISIR/COD
integration is adopter-side and out of support scope. The full open-items list is in
`EDU-PILOT-READINESS-PLAN.md` §15.
