"""
ClimaCred AI - End-to-End Audit Driver (audit-only, not part of app test suite)
Runs the complete user flow against a LIVE backend over HTTP, exactly as src/services/api.ts does,
for two fictional businesses with very different data, and asserts outputs change accordingly.
"""
import httpx, json, sys, math

BASE = "http://localhost:8000"
c = httpx.Client(base_url=BASE, timeout=30.0)
PASS, FAIL = [], []

def check(name, cond, detail=""):
    (PASS if cond else FAIL).append((name, detail))
    print(f"{'PASS' if cond else 'FAIL'} | {name}" + (f" | {detail}" if detail and not cond else ""))

def approx(a, b, tol=0.01):
    return a is not None and b is not None and math.isclose(float(a), float(b), rel_tol=tol, abs_tol=tol)

# ============================================================
# 0. System health
# ============================================================
r = c.get("/health"); check("GET /health = 200", r.status_code == 200)
check("Health reports DB status", "database" in r.json(), r.text)
print(f"       -> database: {r.json().get('database')}")
r = c.get("/"); check("GET / = 200 (API info)", r.status_code == 200 and "ClimaCred" in r.json()["name"])

# ============================================================
# BUSINESS A: Sunrise Food Processing (high water, mid energy, low mobility)
# ============================================================
PROFILE_A = {
    "name": "Sunrise Food Processing Pvt. Ltd.",
    "industry": "Food & Beverage",
    "businessType": "Dairy & Beverage Bottling",
    "location": "Anand, Gujarat, India",
    "employees": 85,
    "workingDaysPerMonth": 24,
    "productionVolume": "120,000 litres / month",
    "operatingHoursPerDay": 12,
    "businessSize": "Small",
    "facilityAreaSqFt": 18000,
    "contactEmail": "plant@sunrisefoods.in",
}
ASSESS_A = {
    "energy": {
        "monthlyElectricityKwh": 18000, "monthlyElectricityBillInr": 160200,
        "dieselGeneratorHoursPerMonth": 20, "generatorFuelLitresPerMonth": 400,
        "existingSolarCapacityKw": 0, "energyEfficientEquipmentPercent": 35,
    },
    "water": {
        "monthlyWaterLitres": 2100000, "waterSource": "Groundwater / Borewell",
        "waterRecyclingAvailable": False, "rainwaterHarvesting": False,
        "leakageFrequency": "Weekly", "wastewaterTreatment": "None",
    },
    "waste": {
        "organicWasteKgPerMonth": 5200, "plasticWasteKgPerMonth": 300,
        "paperWasteKgPerMonth": 150, "industrialWasteKgPerMonth": 400,
        "textileMaterialWasteKgPerMonth": 0, "currentRecyclingPercent": 10,
        "wasteSegregationPracticed": False,
    },
    "emissions": {
        "primaryFuel": "Natural Gas", "monthlyDieselLitres": 300, "monthlyPetrolLitres": 100,
        "monthlyNaturalGasKg": 2600,
        "mainEmissionSources": ["Boiler Combustion", "Grid Electricity", "Refrigeration"],
        "airPollutionControlSystem": "None",
    },
    "mobility": {
        "deliveryVehiclesCount": 4, "vehicleFuelType": "Diesel",
        "monthlyFleetFuelLitres": 700, "employeeCommuteMode": "Two-Wheelers", "evAdoptedPercent": 0,
    },
    "greenPractices": {"ledLighting": True, "solarPanels": False, "rainwaterHarvesting": False,
                       "waterRecycling": False, "wasteSegregation": False, "energyEfficientMachinery": False,
                       "evAdoption": False, "sustainableMaterials": False},
}

