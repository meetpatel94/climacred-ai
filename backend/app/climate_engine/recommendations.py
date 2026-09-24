"""
Recommendation Engine
Transparent scoring: Recommendation Score = Impact Weight + Financial Opportunity + Environmental Opportunity + Feasibility + Business Relevance
Weights configurable.

Solution catalog is structured and explainable.
Does NOT automatically recommend solar to everyone – personalized.
"""
from typing import List, Dict, Any
from app.config import settings

# Weights for recommendation scoring – configurable
RECOMMENDATION_WEIGHTS = {
    "impact_weight": 0.30,
    "financial_weight": 0.25,
    "environmental_weight": 0.20,
    "feasibility_weight": 0.15,
    "business_relevance_weight": 0.10
}

# Full solution catalog (14 solutions, covering Energy, Water, Waste, Mobility, Materials, Operations)
SOLUTION_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "sol-solar",
        "title": "Rooftop Solar PV System (75 kWp)",
        "name": "Rooftop Solar PV System (75 kWp)",
        "category": "Energy",
        "problem_area": "High grid electricity bills and diesel genset running hours during peak daylight factory shifts.",
        "problemAddressed": "High grid electricity bills and diesel genset running hours during peak daylight factory shifts.",
        "description": "Grid-tied rooftop solar system with smart net-metering and inverter telemetry.",
        "shortDesc": "Grid-tied rooftop solar system with smart net-metering and inverter telemetry.",
        "investment_range": "₹28,00,000 – ₹34,00,000",
        "investmentRange": "₹28,00,000 – ₹34,00,000",
        "investmentMinInr": 2800000,
        "investmentMaxInr": 3400000,
        "potentialAnnualSavingsInr": 915000,
        "potentialEnvironmentalImpact": "108,000 kWh clean power generated / year",
        "estimatedPaybackPeriodYears": 3.2,
        "implementationDifficulty": "Medium",
        "implementation_difficulty": "Medium",
        "co2ReductionTonnesPerYear": 88.5,
        "resourceReductionValue": "35% grid power offset",
        "required_inputs": ["monthly_electricity_kwh", "facility_area_sqft", "operating_hours"],
        "applicable_industries": ["All"],
        "featured": True,
        "assumptions": ["Reference sizing: 75 kWp installation, 4.5 peak sun hours, 78% performance ratio (configurable; actual sizing depends on your recorded facility area)."]
    },
    {
        "id": "sol-water-ro",
        "title": "Closed-Loop Water Recycling & Ultrafiltration",
        "name": "Closed-Loop Water Recycling & Ultrafiltration",
        "category": "Water",
        "problem_area": "High freshwater extraction with single-pass rinsing bath effluent.",
        "problemAddressed": "High freshwater extraction with single-pass rinsing bath effluent.",
        "description": "Multi-stage ultrafiltration with reverse osmosis to recycle 65% rinse water back into dye baths.",
        "shortDesc": "Multi-stage ultrafiltration with reverse osmosis to recycle 65% rinse water back into dye baths.",
        "investment_range": "₹22,00,000 – ₹29,00,000",
        "investmentRange": "₹22,00,000 – ₹29,00,000",
        "investmentMinInr": 2200000,
        "investmentMaxInr": 2900000,
        "potentialAnnualSavingsInr": 640000,
        "potentialEnvironmentalImpact": "3,740,000 Litres freshwater saved annually",
        "estimatedPaybackPeriodYears": 3.8,
        "implementationDifficulty": "High",
        "implementation_difficulty": "High",
        "co2ReductionTonnesPerYear": 18.2,
        "resourceReductionValue": "65% freshwater reduction",
        "required_inputs": ["monthly_water_litres", "water_source", "wastewater_treatment"],
        "featured": True,
        "assumptions": ["65% recycling assumes ZLD RO with 85% recovery, 300 operating days"]
    },
    {
        "id": "sol-machinery-vfd",
        "title": "VFD & IE4 Super-Premium Motors Retrofit",
        "name": "VFD & IE4 Super-Premium Motors Retrofit",
        "category": "Energy",
        "problem_area": "Legacy standard induction motors running continuously at fixed speeds with throttle dampers.",
        "problemAddressed": "Legacy standard induction motors running continuously at fixed speeds with throttle dampers.",
        "description": "Replace standard motors on blowers, pumps, and spinning lines with IE4 motors and VFD variable frequency drives.",
        "shortDesc": "Replace standard motors on blowers, pumps, and spinning lines with IE4 motors and VFD variable frequency drives.",
        "investment_range": "₹9,50,000 – ₹13,00,000",
        "investmentRange": "₹9,50,000 – ₹13,00,000",
        "investmentMinInr": 950000,
        "investmentMaxInr": 1300000,
        "potentialAnnualSavingsInr": 410000,
        "potentialEnvironmentalImpact": "46,000 kWh electrical load saved annually",
        "estimatedPaybackPeriodYears": 2.6,
        "implementationDifficulty": "Low",
        "implementation_difficulty": "Low",
        "co2ReductionTonnesPerYear": 37.7,
        "resourceReductionValue": "18% motor load reduction",
        "required_inputs": ["monthly_electricity_kwh", "energy_efficient_equipment_percentage"],
        "featured": True,
        "assumptions": ["Assumes 28% existing efficiency, 12 motors retrofitted, 18% avg load saving"]
    },
    {
        "id": "sol-leak-sensors",
        "title": "Smart Ultrasonic Water Leak & Flow Telemetry",
        "name": "Smart Ultrasonic Water Leak & Flow Telemetry",
        "category": "Water",
        "problem_area": "Unnoticed underground joint leakages and overflow tanks wasting treated water.",
        "problemAddressed": "Unnoticed underground joint leakages and overflow tanks wasting treated water.",
        "description": "IoT ultrasonic clamp-on flow meters and smart alert valves at key distribution junctions.",
        "shortDesc": "IoT ultrasonic clamp-on flow meters and smart alert valves at key distribution junctions.",
        "investment_range": "₹2,20,000 – ₹3,50,000",
        "investmentRange": "₹2,20,000 – ₹3,50,000",
        "investmentMinInr": 220000,
        "investmentMaxInr": 350000,
        "potentialAnnualSavingsInr": 165000,
        "potentialEnvironmentalImpact": "420,000 Litres water saved annually",
        "estimatedPaybackPeriodYears": 1.6,
        "implementationDifficulty": "Low",
        "implementation_difficulty": "Low",
        "co2ReductionTonnesPerYear": 4.1,
        "resourceReductionValue": "9% total water saved",
        "required_inputs": ["monthly_water_litres", "leakage_frequency"],
        "featured": False,
        "assumptions": ["Assumes 8% leakage loss, 90% detection repair effectiveness"]
    },
    {
        "id": "sol-rainwater",
        "title": "Rooftop Rainwater Harvesting & Recharge Well",
        "name": "Rooftop Rainwater Harvesting & Recharge Well",
        "category": "Water",
        "problem_area": "Rainwater runoff loss from the industrial shed roof during monsoon cycles.",
        "problemAddressed": "Rainwater runoff loss from the industrial shed roof during monsoon cycles.",
        "description": "Guttering conduits, multi-media sand filters, and a 120,000 L underground holding storage tank.",
        "shortDesc": "Guttering conduits, multi-media sand filters, and a 120,000 L underground holding storage tank.",
        "investment_range": "₹4,50,000 – ₹6,00,000",
        "investmentRange": "₹4,50,000 – ₹6,00,000",
        "investmentMinInr": 450000,
        "investmentMaxInr": 600000,
        "potentialAnnualSavingsInr": 190000,
        "potentialEnvironmentalImpact": "980,000 Litres groundwater recharged / year",
        "estimatedPaybackPeriodYears": 2.8,
        "implementationDifficulty": "Medium",
        "implementation_difficulty": "Medium",
        "co2ReductionTonnesPerYear": 5.6,
        "resourceReductionValue": "20% seasonal water offset",
        "required_inputs": ["facility_area_sqft", "location"],
        "featured": False,
        "assumptions": ["Reference sizing: regional monsoon rainfall, 70% capture efficiency, 120 kL storage (configurable)."]
    },
    {
        "id": "sol-waste-recovery",
        "title": "Textile Fabric Off-Cut Circular Recovery & Baling",
        "name": "Textile Fabric Off-Cut Circular Recovery & Baling",
        "category": "Waste",
        "problem_area": "Mixed textile off-cuts commonly leave plants through low-recovery scrap channels instead of circular buyers.",
        "problemAddressed": "Mixed textile off-cuts commonly leave plants through low-recovery scrap channels instead of circular buyers.",
        "description": "Automated hydraulic sorting baler + tie-up with certified recycled yarn & acoustic panel manufacturers.",
        "shortDesc": "Automated hydraulic sorting baler + tie-up with certified recycled yarn & acoustic panel manufacturers.",
        "investment_range": "₹3,80,000 – ₹5,20,000",
        "investmentRange": "₹3,80,000 – ₹5,20,000",
        "investmentMinInr": 380000,
        "investmentMaxInr": 520000,
        "potentialAnnualSavingsInr": 320000,
        "potentialEnvironmentalImpact": "28.5 tonnes landfill diversion annually",
        "estimatedPaybackPeriodYears": 1.4,
        "implementationDifficulty": "Low",
        "implementation_difficulty": "Low",
        "co2ReductionTonnesPerYear": 24.3,
        "resourceReductionValue": "66% textile waste recovered",
        "required_inputs": ["material_waste_kg", "recycling_percentage"],
        "featured": True,
        "assumptions": ["Reference sizing: ₹7.5/kg scrap value and 66% recovery to recyclers applied to your recorded material waste."]
    },
    {
        "id": "sol-ev-fleet",
        "title": "Commercial EV Cargo Van Transition (Phase 1)",
        "name": "Commercial EV Cargo Van Transition (Phase 1)",
        "category": "Mobility",
        "problem_area": "Diesel fuel consumption and tailpipe emissions from intra-city dispatch vans.",
        "problemAddressed": "Diesel fuel consumption and tailpipe emissions from intra-city dispatch vans.",
        "description": "Replace diesel cargo vans with 3.5-ton commercial electric vans and install dual 11 kW Type 2 chargers.",
        "shortDesc": "Replace diesel cargo vans with 3.5-ton commercial electric vans and install dual 11 kW Type 2 chargers.",
        "investment_range": "₹18,00,000 – ₹24,00,000",
        "investmentRange": "₹18,00,000 – ₹24,00,000",
        "investmentMinInr": 1800000,
        "investmentMaxInr": 2400000,
        "potentialAnnualSavingsInr": 480000,
        "potentialEnvironmentalImpact": "9,200 Litres diesel avoided annually",
        "estimatedPaybackPeriodYears": 4.2,
        "implementationDifficulty": "Medium",
        "implementation_difficulty": "Medium",
        "co2ReductionTonnesPerYear": 24.8,
        "resourceReductionValue": "50% fleet diesel reduction",
        "required_inputs": ["delivery_vehicles", "monthly_fuel_litres", "vehicle_fuel_type"],
        "featured": False,
        "assumptions": ["Reference sizing: 280 km/day, diesel 9 km/L, EV 1.2 km/kWh per replaced van (configurable)."]
    },
    {
        "id": "sol-route-opt",
        "title": "AI Delivery Route Dispatch & Load Optimization",
        "name": "AI Delivery Route Dispatch & Load Optimization",
        "category": "Mobility",
        "problem_area": "Sub-optimal delivery routing, half-empty return trips, and traffic idling.",
        "problemAddressed": "Sub-optimal delivery routing, half-empty return trips, and traffic idling.",
        "description": "SaaS dispatch software with algorithmic route grouping, vehicle load filling, and driver tracking.",
        "shortDesc": "SaaS dispatch software with algorithmic route grouping, vehicle load filling, and driver tracking.",
        "investment_range": "₹80,000 – ₹1,50,000",
        "investmentRange": "₹80,000 – ₹1,50,000",
        "investmentMinInr": 80000,
        "investmentMaxInr": 150000,
        "potentialAnnualSavingsInr": 145000,
        "potentialEnvironmentalImpact": "3,100 Litres fuel saved per year",
        "estimatedPaybackPeriodYears": 0.8,
        "implementationDifficulty": "Low",
        "implementation_difficulty": "Low",
        "co2ReductionTonnesPerYear": 8.3,
        "resourceReductionValue": "16% transport fuel reduction",
        "required_inputs": ["monthly_fuel_litres", "delivery_vehicles"],
        "featured": False,
        "assumptions": ["Assumes 16% fuel save via route batching, SaaS cost ₹8k/mo"]
    },
    {
        "id": "sol-heat-recovery",
        "title": "Boiler Flue Gas Waste Heat Economizer",
        "name": "Boiler Flue Gas Waste Heat Economizer",
        "category": "Energy",
        "problem_area": "Excessive heat loss in exhaust stack from process steam boilers.",
        "problemAddressed": "Excessive heat loss in exhaust stack from process steam boilers.",
        "description": "Tube bundle heat exchanger pre-heating boiler feedwater from 28°C to 72°C using flue gases.",
        "shortDesc": "Tube bundle heat exchanger pre-heating boiler feedwater from 28°C to 72°C using flue gases.",
        "investment_range": "₹6,50,000 – ₹8,50,000",
        "investmentRange": "₹6,50,000 – ₹8,50,000",
        "investmentMinInr": 650000,
        "investmentMaxInr": 850000,
        "potentialAnnualSavingsInr": 295000,
        "potentialEnvironmentalImpact": "7,400 Litres boiler fuel saved / year",
        "estimatedPaybackPeriodYears": 2.5,
        "implementationDifficulty": "Medium",
        "implementation_difficulty": "Medium",
        "co2ReductionTonnesPerYear": 19.8,
        "resourceReductionValue": "12% boiler fuel reduction",
        "required_inputs": ["primary_fuel", "diesel_litres"],
        "featured": False,
        "assumptions": ["Assumes 2 TPH boiler, 220°C stack, 15% excess air, 12% fuel saving"]
    },
    {
        "id": "sol-led-iot",
        "title": "High-Bay Smart Daylight-Linked LED Lighting",
        "name": "High-Bay Smart Daylight-Linked LED Lighting",
        "category": "Operations",
        "problem_area": "Metal-halide fixtures operating at continuous full wattage regardless of ambient skylights.",
        "problemAddressed": "Metal-halide fixtures operating at continuous full wattage regardless of ambient skylights.",
        "description": "150W high-efficiency LED luminaires with ambient daylight photocell dimming in work halls.",
        "shortDesc": "150W high-efficiency LED luminaires with ambient daylight photocell dimming in work halls.",
        "investment_range": "₹3,00,000 – ₹4,20,000",
        "investmentRange": "₹3,00,000 – ₹4,20,000",
        "investmentMinInr": 300000,
        "investmentMaxInr": 420000,
        "potentialAnnualSavingsInr": 180000,
        "potentialEnvironmentalImpact": "21,000 kWh saved annually",
        "estimatedPaybackPeriodYears": 1.9,
        "implementationDifficulty": "Low",
        "implementation_difficulty": "Low",
        "co2ReductionTonnesPerYear": 17.2,
        "resourceReductionValue": "55% lighting power reduction",
        "required_inputs": ["facility_area_sqft", "operating_hours"],
        "featured": False,
        "assumptions": ["Assumes 120 fixtures, 16h operation, 55% wattage reduction"]
    },
    {
        "id": "sol-material-reuse",
        "title": "Sustainable Material Sourcing & Chemical Recovery",
        "name": "Sustainable Material Sourcing & Chemical Recovery",
        "category": "Materials",
        "problem_area": "High consumption of virgin dyes and chemicals with low reuse cycles.",
        "problemAddressed": "High consumption of virgin dyes and chemical auxiliaries with single-use cycles.",
        "description": "Low-liquor dyeing machines + chemical recovery & reuse system for salts and auxiliaries.",
        "shortDesc": "Low-liquor dyeing + chemical recovery for reuse of salts and auxiliaries.",
        "investment_range": "₹12,00,000 – ₹16,00,000",
        "investmentRange": "₹12,00,000 – ₹16,00,000",
        "investmentMinInr": 1200000,
        "investmentMaxInr": 1600000,
        "potentialAnnualSavingsInr": 380000,
        "potentialEnvironmentalImpact": "18% chemical consumption reduction",
        "estimatedPaybackPeriodYears": 3.7,
        "implementationDifficulty": "High",
        "implementation_difficulty": "High",
        "co2ReductionTonnesPerYear": 12.5,
        "resourceReductionValue": "18% material intensity reduction",
        "required_inputs": ["production_volume", "industry"],
        "featured": False,
        "assumptions": ["Assumes 8 dyeing machines, 18% chemical recovery, GOTS compliant sourcing"]
    },
    {
        "id": "sol-smart-metering",
        "title": "IoT Smart Sub-Metering & Energy Dashboard",
        "name": "IoT Smart Sub-Metering & Energy Dashboard",
        "category": "Operations",
        "problem_area": "Departmental lines lack independent energy telemetry causing unmetered wastage.",
        "problemAddressed": "Departmental lines lack independent energy telemetry.",
        "description": "Wireless IoT edge meters on 12 key motors and steam lines with cloud dashboard & alerts.",
        "shortDesc": "IoT edge meters on key motors with cloud dashboard.",
        "investment_range": "₹2,80,000 – ₹4,00,000",
        "investmentRange": "₹2,80,000 – ₹4,00,000",
        "investmentMinInr": 280000,
        "investmentMaxInr": 400000,
        "potentialAnnualSavingsInr": 210000,
        "potentialEnvironmentalImpact": "Identifies 7-12% unmetered wastage",
        "estimatedPaybackPeriodYears": 1.5,
        "implementationDifficulty": "Low",
        "implementation_difficulty": "Low",
        "co2ReductionTonnesPerYear": 9.8,
        "resourceReductionValue": "10% wastage visibility",
        "required_inputs": ["monthly_electricity_kwh"],
        "featured": False,
        "assumptions": ["Assumes 10% wastage identified and 70% of that mitigated"]
    }
]

