# Award-Year Update Runbook

*Gate-B deliverable. Financial aid is annual: Pell maximums, the SAI formula tables, verification
tracking-group requirements, and COA components all change each award year. This runbook is the owned,
repeatable procedure for rolling the assistant forward to a new award year. `tests/test_award_year.py`
and `tests/test_config_schema.py` fail CI if the code and config disagree on the active year.*

---

## Owner and cadence

**Owner:** the aid office's designated compliance lead, with IT/security for the deploy.
**Cadence:** annually, as soon as the new award-year figures are published (typically a Federal Register
notice + FSA Dear Colleague Letter in the winter/spring before the year begins), and re-checked when ED
issues mid-year corrections.

## What changes each award year

| Item | Where set | Authoritative source |
|---|---|---|
| `AWARD_YEAR` label | `assess_aid.py::AWARD_YEAR` + `config` `award_year` | n/a (the anchor) |
| Pell maximum / minimum | `assess_aid.py::MAX_PELL` / `MIN_PELL` + config | FSA Dear Colleague Letter (annual Pell payment schedule) |
| SAI formula tables (if used) | `assess_aid.py` rules | Federal Register EFC/SAI formula notice |
| Verification tracking groups + required items | `verify_documents.py` + config | Annual Federal Register verification notice (34 CFR 668.56) |
| SAP thresholds (if institution changes them) | `assess_aid.py::SAP_*` + config | Institution SAP policy (34 CFR 668.34) |
| COA components reference | `lookup_coa.py` / labels | ED guidance; institution COA policy (adopter) |

## Procedure

1. **Gather** the published figures for the new year; record each authoritative source URL/citation.
2. **Update code + config together** in one commit: the constant in `assess_aid.py` (and/or
   `verify_documents.py`) AND the mirror in `config/institution.config.json`, including `award_year`.
   The drift gate requires both to agree.
3. **Add/extend a test** for the new year's expected outputs (a known SAI/COA → expected Pell for the
   new tables), so the roll-forward is proven, not assumed.
4. **Run the suite** (`pytest tests/`). `test_award_year.py` confirms the year label is consistent;
   `test_config_schema.py` confirms no value drifted.
5. **SME re-check** (recommended): have the aid-office SME confirm the new figures before deploy
   (`docs/SME-REVIEW-PACKET.md`).
6. **Deploy** through a tagged release (`docs/CHANGE-MANAGEMENT.md`), never by editing a live Lambda.
7. **Record** the update in the change log with the approver and the sources.

## Rollback

If a new-year figure is later corrected, redeploy the prior tagged release or apply the corrected value
through the same procedure. Because estimates are labeled with the award year in their notes, an officer
reviewing an older estimate can see which year's tables produced it.

## Guardrail

The assistant never invents a figure. If the deployed tables are stale relative to a case's award year,
the correct outcome is a review hold, not a wrong number — but the point of this runbook and its CI gates
is to keep the tables current so that path is rarely exercised.