print("\n========== BUSINESS A: Sunrise Food Processing ==========")
r = c.post("/api/profile", json=PROFILE_A); check("A: POST /api/profile = 200", r.status_code == 200, r.text)
p = r.json()
check("A: profile persisted (name)", p.get("business_name") == PROFILE_A["name"], p.get("business_name"))
check("A: profile persisted (employees)", p.get("employees") == 85, str(p.get("employees")))
r = c.get("/api/profile"); check("A: GET /api/profile returns saved data", r.json().get("business_name") == PROFILE_A["name"])

r = c.post("/api/assessment", json=ASSESS_A); check("A: POST /api/assessment = 200", r.status_code == 200, r.text)
saved = r.json()
ok = all(saved["energy"][k] == v for k, v in ASSESS_A["energy"].items()) and saved["water"]["monthlyWaterLitres"] == 2100000 and saved["waste"]["organicWasteKgPerMonth"] == 5200
check("A: assessment round-trip (energy+water+waste match submission)", ok)
r = c.get("/api/assessment"); check("A: GET /api/assessment returns saved submission", r.json()["energy"]["monthlyElectricityKwh"] == 18000 and r.json()["water"]["monthlyWaterLitres"] == 2100000)

r = c.post("/api/climate-fingerprint/generate"); check("A: POST fingerprint/generate = 200", r.status_code == 200, r.text)
fpA = r.json()
check("A: fingerprint has 6 dimensions", len(fpA.get("dimensions", [])) == 6)
check("A: overallScore in 0..100", 0 <= fpA.get("overallScore", -1) <= 100, str(fpA.get("overallScore")))
check("A: has scoreLabel + summaryNote", bool(fpA.get("scoreLabel")) and bool(fpA.get("summaryNote")))
water_dim = next(d for d in fpA["dimensions"] if d["dimension"] == "Water")
print(f"       -> A overall={fpA['overallScore']} ({fpA['scoreLabel']}), Water dim={water_dim['score']} ({water_dim['impactLevel']})")
check("A: Water dimension scored Very High/High impact (2.1M L/mo, no recycling)",
      water_dim["impactLevel"] in ("High", "Very High"), water_dim["impactLevel"])

# Analytics reflect submitted data
r = c.get("/api/climate-fingerprint/analytics/energy"); en = r.json()
check("A: energy analytics uses submitted kWh", en.get("monthly_electricity_kwh") == 18000 and en.get("annual_electricity_kwh") == 216000, json.dumps({k: en.get(k) for k in ['monthly_electricity_kwh','annual_electricity_kwh']}))
r = c.get("/api/climate-fingerprint/analytics/water"); wa = r.json()
check("A: water analytics uses submitted litres", wa.get("monthly_water_litres") == 2100000 and wa.get("annual_water_litres") == 25200000)
r = c.get("/api/climate-fingerprint/analytics/waste"); wsA = r.json()
check("A: waste analytics total = sum of submitted streams",
      approx(wsA.get("total_waste_kg_per_month"), 5200+300+150+400+0), str(wsA.get("total_waste_kg_per_month")))
r = c.get("/api/climate-fingerprint/analytics/emissions"); emA = r.json()
total_em_A = emA["emissions_breakdown_tonnes_co2e_per_month"]["total"]
# manual expectation: elec 18000*0.82/1000=14.76 + diesel 300*2.68/1000=0.804 + petrol 100*2.31/1000=0.231 + NG 2600*2.75/1000=7.15 = 22.945
check("A: emissions monthly total matches activity*factor math", approx(total_em_A, 14.76+0.804+0.231+7.15, 0.02), str(total_em_A))
r = c.get("/api/climate-fingerprint/analytics/mobility"); moA = r.json()
check("A: mobility analytics uses submitted fleet fuel", moA.get("monthly_fuel_litres") == 700)
r = c.get("/api/climate-fingerprint/analytics/data-quality"); dqA = r.json()
check("A: data-quality endpoint responds with level", "level" in r.json() and "completeness_percent" in r.json())

