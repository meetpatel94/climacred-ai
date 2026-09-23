from fastapi import APIRouter, HTTPException
from app.services.fingerprint_service import get_latest_fingerprint, generate_and_save_fingerprint, get_or_generate_fingerprint
from app.utils.calculations import calculate_energy_metrics, calculate_water_metrics, calculate_waste_metrics, calculate_emissions_metrics, calculate_mobility_metrics, calculate_data_quality_score
from app.services.profile_service import get_profile
from app.services.assessment_service import get_assessment
from app.climate_engine.anomaly_detection import detect_anomalies
from app.climate_engine.forecasting import forecast_consumption
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Climate Fingerprint"])

@router.get("", summary="Get latest climate fingerprint")
async def get_fingerprint():
    try:
        fp = get_latest_fingerprint()
        if not fp:
            # If none, generate
            fp = generate_and_save_fingerprint()
        return fp
    except Exception as e:
        logger.error(f"Get fingerprint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", summary="Get latest climate fingerprint (slash)")
async def get_fingerprint_slash():
    return await get_fingerprint()

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
@router.get("/analytics/energy", summary="Get energy analytics")
async def get_energy_analytics():
    try:
        assessment = get_assessment()
        profile = get_profile()
        return calculate_energy_metrics(assessment, profile)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/water", summary="Get water analytics")
async def get_water_analytics():
    try:
        assessment = get_assessment()
        profile = get_profile()
        return calculate_water_metrics(assessment, profile)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/waste", summary="Get waste analytics")
async def get_waste_analytics():
    try:
        assessment = get_assessment()
        return calculate_waste_metrics(assessment)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/emissions", summary="Get emissions analytics")
async def get_emissions_analytics():
    try:
        assessment = get_assessment()
        return calculate_emissions_metrics(assessment)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/mobility", summary="Get mobility analytics")
async def get_mobility_analytics():
    try:
        assessment = get_assessment()
        return calculate_mobility_metrics(assessment)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/data-quality", summary="Get data quality score")
async def get_data_quality():
    try:
        profile = get_profile()
        assessment = get_assessment()
        return calculate_data_quality_score(profile, assessment)
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
