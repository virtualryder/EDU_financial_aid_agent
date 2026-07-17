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
