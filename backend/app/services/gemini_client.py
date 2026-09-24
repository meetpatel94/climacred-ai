"""
Google Gemini gateway - the ONLY module that talks to the Gemini API.

Why this module exists (root cause of the old "Gemini API error 404")
--------------------------------------------------------------------
The previous code sent generateContent requests blindly to a hardcoded chain
``gemini-2.5-flash -> gemini-2.0-flash -> gemini-1.5-flash``. As of 2026:

* ``gemini-1.5-*`` models are shut down (404 for everyone),
* ``gemini-2.0-flash`` was shut down on 2026-06-01 (404 for everyone),
* ``gemini-2.5-*`` models are restricted to projects that already used them;
  keys from newer projects get ``404 "... is no longer available to new users"``.

So every candidate could return 404 and the UI showed "Gemini API error 404".

What this module does instead
-----------------------------
* Uses the official Gemini REST API (``/v1beta``): ``models.list``,
  ``models.get`` and ``models.generateContent``. Authentication uses the
  ``x-goog-api-key`` header (works for standard and authorization keys), so the
  key never appears in a URL, a log line, a response body or the database.
* Verifies a model before using it: it must exist for this key, list
  ``generateContent`` in ``supportedGenerationMethods`` AND answer a tiny real
  ``generateContent`` probe. With ``GEMINI_MODEL`` empty, the newest stable
  Flash-family model that the API reports for this key is selected the same way.
* Classifies failures precisely (invalid key, API disabled, model not found,
  model restricted to existing projects, quota, network) and exposes a
  *safe* message for users. Raw provider messages are logged server-side only.
* Caches the status briefly so the navbar indicator does not spam the API.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

PROVIDER = "Google Gemini"
PROBE_PROMPT = "Reply with the single word OK."
MAX_AUTO_PROBES = 4
#: Delay before the single retry of a transient 5xx error (patched to 0 in tests).
RETRY_DELAY_SECONDS = 1.0

# --- error categories -------------------------------------------------------
NOT_CONFIGURED = "not_configured"
UNREACHABLE = "unreachable"
TIMEOUT = "timeout"
AUTH = "auth"
MODEL_NOT_FOUND = "model_not_found"
MODEL_UNAVAILABLE = "model_unavailable"
NO_MODEL = "no_usable_model"
QUOTA = "quota"
BAD_REQUEST = "bad_request"
UPSTREAM = "upstream_error"
BLOCKED = "blocked"
EMPTY = "empty_response"
INVALID_RESPONSE = "invalid_response"

# Public status values returned by GET /api/ai/status
STATUS_CONNECTED = "connected"
STATUS_NOT_CONFIGURED = "not_configured"
STATUS_UNREACHABLE = "unreachable"
STATUS_ERROR = "error"


class GeminiError(Exception):
    """A classified Gemini failure. ``user_message`` is safe to show in the UI."""

    def __init__(
        self,
        category: str,
        user_message: str,
        *,
        http_status: Optional[int] = None,
        reason: Optional[str] = None,
        model: Optional[str] = None,
        available_models: Optional[List[str]] = None,
    ) -> None:
        super().__init__(user_message)
        self.category = category
        self.user_message = user_message
        self.http_status = http_status
        self.reason = reason
        self.model = model
        self.available_models = available_models

    @property
    def status(self) -> str:
        if self.category == NOT_CONFIGURED:
            return STATUS_NOT_CONFIGURED
        if self.category == UNREACHABLE:
            return STATUS_UNREACHABLE
        return STATUS_ERROR


@dataclass
class GenerateResult:
    text: str
    model: str
    finish_reason: Optional[str] = None
    model_version: Optional[str] = None
    usage: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------
def api_key() -> str:
    return (settings.GEMINI_API_KEY or "").strip()


def configured() -> bool:
    return bool(api_key())


def normalize_model_name(name: Optional[str]) -> str:
    """'models/gemini-x' or ' gemini-x ' -> 'gemini-x' (a 'models/' prefix used to double up in URLs)."""
    value = (name or "").strip()
    if value.startswith("models/"):
        value = value[len("models/"):]
    return value


def configured_model() -> str:
    return normalize_model_name(settings.GEMINI_MODEL)


def api_base() -> str:
    base = (settings.GEMINI_API_BASE or "https://generativelanguage.googleapis.com/v1beta").strip().rstrip("/")
    if base.endswith("/models"):
        base = base[: -len("/models")]
    return base


def api_version() -> str:
    return api_base().rsplit("/", 1)[-1]


def _redact(text: Any) -> str:
    value = "" if text is None else str(text)
    key = api_key()
    if key and key in value:
        value = value.replace(key, "[REDACTED]")
    return value


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# HTTP layer
# ---------------------------------------------------------------------------
def _parse_error(response: Any) -> Dict[str, Optional[str]]:
    body: Any = None
    try:
        body = response.json()
    except Exception:  # noqa: BLE001 - non-JSON error bodies
        body = None
    err = body.get("error") if isinstance(body, dict) and isinstance(body.get("error"), dict) else {}
    reason = None
    for detail in err.get("details") or []:
        if isinstance(detail, dict) and detail.get("reason"):
            reason = str(detail["reason"])
            break
    message = err.get("message") or (getattr(response, "text", "") or "")[:500]
    return {"status": err.get("status"), "reason": reason, "message": str(message)}


def _classify(http_status: int, parsed: Dict[str, Optional[str]], model: Optional[str]) -> GeminiError:
    provider_status = parsed.get("status") or ""
    reason = parsed.get("reason") or ""
    msg = (parsed.get("message") or "").lower()
    code = f"HTTP {http_status}{' ' + provider_status if provider_status else ''}{' / ' + reason if reason else ''}"

    if http_status == 400 and (reason == "API_KEY_INVALID" or "api key not valid" in msg or "api_key_invalid" in msg):
        return GeminiError(
            AUTH,
            f"Gemini rejected the API key ({code}). Create a new key in Google AI Studio "
            "(https://aistudio.google.com/apikey) and set GEMINI_API_KEY in backend/.env, then restart the backend.",
            http_status=http_status, reason=reason or "API_KEY_INVALID", model=model,
        )
    if http_status == 401 or provider_status == "UNAUTHENTICATED":
        return GeminiError(
            AUTH,
            f"Gemini could not authenticate this API key ({code}). Google now rejects standard/unrestricted keys - "
            "create a new key in Google AI Studio and set GEMINI_API_KEY in backend/.env.",
            http_status=http_status, reason=reason, model=model,
        )
    if http_status == 403 or provider_status == "PERMISSION_DENIED":
        if reason == "SERVICE_DISABLED" or "has not been used in project" in msg or "it is disabled" in msg:
            hint = "The Generative Language (Gemini) API is not enabled for this key's Google Cloud project."
        else:
            hint = "This API key is not allowed to call the Gemini API (it may be restricted to other APIs, blocked or leaked)."
        return GeminiError(
            AUTH,
            f"{hint} ({code}). Create or restrict a key for the Gemini API in Google AI Studio and update backend/.env.",
            http_status=http_status, reason=reason, model=model,
        )
    if http_status == 404:
        if "no longer available" in msg or "new users" in msg or "not available to" in msg:
            return GeminiError(
                MODEL_UNAVAILABLE,
                f"Model '{model}' is not available to this API key's project ({code}: Google limits this model to "
                "projects that used it before). Leave GEMINI_MODEL empty to auto-select a current model, or set "
                "one of the available models.",
                http_status=http_status, reason=reason, model=model,
            )
        return GeminiError(
            MODEL_NOT_FOUND,
            f"Model '{model}' was not found for Gemini API {api_version()} or does not support generateContent "
            f"({code}). Leave GEMINI_MODEL empty to auto-select a current model, or set one of the available models.",
            http_status=http_status, reason=reason, model=model,
        )
    if http_status == 429 or provider_status == "RESOURCE_EXHAUSTED":
        return GeminiError(
            QUOTA,
            f"Gemini quota or rate limit exceeded ({code}). Wait a minute and retry, or check the plan/billing "
            "of the key's project in Google AI Studio.",
            http_status=http_status, reason=reason, model=model,
        )
    if http_status >= 500:
        return GeminiError(
            UPSTREAM, f"Gemini service error ({code}). This is usually temporary - retry shortly.",
            http_status=http_status, reason=reason, model=model,
        )
    if http_status == 400 and (provider_status == "FAILED_PRECONDITION" or "location is not supported" in msg):
        return GeminiError(
            BAD_REQUEST,
            f"Gemini API is not available for this request ({code}). The key's project/region may not be eligible.",
            http_status=http_status, reason=reason, model=model,
        )
    return GeminiError(
        BAD_REQUEST, f"Gemini rejected the request ({code}).", http_status=http_status, reason=reason, model=model,
    )


async def _send(method: str, path: str, *, model: Optional[str] = None, json: Any = None,
                params: Optional[Dict[str, Any]] = None, timeout_s: Optional[float] = None,
                retry_transient: bool = True) -> Dict[str, Any]:
    if not configured():
        raise GeminiError(NOT_CONFIGURED, "GEMINI_API_KEY is not set in backend/.env.")
    url = f"{api_base()}/{path}"
    headers = {"x-goog-api-key": api_key(), "Content-Type": "application/json"}
    timeout = httpx.Timeout(float(timeout_s or settings.GEMINI_TIMEOUT_SECONDS), connect=10.0)
    attempts = 2 if retry_transient else 1
    for attempt in range(attempts):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                if method == "GET":
                    response = await client.get(url, headers=headers, params=params)
                else:
                    response = await client.post(url, headers=headers, json=json)
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ProxyError, httpx.NetworkError) as exc:
            logger.error("Gemini unreachable: %s %s -> %s: %s", method, url, exc.__class__.__name__, _redact(exc))
            raise GeminiError(
                UNREACHABLE,
                f"Could not reach the Gemini API at {api_base().split('/')[2]} ({exc.__class__.__name__}). "
                "Check this server's internet connection, proxy or firewall.",
                model=model,
            ) from None
        except httpx.TimeoutException as exc:
            logger.error("Gemini timeout: %s %s -> %s", method, url, exc.__class__.__name__)
            raise GeminiError(
                TIMEOUT,
                f"Gemini did not respond within {int(timeout.read or settings.GEMINI_TIMEOUT_SECONDS)} seconds. "
                "Retry, or raise GEMINI_TIMEOUT_SECONDS in backend/.env.",
                model=model,
            ) from None

        if response.status_code == 200:
            try:
                return response.json()
            except Exception:  # noqa: BLE001
                raise GeminiError(INVALID_RESPONSE, "Gemini returned a response that is not valid JSON.", model=model) from None

        parsed = _parse_error(response)
        logger.error(
            "Gemini API error: %s %s -> HTTP %s %s %s: %s",
            method, url, response.status_code, parsed.get("status") or "", parsed.get("reason") or "",
            _redact(parsed.get("message")),
        )
        if response.status_code in (500, 502, 503, 504) and attempt + 1 < attempts:
            await asyncio.sleep(RETRY_DELAY_SECONDS)
            continue
        raise _classify(response.status_code, parsed, model)
    raise GeminiError(UPSTREAM, "Gemini request failed.", model=model)  # pragma: no cover


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
async def list_models() -> List[Dict[str, Any]]:
    """models.list (all pages)."""
    models: List[Dict[str, Any]] = []
    page_token: Optional[str] = None
    for _ in range(10):
        params: Dict[str, Any] = {"pageSize": 1000}
        if page_token:
            params["pageToken"] = page_token
        data = await _send("GET", "models", params=params, timeout_s=20)
        models.extend([m for m in (data.get("models") or []) if isinstance(m, dict)])
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return models


async def get_model(name: str) -> Dict[str, Any]:
    """models.get for one model."""
    model = normalize_model_name(name)
    return await _send("GET", f"models/{model}", model=model, timeout_s=20)


def supports_generate_content(model_info: Dict[str, Any]) -> bool:
    return "generateContent" in (model_info.get("supportedGenerationMethods") or [])


_EXCLUDED_TOKENS = (
    "preview", "exp", "tts", "image", "live", "audio", "embedding", "embed", "robotics", "computer-use",
    "transcribe", "omni", "latest", "thinking", "learnlm", "gemma", "aqa", "veo", "imagen", "lyria",
    "native", "translate", "-8b", "vision", "research", "agent",
)
_MODEL_TIERS = (
    (0, re.compile(r"^gemini-(\d+)(?:\.(\d+))?-flash$")),
    (1, re.compile(r"^gemini-(\d+)(?:\.(\d+))?-flash-lite$")),
    (2, re.compile(r"^gemini-(\d+)(?:\.(\d+))?-pro$")),
)


def rank_models(models: List[Dict[str, Any]]) -> List[str]:
    """Stable text models that support generateContent, best first.

    Preference: newest stable ``gemini-X.Y-flash``, then ``-flash-lite``, then ``-pro``.
    Preview/experimental/specialised (TTS, image, live, embedding, ...) models are skipped.
    """
    ranked = []
    for info in models:
        if not supports_generate_content(info):
            continue
        name = normalize_model_name(info.get("name"))
        if not name or any(token in name for token in _EXCLUDED_TOKENS):
            continue
        for tier, pattern in _MODEL_TIERS:
            match = pattern.match(name)
            if match:
                major, minor = int(match.group(1)), int(match.group(2) or 0)
                ranked.append((tier, -major, -minor, name))
                break
    ranked.sort()
    return [name for *_rest, name in ranked]


def available_generate_models(models: List[Dict[str, Any]]) -> List[str]:
    """Names of every listed model supporting generateContent (for helpful error messages)."""
    names = [normalize_model_name(m.get("name")) for m in models if supports_generate_content(m)]
    preferred = rank_models(models)
    rest = sorted(n for n in names if n and n not in preferred)
    return (preferred + rest)[:25]


async def _available_models_safe(exclude: Optional[str] = None) -> Optional[List[str]]:
    """Suggestions for error messages (never re-suggests the model that just failed)."""
    try:
        return [m for m in available_generate_models(await list_models()) if m != exclude]
    except GeminiError:
        return None


# ---------------------------------------------------------------------------
# generateContent
# ---------------------------------------------------------------------------
_BLOCK_FINISH_REASONS = {"SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII", "RECITATION", "IMAGE_SAFETY"}


async def generate(model: str, payload: Dict[str, Any], *, timeout_s: Optional[float] = None,
                   retry_transient: bool = True) -> GenerateResult:
    """POST models/{model}:generateContent and parse the first candidate (thought parts skipped)."""
    model = normalize_model_name(model)
    data = await _send("POST", f"models/{model}:generateContent", model=model, json=payload,
                       timeout_s=timeout_s, retry_transient=retry_transient)
    candidates = data.get("candidates") or []
    if not candidates:
        block = (data.get("promptFeedback") or {}).get("blockReason")
        if block:
            raise GeminiError(BLOCKED, f"Gemini blocked the request ({block}).", model=model, reason=block)
        raise GeminiError(EMPTY, "Gemini returned no answer candidate.", model=model)
    candidate = candidates[0] or {}
    parts = ((candidate.get("content") or {}).get("parts")) or []
    text = "".join(
        str(part.get("text", "")) for part in parts
        if isinstance(part, dict) and not part.get("thought")
    )
    return GenerateResult(
        text=text,
        model=model,
        finish_reason=candidate.get("finishReason"),
        model_version=data.get("modelVersion"),
        usage=data.get("usageMetadata") or {},
    )


async def _probe(model: str) -> GenerateResult:
    """Tiny real generateContent call. HTTP 200 with a candidate proves key + model + method."""
    payload = {
        "contents": [{"role": "user", "parts": [{"text": PROBE_PROMPT}]}],
        # Generous cap: on thinking models, thought tokens share this budget.
        "generationConfig": {"maxOutputTokens": 1024},
    }
    return await generate(model, payload, timeout_s=min(float(settings.GEMINI_TIMEOUT_SECONDS), 30.0),
                          retry_transient=False)


# ---------------------------------------------------------------------------
# Status (cached) + model resolution
# ---------------------------------------------------------------------------
_status_cache: Dict[str, Any] = {"result": None, "expires_at": 0.0}


def reset_status_cache() -> None:
    _status_cache["result"] = None
    _status_cache["expires_at"] = 0.0


def _store_status(result: Dict[str, Any]) -> None:
    ttl = settings.GEMINI_STATUS_CACHE_SECONDS if result.get("status") == STATUS_CONNECTED else settings.GEMINI_STATUS_ERROR_CACHE_SECONDS
    _status_cache["result"] = result
    _status_cache["expires_at"] = time.monotonic() + max(0, int(ttl))


def _status_base() -> Dict[str, Any]:
    cm = configured_model()
    return {
        "provider": PROVIDER,
        "configured": configured(),
        "authenticated": False,
        "model": None,
        "status": STATUS_NOT_CONFIGURED,
        "message": "",
        "checked_at": _now_iso(),
        "api_version": api_version(),
        "model_source": "configured" if cm else "auto",
        "configured_model": cm or None,
    }


async def _resolve_and_probe(state: Dict[str, Any]) -> str:
    wanted = configured_model()
    if wanted:
        try:
            info = await get_model(wanted)
            state["authenticated"] = True
        except GeminiError as exc:
            if exc.category in (MODEL_NOT_FOUND, MODEL_UNAVAILABLE):
                state["authenticated"] = True
                exc.available_models = await _available_models_safe(exclude=wanted)
            raise
        if not supports_generate_content(info):
            raise GeminiError(
                MODEL_NOT_FOUND,
                f"Model '{wanted}' exists but does not support generateContent "
                f"(supported: {', '.join(info.get('supportedGenerationMethods') or []) or 'none'}).",
                model=wanted, available_models=await _available_models_safe(exclude=wanted),
            )
        try:
            await _probe(wanted)
        except GeminiError as exc:
            if exc.category in (MODEL_NOT_FOUND, MODEL_UNAVAILABLE):
                exc.available_models = await _available_models_safe(exclude=wanted)
            raise
        return wanted

    models = await list_models()
    state["authenticated"] = True
    candidates = rank_models(models)
    if not candidates:
        raise GeminiError(
            NO_MODEL,
            "The Gemini API did not report any stable text model supporting generateContent for this key. "
            "Set GEMINI_MODEL in backend/.env to a model your key can use.",
            available_models=available_generate_models(models),
        )
    tried: List[str] = []
    last: Optional[GeminiError] = None
    for name in candidates[:MAX_AUTO_PROBES]:
        tried.append(name)
        try:
            await _probe(name)
            return name
        except GeminiError as exc:
            if exc.category in (MODEL_NOT_FOUND, MODEL_UNAVAILABLE, BLOCKED, EMPTY, BAD_REQUEST):
                logger.warning("Gemini auto-select: model %s rejected the probe (%s)", name, exc.category)
                last = exc
                continue
            raise
    raise GeminiError(
        NO_MODEL,
        f"No available Gemini model accepted a generateContent request (tried: {', '.join(tried)}). "
        "Set GEMINI_MODEL in backend/.env to a model your key can use.",
        http_status=last.http_status if last else None,
        available_models=available_generate_models(models),
    )


async def check_status(force: bool = False) -> Dict[str, Any]:
    """Real connection check (cached). Never raises."""
    cached = _status_cache.get("result")
    if not force and cached and time.monotonic() < float(_status_cache.get("expires_at") or 0):
        return {**cached, "cached": True}

    result = _status_base()
    if not configured():
        result.update(status=STATUS_NOT_CONFIGURED, message="GEMINI_API_KEY is not set in backend/.env.")
        _store_status(result)
        return {**result, "cached": False}

    started = time.monotonic()
    state: Dict[str, Any] = {"authenticated": False}
    try:
        model = await _resolve_and_probe(state)
        result.update(
            status=STATUS_CONNECTED,
            authenticated=True,
            model=model,
            message=f"Verified with a live generateContent request to {model}.",
            verified_with="generateContent",
        )
    except GeminiError as exc:
        result.update(
            status=exc.status,
            authenticated=bool(state.get("authenticated")),
            model=exc.model or None,
            message=exc.user_message,
            error_code=exc.category,
            http_status=exc.http_status,
        )
        if exc.available_models:
            result["available_models"] = exc.available_models
    except Exception as exc:  # pragma: no cover - defensive, never break the navbar
        logger.error("Gemini status check crashed: %s", exc.__class__.__name__, exc_info=True)
        result.update(status=STATUS_ERROR, message="Gemini status check failed unexpectedly (see server log).",
                      error_code="internal_error")
    result["latency_ms"] = int((time.monotonic() - started) * 1000)
    result["checked_at"] = _now_iso()
    _store_status(result)
    return {**result, "cached": False}


def last_status() -> Optional[Dict[str, Any]]:
    return _status_cache.get("result")


def record_success(model: str) -> None:
    """A real generateContent call succeeded -> the indicator can say 'connected'."""
    current = _status_cache.get("result") or _status_base()
    updated = {
        **current,
        "configured": True,
        "authenticated": True,
        "status": STATUS_CONNECTED,
        "model": model,
        "message": f"Verified with a live generateContent request to {model}.",
        "verified_with": "generateContent",
        "checked_at": _now_iso(),
    }
    for key in ("error_code", "http_status", "available_models"):
        updated.pop(key, None)
    _store_status(updated)


def record_failure(exc: GeminiError) -> None:
    """A real call failed with a non-transient error -> reflect it in the status indicator."""
    if exc.category in (UPSTREAM, TIMEOUT, BLOCKED, EMPTY, INVALID_RESPONSE, BAD_REQUEST):
        return  # request-specific or transient: the connection itself may still be fine
    current = _status_cache.get("result") or _status_base()
    updated = {
        **current,
        "status": exc.status,
        "authenticated": exc.category not in (AUTH, NOT_CONFIGURED, UNREACHABLE),
        "model": exc.model or current.get("model"),
        "message": exc.user_message,
        "error_code": exc.category,
        "http_status": exc.http_status,
        "checked_at": _now_iso(),
    }
    _store_status(updated)


async def active_model() -> str:
    """The verified model to use, or a GeminiError describing why Gemini is unusable."""
    status = await check_status()
    if status.get("status") == STATUS_CONNECTED and status.get("model"):
        return str(status["model"])
    category = {
        STATUS_NOT_CONFIGURED: NOT_CONFIGURED,
        STATUS_UNREACHABLE: UNREACHABLE,
    }.get(status.get("status"), status.get("error_code") or UPSTREAM)
    raise GeminiError(category, status.get("message") or "Gemini is not connected.",
                      http_status=status.get("http_status"), model=status.get("model"))


async def generate_text(payload: Dict[str, Any]) -> GenerateResult:
    """Generate with the verified model. Raises GeminiError (already recorded for the status)."""
    model = await active_model()
    try:
        result = await generate(model, payload)
    except GeminiError as exc:
        record_failure(exc)
        raise
    if not result.text.strip():
        if (result.finish_reason or "") in _BLOCK_FINISH_REASONS:
            raise GeminiError(BLOCKED, f"Gemini withheld the answer (finishReason={result.finish_reason}).", model=model)
        raise GeminiError(
            EMPTY, f"Gemini returned an empty answer (finishReason={result.finish_reason or 'unknown'}).", model=model,
        )
    record_success(model)
    return result


def public_error(exc: GeminiError) -> Dict[str, Any]:
    """Safe error object for API responses (no key, no raw provider text)."""
    payload: Dict[str, Any] = {"code": exc.category, "message": exc.user_message}
    if exc.http_status:
        payload["http_status"] = exc.http_status
    return payload
