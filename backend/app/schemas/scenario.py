from pydantic import BaseModel, Field
from typing import List, Optional

class ScenarioSimulateRequest(BaseModel):
    selected_solution_ids: List[str] = Field(..., description="List of solution IDs to simulate")
    selectedSolutionIds: Optional[List[str]] = None
    adoption_scale_percent: Optional[int] = Field(100, ge=25, le=100, description="Implementation scale 25-100%")
    adoptionScalePercent: Optional[int] = None

    class Config:
        populate_by_name = True
        extra = "allow"

    def get_selected_ids(self) -> List[str]:
        if self.selected_solution_ids:
            return self.selected_solution_ids
        if self.selectedSolutionIds:
            return self.selectedSolutionIds
        return []

    def get_scale(self) -> int:
        if self.adoption_scale_percent is not None and self.adoption_scale_percent != 100:
            return self.adoption_scale_percent
        if self.adoptionScalePercent is not None:
            return self.adoptionScalePercent
        return 100

class ScenarioResponse(BaseModel):
    selected_solutions: List[str]
    current_state: dict
    projected_state: dict
    investment: dict
    totalInvestmentInr: int
    totalAnnualSavingsInr: int
    energy_change: dict
    water_change: dict
    waste_change: dict
    emission_change: dict
    payback_period_years: float
    projected_climate_score: int
    assumptions: List[str]

    class Config:
        extra = "allow"
