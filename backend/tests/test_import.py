"""
Tests for the Excel / CSV Data Import workflow.

Covers:
  * dataset detection from filename AND headers (never the filename alone)
  * per-row validation with human-readable, row-numbered errors
  * storage in the existing MongoDB collections, linked by ``business_id``
  * the Climate Assessment / Fingerprint being DERIVED from imported data by the
    existing deterministic engine (never taken from the scores in the file)
  * import history, preview-without-storing and idempotent re-imports
  * the reset really emptying an imported database

The ClimaCred test data pack that ships in this repository
(``test_data_pack/csv``) is used where it exists, so these tests exercise the same
files a user uploads. Tests that need a broken row build one inline.
"""
from __future__ import annotations

import csv
from pathlib import Path

import json

import pandas as pd
import pytest

from app.database.mongodb import get_collection
from app.services import import_service
from tests.conftest import client  # noqa: F401  (shared TestClient, empty DB per test)

PACK_CSV = Path(__file__).resolve().parents[2] / "test_data_pack" / "csv"
HAS_PACK = (PACK_CSV / "business_profiles.csv").is_file()


def upload(name: str, content: bytes | str):
    """Build the multipart tuple FastAPI expects for one uploaded file."""
    data = content.encode() if isinstance(content, str) else content
    return ("files", (name, data, "application/octet-stream"))


def pack_csv(name: str) -> bytes:
    return (PACK_CSV / f"{name}.csv").read_bytes()


def expected_scores(business_id: str = "B001") -> dict:
    """The scores the pack says the backend engine must produce for a business."""
    with (PACK_CSV / "climate_assessments.csv").open(newline="", encoding="utf-8") as handle:
        row = next(r for r in csv.DictReader(handle) if r["business_id"] == business_id)
    return {
        "overall": float(row["overall_climate_score"]),
        "Energy": float(row["energy_score"]),
        "Water": float(row["water_score"]),
        "Waste": float(row["waste_score"]),
        "Emissions": float(row["emissions_score"]),
        "Mobility": float(row["mobility_score"]),
        "Operations": float(row["operations_score"]),
    }


# ---------------------------------------------------------------------------
# Empty state
# ---------------------------------------------------------------------------
def test_import_status_on_an_empty_database():
    body = client.get("/api/import").json()
    assert body["active_business"] is None
    assert body["active_business_id"] is None
    assert body["businesses"] == []
    assert body["recent_imports"] == []
    assert body["supported_formats"] == [".xlsx", ".xls", ".csv"]
    assert body["collections"]["business_profiles"] == 0
    assert body["collections"]["energy_data"] == 0
    # The dataset registry the UI renders.
    assert [d["dataset_type"] for d in body["datasets"]][0] == "business_profiles"
    assert len(body["datasets"]) == 17


def test_datasets_endpoint_lists_every_supported_dataset():
    body = client.get("/api/import/datasets").json()
    keys = {d["dataset_type"] for d in body["datasets"]}
    assert {
        "business_profiles", "climate_assessments", "resource_consumption", "emissions_data",
        "mobility_data", "waste_data", "water_data", "energy_data", "operations_materials",
        "green_solutions", "solution_recommendations", "scenarios", "transformation_plans",
        "before_after_impact", "historical_climate_data", "gemini_ai_test_questions",
        "gemini_expected_behaviors",
    } <= keys
    energy = next(d for d in body["datasets"] if d["dataset_type"] == "energy_data")
    assert "electricity_kwh" in energy["required_columns"]
    assert "month" in energy["required_columns"]


def test_upload_requires_a_file():
    """A request with no file at all is rejected by request validation (no 500)."""
    response = client.post("/api/import", files=[])
    assert response.status_code == 422
    assert response.json()["detail"]


def test_upload_rejects_an_empty_file():
    response = client.post("/api/import", files=[upload("business_profiles.csv", b"")])
    assert response.status_code == 400
    assert "is empty" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------
def test_rejects_an_unsupported_extension():
    result = client.post("/api/import", files=[upload("notes.txt", "business_id,month\nB001,2026-01\n")]).json()
    assert result["success"] is False
    assert result["datasets_failed"] == 1
    assert "Unsupported file type" in result["results"][0]["message"]
    assert "Supported formats: .xlsx, .xls, .csv" in result["results"][0]["message"]


