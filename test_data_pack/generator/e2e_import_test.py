#!/usr/bin/env python3
"""
ClimaCred AI - end-to-end import smoke test (TESTING ARTEFACT, NOT APP CODE)
===========================================================================
Loads every business in the pack through the *running application's own API* and
checks that what ClimaCred computes matches what the pack says it should.

Usage:
    # terminal 1
    cd backend && uvicorn app.main:app --port 8099
    # terminal 2
    python3 generator/e2e_import_test.py http://localhost:8099

It exercises, per business:
    POST /api/profile  ->  POST /api/assessment  ->  POST /api/climate-fingerprint/generate
and then reads the fingerprint, recommendations, scenario simulator, transformation
plan, climate report, history, forecast and (deliberately) the Gemini-disconnected
state.

It writes nothing outside the pack. Exit code 0 = all assertions passed.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.abspath(os.path.join(HERE, ".."))
BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8099").rstrip("/")

RESULTS = []


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode() or "null")
    except urllib.error.HTTPError as e:
        return e.code, {"detail": e.read().decode()[:200]}
    except Exception as e:  # noqa: BLE001
        return 0, {"detail": f"{type(e).__name__}: {e}"}


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" :: {detail}" if detail and not ok else ""))


def unwrap(resp, *keys):
    """The API wraps lists in small envelopes ({"recommendations": [...]}, {"plan": [...]})."""
    if isinstance(resp, list):
        return resp
    if isinstance(resp, dict):
        for k in keys:
            if isinstance(resp.get(k), list):
                return resp[k]
    return []


def rows(fname):
    with open(os.path.join(PACK, "csv", fname + ".csv"), newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


pack_assess = {r["business_id"]: r for r in rows("climate_assessments")}
hist_all = rows("historical_climate_data")
impact_all = rows("before_after_impact")
DIM = {"Energy": "energy_score", "Water": "water_score", "Waste": "waste_score",
       "Emissions": "emissions_score", "Mobility": "mobility_score",
       "Operations": "operations_score"}

print(f"== Empty-state checks against {BASE} ==")
call("POST", "/api/profile/reset")
st, prof = call("GET", "/api/profile")
check("empty: GET /api/profile returns null", prof is None, str(prof)[:120])
st, fp = call("GET", "/api/climate-fingerprint")
check("empty: fingerprint is null", fp is None, str(fp)[:120])
st, rec = call("GET", "/api/solutions/recommendations")
check("empty: recommendations list is empty",
      unwrap(rec, "recommendations", "items") == [], str(rec)[:120])
st, sc = call("GET", "/api/scenarios")
check("empty: scenarios list is empty", unwrap(sc, "history", "scenarios") == [], str(sc)[:120])
st, tp = call("GET", "/api/transformation-plan")
check("empty: transformation plan is empty", unwrap(tp, "plan", "items") == [], str(tp)[:120])
st, im = call("GET", "/api/impact/metrics")
check("empty: impact metrics empty", unwrap(im, "metrics", "items") == [], str(im)[:120])
st, st_ai = call("GET", "/api/ai/status")
check("empty: Gemini status is a real state string",
      st_ai.get("status") in ("connected", "not_configured", "unreachable", "error"),
      str(st_ai)[:160])
st, ch = call("POST", "/api/ai/chat", {"message": "What is my biggest climate inefficiency?"})
check("disconnected/no-data chat returns a status and no invented answer",
      ch.get("status") in ("no_data", "not_configured", "unreachable", "error"),
      str(ch)[:160])

print("\n== Loading each business through the API ==")
for bid in sorted(pack_assess):
    expected = pack_assess[bid]
    payload = json.load(open(os.path.join(PACK, "api_payloads", f"{bid}_payload.json"),
                             encoding="utf-8"))
    call("POST", "/api/profile/reset")
    st, r1 = call("POST", "/api/profile", payload["profile"])
    check(f"{bid}: profile accepted", st == 200, f"HTTP {st} {str(r1)[:120]}")
    st, r2 = call("POST", "/api/assessment", payload["assessment"])
    check(f"{bid}: assessment accepted", st == 200, f"HTTP {st} {str(r2)[:120]}")
    st, fp = call("POST", "/api/climate-fingerprint/generate")
    if st != 200 or not isinstance(fp, dict):
        check(f"{bid}: fingerprint generated", False, f"HTTP {st} {str(fp)[:160]}")
        continue
    check(f"{bid}: fingerprint generated", True)

    worst = abs(float(fp.get("overallScore", -1)) - float(expected["overall_climate_score"]))
    dims = {d["dimension"]: d["score"] for d in fp.get("dimensions", [])}
    for d, col in DIM.items():
        worst = max(worst, abs(float(dims.get(d, -1)) - float(expected[col])))
    check(f"{bid}: app scores match climate_assessments.xlsx", worst < 0.05,
          f"max deviation {worst:.3f}")
    check(f"{bid}: stage label matches ({expected['risk_level']})",
          fp.get("scoreLabel") == expected["risk_level"],
          f"{fp.get('scoreLabel')} vs {expected['risk_level']}")

    st, reco = call("GET", "/api/solutions/recommendations?top_n=6")
    reco = unwrap(reco, "recommendations", "items")
    n_rec = len(reco)
    check(f"{bid}: recommendations returned ({n_rec})", n_rec >= 1, str(reco)[:160])
    if reco and isinstance(reco[0], dict):
        check(f"{bid}: recommendations carry a solution + reason",
              bool(reco[0].get("solution") or reco[0].get("title")),
              str(reco[0])[:160])

    sol_ids = [r["solution_id"] for r in rows("solution_recommendations")
               if r["business_id"] == bid] or ["sol-solar"]
    st, sim = call("POST", "/api/scenarios/simulate",
                   {"selected_solution_ids": sol_ids, "adoption_scale_percent": 100})
    check(f"{bid}: scenario simulator ran", st == 200 and isinstance(sim, dict),
          f"HTTP {st} {str(sim)[:160]}")

    st, plan = call("POST", "/api/transformation-plan/generate")
    plan = unwrap(plan, "plan", "items")
    n_plan = len(plan)
    check(f"{bid}: transformation plan generated ({n_plan})", n_plan >= 1, str(plan)[:160])

    st, rep = call("POST", "/api/reports/climate/generate")
    check(f"{bid}: climate report generated",
          st == 200 and isinstance(rep, dict) and bool(rep.get("report_id")), str(rep)[:160])

    call("POST", "/api/climate-fingerprint/generate")
    st, hist = call("GET", "/api/climate-fingerprint/history?limit=24")
    hist = unwrap(hist, "snapshots", "history")
    check(f"{bid}: fingerprint history grows ({len(hist)})", len(hist) >= 2, str(hist)[:160])

    series = [{"month": r["month"], "consumptionKwh": float(r["electricity_kwh"])}
              for r in hist_all if r["business_id"] == bid]
    st, fc = call("POST", "/api/climate-fingerprint/forecast",
                  {"historical_data": series, "metric_key": "consumptionKwh", "periods": 3})
    check(f"{bid}: 24-month history forecasts without fallback",
          isinstance(fc, dict) and fc.get("status") == "success",
          str(fc)[:160])
    st, fc2 = call("POST", "/api/climate-fingerprint/forecast",
                   {"historical_data": series[:6], "metric_key": "consumptionKwh", "periods": 3})
    check(f"{bid}: 6 months of history is refused (insufficient_data)",
          isinstance(fc2, dict) and fc2.get("status") == "insufficient_data", str(fc2)[:160])

    ba = [r for r in impact_all if r["business_id"] == bid]
    if ba:
        before = {r["metric"]: float(r["baseline_value"]) for r in ba}
        after = {r["metric"]: float(r["after_value"]) for r in ba}
        st, imp = call("POST", "/api/impact", {"before": before, "after": after,
                                              "intervention_ids": sol_ids[:2],
                                              "notes": "Pack before/after rows (test data)"})
        got = {m["metric"]: m["percentage_change"] for m in (imp.get("calculated_metrics") or [])} \
            if isinstance(imp, dict) else {}
        # The API reports the signed change ((after-before)/before); the pack reports
        # the FAVOURABLE change (positive = better). Same numbers, opposite sign for
        # the lower-is-better metrics.
        mismatch = 0
        for r in ba:
            exp_fav = float(r["improvement_percent"])
            higher_better = r["direction"].startswith("Increase")
            exp_api = exp_fav if higher_better else -exp_fav
            gotv = got.get(r["metric"])
            if gotv is None or abs(gotv - exp_api) > 0.2:
                mismatch += 1
        check(f"{bid}: impact verification recomputes the table's changes", mismatch == 0,
              f"{mismatch}/{len(ba)} metrics differ; api={str(got)[:150]}")

print("\n== Final empty-state re-check ==")
call("POST", "/api/profile/reset")
st, prof = call("GET", "/api/profile")
check("reset clears the profile again", prof is None, str(prof)[:120])

fails = [r for r in RESULTS if not r[1]]
print(f"\n{len(RESULTS) - len(fails)}/{len(RESULTS)} end-to-end checks passed")
if fails:
    print("\nFailures:")
    for n, _, d in fails:
        print(f"  - {n}: {d}")
sys.exit(0 if not fails else 1)
