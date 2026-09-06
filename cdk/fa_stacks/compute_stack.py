"""ComputeStack (EDU port) — the governed tool Lambdas with explicit least-privilege IAM (P0-5/P0-7).

One function per manifest tool target, from a single staged asset bundle (tools + shared controls).
IAM is explicit and minimal per function: the audit writer can only PutItem the ledger + PutObject the
vault (with an explicit Deny on mutation/bypass); mask_pii can only Comprehend-detect + write the
sanitized store; the assessor/guards only read the sanitized store; the drafter only invokes Bedrock.
Exact ARNs are exported — nothing downstream discovers by name (P0-7).

GA-2 — EDU has TWO authoritative-signing trust domains (deid: mask_pii signs the sanitized_ref;
scorecard: lookup_coa signs the College-Scorecard reference figure), each with its OWN HMAC key so
neither minter can forge the other's proof. Hybrid multi-tenant (governed-core 1.6.0+) adds a THIRD,
tenant-signing key used only by tenancy (the interceptor signs the tenant pair; every tenant-routing
Lambda verifies it). The tenant key is the legacy/shared PROVENANCE_SECRET slot, which the domain
signers never use when their domain key is configured (provenance._secret checks the domain first), so
GA-2 is preserved: a tenant-key holder cannot forge a deid or scorecard proof. A context-supplied
plaintext secret (sandbox validation ONLY) is shared across all three domains."""
import aws_cdk as cdk
from aws_cdk import (aws_bedrock as bedrock, aws_dynamodb as ddb, aws_ec2 as ec2, aws_iam as iam, aws_kms as kms,
                     aws_lambda as lambda_, aws_logs as logs, aws_secretsmanager as sm, aws_ssm as ssm)
from constructs import Construct

RUNTIME = lambda_.Runtime.PYTHON_3_12


def drafter_role_name(prefix):
    """The governed drafter's PINNED IAM role name - the single principal every perimeter layer admits
    (Bedrock VPC-endpoint policy, org SCP/VPCE templates, bypass-alarm allowlist). L12 (PAR-1 port)."""
    return f"{prefix}-compute-coretools"


