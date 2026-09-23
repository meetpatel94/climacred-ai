from datetime import datetime, timezone
from typing import Dict, Any, Optional
from bson import ObjectId
from app.database.mongodb import get_collection
from app.database.collections import COLLECTIONS
from app.utils.validation import validate_business_profile
import logging

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = "default"

def _normalize_profile(data: Dict[str, Any]) -> Dict[str, Any]:
    # Map frontend aliases to canonical snake_case and preserve both
    # Canonical is snake_case; frontend is camelCase/Pascal
    mapping = {
        "name": "business_name",
        "businessType": "business_type",
        "workingDaysPerMonth": "working_days",
        "productionVolume": "production_volume",
        "operatingHoursPerDay": "operating_hours",
        "businessSize": "business_size",
        "facilityAreaSqFt": "facility_area_sqft",
        "contactEmail": "contact_email",
    }
    # First, separate canonical vs frontend inputs to resolve conflicts: canonical wins
    # Build temp dict of all values keyed by canonical
    canonical_values = {}
    frontend_only = {}
    for k, v in data.items():
        canonical = mapping.get(k, k)
        if k in mapping:
            # This is a frontend alias; store but don't overwrite canonical if canonical already provided explicitly
            if canonical not in data or k == canonical:
                # No explicit canonical provided, so frontend value will be used if canonical not already set
                if canonical not in canonical_values:
                    canonical_values[canonical] = v
                frontend_only[k] = v
            else:
                # Canonical explicitly provided elsewhere – frontend alias is secondary, ignore for canonical
                frontend_only[k] = v
                continue
        else:
            # It's canonical or unknown, set directly
            canonical_values[canonical] = v
            # If this canonical has a frontend alias present also, canonical wins; frontend will be synced later

    # Now build normalized with both forms synced to canonical value
    normalized = {}
    # First add all canonical values
    for canon, val in canonical_values.items():
        normalized[canon] = val
    # Also add any frontend-only keys that didn't have canonical (already covered)
    # Now ensure both naming conventions present and synced: frontend = canonical value
    reverse_map = {v:k for k,v in mapping.items()}
    for canonical, frontend in reverse_map.items():
        if canonical in normalized:
            # Sync frontend to canonical
            normalized[frontend] = normalized[canonical]
        elif frontend in frontend_only:
            # Only frontend was provided, canonical already set above; but if not, set it
            normalized[canonical] = frontend_only[frontend]
            normalized[frontend] = frontend_only[frontend]
    # Also preserve any other frontend keys that were not in mapping but are frontend style
    for k, v in frontend_only.items():
        if k not in normalized:
            normalized[k] = v

    # defaults
    if "business_name" not in normalized and "name" not in normalized:
        pass
    # Ensure required fields have defaults if missing for front compat
    defaults = {
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
    for key, val in defaults.items():
        if key not in normalized or normalized[key] is None or normalized[key] == "":
            normalized[key] = val
        # also ensure alias
        # mapping handle already

    return normalized

def get_profile(user_id: str = DEFAULT_USER_ID) -> Dict[str, Any]:
    col = get_collection(COLLECTIONS["business_profiles"])
    doc = col.find_one({"user_id": user_id})
    if not doc:
        # return default seeded profile normalized
        default = _normalize_profile({})
        default["user_id"] = user_id
        default["created_at"] = datetime.now(timezone.utc)
        default["updated_at"] = datetime.now(timezone.utc)
        # insert
        try:
            col.insert_one(default)
        except:
            pass
        # remove mongo _id for return
        default.pop("_id", None)
        return _serialize_profile(default)
    return _serialize_profile(doc)

def _serialize_profile(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return doc
    doc = dict(doc)
    doc.pop("_id", None)
    # Ensure both naming conventions are synced – canonical is source of truth
    mapping = {
        "business_name": "name",
        "business_type": "businessType",
        "working_days": "workingDaysPerMonth",
        "production_volume": "productionVolume",
        "operating_hours": "operatingHoursPerDay",
        "business_size": "businessSize",
        "facility_area_sqft": "facilityAreaSqFt",
        "contact_email": "contactEmail",
    }
    for canonical, frontend in mapping.items():
        if canonical in doc:
            # Canonical wins, sync frontend
            doc[frontend] = doc[canonical]
        elif frontend in doc:
            doc[canonical] = doc[frontend]
        # If both exist but differ, canonical wins
        if canonical in doc and frontend in doc and doc[canonical] != doc[frontend]:
            doc[frontend] = doc[canonical]
    # Also direct copies for API compatibility
    # Ensure int fields are int
    for f in ["employees","working_days","workingDaysPerMonth","operating_hours","operatingHoursPerDay"]:
        if f in doc and doc[f] is not None:
            try:
                doc[f] = int(doc[f])
            except:
                pass
    if "facility_area_sqft" in doc:
        try:
            doc["facility_area_sqft"] = float(doc["facility_area_sqft"])
            doc["facilityAreaSqFt"] = float(doc["facilityAreaSqFt"])
        except:
            pass
    return doc

def create_or_update_profile(data: Dict[str, Any], user_id: str = DEFAULT_USER_ID) -> Dict[str, Any]:
    # Validate
    # For patch, we validate after merging
    col = get_collection(COLLECTIONS["business_profiles"])
    existing = col.find_one({"user_id": user_id})
    if existing:
        merged = {**existing, **data}
    else:
        merged = data
    # Normalize before validation
    normalized = _normalize_profile(merged)
    # Extract canonical for validation
    validate_business_profile({
        "employees": normalized.get("employees"),
        "working_days": normalized.get("working_days"),
        "operating_hours": normalized.get("operating_hours"),
        "facility_area_sqft": normalized.get("facility_area_sqft")
    })

    normalized["user_id"] = user_id
    normalized["updated_at"] = datetime.now(timezone.utc)
    if not existing:
        normalized["created_at"] = datetime.now(timezone.utc)
        col.insert_one(normalized)
    else:
        col.update_one({"user_id": user_id}, {"$set": normalized})

    # Fetch updated
    doc = col.find_one({"user_id": user_id})
    logger.info(f"Profile upsert for user {user_id}")
    return _serialize_profile(doc)

def reset_profile(user_id: str = DEFAULT_USER_ID) -> Dict[str, Any]:
    col = get_collection(COLLECTIONS["business_profiles"])
    col.delete_many({"user_id": user_id})
    # also delete related data? Spec says reset profile only
    # Create fresh default
    return get_profile(user_id)

def patch_profile(updates: Dict[str, Any], user_id: str = DEFAULT_USER_ID) -> Dict[str, Any]:
    # Filter allowed fields
    allowed = ["business_name","name","industry","business_type","businessType","location","employees","working_days","workingDaysPerMonth","production_volume","productionVolume","operating_hours","operatingHoursPerDay","business_size","businessSize","facility_area_sqft","facilityAreaSqFt","contact_email","contactEmail","phone"]
    filtered = {k:v for k,v in updates.items() if k in allowed}
    return create_or_update_profile(filtered, user_id)
