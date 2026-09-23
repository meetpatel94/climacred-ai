"""
Seed script for ClimaCred AI demo business: ABC Textile Manufacturing
Run: python seed.py
Or: python -m seed
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

def clear_demo_data():
    db = get_database()
    for coll in COLLECTIONS.values():
        db[coll].delete_many({"user_id": "default"})
    # Also clear seeded solutions? No, keep solutions
    print("Cleared demo data for user default")

def seed():
    print("Seeding ClimaCred AI demo data...")
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

    print("\nDemo seeding complete.")
    print(" NOTE: This is DEMO data for ABC Textile Manufacturing, clearly labeled as illustrative, not measured real-world data.")
    print(" Dashboard should work immediately after setup.")

if __name__ == "__main__":
    seed()
