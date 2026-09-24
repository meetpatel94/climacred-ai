from typing import List, Dict, Any
from datetime import datetime, timezone
from app.database.mongodb import get_collection
from app.database.collections import COLLECTIONS
from app.services.profile_service import get_profile
from app.services.assessment_service import get_assessment, has_assessment_data
from app.services.fingerprint_service import get_latest_fingerprint, generate_and_save_fingerprint
from app.services.solution_service import get_personalized_recommendations
from app.climate_engine.recommendations import SOLUTION_CATALOG

DEFAULT_USER_ID = "default"

# Phase definitions
PHASES = [
    {"phase": "Phase 1", "phaseName": "Immediate Low-Hanging Actions (Month 1-3)", "timeline": "Month 1 - 3"},
    {"phase": "Phase 2", "phaseName": "System Efficiency Improvements (Month 4-7)", "timeline": "Month 4 - 7"},
    {"phase": "Phase 3", "phaseName": "Capital Green Investments (Month 8-14)", "timeline": "Month 8 - 14"},
    {"phase": "Phase 4", "phaseName": "Impact Verification & Continuous Intelligence (Month 15+)", "timeline": "Month 15 onwards"},
]

# Map solutions to phases and priority based on payback and impact
SOLUTION_PHASE_MAP = {
    "sol-leak-sensors": {"phase": "Phase 1", "priority": "High"},
    "sol-route-opt": {"phase": "Phase 1", "priority": "Medium"},
    "sol-waste-recovery": {"phase": "Phase 1", "priority": "High"},
    "sol-led-iot": {"phase": "Phase 1", "priority": "Medium"},
    "sol-machinery-vfd": {"phase": "Phase 2", "priority": "High"},
    "sol-heat-recovery": {"phase": "Phase 2", "priority": "Medium"},
    "sol-smart-metering": {"phase": "Phase 2", "priority": "Medium"},
    "sol-solar": {"phase": "Phase 3", "priority": "High"},
    "sol-water-ro": {"phase": "Phase 3", "priority": "High"},
    "sol-rainwater": {"phase": "Phase 2", "priority": "Medium"},
    "sol-ev-fleet": {"phase": "Phase 3", "priority": "Medium"},
    "sol-material-reuse": {"phase": "Phase 3", "priority": "Medium"},
}

def _get_solution_title(sol_id: str) -> str:
    for s in SOLUTION_CATALOG:
        if s["id"] == sol_id:
            return s["title"]
    return sol_id

def _get_solution(sol_id: str):
    for s in SOLUTION_CATALOG:
        if s["id"] == sol_id:
            return s
    return None

