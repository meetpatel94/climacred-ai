"""
DEVELOPER / TESTING UTILITY - NOT PART OF NORMAL APPLICATION STARTUP.

Seeds an illustrative demo business ("ABC Textile Manufacturing") for local
testing of the UI and engines. Nothing in the application imports or runs this
file: FastAPI startup, MongoDB connection, the frontend and the dashboard never
seed data. It only runs when a developer executes it explicitly:

    python seed.py --demo            # refuses if real user data exists
    python seed.py --demo --force    # overwrite the stored data of user "default"

Every document it writes is tagged ``data_origin="developer_seed_script"`` so it
can never be mistaken for real user data (or for the legacy auto-inserted demo
data that the backend removes at startup). Remove it again with
``POST /api/profile/reset``. Never point this script at a production database.
"""
import os
import sys
from datetime import datetime, timezone

# Ensure app is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.mongodb import get_database
from app.database.collections import COLLECTIONS, ensure_indexes
from app.services.profile_service import create_or_update_profile
from app.services.assessment_service import save_assessment
from app.services.fingerprint_service import generate_and_save_fingerprint
from app.services.transformation_service import generate_transformation_plan
from app.services.report_service import generate_climate_report
from app.services.solution_service import ensure_solutions_seeded

DEMO_PROFILE = {
    "business_name": "ABC Textile Manufacturing Ltd.",
    "name": "ABC Textile Manufacturing Ltd.",
    "industry": "Textile",
    "business_type": "Fabric Dyeing & Garment Finishing",
    "businessType": "Fabric Dyeing & Garment Finishing",
    "location": "Tirupur Industrial Cluster, Tamil Nadu, India",
    "employees": 145,
    "working_days": 26,
    "workingDaysPerMonth": 26,
    "production_volume": "42,000 meters / month",
    "productionVolume": "42,000 meters / month",
    "operating_hours": 16,
    "operatingHoursPerDay": 16,
    "business_size": "Medium",
    "businessSize": "Medium",
    "facility_area_sqft": 38000,
    "facilityAreaSqFt": 38000,
    "contact_email": "operations@abctextiles.in",
    "contactEmail": "operations@abctextiles.in",
    "phone": "+91 98450 12890"
}

DEMO_ASSESSMENT = {
    "energy": {
        "monthlyElectricityKwh": 38500,
        "monthlyElectricityBillInr": 346500,
        "dieselGeneratorHoursPerMonth": 64,
        "generatorFuelLitresPerMonth": 1280,
        "existingSolarCapacityKw": 0,
        "energyEfficientEquipmentPercent": 28,
    },
    "water": {
        "monthlyWaterLitres": 480000,
        "waterSource": "Groundwater / Borewell",
        "waterRecyclingAvailable": False,
        "rainwaterHarvesting": False,
        "leakageFrequency": "Monthly",
        "wastewaterTreatment": "Primary / Settling",
    },
    "waste": {
        "organicWasteKgPerMonth": 380,
        "plasticWasteKgPerMonth": 950,
        "paperWasteKgPerMonth": 420,
        "industrialWasteKgPerMonth": 1850,
        "textileMaterialWasteKgPerMonth": 3600,
        "currentRecyclingPercent": 22,
        "wasteSegregationPracticed": True,
    },
    "emissions": {
        "primaryFuel": "Electricity Grid",
        "monthlyDieselLitres": 1620,
        "monthlyPetrolLitres": 240,
        "monthlyNaturalGasKg": 0,
        "mainEmissionSources": ["Boiler Combustion", "Grid Electricity (Thermal Base)", "Heavy Transport", "Backup Genset"],
        "airPollutionControlSystem": "Basic Scrubber",
    },
    "mobility": {
        "deliveryVehiclesCount": 8,
        "vehicleFuelType": "Diesel",
        "monthlyFleetFuelLitres": 1950,
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
    }
}

SEED_TAG = {"data_origin": "developer_seed_script"}


