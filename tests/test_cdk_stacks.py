"""P0-5 / P0-2 / P0-6 / P0-7 / P0-12 — the CDK stacks synthesize and carry the controls.

Uses aws_cdk.assertions (pure Python; no CDK CLI, no AWS). Skipped automatically when aws-cdk-lib is
not installed (CI installs it)."""
import json
import os
import pathlib
import sys

import pytest

aws_cdk = pytest.importorskip("aws_cdk")
from aws_cdk.assertions import Template, Match  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cdk"))

from app import stage_lambda_bundle  # noqa: E402
from fa_stacks.data_stack import DataStack  # noqa: E402
from fa_stacks.compute_stack import ComputeStack  # noqa: E402
from fa_stacks.workflow_stack import WorkflowStack  # noqa: E402
from fa_stacks.identity_stack import IdentityStack  # noqa: E402


def _stacks(profile="sandbox-demo", kms="aws-managed"):
    app = aws_cdk.App()
    asset = stage_lambda_bundle()
    data = DataStack(app, "d", prefix="fa-test", retention_profile=profile, kms_mode=kms)
    compute = ComputeStack(app, "c", prefix="fa-test", asset_dir=asset, data=data)
    workflow = WorkflowStack(app, "w", prefix="fa-test", compute=compute, data=data)
    identity = IdentityStack(app, "i", prefix="fa-test")
    return data, compute, workflow, identity


DATA, COMPUTE, WORKFLOW, IDENTITY = _stacks()
T_DATA, T_COMPUTE = Template.from_stack(DATA), Template.from_stack(COMPUTE)
T_WORKFLOW, T_IDENTITY = Template.from_stack(WORKFLOW), Template.from_stack(IDENTITY)


# ── data: retention profiles (P0-12) + sanitized store (P0-1) ────────────────

def test_worm_bucket_object_lock_default_profile():
    T_DATA.has_resource_properties("AWS::S3::Bucket", Match.object_like({
        "ObjectLockEnabled": True,
        "ObjectLockConfiguration": Match.object_like({
            "Rule": {"DefaultRetention": {"Mode": "GOVERNANCE", "Days": 1}}}),
    }))


def test_production_profile_is_compliance_mode():
    d, *_ = _stacks(profile="production-reference")
    Template.from_stack(d).has_resource_properties("AWS::S3::Bucket", Match.object_like({
        "ObjectLockConfiguration": Match.object_like({
            "Rule": {"DefaultRetention": {"Mode": "COMPLIANCE", "Days": 2555}}}),
    }))


def test_unknown_profile_refused():
    with pytest.raises(ValueError):
        _stacks(profile="whatever")


def test_sanitized_artifacts_table_with_ttl():
    T_DATA.has_resource_properties("AWS::DynamoDB::Table", Match.object_like({
        "TableName": "fa-test-sanitized-artifacts",
        "TimeToLiveSpecification": {"AttributeName": "expires_at", "Enabled": True},
    }))


def test_audit_ledger_retained_with_pitr():
    T_DATA.has_resource("AWS::DynamoDB::Table", Match.object_like({
        "DeletionPolicy": "Retain",
        "Properties": Match.object_like({
            "TableName": "fa-test-audit-ledger",
            "PointInTimeRecoverySpecification": {"PointInTimeRecoveryEnabled": True}})}))


# ── compute: explicit IAM (P0-5) + tamper deny + exact-ARN outputs (P0-7) ────

def test_audit_writer_has_explicit_tamper_deny():
    tpl = json.dumps(T_COMPUTE.to_json())
    assert "s3:BypassGovernanceRetention" in tpl and '"Effect": "Deny"' in tpl.replace("'", '"')


def test_exact_arn_outputs_exist():
    outs = T_COMPUTE.to_json().get("Outputs", {})
    for k in ("MaskArn", "AssessArn", "WriteAuditArn", "GuardsArn"):
        assert k in outs, f"exact-ARN output {k} missing (P0-7)"


# ── workflow: deterministic controller shape (P0-2) ──────────────────────────

def _controller_definition():
    """Reassemble the state-machine DefinitionString (an Fn::Join of literals + refs) into JSON."""
    tpl = T_WORKFLOW.to_json()
    for r in tpl["Resources"].values():
        if r["Type"] == "AWS::StepFunctions::StateMachine":
            parts = r["Properties"]["DefinitionString"]["Fn::Join"][1]
            return json.loads("".join(p if isinstance(p, str) else "ARN" for p in parts))
    raise AssertionError("no state machine in workflow stack")


def test_controller_pipeline_order_and_fail_closed_choices():
    doc = _controller_definition()
    # WALK the actual transitions from StartAt along the happy path (a Choice's first `when`).
    state, visited = doc["StartAt"], []
    while state and len(visited) < 40:
        visited.append(state)
        st = doc["States"][state]
        if st["Type"] == "Choice":
            state = st["Choices"][0]["Next"]
        else:
            state = st.get("Next")
    expected = ["Extract", "GuardExtracted", "ExtractedOk",
                    # selected_for_verification is normalized (caller value honored, else default TRUE)
                    # before the institution seed — SelectedProvided -> SelectedFromInput.
                    "SelectedProvided", "SelectedFromInput",
                    # SeedInstitution defaults the OPTIONAL caller inputs (institution identifiers,
                    # verification selection, document lists). Without it those states read JSONPaths
                    # that are not in the {case_id, requester, case_ref} contract and the execution
                    # dies with States.Runtime instead of routing to ManualReview. See
                    # tests/test_workflow_input_contract.py.
                    "HasInstitution", "SeedInstitutionFromInput",
                    "LookupCOA", "GuardReferenceCOA", "ReferenceCoaOk",
                    "MaskPii", "GuardDeidentified", "DeidentifiedOk",
                    "AssessAid", "GuardRulesExecuted", "RulesOk",
                    "VerifyDocuments", "GuardVerification", "VerificationClear",
                    # G1/G2 fail-closed gates: a guardrail-BLOCKED draft (DraftOk) and a refused approval
                    # path (FinalizeOk) route to ManualReview instead of onward — see the choices below.
                    "DraftNotice", "DraftOk", "AuditIntent", "HumanSignoff", "Finalize", "FinalizeOk", "Committed"]
    assert visited == expected, f"happy path deviates from the regulated sequence: {visited}"
    # every guard Choice fails closed to ManualReview
    for choice in ("ExtractedOk", "ReferenceCoaOk", "DeidentifiedOk", "RulesOk"):
        assert doc["States"][choice]["Default"] == "ManualReview"
    # the human gate is a real waitForTaskToken pause
    assert "waitForTaskToken" in doc["States"]["HumanSignoff"]["Resource"]


# ── identity: no users, no passwords (P0-6) ──────────────────────────────────

def test_identity_creates_no_users_and_no_passwords():
    tpl = T_IDENTITY.to_json()
    types = [r["Type"] for r in tpl.get("Resources", {}).values()]
    assert "AWS::Cognito::UserPoolUser" not in types
    assert "ChangeMe" not in json.dumps(tpl)


