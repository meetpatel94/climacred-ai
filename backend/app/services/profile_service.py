from datetime import datetime, timezone
from typing import Dict, Any, Optional
from bson import ObjectId
from app.database.mongodb import get_collection
from app.database.collections import COLLECTIONS
from app.utils.validation import validate_business_profile
import logging

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = "default"

def _normalize_profile(data: Dict[str, Any], fill_defaults: bool = True) -> Dict[str, Any]:
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
    # No fabricated business defaults: a profile is only ever what the user
    # entered or imported. Missing fields simply stay absent.
    return normalized

def get_profile(user_id: str = DEFAULT_USER_ID) -> Optional[Dict[str, Any]]:
    """Return the stored profile, or None when the user has not created one yet.

    This used to insert (and return) a hardcoded "ABC Textile" demo profile on
    first read. That fabricated business data has been removed: an empty database
    must stay empty until the user submits real data.
    """
    col = get_collection(COLLECTIONS["business_profiles"])
    doc = col.find_one({"user_id": user_id})
    if not doc:
        return None
    return _serialize_profile(doc)

def has_profile(user_id: str = DEFAULT_USER_ID) -> bool:
    col = get_collection(COLLECTIONS["business_profiles"])
    return col.find_one({"user_id": user_id}, {"_id": 1}) is not None

def _serialize_profile(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
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
    # BUG FIX: normalize the INCOMING payload alone first, so a value submitted via
    # either naming convention (e.g. only "businessType", or only "business_type")
    # always wins over the stale value stored in the existing document.
    # Previously, merging the stored doc first made the stored canonical key look
    # "explicitly provided", silently discarding alias-only updates.
    incoming = _normalize_profile(dict(data), fill_defaults=False)
    incoming.pop("_id", None)
    incoming.pop("created_at", None)
    incoming.pop("updated_at", None)
    if existing:
        base = {k: v for k, v in existing.items() if k not in ("_id",)}
        merged = {**base, **incoming}
    else:
        merged = incoming
    # Re-sync aliases on the merged document (incoming canonical value wins on conflict)
    normalized = _normalize_profile(merged)
    # Extract canonical for validation (only fields the user actually provided)
    validate_business_profile({
        "employees": normalized.get("employees"),
        "working_days": normalized.get("working_days"),
        "operating_hours": normalized.get("operating_hours"),
        "facility_area_sqft": normalized.get("facility_area_sqft")
    })
    # NOTE: no default business identity is injected here. Fields the user did not
    # provide remain absent so the UI can show a proper empty state.

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
    """Development reset: delete EVERY stored document of this user.

    Previously only the business profile was deleted, so the stored assessment,
    fingerprint (e.g. the old demo score 47.5), plans, scenarios, reports and AI
    caches kept the dashboard populated after a "reset". Now all per-user
    collections are cleared, so GET /api/profile returns null and every module
    shows its empty state. The shared solution catalog is platform content and
    is not touched. Nothing is re-created afterwards.
    """
    from app.database.collections import USER_DATA_COLLECTIONS

    deleted: Dict[str, int] = {}
    for key in USER_DATA_COLLECTIONS:
        result = get_collection(COLLECTIONS[key]).delete_many({"user_id": user_id})
        deleted[key] = int(getattr(result, "deleted_count", 0) or 0)
    logger.info(f"All stored data cleared for user {user_id}: {deleted}")
    return {
        "has_data": False,
        "data": None,
        "profile": None,
        "user_id": user_id,
        "deleted": deleted,
        "message": "All stored business data for this user was deleted. The application is now empty.",
    }

def patch_profile(updates: Dict[str, Any], user_id: str = DEFAULT_USER_ID) -> Dict[str, Any]:
    # Filter allowed fields
    allowed = ["business_name","name","industry","business_type","businessType","location","employees","working_days","workingDaysPerMonth","production_volume","productionVolume","operating_hours","operatingHoursPerDay","business_size","businessSize","facility_area_sqft","facilityAreaSqFt","contact_email","contactEmail","phone"]
    filtered = {k:v for k,v in updates.items() if k in allowed}
    return create_or_update_profile(filtered, user_id)
