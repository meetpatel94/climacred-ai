"""
Transparent scoring methodology for ClimaCred AI Climate Fingerprint
Scores 0-100 per dimension, 100 = best (Low impact), 0 = worst (Very High impact opportunity)
Impact levels:
  80-100: Low
  65-79: Moderate
  40-64: High
  0-39: Very High
Confidence derived from data completeness.
"""
from typing import Dict, Any, Tuple
from datetime import datetime, timezone

def impact_level_from_score(score: float) -> str:
    if score >= 80:
        return "Low"
    elif score >= 65:
        return "Moderate"
    elif score >= 40:
        return "High"
    else:
        return "Very High"

def clamp_score(s: float) -> float:
    return max(0, min(100, round(s, 1)))

# Helper to extract values flexibly from assessment that may be camelCase or snake_case
def get_nested(assessment: dict, section: str, *aliases, default=None):
    sec = assessment.get(section, {})
    # section might be provided as top-level flat? but we assume nested
    for a in aliases:
        if a in sec:
            return sec[a]
    return default

def score_energy(assessment: dict, profile: dict) -> Dict[str, Any]:
    energy = assessment.get("energy", {})
    monthly_kwh = float(get_nested(assessment, "energy", "monthlyElectricityKwh", "monthly_electricity_kwh", default=0) or 0)
    monthly_cost = float(get_nested(assessment, "energy", "monthlyElectricityBillInr", "monthly_electricity_cost", default=0) or 0)
    diesel_hours = float(get_nested(assessment, "energy", "dieselGeneratorHoursPerMonth", "diesel_generator_usage", default=0) or 0)
    diesel_litres = float(get_nested(assessment, "energy", "generatorFuelLitresPerMonth", "diesel_litres", default=0) or 0)
    solar_kw = float(get_nested(assessment, "energy", "existingSolarCapacityKw", "existing_solar_kw", default=0) or 0)
    eff_percent = float(get_nested(assessment, "energy", "energyEfficientEquipmentPercent", "energy_efficient_equipment_percentage", default=50) or 0)

    employees = float(profile.get("employees", profile.get("employees", 100)) or 100)
    if employees == 0:
        employees = 100

    # Benchmark: kWh per employee per month
    kwh_per_employee = monthly_kwh / employees if employees else monthly_kwh
    # Expected benchmark for SME manufacturing: ~180-250 kWh/employee/mo
    # Penalty if above benchmark
    score = 100.0
    # Penalty for high kwh_per_employee
    if kwh_per_employee > 400:
        score -= 35
    elif kwh_per_employee > 300:
        score -= 25
    elif kwh_per_employee > 250:
        score -= 18
    elif kwh_per_employee > 200:
        score -= 10
    elif kwh_per_employee > 150:
        score -= 5

    # Penalty for low efficient equipment
    score -= (100 - eff_percent) * 0.25  # up to -25

    # Solar penalty/bonus
    if solar_kw == 0:
        score -= 12
    elif solar_kw < 10:
        score -= 6
    elif solar_kw >= 30:
        score += 5  # bonus

    # Diesel genset penalty
    if diesel_hours > 80:
        score -= 15
    elif diesel_hours > 40:
        score -= 10
    elif diesel_hours > 20:
        score -= 5

    # Cost efficiency check: cost per kWh
    if monthly_kwh > 0:
        cost_per_kwh = monthly_cost / monthly_kwh if monthly_kwh else 0
        if cost_per_kwh > 10:
            score -= 8  # high tariff/inefficiency
        elif cost_per_kwh > 9:
            score -= 3

    score = clamp_score(score)
    level = impact_level_from_score(score)

    # Determine status and issues
    if level == "Very High":
        status = "High reliance on peak-hour thermal grid & diesel backup"
        cause = "Older non-inverter motors, thermal heat losses, zero or minimal on-site solar"
        opportunity = "Rooftop solar PPA, VFD motor retrofits, waste heat economizer"
        reduction = "32% power reduction potential"
    elif level == "High":
        status = "Elevated electricity intensity with limited efficiency measures"
        cause = f"{kwh_per_employee:.0f} kWh/employee/month exceeds benchmark; {100-eff_percent:.0f}% non-efficient equipment"
        opportunity = "Smart energy monitoring, IE4 motors, solar offset"
        reduction = "22% power reduction potential"
    elif level == "Moderate":
        status = "Moderate energy efficiency, some renewable offset"
        cause = "Partial efficiency but peak load not optimized"
        opportunity = "Peak shaving, load optimization, expand solar"
        reduction = "14% power reduction potential"
    else:
        status = "Efficient energy profile with renewable integration"
        cause = "Low intensity and high equipment efficiency"
        opportunity = "Maintain monitoring, consider storage"
        reduction = "6% further optimization"

    green = assessment.get("greenPractices", {})
    if green.get("solarPanels") or solar_kw>0:
        # slightly improve narrative if solar present
        pass

    confidence = "High" if monthly_kwh>0 and eff_percent is not None else "Medium"
    if monthly_kwh==0:
        confidence="Low"

    return {
        "dimension": "Energy",
        "score": score,
        "impact_level": level,
        "current_status": status,
        "primary_cause": cause,
        "improvement_opportunity": opportunity,
        "potential_reduction": reduction,
        "confidence": confidence,
        "metrics_used": {
            "monthly_kwh": monthly_kwh,
            "kwh_per_employee": round(kwh_per_employee,1),
            "efficient_equipment_percent": eff_percent,
            "existing_solar_kw": solar_kw,
            "diesel_hours": diesel_hours
        }
    }