def test_no_default_password_anywhere_in_any_template():
    for t in (T_DATA, T_COMPUTE, T_WORKFLOW, T_IDENTITY):
        assert "ChangeMe" not in json.dumps(t.to_json())


# ── Review-2: secrets are Secrets Manager resources, never plaintext env ─────

def test_signing_and_hud_secrets_provisioned_and_no_plaintext():
    tpl = T_COMPUTE.to_json()
    types = [r["Type"] for r in tpl.get("Resources", {}).values()]
    assert types.count("AWS::SecretsManager::Secret") >= 3   # GA-2: deid key + HUD key + HUD API token
    s = json.dumps(tpl)
    assert "PROVENANCE_SECRET_ARN_DEID" in s and "PROVENANCE_SECRET_ARN_SCORECARD" in s \
        and "SCORECARD_API_KEY_ARN" in s
    assert '"PROVENANCE_SECRET"' not in s, "plaintext signing secret must not appear in the template"


def test_ga2_domain_keys_are_separate_secrets_with_split_grants():
    """GA-2: the deid and HUD signing keys are DIFFERENT SecretsManager resources, and IAM splits
    them — the lookup function is granted the HUD key but NOT the deid key, and the masker is
    granted the deid key but NOT the HUD key (cross-domain forgery impossible at IAM)."""
    tpl = T_COMPUTE.to_json()
    res = tpl.get("Resources", {})
    secret_ids = [lid for lid, r in res.items() if r["Type"] == "AWS::SecretsManager::Secret"]
    deid = [lid for lid in secret_ids if "SigningSecretDeid" in lid]
    hud = [lid for lid in secret_ids if "SigningSecretScorecard" in lid]
    assert deid and hud and deid != hud

    def _grants(policy_lid_fragment):
        """Set of secret logical ids referenced by IAM policies attached to roles whose logical id
        contains the fragment (CDK names default policies after the function construct)."""
        out = set()
        for lid, r in res.items():
            if r["Type"] != "AWS::IAM::Policy" or policy_lid_fragment not in lid:
                continue
            blob = json.dumps(r)
            for sid in secret_ids:
                if sid in blob:
                    out.add(sid)
        return out

    lookup_grants = _grants("LookupCoa")
    mask_grants = _grants("MaskPii")
    assert hud[0] in lookup_grants and deid[0] not in lookup_grants, \
        "lookup must read ONLY the Scorecard-domain key"
    assert deid[0] in mask_grants and hud[0] not in mask_grants, \
        "mask_pii must read ONLY the deid-domain key"


# ── Gate-B B1: private networking + locked egress ─────────────────────────────

def test_network_stack_locked_egress_and_vpc_lambdas():
    from fa_stacks.network_stack import NetworkStack, ALLOWED_DOMAINS
    app = aws_cdk.App()
    asset = stage_lambda_bundle()
    net = NetworkStack(app, "nn", prefix="fa-net")
    data = DataStack(app, "nd", prefix="fa-net", retention_profile="pilot")
    compute = ComputeStack(app, "nc", prefix="fa-net", asset_dir=asset, data=data, network=net)

    nt = Template.from_stack(net).to_json()
    blob = json.dumps(nt)
    types = [r["Type"] for r in nt["Resources"].values()]
    # firewall + deny-by-default allowlist naming ONLY the HUD domain
    assert "AWS::NetworkFirewall::Firewall" in types
    assert "AWS::NetworkFirewall::RuleGroup" in types
    assert ".api.data.gov" in blob and ALLOWED_DOMAINS == [".api.data.gov"]
    assert '"GeneratedRulesType": "ALLOWLIST"' in blob
    # AWS-service traffic stays private: gateway + interface endpoints
    assert types.count("AWS::EC2::VPCEndpoint") >= 9   # s3+ddb gateway, 7 interface
    # app subnets are ISOLATED (no direct NAT default route from CDK; our routes go to the firewall)
    assert '"VpcEndpointId"' in blob                    # firewall-endpoint routes present
    # lambda SG: no allow-all egress; 443 only
    sgs = [r for r in nt["Resources"].values() if r["Type"] == "AWS::EC2::SecurityGroup"
           and "tools" in json.dumps(r.get("Properties", {}).get("GroupName", ""))]
    assert sgs, "lambda security group missing"
    eg = sgs[0]["Properties"]["SecurityGroupEgress"]
    assert all(e.get("FromPort") == 443 and e.get("ToPort") == 443 for e in eg)

    # every governed tool Lambda runs inside the VPC
    ct = Template.from_stack(compute).to_json()
    fns = [r for r in ct["Resources"].values() if r["Type"] == "AWS::Lambda::Function"]
    assert fns and all("VpcConfig" in f["Properties"] for f in fns)


def test_tenant_pinned_into_every_function_env():
    app = aws_cdk.App()
    asset = stage_lambda_bundle()
    data = DataStack(app, "td", prefix="fa-ten", retention_profile="pilot")
    compute = ComputeStack(app, "tc", prefix="fa-ten", asset_dir=asset, data=data, tenant="uni-example-state")
    fns = [r for r in Template.from_stack(compute).to_json()["Resources"].values()
           if r["Type"] == "AWS::Lambda::Function"]
    assert fns and all(
        f["Properties"]["Environment"]["Variables"].get("TENANT_ID") == "uni-example-state" for f in fns)


def test_default_mode_lambdas_have_no_vpc():
    fns = [r for r in T_COMPUTE.to_json()["Resources"].values() if r["Type"] == "AWS::Lambda::Function"]
    assert fns and all("VpcConfig" not in f["Properties"] for f in fns)


# ── Gate-B B3: pilot identity — REQUIRED software MFA, threat protection, OIDC IdP as IaC ──

def test_pilot_identity_requires_software_mfa_and_threat_protection():
    app = aws_cdk.App()
    i = IdentityStack(app, "ip", prefix="fa-idp", identity_mode="pilot")
    tpl = Template.from_stack(i).to_json()
    pools = [r for r in tpl["Resources"].values() if r["Type"] == "AWS::Cognito::UserPool"]
    assert len(pools) == 1
    p = pools[0]["Properties"]
    assert p["MfaConfiguration"] == "ON"
    assert p["EnabledMfas"] == ["SOFTWARE_TOKEN_MFA"]          # no SMS anywhere
    assert p["UserPoolAddOns"]["AdvancedSecurityMode"] == "ENFORCED"
    assert p.get("AdminCreateUserConfig", {}).get("AllowAdminCreateUserOnly") is True
    types = [r["Type"] for r in tpl["Resources"].values()]
    assert "AWS::Cognito::UserPoolUser" not in types            # still zero users (P0-6)


def test_sandbox_identity_unchanged_and_unknown_mode_refused():
    tpl = T_IDENTITY.to_json()
    p = [r for r in tpl["Resources"].values() if r["Type"] == "AWS::Cognito::UserPool"][0]["Properties"]
    assert p["MfaConfiguration"] == "OPTIONAL"
    with pytest.raises(ValueError):
        IdentityStack(aws_cdk.App(), "ix", prefix="fa-x", identity_mode="prod")


