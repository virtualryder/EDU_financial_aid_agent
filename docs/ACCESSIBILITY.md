# Accessibility & Plain Language — Student Communications

*Gate-B deliverable. Student-facing communications must be understandable and accessible. This documents
the plain-language check built into the draft path and the Section 508 / WCAG mapping for any
institution-hosted surface.*

---

## What ships in the pilot

The assistant produces **draft** communications that a human reviews before sending; no student-facing UI
ships in the pilot. So the accessibility obligation in scope is the **content** of the drafts (plain
language) plus the 508/WCAG expectations for any portal the institution renders them in.

## Plain-language check (built in)

`lib/controls/readability.py` runs an **advisory** check on every drafted notice
(`agents/financial-aid/tools/aid_core.py` surfaces it as `plain_language` in the draft result):

- **Reading grade** — a deterministic Flesch-Kincaid estimate; **target ≤ grade 8**
  (`comms_reading_grade_target` in `config/institution.config.json`). Masking placeholders
  (`[REDACTED:…]`) are stripped before scoring so masking never inflates the grade.
- **Required elements** — the four things a student needs to act: the **outcome**, the **next step**,
  the **deadline**, and **who to contact / how to appeal**. The check reports any missing element.

It is **advisory, not a gate**: the result is attached for the reviewing officer; the human sign-off gate
still owns whether a notice is sent. Rationale: correctness and tone are human judgments; the check
catches an over-complex sentence or an omitted next-step so the officer can fix it. Logic is unit-tested
in `tests/test_readability.py`.

## Section 508 / WCAG 2.1 AA (institution-hosted surface)

If the institution renders these communications in a portal or email template, that surface must meet
Section 508 / WCAG 2.1 AA. The mapping the institution's web/accessibility team should confirm:

| Guideline | Applies to | Owner |
|---|---|---|
| Text alternatives, semantic structure, headings | Portal/email templates | Institution web team |
| Color contrast ≥ 4.5:1, no color-only meaning | Templates | Institution web team |
| Keyboard operability, focus order | Portal | Institution web team |
| Reading level / plain language | Draft content (checked above) | Aid office |
| Screen-reader compatibility | Portal | Institution web team |

The assistant supplies accessible **content**; the rendering surface's conformance is the institution's
(adopter) responsibility, confirmed before go-live.

## Before go-live (Gate C)

The institution's accessibility/ADA office reviews sample drafts and the rendering surface. Record the
review date and reviewer in the change log.
