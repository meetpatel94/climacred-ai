from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class ClimateReportGenerateRequest(BaseModel):
    include_forecast: Optional[bool] = False
    include_anomalies: Optional[bool] = False

    class Config:
        extra = "allow"

class ClimateReportResponse(BaseModel):
    report_id: str
    generated_at: datetime
    data_period: str
    calculation_version: str
    business_profile: Dict[str, Any]
    climate_readiness: Dict[str, Any]
    climate_fingerprint: Dict[str, Any]
    energy_analysis: Dict[str, Any]
    water_analysis: Dict[str, Any]
    waste_analysis: Dict[str, Any]
    emissions_analysis: Dict[str, Any]
    mobility_analysis: Dict[str, Any]
    top_priorities: List[str]
    recommended_solutions: List[Dict[str, Any]]
    scenario_analysis: Optional[Dict[str, Any]] = None
    transformation_plan: List[Dict[str, Any]]
    impact_verification: List[Dict[str, Any]]
    assumptions: List[str]
    methodology: Dict[str, Any]
    data_quality: Dict[str, Any]

    class Config:
        extra = "allow"
