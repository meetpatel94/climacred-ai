"""
Calculation utilities for ClimaCred AI
All functions are pure and retain assumption documentation.
"""
from datetime import datetime, timezone
from typing import Dict, Any
from app.config import settings

def calculate_energy_metrics(assessment: dict, profile: dict = None) -> Dict[str, Any]:
    """
    Energy calculations
    - monthly electricity consumption from assessment.energy.monthlyElectricityKwh
    - annual electricity consumption = monthly * 12
    - estimated electricity-related emissions = monthly_kwh * emission_factor
    """
    energy = assessment.get("energy", {})
    monthly_kwh = float(energy.get("monthlyElectricityKwh", energy.get("monthly_electricity_kwh", 0)) or 0)
    monthly_cost = float(energy.get("monthlyElectricityBillInr", energy.get("monthly_electricity_cost", energy.get("monthly_electricity_bill_inr", 0))) or 0)

    annual_kwh = monthly_kwh * 12
    annual_cost = monthly_cost * 12

    # Configurable emission factor, documented
    emission_factor = float(settings.ELECTRICITY_EMISSION_FACTOR_KG_PER_KWH)
    # monthly emissions in tonnes CO2e
    monthly_emissions_tonnes = (monthly_kwh * emission_factor) / 1000.0
    annual_emissions_tonnes = monthly_emissions_tonnes * 12

    return {
        "monthly_electricity_kwh": monthly_kwh,
        "annual_electricity_kwh": annual_kwh,
        "monthly_electricity_cost_inr": monthly_cost,
        "annual_electricity_cost_inr": annual_cost,
        "estimated_monthly_electricity_emissions_tonnes_co2e": round(monthly_emissions_tonnes, 2),
        "estimated_annual_electricity_emissions_tonnes_co2e": round(annual_emissions_tonnes, 2),
        "emission_factor_used": {
            "factor": emission_factor,
            "unit": "kg CO2e per kWh",
            "source_label": "Configurable grid emission factor (default India CEA 0.82, not certified)",
            "calculation_timestamp": datetime.now(timezone.utc).isoformat(),
            "calculation_version": settings.CALCULATION_VERSION
        },
        "assumptions": [
            f"Electricity emission factor {emission_factor} kg CO2/kWh is configurable and not an official certified value.",
            "Annual values are simple monthly*12 projections, not weather-adjusted.",
        ]
    }

def calculate_water_metrics(assessment: dict, profile: dict = None) -> Dict[str, Any]:
    water = assessment.get("water", {})
    monthly_litres = float(water.get("monthlyWaterLitres", water.get("monthly_water_litres", 0)) or 0)
    annual_litres = monthly_litres * 12

    # Potential savings assumptions
    # If water_recycling false, estimate 50-65% saving with ZLD, else 20%
    # If leak_frequency Frequent -> 8% loss, Monthly -> 5%, Rarely ->2%, Never ->0
    has_recycling = water.get("waterRecyclingAvailable", water.get("water_recycling", False))
    # fallback check greenPractices
    green = assessment.get("greenPractices", {})
    if not has_recycling:
        has_recycling = green.get("waterRecycling", False)

    leakage = water.get("leakageFrequency", water.get("leakage_frequency", "Never"))
    leakage_map = {"Never": 0.0, "Rarely": 0.02, "Monthly": 0.05, "Frequent": 0.08}
    leakage_factor = leakage_map.get(leakage, 0.05)

    # Potential savings: recycling up to 65% + leakage fix
    recycling_savings_factor = 0.65 if not has_recycling else 0.20
    estimated_potential_annual_savings_litres = annual_litres * (recycling_savings_factor + leakage_factor * 0.5)
    # Cap at 70%
    estimated_potential_annual_savings_litres = min(estimated_potential_annual_savings_litres, annual_litres * 0.70)

    return {
        "monthly_water_litres": monthly_litres,
        "annual_water_litres": annual_litres,
        "estimated_potential_annual_savings_litres": round(estimated_potential_annual_savings_litres, 0),
        "estimated_potential_savings_percent": round((estimated_potential_annual_savings_litres / annual_litres * 100) if annual_litres else 0, 1),
        "assumptions": [
            f"Recycling savings factor assumed {recycling_savings_factor*100:.0f}% without system, 20% with existing recycling (configurable).",
            f"Leakage factor for '{leakage}' assumed {leakage_factor*100:.0f}% of total (configurable).",
            "Savings not additive beyond 70% to avoid overestimation."
        ],
        "leakage_factor_used": leakage_factor,
        "recycling_factor_used": recycling_savings_factor
    }

