"""
Detection and removal of the legacy "ABC Textile Manufacturing Ltd." demo business.

Where the fake data came from
-----------------------------
Builds up to commit a9db8ba auto-INSERTED a demo business into MongoDB the first
time ``GET /api/profile`` / ``GET /api/assessment`` found no document
(``profile_service.get_profile`` / ``assessment_service.get_assessment`` wrote
hardcoded defaults), and ``GET /api/climate-fingerprint`` then stored a
fingerprint calculated from them (overall score 47.5). ``backend/seed.py
--demo`` wrote the same values. The current code no longer inserts anything, but
those documents stayed in the MongoDB database (db ``climacred``, user_id
``default``) and were served as if they were the user's own data:

    ABC Textile Manufacturing Ltd. - Tirupur Industrial Cluster - 145 employees -
    38,000 sq.ft - 38,500 kWh - 480,000 L - 3,600 kg textile waste - 1,950 L fleet
    fuel -> calculated 36.47 t CO2e / month and a 47.5/100 Climate Readiness score.

Safety rules
------------
* Only documents that match the exact legacy signature are touched. A real
  business cannot coincidentally match these combinations of values.
* A profile whose business name is still the demo name (plus another demo
  identity field) is the demo business -> deleted.
* A profile that was renamed by the user but still carries demo identity fields
  (the old code filled every missing field with a demo value) keeps everything
  the user entered; only the leftover demo fields are removed.
* An assessment identical to the demo numbers is deleted; a partially edited one
  keeps the user's values and only loses fields that still hold demo numbers.
* Results derived from contaminated inputs (fingerprints, plans, reports,
  scenarios, AI caches) are removed for affected users - they are recalculated
  from the remaining real data on demand. User-entered impact records are kept
  (only the seed script's demo impact record is removed).
* Documents written by ``seed.py --demo`` are tagged ``data_origin=
  "developer_seed_script"`` and are left alone (explicit developer action).

Usage
-----
Runs automatically at backend startup (``PURGE_LEGACY_DEMO_DATA=true``).
Inspect or clean a database manually (from the ``backend`` directory)::

    python -m app.database.legacy_demo            # read-only report
    python -m app.database.legacy_demo --apply    # remove legacy demo data
"""
from __future__ import annotations

import argparse
import json
import logging
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.database.collections import COLLECTIONS, USER_DATA_COLLECTIONS

logger = logging.getLogger(__name__)

SEED_TAG_FIELD = "data_origin"
SEED_TAG_VALUE = "developer_seed_script"

DEMO_BUSINESS_NAME = "ABC Textile Manufacturing Ltd."

# Distinctive identity values written by the legacy auto-insert / seed / mock data.
# (field names in both naming conventions stored by the profile service)
LEGACY_PROFILE_IDENTITY: Dict[Tuple[str, ...], Any] = {
    ("location",): "Tirupur Industrial Cluster, Tamil Nadu, India",
    ("contact_email", "contactEmail"): "operations@abctextiles.in",
    ("phone",): "+91 98450 12890",
    ("business_type", "businessType"): "Fabric Dyeing & Garment Finishing",
    ("production_volume", "productionVolume"): "42,000 meters / month",
    ("employees",): 145,
    ("facility_area_sqft", "facilityAreaSqFt"): 38000,
}

# Numeric assessment values of the legacy demo (identical in the old
# DEFAULT_ASSESSMENT, seed.py DEMO_ASSESSMENT and the old frontend mockData.ts).
LEGACY_ASSESSMENT_STRONG: Dict[str, float] = {
    "energy.monthlyElectricityKwh": 38500,
    "energy.monthlyElectricityBillInr": 346500,
    "energy.generatorFuelLitresPerMonth": 1280,
    "water.monthlyWaterLitres": 480000,
    "waste.plasticWasteKgPerMonth": 950,
    "waste.paperWasteKgPerMonth": 420,
    "waste.industrialWasteKgPerMonth": 1850,
    "waste.textileMaterialWasteKgPerMonth": 3600,
    "emissions.monthlyDieselLitres": 1620,
    "mobility.monthlyFleetFuelLitres": 1950,
}
LEGACY_ASSESSMENT_WEAK: Dict[str, float] = {
    "energy.dieselGeneratorHoursPerMonth": 64,
    "energy.energyEfficientEquipmentPercent": 28,
    "waste.organicWasteKgPerMonth": 380,
    "waste.currentRecyclingPercent": 22,
    "emissions.monthlyPetrolLitres": 240,
    "mobility.deliveryVehiclesCount": 8,
}
#: Strong matches needed before an assessment is considered demo-contaminated.
ASSESSMENT_STRONG_THRESHOLD = 3

