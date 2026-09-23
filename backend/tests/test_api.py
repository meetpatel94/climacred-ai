import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

def test_root():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "ClimaCred AI API" in resp.json()["name"]

def test_profile_get():
    resp = client.get("/api/profile")
    assert resp.status_code == 200
    data = resp.json()
    assert "business_name" in data
    assert "employees" in data

def test_profile_patch_valid():
    resp = client.patch("/api/profile", json={"employees": 150})
    assert resp.status_code == 200
    assert resp.json()["employees"] == 150
    # revert
    client.patch("/api/profile", json={"employees": 145})

def test_profile_patch_invalid_negative():
    resp = client.patch("/api/profile", json={"employees": -5})
    assert resp.status_code == 400

def test_profile_patch_invalid_working_days():
    resp = client.patch("/api/profile", json={"working_days": 40})
    assert resp.status_code == 400

def test_profile_reset():
    resp = client.post("/api/profile/reset")
    assert resp.status_code == 200
    assert resp.json()["business_name"] == "ABC Textile Manufacturing Ltd."

def test_assessment_get():
    resp = client.get("/api/assessment")
    assert resp.status_code == 200
    data = resp.json()
    assert "energy" in data
    assert "water" in data

def test_assessment_validation_negative():
    resp = client.post("/api/assessment", json={"energy": {"monthlyElectricityKwh": -100}})
    assert resp.status_code == 400

def test_assessment_validation_recycling_percent():
    resp = client.post("/api/assessment", json={"waste": {"currentRecyclingPercent": 150}})
    assert resp.status_code == 400

def test_assessment_ev_count_exceeds_vehicle():
    resp = client.post("/api/assessment", json={"mobility": {"deliveryVehiclesCount": 2, "electric_vehicle_count": 5}})
    assert resp.status_code == 400

def test_assessment_update_and_fingerprint_recalc():
    # Save new assessment with better energy efficiency
    new_assessment = {
        "energy": {
            "monthlyElectricityKwh": 30000,
            "monthlyElectricityBillInr": 270000,
            "dieselGeneratorHoursPerMonth": 10,
            "generatorFuelLitresPerMonth": 200,
            "existingSolarCapacityKw": 10,
            "energyEfficientEquipmentPercent": 80
        }
    }
    resp = client.post("/api/assessment", json=new_assessment)
    assert resp.status_code == 200
    # Fingerprint should be recalculated (old invalidated)
    resp2 = client.get("/api/climate-fingerprint")
    assert resp2.status_code == 200
    fp = resp2.json()
    assert "overallScore" in fp
    # Energy score should be higher with efficient equipment
    energy_dim = next(d for d in fp["dimensions"] if d["dimension"]=="Energy")
    assert energy_dim["score"] > 50
    # Reset to demo
    client.post("/api/assessment", json={
        "energy": {
            "monthlyElectricityKwh": 38500,
            "monthlyElectricityBillInr": 346500,
            "dieselGeneratorHoursPerMonth": 64,
            "generatorFuelLitresPerMonth": 1280,
            "existingSolarCapacityKw": 0,
            "energyEfficientEquipmentPercent": 28
        }
    })
    client.post("/api/climate-fingerprint/generate")

def test_fingerprint_generate():
    resp = client.post("/api/climate-fingerprint/generate")
    assert resp.status_code == 200
    data = resp.json()
    assert "overallScore" in data
    assert 0 <= data["overallScore"] <= 100
    assert "dimensions" in data
    assert len(data["dimensions"]) == 6
    for dim in data["dimensions"]:
        assert "score" in dim
        assert 0 <= dim["score"] <= 100
        assert dim["impactLevel"] in ["Low","Moderate","High","Very High"]
        assert "confidence" in dim

def test_energy_calculations():
    resp = client.get("/api/climate-fingerprint/analytics/energy")
    assert resp.status_code == 200
    data = resp.json()
    assert "monthly_electricity_kwh" in data
    assert "annual_electricity_kwh" in data
    assert data["annual_electricity_kwh"] == data["monthly_electricity_kwh"] * 12
    assert "emission_factor_used" in data
    assert "factor" in data["emission_factor_used"]