def calculate_waste_metrics(assessment: dict) -> Dict[str, Any]:
    waste = assessment.get("waste", {})
    organic = float(waste.get("organicWasteKgPerMonth", waste.get("organic_waste_kg", 0)) or 0)
    plastic = float(waste.get("plasticWasteKgPerMonth", waste.get("plastic_waste_kg", 0)) or 0)
    paper = float(waste.get("paperWasteKgPerMonth", waste.get("paper_waste_kg", 0)) or 0)
    industrial = float(waste.get("industrialWasteKgPerMonth", waste.get("industrial_waste_kg", 0)) or 0)
    textile = float(waste.get("textileMaterialWasteKgPerMonth", waste.get("material_waste_kg", waste.get("textile_material_waste_kg", 0))) or 0)

    total = organic + plastic + paper + industrial + textile
    recycling_percent = float(waste.get("currentRecyclingPercent", waste.get("recycling_percentage", 0)) or 0)
    recycling_percent = max(0, min(100, recycling_percent))

    recyclable = total * (recycling_percent / 100.0)
    non_recyclable = total - recyclable

    has_segregation = waste.get("wasteSegregationPracticed", waste.get("waste_segregation", False))
    # Material recovery opportunity: if segregation false, extra 25% could be recovered; if recycling <50, gap to 50
    segregation_bonus = 0.25 if not has_segregation else 0.10
    recycling_gap = max(0, 50 - recycling_percent) / 100.0
    recovery_opportunity_kg = total * (segregation_bonus + recycling_gap * 0.5)
    recovery_opportunity_kg = min(recovery_opportunity_kg, total * 0.6)

    return {
        "total_waste_kg_per_month": round(total, 1),
        "annual_waste_kg": round(total * 12, 1),
        "recyclable_waste_kg_per_month": round(recyclable, 1),
        "non_recyclable_waste_kg_per_month": round(non_recyclable, 1),
        "recycling_rate_percent": recycling_percent,
        "material_recovery_opportunity_kg_per_month": round(recovery_opportunity_kg, 1),
        "material_recovery_opportunity_percent": round((recovery_opportunity_kg / total * 100) if total else 0, 1),
        "breakdown": {
            "organic": organic,
            "plastic": plastic,
            "paper": paper,
            "industrial": industrial,
            "textile_material": textile
        },
        "assumptions": [
            "Recyclable defined as recycling_percent of total; non-recyclable is remainder.",
            f"Recovery opportunity assumes segregation {'absent (+25%)' if not has_segregation else 'present (+10%)'} plus recycling gap to 50%.",
            "Capped at 60% to avoid overestimation."
        ]
    }

