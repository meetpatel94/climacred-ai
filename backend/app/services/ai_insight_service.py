"""
ClimaCred AI - Gemini Dashboard Intelligence layer.

This module adds an AI *interpretation* layer on top of the existing Phase 2
engines. It does not replace or duplicate any calculation:

  1. It reads the user's already-stored data through the EXISTING Phase 2
     services (profile, assessment, fingerprint, analytics, recommendations,
     scenario simulator, transformation plan, impact verification).
  2. It builds one compact structured context (no raw database dumps).
  3. It asks Google Gemini (official REST API) to interpret that context and
     return structured JSON.
  4. It audits every number returned by Gemini against the calculated values,
     so Gemini can never silently invent figures.
  5. If Gemini is not configured / fails / is rate limited, the dashboard keeps
     working with a deterministic "calculated insight" generated from the same
     Phase 2 outputs.

Everything stays inside the existing FastAPI backend, so GEMINI_API_KEY is
never exposed to the frontend.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

import httpx

from app.config import settings
from app.database.mongodb import get_collection
from app.database.collections import COLLECTIONS
from app.services.profile_service import get_profile
from app.services.assessment_service import get_assessment, has_assessment_data
from app.services.fingerprint_service import get_or_generate_fingerprint
from app.services.solution_service import get_personalized_recommendations
from app.services.transformation_service import get_transformation_plan
from app.services.impact_service import get_impact_records, get_latest_impact_as_verification_metrics
from app.services.scenario_service import get_scenario_history
from app.utils.calculations import (
    calculate_energy_metrics,
    calculate_water_metrics,
    calculate_waste_metrics,
    calculate_emissions_metrics,
    calculate_mobility_metrics,
    calculate_data_quality_score,
)
from app.climate_engine.simulations import simulate_with_fingerprint

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = "default"
AI_INSIGHT_COLLECTION = COLLECTIONS["ai_insights"]

STATUS_OK = "ok"
STATUS_UNAVAILABLE = "unavailable"
STATUS_ERROR = "error"
STATUS_NO_DATA = "no_data"

# User-facing copy only. Raw provider errors (HTTP codes, model names, quota
# messages) are logged server-side and never shown in the UI.
NOTICE_UNAVAILABLE = "AI insights are temporarily unavailable."
NOTICE_NO_DATA = "No business climate data yet."
INSUFFICIENT_HISTORY = "Insufficient historical data for a reliable forecast."

DISCLAIMER = (
    "AI-generated interpretation of your calculated ClimaCred data. Values shown are "
    "estimates from the Phase 2 engine, not guaranteed outcomes and not a certified audit."
)

SYSTEM_PROMPT = """You are ClimaCred AI, a climate-intelligence analyst for Indian SMEs.

You receive ONE JSON object ("CONTEXT") containing values that were ALREADY CALCULATED by the ClimaCred
Phase 2 engine from the business's own stored data, plus a "history" block describing whether earlier
snapshots exist.

HARD RULES (never break these):
1. NEVER invent, estimate or extrapolate a number. Every numeric value you write must already appear in
   CONTEXT, or be a direct sum/difference/ranking of values in CONTEXT stated in words.
2. Never present AI output as a guaranteed outcome. Use language such as "estimated", "projected", "may".
3. If CONTEXT.history.has_history is false, you must not compare periods or predict a future value.
   In that case set "forecast" to exactly: "Insufficient historical data for a reliable forecast."
   and say that comparison/forecasting is limited in "summary".
4. Distinguish clearly: "measured" (user-submitted inputs), "calculated" (Phase 2 deterministic values),
   "estimated" (potential savings / projected impacts), and "demo" data when CONTEXT marks it so.
5. Be concise and useful for a business owner: no filler, no repetition, plain English.
6. Return ONLY a valid JSON object matching the requested schema. No markdown, no commentary.

