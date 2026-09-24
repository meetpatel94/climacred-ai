"""
Tests for the Gemini layer: connection status, chat assistant and dashboard insights.

Gemini is never called over the network. ``httpx.AsyncClient`` inside
``app.services.gemini_client`` is replaced by ``FakeAsyncClient``, a programmable
stand-in for the Gemini REST API (models.list, models.get, models.generateContent)
that returns the same JSON shapes - including Google's real error bodies - so the
tests can assert exactly what is sent to Gemini and how every failure is reported.

All tests start from a genuinely empty database (see tests/conftest.py).
"""
import json
from typing import Any, Callable, Dict, List, Optional

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database.collections import COLLECTIONS
from app.database.mongodb import get_collection
from app.main import app
from app.services import ai_chat_service as chat
from app.services import ai_insight_service as ai
from app.services import gemini_client as gc
from tests.conftest import TEST_ASSESSMENT, TEST_PROFILE, seed_real_business

client = TestClient(app)
API_KEY = "test-key-SECRET-9f8e7d"


# ---------------------------------------------------------------------------
# Fake Gemini REST API
# ---------------------------------------------------------------------------
class FakeResponse:
    def __init__(self, status_code: int = 200, payload: Any = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload
        self.text = text or (json.dumps(payload) if payload is not None else "")

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


def google_error(code: int, status: str, message: str, reason: Optional[str] = None) -> FakeResponse:
    err: Dict[str, Any] = {"code": code, "status": status, "message": message}
    if reason:
        err["details"] = [{"@type": "type.googleapis.com/google.rpc.ErrorInfo", "reason": reason}]
    return FakeResponse(code, {"error": err})


def text_response(text: str, finish: str = "STOP") -> FakeResponse:
    return FakeResponse(200, {
        "candidates": [{"content": {"role": "model", "parts": [{"text": text}]}, "finishReason": finish}],
        "usageMetadata": {"totalTokenCount": 42},
        "modelVersion": "fake",
    })


def model_entry(name: str, methods: Optional[List[str]] = None) -> Dict[str, Any]:
    return {"name": f"models/{name}", "supportedGenerationMethods": methods or ["generateContent", "countTokens"]}


NOT_FOUND = lambda m: google_error(  # noqa: E731
    404, "NOT_FOUND",
    f"models/{m} is not found for API version v1beta, or is not supported for generateContent. Call ListModels.",
)
NEW_USERS = lambda m: google_error(  # noqa: E731
    404, "NOT_FOUND", f"This model models/{m} is no longer available to new users.",
)


class FakeGemini:
    def __init__(self) -> None:
        self.models: List[Dict[str, Any]] = [
            model_entry("gemini-2.5-flash"),
            model_entry("gemini-3.5-flash-lite"),
            model_entry("gemini-3.8-flash"),
            model_entry("gemini-3.7-flash"),
            model_entry("gemini-3-flash-preview"),
            model_entry("gemini-3.8-flash-tts"),
            model_entry("gemini-embedding-2", ["embedContent"]),
        ]
        self.list_error: Optional[FakeResponse] = None
        self.get_errors: Dict[str, FakeResponse] = {}
        self.probe_errors: Dict[str, FakeResponse] = {}
        self.generate_queue: List[Any] = []
        self.transport_error: Optional[Exception] = None
        self.calls: List[Dict[str, Any]] = []

    # -- helpers used by the tests --
    def generate_calls(self) -> List[Dict[str, Any]]:
        return [c for c in self.calls if c["method"] == "POST" and not _is_probe(c["json"])]

    def probe_calls(self) -> List[Dict[str, Any]]:
        return [c for c in self.calls if c["method"] == "POST" and _is_probe(c["json"])]

    def last_prompt_text(self) -> str:
        return self.generate_calls()[-1]["json"]["contents"][-1]["parts"][0]["text"]

    def last_context(self) -> Dict[str, Any]:
        text = self.last_prompt_text()
        return json.loads(text[text.index("{"): text.rindex("}") + 1] if "CORRECTION" not in text
                          else text[text.index("{"): text.index("\n\nCORRECTION")])

    # -- request handling --
    def handle_get(self, url: str, params: Any) -> FakeResponse:
        path = url.split("/v1beta/", 1)[1]
        if path == "models":
            return self.list_error or FakeResponse(200, {"models": self.models})
        name = path[len("models/"):]
        if name in self.get_errors:
            return self.get_errors[name]
        for entry in self.models:
            if entry["name"] == f"models/{name}":
                return FakeResponse(200, entry)
        return NOT_FOUND(name)

    def handle_post(self, url: str, payload: Dict[str, Any]) -> FakeResponse:
        model = url.split("/models/", 1)[1].split(":", 1)[0]
        if not any(e["name"] == f"models/{model}" for e in self.models):
            return NOT_FOUND(model)
        if _is_probe(payload):
            return self.probe_errors.get(model) or text_response("OK")
        if self.generate_queue:
            item = self.generate_queue.pop(0)
            return item(payload) if callable(item) else item
        return google_error(500, "INTERNAL", "no queued response")


def _is_probe(payload: Optional[Dict[str, Any]]) -> bool:
    try:
        return payload["contents"][0]["parts"][0]["text"] == gc.PROBE_PROMPT and len(payload["contents"]) == 1
    except (KeyError, IndexError, TypeError):
        return False


FAKE = FakeGemini()


class FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, headers=None, params=None):
        FAKE.calls.append({"method": "GET", "url": url, "headers": headers or {}, "params": params, "json": None})
        if FAKE.transport_error:
            raise FAKE.transport_error
        return FAKE.handle_get(url, params)

    async def post(self, url, headers=None, json=None):
        FAKE.calls.append({"method": "POST", "url": url, "headers": headers or {}, "params": None, "json": json})
        if FAKE.transport_error:
            raise FAKE.transport_error
        return FAKE.handle_post(url, json)


