from datetime import datetime, timezone
from typing import Dict, Any, Optional
from app.database.mongodb import get_collection
from app.database.collections import COLLECTIONS
from app.utils.validation import validate_assessment_data
import logging

logger = logging.getLogger(__name__)
DEFAULT_USER_ID = "default"

# Structural template only. It contains NO values: sections the user has not
# filled in stay empty, so missing data is never displayed as a fabricated
# number or as an invented zero.
EMPTY_SECTIONS = ["energy", "water", "waste", "emissions", "mobility", "greenPractices"]

def _serialize(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not doc:
        return doc
    d = dict(doc)
    d.pop("_id", None)
    d.pop("user_id", None)
    # Keep timestamps but not required for frontend
    d.pop("created_at", None)
    d.pop("updated_at", None)
    return d

def get_assessment(user_id: str = DEFAULT_USER_ID) -> Optional[Dict[str, Any]]:
    """Return the stored climate assessment, or None when nothing is stored yet.

    Previously this inserted a hardcoded demo assessment (38,500 kWh, 480,000 L,
    ...) on first read. That fabricated data has been removed so an empty
    database really is empty.
    """
    col = get_collection(COLLECTIONS["climate_assessments"])
    doc = col.find_one({"user_id": user_id}, sort=[("updated_at", -1)])
    if not doc:
        return None
    return _serialize(doc)


def has_assessment_data(assessment: Optional[Dict[str, Any]]) -> bool:
    """True only when the user has actually recorded at least one value."""
    if not assessment:
        return False
    for section in EMPTY_SECTIONS:
        values = assessment.get(section)
        if isinstance(values, dict):
            for value in values.values():
                if value is None or value == "" or value == []:
                    continue
                if isinstance(value, bool):
                    if value:
                        return True
                    continue
                if isinstance(value, (int, float)):
                    if value != 0:
                        return True
                    continue
                return True
    return False

def get_assessment_updated_at(user_id: str = DEFAULT_USER_ID) -> Optional[datetime]:
    """Timestamp of the stored assessment (used to ignore results derived from older data)."""
    col = get_collection(COLLECTIONS["climate_assessments"])
    doc = col.find_one({"user_id": user_id}, {"updated_at": 1}, sort=[("updated_at", -1)])
    value = (doc or {}).get("updated_at")
    if isinstance(value, datetime) and value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value if isinstance(value, datetime) else None


def has_business_data(user_id: str = DEFAULT_USER_ID) -> bool:
    """True only when the user has BOTH a stored profile and real assessment values.

    Derived documents (fingerprints, plans, scenarios, reports) are calculated from
    exactly these two inputs, so they are only served while both still exist. This
    prevents orphaned results (e.g. a leftover demo fingerprint) from resurfacing.
    """
    from app.services.profile_service import has_profile

    return has_profile(user_id) and has_assessment_data(get_assessment(user_id))


def save_assessment(data: Dict[str, Any], user_id: str = DEFAULT_USER_ID) -> Dict[str, Any]:
    # Validate
    validate_assessment_data(data)
    col = get_collection(COLLECTIONS["climate_assessments"])
    # Normalize: ensure all sections present, merge with existing to avoid missing
    existing = get_assessment(user_id) or {}
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
            target_key = "greenPractices" if section == "green_practices" else section
            if target_key in merged:
                # Already built in this pass. The "green_practices" alias always runs
                # after "greenPractices"; without this guard it overwrote the freshly
                # merged section with the stored one, so green practices could never be
                # changed after the first save (and an imported business kept the
                # previous business's practices).
                continue
            if section in existing:
                merged[section] = existing[section]
            elif section == "green_practices" and "greenPractices" in existing:
                merged["greenPractices"] = existing["greenPractices"]
    # Also handle snake_case sections coming from frontend? Already covered via extra allow

    # Ensure every section exists as an (empty) object – never with invented values
    for key in EMPTY_SECTIONS:
        if key not in merged:
            merged[key] = {}
        if not isinstance(merged[key], dict):
            merged[key] = {}
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

    # Invalidate the *current* fingerprint so it is recalculated from the new data, but
    # KEEP the earlier snapshots: they are real historical records and power the trend
    # charts / history comparison. Only the current snapshot is flagged as superseded.
    fp_col = get_collection(COLLECTIONS["climate_fingerprints"])
    fp_col.update_many({"user_id": user_id}, {"$set": {"superseded": True}})
    # Also invalidate transformation plan and reports cache
    t_col = get_collection(COLLECTIONS["transformation_plans"])
    t_col.delete_many({"user_id": user_id})
    r_col = get_collection(COLLECTIONS["climate_reports"])
    r_col.delete_many({"user_id": user_id})

    return _serialize(doc)

def patch_assessment(updates: Dict[str, Any], user_id: str = DEFAULT_USER_ID) -> Dict[str, Any]:
    existing = get_assessment(user_id) or {}
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