# Inputs recorded inside fingerprint snapshots (dimensions[].metrics_used).
LEGACY_FINGERPRINT_METRICS: Tuple[Tuple[str, str, float], ...] = (
    ("Energy", "monthly_kwh", 38500),
    ("Water", "monthly_litres", 480000),
    ("Waste", "textile_waste", 3600),
    ("Emissions", "diesel_litres", 1620),
    ("Mobility", "monthly_fuel", 1950),
)
FINGERPRINT_THRESHOLD = 3

# seed.py demo impact record ("before" block).
LEGACY_IMPACT_BEFORE = {"energy_kwh": 38500, "water_litres": 480000, "waste_kg": 3600}

# Baseline recorded inside scenario simulation results (result.current_state).
LEGACY_SCENARIO_STATE = {
    "energy_monthly_kwh": 38500,
    "water_monthly_litres": 480000,
    "waste_monthly_kg": 7200,
    "emissions_monthly_tonnes": 36.47,
    "mobility_monthly_fuel": 1950,
}
SCENARIO_THRESHOLD = 3

DERIVED_COLLECTIONS = ("climate_fingerprints", "transformation_plans", "climate_reports", "scenarios", "ai_insights")


# ---------------------------------------------------------------------------
# Matching helpers
# ---------------------------------------------------------------------------
def _same(a: Any, b: Any) -> bool:
    if isinstance(b, (int, float)) and not isinstance(b, bool):
        try:
            return a is not None and not isinstance(a, bool) and abs(float(a) - float(b)) < 1e-9
        except (TypeError, ValueError):
            return False
    return isinstance(a, str) and a.strip() == str(b)


def _get_path(doc: Dict[str, Any], dotted: str) -> Any:
    node: Any = doc
    for part in dotted.split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(part)
    return node


def _is_seed_fixture(doc: Dict[str, Any]) -> bool:
    return doc.get(SEED_TAG_FIELD) == SEED_TAG_VALUE


def classify_profile(doc: Dict[str, Any]) -> Tuple[Optional[str], List[str]]:
    """('demo', []) | ('hybrid', [fields to unset]) | (None, [])."""
    if not doc or _is_seed_fixture(doc):
        return None, []
    matched_fields: List[str] = []
    for names, value in LEGACY_PROFILE_IDENTITY.items():
        if any(_same(doc.get(name), value) for name in names):
            matched_fields.extend(name for name in names if name in doc and _same(doc.get(name), value))
    matched_groups = sum(
        1 for names, value in LEGACY_PROFILE_IDENTITY.items() if any(_same(doc.get(n), value) for n in names)
    )
    name_is_demo = _same(doc.get("business_name"), DEMO_BUSINESS_NAME) or _same(doc.get("name"), DEMO_BUSINESS_NAME)
    if name_is_demo and matched_groups >= 1:
        return "demo", []
    if matched_groups >= 2:
        return "hybrid", sorted(set(matched_fields))
    return None, []


def classify_assessment(doc: Dict[str, Any]) -> Tuple[Optional[str], List[str]]:
    """('demo', []) | ('hybrid', [dotted fields to unset]) | (None, [])."""
    if not doc or _is_seed_fixture(doc):
        return None, []
    strong = [path for path, value in LEGACY_ASSESSMENT_STRONG.items() if _same(_get_path(doc, path), value)]
    if len(strong) < ASSESSMENT_STRONG_THRESHOLD:
        return None, []
    weak = [path for path, value in LEGACY_ASSESSMENT_WEAK.items() if _same(_get_path(doc, path), value)]
    if len(strong) == len(LEGACY_ASSESSMENT_STRONG) and len(weak) == len(LEGACY_ASSESSMENT_WEAK):
        return "demo", []
    return "hybrid", strong + weak