def real_user_data_exists() -> bool:
    """True when user "default" has a profile/assessment that this script did not write."""
    db = get_database()
    for key in ("business_profiles", "climate_assessments"):
        if db[COLLECTIONS[key]].find_one({"user_id": "default", "data_origin": {"$ne": SEED_TAG["data_origin"]}}):
            return True
    return False


def clear_demo_data():
    from app.database.collections import USER_DATA_COLLECTIONS
    db = get_database()
    for key in USER_DATA_COLLECTIONS:
        db[COLLECTIONS[key]].delete_many({"user_id": "default"})
    print("Cleared stored data for user default")


def tag_seeded_documents():
    from app.database.collections import USER_DATA_COLLECTIONS
    db = get_database()
    for key in USER_DATA_COLLECTIONS:
        db[COLLECTIONS[key]].update_many({"user_id": "default"}, {"$set": SEED_TAG})

def seed():
    print("Seeding ClimaCred AI SAMPLE data (developer/testing utility)...")
    ensure_indexes()
    ensure_solutions_seeded()
    clear_demo_data()
    # Profile
    profile = create_or_update_profile(DEMO_PROFILE, user_id="default")
    print(f"✓ Profile seeded: {profile.get('business_name')} ({profile.get('industry')})")

    # Assessment
    assessment = save_assessment(DEMO_ASSESSMENT, user_id="default")
    print(f"✓ Assessment seeded: energy {assessment['energy']['monthlyElectricityKwh']} kWh/mo, water {assessment['water']['monthlyWaterLitres']} L/mo")

    # Fingerprint
    fp = generate_and_save_fingerprint(user_id="default")
    print(f"✓ Fingerprint generated: Overall {fp.get('overallScore')}/100 ({fp.get('scoreLabel')})")
    print(f"  Top improvements: {fp.get('topImprovementDimensions')}")

    # Transformation plan
    plan = generate_transformation_plan(user_id="default")
    print(f"✓ Transformation plan generated: {len(plan)} actions")

    # Report
    report = generate_climate_report(user_id="default")
    print(f"✓ Climate report generated: {report['report_id']}")

    # Seed impact demo record (before/after)
    from app.services.impact_service import create_impact_record
    demo_impact = {
        "before": {"energy_kwh": 38500, "water_litres": 480000, "waste_kg": 3600, "emissions_tonnes": 41.2, "cost_inr": 512000},
        "after": {"energy_kwh": 27720, "water_litres": 196800, "waste_kg": 1440, "emissions_tonnes": 23.9, "cost_inr": 338000},
        "intervention_ids": ["sol-solar","sol-water-ro","sol-machinery-vfd","sol-waste-recovery"],
        "notes": "Demo post-implementation data after Phase 1-3 interventions. Reported implementation outcome, not verified carbon reduction."
    }
    try:
        rec = create_impact_record(demo_impact, user_id="default")
        print(f"✓ Impact verification demo seeded: {len(rec.get('calculated_metrics',[]))} metrics")
    except Exception as e:
        print(f"  ! Impact seed warning: {e}")

    tag_seeded_documents()
    print("\nDemo seeding complete (all documents tagged data_origin=developer_seed_script).")
    print(" NOTE: This is DEMO data for ABC Textile Manufacturing, clearly labeled as illustrative, not measured real-world data.")
    print(" Remove it with: curl -X POST http://localhost:8000/api/profile/reset")

if __name__ == "__main__":
    if "--demo" not in sys.argv and "--yes" not in sys.argv:
        print(
            "Refusing to seed sample data without an explicit flag.\n"
            "This utility is for development/testing only.\n"
            "Run: python seed.py --demo"
        )
        sys.exit(1)
    if real_user_data_exists() and "--force" not in sys.argv:
        print(
            "Refusing to seed: user 'default' already has real (non-seed) business data.\n"
            "Seeding would delete it. Re-run with --force only if you really want that."
        )
        sys.exit(1)
    seed()