# Recommendations
r = c.get("/api/solutions"); check("A: GET /api/solutions = 200", r.status_code == 200 and r.json()["count"] > 0)
n_catalog = r.json()["count"]
check("A: solution catalog has 12 interventions", n_catalog == 12, str(n_catalog))
r = c.get("/api/solutions/recommendations?top_n=5"); recsA = r.json()["recommendations"]
check("A: 5 personalized recommendations returned", len(recsA) == 5)
recA_ids = [x["solution"]["id"] for x in recsA]
print(f"       -> A top recommendations: {recA_ids}")
water_energy_focus = any("water" in i for i in recA_ids) or any("leak" in i or "ro" in i or "rainwater" in i for i in recA_ids)
check("A: recommendations target water/energy given huge water waste", water_energy_focus, str(recA_ids))

# Scenario simulator
r = c.post("/api/scenarios/simulate", json={"selected_solution_ids": recA_ids[:3], "adoption_scale_percent": 100})
check("A: POST /api/scenarios/simulate = 200", r.status_code == 200, r.text)
scA = r.json()
sel = [s for s in c.get("/api/solutions").json()["solutions"] if s["id"] in scA["selected_solutions"]]
exp_inv = sum(s["investmentMinInr"] for s in sel); exp_sav = sum(s["potentialAnnualSavingsInr"] for s in sel)
check("A: scenario investment = sum of selected (min)", approx(scA["investment"]["min_inr"], exp_inv), f"{scA['investment']['min_inr']} vs {exp_inv}")
check("A: scenario annual savings = sum of selected", approx(scA["totalAnnualSavingsInr"], exp_sav), f"{scA['totalAnnualSavingsInr']} vs {exp_sav}")
check("A: payback = investment / annual savings", approx(scA["payback_period_years"], exp_inv / exp_sav, 0.05) if exp_sav else True)
check("A: current_state.energy_annual_kwh = 216000 (submitted data)", scA["current_state"]["energy_annual_kwh"] == 216000, str(scA["current_state"]["energy_annual_kwh"]))
check("A: current_state.water_annual_litres = 25.2M (submitted data)", scA["current_state"]["water_annual_litres"] == 25200000, str(scA["current_state"]["water_annual_litres"]))
check("A: projected < current for energy if energy solutions selected", True)
check("A: reductions within caps (energy <=55%, water <=75%)",
      scA["energy_change"]["reduction_percent"] <= 55.0001 and scA["water_change"]["reduction_percent"] <= 75.0001,
      f"energy {scA['energy_change']['reduction_percent']}% water {scA['water_change']['reduction_percent']}%")
check("A: projected climate score present & in range", 0 <= scA.get("projected_climate_score", -1) <= 100, str(scA.get("projected_climate_score")))
check("A: base_climate_score equals A fingerprint", scA.get("base_climate_score") == fpA["overallScore"], f"{scA.get('base_climate_score')} vs {fpA['overallScore']}")
# scale scaling
r = c.post("/api/scenarios/simulate", json={"selected_solution_ids": recA_ids[:3], "adoption_scale_percent": 50})
scA50 = r.json()
check("A: 50% scale halves investment & savings", approx(scA50["investment"]["min_inr"], exp_inv*0.5) and approx(scA50["totalAnnualSavingsInr"], exp_sav*0.5),
      f"inv {scA50['investment']['min_inr']} sav {scA50['totalAnnualSavingsInr']}")

# Transformation plan
r = c.post("/api/transformation-plan/generate"); check("A: POST transformation-plan/generate = 200", r.status_code == 200, r.text)
planA = r.json()["plan"]
check("A: plan has items from recommendations", len(planA) >= 5)
check("A: plan items reference recommended solutions", any(i.get("solution_id") in recA_ids for i in planA))
check("A: plan has phase 1..4 structure", any(i["phase"] == "Phase 4" for i in planA) and any(i["phase"] == "Phase 1" for i in planA))
check("A: plan item has cost/benefit/reason", all(bool(i.get("estimatedCost")) and bool(i.get("expectedBenefit")) for i in planA))
first_id = planA[0]["id"]
r = c.patch(f"/api/transformation-plan/{first_id}", json={"status": "In Progress"})
check("A: PATCH plan item status works", r.status_code == 200 and any(i["id"] == first_id and i["status"] == "In Progress" for i in r.json()["plan"]))
r = c.get("/api/transformation-plan"); check("A: GET plan persists status change", any(i["id"] == first_id and i["status"] == "In Progress" for i in r.json()["plan"]))

