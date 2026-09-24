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
    "ai_conversations": "ai_conversations",
    # --- Data Import (app/services/import_service.py) -----------------------
    # Monthly time series + reference data that the application had no home for
    # before the Excel/CSV import workflow. Every document carries a
    # ``business_id`` so one business links its profile, resource streams,
    # historical series, assessment, scenarios, plan and impact records.
    "resource_consumption": "resource_consumption",
    "energy_data": "energy_data",
    "water_data": "water_data",
    "waste_data": "waste_data",
    "emissions_data": "emissions_data",
    "mobility_data": "mobility_data",
    "operations_materials": "operations_materials",
    "historical_climate_data": "historical_climate_data",
    "solution_recommendations": "solution_recommendations",
    "gemini_ai_test_questions": "gemini_ai_test_questions",
    "gemini_expected_behaviors": "gemini_expected_behaviors",
    # Audit trail of every upload (filename, dataset, rows, errors, timestamps).
    "data_imports": "data_imports",
}

#: Collections written by the data-import workflow, keyed by ``business_id``.
IMPORTED_TIME_SERIES_COLLECTIONS = (
    "resource_consumption",
    "energy_data",
    "water_data",
    "waste_data",
    "emissions_data",
    "mobility_data",
    "operations_materials",
    "historical_climate_data",
)

#: Collections that hold data belonging to one user (keyed by ``user_id``).
#: ``green_solutions`` is platform catalog content and is intentionally excluded.
USER_DATA_COLLECTIONS = (
    "business_profiles",
    "climate_assessments",
    "climate_fingerprints",
    "scenarios",
    "transformation_plans",
    "impact_records",
    "climate_reports",
    "ai_insights",
    "ai_conversations",
    # Imported data (keyed by ``business_id`` with ``user_id: None``) plus the
    # import audit trail. Included so "Reset All Stored Data" really empties the
    # database - see ``profile_service.reset_profile``.
    "resource_consumption",
    "energy_data",
    "water_data",
    "waste_data",
    "emissions_data",
    "mobility_data",
    "operations_materials",
    "historical_climate_data",
    "solution_recommendations",
    "gemini_ai_test_questions",
    "gemini_expected_behaviors",
    "data_imports",
)

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
        db[COLLECTIONS["ai_conversations"]].create_index([("user_id", 1), ("conversation_id", 1)])
        # Imported data: one document per (business, month) / (business, natural key),
        # so a re-upload updates in place instead of duplicating history.
        for key in IMPORTED_TIME_SERIES_COLLECTIONS:
            db[COLLECTIONS[key]].create_index([("business_id", 1), ("month", 1)], unique=True)
            db[COLLECTIONS[key]].create_index([("business_id", 1), ("month", -1)])
        db[COLLECTIONS["solution_recommendations"]].create_index([("business_id", 1), ("solution_id", 1)], unique=True)
        db[COLLECTIONS["gemini_ai_test_questions"]].create_index("question_id", unique=True)
        db[COLLECTIONS["gemini_expected_behaviors"]].create_index("test_id", unique=True)
        db[COLLECTIONS["data_imports"]].create_index([("user_id", 1), ("started_at", -1)])
        logger.info("MongoDB indexes ensured")
    except Exception as e:
        logger.warning(f"Could not ensure indexes (mock DB or error): {e}")

def get_collections():
    db = get_database()
    return {k: db[v] for k, v in COLLECTIONS.items()}
