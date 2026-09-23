from typing import Dict, Any, List
from datetime import datetime, timezone
from app.database.mongodb import get_collection
from app.database.collections import COLLECTIONS
from app.services.profile_service import get_profile
from app.services.assessment_service import get_assessment
from app.services.fingerprint_service import get_latest_fingerprint, generate_and_save_fingerprint
from app.climate_engine.simulations import simulate_with_fingerprint

DEFAULT_USER_ID = "default"

def simulate_scenario(selected_solution_ids: List[str], adoption_scale_percent: int = 100, user_id: str = DEFAULT_USER_ID) -> Dict[str, Any]:
    profile = get_profile(user_id)
    assessment = get_assessment(user_id)
    fingerprint = get_latest_fingerprint(user_id)
    if not fingerprint:
        fingerprint = generate_and_save_fingerprint(user_id)

    result = simulate_with_fingerprint(selected_solution_ids, profile, assessment, fingerprint, scale=adoption_scale_percent)

    # Save scenario to DB for audit
    col = get_collection(COLLECTIONS["scenarios"])
    doc = {
        "user_id": user_id,
        "selected_solution_ids": selected_solution_ids,
        "adoption_scale_percent": adoption_scale_percent,
        "result": result,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    try:
        col.insert_one(doc)
    except:
        pass

    return result

def get_scenario_history(user_id: str = DEFAULT_USER_ID, limit: int = 10) -> List[Dict[str, Any]]:
    col = get_collection(COLLECTIONS["scenarios"])
    cursor = col.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
    res = []
    for doc in cursor:
        doc.pop("_id", None)
        for k in ["created_at","updated_at"]:
            if k in doc and hasattr(doc[k], "isoformat"):
                doc[k] = doc[k].isoformat()
        # Also handle nested result timestamp?
        res.append(doc)
    return res