def _impact_score_for_dimension(fingerprint: Dict[str, Any], category: str) -> float:
    # Map category to dimension: Materials -> Waste, Operations -> Operations etc.
    category_to_dim = {
        "Energy": "Energy",
        "Water": "Water",
        "Waste": "Waste",
        "Emissions": "Emissions",
        "Mobility": "Mobility",
        "Operations": "Operations",
        "Materials": "Waste",  # materials maps to waste/operations
    }
    dim_name = category_to_dim.get(category, category)
    for d in fingerprint.get("dimensions", []):
        # handle both camel and snake
        dim = d.get("dimension")
        if dim == dim_name:
            # Very High = 100, High=75, Moderate=50, Low=20
            level = d.get("impactLevel") or d.get("impact_level") or d.get("impactLevel") or "Moderate"
            mapping = {"Very High": 100, "High": 75, "Moderate": 45, "Low": 20}
            return mapping.get(level, 45)
    return 40

def _financial_score(solution: Dict[str, Any]) -> float:
    # Higher annual savings relative to investment -> higher score
    savings = solution.get("potentialAnnualSavingsInr", 0)
    investment = solution.get("investmentMinInr", 1)
    # ROI = savings / investment
    roi = savings / investment if investment else 0
    # payback inverse
    payback = solution.get("estimatedPaybackPeriodYears", 3)
    # Score 0-100: roi*100 scaled + payback bonus
    # roi typical 0.05 - 0.8
    score = roi * 180  # roi 0.3 => 54
    if payback <= 1:
        score += 20
    elif payback <= 2:
        score += 12
    elif payback <= 3:
        score += 5
    return min(100, max(0, score))