def score_water(assessment: dict, profile: dict) -> Dict[str, Any]:
    water = assessment.get("water", {})
    monthly_litres = float(get_nested(assessment, "water", "monthlyWaterLitres", "monthly_water_litres", default=0) or 0)
    water_source = get_nested(assessment, "water", "waterSource", "water_source", default="Municipal") or "Municipal"
    recycling = get_nested(assessment, "water", "waterRecyclingAvailable", "water_recycling", default=False)
    # fallback to green practices
    if recycling is False:
        gp = assessment.get("greenPractices", {})
        recycling = gp.get("waterRecycling", gp.get("water_recycling", False)) or False
    rainwater = get_nested(assessment, "water", "rainwaterHarvesting", "rainwater_harvesting", default=False)
    if rainwater is False:
        gp = assessment.get("greenPractices", {})
        rainwater = gp.get("rainwaterHarvesting", False) or False
    leakage = get_nested(assessment, "water", "leakageFrequency", "leakage_frequency", default="Never") or "Never"
    wastewater = get_nested(assessment, "water", "wastewaterTreatment", "wastewater_treatment", default="None") or "None"

    employees = float(profile.get("employees", 100) or 100)
    facility_area = float(profile.get("facilityAreaSqFt", profile.get("facility_area_sqft", 20000)) or 20000)
    if employees==0:
        employees=100

    litres_per_employee = monthly_litres / employees if employees else monthly_litres
    litres_per_sqft = monthly_litres / facility_area if facility_area else monthly_litres

    score = 100.0
    # High water usage penalty
    if monthly_litres > 500000:
        score -= 30
    elif monthly_litres > 400000:
        score -= 22
    elif monthly_litres > 250000:
        score -= 14
    elif monthly_litres > 120000:
        score -= 7

    if litres_per_employee > 4000:
        score -= 12
    elif litres_per_employee > 2500:
        score -= 7

    if not recycling:
        score -= 18
    else:
        score += 8

    if not rainwater:
        score -= 8
    else:
        score += 5

    leakage_penalty = {"Never": 0, "Rarely": 3, "Monthly": 9, "Frequent": 16}
    score -= leakage_penalty.get(leakage, 5)

    wastewater_penalty = {"None": 12, "Primary / Settling": 6, "Full ETP / STP": -5}
    score -= wastewater_penalty.get(wastewater, 6)
    if wastewater == "Full ETP / STP":
        score += 5  # because we subtracted -5 (adds 5)

    # Source penalty: groundwater stress
    if water_source == "Groundwater / Borewell":
        score -= 7
    elif water_source == "Water Tanker":
        score -= 4

    score = clamp_score(score)
    level = impact_level_from_score(score)

    if level == "Very High":
        status = f"{monthly_litres:,.0f} L/month borewell extraction with minimal recycling"
        cause = "Single-pass rinsing baths, unmonitored pipe leakage, no closed-loop RO"
        opportunity = "Zero Liquid Discharge (ZLD) RO recycling & digital ultrasonic leak sensors"
        reduction = "65% freshwater reduction potential"
    elif level == "High":
        status = "High freshwater extraction with partial treatment"
        cause = f"{leakage} leakage events with {'no' if not recycling else 'limited'} water recycling"
        opportunity = "Ultrafiltration recycling & leak telemetry"
        reduction = "42% freshwater reduction potential"
    elif level == "Moderate":
        status = "Moderate water efficiency with some reuse"
        cause = "Some reuse but still high per-employee intensity"
        opportunity = "Expand recycling & rainwater recharge"
        reduction = "22% freshwater reduction potential"
    else:
        status = "Efficient water stewardship with closed-loop systems"
        cause = "Low extraction intensity with full recycling"
        opportunity = "Maintain monitoring & rainwater optimization"
        reduction = "8% further reduction"

    confidence = "High" if monthly_litres>0 else "Low"
    return {
        "dimension": "Water",
        "score": score,
        "impact_level": level,
        "current_status": status,
        "primary_cause": cause,
        "improvement_opportunity": opportunity,
        "potential_reduction": reduction,
        "confidence": confidence,
        "metrics_used": {
            "monthly_litres": monthly_litres,
            "litres_per_employee": round(litres_per_employee,1),
            "litres_per_sqft": round(litres_per_sqft,2),
            "recycling": recycling,
            "rainwater": rainwater,
            "leakage": leakage,
            "wastewater": wastewater,
            "water_source": water_source
        }
    }