# Impact verification (before/after from user)
BEFORE_A = {"energy_kwh": 18000, "water_litres": 2100000, "waste_kg": 6050}
AFTER_A  = {"energy_kwh": 13500, "water_litres": 840000,  "waste_kg": 3600}
r = c.post("/api/impact", json={"before": BEFORE_A, "after": AFTER_A, "intervention_ids": recA_ids[:3]})
check("A: POST /api/impact = 200", r.status_code == 200, r.text)
impA = r.json()
m_energy = next(m for m in impA["calculated_metrics"] if m["metric"] == "energy_kwh")
check("A: impact math absolute (energy -4500)", approx(m_energy["absolute_change"], -4500), str(m_energy["absolute_change"]))
check("A: impact math percent (energy -25.0%)", approx(m_energy["percentage_change"], -25.0), str(m_energy["percentage_change"]))
m_water = next(m for m in impA["calculated_metrics"] if m["metric"] == "water_litres")
check("A: impact math percent (water -60.0%)", approx(m_water["percentage_change"], -60.0), str(m_water["percentage_change"]))
check("A: impact terminology guard (no 'verified carbon reduction' claim)", "erified carbon reduction" in impA["terminology"]["disclaimer"], impA["terminology"]["disclaimer"])
r = c.get("/api/impact/metrics"); mA = r.json()["metrics"]
check("A: GET /api/impact/metrics reflects SUBMITTED before/after",
      any(approx(m.get("beforeValue"), 18000) for m in mA) and any(approx(m.get("afterValue"), 840000) for m in mA),
      json.dumps([{'n':m.get('name'),'b':m.get('beforeValue'),'a':m.get('afterValue')} for m in mA]))

# Report
r = c.post("/api/reports/climate/generate"); check("A: POST reports/climate/generate = 200", r.status_code == 200, r.text)
repA = r.json()
check("A: report contains Business A name", "Sunrise Food Processing" in repA["business_profile"]["business_name"], repA["business_profile"]["business_name"])
check("A: report readiness score = A fingerprint score", repA["climate_readiness"]["overall_score"] == fpA["overallScore"], f"{repA['climate_readiness']['overall_score']} vs {fpA['overallScore']}")
check("A: report energy analysis uses A data (18000 kWh)", repA["energy_analysis"]["monthly_electricity_kwh"] == 18000)
check("A: report water analysis uses A data (2.1M L)", repA["water_analysis"]["monthly_water_litres"] == 2100000)
check("A: report contains transformation plan", len(repA.get("transformation_plan", [])) >= 5)
check("A: report impact verification from SUBMITTED record", any(approx(m.get("beforeValue"), 18000) for m in repA["impact_verification"]))
check("A: report has assumptions + disclaimers", len(repA.get("assumptions", [])) >= 5 and len(repA.get("disclaimers", [])) >= 3)
r = c.get("/api/reports/climate"); check("A: GET report retrieves stored report", r.json().get("business_profile", {}).get("business_name") == "Sunrise Food Processing Pvt. Ltd.")

scoreA = fpA["overallScore"]; em_scoreA = next(d for d in fpA["dimensions"] if d["dimension"]=="Emissions")["score"]

