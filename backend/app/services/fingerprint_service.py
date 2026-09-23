from datetime import datetime, timezone
from typing import Dict, Any, Optional
from app.database.mongodb import get_collection
from app.database.collections import COLLECTIONS
from app.services.profile_service import get_profile
from app.services.assessment_service import get_assessment
from app.climate_engine.fingerprint import generate_fingerprint
from app.utils.validation import validate_business_profile, validate_assessment_data
import logging

logger = logging.getLogger(__name__)
DEFAULT_USER_ID = "default"

def get_latest_fingerprint(user_id: str = DEFAULT_USER_ID) -> Optional[Dict[str, Any]]:
    col = get_collection(COLLECTIONS["climate_fingerprints"])
    doc = col.find_one({"user_id": user_id}, sort=[("created_at", -1)])
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

    # Validate data existence
    if not profile or not assessment:
        raise ValueError("Missing business profile or climate assessment. Complete both before generating fingerprint.")

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

def get_or_generate_fingerprint(user_id: str = DEFAULT_USER_ID) -> Dict[str, Any]:
    latest = get_latest_fingerprint(user_id)
    if latest:
        return latest
    return generate_and_save_fingerprint(user_id)