def _environmental_score(solution: Dict[str, Any]) -> float:
    co2 = solution.get("co2ReductionTonnesPerYear", 0)
    # Scale: 5 MT => 20, 20 MT=>60, 80MT=>95
    if co2 >= 80:
        return 100
    elif co2 >= 40:
        return 75 + (co2-40)/40 *20
    elif co2 >= 15:
        return 50 + (co2-15)/25 *25
    elif co2 >= 5:
        return 20 + (co2-5)/10 *30
    else:
        return co2 * 4

def _feasibility_score(solution: Dict[str, Any]) -> float:
    diff = solution.get("implementationDifficulty") or solution.get("implementation_difficulty") or "Medium"
    mapping = {"Low": 100, "Medium": 65, "High": 35}
    return mapping.get(diff, 65)

def _business_relevance(solution: Dict[str, Any], profile: Dict[str, Any], assessment: Dict[str, Any]) -> float:
    score = 50  # baseline
    industry = profile.get("industry", "") or profile.get("industry", "")
    # textile-specific boosts
    if industry.lower() == "textile":
        textile_boost = {
            "sol-waste-recovery": 30,
            "sol-water-ro": 25,
            "sol-machinery-vfd": 15,
            "sol-material-reuse": 20
        }
        score += textile_boost.get(solution.get("id"), 0)

    # Check green practices: if already has solar, deprioritize solar
    green = assessment.get("greenPractices", {})
    has_solar = green.get("solarPanels") or green.get("solar") or assessment.get("energy", {}).get("existingSolarCapacityKw",0)>0
    if has_solar and solution.get("id") == "sol-solar":
        score -= 25

    has_ev = green.get("evAdoption") or green.get("ev_adoption") or False
    if has_ev and solution.get("id") == "sol-ev-fleet":
        score -= 10

    # Facility size: large facility more relevant for rainwater & solar
    facility = float(profile.get("facilityAreaSqFt", profile.get("facility_area_sqft", 0)) or 0)
    if facility > 30000 and solution.get("id") in ["sol-solar","sol-rainwater"]:
        score += 10

    # Water intensive if water high
    water_l = float(assessment.get("water", {}).get("monthlyWaterLitres", assessment.get("water", {}).get("monthly_water_litres",0)) or 0)
    if water_l > 400000 and solution.get("category") == "Water":
        score += 15

    return max(0, min(100, score))