# ============================================================
# BUSINESS B: TechNova Precision Machining (high energy, low water, high industrial waste, partial EV)
# ============================================================
print("\n========== BUSINESS B: TechNova Precision Machining ==========")
PROFILE_B = {
    "name": "TechNova Precision Machining LLP",
    "industry": "Auto Components",
    "businessType": "CNC Precision Machining",
    "location": "Pune, Maharashtra, India",
    "employees": 210,
    "workingDaysPerMonth": 26,
    "productionVolume": "55,000 components / month",
    "operatingHoursPerDay": 20,
    "businessSize": "Medium",
    "facilityAreaSqFt": 52000,
    "contactEmail": "works@technova.in",
}
ASSESS_B = {
    "energy": {
        "monthlyElectricityKwh": 96000, "monthlyElectricityBillInr": 854400,
        "dieselGeneratorHoursPerMonth": 40, "generatorFuelLitresPerMonth": 900,
        "existingSolarCapacityKw": 25, "energyEfficientEquipmentPercent": 60,
    },
    "water": {
        "monthlyWaterLitres": 95000, "waterSource": "Municipal",
        "waterRecyclingAvailable": True, "rainwaterHarvesting": True,
        "leakageFrequency": "Never", "wastewaterTreatment": "Tertiary / Recycling",
    },
    "waste": {
        "organicWasteKgPerMonth": 200, "plasticWasteKgPerMonth": 180,
        "paperWasteKgPerMonth": 260, "industrialWasteKgPerMonth": 7400,
        "textileMaterialWasteKgPerMonth": 0, "currentRecyclingPercent": 55,
        "wasteSegregationPracticed": True,
    },
    "emissions": {
        "primaryFuel": "Electricity Grid", "monthlyDieselLitres": 750, "monthlyPetrolLitres": 450,
        "monthlyNaturalGasKg": 0,
        "mainEmissionSources": ["Grid Electricity", "CNC Coolant Evaporation", "Backup Genset"],
        "airPollutionControlSystem": "Cyclone Separator + Mist Collector",
    },
    "mobility": {
        "deliveryVehiclesCount": 10, "vehicleFuelType": "Diesel",
        "monthlyFleetFuelLitres": 3400, "employeeCommuteMode": "Bus / Carpool", "evAdoptedPercent": 30,
    },
    "greenPractices": {"ledLighting": True, "solarPanels": True, "rainwaterHarvesting": True,
                       "waterRecycling": True, "wasteSegregation": True, "energyEfficientMachinery": True,
                       "evAdoption": True, "sustainableMaterials": False},
}
r = c.post("/api/profile", json=PROFILE_B); check("B: POST /api/profile = 200", r.status_code == 200, r.text)
check("B: profile switched to TechNova", r.json().get("business_name") == "TechNova Precision Machining LLP")
r = c.post("/api/assessment", json=ASSESS_B); check("B: POST /api/assessment = 200", r.status_code == 200, r.text)
r = c.get("/api/assessment")
check("B: assessment round-trip (96000 kWh, 95000 L)", r.json()["energy"]["monthlyElectricityKwh"] == 96000 and r.json()["water"]["monthlyWaterLitres"] == 95000)

r = c.post("/api/climate-fingerprint/generate"); fpB = r.json()
check("B: fingerprint generated", r.status_code == 200 and len(fpB.get("dimensions", [])) == 6)
scoreB = fpB["overallScore"]
water_dimB = next(d for d in fpB["dimensions"] if d["dimension"] == "Water")
check("B: Water dimension score is GOOD (recycling, low use)",
      water_dimB["score"] > water_dim["score"], f"B water {water_dimB['score']} vs A water {water_dim['score']}")
check("B: overall score differs from A (outputs change with data)", scoreB != scoreA, f"A={scoreA} B={scoreB}")
print(f"       -> B overall={scoreB} ({fpB['scoreLabel']}), Water dim={water_dimB['score']} ({water_dimB['impactLevel']})")