def score_waste(assessment: dict, profile: dict) -> Dict[str, Any]:
    waste = assessment.get("waste", {})
    organic = float(get_nested(assessment, "waste", "organicWasteKgPerMonth", "organic_waste_kg", default=0) or 0)
    plastic = float(get_nested(assessment, "waste", "plasticWasteKgPerMonth", "plastic_waste_kg", default=0) or 0)
    paper = float(get_nested(assessment, "waste", "paperWasteKgPerMonth", "paper_waste_kg", default=0) or 0)
    industrial = float(get_nested(assessment, "waste", "industrialWasteKgPerMonth", "industrial_waste_kg", default=0) or 0)
    textile = float(get_nested(assessment, "waste", "textileMaterialWasteKgPerMonth", "material_waste_kg", default=0) or 0)
    recycling_percent = float(get_nested(assessment, "waste", "currentRecyclingPercent", "recycling_percentage", default=0) or 0)
    segregation = get_nested(assessment, "waste", "wasteSegregationPracticed", "waste_segregation", default=False)
    if segregation is False:
        gp = assessment.get("greenPractices", {})
        segregation = gp.get("wasteSegregation", False) or False

    total = organic+plastic+paper+industrial+textile
    score = 100.0
    # Total waste penalty
    if total > 5000:
        score -= 25
    elif total > 3000:
        score -= 16
    elif total > 1500:
        score -= 8
    elif total > 600:
        score -= 4

    # Recycling rate scoring (inverse: low recycling = low score)
    # high recycling good: >60 = bonus
    if recycling_percent < 10:
        score -= 22
    elif recycling_percent < 25:
        score -= 14
    elif recycling_percent < 40:
        score -= 7
    elif recycling_percent < 60:
        score -= 3
    elif recycling_percent >= 70:
        score += 5

    if not segregation:
        score -= 12
    else:
        score += 4

    # Textile waste specific for textile industry penalty if high
    if textile > 2000:
        score -= 10
    elif textile > 1000:
        score -= 5

    score = clamp_score(score)
    level = impact_level_from_score(score)

    if level == "Very High":
        status = f"{textile:,.0f} kg textile scrap with low recovery routing"
        cause = "Pattern cutting scrap margin and lack of circular upcycling vendor contracts"
        opportunity = "Circular fiber downcycling partner program & automated fabric nesting software"
        reduction = "48% landfill diversion potential"
    elif level == "High":
        status = f"{total:,.0f} kg/mo total waste with {recycling_percent:.0f}% recycling"
        cause = f"{'No segregation; ' if not segregation else ''}High material scrap not routed to recovery"
        opportunity = "Off-cut baling & certified recycler tie-up"
        reduction = "36% landfill diversion potential"
    elif level == "Moderate":
        status = "Moderate waste generation with segregation in place"
        cause = "Recycling present but not maximized"
        opportunity = "Expand material reuse & supplier take-back"
        reduction = "22% diversion potential"
    else:
        status = "Efficient circular waste management"
        cause = "High recycling with segregation"
        opportunity = "Maintain closed-loop & track scope 3"
        reduction = "8% further diversion"

    confidence = "High" if total>0 else "Medium"
    return {
        "dimension": "Waste",
        "score": score,
        "impact_level": level,
        "current_status": status,
        "primary_cause": cause,
        "improvement_opportunity": opportunity,
        "potential_reduction": reduction,
        "confidence": confidence,
        "metrics_used": {
            "total_waste_kg": total,
            "recycling_percent": recycling_percent,
            "segregation": segregation,
            "textile_waste": textile
        }
    }