def generate_transformation_plan(user_id: str = DEFAULT_USER_ID) -> List[Dict[str, Any]]:
    # Use fingerprint + recommendations to prioritize
    profile = get_profile(user_id)
    assessment = get_assessment(user_id)
    if not profile or not has_assessment_data(assessment):
        # No stored business data => no personalised roadmap (empty, not fabricated).
        return []
    recs = get_personalized_recommendations(user_id=user_id, top_n=8)
    fingerprint = get_latest_fingerprint(user_id)
    if not fingerprint:
        try:
            fingerprint = generate_and_save_fingerprint(user_id)
        except ValueError:
            return []

    # Sort recs by score already; map to plan items
    plan_items: List[Dict[str, Any]] = []
    used_sol_ids = set()

    # First, create plan items from top recommendations
    for idx, rec in enumerate(recs):
        sol = rec["solution"]
        sol_id = sol["id"]
        used_sol_ids.add(sol_id)
        mapping = SOLUTION_PHASE_MAP.get(sol_id, {"phase": "Phase 2", "priority": rec["priority"]})
        phase_def = next((p for p in PHASES if p["phase"]==mapping["phase"]), PHASES[0])
        # Derive cost and benefit strings
        cost_label = sol["investment_range"] or sol.get("investmentRange", f"₹{sol['investmentMinInr']/100000:.1f}L – ₹{sol['investmentMaxInr']/100000:.1f}L")
        benefit = f"Save ₹{sol['potentialAnnualSavingsInr']/100000:.1f}L/yr • {sol['resourceReductionValue']} • {sol['co2ReductionTonnesPerYear']} MT CO₂e/yr"
        plan_items.append({
            "id": f"tp-{idx+1}",
            "action": sol["title"],
            "title": sol["title"],
            "phase": mapping["phase"],
            "phaseName": phase_def["phaseName"],
            "priority": mapping["priority"],
            "estimatedCost": cost_label,
            "estimated_cost": cost_label,
            "estimated_cost_min_inr": sol["investmentMinInr"],
            "estimated_cost_max_inr": sol["investmentMaxInr"],
            "expectedBenefit": benefit,
            "expected_benefit": benefit,
            "timeframe": phase_def["timeline"],
            "timeline": phase_def["timeline"],
            "status": "Pending" if idx>1 else ("In Progress" if idx==1 else "Pending"),
            "category": sol["category"],
            "reason": rec["reason"],
            "solution_id": sol_id,
            "confidence": rec["confidence"],
            "assumptions": sol.get("assumptions", [])
        })

    # Always ensure Phase 4 impact verification item exists
    has_phase4 = any(item["phase"]=="Phase 4" for item in plan_items)
    if not has_phase4:
        plan_items.append({
            "id": f"tp-{len(plan_items)+1}",
            "action": "IoT Sub-Meter Telemetry Calibration & Third-Party Audit Verification",
            "title": "IoT Sub-Meter Telemetry Calibration & Third-Party Audit Verification",
            "phase": "Phase 4",
            "phaseName": "Impact Verification & Continuous Intelligence (Month 15+)",
            "priority": "Medium",
            "estimatedCost": "₹1,80,000",
            "estimated_cost": "₹1,80,000",
            "estimated_cost_min_inr": 180000,
            "estimated_cost_max_inr": 180000,
            "expectedBenefit": "Validate annual CO₂ reduction for ESG compliance & buyer audits",
            "expected_benefit": "Validate annual CO₂ reduction for ESG compliance & buyer audits",
            "timeframe": "Month 15 onwards",
            "timeline": "Month 15 onwards",
            "status": "Pending",
            "category": "Operations",
            "reason": "Verification ensures reported implementation outcomes are auditable and not overstated as certified credits.",
            "solution_id": "verification",
            "confidence": "High",
            "assumptions": ["Assumes commissioned interventions have 3 months stable operation before audit"]
        })

    # Sort by phase order then priority
    phase_order = {"Phase 1":0, "Phase 2":1, "Phase 3":2, "Phase 4":3}
    priority_order = {"High":0, "Medium":1, "Low":2}
    plan_items.sort(key=lambda x: (phase_order.get(x["phase"],99), priority_order.get(x["priority"],99)))

    # Reassign IDs sequentially after sort to preserve UI expectations? Keep original ids but okay
    for idx, item in enumerate(plan_items):
        item["id"] = f"tp-{idx+1}"
        item["order"] = idx+1

    # Save to DB
    col = get_collection(COLLECTIONS["transformation_plans"])
    col.delete_many({"user_id": user_id})
    doc = {
        "user_id": user_id,
        "plan_items": plan_items,
        "generated_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "based_on_fingerprint": fingerprint.get("overallScore") if fingerprint else None,
        "calculation_version": "v1.0.0"
    }
    try:
        col.insert_one(doc)
    except:
        pass

    return plan_items

def get_transformation_plan(user_id: str = DEFAULT_USER_ID) -> List[Dict[str, Any]]:
    col = get_collection(COLLECTIONS["transformation_plans"])
    doc = col.find_one({"user_id": user_id}, sort=[("updated_at", -1)])
    if not doc:
        # generate
        return generate_transformation_plan(user_id)
    items = doc.get("plan_items", [])
    # Ensure _id not leaking
    return items

def update_plan_item_status(item_id: str, status: str, user_id: str = DEFAULT_USER_ID) -> List[Dict[str, Any]]:
    if status not in ["Pending","In Progress","Completed"]:
        raise ValueError("Invalid status")
    col = get_collection(COLLECTIONS["transformation_plans"])
    doc = col.find_one({"user_id": user_id}, sort=[("updated_at", -1)])
    if not doc:
        raise ValueError("No transformation plan found. Generate one first.")
    items = doc.get("plan_items", [])
    found = False
    for it in items:
        if it["id"] == item_id:
            it["status"] = status
            found = True
            break
    if not found:
        raise ValueError(f"Plan item {item_id} not found")
    # Update doc
    col.update_one({"_id": doc["_id"]}, {"$set": {"plan_items": items, "updated_at": datetime.now(timezone.utc)}})
    return items
