"""WorkflowStack (EDU) — the DETERMINISTIC workflow controller (P0-2) + the human sign-off gate.

The regulated pipeline is a Step Functions STANDARD state machine — the model no longer decides the
compliance sequence. Every transition is gated on machine-verifiable evidence via the workflow_guards
Lambda (provenance signature, sanitized_ref signature, rules output); a failed guard routes to
ManualReview (NEEDS_REVIEW), never onward:

  RECEIVED → Extract → [extracted?] → LookupCOA → [reference_coa?] → Mask → [deidentified?]
    → AssessAid → [rules_executed?] → VerifyDocuments → [verification?] → (hold → VerificationHold)
    → DraftComm → AuditIntent → HumanSignoff (waitForTaskToken, SoD) → COMMITTED
  VerificationHold is a TERMINAL WORK-QUEUE state (34 CFR 668.51-.61): federal aid is held until the
  required documents are received — the pilot's core value path, not an error.

The LLM operates INSIDE bounded steps only (the drafter Lambda invokes Bedrock; extraction is
deterministic). The sign-off gate keeps the existing separation-of-duties semantics: signoff_register
stores the task token for a DIFFERENT verified approver; finalize runs only after approval."""
import aws_cdk as cdk
from aws_cdk import (aws_kms as kms, aws_logs as logs, aws_stepfunctions as sfn,
                     aws_stepfunctions_tasks as tasks)
from constructs import Construct


