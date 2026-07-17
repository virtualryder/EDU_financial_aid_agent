import json
import os
import urllib.request
import urllib.parse
import urllib.error

# lookup_coa — fetch a REAL institutional Cost of Attendance from the U.S. Department of Education
# College Scorecard API (https://api.data.gov/ed/collegescorecard/v1/schools). The school identifier
# (name or IPEDS unitid) is a NON-PII decision field, so this runs before mask_pii. It replaces the
# illustrative cost_of_attendance with an authoritative figure and returns PROVENANCE so the downstream
# determination and the WORM audit are traceable to the source.
#
# Field: COSTT4_A -> `latest.cost.attendance.academic_year` (academic-year cost of attendance, Title IV).
# Falls back to in/out-of-state tuition when a school does not report a full COA.
#
# API key: env SCORECARD_API_KEY. Defaults to DEMO_KEY (fine for evaluation; low rate limit). For a
# pilot, set a free api.data.gov key via env / Secrets Manager. The call itself is a GOVERNED Gateway
# tool — Cedar-authorized and auditable like every other tool; reaching real federal data is not an
# ungoverned side-channel.

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

    # Short proof fields FIRST (MCP client truncates ~200 chars); provenance object LAST.
    return {
        "found": True,
        "cost_of_attendance": int(coa),
        "school": name,
        "state": state,
        "unitid": uid,
        "coa_source": {
            "source": SOURCE,
            "api": "api.data.gov/ed/collegescorecard/v1/schools",
            "field": field_used,
            "school": name,
            "unitid": uid,
            "authoritative": True,
        },
        "note": "authoritative COA from College Scorecard; pass cost_of_attendance and coa_source to assess_aid",
    }