def test_enterprise_oidc_federation_as_iac_secret_never_plaintext():
    app = aws_cdk.App()
    i = IdentityStack(app, "ifed", prefix="fa-fed", identity_mode="pilot", federation={
        "issuer_url": "https://login.example.gov/oidc",
        "client_id": "housing-agent",
        "client_secret_arn": "arn:aws:secretsmanager:us-east-1:111122223333:secret:oidc-client",
    })
    tpl = Template.from_stack(i).to_json()
    res = tpl["Resources"]
    idps = [r for r in res.values() if r["Type"] == "AWS::Cognito::UserPoolIdentityProvider"]
    assert len(idps) == 1 and idps[0]["Properties"]["ProviderType"] == "OIDC"
    # the client secret is a Secrets Manager DYNAMIC REFERENCE, not a literal
    blob = json.dumps(idps[0])
    assert "{{resolve:secretsmanager:" in blob and "oidc-client" in blob
    # the app client trusts the enterprise IdP (federated users hit the same Cedar policies)
    clients = [r for r in res.values() if r["Type"] == "AWS::Cognito::UserPoolClient"]
    assert any("SupportedIdentityProviders" in c["Properties"] for c in clients)


# ── Gate-B: customer-managed KMS reaches secrets, env, logs, SNS ─────────────

def test_customer_managed_kms_covers_secrets_env_logs_and_sns():
    from fa_stacks.observability_stack import ObservabilityStack
    app = aws_cdk.App()
    asset = stage_lambda_bundle()
    data = DataStack(app, "kd", prefix="fa-kms", retention_profile="pilot", kms_mode="customer-managed")
    compute = ComputeStack(app, "kc", prefix="fa-kms", asset_dir=asset, data=data)
    workflow = WorkflowStack(app, "kw", prefix="fa-kms", compute=compute, data=data)
    obs = ObservabilityStack(app, "ko", prefix="fa-kms", compute=compute, workflow=workflow, data=data)

    d = json.dumps(Template.from_stack(data).to_json())
    assert '"AWS::KMS::Key"' in d and '"EnableKeyRotation": true' in d.replace(" true", " true")

    ct = Template.from_stack(compute).to_json()
    cs = json.dumps(ct)
    res = ct.get("Resources", {})
    # every secret CMK-encrypted
    for lid, r in res.items():
        if r["Type"] == "AWS::SecretsManager::Secret":
            assert "KmsKeyId" in r["Properties"], f"{lid} must use the customer-managed key"
    # every function: CMK env encryption + an explicit CMK-encrypted log group
    fns = [r for r in res.values() if r["Type"] == "AWS::Lambda::Function"]
    lgs = [r for r in res.values() if r["Type"] == "AWS::Logs::LogGroup"]
    assert fns and len(lgs) >= len(fns), "each function needs an explicit CMK log group"
    for r in fns:
        assert "KmsKeyArn" in r["Properties"], "Lambda environment must be CMK-encrypted"
    for r in lgs:
        assert "KmsKeyId" in r["Properties"], "log groups must be CMK-encrypted"
    # SNS ops topic CMK-encrypted
    ot = Template.from_stack(obs).to_json()
    topics = [r for r in ot.get("Resources", {}).values() if r["Type"] == "AWS::SNS::Topic"]
    assert topics and all("KmsMasterKeyId" in t["Properties"] for t in topics)


def test_aws_managed_mode_has_no_cmk_and_still_synthesizes():
    s = json.dumps(T_COMPUTE.to_json())
    assert '"AWS::KMS::Key"' not in s   # default mode: no CMK resources in compute


# ── R3-2: ZERO-PII state machine — only opaque refs cross Step Functions ─────

def test_workflow_state_carries_no_raw_content():
    """The controller's definition must never reference raw content paths: execution input is
    {case_id, requester, case_ref}; intake+mask receive case_ref; the drafter receives only the
    signed sanitized_ref (loads text server-side) and returns notice_ref."""
    asl = json.dumps(T_WORKFLOW.to_json())
    assert "$.application" not in asl, "raw application must never enter Step Functions state"
    assert "masked_case" not in asl, "masked content must not cross state (server-side store only)"
    assert "case_ref" in asl
    tpl = json.dumps(T_COMPUTE.to_json())
    assert "ingest-case" in tpl                      # the one door for raw content
    assert '"CASE_TABLE"' in tpl                     # encrypted pass-by-reference store wired


# ── GA-6: observability stack — alarms + dashboard exist and page via SNS ────

def test_observability_stack_alarms_and_dashboard():
    from fa_stacks.observability_stack import ObservabilityStack
    app = aws_cdk.App()
    asset = stage_lambda_bundle()
    data = DataStack(app, "od", prefix="fa-obs", retention_profile="sandbox-demo")
    compute = ComputeStack(app, "oc", prefix="fa-obs", asset_dir=asset, data=data)
    workflow = WorkflowStack(app, "ow", prefix="fa-obs", compute=compute, data=data)
    obs = ObservabilityStack(app, "oo", prefix="fa-obs", compute=compute, workflow=workflow)
    tpl = Template.from_stack(obs)
    types = [r["Type"] for r in tpl.to_json().get("Resources", {}).values()]
    assert types.count("AWS::CloudWatch::Alarm") >= 8       # 3 workflow + 5 lambda-error alarms
    assert "AWS::CloudWatch::Dashboard" in types
    assert "AWS::SNS::Topic" in types
    # every alarm pages the ops topic
    s = json.dumps(tpl.to_json())
    assert s.count("AlarmActions") >= 8


# ── GA-1: AgentCore/Gateway/Cedar attachment is IaC with full-coverage assertions ──

def _gateway_stack():
    from fa_stacks.gateway_stack import GatewayStack
    app = aws_cdk.App()
    asset = stage_lambda_bundle()
    data = DataStack(app, "gd", prefix="hou-gw", retention_profile="sandbox-demo")
    compute = ComputeStack(app, "gc", prefix="hou-gw", asset_dir=asset, data=data)
    identity = IdentityStack(app, "gi", prefix="hou-gw")
    return Template.from_stack(GatewayStack(app, "gg", prefix="hou-gw", compute=compute, identity=identity))


T_GATEWAY = _gateway_stack()