def score_emissions(assessment: dict, profile: dict) -> Dict[str, Any]:
    emissions = assessment.get("emissions", {})
    energy = assessment.get("energy", {})
    monthly_kwh = float(get_nested(assessment, "energy", "monthlyElectricityKwh", "monthly_electricity_kwh", default=0) or 0)
    diesel = float(get_nested(assessment, "emissions", "monthlyDieselLitres", "diesel_litres", default=0) or 0)
    # fallback generator fuel
    gen_fuel = float(get_nested(assessment, "energy", "generatorFuelLitresPerMonth", default=0) or 0)
    if diesel == 0 and gen_fuel>0:
        diesel = gen_fuel
    petrol = float(get_nested(assessment, "emissions", "monthlyPetrolLitres", "petrol_litres", default=0) or 0)
    natural_gas = float(get_nested(assessment, "emissions", "monthlyNaturalGasKg", "natural_gas_units", default=0) or 0)
    primary_fuel = get_nested(assessment, "emissions", "primaryFuel", "primary_fuel", default="Electricity Grid")
    air_control = get_nested(assessment, "emissions", "airPollutionControlSystem", "air_control_system", default="None")

    # Estimate total emissions using same factors as calculations
    from app.config import settings
    total_tonnes = (monthly_kwh*settings.ELECTRICITY_EMISSION_FACTOR_KG_PER_KWH + diesel*settings.DIESEL_EMISSION_FACTOR_KG_PER_LITRE + petrol*settings.PETROL_EMISSION_FACTOR_KG_PER_LITRE + natural_gas*settings.NATURAL_GAS_EMISSION_FACTOR_KG_PER_KG)/1000.0

    score = 100.0
    if total_tonnes > 45:
        score -= 30
    elif total_tonnes > 30:
        score -= 20
    elif total_tonnes > 15:
        score -= 10
    elif total_tonnes > 8:
        score -= 5

    if diesel > 1500:
        score -= 12
    elif diesel > 800:
        score -= 7
    elif diesel > 300:
        score -= 3

    if primary_fuel in ["Diesel","Coal / Biomass"]:
        score -= 10
    elif primary_fuel == "Natural Gas / PNG":
        score -= 3

    air_penalties = {"None": 14, "Basic Scrubber": 6, "Bag Filter / ESP": 2, "Advanced Multi-Stage": -4}
    score -= air_penalties.get(air_control, 6)
    if air_control == "Advanced Multi-Stage":
        score += 4

    score = clamp_score(score)
    level = impact_level_from_score(score)

    if level == "Very High":
        status = f"{total_tonnes:.1f} MT CO₂e / month Scope 1 & 2 combined emissions footprint"
        cause = "Grid emission factor (0.82 kg CO₂/kWh) + diesel boiler fuel; no advanced controls"
        opportunity = "Renewable power transition + biomass pellet boiler retrofit"
        reduction = "52% Scope 1+2 emissions potential"
    elif level == "High":
        status = f"{total_tonnes:.1f} MT CO₂e/month with {diesel:.0f}L diesel combustion"
        cause = f"Primary fuel {primary_fuel} with {air_control} air controls"
        opportunity = "Solar transition + flue gas economizer"
        reduction = "34% emissions reduction potential"
    elif level == "Moderate":
        status = f"{total_tonnes:.1f} MT CO₂e/month moderate footprint"
        cause = "Grid dependence but some fuel controls"
        opportunity = "Expand renewable & heat recovery"
        reduction = "18% reduction potential"
    else:
        status = "Low emissions intensity with advanced controls"
        cause = "Efficient fuel mix and advanced abatement"
        opportunity = "Maintain & monitor scope 3"
        reduction = "7% further reduction"

    confidence = "High" if monthly_kwh>0 or diesel>0 else "Medium"
    return {
        "dimension": "Emissions",
        "score": score,
        "impact_level": level,
        "current_status": status,
        "primary_cause": cause,
        "improvement_opportunity": opportunity,
        "potential_reduction": reduction,
        "confidence": confidence,
        "metrics_used": {
            "total_tonnes_monthly": round(total_tonnes,2),
            "monthly_kwh": monthly_kwh,
            "diesel_litres": diesel,
            "petrol_litres": petrol,
            "natural_gas_kg": natural_gas,
            "primary_fuel": primary_fuel,
            "air_control": air_control
        }
    }

