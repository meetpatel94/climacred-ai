"""
ClimaCred AI - Excel / CSV data import.

What this module does
---------------------
Parses ``.xlsx`` / ``.xls`` / ``.csv`` files, detects which ClimaCred dataset each
one contains (from the filename AND the column headers - never from the filename
alone), validates every row, stores the valid rows in the EXISTING MongoDB
architecture and returns a per-file import summary.

Hard rules
----------
* Files are never forwarded to Gemini. Parsing, validation and storage all happen
  in the backend; the AI layer only ever reads what this module stored.
* Nothing is invented. A row that fails validation is rejected and reported with
  a human-readable, row-numbered message - bad rows are never silently dropped.
* Existing collections/services are reused wherever an equivalent already exists
  (``business_profiles``, ``climate_assessments``, ``green_solutions``,
  ``scenarios``, ``transformation_plans``, ``impact_records``). New collections are
  created only for time series the application never had a home for
  (``energy_data``, ``water_data``, ...).
* Rows are linked by ``business_id`` (``B001`` ...), so one business connects its
  profile, energy, water, waste, emissions, mobility, operations, historical
  series, assessment, scenarios, plan and impact records.
* Deterministic backend calculations stay the source of truth. The Climate
  Assessment the scoring engine uses is DERIVED from the imported monthly data;
  scores shipped inside ``climate_assessments`` are stored as a reference only.

Re-importing the same file is idempotent: rows are upserted on their natural key,
and the summary reports how many rows were inserted vs updated.
"""
from __future__ import annotations

import io
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd

from app.database.collections import COLLECTIONS
from app.database.mongodb import get_collection

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = "default"

SUPPORTED_EXTENSIONS = (".xlsx", ".xls", ".csv")
MAX_FILE_BYTES = 25 * 1024 * 1024  # 25 MB per upload

#: Value written on every document this module stores, so imported data can always
#: be told apart from data the user typed into the UI.
DATA_ORIGIN = "import"

_BUSINESS_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{1,31}$")
_MONTH_RE = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")

# ---------------------------------------------------------------------------
# Column types
# ---------------------------------------------------------------------------
_STR = "str"          # non-empty string (when required)
_TEXT = "text"        # any string, empty allowed
_INT = "int"
_FLOAT = "float"
_NN_INT = "nn_int"    # integer >= 0
_NN_FLOAT = "nn_float"  # number >= 0
_PCT = "pct"          # 0..100
_SIGNED_PCT = "signed_pct"  # -100..100 (e.g. a waste *reduction* percentage)
_EFF = "efficiency"   # 0..200: an efficiency ratio can exceed 100% when recycled input is counted
_MONTH = "month"      # YYYY-MM
_DATE = "date"        # ISO date
_BOOL = "bool"
_JSON = "json"


class RowError(ValueError):
    """A single row failed validation. Carries the row number and the column."""

    def __init__(self, row_number: int, column: str, message: str) -> None:
        super().__init__(message)
        self.row_number = row_number
        self.column = column
        self.message = message

    def as_dict(self) -> Dict[str, Any]:
        return {"row": self.row_number, "column": self.column, "message": self.message}


class DatasetError(ValueError):
    """The file itself is unusable (bad extension, no headers, unknown dataset...)."""

    def __init__(self, message: str, *, error_code: str = "dataset_error", **extra: Any) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.extra = extra


# ---------------------------------------------------------------------------
# Dataset registry
# ---------------------------------------------------------------------------
class Dataset:
    """Declarative description of one importable ClimaCred dataset."""

    def __init__(
        self,
        key: str,
        label: str,
        collection: str,
        fields: Dict[str, Tuple[str, bool]],
        *,
        signature: Sequence[str] = (),
        filename_hints: Sequence[str] = (),
        unique_key: Sequence[str] = (),
        business_scoped: bool = True,
        description: str = "",
        transform: Optional[Any] = None,
        payload_column: Optional[str] = None,
        payload_key: Optional[str] = None,
    ) -> None:
        self.key = key
        self.label = label
        self.collection = collection
        self.fields = fields
        self.signature = tuple(signature)
        self.filename_hints = tuple(filename_hints) or (key,)
        self.unique_key = tuple(unique_key)
        self.business_scoped = business_scoped
        self.description = description
        self.transform = transform
        # Some workbooks ship a companion sheet holding an API-ready JSON payload per
        # business (the ClimaCred test pack does this for climate assessments). It is
        # stored alongside the row and used as the assessment INPUT; the scores are
        # still always calculated by the ClimaCred engine.
        self.payload_column = payload_column
        self.payload_key = payload_key

    @property
    def required_columns(self) -> Tuple[str, ...]:
        return tuple(name for name, (_type, required) in self.fields.items() if required)

    @property
    def columns(self) -> Tuple[str, ...]:
        return tuple(self.fields.keys())

    def describe(self) -> Dict[str, Any]:
        return {
            "dataset_type": self.key,
            "label": self.label,
            "collection": self.collection,
            "description": self.description,
            "required_columns": list(self.required_columns),
            "optional_columns": [c for c in self.columns if c not in self.required_columns],
            "unique_key": list(self.unique_key),
            "business_scoped": self.business_scoped,
        }


# --- transforms (row -> stored document) -----------------------------------
def _profile_document(row: Dict[str, Any]) -> Dict[str, Any]:
    """Map an imported business profile row onto the app's profile document shape.

    Both the canonical snake_case keys used by the backend and the camelCase keys
    the frontend reads are produced, exactly like ``profile_service`` does.
    """
    location = ", ".join(str(p) for p in (row.get("city"), row.get("state")) if p)
    doc = {
        "business_id": row.get("business_id"),
        "business_name": row.get("business_name"),
        "name": row.get("business_name"),
        "industry": row.get("industry"),
        "sub_industry": row.get("sub_industry"),
        "business_type": row.get("sub_industry"),
        "businessType": row.get("sub_industry"),
        "location": location or None,
        "employees": row.get("employee_count"),
        "working_days": row.get("operating_days_per_month"),
        "workingDaysPerMonth": row.get("operating_days_per_month"),
        "operating_hours": row.get("operating_hours_per_day"),
        "operatingHoursPerDay": row.get("operating_hours_per_day"),
        "business_size": row.get("business_size"),
        "businessSize": row.get("business_size"),
        "facility_area_sqft": row.get("facility_area_sqft"),
        "facilityAreaSqFt": row.get("facility_area_sqft"),
        "contact_email": row.get("contact_email"),
        "contactEmail": row.get("contact_email"),
        "annual_turnover": row.get("annual_turnover"),
        "ownership_type": row.get("ownership_type"),
        "facility_type": row.get("facility_type"),
        "year_established": row.get("year_established"),
        "primary_products": row.get("primary_products"),
    }
    return {k: v for k, v in doc.items() if v is not None}


def _catalog_document(row: Dict[str, Any]) -> Dict[str, Any]:
    """Map an imported green-solution row onto the app's solution catalog shape."""
    def _num(*keys: str) -> Optional[float]:
        for key in keys:
            if row.get(key) is not None:
                return float(row[key])
        return None

    capex_min = _num("estimated_capex_min", "estimated_capex")
    capex_max = _num("estimated_capex_max", "estimated_capex")
    savings = _num("estimated_annual_savings") or 0.0
    payback_months = _num("estimated_payback_months")
    doc = {
        "id": row.get("solution_id"),
        "title": row.get("solution_name"),
        "category": row.get("category"),
        "description": row.get("description"),
        "problemAddressed": row.get("category"),
        "shortDesc": row.get("description"),
        "applicableIndustries": row.get("applicable_industries"),
        "investmentMinInr": capex_min or 0.0,
        "investmentMaxInr": capex_max or capex_min or 0.0,
        "investmentRange": (
            f"Rs {capex_min:,.0f} - {capex_max:,.0f}" if capex_min is not None else None
        ),
        "potentialAnnualSavingsInr": savings,
        "co2ReductionTonnesPerYear": _num("estimated_annual_emission_reduction_tco2e") or 0.0,
        "potentialEnvironmentalImpact": (
            f"{_num('estimated_water_saving_litres') or 0:,.0f} L water / "
            f"{_num('estimated_waste_reduction_kg') or 0:,.0f} kg waste / "
            f"{_num('estimated_annual_energy_saving_kwh') or 0:,.0f} kWh per year"
        ),
        "estimatedPaybackPeriodYears": round(payback_months / 12.0, 2) if payback_months else None,
        "implementationDifficulty": row.get("complexity"),
        "estimated_payback_months": payback_months,
        "implementation_months": _num("implementation_months"),
        "expected_life_years": _num("expected_life_years"),
        "featured": False,
    }
    return {k: v for k, v in doc.items() if v is not None}


DATASETS: Dict[str, Dataset] = {}


def _register(dataset: Dataset) -> None:
    DATASETS[dataset.key] = dataset


# --- business profiles ------------------------------------------------------
_register(Dataset(
    "business_profiles",
    "Business Profiles",
    COLLECTIONS["business_profiles"],
    {
        "business_id": (_STR, True),
        "business_name": (_STR, True),
        "industry": (_STR, True),
        "sub_industry": (_TEXT, False),
        "city": (_TEXT, False),
        "state": (_TEXT, False),
        "employee_count": (_NN_INT, True),
        "facility_area_sqft": (_NN_FLOAT, True),
        "operating_days_per_month": (_NN_INT, True),
        "operating_hours_per_day": (_NN_INT, True),
        "annual_turnover": (_NN_FLOAT, False),
        "ownership_type": (_TEXT, False),
        "facility_type": (_TEXT, False),
        "year_established": (_INT, False),
        "primary_products": (_TEXT, False),
        "contact_email": (_TEXT, False),
        "created_at": (_TEXT, False),
        "business_size": (_STR, True),
        "test_archetype": (_TEXT, False),
    },
    signature=("business_name", "employee_count", "facility_area_sqft", "business_size"),
    filename_hints=("business_profile", "business_profiles", "profile", "profiles"),
    unique_key=("business_id",),
    description="Identity, size, location and contact details of each business. Import this first.",
    transform=_profile_document,
))

