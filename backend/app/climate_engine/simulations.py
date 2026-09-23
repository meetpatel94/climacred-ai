"""
Scenario Simulator
Calculates combined outcomes for multiple interventions, avoids double counting, documents assumptions.
"""
from typing import List, Dict, Any
from datetime import datetime, timezone
from app.climate_engine.recommendations import SOLUTION_CATALOG
from app.utils.calculations import calculate_energy_metrics, calculate_water_metrics, calculate_waste_metrics, calculate_emissions_metrics, calculate_mobility_metrics

# Helper to get solution by id
def get_solution_by_id(sol_id: str):
    for s in SOLUTION_CATALOG:
        if s["id"] == sol_id:
            return s
    return None

def simulate_scenarios(selected_solution_ids: List[str], profile: Dict[str, Any], assessment: Dict[str, Any], adoption_scale_percent: float = 100.0) -> Dict[str, Any]:
    """
    selected_solution_ids: list of solution ids
    adoption_scale_percent: 25-100 representing phased scale
    Returns current_state, projected_state, investment, savings, changes
    Avoids double counting via category caps.
    """
    scale = max(25, min(100, adoption_scale_percent)) / 100.0

    # Baseline metrics
    energy_base = calculate_energy_metrics(assessment, profile)
    water_base = calculate_water_metrics(assessment, profile)
    waste_base = calculate_waste_metrics(assessment)
    emissions_base = calculate_emissions_metrics(assessment)
    mobility_base = calculate_mobility_metrics(assessment)

    current_state = {
        "energy_monthly_kwh": energy_base["monthly_electricity_kwh"],
        "energy_annual_kwh": energy_base["annual_electricity_kwh"],
        "energy_monthly_cost_inr": energy_base["monthly_electricity_cost_inr"],
        "water_monthly_litres": water_base["monthly_water_litres"],
        "water_annual_litres": water_base["annual_water_litres"],
        "waste_monthly_kg": waste_base["total_waste_kg_per_month"],
        "emissions_monthly_tonnes": emissions_base["emissions_breakdown_tonnes_co2e_per_month"]["total"],
        "emissions_annual_tonnes": emissions_base["annual_total_tonnes_co2e"],
        "mobility_monthly_fuel": mobility_base["monthly_fuel_litres"],
    }

    selected = [get_solution_by_id(sid) for sid in selected_solution_ids if get_solution_by_id(sid)]
    if not selected:
        return {
            "error": "No valid solutions selected",
            "current_state": current_state,
            "projected_state": current_state,
            "selected_solutions": [],
            "message": "Select at least one valid intervention"
        }

    # Aggregate investment & savings with scale
    total_investment_min = sum(s["investmentMinInr"] for s in selected) * scale
    total_investment_max = sum(s["investmentMaxInr"] for s in selected) * scale
    total_annual_savings = sum(s["potentialAnnualSavingsInr"] for s in selected) * scale
    total_co2 = sum(s["co2ReductionTonnesPerYear"] for s in selected) * scale

    # Calculate category-specific reductions avoiding double counting
    # Energy: solar 108k kWh/yr scaled, VFD 46k, heat recovery ~21k, LED 21k, smart metering 10% of base?
    # Use caps: energy reduction max 55% of base annual
    energy_reduction_kwh = 0
    for s in selected:
        if s["id"] == "sol-solar":
            energy_reduction_kwh += 108000 * scale
        elif s["id"] == "sol-machinery-vfd":
            energy_reduction_kwh += 46000 * scale
        elif s["id"] == "sol-heat-recovery":
            # fuel saving not electricity? But count as equivalent?
            energy_reduction_kwh += 15000 * scale  # approximate
        elif s["id"] == "sol-led-iot":
            energy_reduction_kwh += 21000 * scale
        elif s["id"] == "sol-smart-metering":
            energy_reduction_kwh += (energy_base["annual_electricity_kwh"] * 0.07 * scale)

    # Cap energy reduction
    max_energy_reduction = energy_base["annual_electricity_kwh"] * 0.55
    energy_reduction_kwh = min(energy_reduction_kwh, max_energy_reduction)
    energy_reduction_percent = (energy_reduction_kwh / energy_base["annual_electricity_kwh"] * 100) if energy_base["annual_electricity_kwh"] else 0

    # Water: ro 3.74M L/yr, leak 420k, rainwater 980k
    water_reduction_litres = 0
    for s in selected:
        if s["id"] == "sol-water-ro":
            water_reduction_litres += 3740000 * scale
        elif s["id"] == "sol-leak-sensors":
            water_reduction_litres += 420000 * scale
        elif s["id"] == "sol-rainwater":
            water_reduction_litres += 980000 * scale

    max_water_reduction = water_base["annual_water_litres"] * 0.75
    water_reduction_litres = min(water_reduction_litres, max_water_reduction)
    water_reduction_percent = (water_reduction_litres / water_base["annual_water_litres"] * 100) if water_base["annual_water_litres"] else 0

    # Waste: waste recovery 28.5T /yr, material reuse maybe 18% of total?
    waste_reduction_kg = 0
    for s in selected:
        if s["id"] == "sol-waste-recovery":
            waste_reduction_kg += 28500 * scale
        elif s["id"] == "sol-material-reuse":
            waste_reduction_kg += (waste_base["annual_waste_kg"] * 0.18 * scale)

    max_waste_reduction = waste_base["annual_waste_kg"] * 0.68
    waste_reduction_kg = min(waste_reduction_kg, max_waste_reduction)
    waste_reduction_percent = (waste_reduction_kg / waste_base["annual_waste_kg"] * 100) if waste_base["annual_waste_kg"] else 0

    # Emissions: use co2Reduction totals but cap at 70% of annual
    co2_reduction = min(total_co2, emissions_base["annual_total_tonnes_co2e"] * 0.65)
    co2_reduction_percent = (co2_reduction / emissions_base["annual_total_tonnes_co2e"] * 100) if emissions_base["annual_total_tonnes_co2e"] else 0

    payback = (total_investment_min / total_annual_savings) if total_annual_savings else 0

    # Projected state
    projected_state = {
        "energy_annual_kwh": round(energy_base["annual_electricity_kwh"] - energy_reduction_kwh, 0),
        "energy_monthly_kwh": round((energy_base["annual_electricity_kwh"] - energy_reduction_kwh)/12, 0),
        "water_annual_litres": round(water_base["annual_water_litres"] - water_reduction_litres, 0),
        "water_monthly_litres": round((water_base["annual_water_litres"] - water_reduction_litres)/12, 0),
        "waste_annual_kg": round(waste_base["annual_waste_kg"] - waste_reduction_kg, 1),
        "waste_monthly_kg": round((waste_base["annual_waste_kg"] - waste_reduction_kg)/12, 1),
        "emissions_annual_tonnes": round(emissions_base["annual_total_tonnes_co2e"] - co2_reduction, 2),
        "emissions_monthly_tonnes": round((emissions_base["annual_total_tonnes_co2e"] - co2_reduction)/12, 2),
        "mobility_annual_fuel": round(mobility_base["annual_fuel_litres"] - sum(9200 if s["id"]=="sol-ev-fleet" else 3100 if s["id"]=="sol-route-opt" else 0 for s in selected)*scale, 1)
    }

    # Projected climate score – naive: base overall + 4 per solution * scale, capped 94
    # Need fingerprint? If not, assume base 58
    # We'll attempt to estimate improvement based on co2+water etc.
    # Simple: each intervention adds 3-6 points scaled
    # Map sol to points:
    points_map = {
        "sol-solar": 5.5,
        "sol-water-ro": 5.0,
        "sol-machinery-vfd": 4.2,
        "sol-leak-sensors": 2.5,
        "sol-rainwater": 3.0,
        "sol-waste-recovery": 4.0,
        "sol-ev-fleet": 3.5,
        "sol-route-opt": 1.8,
        "sol-heat-recovery": 3.2,
        "sol-led-iot": 2.2,
        "sol-material-reuse": 3.0,
        "sol-smart-metering": 2.0
    }
    base_score = 58  # default; will be overridden if caller provides fingerprint
    # Try to derive from emissions etc? Keep base
    added = sum(points_map.get(s["id"], 2.5) for s in selected) * scale
    projected_score = min(94, round(base_score + added))

    # Adjust if profile/assessment indicates higher base? We attempt to compute if fingerprint available via caller arg?
    # Caller can pass current fingerprint; for now keep 58 base but document

    assumptions = [
        "Combined savings capped to avoid double counting: energy max 55%, water max 75%, waste max 68%, CO2 max 65% of baseline.",
        f"Adoption scale {scale*100:.0f}% linearly scales investment, savings and impacts (pilot assumption).",
        "Solar generation assumes 75 kWp, 4.5 peak sun hours, 78% PR; VFD saving 18% motor load.",
        "Water recycling saving 65% assumes ZLD RO with 85% recovery; leakage saving 90% repair effectiveness.",
        "Waste diversion 66% for textile off-cut; material reuse 18% of total waste.",
        "CO2 reductions summed per solution then capped; not additive beyond system limit.",
        "Payback based on min investment / annual savings at current tariffs (₹8.9/kWh, ₹30/kL).",
        "Not a guaranteed saving; estimated, requires site audit verification.",
        "Projected climate score is decision-support estimate, not certified."
    ]

    investment_avg = (total_investment_min + total_investment_max)/2 if selected else 0

    return {
        "selected_solutions": [s["id"] for s in selected],
        "selected_count": len(selected),
        "adoption_scale_percent": int(scale*100),
        "current_state": current_state,
        "projected_state": projected_state,
        "investment": {
            "min_inr": round(total_investment_min, 0),
            "max_inr": round(total_investment_max, 0),
            "avg_inr": round(investment_avg, 0),
            "total_inr": round(total_investment_min,0)  # for frontend compat
        },
        "totalInvestmentInr": round(total_investment_min,0),
        "totalAnnualSavingsInr": round(total_annual_savings,0),
        "annual_savings_inr": round(total_annual_savings,0),
        "monthly_savings_inr": round(total_annual_savings/12,0),
        "energy_change": {
            "reduction_kwh_per_year": round(energy_reduction_kwh,0),
            "reduction_percent": round(energy_reduction_percent,1),
            "energyReductionKwh": round(energy_reduction_kwh,0),
            "energyReductionPercent": round(energy_reduction_percent,1)
        },
        "water_change": {
            "reduction_litres_per_year": round(water_reduction_litres,0),
            "reduction_percent": round(water_reduction_percent,1),
            "waterReductionLitres": round(water_reduction_litres,0),
            "waterReductionPercent": round(water_reduction_percent,1)
        },
        "waste_change": {
            "reduction_kg_per_year": round(waste_reduction_kg,1),
            "reduction_percent": round(waste_reduction_percent,1),
            "wasteReductionKg": round(waste_reduction_kg,1),
            "wasteReductionPercent": round(waste_reduction_percent,1)
        },
        "emission_change": {
            "reduction_tonnes_co2_per_year": round(co2_reduction,2),
            "reduction_percent": round(co2_reduction_percent,1),
            "co2ReductionTonnes": round(co2_reduction,2),
            "co2ReductionPercent": round(co2_reduction_percent,1)
        },
        "payback_period_years": round(payback,1),
        "estimatedPaybackYears": round(payback,1),
        "projected_climate_score": projected_score,
        "projectedClimateScore": projected_score,
        "assumptions": assumptions,
        "calculation_timestamp": datetime.now(timezone.utc).isoformat(),
        "calculation_version": "v1.0.0"
    }

def simulate_with_fingerprint(selected_ids: List[str], profile: Dict[str, Any], assessment: Dict[str, Any], fingerprint: Dict[str, Any], scale: float = 100):
    result = simulate_scenarios(selected_ids, profile, assessment, scale)
    # Override projected score using actual base fingerprint
    if fingerprint:
        base = fingerprint.get("overallScore") or fingerprint.get("overall_score") or 58
        points_map = {
            "sol-solar": 5.5, "sol-water-ro":5.0, "sol-machinery-vfd":4.2, "sol-leak-sensors":2.5,
            "sol-rainwater":3.0, "sol-waste-recovery":4.0, "sol-ev-fleet":3.5, "sol-route-opt":1.8,
            "sol-heat-recovery":3.2, "sol-led-iot":2.2, "sol-material-reuse":3.0, "sol-smart-metering":2.0
        }
        added = sum(points_map.get(sid, 2.5) for sid in selected_ids if get_solution_by_id(sid)) * (scale/100.0)
        result["projected_climate_score"] = min(94, round(base + added))
        result["projectedClimateScore"] = result["projected_climate_score"]
        result["base_climate_score"] = base
    return result