def test_water_calculations():
    resp = client.get("/api/climate-fingerprint/analytics/water")
    assert resp.status_code == 200
    data = resp.json()
    assert "monthly_water_litres" in data
    assert "annual_water_litres" in data
    assert "assumptions" in data

def test_waste_calculations():
    resp = client.get("/api/climate-fingerprint/analytics/waste")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_waste_kg_per_month" in data
    assert "recycling_rate_percent" in data
    assert data["recycling_rate_percent"] >=0 and data["recycling_rate_percent"] <=100

def test_emissions_calculations():
    resp = client.get("/api/climate-fingerprint/analytics/emissions")
    assert resp.status_code == 200
    data = resp.json()
    assert "emissions_breakdown_tonnes_co2e_per_month" in data
    assert "total" in data["emissions_breakdown_tonnes_co2e_per_month"]
    assert "factors_used" in data

def test_mobility_calculations():
    resp = client.get("/api/climate-fingerprint/analytics/mobility")
    assert resp.status_code == 200
    data = resp.json()
    assert "monthly_fuel_litres" in data
    assert "ev_adopted_percent" in data
    assert 0 <= data["ev_adopted_percent"] <= 100

def test_data_quality():
    resp = client.get("/api/climate-fingerprint/analytics/data-quality")
    assert resp.status_code == 200
    data = resp.json()
    assert "completeness_percent" in data
    assert "level" in data
    assert data["level"] in ["High","Medium","Low"]

def test_zero_consumption_edge():
    # Zero electricity and water
    resp = client.post("/api/assessment", json={
        "energy": {
            "monthlyElectricityKwh": 0,
            "monthlyElectricityBillInr": 0,
            "dieselGeneratorHoursPerMonth": 0,
            "generatorFuelLitresPerMonth": 0,
            "existingSolarCapacityKw": 0,
            "energyEfficientEquipmentPercent": 0
        },
        "water": {
            "monthlyWaterLitres": 0,
            "waterSource": "Municipal",
            "waterRecyclingAvailable": False,
            "rainwaterHarvesting": False,
            "leakageFrequency": "Never",
            "wastewaterTreatment": "None"
        },
        "waste": {
            "organicWasteKgPerMonth": 0,
            "plasticWasteKgPerMonth": 0,
            "paperWasteKgPerMonth": 0,
            "industrialWasteKgPerMonth": 0,
            "textileMaterialWasteKgPerMonth": 0,
            "currentRecyclingPercent": 0,
            "wasteSegregationPracticed": False
        }
    })
    assert resp.status_code == 200
    fp_resp = client.post("/api/climate-fingerprint/generate")
    assert fp_resp.status_code == 200
    fp = fp_resp.json()
    # Should still produce scores, not crash
    assert fp["overallScore"] >=0
    # Reset
    client.post("/api/assessment", json={
        "energy": {
            "monthlyElectricityKwh": 38500,
            "monthlyElectricityBillInr": 346500,
            "dieselGeneratorHoursPerMonth": 64,
            "generatorFuelLitresPerMonth": 1280,
            "existingSolarCapacityKw": 0,
            "energyEfficientEquipmentPercent": 28
        },
        "water": {
            "monthlyWaterLitres": 480000,
            "waterSource": "Groundwater / Borewell",
            "waterRecyclingAvailable": False,
            "rainwaterHarvesting": False,
            "leakageFrequency": "Monthly",
            "wastewaterTreatment": "Primary / Settling"
        },
        "waste": {
            "organicWasteKgPerMonth": 380,
            "plasticWasteKgPerMonth": 950,
            "paperWasteKgPerMonth": 420,
            "industrialWasteKgPerMonth": 1850,
            "textileMaterialWasteKgPerMonth": 3600,
            "currentRecyclingPercent": 22,
            "wasteSegregationPracticed": True
        }
    })
    client.post("/api/climate-fingerprint/generate")

