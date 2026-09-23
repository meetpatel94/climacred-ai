from datetime import datetime, timezone
from typing import Dict, Any
from app.database.mongodb import get_collection
from app.database.collections import COLLECTIONS
from app.utils.validation import validate_assessment_data
import logging

logger = logging.getLogger(__name__)
DEFAULT_USER_ID = "default"

DEFAULT_ASSESSMENT = {
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

def _serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return doc
    d = dict(doc)
    d.pop("_id", None)
    d.pop("user_id", None)
    # Keep timestamps but not required for frontend
    d.pop("created_at", None)
    d.pop("updated_at", None)
    return d

def get_assessment(user_id: str = DEFAULT_USER_ID) -> Dict[str, Any]:
    col = get_collection(COLLECTIONS["climate_assessments"])
    doc = col.find_one({"user_id": user_id}, sort=[("updated_at", -1)])
    if not doc:
        # insert default
        new_doc = {
            "user_id": user_id,
            **DEFAULT_ASSESSMENT,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        try:
            col.insert_one(new_doc)
        except:
            pass
        return _serialize(new_doc)
    return _serialize(doc)

def save_assessment(data: Dict[str, Any], user_id: str = DEFAULT_USER_ID) -> Dict[str, Any]:
    # Validate
    validate_assessment_data(data)
    col = get_collection(COLLECTIONS["climate_assessments"])
    # Normalize: ensure all sections present, merge with existing to avoid missing
    existing = get_assessment(user_id)
    # data may be partial (PATCH) or full (POST)
    # If data contains nested sections, merge
    merged = {}
    for section in ["energy","water","waste","emissions","mobility","greenPractices","green_practices"]:
        if section in data:
            # merge existing section with new
            existing_section = existing.get(section) or existing.get("greenPractices") if section in ["greenPractices","green_practices"] else existing.get(section)
            # handle alias green_practices vs greenPractices
            target_key = "greenPractices" if section in ["greenPractices","green_practices"] else section
            if target_key not in merged:
                merged[target_key] = {}
            if existing_section:
                merged[target_key].update(existing_section)
            merged[target_key].update(data[section])
        else:
            # keep existing if not provided
            if section in existing:
                merged[section] = existing[section]
            elif section == "green_practices" and "greenPractices" in existing:
                merged["greenPractices"] = existing["greenPractices"]
    # Also handle snake_case sections coming from frontend? Already covered via extra allow

    # Ensure all default sections at least present
    for key in DEFAULT_ASSESSMENT:
        if key not in merged:
            merged[key] = DEFAULT_ASSESSMENT[key]
        # else ensure subfields defaults for missing?
    # Also handle green_practices alias
    if "green_practices" in merged and "greenPractices" not in merged:
        merged["greenPractices"] = merged.pop("green_practices")
    if "green_practices" in merged:
        del merged["green_practices"]

    doc = {
        "user_id": user_id,
        **merged,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    # Upsert: keep history? Spec says store structured documents; we will keep only latest but also keep history collection? For simplicity, update latest
    # Delete old and insert new to maintain single active
    col.delete_many({"user_id": user_id})
    col.insert_one(doc)
    logger.info(f"Assessment saved for user {user_id}, invalidate fingerprint cache")

    # Invalidate fingerprint: delete old fingerprint so it recalculates on next generate? Or keep but mark stale?
    # We'll delete old fingerprint to force recalc
    fp_col = get_collection(COLLECTIONS["climate_fingerprints"])
    fp_col.delete_many({"user_id": user_id})
    # Also invalidate transformation plan and reports cache
    t_col = get_collection(COLLECTIONS["transformation_plans"])
    t_col.delete_many({"user_id": user_id})
    r_col = get_collection(COLLECTIONS["climate_reports"])
    r_col.delete_many({"user_id": user_id})

    return _serialize(doc)

def patch_assessment(updates: Dict[str, Any], user_id: str = DEFAULT_USER_ID) -> Dict[str, Any]:
    existing = get_assessment(user_id)
    # Deep merge
    merged = {}
    for k, v in existing.items():
        if isinstance(v, dict):
            merged[k] = dict(v)
        else:
            merged[k] = v
    for section, values in updates.items():
        if section in merged and isinstance(values, dict) and isinstance(merged[section], dict):
            merged[section].update(values)
        else:
            merged[section] = values
    return save_assessment(merged, user_id)