@pytest.fixture
def gemini(monkeypatch):
    """Gemini configured with a (fake) key; network replaced by the fake API."""
    global FAKE
    FAKE = FakeGemini()
    monkeypatch.setattr(settings, "GEMINI_API_KEY", API_KEY)
    monkeypatch.setattr(settings, "GEMINI_MODEL", "")
    monkeypatch.setattr(gc.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(gc, "RETRY_DELAY_SECONDS", 0)
    gc.reset_status_cache()
    return FAKE


@pytest.fixture
def business():
    seed_real_business()
    return {"profile": TEST_PROFILE, "assessment": TEST_ASSESSMENT}


def status(refresh: bool = False) -> Dict[str, Any]:
    resp = client.get("/api/ai/status" + ("?refresh=true" if refresh else ""))
    assert resp.status_code == 200
    assert API_KEY not in resp.text
    return resp.json()


def ask(message: str, conversation_id: Optional[str] = None) -> Dict[str, Any]:
    body: Dict[str, Any] = {"message": message}
    if conversation_id:
        body["conversation_id"] = conversation_id
    resp = client.post("/api/ai/chat", json=body)
    assert resp.status_code == 200, resp.text
    assert API_KEY not in resp.text
    return resp.json()


def insight_from_context() -> Dict[str, Any]:
    """A Gemini insight that only uses figures present in the stored/calculated context."""
    ctx = ai.build_context()
    energy = ctx["calculated_analytics"]["energy"]
    water = ctx["calculated_analytics"]["water"]
    return {
        "summary": f"Your plant uses {int(energy['monthly_kwh'])} kWh and {int(water['monthly_litres'])} litres per month.",
        "recent_changes": ["Only one stored snapshot exists so far."],
        "key_risk": "Groundwater dependency without recycling.",
        "focus_now": "Water and energy efficiency.",
        "priority_action": "Start with the top recommendation.",
        "forecast": "Insufficient historical data for a reliable forecast.",
        "expected_impact": "Estimated savings per the solution catalog.",
        "confidence": "Medium",
        "details": {"data_used": ["profile", "assessment"], "reasoning_summary": "Based on stored data."},
    }


# ===========================================================================
# GET /api/ai/status
# ===========================================================================
def test_status_without_key_is_not_configured_and_makes_no_call(monkeypatch):
    monkeypatch.setattr(gc.httpx, "AsyncClient", FakeAsyncClient)
    FAKE.calls.clear()
    body = status()
    assert body["provider"] == "Google Gemini"
    assert body["configured"] is False and body["authenticated"] is False
    assert body["status"] == "not_configured"
    assert "GEMINI_API_KEY" in body["message"]
    assert FAKE.calls == []


def test_status_connected_only_after_a_real_generate_content_call(gemini):
    body = status()
    assert body["status"] == "connected"
    assert body["configured"] is True and body["authenticated"] is True
    # auto-selection: newest stable Flash model reported by models.list (preview/tts/embedding skipped)
    assert body["model"] == "gemini-3.8-flash"
    assert body["model_source"] == "auto"
    probes = gemini.probe_calls()
    assert len(probes) == 1 and probes[0]["url"].endswith("/v1beta/models/gemini-3.8-flash:generateContent")
    # key only in the header, never in the URL
    assert probes[0]["headers"]["x-goog-api-key"] == API_KEY
    assert all("key=" not in c["url"] and API_KEY not in c["url"] for c in gemini.calls)


def test_status_skips_models_restricted_to_existing_projects(gemini):
    """Root cause of the old 404: gemini-2.5-* answers 404 'no longer available to new users'."""
    gemini.models = [model_entry("gemini-2.5-flash"), model_entry("gemini-3.5-flash-lite")]
    gemini.probe_errors["gemini-2.5-flash"] = NEW_USERS("gemini-2.5-flash")
    body = status()
    assert body["status"] == "connected"
    assert body["model"] == "gemini-3.5-flash-lite"
    assert [c["url"].split("/models/")[1] for c in gemini.probe_calls()] == [
        "gemini-2.5-flash:generateContent", "gemini-3.5-flash-lite:generateContent",
    ]


def test_configured_model_is_verified_before_use(gemini, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_MODEL", "gemini-3.7-flash")
    body = status()
    assert body["status"] == "connected" and body["model"] == "gemini-3.7-flash"
    assert body["model_source"] == "configured"
    assert any(c["method"] == "GET" and c["url"].endswith("/models/gemini-3.7-flash") for c in gemini.calls)


def test_retired_configured_model_is_detected_not_called_blindly(gemini, monkeypatch):
    """GEMINI_MODEL=gemini-1.5-flash (shut down) -> models.get 404 -> clear error, no generateContent."""
    monkeypatch.setattr(settings, "GEMINI_MODEL", "gemini-1.5-flash")
    body = status()
    assert body["status"] == "error"
    assert body["error_code"] == "model_not_found"
    assert body["authenticated"] is True  # the key works, the model does not
    assert "gemini-1.5-flash" in body["message"] and "404" in body["message"]
    assert "gemini-3.8-flash" in body["available_models"]
    assert not any(c["method"] == "POST" for c in gemini.calls)


def test_configured_model_restricted_for_new_projects(gemini, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
    gemini.probe_errors["gemini-2.5-flash"] = NEW_USERS("gemini-2.5-flash")
    body = status()
    assert body["status"] == "error" and body["error_code"] == "model_unavailable"
    assert "not available to this API key's project" in body["message"]
    assert body["available_models"][0] == "gemini-3.8-flash"
    assert "gemini-2.5-flash" not in body["available_models"]  # never re-suggest the failing model


def test_models_prefix_in_config_is_normalised(gemini, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_MODEL", "models/gemini-3.8-flash")
    assert status()["model"] == "gemini-3.8-flash"
    assert all("/models/models/" not in c["url"] for c in gemini.calls)


def test_model_without_generate_content_is_rejected(gemini, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_MODEL", "gemini-embedding-2")
    body = status()
    assert body["status"] == "error" and "does not support generateContent" in body["message"]
    assert not any(c["method"] == "POST" for c in gemini.calls)


def test_invalid_api_key_is_reported(gemini):
    gemini.list_error = google_error(400, "INVALID_ARGUMENT", "API key not valid. Please pass a valid API key.", "API_KEY_INVALID")
    body = status()
    assert body["status"] == "error" and body["error_code"] == "auth"
    assert body["configured"] is True and body["authenticated"] is False
    assert "API_KEY_INVALID" in body["message"]
    assert "API key not valid" not in body["message"]  # raw provider text stays in the server log


def test_permission_denied_key_is_reported(gemini):
    gemini.list_error = google_error(403, "PERMISSION_DENIED", "Generative Language API has not been used in project 123 before or it is disabled.", "SERVICE_DISABLED")
    body = status()
    assert body["status"] == "error" and body["error_code"] == "auth"
    assert "not enabled" in body["message"]
    assert "123" not in body["message"]  # project numbers never reach the UI


def test_quota_error_is_reported(gemini):
    gemini.probe_errors["gemini-3.8-flash"] = google_error(429, "RESOURCE_EXHAUSTED", "Quota exceeded")
    body = status()
    assert body["status"] == "error" and body["error_code"] == "quota"
    assert body["authenticated"] is True


def test_unreachable_api_is_not_connected(gemini):
    gemini.transport_error = httpx.ConnectError("TLS/SSL connection has been closed (EOF)")
    body = status()
    assert body["status"] == "unreachable"
    assert body["configured"] is True and body["authenticated"] is False
    assert "Could not reach the Gemini API" in body["message"]


def test_status_is_cached_and_refresh_rechecks(gemini):
    assert status()["cached"] is False
    calls = len(gemini.calls)
    second = status()
    assert second["cached"] is True and len(gemini.calls) == calls
    third = status(refresh=True)
    assert third["cached"] is False and len(gemini.calls) > calls


# ===========================================================================
# POST /api/ai/chat
# ===========================================================================
def test_chat_contract_and_real_answer_with_empty_database(gemini):
    gemini.generate_queue.append(text_response("Hello! I'm the ClimaCred AI Assistant. How can I help?"))
    body = ask("Hello")
    assert body["status"] == "ok"
    assert body["answer"] == "Hello! I'm the ClimaCred AI Assistant. How can I help?"
    assert body["provider"] == "gemini" and body["model"] == "gemini-3.8-flash"
    assert body["conversation_id"] and body["has_data"] is False
    call = gemini.generate_calls()[-1]
    assert call["url"].endswith("/models/gemini-3.8-flash:generateContent")
    context = gemini.last_context()
    assert context["data_state"]["has_data"] is False
    assert context["business_profile"] is None
    for key in ("climate_fingerprint", "calculated_analytics", "recommendations", "transformation_plan"):
        assert key not in context, key
    assert chat.NO_DATA_SENTENCE in call["json"]["systemInstruction"]["parts"][0]["text"]


def test_chat_without_data_never_sends_leftover_business_values(gemini):
    """Even an orphaned legacy fingerprint in the DB must not reach Gemini."""
    get_collection(COLLECTIONS["climate_fingerprints"]).insert_one({"user_id": "default", "overallScore": 47.5, "dimensions": []})
    gemini.generate_queue.append(text_response(chat.NO_DATA_SENTENCE))
    body = ask("Do you have my business climate data?")
    assert body["answer"] == chat.NO_DATA_SENTENCE
    assert "47.5" not in gemini.last_prompt_text()


def test_chat_context_uses_only_stored_business_data(gemini, business):
    gemini.generate_queue.append(text_response("Water is your weakest area."))
    body = ask("What's my biggest climate risk?")
    assert body["status"] == "ok" and body["has_data"] is True
    context = gemini.last_context()
    assert context["business_profile"]["name"] == TEST_PROFILE["name"]
    assert context["calculated_analytics"]["energy"]["monthly_kwh"] == 21500
    assert context["calculated_analytics"]["water"]["monthly_litres"] == 260000
    text = gemini.last_prompt_text()
    for demo_value in ("ABC Textile", "38500", "480000", "Tirupur"):
        assert demo_value not in text


def test_chat_follow_up_uses_server_side_memory(gemini, business):
    gemini.generate_queue += [text_response("Water use is high because nothing is recycled."),
                              text_response("Install water recycling first.")]
    first = ask("Why is my water impact high?")
    second = ask("How can I reduce it?", first["conversation_id"])
    assert second["conversation_id"] == first["conversation_id"]
    contents = gemini.generate_calls()[-1]["json"]["contents"]
    assert [c["role"] for c in contents] == ["user", "model", "user"]
    assert contents[0]["parts"][0]["text"] == "Why is my water impact high?"
    assert contents[1]["parts"][0]["text"] == "Water use is high because nothing is recycled."
    assert contents[2]["parts"][0]["text"].startswith("How can I reduce it?")


def test_clear_chat_forgets_the_conversation(gemini, business):
    gemini.generate_queue += [text_response("First answer."), text_response("Fresh answer.")]
    first = ask("What should I do next?")
    resp = client.delete(f"/api/ai/chat/{first['conversation_id']}")
    assert resp.json()["cleared"] is True
    ask("And then?", first["conversation_id"])
    assert len(gemini.generate_calls()[-1]["json"]["contents"]) == 1


def test_chat_payload_follows_current_gemini_guidance(gemini):
    gemini.generate_queue.append(text_response("Hi."))
    ask("Hello")
    payload = gemini.generate_calls()[-1]["json"]
    assert "temperature" not in payload["generationConfig"]  # Gemini 3: keep the default (1.0)
    assert payload["contents"][-1]["role"] == "user"
    assert "systemInstruction" in payload


def test_chat_without_key_returns_explicit_state_not_a_canned_answer():
    body = ask("What's my biggest climate risk?")
    assert body["status"] == "not_configured"
    assert body["answer"] is None and body["reply"] is None
    assert body["error"]["code"] == "not_configured"


def test_chat_gemini_failure_is_explicit_and_updates_status(gemini, business):
    assert status()["status"] == "connected"
    gemini.generate_queue.append(google_error(429, "RESOURCE_EXHAUSTED", "Quota exceeded for model"))
    body = ask("What changed recently?")
    assert body["status"] == "error" and body["answer"] is None
    assert body["error"]["code"] == "quota"
    assert status()["status"] == "error"  # the navbar indicator reflects the real failure


def test_chat_failed_turn_is_not_stored(gemini, business):
    gemini.generate_queue += [google_error(503, "UNAVAILABLE", "overloaded"), google_error(503, "UNAVAILABLE", "overloaded")]
    failed = ask("Explain my climate score.")
    assert failed["status"] == "error"
    gemini.generate_queue.append(text_response("Your score is explained here."))
    ask("Explain my climate score.", failed["conversation_id"])
    assert len(gemini.generate_calls()[-1]["json"]["contents"]) == 1


def test_chat_unverified_numbers_are_retried_then_flagged(gemini, business):
    gemini.generate_queue += [text_response("Your emissions are 987.65 tonnes."),
                              text_response("Your emissions are 987.65 tonnes, maybe 123.45.")]
    body = ask("What are my emissions?")
    assert len(gemini.generate_calls()) == 2
    assert "CORRECTION" in gemini.generate_calls()[-1]["json"]["contents"][-1]["parts"][0]["text"]
    assert body["status"] == "ok" and body["number_audit"]["verified"] is False
    assert "987.65" in body["notice"]


def test_chat_corrected_answer_is_used_when_verified(gemini, business):
    gemini.generate_queue += [text_response("Your electricity use is 99999 kWh."),
                              text_response("Your electricity use is 21500 kWh per month.")]
    body = ask("How much electricity do I use?")
    assert body["answer"] == "Your electricity use is 21500 kWh per month."
    assert body["number_audit"]["verified"] is True and body["notice"] is None


def test_chat_budget_and_scenario_numbers_come_from_the_backend(gemini, business):
    gemini.generate_queue += [text_response("See the budget selection."), text_response("See the projection.")]
    ask("What can I do with a ₹10 lakh budget?")
    answers = gemini.last_context()["calculated_answers"]
    assert answers["budget_selection"]["budget_inr"] == 1000000
    assert answers["budget_selection"]["total_investment_inr"] <= 1000000
    ask("What if I install rooftop solar?")
    assert gemini.last_context()["calculated_answers"]["scenario_projection"]["origin"] == "backend_scenario_engine"


def test_changed_assessment_changes_what_gemini_receives(gemini, business):
    gemini.generate_queue += [text_response("A."), text_response("B.")]
    ask("What's my biggest climate risk?")
    before = gemini.last_context()["calculated_analytics"]
    changed = json.loads(json.dumps(TEST_ASSESSMENT))
    changed["energy"]["monthlyElectricityKwh"] = 64000
    changed["water"]["monthlyWaterLitres"] = 90000
    assert client.post("/api/assessment", json=changed).status_code == 200
    ask("What's my biggest climate risk?")
    after = gemini.last_context()["calculated_analytics"]
    assert before["energy"]["monthly_kwh"] == 21500 and after["energy"]["monthly_kwh"] == 64000
    assert after["water"]["monthly_litres"] == 90000


def test_chat_empty_message_is_rejected():
    assert client.post("/api/ai/chat", json={"message": "   "}).status_code == 400


def test_chat_legacy_history_is_sanitised(gemini):
    gemini.generate_queue.append(text_response("ok"))
    client.post("/api/ai/chat", json={"message": "third", "history": [
        {"role": "assistant", "content": "orphan model turn"},
        {"role": "user", "content": "first"}, {"role": "user", "content": "first again"},
        {"role": "assistant", "content": "answer"},
    ]})
    roles = [c["role"] for c in gemini.generate_calls()[-1]["json"]["contents"]]
    assert roles == ["user", "model", "user"]


def test_suggestions_are_the_four_product_questions(business):
    body = client.get("/api/ai/chat/suggestions").json()
    assert body["has_data"] is True
    assert body["suggestions"] == [
        "What's my biggest climate risk?", "What changed recently?", "What should I do next?", "Explain my climate score.",
    ]
    client.post("/api/profile/reset")
    assert client.get("/api/ai/chat/suggestions").json()["has_data"] is False


# ===========================================================================
# GET /api/ai/dashboard-insights
# ===========================================================================
def test_insights_without_data_make_no_ai_call(gemini):
    body = client.get("/api/ai/dashboard-insights").json()
    assert body["status"] == "no_data" and body["insight"] is None and body["has_data"] is False
    assert gemini.calls == []


def test_insights_with_data_come_from_gemini(gemini, business):
    gemini.generate_queue.append(lambda payload: text_response(json.dumps(insight_from_context())))
    body = client.get("/api/ai/dashboard-insights").json()
    assert body["status"] == "ok" and body["source"] == "gemini" and body["model"] == "gemini-3.8-flash"
    insight = body["insight"]
    for section in ("recent_changes", "key_risk", "priority_action", "forecast", "expected_impact"):
        assert insight[section], section
    assert insight["details"]["number_audit"]["verified"] is True
    payload = gemini.generate_calls()[-1]["json"]
    assert payload["generationConfig"]["responseMimeType"] == "application/json"
    assert "temperature" not in payload["generationConfig"]


def test_insight_failure_is_explicit_without_template_text(gemini, business):
    gemini.generate_queue += [google_error(500, "INTERNAL", "boom"), google_error(500, "INTERNAL", "boom")]
    body = client.get("/api/ai/dashboard-insights").json()
    assert body["status"] == "error" and body["insight"] is None and body["source"] is None
    assert body["error"]["code"] == "upstream_error"
    assert body["calculated"]["energy_kwh_month"] == 21500  # real backend values are still provided


def test_insight_without_key_is_not_configured(business):
    body = client.get("/api/ai/dashboard-insights").json()
    assert body["status"] == "not_configured" and body["insight"] is None


def test_insight_invalid_json_is_an_error(gemini, business):
    gemini.generate_queue.append(text_response("this is not json"))
    body = client.get("/api/ai/dashboard-insights").json()
    assert body["status"] == "error" and body["error"]["code"] == "invalid_response"


def test_insight_cache_and_refresh(gemini, business):
    gemini.generate_queue += [lambda p: text_response(json.dumps(insight_from_context())) for _ in range(2)]
    client.get("/api/ai/dashboard-insights")
    cached = client.get("/api/ai/dashboard-insights").json()
    assert cached["cached"] is True and len(gemini.generate_calls()) == 1
    client.get("/api/ai/dashboard-insights?refresh=true")
    assert len(gemini.generate_calls()) == 2


def test_changed_data_invalidates_insight_cache(gemini, business):
    gemini.generate_queue += [lambda p: text_response(json.dumps(insight_from_context())) for _ in range(2)]
    first = client.get("/api/ai/dashboard-insights").json()
    changed = json.loads(json.dumps(TEST_ASSESSMENT))
    changed["energy"]["monthlyElectricityKwh"] = 30000
    client.post("/api/assessment", json=changed)
    client.post("/api/climate-fingerprint/generate")
    second = client.get("/api/ai/dashboard-insights").json()
    assert second["cached"] is False and second["data_signature"] != first["data_signature"]
    assert second["calculated"]["energy_kwh_month"] == 30000


def test_insight_invented_numbers_are_flagged(gemini, business):
    def invented(payload):
        data = insight_from_context()
        data["key_risk"] = "Emissions will reach 4321.5 tonnes next year."
        return text_response(json.dumps(data))
    gemini.generate_queue.append(invented)
    body = client.get("/api/ai/dashboard-insights").json()
    assert body["insight"]["details"]["number_audit"]["verified"] is False
    assert "4321.5" in body["insight"]["details"]["number_audit"]["unsupported_values"]


def test_insight_without_history_never_forecasts(gemini, business):
    def forecasting(payload):
        data = insight_from_context()
        data["forecast"] = "Energy will rise next quarter."
        return text_response(json.dumps(data))
    gemini.generate_queue.append(forecasting)
    body = client.get("/api/ai/dashboard-insights").json()
    assert body["insight"]["forecast"] == ai.INSUFFICIENT_HISTORY


def test_api_key_never_appears_in_any_response(gemini, business):
    gemini.generate_queue += [text_response("answer"), lambda p: text_response(json.dumps(insight_from_context()))]
    for resp in (
        client.get("/api/ai/status"),
        client.post("/api/ai/chat", json={"message": "hi"}),
        client.get("/api/ai/dashboard-insights"),
        client.get("/api/ai/chat/suggestions"),
        client.get("/"),
        client.get("/health"),
    ):
        assert API_KEY not in resp.text
    for name in COLLECTIONS.values():
        for doc in get_collection(name).find({}):
            assert API_KEY not in json.dumps(doc, default=str)