def test_rejects_an_unknown_dataset():
    result = client.post("/api/import", files=[upload("notes.csv", "foo,bar,baz\n1,2,3\n")]).json()
    assert result["results"][0]["success"] is False
    assert "Unknown dataset type" in result["results"][0]["message"]


def test_filename_alone_is_never_enough():
    """A file *named* energy_data.csv with unrelated columns must not be imported."""
    result = client.post("/api/import", files=[upload("energy_data.csv", "foo,bar\n1,2\n")]).json()
    assert result["results"][0]["success"] is False
    assert result["results"][0]["dataset_type"] is None


def test_detects_the_dataset_from_headers_when_the_filename_is_generic():
    """Headers decide: a badly named file is still recognised and validated."""
    client.post("/api/import", files=[upload("business_profiles.csv", pack_csv("business_profiles"))])
    frame = PACK_CSV / "water_data.csv"
    result = client.post("/api/import/preview", files=[upload("my-upload.csv", frame.read_bytes())]).json()
    assert result["results"][0]["dataset_type"] == "water_data"
    assert result["results"][0]["rows_received"] == 60
    assert result["results"][0]["rows_imported"] == 60
    assert result["results"][0]["success"] is True
    assert result["results"][0]["stored"] is False
    assert get_collection("water_data").count_documents({}) == 0


def test_preview_stores_nothing():
    client.post("/api/import/preview", files=[upload("business_profiles.csv", pack_csv("business_profiles"))])
    assert get_collection("business_profiles").count_documents({}) == 0
    assert client.get("/api/profile").json() is None


# ---------------------------------------------------------------------------
# Row validation
# ---------------------------------------------------------------------------
def _energy_csv(rows: list[str]) -> str:
    header = ("business_id,month,electricity_kwh,grid_kwh,renewable_kwh,diesel_litres,LPG_kg,"
              "peak_demand_kw,production_units,energy_intensity_kwh_per_unit,renewable_share_percent")
    return "\n".join([header, *rows]) + "\n"


def test_reports_invalid_numeric_values_with_row_numbers():
    client.post("/api/import", files=[upload("business_profiles.csv", pack_csv("business_profiles"))])
    body = _energy_csv([
        "B001,2026-01,1000,1000,0,0,0,10,100,10,0",
        "B001,2026-02,not-a-number,1000,0,0,0,10,100,10,0",
        "B001,2026-03,1000,1000,0,0,0,10,100,10,0",
    ])
    result = client.post("/api/import", files=[upload("energy_data.csv", body)]).json()["results"][0]
    assert result["rows_received"] == 3
    assert result["rows_imported"] == 2
    assert result["rows_rejected"] == 1
    assert result["success"] is True
    error = result["validation_errors"][0]
    assert error["row"] == 3  # spreadsheet row: header + 2
    assert error["column"] == "electricity_kwh"
    assert "must be numeric" in error["message"]


def test_rejects_negative_consumption():
    client.post("/api/import", files=[upload("business_profiles.csv", pack_csv("business_profiles"))])
    body = _energy_csv(["B001,2026-01,-500,1000,0,0,0,10,100,10,0"])
    result = client.post("/api/import", files=[upload("energy_data.csv", body)]).json()["results"][0]
    assert result["rows_imported"] == 0
    assert "cannot be negative" in result["validation_errors"][0]["message"]


def test_rejects_an_invalid_month():
    client.post("/api/import", files=[upload("business_profiles.csv", pack_csv("business_profiles"))])
    body = _energy_csv(["B001,2026-13,1000,1000,0,0,0,10,100,10,0"])
    result = client.post("/api/import", files=[upload("energy_data.csv", body)]).json()["results"][0]
    assert result["rows_imported"] == 0
    assert "must be a YYYY-MM month" in result["validation_errors"][0]["message"]


def test_rejects_a_malformed_business_id():
    body = ("business_id,business_name,industry,employee_count,facility_area_sqft,"
            "operating_days_per_month,operating_hours_per_day,business_size\n"
            "9001,Some Works,Manufacturing,10,1000,25,8,Small\n")
    result = client.post("/api/import", files=[upload("business_profiles.csv", body)]).json()["results"][0]
    assert result["rows_imported"] == 0
    assert "Invalid business_id" in result["validation_errors"][0]["message"]


