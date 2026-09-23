from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from app.database.mongodb import get_collection
from app.database.collections import COLLECTIONS
import logging

logger = logging.getLogger(__name__)
DEFAULT_USER_ID = "default"

# For demo, we allow submitting impact data with before/after metrics

def calculate_impact_metrics(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    """
    before/after dicts contain: energy_kwh, water_litres, waste_kg, emissions_tonnes, cost_inr
    But flexibility: they may contain arbitrary metrics list
    """
    # If they pass metrics list, we handle that style
    # Expected API spec example:
    # Before: Energy=10000kWh, Water=80000L, Waste=2000kg
    # After: Energy=7200kWh etc.
    # Calculate absolute_change, percentage_change, estimated_impact
    results = {}
    metrics = []
    # Determine metric keys from before dict
    # before and after are dicts with same keys
    for key in before.keys():
        if key in ["_id","user_id","created_at","updated_at","notes","intervention_ids"]:
            continue
        b_val = before.get(key)
        a_val = after.get(key)
        if isinstance(b_val, (int,float)) and isinstance(a_val, (int,float)):
            abs_change = a_val - b_val
            pct_change = ((a_val - b_val)/b_val*100) if b_val !=0 else 0
            # estimated impact: reduction positive
            # Use terminology not verified carbon reduction
            verdict = ""
            if pct_change < -5:
                verdict = f"Observed {abs(pct_change):.1f}% reduction; estimated environmental impact favorable."
            elif pct_change > 5:
                verdict = f"Observed {pct_change:.1f}% increase; requires review."
            else:
                verdict = "No significant change observed."

            metrics.append({
                "metric": key,
                "before": b_val,
                "after": a_val,
                "absolute_change": round(abs_change,2),
                "percentage_change": round(pct_change,2),
                "estimated_impact": verdict,
                "terminology_note": "Use 'observed change' and 'estimated environmental impact', not 'verified carbon reduction' unless methodology supports it."
            })

    return {
        "metrics": metrics,
        "summary": f"Calculated {len(metrics)} metrics. Terminology: 'reported implementation outcome'."
    }

def create_impact_record(data: Dict[str, Any], user_id: str = DEFAULT_USER_ID) -> Dict[str, Any]:
    """
    data should contain: before (dict), after (dict), intervention_ids (optional), notes
    Also support alternative: metrics array with beforeValue/afterValue
    """
    col = get_collection(COLLECTIONS["impact_records"])

    before = data.get("before") or data.get("before_data") or {}
    after = data.get("after") or data.get("after_data") or {}

    # Handle metrics array format if provided directly
    # Frontend ImpactVerificationPage uses metrics list with beforeValue/afterValue
    # But POST /api/impact spec expects before/after structured
    # Support both: if data contains "metrics" list
    metrics_input = data.get("metrics")
    if metrics_input and isinstance(metrics_input, list):
        # Convert to before/after dict
        before = {}
        after = {}
        for m in metrics_input:
            key = m.get("id") or m.get("name") or m.get("metric")
            before[key] = m.get("beforeValue", m.get("before", 0))
            after[key] = m.get("afterValue", m.get("after", 0))

    # Also handle flat fields: if data directly has energy_before etc?
    # Check for alternative field naming
    if not before and not after:
        # Legacy: they may send flat with beforeValue etc per metric? Already captured
        # fallback: try to extract from data keys that contain _before and _after
        # e.g., energy_before, energy_after
        temp_before = {}
        temp_after = {}
        for k,v in data.items():
            if k.endswith("_before"):
                base = k[:-7]
                temp_before[base]=v
            elif k.endswith("_after"):
                base = k[:-6]
                temp_after[base]=v
        if temp_before:
            before = temp_before
            after = temp_after

    if not before or not after:
        raise ValueError("Both 'before' and 'after' data required for impact verification")

    calc = calculate_impact_metrics(before, after)

    doc = {
        "user_id": user_id,
        "before": before,
        "after": after,
        "intervention_ids": data.get("intervention_ids") or data.get("interventionIds") or data.get("selected_solution_ids") or [],
        "notes": data.get("notes", ""),
        "calculated_metrics": calc["metrics"],
        "summary": calc["summary"],
        "terminology": {
            "observed_change": "Use 'observed change' for delta.",
            "estimated_impact": "Use 'estimated environmental impact' for inferred benefit.",
            "reported_outcome": "Use 'reported implementation outcome' for user-supplied post data.",
            "disclaimer": "Not 'verified carbon reduction' unless data and methodology support verification."
        },
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }

    col.insert_one(doc)
    doc.pop("_id", None)
    for k in ["created_at","updated_at"]:
        if k in doc and hasattr(doc[k], "isoformat"):
            doc[k] = doc[k].isoformat()

    # Also transform to frontend ImpactVerificationMetric style if needed? Return raw
    return doc

def get_impact_records(user_id: str = DEFAULT_USER_ID, limit: int = 20) -> List[Dict[str, Any]]:
    col = get_collection(COLLECTIONS["impact_records"])
    cursor = col.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
    res = []
    for doc in cursor:
        doc.pop("_id", None)
        for k in ["created_at","updated_at"]:
            if k in doc and hasattr(doc[k], "isoformat"):
                doc[k] = doc[k].isoformat()
        res.append(doc)
    return res

def get_latest_impact_as_verification_metrics(user_id: str = DEFAULT_USER_ID) -> List[Dict[str, Any]]:
    """
    Returns list in frontend ImpactVerificationMetric format for backward compat:
    For demo, if no impact records, return static demo metrics derived from default before/after example
    """
    records = get_impact_records(user_id, limit=1)
    if not records:
        # Return demo default metrics (as in mockData)
        return [
            {
                "id": "imp-energy",
                "name": "Grid Electricity Consumption",
                "category": "Energy",
                "unit": "kWh / month",
                "unitLabel": "kWh",
                "beforeValue": 38500,
                "afterValue": 27720,
                "differenceValue": -10780,
                "differencePercent": -28.0,
                "impactVerdict": "28% load reduced via solar offset & VFD pump speed throttling.",
            },
            {
                "id": "imp-water",
                "name": "Freshwater Borewell Extraction",
                "category": "Water",
                "unit": "Litres / month",
                "unitLabel": "Litres",
                "beforeValue": 480000,
                "afterValue": 196800,
                "differenceValue": -283200,
                "differencePercent": -59.0,
                "impactVerdict": "59% groundwater conserved with closed-loop ultrafiltration & leak repair.",
            },
            {
                "id": "imp-waste",
                "name": "Landfill-Destined Material Scrap",
                "category": "Waste",
                "unit": "kg / month",
                "unitLabel": "kg",
                "beforeValue": 3600,
                "afterValue": 1440,
                "differenceValue": -2160,
                "differencePercent": -60.0,
                "impactVerdict": "2.16 tonnes/mo yarn scrap diverted to circular recycled yarn spinning.",
            },
            {
                "id": "imp-emissions",
                "name": "Total Scope 1 & 2 Emissions",
                "category": "Emissions",
                "unit": "MT CO₂e / month",
                "unitLabel": "MT CO₂e",
                "beforeValue": 41.2,
                "afterValue": 23.9,
                "differenceValue": -17.3,
                "differencePercent": -42.0,
                "impactVerdict": "17.3 MT CO₂e monthly reduction from clean solar + boiler economizer.",
            },
            {
                "id": "imp-cost",
                "name": "Net Monthly Operational Utility Cost",
                "category": "Financial",
                "unit": "₹ / month",
                "unitLabel": "₹",
                "beforeValue": 512000,
                "afterValue": 338000,
                "differenceValue": -174000,
                "differencePercent": -34.0,
                "impactVerdict": "₹1.74 Lakh monthly utility cost saving (₹20.8 Lakh annualized).",
            },
        ]
    # If we have records, convert latest record to metrics
    latest = records[0]
    metrics = []
    before = latest.get("before", {})
    after = latest.get("after", {})
    calc_metrics = latest.get("calculated_metrics", [])
    # Map to frontend structure if possible
    # Try to produce friendly categories
    category_map = {
        "energy": "Energy",
        "energy_kwh": "Energy",
        "water": "Water",
        "water_litres": "Water",
        "waste": "Waste",
        "waste_kg": "Waste",
        "emissions": "Emissions",
        "emissions_tonnes": "Emissions",
        "cost": "Financial",
        "cost_inr": "Financial",
        "fuel": "Mobility"
    }
    for cm in calc_metrics:
        metric_key = cm["metric"]
        # Guess category
        cat = "Operations"
        for k, v in category_map.items():
            if k in metric_key.lower():
                cat = v
                break
        # Unit handling
        unit_map = {
            "energy": "kWh / month",
            "water": "Litres / month",
            "waste": "kg / month",
            "emissions": "MT CO₂e / month",
            "cost": "₹ / month",
            "fuel": "L / month"
        }
        unit = "units"
        for k, v in unit_map.items():
            if k in metric_key.lower():
                unit = v
                break
        before_val = cm["before"]
        after_val = cm["after"]
        diff = cm["absolute_change"]
        pct = cm["percentage_change"]
        metrics.append({
            "id": f"imp-{metric_key}",
            "name": metric_key.replace("_"," ").title(),
            "category": cat,
            "unit": unit,
            "unitLabel": unit.split(" ")[0],
            "beforeValue": before_val,
            "afterValue": after_val,
            "differenceValue": diff,
            "differencePercent": pct,
            "impactVerdict": cm["estimated_impact"]
        })
    return metrics