def calculate_emissions_metrics(assessment: dict) -> Dict[str, Any]:
    emissions = assessment.get("emissions", {})
    energy = assessment.get("energy", {})

    diesel = float(emissions.get("monthlyDieselLitres", emissions.get("diesel_litres", 0)) or 0)
    # fallback from energy generator fuel if emissions diesel 0?
    if diesel == 0:
        diesel = float(energy.get("generatorFuelLitresPerMonth", 0) or 0)
        # but also need to consider emissions diesel vs generator; we take max
        diesel = max(diesel, float(emissions.get("monthlyDieselLitres", 0) or 0))

    petrol = float(emissions.get("monthlyPetrolLitres", emissions.get("petrol_litres", 0)) or 0)
    natural_gas = float(emissions.get("monthlyNaturalGasKg", emissions.get("natural_gas_units", emissions.get("monthlyNaturalGasKg", 0))) or 0)

    monthly_kwh = float(energy.get("monthlyElectricityKwh", energy.get("monthly_electricity_kwh", 0)) or 0)

    diesel_factor = settings.DIESEL_EMISSION_FACTOR_KG_PER_LITRE
    petrol_factor = settings.PETROL_EMISSION_FACTOR_KG_PER_LITRE
    gas_factor = settings.NATURAL_GAS_EMISSION_FACTOR_KG_PER_KG
    electricity_factor = settings.ELECTRICITY_EMISSION_FACTOR_KG_PER_KWH

    diesel_emissions = diesel * diesel_factor / 1000.0
    petrol_emissions = petrol * petrol_factor / 1000.0
    gas_emissions = natural_gas * gas_factor / 1000.0
    electricity_emissions = monthly_kwh * electricity_factor / 1000.0

    total_monthly = diesel_emissions + petrol_emissions + gas_emissions + electricity_emissions

    ts = datetime.now(timezone.utc).isoformat()

    return {
        "monthly_diesel_litres": diesel,
        "monthly_petrol_litres": petrol,
        "monthly_natural_gas_kg": natural_gas,
        "monthly_electricity_kwh": monthly_kwh,
        "emissions_breakdown_tonnes_co2e_per_month": {
            "diesel": round(diesel_emissions, 2),
            "petrol": round(petrol_emissions, 2),
            "natural_gas": round(gas_emissions, 2),
            "electricity": round(electricity_emissions, 2),
            "total": round(total_monthly, 2)
        },
        "annual_total_tonnes_co2e": round(total_monthly * 12, 2),
        "factors_used": [
            {"factor": diesel_factor, "unit": "kg CO2e per litre diesel", "source_label": "Configurable DEFRA/IPCC derived, not certified", "calculation_timestamp": ts},
            {"factor": petrol_factor, "unit": "kg CO2e per litre petrol", "source_label": "Configurable, not certified", "calculation_timestamp": ts},
            {"factor": gas_factor, "unit": "kg CO2e per kg natural gas", "source_label": "Configurable, not certified", "calculation_timestamp": ts},
            {"factor": electricity_factor, "unit": "kg CO2e per kWh", "source_label": "Configurable grid factor, not certified", "calculation_timestamp": ts},
        ],
        "assumptions": [
            "Emissions are estimated, not verified carbon accounting. Not a certified footprint.",
            "Electricity emissions use same configurable factor as energy calculations.",
        ],
        "calculation_timestamp": ts,
        "calculation_version": settings.CALCULATION_VERSION
    }

def calculate_mobility_metrics(assessment: dict) -> Dict[str, Any]:
    mobility = assessment.get("mobility", {})
    vehicles = int(mobility.get("deliveryVehiclesCount", mobility.get("delivery_vehicles", 0)) or 0)
    monthly_fuel = float(mobility.get("monthlyFleetFuelLitres", mobility.get("monthly_fuel_litres", 0)) or 0)
    ev_percent = float(mobility.get("evAdoptedPercent", mobility.get("electric_vehicle_count", 0)) or 0)
    # Handle if electric_vehicle_count passed as count not percent
    ev_count = mobility.get("electricVehicleCount", mobility.get("electric_vehicle_count", None))
    # If assessment has electric_vehicle_count as number and vehicles>0, compute percent
    if ev_count is not None and vehicles > 0:
        # Check if ev_percent looks like count (if < vehicles and is integer-like)
        # We'll heuristic: if ev_percent came from electric_vehicle_count field and is count style, recalc
        # Actually front types: evAdoptedPercent is percent; so we keep as is, but also support count
        try:
            ev_count_val = float(ev_count)
            if ev_count_val <= vehicles and ev_percent == ev_count_val:
                # It was count, convert
                ev_percent = (ev_count_val / vehicles * 100) if vehicles else 0
        except:
            pass

    # Mobility emissions: assume diesel default unless fuel type indicates otherwise
    fuel_type = mobility.get("vehicleFuelType", mobility.get("vehicle_fuel_type", "Diesel"))
    # Choose factor based on fuel type for simplicity: Diesel 2.68, Petrol 2.31, CNG ~2.0, Electric 0.4 * grid?
    fuel_factor_map = {
        "Diesel": settings.DIESEL_EMISSION_FACTOR_KG_PER_LITRE,
        "Petrol": settings.PETROL_EMISSION_FACTOR_KG_PER_LITRE,
        "CNG": 2.0,
        "Electric": 0.5,
        "Mixed Fleet": 2.5
    }
    factor = fuel_factor_map.get(fuel_type, 2.68)
    monthly_mobility_emissions_tonnes = (monthly_fuel * factor) / 1000.0
    annual_mobility_emissions = monthly_mobility_emissions_tonnes * 12

    # EV adoption percentage
    ev_percent = max(0, min(100, ev_percent))
    # Potential improvement: transitioning remaining fleet to EV could cut emissions ~60%
    # Estimate potential: (100 - ev_percent)% * monthly_fuel * factor * 0.6 saving
    potential_monthly_fuel_saving = monthly_fuel * ((100 - ev_percent)/100.0) * 0.3  # assume route optimization + partial EV
    potential_emission_saving = potential_monthly_fuel_saving * factor / 1000.0

    return {
        "delivery_vehicles_count": vehicles,
        "vehicle_fuel_type": fuel_type,
        "monthly_fuel_litres": monthly_fuel,
        "annual_fuel_litres": round(monthly_fuel * 12, 1),
        "monthly_mobility_emissions_tonnes_co2e": round(monthly_mobility_emissions_tonnes, 2),
        "annual_mobility_emissions_tonnes_co2e": round(annual_mobility_emissions, 2),
        "ev_adopted_percent": ev_percent,
        "ev_adopted_count_estimate": round(vehicles * ev_percent / 100.0, 1),
        "potential_monthly_fuel_saving_litres": round(potential_monthly_fuel_saving, 1),
        "potentialMonthlyEmissionsSaving_tonnes": round(potential_emission_saving, 2),
        "potential_improvement_percent": round(((100 - ev_percent) * 0.6), 1) if vehicles else 0,
        "fuel_emission_factor_used": {
            "factor": factor,
            "unit": f"kg CO2e per litre {fuel_type}",
            "source_label": "Configurable, not certified",
            "calculation_timestamp": datetime.now(timezone.utc).isoformat()
        },
        "assumptions": [
            f"Mobility emission factor {factor} kg CO2/L based on {fuel_type} (configurable, not certified).",
            "Potential saving assumes 30% fuel reduction via EV + route optimization on non-electric fleet.",
            "EV adoption percent capped 0-100."
        ]
    }