# --- climate assessments ----------------------------------------------------
_register(Dataset(
    "climate_assessments",
    "Climate Assessments",
    COLLECTIONS["climate_assessments"],
    {
        "assessment_id": (_STR, True),
        "business_id": (_STR, True),
        "assessment_date": (_DATE, True),
        "energy_score": (_PCT, True),
        "water_score": (_PCT, True),
        "waste_score": (_PCT, True),
        "emissions_score": (_PCT, True),
        "mobility_score": (_PCT, True),
        "operations_score": (_PCT, True),
        "overall_climate_score": (_PCT, True),
        "risk_level": (_TEXT, False),
        "key_issue_1": (_TEXT, False),
        "key_issue_2": (_TEXT, False),
        "key_issue_3": (_TEXT, False),
        "energy_impact_level": (_TEXT, False),
        "water_impact_level": (_TEXT, False),
        "waste_impact_level": (_TEXT, False),
        "emissions_impact_level": (_TEXT, False),
        "mobility_impact_level": (_TEXT, False),
        "operations_impact_level": (_TEXT, False),
        "data_completeness_percent": (_PCT, False),
        "scoring_source": (_TEXT, False),
    },
    signature=("overall_climate_score", "energy_score", "risk_level"),
    filename_hints=("climate_assessment", "climate_assessments", "assessment", "assessments"),
    unique_key=("business_id", "assessment_date"),
    payload_column="post_api_assessment_json",
    payload_key="assessment_payload",
    description=(
        "Reference scores per business, plus (when the workbook carries the companion "
        "sheet) the API-ready assessment inputs. ClimaCred always RE-COMPUTES the scores "
        "with its own engine; the scores in this file are stored for comparison only."
    ),
))

# --- monthly resource streams ----------------------------------------------
_MONTHLY_COMMON = {
    "business_id": (_STR, True),
    "month": (_MONTH, True),
}


def _monthly(**fields: Tuple[Tuple[str, bool], ...]) -> Dict[str, Tuple[str, bool]]:
    return {**_MONTHLY_COMMON, **dict(fields)}


_register(Dataset(
    "energy_data",
    "Energy Data",
    "energy_data",
    _monthly(
        electricity_kwh=(_NN_FLOAT, True),
        grid_kwh=(_NN_FLOAT, False),
        renewable_kwh=(_NN_FLOAT, False),
        diesel_litres=(_NN_FLOAT, False),
        LPG_kg=(_NN_FLOAT, False),
        peak_demand_kw=(_NN_FLOAT, False),
        production_units=(_NN_FLOAT, False),
        energy_intensity_kwh_per_unit=(_NN_FLOAT, False),
        renewable_share_percent=(_PCT, False),
    ),
    signature=("electricity_kwh", "grid_kwh", "renewable_kwh", "peak_demand_kw"),
    unique_key=("business_id", "month"),
    description="Monthly grid vs renewable electricity split, peak demand and energy intensity.",
))

_register(Dataset(
    "water_data",
    "Water Data",
    "water_data",
    _monthly(
        freshwater_intake_litres=(_NN_FLOAT, True),
        process_water_litres=(_NN_FLOAT, False),
        cleaning_water_litres=(_NN_FLOAT, False),
        reused_water_litres=(_NN_FLOAT, False),
        wastewater_generated_litres=(_NN_FLOAT, False),
        wastewater_treated_litres=(_NN_FLOAT, False),
        water_reuse_rate_percent=(_PCT, False),
        water_intensity_litres_per_unit=(_NN_FLOAT, False),
    ),
    signature=("freshwater_intake_litres", "wastewater_generated_litres", "reused_water_litres"),
    unique_key=("business_id", "month"),
    description="Monthly water intake split, reuse, wastewater treated and water intensity.",
))

_register(Dataset(
    "waste_data",
    "Waste Data",
    "waste_data",
    _monthly(
        total_waste_kg=(_NN_FLOAT, True),
        recyclable_kg=(_NN_FLOAT, False),
        recycled_kg=(_NN_FLOAT, False),
        organic_kg=(_NN_FLOAT, False),
        organic_recovered_kg=(_NN_FLOAT, False),
        hazardous_kg=(_NN_FLOAT, False),
        landfill_kg=(_NN_FLOAT, False),
        waste_reduction_percent=(_SIGNED_PCT, False),
        recycling_rate_percent=(_PCT, False),
        disposal_cost=(_NN_FLOAT, False),
    ),
    signature=("total_waste_kg", "landfill_kg", "recycling_rate_percent"),
    unique_key=("business_id", "month"),
    description="Monthly waste streams, recycled volume, landfill tonnage and disposal cost.",
))

_register(Dataset(
    "emissions_data",
    "Emissions Data",
    "emissions_data",
    _monthly(
        scope_1_emissions_tco2e=(_NN_FLOAT, True),
        scope_2_emissions_tco2e=(_NN_FLOAT, True),
        scope_3_emissions_tco2e=(_NN_FLOAT, False),
        total_emissions_tco2e=(_NN_FLOAT, True),
        diesel_emissions_tco2e=(_NN_FLOAT, False),
        electricity_emissions_tco2e=(_NN_FLOAT, False),
        mobility_emissions_tco2e=(_NN_FLOAT, False),
        emissions_intensity=(_NN_FLOAT, False),
    ),
    signature=("scope_1_emissions_tco2e", "scope_2_emissions_tco2e", "total_emissions_tco2e"),
    unique_key=("business_id", "month"),
    description="Monthly Scope 1/2/3 emissions with source breakdown and intensity.",
))

_register(Dataset(
    "mobility_data",
    "Mobility Data",
    "mobility_data",
    _monthly(
        company_vehicle_count=(_NN_INT, True),
        diesel_litres=(_NN_FLOAT, False),
        petrol_litres=(_NN_FLOAT, False),
        CNG_kg=(_NN_FLOAT, False),
        EV_kwh=(_NN_FLOAT, False),
        employee_commute_km=(_NN_FLOAT, False),
        business_travel_km=(_NN_FLOAT, False),
        logistics_km=(_NN_FLOAT, False),
        estimated_mobility_emissions_tco2e=(_NN_FLOAT, False),
    ),
    signature=("company_vehicle_count", "employee_commute_km", "logistics_km"),
    unique_key=("business_id", "month"),
    description="Monthly fleet fuels, EV electricity and commute / travel / logistics distance.",
))

_register(Dataset(
    "operations_materials",
    "Operations & Materials",
    "operations_materials",
    _monthly(
        raw_material_consumption_kg=(_NN_FLOAT, True),
        recycled_material_kg=(_NN_FLOAT, False),
        virgin_material_kg=(_NN_FLOAT, False),
        production_output_kg=(_NN_FLOAT, False),
        rejected_material_kg=(_NN_FLOAT, False),
        packaging_material_kg=(_NN_FLOAT, False),
        recycled_input_percent=(_PCT, False),
        material_efficiency_percent=(_EFF, False),
    ),
    signature=("raw_material_consumption_kg", "virgin_material_kg", "material_efficiency_percent"),
    unique_key=("business_id", "month"),
    description="Monthly material input / output, recycled input share and material efficiency.",
))

_register(Dataset(
    "resource_consumption",
    "Resource Consumption",
    "resource_consumption",
    _monthly(
        electricity_kwh=(_NN_FLOAT, True),
        diesel_litres=(_NN_FLOAT, False),
        LPG_kg=(_NN_FLOAT, False),
        water_litres=(_NN_FLOAT, True),
        wastewater_litres=(_NN_FLOAT, False),
        total_waste_kg=(_NN_FLOAT, True),
        recyclable_waste_kg=(_NN_FLOAT, False),
        hazardous_waste_kg=(_NN_FLOAT, False),
        organic_waste_kg=(_NN_FLOAT, False),
        general_waste_kg=(_NN_FLOAT, False),
        production_units=(_NN_FLOAT, False),
        operating_days=(_NN_INT, False),
        employee_count=(_NN_INT, False),
    ),
    signature=("total_waste_kg", "water_litres", "electricity_kwh", "organic_waste_kg"),
    unique_key=("business_id", "month"),
    description="Consolidated monthly resource ledger (energy, water and waste in one row).",
))

_register(Dataset(
    "historical_climate_data",
    "Historical Climate Data",
    "historical_climate_data",
    _monthly(
        climate_score=(_PCT, False),
        electricity_kwh=(_NN_FLOAT, False),
        water_litres=(_NN_FLOAT, False),
        waste_kg=(_NN_FLOAT, False),
        emissions_tco2e=(_NN_FLOAT, False),
        renewable_share_percent=(_PCT, False),
        recycling_rate_percent=(_PCT, False),
        water_reuse_rate_percent=(_PCT, False),
    ),
    signature=("climate_score", "renewable_share_percent", "water_reuse_rate_percent"),
    unique_key=("business_id", "month"),
    description="24-month climate series per business: powers trend charts and 'what changed' answers.",
))

