"""
Regression tests for Excel workbook detection.

The generated files in ``test_data_pack/`` are the source of truth. These tests
must keep proving that ``business_profiles.xlsx`` is recognised as 5 valid rows
and that the JSON companion sheet is not imported as business rows.
"""
from __future__ import annotations

import io
from pathlib import Path

import pytest
from openpyxl import Workbook

from app.database.mongodb import get_collection
from tests.conftest import client

PACK = Path(__file__).resolve().parents[2] / "test_data_pack"
XLSX = {
    "business_profiles": 5,
    "climate_assessments": 5,
    "resource_consumption": 60,
    "emissions_data": 60,
    "mobility_data": 60,
    "waste_data": 60,
    "water_data": 60,
    "energy_data": 60,
    "operations_materials": 60,
    "green_solutions": 18,
    "solution_recommendations": 28,
    "scenarios": 35,
    "transformation_plans": 65,
    "before_after_impact": 30,
    "historical_climate_data": 120,
}


def upload(name: str, content: bytes):
    return ("files", (name, content, "application/octet-stream"))


def pack_xlsx(name: str) -> bytes:
    return (PACK / f"{name}.xlsx").read_bytes()


def pack_csv(name: str) -> bytes:
    return (PACK / "csv" / f"{name}.csv").read_bytes()


def workbook_bytes(sheets: dict) -> bytes:
    book = Workbook()
    first = True
    for title, rows in sheets.items():
        worksheet = book.active if first else book.create_sheet(title)
        worksheet.title = title
        first = False
        for row in rows:
            worksheet.append(row)
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


def test_xlsx_business_profile_detection_regression():
    """business_profiles.xlsx → dataset = business_profiles, rows = 5, valid = true."""
    response = client.post("/api/import/preview", files=[upload("business_profiles.xlsx", pack_xlsx("business_profiles"))])
    assert response.status_code == 200
    body = response.json()
    result = body["results"][0]
    assert result["filename"] == "business_profiles.xlsx"
    assert result["extension"] == ".xlsx"
    assert result["dataset"] == "business_profiles"
    assert result["dataset_type"] == "business_profiles"
    assert result["sheet"] == "business_profiles"
    assert result["rows"] == 5
    assert result["rows_received"] == 5
    assert result["status"] == "valid"
    assert result["validation"]["valid"] is True
    assert result["validation"]["accepted_rows"] == 5
    assert result["validation"]["rejected_rows"] == 0
    assert result["validation"]["errors"] == []
    assert result["business_ids"] == ["B001", "B002", "B003", "B004", "B005"]
    assert "business_id" in result["columns"]
    assert "business_name" in result["columns"]
    # The POST-ready JSON sheet is reported, not imported as business rows.
    roles = {sheet["name"]: sheet["role"] for sheet in result["available_sheets"]}
    assert roles["business_profiles"] == "data"
    assert roles["api_payload_sheet"] == "reference"
    assert get_collection("business_profiles").count_documents({}) == 0


def test_xlsx_multi_sheet_does_not_import_the_json_sheet_as_rows():
    client.post("/api/import", files=[upload("business_profiles.xlsx", pack_xlsx("business_profiles"))])
    assert get_collection("business_profiles").count_documents({}) == 5
    stored_ids = sorted(doc["business_id"] for doc in get_collection("business_profiles").find({}, {"business_id": 1}))
    assert stored_ids == ["B001", "B002", "B003", "B004", "B005"]
    # Five businesses, not ten (the JSON companion sheet must not become rows).
    assert get_collection("business_profiles").count_documents({"business_id": "B001"}) == 1


def test_csv_detection_matches_the_xlsx_dataset():
    response = client.post("/api/import/preview", files=[upload("business_profiles.csv", pack_csv("business_profiles"))])
    result = response.json()["results"][0]
    assert result["dataset"] == "business_profiles"
    assert result["rows"] == 5
    assert result["validation"]["valid"] is True
    assert result["extension"] == ".csv"


def test_hyphenated_and_spaced_filenames_still_detect_from_headers():
    content = pack_xlsx("business_profiles")
    for name in ("Business Profiles.xlsx", "business-profiles.xlsx", "profiles.xlsx"):
        result = client.post("/api/import/preview", files=[upload(name, content)]).json()["results"][0]
        assert result["dataset"] == "business_profiles", name
        assert result["rows"] == 5
        assert result["validation"]["valid"] is True