Length limits: summary <= 320 chars, key_risk <= 220, priority_action <= 220, focus_now <= 200,
forecast <= 200, expected_impact <= 200, each recent_changes item <= 160, reasoning_summary <= 700.
Arrays: max 4 items unless stated otherwise."""

RESPONSE_SCHEMA_HINT = """{
  "summary": "one concise, business-ready insight about the current state",
  "recent_changes": ["what changed vs the previous snapshot / latest submission"],
  "key_risk": "the single most important current climate risk or inefficiency",
  "focus_now": "what the business should focus on right now",
  "priority_action": "the recommended next concrete action",
  "forecast": "short forecast/prediction when history supports it, else the exact insufficient-data sentence",
  "expected_impact": "expected business + environmental impact of the priority action",
  "confidence": "High | Medium | Low",
  "details": {
    "data_used": ["short labels of the stored data actually used"],
    "reasoning_summary": "why you generated this insight, in 2-4 sentences",
    "historical_comparison": "what earlier snapshots show, or that history is not available yet",
    "main_risks": ["2-4 risks"],
    "recommended_actions": ["2-4 concrete actions, referencing existing ClimaCred recommendations when possible"],
    "related_recommendations": ["ids or titles from CONTEXT.recommendations that support the insight"],
    "expected_impact_detail": "measured/estimated impact detail, explicitly flagged as estimated",
    "confidence_note": "data availability / confidence explanation",
    "assumptions": ["assumptions actually used"]
  }
}"""


# ---------------------------------------------------------------------------
# Number audit (prevents invented figures reaching the dashboard)
# ---------------------------------------------------------------------------
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)*")


def _norm_number(token: str) -> str:
    """Normalise a numeric token: '1,74,000' -> '174000', '0.820' -> '0.82', '-19.5' -> '19.5'."""
    cleaned = token.replace(",", "").strip().lstrip("+-")
    if cleaned.endswith("."):
        cleaned = cleaned[:-1]
    try:
        value = float(cleaned)
    except ValueError:
        return cleaned
    if value == int(value):
        return str(int(value))
    return f"{round(value, 4):g}"


def _candidate_forms(value: float) -> Set[str]:
    """Allowed forms of a calculated value (raw, thousand, lakh, crore + rounded)."""
    forms: Set[str] = set()
    for scaled in (value, value / 1000.0, value / 100000.0, value / 10000000.0):
        for rounded in (scaled, round(scaled, 1), round(scaled, 2)):
            forms.add(_norm_number(f"{rounded}"))
    return forms


def _walk_numbers(node: Any, out: Set[str]) -> None:
    if isinstance(node, bool):
        return
    if isinstance(node, (int, float)):
        out |= _candidate_forms(float(node))
    elif isinstance(node, str):
        for token in _NUMBER_RE.findall(node):
            out.add(_norm_number(token))
    elif isinstance(node, dict):
        for v in node.values():
            _walk_numbers(v, out)
    elif isinstance(node, (list, tuple)):
        for v in node:
            _walk_numbers(v, out)


def _allowed_numbers(context: Dict[str, Any]) -> Set[str]:
    """All numeric tokens Gemini may reuse: context values, list sizes and the current year."""
    allowed: Set[str] = set()
    _walk_numbers(context, allowed)
    for value in _iter_list_lengths(context):
        allowed |= _candidate_forms(float(value))
    now = datetime.now(timezone.utc)
    allowed |= _candidate_forms(float(now.year))
    allowed |= _candidate_forms(float(now.month))
    return allowed


def _iter_list_lengths(node: Any):
    if isinstance(node, dict):
        for v in node.values():
            yield from _iter_list_lengths(v)
    elif isinstance(node, list):
        yield len(node)
        for v in node:
            yield from _iter_list_lengths(v)


def _strings_from_insight(node: Any):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from _strings_from_insight(v)
    elif isinstance(node, list):
        for v in node:
            yield from _strings_from_insight(v)


def audit_numbers(insight: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Return which numeric tokens in the AI output are NOT backed by calculated data."""
    allowed = _allowed_numbers(context)
    unsupported: List[str] = []
    for text in _strings_from_insight(insight):
        for token in _NUMBER_RE.findall(text):
            normalized = _norm_number(token)
            if normalized not in allowed and token not in unsupported:
                unsupported.append(token)
    return {"verified": len(unsupported) == 0, "unsupported_values": unsupported[:10]}


# ---------------------------------------------------------------------------
# Context building (reuses existing Phase 2 services only)
# ---------------------------------------------------------------------------
def _truncate(text: Any, limit: int = 240) -> str:
    value = "" if text is None else str(text)
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"


def _round(value: Any, digits: int = 2) -> Any:
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return value


