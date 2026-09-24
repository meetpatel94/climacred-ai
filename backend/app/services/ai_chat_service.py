"""
ClimaCred AI - Gemini chat assistant service.

The floating "ClimaCred AI Assistant" in the UI talks to this service through
POST /api/ai/chat. Design rules (same guarantees as the dashboard insight layer):

  1. The backend collects the user's stored ClimaCred data automatically - the
     user never pastes data, uploads a report or repeats their business details.
  2. Numerical questions (payback, investment, savings, emissions, score,
     scenarios, budgets) are answered from EXISTING Phase 2 calculation
     services; Gemini only explains the numbers.
  3. Gemini never sees a raw database dump - only the compact structured context.
  4. Every number Gemini returns is re-audited against the calculated context.
     Unverified output is retried once and then replaced by a deterministic,
     calculation-only answer. Gemini is never allowed to invent data.
  5. With an empty database the assistant says it has no business data and can
     still answer general "how does ClimaCred work" questions - without inventing
     a business profile.
  6. GEMINI_API_KEY stays in the backend environment; the browser never sees it.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.services.ai_insight_service import (
    DISCLAIMER,
    STATUS_ERROR,
    STATUS_OK,
    STATUS_UNAVAILABLE,
    audit_numbers,
    build_context,
    call_gemini,
    gemini_configured,
    gemini_model_name,
    INSUFFICIENT_HISTORY,
)

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = "default"

NO_DATA_REPLY = (
    "I don't have your business climate data yet.\n\n"
    "Complete your Climate Assessment and I'll analyze it for you."
)

NO_DATA_NOTE = (
    "You can still ask me how ClimaCred AI works, what data we need, or how the "
    "Climate Fingerprint, recommendations and scenario simulator behave."
)

UNAVAILABLE_REPLY = (
    "I can't reach the AI model right now, so I won't guess.\n\n"
    "Your calculated ClimaCred data on the dashboard is unaffected and still available."
)

UNVERIFIED_REPLY = (
    "I couldn't verify an answer against your stored ClimaCred data, so I'd rather not guess.\n\n"
    "Please try rephrasing the question, or check the calculated values on your dashboard."
)

CHAT_SYSTEM_PROMPT = """You are the ClimaCred AI Assistant for Indian SMEs, embedded in the ClimaCred platform.

You receive a CONTEXT JSON object that contains ONLY the user's stored ClimaCred data and values that were
already calculated by the ClimaCred calculation engine, plus an optional "calculated_answers" block that the
backend computed for this specific question.

HARD RULES (never break these):
1. NEVER invent, estimate, guess or extrapolate a number. Every number you write must already appear in
   CONTEXT or in CONTEXT.calculated_answers. No exceptions: no invented energy, water, waste, emissions,
   savings, investment, payback, percentages, scores or historical measurements.
2. If CONTEXT.data_state.has_data is false: do NOT describe or assume any business, facility, industry or
   metric. State clearly that you do not have their business climate data yet, ask them to complete the
   Climate Assessment, and (if the question is a general product question) explain how ClimaCred works.
3. If the answer is not available in CONTEXT, reply exactly in spirit: "I don't have enough data to answer
   that reliably." If history is insufficient for a trend/forecast, say: "There isn't enough historical data
   for a reliable trend or forecast." Never fill the gap with invented values.
4. Numerical results (payback, investment, savings, emissions, climate score, scenario outcomes) come from the
   backend calculation services - explain them, never recompute or alter them.
5. Answer style: short, clear, business-friendly and action-oriented. Use this shape when it fits:
   a one-line answer, then "Why:", then "What to do next:" (max 3 short numbered steps), and one relevant
   number from CONTEXT. No long paragraphs. Do not repeat the question.
