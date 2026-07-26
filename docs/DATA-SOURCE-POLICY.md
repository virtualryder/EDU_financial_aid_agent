# Data-Source Policy — correctness over availability

*What each data source IS, what it may be used for, and what happens when it is unavailable or
unverifiable. The rule everywhere: the system fails closed to a human — it never fabricates,
never falls back to sample data, and never lets a caller-typed label stand in for provenance.*

## College Scorecard (api.data.gov) — VERIFIED REFERENCE DATA, not institutional COA

**The correction this policy leads with (external review finding, adopted):** College Scorecard
publishes public, institution-level cost metrics (averages and reported figures). It is legitimate
**contextual reference data** for a preliminary aid ESTIMATE — it is **never** the student-specific,
institution-approved cost of attendance an award package requires (program, enrollment intensity,
housing arrangement, books, transportation, etc. are institution-controlled).

Controls on the lookup:
- The ONLY component that reaches the API (`lookup_coa`) **HMAC-signs the exact figure fetched**
  (GA-2 `scorecard` domain key; key IAM-restricted to the lookup). Verifiers rebuild the signed
  field set from the values they actually use — a fabricated or tampered figure fails verification
  and the case routes to `NEEDS_REVIEW`. **The signature proves integrity + origin, not award
  authority.**
- Every output that uses the figure carries
  `coa_basis: "College Scorecard REFERENCE data - institutional COA required for any award package"`
  and the deterministic result is an **estimate**, never an award.
- **Source down / key invalid:** the lookup returns `found: false`; `GuardReferenceCOA` fails
  closed; the case routes to `ManualReview`. No estimate is produced on unverifiable data.
- API key: `SCORECARD_API_KEY_ARN` (Secrets Manager) → `SCORECARD_API_KEY` env (dev) → `DEMO_KEY`
  (public fallback — acceptable ONLY because this is reference data; heavily rate-limited).

## FAFSA/intake content — FERPA education record + GLBA-covered financial data

Enters the system through exactly one door (`ingest-case`) into the encrypted, TTL'd,
institution-scoped case store; only opaque refs cross Step Functions (zero-PII state, strict-canary
enforced). De-identification is PROVEN by the mask_pii-signed sanitized artifact (`deid` domain
key) before any model interaction; FAFSA tax data never reaches Bedrock unmasked and never reaches
telemetry.

## ISIR / SIS / COD — NOT integrated (adopter work)

There is no validated ISIR intake, no SIS read, no COD connection. Until a read-only SIS/ISIR
integration exists and is validated by the institution, **real student data may be used in shadow
mode only**, and nothing this system produces is part of the official case record. The governed
OAuth connector pattern (`lib/connector/`) is the reference architecture for that future
integration — it is a mock, and is labeled as such.

## Authoritative figures that ARE embedded

Pell maximum/minimum for the award year are pinned constants with their source cited in
`assess_aid.py` (FSA Dear Colleague letter); SAP thresholds are **institution-configurable**
parameters, defaulted for demonstration and flagged as configuration, not policy.