def test_rejects_rows_whose_business_was_never_imported():
    body = _energy_csv(["B999,2026-01,1000,1000,0,0,0,10,100,10,0"])
    result = client.post("/api/import", files=[upload("energy_data.csv", body)]).json()["results"][0]
    assert result["rows_imported"] == 0
    assert "No business profiles are stored yet" in result["validation_errors"][0]["message"]


def test_rejects_duplicate_records_inside_one_file():
    client.post("/api/import", files=[upload("business_profiles.csv", pack_csv("business_profiles"))])
    body = _energy_csv([
        "B001,2026-01,1000,1000,0,0,0,10,100,10,0",
        "B001,2026-01,2000,2000,0,0,0,10,100,10,0",
    ])
    result = client.post("/api/import", files=[upload("energy_data.csv", body)]).json()["results"][0]
    assert result["rows_imported"] == 1
    assert result["rows_rejected"] == 1
    assert "Duplicate record" in result["validation_errors"][0]["message"]


def test_reports_a_missing_required_column():
    body = "business_id,month,grid_kwh\nB001,2026-01,10\n"
    result = client.post("/api/import", files=[upload("energy_data.csv", body)]).json()["results"][0]
    assert result["success"] is False
    assert "Unknown dataset type" in result["message"]


def test_rejects_an_invalid_date():
    body = ("assessment_id,business_id,assessment_date,energy_score,water_score,waste_score,"
            "emissions_score,mobility_score,operations_score,overall_climate_score\n"
            "CA-1,B001,not-a-date,10,10,10,10,10,10,10\n")
    client.post("/api/import", files=[upload("business_profiles.csv", pack_csv("business_profiles"))])
    result = client.post("/api/import", files=[upload("climate_assessments.csv", body)]).json()["results"][0]
    assert result["rows_imported"] == 0
    assert "must be a valid date" in result["validation_errors"][0]["message"]


# ---------------------------------------------------------------------------
# Importing the real test data pack
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not HAS_PACK, reason="test_data_pack/csv is not present")
def test_imports_the_whole_test_data_pack():
    files = [
        upload(f"{name}.csv", pack_csv(name))
        for name in (
            "business_profiles", "climate_assessments", "resource_consumption", "energy_data",
            "water_data", "waste_data", "emissions_data", "mobility_data", "operations_materials",
            "historical_climate_data", "green_solutions", "solution_recommendations", "scenarios",
            "transformation_plans", "before_after_impact", "gemini_ai_test_questions",
            "gemini_expected_behaviors",
        )
    ]
    result = client.post("/api/import", files=files).json()
    assert result["success"] is True, [r["message"] for r in result["results"] if not r["success"]]
    assert result["datasets_imported"] == 17
    assert result["datasets_failed"] == 0
    assert result["rows_rejected"] == 0
    assert result["rows_imported"] == 799
    assert "17 dataset(s) imported successfully" in result["message"]
    assert result["active_business"] == "B001"

    by_type = {r["dataset_type"]: r for r in result["results"]}
    assert by_type["business_profiles"]["rows_imported"] == 5
    assert by_type["energy_data"]["rows_imported"] == 60
    assert by_type["water_data"]["rows_imported"] == 60
    assert by_type["waste_data"]["rows_imported"] == 60
    assert by_type["emissions_data"]["rows_imported"] == 60
    assert by_type["mobility_data"]["rows_imported"] == 60
    assert by_type["operations_materials"]["rows_imported"] == 60
    assert by_type["historical_climate_data"]["rows_imported"] == 120
    assert by_type["before_after_impact"]["rows_imported"] == 30

    # Everything is linked to the same business ids.
    assert set(by_type["energy_data"]["business_ids"]) == {"B001", "B002", "B003", "B004", "B005"}
    stored = client.get("/api/import").json()
    assert stored["collections"]["energy_data"] == 60
    assert stored["collections"]["historical_climate_data"] == 120
    assert [b["business_id"] for b in stored["businesses"]] == ["B001", "B002", "B003", "B004", "B005"]
    assert stored["active_business"]["name"] == "Sunrise Textile Industries Pvt. Ltd."
    assert stored["active_business"]["source"] == "imported"