def score_mobility(assessment: dict, profile: dict) -> Dict[str, Any]:
    mobility = assessment.get("mobility", {})
    vehicles = int(get_nested(assessment, "mobility", "deliveryVehiclesCount", "delivery_vehicles", default=0) or 0)
    vehicle_fuel = get_nested(assessment, "mobility", "vehicleFuelType", "vehicle_fuel_type", default="Diesel") or "Diesel"
    monthly_fuel = float(get_nested(assessment, "mobility", "monthlyFleetFuelLitres", "monthly_fuel_litres", default=0) or 0)
    employee_commute = get_nested(assessment, "mobility", "employeeCommuteMode", "employee_transport", default="Mixed") or "Mixed"
    ev_percent = float(get_nested(assessment, "mobility", "evAdoptedPercent", "electric_vehicle_count", default=0) or 0)
    # If electric_vehicle_count is count
    ev_count_alias = get_nested(assessment, "mobility", "electricVehicleCount", default=None)
    if ev_count_alias is not None and vehicles>0:
        try:
            if float(ev_count_alias) <= vehicles and ev_percent==float(ev_count_alias):
                ev_percent = float(ev_count_alias)/vehicles*100
        except:
            pass
    ev_percent = max(0, min(100, ev_percent))

    score = 100.0
    # Fuel intensity per vehicle
    fuel_per_vehicle = (monthly_fuel / vehicles) if vehicles else 0
    if vehicles>0:
        if fuel_per_vehicle > 300:
            score -= 22
        elif fuel_per_vehicle > 220:
            score -= 14
        elif fuel_per_vehicle > 150:
            score -= 7
        elif fuel_per_vehicle > 80:
            score -= 3

    if monthly_fuel > 2000:
        score -= 12
    elif monthly_fuel > 1200:
        score -= 7
    elif monthly_fuel > 600:
        score -= 4

    if ev_percent == 0:
        score -= 12
    elif ev_percent < 20:
        score -= 7
    elif ev_percent < 50:
        score -= 3
    elif ev_percent >= 80:
        score += 6

    fuel_penalties = {"Diesel": 8, "Petrol": 6, "CNG": 3, "Electric": -8, "Mixed Fleet": 5}
    score -= fuel_penalties.get(vehicle_fuel, 5)
    if vehicle_fuel=="Electric":
        score += 8

    if employee_commute == "Two-Wheelers":
        score -= 4
    elif employee_commute == "Company Bus":
        score += 3

    score = clamp_score(score)
    level = impact_level_from_score(score)

    if level == "Very High":
        status = f"{vehicles} diesel cargo vans with {fuel_per_vehicle:.0f} L/vehicle/month high fuel intensity"
        cause = "Legacy diesel fleet with ~9 km/L fuel efficiency and zero telemetry"
        opportunity = "Phased commercial EV fleet transition and route batching"
        reduction = "42% logistics emissions potential"
    elif level == "High":
        status = f"{vehicles} delivery vehicles with {monthly_fuel:.0f} L monthly fuel, {ev_percent:.0f}% EV"
        cause = f"{vehicle_fuel} fleet with low EV adoption"
        opportunity = "EV transition + AI route optimization"
        reduction = "32% mobility emissions potential"
    elif level == "Moderate":
        status = f"{vehicles} vehicles with moderate fuel use, {ev_percent:.0f}% electric"
        cause = "Partial EV adoption but route not optimized"
        opportunity = "Expand EV & load optimization"
        reduction = "18% reduction potential"
    else:
        status = "Efficient low-emission mobility"
        cause = "High EV share and optimized routing"
        opportunity = "Maintain telemetry & charging infra"
        reduction = "6% further reduction"

    confidence = "High" if vehicles>0 else "Medium"
    return {
        "dimension": "Mobility",
        "score": score,
        "impact_level": level,
        "current_status": status,
        "primary_cause": cause,
        "improvement_opportunity": opportunity,
        "potential_reduction": reduction,
        "confidence": confidence,
        "metrics_used": {
            "vehicles": vehicles,
            "monthly_fuel": monthly_fuel,
            "fuel_per_vehicle": round(fuel_per_vehicle,1),
            "ev_percent": ev_percent,
            "fuel_type": vehicle_fuel,
            "commute_mode": employee_commute
        }
    }