# --- decision support / roadmap --------------------------------------------
_register(Dataset(
    "green_solutions",
    "Green Solutions",
    COLLECTIONS["green_solutions"],
    {
        "solution_id": (_STR, True),
        "solution_name": (_STR, True),
        "category": (_STR, True),
        "description": (_TEXT, False),
        "applicable_industries": (_TEXT, False),
        "estimated_capex": (_NN_FLOAT, False),
        "estimated_capex_min": (_NN_FLOAT, False),
        "estimated_capex_max": (_NN_FLOAT, False),
        "estimated_annual_savings": (_NN_FLOAT, False),
        "estimated_annual_emission_reduction_tco2e": (_NN_FLOAT, False),
        "estimated_water_saving_litres": (_NN_FLOAT, False),
        "estimated_waste_reduction_kg": (_NN_FLOAT, False),
        "estimated_annual_energy_saving_kwh": (_NN_FLOAT, False),
        "estimated_payback_months": (_NN_FLOAT, False),
        "implementation_months": (_NN_FLOAT, False),
        "complexity": (_TEXT, False),
        "expected_life_years": (_NN_FLOAT, False),
        "in_climacred_catalog": (_TEXT, False),
        "basis_note": (_TEXT, False),
    },
    signature=("solution_id", "estimated_capex", "estimated_annual_savings"),
    filename_hints=("green_solution", "green_solutions", "solution_catalog", "solutions"),
    unique_key=("solution_id",),
    business_scoped=False,
    description="Solution catalog with capex, savings and payback economics.",
    transform=_catalog_document,
))

_register(Dataset(
    "solution_recommendations",
    "Solution Recommendations",
    "solution_recommendations",
    {
        "business_id": (_STR, True),
        "solution_id": (_STR, True),
        "solution_name": (_STR, True),
        "priority": (_INT, True),
        "reason": (_TEXT, False),
        "baseline_metric": (_TEXT, False),
        "estimated_improvement": (_TEXT, False),
        "estimated_capex": (_NN_FLOAT, False),
        "estimated_annual_savings": (_NN_FLOAT, False),
        "estimated_emission_reduction": (_NN_FLOAT, False),
        "estimated_payback_months": (_NN_FLOAT, False),
        "implementation_timeline": (_TEXT, False),
        "scaling_basis": (_TEXT, False),
        "addresses_dimension": (_TEXT, False),
        "addresses_dimension_score": (_PCT, False),
    },
    signature=("solution_id", "addresses_dimension", "scaling_basis"),
    unique_key=("business_id", "solution_id"),
    description="Per-business recommendations derived from that business's own inefficiencies.",
))

_register(Dataset(
    "scenarios",
    "Scenarios",
    COLLECTIONS["scenarios"],
    {
        "scenario_id": (_STR, True),
        "business_id": (_STR, True),
        "scenario_name": (_STR, True),
        "solutions_included": (_TEXT, False),
        "capex": (_NN_FLOAT, False),
        "annual_operating_cost_change": (_FLOAT, False),
        "annual_energy_savings_kwh": (_NN_FLOAT, False),
        "annual_water_savings_litres": (_NN_FLOAT, False),
        "annual_waste_reduction_kg": (_NN_FLOAT, False),
        "annual_emission_reduction_tco2e": (_NN_FLOAT, False),
        "annual_cost_savings": (_NN_FLOAT, False),
        "payback_years": (_NN_FLOAT, False),
        "projected_5_year_savings": (_FLOAT, False),
        "implementation_months": (_NN_FLOAT, False),
        "baseline_annual_electricity_kwh": (_NN_FLOAT, False),
        "baseline_annual_water_litres": (_NN_FLOAT, False),
        "baseline_annual_emissions_tco2e": (_NN_FLOAT, False),
    },
    signature=("scenario_id", "scenario_name", "solutions_included"),
    filename_hints=("scenario", "scenarios"),
    unique_key=("business_id", "scenario_id"),
    description="Pre-defined what-if scenarios per business (stored as reference scenarios).",
))

_register(Dataset(
    "transformation_plans",
    "Transformation Plans",
    COLLECTIONS["transformation_plans"],
    {
        "business_id": (_STR, True),
        "phase": (_STR, True),
        "action": (_STR, True),
        "solution_id": (_TEXT, False),
        "start_month": (_INT, True),
        "duration_months": (_INT, True),
        "expected_cost": (_NN_FLOAT, False),
        "expected_savings": (_NN_FLOAT, False),
        "expected_emission_reduction": (_NN_FLOAT, False),
        "expected_water_saving": (_NN_FLOAT, False),
        "owner_role": (_TEXT, False),
        "dependency": (_TEXT, False),
        "status": (_TEXT, False),
    },
    signature=("phase", "action", "owner_role", "start_month"),
    filename_hints=("transformation_plan", "transformation_plans", "roadmap"),
    unique_key=("business_id", "phase", "action"),
    description="Phased roadmap actions tied to solution ids.",
))

_register(Dataset(
    "before_after_impact",
    "Before / After Impact",
    COLLECTIONS["impact_records"],
    {
        "business_id": (_STR, True),
        "metric": (_STR, True),
        "baseline_value": (_FLOAT, True),
        "after_value": (_FLOAT, True),
        "unit": (_TEXT, False),
        "improvement_percent": (_SIGNED_PCT, False),
        "verification_status": (_TEXT, False),
        "measurement_period": (_TEXT, False),
        "direction": (_TEXT, False),
    },
    signature=("baseline_value", "after_value", "verification_status"),
    filename_hints=("before_after_impact", "before_after", "impact"),
    unique_key=("business_id", "metric"),
    description="Baseline vs post-intervention metrics for impact verification.",
))

# --- AI test harness reference data ----------------------------------------
_register(Dataset(
    "gemini_ai_test_questions",
    "Gemini AI Test Questions",
    "gemini_ai_test_questions",
    {
        "question_id": (_STR, True),
        "group": (_TEXT, False),
        "question": (_STR, True),
        "expected_answer_basis": (_TEXT, False),
        "must_not_contain": (_TEXT, False),
        "applicable_businesses": (_TEXT, False),
        "gemini_note": (_TEXT, False),
    },
    signature=("question_id", "expected_answer_basis", "must_not_contain"),
    unique_key=("question_id",),
    business_scoped=False,
    description="Chat questions used to verify the AI assistant is grounded in stored data.",
))

_register(Dataset(
    "gemini_expected_behaviors",
    "Gemini Expected Behaviors",
    "gemini_expected_behaviors",
    {
        "test_id": (_STR, True),
        "scenario": (_TEXT, False),
        "user_question": (_TEXT, False),
        "expected_behavior": (_TEXT, False),
        "data_source": (_TEXT, False),
        "should_use_gemini": (_BOOL, False),
        "should_refuse_hallucination": (_BOOL, False),
        "expected_context": (_TEXT, False),
        "pass_condition": (_TEXT, False),
    },
    signature=("test_id", "expected_behavior", "should_refuse_hallucination"),
    unique_key=("test_id",),
    business_scoped=False,
    description="Integration expectations for the AI layer (no-data, disconnected, hallucination guards).",
))


