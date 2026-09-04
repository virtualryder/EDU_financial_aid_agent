"""ingest_case — R3-2: the ONLY door through which raw applicant content enters the system.

Called BEFORE the workflow starts (by the intake API/operator script). Writes the raw application to
the encrypted, TTL'd, tenant-scoped case store and returns an OPAQUE ref — the Step Functions
execution is then started with {case_id, requester, case_ref} and NO raw content ever enters
execution input/output (the canary's strict gate).

The response deliberately echoes only length + ref — never the content."""
import json

import case_store


def _coerce(e):
    e = e or {}
    if isinstance(e, str):
        try:
            return json.loads(e)
        except Exception:
            return {"application": e}
    return e


import tenancy  # noqa: E402  (phase 107: interceptor-injected, HMAC-signed tenant)
import telemetry  # noqa: E402  (phase 110: correlation keys -> one aegis.call log line per invocation)


def _bind_tenant(e):
    """Multi-tenant INGESTION BOUNDARY. Returns (tenant, error).

    ingest is not a gateway tool (the intake integration invokes it directly under IAM), so no
    interceptor injects the signed tenant. Order of trust, all DERIVED and fail-closed:
      1. an HMAC-signed pair already on the event (a governed caller re-ingesting) — verified;
      2. multi-tenant: a VERIFIED Cognito access token (RS256/JWKS, pool + client + group checked)
         of a tenant member; the tenant is its tenant_<id> group / custom:tenant claim;
      3. silo: the deployment's pinned TENANT_ID.
    A typed `tenant` field is never consulted."""
    t = tenancy.bind_tenant_from_args(e)
    if t or not tenancy.multitenant_enabled():
        return t, None
    import identity
    claims, err = identity.verify_access_token(e.get("access_token"), require_group=True)
    if err:
        return None, "multi-tenant: ingestion identity not verified: %s" % err
    t = tenancy.tenant_from_claims(claims)
    if not t:
        return None, "multi-tenant: verified ingestion identity carries no tenant"
    tenancy.set_request_claims({tenancy._CLAIM: t})
    return t, None


@telemetry.instrument('ingest_application')
def handler(event, context):
    e = _coerce(event)
    # Phase 107 / governed-core 1.6.0 (hybrid multi-tenant): bind the DERIVED tenant for per-tenant
    # store routing. Unsigned/forged values are refused; multi-tenant mode fails closed.
    tenant, err = _bind_tenant(e)
    if err:
        return {"ingested": False, "error": err}
    text = e.get("application", "")
    if not isinstance(text, str):
        text = json.dumps(text, ensure_ascii=False)
    if not text.strip():
        return {"ingested": False, "error": "empty application"}
    ref = case_store.put_case(text, kind="application", case_id=e.get("case_id", ""))
    out = {"ingested": True, "case_ref": ref, "case_id": e.get("case_id", ""),
           "chars": len(text),
           "note": "start the workflow with {case_id, requester, case_ref} - raw content never enters Step Functions state"}
    # governed-core 1.6.0 (hybrid multi-tenant): the workflow starter must carry the acting tenant into
    # the execution input as the SIGNED pair (the Step Functions hop has no interceptor). Minted here
    # from the interceptor-bound tenant, so the caller cannot choose it. {} in silo mode.
    binding = tenancy.signed_binding()
    if binding:
        out["tenant_binding"] = binding
        out["note"] = "start the workflow with {case_id, requester, case_ref, **tenant_binding}"
    return out
