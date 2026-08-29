"""ComputeStack (EDU port) — the governed tool Lambdas with explicit least-privilege IAM (P0-5/P0-7).

One function per manifest tool target, from a single staged asset bundle (tools + shared controls).
IAM is explicit and minimal per function: the audit writer can only PutItem the ledger + PutObject the
vault (with an explicit Deny on mutation/bypass); mask_pii can only Comprehend-detect + write the
sanitized store; the assessor/guards only read the sanitized store; the drafter only invokes Bedrock.
Exact ARNs are exported — nothing downstream discovers by name (P0-7)."""
import aws_cdk as cdk
from aws_cdk import (aws_ec2 as ec2, aws_iam as iam, aws_kms as kms, aws_lambda as lambda_,
                     aws_logs as logs, aws_secretsmanager as sm)
from constructs import Construct

RUNTIME = lambda_.Runtime.PYTHON_3_12


class ComputeStack(cdk.Stack):
    def __init__(self, scope: Construct, cid: str, *, prefix: str, asset_dir: str, data,
                 provenance_secret: str = "", network=None, tenant: str = "",
                 guardrail_id: str = "", guardrail_version: str = "1",
                 identity=None, approvals_client_id: str = "", **kw):
        super().__init__(scope, cid, **kw)
        code = lambda_.Code.from_asset(asset_dir)
        # Gate-B (customer-managed KMS): when the DataStack was deployed with kms=customer-managed,
        # the SAME CMK protects this stack's secrets, Lambda environment variables, and log groups —
        # one customer-controlled key over every place case data or key material can rest.
        # IMPORTED by ARN (not the concrete Key object): grants then land on the FUNCTION ROLES in
        # this stack instead of rewriting the key policy in the data stack, which would create a
        # cross-stack dependency cycle. Service principals that need the key policy itself (logs,
        # cloudwatch) are pre-authorized in the DataStack key policy.
        cmk = None
        if getattr(data, "cmk", None) is not None:
            cmk = kms.Key.from_key_arn(self, "DataCmk", data.cmk.key_arn)
        common_env = {
            "AUDIT_TABLE": data.audit_table.table_name,
            "WORM_BUCKET": data.worm_bucket.bucket_name,
            # The pinned governed-core evidence writer reads AUDIT_BUCKET
            # (governed_core/controls/evidence.py: _env("AUDIT_BUCKET") or
            # "evidence-worm-<acct>-<region>"). Without this alias the WORM mirror
            # silently no-ops with worm_error=NoSuchBucket (same defect fixed on
            # benefits, cdee12c). WORM_BUCKET kept for anything reading the old name.
            "AUDIT_BUCKET": data.worm_bucket.bucket_name,
            "SANITIZED_TABLE": data.sanitized_table.table_name,
            "PENDING_TABLE": data.pending_table.table_name,
            "CASE_TABLE": data.case_table.table_name,   # R3-2 pass-by-reference store
        }
        # Gate-B B5: the deployment's pinned tenant (one PHA per isolated deployment). Tenant identity
        # is DERIVED from this, never from any request body (lib/controls/tenancy.py).
        if tenant:
            common_env["TENANT_ID"] = tenant
        # Per-deploy signing secrets (P0-1/P0-3-prov + GA-2 key separation). DEFAULT (Review-2): a
        # generated AWS Secrets Manager secret PER TRUST DOMAIN, referenced by ARN — never plaintext in
        # the template. GA-2: the de-identification proof (mask_pii sanitized_ref) and the
        # authoritative-source proof (HUD limits) are signed with DIFFERENT keys, so neither minter can
        # forge the other's trust statement. A context-supplied plaintext secret remains available for
        # disposable sandbox validation ONLY (shared across domains — acceptable in a throwaway
        # sandbox, never in a pilot). HUD API token is a separate operator-filled secret.
        self.signing_secret_deid = None
        self.signing_secret_scorecard = None
        if provenance_secret:
            common_env["PROVENANCE_SECRET"] = provenance_secret   # sandbox-only path (shared)
        else:
            gen = sm.SecretStringGenerator(password_length=64, exclude_punctuation=True)
            self.signing_secret_deid = sm.Secret(
                self, "SigningSecretDeid", secret_name=f"{prefix}/provenance-signing-deid",
                description="GA-2 deid-domain HMAC key: signs mask_pii sanitized-artifact refs ONLY (rotate via new version; consumers re-read on cold start)",
                generate_secret_string=gen, encryption_key=cmk)
            self.signing_secret_scorecard = sm.Secret(
                self, "SigningSecretScorecard", secret_name=f"{prefix}/provenance-signing-scorecard",
                description="GA-2 Scorecard-domain HMAC key: signs College Scorecard REFERENCE-data provenance ONLY (rotate via new version; consumers re-read on cold start)",
                generate_secret_string=gen, encryption_key=cmk)
            common_env["PROVENANCE_SECRET_ARN_DEID"] = self.signing_secret_deid.secret_arn
            common_env["PROVENANCE_SECRET_ARN_SCORECARD"] = self.signing_secret_scorecard.secret_arn
        self.scorecard_key_secret = sm.Secret(
            self, "ScorecardKeySecret", secret_name=f"{prefix}/scorecard-api-key",
            description="api.data.gov key for College Scorecard (operator fills value; DEMO_KEY fallback works for evaluation)",
            encryption_key=cmk,
        )

        def fn(name, handler_module, env=None, timeout=30):
            # Observability parity with benefits (obs review 2026-08-29): the log group is now
            # UNCONDITIONAL — 1-year retention must not be a side effect of the kms switch. CMK
            # encryption (Lambda's implicit log groups are AES-256 only) still applies only with a CMK.
            log_group = logs.LogGroup(
                self, name.replace("-", " ").title().replace(" ", "") + "Logs",
                log_group_name=f"/aws/lambda/{prefix}-{name}",
                encryption_key=cmk, retention=logs.RetentionDays.ONE_YEAR,
                removal_policy=cdk.RemovalPolicy.DESTROY)
            # Gate-B (B1): with a NetworkStack, every governed tool runs in the private app subnets
            # behind the egress firewall — no direct internet path exists from any tool.
            net = {}
            if network is not None:
                net = dict(vpc=network.vpc,
                           vpc_subnets=ec2.SubnetSelection(subnet_group_name="app"),
                           security_groups=[network.lambda_sg])
            f = lambda_.Function(
                self, name.replace("-", " ").title().replace(" ", ""),
                function_name=f"{prefix}-{name}", runtime=RUNTIME, code=code,
                handler=f"{handler_module}.handler",
                timeout=cdk.Duration.seconds(timeout), memory_size=256,
                environment={**common_env, **(env or {})},
                environment_encryption=cmk, log_group=log_group,
                tracing=lambda_.Tracing.ACTIVE,   # X-Ray on every governed tool (obs review 2026-08-29)
                **net,
            )
            if cmk is not None:
                cmk.grant_decrypt(f)   # runtime decrypt of CMK-encrypted env vars (role policy)
            return f

        self.ingest = fn("ingest-case", "ingest_case")   # R3-2: the only door for raw content
        self.intake = fn("intake-fafsa", "intake_fafsa")
        self.lookup = fn("lookup-coa", "lookup_coa")
        self.mask = fn("mask-pii", "mask_pii")
        self.assess = fn("assess-aid", "assess_aid")
        self.verify_docs = fn("verify-documents", "verify_documents")
        self.pj = fn("professional-judgment", "professional_judgment")
        # Guardrail-pinned drafting (G1 parity): aid_core honors GUARDRAIL_ID/VERSION like
        # benefits_core; supplying the platform guardrail makes every generation guardrail-assessed.
        core_env = {}
        if guardrail_id:
            core_env = {"GUARDRAIL_ID": guardrail_id, "GUARDRAIL_VERSION": guardrail_version}
        self.core = fn("core-tools", "aid_core", env=core_env, timeout=60)
        self.write_audit = fn("write-audit", "write_audit")
        self.request_signoff = fn("request-signoff", "request_signoff")
        self.signoff_register = fn("signoff-register", "signoff_register")
        self.finalize = fn("finalize", "finalize_signoff")
        self.guards = fn("workflow-guards", "workflow_guards")
        # approve-signoff (G2 parity): the identity-verifying approve path (Cognito access token,
        # SoD, single-use). governed-core 1.5.0 finalize refuses approvals that did not come through it.
        self.approve_signoff = None
        if identity is not None:
            self.approve_signoff = fn("approve-signoff", "approve_signoff", env={
                "POOL_ID": identity.pool.user_pool_id,
                "CLIENT_ID": approvals_client_id or identity.client.user_pool_client_id,
                "REVIEWER_GROUP": "aid_officer",
            })

        # ── explicit least-privilege wiring ──────────────────────────────────
        # Secrets (Review-2 + GA-2): each domain key readable ONLY by that domain's signer + verifiers.
        # DEID key: mask_pii signs; the sanitized-ref verifiers verify. HUD key: lookup signs; the
        # provenance verifiers (assess, guards) verify. The lookup CANNOT read the deid key and the
        # masker CANNOT read the HUD key — cross-domain forgery is an IAM impossibility, not just a
        # code convention. HUD API token readable ONLY by the lookup. No plaintext in the template.
        if self.signing_secret_deid is not None:
            for f in (self.mask, self.assess, self.pj,
                      self.core, self.guards):
                self.signing_secret_deid.grant_read(f)
        if self.signing_secret_scorecard is not None:
            for f in (self.lookup, self.assess, self.guards):
                self.signing_secret_scorecard.grant_read(f)
        self.scorecard_key_secret.grant_read(self.lookup)
        # R3-2 case store: ingest WRITES raw content; intake + mask READ it (the only two consumers
        # of raw text); the drafter WRITES the notice. Nothing else touches raw content.
        data.case_table.grant(self.ingest, "dynamodb:PutItem")
        data.case_table.grant(self.intake, "dynamodb:GetItem")
        data.case_table.grant(self.mask, "dynamodb:GetItem")
        data.case_table.grant(self.core, "dynamodb:PutItem")
        data.pending_table.grant(self.signoff_register, "dynamodb:PutItem")
        data.pending_table.grant_read_write_data(self.finalize)   # marker read path uses audit table; pending read for ops
        self.lookup.add_environment("SCORECARD_API_KEY_ARN", self.scorecard_key_secret.secret_arn)
        # masking: detect PII + write the sanitized store (PutItem only)
        self.mask.add_to_role_policy(iam.PolicyStatement(
            actions=["comprehend:DetectPiiEntities"], resources=["*"]))
        data.sanitized_table.grant(self.mask, "dynamodb:PutItem")
        # sanitized-store readers (content channel)
        for f in (self.core, self.guards):
            data.sanitized_table.grant(f, "dynamodb:GetItem")
        # drafter: Bedrock only (scoped by inference-profile at deploy via env MODEL_ARNS if narrowed)
        self.core.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel"], resources=["*"]))
        if guardrail_id:
            self.core.add_to_role_policy(iam.PolicyStatement(
                actions=["bedrock:ApplyGuardrail"],
                resources=[f"arn:aws:bedrock:{self.region}:{self.account}:guardrail/{guardrail_id}"]))
        if self.approve_signoff is not None:
            data.pending_table.grant(self.approve_signoff, "dynamodb:GetItem", "dynamodb:UpdateItem")
            self.approve_signoff.add_to_role_policy(iam.PolicyStatement(
                actions=["states:SendTaskSuccess", "states:SendTaskFailure"],
                resources=[f"arn:aws:states:{self.region}:{self.account}:"
                           f"stateMachine:{prefix}-determination-workflow"]))
            data.audit_table.grant(self.approve_signoff, "dynamodb:PutItem",
                                   "dynamodb:GetItem", "dynamodb:TransactWriteItems")
            data.worm_bucket.grant_put(self.approve_signoff)
        # audit writer: append-only + WORM put, with explicit tamper Deny
        data.audit_table.grant(self.write_audit, "dynamodb:PutItem",
                               "dynamodb:GetItem", "dynamodb:TransactWriteItems")
        data.worm_bucket.grant_put(self.write_audit)
        self.write_audit.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.DENY,
            actions=["dynamodb:DeleteItem", "dynamodb:UpdateItem",
                     "s3:DeleteObject", "s3:DeleteObjectVersion",
                     "s3:PutObjectRetention", "s3:PutObjectLegalHold",
                     "s3:BypassGovernanceRetention"],
            resources=[data.audit_table.table_arn,
                       data.worm_bucket.bucket_arn, f"{data.worm_bucket.bucket_arn}/*"]))
        # request_signoff also records INTENT evidence + starts the sign-off machine (arn via env at wire-up)
        data.audit_table.grant(self.request_signoff, "dynamodb:PutItem",
                               "dynamodb:GetItem", "dynamodb:TransactWriteItems")
        data.worm_bucket.grant_put(self.request_signoff)
        # finalize: writes the COMMITTED evidence + the exactly-once FINAL# marker (conditional put)
        data.audit_table.grant(self.finalize, "dynamodb:PutItem",
                               "dynamodb:GetItem", "dynamodb:TransactWriteItems")
        data.worm_bucket.grant_put(self.finalize)

        for name, f in {
            "IngestArn": self.ingest,
            "IntakeArn": self.intake, "LookupArn": self.lookup, "MaskArn": self.mask,
            "AssessArn": self.assess, "CoreArn": self.core, "WriteAuditArn": self.write_audit,
            "RequestSignoffArn": self.request_signoff, "GuardsArn": self.guards,
        }.items():
            cdk.CfnOutput(self, name, value=f.function_arn)   # exact ARNs (P0-7)
