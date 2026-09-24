"""
Tests for the Gemini AI intelligence layer (Phase 3).

Gemini is never called over the network in these tests: the httpx client used by
the service is replaced with a fake transport, so we can assert exactly what is
sent to Gemini and how the API behaves for success / failure / missing key.
"""
import asyncio
import json

import pytest

from app.main import app
from app.config import settings
from app.database.mongodb import get_collection
from app.database.collections import COLLECTIONS
from app.services import ai_insight_service as ai
from fastapi.testclient import TestClient

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


def gemini_text(payload: dict) -> FakeResponse:
    return FakeResponse(200, {"candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}]})


# Insight using ONLY figures that already exist in the stored/calculated context.
# Built from the live context so the guardrail test is about invented values, not stale fixtures.
def gemini_insight_ok(**overrides) -> dict:
    ctx = ai.build_context()
    energy = ctx["calculated_analytics"]["energy"]
    water = ctx["calculated_analytics"]["water"]
    score = ctx["climate_fingerprint"]["overall_score"]
    payload = {
        "summary": (
            f"Your plant spends Rs {int(energy['monthly_cost_inr'])} on {int(energy['monthly_kwh'])} kWh of grid power "
            f"and extracts {int(water['monthly_litres'])} litres of water each month."
        ),
        "recent_changes": [f"Climate readiness score is {score}/100 with only one stored snapshot."],
        "key_risk": "Groundwater dependency without closed-loop recycling.",
        "focus_now": "Water recycling and rooftop solar are the two weakest dimensions.",
        "priority_action": "Deploy ultrafiltration water recycling before scaling production.",
        "forecast": "Insufficient historical data for a reliable forecast.",
        "expected_impact": "Estimated water saving potential of about 4.8 lakh litres per month.",
        "confidence": "Medium",
        "details": {
            "data_used": ["Climate assessment (measured)", f"Fingerprint score {score}/100 (calculated)"],
            "reasoning_summary": "The insight is derived from the stored assessment, fingerprint and recommendations.",
            "historical_comparison": "Only the latest snapshot exists.",
            "main_risks": ["Escalating water cost", "Grid tariff exposure"],
            "recommended_actions": ["Install water recycling", "Evaluate rooftop solar"],
            "related_recommendations": ["sol-water-ro", "sol-solar"],
            "expected_impact_detail": "Potential savings are catalog estimates, not guaranteed.",
            "confidence_note": "Medium data completeness.",
            "assumptions": ["Steady production volume"],
        },
    }
    payload.update(overrides)
    return payload


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch):
    """Isolate tests: no cached AI payloads, no leftover API key, no queued Gemini responses."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    monkeypatch.setattr(ai.httpx, "AsyncClient", FakeAsyncClient)
    FakeAsyncClient.queue = []
    FakeAsyncClient.calls = []
    get_collection(COLLECTIONS["ai_insights"]).delete_many({})
    yield
    FakeAsyncClient.queue = []
    FakeAsyncClient.calls = []
    get_collection(COLLECTIONS["ai_insights"]).delete_many({})


# ---------------------------------------------------------------------------
# 1. Status endpoint / key configuration
# ---------------------------------------------------------------------------
def test_ai_status_without_key():
    resp = client.get("/api/ai/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["gemini_configured"] is False
    assert body["model"] == settings.GEMINI_MODEL


def test_ai_status_with_key(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "unit-test-key")
    resp = client.get("/api/ai/status")
    assert resp.status_code == 200
    assert resp.json()["gemini_configured"] is True


# ---------------------------------------------------------------------------
# 2. Missing API key -> application keeps working with calculated insights
# ---------------------------------------------------------------------------
def _internal_keys(node, path="$") -> list:
    """Walk the context and return any MongoDB-internal keys (_id, ...) that leaked in."""
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


def test_dashboard_insights_without_key_uses_calculated_fallback():
    resp = client.get("/api/ai/dashboard-insights")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ai_available"] is False
    assert body["source"] == "calculated"
    assert body["status"] in ("unavailable", "error")
    assert body["notice"] == "AI insights unavailable — showing calculated insights."
    # Calculated Phase 2 values are still exposed as the source of truth
    assert body["calculated"]["climate_score"] is not None
    assert body["calculated"]["energy_kwh_month"] is not None
    # The calculated insight is still complete enough for the dashboard + More Info
    insight = body["insight"]
    for field in ("summary", "key_risk", "priority_action", "forecast", "expected_impact", "confidence"):
        assert insight[field]
    for field in ("data_used", "reasoning_summary", "recommended_actions", "assumptions"):
        assert insight["details"][field]
    assert len(FakeAsyncClient.calls) == 0  # no AI call was attempted


def test_existing_endpoints_still_work_with_ai_layer_present():
    assert client.get("/api/profile").status_code == 200
    assert client.get("/api/assessment").status_code == 200
    assert client.get("/api/climate-fingerprint").status_code == 200
    assert client.get("/api/solutions").status_code == 200
    assert client.get("/api/transformation-plan").status_code == 200
    assert client.get("/api/impact").status_code == 200
    assert client.get("/api/reports/climate").status_code == 200


# ---------------------------------------------------------------------------
# 3. Gemini configured -> structured AI insight
# ---------------------------------------------------------------------------
def test_dashboard_insights_with_key_returns_gemini_insight(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "unit-test-key")
    FakeAsyncClient.queue = [gemini_text(gemini_insight_ok())]

    resp = client.get("/api/ai/dashboard-insights")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["source"] == "gemini"
    assert body["ai_available"] is True
    assert body["notice"] is None
    assert body["insight"]["summary"].startswith("Your plant spends")
    assert body["insight"]["details"]["number_audit"]["verified"] is True
    assert body["insight"]["details"]["number_audit"]["unsupported_values"] == []

    # Exactly one Gemini call, request carries the key only in the backend header
    assert len(FakeAsyncClient.calls) == 1
    call = FakeAsyncClient.calls[0]
    assert call["url"].endswith(f"models/{settings.GEMINI_MODEL}:generateContent")
    assert call["headers"]["x-goog-api-key"] == "unit-test-key"
    assert "responseMimeType" in json.dumps(call["json"])
    body_sent = json.dumps(call["json"])
    assert "unit-test-key" not in body_sent  # key never inside the prompt payload
    assert "MONGODB_URI" not in body_sent and "mongodb://" not in body_sent


def test_prompt_contains_existing_project_data_only():
    context = ai.build_context()
    prompt_blob = json.dumps(context, default=str)
    # Required context blocks from the spec
    for block in [
        "business_profile",
        "climate_assessment_latest",
        "climate_fingerprint",
        "calculated_analytics",
        "recommendations",
        "selected_scenario",
        "transformation_plan",
        "impact_verification",
        "history",
    ]:
        assert block in context, f"missing context block {block}"
    assert "monthlyElectricityKwh" in prompt_blob
    # No raw database dump artefacts / no secrets
    assert not _internal_keys(context), "context leaks MongoDB internal keys"
    assert "user_id" not in prompt_blob
    assert "password" not in prompt_blob.lower()
    assert "api_key" not in prompt_blob.lower()


# ---------------------------------------------------------------------------
# 4. Numeric guardrail: Gemini must not invent values
# ---------------------------------------------------------------------------
def test_unsupported_numbers_are_flagged(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "unit-test-key")
    invented = gemini_insight_ok(summary="Expect 9,99,999 kWh saved next year.")
    FakeAsyncClient.queue = [gemini_text(invented)]

    body = client.get("/api/ai/dashboard-insights").json()
    audit = body["insight"]["details"]["number_audit"]
    assert audit["verified"] is False
    assert "9,99,999" in audit["unsupported_values"]


def test_forecast_is_forced_when_no_history(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "unit-test-key")
    predicting = gemini_insight_ok(forecast="Consumption will rise by 12% next quarter.")
    FakeAsyncClient.queue = [gemini_text(predicting)]

    body = client.get("/api/ai/dashboard-insights").json()
    assert body["insight"]["forecast"] == ai.INSUFFICIENT_HISTORY


def test_history_flag_reflects_stored_snapshots():
    body = client.get("/api/ai/dashboard-insights").json()
    # A fresh database has exactly one fingerprint snapshot
    assert body["history"]["fingerprint_snapshots"] >= 1
    assert body["history"]["available"] in (True, False)
    assert isinstance(body["history"]["note"], str)


# ---------------------------------------------------------------------------
# 5. Gemini failure -> graceful fallback
# ---------------------------------------------------------------------------
def test_gemini_quota_error_falls_back(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "unit-test-key")
    FakeAsyncClient.queue = [FakeResponse(429, text="quota exceeded"), FakeResponse(429, text="quota exceeded")]

    body = client.get("/api/ai/dashboard-insights").json()
    assert body["status"] == "error"
    assert body["source"] == "calculated"
    assert body["ai_available"] is False
    assert body["notice"] == "AI insights unavailable — showing calculated insights."
    assert "429" in (body["reason"] or "")
    assert body["insight"]["summary"]


def test_gemini_invalid_json_falls_back(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "unit-test-key")
    FakeAsyncClient.queue = [FakeResponse(200, {"candidates": [{"content": {"parts": [{"text": "not json at all"}]}}]})]

    body = client.get("/api/ai/dashboard-insights").json()
    assert body["source"] == "calculated"
    assert body["notice"] == "AI insights unavailable — showing calculated insights."


def test_gemini_marked_unavailable_when_no_candidate(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "unit-test-key")
    FakeAsyncClient.queue = [FakeResponse(200, {"promptFeedback": {"blockReason": "SAFETY"}, "candidates": []})]

    body = client.get("/api/ai/dashboard-insights").json()
    assert body["source"] == "calculated"
    assert "SAFETY" in (body["reason"] or "")


# ---------------------------------------------------------------------------
# 6. Caching: Gemini is not called again for unchanged data
# ---------------------------------------------------------------------------
def test_cache_prevents_repeated_gemini_calls(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "unit-test-key")
    FakeAsyncClient.queue = [gemini_text(gemini_insight_ok())]

    first = asyncio.run(ai.get_dashboard_insights(force=False))
    assert first["source"] == "gemini"
    assert first["cached"] is False
    assert len(FakeAsyncClient.calls) == 1

    second = asyncio.run(ai.get_dashboard_insights(force=False))
    assert second["cached"] is True
    assert len(FakeAsyncClient.calls) == 1  # no second Gemini call

    # Data changes -> new signature -> regeneration
    FakeAsyncClient.queue = [gemini_text(gemini_insight_ok())]
    client.post("/api/assessment", json={"energy": {"monthlyElectricityKwh": 30123, "monthlyElectricityBillInr": 271107}})
    third = asyncio.run(ai.get_dashboard_insights(force=False))
    assert third["data_signature"] != first["data_signature"]
    assert third["cached"] is False
    assert len(FakeAsyncClient.calls) == 2

    # restore demo assessment
    client.post("/api/assessment", json={"energy": {"monthlyElectricityKwh": 38500, "monthlyElectricityBillInr": 346500}})


def test_endpoint_accepts_refresh_parameter(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "unit-test-key")
    FakeAsyncClient.queue = [gemini_text(gemini_insight_ok()), gemini_text(gemini_insight_ok())]
    assert client.get("/api/ai/dashboard-insights").json()["cached"] is False
    assert client.get("/api/ai/dashboard-insights").json()["cached"] is True
    assert client.get("/api/ai/dashboard-insights?refresh=true").json()["cached"] is False


# ---------------------------------------------------------------------------
# 7. Historical comparison uses stored snapshots when they exist
# ---------------------------------------------------------------------------
def test_history_is_included_when_earlier_snapshot_exists(monkeypatch):
    from datetime import datetime, timedelta, timezone
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "unit-test-key")
    col = get_collection(COLLECTIONS["climate_fingerprints"])
    latest = col.find_one({}, sort=[("created_at", -1)])
    assert latest is not None
    older = dict(latest)
    older_id = older.pop("_id")
    older["overallScore"] = 51
    older["created_at"] = datetime.now(timezone.utc) - timedelta(days=30)
    older["updated_at"] = older["created_at"]
    col.insert_one(older)

    body = client.get("/api/ai/dashboard-insights").json()
    assert body["history"]["available"] is True
    assert body["history"]["fingerprint_snapshots"] >= 2

    context = ai.build_context()
    assert len(context["history"]["previous_fingerprints"]) >= 1
    col.delete_one({"_id": older_id})


# ---------------------------------------------------------------------------
# 8. Unit-level guardrails
# ---------------------------------------------------------------------------
def test_number_audit_allows_calculated_forms():
    context = {"a": 174000, "b": 38500.0, "change_percent": -19.48}
    insight = {"summary": "₹1.74 lakh saved; 38,500 kWh consumed; a 19.48% drop was observed."}
    audit = ai.audit_numbers(insight, context)
    assert audit["verified"] is True, audit["unsupported_values"]


def test_number_audit_flags_unknown_values():
    audit = ai.audit_numbers({"summary": "Save 4,44,321 kWh."}, {"a": 100})
    assert audit["verified"] is False
    assert "4,44,321" in audit["unsupported_values"]


def test_normalize_insight_tolerates_missing_fields():
    normalized = ai.normalize_insight({}, {"history": {"has_history": False}, "climate_fingerprint": {}})
    assert normalized["forecast"] == ai.INSUFFICIENT_HISTORY
    assert normalized["recent_changes"] == []
    assert normalized["details"]["number_audit"]["verified"] is True
    assert normalized["confidence"] in ("High", "Medium", "Low")


def test_calculated_insight_contains_no_invented_numbers():
    context = ai.build_context()
    fallback = ai._calculated_insight(context, "test reason")
    audit = ai.audit_numbers(fallback, context)
    assert audit["verified"] is True, audit["unsupported_values"]
    assert fallback["details"]["number_audit"]["verified"] is True
