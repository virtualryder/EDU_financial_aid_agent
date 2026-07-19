import json
import os
import urllib.request
import urllib.parse
import urllib.error

import provenance  # shared signer (bundled beside this handler at deploy; on sys.path in tests)

# lookup_coa — fetch a REAL institutional Cost of Attendance from the U.S. Department of Education
# College Scorecard API (https://api.data.gov/ed/collegescorecard/v1/schools). The school identifier
# (name or IPEDS unitid) is a NON-PII decision field, so this runs before mask_pii. It replaces the
# illustrative cost_of_attendance with an authoritative figure and returns SIGNED PROVENANCE so the
# downstream determination and the WORM audit are traceable to the source.
#
# P0-3: this is the ONLY component that actually calls College Scorecard, so it is the only one that can
# vouch for the COA. It SIGNS the exact figure it fetched (unitid, school, cost_of_attendance) with the
# per-deploy PROVENANCE_SECRET and returns that token as `coa_source`. assess_aid verifies the signature
# before treating the COA as authoritative — a caller can no longer hand assess a fabricated COA plus a
# "College Scorecard" label and have it trusted.
#
# Field: COSTT4_A -> `latest.cost.attendance.academic_year` (academic-year cost of attendance, Title IV).
# Falls back to in/out-of-state tuition when a school does not report a full COA.
#
# API key: env SCORECARD_API_KEY. Defaults to DEMO_KEY (fine for evaluation; low rate limit). For a
# pilot, set a free api.data.gov key via env / Secrets Manager. The call itself is a GOVERNED Gateway
# tool — Cedar-authorized and auditable like every other tool. Fail-soft: found=false on any error, and
# because a source-down lookup returns NO signed token, the downstream determination becomes NEEDS_REVIEW
# instead of a fabricated answer.

API_BASE = "https://api.data.gov/ed/collegescorecard/v1/schools"
API_KEY = os.environ.get("SCORECARD_API_KEY", "DEMO_KEY")
FIELDS = "id,school.name,school.state,latest.cost.attendance.academic_year,latest.cost.tuition.in_state,latest.cost.tuition.out_of_state"
SOURCE = "US Dept of Education — College Scorecard"


def _coerce(e):
    e = e or {}
    if isinstance(e, str):
        try:
            e = json.loads(e)
        except Exception:
            e = {"school": e}
    return e


def _query(params):
    url = API_BASE + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "governed-financial-aid-agent/1.0"})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read().decode("utf-8"))


def handler(event, context):
    e = _coerce(event)
    school = (e.get("school") or "").strip()
    unitid = e.get("unitid")

    params = {"api_key": API_KEY, "fields": FIELDS, "per_page": 1}
    if unitid:
        params["id"] = str(unitid)
    elif school:
        params["school.name"] = school
    else:
        return {"found": False, "error": "provide a school name or IPEDS unitid"}

    try:
        data = _query(params)
    except urllib.error.HTTPError as ex:
        return {"found": False, "error": "College Scorecard HTTP %s: %s" % (ex.code, ex.reason), "source": SOURCE}
    except (urllib.error.URLError, TimeoutError, ValueError) as ex:
        return {"found": False, "error": "College Scorecard call failed: %s" % type(ex).__name__, "source": SOURCE}

    results = (data or {}).get("results") or []
    if not results:
        return {"found": False, "error": "no institution matched '%s'" % (unitid or school), "source": SOURCE}

    r = results[0]
    name = r.get("school.name", school)
    state = r.get("school.state", "")
    uid = r.get("id", unitid)
    coa = r.get("latest.cost.attendance.academic_year")
    field_used = "cost.attendance.academic_year"
    if coa in (None, 0):
        # fall back to tuition if the school does not report a full academic-year COA
        coa = r.get("latest.cost.tuition.out_of_state") or r.get("latest.cost.tuition.in_state")
        field_used = "cost.tuition (COA not reported)"

    if coa in (None, 0):
        return {"found": False, "error": "institution '%s' reports no cost data" % name,
                "source": SOURCE, "school": name, "unitid": uid}

    coa = int(coa)
    # ---- SIGN the fetched figure. The signed field set is EXACTLY what assess re-derives and verifies. ----
    sig_fields = {"unitid": str(uid), "school": name, "cost_of_attendance": coa}
    tok = provenance.sign(SOURCE, sig_fields)
    coa_source_obj = {
        "source": SOURCE,
        "api": "api.data.gov/ed/collegescorecard/v1/schools",
        "field": field_used,
        "school": name,
        "unitid": uid,
        "authoritative": tok.get("authoritative", False),
        "sig": tok.get("sig"),
        "alg": tok.get("alg"),
    }
    # coa_source travels as a JSON STRING (assess declares it string-typed at the gateway); assess parses
    # it and verifies the signature. This is a machine provenance token, not a human label.
    coa_source = json.dumps(coa_source_obj, separators=(",", ":"), ensure_ascii=False)

    # Short proof fields FIRST (MCP client truncates ~220 chars); provenance token LAST.
    return {
        "found": True,
        "cost_of_attendance": coa,
        "school": name,
        "state": state,
        "unitid": uid,
        "authoritative": tok.get("authoritative", False),
        "coa_source": coa_source,
        "note": "authoritative COA from College Scorecard; pass cost_of_attendance AND coa_source (signed) to assess_aid",
    }
