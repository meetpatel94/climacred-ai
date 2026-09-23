from fastapi import APIRouter, HTTPException
from app.services.report_service import generate_climate_report, get_latest_report, get_report_history
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Reports"])

@router.get("/climate", summary="Get latest climate report")
async def get_climate_report():
    try:
        report = get_latest_report()
        if not report:
            report = generate_climate_report()
        return report
    except Exception as e:
        logger.error(f"Get report error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/climate/", summary="Get latest climate report (slash)")
async def get_climate_report_slash():
    return await get_climate_report()

@router.post("/climate/generate", summary="Generate new climate report")
async def generate_report():
    try:
        report = generate_climate_report()
        return report
    except Exception as e:
        logger.error(f"Generate report error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/climate/generate/", summary="Generate new climate report (slash)")
async def generate_report_slash():
    return await generate_report()

@router.get("/history", summary="Get report history")
async def report_history(limit: int = 10):
    try:
        history = get_report_history(limit=limit)
        return {"reports": history, "count": len(history)}
    except Exception as e:
        logger.error(f"Report history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
