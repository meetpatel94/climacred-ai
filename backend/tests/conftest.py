"""
Shared test fixtures for ClimaCred AI.

The application no longer auto-seeds a demo business, so every test that needs
stored data has to create it explicitly through the real API - which is also what
makes the "empty database" tests meaningful.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.mongodb import get_database
from app.database.collections import COLLECTIONS
from app.config import settings

client = TestClient(app)

#: A genuine (test) business used by tests that need real stored data.
TEST_PROFILE = {
    "name": "Shakti Precision Components Pvt. Ltd.",
    "industry": "Auto Components",
    "businessType": "Machining & Surface Treatment",
    "location": "Pune, Maharashtra, India",
    "employees": 64,
    "workingDaysPerMonth": 25,
    "productionVolume": "18,000 parts / month",
    "operatingHoursPerDay": 14,
    "businessSize": "Small",
    "facilityAreaSqFt": 14500,
    "contactEmail": "plant@shaktiprecision.in",
    "phone": "+91 98220 00000",
}

TEST_ASSESSMENT = {
    "energy": {
        "monthlyElectricityKwh": 21500,
        "monthlyElectricityBillInr": 193500,
        "dieselGeneratorHoursPerMonth": 22,
        "generatorFuelLitresPerMonth": 480,
        "existingSolarCapacityKw": 0,
        "energyEfficientEquipmentPercent": 35,
    },
    "water": {
        "monthlyWaterLitres": 260000,
        "waterSource": "Groundwater / Borewell",
        "waterRecyclingAvailable": False,
        "rainwaterHarvesting": False,
        "leakageFrequency": "Monthly",
        "wastewaterTreatment": "Primary / Settling",
    },
    "waste": {
        "organicWasteKgPerMonth": 120,
        "plasticWasteKgPerMonth": 260,
        "paperWasteKgPerMonth": 140,
        "industrialWasteKgPerMonth": 900,
        "textileMaterialWasteKgPerMonth": 0,
        "currentRecyclingPercent": 30,
        "wasteSegregationPracticed": True,
    },
    "emissions": {
        "primaryFuel": "Electricity Grid",
        "monthlyDieselLitres": 620,
        "monthlyPetrolLitres": 90,
        "monthlyNaturalGasKg": 0,
        "mainEmissionSources": ["Grid Electricity (Thermal Base)", "Backup Genset"],
        "airPollutionControlSystem": "Basic Scrubber",
    },
    "mobility": {
        "deliveryVehiclesCount": 4,
        "vehicleFuelType": "Diesel",
        "monthlyFleetFuelLitres": 780,
        "employeeCommuteMode": "Two-Wheelers",
        "evAdoptedPercent": 0,
    },
    "greenPractices": {
        "ledLighting": True,
        "solarPanels": False,
        "rainwaterHarvesting": False,
        "waterRecycling": False,
        "wasteSegregation": True,
        "energyEfficientMachinery": False,
        "evAdoption": False,
        "sustainableMaterials": False,
    },
}


def clear_all_data() -> None:
    """Wipe every stored document so each test starts from a genuinely empty DB."""
    db = get_database()
    for name in COLLECTIONS.values():
        db[name].delete_many({})


def seed_real_business(profile=None, assessment=None) -> None:
    """Store real (test) business data through the public API."""
    resp = client.post("/api/profile", json=profile or TEST_PROFILE)
    assert resp.status_code == 200, resp.text
    resp = client.post("/api/assessment", json=assessment or TEST_ASSESSMENT)
    assert resp.status_code == 200, resp.text
    resp = client.post("/api/climate-fingerprint/generate")
    assert resp.status_code == 200, resp.text


@pytest.fixture(autouse=True)
def empty_database(monkeypatch):
    """Every test runs against a truly empty database (no auto-seeded demo data)."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    clear_all_data()
    yield
    clear_all_data()


@pytest.fixture
def real_business():
    """Stored real test business (profile + assessment + fingerprint)."""
    seed_real_business()
    return {"profile": TEST_PROFILE, "assessment": TEST_ASSESSMENT}
