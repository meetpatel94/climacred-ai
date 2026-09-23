from pydantic import BaseModel, Field, field_validator, EmailStr
from typing import Optional
from datetime import datetime

class BusinessProfileBase(BaseModel):
    business_name: Optional[str] = Field(None, alias="business_name", description="Business legal name")
    name: Optional[str] = Field(None, description="Alias for business_name frontend")
    industry: Optional[str] = Field(None, description="Industry sector")
    business_type: Optional[str] = Field(None, alias="business_type")
    businessType: Optional[str] = Field(None)
    location: Optional[str] = None
    employees: Optional[int] = Field(None, ge=0, le=100000)
    working_days: Optional[int] = Field(None, alias="working_days", ge=1, le=31)
    workingDaysPerMonth: Optional[int] = Field(None, ge=1, le=31)
    production_volume: Optional[str] = None
    productionVolume: Optional[str] = None
    operating_hours: Optional[int] = Field(None, ge=1, le=24)
    operatingHoursPerDay: Optional[int] = Field(None, ge=1, le=24)
    business_size: Optional[str] = Field(None, description="Micro, Small, Medium, Mid-Market")
    businessSize: Optional[str] = None
    facility_area_sqft: Optional[float] = Field(None, ge=0)
    facilityAreaSqFt: Optional[float] = Field(None, ge=0)
    contact_email: Optional[str] = None
    contactEmail: Optional[str] = None
    phone: Optional[str] = None

    class Config:
        populate_by_name = True
        extra = "ignore"

class BusinessProfileCreate(BusinessProfileBase):
    pass

class BusinessProfileUpdate(BusinessProfileBase):
    pass

class BusinessProfileResponse(BaseModel):
    id: Optional[str] = None
    business_name: str
    name: str
    industry: str
    business_type: str
    businessType: str
    location: str
    employees: int
    working_days: int
    workingDaysPerMonth: int
    production_volume: str
    productionVolume: str
    operating_hours: int
    operatingHoursPerDay: int
    business_size: str
    businessSize: str
    facility_area_sqft: float
    facilityAreaSqFt: float
    contact_email: str
    contactEmail: str
    phone: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
