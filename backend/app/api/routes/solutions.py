from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.services.solution_service import get_solutions, get_solution_by_id, get_personalized_recommendations
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Solutions"])

@router.get("", summary="List green solutions catalog")
async def list_solutions(category: Optional[str] = Query(None, description="Filter by category: Energy, Water, Waste, Mobility, Materials, Operations")):
    try:
        # Served from the in-code catalog; nothing is written to the database on read.
        sols = get_solutions(category)
        return {"solutions": sols, "count": len(sols), "category": category or "All"}
    except Exception as e:
        logger.error(f"List solutions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", summary="List green solutions catalog (slash)")
async def list_solutions_slash(category: Optional[str] = Query(None)):
    return await list_solutions(category)

@router.get("/recommendations", summary="Get personalized recommendations (top interventions)")
async def get_recommendations(top_n: int = Query(5, ge=1, le=12), user_id: str = Query("default")):
    try:
        recs = get_personalized_recommendations(user_id=user_id, top_n=top_n)
        return {"recommendations": recs, "count": len(recs)}
    except Exception as e:
        logger.error(f"Recommendations error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/recommendations/", summary="Get personalized recommendations (slash)")
async def get_recommendations_slash(top_n: int = Query(5, ge=1, le=12), user_id: str = Query("default")):
    return await get_recommendations(top_n, user_id)

@router.get("/{solution_id}", summary="Get solution by ID")
async def get_solution(solution_id: str):
    try:
        sol = get_solution_by_id(solution_id)
        if not sol:
            raise HTTPException(status_code=404, detail=f"Solution {solution_id} not found")
        return sol
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get solution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{solution_id}/", summary="Get solution by ID (slash)")
async def get_solution_slash(solution_id: str):
    return await get_solution(solution_id)