class ComputeStack(cdk.Stack):
    def __init__(self, scope: Construct, cid: str, *, prefix: str, asset_dir: str, data,
                 provenance_secret: str = "", network=None, tenant: str = "",
                 guardrail_id: str = "", guardrail_version: str = "1", guardrail_config: dict = None,
                 identity=None, approvals_client_id: str = "", multitenant: bool = False,
                 global_kill_switch: str = "", budget: dict = None, runtime_name: str = "", **kw):
        super().__init__(scope, cid, **kw)
        # RT-3 (port from benefits, 2026-09-06): the IaC runtime execution role scopes its resources to
        # the runtime name and the deployment's SSM root / kill switch.
        self._runtime_name = runtime_name or "financial_aid_runtime_agent"
        self._global_kill_switch = global_kill_switch
        code = lambda_.Code.from_asset(asset_dir)

        # ── #166: Bedrock Guardrail as IaC (PAR-1 port from benefits, 2026-09-06) ─────────────
        # If an external guardrail id is supplied (-c guardrail_id) it wins (platform-managed guardrail);
        # otherwise create the guardrail here from the manifest `guardrail:` block so a from-zero CDK
        # deploy is self-contained. PII entities -> ANONYMIZE, prompt-attack -> the declared strength.
        # A published version is created and PINNED (never DRAFT) so the drafter assesses against an
        # immutable version; the drafter fails closed on ANY guardrail_intervened.
        gcfg = guardrail_config or {}
        self.guardrail = None
        self.guardrail_arn = ""
        if not guardrail_id and gcfg.get("name"):
            pa = (gcfg.get("prompt_attack") or "HIGH").upper()
            pii = [{"type": t, "action": "ANONYMIZE"} for t in gcfg.get("pii_anonymize", [])]
            # #150/#190: contextual grounding policy from the manifest `grounding:` thresholds. GROUNDING
            # scores how well the drafted text is supported by the grounding_source; RELEVANCE how well it
            # answers the query. The drafter tags its Converse content with those qualifiers and fails
            # closed on intervention. L14: the deterministic assessment travels INTO the grounding source
            # (see the drafter), otherwise a stated determination is legitimately ungrounded.
            gnd = gcfg.get("grounding") or {}
            grounding_filters = []
            if gnd.get("grounding_threshold") is not None:
                grounding_filters.append(bedrock.CfnGuardrail.ContextualGroundingFilterConfigProperty(
                    type="GROUNDING", threshold=float(gnd["grounding_threshold"])))
            if gnd.get("relevance_threshold") is not None:
                grounding_filters.append(bedrock.CfnGuardrail.ContextualGroundingFilterConfigProperty(
                    type="RELEVANCE", threshold=float(gnd["relevance_threshold"])))
            self.guardrail = bedrock.CfnGuardrail(
                self, "Guardrail",
                name=f"{prefix}-{gcfg['name']}",
                description=gcfg.get("description", "Aegis financial-aid output guardrail (IaC)"),
                blocked_input_messaging="Blocked by the Aegis financial-aid guardrail.",
                blocked_outputs_messaging="[Output withheld by the Aegis financial-aid guardrail.]",
                content_policy_config=bedrock.CfnGuardrail.ContentPolicyConfigProperty(
                    filters_config=[bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        type="PROMPT_ATTACK", input_strength=pa, output_strength="NONE")]),
                sensitive_information_policy_config=(
                    bedrock.CfnGuardrail.SensitiveInformationPolicyConfigProperty(
                        pii_entities_config=[bedrock.CfnGuardrail.PiiEntityConfigProperty(
                            type=e["type"], action=e["action"]) for e in pii]) if pii else None),
                contextual_grounding_policy_config=(
                    bedrock.CfnGuardrail.ContextualGroundingPolicyConfigProperty(
                        filters_config=grounding_filters) if grounding_filters else None),
            )
            # A guardrail VERSION is an immutable snapshot; CfnGuardrailVersion does NOT auto-republish
            # when the policies change (found live on benefits 2026-09-05). A config signature in the
            # description makes a policy change replace the version -> fresh published version.
            _cfg_sig = "pa=%s;pii=%d;gnd=%s;rel=%s" % (
                pa, len(pii), gnd.get("grounding_threshold"), gnd.get("relevance_threshold"))
            ver = bedrock.CfnGuardrailVersion(self, "GuardrailVersion",
                                              guardrail_identifier=self.guardrail.attr_guardrail_id,
                                              description="aegis-guardrail cfg " + _cfg_sig)
            guardrail_id = self.guardrail.attr_guardrail_id
            guardrail_version = ver.attr_version
            self.guardrail_arn = self.guardrail.attr_guardrail_arn
            cdk.CfnOutput(self, "GuardrailId", value=guardrail_id)
            cdk.CfnOutput(self, "GuardrailVersionOut", value=guardrail_version, export_name=None)
            cdk.CfnOutput(self, "GuardrailArnOut", value=self.guardrail_arn)
        cmk = None
        if getattr(data, "cmk", None) is not None:
            cmk = kms.Key.from_key_arn(self, "DataCmk", data.cmk.key_arn)

        # ── Kill Switch (task 127, governed-core 1.8.0) ──────────────────────
        # ONE SSM Parameter Store flag per deployment, under the same root as the gateway-discovery
        # parameter (/<prefix>-aid/*) so the Runtime's existing ssm:GetParameter grant covers it. Every
        # governed Lambda (incl. the gateway interceptor) and the Runtime read it FIRST, fail-closed,
        # with a 15 s in-process TTL cache. Optional -c global_kill_switch=/aegis/kill-switch adds the
        # platform-wide parameter (engaged if EITHER is engaged). Only the two controller functions
        # below may write the deployment parameter — nothing else in this app holds ssm:PutParameter.
        ks_name = f"/{prefix}-aid/kill-switch"
        self.kill_switch_param = ssm.StringParameter(
            self, "KillSwitchParam", parameter_name=ks_name,
            string_value='{"engaged": false, "actor": "", "reason": "", "at": 0}',
            description="EDU financial-aid pack Kill Switch (containment). engaged=true => every agent "
                        "action is refused: gateway interceptor 403 + WORM DENIED record, tool Lambdas "
                        "refuse, Runtime refuses. Change ONLY via the engage/disengage function URLs "
                        "(IAM-verified actor, separation of duties). docs/ops/KILL-SWITCH.md")
        kill_params = [ks_name]
        kill_param_arns = [self.kill_switch_param.parameter_arn]
        if global_kill_switch:
            kill_params.append(global_kill_switch)
            kill_param_arns.append(f"arn:aws:ssm:{self.region}:{self.account}:parameter{global_kill_switch}")

        # ── Budget meter (task 128, governed-core 1.9.0) ────────────────────
        # ONE DynamoDB table per deployment: <tenant>#<YYYY-MM> -> used / tokens / usd_micro (+ optional
        # per-tenant cap overrides). DEFAULTS from the manifest budget: block (B5) + -c budget_usd; the
        # pinned price table (lib/model_prices.json) is inlined so every commit records its price_version.
        budget = budget or {}
        self.budgets_table = ddb.Table(
            self, "Budgets", table_name=f"{prefix}-budgets",
            partition_key=ddb.Attribute(name="budget_key", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST, encryption_key=cmk,
            encryption=ddb.TableEncryption.CUSTOMER_MANAGED if cmk else ddb.TableEncryption.AWS_MANAGED,
            removal_policy=cdk.RemovalPolicy.DESTROY)
        budget_env = {
            "BUDGET_TABLE": self.budgets_table.table_name,
            "BUDGET_CAP_TOKENS": str(int(budget.get("monthly_token_cap") or 0)),
            "BUDGET_CAP_USD_MICRO": str(int(round(float(budget.get("monthly_usd") or 0) * 1_000_000))),
            "BUDGET_BEHAVIOR": str(budget.get("cap_behavior") or "hard"),
            "BUDGET_RESERVE_TOKENS": str(int(budget.get("reserve_tokens") or 4000)),
            "BUDGET_PRICES_JSON": budget.get("prices_json") or "",
            "BUDGET_DEPLOYMENT": prefix,
        }

        common_env = {
            **budget_env,
            "KILL_SWITCH_PARAMS": ",".join(kill_params),
            "KILL_SWITCH_TTL_SECONDS": "15",
            "AUDIT_TABLE": data.audit_table.table_name,
            "WORM_BUCKET": data.worm_bucket.bucket_name,
            # The pinned governed-core evidence writer reads AUDIT_BUCKET; without this alias the WORM
            # mirror silently no-ops with worm_error=NoSuchBucket (same defect fixed on benefits/PV).
            "AUDIT_BUCKET": data.worm_bucket.bucket_name,
            "SANITIZED_TABLE": data.sanitized_table.table_name,
            "PENDING_TABLE": data.pending_table.table_name,
            "CASE_TABLE": data.case_table.table_name,   # R3-2 pass-by-reference store
        }
        if tenant:
            common_env["TENANT_ID"] = tenant
        # Hybrid multi-tenant (phase 107): tenant is derived per request from the gateway interceptor's
        # HMAC-signed injection (never the pinned env); MULTITENANT=1 makes the routing fail-closed.
        if multitenant:
            common_env["MULTITENANT"] = "1"
            # governed-core 1.6.0: the canonical evidence writer routes the WORM copy to the acting
            # tenant's OWN Object Lock vault. Template = the exact per-tenant DataStack naming.
            common_env["WORM_BUCKET_TEMPLATE"] = f"{prefix}-{{tenant}}-worm-{self.account}"

        # Per-deploy signing secrets (P0-1/P0-3-prov + GA-2 key separation + tenant signing). DEFAULT
        # (Review-2): generated AWS Secrets Manager secrets referenced by ARN — never plaintext. A
        # context-supplied plaintext secret is disposable-sandbox ONLY (shared across all three domains).
        self.signing_secret_deid = None
        self.signing_secret_scorecard = None
        self.signing_secret_tenant = None
        if provenance_secret:
            common_env["PROVENANCE_SECRET"] = provenance_secret   # sandbox-only path (shared: deid+scorecard+tenant)
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
            # Tenant-signing key (hybrid multi-tenant): the legacy/shared PROVENANCE_SECRET slot tenancy
            # falls back to (domain=None). Domain signers never use it while their domain key is set, so
            # GA-2 holds — a tenant-key holder cannot forge a deid/scorecard proof.
            self.signing_secret_tenant = sm.Secret(
                self, "SigningSecretTenant", secret_name=f"{prefix}/provenance-signing-tenant",
                description="Tenant-domain HMAC key: signs/verifies the interceptor-injected tenant pair ONLY (governed-core tenancy; GA-2-separate from the deid/scorecard keys)",
                generate_secret_string=gen, encryption_key=cmk)
            common_env["PROVENANCE_SECRET_ARN"] = self.signing_secret_tenant.secret_arn
        self.scorecard_key_secret = sm.Secret(
            self, "ScorecardKeySecret", secret_name=f"{prefix}/scorecard-api-key",
            description="api.data.gov key for College Scorecard (operator fills value; DEMO_KEY fallback works for evaluation)",
            encryption_key=cmk)

        def fn(name, handler_module, env=None, timeout=30):
            log_group = logs.LogGroup(
                self, name.replace("-", " ").title().replace(" ", "") + "Logs",
                log_group_name=f"/aws/lambda/{prefix}-{name}",
                encryption_key=cmk, retention=logs.RetentionDays.ONE_YEAR,
                removal_policy=cdk.RemovalPolicy.DESTROY)
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
                tracing=lambda_.Tracing.ACTIVE,
                **net)
            if cmk is not None:
                cmk.grant_decrypt(f)
            f.add_to_role_policy(iam.PolicyStatement(
                sid="ReadKillSwitch", actions=["ssm:GetParameter"], resources=kill_param_arns))
            return f

        # Hybrid multi-tenant ingestion boundary (governed-core 1.6.0): ingest is NOT a gateway tool
        # (direct IAM invocation), so there is no interceptor to derive the tenant. In multi-tenant mode
        # it derives the tenant from a VERIFIED Cognito access token of a tenant member and mints the
        # signed pair the workflow carries. Unused in silo mode.
        ingest_env = ({"POOL_ID": identity.pool.user_pool_id,
                       "CLIENT_ID": approvals_client_id or identity.client.user_pool_client_id,
                       "REVIEWER_GROUP": "aid_officer"}
                      if (multitenant and identity is not None) else None)
        self.ingest = fn("ingest-case", "ingest_case", env=ingest_env)   # R3-2: the only door for raw content
        self.intake = fn("intake-fafsa", "intake_fafsa")
        self.lookup = fn("lookup-coa", "lookup_coa")
        self.mask = fn("mask-pii", "mask_pii")
        self.assess = fn("assess-aid", "assess_aid")
        self.verify_docs = fn("verify-documents", "verify_documents")
        self.pj = fn("professional-judgment", "professional_judgment")
        # Guardrail-pinned drafting (G1 parity): aid_core honors GUARDRAIL_ID/VERSION like benefits_core.
        core_env = {}
        if guardrail_id:
            core_env = {"GUARDRAIL_ID": guardrail_id, "GUARDRAIL_VERSION": guardrail_version}
        self.core = fn("core-tools", "aid_core", env=core_env, timeout=60)
        # Live-found L12 in the benefits Tier-1 gate (2026-09-06): the Bedrock VPC-endpoint policy and the
        # org SCP/VPCE templates admit the drafter BY ROLE ARN, but a CDK-generated role name
        # (<prefix>-compute-CoreToolsServiceRole<hash>-<rand>) is neither predictable nor the case the
        # pattern guessed (ArnLike is case-sensitive). Pin the physical name so every perimeter layer
        # can name the EXACT principal - no wildcard, no case guessing. Immutable: changing it replaces
        # the role (fine for a fresh deploy; a pilot re-deploy is a role replacement, documented).
        self.core.role.node.default_child.add_property_override("RoleName", drafter_role_name(prefix))
        self.drafter_role_arn = f"arn:aws:iam::{self.account}:role/{drafter_role_name(prefix)}"
        self.write_audit = fn("write-audit", "write_audit")
        self.request_signoff = fn("request-signoff", "request_signoff")
        self.signoff_register = fn("signoff-register", "signoff_register")
        self.finalize = fn("finalize", "finalize_signoff")
        self.guards = fn("workflow-guards", "workflow_guards")
        # Phase 107: the AgentCore Gateway REQUEST interceptor — derives the tenant from the VALIDATED
        # JWT and injects it HMAC-signed for the targets (a pass-through in silo mode).
        self.tenant_interceptor = fn("tenant-interceptor", "tenant_interceptor")
        # approve-signoff (G2 parity): the human approver's out-of-band door (Cognito access token, SoD,
        # single-use). governed-core finalize refuses approvals that did not come through it.
        self.approve_signoff = None
        if identity is not None:
            self.approve_signoff = fn("approve-signoff", "approve_signoff", env={
                "POOL_ID": identity.pool.user_pool_id,
                "CLIENT_ID": approvals_client_id or identity.client.user_pool_client_id,
                "REVIEWER_GROUP": "aid_officer"})

        # ── Kill Switch controller (task 127): TWO functions from ONE governed-core module, each behind
        # a Lambda FUNCTION URL with AuthType AWS_IAM — the actor recorded in the parameter + WORM ledger
        # is the IAM-verified caller, and SoD on release is enforced on that identity. IAM SoD: two
        # managed policies (engage-only / disengage-only), assigned to different roles by the runbook.
        self.kill_switch_fns = {}
        self.kill_switch_urls = {}
        self.kill_switch_policies = {}
        for mode in ("engage", "disengage"):
            f = fn(f"kill-switch-{mode}", "kill_switch_control",
                   env={"KILL_SWITCH_MODE": mode, "KILL_SWITCH_PARAM": ks_name})
            f.add_to_role_policy(iam.PolicyStatement(
                sid="WriteKillSwitch", actions=["ssm:PutParameter"],
                resources=[self.kill_switch_param.parameter_arn]))
            data.audit_table.grant(f, "dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:TransactWriteItems")
            data.worm_bucket.grant_put(f)
            url = f.add_function_url(auth_type=lambda_.FunctionUrlAuthType.AWS_IAM)
            pol = iam.ManagedPolicy(
                self, f"KillSwitch{mode.title()}Policy",
                managed_policy_name=f"{prefix}-killswitch-{mode}",
                description=f"Grants ONLY lambda:InvokeFunctionUrl on the {mode} function of the "
                            f"{prefix} Kill Switch (AWS_IAM function URL). Assign to a different role "
                            f"than the other mode (separation of duties).",
                statements=[iam.PolicyStatement(
                    sid=f"{mode.title()}KillSwitch",
                    actions=["lambda:InvokeFunctionUrl", "lambda:InvokeFunction"],
                    resources=[f.function_arn],
                    conditions={"StringEquals": {"lambda:FunctionUrlAuthType": "AWS_IAM"},
                                "Bool": {"lambda:InvokedViaFunctionUrl": "true"}})])
            self.kill_switch_fns[mode], self.kill_switch_urls[mode], self.kill_switch_policies[mode] = f, url, pol
        # The gateway interceptor writes a DENIED record for every refused call into the acting tenant's
        # ledger + vault (mirror grants below in multi-tenant mode), base stores in silo mode.
        data.audit_table.grant(self.tenant_interceptor, "dynamodb:PutItem", "dynamodb:GetItem",
                               "dynamodb:TransactWriteItems")
        data.worm_bucket.grant_put(self.tenant_interceptor)
        # Budget meter grants (least privilege): the interceptor only READS the meter (check); the drafter
        # (server-side Bedrock call) READS + UPDATES it (commit) and publishes the Aegis/Budget metrics.
        self.budgets_table.grant(self.tenant_interceptor, "dynamodb:GetItem")
        self.budgets_table.grant(self.core, "dynamodb:GetItem", "dynamodb:UpdateItem")
        self.core.add_to_role_policy(iam.PolicyStatement(
            sid="BudgetMetrics", actions=["cloudwatch:PutMetricData"], resources=["*"],
            conditions={"StringEquals": {"cloudwatch:namespace": "Aegis/Budget"}}))
        # The drafter refuses on the WORKFLOW hop (no interceptor in front of a Step Functions task), so
        # its budget / kill-switch refusals must land as DENIED records too: the same append-only ledger
        # grant the interceptor has (Put + Get head + TransactWrite; no Update/Delete).
        data.audit_table.grant(self.core, "dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:TransactWriteItems")
        data.worm_bucket.grant_put(self.core)

        # ── explicit least-privilege wiring ──────────────────────────────────
        # GA-2 secrets: each domain key readable ONLY by that domain's signer + verifiers. DEID: mask_pii
        # signs; the sanitized-ref verifiers verify. SCORECARD: lookup signs; the provenance verifiers
        # verify. Cross-domain forgery is an IAM impossibility, not just a code convention.
        if self.signing_secret_deid is not None:
            for f in (self.mask, self.assess, self.pj, self.core, self.guards):
                self.signing_secret_deid.grant_read(f)
        if self.signing_secret_scorecard is not None:
            for f in (self.lookup, self.assess, self.guards):
                self.signing_secret_scorecard.grant_read(f)
        # Tenant-signing key: the interceptor SIGNS the tenant pair; every tenant-routing Lambda VERIFIES
        # it (ingest also signs the pair the workflow carries). Only granted in multi-tenant mode.
        if self.signing_secret_tenant is not None and multitenant:
            for f in (self.tenant_interceptor, self.ingest, self.intake, self.mask, self.assess,
                      self.pj, self.lookup, self.core, self.guards, self.write_audit,
                      self.request_signoff, self.signoff_register, self.finalize, self.approve_signoff):
                if f is not None:
                    self.signing_secret_tenant.grant_read(f)
        self.scorecard_key_secret.grant_read(self.lookup)
        self.lookup.add_environment("SCORECARD_API_KEY_ARN", self.scorecard_key_secret.secret_arn)
        # R3-2 case store: ingest WRITES raw content; intake + mask READ it; the drafter WRITES the notice.
        data.case_table.grant(self.ingest, "dynamodb:PutItem")
        data.case_table.grant(self.intake, "dynamodb:GetItem")
        data.case_table.grant(self.mask, "dynamodb:GetItem")
        data.case_table.grant(self.core, "dynamodb:PutItem")
        data.pending_table.grant(self.signoff_register, "dynamodb:PutItem")
        data.pending_table.grant_read_write_data(self.finalize)
        # masking: detect PII + write the sanitized store (PutItem only)
        self.mask.add_to_role_policy(iam.PolicyStatement(
            actions=["comprehend:DetectPiiEntities"], resources=["*"]))
        data.sanitized_table.grant(self.mask, "dynamodb:PutItem")
        # sanitized-store readers (content channel)
        for f in (self.core, self.guards):
            data.sanitized_table.grant(f, "dynamodb:GetItem")
        # drafter: Bedrock only. MANDATORY-GUARDRAIL IAM CONDITION (external review; RT-3 port): with a
        # guardrail configured, model invocations are DENIED unless the request carries a guardrail
        # (Null present-check on bedrock:GuardrailIdentifier) - an ungoverned drafter call cannot bypass it.
        _has_guardrail = bool(guardrail_id)
        self.core.add_to_role_policy(iam.PolicyStatement(
            sid="DrafterBedrockGuardrailRequired" if _has_guardrail else "DrafterBedrock",
            actions=["bedrock:InvokeModel"], resources=["*"],
            conditions=({"Null": {"bedrock:GuardrailIdentifier": "false"}} if _has_guardrail else None)))
        self.runtime_role = self._runtime_execution_role(prefix, _has_guardrail, guardrail_id)
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
        # request_signoff records INTENT evidence + starts the sign-off machine
        data.audit_table.grant(self.request_signoff, "dynamodb:PutItem",
                               "dynamodb:GetItem", "dynamodb:TransactWriteItems")
        data.worm_bucket.grant_put(self.request_signoff)
        # finalize: writes the COMMITTED evidence + the exactly-once FINAL# marker (conditional put)
        data.audit_table.grant(self.finalize, "dynamodb:PutItem",
                               "dynamodb:GetItem", "dynamodb:TransactWriteItems")
        data.worm_bucket.grant_put(self.finalize)

        # ── Hybrid multi-tenant (phase 107/109) ─────────────────────────────
        # The SAME least-privilege actions, mirrored onto EVERY tenant's own store inside this prefix
        # (<prefix>-<tenant>-<logical>), routed per request by tenancy.route_store; the audit tamper DENY
        # is mirrored onto every tenant's ledger + vault.
        if multitenant:
            def _tbl(logical):
                base = f"arn:aws:dynamodb:{self.region}:{self.account}:table/{prefix}-*-{logical}"
                return [base, f"{base}/index/*"]
            worm = [f"arn:aws:s3:::{prefix}-*-worm-*", f"arn:aws:s3:::{prefix}-*-worm-*/*"]

            def _mt(fn_, resources, *actions):
                fn_.add_to_role_policy(iam.PolicyStatement(actions=list(actions), resources=resources))
            RW = ["dynamodb:GetItem", "dynamodb:BatchGetItem", "dynamodb:Query", "dynamodb:Scan",
                  "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem",
                  "dynamodb:BatchWriteItem", "dynamodb:ConditionCheckItem", "dynamodb:DescribeTable"]
            AUD = ["dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:TransactWriteItems"]
            _mt(self.ingest, _tbl("case-store"), "dynamodb:PutItem")
            _mt(self.intake, _tbl("case-store"), "dynamodb:GetItem")
            _mt(self.mask, _tbl("case-store"), "dynamodb:GetItem")
            _mt(self.core, _tbl("case-store"), "dynamodb:PutItem")
            _mt(self.signoff_register, _tbl("pending-approvals"), "dynamodb:PutItem")
            _mt(self.finalize, _tbl("pending-approvals"), *RW)
            _mt(self.mask, _tbl("sanitized-artifacts"), "dynamodb:PutItem")
            for f in (self.core, self.guards):
                _mt(f, _tbl("sanitized-artifacts"), "dynamodb:GetItem")
            for f in (self.write_audit, self.request_signoff, self.finalize, self.tenant_interceptor, self.core):
                _mt(f, _tbl("audit-ledger"), *AUD)
                _mt(f, worm, "s3:PutObject", "s3:Abort*")
            if self.approve_signoff is not None:
                _mt(self.approve_signoff, _tbl("pending-approvals"), "dynamodb:GetItem", "dynamodb:UpdateItem")
                _mt(self.approve_signoff, _tbl("audit-ledger"), *AUD)
                _mt(self.approve_signoff, worm, "s3:PutObject", "s3:Abort*")
            self.write_audit.add_to_role_policy(iam.PolicyStatement(
                effect=iam.Effect.DENY,
                actions=["dynamodb:DeleteItem", "dynamodb:UpdateItem",
                         "s3:DeleteObject", "s3:DeleteObjectVersion",
                         "s3:PutObjectRetention", "s3:PutObjectLegalHold",
                         "s3:BypassGovernanceRetention"],
                resources=_tbl("audit-ledger") + worm))

        for name, f in {
            "IngestArn": self.ingest, "IntakeArn": self.intake, "LookupArn": self.lookup,
            "MaskArn": self.mask, "AssessArn": self.assess, "CoreArn": self.core,
            "WriteAuditArn": self.write_audit, "RequestSignoffArn": self.request_signoff,
            "GuardsArn": self.guards,
        }.items():
            cdk.CfnOutput(self, name, value=f.function_arn)   # exact ARNs (P0-7)
        cdk.CfnOutput(self, "DrafterRoleArn", value=self.drafter_role_arn)   # the perimeter's exact principal (L12)
        cdk.CfnOutput(self, "BudgetsTableName", value=self.budgets_table.table_name,
                      description="Per-tenant meter: <tenant>#<YYYY-MM>; PutItem cap_tokens / cap_usd_micro / behavior to override one tenant")
        cdk.CfnOutput(self, "KillSwitchParameter", value=ks_name)
        for mode in ("engage", "disengage"):
            cdk.CfnOutput(self, f"KillSwitch{mode.title()}Url", value=self.kill_switch_urls[mode].url,
                          description=f"POST {{reason}} with SigV4 (AWS_IAM) to {mode} the Kill Switch; GET = status")
            cdk.CfnOutput(self, f"KillSwitch{mode.title()}PolicyArn",
                          value=self.kill_switch_policies[mode].managed_policy_arn)
        if self.approve_signoff is not None:
            cdk.CfnOutput(self, "ApproveSignoffArn", value=self.approve_signoff.function_arn,
                          description="The ONLY working approve path: verifies the approver's Cognito "
                                      "access token, enforces SoD, consumes the single-use approval.")

    def _runtime_execution_role(self, prefix, has_guardrail, guardrail_id):
        """AgentCore RUNTIME EXECUTION ROLE as IaC (third external review, 2026-09-05). The toolkit's
        `agentcore configure` otherwise auto-creates the role, and AWS states CLI-generated policies are
        for development/testing. This role is the documented runtime policy ("IAM Permissions for
        AgentCore Runtime": ECR pull, runtime log groups, X-Ray, bedrock-agentcore metrics, workload
        access tokens, model invocation) plus exactly what THIS runtime needs (gateway-URL + kill-switch
        SSM reads, the budget meter's table + metric namespace, ApplyGuardrail on the platform guardrail),
        every resource scoped to the deployment. With a guardrail configured, the runtime's model calls
        carry the same MANDATORY-GUARDRAIL condition as the drafter (agent.py passes guardrailConfig via
        Strands), so the runtime cannot make an unguarded model call either. Launch with
        `agentcore configure --execution-role <RuntimeExecutionRoleArn>`; the role name is deterministic so
        the org SCP allowlist and the bypass alarm can reference it. RT-3 port from benefits (2026-09-06)."""
        rt, region, acct = self._runtime_name, self.region, self.account
        role = iam.Role(
            self, "RuntimeExecutionRole", role_name=f"{prefix}-agentcore-runtime",
            assumed_by=iam.ServicePrincipal("bedrock-agentcore.amazonaws.com", conditions={
                "StringEquals": {"aws:SourceAccount": acct},
                "ArnLike": {"aws:SourceArn": f"arn:aws:bedrock-agentcore:{region}:{acct}:*"}}),
            description="Aegis governed AgentCore runtime execution role (IaC, least privilege)")
        stmts = [
            iam.PolicyStatement(sid="ECRImageAccess", actions=["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"],
                                resources=[f"arn:aws:ecr:{region}:{acct}:repository/*"]),
            iam.PolicyStatement(sid="ECRTokenAccess", actions=["ecr:GetAuthorizationToken"], resources=["*"]),
            iam.PolicyStatement(sid="RuntimeLogGroups", actions=["logs:DescribeLogStreams", "logs:CreateLogGroup"],
                                resources=[f"arn:aws:logs:{region}:{acct}:log-group:/aws/bedrock-agentcore/runtimes/*"]),
            iam.PolicyStatement(sid="RuntimeLogResourcePolicy", actions=["logs:PutResourcePolicy"],
                                resources=[f"arn:aws:logs:{region}:{acct}:log-group:/aws/bedrock-agentcore/runtimes/{rt}-*"]),
            iam.PolicyStatement(sid="DescribeLogGroups", actions=["logs:DescribeLogGroups"],
                                resources=[f"arn:aws:logs:{region}:{acct}:log-group:*"]),
            iam.PolicyStatement(sid="RuntimeLogStreams", actions=["logs:CreateLogStream", "logs:PutLogEvents"],
                                resources=[f"arn:aws:logs:{region}:{acct}:log-group:/aws/bedrock-agentcore/runtimes/*:log-stream:*"]),
            iam.PolicyStatement(sid="XRay", actions=["xray:PutTraceSegments", "xray:PutTelemetryRecords",
                                                     "xray:GetSamplingRules", "xray:GetSamplingTargets"], resources=["*"]),
            iam.PolicyStatement(sid="AgentCoreMetrics", actions=["cloudwatch:PutMetricData"], resources=["*"],
                                conditions={"StringEquals": {"cloudwatch:namespace": "bedrock-agentcore"}}),
            iam.PolicyStatement(sid="BudgetMetrics", actions=["cloudwatch:PutMetricData"], resources=["*"],
                                conditions={"StringEquals": {"cloudwatch:namespace": "Aegis/Budget"}}),
            iam.PolicyStatement(sid="GetAgentAccessToken",
                                actions=["bedrock-agentcore:GetWorkloadAccessToken", "bedrock-agentcore:GetWorkloadAccessTokenForJWT",
                                         "bedrock-agentcore:GetWorkloadAccessTokenForUserId"],
                                resources=[f"arn:aws:bedrock-agentcore:{region}:{acct}:workload-identity-directory/default",
                                           f"arn:aws:bedrock-agentcore:{region}:{acct}:workload-identity-directory/default/workload-identity/{rt}-*"]),
            iam.PolicyStatement(sid="BedrockModelInvocationGuardrailRequired" if has_guardrail else "BedrockModelInvocation",
                                actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                                resources=["arn:aws:bedrock:*::foundation-model/*", f"arn:aws:bedrock:{region}:{acct}:*"],
                                conditions=({"Null": {"bedrock:GuardrailIdentifier": "false"}} if has_guardrail else None)),
            iam.PolicyStatement(sid="GovernanceParameters", actions=["ssm:GetParameter"],
                                resources=[f"arn:aws:ssm:{region}:{acct}:parameter/{prefix}-aid/*"]
                                + ([f"arn:aws:ssm:{region}:{acct}:parameter{self._global_kill_switch}"] if self._global_kill_switch else [])),
            iam.PolicyStatement(sid="BudgetMeter", actions=["dynamodb:GetItem", "dynamodb:UpdateItem"],
                                resources=[self.budgets_table.table_arn]),
        ]
        if has_guardrail:
            g_arn = self.guardrail_arn or f"arn:aws:bedrock:{region}:{acct}:guardrail/{guardrail_id}"
            stmts.append(iam.PolicyStatement(sid="ApplyPlatformGuardrail", actions=["bedrock:ApplyGuardrail"], resources=[g_arn]))
        for st in stmts:
            role.add_to_policy(st)
        cdk.CfnOutput(self, "RuntimeExecutionRoleArn", value=role.role_arn,
                      description="Pass to `agentcore configure --execution-role` (IaC role; never the CLI-generated one).")
        cdk.CfnOutput(self, "RuntimeExecutionRoleName", value=role.role_name)
        return role


