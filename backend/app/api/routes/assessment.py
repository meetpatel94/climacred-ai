from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any
from app.services.assessment_service import get_assessment, save_assessment, patch_assessment
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Assessment"])

@router.get("", summary="Get climate assessment")
async def get_assessment_route():
    try:
        return get_assessment()
    except Exception as e:
        logger.error(f"Get assessment error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", summary="Get climate assessment (slash)")
async def get_assessment_route_slash():
    return await get_assessment_route()

@router.post("", summary="Create or update climate assessment")
async def post_assessment_route(data: Dict[str, Any] = Body(...)):
    try:
        result = save_assessment(data)
        # Also potentially return fingerprint? Spec doesn't require but we can include message
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Post assessment error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", summary="Create or update climate assessment (slash)")
async def post_assessment_route_slash(data: Dict[str, Any] = Body(...)):
    return await post_assessment_route(data)

@router.patch("", summary="Patch climate assessment")
async def patch_assessment_route(data: Dict[str, Any] = Body(...)):
    try:
        return patch_assessment(data)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Patch assessment error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/", summary="Patch climate assessment (slash)")
async def patch_assessment_route_slash(data: Dict[str, Any] = Body(...)):
    return await patch_assessment_route(data)

# Additional endpoint for validation preview
@router.post("/validate", summary="Validate assessment data")
async def validate_assessment_route(data: Dict[str, Any] = Body(...)):
    from app.utils.validation import validate_assessment_data
    try:
        validate_assessment_data(data)
        return {"valid": True, "message": "Assessment data valid"}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
