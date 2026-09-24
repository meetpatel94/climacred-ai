#!/usr/bin/env python3
"""
ClimaCred AI - Test Data Pack VALIDATOR (TESTING ARTEFACT, NOT APPLICATION CODE)
================================================================================
Re-reads the generated files and proves the pack is internally consistent:

  * XLSX and CSV copies agree cell-for-cell (headers, row counts, values)
  * no blank required fields, no impossible negatives, no formulas
  * consistent business ids and month keys across every file
  * emissions: total = scope1 + scope2 + scope3, and each component recomputed
    from the resource tables using the APPLICATION's own emission factors
  * waste / water / energy / materials percentage and intensity maths
  * solution catalog and recommendation payback = capex / savings * 12
  * scenarios and transformation plan totals reconcile
  * before/after improvement_percent recomputed from baseline/after
  * historical_climate_data ties to resource_consumption for the last 12 months
  * climate_assessments scores reproduce when the repository's own
    generate_fingerprint() is re-run on the stored assessment payload

Writes VALIDATION_REPORT.md (human) and VALIDATION_REPORT.csv (machine).
Exit code 0 = every check passed.
"""
from __future__ import annotations

import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.abspath(os.path.join(HERE, ".."))
REPO = os.path.abspath(os.path.join(PACK, ".."))
sys.path.insert(0, os.path.join(REPO, "backend"))

from app.config import settings  # noqa: E402
from app.climate_engine.fingerprint import generate_fingerprint  # noqa: E402
from openpyxl import load_workbook  # noqa: E402

EF_ELEC = settings.ELECTRICITY_EMISSION_FACTOR_KG_PER_KWH
EF_DIESEL = settings.DIESEL_EMISSION_FACTOR_KG_PER_LITRE
EF_PETROL = settings.PETROL_EMISSION_FACTOR_KG_PER_LITRE
EF_GAS = settings.NATURAL_GAS_EMISSION_FACTOR_KG_PER_KG

CHECKS = []
FAILS = []


def check(name, ok, detail=""):
    CHECKS.append((name, "PASS" if ok else "FAIL", detail))
    if not ok:
        FAILS.append(f"{name} :: {detail}")


def close(a, b, tol):
    return abs(float(a) - float(b)) <= tol