def test_attachment_covers_every_manifest_tool_and_enforce():
    tpl = T_GATEWAY.to_json()
    props = next(r["Properties"] for r in tpl["Resources"].values()
                 if r["Type"] == "AWS::CloudFormation::CustomResource")
    def _tokjson(v):
        if isinstance(v, dict) and "Fn::Join" in v:   # ARN tokens synthesize as Fn::Join
            return json.loads("".join(x if isinstance(x, str) else "ARN" for x in v["Fn::Join"][1]))
        return json.loads(v)

    targets = _tokjson(props["TargetsJson"])
    names = {t["name"] for t in targets}
    assert names == {"intake-fafsa", "lookup-coa", "mask-pii", "assess-aid",
                         "verify-docs", "record-pj", "fa-core", "write-audit", "request-signoff"}
    all_tools = [tool["name"] for t in targets for tool in t["tools"]]
    assert "finalize_award" in all_tools and "request_signoff" in all_tools and "commit_professional_judgment" in all_tools
    # no tool schema may declare a credential field (P0-3 holds at the gateway layer too)
    for t in targets:
        for tool in t["tools"]:
            assert "access_token" not in tool["inputSchema"]["properties"]
    policies = _tokjson(props["PoliciesJson"])
    assert {p["name"].split("hou_gw_", 1)[-1] for p in policies} == {
        "aid_officer_permit", "mask_before_assess", "mask_before_pj",
        "mask_before_draft", "no_self_commit", "no_self_professional_judgment"}
    assert all("__GATEWAY_ARN__" in p["definition"] for p in policies if p["name"].startswith("hou_gw_no_self"))
    assert props["Enforcement"] == "ENFORCE"
    authz = props["AuthorizerConfigJson"]
    authz_s = authz if isinstance(authz, str) else "".join(
        x if isinstance(x, str) else "TOKEN" for x in authz["Fn::Join"][1])
    assert "customJWTAuthorizer" in authz_s and "allowedClients" in authz_s


def test_gateway_role_invokes_only_exact_lambda_arns():
    s = json.dumps(T_GATEWAY.to_json())
    assert "lambda:InvokeFunction" in s
    assert "starts_with" not in s and ":function:*" not in s   # exact ARNs, never discovery/wildcards


# -- RT-3 (port from benefits, 2026-09-06): runtime execution role as IaC ----------------------------

def test_runtime_execution_role_is_iac_least_privilege_with_mandatory_guardrail():
    """The AgentCore runtime must NOT run on the CLI-generated role (AWS: development/testing only). The
    compute stack exports an IaC execution role: the documented runtime policy scoped to this deployment +
    region + runtime name, the runtime's governance needs (SSM, budget meter, ApplyGuardrail), a
    SourceAccount/SourceArn-conditioned trust and - with a guardrail - the mandatory-guardrail condition."""
    app = aws_cdk.App()
    asset = stage_lambda_bundle()
    data = DataStack(app, "dg", prefix="fa-test", retention_profile="sandbox-demo", kms_mode="aws-managed")
    compute = ComputeStack(app, "cg", prefix="fa-test", asset_dir=asset, data=data, guardrail_id="gr-abc123")
    t = Template.from_stack(compute)
    roles = {k: v for k, v in t.find_resources("AWS::IAM::Role").items()
             if v["Properties"].get("RoleName") == "fa-test-agentcore-runtime"}
    assert len(roles) == 1, "IaC runtime execution role missing"
    role = next(iter(roles.values()))["Properties"]
    trust = json.dumps(role["AssumeRolePolicyDocument"])
    assert "bedrock-agentcore.amazonaws.com" in trust and "aws:SourceAccount" in trust and "aws:SourceArn" in trust
    pols = json.dumps([v for v in t.find_resources("AWS::IAM::Policy").values()
                       if "RuntimeExecutionRole" in json.dumps(v["Properties"].get("Roles"))])
    for needle in ("ecr:BatchGetImage", "ecr:GetAuthorizationToken", "/aws/bedrock-agentcore/runtimes/",
                   "bedrock-agentcore:GetWorkloadAccessTokenForJWT", "workload-identity/financial_aid_runtime_agent-*",
                   "xray:PutTraceSegments", "Aegis/Budget", "ssm:GetParameter", "-aid/*",
                   "dynamodb:UpdateItem", "bedrock:ApplyGuardrail", "bedrock:InvokeModelWithResponseStream",
                   "bedrock:GuardrailIdentifier"):
        assert needle in pols, f"runtime execution role policy is missing {needle}"
    assert '"bedrock-agentcore:*"' not in pols and '"Action": "*"' not in pols
    t.has_output("RuntimeExecutionRoleArn", {})
    # the drafter carries the same mandatory-guardrail condition
    core = json.dumps([v for v in t.find_resources("AWS::IAM::Policy").values()
                       if "CoreTools" in json.dumps(v["Properties"].get("Roles"))])
    assert "DrafterBedrockExactGuardrail" in core and "bedrock:GuardrailIdentifier" in core


def test_runtime_execution_role_without_guardrail_has_no_guardrail_condition():
    """Sandbox without a guardrail: the runtime role must still exist (IaC, never CLI) but not carry a
    guardrail condition its calls could not satisfy."""
    pols = json.dumps([v for v in T_COMPUTE.find_resources("AWS::IAM::Policy").values()
                       if "RuntimeExecutionRole" in json.dumps(v["Properties"].get("Roles"))])
    assert "bedrock:InvokeModel" in pols and "bedrock:GuardrailIdentifier" not in pols and "ApplyGuardrail" not in pols
    T_COMPUTE.has_resource_properties("AWS::IAM::Role", Match.object_like({"RoleName": "fa-test-agentcore-runtime"}))


# -- PAR-1 (port from benefits, 2026-09-06): #168 capture-all trail + WORM lineage --------------------

def test_capture_trail_selects_bedrock_and_agentcore_data_events():
    """The account capture trail (#168) must use ADVANCED selectors that record management events (where
    CloudTrail logs InvokeModel / Converse) PLUS every documented Bedrock data-plane resource type and the
    AgentCore Gateway, so a bypass through ApplyGuardrail / InvokeAgent / RetrieveAndGenerate / async or
    bidirectional invokes / the gateway is captured in WORM custody too. Basic EventSelectors must be gone
    (a trail cannot carry both)."""
    from fa_stacks.lineage_stack import LineageStack
    app = aws_cdk.App()
    t = Template.from_stack(LineageStack(app, "lp", prefix="fa-ptest"))
    trails = t.find_resources("AWS::CloudTrail::Trail")
    assert len(trails) == 1
    props = next(iter(trails.values()))["Properties"]
    assert "EventSelectors" not in props, "basic EventSelectors must be removed when advanced selectors are used"
    sel = props["AdvancedEventSelectors"]
    types = set()
    mgmt = False
    for s in sel:
        fields = {f["Field"]: f["Equals"] for f in s["FieldSelectors"]}
        if fields.get("eventCategory") == ["Management"]:
            mgmt = True
        for rt in fields.get("resources.type", []):
            types.add(rt)
        assert len(fields.get("resources.type", [])) <= 1, "one resources.type per advanced selector"
    assert mgmt, "management events (InvokeModel / Converse live here) must be selected"
    for rt in ("AWS::S3::Object", "AWS::Lambda::Function", "AWS::Bedrock::Model", "AWS::Bedrock::AsyncInvoke",
               "AWS::Bedrock::Guardrail", "AWS::Bedrock::KnowledgeBase", "AWS::Bedrock::AgentAlias",
               "AWS::Bedrock::InlineAgent", "AWS::Bedrock::FlowAlias",
               "AWS::BedrockAgentCore::Gateway", "AWS::BedrockAgentCore::Runtime", "AWS::BedrockAgentCore::RuntimeEndpoint"):
        assert rt in types, f"capture trail no longer selects data events for {rt}"
    assert props.get("IsMultiRegionTrail") is True and props.get("EnableLogFileValidation") is True
    # live-rejected by CloudTrail (2026-09-05): never let it back in
    assert "AWS::Bedrock::Prompt" not in types


