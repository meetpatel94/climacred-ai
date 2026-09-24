"""
Excel workbook inspection for the Data Import module.

XLSX files are opened with openpyxl and every worksheet is examined. The first
sheet is never assumed to be the dataset: empty sheets are skipped, JSON /
reference sheets are labelled so they are not imported as business rows, and
the header row is located by matching known columns rather than blindly using
row 1.
"""
from __future__ import annotations

import io
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd

_REFERENCE_NAME_RE = re.compile(
    r"(payload|reference|readme|documentation|instruction|manifest|notes|legend)",
    re.IGNORECASE,
)


class WorkbookParseError(ValueError):
    """The workbook could not be read. Carries a stable error_code for the API."""

    def __init__(self, message: str, *, error_code: str = "parse_error", **extra: Any) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.extra = extra


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    try:
        if value != value:  # NaN
            return True
    except Exception:
        pass
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def _header_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _canonical(value: Any, known: Dict[str, str], aliases: Dict[str, str]) -> str:
    text = _header_text(value)
    if not text or text.lower().startswith("unnamed"):
        return ""
    if text in known.values():
        return text
    lowered = text.lower().replace(" ", "_").replace("-", "_")
    if lowered in known:
        return known[lowered]
    alias = aliases.get(lowered)
    return alias or text


def sheet_role(sheet_name: str, columns: Sequence[str]) -> str:
    """A JSON/reference sheet must not be treated as the tabular dataset."""
    lowered = [str(column).lower() for column in columns]
    jsonish = [column for column in lowered if "json" in column or column.endswith("payload") or "payload" in column]
    if jsonish and len(lowered) - len(jsonish) <= 2:
        return "reference"
    if _REFERENCE_NAME_RE.search(sheet_name or "") and not any(
        column in lowered
        for column in ("business_name", "electricity_kwh", "solution_name", "scenario_name", "metric", "question")
    ):
        return "reference"
    return "data"


def _find_header_index(rows: Sequence[Sequence[Any]], known: Dict[str, str], aliases: Dict[str, str]) -> int:
    best_index = 0
    best_hits = -1
    for index, row in enumerate(rows[:25]):
        hits = 0
        for cell in row:
            canon = _canonical(cell, known, aliases)
            if canon and canon.lower() in known:
                hits += 1
        if hits > best_hits:
            best_hits = hits
            best_index = index
        if hits >= 3:
            return index
    return best_index if best_hits >= 2 else 0


def frame_from_rows(
    rows: Sequence[Sequence[Any]],
    known: Dict[str, str],
    aliases: Dict[str, str],
) -> pd.DataFrame:
    matrix = [list(row) for row in rows]
    while matrix and all(_is_blank(cell) for cell in matrix[-1]):
        matrix.pop()
    if not matrix:
        return pd.DataFrame()
    header_index = _find_header_index(matrix, known, aliases)
    raw_headers = [_canonical(cell, known, aliases) for cell in matrix[header_index]]
    keep: List[int] = []
    headers: List[str] = []
    seen = set()
    for index, header in enumerate(raw_headers):
        if not header or header in seen:
            continue
        seen.add(header)
        headers.append(header)
        keep.append(index)
    if not headers:
        return pd.DataFrame()
    records: List[Dict[str, Any]] = []
    for raw in matrix[header_index + 1:]:
        if all(_is_blank(cell) for cell in raw):
            continue
        record: Dict[str, Any] = {}
        for header, index in zip(headers, keep):
            value = raw[index] if index < len(raw) else None
            record[header] = None if _is_blank(value) else value
        records.append(record)
    return pd.DataFrame.from_records(records, columns=headers)


def _report(name: str, frame: pd.DataFrame, *, state: str, role: str, empty: bool = False) -> Dict[str, Any]:
    columns = [] if frame is None else [str(column) for column in frame.columns]
    return {
        "name": name,
        "state": state,
        "empty": bool(empty or (not columns and (frame is None or frame.empty))),
        "rows": 0 if empty or frame is None else int(len(frame)),
        "columns": columns,
        "role": role,
    }


def read_xlsx(
    content: bytes,
    *,
    known_columns: Sequence[str],
    aliases: Optional[Dict[str, str]] = None,
) -> Tuple[List[Tuple[str, pd.DataFrame]], List[Dict[str, Any]]]:
    """Open an .xlsx workbook and return (tables, sheet reports) for every sheet.

    ``tables`` contains every non-empty sheet, including reference sheets, so the
    caller can both select the dataset and still read a companion JSON sheet.
    Empty sheets are reported and omitted from ``tables``.
    """
    try:
        import openpyxl
    except ImportError as exc:  # pragma: no cover - pinned in requirements.txt
        raise WorkbookParseError(
            "Could not read the Excel workbook because openpyxl is not installed. "
            "The file was not converted to CSV.",
            error_code="missing_excel_engine",
        ) from exc
    try:
        workbook = openpyxl.load_workbook(io.BytesIO(content), data_only=True, read_only=False)
    except Exception as exc:
        raise WorkbookParseError(
            f"Could not parse the Excel workbook ({type(exc).__name__}: {exc}).",
            error_code="parse_error",
        ) from None

    known = {column.lower(): column for column in known_columns if column}
    alias_map = dict(aliases or {})
    visible: List[Tuple[str, pd.DataFrame]] = []
    hidden: List[Tuple[str, pd.DataFrame]] = []
    reports: List[Dict[str, Any]] = []
    try:
        if not workbook.worksheets:
            raise WorkbookParseError("The workbook contains no sheets.", error_code="empty_workbook", available_sheets=[])
        for worksheet in workbook.worksheets:
            state = getattr(worksheet, "sheet_state", "visible") or "visible"
            matrix = [list(row) for row in worksheet.iter_rows(values_only=True)]
            if not any(not _is_blank(cell) for row in matrix for cell in row):
                reports.append(_report(worksheet.title, pd.DataFrame(), state=state, role="empty", empty=True))
                continue
            frame = frame_from_rows(matrix, known, alias_map)
            role = "hidden" if state != "visible" else sheet_role(worksheet.title, list(frame.columns))
            reports.append(_report(
                worksheet.title,
                frame,
                state=state,
                role=role,
                empty=frame.empty and len(frame.columns) == 0,
            ))
            if frame.empty and len(frame.columns) == 0:
                continue
            bucket = hidden if state != "visible" else visible
            bucket.append((str(worksheet.title), frame))
    finally:
        workbook.close()
    # A hidden sheet is only used when the workbook has no visible table at all.
    return (visible or hidden), reports
