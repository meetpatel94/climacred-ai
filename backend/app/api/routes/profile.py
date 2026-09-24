from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any
from app.services.profile_service import get_profile, create_or_update_profile, reset_profile, patch_profile
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Profile"])

@router.get("", summary="Get business profile (null when the user has not created one yet)")
async def get_business_profile():
    try:
        return get_profile()
    except Exception as e:
        logger.error(f"Get profile error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", summary="Get business profile (slash)")
async def get_business_profile_slash():
    return await get_business_profile()

@router.patch("", summary="Update business profile (PATCH)")
async def patch_business_profile(data: Dict[str, Any] = Body(...)):
    try:
        return patch_profile(data)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Patch profile error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/", summary="Update business profile (PATCH slash)")
async def patch_business_profile_slash(data: Dict[str, Any] = Body(...)):
    return await patch_business_profile(data)

@router.post("", summary="Create or update business profile (POST)")
async def post_business_profile(data: Dict[str, Any] = Body(...)):
    try:
        return create_or_update_profile(data)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Post profile error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", summary="Create or update business profile (POST slash)")
async def post_business_profile_slash(data: Dict[str, Any] = Body(...)):
    return await post_business_profile(data)

@router.post("/reset", summary="Clear the stored business profile (returns null)")
async def reset_business_profile():
    try:
        return reset_profile()
    except Exception as e:
        logger.error(f"Reset profile error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset/", summary="Reset business profile to default (slash)")
async def reset_business_profile_slash():
    return await reset_business_profile()