#: Import order recommended by the test-data pack (dependencies first).
IMPORT_ORDER = (
    "business_profiles",
    "climate_assessments",
    "resource_consumption",
    "energy_data",
    "water_data",
    "waste_data",
    "emissions_data",
    "mobility_data",
    "operations_materials",
    "historical_climate_data",
    "green_solutions",
    "solution_recommendations",
    "scenarios",
    "transformation_plans",
    "before_after_impact",
    "gemini_ai_test_questions",
    "gemini_expected_behaviors",
)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------
def _extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _filename_stem(filename: str) -> str:
    """Normalise a filename to a dataset key stem.

    Lowercase, strip the extension and any ``__sheet`` suffix, and treat hyphens
    and spaces as underscores. ``Business Profiles.xlsx`` and
    ``business-profiles.csv`` both become ``business_profiles``.
    """
    name = str(filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    stem = name.rsplit(".", 1)[0].lower() if "." in name else name.lower()
    stem = re.sub(r"__.*$", "", stem)
    stem = stem.replace("-", " ").replace("_", " ")
    stem = re.sub(r"[^a-z0-9]+", "_", stem).strip("_")
    return stem


def _column_aliases() -> dict:
    """Header variants that are not already a known column under case/spacing fold."""
    return {
        "company_name": "business_name",
        "company": "business_name",
        "employees": "employee_count",
        "staff_count": "employee_count",
        "businessid": "business_id",
        "biz_id": "business_id",
    }


def _known_import_columns() -> list:
    columns = []
    for dataset in DATASETS.values():
        columns.extend(dataset.fields.keys())
        if dataset.payload_column:
            columns.append(dataset.payload_column)
    return columns


def _canonicalize_header(value: Any) -> str:
    text_value = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text_value or text_value.lower().startswith("unnamed"):
        return ""
    known = {column.lower(): column for column in _known_import_columns()}
    if text_value in set(known.values()):
        return text_value
    lowered = text_value.lower().replace(" ", "_").replace("-", "_")
    lowered = re.sub(r"_+", "_", lowered).strip("_")
    if lowered in known:
        return known[lowered]
    return _column_aliases().get(lowered, text_value)


def validate_extension(filename: str) -> str:
    ext = _extension(filename)
    if f".{ext}" not in SUPPORTED_EXTENSIONS:
        raise DatasetError(
            f"Unsupported file type '.{ext or filename}'. Supported formats: "
            + ", ".join(SUPPORTED_EXTENSIONS),
            error_code="unsupported_extension",
        )
    return ext


def _read_tables(content: bytes, ext: str):
    """Read every sheet (xlsx/xls) or the single table (csv) of an upload.

    Returns ``(tables, sheet_reports)``. The first worksheet is never assumed to
    be the dataset: empty sheets are reported and skipped, and a hidden sheet is
    used only when the workbook has no visible table.
    """
    from app.services.workbook_parser import WorkbookParseError, read_xlsx

    try:
        if ext == "csv":
            frame = None
            for encoding in ("utf-8-sig", "latin-1"):
                try:
                    frame = pd.read_csv(io.BytesIO(content), dtype=object, encoding=encoding, keep_default_na=False)
                    break
                except UnicodeDecodeError:
                    continue
            if frame is None:
                raise DatasetError("Could not decode the CSV file as text.", error_code="parse_error")
            frame = _normalize_columns(frame)
            report = _sheet_report("csv", frame)
            return [("csv", frame)], [report]
        if ext == "xlsx":
            try:
                tables, reports = read_xlsx(
                    content,
                    known_columns=_known_import_columns(),
                    aliases=_column_aliases(),
                )
            except WorkbookParseError as exc:
                raise DatasetError(str(exc), error_code=exc.error_code, **exc.extra) from None
            if not tables:
                raise DatasetError(
                    "The workbook has no tabular data. Empty, hidden-only, or documentation sheets were ignored.",
                    error_code="empty_workbook",
                    available_sheets=reports,
                    detected_columns=[],
                )
            return tables, reports
        engine = "xlrd"
        sheets = pd.read_excel(io.BytesIO(content), sheet_name=None, dtype=object, engine=engine)
        tables = []
        reports = []
        for name, frame in sheets.items():
            frame = _normalize_columns(frame)
            reports.append(_sheet_report(str(name), frame))
            if not (frame.empty and len(frame.columns) == 0):
                tables.append((str(name), frame))
        if not tables:
            raise DatasetError(
                "The workbook has no tabular data.",
                error_code="empty_workbook",
                available_sheets=reports,
            )
        return tables, reports
    except DatasetError:
        raise
    except Exception as exc:
        raise DatasetError(
            f"Could not parse the file ({type(exc).__name__}: {exc}).",
            error_code="parse_error",
        ) from None


def _sheet_report(name: str, frame: pd.DataFrame, *, role: str = "data") -> dict:
    columns = [str(column) for column in frame.columns]
    return {
        "name": name,
        "state": "visible",
        "empty": not columns and frame.empty,
        "rows": 0 if frame is None else int(len(frame)),
        "columns": columns,
        "role": role,
    }


def _normalize_header(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame.columns = [_canonicalize_header(c) for c in frame.columns]
    # Drop fully unnamed / empty columns (Excel pads tables with them).
    frame = frame.loc[:, [c for c in frame.columns if c and not str(c).lower().startswith("unnamed")]]
    return frame


# ---------------------------------------------------------------------------
# Dataset detection (filename AND headers - never the filename alone)
# ---------------------------------------------------------------------------
def _header_score(dataset: Dataset, headers: Sequence[str]) -> Tuple[int, List[str]]:
    """Header evidence for a dataset: (score, missing required columns)."""
    present = set(headers)
    missing = [c for c in dataset.required_columns if c not in present]
    if missing:
        return -1, missing
    score = 0
    signature_hits = sum(1 for column in dataset.signature if column in present)
    if dataset.signature and signature_hits == 0:
        return -1, []
    score += 25 * signature_hits
    score += 5 * sum(1 for column in dataset.columns if column in present)
    # A header set that clearly belongs to another dataset is penalised.
    foreign = sum(1 for other in DATASETS.values() if other.key != dataset.key for c in other.signature if c in present)
    score -= 3 * foreign
    return score, []


def _filename_score(dataset: Dataset, filename: str) -> int:
    stem = _filename_stem(filename)
    if stem == dataset.key or stem == _filename_stem(dataset.key):
        return 100
    score = 0
    for hint in dataset.filename_hints:
        hint_stem = _filename_stem(hint)
        if hint_stem == stem:
            score = max(score, 100)
        elif hint_stem and hint_stem in stem:
            score = max(score, 40)
    return score


def detect_dataset(filename: str, headers: Sequence[str]) -> Tuple[Optional[Dataset], Dict[str, Any]]:
    """Pick the dataset a table contains.

    A filename match alone is never enough: the required columns must be present
    (and at least one signature column), so ``notes.xlsx`` or a payload sheet can
    never be imported as if it were real data.
    """
    normalized = [_normalize_header(h) for h in headers]
    ranked: List[Tuple[int, Dataset, List[str]]] = []
    for dataset in DATASETS.values():
        header_points, missing = _header_score(dataset, normalized)
        if header_points < 0:
            continue
        ranked.append((header_points + _filename_score(dataset, filename), dataset, missing))
    ranked.sort(key=lambda item: item[0], reverse=True)
    if not ranked:
        return None, {
            "reason": "unknown_dataset",
            "error_code": "unknown_dataset",
            "message": (
                "Unknown dataset type. The column headers do not match any ClimaCred dataset "
                f"(found: {', '.join(normalized[:12])}{'...' if len(normalized) > 12 else ''})."
            ),
            "headers": normalized,
        }
    best_score, best, _missing = ranked[0]
    if best_score < 25:  # pragma: no cover - defensive
        return None, {"reason": "low_confidence", "error_code": "unknown_dataset",
                      "message": "Could not identify the dataset with confidence.",
                      "headers": normalized}
    return best, {
        "reason": "matched",
        "confidence": best_score,
        "headers": normalized,
        "runner_up": ranked[1][1].key if len(ranked) > 1 else None,
    }


def _payload_only_dataset(headers: Sequence[str]) -> Optional[Dataset]:
    """A standalone "API payload" sheet/file: business_id + a payload column.

    The test pack ships ``climate_assessments__assessment_api_payloads.csv`` next to
    ``climate_assessments.csv`` (in the .xlsx it is a second sheet). It carries the
    exact assessment inputs the pack's scores were computed from, so it is attached
    to its parent dataset instead of being rejected as an unknown file.
    """
    present = set(headers)
    if "business_id" not in present:
        return None
    for dataset in DATASETS.values():
        if dataset.payload_column and dataset.payload_column in present:
            return dataset
    return None


def pick_table(filename: str, tables: Sequence[Tuple[str, pd.DataFrame]]) -> Tuple[str, pd.DataFrame, Dataset, Dict[str, Any]]:
    """Choose the sheet that actually holds the dataset (workbooks carry extra sheets).

    A JSON / API-payload companion sheet is never selected when a real tabular
    sheet is present. If several sheets each match a different dataset and the
    filename does not identify one of them, the file is rejected with the
    candidate list instead of silently importing the wrong sheet.
    """
    evaluated: List[Tuple[int, str, pd.DataFrame, Dataset, Dict[str, Any]]] = []
    unknown: Optional[Dict[str, Any]] = None
    detected_columns: List[str] = []
    for sheet_name, frame in tables:
        frame = _normalize_columns(frame)
        if frame.empty and len(frame.columns) == 0:
            continue
        if not detected_columns:
            detected_columns = [str(column) for column in frame.columns]
        dataset, info = detect_dataset(filename, list(frame.columns))
        if dataset is None:
            parent = _payload_only_dataset(list(frame.columns))
            if parent is not None:
                evaluated.append((-1, sheet_name, frame, parent,
                                  {**info, "reason": "payload_sheet", "payload_only": True}))
                continue
            unknown = unknown or info
            continue
        evaluated.append((int(info.get("confidence") or 0), sheet_name, frame, dataset, info))
    if not evaluated:
        headers = (unknown or {}).get("headers") or detected_columns
        raise DatasetError(
            (unknown or {}).get("message") or "No readable data sheet found in the file.",
            error_code=(unknown or {}).get("error_code") or "unknown_dataset",
            detected_columns=list(headers),
        )
    data_sheets = [item for item in evaluated if item[0] >= 0]
    payload_sheets = [item for item in evaluated if item[0] < 0]
    if not data_sheets:
        _score, sheet_name, frame, dataset, info = payload_sheets[0]
        info = {**info, "candidates": _candidate_views(evaluated)}
        return sheet_name, frame, dataset, info

    data_sheets.sort(key=lambda item: item[0], reverse=True)
    distinct = {}
    for item in data_sheets:
        distinct.setdefault(item[3].key, item)
    if len(distinct) > 1:
        winner = data_sheets[0]
        filename_points = _filename_score(winner[3], filename)
        runner_up = next(item for item in data_sheets if item[3].key != winner[3].key)
        runner_points = _filename_score(runner_up[3], filename)
        if filename_points < 100 or filename_points <= runner_points:
            raise DatasetError(
                "This workbook has more than one dataset sheet ("
                + ", ".join(f"{item[1]} → {item[3].key}" for item in data_sheets)
                + "). Split them or name the file after the dataset to import.",
                error_code="multiple_datasets",
                detected_columns=detected_columns,
                candidates=_candidate_views(data_sheets),
            )
    _score, sheet_name, frame, dataset, info = data_sheets[0]
    others = [
        {"sheet": item[1], "dataset": item[3].key, "rows": int(len(item[2])), "confidence": item[0]}
        for item in data_sheets[1:]
    ]
    info = {**info, "candidates": _candidate_views(evaluated), "other_data_sheets": others}
    return sheet_name, frame, dataset, info


def _candidate_views(evaluated: Sequence[Tuple[int, str, pd.DataFrame, Dataset, Dict[str, Any]]]) -> List[Dict[str, Any]]:
    views = []
    for score, sheet_name, frame, dataset, info in evaluated:
        views.append({
            "sheet": sheet_name,
            "dataset": dataset.key,
            "rows": int(len(frame)),
            "confidence": score,
            "payload_only": bool(info.get("payload_only")),
            "columns": [str(column) for column in frame.columns],
        })
    return views

def collect_companion_payloads(
    tables: Sequence[Tuple[str, pd.DataFrame]],
    used_sheet: str,
    dataset: Dataset,
) -> Dict[str, Any]:
    """Read a workbook's companion sheet of API-ready payloads keyed by business_id.

    ``climate_assessments.xlsx`` ships ``post_api_assessment_json`` on a second sheet.
    Those payloads are the exact assessment inputs the pack's own scores were computed
    from, so they are the most faithful import source available. A malformed payload
    is reported, never guessed at.
    """
    if not dataset.payload_column:
        return {}
    payloads: Dict[str, Any] = {}
    for sheet_name, frame in tables:
        if sheet_name == used_sheet:
            continue
        frame = _normalize_columns(frame)
        columns = set(frame.columns)
        if dataset.payload_column not in columns or "business_id" not in columns:
            continue
        for raw_row in frame.to_dict(orient="records"):
            business_id = _normalize_header(raw_row.get("business_id"))
            raw_payload = raw_row.get(dataset.payload_column)
            if not business_id or _is_blank(raw_payload):
                continue
            try:
                parsed = json.loads(str(raw_payload))
            except json.JSONDecodeError:
                payloads[business_id] = {"error": f"{dataset.payload_column} on sheet '{sheet_name}' is not valid JSON."}
                continue
            if isinstance(parsed, dict):
                payloads[business_id] = parsed
    return payloads


# ---------------------------------------------------------------------------
# Value coercion & validation
# ---------------------------------------------------------------------------
_TRUE_VALUES = {"true", "yes", "y", "1", "1.0"}
_FALSE_VALUES = {"false", "no", "n", "0", "0.0", ""}


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and pd.isna(value):
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def _to_number(value: Any) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "").replace("₹", "")
    if text.endswith("%"):
        text = text[:-1]
    return float(text)


def coerce(column: str, spec: Tuple[str, bool], raw: Any) -> Any:
    """Convert one cell to its declared type, or raise ``ValueError``."""
    kind, required = spec
    if _is_blank(raw):
        if required:
            raise ValueError(f"{column} is required but was empty.")
        return None

    if kind == _STR:
        text = _normalize_header(raw)
        if not text:
            raise ValueError(f"{column} is required but was empty.")
        return text
    if kind == _TEXT:
        return _normalize_header(raw)
    if kind in (_INT, _NN_INT):
        try:
            number = _to_number(raw)
        except (TypeError, ValueError):
            raise ValueError(f"{column} must be a whole number (got '{raw}').") from None
        if abs(number - round(number)) > 1e-9:
            raise ValueError(f"{column} must be a whole number (got '{raw}').")
        value = int(round(number))
        if kind == _NN_INT and value < 0:
            raise ValueError(f"{column} cannot be negative (got {value}).")
        return value
    if kind in (_FLOAT, _NN_FLOAT, _PCT, _SIGNED_PCT, _EFF):
        try:
            value = _to_number(raw)
        except (TypeError, ValueError):
            raise ValueError(f"{column} must be numeric (got '{raw}').") from None
        if kind == _NN_FLOAT and value < 0:
            raise ValueError(f"{column} cannot be negative (got {value}).")
        if kind == _PCT and not 0 <= value <= 100:
            raise ValueError(f"{column} must be between 0 and 100 (got {value}).")
        if kind == _SIGNED_PCT and not -100 <= value <= 100:
            raise ValueError(f"{column} must be between -100 and 100 (got {value}).")
        if kind == _EFF and not 0 <= value <= 200:
            raise ValueError(f"{column} must be between 0 and 200 (got {value}).")
        return value
    if kind == _MONTH:
        return _coerce_month(column, raw)
    if kind == _DATE:
        return _coerce_date(column, raw)
    if kind == _BOOL:
        text = str(raw).strip().lower()
        if text in _TRUE_VALUES:
            return True
        if text in _FALSE_VALUES:
            return False
        raise ValueError(f"{column} must be true/false (got '{raw}').")
    if kind == _JSON:
        try:
            return json.loads(str(raw))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{column} must be valid JSON ({exc}).") from None
    raise ValueError(f"{column} has an unsupported column type '{kind}'.")  # pragma: no cover


def _coerce_month(column: str, raw: Any) -> str:
    text = _normalize_header(raw)
    match = _MONTH_RE.match(text)
    if match:
        return text
    try:  # Excel dates arrive as Timestamps
        stamp = pd.to_datetime(raw, errors="raise")
        return f"{stamp.year:04d}-{stamp.month:02d}"
    except (ValueError, TypeError):
        pass
    raise ValueError(f"{column} must be a YYYY-MM month (got '{raw}').")


def _coerce_date(column: str, raw: Any) -> str:
    text = _normalize_header(raw)
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text[:19], fmt).date().isoformat()
        except ValueError:
            continue
    try:
        stamp = pd.to_datetime(raw, errors="raise")
        return stamp.date().isoformat()
    except (ValueError, TypeError):
        raise ValueError(f"{column} must be a valid date (got '{raw}').") from None


