#!/usr/bin/env python3
"""Profile a local TCIA clinical XLSX without emitting patient-level values."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import sys
from collections import Counter
from datetime import date, datetime, time
from pathlib import Path
from typing import Any


def _safe_sheet_name(name: str, index: int) -> str:
    # Patient-specific worksheet names are not needed in a public aggregate report.
    if re.search(r"(?i)(patient|subject|case|ccth)[ _-]*[a-z]*\d+", name):
        return f"Sheet {index} (identifier-like name redacted)"
    return name


def _cell_kind(cell: Any) -> str:
    if cell.data_type == "f":
        return "formula"
    value = cell.value
    if value is None or (isinstance(value, str) and not value.strip()):
        return "blank"
    if cell.is_date or isinstance(value, (date, datetime, time)):
        return "date/time"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "text"
    return "other"


def _field_role(name: str) -> str:
    lowered = name.casefold()
    if re.search(r"(patient|subject|participant).*(id|no|number)|(case).*(name|id|no|number)|(^|\b)(id|mrn)(\b|$)", lowered):
        return "candidate identifier field (values not emitted)"
    if re.search(r"response|outcome|pcr|survival|recurrence|progression|metast|death|follow.?up|event", lowered):
        return "candidate endpoint/follow-up field (requires source/clinical validation)"
    if re.search(r"date|time|day|month|year", lowered):
        return "date/time-like field by name"
    return "meaning follows source column label; no clinical interpretation inferred"


def profile_xlsx(path: Path) -> dict[str, Any]:
    try:
        import openpyxl
    except ImportError as exc:
        raise RuntimeError("openpyxl is required for read-only XLSX profiling") from exc

    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    file_bytes = path.read_bytes()
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=False)
    sheets: list[dict[str, Any]] = []
    try:
        for sheet_index, ws in enumerate(workbook.worksheets, start=1):
            sample_rows = list(ws.iter_rows(min_row=1, max_row=min(ws.max_row or 1, 15), values_only=False))
            # Pick the early row that looks most like a header, without emitting any row values.
            candidates: list[tuple[int, int, int]] = []
            for row_index, row in enumerate(sample_rows, start=1):
                nonblank = [cell for cell in row if _cell_kind(cell) != "blank"]
                text_cells = [cell for cell in nonblank if isinstance(cell.value, str) and cell.data_type != "f"]
                if len(text_cells) >= 2:
                    candidates.append((len(text_cells), len(nonblank), row_index))
            header_row = max(candidates)[2] if candidates else 1
            header_cells = sample_rows[header_row - 1] if sample_rows else []
            raw_headers = [cell.value if isinstance(cell.value, str) else None for cell in header_cells]
            worksheet_max_col = ws.max_column or len(raw_headers)
            named_header_count = sum(bool(value and value.strip()) for value in raw_headers)
            if not named_header_count:
                sheets.append({
                    "sheet": _safe_sheet_name(ws.title, sheet_index),
                    "state": "no textual header detected in first 15 rows",
                    "declared_dimension": ws.calculate_dimension(),
                    "worksheet_max_column": worksheet_max_col,
                })
                continue
            headers: list[str] = []
            for col in range(worksheet_max_col):
                value = raw_headers[col] if col < len(raw_headers) else None
                headers.append(re.sub(r"\s+", " ", value).strip() if value and value.strip() else f"Column {col + 1} (blank header)")

            blank_counts = [0] * worksheet_max_col
            sentinel_counts = [Counter() for _ in range(worksheet_max_col)]
            type_counts = [Counter() for _ in range(worksheet_max_col)]
            row_shape_counts: Counter[int] = Counter()
            identifier_distinct: dict[int, set[str]] = {}
            identifier_rows: dict[int, int] = {}
            for col, header in enumerate(headers):
                if _field_role(header).startswith("candidate identifier"):
                    identifier_distinct[col] = set()
                    identifier_rows[col] = 0

            data_rows = 0
            rows_with_candidate_identifier = 0
            rows_without_candidate_identifier = 0
            for row in ws.iter_rows(min_row=header_row + 1, max_col=worksheet_max_col, values_only=False):
                nonblank_count = sum(_cell_kind(cell) != "blank" for cell in row)
                if not nonblank_count:
                    continue
                data_rows += 1
                row_shape_counts[nonblank_count] += 1
                has_identifier = any(col in identifier_distinct and _cell_kind(row[col]) != "blank" for col in range(worksheet_max_col))
                if has_identifier:
                    rows_with_candidate_identifier += 1
                else:
                    rows_without_candidate_identifier += 1
                for col, cell in enumerate(row):
                    kind = _cell_kind(cell)
                    if kind == "blank":
                        blank_counts[col] += 1
                        continue
                    type_counts[col][kind] += 1
                    value = cell.value
                    if isinstance(value, str):
                        sentinel = value.strip().casefold()
                        if sentinel in {"na", "n/a", "unknown", "not available", "not reported", "not applicable"}:
                            sentinel_counts[col][sentinel] += 1
                    if col in identifier_distinct:
                        identifier_rows[col] += 1
                        identifier_distinct[col].add(str(value).strip().casefold())

            fields = []
            for col, header in enumerate(headers):
                has_header = col < len(raw_headers) and bool(raw_headers[col] and raw_headers[col].strip())
                if not has_header and not type_counts[col]:
                    continue
                field = {
                    "name": header,
                    "role_hint": _field_role(header),
                    "nonblank_count": sum(type_counts[col].values()),
                    "observed_types": dict(sorted(type_counts[col].items())),
                    "blank_count": blank_counts[col],
                    "blank_rate": (blank_counts[col] / data_rows) if data_rows else None,
                    "sentinel_counts": dict(sorted(sentinel_counts[col].items())),
                }
                if col in identifier_distinct:
                    field["candidate_key_profile"] = {
                        "nonblank_values": identifier_rows[col],
                        "distinct_values": len(identifier_distinct[col]),
                        "duplicate_nonblank_rows": identifier_rows[col] - len(identifier_distinct[col]),
                    }
                fields.append(field)
            sheets.append({
                "sheet": _safe_sheet_name(ws.title, sheet_index),
                "state": "profiled",
                "declared_dimension": ws.calculate_dimension(),
                "worksheet_max_row": ws.max_row,
                "worksheet_max_column": worksheet_max_col,
                "header_row_1_based": header_row,
                "column_count": named_header_count,
                "unlabeled_columns_with_data": [col + 1 for col in range(worksheet_max_col) if (col >= len(raw_headers) or not raw_headers[col] or not raw_headers[col].strip()) and type_counts[col]],
                "record_count": data_rows,
                "nonblank_cells_per_record_histogram": {str(k): v for k, v in sorted(row_shape_counts.items())},
                "rows_with_candidate_identifier": rows_with_candidate_identifier,
                "rows_without_candidate_identifier": rows_without_candidate_identifier,
                "fields": fields,
                "row_values_emitted": False,
            })
    finally:
        workbook.close()

    return {
        "source_filename": path.name,
        "file_size_bytes": len(file_bytes),
        "sha256": hashlib.sha256(file_bytes).hexdigest(),
        "inspection": "openpyxl read_only=True, data_only=False; no workbook writes",
        "privacy": "No patient-level cell values, samples, or identifier values are emitted.",
        "runtime": {"python": sys.version.split()[0], "platform": platform.platform(), "openpyxl": openpyxl.__version__},
        "sheets": sheets,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xlsx", type=Path, help="local clinical workbook path; keep it outside Git")
    parser.add_argument("--output", type=Path, help="optional path for aggregate JSON output")
    args = parser.parse_args()
    result = profile_xlsx(args.xlsx)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