@pytest.mark.skipif(not HAS_PACK, reason="test_data_pack/csv is not present")
def test_fingerprint_is_calculated_from_the_imported_data():
    """The engine recomputes the scores and reproduces the pack's expected values."""
    client.post("/api/import", files=[
        upload("business_profiles.csv", pack_csv("business_profiles")),
        upload("climate_assessments.csv", pack_csv("climate_assessments")),
        upload("energy_data.csv", pack_csv("energy_data")),
        upload("water_data.csv", pack_csv("water_data")),
        upload("waste_data.csv", pack_csv("waste_data")),
        upload("emissions_data.csv", pack_csv("emissions_data")),
        upload("mobility_data.csv", pack_csv("mobility_data")),
        upload("operations_materials.csv", pack_csv("operations_materials")),
        upload("climate_assessments__assessment_api_payloads.csv",
               pack_csv("climate_assessments__assessment_api_payloads")),
    ])
    fingerprint = client.get("/api/climate-fingerprint").json()
    expected = expected_scores("B001")
    assert fingerprint["overallScore"] == pytest.approx(expected["overall"], abs=0.05)
    computed = {d["dimension"]: d["score"] for d in fingerprint["dimensions"]}
    for dimension, score in expected.items():
        if dimension == "overall":
            continue
        assert computed[dimension] == pytest.approx(score, abs=0.05), dimension
    # The profile in the sidebar comes from the import, not from a hardcoded demo.
    profile = client.get("/api/profile").json()
    assert profile["name"] == "Sunrise Textile Industries Pvt. Ltd."
    assert profile["industry"] == "Textile Manufacturing"
    assert profile["businessSize"] == "Medium"


@pytest.mark.skipif(not HAS_PACK, reason="test_data_pack/csv is not present")
def test_scores_are_derived_from_monthly_data_without_the_assessment_file():
    """With only the resource streams imported, the engine still scores the business."""
    client.post("/api/import", files=[
        upload("business_profiles.csv", pack_csv("business_profiles")),
        upload("energy_data.csv", pack_csv("energy_data")),
        upload("water_data.csv", pack_csv("water_data")),
        upload("waste_data.csv", pack_csv("waste_data")),
        upload("mobility_data.csv", pack_csv("mobility_data")),
        upload("resource_consumption.csv", pack_csv("resource_consumption")),
    ])
    assessment = client.get("/api/assessment").json()
    assert assessment["energy"]["monthlyElectricityKwh"] == pytest.approx(266531, rel=0.05)
    assert assessment["water"]["monthlyWaterLitres"] == pytest.approx(4803700, rel=0.05)
    assert assessment["derived_from_import"]["input_source"] == "derived_from_imported_monthly_data"
    fingerprint = client.get("/api/climate-fingerprint").json()
    assert fingerprint["overallScore"] is not None
    assert len(fingerprint["dimensions"]) == 6


@pytest.mark.skipif(not HAS_PACK, reason="test_data_pack/csv is not present")
def test_scores_shipped_in_the_file_are_not_used_as_the_application_score():
    """A file claiming a perfect score must not overwrite the engine's calculation."""
    body = ("assessment_id,business_id,assessment_date,energy_score,water_score,waste_score,"
            "emissions_score,mobility_score,operations_score,overall_climate_score\n"
            "CA-FAKE,B001,2026-08-31,100,100,100,100,100,100,100\n")
    client.post("/api/import", files=[
        upload("business_profiles.csv", pack_csv("business_profiles")),
        upload("energy_data.csv", pack_csv("energy_data")),
        upload("water_data.csv", pack_csv("water_data")),
        upload("waste_data.csv", pack_csv("waste_data")),
        upload("climate_assessments.csv", body),
    ])
    fingerprint = client.get("/api/climate-fingerprint").json()
    assert fingerprint["overallScore"] < 100
    stored = get_collection("climate_assessments").find_one({"business_id": "B001"})
    assert stored["overall_climate_score"] == 100  # the imported value is kept, but only as a reference
    assert stored["user_id"] is None  # it is not the document the app reads


