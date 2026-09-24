from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.database.mongodb import get_collection
from app.database.collections import COLLECTIONS
from app.services.profile_service import get_profile
from app.services.assessment_service import get_assessment, has_assessment_data
from app.climate_engine.fingerprint import generate_fingerprint
from app.utils.validation import validate_business_profile, validate_assessment_data
import logging

logger = logging.getLogger(__name__)
DEFAULT_USER_ID = "default"

def get_latest_fingerprint(user_id: str = DEFAULT_USER_ID) -> Optional[Dict[str, Any]]:
    col = get_collection(COLLECTIONS["climate_fingerprints"])
    # Superseded snapshots stay stored as history but are no longer the current one.
    doc = col.find_one({"user_id": user_id, "superseded": {"$ne": True}}, sort=[("created_at", -1)])
    if not doc:
        return None
    d = dict(doc)
    d.pop("_id", None)
    # Convert datetime to iso for serialization
    for k in ["created_at","updated_at","generated_at"]:
        if k in d and hasattr(d[k], "isoformat"):
            d[k] = d[k].isoformat()
    return d

def generate_and_save_fingerprint(user_id: str = DEFAULT_USER_ID) -> Dict[str, Any]:
    profile = get_profile(user_id)
    assessment = get_assessment(user_id)

    # A fingerprint is only ever calculated from real, user-provided data.
    if not profile:
        raise ValueError("No business profile stored yet. Add your business data before generating a Climate Fingerprint.")
    if not assessment or not has_assessment_data(assessment):
        raise ValueError("No climate assessment data stored yet. Complete your Climate Assessment before generating a Climate Fingerprint.")

    # Validate data quality via utils? But allow generation even if low quality; we include warning
    # 1. Retrieve business profile - done
    # 2. Retrieve climate assessment - done
    # 3. Validate data
    try:
        validate_assessment_data(assessment)
    except Exception as e:
        logger.warning(f"Assessment validation warning: {e}")

    # 4. Calculate dimension scores + 5. overall + 6. high-impact areas + 7. explanations -> via generate_fingerprint
    fingerprint = generate_fingerprint(profile, assessment)

    # 8. Save fingerprint to MongoDB
    col = get_collection(COLLECTIONS["climate_fingerprints"])
    doc = dict(fingerprint)
    # Ensure generated_at is datetime for storage?
    # Keep iso string but also store datetime
    doc["user_id"] = user_id
    doc["created_at"] = datetime.now(timezone.utc)
    doc["updated_at"] = datetime.now(timezone.utc)
    # Convert generated_at to datetime if string?
    # Keep as string for retrieval but also store datetime
    col.insert_one(doc)

    # 9. Return structured result
    # Serialize: remove _id
    doc.pop("_id", None)
    for k in ["created_at","updated_at"]:
        if k in doc and hasattr(doc[k], "isoformat"):
            doc[k] = doc[k].isoformat()
    logger.info(f"Fingerprint generated for user {user_id} overall {fingerprint.get('overallScore')}")
    return doc

def get_or_generate_fingerprint(user_id: str = DEFAULT_USER_ID) -> Optional[Dict[str, Any]]:
    """Latest stored fingerprint, regenerated from stored data when possible.

    Returns None (instead of raising) when the user has not entered real data yet,
    so callers such as the dashboard/AI layer can show a clean empty state.
    """
    latest = get_latest_fingerprint(user_id)
    if latest:
        return latest
    try:
        return generate_and_save_fingerprint(user_id)
    except ValueError:
        return None


def get_fingerprint_history(user_id: str = DEFAULT_USER_ID, limit: int = 24) -> List[Dict[str, Any]]:
    """Stored fingerprint snapshots (oldest → newest) used for real historical charts.

    Each snapshot keeps the calculated dimension metrics that were used at the time,
    so trends are derived from records the user actually submitted.
    """
    col = get_collection(COLLECTIONS["climate_fingerprints"])
    cursor = col.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
    snapshots: List[Dict[str, Any]] = []
    for doc in cursor:
        created = doc.get("created_at") or doc.get("generated_at")
        dimensions = doc.get("dimensions") or []
        metrics: Dict[str, Any] = {}
        scores: Dict[str, Any] = {}
        for dim in dimensions:
            name = dim.get("dimension")
            if name:
                scores[name] = dim.get("score")
                metrics[name] = dim.get("metrics_used") or {}
        snapshots.append({
            "created_at": created.isoformat() if hasattr(created, "isoformat") else created,
            "overall_score": doc.get("overallScore"),
            "score_label": doc.get("scoreLabel"),
            "dimension_scores": scores,
            "dimension_metrics": metrics,
            "data_quality": doc.get("data_quality"),
        })
    snapshots.reverse()
    return snapshots