6. Be explicit about uncertainty: potential savings/payback are catalog estimates, not guarantees.
7. Never claim government certification, verified carbon credits or guaranteed savings.
8. Reply in plain text (no markdown headers, no code fences, no JSON), max ~180 words unless the user
   explicitly asks for more detail."""


# ---------------------------------------------------------------------------
# Lightweight intent helpers (kept intentionally simple and explainable)
# ---------------------------------------------------------------------------
_BUDGET_RE = re.compile(
    r"(?:₹|rs\.?|inr)?\s*([0-9][0-9,\.]*)\s*(lakh|lac|lakhs|crore|cr|k|thousand)?",
    re.IGNORECASE,
)

TREND_KEYWORDS = ("trend", "changed", "change", "compare", "increase", "decrease", "last month", "history", "over time")
FORECAST_KEYWORDS = ("forecast", "predict", "future", "next month", "next year", "projected")
SCENARIO_KEYWORDS = ("what if", "what happens if", "scenario", "simulate", "if i install", "if we install", "switch to", "increase renewable", "add solar")


def _extract_budget_inr(message: str) -> Optional[float]:
    """Extract a budget mentioned in the question, e.g. 'with a ₹10 lakh budget' → 1,000,000 INR."""
    text = message.lower()
    if "budget" not in text and "invest" not in text and "afford" not in text and "spend" not in text:
        return None
    best: Optional[float] = None
    for raw, unit in _BUDGET_RE.findall(text):
        cleaned = raw.replace(",", "").rstrip(".")
        try:
            value = float(cleaned)
        except ValueError:
            continue
        unit = (unit or "").lower()
        if unit in ("lakh", "lac", "lakhs"):
            value *= 100_000
        elif unit in ("crore", "cr"):
            value *= 10_000_000
        elif unit in ("k", "thousand"):
            value *= 1_000
        elif value < 1000:  # bare small number next to "busget"/"invest" is not a budget
            continue
        if value >= 10_000 and (best is None or value > best):
            best = value
    return best


def _recommendations_within_budget(recommendations: List[Dict[str, Any]], budget_inr: float) -> Dict[str, Any]:
    """Greedy, deterministic budget selection from existing recommendation outputs.

    Shortest payback first (highest annual saving per rupee), never exceeding the budget.
    """
    candidates = []
    for rec in recommendations:
        investment = ((rec.get("solution") or {}).get("investmentMinInr")) or 0
        payback = (rec.get("solution") or {}).get("estimatedPaybackPeriodYears")
        savings = (rec.get("solution") or {}).get("potentialAnnualSavingsInr") or 0
        if investment and investment <= budget_inr:
            candidates.append((payback if payback is not None else 99, -savings, rec))
    candidates.sort(key=lambda item: (item[0], item[1]))

    selected: List[Dict[str, Any]] = []
    spent = 0.0
    saved = 0.0
    for payback, _neg_savings, rec in candidates:
        investment = (rec.get("solution") or {}).get("investmentMinInr") or 0
        if spent + investment > budget_inr:
            continue
        spent += investment
        saved += (rec.get("solution") or {}).get("potentialAnnualSavingsInr") or 0
        selected.append({
            "solution_id": rec.get("solution_id"),
            "title": (rec.get("solution") or {}).get("title"),
            "investment_min_inr": investment,
            "estimated_payback_years": (rec.get("solution") or {}).get("estimatedPaybackPeriodYears"),
            "potential_annual_savings_inr": (rec.get("solution") or {}).get("potentialAnnualSavingsInr"),
        })
    return {
        "budget_inr": budget_inr,
        "selected": selected,
        "total_investment_inr": round(spent, 2),
        "total_potential_annual_savings_inr": round(saved, 2),
        "assumption": "Deterministic budget packing by shortest payback using catalog investment minimums; estimates, not guarantees.",
    }


def _scenario_projection(context: Dict[str, Any], message: str) -> Optional[Dict[str, Any]]:
    """Run the existing scenario engine for 'what if' questions (pure engine call)."""
    from app.climate_engine.simulations import simulate_with_fingerprint
    from app.services.profile_service import get_profile
    from app.services.assessment_service import get_assessment
    from app.services.fingerprint_service import get_latest_fingerprint

    profile = get_profile(DEFAULT_USER_ID) or {}
    assessment = get_assessment(DEFAULT_USER_ID) or {}
    fingerprint = get_latest_fingerprint(DEFAULT_USER_ID) or {}
    if not fingerprint:
        return None

    recs = context.get("recommendations") or []
    if not recs:
        return None
    text = message.lower()
    matched_ids = [
        rec["solution_id"] for rec in recs
        if rec.get("title") and any(word in text for word in str(rec["title"]).lower().split() if len(word) > 4)
    ]
    selected_ids = matched_ids[:3] or [rec["solution_id"] for rec in recs[:2] if rec.get("solution_id")]
    if not selected_ids:
        return None
    try:
        result = simulate_with_fingerprint(selected_ids, profile, assessment, fingerprint, scale=100)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Scenario projection for chat failed: %s", exc)
        return None
    return {
        "origin": "backend_scenario_engine",
        "selected_solution_ids": selected_ids,
        "adoption_scale_percent": 100,
        "investment_min_inr": (result.get("investment") or {}).get("min_inr"),
        "annual_savings_inr": result.get("annual_savings_inr"),
        "payback_years": result.get("payback_period_years"),
        "projected_climate_score": result.get("projected_climate_score"),
        "assumptions": (result.get("assumptions") or [])[:4],
    }


def build_chat_context(user_id: str = DEFAULT_USER_ID, message: str = "") -> Dict[str, Any]:
    """Compact structured context for one chat turn (no database dumps)."""
    context = build_context(user_id)
    has_data = bool(context.get("data_state", {}).get("has_data"))
    recommendations = context.get("recommendations") or []

    answers: Dict[str, Any] = {
        "note": (
            "All figures below were calculated by the ClimaCred backend from the user's stored data. "
            "Explain them; do not recompute."
        ),
        "recommendations_with_payback": [
            {
                "solution_id": rec.get("solution_id"),
                "title": rec.get("title"),
                "priority": rec.get("priority"),
                "investment_min_inr": rec.get("investment_range_inr", [None, None])[0],
                "investment_max_inr": rec.get("investment_range_inr", [None, None])[1],
                "estimated_payback_years": rec.get("payback_years"),
                "potential_annual_savings_inr": rec.get("annual_savings_inr"),
                "resource_reduction": rec.get("resource_reduction"),
            }
            for rec in recommendations[:6]
        ],
        "shortest_payback": None,
        "budget_selection": None,
        "scenario_projection": None,
    }

    with_payback = [r for r in answers["recommendations_with_payback"] if r.get("estimated_payback_years") is not None]
    if with_payback:
        answers["shortest_payback"] = min(with_payback, key=lambda r: r["estimated_payback_years"])

    text = (message or "").lower()
    if has_data and recommendations:
        if any(word in text for word in ("budget", "invest", "afford", "spend", "lakh", "crore")):
            budget = _extract_budget_inr(message)
            if budget:
                answers["budget_selection"] = _recommendations_within_budget(recommendations, budget)
        if any(word in text for word in SCENARIO_KEYWORDS):
            answers["scenario_projection"] = _scenario_projection(context, message)

    context["calculated_answers"] = answers
    context["user_question"] = message
    context["conversation_rules"] = {
        "answer_length": "short (<180 words) unless more detail is requested",
        "follow_up_context": "Use the earlier conversation turns to resolve references such as 'it' or 'that'.",
        "forecast_policy": (
            "Compare periods only when history.resource_series has 2+ snapshots; otherwise say: "
            + INSUFFICIENT_HISTORY
        ),
    }
    return context


def _chat_suggestions(has_data: bool) -> List[str]:
    """Suggested starter questions, answered from the user's real data."""
    if not has_data:
        # The four product questions always work; without data they return the
        # no-data explanation, and the extra items explain the platform itself.
        return [
            "What's my biggest climate risk?",
            "What data do you need from me?",
            "Explain my climate score.",
            "What happens after I complete the assessment?",
        ]
    return [
        "What's my biggest climate risk?",
        "What changed recently?",
        "What should I do next?",
        "Explain my climate score.",
    ]


