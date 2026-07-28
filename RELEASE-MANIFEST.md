# Release Manifest — single authoritative record

*This is the ONE place that states the release, the counts, and the validation facts. Every other
document should reference this file rather than restating numbers. If a number anywhere disagrees with
this table, this table is correct and the other file is a bug.*

---

## Authoritative record

| Field | Value |
|---|---|
| **Product** | Financial Aid Verification & Student Communication **Assistant** (not an awarding / eligibility-adjudication agent) |
| **Supported tag** | `v0.1.3-pilot-rc1` — pins this reconciled state (docs + Gate-B operating-model bundle + 153 offline tests) |
| **EP1 validation** | ran on the code first cut as `v0.1.0-pilot-rc1`; `v0.1.1` = `v0.1.0` + **documentation reconciliation + operating-model bundle + 18 offline tests (132→150)**, **no infrastructure change** — so the EP1 live evidence carries forward unchanged |
| **EP1 validation date** | 2026-07-26 |
| **Region** | us-east-1 |
| **AWS account** | clean isolated account (id redacted in all committed files) |
| **Offline test suite** | **150 / 150** passing (unit + eval + Cedar policy + **24 CDK stack-synthesis** assertions) |
| **Legacy demo checks** | 32-check governance demo — **shell engine, internal reference only, NOT a customer path** |
| **EP1 live scenarios** | 6 (see below) |
| **Concurrency cases** | 10 concurrent executions → 10/10 SUCCEEDED, one `FINAL#` marker each |
| **Replay attempts** | 10 concurrent identical finalize replays → `FIRST:1 / IDEMPOTENT:9` (exactly-once) |
| **PII telemetry canary** | **PASS** — 0 hits across CloudWatch Logs · X-Ray · DLQs · Step Functions history |
| **Deployment stacks** | 7 (data · network · identity · compute · workflow · observability · gateway) |
| **Evidence source** | **Author-produced, synthetic data only** — not independently audited or pen-tested |

## EP1 live scenarios (the "6")

1. **Happy path** (`val1-happy-3`) → SUCCEEDED end-to-end inside the private network; live College
   Scorecard REFERENCE-COA lookup through the `.api.data.gov`-only egress firewall; exactly-once `FINAL#`.
2. **VerificationHold** (`val1-hold-1`) → terminated at the VerificationHold work-queue state (34 CFR
   668); no estimate drafted, nothing committed.
3. **Source-down / unverifiable school id** → fail-closed routing to manual review (no estimate on an
   unverified COA).
4. **Load** → 10/10 concurrent SUCCEEDED.
5. **Replay storm** → 10 identical replays, `FIRST:1 / IDEMPOTENT:9`.
6. **PII telemetry canary (strict)** → PASS (0 leaks).

## Count glossary (why several numbers exist — all legitimate, distinct)

- **153 offline tests** — the CI suite (grew 132 at EP0 → 137 after doc-integrity → 150 → 153 after the
  Gate-B operating-model bundle added config/award-year/readability gates). This is the current
  authoritative offline number.
- **32-check legacy demo** — the shell-engine governance demo. Internal reference only; retired from
  the customer path. Do not cite it as pilot evidence.
- **10 concurrency + 10 replay** — the EP1 load/replay storm; distinct from the offline suite.

## Known limitations (explicit)

- Evidence is author-produced on synthetic data; **no independent audit or penetration test** yet.
- **No credentialed financial-aid SME sign-off** on the rules/templates yet (blocks real data).
- No validated ISIR intake, no SIS read, no COD integration — real data stays shadow-mode until these
  exist and are institution-owned.
- Enterprise IdP federation is a shipped pilot reference (Cognito+OIDC), not a validated institutional
  integration.
- College Scorecard is **reference data**, never institutional COA; all outputs are **estimates**.
- Single-account validation; production wants multi-account separation.
- The independent clean-account reproduction (GitHub-OIDC release-validation workflow) is the next
  external proof point and has not yet been run by a third party.

## Provenance

Author: David Ryder (AWS HCLS SA). Build pattern ported from `Housing_eligibility_agent v0.9.4`. Full
readiness roadmap and gates: `EDU-PILOT-READINESS-PLAN.md`. Threat model: `docs/THREAT-MODEL.md`.
