"""Review-3 R3-2 — ZERO-PII pass-by-reference orchestration.

The finding this closes: the PII canary measured 87 marker hits in Step Functions execution history
because the raw application traveled as state input. Now raw content is written ONCE to the
encrypted, TTL'd, tenant-scoped case store and only opaque refs cross the controller."""
import importlib
import os

os.environ.setdefault("PROVENANCE_SECRET", "p0-unit-provenance-secret")

from toolkit import CONTROLS  # noqa: E402
import sys  # noqa: E402
import pathlib  # noqa: E402
sys.path.insert(0, str(CONTROLS))
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agents" / "financial-aid" / "tools"))

import case_store  # noqa: E402
import ingest_case  # noqa: E402

RAW = "Applicant Maria Gonzalez (SSN 523-11-9876) files a FAFSA. Student Aid Index 2500, enrolled full-time at Example State University (unitid 123456), GPA 3.1, pace 85%."


def _fresh():
    case_store.MemoryCaseStore.items.clear()


def test_ingest_returns_ref_never_content(monkeypatch):
    _fresh()
    out = ingest_case.handler({"application": RAW, "case_id": "HOU-1"}, None)
    assert out["ingested"] is True and out["case_ref"].startswith("case-")
    assert RAW not in str(out) and "Gonzalez" not in str(out)   # the response is content-free
    assert case_store.get_case(out["case_ref"]) == RAW
    assert ingest_case.handler({"application": "  "}, None)["ingested"] is False


def test_case_store_tenant_scoped(monkeypatch):
    _fresh()
    monkeypatch.setenv("TENANT_ID", "pha-a")
    ref = case_store.put_case(RAW)
    assert case_store.get_case(ref) == RAW
    monkeypatch.setenv("TENANT_ID", "pha-b")
    assert case_store.get_case(ref) is None      # cross-tenant fetch refused (B5)
    monkeypatch.delenv("TENANT_ID")
    assert case_store.get_case("case-nope") is None
    assert case_store.get_case(None) is None


def test_intake_extracts_from_ref_and_fails_closed_on_bad_ref():
    _fresh()
    import intake_fafsa as intake
    ref = case_store.put_case(RAW)
    out = intake.handler({"case_ref": ref}, None)
    assert out["structured"] is True
    assert out["fields"]["student_aid_index"] == 2500
    bad = intake.handler({"case_ref": "case-unknown"}, None)
    assert bad.get("structured") is False and "fail-closed" in bad["error"]


def test_mask_by_ref_returns_no_content(monkeypatch):
    _fresh()
    import mask_pii
    importlib.reload(mask_pii)

    class _CM:
        def detect_pii_entities(self, Text, LanguageCode):
            return {"Entities": [{"BeginOffset": 10, "EndOffset": 24, "Type": "NAME"}]}

    import boto3
    monkeypatch.setattr(boto3, "client", lambda *_a, **_k: _CM())
    ref = case_store.put_case(RAW)
    out = mask_pii.handler({"case_ref": ref}, None)
    assert out["deidentified"] is True and "sanitized_ref" in out
    assert "masked_case" not in out                      # R3-2: no content into state output
    assert "Gonzalez" not in str(out) and "523-11" not in str(out)
    # unknown ref fails closed
    bad = mask_pii.handler({"case_ref": "case-unknown"}, None)
    assert bad["deidentified"] is False and "fail-closed" in bad["error"]
    # inline mode (dev/direct) still returns the masked text
    inline = mask_pii.handler({"case": RAW}, None)
    assert "masked_case" in inline


def test_drafter_stores_notice_by_ref_when_case_store_configured(monkeypatch):
    _fresh()
    import sanitized
    import aid_core
    importlib.reload(aid_core)
    masked = "[REDACTED:NAME] files a FAFSA. SAI 2500, full-time, Example State University."
    sref = sanitized.mint_ref(masked, engine="comprehend", store=sanitized.MemoryStore())
    # store carries the text via candidate binding instead (no store configured for sanitized)
    class _BR:
        def converse(self, **kw):
            return {"output": {"message": {"content": [{"text": "Dear student, estimate drafted."}]}},
                    "stopReason": "end_turn"}

    import boto3
    monkeypatch.setattr(boto3, "client", lambda *_a, **_k: _BR())
    monkeypatch.setenv("CASE_TABLE", "unit-inmemory")   # flips notice->ref path; table calls fall back? no:
    # CASE_TABLE set means case_store would call boto3 Table — monkeypatch _table to memory
    monkeypatch.setattr(case_store, "_table", lambda: None)
    out = aid_core.handler({"deidentified": True, "sanitized_ref": sref, "case": masked}, None)
    assert out.get("notice_ref", "").startswith("case-")
    assert "notice" not in out                           # content stored, not echoed
    assert case_store.get_case(out["notice_ref"]).startswith("Dear student")
    monkeypatch.delenv("CASE_TABLE")
    out2 = aid_core.handler({"deidentified": True, "sanitized_ref": sref, "case": masked}, None)
    assert "notice" in out2                              # dev/inline mode unchanged