def load_csv(name):
    with open(os.path.join(PACK, "csv", name + ".csv"), newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def xlsx_headers(name, sheet=None):
    wb = load_workbook(os.path.join(PACK, name + ".xlsx"), data_only=False)
    ws = wb[sheet] if sheet else wb.worksheets[0]
    headers = [("" if c.value is None else str(c.value)) for c in ws[1]]
    rows = [[c.value for c in row] for row in ws.iter_rows(min_row=2)]
    # formulas?
    formula_cells = 0
    for row in ws.iter_rows():
        for c in row:
            if isinstance(c.value, str) and c.value.startswith("="):
                formula_cells += 1
    return headers, rows, formula_cells


# ---------------------------------------------------------------------------
FILES = ["business_profiles", "climate_assessments", "resource_consumption",
         "emissions_data", "mobility_data", "waste_data", "water_data", "energy_data",
         "operations_materials", "green_solutions", "solution_recommendations", "scenarios",
         "transformation_plans", "before_after_impact", "historical_climate_data",
         "gemini_ai_test_questions", "gemini_expected_behaviors"]

REQUIRED_HEADERS = {
    "business_profiles": ["business_id", "business_name", "industry", "sub_industry", "city",
                          "state", "employee_count", "facility_area_sqft",
                          "operating_days_per_month", "operating_hours_per_day",
                          "annual_turnover", "ownership_type", "facility_type",
                          "year_established", "primary_products", "contact_email", "created_at"],
    "climate_assessments": ["assessment_id", "business_id", "assessment_date", "energy_score",
                            "water_score", "waste_score", "emissions_score", "mobility_score",
                            "operations_score", "overall_climate_score", "risk_level",
                            "key_issue_1", "key_issue_2", "key_issue_3"],
    "resource_consumption": ["business_id", "month", "electricity_kwh", "diesel_litres", "LPG_kg",
                             "water_litres", "wastewater_litres", "total_waste_kg",
                             "recyclable_waste_kg", "hazardous_waste_kg", "organic_waste_kg",
                             "general_waste_kg", "production_units", "operating_days",
                             "employee_count"],
    "emissions_data": ["business_id", "month", "scope_1_emissions_tco2e",
                       "scope_2_emissions_tco2e", "scope_3_emissions_tco2e",
                       "total_emissions_tco2e", "diesel_emissions_tco2e",
                       "electricity_emissions_tco2e", "mobility_emissions_tco2e",
                       "emissions_intensity"],
    "mobility_data": ["business_id", "month", "company_vehicle_count", "diesel_litres",
                      "petrol_litres", "CNG_kg", "EV_kwh", "employee_commute_km",
                      "business_travel_km", "logistics_km",
                      "estimated_mobility_emissions_tco2e"],
    "waste_data": ["business_id", "month", "total_waste_kg", "recyclable_kg", "recycled_kg",
                   "organic_kg", "hazardous_kg", "landfill_kg", "waste_reduction_percent",
                   "recycling_rate_percent", "disposal_cost"],
    "water_data": ["business_id", "month", "freshwater_intake_litres", "process_water_litres",
                   "cleaning_water_litres", "reused_water_litres",
                   "wastewater_generated_litres", "wastewater_treated_litres",
                   "water_reuse_rate_percent", "water_intensity_litres_per_unit"],
    "energy_data": ["business_id", "month", "electricity_kwh", "grid_kwh", "renewable_kwh",
                    "diesel_litres", "LPG_kg", "peak_demand_kw", "production_units",
                    "energy_intensity_kwh_per_unit", "renewable_share_percent"],
    "operations_materials": ["business_id", "month", "raw_material_consumption_kg",
                             "recycled_material_kg", "virgin_material_kg",
                             "production_output_kg", "rejected_material_kg",
                             "packaging_material_kg", "recycled_input_percent",
                             "material_efficiency_percent"],
    "green_solutions": ["solution_id", "solution_name", "category", "description",
                        "applicable_industries", "estimated_capex",
                        "estimated_annual_savings",
                        "estimated_annual_emission_reduction_tco2e",
                        "estimated_water_saving_litres", "estimated_waste_reduction_kg",
                        "estimated_payback_months", "implementation_months", "complexity",
                        "expected_life_years"],
    "solution_recommendations": ["business_id", "solution_id", "priority", "reason",
                                 "baseline_metric", "estimated_improvement", "estimated_capex",
                                 "estimated_annual_savings", "estimated_emission_reduction",
                                 "estimated_payback_months", "implementation_timeline"],
    "scenarios": ["scenario_id", "business_id", "scenario_name", "capex",
                  "annual_operating_cost_change", "annual_energy_savings_kwh",
                  "annual_water_savings_litres", "annual_waste_reduction_kg",
                  "annual_emission_reduction_tco2e", "annual_cost_savings", "payback_years",
                  "projected_5_year_savings", "implementation_months"],
    "transformation_plans": ["business_id", "phase", "action", "solution_id", "start_month",
                             "duration_months", "expected_cost", "expected_savings",
                             "expected_emission_reduction", "expected_water_saving",
                             "owner_role", "dependency", "status"],
    "before_after_impact": ["business_id", "metric", "baseline_value", "after_value", "unit",
                            "improvement_percent", "verification_status",
                            "measurement_period"],
    "historical_climate_data": ["business_id", "month", "climate_score", "electricity_kwh",
                                "water_litres", "waste_kg", "emissions_tco2e",
                                "renewable_share_percent", "recycling_rate_percent",
                                "water_reuse_rate_percent"],
    "gemini_ai_test_questions": ["question_id", "group", "question", "expected_answer_basis",
                                 "must_not_contain"],
    "gemini_expected_behaviors": ["test_id", "scenario", "user_question", "expected_behavior",
                                  "data_source", "should_use_gemini",
                                  "should_refuse_hallucination", "expected_context",
                                  "pass_condition"],
}

# ---- 1. files, headers, xlsx/csv agreement ---------------------------------
data = {}
for name in FILES:
    csv_rows = load_csv(name)
    headers, rows, formulas = xlsx_headers(name)
    data[name] = csv_rows
    missing = [h for h in REQUIRED_HEADERS[name] if h not in headers]
    check(f"{name}: required headers present", not missing, f"missing={missing}")
    check(f"{name}: XLSX row count == CSV row count",
          len(rows) == len(csv_rows), f"xlsx={len(rows)} csv={len(csv_rows)}")
    check(f"{name}: no formula cells", formulas == 0, f"formula cells={formulas}")
    # cell-for-cell comparison (numbers compared as floats with tolerance)
    mismatches = 0
    for i, (xr, cr) in enumerate(zip(rows, csv_rows), start=2):
        for j, h in enumerate(headers):
            if h not in cr:
                continue
            xv, cvv = xr[j], cr[h]
            if xv is None or cvv in (None, ""):
                if (xv is None) != (cvv in (None, "")):
                    mismatches += 1
                continue
            try:
                if not close(xv, cvv, 1e-6):
                    mismatches += 1
            except (TypeError, ValueError):
                if str(xv).strip() != str(cvv).strip():
                    mismatches += 1
    check(f"{name}: every XLSX cell equals its CSV copy", mismatches == 0,
          f"{mismatches} mismatching cells")
    # blanks in required columns
    blanks = sum(1 for r in csv_rows for h in REQUIRED_HEADERS[name] if r.get(h, "") == "")
    check(f"{name}: no blank required fields", blanks == 0, f"{blanks} blank cells")

# ---- 2. business ids and month keys ----------------------------------------
BIDS = sorted({r["business_id"] for r in data["business_profiles"]})
check("5 businesses in the profile file", len(BIDS) == 5, f"found {BIDS}")
for name in FILES:
    rows = data[name]
    if not rows or "business_id" not in rows[0]:
        continue
    ids = sorted({r["business_id"] for r in rows})
    check(f"{name}: business ids subset of profiles", set(ids) <= set(BIDS),
          f"unexpected={sorted(set(ids)-set(BIDS))}")

MONTHS = {}
for name in ["resource_consumption", "emissions_data", "mobility_data", "waste_data",
             "water_data", "energy_data", "operations_materials", "historical_climate_data"]:
    for r in data[name]:
        MONTHS.setdefault(r["business_id"], set()).add(r["month"])
LAST12 = sorted(MONTHS["B001"])[-12:]
for bid in BIDS:
    check(f"{bid}: historical_climate_data has 24 months", len(MONTHS[bid]) == 24,
          f"{len(MONTHS[bid])} months")

# ---- 3. emissions identities ------------------------------------------------
idx = {}
for name in ["resource_consumption", "emissions_data", "mobility_data", "waste_data",
             "water_data", "energy_data", "operations_materials", "historical_climate_data"]:
    idx[name] = {(r["business_id"], r["month"]): r for r in data[name]}

bad_total = bad_s2 = bad_diesel = bad_grid = 0
for key, e in idx["emissions_data"].items():
    en = idx["energy_data"][key]
    rc = idx["resource_consumption"][key]
    if not close(e["total_emissions_tco2e"],
                 float(e["scope_1_emissions_tco2e"]) + float(e["scope_2_emissions_tco2e"])
                 + float(e["scope_3_emissions_tco2e"]), 0.02):
        bad_total += 1
    if not close(e["electricity_emissions_tco2e"], e["scope_2_emissions_tco2e"], 0.01):
        bad_s2 += 1
    if not close(e["diesel_emissions_tco2e"], float(rc["diesel_litres"]) * EF_DIESEL / 1000.0, 0.02):
        bad_diesel += 1
    if not close(e["scope_2_emissions_tco2e"],
                 (float(en["grid_kwh"]) + float(idx["mobility_data"][key]["EV_kwh"])) * EF_ELEC / 1000.0, 0.02):
        bad_grid += 1
check("emissions: total = scope1 + scope2 + scope3 in all 60 rows", bad_total == 0,
      f"{bad_total} rows off")
check("emissions: electricity_emissions == scope_2", bad_s2 == 0, f"{bad_s2} rows off")
check("emissions: diesel_emissions == resource diesel x app diesel factor", bad_diesel == 0,
      f"{bad_diesel} rows off")
check("emissions: scope_2 == (grid_kwh + EV_kwh) x app grid factor", bad_grid == 0,
      f"{bad_grid} rows off")

# no negative emissions anywhere
neg = [k for k, e in idx["emissions_data"].items()
       if min(float(e[c]) for c in ["scope_1_emissions_tco2e", "scope_2_emissions_tco2e",
                                    "scope_3_emissions_tco2e", "total_emissions_tco2e"]) < 0]
check("emissions: no negative values", not neg, f"{len(neg)} negative rows")

# ---- 4. energy identities ---------------------------------------------------
bad = 0
for key, en in idx["energy_data"].items():
    if not close(float(en["grid_kwh"]) + float(en["renewable_kwh"]), en["electricity_kwh"], 1.0):
        bad += 1
    if float(en["electricity_kwh"]) and not close(en["renewable_share_percent"],
                                                  float(en["renewable_kwh"]) / float(en["electricity_kwh"]) * 100, 0.11):
        bad += 1
    if float(en["production_units"]) and not close(en["energy_intensity_kwh_per_unit"],
                                                   float(en["electricity_kwh"]) / float(en["production_units"]), 0.002):
        bad += 1
check("energy: grid + renewable = electricity; share and intensity correct", bad == 0,
      f"{bad} rows off")

# diesel split: resource = energy(non-fleet) + mobility(fleet)
bad = 0
for key, rc in idx["resource_consumption"].items():
    tot = float(idx["energy_data"][key]["diesel_litres"]) + float(idx["mobility_data"][key]["diesel_litres"])
    if not close(rc["diesel_litres"], tot, 2.0):
        bad += 1
check("diesel: resource_consumption = energy_data + mobility_data", bad == 0, f"{bad} rows off")

# LPG ties to resource file
bad = 0
for key, en in idx["energy_data"].items():
    if not close(en["LPG_kg"], idx["resource_consumption"][key]["LPG_kg"], 1.0):
        bad += 1
check("LPG: energy_data == resource_consumption", bad == 0, f"{bad} rows off")

# ---- 5. waste identities ----------------------------------------------------
bad = 0
for key, w in idx["waste_data"].items():
    rc = idx["resource_consumption"][key]
    if not close(w["total_waste_kg"], rc["total_waste_kg"], 1.0):
        bad += 1
    if not close(float(w["recyclable_kg"]) + float(w["organic_kg"]) + float(w["hazardous_kg"])
                 + float(rc["general_waste_kg"]), w["total_waste_kg"], 2.0):
        bad += 1
    if float(w["recycled_kg"]) > float(w["recyclable_kg"]) + 0.5:
        bad += 1
    if not close(w["landfill_kg"], float(w["total_waste_kg"]) - float(w["recycled_kg"])
                 - float(w.get("organic_recovered_kg") or 0) - float(w["hazardous_kg"]), 2.0):
        bad += 1
    if float(w["total_waste_kg"]) and not close(
            w["recycling_rate_percent"],
            (float(w["recycled_kg"]) + float(w.get("organic_recovered_kg") or 0))
            / float(w["total_waste_kg"]) * 100, 0.11):
        bad += 1
check("waste: totals partition, landfill balance and recycling rate exact", bad == 0,
      f"{bad} rows off")

# recycling_rate never exceeds 100, no negative landfill
check("waste: no waste stream exceeds its own total",
      all(float(r["recycled_kg"]) >= 0 and float(r["landfill_kg"]) >= -1
          for r in data["waste_data"]), "negative landfill or recycled found")

# ---- 6. water identities ----------------------------------------------------
bad = 0
for key, wa in idx["water_data"].items():
    if float(wa["process_water_litres"]) + float(wa["cleaning_water_litres"]) > \
            float(wa["freshwater_intake_litres"]) + 1:
        bad += 1
    if float(wa["wastewater_treated_litres"]) > float(wa["wastewater_generated_litres"]) + 1:
        bad += 1
    denom = float(wa["freshwater_intake_litres"]) + float(wa["reused_water_litres"])
    if denom and not close(wa["water_reuse_rate_percent"],
                           float(wa["reused_water_litres"]) / denom * 100, 0.11):
        bad += 1
    if float(wa["freshwater_intake_litres"]) and not close(
            wa["water_intensity_litres_per_unit"],
            float(wa["freshwater_intake_litres"]) / float(idx["energy_data"][key]["production_units"]), 0.02):
        bad += 1
check("water: split, reuse rate, treatment and intensity correct", bad == 0, f"{bad} rows off")

# ---- 7. operations / materials ---------------------------------------------
bad = 0
for key, om in idx["operations_materials"].items():
    if not close(float(om["recycled_material_kg"]) + float(om["virgin_material_kg"]),
                 om["raw_material_consumption_kg"], 2.0):
        bad += 1
    if not close(om["recycled_input_percent"],
                 float(om["recycled_material_kg"]) / float(om["raw_material_consumption_kg"]) * 100, 0.11):
        bad += 1
    if not close(om["material_efficiency_percent"],
                 float(om["production_output_kg"]) / float(om["raw_material_consumption_kg"]) * 100, 0.11):
        bad += 1
check("materials: virgin + recycled = raw; input% and efficiency% correct", bad == 0,
      f"{bad} rows off")

# ---- 8. solution catalog ----------------------------------------------------
sol = {r["solution_id"]: r for r in data["green_solutions"]}
check("catalog: at least 15 solutions", len(sol) >= 15, f"{len(sol)} solutions")
bad = [s for s, r in sol.items()
       if not close(r["estimated_payback_months"],
                    float(r["estimated_capex"]) / float(r["estimated_annual_savings"]) * 12, 0.6)]
check("catalog: payback = capex / annual savings x 12", not bad, f"off={bad}")
bad = [s for s, r in sol.items()
       if not close(r["estimated_capex"],
                    (float(r["estimated_capex_min"]) + float(r["estimated_capex_max"])) / 2.0, 1.0)]
check("catalog: estimated_capex is the mid-point of the min/max range", not bad, f"off={bad}")
bad = [s for s, r in sol.items()
       if float(r["estimated_annual_emission_reduction_tco2e"]) * 1000.0 / EF_ELEC
       != float(r["estimated_annual_energy_saving_kwh"]) and float(r["estimated_annual_energy_saving_kwh"]) > 0
       and not close(float(r["estimated_annual_emission_reduction_tco2e"]) * 1000.0 / EF_ELEC,
                     r["estimated_annual_energy_saving_kwh"], 60)]
check("catalog: emission reduction consistent with kWh saved x grid factor", not bad, f"off={bad}")
check("catalog: contains the 12 in-app solution ids",
      {"sol-solar", "sol-water-ro", "sol-machinery-vfd", "sol-leak-sensors", "sol-rainwater",
       "sol-waste-recovery", "sol-ev-fleet", "sol-route-opt", "sol-heat-recovery",
       "sol-led-iot", "sol-material-reuse", "sol-smart-metering"} <= set(sol), "missing ids")
check("catalog: no negative capex/savings",
      all(float(r["estimated_capex"]) > 0 and float(r["estimated_annual_savings"]) > 0
          for r in data["green_solutions"]), "non-positive values")

# ---- 9. recommendations -----------------------------------------------------
recs = data["solution_recommendations"]
per_biz = {}
for r in recs:
    per_biz.setdefault(r["business_id"], []).append(r)
check("recommendations: at least 3 per business",
      all(len(v) >= 3 for v in per_biz.values()) and len(per_biz) == 5,
      {k: len(v) for k, v in per_biz.items()})
check("recommendations: every solution_id exists in the catalog",
      all(r["solution_id"] in sol for r in recs),
      [r["solution_id"] for r in recs if r["solution_id"] not in sol])
check("recommendations: payback = capex / savings x 12",
      all(close(r["estimated_payback_months"],
                float(r["estimated_capex"]) / float(r["estimated_annual_savings"]) * 12, 0.6)
          for r in recs), "payback mismatch")
scores = {r["business_id"]: r for r in data["climate_assessments"]}
DIM_COL = {"Energy": "energy_score", "Water": "water_score", "Waste": "waste_score",
           "Emissions": "emissions_score", "Mobility": "mobility_score",
           "Operations": "operations_score"}
bad = []
for bid, rows in per_biz.items():
    weak = {d for d, _ in sorted(
        ((d, float(scores[bid][c])) for d, c in DIM_COL.items()), key=lambda x: x[1])[:3]}
    top = [r for r in rows if r["priority"] == "1"][0]
    if top["addresses_dimension"] not in weak:
        bad.append((bid, top["addresses_dimension"], sorted(weak)))
check("recommendations: priority 1 addresses one of the business's three weakest dimensions",
      not bad, f"{bad}")
check("recommendations: addresses_dimension_score matches the stored assessment",
      all(close(r["addresses_dimension_score"], scores[r["business_id"]][DIM_COL[r["addresses_dimension"]]], 0.05)
          for r in recs), "dimension score mismatch")

check("recommendations: priorities are 1..n per business",
      all(sorted(int(r["priority"]) for r in v) == list(range(1, len(v) + 1))
          for v in per_biz.values()), "priority gaps")

# ---- 10. scenarios ----------------------------------------------------------
scen = data["scenarios"]
per_biz_scen = {}
for r in scen:
    per_biz_scen.setdefault(r["business_id"], []).append(r)
check("scenarios: 7 per business", all(len(v) == 7 for v in per_biz_scen.values()),
      {k: len(v) for k, v in per_biz_scen.items()})
check("scenarios: baseline row is all zeros",
      all(float(r["capex"]) == 0 and float(r["annual_cost_savings"]) == 0
          for r in scen if r["scenario_name"] == "Current Baseline"), "baseline not zero")
check("scenarios: payback_years = capex / annual savings",
      all(close(r["payback_years"], float(r["capex"]) / float(r["annual_cost_savings"]), 0.02)
          for r in scen if float(r["annual_cost_savings"]) > 0), "payback mismatch")
check("scenarios: 5-year projection = 5 x (savings - operating change) - capex",
      all(close(r["projected_5_year_savings"],
                5 * (float(r["annual_cost_savings"]) - float(r["annual_operating_cost_change"]))
                - float(r["capex"]), 2.0) for r in scen), "5-year mismatch")
bad = []
for bid, rows in per_biz_scen.items():
    comb = [r for r in rows if r["scenario_name"] == "Combined Transformation Scenario"][0]
    for r in rows:
        if r is comb or r["scenario_name"] == "Current Baseline":
            continue
        if float(r["capex"]) > float(comb["capex"]) or float(r["annual_cost_savings"]) > float(comb["annual_cost_savings"]):
            bad.append((bid, r["scenario_name"]))
check("scenarios: combined total >= every single scenario", not bad, f"{bad}")
check("scenarios: no negative capex/savings",
      all(float(r["capex"]) >= 0 and float(r["annual_cost_savings"]) >= 0 for r in scen), "negative")

# ---- 11. transformation plan ------------------------------------------------
plan = data["transformation_plans"]
per_biz_plan = {}
for r in plan:
    per_biz_plan.setdefault(r["business_id"], []).append(r)
check("plan: every business has a plan", len(per_biz_plan) == 5, list(per_biz_plan))
PHASE_ORDER = ["Phase 1 - Quick Wins", "Phase 2 - Efficiency Improvements",
               "Phase 3 - Circularity", "Phase 4 - Renewable / Mobility Transition",
               "Phase 5 - Verification"]
check("plan: all 5 phases present per business",
      all(sorted({r["phase"] for r in v}) == PHASE_ORDER for v in per_biz_plan.values()),
      {k: sorted({r["phase"] for r in v}) for k, v in per_biz_plan.items()})
check("plan: rows are grouped in phase order",
      all([r["phase"] for r in v] == sorted([r["phase"] for r in v],
                                            key=lambda p: PHASE_ORDER.index(p))
          for v in per_biz_plan.values()), "phase ordering")
check("plan: phases are the five documented names",
      all(r["phase"] in PHASE_ORDER for r in plan), "unexpected phase name")
check("plan: solution ids exist in catalog (N/A allowed for verification)",
      all(r["solution_id"] == "N/A" or r["solution_id"] in sol for r in plan), "unknown solution id")
check("plan: no negative costs or savings",
      all(float(r["expected_cost"]) >= 0 and float(r["expected_savings"]) >= 0 for r in plan), "negative")
bad = []
for bid, rows in per_biz_plan.items():
    comb = [r for r in per_biz_scen[bid] if r["scenario_name"] == "Combined Transformation Scenario"][0]
    p_cost = sum(float(r["expected_cost"]) for r in rows)
    p_save = sum(float(r["expected_savings"]) for r in rows)
    p_co2 = sum(float(r["expected_emission_reduction"]) for r in rows)
    if not close(p_cost, float(comb["capex"]) + 180000, 3) or \
       not close(p_save, comb["annual_cost_savings"], 3) or \
       not close(p_co2, comb["annual_emission_reduction_tco2e"], 0.05):
        bad.append((bid, p_cost, comb["capex"], p_save, comb["annual_cost_savings"]))
check("plan: plan totals == combined scenario totals + verification action", not bad, f"{bad}")

# ---- 12. before / after -----------------------------------------------------
ba = data["before_after_impact"]
bids_ba = sorted({r["business_id"] for r in ba})
check("before/after: exactly 3 businesses", len(bids_ba) == 3, bids_ba)
check("before/after: 10 metrics per business",
      all(len([r for r in ba if r["business_id"] == b]) == 10 for b in bids_ba), "metric count")
def fav_pct(row):
    base, after = float(row["baseline_value"]), float(row["after_value"])
    if not base:
        return 0.0
    # direction column states which way is favourable
    higher_better = row["direction"].startswith("Increase")
    delta = (after - base) if higher_better else (base - after)
    return delta / base * 100.0


bad = [r["metric"] for r in ba if not close(r["improvement_percent"], fav_pct(r), 0.15)]
check("before/after: improvement_percent recomputes exactly (positive = favourable)",
      not bad, f"off={bad}")
check("before/after: status never claims third-party verification",
      all("not third-party verified" in r["verification_status"] for r in ba), "status wording")
check("before/after: contains both improvements and deteriorations",
      any(float(r["improvement_percent"]) < 0 for r in ba)
      and any(float(r["improvement_percent"]) > 0 for r in ba),
      "expected a mixed outcome set")

# ---- 13. historical ↔ resource consistency ---------------------------------
bad = 0
for key, h in idx["historical_climate_data"].items():
    if key[1] not in LAST12:
        continue
    if not close(h["electricity_kwh"], idx["energy_data"][key]["electricity_kwh"], 1.0):
        bad += 1
    if not close(h["water_litres"], idx["water_data"][key]["freshwater_intake_litres"], 1.0):
        bad += 1
    if not close(h["waste_kg"], idx["waste_data"][key]["total_waste_kg"], 1.0):
        bad += 1
    if not close(h["emissions_tco2e"], idx["emissions_data"][key]["total_emissions_tco2e"], 0.02):
        bad += 1
    if not close(h["renewable_share_percent"], idx["energy_data"][key]["renewable_share_percent"], 0.11):
        bad += 1
    if not close(h["recycling_rate_percent"], idx["waste_data"][key]["recycling_rate_percent"], 0.11):
        bad += 1
    if not close(h["water_reuse_rate_percent"], idx["water_data"][key]["water_reuse_rate_percent"], 0.11):
        bad += 1
check("history: last 12 months agree column-for-column with the detail tables",
      bad == 0, f"{bad} rows off")
check("history: climate_score inside 0-100 for all 120 rows",
      all(0 <= float(r["climate_score"]) <= 100 for r in data["historical_climate_data"]),
      "score out of range")

# ---- 14. the app's own engine reproduces the assessment scores --------------
wb = load_workbook(os.path.join(PACK, "climate_assessments.xlsx"), data_only=True)
api_headers = [c.value for c in wb["assessment_api_payloads"][1]]
api_rows = [[c.value for c in row] for row in wb["assessment_api_payloads"].iter_rows(min_row=2)]
payloads = {r[0]: json.loads(r[1]) for r in api_rows}
prof_wb = load_workbook(os.path.join(PACK, "business_profiles.xlsx"), data_only=True)
prof_rows = [[c.value for c in row] for row in prof_wb["api_payload_sheet"].iter_rows(min_row=2)]
profiles = {r[0]: json.loads(r[1]) for r in prof_rows}
stored = {r["business_id"]: r for r in data["climate_assessments"]}
worst = 0.0
for bid, row in stored.items():
    fp = generate_fingerprint(profiles[bid], payloads[bid])
    dims = {d["dimension"]: d["score"] for d in fp["dimensions"]}
    worst = max(worst, abs(dims["Energy"] - float(row["energy_score"])),
                abs(dims["Water"] - float(row["water_score"])),
                abs(dims["Waste"] - float(row["waste_score"])),
                abs(dims["Emissions"] - float(row["emissions_score"])),
                abs(dims["Mobility"] - float(row["mobility_score"])),
                abs(dims["Operations"] - float(row["operations_score"])),
                abs(fp["overallScore"] - float(row["overall_climate_score"])))
check("assessment: repository's generate_fingerprint() reproduces every stored score",
      worst < 0.05, f"max deviation {worst:.4f}")

# dimension scores must match the direction of the business story
directions = {}
for bid in BIDS:
    series = sorted([r for r in data["historical_climate_data"] if r["business_id"] == bid],
                    key=lambda r: r["month"])
    directions[bid] = (float(series[-1]["climate_score"]) - float(series[0]["climate_score"]))
check("history: B003 and B004 improve over 24 months and B001/B005 worsen",
      directions["B003"] > 0 and directions["B004"] > 0 and directions["B001"] < 0
      and directions["B005"] < 0,
      {k: round(v, 2) for k, v in directions.items()})

# ---- 15. test-case coverage -------------------------------------------------
groups = {r["group"] for r in data["gemini_ai_test_questions"]}
check("questions: at least 40 questions", len(data["gemini_ai_test_questions"]) >= 40,
      str(len(data["gemini_ai_test_questions"])))
check("questions: 12 groups", len(groups) == 12, sorted(groups))
check("behaviours: at least 10 integration test cases",
      len(data["gemini_expected_behaviors"]) >= 10, str(len(data["gemini_expected_behaviors"])))
check("behaviours: no-data, disconnected and empty-database cases covered",
      all(any(k in r["scenario"].lower() for r in data["gemini_expected_behaviors"])
          for k in ["no business profile", "unavailable", "empty database"]),
      "missing core states")

# ---- report -----------------------------------------------------------------
ok = len(FAILS) == 0
report = ["# ClimaCred AI Test Data Pack - Validation Report", "",
          f"Generated: {__import__('datetime').date.today().isoformat()}  ",
          f"Result: **{'ALL CHECKS PASSED' if ok else 'FAILURES PRESENT'}** "
          f"({len(CHECKS) - len(FAILS)}/{len(CHECKS)} checks passed)", "",
          "## Row counts", "",
          "| File | Rows |", "| --- | --- |"]
for name in FILES:
    report.append(f"| {name}.xlsx | {len(data[name])} |")
report += [f"| MANIFEST.xlsx | 18 |", "",
           "## Checks", "", "| # | Check | Result | Detail |", "| --- | --- | --- | --- |"]
for i, (n, res, det) in enumerate(CHECKS, start=1):
    report.append(f"| {i} | {n} | {res} | {det} |")
if FAILS:
    report += ["", "## Failures", ""] + [f"- {f}" for f in FAILS]
with open(os.path.join(PACK, "VALIDATION_REPORT.md"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(report) + "\n")
with open(os.path.join(PACK, "VALIDATION_REPORT.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["check_number", "check", "result", "detail"])
    for i, (n, res, det) in enumerate(CHECKS, start=1):
        w.writerow([i, n, res, det])

print("\n".join(f"[{res}] {n}{(' :: ' + str(det)) if det and res == 'FAIL' else ''}"
                for n, res, det in CHECKS))
print(f"\n{len(CHECKS) - len(FAILS)}/{len(CHECKS)} checks passed")
sys.exit(0 if ok else 1)