@pytest.mark.skipif(not HAS_PACK, reason="test_data_pack/csv is not present")
def test_the_standalone_api_payload_file_is_attached_to_the_assessments():
    """The pack's ``climate_assessments__assessment_api_payloads.csv`` is not rejected."""
    result = client.post("/api/import", files=[
        upload("business_profiles.csv", pack_csv("business_profiles")),
        upload("climate_assessments__assessment_api_payloads.csv",
               pack_csv("climate_assessments__assessment_api_payloads")),
    ]).json()
    payload_result = result["results"][1]
    assert payload_result["dataset_type"] == "climate_assessments"
    assert payload_result["detection"]["payload_only"] is True
    assert payload_result["rows_imported"] == 5
    assert payload_result["success"] is True
    assert result["active_business"] == "B001"
    # The payload became the assessment input and the engine scored it.
    assessment = client.get("/api/assessment").json()
    assert assessment["energy"]["monthlyElectricityKwh"] == 266531
    assert assessment["derived_from_import"]["input_source"] == "imported_climate_assessments_payload"
    assert client.get("/api/climate-fingerprint").json()["overallScore"] == pytest.approx(
        expected_scores("B001")["overall"], abs=0.05)


# ---------------------------------------------------------------------------
# Re-import, history, business switching
# ---------------------------------------------------------------------------
def test_reimporting_the_same_file_updates_instead_of_duplicating():
    files = [upload("business_profiles.csv", pack_csv("business_profiles"))]
    client.post("/api/import", files=files)
    assert get_collection("business_profiles").count_documents({}) == 5
    second = client.post("/api/import", files=files).json()
    # Still exactly 5 documents. B001 is re-inserted because activating it moved the
    # imported row onto the application's profile document (and then removed it).
    assert get_collection("business_profiles").count_documents({}) == 5
    assert second["results"][0]["rows_imported"] == 5
    assert second["results"][0]["rows_updated"] == 4
    assert second["results"][0]["rows_inserted"] == 1


def test_import_history_is_recorded():
    client.post("/api/import", files=[upload("business_profiles.csv", pack_csv("business_profiles"))])
    client.post("/api/import", files=[upload("notes.txt", "x,y\n1,2\n")])
    imports = client.get("/api/import/history").json()["imports"]
    assert len(imports) == 2
    assert imports[0]["filename"] == "notes.txt" and imports[0]["success"] is False
    assert imports[1]["filename"] == "business_profiles.csv"
    assert imports[1]["dataset_label"] == "Business Profiles"
    assert imports[1]["rows_imported"] == 5
    assert imports[1]["started_at"] and imports[1]["completed_at"]


@pytest.mark.skipif(not HAS_PACK, reason="test_data_pack/csv is not present")
def test_switching_the_active_business_recalculates_everything():
    client.post("/api/import", files=[
        upload("business_profiles.csv", pack_csv("business_profiles")),
        upload("climate_assessments.csv", pack_csv("climate_assessments")),
        upload("climate_assessments__assessment_api_payloads.csv",
               pack_csv("climate_assessments__assessment_api_payloads")),
        upload("energy_data.csv", pack_csv("energy_data")),
        upload("water_data.csv", pack_csv("water_data")),
        upload("waste_data.csv", pack_csv("waste_data")),
    ])
    assert client.get("/api/profile").json()["name"] == "Sunrise Textile Industries Pvt. Ltd."
    assert client.get("/api/climate-fingerprint").json()["overallScore"] == pytest.approx(
        expected_scores("B001")["overall"], abs=0.05)
    switched = client.post("/api/import/businesses/B003/activate").json()
    assert switched["business_id"] == "B003"
    assert client.get("/api/profile").json()["name"] == "FreshHarvest Food Processing Pvt. Ltd."
    expected = expected_scores("B003")
    fingerprint = client.get("/api/climate-fingerprint").json()
    assert fingerprint["overallScore"] == pytest.approx(expected["overall"], abs=0.05)
    assert client.post("/api/import/businesses/B999/activate").status_code == 404


