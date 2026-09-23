"""
Climate Fingerprint Engine
Aggregates dimension scores, calculates overall Climate Readiness, identifies high-impact areas, generates explanations
"""
from typing import Dict, Any, List
from datetime import datetime, timezone
from app.config import settings
from app.climate_engine.scoring import (
    score_energy, score_water, score_waste, score_emissions, score_mobility, score_operations,
    impact_level_from_score
)
from app.utils.calculations import calculate_data_quality_score

WEIGHTS = {
    "Energy": settings.WEIGHT_ENERGY,
    "Water": settings.WEIGHT_WATER,
    "Waste": settings.WEIGHT_WASTE,
    "Emissions": settings.WEIGHT_EMISSIONS,
    "Mobility": settings.WEIGHT_MOBILITY,
    "Operations": settings.WEIGHT_OPERATIONS,
}

def calculate_overall_score(dimensions: List[Dict[str, Any]]) -> float:
    total = 0.0
    for dim in dimensions:
        w = WEIGHTS.get(dim["dimension"], 0)
        total += dim["score"] * w
    return round(total, 1)

def score_label_from_overall(score: float) -> str:
    if score >= 80:
        return "Leadership Stage"
    elif score >= 65:
        return "Accelerated Stage"
    elif score >= 45:
        return "Transition Stage"
    else:
        return "At-Risk Stage"

def generate_fingerprint(profile: Dict[str, Any], assessment: Dict[str, Any]) -> Dict[str, Any]:
    # Calculate each dimension
    energy_dim = score_energy(assessment, profile)
    water_dim = score_water(assessment, profile)
    waste_dim = score_waste(assessment, profile)
    emissions_dim = score_emissions(assessment, profile)
    mobility_dim = score_mobility(assessment, profile)
    operations_dim = score_operations(assessment, profile)

    dimensions = [energy_dim, water_dim, waste_dim, emissions_dim, mobility_dim, operations_dim]

    # Overall
    overall = calculate_overall_score(dimensions)
    label = score_label_from_overall(overall)

    # Top improvement dimensions: sort by score ascending (worst first) where impact High/Very High
    sorted_dims = sorted(dimensions, key=lambda x: x["score"])
    top_improvement = [d["dimension"] for d in sorted_dims[:3] ]

    # Benchmark percentile (mock: derive from overall vs typical)
    # For textile medium benchmark, avg 58, percentile = overall *0.8 approx
    benchmark_percentile = max(5, min(95, int(overall * 0.85 + 5)))

    # Summary note generation (transparent, not generic)
    # Identify worst dimension
    worst = sorted_dims[0]
    second = sorted_dims[1] if len(sorted_dims)>1 else None
    if worst["impact_level"] in ["Very High","High"]:
        summary = f"Your business has significant improvement opportunities primarily in {', '.join(top_improvement[:2])}. "
        summary += f"{worst['dimension']} is the highest priority because {worst['primary_cause'].lower()}. "
        if second:
            summary += f"{second['dimension']} follows with {second['primary_cause'].lower()}. "
        summary += f"Implementing targeted interventions can raise your Climate Readiness to {min(94, int(overall+26))}+."
    else:
        summary = f"Your business demonstrates balanced resource performance. Highest incremental gain in {worst['dimension']} ({worst['improvement_opportunity'].lower()}). Overall readiness at {label.lower()} indicates ongoing maturity."

    # Data quality
    dq = calculate_data_quality_score(profile, assessment)

    # Confidence overall: avg of dimensions confidence mapping
    conf_map = {"High": 3, "Medium": 2, "Low": 1}
    avg_conf_val = sum(conf_map.get(d.get("confidence","Medium"),2) for d in dimensions)/len(dimensions)
    if avg_conf_val >= 2.6:
        overall_conf = "High"
    elif avg_conf_val >= 1.8:
        overall_conf = "Medium"
    else:
        overall_conf = "Low"

    # Build fingerprint dimensions for API response shape expected by frontend
    # Frontend expects: dimension, score, impactLevel, currentStatus, primaryCause, improvementOpportunity, potentialReduction
    frontend_dims = []
    for d in dimensions:
        frontend_dims.append({
            "dimension": d["dimension"],
            "score": d["score"],
            "impactLevel": d["impact_level"],
            "impact_level": d["impact_level"],
            "currentStatus": d["current_status"],
            "current_status": d["current_status"],
            "primaryCause": d["primary_cause"],
            "primary_cause": d["primary_cause"],
            "improvementOpportunity": d["improvement_opportunity"],
            "improvement_opportunity": d["improvement_opportunity"],
            "potentialReduction": d["potential_reduction"],
            "potential_reduction": d["potential_reduction"],
            "confidence": d["confidence"],
            "metrics_used": d.get("metrics_used", {})
        })

    fingerprint = {
        "overallScore": overall,
        "overall_score": overall,
        "scoreLabel": label,
        "score_label": label,
        "dimensions": frontend_dims,
        "topImprovementDimensions": top_improvement,
        "top_improvement_dimensions": top_improvement,
        "summaryNote": summary,
        "summary_note": summary,
        "benchmarkPercentile": benchmark_percentile,
        "benchmark_percentile": benchmark_percentile,
        "weights_used": WEIGHTS,
        "data_quality": dq,
        "confidence": overall_conf,
        "methodology": {
            "description": "Decision-support metric, not an official environmental certification.",
            "weights": WEIGHTS,
            "scoring_range": "0-100 per dimension, 100=best. Overall weighted sum.",
            "impact_levels": "Low 80-100, Moderate 65-79, High 40-64, Very High 0-39",
            "calculation_version": settings.CALCULATION_VERSION,
            "disclaimer": "Scores derived from submitted business data using transparent transparent assumptions. Not a government certification."
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "calculation_version": settings.CALCULATION_VERSION
    }

    return fingerprint

def fingerprint_to_mongo_doc(fingerprint: Dict[str, Any], user_id: str = "default") -> Dict[str, Any]:
    doc = fingerprint.copy()
    doc["user_id"] = user_id
    doc["created_at"] = datetime.now(timezone.utc)
    doc["updated_at"] = datetime.now(timezone.utc)
    return doc
