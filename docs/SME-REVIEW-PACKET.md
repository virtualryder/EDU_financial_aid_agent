# SME Review Packet — Financial-Aid Subject-Matter Sign-off

*Gate-B deliverable, Gate-C blocker. This packet is formatted for a **credentialed financial-aid
professional** (a working Director/Associate Director of Financial Aid, or a NASFAA-trained aid officer)
to red-line. The domain correctness of the rules, verification logic, and student-communication language
is currently **asserted by the builder, not attested by an SME**. No real student data is processed until
a qualified aid officer signs Section 6 of this packet.*

---

## 1. What the assistant does (and does not do)

It is a **Financial Aid Verification & Student Communication Assistant**. It prepares work for an aid
officer: it produces a verification worklist, a reference-based aid **estimate**, and a **draft** student
communication. It does **not** award, disburse, write to COD, or commit a Professional Judgment — those
are human-only and technically forbidden to the agent (Cedar deny + tool refusal). Every output is a
draft for officer review.

## 2. The Pell estimate rule (plain English)

For award year **2026-27** (Pell max $7,395, min $740; FSA DCL 2026-01-30):

> Estimated Pell = min(Cost of Attendance, $7,395) − Student Aid Index, floored at $0, then prorated by
> enrollment intensity (full 100% / three-quarter 75% / half 50% / less-than-half 25%). An award that
> rounds below $740 becomes $0 unless the SAI qualifies for the minimum.

- **SAI** comes from the FAFSA/intake (the student's own datum).
- **COA** is **College Scorecard reference data**, not the institution's COA — so every estimate is
  labeled an estimate and says an institutional COA is required for any actual award.
- If the COA figure is not cryptographically verified as coming from the real Scorecard lookup, the case
  goes to **NEEDS_REVIEW** — no estimate is made on an unverified number.

**SME question:** Is this Pell calculation, proration, and minimum-award rounding correct for your
institution's practice? Note any deviation.

## 3. Satisfactory Academic Progress (SAP)

Default thresholds: cumulative GPA ≥ **2.0** AND completion pace ≥ **67%** (34 CFR 668.34; institution
policy governs). If SAP is not met, the case is held as NEEDS_REVIEW with a note that a SAP appeal or
academic plan is required. Thresholds are configurable (`docs/CONFIGURATION-WORKSHEET.md`).

**SME question:** Do these thresholds and the "hold, don't deny" behavior match your SAP policy?

## 4. Verification decision table (34 CFR 668)

| Situation | Assistant behavior | Terminal state |
|---|---|---|
| Selected for verification | Holds — no estimate proceeds to a student until documents clear | **VerificationHold** (aid-office work queue) |
| Required documents missing/incomplete | Holds; lists exactly which items are outstanding | **VerificationHold** |
| Not selected, documents complete, SAP met, COA verified | Produces an estimate + draft notice for officer review | Estimate (draft) |
| COA unverified / source down | Refuses to estimate | NEEDS_REVIEW / ManualReview |
| SAP not met | Holds pending appeal/plan | NEEDS_REVIEW |

Verification works on document **flags** (which items are required vs received), not document **content**.
Groups in scope for the pilot: **V1, V4, V5** (configurable).

**SME question:** Are the in-scope verification groups, the required-item logic, and the hold-until-clear
behavior consistent with current-year verification requirements?

## 5. Professional Judgment (human-only)

The assistant can **prepare** a PJ package — capture the circumstance, assemble supporting documentation,
and require an officer rationale — but it can **never commit** a PJ adjustment. Committing is a senior aid
officer's discretionary action (HEA 479A / 34 CFR 668), enforced by Cedar `no_self_professional_judgment`
and refused at the tool. Documentation checklist: circumstance statement, supporting documentation,
officer rationale, officer signature.

**SME question:** Is the prepare-only boundary and the PJ documentation checklist appropriate?

## 6. Sample outputs to review

Attach or generate one example per branch from the synthetic dataset (`data/synthetic/`): an eligible
estimate + draft notice, a VerificationHold worklist, a SAP-hold case, and a PJ preparation package.
Review the **draft communication language** specifically for accuracy, tone, and required elements (what
the outcome is, what to do next, by when, who to contact / how to appeal) — the assistant runs an advisory
plain-language check (target grade ≤ 8), but a human's judgment on tone and correctness is what matters.

**SME question:** Are the draft communications accurate, appropriately caveated as estimates, and
respectful in tone? Mark any language you would not send to a student.

## 7. SME sign-off

I am a credentialed financial-aid professional and I have reviewed the rules (§2–3), the verification
logic (§4), the Professional Judgment boundary (§5), and the sample communications (§6). My corrections
are recorded and (where accepted) reflected in the rules/config.

Name / title / institution: __________________________
NASFAA or credential reference: __________________________
Signature / date: __________________________

*Until this section is signed, the assistant remains synthetic-data-only and is not run against real
student records.*