# ── 2026-09-05 controls (PAR-1 port from benefits, 2026-09-06) ────────────────────────────────

def _perimeter_stacks(kms="aws-managed", lock_days=0, capture=True):
    from fa_stacks.observability_stack import ObservabilityStack
    from fa_stacks.lineage_stack import LineageStack
    app = aws_cdk.App()
    asset = stage_lambda_bundle()
    data = DataStack(app, "dq", prefix="fa-qtest", retention_profile="sandbox-demo", kms_mode=kms)
    compute = ComputeStack(app, "cq", prefix="fa-qtest", asset_dir=asset, data=data)
    workflow = WorkflowStack(app, "wq", prefix="fa-qtest", compute=compute, data=data)
    lineage = LineageStack(app, "lq", prefix="fa-qtest") if capture else None
    obs = ObservabilityStack(app, "oq", prefix="fa-qtest", compute=compute, workflow=workflow, data=data,
                             model_logging=True, lineage=lineage, transparency_lock_days=lock_days,
                             runtime_role_name="AmazonBedrockAgentCoreSDKRuntime-x",
                             approved_bedrock_principals=("arn:aws:iam::111122223333:role/break-glass",))
    return data, compute, obs


def test_bedrock_perimeter_bypass_alarm_from_capture_trail():
    """DETECTIVE perimeter: with the capture trail present, two metric filters on its log group feed
    Aegis/Perimeter BedrockBypassInvocations - (a) assumed-role sessions whose ISSUING ROLE (not the
    caller-chosen session name) is outside the allowlist, (b) any IAM-user / root caller - and a >=1
    alarm goes to the ops topic. Without the trail there is nothing to read, so no alarm is claimed."""
    _, compute, obs = _perimeter_stacks()
    to = Template.from_stack(obs)
    filters = to.find_resources("AWS::Logs::MetricFilter")
    pats = [json.dumps(v["Properties"]["FilterPattern"]) for v in filters.values()]
    assert len(filters) == 2, f"expected two bypass metric filters, got {len(filters)}"
    joined = " ".join(pats)
    assert "bedrock.amazonaws.com" in joined and "InvokeModel" in joined and "RetrieveAndGenerate" in joined
    assert "sessionIssuer.arn" in joined, "the role filter must key on the issuing ROLE arn, not the session name"
    assert "userIdentity.arn" not in joined and "principalId" not in joined, "never key on a caller-chosen session name"
    assert "IAMUser" in joined and "Root" in joined
    assert "break-glass" in joined and "AmazonBedrockAgentCoreSDKRuntime-x" in joined
    to.has_resource_properties("AWS::CloudWatch::Alarm", Match.object_like({
        "AlarmName": "fa-qtest-bedrock-perimeter-bypass", "Namespace": "Aegis/Perimeter/fa-qtest",
        "MetricName": "BedrockBypassInvocations", "Threshold": 1,
        "ComparisonOperator": "GreaterThanOrEqualToThreshold"}))
    _, _, obs2 = _perimeter_stacks(capture=False)
    assert Template.from_stack(obs2).find_resources("AWS::Logs::MetricFilter") == {}


def test_model_invocation_logging_is_restore_aware():
    """Live-found L6 (benefits Tier-1 gate 2026-09-05): model-invocation logging is an ACCOUNT singleton and
    the old AwsCustomResource simply DELETED it on teardown, switching off the account's pre-existing
    config. The resource is now a Lambda-backed provider that snapshots the prior config to SSM on create
    and restores it on delete - it needs Get (snapshot) as well as Put/Delete, the SSM parameter, and
    PassRole scoped to the bedrock service."""
    _, _, obs = _perimeter_stacks()
    t = Template.from_stack(obs)
    t.resource_count_is("Custom::AegisModelInvocationLogging", 1)
    crs = t.find_resources("Custom::AegisModelInvocationLogging")
    props = list(crs.values())[0]["Properties"]
    assert props["SnapshotParameter"] == "/fa-qtest/model-logging/prior" and "LoggingConfig" in props
    pols = json.dumps(t.find_resources("AWS::IAM::Policy"))
    assert "bedrock:GetModelInvocationLoggingConfiguration" in pols and "bedrock:PutModelInvocationLoggingConfiguration" in pols
    assert "ssm:PutParameter" in pols and "model-logging/prior" in pols
    assert '"iam:PassedToService": "bedrock.amazonaws.com"' in pols
    assert "deleteModelInvocationLoggingConfiguration" not in json.dumps(t.to_json())


def test_invocation_log_store_is_regulated_data_under_production_settings():
    """The model-invocation store records EVERY caller's prompts (account setting), so under
    customer-managed KMS + model_log_lock_days>0 it must be CMK-encrypted (log group AND large-payload
    bucket, with the bedrock service granted use of the key), Object-Locked in COMPLIANCE mode, versioned,
    RETAINED and never auto-emptied. The sandbox default keeps the destroy/auto-delete shape."""
    data, _, obs = _perimeter_stacks(kms="customer-managed", lock_days=400)
    to, td = Template.from_stack(obs), Template.from_stack(data)
    to.has_resource_properties("AWS::S3::Bucket", Match.object_like({
        "ObjectLockEnabled": True,
        "ObjectLockConfiguration": Match.object_like({"Rule": {"DefaultRetention": {"Mode": "COMPLIANCE", "Days": 400}}}),
        "VersioningConfiguration": {"Status": "Enabled"},
        "BucketEncryption": Match.object_like({"ServerSideEncryptionConfiguration": [
            Match.object_like({"ServerSideEncryptionByDefault": Match.object_like({"SSEAlgorithm": "aws:kms"})})]})}))
    bucket = [v for v in to.find_resources("AWS::S3::Bucket").values() if v.get("Properties", {}).get("ObjectLockEnabled")][0]
    assert bucket.get("DeletionPolicy") == "Retain"
    assert to.find_resources("Custom::S3AutoDeleteObjects") == {}, "a locked regulated-data store must never be auto-emptied"
    lg = [v for v in to.find_resources("AWS::Logs::LogGroup").values()
          if "modelinvocations" in json.dumps(v.get("Properties", {}).get("LogGroupName"))][0]
    assert "KmsKeyId" in lg["Properties"] and lg.get("DeletionPolicy") == "Retain"
    assert "BedrockInvocationLogDelivery" in json.dumps(td.to_json()), "bedrock service must be granted the CMK for delivery"
    _, _, obs0 = _perimeter_stacks()
    t0 = Template.from_stack(obs0)
    assert t0.find_resources("Custom::S3AutoDeleteObjects") != {}
    assert not any(v.get("Properties", {}).get("ObjectLockEnabled") for v in t0.find_resources("AWS::S3::Bucket").values())