def _normalise_history(history: Optional[List[Dict[str, Any]]]) -> List[Dict[str, str]]:
    """Keep the last N turns of the current session, in Gemini's content shape."""
    if not history:
        return []
    clean: List[Dict[str, str]] = []
    for turn in history:
        if not isinstance(turn, dict):
            continue
        role = "assistant" if str(turn.get("role")) in ("assistant", "model", "ai") else "user"
        content = str(turn.get("content") or "").strip()
        if not content:
            continue
        clean.append({"role": role, "content": content[: settings.AI_CHAT_MAX_MESSAGE_CHARS]})
    return clean[-settings.AI_CHAT_MAX_HISTORY_TURNS:]


def _gemini_chat_payload(context: Dict[str, Any], history: List[Dict[str, str]], message: str) -> Dict[str, Any]:
    contents: List[Dict[str, Any]] = []
    for turn in history:
        contents.append({
            "role": "model" if turn["role"] == "assistant" else "user",
            "parts": [{"text": turn["content"]}],
        })
    contents.append({
        "role": "user",
        "parts": [{"text": (
            "CONTEXT (stored ClimaCred data + backend-calculated values - do not invent any other number):\n"
            f"{json.dumps(context, ensure_ascii=False, default=str)}\n\n"
            f"USER QUESTION: {message}"
        )}],
    })
    return {
        "systemInstruction": {"parts": [{"text": CHAT_SYSTEM_PROMPT}]},
        "contents": contents,
        "generationConfig": {
            "temperature": 0.3,
            "topP": 0.9,
            "maxOutputTokens": 1024,
            "responseMimeType": "text/plain",
        },
    }