def is_legacy_fingerprint(doc: Dict[str, Any]) -> bool:
    if not doc or _is_seed_fixture(doc):
        return False
    metrics = {d.get("dimension"): (d.get("metrics_used") or {}) for d in (doc.get("dimensions") or []) if isinstance(d, dict)}
    hits = sum(1 for dim, key, value in LEGACY_FINGERPRINT_METRICS if _same((metrics.get(dim) or {}).get(key), value))
    return hits >= FINGERPRINT_THRESHOLD


def is_legacy_report(doc: Dict[str, Any]) -> bool:
    if not doc or _is_seed_fixture(doc):
        return False
    embedded = doc.get("business_profile") or doc.get("businessProfile") or {}
    return isinstance(embedded, dict) and classify_profile(embedded)[0] == "demo"


def is_legacy_scenario(doc: Dict[str, Any]) -> bool:
    if not doc or _is_seed_fixture(doc):
        return False
    state = ((doc.get("result") or {}).get("current_state")) or {}
    hits = sum(1 for key, value in LEGACY_SCENARIO_STATE.items() if _same(state.get(key), value))
    return hits >= SCENARIO_THRESHOLD


def is_legacy_ai_insight(doc: Dict[str, Any]) -> bool:
    if not doc or _is_seed_fixture(doc):
        return False
    calculated = ((doc.get("payload") or {}).get("calculated")) or {}
    return _same(calculated.get("business_name"), DEMO_BUSINESS_NAME) or (
        _same(calculated.get("energy_kwh_month"), 38500) and _same(calculated.get("water_litres_month"), 480000)
    )


def is_legacy_impact(doc: Dict[str, Any]) -> bool:
    if not doc or _is_seed_fixture(doc):
        return False
    before = doc.get("before") or {}
    return isinstance(before, dict) and all(_same(before.get(k), v) for k, v in LEGACY_IMPACT_BEFORE.items())


# ---------------------------------------------------------------------------
# Scan / purge
# ---------------------------------------------------------------------------
def _db(db: Any = None) -> Any:
    if db is not None:
        return db
    from app.database.mongodb import get_database

    return get_database()


def scan(db: Any = None) -> Dict[str, Any]:
    """Read-only report of legacy demo documents per collection."""
    database = _db(db)
    report: Dict[str, Any] = {"profiles": [], "assessments": [], "fingerprints": 0, "reports": 0, "impact_records": 0}
    for doc in database[COLLECTIONS["business_profiles"]].find({}):
        verdict, fields = classify_profile(doc)
        if verdict:
            report["profiles"].append({"user_id": doc.get("user_id"), "verdict": verdict, "demo_fields": fields})
    for doc in database[COLLECTIONS["climate_assessments"]].find({}):
        verdict, fields = classify_assessment(doc)
        if verdict:
            report["assessments"].append({"user_id": doc.get("user_id"), "verdict": verdict, "demo_fields": fields})
    report["fingerprints"] = sum(1 for d in database[COLLECTIONS["climate_fingerprints"]].find({}) if is_legacy_fingerprint(d))
    report["reports"] = sum(1 for d in database[COLLECTIONS["climate_reports"]].find({}) if is_legacy_report(d))
    report["impact_records"] = sum(1 for d in database[COLLECTIONS["impact_records"]].find({}) if is_legacy_impact(d))
    report["scenarios"] = sum(1 for d in database[COLLECTIONS["scenarios"]].find({}) if is_legacy_scenario(d))
    report["ai_insights"] = sum(1 for d in database[COLLECTIONS["ai_insights"]].find({}) if is_legacy_ai_insight(d))
    report["found"] = bool(
        report["profiles"] or report["assessments"] or report["fingerprints"] or report["reports"]
        or report["impact_records"] or report["scenarios"] or report["ai_insights"]
    )
    return report