def generate_recommendations(profile: Dict[str, Any], assessment: Dict[str, Any], fingerprint: Dict[str, Any], top_n: int = 5) -> List[Dict[str, Any]]:
    """
    Returns top recommended interventions with transparent scoring breakdown.
    """
    scored = []
    for sol in SOLUTION_CATALOG:
        impact = _impact_score_for_dimension(fingerprint, sol["category"])
        financial = _financial_score(sol)
        environmental = _environmental_score(sol)
        feasibility = _feasibility_score(sol)
        relevance = _business_relevance(sol, profile, assessment)

        # Weighted total
        total = (
            impact * RECOMMENDATION_WEIGHTS["impact_weight"] +
            financial * RECOMMENDATION_WEIGHTS["financial_weight"] +
            environmental * RECOMMENDATION_WEIGHTS["environmental_weight"] +
            feasibility * RECOMMENDATION_WEIGHTS["feasibility_weight"] +
            relevance * RECOMMENDATION_WEIGHTS["business_relevance_weight"]
        )
        total = round(total, 1)

        # Generate reason personalized
        # Find dimension cause
        dim_match = None
        for d in fingerprint.get("dimensions", []):
            if d.get("dimension") == (sol["category"] if sol["category"]!="Materials" else "Waste"):
                dim_match = d
                break

        priority = "High" if total >= 70 else "Medium" if total >= 50 else "Low"

        # Confidence: based on fingerprint confidence and data
        confidence = dim_match.get("confidence", "Medium") if dim_match else "Medium"

        # Estimated values: we use catalog defaults but document assumptions
        reason = f"{sol['category']} is "
        if dim_match:
            reason += f"{dim_match.get('impactLevel') or dim_match.get('impact_level')} priority (score {dim_match.get('score')}/100) due to { (dim_match.get('primaryCause') or dim_match.get('primary_cause') or '').lower() }. "
        reason += f"{sol['description']} Addresses: {sol['problem_area']}"

        scored.append({
            "solution": sol,
            "solution_id": sol["id"],
            "score": total,
            "reason": reason,
            "priority": priority,
            "estimated_investment": {
                "min_inr": sol["investmentMinInr"],
                "max_inr": sol["investmentMaxInr"],
                "range_label": sol["investment_range"] or sol.get("investmentRange")
            },
            "estimated_annual_saving_inr": sol["potentialAnnualSavingsInr"],
            "estimated_environmental_benefit": sol["potentialEnvironmentalImpact"],
            "estimated_co2_reduction_tonnes_per_year": sol["co2ReductionTonnesPerYear"],
            "estimated_payback_years": sol["estimatedPaybackPeriodYears"],
            "confidence": confidence,
            "assumptions": sol.get("assumptions", []),
            "breakdown": {
                "impact_weight": round(impact * RECOMMENDATION_WEIGHTS["impact_weight"],1),
                "financial_opportunity": round(financial * RECOMMENDATION_WEIGHTS["financial_weight"],1),
                "environmental_opportunity": round(environmental * RECOMMENDATION_WEIGHTS["environmental_weight"],1),
                "feasibility": round(feasibility * RECOMMENDATION_WEIGHTS["feasibility_weight"],1),
                "business_relevance": round(relevance * RECOMMENDATION_WEIGHTS["business_relevance_weight"],1),
                "weights_used": RECOMMENDATION_WEIGHTS,
                "raw_scores": {
                    "impact": impact,
                    "financial": round(financial,1),
                    "environmental": round(environmental,1),
                    "feasibility": feasibility,
                    "business_relevance": relevance
                }
            }
        })

    # Sort by total descending
    scored.sort(key=lambda x: x["score"], reverse=True)

    # Filter: if solar already exists and score high but we penalized, still might appear but lower
    # Ensure diversity: don't return all same category? But allow if needed.
    # Return top_n
    return scored[:top_n]

def get_all_solutions():
    return SOLUTION_CATALOG