def build_context(user_id: str = DEFAULT_USER_ID, history_limit: int = 6) -> Dict[str, Any]:
    """Collect the user's existing stored data into one compact, prompt-safe context.

    Only stored user data and derived engine values are collected. When the user
    has no stored data the context is marked ``has_data = False`` and no business
    values are invented.
    """
    profile = get_profile(user_id) or {}
    assessment = get_assessment(user_id) or {}
    fingerprint = get_or_generate_fingerprint(user_id) or {}
    has_profile = bool(profile)
    has_assessment = has_assessment_data(assessment)
    has_data = has_profile and has_assessment

    energy = calculate_energy_metrics(assessment, profile)
    water = calculate_water_metrics(assessment, profile)
    waste = calculate_waste_metrics(assessment)
    emissions = calculate_emissions_metrics(assessment)
    mobility = calculate_mobility_metrics(assessment)
    quality = calculate_data_quality_score(profile, assessment)

    recommendations = get_personalized_recommendations(user_id=user_id, top_n=5) or []
    plan_items = get_transformation_plan(user_id) or []
    impact_records = get_impact_records(user_id, limit=5) or []
    impact_metrics = get_latest_impact_as_verification_metrics(user_id) or []
    scenario_history = get_scenario_history(user_id, limit=2) or []
    fingerprint_history = _fingerprint_history(user_id, history_limit)
    resource_series = _resource_series(user_id, history_limit)

    # "Selected scenario" = latest simulator run, else the deterministic projection of the top 2
    # recommendations (pure engine call, nothing is written to the database).
    selected_scenario = None
    if scenario_history:
        latest = scenario_history[0]
        selected_scenario = {
            "origin": "user_selected_in_simulator",
            "selected_solutions": latest.get("selected_solution_ids"),
            "adoption_scale_percent": latest.get("adoption_scale_percent"),
            "investment_inr": (latest.get("result") or {}).get("investment", {}).get("min_inr"),
            "annual_savings_inr": (latest.get("result") or {}).get("annual_savings_inr"),
            "payback_years": (latest.get("result") or {}).get("payback_period_years"),
            "projected_climate_score": (latest.get("result") or {}).get("projected_climate_score"),
            "run_at": latest.get("created_at"),
        }
    else:
        top_ids = [r.get("solution_id") for r in recommendations[:2] if r.get("solution_id")]
        if top_ids:
            simulated = simulate_with_fingerprint(top_ids, profile, assessment, fingerprint, scale=100)
            selected_scenario = {
                "origin": "engine_default_top_recommendations",
                "selected_solutions": top_ids,
                "adoption_scale_percent": 100,
                "investment_inr": (simulated.get("investment") or {}).get("min_inr"),
                "annual_savings_inr": simulated.get("annual_savings_inr"),
                "payback_years": simulated.get("payback_period_years"),
                "projected_climate_score": simulated.get("projected_climate_score"),
            }

    dimensions = []
    for dim in fingerprint.get("dimensions", []) or []:
        dimensions.append({
            "dimension": dim.get("dimension"),
            "score": dim.get("score"),
            "impact_level": dim.get("impactLevel"),
            "confidence": dim.get("confidence"),
            "primary_cause": _truncate(dim.get("primaryCause"), 160),
            "improvement_opportunity": _truncate(dim.get("improvementOpportunity"), 160),
        })

    has_history = len(fingerprint_history) > 1 or bool(impact_records)
    resource_changes = _resource_changes(resource_series)

    context: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        # Explicit data availability. Gemini (and the deterministic fallback) must
        # never answer business-specific questions when has_data is false.
        "data_state": {
            "has_data": has_data,
            "has_business_profile": has_profile,
            "has_climate_assessment": has_assessment,
            "has_climate_fingerprint": bool(fingerprint.get("overallScore") is not None),
            "message": (
                "Stored business climate data is available for analysis."
                if has_data
                else "No business climate data is stored yet. The user has not completed a Climate Assessment."
            ),
        },
        "data_classification": {
            "measured": "Business profile + climate assessment values submitted by the user.",
            "calculated": "Deterministic Phase 2 engine outputs (emissions, costs, scores, percentages).",
            "estimated": "Potential savings / projected impacts derived from catalog assumptions.",
            "demo": "Illustrative values included only where explicitly labelled 'demo'.",
        },
        "business_profile": {
            "name": profile.get("business_name") or profile.get("name"),
            "industry": profile.get("industry"),
            "business_type": profile.get("business_type") or profile.get("businessType"),
            "location": profile.get("location"),
            "employees": profile.get("employees"),
            "business_size": profile.get("business_size") or profile.get("businessSize"),
            "facility_area_sqft": profile.get("facility_area_sqft") or profile.get("facilityAreaSqFt"),
            "operating_hours_per_day": profile.get("operating_hours") or profile.get("operatingHoursPerDay"),
            "working_days_per_month": profile.get("working_days") or profile.get("workingDaysPerMonth"),
            "production_volume": profile.get("production_volume") or profile.get("productionVolume"),
        },
        "climate_fingerprint": {
            "overall_score": fingerprint.get("overallScore"),
            "score_label": fingerprint.get("scoreLabel"),
            "confidence": fingerprint.get("confidence"),
            "benchmark_percentile": fingerprint.get("benchmarkPercentile"),
            "summary_note": _truncate(fingerprint.get("summaryNote"), 320),
            "top_improvement_dimensions": fingerprint.get("topImprovementDimensions"),
            "dimensions": dimensions,
            "generated_at": fingerprint.get("generated_at") or fingerprint.get("created_at"),
        },
        "climate_assessment_latest": assessment,
        "calculated_analytics": {
            "energy": {
                "monthly_kwh": _round(energy.get("monthly_electricity_kwh")),
                "annual_kwh": _round(energy.get("annual_electricity_kwh")),
                "monthly_cost_inr": _round(energy.get("monthly_electricity_cost_inr")),
                "annual_cost_inr": _round(energy.get("annual_electricity_cost_inr")),
                "annual_emissions_tonnes_co2e": energy.get("estimated_annual_electricity_emissions_tonnes_co2e"),
                "grid_emission_factor_kg_per_kwh": (energy.get("emission_factor_used") or {}).get("factor"),
            },
            "water": {
                "monthly_litres": _round(water.get("monthly_water_litres")),
                "annual_litres": _round(water.get("annual_water_litres")),
                "estimated_potential_annual_savings_litres": _round(water.get("estimated_potential_annual_savings_litres")),
                "estimated_potential_savings_percent": water.get("estimated_potential_savings_percent"),
            },
            "waste": {
                "monthly_kg": _round(waste.get("total_waste_kg_per_month")),
                "annual_kg": _round(waste.get("annual_waste_kg")),
                "recycling_rate_percent": waste.get("recycling_rate_percent"),
                "material_recovery_opportunity_kg_per_month": _round(waste.get("material_recovery_opportunity_kg_per_month")),
                "breakdown_kg_per_month": waste.get("breakdown"),
            },
            "emissions": {
                "monthly_total_tonnes_co2e": (emissions.get("emissions_breakdown_tonnes_co2e_per_month") or {}).get("total"),
                "annual_total_tonnes_co2e": emissions.get("annual_total_tonnes_co2e"),
                "breakdown_tonnes_co2e_per_month": emissions.get("emissions_breakdown_tonnes_co2e_per_month"),
            },
            "mobility": {
                "vehicles": mobility.get("delivery_vehicles_count"),
                "fuel_type": mobility.get("vehicle_fuel_type"),
                "monthly_fuel_litres": _round(mobility.get("monthly_fuel_litres")),
                "annual_mobility_emissions_tonnes_co2e": mobility.get("annual_mobility_emissions_tonnes_co2e"),
                "ev_adopted_percent": mobility.get("ev_adopted_percent"),
            },
            "data_quality": {
                "completeness_percent": quality.get("completeness_percent"),
                "level": quality.get("level"),
                "missing_fields_count": quality.get("total_missing"),
                "message": _truncate(quality.get("message"), 240),
            },
        },
        "recommendations": [
            {
                "solution_id": r.get("solution_id"),
                "title": (r.get("solution") or {}).get("title"),
                "category": (r.get("solution") or {}).get("category"),
                "priority": r.get("priority"),
                "confidence": r.get("confidence"),
                "annual_savings_inr": (r.get("solution") or {}).get("potentialAnnualSavingsInr"),
                "investment_range_inr": [
                    (r.get("solution") or {}).get("investmentMinInr"),
                    (r.get("solution") or {}).get("investmentMaxInr"),
                ],
                "payback_years": (r.get("solution") or {}).get("estimatedPaybackPeriodYears"),
                "resource_reduction": (r.get("solution") or {}).get("resourceReductionValue"),
                "co2_reduction_tonnes_per_year": (r.get("solution") or {}).get("co2ReductionTonnesPerYear"),
                "reason": _truncate(r.get("reason"), 220),
            }
            for r in recommendations
        ],
        "selected_scenario": selected_scenario,
        "transformation_plan": [
            {
                "phase": item.get("phase"),
                "action": item.get("action") or item.get("title"),
                "priority": item.get("priority"),
                "status": item.get("status"),
                "timeframe": item.get("timeframe") or item.get("timeline"),
                "expected_benefit": _truncate(item.get("expectedBenefit") or item.get("expected_benefit"), 160),
            }
            for item in plan_items[:8]
        ],
        "impact_verification": {
            "records_available": len(impact_records),
            "latest_metrics": [
                {
                    "metric": m.get("name"),
                    "category": m.get("category"),
                    "before": m.get("beforeValue"),
                    "after": m.get("afterValue"),
                    "change": m.get("differenceValue"),
                    "change_percent": m.get("differencePercent"),
                    "verdict": _truncate(m.get("impactVerdict"), 160),
                }
                for m in impact_metrics[:5]
            ],
        },
        "history": {
            "has_history": has_history,
            "fingerprint_snapshots": len(fingerprint_history),
            "latest_fingerprint": fingerprint_history[0] if fingerprint_history else None,
            "previous_fingerprints": fingerprint_history[1:],
            "impact_records_count": len(impact_records),
            "scenario_runs_count": len(scenario_history),
            # Real per-snapshot resource values (from stored fingerprints) used for
            # period-over-period comparison. Empty when no snapshots are stored.
            "resource_series": resource_series,
            "resource_changes": resource_changes,
            "note": (
                "Earlier snapshots are available for comparison."
                if has_history
                else "Only the latest snapshot exists; period comparison and forecasting are limited."
            ),
        },
    }
    return context