def purge(db: Any = None, dry_run: bool = False) -> Dict[str, Any]:
    """Remove legacy demo documents (see module docstring for the exact rules)."""
    database = _db(db)
    summary: Dict[str, Any] = {"dry_run": dry_run, "deleted": {}, "modified": {}, "affected_users": []}
    affected: set = set()        # users with any legacy document
    inputs_affected: set = set()  # users whose profile/assessment held demo values

    def _count(bucket: str, key: str, n: int = 1) -> None:
        summary[bucket][key] = summary[bucket].get(key, 0) + n

    profiles = database[COLLECTIONS["business_profiles"]]
    for doc in list(profiles.find({})):
        verdict, fields = classify_profile(doc)
        if verdict == "demo":
            affected.add(doc.get("user_id")); inputs_affected.add(doc.get("user_id"))
            _count("deleted", "business_profiles")
            if not dry_run:
                profiles.delete_one({"_id": doc["_id"]})
        elif verdict == "hybrid":
            affected.add(doc.get("user_id")); inputs_affected.add(doc.get("user_id"))
            _count("modified", "business_profiles")
            if not dry_run:
                profiles.update_one({"_id": doc["_id"]}, {"$unset": {f: "" for f in fields}})

    assessments = database[COLLECTIONS["climate_assessments"]]
    for doc in list(assessments.find({})):
        verdict, fields = classify_assessment(doc)
        if verdict == "demo":
            affected.add(doc.get("user_id")); inputs_affected.add(doc.get("user_id"))
            _count("deleted", "climate_assessments")
            if not dry_run:
                assessments.delete_one({"_id": doc["_id"]})
        elif verdict == "hybrid":
            affected.add(doc.get("user_id")); inputs_affected.add(doc.get("user_id"))
            _count("modified", "climate_assessments")
            if not dry_run:
                assessments.update_one({"_id": doc["_id"]}, {"$unset": {f: "" for f in fields}})

    # Individually recognisable demo-derived documents (e.g. a demo snapshot left in the
    # history of a user who has since entered real data) are removed one by one.
    for key, predicate in (
        ("climate_fingerprints", is_legacy_fingerprint),
        ("climate_reports", is_legacy_report),
        ("impact_records", is_legacy_impact),
        ("scenarios", is_legacy_scenario),
        ("ai_insights", is_legacy_ai_insight),
    ):
        col = database[COLLECTIONS[key]]
        for doc in list(col.find({})):
            if predicate(doc):
                affected.add(doc.get("user_id"))
                _count("deleted", key)
                if not dry_run:
                    col.delete_one({"_id": doc["_id"]})

    # Everything calculated from contaminated inputs is recalculated on demand.
    for user_id in sorted(u for u in inputs_affected if u is not None):
        for key in DERIVED_COLLECTIONS:
            col = database[COLLECTIONS[key]]
            query = {"user_id": user_id, SEED_TAG_FIELD: {"$ne": SEED_TAG_VALUE}}
            n = col.count_documents(query)
            if n:
                _count("deleted", key, n)
                if not dry_run:
                    col.delete_many(query)

    summary["affected_users"] = sorted(str(u) for u in affected if u is not None)
    summary["found"] = bool(summary["deleted"] or summary["modified"])
    return summary


def purge_on_startup() -> Dict[str, Any]:
    """Startup hook: remove legacy demo data and log exactly what happened."""
    summary = purge()
    if summary["found"]:
        logger.warning(
            "Removed legacy 'ABC Textile' demo data written by older ClimaCred builds: deleted=%s modified=%s users=%s",
            summary["deleted"], summary["modified"], summary["affected_users"],
        )
    else:
        logger.info("No legacy demo data found in the database.")
    return summary


def user_data_counts(user_id: str = "default", db: Any = None) -> Dict[str, int]:
    database = _db(db)
    return {key: database[COLLECTIONS[key]].count_documents({"user_id": user_id}) for key in USER_DATA_COLLECTIONS}


def _main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect / remove legacy ClimaCred demo data from MongoDB.")
    parser.add_argument("--apply", action="store_true", help="remove legacy demo documents (default: read-only report)")
    parser.add_argument("--user", default="default", help="user_id to summarise (default: default)")
    args = parser.parse_args(list(argv) if argv is not None else None)

    from app.config import settings
    from app.database.mongodb import get_database, is_mock_db

    database = get_database()
    print(f"Database: {settings.MONGODB_DATABASE} @ {settings.MONGODB_URI} "
          f"({'in-memory mongomock - nothing persisted' if is_mock_db() else 'real MongoDB'})")
    print(f"Stored documents for user_id={args.user!r}: {json.dumps(user_data_counts(args.user, database))}")
    report = scan(database)
    print("Legacy demo scan:", json.dumps(report, indent=2, default=str))
    if args.apply:
        print("Purge result:", json.dumps(purge(database), indent=2, default=str))
    elif report["found"]:
        print("Run again with --apply to remove the legacy demo documents listed above.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
