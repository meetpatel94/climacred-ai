from fastapi import APIRouter, HTTPException
from app.services.fingerprint_service import (
    get_latest_fingerprint,
    generate_and_save_fingerprint,
    get_or_generate_fingerprint,
    get_fingerprint_history,
)
from app.services.assessment_service import has_assessment_data
from app.utils.calculations import calculate_energy_metrics, calculate_water_metrics, calculate_waste_metrics, calculate_emissions_metrics, calculate_mobility_metrics, calculate_data_quality_score
from app.services.profile_service import get_profile
from app.services.assessment_service import get_assessment
from app.climate_engine.anomaly_detection import detect_anomalies
from app.climate_engine.forecasting import forecast_consumption
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Climate Fingerprint"])

@router.get("", summary="Get latest climate fingerprint (null until real data exists)")
async def get_fingerprint():
    try:
        # Returns null when the user has no stored data - the frontend then shows
        # "Complete your Climate Assessment to generate your Climate Fingerprint."
        return get_or_generate_fingerprint()
    except Exception as e:
        logger.error(f"Get fingerprint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", summary="Get latest climate fingerprint (slash)")
async def get_fingerprint_slash():
    return await get_fingerprint()

@router.get("/history", summary="Stored fingerprint snapshots used for real historical charts")
async def fingerprint_history(limit: int = 24):
    try:
        snapshots = get_fingerprint_history(limit=limit)
        return {"snapshots": snapshots, "count": len(snapshots)}
    except Exception as e:
        logger.error(f"Fingerprint history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate", summary="Generate climate fingerprint from current profile & assessment")
async def generate_fingerprint():
    try:
        fp = generate_and_save_fingerprint()
        return fp
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Generate fingerprint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate/", summary="Generate climate fingerprint (slash)")
async def generate_fingerprint_slash():
    return await generate_fingerprint()

# Additional analytics endpoints
def _no_data(domain: str) -> dict:
    """Uniform empty-state payload for analytics endpoints (no fabricated zeros)."""
    return {
        "available": False,
        "domain": domain,
        "message": f"No {domain} data yet",
        "reason": "No climate assessment data is stored for this business yet.",
    }


def _has_any_data() -> bool:
    return has_assessment_data(get_assessment())


@router.get("/analytics/energy", summary="Get energy analytics")
async def get_energy_analytics():
    try:
        if not _has_any_data():
            return _no_data("energy")
        return {**calculate_energy_metrics(get_assessment(), get_profile()), "available": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/water", summary="Get water analytics")
async def get_water_analytics():
    try:
        if not _has_any_data():
            return _no_data("water")
        return {**calculate_water_metrics(get_assessment(), get_profile()), "available": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/waste", summary="Get waste analytics")
async def get_waste_analytics():
    try:
        if not _has_any_data():
            return _no_data("waste")
        return {**calculate_waste_metrics(get_assessment()), "available": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/emissions", summary="Get emissions analytics")
async def get_emissions_analytics():
    try:
        if not _has_any_data():
            return _no_data("emissions")
        return {**calculate_emissions_metrics(get_assessment()), "available": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/mobility", summary="Get mobility analytics")
async def get_mobility_analytics():
    try:
        if not _has_any_data():
            return _no_data("mobility")
        return {**calculate_mobility_metrics(get_assessment()), "available": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/data-quality", summary="Get data quality score")
async def get_data_quality():
    try:
        if not _has_any_data():
            return _no_data("assessment")
        return {**calculate_data_quality_score(get_profile(), get_assessment()), "available": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/anomaly-detection", summary="Run anomaly detection (requires historical data)")
async def anomaly_detection(payload: dict):
    # payload: {historical_data: [...], metric_key: "consumptionKwh"}
    historical = payload.get("historical_data") or payload.get("historicalData") or []
    metric_key = payload.get("metric_key") or payload.get("metricKey") or "consumptionKwh"
    try:
        return detect_anomalies(historical, metric_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/forecast", summary="Run forecasting (requires historical data)")
async def forecasting(payload: dict):
    historical = payload.get("historical_data") or payload.get("historicalData") or []
    metric_key = payload.get("metric_key") or payload.get("metricKey") or "consumptionKwh"
    periods = payload.get("periods", 3)
    try:
        return forecast_consumption(historical, metric_key, periods)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
