# Cedar policies (the governance core)

These four Cedar statements are the authorization model for the agent. They are the
**single most important artifact in the repo** — everything else exists to enforce them.

They are **declared in `agents/financial-aid/manifest.yaml`** (under `policies:`) and rendered to
Cedar by `lib/engine/render.py` at deploy time, then attached to the AgentCore Policy engine. The
`.cedar` files here are the rendered, human-readable form, checked in so the model is reviewable
without running a deploy. The account id (`111122223333`) and gateway ARN are placeholders — the
deploy substitutes the real account and the gateway ARN that only exists after the gateway is created.

| Policy | Kind | What it enforces |
|---|---|---|
| `aid_officer_permit` | permit | Only a member of the `aid_officer` Cognito group may use any tool. Everything else is denied by default. |
| `mask_before_assess` | forbid | `assess_aid` cannot run on data that hasn't been de-identified (`deidentified == true`). |
| `mask_before_draft` | forbid | `draft_award_notice` cannot run on un-masked data — the model only sees de-identified text. |
| `no_self_commit` | forbid | The agent can never call `finalize_award`; committing an award is reachable **only** through the human sign-off gate. |
| `mask_before_pj` | forbid | `record_professional_judgment` cannot run on un-masked data. |
| `no_self_professional_judgment` | forbid | The agent can never call `commit_professional_judgment`; committing a PJ adjustment is a senior-human-only decision. |

Two rules of the engine make this airtight: **deny-by-default** (no statement, no access) and
**forbid wins** (a forbid overrides any permit). The demo
(`bash lib/engine/demo.sh agents/financial-aid`) proves each of these live in ENFORCE mode — a
31-check pass — and each denial names the exact policy that fired.

## Perimeter profile (PAR-1 step 5, 2026-09-06) — attached only with `-c perimeter=1`

Ported from the benefits pack so this pack carries the same #160/#161 model. `consent`, `purpose`,
`budget_ok` and `within_service_window` are **authoritative**: the gateway interceptor strips any
caller-supplied copy and re-injects them from the server clock, the live per-tenant meter and the
server-side authz store (`lib/controls/authoritative_context.py`, whose record `ingest_case` writes from
the verified aid officer's `consent_attested` + `purpose` attestation). A missing value fails the guard, so
the forbid fires — fail-closed.

| Policy | Condition |
|---|---|
| `require_entitlement` | **entitlement** — zero-default tools (#160): no non-empty `custom:tools` claim and no `tools_granted` membership ⇒ zero tools |
| `require_service_window` | **temporal** — the governed decision actions are refused outside the deployment's service window |
| `consent_purpose_before_assess_aid` | **consent + purpose** — the aid determination (FERPA-adjacent) needs the student's recorded authorization and an authorized purpose (`aid_determination` / `verification`) |
| `budget_before_draft_award_notice` | **budget** — the model-spending drafter is refused when the live per-tenant meter is at cap |

| `amount_cap_assess_aid` | **quantitative** — a cost of attendance above the institutional ceiling (100,000) is not an automated determination; the aid officer must review it |

All five conditions are live in this pack; `reviewer's` above is the aid officer.
