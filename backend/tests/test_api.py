"""
Phase 2 API tests - data authenticity edition.

The suite is split in two halves:

  TEST A - empty database: nothing that looks like a business, a metric, a chart
           dataset, a recommendation, a plan, an impact record or a report may
           appear anywhere in the API responses.
  TEST B - real data: a real (test) business is submitted through the API and
           every derived value must come from those submitted numbers.
"""
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import client, TEST_PROFILE, TEST_ASSESSMENT, seed_real_business

# Values that used to be hardcoded demo data and must never be fabricated again.
FORBIDDEN_FIXTURE_STRINGS = [
    "ABC Textile",
    "abctextiles.in",
    "Tirupur Industrial Cluster",
    "98450 12890",
]


# ---------------------------------------------------------------------------
# System
# ---------------------------------------------------------------------------
def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_root():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "ClimaCred AI API" in resp.json()["name"]


# ---------------------------------------------------------------------------
# TEST A - EMPTY DATABASE MUST BE REALLY EMPTY
# ---------------------------------------------------------------------------
def test_empty_database_returns_no_profile():
    resp = client.get("/api/profile")
    assert resp.status_code == 200
    assert resp.json() is None


def test_empty_database_returns_no_assessment():
    resp = client.get("/api/assessment")
    assert resp.status_code == 200
    assert resp.json() is None


def test_empty_database_returns_no_fingerprint():
    resp = client.get("/api/climate-fingerprint")
    assert resp.status_code == 200
    assert resp.json() is None


def test_empty_database_fingerprint_generate_explains_missing_data():
    resp = client.post("/api/climate-fingerprint/generate")
    assert resp.status_code == 400
    assert "profile" in resp.json()["detail"].lower()