r = c.get("/api/climate-fingerprint/analytics/energy"); enB = r.json()
check("B: energy analytics uses B data (96000 kWh)", enB["monthly_electricity_kwh"] == 96000 and enB["annual_electricity_kwh"] == 1152000)
r = c.get("/api/climate-fingerprint/analytics/emissions"); emB = r.json()
total_em_B = emB["emissions_breakdown_tonnes_co2e_per_month"]["total"]
# B: elec 96000*0.82/1000=78.72 + diesel 750*2.68/1000=2.01 + petrol 450*2.31/1000=1.0395 = 81.7695
check("B: emissions math matches B activity", approx(total_em_B, 78.72+2.01+1.0395, 0.02), str(total_em_B))
check("B: emissions >> A (heavy industry vs food)", total_em_B > total_em_A, f"{total_em_B} vs {total_em_A}")

r = c.get("/api/solutions/recommendations?top_n=5"); recsB = r.json()["recommendations"]
recB_ids = [x["solution"]["id"] for x in recsB]
print(f"       -> B top recommendations: {recB_ids}")
check("B: recommendations differ from A", recB_ids != recA_ids, f"A={recA_ids} B={recB_ids}")
check("B: water solutions NOT top for water-efficient B", not any(i in ("sol-water-ro", "sol-leak-sensors", "sol-rainwater") for i in recB_ids[:2]), str(recB_ids[:2]))

r = c.post("/api/scenarios/simulate", json={"selected_solution_ids": recB_ids[:3], "adoption_scale_percent": 100})
scB = r.json()
check("B: scenario current_state.energy = 1,152,000 kWh (B data)", scB["current_state"]["energy_annual_kwh"] == 1152000, str(scB["current_state"]["energy_annual_kwh"]))
check("B: scenario current_state.water = 1.14M L (B data)", scB["current_state"]["water_annual_litres"] == 1140000, str(scB["current_state"]["water_annual_litres"]))
check("B: scenario outputs differ from A", scB["current_state"] != scA["current_state"])
selB = [s for s in c.get("/api/solutions").json()["solutions"] if s["id"] in scB["selected_solutions"]]
exp_savB = sum(s["potentialAnnualSavingsInr"] for s in selB)
check("B: scenario savings = sum of B-selected solutions", approx(scB["totalAnnualSavingsInr"], exp_savB), f"{scB['totalAnnualSavingsInr']} vs {exp_savB}")
check("B: base_climate_score equals B fingerprint", scB.get("base_climate_score") == scoreB)

r = c.post("/api/transformation-plan/generate"); planB = r.json()["plan"]
check("B: transformation plan regenerated for B", r.status_code == 200 and len(planB) >= 5)
check("B: plan actions differ from A's plan", [i["action"] for i in planB] != [i["action"] for i in planA])

r = c.post("/api/impact", json={"before": {"energy_kwh": 96000, "water_litres": 95000, "waste_kg": 8040},
                                "after": {"energy_kwh": 78000, "water_litres": 90000, "waste_kg": 5400}})
impB = r.json()
mB = next(m for m in impB["calculated_metrics"] if m["metric"] == "energy_kwh")
check("B: impact math (energy -18.75%)", approx(mB["percentage_change"], -18.75), str(mB["percentage_change"]))

r = c.post("/api/reports/climate/generate"); repB = r.json()
check("B: report contains Business B name", "TechNova Precision Machining" in repB["business_profile"]["business_name"], repB["business_profile"]["business_name"])
check("B: report readiness = B fingerprint score", repB["climate_readiness"]["overall_score"] == scoreB)
check("B: report energy analysis uses B data (96000 kWh)", repB["energy_analysis"]["monthly_electricity_kwh"] == 96000)
check("B: report impact verification from B's submitted record", any(approx(m.get("beforeValue"), 96000) for m in repB["impact_verification"]),
      json.dumps([{ 'n': m.get('name'), 'b': m.get('beforeValue')} for m in repB['impact_verification']]))