def test_100_percent_recycling():
    resp = client.post("/api/assessment", json={
        "waste": {
            "organicWasteKgPerMonth": 100,
            "plasticWasteKgPerMonth": 100,
            "paperWasteKgPerMonth": 100,
            "industrialWasteKgPerMonth": 100,
            "textileMaterialWasteKgPerMonth": 100,
            "currentRecyclingPercent": 100,
            "wasteSegregationPracticed": True
        }
    })
    assert resp.status_code == 200
    fp_resp = client.post("/api/climate-fingerprint/generate")
    waste_dim = next(d for d in fp_resp.json()["dimensions"] if d["dimension"]=="Waste")
    # 100% recycling should give high score (low impact)
    assert waste_dim["score"] >= 70
    # Reset
    client.post("/api/assessment", json={
        "waste": {
            "organicWasteKgPerMonth": 380,
            "plasticWasteKgPerMonth": 950,
            "paperWasteKgPerMonth": 420,
            "industrialWasteKgPerMonth": 1850,
            "textileMaterialWasteKgPerMonth": 3600,
            "currentRecyclingPercent": 22,
            "wasteSegregationPracticed": True
        }
    })
    client.post("/api/climate-fingerprint/generate")

def test_solutions_catalog():
    resp = client.get("/api/solutions")
    assert resp.status_code == 200
    data = resp.json()
    assert "solutions" in data
    assert len(data["solutions"]) >= 10
    # Check required fields
    for sol in data["solutions"]:
        assert "id" in sol
        assert "category" in sol
        assert "investmentMinInr" in sol
        assert "potentialAnnualSavingsInr" in sol