def test_empty_database_analytics_are_unavailable_not_zero_filled():
    for domain in ("energy", "water", "waste", "emissions", "mobility", "data-quality"):
        resp = client.get(f"/api/climate-fingerprint/analytics/{domain}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["available"] is False
        assert body["message"].startswith("No ")
        assert "monthly_electricity_kwh" not in body


def test_empty_database_has_no_recommendations_or_plan():
    recs = client.get("/api/solutions/recommendations?top_n=5").json()
    assert recs["recommendations"] == []
    plan = client.get("/api/transformation-plan").json()
    assert plan["plan"] == []
    generated = client.post("/api/transformation-plan/generate").json()
    assert generated["plan"] == []


def test_empty_database_has_no_impact_metrics():
    body = client.get("/api/impact").json()
    assert body["records"] == []
    assert body["metrics"] == []
    assert client.get("/api/impact/metrics").json()["metrics"] == []


def test_empty_database_has_no_report():
    assert client.get("/api/reports/climate").json() is None
    resp = client.post("/api/reports/climate/generate")
    assert resp.status_code == 400
    assert "no business climate data" in resp.json()["detail"].lower()


def test_empty_database_has_no_history():
    body = client.get("/api/climate-fingerprint/history").json()
    assert body["snapshots"] == []
    assert body["count"] == 0


def test_empty_database_never_exposes_fake_business_values():
    """Scan every user-facing GET endpoint for fabricated demo data."""
    paths = [
        "/api/profile",
        "/api/assessment",
        "/api/climate-fingerprint",
        "/api/climate-fingerprint/history",
        "/api/climate-fingerprint/analytics/energy",
        "/api/climate-fingerprint/analytics/water",
        "/api/climate-fingerprint/analytics/waste",
        "/api/climate-fingerprint/analytics/emissions",
        "/api/climate-fingerprint/analytics/mobility",
        "/api/climate-fingerprint/analytics/data-quality",
        "/api/transformation-plan",
        "/api/impact",
        "/api/impact/metrics",
        "/api/reports/climate",
        "/api/ai/dashboard-insights",
        "/api/solutions/recommendations",
    ]
    for path in paths:
        resp = client.get(path)
        assert resp.status_code == 200, path
        body = resp.text
        for forbidden in FORBIDDEN_FIXTURE_STRINGS:
            assert forbidden not in body, f"{path} leaked demo data: {forbidden}"
        for value in ("38500", "480000", "3600", "41.2", "1950"):
            assert value not in body, f"{path} leaked demo metric {value}"


def test_empty_database_dashboard_insight_is_a_clean_empty_state():
    resp = client.get("/api/ai/dashboard-insights")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "no_data"
    assert body["has_data"] is False
    assert body["ai_available"] is False
    assert body["insight"] is None
    assert body["notice"] == "No business climate data yet."
    assert body["calculated"]["business_name"] is None
    assert body["calculated"]["climate_score"] is None


def test_solutions_catalog_is_product_content_not_user_data():
    """The intervention catalog is platform content and is still available."""
    resp = client.get("/api/solutions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["solutions"]) >= 10
    for sol in data["solutions"]:
        assert "id" in sol and "category" in sol
        assert "investmentMinInr" in sol and "potentialAnnualSavingsInr" in sol
    # Catalog problem statements must not quote one customer's measured values.
    assert "480,000 L/mo" not in resp.text
    assert "38,000 sq ft" not in resp.text


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
def test_profile_is_created_from_submitted_data_only():
    resp = client.post("/api/profile", json=TEST_PROFILE)
    assert resp.status_code == 200
    body = resp.json()
    assert body["business_name"] == TEST_PROFILE["name"]
    assert body["employees"] == TEST_PROFILE["employees"]
    # Nothing that was not submitted may be invented
    assert body.get("phone") == TEST_PROFILE["phone"]
    assert body.get("location") == TEST_PROFILE["location"]


def test_profile_created_with_minimum_fields_keeps_missing_fields_missing():
    resp = client.post("/api/profile", json={"name": "Bare Minimum Works"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["business_name"] == "Bare Minimum Works"
    assert body.get("employees") is None
    assert body.get("facility_area_sqft") is None
    assert "ABC Textile" not in resp.text


def test_profile_patch_valid():
    client.post("/api/profile", json=TEST_PROFILE)
    resp = client.patch("/api/profile", json={"employees": 150})
    assert resp.status_code == 200
    assert resp.json()["employees"] == 150


def test_profile_patch_invalid_negative():
    assert client.patch("/api/profile", json={"employees": -5}).status_code == 400


def test_profile_patch_invalid_working_days():
    assert client.patch("/api/profile", json={"working_days": 40}).status_code == 400


def test_profile_reset_clears_data_without_fabricating_a_default():
    client.post("/api/profile", json=TEST_PROFILE)
    resp = client.post("/api/profile/reset")
    assert resp.status_code == 200
    assert resp.json() is None
    assert client.get("/api/profile").json() is None


# ---------------------------------------------------------------------------
# Assessment
# ---------------------------------------------------------------------------
def test_assessment_stores_only_submitted_values():
    payload = {"energy": {"monthlyElectricityKwh": 9000, "monthlyElectricityBillInr": 81000}}
    resp = client.post("/api/assessment", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["energy"]["monthlyElectricityKwh"] == 9000
    # Sections the user did not fill in stay empty
    assert body["water"] == {}
    assert "ABC Textile" not in resp.text


def test_assessment_validation_negative():
    assert client.post("/api/assessment", json={"energy": {"monthlyElectricityKwh": -100}}).status_code == 400


def test_assessment_validation_recycling_percent():
    assert client.post("/api/assessment", json={"waste": {"currentRecyclingPercent": 150}}).status_code == 400


def test_assessment_ev_count_exceeds_vehicle():
    resp = client.post("/api/assessment", json={"mobility": {"deliveryVehiclesCount": 2, "electric_vehicle_count": 5}})
    assert resp.status_code == 400


def test_assessment_update_invalidates_fingerprint(real_business):
    # Better energy profile must raise the Energy score of the recalculation
    resp = client.post("/api/assessment", json={
        "energy": {
            "monthlyElectricityKwh": 12000,
            "monthlyElectricityBillInr": 108000,
            "dieselGeneratorHoursPerMonth": 6,
            "generatorFuelLitresPerMonth": 90,
            "existingSolarCapacityKw": 30,
            "energyEfficientEquipmentPercent": 85,
        }
    })
    assert resp.status_code == 200
    fp = client.get("/api/climate-fingerprint").json()
    assert fp is not None
    energy_dim = next(d for d in fp["dimensions"] if d["dimension"] == "Energy")
    assert energy_dim["score"] > 60
    # The stored calculated value must equal the submitted input
    assert fp["dimensions"][0]["metrics_used"]["monthly_kwh"] == 12000


def test_incomplete_assessment_still_produces_calculated_output():
    client.post("/api/profile", json=TEST_PROFILE)
    resp = client.post("/api/assessment", json={"energy": {"monthlyElectricityKwh": 10000}})
    assert resp.status_code == 200
    fp = client.post("/api/climate-fingerprint/generate")
    assert fp.status_code == 200
    assert 0 <= fp.json()["overallScore"] <= 100


# ---------------------------------------------------------------------------
# Fingerprint, analytics, history (TEST B - real data)
# ---------------------------------------------------------------------------
def test_fingerprint_generate_uses_real_data(real_business):
    fp = client.post("/api/climate-fingerprint/generate").json()
    assert 0 <= fp["overallScore"] <= 100
    assert len(fp["dimensions"]) == 6
    energy = next(d for d in fp["dimensions"] if d["dimension"] == "Energy")
    assert energy["metrics_used"]["monthly_kwh"] == TEST_ASSESSMENT["energy"]["monthlyElectricityKwh"]
    for dim in fp["dimensions"]:
        assert dim["impactLevel"] in ["Low", "Moderate", "High", "Very High"]
        assert "confidence" in dim


def test_energy_calculations(real_business):
    data = client.get("/api/climate-fingerprint/analytics/energy").json()
    assert data["available"] is True
    assert data["monthly_electricity_kwh"] == TEST_ASSESSMENT["energy"]["monthlyElectricityKwh"]
    assert data["annual_electricity_kwh"] == data["monthly_electricity_kwh"] * 12
    assert "factor" in data["emission_factor_used"]


def test_water_calculations(real_business):
    data = client.get("/api/climate-fingerprint/analytics/water").json()
    assert data["monthly_water_litres"] == TEST_ASSESSMENT["water"]["monthlyWaterLitres"]
    assert data["annual_water_litres"] == data["monthly_water_litres"] * 12
    assert data["assumptions"]


def test_waste_calculations(real_business):
    data = client.get("/api/climate-fingerprint/analytics/waste").json()
    expected_total = sum(
        TEST_ASSESSMENT["waste"][key] for key in (
            "organicWasteKgPerMonth", "plasticWasteKgPerMonth", "paperWasteKgPerMonth",
            "industrialWasteKgPerMonth", "textileMaterialWasteKgPerMonth",
        )
    )
    assert data["total_waste_kg_per_month"] == expected_total
    assert 0 <= data["recycling_rate_percent"] <= 100


def test_emissions_calculations(real_business):
    data = client.get("/api/climate-fingerprint/analytics/emissions").json()
    assert "total" in data["emissions_breakdown_tonnes_co2e_per_month"]
    assert "factors_used" in data


def test_mobility_calculations(real_business):
    data = client.get("/api/climate-fingerprint/analytics/mobility").json()
    assert data["monthly_fuel_litres"] == TEST_ASSESSMENT["mobility"]["monthlyFleetFuelLitres"]
    assert data["delivery_vehicles_count"] == TEST_ASSESSMENT["mobility"]["deliveryVehiclesCount"]


def test_data_quality(real_business):
    data = client.get("/api/climate-fingerprint/analytics/data-quality").json()
    assert data["level"] in ["High", "Medium", "Low"]
    assert 0 <= data["completeness_percent"] <= 100


def test_zero_consumption_edge(real_business):
    resp = client.post("/api/assessment", json={
        "energy": {
            "monthlyElectricityKwh": 0, "monthlyElectricityBillInr": 0,
            "dieselGeneratorHoursPerMonth": 0, "generatorFuelLitresPerMonth": 0,
            "existingSolarCapacityKw": 0, "energyEfficientEquipmentPercent": 0,
        },
        "water": {
            "monthlyWaterLitres": 0, "waterSource": "Municipal", "waterRecyclingAvailable": False,
            "rainwaterHarvesting": False, "leakageFrequency": "Never", "wastewaterTreatment": "None",
        },
    })
    assert resp.status_code == 200
    energy = client.get("/api/climate-fingerprint/analytics/energy").json()
    # A real submitted zero stays zero (it is not "missing")
    assert energy["monthly_electricity_kwh"] == 0
    assert client.post("/api/climate-fingerprint/generate").status_code == 200


def test_100_percent_recycling(real_business):
    resp = client.post("/api/assessment", json={"waste": {
        "organicWasteKgPerMonth": 100, "plasticWasteKgPerMonth": 100, "paperWasteKgPerMonth": 100,
        "industrialWasteKgPerMonth": 100, "textileMaterialWasteKgPerMonth": 100,
        "currentRecyclingPercent": 100, "wasteSegregationPracticed": True,
    }})
    assert resp.status_code == 200
    fp = client.post("/api/climate-fingerprint/generate").json()
    waste_dim = next(d for d in fp["dimensions"] if d["dimension"] == "Waste")
    assert waste_dim["score"] >= 70


def test_history_grows_with_each_stored_fingerprint(real_business):
    client.post("/api/climate-fingerprint/generate")
    body = client.get("/api/climate-fingerprint/history").json()
    assert body["count"] >= 2
    latest = body["snapshots"][-1]
    assert latest["dimension_metrics"]["Energy"]["monthly_kwh"] == TEST_ASSESSMENT["energy"]["monthlyElectricityKwh"]
    assert latest["overall_score"] is not None
    # Oldest first for charting
    assert body["snapshots"][0]["created_at"] <= latest["created_at"]


def test_history_preserves_earlier_snapshots_when_data_changes(real_business):
    """Saving new data must add a snapshot, not delete the earlier real records."""
    before = client.get("/api/climate-fingerprint/history").json()["count"]
    client.patch("/api/assessment", json={"energy": {"monthlyElectricityKwh": 41000}})

    # The current fingerprint is recalculated from the new data...
    fp = client.get("/api/climate-fingerprint").json()
    assert fp["overallScore"] is not None

    after = client.get("/api/climate-fingerprint/history").json()
    assert after["count"] == before + 1
    latest = after["snapshots"][-1]
    assert latest["dimension_metrics"]["Energy"]["monthly_kwh"] == 41000
    # ...while the earlier snapshot keeps the previously stored value
    assert after["snapshots"][0]["dimension_metrics"]["Energy"]["monthly_kwh"] == TEST_ASSESSMENT["energy"]["monthlyElectricityKwh"]


# ---------------------------------------------------------------------------
# Recommendations, scenarios, plan
# ---------------------------------------------------------------------------
def test_recommendations_personalized(real_business):
    data = client.get("/api/solutions/recommendations?top_n=5").json()
    assert len(data["recommendations"]) == 5
    for rec in data["recommendations"]:
        assert rec["solution"] and rec["reason"] and rec["priority"]
        assert rec["estimated_investment"] and rec["assumptions"]


def test_recommendations_match_the_weakest_dimension(real_business):
    fp = client.get("/api/climate-fingerprint").json()
    weakest = min(fp["dimensions"], key=lambda d: d["score"])["dimension"]
    recs = client.get("/api/solutions/recommendations?top_n=5").json()["recommendations"]
    categories = [r["solution"]["category"] for r in recs]
    assert weakest in categories or "Materials" in categories


def test_scenario_simulation_single(real_business):
    data = client.post("/api/scenarios/simulate", json={"selected_solution_ids": ["sol-solar"]}).json()
    assert "totalInvestmentInr" in data and "totalAnnualSavingsInr" in data
    assert "energy_change" in data and "assumptions" in data


def test_scenario_simulation_multiple_no_double_counting(real_business):
    data = client.post("/api/scenarios/simulate", json={
        "selected_solution_ids": ["sol-solar", "sol-machinery-vfd", "sol-water-ro", "sol-leak-sensors", "sol-waste-recovery"],
        "adoption_scale_percent": 100,
    }).json()
    assert data["energy_change"]["energyReductionPercent"] <= 55
    assert data["water_change"]["waterReductionPercent"] <= 75
    assert data["waste_change"]["wasteReductionPercent"] <= 68


def test_scenario_invalid_empty(real_business):
    assert client.post("/api/scenarios/simulate", json={"selected_solution_ids": []}).status_code == 400


def test_transformation_plan_generate(real_business):
    plan = client.post("/api/transformation-plan/generate").json()["plan"]
    assert len(plan) >= 5
    phases = {p["phase"] for p in plan}
    assert "Phase 1" in phases and "Phase 4" in phases
    for item in plan:
        assert item["priority"] in ["High", "Medium", "Low"]


def test_transformation_update_status(real_business):
    client.post("/api/transformation-plan/generate")
    plan = client.get("/api/transformation-plan").json()["plan"]
    first_id = plan[0]["id"]
    resp = client.patch(f"/api/transformation-plan/{first_id}", json={"status": "Completed"})
    assert resp.status_code == 200
    updated = next(i for i in resp.json()["plan"] if i["id"] == first_id)
    assert updated["status"] == "Completed"


# ---------------------------------------------------------------------------
# Impact verification
# ---------------------------------------------------------------------------
def test_impact_create_and_get():
    payload = {
        "before": {"energy_kwh": 10000, "water_litres": 80000, "waste_kg": 2000},
        "after": {"energy_kwh": 7200, "water_litres": 61000, "waste_kg": 1350},
    }
    data = client.post("/api/impact", json=payload).json()
    assert len(data["calculated_metrics"]) == 3
    for metric in data["calculated_metrics"]:
        assert "absolute_change" in metric and "percentage_change" in metric
        assert "verified carbon reduction" not in metric["estimated_impact"].lower()

    body = client.get("/api/impact").json()
    assert len(body["records"]) == 1
    metrics = body["metrics"]
    assert metrics[0]["beforeValue"] == 10000
    assert metrics[0]["afterValue"] == 7200
    assert round(metrics[0]["differencePercent"], 1) == -28.0


def test_impact_missing_data():
    assert client.post("/api/impact", json={"before": {"energy_kwh": 10000}}).status_code == 400


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
def test_report_generate(real_business):
    resp = client.post("/api/reports/climate/generate")
    assert resp.status_code == 200
    data = resp.json()
    for key in ("report_id", "assumptions", "methodology", "data_quality"):
        assert key in data
    assert "business_profile" in data or "businessProfile" in data
    assert "energy_analysis" in data or "energyAnalysis" in data
    assert data.get("generated_at") or data.get("generatedAt")
    # Report content must quote the submitted business, never a demo one
    assert "ABC Textile" not in resp.text


def test_anomaly_insufficient_data():
    resp = client.post("/api/climate-fingerprint/anomaly-detection", json={
        "historical_data": [{"month": "Jan", "consumptionKwh": 1000}], "metric_key": "consumptionKwh",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "insufficient_data"
    assert "Insufficient historical data" in resp.json()["message"]


def test_forecast_insufficient_data():
    resp = client.post("/api/climate-fingerprint/forecast", json={
        "historical_data": [{"month": "Jan", "consumptionKwh": 1000}], "metric_key": "consumptionKwh",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "insufficient_data"


def test_changed_data_changes_outputs():
    """TEST B: substantially different business data must drive different results."""
    seed_real_business()
    first_fp = client.get("/api/climate-fingerprint").json()
    first_score = first_fp["overallScore"]
    first_energy = client.get("/api/climate-fingerprint/analytics/energy").json()["monthly_electricity_kwh"]

    changed = json.loads(json.dumps(TEST_ASSESSMENT))
    changed["energy"]["monthlyElectricityKwh"] = 41000
    changed["energy"]["existingSolarCapacityKw"] = 60
    changed["energy"]["energyEfficientEquipmentPercent"] = 90
    changed["water"]["monthlyWaterLitres"] = 40000
    changed["water"]["waterRecyclingAvailable"] = True
    changed["greenPractices"]["solarPanels"] = True
    changed["greenPractices"]["waterRecycling"] = True
    seed_real_business(profile=TEST_PROFILE, assessment=changed)

    second_energy = client.get("/api/climate-fingerprint/analytics/energy").json()["monthly_electricity_kwh"]
    second_fp = client.get("/api/climate-fingerprint").json()
    assert second_energy == 41000 and first_energy == 21500
    assert second_fp["overallScore"] != first_score
    water_dim = next(d for d in second_fp["dimensions"] if d["dimension"] == "Water")
    assert water_dim["metrics_used"]["monthly_litres"] == 40000