def test_unknown_file_returns_diagnostics():
    content = workbook_bytes({"Notes": [["foo", "bar", "baz"], [1, 2, 3]]})
    result = client.post("/api/import/preview", files=[upload("notes.xlsx", content)]).json()["results"][0]
    assert result["success"] is False
    assert result["dataset"] is None
    assert result["rows"] == 0
    assert result["error_code"] == "unknown_dataset"
    assert result["status"] == "unrecognized"
    assert "Unknown dataset type" in result["message"]
    assert result["detected_columns"]
    assert result["available_sheets"][0]["name"] == "Notes"
    assert get_collection("business_profiles").count_documents({}) == 0


def test_empty_workbook():
    content = workbook_bytes({"Sheet1": []})
    result = client.post("/api/import/preview", files=[upload("empty.xlsx", content)]).json()["results"][0]
    assert result["success"] is False
    assert result["dataset"] is None
    assert result["rows"] == 0
    assert result["error_code"] == "empty_workbook"
    assert result["available_sheets"]


def test_invalid_headers_are_not_recognised():
    content = workbook_bytes({"Data": [["not_a_column", "also_wrong"], ["x", "y"]]})
    result = client.post("/api/import/preview", files=[upload("business_profiles.xlsx", content)]).json()["results"][0]
    assert result["dataset"] is None
    assert result["rows"] == 0
    assert result["validation"]["valid"] is False
    assert result["error_code"] == "unknown_dataset"
    # Filename alone must never be enough.
    assert "Unknown dataset type" in result["message"]


def test_valid_workbook_persists_all_five_businesses_without_overwriting():
    response = client.post("/api/import", files=[upload("business_profiles.xlsx", pack_xlsx("business_profiles"))])
    body = response.json()
    assert body["success"] is True
    assert body["results"][0]["status"] == "imported"
    assert body["results"][0]["rows_imported"] == 5
    assert body["active_business"] == "B001"
    profile = client.get("/api/profile").json()
    assert profile["name"] == "Sunrise Textile Industries Pvt. Ltd."
    assert profile["business_id"] == "B001"
    ids = [item["business_id"] for item in client.get("/api/import/businesses").json()["businesses"]]
    assert ids == ["B001", "B002", "B003", "B004", "B005"]


def test_multiple_xlsx_files_and_partial_failure():
    bad = workbook_bytes({"Notes": [["foo", "bar"], [1, 2]]})
    response = client.post("/api/import", files=[
        upload("notes.xlsx", bad),
        upload("business_profiles.xlsx", pack_xlsx("business_profiles")),
        upload("green_solutions.xlsx", pack_xlsx("green_solutions")),
    ])
    body = response.json()
    by_name = {item["filename"]: item for item in body["results"]}
    assert by_name["notes.xlsx"]["success"] is False
    assert by_name["notes.xlsx"]["dataset"] is None
    assert by_name["business_profiles.xlsx"]["success"] is True
    assert by_name["business_profiles.xlsx"]["rows_imported"] == 5
    assert by_name["green_solutions.xlsx"]["success"] is True
    assert by_name["green_solutions.xlsx"]["rows_imported"] == 18
    # The failed file did not roll back the valid ones.
    assert get_collection("business_profiles").count_documents({}) == 5
    assert body["datasets_imported"] == 2
    assert body["datasets_failed"] == 1


def test_duplicate_business_id_is_rejected():
    content = workbook_bytes({"business_profiles": [
        ["business_id", "business_name", "industry", "employee_count", "facility_area_sqft",
         "operating_days_per_month", "operating_hours_per_day", "business_size"],
        ["B001", "First Works", "Textile", 10, 1000, 26, 8, "Small"],
        ["B001", "Duplicate Works", "Textile", 12, 1100, 26, 8, "Small"],
    ]})
    result = client.post("/api/import", files=[upload("business_profiles.xlsx", content)]).json()["results"][0]
    assert result["rows_imported"] == 1
    assert result["rows_rejected"] == 1
    assert result["validation"]["valid"] is False
    assert result["error_code"] == "duplicate_record"
    assert "Duplicate record" in result["validation_errors"][0]["message"]
    assert get_collection("business_profiles").count_documents({"business_id": "B001"}) == 1