def _resource_series(user_id: str, limit: int) -> List[Dict[str, Any]]:
    """Real resource values per stored fingerprint snapshot (oldest → newest)."""
    from app.services.fingerprint_service import get_fingerprint_history

    series: List[Dict[str, Any]] = []
    for snapshot in get_fingerprint_history(user_id, limit=limit):
        metrics = snapshot.get("dimension_metrics") or {}
        energy = metrics.get("Energy") or {}
        water = metrics.get("Water") or {}
        waste = metrics.get("Waste") or {}
        emissions = metrics.get("Emissions") or {}
        mobility = metrics.get("Mobility") or {}
        series.append({
            "recorded_at": snapshot.get("created_at"),
            "climate_score": snapshot.get("overall_score"),
            "energy_kwh_per_month": energy.get("monthly_kwh"),
            "water_litres_per_month": water.get("monthly_litres"),
            "waste_kg_per_month": waste.get("total_waste_kg"),
            "emissions_tonnes_per_month": emissions.get("total_tonnes_monthly"),
            "mobility_fuel_litres_per_month": mobility.get("monthly_fuel"),
        })
    return [row for row in series if any(
        row[key] is not None for key in (
            "energy_kwh_per_month", "water_litres_per_month", "waste_kg_per_month",
            "emissions_tonnes_per_month", "mobility_fuel_litres_per_month",
        )
    )]


def _resource_changes(series: List[Dict[str, Any]]) -> Dict[str, Any]:
    """First vs latest stored value per resource. Only reported when 2+ records exist."""
    if len(series) < 2:
        return {"available": False, "note": "Insufficient stored history for a period comparison."}
    metrics = {
        "energy_kwh_per_month": "energy",
        "water_litres_per_month": "water",
        "waste_kg_per_month": "waste",
        "emissions_tonnes_per_month": "emissions",
        "mobility_fuel_litres_per_month": "mobility",
    }
    changes: Dict[str, Any] = {"available": True, "records_compared": len(series)}
    first, latest = series[0], series[-1]
    for key, label in metrics.items():
        a, b = first.get(key), latest.get(key)
        if a in (None, 0) or b is None or a is None:
            continue
        pct = round((b - a) / a * 100, 1)
        changes[label] = {
            "first_value": a,
            "latest_value": b,
            "change_percent": pct,
            "direction": "increase" if pct > 0 else "decrease" if pct < 0 else "flat",
            "first_recorded_at": first.get("recorded_at"),
            "latest_recorded_at": latest.get("recorded_at"),
        }
    return changes