def store_payloads_only(dataset: Dataset, frame: pd.DataFrame, import_id: str, *, persist: bool = True, extra_business_ids: Optional[Iterable[str]] = None) -> Tuple[int, List[Dict[str, Any]]]:
    """Attach API-ready payloads from a standalone sheet/file to their business rows.

    Returns (rows stored, validation errors). Nothing is invented: a payload that is
    not valid JSON is reported and skipped.
    """
    col = get_collection(dataset.collection)
    known = set(known_business_ids())
    if extra_business_ids:
        known.update(str(item) for item in extra_business_ids if item)
    stored = 0
    errors: List[Dict[str, Any]] = []
    for position, raw_row in enumerate(frame.to_dict(orient="records"), start=2):
        business_id = _normalize_header(raw_row.get("business_id"))
        raw_payload = raw_row.get(dataset.payload_column)
        if not business_id or not _BUSINESS_ID_RE.match(business_id):
            errors.append({"row": position, "column": "business_id",
                           "message": f"Invalid business_id '{business_id}'. Expected a code such as 'B001'."})
            continue
        if known and business_id not in known:
            errors.append({"row": position, "column": "business_id",
                           "message": f"Invalid business_id '{business_id}': not present in business_profiles."})
            continue
        try:
            payload = json.loads(str(raw_payload))
        except (json.JSONDecodeError, TypeError):
            errors.append({"row": position, "column": dataset.payload_column or "",
                           "message": f"{dataset.payload_column} is not valid JSON."})
            continue
        if not isinstance(payload, dict):
            errors.append({"row": position, "column": dataset.payload_column or "",
                           "message": f"{dataset.payload_column} must be a JSON object."})
            continue
        if not persist:
            stored += 1
            continue
        result = col.update_one(
            {"business_id": business_id, "user_id": None},
            {"$set": {dataset.payload_key: payload, "import_id": import_id,
                      "imported_at": datetime.now(timezone.utc), "dataset_type": dataset.key,
                      "data_origin": DATA_ORIGIN}},
            upsert=True,
        )
        stored += 1 if (getattr(result, "matched_count", 0) or getattr(result, "upserted_id", None)) else 0
    return stored, errors


# ---------------------------------------------------------------------------
# Business registry
# ---------------------------------------------------------------------------
def known_business_ids() -> List[str]:
    col = get_collection(COLLECTIONS["business_profiles"])
    ids = {doc.get("business_id") for doc in col.find({"business_id": {"$ne": None}}, {"business_id": 1})}
    return sorted(str(bid) for bid in ids if bid)


def get_active_business_id() -> Optional[str]:
    """The business_id of the profile the application currently serves (user 'default')."""
    col = get_collection(COLLECTIONS["business_profiles"])
    doc = col.find_one({"user_id": DEFAULT_USER_ID, "business_id": {"$ne": None}}, {"business_id": 1})
    return str(doc["business_id"]) if doc else None


def list_businesses() -> List[Dict[str, Any]]:
    """Every imported business, newest import last, with per-dataset row counts."""
    col = get_collection(COLLECTIONS["business_profiles"])
    active = get_active_business_id()
    businesses: List[Dict[str, Any]] = []
    for doc in col.find({"business_id": {"$ne": None}}).sort("business_id", 1):
        business_id = str(doc["business_id"])
        counts = {
            key: get_collection(dataset.collection).count_documents({"business_id": business_id})
            for key, dataset in DATASETS.items()
            if dataset.business_scoped and key != "business_profiles"
        }
        businesses.append({
            "business_id": business_id,
            "business_name": doc.get("business_name") or doc.get("name"),
            "industry": doc.get("industry"),
            "business_size": doc.get("business_size") or doc.get("businessSize"),
            "location": doc.get("location"),
            "employees": doc.get("employees"),
            "active": business_id == active,
            "row_counts": counts,
            "total_rows": sum(counts.values()),
        })
    return businesses


def activate_business(business_id: str) -> Dict[str, Any]:
    """Make an imported business the one the application serves.

    The imported placeholder row is copied onto the application's profile document
    (``user_id: "default"``) through the existing profile service and then removed,
    so each business exists exactly once in ``business_profiles``.
    """
    from app.services.profile_service import create_or_update_profile

    col = get_collection(COLLECTIONS["business_profiles"])
    doc = col.find_one({"business_id": business_id})
    if not doc:
        raise ValueError(f"Business '{business_id}' has not been imported yet.")
    if not doc.get("business_name"):
        raise ValueError(f"Business '{business_id}' has no business name stored.")
    # Park the previously active profile (user_id=None) BEFORE the upsert. The
    # profile service updates the single user_id="default" document in place, so
    # without this step activating B003 would overwrite B001.
    previous = col.find_one({"user_id": DEFAULT_USER_ID, "business_id": {"$ne": business_id}})
    if previous:
        col.update_one({"_id": previous["_id"]}, {"$set": {"user_id": None}})
    excluded = ("_id", "user_id", "created_at", "updated_at", "imported_at", "dataset_type", "_source_row")
    payload = {key: value for key, value in doc.items() if key not in excluded}
    profile = create_or_update_profile(payload, DEFAULT_USER_ID)
    col.delete_many({"business_id": business_id, "user_id": None})
    logger.info("Activated imported business %s for user %s", business_id, DEFAULT_USER_ID)
    return {"business_id": business_id, "profile": profile, "assessment_synced": sync_assessment_from_imports(business_id)}