def test_bedrock_runtime_endpoint_policy_admits_only_the_governed_drafter():
    """NETWORK half of the perimeter inside the pack VPC: the bedrock-runtime interface endpoint carries
    a policy that allows inference ONLY from the pinned drafter role (+ approved principals), keyed on
    aws:PrincipalArn (the ROLE arn for sessions) and aws:PrincipalAccount."""
    from fa_stacks.network_stack import NetworkStack
    from fa_stacks.compute_stack import drafter_role_name
    app = aws_cdk.App()
    net = NetworkStack(app, "np", prefix="fa-ptest", bedrock_principals=("arn:aws:iam::111122223333:role/break-glass",))
    t = Template.from_stack(net)
    eps = t.find_resources("AWS::EC2::VPCEndpoint")
    bedrock = [v for v in eps.values() if "bedrock-runtime" in json.dumps(v["Properties"]["ServiceName"])]
    assert len(bedrock) == 1
    pol = json.dumps(bedrock[0]["Properties"]["PolicyDocument"])
    assert "GovernedDrafterOnly" in pol and "break-glass" in pol
    assert f":role/{drafter_role_name('fa-ptest')}\"" in pol and "*ServiceRole" not in pol
    roles = T_COMPUTE.find_resources("AWS::IAM::Role", {"Properties": {"RoleName": drafter_role_name("fa-test")}})
    assert len(roles) == 1, "the drafter role must carry the pinned physical name"
    fn = T_COMPUTE.find_resources("AWS::Lambda::Function", {"Properties": {"FunctionName": "fa-test-core-tools"}})
    assert list(fn.values())[0]["Properties"]["Role"]["Fn::GetAtt"][0] == list(roles)[0]
    T_COMPUTE.has_output("DrafterRoleArn", {})
    assert "aws:PrincipalArn" in pol and "aws:PrincipalAccount" in pol
    assert '"bedrock:InvokeModel"' in pol and '"bedrock:InvokeModelWithResponseStream"' in pol
    others = [v for v in eps.values() if "bedrock-runtime" not in json.dumps(v["Properties"]["ServiceName"])]
    assert all("PolicyDocument" not in v["Properties"] for v in others)


def test_private_vpc_azs_are_ones_every_endpoint_service_offers():
    """cognito-idp is offered only in us-east-1b/1c/1d (live-found in the benefits Tier-1 gate), so every
    subnet must sit in the vetted AZ set, every interface endpoint must span exactly those subnets, and
    -c vpc_azs overrides."""
    from fa_stacks.network_stack import NetworkStack
    t = Template.from_stack(NetworkStack(aws_cdk.App(), "naz0", prefix="fa-az"))
    azs = {v["Properties"]["AvailabilityZone"] for v in t.find_resources("AWS::EC2::Subnet").values()}
    assert azs == set(NetworkStack.DEFAULT_AZS), azs
    assert "us-east-1a" not in azs
    for v in t.find_resources("AWS::EC2::VPCEndpoint").values():
        if v["Properties"].get("VpcEndpointType") == "Interface":
            assert len(v["Properties"]["SubnetIds"]) == len(NetworkStack.DEFAULT_AZS)
    n2 = Template.from_stack(NetworkStack(aws_cdk.App(), "naz", prefix="fa-az2", azs=("us-east-1c", "us-east-1d")))
    assert {v["Properties"]["AvailabilityZone"] for v in n2.find_resources("AWS::EC2::Subnet").values()} == {"us-east-1c", "us-east-1d"}


# boto3 service name -> VPC endpoint ServiceName suffix. Every service a DEPLOYED Lambda talks to
# must have an endpoint in the private VPC; anything else hangs until the Lambda timeout.
_BOTO3_TO_ENDPOINT = {
    "ssm": "ssm", "cloudwatch": "monitoring", "logs": "logs", "kms": "kms", "sts": "sts",
    "secretsmanager": "secretsmanager", "stepfunctions": "states", "comprehend": "comprehend",
    "bedrock-runtime": "bedrock-runtime", "bedrock-agentcore": "bedrock-agentcore",
    "cognito-idp": "cognito-idp", "s3": "s3", "dynamodb": "dynamodb",
}


def _deployed_handler_modules():
    """The handler modules ComputeStack actually deploys (the `fn("name", "module")` calls)."""
    import re
    src = (ROOT / "cdk" / "fa_stacks" / "compute_stack.py").read_text(encoding="utf-8")
    return sorted(set(re.findall(r'=\s*fn\(\s*"[^"]+",\s*"([A-Za-z0-9_]+)"', src)))


