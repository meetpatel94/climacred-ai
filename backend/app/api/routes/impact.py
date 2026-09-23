from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any
from app.services.impact_service import create_impact_record, get_impact_records, get_latest_impact_as_verification_metrics
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Impact Verification"])

@router.get("", summary="Get impact verification records")
async def get_impact():
    try:
        records = get_impact_records()
        # Also provide derived verification metrics for frontend compat
        metrics = get_latest_impact_as_verification_metrics()
        return {"records": records, "metrics": metrics, "count": len(records)}
    except Exception as e:
        logger.error(f"Get impact error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", summary="Get impact verification records (slash)")
async def get_impact_slash():
    return await get_impact()

@router.get("/metrics", summary="Get impact verification metrics (frontend shaped)")
async def get_impact_metrics():
    try:
        metrics = get_latest_impact_as_verification_metrics()
        return {"metrics": metrics}
    except Exception as e:
        logger.error(f"Get impact metrics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics/", summary="Get impact verification metrics (slash)")
async def get_impact_metrics_slash():
    return await get_impact_metrics()

@router.post("", summary="Submit post-implementation impact data")
async def post_impact(data: Dict[str, Any] = Body(...)):
    try:
        # Support both {before, after} and {metrics} styles
        record = create_impact_record(data)
        return record
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Post impact error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", summary="Submit post-implementation impact data (slash)")
async def post_impact_slash(data: Dict[str, Any] = Body(...)):
    return await post_impact(data)