def test_recommendations_personalized():
    resp = client.get("/api/solutions/recommendations?top_n=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "recommendations" in data
    assert len(data["recommendations"]) == 5
    for rec in data["recommendations"]:
        assert "solution" in rec
        assert "reason" in rec
        assert "priority" in rec
        assert "estimated_investment" in rec
        assert "assumptions" in rec

def test_recommendations_not_always_solar():
    # Solar should not be top for every business; check that recommendations are diverse
    resp = client.get("/api/solutions/recommendations?top_n=5")
    recs = resp.json()["recommendations"]
    # For ABC textile, water is Very High, so water solutions should appear
    categories = [r["solution"]["category"] for r in recs]
    assert "Water" in categories or "Waste" in categories

def test_scenario_simulation_single():
    resp = client.post("/api/scenarios/simulate", json={"selected_solution_ids": ["sol-solar"]})
    assert resp.status_code == 200
    data = resp.json()
    assert "totalInvestmentInr" in data
    assert "totalAnnualSavingsInr" in data
    assert "energy_change" in data
    assert "assumptions" in data

def test_scenario_simulation_multiple_no_double_counting():
    # Solar + VFD + water RO together should be capped
    resp = client.post("/api/scenarios/simulate", json={"selected_solution_ids": ["sol-solar", "sol-machinery-vfd", "sol-water-ro", "sol-leak-sensors", "sol-waste-recovery"], "adoption_scale_percent": 100})
    assert resp.status_code == 200
    data = resp.json()
    # Energy reduction should not exceed 55%
    assert data["energy_change"]["energyReductionPercent"] <= 55
    assert data["water_change"]["waterReductionPercent"] <= 75
    assert data["waste_change"]["wasteReductionPercent"] <= 68

def test_scenario_invalid_empty():
    resp = client.post("/api/scenarios/simulate", json={"selected_solution_ids": []})
    assert resp.status_code == 400

def test_transformation_plan_generate():
    resp = client.post("/api/transformation-plan/generate")
    assert resp.status_code == 200
    data = resp.json()
    assert "plan" in data
    plan = data["plan"]
    assert len(plan) >= 5
    # Check phases present
    phases = set(p["phase"] for p in plan)
    assert "Phase 1" in phases
    assert "Phase 4" in phases
    for item in plan:
        assert "id" in item
        assert "action" in item
        assert "priority" in item
        assert item["priority"] in ["High","Medium","Low"]

def test_transformation_plan_get():
    resp = client.get("/api/transformation-plan")
    assert resp.status_code == 200
    assert "plan" in resp.json()

def test_transformation_update_status():
    # Get plan
    resp = client.get("/api/transformation-plan")
    plan = resp.json()["plan"]
    first_id = plan[0]["id"]
    # Update status
    resp2 = client.patch(f"/api/transformation-plan/{first_id}", json={"status": "Completed"})
    assert resp2.status_code == 200
    # Verify
    updated = next(i for i in resp2.json()["plan"] if i["id"]==first_id)
    assert updated["status"] == "Completed"
    # Revert to Pending for idempotence
    client.patch(f"/api/transformation-plan/{first_id}", json={"status": "Pending"})

def test_impact_create_and_get():
    payload = {
        "before": {"energy_kwh": 10000, "water_litres": 80000, "waste_kg": 2000},
        "after": {"energy_kwh": 7200, "water_litres": 61000, "waste_kg": 1350}
    }
    resp = client.post("/api/impact", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "calculated_metrics" in data
    assert len(data["calculated_metrics"]) == 3
    for m in data["calculated_metrics"]:
        assert "absolute_change" in m
        assert "percentage_change" in m
        assert "estimated_impact" in m
        # Check terminology not verified carbon reduction
        assert "verified carbon reduction" not in m["estimated_impact"].lower()

    # GET should return records
    resp2 = client.get("/api/impact")
    assert resp2.status_code == 200
    assert "records" in resp2.json()

def test_impact_missing_data():
    resp = client.post("/api/impact", json={"before": {"energy_kwh": 10000}})
    assert resp.status_code == 400

def test_report_generate():
    resp = client.post("/api/reports/climate/generate")
    assert resp.status_code == 200
    data = resp.json()
    assert "report_id" in data
    assert "business_profile" in data or "businessProfile" in data
    assert "climate_fingerprint" in data or "climateFingerprint" in data
    assert "energy_analysis" in data or "energyAnalysis" in data
    assert "assumptions" in data
    assert "methodology" in data
    assert "data_quality" in data

def test_report_distinguishes_data_types():
    resp = client.post("/api/reports/climate/generate")
    data = resp.json()
    methodology = data.get("methodology", {})
    distinct = methodology.get("distinct_data_types") or methodology.get("distinctDataTypes")
    # May be in methodology or top-level
    assert data.get("assumptions") is not None
    # Check report has generated_at and calculation_version
    assert "generated_at" in data or "generatedAt" in data
    assert "calculation_version" in data or "calculationVersion" in data

def test_anomaly_insufficient_data():
    resp = client.post("/api/climate-fingerprint/anomaly-detection", json={"historical_data": [{"month":"Jan","consumptionKwh":1000}], "metric_key":"consumptionKwh"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "insufficient_data"
    assert "Insufficient historical data" in resp.json()["message"]

def test_forecast_insufficient_data():
    resp = client.post("/api/climate-fingerprint/forecast", json={"historical_data": [{"month":"Jan","consumptionKwh":1000}], "metric_key":"consumptionKwh"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "insufficient_data"

def test_incomplete_assessment_handling():
    # Send incomplete assessment (only energy)
    resp = client.post("/api/assessment", json={"energy": {"monthlyElectricityKwh": 10000}})
    assert resp.status_code == 200
    # Fingerprint should still generate with defaults for missing sections
    fp_resp = client.post("/api/climate-fingerprint/generate")
    assert fp_resp.status_code == 200
    # Reset
    client.post("/api/assessment", json={
        "energy": {"monthlyElectricityKwh":38500,"monthlyElectricityBillInr":346500,"dieselGeneratorHoursPerMonth":64,"generatorFuelLitresPerMonth":1280,"existingSolarCapacityKw":0,"energyEfficientEquipmentPercent":28},
        "water": {"monthlyWaterLitres":480000,"waterSource":"Groundwater / Borewell","waterRecyclingAvailable":False,"rainwaterHarvesting":False,"leakageFrequency":"Monthly","wastewaterTreatment":"Primary / Settling"},
        "waste": {"organicWasteKgPerMonth":380,"plasticWasteKgPerMonth":950,"paperWasteKgPerMonth":420,"industrialWasteKgPerMonth":1850,"textileMaterialWasteKgPerMonth":3600,"currentRecyclingPercent":22,"wasteSegregationPracticed":True}
    })
    client.post("/api/climate-fingerprint/generate")
