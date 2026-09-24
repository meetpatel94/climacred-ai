from typing import List, Dict, Any, Optional
from app.climate_engine.recommendations import SOLUTION_CATALOG, generate_recommendations
from app.services.profile_service import get_profile
from app.services.assessment_service import get_assessment, has_assessment_data
from app.services.fingerprint_service import get_latest_fingerprint, generate_and_save_fingerprint

DEFAULT_USER_ID = "default"

def get_solutions(category: Optional[str] = None) -> List[Dict[str, Any]]:
    if not category or category.lower() == "all":
        return SOLUTION_CATALOG
    return [s for s in SOLUTION_CATALOG if s["category"].lower() == category.lower()]

def get_solution_by_id(solution_id: str) -> Optional[Dict[str, Any]]:
    for s in SOLUTION_CATALOG:
        if s["id"] == solution_id:
            return s
    return None

def get_personalized_recommendations(user_id: str = DEFAULT_USER_ID, top_n: int = 5) -> List[Dict[str, Any]]:
    """Recommendations are only produced from real stored user data.

    With an empty database there is nothing to personalise against, so an empty
    list is returned (previously demo defaults were implicitly assumed).
    """
    profile = get_profile(user_id)
    assessment = get_assessment(user_id)
    if not profile or not has_assessment_data(assessment):
        return []
    fingerprint = get_latest_fingerprint(user_id)
    if not fingerprint:
        try:
            fingerprint = generate_and_save_fingerprint(user_id)
        except ValueError:
            return []
    recs = generate_recommendations(profile, assessment, fingerprint, top_n=top_n)
    return recs

# Backwards compat for solutions catalog serving via DB? Seed green_solutions collection if empty
def ensure_solutions_seeded():
    from app.database.mongodb import get_collection
    from app.database.collections import COLLECTIONS
    col = get_collection(COLLECTIONS["green_solutions"])
    if col.count_documents({}) == 0:
        for sol in SOLUTION_CATALOG:
            try:
                col.insert_one({**sol, "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc)})
            except:
                pass