# ---------------------------------------------------------------------------
# Gemini grounding & reset
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not HAS_PACK, reason="test_data_pack/csv is not present")
def test_gemini_context_uses_the_imported_history():
    from app.services.ai_insight_service import build_context

    client.post("/api/import", files=[
        upload("business_profiles.csv", pack_csv("business_profiles")),
        upload("climate_assessments.csv", pack_csv("climate_assessments")),
        upload("climate_assessments__assessment_api_payloads.csv",
               pack_csv("climate_assessments__assessment_api_payloads")),
        upload("historical_climate_data.csv", pack_csv("historical_climate_data")),
    ])
    context = build_context()
    history = context["history"]
    assert history["resource_series_source"] == "imported_historical_climate_data"
    assert history["months_of_history"] == 24
    assert history["resource_changes"]["available"] is True
    assert history["last_12_months"]["available"] is True
    # 24 months for the ACTIVE business (the pack holds 24 x 5 businesses).
    assert history["imported_datasets"]["historical_climate_data"] == 24
    # Real imported values, not invented ones.
    first = history["resource_series"][0]
    assert first["recorded_at"] == "2024-09"
    assert first["energy_kwh_per_month"] == pytest.approx(276942)
    assert context["business_profile"]["name"] == "Sunrise Textile Industries Pvt. Ltd."


def test_gemini_context_reports_no_data_on_an_empty_database():
    from app.services.ai_insight_service import build_context

    context = build_context()
    assert context["data_state"]["has_data"] is False
    assert context["business_profile"] is None
    assert context["history"]["has_history"] is False
    # Nothing that could be mistaken for a business metric is sent to Gemini.
    assert "calculated_analytics" not in context
    assert "climate_fingerprint" not in context


def test_gemini_context_still_reports_no_data_with_a_profile_but_no_assessment():
    from app.services.ai_insight_service import build_context

    client.post("/api/import", files=[upload("business_profiles.csv", pack_csv("business_profiles"))])
    context = build_context()
    assert context["data_state"]["has_data"] is False
    assert context["data_state"]["has_business_profile"] is True
    assert context["data_state"]["has_climate_assessment"] is False
    assert "calculated_analytics" not in context


def test_reset_clears_imported_data_too():
    client.post("/api/import", files=[
        upload("business_profiles.csv", pack_csv("business_profiles")),
        upload("energy_data.csv", pack_csv("energy_data")),
        upload("green_solutions.csv", pack_csv("green_solutions")),
    ])
    assert get_collection("energy_data").count_documents({}) == 60
    assert get_collection("business_profiles").count_documents({}) == 5

    result = client.post("/api/profile/reset").json()
    assert result["has_data"] is False
    assert get_collection("energy_data").count_documents({}) == 0
    assert get_collection("business_profiles").count_documents({}) == 0
    assert get_collection("data_imports").count_documents({}) == 0
    assert get_collection("green_solutions").count_documents({"data_origin": "import"}) == 0
    assert client.get("/api/profile").json() is None
    assert client.get("/api/assessment").json() is None
    assert client.get("/api/climate-fingerprint").json() is None
    assert client.get("/api/import").json()["businesses"] == []


# ---------------------------------------------------------------------------
# Service-level unit checks
# ---------------------------------------------------------------------------
def test_dataset_detection_uses_headers_over_filename():
    dataset, info = import_service.detect_dataset(
        "climate_assessments.csv", ["business_id", "month", "electricity_kwh", "grid_kwh", "peak_demand_kw"]
    )
    assert dataset.key == "energy_data"
    assert info["reason"] == "matched"


def test_xlsx_companion_sheet_is_read_as_the_assessment_payload():
    from app.services.import_service import collect_companion_payloads, DATASETS

    payload = {"energy": {"monthlyElectricityKwh": 1234}}
    tables = [
        ("climate_assessments", pd.DataFrame([{"assessment_id": "A", "business_id": "B001"}])),
        ("assessment_api_payloads", pd.DataFrame([
            {"business_id": "B001", "post_api_assessment_json": json.dumps(payload)},
        ])),
    ]
    payloads = collect_companion_payloads(tables, "climate_assessments", DATASETS["climate_assessments"])
    assert payloads["B001"] == payload
