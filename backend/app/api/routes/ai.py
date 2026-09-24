"""
Gemini AI routes.

  GET    /api/ai/status                       real Gemini connection check (cached briefly)
  POST   /api/ai/chat                         {"message", "conversation_id"} -> {"answer", "provider", "model", "conversation_id"}
  DELETE /api/ai/chat/{conversation_id}       clear a conversation ("Clear chat")
  GET    /api/ai/chat/suggestions             starter questions + whether stored data exists
  GET    /api/ai/dashboard-insights           Gemini insight for the dashboard (auto-loaded)

Every Gemini call happens server-side with the key from backend/.env. AI endpoints
answer HTTP 200 with an explicit "status" field ("ok" / "no_data" / "not_configured" /
"unreachable" / "error") and a safe message, so the UI can show the exact state
without the browser logging failed requests. Raw provider errors are only logged.
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException, Query

from app.services import gemini_client
from app.services.ai_chat_service import SUGGESTIONS, answer_question, delete_conversation
from app.services.ai_insight_service import get_dashboard_insights

logger = logging.getLogger(__name__)
router = APIRouter(tags=["AI Intelligence"])


@router.get("/status", summary="Real Gemini connection status (key, verified model, live generateContent)")
async def ai_status(refresh: bool = Query(False, description="Bypass the short status cache and re-check now")):
    """
    - ``not_configured``: GEMINI_API_KEY missing in backend/.env (no network call).
    - ``connected``: the model was verified via the models API AND a real tiny
      generateContent request succeeded. A key that merely exists is NOT "connected".
    - ``unreachable``: the Gemini API could not be reached from the server.
    - ``error``: Gemini answered with an error (invalid key, model not found /
      not available to this project, quota, ...) - see ``message`` / ``error_code``.
    The API key is never part of the response.
    """
    return await gemini_client.check_status(force=refresh)


@router.post("/chat", summary="ClimaCred AI Assistant (Gemini, grounded in the user's stored data)")
async def ai_chat(payload: Dict[str, Any] = Body(...)):
    """
    Request:  {"message": "What's my biggest climate risk?", "conversation_id": "optional-id"}
    Response: {"answer": "...", "provider": "gemini", "model": "...", "conversation_id": "...",
               "status": "ok", "has_data": true, "number_audit": {...}}

    When Gemini cannot answer, ``answer`` is null and ``status``/``message`` say why.
    Omit ``conversation_id`` to start a new conversation; reuse the returned id for follow-ups.
    """
    body = payload or {}
    message = body.get("message") or body.get("question") or ""
    conversation_id: Optional[str] = body.get("conversation_id") or body.get("conversationId")
    history: Optional[List[Dict[str, Any]]] = body.get("history") if isinstance(body.get("history"), list) else None
    if not str(message).strip():
        raise HTTPException(status_code=400, detail="Please type a question.")
    try:
        return await answer_question(str(message), conversation_id=conversation_id, history=history)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(f"AI chat failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="AI assistant failed unexpectedly (see server log).")


@router.delete("/chat/{conversation_id}", summary="Clear one conversation's server-side memory")
async def ai_chat_clear(conversation_id: str):
    return {"conversation_id": conversation_id, "cleared": delete_conversation(conversation_id)}


@router.get("/chat/suggestions", summary="Suggested starter questions for the chat assistant")
async def chat_suggestions():
    from app.services.assessment_service import has_business_data

    return {"has_data": has_business_data(), "suggestions": list(SUGGESTIONS)}


@router.get("/dashboard-insights", summary="Gemini climate intelligence for the dashboard (auto-loaded)")
async def dashboard_insights(
    refresh: bool = Query(False, description="Bypass the cache and regenerate the insight"),
):
    """
    Gemini interpretation of the user's latest stored data (What Changed, Key Risk,
    What To Do Next, Trend / Forecast, Expected Impact). Cached per data signature.
    ``status`` is "no_data" (nothing stored, no AI call), "ok", or the Gemini
    connection problem ("not_configured" / "unreachable" / "error") with ``insight`` null.
    """
    try:
        return await get_dashboard_insights(force=refresh)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(f"Dashboard AI insight failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="AI insight failed unexpectedly (see server log).")


@router.get("/dashboard-insights/", include_in_schema=False)
async def dashboard_insights_slash(refresh: bool = Query(False)):
    return await dashboard_insights(refresh=refresh)
