"""
Tests for the Gemini AI layer (dashboard insight + chat assistant).

Gemini is never called over the network: the httpx client used by the service is
replaced with a fake transport, so we can assert exactly what is sent to Gemini
and how the API behaves for success / missing key / invalid key / 404 model /
transport failure / invented numbers.

All tests run against a genuinely empty database unless they explicitly store a
real test business (see tests/conftest.py).
"""
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.database.mongodb import get_collection
from app.database.collections import COLLECTIONS
from app.services import ai_insight_service as ai
from tests.conftest import TEST_PROFILE, TEST_ASSESSMENT, seed_real_business

client = TestClient(app)


# ---------------------------------------------------------------------------
# Fake Gemini transport
# ---------------------------------------------------------------------------
class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        return self._payload


class FakeAsyncClient:
    queue = []
    calls = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, headers=None, json=None):
        FakeAsyncClient.calls.append({"url": url, "headers": headers or {}, "json": json or {}})
        if FakeAsyncClient.queue:
            return FakeAsyncClient.queue.pop(0)
        return FakeResponse(500, text="no queued response")


def gemini_text(payload) -> FakeResponse:
    if isinstance(payload, str):
        return FakeResponse(200, {"candidates": [{"content": {"parts": [{"text": payload}]}}]})
    return FakeResponse(200, {"candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}]})


# Insight using ONLY figures that already exist in the stored/calculated context.
def gemini_insight_ok() -> dict:
    ctx = ai.build_context()
    energy = ctx["calculated_analytics"]["energy"]
    water = ctx["calculated_analytics"]["water"]
    score = ctx["climate_fingerprint"]["overall_score"]
    return {
        "summary": (
            f"Your plant spends Rs {int(energy['monthly_cost_inr'])} on {int(energy['monthly_kwh'])} kWh of grid power "
            f"and extracts {int(water['monthly_litres'])} litres of water each month."
        ),
        "recent_changes": [f"Climate readiness score is {score}/100 with only one stored snapshot."],
        "key_risk": "Groundwater dependency without closed-loop recycling.",
        "focus_now": "Water recycling and rooftop solar are the two weakest dimensions.",
        "priority_action": "Deploy ultrafiltration water recycling before scaling production.",
        "forecast": "Insufficient historical data for a reliable forecast.",
        "expected_impact": "Estimated water saving potential of about 65% of monthly intake.",
        "confidence": "Medium",
        "details": {
            "data_used": ["Climate assessment (measured)", f"Fingerprint score {score}/100 (calculated)"],
            "reasoning_summary": "The insight is derived from the stored assessment, fingerprint and recommendations.",
            "historical_comparison": "Only the latest snapshot exists.",
            "why_it_matters": "Water stress and grid tariff exposure drive both compliance and cost risk.",
            "main_risks": ["Escalating water cost", "Grid tariff exposure"],
            "recommended_actions": ["Install water recycling", "Evaluate rooftop solar"],
            "related_recommendations": ["sol-water-ro", "sol-solar"],
            "expected_impact_detail": "Potential savings are catalog estimates, not guaranteed.",
            "confidence_note": "Medium data completeness.",
            "assumptions": ["Steady production volume"],
        },
    }


@pytest.fixture(autouse=True)
def _ai_state(monkeypatch):
    """Isolate tests: no cached AI payloads, no leftover API key, no queued responses."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    # Both the dashboard insight and the chat assistant call Gemini through the
    # transport defined in ai_insight_service.
    monkeypatch.setattr(ai.httpx, "AsyncClient", FakeAsyncClient)
    FakeAsyncClient.queue = []
    FakeAsyncClient.calls = []
    get_collection(COLLECTIONS["ai_insights"]).delete_many({})
    yield
    FakeAsyncClient.queue = []
    FakeAsyncClient.calls = []
    get_collection(COLLECTIONS["ai_insights"]).delete_many({})


@pytest.fixture
def business():
    seed_real_business()
    return {"profile": TEST_PROFILE, "assessment": TEST_ASSESSMENT}


def _internal_keys(node, path="$") -> list:
    """Walk a payload and return any MongoDB-internal keys (_id, ...) that leaked in."""
    found = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key.startswith("_"):
                found.append(f"{path}.{key}")
            found += _internal_keys(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found += _internal_keys(value, f"{path}[{index}]")
    return found


# ---------------------------------------------------------------------------
# 1. Status endpoint / key configuration
# ---------------------------------------------------------------------------
def test_ai_status_without_key():
    body = client.get("/api/ai/status").json()
    assert body["gemini_configured"] is False
    assert body["model"] == settings.GEMINI_MODEL
    assert body["chat_enabled"] is True


def test_ai_status_with_key(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "unit-test-key")
    assert client.get("/api/ai/status").json()["gemini_configured"] is True


# ---------------------------------------------------------------------------
# 2. Empty database (TEST A)
# ---------------------------------------------------------------------------
def test_dashboard_insights_without_data_is_empty_state():
    body = client.get("/api/ai/dashboard-insights").json()
    assert body["status"] == "no_data"
    assert body["has_data"] is False
    assert body["insight"] is None
    assert body["notice"] == "No business climate data yet."
    assert body["calculated"]["business_name"] is None
    assert body["calculated"]["energy_kwh_month"] is None
    assert len(FakeAsyncClient.calls) == 0  # no AI call for an empty database


def test_dashboard_insights_without_data_and_with_key_still_makes_no_ai_call(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "unit-test-key")
    body = client.get("/api/ai/dashboard-insights").json()
    assert body["status"] == "no_data"
    assert body["insight"] is None
    assert len(FakeAsyncClient.calls) == 0


def test_chat_without_data_does_not_invent_a_business():
    body = client.post("/api/ai/chat", json={"message": "What is my biggest climate problem?"}).json()
    assert body["has_data"] is False
    assert body["ai_available"] is False
    assert "I don't have your business climate data yet." in body["reply"]
    assert "Complete your Climate Assessment" in body["reply"]
    assert len(FakeAsyncClient.calls) == 0


def test_chat_general_questions_allowed_without_data(monkeypatch):
    """General product questions may be answered by Gemini, but business data must not be invented."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "unit-test-key")
    FakeAsyncClient.queue = [gemini_text(
        "ClimaCred AI scores six dimensions: Energy, Water, Waste, Emissions, Mobility and Operations."
    )]
    body = client.post("/api/ai/chat", json={"message": "How does the Climate Fingerprint work?"}).json()
    assert body["source"] == "gemini"
    assert body["has_data"] is False
    sent = json.dumps(FakeAsyncClient.calls[0]["json"])
    assert "has_data" in sent
    assert "No business climate data is stored yet." in sent  # empty-state instruction
    assert "ABC Textile" not in sent


def test_existing_endpoints_still_work_with_ai_layer_present():
    for path in ("/api/solutions", "/api/transformation-plan", "/api/impact", "/api/reports/climate"):
        assert client.get(path).status_code == 200


# ---------------------------------------------------------------------------
# 3. Real data + Gemini configured
# ---------------------------------------------------------------------------
def test_dashboard_insights_with_key_returns_gemini_insight(business, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "unit-test-key")
    FakeAsyncClient.queue = [gemini_text(gemini_insight_ok())]

    body = client.get("/api/ai/dashboard-insights").json()
    assert body["status"] == "ok"
    assert body["source"] == "gemini"
    assert body["ai_available"] is True
    assert body["notice"] is None
    assert body["has_data"] is True
    assert body["insight"]["details"]["number_audit"]["verified"] is True
    assert body["insight"]["details"]["why_it_matters"]
    assert body["calculated"]["energy_kwh_month"] == TEST_ASSESSMENT["energy"]["monthlyElectricityKwh"]

    # Exactly one Gemini call; the key travels only in the backend request header
    assert len(FakeAsyncClient.calls) == 1
    call = FakeAsyncClient.calls[0]
    assert call["url"].endswith(f"models/{settings.GEMINI_MODEL}:generateContent")
    assert call["headers"]["x-goog-api-key"] == "unit-test-key"
    sent = json.dumps(call["json"])
    assert "unit-test-key" not in sent
    assert "MONGODB_URI" not in sent and "mongodb://" not in sent
    assert _internal_keys(body) == []


def test_dashboard_context_and_output_contain_only_stored_values(business, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "unit-test-key")
    FakeAsyncClient.queue = [gemini_text(gemini_insight_ok())]
    client.get("/api/ai/dashboard-insights")
    sent = json.dumps(FakeAsyncClient.calls[0]["json"])
    # Values that were submitted are present...
    assert str(TEST_ASSESSMENT["energy"]["monthlyElectricityKwh"]) in sent
    # ...and the removed demo business is nowhere to be seen.
    for forbidden in ("ABC Textile", "38500", "480000", "Tirupur"):
        assert forbidden not in sent


# ---------------------------------------------------------------------------
# 4. Gemini failure handling (never breaks the app, never leaks raw errors)
# ---------------------------------------------------------------------------
def test_dashboard_insights_without_key_uses_calculated_fallback(business):
    body = client.get("/api/ai/dashboard-insights").json()
    assert body["ai_available"] is False
    assert body["source"] == "calculated"
    assert body["status"] in ("unavailable", "error")
    assert body["notice"] == "AI insights are temporarily unavailable."
    assert "reason" not in body  # raw provider errors are not exposed
    assert body["calculated"]["climate_score"] is not None
    insight = body["insight"]
    for field in ("summary", "key_risk", "priority_action", "forecast", "expected_impact", "confidence"):
        assert insight[field]
    for field in ("data_used", "reasoning_summary", "recommended_actions", "assumptions", "why_it_matters"):
        assert insight["details"][field]
    assert len(FakeAsyncClient.calls) == 0


def test_invalid_api_key_is_reported_cleanly(business, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "wrong-key")
    FakeAsyncClient.queue = [FakeResponse(401, text='{"error":{"message":"API key not valid"}}')]
    body = client.get("/api/ai/dashboard-insights").json()
    assert body["status"] == "error"
    assert body["source"] == "calculated"
    assert body["notice"] == "AI insights are temporarily unavailable."
    assert "401" not in body["notice"] and "API key" not in json.dumps(body)


def test_gemini_transport_failure_falls_back(business, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "unit-test-key")

    class BoomClient(FakeAsyncClient):
        async def post(self, url, headers=None, json=None):
            raise ai.httpx.TransportError("connection reset")

    monkeypatch.setattr(ai.httpx, "AsyncClient", BoomClient)
    body = client.get("/api/ai/dashboard-insights").json()
    assert body["source"] == "calculated"
    assert body["notice"] == "AI insights are temporarily unavailable."
    assert body["insight"]["summary"]


def test_gemini_404_model_is_retried_with_fallback_model(business, monkeypatch):
    """A wrong GEMINI_MODEL must not break the AI layer (original 404 investigation)."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "unit-test-key")
    monkeypatch.setattr(settings, "GEMINI_MODEL", "gemini-does-not-exist")
    FakeAsyncClient.queue = [
        FakeResponse(404, text='{"error":{"message":"models/gemini-does-not-exist is not found"}}'),
        gemini_text(gemini_insight_ok()),
    ]
    body = client.get("/api/ai/dashboard-insights").json()
    assert body["status"] == "ok"
    assert body["source"] == "gemini"
    urls = [call["url"] for call in FakeAsyncClient.calls]
    assert urls[0].endswith("models/gemini-does-not-exist:generateContent")
    assert urls[1].endswith("models/gemini-2.5-flash:generateContent")
    assert len(urls) == 2


def test_gemini_404_on_all_models_falls_back_to_calculated(business, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "unit-test-key")
    monkeypatch.setattr(settings, "GEMINI_MODEL", "gemini-missing")
    monkeypatch.setattr(settings, "GEMINI_MODEL_FALLBACKS", "gemini-also-missing")
    FakeAsyncClient.queue = [
        FakeResponse(404, text="model not found"),
        FakeResponse(404, text="model not found"),
    ]
    body = client.get("/api/ai/dashboard-insights").json()
    assert body["source"] == "calculated"
    assert body["notice"] == "AI insights are temporarily unavailable."
    assert "404" not in json.dumps(body)


def test_gemini_invalid_json_falls_back(business, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "unit-test-key")
    FakeAsyncClient.queue = [FakeResponse(200, {"candidates": [{"content": {"parts": [{"text": "not json at all"}]}}]})]
    body = client.get("/api/ai/dashboard-insights").json()
    assert body["source"] == "calculated"


def test_quota_error_falls_back(business, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "unit-test-key")
    FakeAsyncClient.queue = [
        FakeResponse(429, text="quota"),
        FakeResponse(429, text="quota"),
    ]
    body = client.get("/api/ai/dashboard-insights").json()
    assert body["source"] == "calculated"
    assert body["notice"] == "AI insights are temporarily unavailable."


# ---------------------------------------------------------------------------
# 5. Cache behaviour
# ---------------------------------------------------------------------------
def test_cache_prevents_repeated_gemini_calls(business, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "unit-test-key")
    FakeAsyncClient.queue = [gemini_text(gemini_insight_ok())]
    first = client.get("/api/ai/dashboard-insights").json()
    second = client.get("/api/ai/dashboard-insights").json()
    assert first["source"] == "gemini" and second["cached"] is True
    assert len(FakeAsyncClient.calls) == 1


def test_refresh_bypasses_cache(business, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "unit-test-key")
    FakeAsyncClient.queue = [gemini_text(gemini_insight_ok()), gemini_text(gemini_insight_ok())]
    client.get("/api/ai/dashboard-insights")
    refreshed = client.get("/api/ai/dashboard-insights?refresh=true").json()
    assert refreshed["cached"] is False
    assert len(FakeAsyncClient.calls) == 2


def test_changed_stored_data_invalidates_cache_and_changes_insight(business, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "unit-test-key")
    FakeAsyncClient.queue = [gemini_text(gemini_insight_ok()), gemini_text(gemini_insight_ok())]
    first = client.get("/api/ai/dashboard-insights").json()

    seed_real_business(assessment={**TEST_ASSESSMENT, "energy": {**TEST_ASSESSMENT["energy"], "monthlyElectricityKwh": 41000}})
    second = client.get("/api/ai/dashboard-insights").json()

    assert first["cached"] is False and second["cached"] is False
    assert first["data_signature"] != second["data_signature"]
    assert first["calculated"]["energy_kwh_month"] == 21500
    assert second["calculated"]["energy_kwh_month"] == 41000
    assert len(FakeAsyncClient.calls) == 2


def test_history_and_trends_use_stored_snapshots(business, monkeypatch):
    # A second real snapshot makes period comparison possible.
    client.post("/api/climate-fingerprint/generate")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "unit-test-key")
    FakeAsyncClient.queue = [gemini_text(gemini_insight_ok())]
    body = client.get("/api/ai/dashboard-insights").json()
    assert body["history"]["fingerprint_snapshots"] >= 2
    sent = json.loads(FakeAsyncClient.calls[0]["json"]["contents"][0]["parts"][0]["text"].split("\n", 1)[1].rsplit("\n\nReturn", 1)[0])
    series = sent["history"]["resource_series"]
    assert len(series) >= 2
    assert series[0]["energy_kwh_per_month"] == TEST_ASSESSMENT["energy"]["monthlyElectricityKwh"]


# ---------------------------------------------------------------------------
# 6. Chat assistant
# ---------------------------------------------------------------------------
def test_chat_uses_stored_data(business, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "unit-test-key")
    FakeAsyncClient.queue = [gemini_text("Your water use is your largest resource pressure.")]
    body = client.post("/api/ai/chat", json={"message": "What is my biggest climate problem?"}).json()
    assert body["status"] == "ok"
    assert body["source"] == "gemini"
    assert body["has_data"] is True
    assert body["reply"].startswith("Your water use")
    sent = json.dumps(FakeAsyncClient.calls[0]["json"])
    assert str(TEST_ASSESSMENT["water"]["monthlyWaterLitres"]) in sent
    assert "ABC Textile" not in sent
    assert body["suggestions"]


def test_chat_follow_up_questions_keep_conversation_context(business, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "unit-test-key")
    FakeAsyncClient.queue = [gemini_text("Water is your weakest dimension.")]
    history = [
        {"role": "user", "content": "Why is my water score low?"},
        {"role": "assistant", "content": "Because 260000 litres is drawn monthly without recycling."},
    ]
    body = client.post("/api/ai/chat", json={"message": "What should I do about it?", "history": history}).json()
    assert body["source"] == "gemini"
    contents = FakeAsyncClient.calls[0]["json"]["contents"]
    assert [c["role"] for c in contents] == ["user", "model", "user"]
    assert "What should I do about it?" in contents[-1]["parts"][0]["text"]


def test_chat_history_is_capped_and_sanitised(business, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "unit-test-key")
    FakeAsyncClient.queue = [gemini_text("ok")]
    history = [{"role": "user", "content": f"q{i}"} for i in range(40)]
    client.post("/api/ai/chat", json={"message": "and now?", "history": history})
    contents = FakeAsyncClient.calls[0]["json"]["contents"]
    assert len(contents) == settings.AI_CHAT_MAX_HISTORY_TURNS + 1


def test_chat_calculates_payback_with_the_backend(business, monkeypatch):
    """Numeric questions must be answered from backend calculation services."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "unit-test-key")
    FakeAsyncClient.queue = [gemini_text("Use the shortest payback option first.")]
    client.post("/api/ai/chat", json={"message": "Which solution has the shortest payback?"})
    sent = json.dumps(FakeAsyncClient.calls[0]["json"])
    assert "shortest_payback" in sent and "estimated_payback_years" in sent
    assert "recommendations_with_payback" in sent


def test_chat_budget_question_uses_backend_selection(business, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "unit-test-key")
    FakeAsyncClient.queue = [gemini_text("Here is the best fit for that budget.")]
    body = client.post("/api/ai/chat", json={"message": "What should I prioritize with a ₹10 lakh budget?"}).json()
    sent = json.dumps(FakeAsyncClient.calls[0]["json"])
    assert "budget_selection" in sent
    assert "1000000" in sent.replace(".0", "")  # ₹10 lakh normalised to INR
    assert body["number_audit"]["verified"] is True


def test_chat_scenario_question_runs_the_simulation_engine(business, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "unit-test-key")
    FakeAsyncClient.queue = [gemini_text("Here is the modelled outcome.")]
    client.post("/api/ai/chat", json={"message": "What happens if I increase renewable energy?"})
    sent = json.dumps(FakeAsyncClient.calls[0]["json"])
    assert "scenario_projection" in sent
    assert "projected_climate_score" in sent


def test_chat_never_ships_invented_numbers(business, monkeypatch):
    """An answer containing unverifiable figures is retried, then replaced by calculated text."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "unit-test-key")
    FakeAsyncClient.queue = [
        gemini_text("Your emissions dropped by 987654 tonnes last quarter."),
        gemini_text("Your emissions dropped by 555555 tonnes last quarter."),
    ]
    body = client.post("/api/ai/chat", json={"message": "How have my emissions changed?"}).json()
    assert "987654" not in body["reply"]
    assert "555555" not in body["reply"]
    assert body["source"] == "calculated"
    assert body["notice"]
    assert body["number_audit"]["verified"] is True
    assert len(FakeAsyncClient.calls) == 2


def test_chat_retry_with_verified_numbers_is_used(business, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "unit-test-key")
    water = TEST_ASSESSMENT["water"]["monthlyWaterLitres"]
    FakeAsyncClient.queue = [
        gemini_text("Your water use rose by 123456 litres."),
        gemini_text(f"Your latest recorded water use is {water} litres per month."),
    ]
    body = client.post("/api/ai/chat", json={"message": "How has my water changed?"}).json()
    assert body["source"] == "gemini"
    assert str(water) in body["reply"]


def test_chat_without_key_returns_calculated_answer(business):
    body = client.post("/api/ai/chat", json={"message": "What should I do next?"}).json()
    assert body["source"] == "calculated"
    assert body["ai_available"] is False
    assert body["reply"]
    assert "gemini was unavailable" in body["reply"].lower()
    assert body["number_audit"]["verified"] is True


def test_chat_error_handling_returns_clean_message(business, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "unit-test-key")

    class BoomClient(FakeAsyncClient):
        async def post(self, url, headers=None, json=None):
            raise ai.httpx.TimeoutException("timeout")

    monkeypatch.setattr(ai.httpx, "AsyncClient", BoomClient)
    body = client.post("/api/ai/chat", json={"message": "Compare my current month with last month."}).json()
    assert body["source"] == "calculated"
    assert body["reply"]
    assert "Timeout" not in json.dumps(body)


def test_chat_empty_message_is_handled():
    body = client.post("/api/ai/chat", json={"message": "   "}).json()
    assert body["status"] == "invalid"
    assert body["reply"]


def test_chat_suggestions_reflect_data_state(business):
    with_data = client.get("/api/ai/chat/suggestions").json()
    assert with_data["has_data"] is True
    assert "What's my biggest climate risk?" in with_data["suggestions"]


def test_chat_suggestions_without_data():
    body = client.get("/api/ai/chat/suggestions").json()
    assert body["has_data"] is False
    # The four product prompts are always offered; without data the assistant
    # answers with the no-data explanation, and the extra items explain the platform.
    assert body["suggestions"]
    assert "What's my biggest climate risk?" in body["suggestions"]
    assert "Explain my climate score." in body["suggestions"]
    assert any("data do you need" in s.lower() for s in body["suggestions"])


def test_api_key_never_appears_in_any_response(business, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "super-secret-key-value")
    FakeAsyncClient.queue = [gemini_text(gemini_insight_ok()), gemini_text("ok")]
    responses = [
        client.get("/api/ai/status").text,
        client.get("/api/ai/dashboard-insights").text,
        client.post("/api/ai/chat", json={"message": "hello"}).text,
        client.get("/api/ai/chat/suggestions").text,
    ]
    for body in responses:
        assert "super-secret-key-value" not in body

def test_chat_risk_question_uses_calculated_weakest_dimension(business):
    """'What's my biggest climate risk?' must answer from stored/calculated values only."""
    weak_resp = client.get("/api/climate-fingerprint").json()
    dimensions = [d for d in weak_resp.get("dimensions", []) if d.get("score") is not None]
    weakest = min(dimensions, key=lambda d: d["score"])
    body = client.post("/api/ai/chat", json={"message": "What's my biggest climate risk?"}).json()
    reply = body["reply"]
    assert weakest["dimension"] in reply
    assert str(weakest["score"]) in reply
    assert body["source"] == "calculated"
    assert body["number_audit"]["verified"] is True


def test_chat_score_question_explains_the_stored_score(business):
    fingerprint = client.get("/api/climate-fingerprint").json()
    body = client.post("/api/ai/chat", json={"message": "Explain my climate score."}).json()
    assert str(fingerprint["overallScore"]) in body["reply"]
    assert body["number_audit"]["verified"] is True


def test_chat_change_question_reports_insufficient_history(business):
    """A single snapshot cannot support a comparison; the exact phrase must be used."""
    body = client.post("/api/ai/chat", json={"message": "What changed recently?"}).json()
    assert "not have enough stored history" in body["reply"].lower()


def test_provider_errors_are_never_exposed_to_users(business, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "invalid-key")
    FakeAsyncClient.queue = [FakeResponse(401, payload={"error": {"message": "API key not valid"}})]
    monkeypatch.setattr(ai.httpx, "AsyncClient", FakeAsyncClient)
    raw = client.get("/api/ai/dashboard-insights").text
    for leaked in ("API key not valid", "401", "invalid-key", "generativelanguage.googleapis.com"):
        assert leaked not in raw
    assert "temporarily unavailable" in raw