def _fingerprint_history(user_id: str, limit: int) -> List[Dict[str, Any]]:
    try:
        col = get_collection(COLLECTIONS["climate_fingerprints"])
        cursor = col.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
        history: List[Dict[str, Any]] = []
        for doc in cursor:
            created = doc.get("created_at")
            history.append({
                "created_at": created.isoformat() if hasattr(created, "isoformat") else created,
                "overall_score": doc.get("overallScore"),
                "score_label": doc.get("scoreLabel"),
                "dimension_scores": {
                    d.get("dimension"): d.get("score") for d in (doc.get("dimensions") or [])
                },
            })
        return history
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(f"Fingerprint history unavailable: {exc}")
        return []


#: Keys that change on every request and therefore must not influence the data signature.
_VOLATILE_KEYS = ("generated_at",)


def data_signature(context: Dict[str, Any]) -> str:
    """Stable hash of the stored data: identical data => identical signature => cached insight."""
    stable = {k: v for k, v in context.items() if k not in _VOLATILE_KEYS}
    payload = json.dumps(stable, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


# ---------------------------------------------------------------------------
# Gemini call (official REST API, server-side only)
# ---------------------------------------------------------------------------
def gemini_configured() -> bool:
    return bool((settings.GEMINI_API_KEY or "").strip())


def _gemini_base() -> str:
    """Normalised API base, tolerant of a trailing slash or an accidental /models suffix."""
    base = (settings.GEMINI_API_BASE or "https://generativelanguage.googleapis.com/v1beta").strip().rstrip("/")
    if base.endswith("/models"):
        base = base[: -len("/models")]
    return base


def _candidate_models() -> List[str]:
    """Configured model first, then the configured fallbacks (401/404-safe).

    A 404 from Google's API is almost always "model not found / not supported for
    this API version". Trying the configured fallback list (and logging the real
    error) means a wrong GEMINI_MODEL no longer breaks the AI layer.
    """
    primary = (settings.GEMINI_MODEL or "").strip()
    fallbacks = [m.strip() for m in (settings.GEMINI_MODEL_FALLBACKS or "").split(",") if m.strip()]
    ordered: List[str] = []
    for model in [primary, *fallbacks]:
        if model and model not in ordered:
            ordered.append(model)
    return ordered


def gemini_model_name() -> str:
    """Model reported to the UI (the primary configured model)."""
    return (settings.GEMINI_MODEL or "gemini-2.5-flash").strip()


def _gemini_url(model: str) -> str:
    return f"{_gemini_base()}/models/{model}:generateContent"


def _gemini_payload(context: Dict[str, Any]) -> Dict[str, Any]:
    user_prompt = (
        "CONTEXT (all values already calculated by ClimaCred Phase 2 — do not invent numbers):\n"
        f"{json.dumps(context, ensure_ascii=False, default=str)}\n\n"
        "Return ONLY JSON with this exact structure:\n"
        f"{RESPONSE_SCHEMA_HINT}"
    )
    return {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "temperature": 0.25,
            "topP": 0.9,
            "maxOutputTokens": 2048,
            "responseMimeType": "application/json",
        },
    }


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(cleaned[start:end + 1])
            except json.JSONDecodeError:
                return None
    return None


async def call_gemini(
    context: Dict[str, Any],
    payload_builder=None,
    used_models: Optional[List[str]] = None,
    expect_json: bool = True,
) -> Tuple[Optional[Any], Optional[str]]:
    """Call Gemini's generateContent API. Returns (parsed_json, error_reason).

    Never raises, and never leaks the raw provider error to the caller's response
    body — errors are logged here and only a short reason string is returned for
    server-side logging.
    """
    if not gemini_configured():
        return None, "GEMINI_API_KEY not configured"

    builder = payload_builder or _gemini_payload
    timeout = httpx.Timeout(float(settings.GEMINI_TIMEOUT_SECONDS), connect=10.0)
    headers = {
        "x-goog-api-key": settings.GEMINI_API_KEY,
        "Content-Type": "application/json",
    }
    last_error: Optional[str] = None

    for model in _candidate_models():
        if used_models is not None and model not in used_models:
            used_models.append(model)
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(_gemini_url(model), headers=headers, json=builder(context))
                if response.status_code in (429, 500, 502, 503, 504) and attempt == 0:
                    last_error = f"Gemini transient error {response.status_code}"
                    logger.warning(f"{last_error} (model={model}); retrying once")
                    continue
                if response.status_code == 404:
                    # Model not found for this API version -> try the next candidate.
                    detail = (response.text or "")[:300]
                    last_error = f"Gemini model '{model}' not found (404)"
                    logger.error(
                        "%s - POST %s returned 404. Check GEMINI_MODEL. Response: %s",
                        last_error, _gemini_url(model), detail,
                    )
                    break
                if response.status_code in (401, 403):
                    last_error = f"Gemini rejected the API key ({response.status_code})"
                    logger.error(
                        "%s - GEMINI_API_KEY was rejected by %s. Verify the key in backend/.env",
                        last_error, _gemini_url(model),
                    )
                    return None, last_error
                if response.status_code != 200:
                    detail = (response.text or "")[:300]
                    last_error = f"Gemini API error {response.status_code}"
                    logger.warning("%s (model=%s): %s", last_error, model, detail)
                    break
                data = response.json()
                candidates = data.get("candidates") or []
                if not candidates:
                    reason = (data.get("promptFeedback") or {}).get("blockReason")
                    last_error = f"Gemini returned no candidate ({reason or 'unknown reason'})"
                    logger.warning("%s (model=%s)", last_error, model)
                    break
                parts = ((candidates[0].get("content") or {}).get("parts")) or []
                text = "".join(p.get("text", "") for p in parts)
                if not expect_json:
                    # Chat replies are plain text.
                    if not text.strip():
                        last_error = "Gemini returned an empty response"
                        logger.warning("%s (model=%s)", last_error, model)
                        break
                    if model != gemini_model_name():
                        logger.info("Gemini responded using fallback model '%s'", model)
                    return text, None
                parsed = _extract_json(text)
                if not parsed:
                    last_error = "Gemini response was not valid JSON"
                    logger.warning("%s (model=%s)", last_error, model)
                    break
                if model != gemini_model_name():
                    logger.info("Gemini responded using fallback model '%s'", model)
                return parsed, None
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = f"Gemini request failed: {exc.__class__.__name__}"
                logger.warning("%s (model=%s)", last_error, model)
            except Exception as exc:  # pragma: no cover - defensive
                last_error = f"Gemini call error: {exc.__class__.__name__}"
                logger.warning(last_error, exc_info=True)
                return None, last_error
    return None, last_error or "Gemini request failed"