def _as_reply(raw: Any) -> str:
    """Extract plain text from a Gemini chat response."""
    if isinstance(raw, str):
        return raw.strip()
    if isinstance(raw, dict):
        for key in ("reply", "answer", "text", "summary", "message"):
            value = raw.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        try:
            return json.dumps(raw)[:1200]
        except (TypeError, ValueError):  # pragma: no cover - defensive
            return ""
    return ""


def _inr(value: Any) -> str:
    try:
        return f"\u20b9{int(float(value)):,}"
    except (TypeError, ValueError):
        return "\u20b9-"


def _calculated_reply(context: Dict[str, Any], message: str) -> str:
    """Deterministic answer used when Gemini is unavailable - engine values only."""
    analytics = context.get("calculated_analytics", {})
    fingerprint = context.get("climate_fingerprint", {})
    dimensions = fingerprint.get("dimensions") or []
    recommendations = context.get("recommendations") or []
    top_rec = recommendations[0] if recommendations else None
    answers = context.get("calculated_answers") or {}
    budget = answers.get("budget_selection")
    scenario = answers.get("scenario_projection")
    history = context.get("history") or {}
    changes = history.get("resource_changes") or {}
    text = (message or "").lower()
    water = analytics.get("water", {})
    energy = analytics.get("energy", {})
    waste = analytics.get("waste", {})
    emissions = analytics.get("emissions", {})

    weakest = None
    for dim in dimensions:
        if dim.get("score") is None:
            continue
        if weakest is None or dim["score"] < weakest["score"]:
            weakest = dim

    def number_line() -> Optional[str]:
        if energy.get("monthly_kwh"):
            return f"Latest recorded electricity use: {energy['monthly_kwh']:,.0f} kWh/month."
        if water.get("monthly_litres"):
            return f"Latest recorded water use: {water['monthly_litres']:,.0f} litres/month."
        if waste.get("monthly_kg"):
            return f"Latest recorded waste: {waste['monthly_kg']:,.0f} kg/month."
        return None

    lines: List[str] = []

    score_intent = any(word in text for word in ("score", "rating", "readiness", "how am i doing"))
    risk_intent = any(word in text for word in ("risk", "risky", "vulnerab", "biggest problem", "weakest"))
    change_intent = any(word in text for word in ("changed", "change", "recent", "since", "last time", "trend", "improving"))

    if budget and budget.get("selected"):
        picks = ", ".join(item["title"] for item in budget["selected"] if item.get("title"))
        lines.append(f"Answer: With {_inr(budget['budget_inr'])} the shortest-payback combination is: {picks}.")
        lines.append(
            f"Relevant number: {_inr(budget['total_investment_inr'])} estimated investment for about "
            f"{_inr(budget['total_potential_annual_savings_inr'])} potential annual savings."
        )
    elif scenario and scenario.get("payback_years") is not None:
        lines.append(
            f"Answer: Running {', '.join(scenario['selected_solution_ids'])} in the ClimaCred simulator gives an "
            f"estimated {_inr(scenario['investment_min_inr'])} investment and {_inr(scenario['annual_savings_inr'])} "
            f"annual savings."
        )
        lines.append(f"Relevant number: estimated payback of {scenario['payback_years']} years.")
    elif score_intent and fingerprint.get("overall_score") is not None:
        lines.append(
            f"Answer: Your Climate Readiness score is {fingerprint.get('overall_score')}/100 "
            f"({fingerprint.get('score_label') or 'calculated from your stored data'})."
        )
        if dimensions:
            best = max(dimensions, key=lambda d: d.get("score") or 0)
            lines.append(
                f"Why: the score is weighted across {len(dimensions)} dimensions; strongest is {best.get('dimension')} "
                f"({best.get('score')}/100) and weakest is {weakest.get('dimension')} ({weakest.get('score')}/100)."
                if weakest else ""
            )
        if top_rec:
            lines.append(f"What to do next: {top_rec.get('title')}.")
    elif change_intent:
        series = history.get("resource_series") or []
        change_items = [
            (label, value)
            for label, value in changes.items()
            if isinstance(value, dict) and value.get("latest_value") is not None
        ]
        if changes.get("available") and series and change_items:
            lines.append(
                f"Answer: Comparing your {changes.get('records_compared', len(series))} stored snapshots:"
            )
            for label, item in change_items[:3]:
                lines.append(
                    f"• {label}: {item.get('first_value'):,} → {item.get('latest_value'):,} "
                    f"({item.get('change_percent')}%)."
                )
        else:
            lines.append(
                "Answer: I do not have enough stored history for a reliable change comparison yet. "
                "Only one usable snapshot is on file."
            )
            lines.append("What to do next: update your Climate Assessment to create the next comparable snapshot.")
    elif risk_intent and weakest:
        lines.append(
            f"Answer: Your biggest climate risk is {weakest.get('dimension')} "
            f"({weakest.get('score')}/100, {weakest.get('impact_level')} impact)."
        )
        if weakest.get("primary_cause"):
            lines.append(f"Why: {weakest.get('primary_cause')}.")
        if top_rec:
            lines.append(f"What to do next: {top_rec.get('title')}.")
        number = number_line()
        if number:
            lines.append(f"Relevant number: {number}")
    else:
        if weakest:
            lines.append(
                f"Answer: Your weakest dimension is {weakest.get('dimension')} "
                f"({weakest.get('score')}/100, {weakest.get('impact_level')} impact)."
            )
        if top_rec:
            lines.append(f"What to do next: {top_rec.get('title')}.")
        number = number_line()
        if number:
            lines.append(f"Relevant number: {number}")

    if top_rec and not (risk_intent or score_intent or budget or scenario):
        lines.append(
            f"Expected impact: {top_rec.get('resource_reduction') or 'resource reduction per the solution catalog'}"
            + (f" \u2022 {_inr(top_rec.get('annual_savings_inr'))} potential annual savings" if top_rec.get("annual_savings_inr") else "")
            + "."
        )
    if emissions.get("monthly_total_tonnes_co2e"):
        lines.append(
            f"Your calculated footprint is {emissions['monthly_total_tonnes_co2e']} MT CO\u2082e/month "
            f"({emissions.get('annual_total_tonnes_co2e')} MT CO\u2082e/year)."
        )

    lines = [line for line in lines if line]
    lines.append("This answer was generated by the ClimaCred calculation engine (Gemini was unavailable).")
    return "\n".join(lines)