def score_operations(assessment: dict, profile: dict) -> Dict[str, Any]:
    green = assessment.get("greenPractices", {})
    # count true green practices
    practice_keys = ["ledLighting","solarPanels","rainwaterHarvesting","waterRecycling","wasteSegregation","energyEfficientMachinery","evAdoption","sustainableMaterials",
                     "led_lighting","solar","rainwater_harvesting","water_recycling","waste_segregation","energy_efficient_machinery","ev_adoption","sustainable_materials"]
    # Normalize: check both forms
    true_count = 0
    total_practices = 8
    mapped = [
        ("ledLighting","led_lighting"),
        ("solarPanels","solar"),
        ("rainwaterHarvesting","rainwater_harvesting"),
        ("waterRecycling","water_recycling"),
        ("wasteSegregation","waste_segregation"),
        ("energyEfficientMachinery","energy_efficient_machinery"),
        ("evAdoption","ev_adoption"),
        ("sustainableMaterials","sustainable_materials"),
    ]
    for cam, snake in mapped:
        val = green.get(cam, green.get(snake, False))
        if val is True or val == 1 or val == "true":
            true_count += 1

    operating_hours = float(profile.get("operatingHoursPerDay", profile.get("operating_hours_per_day", 16)) or 16)
    working_days = float(profile.get("workingDaysPerMonth", profile.get("working_days", 26)) or 26)

    score = 50.0  # base
    # Green practices give points
    score += true_count * 7  # up to 56 => could exceed 100, clamp
    # penalty if very low adoption
    if true_count <= 1:
        score -= 10
    elif true_count <= 3:
        score -= 4

    # Operational intensity: high hours with manual tracking assumed less efficient
    if operating_hours >= 20 and true_count < 4:
        score -= 8
    if working_days >= 26 and true_count < 3:
        score -= 4

    # Facility area vs employees density check? Not needed

    score = clamp_score(score)
    level = impact_level_from_score(score)

    if level == "Very High":
        status = "Manual paper logbooks for power tracking and maintenance"
        cause = "Lack of automated sub-metering IoT sensors at departmental line feeds"
        opportunity = "IoT edge smart sub-metering on key motors and steam lines"
        reduction = "20% unmetered wastage potential"
    elif level == "High":
        status = f"Only {true_count}/8 green practices adopted, limited automation"
        cause = "Low adoption of systematic sustainability operations"
        opportunity = "LED conversion, smart sensors, sustainable materials"
        reduction = "16% operations improvement potential"
    elif level == "Moderate":
        status = f"{true_count}/8 green practices implemented, partial automation"
        cause = "Some operational improvements but gap in digital metering"
        opportunity = "IoT telemetry & sustainable sourcing"
        reduction = "10% improvement potential"
    else:
        status = "Mature green operations with high practice adoption"
        cause = f"{true_count}/8 green practices with automated monitoring"
        opportunity = "Continuous intelligence & audit verification"
        reduction = "4% optimization potential"

    confidence = "High" if true_count is not None else "Medium"
    return {
        "dimension": "Operations",
        "score": score,
        "impact_level": level,
        "current_status": status,
        "primary_cause": cause,
        "improvement_opportunity": opportunity,
        "potential_reduction": reduction,
        "confidence": confidence,
        "metrics_used": {
            "green_practices_adopted": true_count,
            "total_practices": total_practices,
            "operating_hours": operating_hours,
            "working_days": working_days
        }
    }
