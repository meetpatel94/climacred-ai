"""
Collection names and index creation
"""
from app.database.mongodb import get_database, is_mock_db
import logging

logger = logging.getLogger(__name__)

COLLECTIONS = {
    "users": "users",
    "business_profiles": "business_profiles",
    "climate_assessments": "climate_assessments",
    "climate_fingerprints": "climate_fingerprints",
    "green_solutions": "green_solutions",
    "scenarios": "scenarios",
    "transformation_plans": "transformation_plans",
    "impact_records": "impact_records",
    "climate_reports": "climate_reports",
    "ai_insights": "ai_insights",
}

def ensure_indexes():
    try:
        db = get_database()
        # Business profiles: single doc per default user
        db[COLLECTIONS["business_profiles"]].create_index("user_id", unique=False)
        db[COLLECTIONS["climate_assessments"]].create_index("user_id")
        db[COLLECTIONS["climate_fingerprints"]].create_index([("user_id", 1), ("created_at", -1)])
        db[COLLECTIONS["green_solutions"]].create_index("id", unique=True)
        db[COLLECTIONS["scenarios"]].create_index("user_id")
        db[COLLECTIONS["transformation_plans"]].create_index("user_id")
        db[COLLECTIONS["impact_records"]].create_index([("user_id", 1), ("created_at", -1)])
        db[COLLECTIONS["climate_reports"]].create_index([("user_id", 1), ("generated_at", -1)])
        db[COLLECTIONS["ai_insights"]].create_index([("user_id", 1), ("data_signature", 1)])
        logger.info("MongoDB indexes ensured")
    except Exception as e:
        logger.warning(f"Could not ensure indexes (mock DB or error): {e}")

def get_collections():
    db = get_database()
    return {k: db[v] for k, v in COLLECTIONS.items()}
