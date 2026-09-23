from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any
from app.services.transformation_service import get_transformation_plan, generate_transformation_plan, update_plan_item_status
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Transformation Plan"])

@router.get("", summary="Get transformation plan")
async def get_plan():
    try:
        items = get_transformation_plan()
        return {"plan": items, "count": len(items)}
    except Exception as e:
        logger.error(f"Get transformation plan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", summary="Get transformation plan (slash)")
async def get_plan_slash():
    return await get_plan()

@router.post("/generate", summary="Generate transformation plan (personalized)")
async def generate_plan():
    try:
        items = generate_transformation_plan()
        return {"plan": items, "count": len(items), "generated": True}
    except Exception as e:
        logger.error(f"Generate plan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate/", summary="Generate transformation plan (slash)")
async def generate_plan_slash():
    return await generate_plan()

@router.patch("/{item_id}", summary="Update transformation plan item status")
async def update_item(item_id: str, payload: Dict[str, Any] = Body(...)):
    try:
        status = payload.get("status") or payload.get("new_status")
        if not status:
            raise HTTPException(status_code=400, detail="status field required (Pending, In Progress, Completed)")
        items = update_plan_item_status(item_id, status)
        return {"plan": items, "updated_id": item_id, "new_status": status}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Update plan item error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{item_id}/", summary="Update transformation plan item status (slash)")
async def update_item_slash(item_id: str, payload: Dict[str, Any] = Body(...)):
    return await update_item(item_id, payload)
