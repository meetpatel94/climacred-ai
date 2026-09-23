from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime

class EnergyData(BaseModel):
    monthlyElectricityKwh: Optional[float] = Field(None, ge=0)
    monthly_electricity_kwh: Optional[float] = Field(None, ge=0, alias="monthly_electricity_kwh")
    monthlyElectricityBillInr: Optional[float] = Field(None, ge=0)
    monthly_electricity_cost: Optional[float] = Field(None, ge=0)
    monthly_electricity_bill_inr: Optional[float] = Field(None, ge=0)
    dieselGeneratorHoursPerMonth: Optional[float] = Field(None, ge=0)
    diesel_generator_usage: Optional[float] = Field(None, ge=0)
    generatorFuelLitresPerMonth: Optional[float] = Field(None, ge=0)
    diesel_litres: Optional[float] = Field(None, ge=0)
    existingSolarCapacityKw: Optional[float] = Field(None, ge=0)
    existing_solar_kw: Optional[float] = Field(None, ge=0)
    energyEfficientEquipmentPercent: Optional[float] = Field(None, ge=0, le=100)
    energy_efficient_equipment_percentage: Optional[float] = Field(None, ge=0, le=100)

    class Config:
        populate_by_name = True
        extra = "ignore"

class WaterData(BaseModel):
    monthlyWaterLitres: Optional[float] = Field(None, ge=0)
    monthly_water_litres: Optional[float] = Field(None, ge=0)
    waterSource: Optional[str] = None
    water_source: Optional[str] = None
    waterRecyclingAvailable: Optional[bool] = None
    water_recycling: Optional[bool] = None
    rainwaterHarvesting: Optional[bool] = None
    rainwater_harvesting: Optional[bool] = None
    leakageFrequency: Optional[str] = None
    leakage_frequency: Optional[str] = None
    wastewaterTreatment: Optional[str] = None
    wastewater_treatment: Optional[str] = None

    class Config:
        populate_by_name = True
        extra = "allow"

class WasteData(BaseModel):
    organicWasteKgPerMonth: Optional[float] = Field(None, ge=0)
    organic_waste_kg: Optional[float] = Field(None, ge=0)
    plasticWasteKgPerMonth: Optional[float] = Field(None, ge=0)
    plastic_waste_kg: Optional[float] = Field(None, ge=0)
    paperWasteKgPerMonth: Optional[float] = Field(None, ge=0)
    paper_waste_kg: Optional[float] = Field(None, ge=0)
    industrialWasteKgPerMonth: Optional[float] = Field(None, ge=0)
    industrial_waste_kg: Optional[float] = Field(None, ge=0)
    textileMaterialWasteKgPerMonth: Optional[float] = Field(None, ge=0)
    material_waste_kg: Optional[float] = Field(None, ge=0)
    currentRecyclingPercent: Optional[float] = Field(None, ge=0, le=100)
    recycling_percentage: Optional[float] = Field(None, ge=0, le=100)
    wasteSegregationPracticed: Optional[bool] = None
    waste_segregation: Optional[bool] = None

    class Config:
        populate_by_name = True
        extra = "ignore"

class EmissionsData(BaseModel):
    primaryFuel: Optional[str] = None
    primary_fuel: Optional[str] = None
    monthlyDieselLitres: Optional[float] = Field(None, ge=0)
    diesel_litres: Optional[float] = Field(None, ge=0)
    monthlyPetrolLitres: Optional[float] = Field(None, ge=0)
    petrol_litres: Optional[float] = Field(None, ge=0)
    monthlyNaturalGasKg: Optional[float] = Field(None, ge=0)
    natural_gas_units: Optional[float] = Field(None, ge=0)
    mainEmissionSources: Optional[List[str]] = None
    main_emission_sources: Optional[List[str]] = None
    airPollutionControlSystem: Optional[str] = None
    air_control_system: Optional[str] = None

    class Config:
        populate_by_name = True
        extra = "ignore"

class MobilityData(BaseModel):
    deliveryVehiclesCount: Optional[int] = Field(None, ge=0)
    delivery_vehicles: Optional[int] = Field(None, ge=0)
    vehicleFuelType: Optional[str] = None
    vehicle_fuel_type: Optional[str] = None
    monthlyFleetFuelLitres: Optional[float] = Field(None, ge=0)
    monthly_fuel_litres: Optional[float] = Field(None, ge=0)
    employeeCommuteMode: Optional[str] = None
    employee_transport: Optional[str] = None
    evAdoptedPercent: Optional[float] = Field(None, ge=0, le=100)
    electric_vehicle_count: Optional[float] = Field(None, ge=0)
    electricVehicleCount: Optional[int] = Field(None, ge=0)

    class Config:
        populate_by_name = True
        extra = "ignore"

class GreenPracticesData(BaseModel):
    ledLighting: Optional[bool] = None
    led_lighting: Optional[bool] = None
    solarPanels: Optional[bool] = None
    solar: Optional[bool] = None
    rainwaterHarvesting: Optional[bool] = None
    rainwater_harvesting: Optional[bool] = None
    waterRecycling: Optional[bool] = None
    water_recycling: Optional[bool] = None
    wasteSegregation: Optional[bool] = None
    waste_segregation: Optional[bool] = None
    energyEfficientMachinery: Optional[bool] = None
    energy_efficient_machinery: Optional[bool] = None
    evAdoption: Optional[bool] = None
    ev_adoption: Optional[bool] = None
    sustainableMaterials: Optional[bool] = None
    sustainable_materials: Optional[bool] = None

    class Config:
        populate_by_name = True
        extra = "allow"

class ClimateAssessmentBase(BaseModel):
    energy: Optional[EnergyData] = None
    water: Optional[WaterData] = None
    waste: Optional[WasteData] = None
    emissions: Optional[EmissionsData] = None
    mobility: Optional[MobilityData] = None
    greenPractices: Optional[GreenPracticesData] = None
    green_practices: Optional[GreenPracticesData] = None

    class Config:
        populate_by_name = True
        extra = "allow"

class ClimateAssessmentCreate(ClimateAssessmentBase):
    pass

class ClimateAssessmentUpdate(ClimateAssessmentBase):
    pass

class ClimateAssessmentResponse(ClimateAssessmentBase):
    id: Optional[str] = None
    user_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