def test_unknown_business_id_is_rejected():
    client.post("/api/import", files=[upload("business_profiles.xlsx", pack_xlsx("business_profiles"))])
    content = workbook_bytes({"energy_data": [
        ["business_id", "month", "electricity_kwh"],
        ["B999", "2026-01", 1000],
    ]})
    result = client.post("/api/import/preview", files=[upload("energy_data.xlsx", content)]).json()["results"][0]
    assert result["dataset"] == "energy_data"
    assert result["rows"] == 1
    assert result["validation"]["valid"] is False
    assert result["error_code"] == "unknown_business_id"
    assert "B999" in result["validation_errors"][0]["message"]
    assert get_collection("energy_data").count_documents({}) == 0


def test_empty_database_stays_empty_until_a_real_import():
    status = client.get("/api/import").json()
    assert status["businesses"] == []
    assert status["active_business"] is None
    assert client.get("/api/profile").json() is None
    client.post("/api/import/preview", files=[upload("business_profiles.xlsx", pack_xlsx("business_profiles"))])
    assert client.get("/api/profile").json() is None
    assert get_collection("business_profiles").count_documents({}) == 0


def test_all_generated_xlsx_files_are_recognised_and_persisted():
    uploads = [upload(f"{name}.xlsx", pack_xlsx(name)) for name in XLSX]
    preview = client.post("/api/import/preview", files=uploads).json()
    by_name = {item["filename"]: item for item in preview["results"]}
    assert preview["needs_attention"] == 0
    for name, rows in XLSX.items():
        item = by_name[f"{name}.xlsx"]
        assert item["dataset"] == name, item
        assert item["rows"] == rows, item
        assert item["validation"]["valid"] is True, item["message"]
        assert item["status"] == "valid"

    imported = client.post("/api/import", files=uploads).json()
    assert imported["success"] is True, [item["message"] for item in imported["results"] if not item["success"]]
    assert imported["datasets_failed"] == 0
    assert imported["rows_imported"] == sum(XLSX.values())
    stored = {item["dataset"]: item["rows_imported"] for item in imported["results"]}
    assert stored == XLSX
    assert get_collection("business_profiles").count_documents({}) == 5
    assert get_collection("energy_data").count_documents({}) == 60
    assert get_collection("historical_climate_data").count_documents({}) == 120
    assert get_collection("climate_assessments").count_documents({"business_id": {"$in": list("B00" + str(i) for i in range(1, 6))}}) == 5
    profile = client.get("/api/profile").json()
    assert profile["name"] == "Sunrise Textile Industries Pvt. Ltd."
    assert "ABC Textile" not in profile["name"]


def test_csv_equivalents_detect_the_same_datasets():
    uploads = [upload(f"{name}.csv", pack_csv(name)) for name in XLSX]
    preview = client.post("/api/import/preview", files=uploads).json()
    by_name = {item["filename"]: item for item in preview["results"]}
    for name, rows in XLSX.items():
        item = by_name[f"{name}.csv"]
        assert item["dataset"] == name, item.get("message")
        assert item["rows"] == rows, item
        assert item["validation"]["valid"] is True, item["message"]


def test_switching_the_active_business_does_not_overwrite_the_others():
    client.post("/api/import", files=[
        upload("business_profiles.xlsx", pack_xlsx("business_profiles")),
        upload("climate_assessments.xlsx", pack_xlsx("climate_assessments")),
    ])
    switched = client.post("/api/import/businesses/B003/activate")
    assert switched.status_code == 200
    assert client.get("/api/profile").json()["name"] == "FreshHarvest Food Processing Pvt. Ltd."
    ids = sorted(doc["business_id"] for doc in get_collection("business_profiles").find({}, {"business_id": 1}))
    assert ids == ["B001", "B002", "B003", "B004", "B005"]
    b001 = get_collection("business_profiles").find_one({"business_id": "B001"})
    assert b001["business_name"] == "Sunrise Textile Industries Pvt. Ltd."
    assert b001["user_id"] is None


def test_climate_assessment_workbook_uses_the_data_sheet_not_the_payload_sheet():
    result = client.post(
        "/api/import/preview",
        files=[
            upload("business_profiles.xlsx", pack_xlsx("business_profiles")),
            upload("climate_assessments.xlsx", pack_xlsx("climate_assessments")),
        ],
    ).json()["results"][1]
    assert result["dataset"] == "climate_assessments"
    assert result["sheet"] == "climate_assessments"
    assert result["rows"] == 5
    assert result["validation"]["valid"] is True
    sheet_names = [sheet["name"] for sheet in result["available_sheets"]]
    assert "assessment_api_payloads" in sheet_names
    assert "post_api_assessment_json" not in result["columns"]