def _bundle_boto3_services(bundle_dir, roots):
    """boto3 client/resource service names reachable from `roots` through the bundle's own modules
    (transitive local imports), so an undeployed reference module does not inflate the set."""
    import ast
    bundle = pathlib.Path(bundle_dir)
    local = {p.stem for p in bundle.glob("*.py")}
    seen, todo, services = set(), list(roots), set()
    while todo:
        mod = todo.pop()
        if mod in seen or mod not in local:
            continue
        seen.add(mod)
        tree = ast.parse((bundle / f"{mod}.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                todo.extend(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                todo.append(node.module.split(".")[0])
            elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                  and node.func.attr in ("client", "resource")
                  and isinstance(node.func.value, ast.Name) and node.func.value.id == "boto3"
                  and node.args and isinstance(node.args[0], ast.Constant)):
                services.add(node.args[0].value)
    return services


def test_private_vpc_has_an_endpoint_for_every_service_the_deployed_lambdas_call():
    """Live-found L9 (benefits Tier-1 gate attempt 8, 2026-09-06): every governed tool reads the kill switch
    from SSM first and the budget meter publishes CloudWatch metrics, but the private VPC had no ssm or
    monitoring endpoint - every tool hung to its timeout and the gateway returned 500s. Derive the required
    endpoint set from the boto3 clients in the DEPLOYED bundle and assert each one exists."""
    from fa_stacks.network_stack import NetworkStack
    services = _bundle_boto3_services(stage_lambda_bundle(), _deployed_handler_modules())
    assert {"ssm", "cloudwatch", "dynamodb"} <= services, services
    unknown = services - set(_BOTO3_TO_ENDPOINT)
    assert not unknown, f"add these boto3 services to _BOTO3_TO_ENDPOINT: {unknown}"
    present = set()
    for v in Template.from_stack(NetworkStack(aws_cdk.App(), "nep", prefix="fa-ep")).find_resources("AWS::EC2::VPCEndpoint").values():
        name = v["Properties"]["ServiceName"]
        if isinstance(name, dict):
            name = "".join(x for x in name["Fn::Join"][1] if isinstance(x, str))
        present.add(name.rsplit(".", 1)[-1])
    missing = {_BOTO3_TO_ENDPOINT[s] for s in services} - present
    assert not missing, f"deployed Lambdas call services with no VPC endpoint (would hang in private mode): {missing}"


def test_cmk_logs_grant_covers_every_log_group_family():
    """Live-found (benefits Tier-1 gate, 2026-09-05): the CMK's CloudWatch-Logs grant covered only
    /aws/lambda/<prefix>-*, so the workflow controller log group (/aws/states/...) was refused the key under
    kms=customer-managed. Every log-group family the pack encrypts with the CMK must be in the grant."""
    d = DataStack(aws_cdk.App(), "dk", prefix="fa-ktest", retention_profile="sandbox-demo", kms_mode="customer-managed")
    keys = Template.from_stack(d).find_resources("AWS::KMS::Key")
    assert len(keys) == 1
    pol = json.dumps(next(iter(keys.values()))["Properties"]["KeyPolicy"])
    for fam in ("log-group:/aws/lambda/fa-ktest-*", "log-group:/aws/states/fa-ktest-*",
                "log-group:/aws/bedrock/modelinvocations/fa-ktest*", "log-group:/aws/cloudtrail/fa-ktest-*"):
        assert fam in pol, f"CMK logs grant does not cover {fam}"


# ── #166 / #190: guardrail as IaC + grounded drafter (PAR-1 step 3 port, 2026-09-06) ──────────

def _compute_with_guardrail():
    """A compute stack built from the manifest guardrail block (as app.py does), no external id."""
    import yaml
    app = aws_cdk.App()
    asset = stage_lambda_bundle()
    data = DataStack(app, "dg", prefix="fa-gtest", retention_profile="sandbox-demo", kms_mode="aws-managed")
    _m = yaml.safe_load((ROOT / "agents" / "financial-aid" / "manifest.yaml").read_text(encoding="utf-8")) or {}
    gcfg = dict(_m.get("guardrail") or {})
    gcfg["grounding"] = dict(_m.get("grounding") or {})
    compute = ComputeStack(app, "cg", prefix="fa-gtest", asset_dir=asset, data=data,
                           tenant="fa-test-school", guardrail_config=gcfg)
    return Template.from_stack(compute)


def test_guardrail_created_as_iac_with_pinned_version_and_grounding():
    """The manifest guardrail block becomes a real AWS::Bedrock::Guardrail (PROMPT_ATTACK at the declared
    strength, PII ANONYMIZE, CONTEXTUAL GROUNDING + RELEVANCE from the manifest thresholds) with a
    PINNED published version (the drafter never assesses against DRAFT)."""
    t = _compute_with_guardrail()
    t.resource_count_is("AWS::Bedrock::Guardrail", 1)
    t.resource_count_is("AWS::Bedrock::GuardrailVersion", 1)
    t.has_resource_properties("AWS::Bedrock::Guardrail", Match.object_like({
        "ContentPolicyConfig": {"FiltersConfig": Match.array_with([
            Match.object_like({"Type": "PROMPT_ATTACK", "InputStrength": "HIGH"})])},
        "SensitiveInformationPolicyConfig": {"PiiEntitiesConfig": Match.array_with([
            Match.object_like({"Type": "US_SOCIAL_SECURITY_NUMBER", "Action": "ANONYMIZE"})])},
        "ContextualGroundingPolicyConfig": {"FiltersConfig": Match.array_with([
            Match.object_like({"Type": "GROUNDING", "Threshold": Match.any_value()}),
            Match.object_like({"Type": "RELEVANCE", "Threshold": Match.any_value()}),
        ])},
    }))


def test_drafter_gets_guardrail_env_applyguardrail_perm_and_mandatory_guardrail_condition():
    """The drafter Lambda receives GUARDRAIL_ID/VERSION from the IaC guardrail, an ApplyGuardrail grant,
    and its bedrock:InvokeModel is DENIED unless the request carries a guardrail (Null present-check on
    bedrock:GuardrailIdentifier) - a mis-coded drafter cannot make an ungoverned model call."""
    t = _compute_with_guardrail()
    t.has_resource_properties("AWS::Lambda::Function", Match.object_like({
        "Environment": {"Variables": Match.object_like({"GUARDRAIL_ID": Match.any_value(),
                                                        "GUARDRAIL_VERSION": Match.any_value()})}}))
    t.has_resource_properties("AWS::IAM::Policy", Match.object_like({
        "PolicyDocument": {"Statement": Match.array_with([
            Match.object_like({"Action": "bedrock:ApplyGuardrail"})])}}))
    tj = json.dumps(t.to_json())
    assert '"bedrock:GuardrailIdentifier"' in tj and '"bedrock:InvokeModel"' in tj
    # the runtime execution role carries the same mandatory-guardrail condition (RT-3)
    assert "RuntimeBedrockExactGuardrail" in tj


def test_workflow_passes_the_engine_assessment_to_the_grounded_drafter():
    """L14 (full-portfolio gate 2026-09-06): the grounded drafter can only state what is IN its grounding
    source, so the workflow's draft state must carry the deterministic assessment output with the signed
    ref - the production payload, not a proof-shaped one."""
    wf = json.dumps(T_WORKFLOW.to_json())
    seg = wf[wf.index("DraftN"): wf.index("DraftN") + 1200]
    assert "determination.$" in seg and "$.assessment.out" in seg and "sanitized_ref.$" in seg


# ── #170 WAF on the auth front door + #160 entitlement grant as IaC (PAR-1 step 4 port, 2026-09-06) ──

def test_waf_off_by_default():
    """No Web ACL unless -c waf=1 (baseline identity is unchanged)."""
    t = Template.from_stack(IdentityStack(aws_cdk.App(), "i0", prefix="fa-wtest"))
    t.resource_count_is("AWS::WAFv2::WebACL", 0)


def test_waf_web_acl_created_for_pool():
    """`-c waf=1` creates a REGIONAL Web ACL (managed common rules + per-IP rate limit) for the auth
    surface. Association to the pool is applied post-deploy with retry (WAF<->Cognito association is
    eventually consistent and the native CFN association resource hangs for Cognito targets)."""
    t = Template.from_stack(IdentityStack(aws_cdk.App(), "iw", prefix="fa-wtest", waf=True))
    t.resource_count_is("AWS::WAFv2::WebACL", 1)
    t.has_resource_properties("AWS::WAFv2::WebACL", Match.object_like({
        "Scope": "REGIONAL",
        "DefaultAction": {"Allow": {}},
        "Rules": Match.array_with([
            Match.object_like({"Statement": {"ManagedRuleGroupStatement": Match.object_like(
                {"VendorName": "AWS", "Name": "AWSManagedRulesCommonRuleSet"})}}),
            Match.object_like({"Action": {"Block": {}},
                               "Statement": {"RateBasedStatement": Match.object_like({"AggregateKeyType": "IP"})}}),
        ])}))
    t.has_output("WafAssociateTarget", {})


def test_identity_provisions_the_zero_default_entitlement_grant():
    """#160 / L11: the zero-default entitlement admits only a non-empty custom:tools claim or membership in
    tools_granted - BOTH must be IaC (the pool attribute and the group), or every operator is denied every
    tool on a fresh deployment (found live on benefits, Tier-1 gate attempt 9)."""
    t = T_IDENTITY
    t.has_resource_properties("AWS::Cognito::UserPoolGroup", Match.object_like({"GroupName": "tools_granted"}))
    t.has_resource_properties("AWS::Cognito::UserPoolGroup", Match.object_like({"GroupName": "aid_officer"}))
    t.has_resource_properties("AWS::Cognito::UserPool", Match.object_like({
        "Schema": Match.array_with([Match.object_like({"Name": "tools", "AttributeDataType": "String", "Mutable": True})])}))


# ── PAR-1 step 5 (2026-09-06): authoritative Cedar context (#3) + the perimeter profile ──

def test_authz_store_is_iac_and_only_ingest_writes_it():
    """#3 / L18: the AUTHORITATIVE consent + authorized-purpose record Cedar's consent/purpose are derived
    from is a real store (CMK-encrypted, TTL'd); the gateway interceptor may only READ it and ingest - the
    one door raw content enters, by a verified operator - is the only writer."""
    T_DATA.has_resource_properties("AWS::DynamoDB::Table", Match.object_like({
        "TableName": "fa-test-authz-context",
        "KeySchema": [{"AttributeName": "case_id", "KeyType": "HASH"}],
        "TimeToLiveSpecification": Match.object_like({"AttributeName": "expires_at", "Enabled": True})}))
    T_DATA.has_output("AuthzTableName", {})
    fn = list(T_COMPUTE.find_resources("AWS::Lambda::Function",
                                       {"Properties": {"FunctionName": "fa-test-ingest-case"}}).values())[0]
    env = fn["Properties"]["Environment"]["Variables"]
    assert "AUTHZ_TABLE" in env and env.get("AUTHZ_TABLE_TEMPLATE") == "fa-test-{tenant}-authz-context"
    pols = T_COMPUTE.find_resources("AWS::IAM::Policy")

    def _stmts(role_ref):
        return [st for v in pols.values() if any(r.get("Ref") == role_ref for r in v["Properties"].get("Roles", []))
                for st in v["Properties"]["PolicyDocument"]["Statement"]]
    authz_writes = [st for st in _stmts(fn["Properties"]["Role"]["Fn::GetAtt"][0])
                    if "AuthzContext" in json.dumps(st.get("Resource"))
                    and "dynamodb:PutItem" in json.dumps(st.get("Action"))]
    assert authz_writes, "ingest must be able to write the authoritative consent/purpose record"
    ic = list(T_COMPUTE.find_resources("AWS::Lambda::Function",
                                       {"Properties": {"FunctionName": "fa-test-tenant-interceptor"}}).values())[0]
    for st in _stmts(ic["Properties"]["Role"]["Fn::GetAtt"][0]):
        if "AuthzContext" in json.dumps(st.get("Resource")):
            assert "dynamodb:PutItem" not in json.dumps(st.get("Action")), "the interceptor must never write the record"


def test_perimeter_profile_attaches_the_gates_and_declares_their_fields():
    """The #160/#161 gates attach ONLY with -c perimeter=1, and the gateway then declares the
    context.input fields they read on every tool schema (optional, so baseline callers are unaffected).
    Without the flag the proven baseline policy set is byte-for-byte unchanged."""
    from fa_stacks.gateway_stack import _policies, _PERIMETER_INPUT_FIELDS
    base = {p["name"].split("fa_test_", 1)[-1] for p in _policies("fa-test", multitenant=True, perimeter=False)}
    peri = {p["name"].split("fa_test_", 1)[-1] for p in _policies("fa-test", multitenant=True, perimeter=True)}
    added = peri - base
    assert "require_entitlement" in added and "require_service_window" in added
    assert any(n.startswith("consent_purpose_before_") for n in added)
    assert any(n.startswith("budget_before_") for n in added)
    assert base and not (base - peri), "the baseline set must be unchanged by the perimeter profile"
    for f in ("consent", "purpose", "budget_ok", "within_service_window", "case_id"):
        assert f in _PERIMETER_INPUT_FIELDS


# ── CHK-1: hardened trail log bucket + Log4j WAF rule group (2026-09-06) ────────────────────────


def test_evidence_trail_delivers_into_a_declared_hardened_bucket():
    """The data-events trail on the WORM vault proves nobody but the gateway touched the evidence.
    Its OWN log bucket was a CDK auto-created default that synthesized with no properties at all -
    no block-public-access, no TLS enforcement, no versioning, no declared encryption (checkov
    CKV_AWS_53/54/55/56/21/35). Found by the CHK-1 sizing scan, 2026-09-06."""
    from fa_stacks.observability_stack import ObservabilityStack
    app = aws_cdk.App()
    asset = stage_lambda_bundle()
    data = DataStack(app, "cd", prefix="fa-chk1")
    compute = ComputeStack(app, "cc", prefix="fa-chk1", asset_dir=asset, data=data)
    workflow = WorkflowStack(app, "cw", prefix="fa-chk1", compute=compute, data=data)
    t = Template.from_stack(ObservabilityStack(app, "co", prefix="fa-chk1", compute=compute,
                                               workflow=workflow, data=data))
    t.has_resource_properties("AWS::S3::Bucket", Match.object_like({
        "PublicAccessBlockConfiguration": {
            "BlockPublicAcls": True, "BlockPublicPolicy": True,
            "IgnorePublicAcls": True, "RestrictPublicBuckets": True},
        "VersioningConfiguration": {"Status": "Enabled"},
        "BucketEncryption": Match.any_value(),
    }))
    # and the trail is wired to a bucket this stack declares, not to an implicit one
    t.has_resource_properties("AWS::CloudTrail::Trail", Match.object_like({
        "TrailName": Match.string_like_regexp(r".*-worm-data-events$"),
        "EnableLogFileValidation": True,
        "S3BucketName": {"Ref": Match.string_like_regexp("WormDataEventsLogs.*")},
    }))


def test_waf_inspects_for_known_bad_inputs_including_log4j():
    """checkov CKV_AWS_192: the Common Rule Set does not by itself inspect for a Log4j2 JNDI
    lookup; the Known Bad Inputs managed group (Log4JRCE) is attached alongside it."""
    t = Template.from_stack(IdentityStack(aws_cdk.App(), "iw2", prefix="fa-wtest", waf=True))
    t.has_resource_properties("AWS::WAFv2::WebACL", Match.object_like({
        "Rules": Match.array_with([
            Match.object_like({"Statement": {"ManagedRuleGroupStatement": Match.object_like(
                {"VendorName": "AWS", "Name": "AWSManagedRulesKnownBadInputsRuleSet"})}}),
        ])}))