# ---------------------------------------------------------------------------
# Row validation
# ---------------------------------------------------------------------------
def validate_rows(dataset: Dataset, frame: pd.DataFrame, *, extra_business_ids: Optional[Iterable[str]] = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Validate + coerce every row. Returns (valid rows, validation errors).

    Nothing is dropped silently: every rejected row produces one entry in the
    error list with its 1-based spreadsheet row number.
    """
    valid: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    known_ids = set(known_business_ids()) if dataset.business_scoped else set()
    if extra_business_ids:
        known_ids.update(str(item) for item in extra_business_ids if item)
    # business_profiles defines the registry, so it validates against itself.
    if dataset.key == "business_profiles":
        known_ids = set()
    seen: set = set()
    unknown_businesses: set = set()

    # Excel row numbers: +2 accounts for the header row and 0-based indexing.
    for position, raw_row in enumerate(frame.to_dict(orient="records"), start=2):
        row: Dict[str, Any] = {}
        row_errors: List[RowError] = []
        for column, spec in dataset.fields.items():
            try:
                row[column] = coerce(column, spec, raw_row.get(column))
            except ValueError as exc:
                row_errors.append(RowError(position, column, str(exc)))
        if row_errors:
            errors.extend(err.as_dict() for err in row_errors)
            continue

        if dataset.business_scoped:
            business_id = str(row.get("business_id") or "")
            if not _BUSINESS_ID_RE.match(business_id):
                errors.append({"row": position, "column": "business_id",
                               "message": f"Invalid business_id '{business_id}'. Expected a code such as 'B001'."})
                continue
            if dataset.key != "business_profiles" and known_ids and business_id not in known_ids:
                errors.append({"row": position, "column": "business_id",
                               "message": (f"Invalid business_id '{business_id}': not present in business_profiles. "
                                           "Import business_profiles first.")})
                continue
            if dataset.key != "business_profiles" and not known_ids:
                unknown_businesses.add(business_id)

        if dataset.unique_key:
            key = tuple(row.get(column) for column in dataset.unique_key)
            if key in seen:
                errors.append({"row": position, "column": ", ".join(dataset.unique_key),
                               "message": f"Duplicate record ({', '.join(str(part) for part in key)}) already present in this file."})
                continue
            seen.add(key)

        if dataset.key == "business_profiles":
            known_ids.add(str(row.get("business_id")))

        row["_row"] = position
        valid.append(row)

    if unknown_businesses and dataset.key != "business_profiles":
        errors.append({
            "row": None,
            "column": "business_id",
            "message": (f"No business profiles are stored yet, so {', '.join(sorted(unknown_businesses))} could not be "
                        "linked to a business. Import business_profiles first, then re-import this file."),
        })
        return [], errors
    return valid, errors


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------
def _store_document(dataset: Dataset, row: Dict[str, Any], import_id: str, now: datetime,
                    payloads: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Build the (query, document) pair used to upsert one validated row."""
    stored = {k: v for k, v in row.items() if not k.startswith("_")}
    if dataset.transform is not None:
        stored = dataset.transform(stored)
        stored = {k: v for k, v in stored.items() if v is not None}
        stored["_source_row"] = {k: v for k, v in row.items() if not k.startswith("_")}
    stored["data_origin"] = DATA_ORIGIN
    stored["import_id"] = import_id
    stored["imported_at"] = now
    stored["dataset_type"] = dataset.key
    if dataset.payload_key and payloads:
        payload = payloads.get(str(row.get("business_id")))
        if isinstance(payload, dict) and "error" not in payload:
            stored[dataset.payload_key] = payload
    # Per-user scoping. The solution catalog is shared platform content, so imported
    # solutions are matched by ``id``. Every other dataset is stored with
    # ``user_id: None`` and linked through ``business_id``: an imported row can then
    # never be mistaken for the single document the user created through the UI, and
    # ``save_assessment``/``get_profile`` (which filter on ``user_id``) ignore it.
    is_catalog = dataset.collection == COLLECTIONS["green_solutions"]
    stored["user_id"] = DEFAULT_USER_ID if is_catalog else None
    if not dataset.unique_key:
        return {"_id": uuid.uuid4().hex}, stored
    query: Dict[str, Any] = {column: row.get(column) for column in dataset.unique_key}
    if not is_catalog:
        query["user_id"] = None
    return query, stored


def _upsert(dataset: Dataset, query: Dict[str, Any], document: Dict[str, Any]) -> str:
    col = get_collection(dataset.collection)
    if dataset.collection == COLLECTIONS["green_solutions"]:
        return _upsert_catalog(col, query, document)
    existing = col.find_one(query, {"_id": 1})
    if existing:
        col.update_one({"_id": existing["_id"]}, {"$set": document})
        return "updated"
    col.insert_one(document)
    return "inserted"


def _upsert_catalog(col: Any, query: Dict[str, Any], document: Dict[str, Any]) -> str:
    """Green solutions are platform catalog content: never overwrite the app's own
    economics, keep the imported figures alongside as a reference instead."""
    existing = col.find_one({"id": query["solution_id"]})
    reference = {k: v for k, v in (document.get("_source_row") or {}).items()}
    if existing:
        col.update_one({"_id": existing["_id"]}, {"$set": {"imported_reference": reference,
                                                           "imported_at": document["imported_at"],
                                                           "import_id": document["import_id"]}})
        return "updated"
    document.pop("_source_row", None)
    col.insert_one(document)
    return "inserted"


# ---------------------------------------------------------------------------
# Assessment derivation (deterministic engine stays the source of truth)
# ---------------------------------------------------------------------------
def _latest_month(collection_name: str, business_id: str) -> Optional[Dict[str, Any]]:
    col = get_collection(collection_name)
    return col.find_one({"business_id": business_id}, sort=[("month", -1)])


#: Assessment sections the scoring engine understands.
ASSESSMENT_SECTIONS = ("energy", "water", "waste", "emissions", "mobility", "greenPractices", "green_practices")


def stored_assessment_payload(business_id: str) -> Optional[Dict[str, Any]]:
    """The API-ready assessment inputs imported with ``climate_assessments`` (if any)."""
    col = get_collection(COLLECTIONS["climate_assessments"])
    doc = col.find_one(
        {"business_id": business_id, "assessment_payload": {"$exists": True}},
        sort=[("assessment_date", -1)],
    )
    payload = (doc or {}).get("assessment_payload")
    if not isinstance(payload, dict) or not any(section in payload for section in ASSESSMENT_SECTIONS):
        return None
    return {section: values for section, values in payload.items()
            if section in ASSESSMENT_SECTIONS and isinstance(values, dict) and values}


def derive_assessment_payload(business_id: str) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """Build the Climate Assessment INPUTS for a business from its imported data.

    Precedence:
      1. the API-ready assessment payload that came with ``climate_assessments``
         (the most faithful record of what the business reported), else
      2. values derived from the imported monthly resource streams.

    In both cases only the INPUTS are taken from the import: the Energy / Water /
    Waste / Emissions / Mobility / Operations and overall scores are calculated by
    the existing ClimaCred engine (``app/climate_engine``). Nothing is taken from
    Gemini, and the scores shipped inside ``climate_assessments`` are never used as
    the application's score - they are stored for comparison only.
    """
    imported = stored_assessment_payload(business_id)
    if imported:
        return imported, {
            "available": True,
            "business_id": business_id,
            "input_source": "imported_climate_assessments_payload",
            "sources": {"climate_assessments": "assessment_payload"},
        }

    energy = _latest_month("energy_data", business_id)
    water = _latest_month("water_data", business_id)
    waste = _latest_month("waste_data", business_id)
    mobility = _latest_month("mobility_data", business_id)
    resources = _latest_month("resource_consumption", business_id)
    operations = _latest_month("operations_materials", business_id)

    sources = {
        "energy_data": (energy or {}).get("month"),
        "water_data": (water or {}).get("month"),
        "waste_data": (waste or {}).get("month"),
        "mobility_data": (mobility or {}).get("month"),
        "resource_consumption": (resources or {}).get("month"),
        "operations_materials": (operations or {}).get("month"),
    }
    used = {key: value for key, value in sources.items() if value}
    if not used:
        return None, {"available": False, "sources": sources,
                      "message": "No imported monthly resource data found for this business yet."}
    input_source = "derived_from_imported_monthly_data"

    def _pick(primary: Optional[Dict[str, Any]], primary_key: str, fallback: Optional[Dict[str, Any]], fallback_key: str) -> Optional[float]:
        for frame, key in ((primary, primary_key), (fallback, fallback_key)):
            if frame and frame.get(key) is not None:
                return float(frame[key])
        return None

    electricity = _pick(energy, "electricity_kwh", resources, "electricity_kwh")
    stationary_diesel = _pick(energy, "diesel_litres", None, "")
    water_litres = _pick(water, "freshwater_intake_litres", resources, "water_litres")
    organic = _pick(waste, "organic_kg", resources, "organic_waste_kg")
    hazardous = _pick(waste, "hazardous_kg", resources, "hazardous_waste_kg")
    total_waste = _pick(waste, "total_waste_kg", resources, "total_waste_kg")
    recycling_rate = _pick(waste, "recycling_rate_percent", None, "")
    fleet_diesel = (mobility or {}).get("diesel_litres")
    fleet_petrol = (mobility or {}).get("petrol_litres")
    lpg = _pick(resources, "LPG_kg", energy, "LPG_kg")

    # "Material / scrap waste" is the residual of the imported waste split, so the
    # engine's total (organic + plastic + paper + industrial + material) equals the
    # imported total_waste_kg exactly instead of under-counting it.
    material_scrap = None
    if total_waste is not None:
        material_scrap = max(0.0, total_waste - (organic or 0.0) - (hazardous or 0.0))

    payload: Dict[str, Any] = {
        "energy": {},
        "water": {},
        "waste": {},
        "emissions": {},
        "mobility": {},
        "greenPractices": {},
    }
    if electricity is not None:
        payload["energy"]["monthlyElectricityKwh"] = round(electricity, 2)
    if stationary_diesel is not None:
        payload["energy"]["generatorFuelLitresPerMonth"] = round(float(stationary_diesel), 2)
    if water_litres is not None:
        payload["water"]["monthlyWaterLitres"] = round(water_litres, 2)
    if water and water.get("reused_water_litres") is not None:
        payload["water"]["waterRecyclingAvailable"] = float(water["reused_water_litres"]) > 0
        payload["greenPractices"]["waterRecycling"] = float(water["reused_water_litres"]) > 0
    if organic is not None:
        payload["waste"]["organicWasteKgPerMonth"] = round(organic, 2)
    if hazardous is not None:
        payload["waste"]["industrialWasteKgPerMonth"] = round(hazardous, 2)
    if material_scrap is not None:
        payload["waste"]["textileMaterialWasteKgPerMonth"] = round(material_scrap, 2)
    if recycling_rate is not None:
        payload["waste"]["currentRecyclingPercent"] = round(float(recycling_rate), 2)
        payload["waste"]["wasteSegregationPracticed"] = float(recycling_rate) > 0
        payload["greenPractices"]["wasteSegregation"] = float(recycling_rate) > 0
    if fleet_diesel is not None or fleet_petrol is not None:
        payload["mobility"]["monthlyFleetFuelLitres"] = round(float(fleet_diesel or 0) + float(fleet_petrol or 0), 2)
    if mobility and mobility.get("company_vehicle_count") is not None:
        payload["mobility"]["deliveryVehiclesCount"] = int(mobility["company_vehicle_count"])
    if mobility:
        fuels = {"Diesel": float(mobility.get("diesel_litres") or 0),
                 "Petrol": float(mobility.get("petrol_litres") or 0),
                 "CNG": float(mobility.get("CNG_kg") or 0)}
        dominant = max(fuels, key=lambda name: fuels[name])
        if fuels[dominant] > 0:
            payload["mobility"]["vehicleFuelType"] = dominant
        if mobility.get("EV_kwh") is not None and mobility.get("company_vehicle_count"):
            payload["greenPractices"]["evAdoption"] = float(mobility["EV_kwh"]) > 0
    # Total diesel across the site (stationary + fleet) is what the emissions score uses.
    total_diesel = sum(v for v in (
        float(stationary_diesel) if stationary_diesel is not None else None,
        float(fleet_diesel) if fleet_diesel is not None else None,
    ) if v is not None) if (stationary_diesel is not None or fleet_diesel is not None) else None
    if total_diesel is not None:
        payload["emissions"]["monthlyDieselLitres"] = round(total_diesel, 2)
    if fleet_petrol is not None:
        payload["emissions"]["monthlyPetrolLitres"] = round(float(fleet_petrol), 2)
    if lpg is not None:
        # The pack records LPG, not natural gas; the engine's gas factor (2.75 kg CO2e/kg)
        # is applied to it and the substitution is recorded in the assessment document.
        payload["emissions"]["monthlyNaturalGasKg"] = round(float(lpg), 2)
    if energy and energy.get("renewable_kwh") is not None:
        payload["greenPractices"]["solarPanels"] = float(energy["renewable_kwh"]) > 0
    if operations and operations.get("material_efficiency_percent") is not None:
        payload["greenPractices"]["sustainableMaterials"] = float(operations["material_efficiency_percent"]) >= 80

    payload = {section: values for section, values in payload.items() if values}
    if not payload:
        return None, {"available": False, "sources": sources, "message": "Imported rows contained no usable values."}
    return payload, {"available": True, "sources": sources, "business_id": business_id,
                     "input_source": input_source}


def sync_assessment_from_imports(business_id: Optional[str] = None) -> Dict[str, Any]:
    """Derive the app's Climate Assessment from imported data and score it.

    Uses the existing ``assessment_service`` / fingerprint engine, so the Climate
    Fingerprint, dashboard, recommendations, scenarios and reports all follow.
    """
    from app.services.assessment_service import save_assessment
    from app.services.fingerprint_service import generate_and_save_fingerprint

    business_id = business_id or get_active_business_id()
    if not business_id:
        return {"synced": False, "reason": "no_active_business",
                "message": "No imported business is active yet. Import business_profiles first."}
    payload, info = derive_assessment_payload(business_id)
    if not payload:
        return {"synced": False, "reason": "no_monthly_data", "business_id": business_id, **info}
    try:
        # The imported assessment REPLACES the stored one: save_assessment() merges
        # section by section, so a leftover field from the previously active business
        # would otherwise survive a business switch or a re-import.
        get_collection(COLLECTIONS["climate_assessments"]).delete_many({"user_id": DEFAULT_USER_ID})
        save_assessment(payload, DEFAULT_USER_ID)
    except ValueError as exc:
        return {"synced": False, "reason": "validation_failed", "business_id": business_id, "message": str(exc), **info}
    get_collection(COLLECTIONS["climate_assessments"]).update_one(
        {"user_id": DEFAULT_USER_ID},
        {"$set": {"derived_from_import": {"business_id": business_id, **info}}},
    )
    fingerprint = generate_and_save_fingerprint(DEFAULT_USER_ID)
    return {
        "synced": True,
        "business_id": business_id,
        "assessment_sections": sorted(payload.keys()),
        "derived_from": info.get("sources"),
        "overall_score": fingerprint.get("overallScore"),
        "score_label": fingerprint.get("scoreLabel"),
        "dimension_scores": {d.get("dimension"): d.get("score") for d in (fingerprint.get("dimensions") or [])},
        "note": (
            "Assessment inputs came from "
            + ("the assessment payload imported with climate_assessments."
               if info.get("input_source") == "imported_climate_assessments_payload"
               else "the imported monthly resource streams (LPG is scored with the natural-gas "
                    "emission factor).")
            + " Every score is calculated by the ClimaCred engine - the scores shipped inside "
              "climate_assessments are stored for comparison only and are never used as the "
              "application's score."
        ),
    }


# ---------------------------------------------------------------------------
# Import orchestration
# ---------------------------------------------------------------------------
def _record_import(summary: Dict[str, Any]) -> None:
    get_collection("data_imports").insert_one({**summary, "user_id": DEFAULT_USER_ID})


def _finish_summary(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Add the fields the Data Import page and the regression tests both read."""
    summary["completed_at"] = summary.get("completed_at") or datetime.now(timezone.utc).isoformat()
    dataset = summary.get("dataset_type")
    rows = int(summary.get("rows_received") or 0)
    rejected = int(summary.get("rows_rejected") or 0)
    errors = list(summary.get("validation_errors") or [])
    accepted = int(summary.get("rows_imported") or 0)
    filename = summary.get("filename") or ""
    ext = _extension(filename)
    summary["dataset"] = dataset
    summary["rows"] = rows
    summary["extension"] = f".{ext}" if ext else summary.get("extension")
    summary["columns"] = list(summary.get("columns") or [])
    summary["available_sheets"] = list(summary.get("available_sheets") or [])
    if not summary.get("detected_columns"):
        for sheet in summary["available_sheets"]:
            if sheet.get("columns"):
                summary["detected_columns"] = list(sheet["columns"])
                break
        else:
            summary["detected_columns"] = list(summary["columns"])
    fully_valid = bool(dataset) and rows > 0 and rejected == 0 and not errors and bool(summary.get("success"))
    summary["validation"] = {
        "valid": fully_valid,
        "accepted_rows": accepted,
        "rejected_rows": rejected,
        "errors": errors,
    }
    if fully_valid:
        summary["status"] = "imported" if summary.get("stored") else "valid"
        summary["error_code"] = None
    elif not dataset:
        summary["status"] = "unrecognized"
        summary["success"] = False
        summary.setdefault("error_code", "unknown_dataset")
    elif rows == 0:
        summary["status"] = "needs_attention"
        summary["success"] = False
        summary.setdefault("error_code", "empty_dataset")
    else:
        summary["status"] = "needs_attention" if not summary.get("stored") or not summary.get("success") or rejected else "imported"
        if rejected or errors:
            summary["status"] = "needs_attention"
        summary.setdefault("error_code", "validation_failed")
    return summary


def provisional_business_ids(files: Sequence[Tuple[str, bytes]]) -> set:
    """Business ids declared by business_profiles files in this same request.

    Preview validates the whole batch before anything is stored, so a climate
    file uploaded next to business_profiles must not be rejected as unknown.
    """
    ids: set = set()
    for name, content in files:
        try:
            ext = validate_extension(name)
            tables, _reports = _read_tables(content, ext)
            if not tables:
                continue
            _sheet, frame, dataset, info = pick_table(name, tables)
        except (DatasetError, Exception):
            continue
        if dataset.key != "business_profiles" or info.get("payload_only"):
            continue
        if "business_id" not in frame.columns:
            continue
        for value in frame["business_id"].tolist():
            text_value = _normalize_header(value)
            if text_value:
                ids.add(text_value)
    return ids


def import_table(
    filename: str,
    content: bytes,
    *,
    import_id: Optional[str] = None,
    persist: bool = True,
    extra_business_ids: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """Parse, detect, validate and (optionally) store one uploaded file."""
    import_id = import_id or uuid.uuid4().hex
    started = datetime.now(timezone.utc)
    summary: Dict[str, Any] = {
        "import_id": import_id,
        "filename": filename,
        "success": False,
        "dataset_type": None,
        "dataset_label": None,
        "collection": None,
        "sheet": None,
        "rows_received": 0,
        "rows_imported": 0,
        "rows_inserted": 0,
        "rows_updated": 0,
        "rows_rejected": 0,
        "validation_errors": [],
        "available_sheets": [],
        "detected_columns": [],
        "columns": [],
        "started_at": started.isoformat(),
        "completed_at": None,
        "message": "",
        "stored": bool(persist),
    }
    try:
        ext = validate_extension(filename)
        summary["extension"] = f".{ext}"
        if len(content) > MAX_FILE_BYTES:
            raise DatasetError(
                f"File is {len(content) / 1048576:.1f} MB; the limit is {MAX_FILE_BYTES // 1048576} MB.",
                error_code="file_too_large",
            )
        tables, reports = _read_tables(content, ext)
        summary["available_sheets"] = reports
        if not tables:
            raise DatasetError("The file contains no sheets.", error_code="empty_workbook", available_sheets=reports)
        sheet_name, frame, dataset, info = pick_table(filename, tables)
        frame = frame.dropna(how="all")
        summary["columns"] = [str(column) for column in frame.columns]
        summary["detected_columns"] = list(summary["columns"])
        payloads = collect_companion_payloads(tables, sheet_name, dataset)
        if info.get("payload_only"):
            stored, errors = store_payloads_only(
                dataset, frame, import_id, persist=persist, extra_business_ids=extra_business_ids,
            )
            summary.update({
                "dataset_type": dataset.key,
                "dataset_label": dataset.label,
                "collection": dataset.collection,
                "sheet": sheet_name,
                "detection": info,
                "rows_received": int(len(frame)),
                "rows_imported": stored,
                "rows_rejected": int(len(frame) - stored),
                "validation_errors": errors,
                "success": stored > 0 and not errors,
                "message": (
                    f"{filename} - {stored} assessment input payload(s) attached to {dataset.label}."
                    if stored else f"{filename} - no usable payload rows."
                ),
            })
        else:
            summary.update({
                "dataset_type": dataset.key,
                "dataset_label": dataset.label,
                "collection": dataset.collection,
                "sheet": sheet_name,
                "detection": info,
                "rows_received": int(len(frame)),
            })
            valid, errors = validate_rows(dataset, frame, extra_business_ids=extra_business_ids)
            summary["validation_errors"] = errors
            summary["rows_rejected"] = int(len(frame) - len(valid))
            if any("Duplicate record" in (err.get("message") or "") for err in errors):
                summary["error_code"] = "duplicate_record"
            elif any(
                "not present in business_profiles" in (err.get("message") or "")
                or "No business profiles are stored yet" in (err.get("message") or "")
                for err in errors
            ):
                summary["error_code"] = "unknown_business_id"

            if not valid:
                summary["rows_imported"] = 0
                summary["success"] = False
                summary["message"] = (
                    f"{filename} - {summary['rows_rejected']} of {summary['rows_received']} rows rejected: "
                    + (errors[0]["message"] if errors else "no rows to import.")
                )
            else:
                if not persist:
                    summary["rows_imported"] = len(valid)
                else:
                    now = datetime.now(timezone.utc)
                    for row in valid:
                        query, document = _store_document(dataset, row, import_id, now, payloads)
                        outcome = _upsert(dataset, query, document)
                        summary["rows_imported"] += 1
                        summary["rows_inserted" if outcome == "inserted" else "rows_updated"] += 1
                if payloads:
                    summary["companion_payloads"] = sorted(
                        k for k, v in payloads.items() if isinstance(v, dict) and "error" not in v
                    )
                summary["success"] = True
                summary["message"] = (
                    f"{filename} - {summary['rows_imported']} {dataset.label.lower()} rows "
                    + ("validated and ready to import" if not persist else "imported")
                    + (f", {summary['rows_rejected']} rejected." if summary["rows_rejected"] else ".")
                )
                if dataset.business_scoped and valid:
                    summary["business_ids"] = sorted({str(row.get("business_id")) for row in valid if row.get("business_id")})
    except DatasetError as exc:
        summary["message"] = f"{filename} - {exc}"
        summary["error"] = str(exc)
        summary["error_code"] = getattr(exc, "error_code", "dataset_error")
        extra = getattr(exc, "extra", {}) or {}
        for key in ("detected_columns", "available_sheets", "candidates"):
            if extra.get(key) is not None:
                summary[key] = extra[key]
        summary["success"] = False
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Import of %s failed: %s", filename, exc, exc_info=True)
        summary["message"] = f"{filename} - import failed ({type(exc).__name__})."
        summary["error"] = str(exc)
        summary["error_code"] = "import_failed"
        summary["success"] = False

    summary = _finish_summary(summary)
    if persist:
        _record_import(summary)
    return summary

def import_files(files: Iterable[Tuple[str, bytes]]) -> Dict[str, Any]:
    """Import several uploads in one request.

    Files are processed in the dependency order recommended by the data pack
    (business profiles first), then in the order they were uploaded, so a single
    multi-file upload always links correctly.
    """
    import_id = uuid.uuid4().hex
    started = datetime.now(timezone.utc)
    items = list(files)

    def sort_key(item: Tuple[str, bytes]) -> Tuple[int, int, str]:
        name = item[0]
        ext = _extension(name)
        stem = _filename_stem(name)
        order = IMPORT_ORDER.index(stem) if stem in IMPORT_ORDER else len(IMPORT_ORDER)
        return (0 if f".{ext}" in SUPPORTED_EXTENSIONS else 1, order, name)

    known_ids = provisional_business_ids(items)
    results = [
        import_table(name, content, import_id=import_id, extra_business_ids=known_ids)
        for name, content in sorted(items, key=sort_key)
    ]

    # A profile import (re)links the active business; monthly imports feed the engine.
    imported_types = [r["dataset_type"] for r in results if r["success"]]
    assessment = None
    if any(t in imported_types for t in ("business_profiles", "climate_assessments", "resource_consumption",
                                         "energy_data", "water_data", "waste_data", "emissions_data",
                                         "mobility_data", "operations_materials")):
        profile_result = next((r for r in results if r["dataset_type"] == "business_profiles" and r["success"]), None)
        if profile_result and profile_result.get("business_ids"):
            activate_business(profile_result["business_ids"][0])
        assessment = sync_assessment_from_imports()

    summary = {
        "success": all(r["success"] for r in results) and bool(results),
        "import_id": import_id,
        "files_received": len(results),
        "datasets_imported": len([r for r in results if r["success"]]),
        "datasets_failed": len([r for r in results if not r["success"]]),
        "rows_imported": sum(r["rows_imported"] for r in results),
        "rows_rejected": sum(r["rows_rejected"] for r in results),
        "results": results,
        "assessment": assessment,
        "active_business": get_active_business_id(),
        "started_at": started.isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "message": (
            f"{len([r for r in results if r['success']])} dataset(s) imported successfully"
            if all(r["success"] for r in results) and results
            else f"{len([r for r in results if not r['success']])} file(s) failed to import."
        ),
    }
    return summary


def import_history(limit: int = 25) -> List[Dict[str, Any]]:
    col = get_collection("data_imports")
    history = []
    for doc in col.find({"user_id": DEFAULT_USER_ID}).sort("started_at", -1).limit(limit):
        doc.pop("_id", None)
        history.append(doc)
    return history


def stored_counts() -> Dict[str, int]:
    """Document counts per collection - proves whether the database is really empty."""
    counts: Dict[str, int] = {}
    names = sorted(set(list(COLLECTIONS.values()) + [d.collection for d in DATASETS.values()] + ["data_imports"]))
    for name in names:
        counts[name] = int(get_collection(name).count_documents({}))
    return counts


def import_status() -> Dict[str, Any]:
    """Everything the Data Import page needs to describe the current state."""
    from app.services.profile_service import get_profile

    profile = get_profile(DEFAULT_USER_ID) or {}
    col = get_collection(COLLECTIONS["business_profiles"])
    active_doc = col.find_one({"user_id": DEFAULT_USER_ID}) or {}
    return {
        "supported_formats": list(SUPPORTED_EXTENSIONS),
        "max_file_mb": MAX_FILE_BYTES // 1048576,
        "datasets": [DATASETS[key].describe() for key in IMPORT_ORDER],
        "recommended_import_order": list(IMPORT_ORDER),
        "collections": stored_counts(),
        "active_business_id": get_active_business_id(),
        "active_business": {
            "name": profile.get("name") or profile.get("business_name"),
            "industry": profile.get("industry"),
            "business_size": profile.get("businessSize") or profile.get("business_size"),
            "business_id": active_doc.get("business_id"),
            "data_origin": active_doc.get("data_origin"),
            "import_id": active_doc.get("import_id"),
            "source": (
                "imported" if active_doc.get("data_origin") == DATA_ORIGIN
                else "developer_seed_script" if active_doc.get("data_origin")
                else "entered_in_app" if active_doc else None
            ),
        } if active_doc else None,
        "businesses": list_businesses(),
        "recent_imports": import_history(limit=10),
    }
