from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, List
from app.services.scenario_service import simulate_scenario, get_scenario_history
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Scenarios"])

@router.post("/simulate", summary="Simulate scenario with selected solutions")
async def simulate(payload: Dict[str, Any] = Body(...)):
    try:
        selected = payload.get("selected_solution_ids") or payload.get("selectedSolutionIds") or payload.get("selected_solutions") or []
        # Also support single list under "solution_ids"
        if not selected and "solution_ids" in payload:
            selected = payload["solution_ids"]
        scale = payload.get("adoption_scale_percent") or payload.get("adoptionScalePercent") or payload.get("scale") or 100
        if isinstance(scale, str):
            try:
                scale = int(scale)
            except:
                scale = 100
        if not selected:
            raise HTTPException(status_code=400, detail="selected_solution_ids required (at least one solution ID)")
        result = simulate_scenario(selected, adoption_scale_percent=scale)
        return result
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Simulate error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/simulate/", summary="Simulate scenario (slash)")
async def simulate_slash(payload: Dict[str, Any] = Body(...)):
    return await simulate(payload)

@router.get("/history", summary="Get scenario simulation history")
async def history(limit: int = 10):
    try:
        return {"history": get_scenario_history(limit=limit)}
    except Exception as e:
        logger.error(f"Scenario history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/", summary="Get scenario history (slash)")
async def history_slash(limit: int = 10):
    return await history(limit)

# Also support GET /scenarios for listing? Not needed but provide
@router.get("", summary="Get scenarios (list history)")
async def list_scenarios(limit: int = 10):
    return await history(limit)

@router.get("/", summary="Get scenarios (list history slash)")
async def list_scenarios_slash(limit: int = 10):
    return await history(limit)
