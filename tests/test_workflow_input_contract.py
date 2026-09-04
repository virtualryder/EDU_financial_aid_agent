"""Controller input-contract gate — every JSONPath the state machine reads must be reachable.

WHY THIS EXISTS. `LookupCOA` read `$.school` and `$.unitid` directly from execution state. The
documented execution-input contract is `{case_id, requester, case_ref}` (DEPLOYMENT-GUIDE.md §2, and
the R3-2 note in workflow_stack.py), so neither field is ever present. Every execution started with
the documented command died with:

    An error occurred while executing the state 'LookupCOA' ... The JSONPath '$.school'
    specified for the field 'school.$' could not be found in the input

That is a **hard execution failure, not a fail-closed outcome**: no ManualReview record, no audit
intent — the governed pipeline simply crashed. It is the exact trap the guard comment two lines below
warns about ("a brittle JSONPath here would turn fail-closed into a runtime error"), committed on the
input side. Found by running the guide's own command against a live deployment (`fa-val2`, 2026-07-28).

The offline suite could not catch it: `Template.from_stack()` asserts the state machine's *shape*, and
a JSONPath that resolves against nothing is structurally valid — it only fails at runtime, with real
state. This gate closes that gap by checking the synthesized definition against the documented contract.
"""
import json

import pytest

aws_cdk = pytest.importorskip("aws_cdk")
from aws_cdk import assertions  # noqa: E402

# The fields an execution is actually started with — DEPLOYMENT-GUIDE.md §2.
EXECUTION_INPUT_FIELDS = {"case_id", "requester", "case_ref",
                          # OPTIONAL: the SIS/ingest starter may supply an institution so the
                          # reference-COA lookup can sign and the case can reach sign-off. Guarded by
                          # the HasInstitution Choice (is_present), so its absence never crashes.
                          "institution",
                          # OPTIONAL: selected_for_verification comes from the ISIR (CPS); when absent
                          # the workflow defaults it TRUE (stricter 34 CFR 668 path).
                          "selected_for_verification"}

# Roots produced by an earlier state via result_path — safe to read downstream.
PRODUCED_UPSTREAM = {
    "extract", "guards", "lookup", "mask", "assessment", "documents",
    "draft", "audit", "approval", "commit",
    "seeded",          # the SeedInstitution Pass state's defaults
    "_sel",            # SelectedFromInput/SelectedDefault normalize selected_for_verification
}

# ASL/Step Functions internals, not execution state: "$.Payload" inside a ResultSelector refers to the
# Lambda response, and "$$.Task.Token" is the context object. Neither is a state-path read.
ASL_INTERNALS = {"Payload", "Task", "Execution", "State", "StateMachine"}

ALLOWED_ROOTS = EXECUTION_INPUT_FIELDS | PRODUCED_UPSTREAM | ASL_INTERNALS


def _controller_definition_json():
    """Synthesize the workflow stack and return the controller's ASL definition as text."""
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "cdk"))
    import aws_cdk as cdk
    from fa_stacks.data_stack import DataStack
    from fa_stacks.compute_stack import ComputeStack
    from fa_stacks.workflow_stack import WorkflowStack
    from app import stage_lambda_bundle

    app = cdk.App()
    asset = stage_lambda_bundle()
    data = DataStack(app, "d", prefix="fa-t", retention_profile="sandbox-demo", kms_mode="aws-managed")
    compute = ComputeStack(app, "c", prefix="fa-t", asset_dir=asset, data=data)
    wf = WorkflowStack(app, "w", prefix="fa-t", compute=compute, data=data)
    return json.dumps(assertions.Template.from_stack(wf).to_json())


def test_no_unreachable_toplevel_jsonpath():
    """A `"x.$": "$.y"` where `y` is neither execution input nor produced upstream fails at RUNTIME."""
    body = _controller_definition_json()
    import re

    offenders = sorted({
        m for m in re.findall(r'\$\.([A-Za-z_][A-Za-z0-9_]*)', body)
        if m not in ALLOWED_ROOTS
    })
    assert not offenders, (
        "the controller reads top-level JSONPath roots that are neither in the documented execution "
        f"input {sorted(EXECUTION_INPUT_FIELDS)} nor produced by an earlier state: {offenders}. "
        "Referencing a missing path raises States.Runtime and FAILS the execution instead of routing "
        "to ManualReview — seed a default (see SeedInstitution) or produce it upstream.")


def test_seed_institution_precedes_lookup():
    """The optional institution identifiers must be defaulted before LookupCOA runs."""
    body = _controller_definition_json()
    assert "SeedInstitution" in body, "SeedInstitution state is missing"
    assert "$.seeded.institution.school" in body, (
        "LookupCOA must read the SEEDED institution identifiers ($.seeded.institution.school), not "
        "raw $.school which is never present in execution state")
    for seeded in ("$.seeded.selected_for_verification", "$.seeded.required_documents",
                   "$.seeded.received_documents"):
        assert seeded in body, (
            f"{seeded} must be read from the seeded defaults — AssessAid and VerifyDocuments had the "
            "same missing-JSONPath defect as LookupCOA, hidden only because LookupCOA crashed first")
