"""
Data Import routes - Excel / CSV uploads.

    GET    /api/import                 import status: datasets, formats, stored counts, active business
    POST   /api/import                 upload one or more files, validate + store them
    POST   /api/import/preview         parse + detect + validate WITHOUT storing anything
    GET    /api/import/history         recent imports (filename, dataset, rows, status, timestamp)
    GET    /api/import/datasets        the supported dataset schemas (columns the UI can show)
    GET    /api/import/businesses      imported businesses with per-dataset row counts
    POST   /api/import/businesses/{business_id}/activate   serve a different imported business

The upload is parsed, validated and stored by the backend. Files are never sent to
Gemini; the AI layer only reads what the import stored.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.services import import_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Data Import"])


async def _read_uploads(files: List[UploadFile]) -> List[Tuple[str, bytes]]:
    if not files:
        raise HTTPException(status_code=400, detail="No file was uploaded. Attach at least one .xlsx, .xls or .csv file.")
    uploads: List[Tuple[str, bytes]] = []
    for upload in files:
        name = upload.filename or "unnamed"
        try:
            content = await upload.read()
        except Exception as exc:  # pragma: no cover - defensive
            raise HTTPException(status_code=400, detail=f"Could not read '{name}' ({exc}).") from None
        if not content:
            raise HTTPException(status_code=400, detail=f"'{name}' is empty.")
        uploads.append((name, content))
    return uploads


@router.get("", summary="Data import status (datasets, formats, stored counts, active business)")
async def get_import_status():
    try:
        return import_service.import_status()
    except Exception as exc:
        logger.error(f"Import status error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not read the import status.")


@router.get("/", include_in_schema=False)
async def get_import_status_slash():
    return await get_import_status()


@router.get("/datasets", summary="Supported dataset types and their expected columns")
async def get_datasets():
    return {
        "supported_formats": list(import_service.SUPPORTED_EXTENSIONS),
        "max_file_mb": import_service.MAX_FILE_BYTES // 1048576,
        "recommended_import_order": list(import_service.IMPORT_ORDER),
        "datasets": [import_service.DATASETS[key].describe() for key in import_service.IMPORT_ORDER],
    }


@router.get("/history", summary="Recent imports (filename, dataset, rows, status, imported at)")
async def get_history(limit: int = Query(25, ge=1, le=200)):
    return {"imports": import_service.import_history(limit=limit)}


@router.get("/businesses", summary="Imported businesses with per-dataset row counts")
async def get_businesses():
    return {
        "active_business_id": import_service.get_active_business_id(),
        "businesses": import_service.list_businesses(),
    }


@router.post("/businesses/{business_id}/activate", summary="Serve a different imported business")
async def activate(business_id: str):
    try:
        return import_service.activate_business(business_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"Activate business error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not activate that business.")


@router.post("/sync-assessment", summary="Re-derive the Climate Assessment from the imported data")
async def sync_assessment():
    """Recalculate the Climate Assessment + Fingerprint from what is stored.

    Used by the Climate Fingerprint page's "Run Climate Assessment" action and by the
    Data Import page after an upload. Scores come from the deterministic engine.
    """
    try:
        return import_service.sync_assessment_from_imports()
    except Exception as exc:
        logger.error(f"Assessment sync error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not recalculate the assessment.")


@router.post("/preview", summary="Parse, detect and validate uploads WITHOUT storing them")
async def preview_import(files: List[UploadFile] = File(..., description="One or more .xlsx / .xls / .csv files")):
    """Same detection and validation as the real import, but nothing is written.

    Lets the UI show "detected dataset / rows / validation status" per file before
    the user confirms the import.
    """
    try:
        uploads = await _read_uploads(files)
        # Ids from business_profiles in this same request count as known, so the
        # other files in the batch can be validated before anything is stored.
        known_ids = import_service.provisional_business_ids(uploads)
        results: List[Dict[str, Any]] = []
        for name, content in uploads:
            summary = import_service.import_table(
                name, content, persist=False, extra_business_ids=known_ids,
            )
            summary["stored"] = False
            # Preview never stores, so a fully valid file is "valid", not "imported".
            if summary.get("validation", {}).get("valid"):
                summary["status"] = "valid"
            results.append(summary)
        return {
            "files_received": len(results),
            "ready_to_import": sum(1 for r in results if r["success"]),
            "needs_attention": sum(1 for r in results if not r["success"]),
            "rows_received": sum(r["rows_received"] for r in results),
            "rows_rejected": sum(r["rows_rejected"] for r in results),
            "results": results,
        }
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(f"Import preview failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not preview the upload.")


@router.post("", summary="Import uploaded Excel/CSV files into MongoDB")
async def post_import(files: List[UploadFile] = File(..., description="One or more .xlsx / .xls / .csv files")):
    """Validate and store the uploaded datasets, then refresh the derived data.

    Response:
        {
          "success": true,
          "datasets_imported": 9,
          "rows_imported": 428,
          "results": [ {"success": true, "dataset_type": "energy_data", "filename": "...",
                        "rows_received": 60, "rows_imported": 60, "rows_rejected": 0,
                        "validation_errors": []}, ... ],
          "assessment": {...}, "active_business": "B001"
        }

    Rows that fail validation are never silently ignored: each one is reported in
    ``validation_errors`` with its spreadsheet row number.
    """
    try:
        uploads = await _read_uploads(files)
        return import_service.import_files(uploads)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(f"Import failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Import failed unexpectedly (see server log).")


@router.post("/", include_in_schema=False)
async def post_import_slash(files: List[UploadFile] = File(...)):
    return await post_import(files)
