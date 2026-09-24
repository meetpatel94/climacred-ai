from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import uuid
from app.database.mongodb import get_collection
from app.database.collections import COLLECTIONS
from app.services.profile_service import get_profile
from app.services.assessment_service import get_assessment, has_assessment_data, has_business_data
from app.services.fingerprint_service import get_latest_fingerprint, generate_and_save_fingerprint
from app.services.transformation_service import get_transformation_plan
from app.services.impact_service import get_impact_records, get_latest_impact_as_verification_metrics
from app.services.solution_service import get_personalized_recommendations
from app.utils.calculations import calculate_energy_metrics, calculate_water_metrics, calculate_waste_metrics, calculate_emissions_metrics, calculate_mobility_metrics, calculate_data_quality_score
from app.climate_engine.simulations import simulate_scenarios
from app.config import settings

DEFAULT_USER_ID = "default"

def generate_climate_report(user_id: str = DEFAULT_USER_ID, include_scenario: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    profile = get_profile(user_id)
    assessment = get_assessment(user_id)
    if not profile or not has_assessment_data(assessment):
        # A report can only describe data that actually exists.
        raise ValueError(
            "No business climate data stored yet. Add your business data and complete the Climate Assessment before generating a report."
        )
    fingerprint = get_latest_fingerprint(user_id)
    if not fingerprint:
        fingerprint = generate_and_save_fingerprint(user_id)

    energy_analysis = calculate_energy_metrics(assessment, profile)
    water_analysis = calculate_water_metrics(assessment, profile)
    waste_analysis = calculate_waste_metrics(assessment)
    emissions_analysis = calculate_emissions_metrics(assessment)
    mobility_analysis = calculate_mobility_metrics(assessment)
    data_quality = calculate_data_quality_score(profile, assessment)
    recommendations = get_personalized_recommendations(user_id=user_id, top_n=5)
    transformation_plan = get_transformation_plan(user_id)
    impact_records = get_impact_records(user_id, limit=5)
    impact_verification = get_latest_impact_as_verification_metrics(user_id)

    # Scenario analysis: if not provided, simulate top 2 recommendations
    if include_scenario:
        scenario_analysis = include_scenario
    else:
        top_ids = [r["solution_id"] for r in recommendations[:2]]
        if top_ids:
            scenario_analysis = simulate_scenarios(top_ids, profile, assessment, adoption_scale_percent=100)
        else:
            scenario_analysis = None

    # Determine top priorities from fingerprint
    top_priorities = fingerprint.get("topImprovementDimensions") or fingerprint.get("top_improvement_dimensions") or []

    # Methodology & assumptions
    assumptions = [
        "Energy emissions factor configurable, not certified (default India 0.82 kg CO2/kWh).",
        "Water savings based on configurable recycling factor 65% + leakage factor; capped 70%.",
        "Waste recovery assumed 66% for textile off-cut; material reuse 18% theoretical.",
        "Emissions estimated using DEFRA/IPCC-derived factors stored with calculation; not official carbon accounting.",
        "Mobility emission factor depends on fuel type; EV saving assumes 30% reduction on non-EV fleet.",
        "Projected savings are estimated, not guaranteed; require site audit.",
        "Climate Readiness is decision-support metric, not official certification.",
    ]
    # Add fingerprint methodology
    methodology = fingerprint.get("methodology", {})
    methodology.update({
        "weights": fingerprint.get("weights_used"),
        "calculation_version": settings.CALCULATION_VERSION,
        "data_quality": data_quality,
        "distinct_data_types": {
            "measured_data": "Directly submitted business profile and assessment inputs (e.g., monthly kWh, litres).",
            "calculated_values": "Deterministic derivations (annual = monthly*12, emissions = activity * factor).",
            "estimated_values": "Potential savings, environmental impacts, payback based on catalog assumptions.",
            "assumptions": "Configurable factors documented per calculation.",
            "ai_insights": "Narrative summaries generated from scoring logic, not ML black box."
        }
    })

    report = {
        "report_id": f"CC-{datetime.now(timezone.utc).year}-TX-{str(uuid.uuid4())[:4].upper()}",
        "reportId": f"CC-{datetime.now(timezone.utc).year}-TX-{str(uuid.uuid4())[:4].upper()}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "data_period": f"{profile.get('business_name','Business')} - Assessment as of {datetime.now(timezone.utc).strftime('%B %Y')}",
        "dataPeriod": f"Assessment as of {datetime.now(timezone.utc).strftime('%B %Y')}",
        "calculation_version": settings.CALCULATION_VERSION,
        "calculationVersion": settings.CALCULATION_VERSION,
        "business_profile": profile,
        "businessProfile": profile,
        "climate_readiness": {
            "overall_score": fingerprint.get("overallScore") or fingerprint.get("overall_score"),
            "score_label": fingerprint.get("scoreLabel") or fingerprint.get("score_label"),
            "benchmark_percentile": fingerprint.get("benchmarkPercentile") or fingerprint.get("benchmark_percentile"),
            "confidence": fingerprint.get("confidence")
        },
        "climateReadiness": {
            "overallScore": fingerprint.get("overallScore") or fingerprint.get("overall_score"),
            "scoreLabel": fingerprint.get("scoreLabel") or fingerprint.get("score_label")
        },
        "climate_fingerprint": fingerprint,
        "climateFingerprint": fingerprint,
        "energy_analysis": energy_analysis,
        "energyAnalysis": energy_analysis,
        "water_analysis": water_analysis,
        "waterAnalysis": water_analysis,
        "waste_analysis": waste_analysis,
        "wasteAnalysis": waste_analysis,
        "emissions_analysis": emissions_analysis,
        "emissionsAnalysis": emissions_analysis,
        "mobility_analysis": mobility_analysis,
        "mobilityAnalysis": mobility_analysis,
        "top_priorities": top_priorities,
        "topPriorities": top_priorities,
        "recommended_solutions": recommendations,
        "recommendedSolutions": recommendations,
        "scenario_analysis": scenario_analysis,
        "scenarioAnalysis": scenario_analysis,
        "transformation_plan": transformation_plan,
        "transformationPlan": transformation_plan,
        "impact_verification": impact_verification,
        "impactVerification": impact_verification,
        "impact_records": impact_records,
        "assumptions": assumptions,
        "methodology": methodology,
        "data_quality": data_quality,
        "dataQuality": data_quality,
        "disclaimers": [
            "Measured vs calculated vs estimated values are distinguished throughout.",
            "No government certification or carbon credits claimed.",
            "Financial savings are estimates, not guarantees.",
            "Emission metrics retain calculation inputs (factor, unit, source_label, timestamp) for transparency."
        ]
    }

    # Save to DB
    col = get_collection(COLLECTIONS["climate_reports"])
    doc = {
        "user_id": user_id,
        **report,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "generated_at_dt": datetime.now(timezone.utc)
    }
    # Ensure generated_at is iso string for doc already; keep datetime backup
    doc["generated_at"] = report["generated_at"]
    try:
        col.insert_one(doc)
    except:
        pass

    return report

def get_latest_report(user_id: str = DEFAULT_USER_ID) -> Optional[Dict[str, Any]]:
    # Reports embed the business profile. A stored report must never resurface
    # after the profile/assessment it describes was deleted.
    if not has_business_data(user_id):
        return None
    col = get_collection(COLLECTIONS["climate_reports"])
    doc = col.find_one({"user_id": user_id}, sort=[("created_at", -1)])
    if not doc:
        return None
    d = dict(doc)
    d.pop("_id", None)
    for k in ["created_at","updated_at","generated_at_dt"]:
        if k in d and hasattr(d[k], "isoformat"):
            d[k] = d[k].isoformat()
    return d

def get_report_history(user_id: str = DEFAULT_USER_ID, limit: int = 10) -> List[Dict[str, Any]]:
    if not has_business_data(user_id):
        return []
    col = get_collection(COLLECTIONS["climate_reports"])
    cursor = col.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
    res = []
    for doc in cursor:
        doc.pop("_id", None)
        for k in ["created_at","updated_at","generated_at_dt"]:
            if k in doc and hasattr(doc[k], "isoformat"):
                doc[k] = doc[k].isoformat()
        res.append(doc)
    return res