def _no_data_reply_from_gemini() -> str:
    return f"{NO_DATA_REPLY}\n\n{NO_DATA_NOTE}"


async def answer_question(
    message: str,
    history: Optional[List[Dict[str, Any]]] = None,
    user_id: str = DEFAULT_USER_ID,
) -> Dict[str, Any]:
    """
    Answer one chat turn using the user's real stored data.

    Returns a payload with: status, source ('gemini' | 'calculated'), ai_available,
    has_data, reply, model, generated_at, number_audit, suggestions.
    Never raises for AI-side problems and never returns a fabricated answer.
    """
    question = (message or "").strip()[: settings.AI_CHAT_MAX_MESSAGE_CHARS]
    if not question:
        return {
            "status": "invalid",
            "source": "calculated",
            "ai_available": gemini_configured(),
            "has_data": False,
            "reply": "Please type a question about your ClimaCred data.",
            "model": gemini_model_name(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "number_audit": {"verified": True, "unsupported_values": []},
            "suggestions": _chat_suggestions(False),
            "disclaimer": DISCLAIMER,
        }

    context = build_chat_context(user_id, question)
    has_data = bool(context.get("data_state", {}).get("has_data"))
    turns = _normalise_history(history)

    base = {
        "model": gemini_model_name(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "has_data": has_data,
        "disclaimer": DISCLAIMER,
        "suggestions": _chat_suggestions(has_data),
    }

    if not gemini_configured():
        reply = _calculated_reply(context, question) if has_data else _no_data_reply_from_gemini()
        logger.info("Chat answered without Gemini (key not configured, has_data=%s)", has_data)
        return {
            **base,
            "status": STATUS_UNAVAILABLE,
            "source": "calculated",
            "ai_available": False,
            "notice": "AI assistant is temporarily unavailable." if has_data else None,
            "reply": reply,
            "number_audit": audit_numbers({"reply": reply}, context),
        }

    raw, error = await call_gemini(
        context,
        payload_builder=lambda ctx: _gemini_chat_payload(ctx, turns, question),
        expect_json=False,
    )
    reply = _as_reply(raw)

    if not reply:
        logger.warning("Gemini chat unavailable (%s) - serving calculated answer", error)
        fallback = _calculated_reply(context, question) if has_data else _no_data_reply_from_gemini()
        return {
            **base,
            "status": STATUS_ERROR if error else STATUS_UNAVAILABLE,
            "source": "calculated",
            "ai_available": False,
            "notice": "AI assistant is temporarily unavailable." if has_data else None,
            "reply": fallback,
            "number_audit": audit_numbers({"reply": fallback}, context),
        }

    audit = audit_numbers({"reply": reply}, context)
    if not audit["verified"]:
        # One corrective retry, then fall back to calculation-only text. Gemini is
        # never allowed to ship unverifiable figures to the user.
        logger.warning("Gemini chat reply contained unverified numbers: %s", audit["unsupported_values"])
        corrective_context = dict(context)
        corrective_context["correction_instruction"] = (
            "Your previous answer contained numbers that are NOT present in CONTEXT "
            f"({audit['unsupported_values']}). Rewrite the answer using ONLY numbers that appear in CONTEXT "
            "or CONTEXT.calculated_answers, or state that you don't have enough data."
        )
        retry_raw, retry_error = await call_gemini(
            corrective_context,
            payload_builder=lambda ctx: _gemini_chat_payload(ctx, turns, question),
            expect_json=False,
        )
        retry_reply = _as_reply(retry_raw)
        if retry_reply:
            retry_audit = audit_numbers({"reply": retry_reply}, corrective_context)
            if retry_audit["verified"]:
                return {
                    **base,
                    "status": STATUS_OK,
                    "source": "gemini",
                    "ai_available": True,
                    "notice": None,
                    "reply": retry_reply,
                    "number_audit": retry_audit,
                }
            logger.warning("Gemini chat retry still unverified: %s", retry_audit["unsupported_values"])
        else:
            logger.warning("Gemini chat retry unavailable (%s)", retry_error)
        safe_reply = _calculated_reply(context, question) if has_data else _no_data_reply_from_gemini()
        return {
            **base,
            "status": STATUS_OK,
            "source": "calculated",
            "ai_available": True,
            "notice": "Some AI wording could not be verified against your data, so a calculated answer is shown.",
            "reply": safe_reply,
            "number_audit": audit_numbers({"reply": safe_reply}, context),
        }

    return {
        **base,
        "status": STATUS_OK,
        "source": "gemini",
        "ai_available": True,
        "notice": None,
        "reply": reply,
        "number_audit": audit,
    }
