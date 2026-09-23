from typing import Any, Dict

def validate_non_negative(value: Any, field: str):
    if value is not None and isinstance(value, (int, float)) and value < 0:
        raise ValueError(f"{field} cannot be negative")

def validate_percentage(value: Any, field: str):
    if value is not None and isinstance(value, (int, float)):
        if not 0 <= value <= 100:
            raise ValueError(f"{field} must be between 0 and 100")

def validate_business_profile(data: Dict[str, Any]):
    # Validate employees, operating_hours, etc.
    employees = data.get("employees")
    if employees is not None and employees < 0:
        raise ValueError("employees cannot be negative")
    if employees is not None and employees > 100000:
        raise ValueError("employees exceeds reasonable range (0-100000)")
    working_days = data.get("working_days") or data.get("workingDaysPerMonth")
    if working_days is not None:
        if not 1 <= working_days <= 31:
            raise ValueError("working_days must be 1-31")
    operating_hours = data.get("operating_hours") or data.get("operatingHoursPerDay")
    if operating_hours is not None:
        if not 1 <= operating_hours <= 24:
            raise ValueError("operating_hours must be 1-24")
    facility = data.get("facility_area_sqft") or data.get("facilityAreaSqFt")
    if facility is not None and facility < 0:
        raise ValueError("facility_area_sqft cannot be negative")

def validate_assessment_data(data: Dict[str, Any]):
    # Energy validation
    energy = data.get("energy", {})
    for k in ["monthlyElectricityKwh","monthly_electricity_kwh","monthlyElectricityBillInr","monthly_electricity_cost","dieselGeneratorHoursPerMonth","generatorFuelLitresPerMonth","existingSolarCapacityKw","energyEfficientEquipmentPercent"]:
        if k in energy and energy[k] is not None:
            if isinstance(energy[k], (int,float)) and energy[k] < 0:
                raise ValueError(f"energy.{k} cannot be negative")
    if "energyEfficientEquipmentPercent" in energy:
        validate_percentage(energy["energyEfficientEquipmentPercent"], "energy.energyEfficientEquipmentPercent")
    if "energy_efficient_equipment_percentage" in energy:
        validate_percentage(energy["energy_efficient_equipment_percentage"], "energy.energy_efficient_equipment_percentage")

    # Water
    water = data.get("water", {})
    for k in ["monthlyWaterLitres","monthly_water_litres"]:
        if k in water and water[k] is not None and water[k] < 0:
            raise ValueError(f"water.{k} cannot be negative")

    # Waste
    waste = data.get("waste", {})
    for k in ["organicWasteKgPerMonth","plasticWasteKgPerMonth","paperWasteKgPerMonth","industrialWasteKgPerMonth","textileMaterialWasteKgPerMonth","currentRecyclingPercent","recycling_percentage"]:
        if k in waste and waste[k] is not None:
            if isinstance(waste[k], (int,float)) and waste[k] < 0:
                raise ValueError(f"waste.{k} cannot be negative")
    if "currentRecyclingPercent" in waste:
        validate_percentage(waste["currentRecyclingPercent"], "waste.currentRecyclingPercent")
    if "recycling_percentage" in waste:
        validate_percentage(waste["recycling_percentage"], "waste.recycling_percentage")

    # Mobility EV check
    mobility = data.get("mobility", {})
    vehicles = mobility.get("deliveryVehiclesCount", mobility.get("delivery_vehicles", 0))
    ev_percent = mobility.get("evAdoptedPercent")
    if ev_percent is not None:
        validate_percentage(ev_percent, "mobility.evAdoptedPercent")
    ev_count = mobility.get("electric_vehicle_count")
    if ev_count is not None and vehicles is not None:
        if isinstance(ev_count, (int,float)) and isinstance(vehicles, (int,float)):
            if ev_count < 0:
                raise ValueError("mobility.electric_vehicle_count cannot be negative")
            if ev_count > vehicles:
                raise ValueError("EV count cannot exceed total vehicle count")

    # Emissions
    emissions = data.get("emissions", {})
    for k in ["monthlyDieselLitres","monthlyPetrolLitres","monthlyNaturalGasKg","diesel_litres","petrol_litres","natural_gas_units"]:
        if k in emissions and emissions[k] is not None and emissions[k] < 0:
            raise ValueError(f"emissions.{k} cannot be negative")

def sanitize_mongo_query(query: dict) -> dict:
    # Prevent unsafe queries: disallow keys starting with $
    safe = {}
    for k, v in query.items():
        if k.startswith("$"):
            continue
        if isinstance(v, dict):
            # recurse but filter $
            filtered = {kk: vv for kk, vv in v.items() if not kk.startswith("$")}
            safe[k] = filtered
        else:
            safe[k] = v
    return safe