# ---------------------------------------------------------------------------
# Normalisation + deterministic fallback
# ---------------------------------------------------------------------------
def _as_text(value: Any, limit: int) -> str:
    return _truncate(value, limit) if value is not None else ""


def _as_list(value: Any, limit: int = 4, item_limit: int = 200) -> List[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    out: List[str] = []
    for item in value[:limit]:
        if isinstance(item, dict):
            item = " — ".join(str(v) for v in item.values() if isinstance(v, (str, int, float)))
        text = _truncate(item, item_limit).strip()
        if text:
            out.append(text)
    return out


def normalize_insight(raw: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Coerce the model output into the stable dashboard schema (never trust the shape)."""
    details = raw.get("details") if isinstance(raw.get("details"), dict) else {}
    confidence = str(raw.get("confidence") or "").strip().title()
    if confidence not in ("High", "Medium", "Low"):
        confidence = str(context.get("climate_fingerprint", {}).get("confidence") or "Medium").title()

    has_history = bool(context.get("history", {}).get("has_history"))
    forecast = _as_text(raw.get("forecast"), 240).strip()
    if not forecast:
        forecast = INSUFFICIENT_HISTORY if not has_history else "No forecast generated from the available data."

    insight = {
        "summary": _as_text(raw.get("summary"), 400),
        "recent_changes": _as_list(raw.get("recent_changes"), limit=4, item_limit=200),
        "key_risk": _as_text(raw.get("key_risk"), 300),
        "focus_now": _as_text(raw.get("focus_now"), 260),
        "priority_action": _as_text(raw.get("priority_action"), 300),
        "forecast": forecast,
        "expected_impact": _as_text(raw.get("expected_impact"), 300),
        "confidence": confidence,
        "details": {
            "data_used": _as_list(details.get("data_used"), limit=8, item_limit=120),
            "reasoning_summary": _as_text(details.get("reasoning_summary"), 900),
            "historical_comparison": _as_text(details.get("historical_comparison"), 500),
            "why_it_matters": _as_text(details.get("why_it_matters"), 500),
            "main_risks": _as_list(details.get("main_risks"), limit=4),
            "recommended_actions": _as_list(details.get("recommended_actions"), limit=4),
            "related_recommendations": _as_list(details.get("related_recommendations"), limit=5, item_limit=160),
            "expected_impact_detail": _as_text(details.get("expected_impact_detail"), 500),
            "confidence_note": _as_text(details.get("confidence_note"), 400),
            "assumptions": _as_list(details.get("assumptions"), limit=5),
        },
    }

    if not has_history:
        # Guardrail: without earlier snapshots Gemini must not predict a future value.
        insight["forecast"] = INSUFFICIENT_HISTORY
        if not insight["details"]["historical_comparison"]:
            insight["details"]["historical_comparison"] = (
                "No earlier snapshot is stored yet, so period-over-period comparison is limited."
            )

    insight["details"]["number_audit"] = audit_numbers(insight, context)
    return insight


def _calculated_insight(context: Dict[str, Any], reason: str) -> Dict[str, Any]:
    """Deterministic insight used when Gemini is unavailable — Phase 2 outputs only."""
    fp = context.get("climate_fingerprint", {})
    dims = fp.get("dimensions") or []
    top_dim = None
    for dim in dims:
        if top_dim is None or (dim.get("score") or 100) < (top_dim.get("score") or 100):
            top_dim = dim
    recs = context.get("recommendations") or []
    top_rec = recs[0] if recs else {}
    analytics = context.get("calculated_analytics", {})
    history = context.get("history", {})
    impact = context.get("impact_verification", {})

    recent_changes: List[str] = []
    if history.get("has_history"):
        latest = history.get("latest_fingerprint") or {}
        previous = (history.get("previous_fingerprints") or [{}])[0]
        if latest.get("overall_score") is not None and previous.get("overall_score") is not None:
            delta = round(latest["overall_score"] - previous["overall_score"], 1)
            direction = "improved" if delta > 0 else "declined" if delta < 0 else "held steady"
            recent_changes.append(
                f"Climate readiness {direction} by {abs(delta)} points vs the previous snapshot "
                f"({previous['overall_score']} → {latest['overall_score']})."
            )
        latest_metrics = impact.get("latest_metrics") or []
        if latest_metrics:
            first = latest_metrics[0]
            recent_changes.append(
                f"Latest verified impact on {first.get('metric')}: {first.get('change_percent')}% change "
                f"({first.get('before')} → {first.get('after')})."
            )
    if not recent_changes:
        recent_changes = [
            "Only one stored snapshot is available, so no reliable change comparison can be shown yet.",
            "Update your Climate Assessment to create the next comparable snapshot.",
        ]

    forecast = INSUFFICIENT_HISTORY
    comparison = "No earlier snapshot is stored yet, so period-over-period comparison is limited."
    if history.get("has_history"):
        comparison = f"{history.get('fingerprint_snapshots')} stored fingerprint snapshots were compared."
        forecast = "Trend direction is derived from your stored snapshots; a longer history improves accuracy."

    energy = analytics.get("energy", {})
    water = analytics.get("water", {})
    insight = {
        "summary": _truncate(
            fp.get("summary_note")
            or "Your latest calculated climate data has been summarised from the Phase 2 engine.",
            320,
        ),
        "recent_changes": recent_changes,
        "key_risk": _truncate(
            (top_dim or {}).get("primary_cause")
            or "Highest-impact resource inefficiency identified by the Climate Fingerprint.",
            280,
        ),
        "focus_now": _truncate(
            f"{(top_dim or {}).get('dimension', 'Resource efficiency')} is the weakest dimension "
            f"({(top_dim or {}).get('score')}/100).",
            260,
        ),
        "priority_action": _truncate(
            f"Start with: {top_rec['title']}" if top_rec.get("title") else "Generate your transformation plan.",
            280,
        ),
        "forecast": forecast,
        "expected_impact": _truncate(
            "Estimated: "
            + (top_rec.get("resource_reduction") or "resource reduction per the solution catalog")
            + (
                f" • ₹{int(top_rec['annual_savings_inr']):,} potential annual savings"
                if top_rec.get("annual_savings_inr")
                else ""
            ),
            300,
        ),
        "confidence": str(fp.get("confidence") or "Medium").title(),
        "details": {
            "data_used": [
                "Business profile (stored)",
                "Latest climate assessment (stored)",
                f"Climate fingerprint score {fp.get('overall_score')}/100",
                f"Energy {energy.get('monthly_kwh')} kWh/month",
                f"Water {water.get('monthly_litres')} litres/month",
                "Phase 2 recommendations + transformation plan",
            ],
            "reasoning_summary": (
                "Gemini was not used for this insight, so it was composed deterministically from "
                "ClimaCred's Phase 2 fingerprint, analytics and recommendation outputs. Every figure "
                "matches your calculated data. (The technical reason is recorded in the server log.)"
            ),
            "historical_comparison": comparison,
            "why_it_matters": _truncate(
                (
                    f"{(top_dim or {}).get('dimension', 'This dimension')} is your lowest-scoring dimension "
                    f"({(top_dim or {}).get('score')}/100). {(top_dim or {}).get('primary_cause') or ''} "
                    "Improving it lowers operating cost, regulatory exposure and buyer audit risk."
                ).strip(),
                500,
            ),
            "main_risks": _as_list(
                [d.get("primary_cause") for d in dims[:3]] or ["Data completeness limits analysis depth."],
                limit=3,
            ),
            "recommended_actions": _as_list(
                [r.get("title") for r in recs[:3]] or ["Complete the Climate Assessment to unlock recommendations."],
                limit=3,
            ),
            "related_recommendations": _as_list(
                [f"{r.get('solution_id')} — {r.get('title')}" for r in recs[:3]],
                limit=5,
                item_limit=160,
            ),
            "expected_impact_detail": _truncate(top_rec.get("reason"), 500)
            or "Estimated impact is available once recommendations are generated.",
            "confidence_note": (
                f"Data completeness {analytics.get('data_quality', {}).get('completeness_percent')}% "
                f"({analytics.get('data_quality', {}).get('level')}). "
                "Calculated values are deterministic; potential savings are estimates."
            ),
            "assumptions": [
                "Potential savings, investment and payback come from the ClimaCred solution catalog and are estimates.",
                "Emission factors are configurable defaults, not certified accounting values.",
                "No AI model was called for this insight.",
            ],
        },
    }
    # The calculated insight is deterministic, so the audit must always pass.
    insight["details"]["number_audit"] = audit_numbers(insight, context)
    return insight


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
def _read_cache(user_id: str, signature: str) -> Optional[Dict[str, Any]]:
    try:
        col = get_collection(AI_INSIGHT_COLLECTION)
        doc = col.find_one({"user_id": user_id, "data_signature": signature}, sort=[("updated_at", -1)])
        if not doc:
            return None
        updated = doc.get("updated_at")
        if hasattr(updated, "tzinfo") and updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        if isinstance(updated, datetime):
            age_minutes = (datetime.now(timezone.utc) - updated).total_seconds() / 60.0
            if age_minutes > float(settings.AI_INSIGHT_CACHE_MINUTES):
                return None
        return doc.get("payload")
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(f"AI insight cache read failed: {exc}")
        return None


def _write_cache(user_id: str, signature: str, payload: Dict[str, Any]) -> None:
    try:
        col = get_collection(AI_INSIGHT_COLLECTION)
        col.delete_many({"user_id": user_id})
        col.insert_one({
            "user_id": user_id,
            "data_signature": signature,
            "payload": payload,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        })
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(f"AI insight cache write failed: {exc}")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def _dashboard_calculated_values(context: Dict[str, Any]) -> Dict[str, Any]:
    if not context.get("data_state", {}).get("has_data"):
        # Nothing stored yet: expose explicit nulls (no fabricated zeros or names).
        return {
            "business_name": None,
            "climate_score": None,
            "score_label": None,
            "top_improvement_dimensions": None,
            "energy_kwh_month": None,
            "energy_cost_inr_month": None,
            "water_litres_month": None,
            "waste_kg_month": None,
            "emissions_tonnes_month": None,
            "mobility_fuel_litres_month": None,
            "data_quality_level": None,
            "data_quality_completeness_percent": None,
            "top_recommendation": {"solution_id": None, "title": None, "priority": None},
            "data_sources": "No business climate data stored yet.",
        }
    analytics = context.get("calculated_analytics", {})
    fp = context.get("climate_fingerprint", {})
    recs = context.get("recommendations") or []
    top_rec = recs[0] if recs else {}
    return {
        "business_name": context.get("business_profile", {}).get("name"),
        "climate_score": fp.get("overall_score"),
        "score_label": fp.get("score_label"),
        "top_improvement_dimensions": fp.get("top_improvement_dimensions"),
        "energy_kwh_month": analytics.get("energy", {}).get("monthly_kwh"),
        "energy_cost_inr_month": analytics.get("energy", {}).get("monthly_cost_inr"),
        "water_litres_month": analytics.get("water", {}).get("monthly_litres"),
        "waste_kg_month": analytics.get("waste", {}).get("monthly_kg"),
        "emissions_tonnes_month": analytics.get("emissions", {}).get("monthly_total_tonnes_co2e"),
        "mobility_fuel_litres_month": analytics.get("mobility", {}).get("monthly_fuel_litres"),
        "data_quality_level": analytics.get("data_quality", {}).get("level"),
        "data_quality_completeness_percent": analytics.get("data_quality", {}).get("completeness_percent"),
        "top_recommendation": {
            "solution_id": top_rec.get("solution_id"),
            "title": top_rec.get("title"),
            "priority": top_rec.get("priority"),
        },
        "data_sources": "Calculated from your stored profile, assessment, fingerprint and plan.",
    }


async def get_dashboard_insights(user_id: str = DEFAULT_USER_ID, force: bool = False) -> Dict[str, Any]:
    """
    Build (or return the cached) dashboard AI insight from the user's latest stored data.

    Always returns a usable payload:
      * has_data=false  -> clean empty state (no AI call, no fabricated content)
      * Gemini ok       -> Gemini interpretation of the calculated context
      * Gemini missing/failing -> deterministic calculated insight + clean notice
        (the raw provider error is logged only, never returned to the browser).
    """
    context = build_context(user_id)
    has_data = bool(context.get("data_state", {}).get("has_data"))
    signature = data_signature(context)

    base = {
        "data_signature": signature,
        "cached": False,
        "model": gemini_model_name(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "has_data": has_data,
        "calculated": _dashboard_calculated_values(context),
        "history": {
            "available": bool(context.get("history", {}).get("has_history")),
            "fingerprint_snapshots": context.get("history", {}).get("fingerprint_snapshots"),
            "impact_records": context.get("history", {}).get("impact_records_count"),
            "scenario_runs": context.get("history", {}).get("scenario_runs_count"),
            "note": context.get("history", {}).get("note"),
        },
        "disclaimer": DISCLAIMER,
    }

    # ---- Empty database: no fake business, no AI call ---------------------
    if not has_data:
        return {
            **base,
            "status": STATUS_NO_DATA,
            "source": "calculated",
            "ai_available": False,
            "notice": NOTICE_NO_DATA,
            "message": "Complete your Climate Assessment to generate your Climate Intelligence.",
            "insight": None,
        }

    if not force:
        cached = _read_cache(user_id, signature)
        if cached:
            payload = dict(cached)
            payload["cached"] = True
            return payload

    if not gemini_configured():
        fallback = _calculated_insight(context, "GEMINI_API_KEY is not configured on the server")
        logger.info("Gemini not configured - serving calculated dashboard insight")
        return {
            **base,
            "status": STATUS_UNAVAILABLE,
            "source": "calculated",
            "ai_available": False,
            "notice": NOTICE_UNAVAILABLE,
            "insight": fallback,
        }

    raw, error = await call_gemini(context)
    if raw is None:
        fallback = _calculated_insight(context, error or "Gemini request failed")
        # Real error stays in the server log; the UI only receives clean copy.
        logger.warning("Gemini unavailable (%s) - serving calculated dashboard insight", error)
        return {
            **base,
            "status": STATUS_ERROR if error and "not configured" not in error else STATUS_UNAVAILABLE,
            "source": "calculated",
            "ai_available": False,
            "notice": NOTICE_UNAVAILABLE,
            "insight": fallback,
        }

    insight = normalize_insight(raw, context)
    audit = insight["details"]["number_audit"]
    if not audit["verified"]:
        logger.warning(f"Gemini output contained unverified numbers: {audit['unsupported_values']}")

    payload = {
        **base,
        "status": STATUS_OK,
        "source": "gemini",
        "ai_available": True,
        "notice": None,
        "insight": insight,
    }
    _write_cache(user_id, signature, payload)
    return {**payload, "cached": False}