class WorkflowStack(cdk.Stack):
    def __init__(self, scope: Construct, cid: str, *, prefix: str, compute, data,
                 multitenant: bool = False, **kw):
        super().__init__(scope, cid, **kw)

        # Hybrid multi-tenant (governed-core 1.6.0): the Step Functions hop has NO gateway interceptor,
        # so the acting tenant travels in the execution input as the HMAC-SIGNED pair (minted by the
        # tenanted caller that started the execution via ingest-case) and is threaded into EVERY Lambda
        # payload; each Lambda re-verifies the signature before routing to that tenant's ledger / vault /
        # approvals register. An execution started WITHOUT the pair fails at the first state
        # (States.Runtime on the missing path) — fail-closed, never a silent write to the base stores.
        # Phase 110 (1.7.0): the execution ARN is threaded ALWAYS so every aegis.call line + WORM record
        # joins back to this execution and its X-Ray trace.
        tenant_fields = ({"__aegis_tenant.$": "$.__aegis_tenant",
                          "__aegis_tenant_sig.$": "$.__aegis_tenant_sig"} if multitenant else {})
        tenant_fields = {**tenant_fields, "__aegis_execution.$": "$$.Execution.Id"}

        def invoke(name, fn, payload, result_path):
            return tasks.LambdaInvoke(self, name, lambda_function=fn,
                                      payload=sfn.TaskInput.from_object({**payload, **tenant_fields}),
                                      result_selector={"out.$": "$.Payload"},
                                      result_path=result_path)

        def guard(name, guard_name, payload):
            return tasks.LambdaInvoke(self, name, lambda_function=compute.guards,
                                      payload=sfn.TaskInput.from_object(
                                          {"guard": guard_name, **payload, **tenant_fields}),
                                      result_selector={"ok.$": "$.Payload.ok",
                                                       "reason.$": "$.Payload.reason"},
                                      result_path=f"$.guards.{guard_name}")

        manual_review = sfn.Succeed(self, "ManualReview",
                                    comment="Fail-closed: evidence missing/unverified -> NEEDS_REVIEW "
                                            "for an aid officer; no automated outcome.")

        # R3-2 ZERO-PII STATE: the execution is started with {case_id, requester, case_ref} — the
        # raw application NEVER enters Step Functions state (it lives in the encrypted case store;
        # `scripts/`/the intake API call the ingest-case Lambda first). The canary's strict gate
        # (`pii_canary.py --strict`) holds the controller to zero content in execution history.
        extract = invoke("Extract", compute.intake,
                         {"case_ref.$": "$.case_ref"}, "$.extract")
        g_extracted = guard("GuardExtracted", "extracted", {"fields.$": "$.extract.out.fields"})

        # The execution input contract is {case_id, requester, case_ref} (see the R3-2 note above), so
        # `$.school` / `$.unitid` are NOT in state. Referencing them directly made LookupCOA raise
        # States.Runtime ("The JSONPath '$.school' ... could not be found in the input") and the whole
        # execution FAILED — the exact "brittle JSONPath turns fail-closed into a runtime error" trap
        # called out on the guard below, committed on the input side. Found by running the documented
        # command on a live deployment (fa-val2, 2026-07-28).
        #
        # Seeding defaults keeps the optional identifiers resolvable. An unidentified (or source-down)
        # lookup returns NO signed provenance token, so GuardReferenceCOA routes to ManualReview —
        # fail CLOSED by design, and now actually reachable instead of crashing first.
        # THREE states had this defect, not one. LookupCOA crashed first, which masked the other two:
        # AssessAid reads $.selected_for_verification and VerifyDocuments reads $.required_documents /
        # $.received_documents — none of which are in the {case_id, requester, case_ref} contract
        # either. Fixing only LookupCOA would have moved the same crash downstream.
        #
        # `selected_for_verification` defaults to TRUE deliberately: absent an explicit caller value,
        # route the case through 34 CFR 668 verification (the stricter path) rather than silently
        # skipping it. Defaulting to false would fail OPEN.
        seed_institution = sfn.Pass(
            self, "SeedInstitution",
            comment="Default the OPTIONAL caller-supplied inputs so no downstream state can raise "
                    "States.Runtime on a missing JSONPath. No institution identifier -> unsigned "
                    "lookup -> GuardReferenceCOA -> ManualReview. selected_for_verification defaults "
                    "TRUE (stricter path) so a missing value cannot skip verification.",
            parameters={
                "institution": {"school": "", "unitid": ""},
                "selected_for_verification": True,
                "required_documents": [],
                "received_documents": [],
            },
            result_path="$.seeded")

        lookup = invoke("LookupCOA", compute.lookup,
                        {"school.$": "$.seeded.institution.school",
                         "unitid.$": "$.seeded.institution.unitid"}, "$.lookup")
        # Pass the WHOLE lookup output: a source-down lookup has no coa keys, and judging that is
        # the guard's job — a brittle JSONPath here would turn fail-closed into a runtime error.
        g_coa = guard("GuardReferenceCOA", "reference_coa", {"lookup.$": "$.lookup.out"})

        mask = invoke("MaskPii", compute.mask, {"case_ref.$": "$.case_ref"}, "$.mask")
        g_deid = guard("GuardDeidentified", "deidentified",
                       {"sanitized_ref.$": "$.mask.out.sanitized_ref"})

        assess = invoke("AssessAid", compute.assess,
                        {"student_aid_index.$": "$.extract.out.fields.student_aid_index",
                         "cost_of_attendance.$": "$.lookup.out.cost_of_attendance",
                         "enrollment_status.$": "$.extract.out.fields.enrollment_status",
                         "sap_gpa.$": "$.extract.out.fields.sap_gpa",
                         "sap_pace.$": "$.extract.out.fields.sap_pace",
                         "selected_for_verification.$": "$.seeded.selected_for_verification",
                         "coa_source.$": "$.lookup.out.coa_source",
                         "deidentified": True, "sanitized_ref.$": "$.mask.out.sanitized_ref"},
                        "$.assessment")
        g_rules = guard("GuardRulesExecuted", "rules_executed", {"assessment.$": "$.assessment.out"})

        # 34 CFR 668 verification: document completeness decides whether the case may proceed to a
        # drafted communication or HOLDS as an aid-office work-queue item.
        verify_docs = invoke("VerifyDocuments", compute.verify_docs,
                             {"case_id.$": "$.case_id",
                              "required_documents.$": "$.seeded.required_documents",
                              "received_documents.$": "$.seeded.received_documents"}, "$.documents")
        g_verify = guard("GuardVerification", "verification",
                         {"assessment.$": "$.assessment.out", "documents.$": "$.documents.out"})
        verification_hold = sfn.Succeed(
            self, "VerificationHold",
            comment="TERMINAL WORK QUEUE (not an error): aid held pending required verification "
                    "documents (34 CFR 668.51-.61); the aid office works the hold and re-runs the case.")

        # R3-2: no content in the payload — the drafter loads the masked text SERVER-SIDE from the
        # sanitized-artifact store via the signed ref, and returns notice_ref (not the notice text).
        draft = invoke("DraftNotice", compute.core,
                       {"determination.$": "States.JsonToString($.assessment.out)",
                        "deidentified": True, "sanitized_ref.$": "$.mask.out.sanitized_ref"},
                       "$.draft")
        audit_intent = invoke("AuditIntent", compute.write_audit,
                              {"icsr_id.$": "$.case_id", "action": "determination",
                               "phase": "INTENT", "actor": "workflow-controller",
                               "payload.$": "States.JsonToString($.assessment.out)"},
                              "$.audit")

        signoff = tasks.LambdaInvoke(
            self, "HumanSignoff", lambda_function=compute.signoff_register,
            integration_pattern=sfn.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
            payload=sfn.TaskInput.from_object(
                {"icsr_id.$": "$.case_id", "requester.$": "$.requester",
                 # GA-5: bind the approval to the EXACT assessment content the approver saw
                 "content_hash.$": "States.Hash(States.JsonToString($.assessment.out), 'SHA-256')",
                 "taskToken": sfn.JsonPath.task_token, **tenant_fields}),
            timeout=cdk.Duration.hours(24), result_path="$.approval")
        finalize = invoke("Finalize", compute.finalize,
                          {"icsr_id.$": "$.case_id", "requester.$": "$.requester",
                           "approver.$": "$.approval.approver"}, "$.commit")
        committed = sfn.Succeed(self, "Committed")

        # explicit chain with fail-closed choices; the verification choice routes HOLDS to the
        # VerificationHold work queue (terminal), never onward to a drafted communication.
        c1 = sfn.Choice(self, "ExtractedOk").when(
            sfn.Condition.boolean_equals("$.guards.extracted.ok", True),
            seed_institution).otherwise(manual_review)
        c2 = sfn.Choice(self, "ReferenceCoaOk").when(
            sfn.Condition.boolean_equals("$.guards.reference_coa.ok", True), mask).otherwise(manual_review)
        c3 = sfn.Choice(self, "DeidentifiedOk").when(
            sfn.Condition.boolean_equals("$.guards.deidentified.ok", True), assess).otherwise(manual_review)
        c4 = sfn.Choice(self, "RulesOk").when(
            sfn.Condition.boolean_equals("$.guards.rules_executed.ok", True), verify_docs).otherwise(manual_review)
        c5 = sfn.Choice(self, "VerificationClear").when(
            sfn.Condition.boolean_equals("$.guards.verification.ok", True), draft).otherwise(verification_hold)
        # G1 parity: a guardrail-BLOCKED or errored draft must not reach the sign-off gate.
        c6 = sfn.Choice(self, "DraftOk").when(
            sfn.Condition.or_(sfn.Condition.is_present("$.draft.out.notice_ref"),
                              sfn.Condition.is_present("$.draft.out.notice")),
            audit_intent).otherwise(manual_review)
        # G2 parity: a finalize that refuses (approval path unverified / SoD) routes to ManualReview.
        c7 = sfn.Choice(self, "FinalizeOk").when(
            sfn.Condition.boolean_equals("$.commit.out.committed", True),
            committed).otherwise(manual_review)

        definition = (extract.next(g_extracted).next(c1))
        seed_institution.next(lookup)
        lookup.next(g_coa).next(c2)
        mask.next(g_deid).next(c3)
        assess.next(g_rules).next(c4)
        verify_docs.next(g_verify).next(c5)
        draft.next(c6)
        audit_intent.next(signoff).next(finalize).next(c7)

        # Observability parity (obs review 2026-08-29): retained (1y) execution logging + X-Ray.
        # include_execution_data=False keeps case payloads out of the log stream (R3-2). CMK when present.
        wf_cmk = None
        if getattr(data, "cmk", None) is not None:
            wf_cmk = kms.Key.from_key_arn(self, "WfCmk", data.cmk.key_arn)
        wf_logs = logs.LogGroup(
            self, "ControllerLogs", log_group_name=f"/aws/states/{prefix}-determination-workflow",
            encryption_key=wf_cmk, retention=logs.RetentionDays.ONE_YEAR,
            removal_policy=cdk.RemovalPolicy.DESTROY)
        self.controller = sfn.StateMachine(
            self, "Controller", state_machine_name=f"{prefix}-determination-workflow",
            definition_body=sfn.DefinitionBody.from_chainable(definition),
            state_machine_type=sfn.StateMachineType.STANDARD,
            timeout=cdk.Duration.hours(25),
            tracing_enabled=True,
            logs=sfn.LogOptions(destination=wf_logs, level=sfn.LogLevel.ALL,
                                include_execution_data=False),
        )
        cdk.CfnOutput(self, "ControllerArn", value=self.controller.state_machine_arn)