def calculate_data_quality_score(profile: dict, assessment: dict) -> Dict[str, Any]:
    """
    Score completeness and reliability
    High: >85% fields filled, no defaults
    Medium: 60-85%
    Low: <60%
    """
    required_profile_fields = ["business_name","industry","business_type","location","employees","working_days","operating_hours","business_size"]
    # Map frontend names to backend
    # Check profile completeness
    filled_profile = 0
    missing_profile = []
    for f in required_profile_fields:
        # try multiple aliases
        aliases = {
            "business_name": ["business_name","name"],
            "industry": ["industry"],
            "business_type": ["business_type","businessType"],
            "location": ["location"],
            "employees": ["employees"],
            "working_days": ["working_days","workingDaysPerMonth"],
            "operating_hours": ["operating_hours","operatingHoursPerDay"],
            "business_size": ["business_size","businessSize"],
        }
        found = False
        for alias in aliases[f]:
            if profile.get(alias) not in [None, "", 0] or (alias in profile and profile[alias] == 0 and f in ["employees"]):
                # need to check 0 is valid? employees 0 is missing
                if profile.get(alias) not in [None, ""]:
                    if isinstance(profile.get(alias), (int,float)) and profile.get(alias) == 0 and f != "employees":
                        continue
                    found = True
                    break
        if found:
            filled_profile += 1
        else:
            missing_profile.append(f)

    # Assessment: count filled numeric and enums
    total_assessment_fields = 0
    filled_assessment = 0
    missing_assessment = []
    # Define sections fields to check
    sections = {
        "energy": ["monthly_electricity_kwh","monthly_electricity_cost","diesel_generator_usage","diesel_litres","existing_solar_kw","energy_efficient_equipment_percentage"],
        "water": ["monthly_water_litres","water_source","water_recycling","rainwater_harvesting","leakage_frequency","wastewater_treatment"],
        "waste": ["organic_waste_kg","plastic_waste_kg","paper_waste_kg","industrial_waste_kg","material_waste_kg","recycling_percentage","waste_segregation"],
        "emissions": ["primary_fuel","diesel_litres","petrol_litres","natural_gas_units","main_emission_sources","air_control_system"],
        "mobility": ["delivery_vehicles","vehicle_fuel_type","monthly_fuel_litres","employee_transport","electric_vehicle_count"],
        "green_practices": ["led_lighting","solar","rainwater_harvesting","water_recycling","waste_segregation","energy_efficient_machinery","ev_adoption","sustainable_materials"]
    }
    # Map frontend structure
    for section, fields in sections.items():
        sec_data = assessment.get(section, {})
        for fld in fields:
            total_assessment_fields += 1
            # need to map frontend camelCase
            # We'll check if any key exists in sec_data (case-insensitive?)
            # Instead we check if sec_data has any value
            # For frontend structure, section keys are camelCase but we handle both
            # Let's flatten check: if sec_data is dict and has any keys, consider filled if not None
            # We'll count per section overall.
            # Simplify: if section exists and has at least one key filled, count proportionally
            # Instead we do detailed check for frontend camelCase mapping
            frontend_map = {
                "monthly_electricity_kwh": ["monthlyElectricityKwh","monthly_electricity_kwh"],
                "monthly_electricity_cost": ["monthlyElectricityBillInr","monthly_electricity_cost"],
                "diesel_generator_usage": ["dieselGeneratorHoursPerMonth","diesel_generator_usage"],
                "diesel_litres": ["generatorFuelLitresPerMonth","diesel_litres","monthlyDieselLitres"],
                "existing_solar_kw": ["existingSolarCapacityKw","existing_solar_kw"],
                "energy_efficient_equipment_percentage": ["energyEfficientEquipmentPercent","energy_efficient_equipment_percentage"],
                "monthly_water_litres": ["monthlyWaterLitres","monthly_water_litres"],
                "water_source": ["waterSource","water_source"],
                "water_recycling": ["waterRecyclingAvailable","water_recycling","waterRecycling"],
                "rainwater_harvesting": ["rainwaterHarvesting","rainwater_harvesting"],
                "leakage_frequency": ["leakageFrequency","leakage_frequency"],
                "wastewater_treatment": ["wastewaterTreatment","wastewater_treatment"],
                "organic_waste_kg": ["organicWasteKgPerMonth","organic_waste_kg"],
                "plastic_waste_kg": ["plasticWasteKgPerMonth","plastic_waste_kg"],
                "paper_waste_kg": ["paperWasteKgPerMonth","paper_waste_kg"],
                "industrial_waste_kg": ["industrialWasteKgPerMonth","industrial_waste_kg"],
                "material_waste_kg": ["textileMaterialWasteKgPerMonth","material_waste_kg"],
                "recycling_percentage": ["currentRecyclingPercent","recycling_percentage"],
                "waste_segregation": ["wasteSegregationPracticed","waste_segregation","wasteSegregation"],
                "primary_fuel": ["primaryFuel","primary_fuel"],
                "diesel_litres": ["monthlyDieselLitres","diesel_litres"],
                "petrol_litres": ["monthlyPetrolLitres","petrol_litres"],
                "natural_gas_units": ["monthlyNaturalGasKg","natural_gas_units"],
                "main_emission_sources": ["mainEmissionSources","main_emission_sources"],
                "air_control_system": ["airPollutionControlSystem","air_control_system"],
                "delivery_vehicles": ["deliveryVehiclesCount","delivery_vehicles"],
                "vehicle_fuel_type": ["vehicleFuelType","vehicle_fuel_type"],
                "monthly_fuel_litres": ["monthlyFleetFuelLitres","monthly_fuel_litres"],
                "employee_transport": ["employeeCommuteMode","employee_transport"],
                "electric_vehicle_count": ["evAdoptedPercent","electric_vehicle_count","electricVehicleCount"],
                "led_lighting": ["ledLighting","led_lighting"],
                "solar": ["solarPanels","solar"],
                "energy_efficient_machinery": ["energyEfficientMachinery","energy_efficient_machinery"],
                "ev_adoption": ["evAdoption","ev_adoption"],
                "sustainable_materials": ["sustainableMaterials","sustainable_materials"],
            }
            aliases = frontend_map.get(fld, [fld])
            found = False
            for a in aliases:
                if a in sec_data and sec_data[a] not in [None, ""]:
                    found = True
                    break
            if found:
                filled_assessment += 1
            else:
                missing_assessment.append(f"{section}.{fld}")

    total_fields = len(required_profile_fields) + total_assessment_fields
    filled = filled_profile + filled_assessment
    completeness = (filled / total_fields * 100) if total_fields else 0

    if completeness >= 85:
        level = "High"
    elif completeness >= 60:
        level = "Medium"
    else:
        level = "Low"

    return {
        "completeness_percent": round(completeness, 1),
        "level": level,
        "filled_fields": filled,
        "total_fields": total_fields,
        "missing_profile_fields": missing_profile,
        "missing_assessment_fields": missing_assessment[:20],  # limit
        "total_missing": len(missing_profile) + len(missing_assessment),
        "message": f"Data quality is {level}. Completeness {completeness:.1f}%. {'Improve by filling missing fields to improve fingerprint confidence.' if level!='High' else 'Good completeness for decision support.'}"
    }
