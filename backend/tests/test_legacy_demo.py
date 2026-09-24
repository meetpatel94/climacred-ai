"""
Regression tests for the fake "ABC Textile" data.

Root cause: builds up to commit a9db8ba auto-inserted a demo business into MongoDB
on the first GET /api/profile / GET /api/assessment (and seed.py wrote the same
values). Those documents survived in MongoDB and the current code served them as
real data: ABC Textile, Tirupur, 145 employees, 38,000 sq.ft, 38,500 kWh, 480,000 L,
3,600 kg, 1,950 L, 36.47 t CO2e and a 47.5/100 score.

The fixtures in tests/fixtures/ are real dumps produced by running that old code.
"""
import json
import pathlib

from bson import json_util
from fastapi.testclient import TestClient

from app.database import legacy_demo
from app.database.collections import COLLECTIONS
from app.database.mongodb import get_database
from app.main import app
from tests.conftest import TEST_ASSESSMENT, TEST_PROFILE, seed_real_business

client = TestClient(app)
FIXTURES = pathlib.Path(__file__).parent / "fixtures"
DEMO_MARKERS = ("ABC Textile", "Tirupur", "abctextiles", "38500", "480000", "47.5", "36.47")


def load_fixture(name: str) -> dict:
    db = get_database()
    data = json_util.loads((FIXTURES / name).read_text())
    for collection, docs in data.items():
        if docs:
            db[collection].insert_many(docs)
    return {k: len(v) for k, v in data.items()}


def counts() -> dict:
    db = get_database()
    return {key: db[COLLECTIONS[key]].count_documents({}) for key in (
        "business_profiles", "climate_assessments", "climate_fingerprints",
        "transformation_plans", "climate_reports", "impact_records",
    )}


def assert_everything_empty(c: TestClient) -> None:
    assert c.get("/api/profile").json() is None
    assert c.get("/api/assessment").json() is None
    assert c.get("/api/climate-fingerprint").json() is None
    assert c.get("/api/climate-fingerprint/history").json()["count"] == 0
    for domain in ("energy", "water", "waste", "emissions", "mobility"):
        assert c.get(f"/api/climate-fingerprint/analytics/{domain}").json()["available"] is False
    assert c.get("/api/transformation-plan").json()["count"] == 0
    assert c.get("/api/impact").json()["count"] == 0
    assert c.get("/api/reports/climate").json() is None
    assert c.get("/api/ai/dashboard-insights").json()["status"] == "no_data"
    for path in ("/api/profile", "/api/assessment", "/api/climate-fingerprint", "/api/transformation-plan",
                 "/api/impact", "/api/reports/climate", "/api/ai/dashboard-insights"):
        body = c.get(path).text
        for marker in DEMO_MARKERS:
            assert marker not in body, f"{path} still exposes {marker}"


def test_fixture_reproduces_the_reported_fake_values_without_the_purge():
    """Documents the bug: the current read path serves whatever legacy documents exist."""
    load_fixture("legacy_autoinsert_db.json")
    profile = client.get("/api/profile").json()
    assert profile["business_name"] == "ABC Textile Manufacturing Ltd."
    assert profile["employees"] == 145 and profile["facility_area_sqft"] == 38000
    assert client.get("/api/climate-fingerprint").json()["overallScore"] == 47.5
    emissions = client.get("/api/climate-fingerprint/analytics/emissions").json()
    assert emissions["emissions_breakdown_tonnes_co2e_per_month"]["total"] == 36.47


def test_startup_removes_legacy_auto_inserted_demo():
    load_fixture("legacy_autoinsert_db.json")
    with TestClient(app) as c:  # runs the startup event
        assert counts()["business_profiles"] == 0
        assert counts()["climate_assessments"] == 0
        assert counts()["climate_fingerprints"] == 0
        assert_everything_empty(c)


def test_startup_removes_legacy_seed_script_output():
    loaded = load_fixture("legacy_seed_db.json")
    assert loaded["transformation_plans"] == 1 and loaded["climate_reports"] == 1 and loaded["impact_records"] == 1
    with TestClient(app) as c:
        assert all(v == 0 for v in counts().values()), counts()
        assert_everything_empty(c)


def test_scan_is_read_only_and_cli_reports(capsys):
    load_fixture("legacy_seed_db.json")
    before = counts()
    report = legacy_demo.scan()
    assert report["found"] is True
    assert report["profiles"][0]["verdict"] == "demo"
    assert report["assessments"][0]["verdict"] == "demo"
    assert legacy_demo.purge(dry_run=True)["found"] is True
    assert counts() == before
    assert legacy_demo._main([]) == 0
    out = capsys.readouterr().out
    assert "Legacy demo scan" in out and "--apply" in out
    assert counts() == before