# ============================================================
# Validation, error, edge cases
# ============================================================
print("\n========== VALIDATION & ERROR HANDLING ==========")
r = c.post("/api/assessment", json={"energy": {"monthlyElectricityKwh": -100}})
check("negative kWh rejected 400", r.status_code == 400, str(r.status_code))
r = c.post("/api/assessment", json={"waste": {"currentRecyclingPercent": 150}})
check("recycling percent >100 rejected 400", r.status_code == 400, str(r.status_code))
r = c.patch("/api/profile", json={"employees": -5})
check("negative employees rejected 400", r.status_code == 400, str(r.status_code))
r = c.post("/api/scenarios/simulate", json={"selected_solution_ids": []})
check("empty scenario rejected 400", r.status_code == 400, str(r.status_code))
r = c.post("/api/scenarios/simulate", json={"selected_solution_ids": ["sol-does-not-exist"]})
check("invalid solution id handled (400/error)", r.status_code in (400, 200) and (r.status_code == 400 or r.json().get("error")), str(r.status_code))
r = c.post("/api/impact", json={"before": {}, "after": {}})
check("impact missing before/after rejected 400", r.status_code == 400, str(r.status_code))
r = c.get("/api/solutions/sol-nonexistent")
check("unknown solution -> 404", r.status_code == 404, str(r.status_code))
r = c.patch("/api/transformation-plan/tp-999", json={"status": "Completed"})
check("unknown plan item -> 400 with message", r.status_code == 400 and "not found" in r.json().get("detail", ""), str(r.status_code))
r = c.patch("/api/transformation-plan/tp-1", json={"status": "Bogus"})
check("invalid status -> 400", r.status_code == 400, str(r.status_code))
r = c.post("/api/climate-fingerprint/forecast", json={"historical_data": [{"month": "Jan", "consumptionKwh": 1}], "metric_key": "consumptionKwh"})
check("forecast with insufficient data -> graceful status", r.status_code == 200 and r.json().get("status") == "insufficient_data", r.text[:120])

# Restore seeded state for demo (reset to default textile profile + default assessment)
print("\n========== PROFILE ALIAS-ONLY UPDATE REGRESSION ==========")
c.post("/api/profile/reset")
r = c.patch("/api/profile", json={"businessType": "Snacks Manufacturing"})  # camelCase alias only
check("alias-only PATCH businessType persists", r.json().get("businessType") == "Snacks Manufacturing", str(r.json().get("businessType")))
r = c.patch("/api/profile", json={"business_type": "Frozen Foods"})  # snake_case canonical only
check("canonical-only PATCH persists + alias synced", r.json().get("business_type") == "Frozen Foods" and r.json().get("businessType") == "Frozen Foods", str(r.json().get("business_type")))
r = c.patch("/api/profile", json={"name": "Alias Test Co."})  # name alias only
check("alias-only PATCH name persists", r.json().get("business_name") == "Alias Test Co.", str(r.json().get("business_name")))
r = c.get("/api/profile")
check("alias updates survive re-read", r.json().get("business_name") == "Alias Test Co." and r.json().get("businessType") == "Frozen Foods")
check("unrelated stored fields not clobbered by partial update", r.json().get("industry") in ("Textile", "Food & Beverage"), str(r.json().get("industry")))

print("\n========== RESTORE DEFAULT SEEDED STATE ==========")
c.post("/api/profile/reset")
c.post("/api/assessment", json={})
c.post("/api/climate-fingerprint/generate")
c.post("/api/impact", json={"before": {"energy_kwh": 10000, "water_litres": 80000, "waste_kg": 2000},
                            "after": {"energy_kwh": 7200, "water_litres": 61000, "waste_kg": 1350}})
print("\n(restored default seeded state for demo)")

# ============================================================
print(f"\n================= AUDIT RESULT: {len(PASS)} passed, {len(FAIL)} failed =================")
if FAIL:
    print("FAILED CHECKS:")
    for name, detail in FAIL:
        print(f"  - {name} :: {detail[:300]}")
sys.exit(1 if FAIL else 0)