DETERMINATION = {"assessed": True, "determination": "ELIGIBLE", "eligible": True, "aid_track": "STANDARD",
                 "sap_status": "SATISFACTORY", "pell_award": 4895, "enrollment_status": "FULL_TIME",
                 "cost_of_attendance": 21000, "reason": "SAI 2500 within the Pell range",
                 "notes": ["SMUGGLED free text must not reach the grounding source"]}


def test_drafter_grounds_core_on_case_plus_determination_and_appends_boilerplate(monkeypatch):
    """#190 / L14 (PAR-1 port): with a guardrail bound, the model is asked for ONLY the grounded factual core
    (case + the deterministic determination as grounding_source, a query), the determination reaches the
    source from an allowlist of fields only, and the fixed boilerplate is appended deterministically."""
    _fresh()
    import sanitized
    import aid_core
    importlib.reload(aid_core)
    masked = "[REDACTED:NAME] files a FAFSA. SAI 2500, full-time, Example State University."
    sref = sanitized.mint_ref(masked, engine="comprehend", store=sanitized.MemoryStore())
    seen = {}

    class _BR:
        def converse(self, **kw):
            seen.update(kw)
            return {"output": {"message": {"content": [{"text": "Dear student, you are eligible."}]}},
                    "stopReason": "end_turn"}
    import boto3
    monkeypatch.setattr(boto3, "client", lambda *_a, **_k: _BR())
    monkeypatch.setattr(aid_core, "GUARDRAIL_ID", "gr-fa123")
    monkeypatch.setattr(aid_core, "GUARDRAIL_VERSION", "1")
    monkeypatch.delenv("CASE_TABLE", raising=False)
    out = aid_core.handler({"deidentified": True, "sanitized_ref": sref, "case": masked,
                            "determination": DETERMINATION}, None)
    assert seen.get("guardrailConfig") == {"guardrailIdentifier": "gr-fa123", "guardrailVersion": "1"}
    assert seen["system"] == [{"text": aid_core._SYSTEM_GROUNDED_CORE}]
    blocks = seen["messages"][0]["content"]
    quals = [q for b in blocks for q in b.get("guardContent", {}).get("text", {}).get("qualifiers", [])]
    assert "grounding_source" in quals and "query" in quals
    src = [b["guardContent"]["text"]["text"] for b in blocks
           if "grounding_source" in b.get("guardContent", {}).get("text", {}).get("qualifiers", [])][0]
    assert masked in src and "determination=ELIGIBLE" in src and "pell_award=4895" in src and "sap_status=SATISFACTORY" in src
    assert "SMUGGLED" not in src
    assert out["notice"].startswith("Dear student") and out["notice"].endswith(aid_core._NOTICE_BOILERPLATE)
    assert out.get("guardrail_applied") is True


def test_drafter_refuses_without_the_engine_determination_when_guardrail_bound(monkeypatch):
    """L14: under a guardrail the deterministic determination is REQUIRED; without it the drafter refuses
    fail-closed BEFORE any model call (no spend, no notice) - the EDU workflow already passed it as a JSON
    string, and the drafter now actually uses it; the gateway schema requires it too."""
    _fresh()
    import sanitized
    import aid_core
    importlib.reload(aid_core)
    masked = "[REDACTED:NAME] files a FAFSA. SAI 2500, full-time, Example State University."
    sref = sanitized.mint_ref(masked, engine="comprehend", store=sanitized.MemoryStore())
    called = {"converse": False}

    class _Never:
        def converse(self, **kw):
            called["converse"] = True
            return {"output": {"message": {"content": [{"text": "x"}]}}, "stopReason": "end_turn"}
    import boto3
    monkeypatch.setattr(boto3, "client", lambda *_a, **_k: _Never())
    monkeypatch.setattr(aid_core, "GUARDRAIL_ID", "gr-fa123")
    monkeypatch.setattr(aid_core, "GUARDRAIL_VERSION", "1")
    out = aid_core.handler({"deidentified": True, "sanitized_ref": sref, "case": masked}, None)
    assert out.get("drafted_by") is None and out.get("determination_present") is False
    assert "determination required" in out.get("error", "") and called["converse"] is False
    # a JSON-string determination (the workflow's States.JsonToString shape) is accepted
    seen = {}

    class _Spy:
        def converse(self, **kw):
            seen.update(kw)
            return {"output": {"message": {"content": [{"text": "core"}]}}, "stopReason": "end_turn"}
    monkeypatch.setattr(boto3, "client", lambda *_a, **_k: _Spy())
    import json as _json
    out2 = aid_core.handler({"deidentified": True, "sanitized_ref": sref, "case": masked,
                             "determination": _json.dumps(DETERMINATION)}, None)
    assert out2.get("drafted_by") and "determination=ELIGIBLE" in _json.dumps(seen["messages"])
    wf = (ROOT / "cdk" / "fa_stacks" / "workflow_stack.py").read_text(encoding="utf-8")
    assert '"determination.$": "States.JsonToString($.assessment.out)"' in wf
    import yaml
    m = yaml.safe_load((ROOT / "agents" / "financial-aid" / "manifest.yaml").read_text(encoding="utf-8"))
    tool = [t for tg in m["tools"] for t in tg.get("mcp_tools", []) if t["name"] == "draft_award_notice"][0]
    assert "determination" in tool["input"] and "determination" in tool["required"] and "sanitized_ref" in tool["required"]