def test_real_user_data_is_never_touched():
    seed_real_business()
    client.post("/api/transformation-plan/generate")
    before = counts()
    summary = legacy_demo.purge()
    assert summary["found"] is False
    assert counts() == before
    assert client.get("/api/profile").json()["business_name"] == TEST_PROFILE["name"]


def test_real_textile_business_with_some_common_values_is_not_demo():
    """A genuine textile SME sharing generic values (industry, 26 days, 16 h) is kept."""
    profile = {**TEST_PROFILE, "name": "Test Textile Manufacturing", "industry": "Textile",
               "workingDaysPerMonth": 26, "operatingHoursPerDay": 16, "businessSize": "Medium"}
    assessment = json.loads(json.dumps(TEST_ASSESSMENT))
    assessment["waste"]["currentRecyclingPercent"] = 22  # one coincidental demo value
    assessment["mobility"]["deliveryVehiclesCount"] = 8
    seed_real_business(profile, assessment)
    assert legacy_demo.purge()["found"] is False
    assert client.get("/api/assessment").json()["waste"]["currentRecyclingPercent"] == 22


def test_user_edits_on_top_of_the_legacy_demo_are_preserved():
    """Old code merged user edits into the auto-inserted demo document. Keep the edits,
    remove only the demo leftovers."""
    load_fixture("legacy_autoinsert_db.json")
    db = get_database()
    db[COLLECTIONS["business_profiles"]].update_one({}, {"$set": {
        "business_name": "Test Textile Manufacturing", "name": "Test Textile Manufacturing", "employees": 60,
    }})
    db[COLLECTIONS["climate_assessments"]].update_one({}, {"$set": {"energy.monthlyElectricityKwh": 21000}})

    summary = legacy_demo.purge()
    assert summary["modified"] == {"business_profiles": 1, "climate_assessments": 1}

    profile = db[COLLECTIONS["business_profiles"]].find_one({})
    assert profile["business_name"] == "Test Textile Manufacturing" and profile["employees"] == 60
    for demo_field in ("location", "contact_email", "contactEmail", "phone", "facility_area_sqft", "production_volume"):
        assert demo_field not in profile, demo_field

    assessment = db[COLLECTIONS["climate_assessments"]].find_one({})
    assert assessment["energy"]["monthlyElectricityKwh"] == 21000
    assert "monthlyWaterLitres" not in assessment["water"]
    assert "textileMaterialWasteKgPerMonth" not in assessment["waste"]
    assert "monthlyFleetFuelLitres" not in assessment["mobility"]
    # the 47.5 snapshot was calculated from demo inputs -> removed, recalculated on demand
    assert db[COLLECTIONS["climate_fingerprints"]].count_documents({}) == 0
    fingerprint = client.get("/api/climate-fingerprint").json()
    assert fingerprint is None or fingerprint["overallScore"] != 47.5


def test_legacy_snapshots_are_removed_from_real_history():
    """A user who replaced the demo keeps only real snapshots (no demo-vs-real 'trends')."""
    load_fixture("legacy_autoinsert_db.json")
    db = get_database()
    db[COLLECTIONS["business_profiles"]].delete_many({})
    db[COLLECTIONS["climate_assessments"]].delete_many({})
    db[COLLECTIONS["climate_fingerprints"]].update_many({}, {"$set": {"superseded": True}})
    seed_real_business()
    assert db[COLLECTIONS["climate_fingerprints"]].count_documents({}) == 2
    legacy_demo.purge()
    history = client.get("/api/climate-fingerprint/history").json()
    assert history["count"] >= 1
    assert all(s["overall_score"] != 47.5 for s in history["snapshots"])
    assert all((s["dimension_metrics"].get("Energy") or {}).get("monthly_kwh") != 38500 for s in history["snapshots"])


def test_explicit_seed_fixtures_are_left_alone():
    load_fixture("legacy_autoinsert_db.json")
    db = get_database()
    for key in ("business_profiles", "climate_assessments", "climate_fingerprints"):
        db[COLLECTIONS[key]].update_many({}, {"$set": {"data_origin": "developer_seed_script"}})
    assert legacy_demo.purge()["found"] is False
    assert counts()["business_profiles"] == 1


def test_startup_never_seeds_an_empty_database():
    with TestClient(app) as c:
        assert all(v == 0 for v in counts().values())
        assert_everything_empty(c)
    assert all(v == 0 for v in counts().values())


def test_application_never_imports_or_runs_seeding_code():
    """seed.py is a developer script; no application module imports it, and the
    catalog-copy helper is never called by the API (only defined)."""
    app_dir = pathlib.Path(__file__).resolve().parents[1] / "app"
    for source in app_dir.rglob("*.py"):
        text = source.read_text()
        assert "import seed" not in text and "from seed" not in text, source
        assert "runpy" not in text, source
        calls = text.count("ensure_solutions_seeded(") - text.count("def ensure_solutions_seeded(")
        assert calls == 0, f"{source} calls ensure_solutions_seeded()"
