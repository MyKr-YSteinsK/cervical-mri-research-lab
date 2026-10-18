#!/usr/bin/env python3
"""Build a private, file-level index and a de-identified CCTH inventory report.

The scanner reads filesystem metadata and selected DICOM header tags only. It
does not decode PixelData, read clinical tables, compute file-content hashes,
or write inside the source data tree. Exact paths and DICOM UIDs are written
only beneath the Git-ignored ``.local/dataset-index`` directory.
"""

from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import importlib.util
import json
import math
import os
import re
import stat
import sys
import time
import warnings
from pathlib import Path
from typing import Any


SCRIPT_VERSION = "1.0.0"
INDEX_SCHEMA_VERSION = "1.0.0"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_RELATIVE = Path(
    "data/raw/tcia/ccth_idc_v25_full/cc_tumor_heterogeneity"
)
DEFAULT_INDEX_RELATIVE = Path(".local/dataset-index")
DEFAULT_REPORT_RELATIVE = Path("docs/datasets/CCTH_DATASET_INDEX.md")
DEFAULT_SUMMARY_RELATIVE = Path("evidence/ccth_inventory_summary.json")
KNOWN_MODALITIES = ("MR", "CT", "PT", "REG", "RTSTRUCT")
IMAGE_MODALITIES = ("MR", "CT", "PT")
EXPECTED_CASES = tuple(
    [f"A{i:02d}" for i in range(1, 13)] + [f"B{i:02d}" for i in range(1, 12)]
)
REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)

# This fallback reuses the already present, ignored pydicom 3.0.2 package from
# the previous CMRL audit. It changes no environment and installs nothing.
_local_pydicom = REPO_ROOT / ".local" / "r0" / "cmrl05-pydicom"
if importlib.util.find_spec("pydicom") is None and (_local_pydicom / "pydicom").is_dir():
    sys.path.insert(0, str(_local_pydicom))

try:
    import pydicom
    from pydicom.tag import Tag
except ImportError as exc:  # pragma: no cover - environment-specific preflight
    raise SystemExit(
        "pydicom is unavailable; use an existing Python environment with pydicom."
    ) from exc


HEADER_TAGS = [
    Tag(value)
    for value in (
        "00080016",  # SOPClassUID
        "00080018",  # SOPInstanceUID
        "00080060",  # Modality
        "00180050",  # SliceThickness
        "00180088",  # SpacingBetweenSlices
        "0020000D",  # StudyInstanceUID
        "0020000E",  # SeriesInstanceUID
        "00200013",  # InstanceNumber
        "00200032",  # ImagePositionPatient
        "00200037",  # ImageOrientationPatient
        "00200052",  # FrameOfReferenceUID
        "00280008",  # NumberOfFrames
        "00280010",  # Rows
        "00280011",  # Columns
        "00280030",  # PixelSpacing
    )
]

FILE_FIELDS = [
    "record_index",
    "case_alias",
    "relative_path",
    "directory_depth",
    "file_name",
    "extension",
    "file_size_bytes",
    "header_status",
    "header_error_class",
    "modality",
    "sop_class_uid",
    "study_uid",
    "series_uid",
    "sop_instance_uid",
    "frame_of_reference_uid",
    "instance_number",
    "rows",
    "columns",
    "number_of_frames",
    "pixel_spacing",
    "image_orientation_patient",
    "image_position_patient",
    "slice_thickness_mm",
    "spacing_between_slices_mm",
    "transfer_syntax_uid",
    "study_directory_matches_study_uid",
    "series_directory_matches_series_uid",
    "series_directory_matches_modality_series_uid",
    "filename_matches_sop_instance_uid",
    "filename_has_uuid_stem_shape",
]

DIRECTORY_FIELDS = [
    "relative_path",
    "depth",
    "directory_kind",
    "direct_file_count",
    "direct_directory_count",
    "recursive_file_count",
    "direct_bytes",
    "recursive_bytes",
    "is_empty",
    "scan_error_class",
]

STUDY_FIELDS = [
    "case_alias",
    "study_uid",
    "study_relative_dir",
    "series_group_count",
    "file_count",
    "unique_sop_instance_count",
    "total_bytes",
    "modalities",
    "study_relative_dirs",
]

SERIES_FIELDS = [
    "case_alias",
    "study_uid",
    "series_uid",
    "series_relative_dir",
    "series_relative_dirs",
    "modalities",
    "file_count",
    "unique_sop_instance_count",
    "duplicate_sop_uid_group_count",
    "total_bytes",
    "header_error_count",
    "rows_unique_count",
    "columns_unique_count",
    "number_of_frames_values",
    "pixel_spacing_unique_count",
    "orientation_unique_count",
    "position_unique_count",
    "projected_slice_position_count",
    "projected_slice_position_min_mm",
    "projected_slice_position_max_mm",
    "slice_thickness_values_mm",
    "spacing_between_slices_values_mm",
    "directory_matches_series_uid",
    "directory_matches_modality_series_uid",
    "volume_candidate_status",
]

CASE_FIELDS = [
    "case_alias",
    "case_directory_name",
    "directory_file_count",
    "directory_bytes",
    "study_directory_count",
    "series_directory_count",
    "empty_series_directory_count",
    "header_study_count",
    "header_series_group_count",
    "header_files_with_sop_instance_uid",
    "modality_file_counts_json",
]


class AuditError(RuntimeError):
    """A sanitized reason that prevents unsafe or incomplete output."""


def _is_reparse(st: os.stat_result) -> bool:
    return stat.S_ISLNK(st.st_mode) or bool(
        int(getattr(st, "st_file_attributes", 0)) & REPARSE_POINT
    )


def _case_alias(directory_name: str) -> str:
    match = re.fullmatch(r"CCTH-([AB]\d{2})", directory_name, flags=re.IGNORECASE)
    return match.group(1).upper() if match else "UNMAPPED"


def _value_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (str, bytes)):
        return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value
    try:
        return "\\".join(str(item) for item in value)
    except TypeError:
        return str(value)


def _numeric_tuple(value: Any) -> tuple[float, ...] | None:
    if value is None or value == "":
        return None
    try:
        parts = value.split("\\") if isinstance(value, str) else list(value)
        numbers = tuple(float(item) for item in parts)
    except (TypeError, ValueError):
        try:
            numbers = (float(value),)
        except (TypeError, ValueError):
            return None
    if not numbers or not all(math.isfinite(number) for number in numbers):
        return None
    return numbers


def _number_text(value: Any) -> str:
    numbers = _numeric_tuple(value)
    if numbers is None:
        return ""
    return "\\".join(format(number, ".12g") for number in numbers)


def _integer_text(value: Any) -> str:
    if value is None or value == "":
        return ""
    try:
        return str(int(value))
    except (TypeError, ValueError):
        return ""


def _projected_position(position: Any, orientation: Any) -> float | None:
    point = _numeric_tuple(position)
    directions = _numeric_tuple(orientation)
    if point is None or directions is None or len(point) != 3 or len(directions) != 6:
        return None
    row = directions[:3]
    column = directions[3:]
    normal = (
        row[1] * column[2] - row[2] * column[1],
        row[2] * column[0] - row[0] * column[2],
        row[0] * column[1] - row[1] * column[0],
    )
    norm = math.sqrt(sum(component * component for component in normal))
    if not math.isfinite(norm) or norm == 0:
        return None
    return round(sum(point[i] * normal[i] / norm for i in range(3)), 5)


def _new_series_accumulator() -> dict[str, Any]:
    return {
        "file_count": 0,
        "total_bytes": 0,
        "modalities": collections.Counter(),
        "sop_counts": collections.Counter(),
        "header_error_count": 0,
        "rows": set(),
        "columns": set(),
        "frames": set(),
        "pixel_spacing": set(),
        "orientation": set(),
        "position": set(),
        "projected_position": set(),
        "slice_thickness": set(),
        "spacing_between_slices": set(),
        "series_directory_names": set(),
        "series_relative_dirs": set(),
    }


def _new_study_accumulator() -> dict[str, Any]:
    return {
        "file_count": 0,
        "total_bytes": 0,
        "modalities": collections.Counter(),
        "sop_uids": set(),
        "series_keys": set(),
        "study_relative_dirs": set(),
    }


def _new_case_accumulator() -> dict[str, Any]:
    return {
        "directory_file_count": 0,
        "directory_bytes": 0,
        "study_directories": 0,
        "series_directories": 0,
        "empty_series_directories": 0,
        "header_studies": set(),
        "header_series_groups": set(),
        "sop_files": 0,
        "modalities": collections.Counter(),
    }


def _csv_write(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _relative_posix(path: Path, root: Path) -> str:
    relative = path.relative_to(root)
    return "" if relative == Path(".") else relative.as_posix()


def _directory_kind(depth: int) -> str:
    return {0: "dataset_root", 1: "case", 2: "study", 3: "series"}.get(
        depth, "nested_or_unexpected"
    )


def _scan(root: Path, index_partial: Path) -> dict[str, Any]:
    directories: dict[str, dict[str, Any]] = {
        "": {
            "relative_path": "",
            "depth": 0,
            "directory_kind": "dataset_root",
            "direct_file_count": 0,
            "direct_directory_count": 0,
            "recursive_file_count": 0,
            "direct_bytes": 0,
            "recursive_bytes": 0,
            "scan_error_class": "",
            "children": [],
        }
    }
    children_by_parent: dict[str, list[str]] = collections.defaultdict(list)
    series_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    studies_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    cases_by_alias = {alias: _new_case_accumulator() for alias in EXPECTED_CASES}
    case_directory_names: dict[str, str] = {}
    extension_counts: collections.Counter[str] = collections.Counter()
    modality_files: collections.Counter[str] = collections.Counter()
    modality_bytes: collections.Counter[str] = collections.Counter()
    modality_sop_uids: dict[str, set[str]] = collections.defaultdict(set)
    modality_series_keys: dict[str, set[tuple[str, str, str]]] = collections.defaultdict(set)
    image_metadata_presence: dict[str, collections.Counter[str]] = collections.defaultdict(
        collections.Counter
    )
    header_errors: collections.Counter[str] = collections.Counter()
    basename_counts: collections.Counter[str] = collections.Counter()
    sop_seen: dict[str, tuple[str, str, str, int]] = {}
    duplicate_sop_uids: set[str] = set()
    duplicate_sop_conflict_uids: set[str] = set()
    duplicate_sop_size_conflict_uids: set[str] = set()
    study_uids: set[str] = set()
    series_uids: set[str] = set()
    frame_uids: set[str] = set()
    sop_uids: set[str] = set()
    counters: collections.Counter[str] = collections.Counter()
    expected_path_checks: collections.Counter[str] = collections.Counter()
    scanned_case_directories: set[str] = set()
    start_time = time.monotonic()
    file_rows = 0

    with index_partial.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FILE_FIELDS, extrasaction="ignore")
        writer.writeheader()
        stack = [root]
        while stack:
            current = stack.pop()
            current_rel = _relative_posix(current, root)
            try:
                with os.scandir(current) as iterator:
                    entries = sorted(iterator, key=lambda entry: entry.name.casefold())
            except OSError as exc:
                directories[current_rel]["scan_error_class"] = type(exc).__name__
                counters["directory_read_error_count"] += 1
                counters["filesystem_inventory_complete"] = 0
                continue

            child_directories: list[Path] = []
            for entry in entries:
                try:
                    item_stat = entry.stat(follow_symlinks=False)
                except OSError as exc:
                    counters["metadata_error_count"] += 1
                    counters["filesystem_inventory_complete"] = 0
                    counters["metadata_error_" + type(exc).__name__] += 1
                    continue

                if _is_reparse(item_stat):
                    counters["reparse_entry_count"] += 1
                    counters["filesystem_inventory_complete"] = 0
                    if stat.S_ISDIR(item_stat.st_mode):
                        counters["reparse_directory_not_followed_count"] += 1
                    else:
                        counters["reparse_file_not_followed_count"] += 1
                    continue

                entry_path = Path(entry.path)
                relative = _relative_posix(entry_path, root)
                parts = Path(relative).parts
                depth = len(parts)
                case_name = parts[0] if parts else ""
                alias = _case_alias(case_name) if case_name else "UNMAPPED"
                if alias in cases_by_alias and depth == 1:
                    scanned_case_directories.add(alias)
                    case_directory_names[alias] = case_name
                elif depth == 1:
                    counters["unexpected_top_level_directory_count"] += 1

                if stat.S_ISDIR(item_stat.st_mode):
                    directories[current_rel]["direct_directory_count"] += 1
                    directories[relative] = {
                        "relative_path": relative,
                        "depth": depth,
                        "directory_kind": _directory_kind(depth),
                        "direct_file_count": 0,
                        "direct_directory_count": 0,
                        "recursive_file_count": 0,
                        "direct_bytes": 0,
                        "recursive_bytes": 0,
                        "scan_error_class": "",
                        "children": [],
                    }
                    directories[current_rel]["children"].append(relative)
                    children_by_parent[current_rel].append(relative)
                    child_directories.append(entry_path)
                    if alias in cases_by_alias and depth == 2:
                        cases_by_alias[alias]["study_directories"] += 1
                    elif alias in cases_by_alias and depth == 3:
                        cases_by_alias[alias]["series_directories"] += 1
                    continue

                if not stat.S_ISREG(item_stat.st_mode):
                    counters["special_nonregular_entry_count"] += 1
                    continue

                size = int(item_stat.st_size)
                counters["file_count"] += 1
                counters["total_bytes"] += size
                counters["zero_byte_file_count"] += int(size == 0)
                counters["unreadable_access_flag_count"] += int(
                    not os.access(entry_path, os.R_OK)
                )
                directories[current_rel]["direct_file_count"] += 1
                directories[current_rel]["direct_bytes"] += size
                if alias in cases_by_alias:
                    cases_by_alias[alias]["directory_file_count"] += 1
                    cases_by_alias[alias]["directory_bytes"] += size
                else:
                    counters["unmapped_case_file_count"] += 1
                    counters["unmapped_case_file_bytes"] += size

                extension = entry_path.suffix.casefold() or "<none>"
                extension_counts[extension] += 1
                basename_counts[entry_path.name.casefold()] += 1
                counters["files_with_expected_four_components"] += int(depth == 4)

                row: dict[str, Any] = {
                    "record_index": file_rows + 1,
                    "case_alias": alias,
                    "relative_path": relative,
                    "directory_depth": depth - 1,
                    "file_name": entry_path.name,
                    "extension": extension,
                    "file_size_bytes": size,
                    "header_status": "HEADER_UNREADABLE",
                    "header_error_class": "",
                    "modality": "MISSING",
                    "sop_class_uid": "",
                    "study_uid": "",
                    "series_uid": "",
                    "sop_instance_uid": "",
                    "frame_of_reference_uid": "",
                    "instance_number": "",
                    "rows": "",
                    "columns": "",
                    "number_of_frames": "",
                    "pixel_spacing": "",
                    "image_orientation_patient": "",
                    "image_position_patient": "",
                    "slice_thickness_mm": "",
                    "spacing_between_slices_mm": "",
                    "transfer_syntax_uid": "",
                    "study_directory_matches_study_uid": "",
                    "series_directory_matches_series_uid": "",
                    "filename_matches_sop_instance_uid": "",
                }
                dataset: Any | None = None
                if size == 0:
                    row["header_status"] = "ZERO_BYTE_FILE"
                    counters["header_zero_byte_file_count"] += 1
                else:
                    try:
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore")
                            dataset = pydicom.dcmread(
                                str(entry_path),
                                stop_before_pixels=True,
                                force=False,
                                defer_size="1 MB",
                                specific_tags=HEADER_TAGS,
                            )
                        row["header_status"] = "PARSED"
                        counters["header_parsed_file_count"] += 1
                    except Exception as exc:  # retain only a class, never an error string/path
                        error_class = type(exc).__name__
                        row["header_error_class"] = error_class
                        header_errors[error_class] += 1
                        counters["header_error_file_count"] += 1

                if dataset is not None:
                    modality = _value_text(getattr(dataset, "Modality", "")).strip().upper()
                    modality = modality or "MISSING"
                    row["modality"] = modality
                    row["sop_class_uid"] = _value_text(getattr(dataset, "SOPClassUID", ""))
                    row["study_uid"] = _value_text(getattr(dataset, "StudyInstanceUID", ""))
                    row["series_uid"] = _value_text(getattr(dataset, "SeriesInstanceUID", ""))
                    row["sop_instance_uid"] = _value_text(getattr(dataset, "SOPInstanceUID", ""))
                    row["frame_of_reference_uid"] = _value_text(
                        getattr(dataset, "FrameOfReferenceUID", "")
                    )
                    row["instance_number"] = _integer_text(
                        getattr(dataset, "InstanceNumber", None)
                    )
                    row["rows"] = _integer_text(getattr(dataset, "Rows", None))
                    row["columns"] = _integer_text(getattr(dataset, "Columns", None))
                    row["number_of_frames"] = _integer_text(
                        getattr(dataset, "NumberOfFrames", None)
                    )
                    row["pixel_spacing"] = _number_text(getattr(dataset, "PixelSpacing", None))
                    row["image_orientation_patient"] = _number_text(
                        getattr(dataset, "ImageOrientationPatient", None)
                    )
                    row["image_position_patient"] = _number_text(
                        getattr(dataset, "ImagePositionPatient", None)
                    )
                    row["slice_thickness_mm"] = _number_text(
                        getattr(dataset, "SliceThickness", None)
                    )
                    row["spacing_between_slices_mm"] = _number_text(
                        getattr(dataset, "SpacingBetweenSlices", None)
                    )
                    file_meta = getattr(dataset, "file_meta", None)
                    row["transfer_syntax_uid"] = _value_text(
                        getattr(file_meta, "TransferSyntaxUID", "")
                    )

                    study_uid = row["study_uid"]
                    series_uid = row["series_uid"]
                    sop_uid = row["sop_instance_uid"]
                    frame_uid = row["frame_of_reference_uid"]
                    rows_value = _integer_text(getattr(dataset, "Rows", None))
                    columns_value = _integer_text(getattr(dataset, "Columns", None))
                    frames_value = _integer_text(getattr(dataset, "NumberOfFrames", None)) or "1"
                    pixel_spacing = _numeric_tuple(getattr(dataset, "PixelSpacing", None))
                    orientation = _numeric_tuple(
                        getattr(dataset, "ImageOrientationPatient", None)
                    )
                    position = _numeric_tuple(getattr(dataset, "ImagePositionPatient", None))
                    projected = _projected_position(
                        getattr(dataset, "ImagePositionPatient", None),
                        getattr(dataset, "ImageOrientationPatient", None),
                    )
                    slice_thickness = _numeric_tuple(getattr(dataset, "SliceThickness", None))
                    slice_spacing = _numeric_tuple(
                        getattr(dataset, "SpacingBetweenSlices", None)
                    )
                    if alias in cases_by_alias:
                        cases_by_alias[alias]["modalities"][modality] += 1
                    modality_files[modality] += 1
                    modality_bytes[modality] += size

                    required_uid_count = sum(bool(value) for value in (study_uid, series_uid, sop_uid))
                    counters["files_with_all_study_series_sop_uids"] += int(
                        required_uid_count == 3
                    )
                    counters["files_missing_study_uid"] += int(not study_uid)
                    counters["files_missing_series_uid"] += int(not series_uid)
                    counters["files_missing_sop_instance_uid"] += int(not sop_uid)
                    counters["files_missing_modality"] += int(modality == "MISSING")
                    if study_uid:
                        study_uids.add(study_uid)
                    if series_uid:
                        series_uids.add(series_uid)
                    if frame_uid:
                        frame_uids.add(frame_uid)
                    if sop_uid:
                        sop_uids.add(sop_uid)
                        if alias in cases_by_alias:
                            cases_by_alias[alias]["sop_files"] += 1
                        previous = sop_seen.get(sop_uid)
                        current_identity = (alias, study_uid, series_uid)
                        if previous is None:
                            sop_seen[sop_uid] = (*current_identity, size)
                        else:
                            duplicate_sop_uids.add(sop_uid)
                            counters["duplicate_sop_instance_uid_extra_file_count"] += 1
                            if previous[:3] != current_identity:
                                duplicate_sop_conflict_uids.add(sop_uid)
                            if previous[3] != size:
                                duplicate_sop_size_conflict_uids.add(sop_uid)

                    if len(parts) == 4:
                        expected_series_directory_name = f"{modality}_{series_uid}"
                        filename_uuid_shape = bool(
                            re.fullmatch(
                                r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
                                entry_path.stem,
                            )
                        )
                        expected_path_checks[
                            "files_at_case_study_series_instance_depth"
                        ] += 1
                        expected_path_checks[
                            "study_directory_matches_study_uid"
                        ] += int(bool(study_uid) and parts[1] == study_uid)
                        expected_path_checks[
                            "series_directory_matches_series_uid"
                        ] += int(bool(series_uid) and parts[2] == series_uid)
                        expected_path_checks[
                            "series_directory_matches_modality_series_uid"
                        ] += int(
                            bool(series_uid)
                            and parts[2] == expected_series_directory_name
                        )
                        expected_path_checks[
                            "filename_matches_sop_instance_uid"
                        ] += int(bool(sop_uid) and entry_path.stem == sop_uid)
                        expected_path_checks["filename_has_uuid_stem_shape"] += int(
                            filename_uuid_shape
                        )
                        row["study_directory_matches_study_uid"] = str(
                            bool(study_uid) and parts[1] == study_uid
                        ).lower()
                        row["series_directory_matches_series_uid"] = str(
                            bool(series_uid) and parts[2] == series_uid
                        ).lower()
                        row["series_directory_matches_modality_series_uid"] = str(
                            bool(series_uid)
                            and parts[2] == expected_series_directory_name
                        ).lower()
                        row["filename_matches_sop_instance_uid"] = str(
                            bool(sop_uid) and entry_path.stem == sop_uid
                        ).lower()
                        row["filename_has_uuid_stem_shape"] = str(
                            filename_uuid_shape
                        ).lower()

                    if modality in IMAGE_MODALITIES:
                        field_values = {
                            "rows": rows_value,
                            "columns": columns_value,
                            "pixel_spacing": pixel_spacing,
                            "orientation": orientation,
                            "position": position,
                            "slice_thickness": slice_thickness,
                            "spacing_between_slices": slice_spacing,
                        }
                        presence = image_metadata_presence[modality]
                        presence["image_instance_count"] += 1
                        for field, value in field_values.items():
                            presence[field + "_present_count"] += int(value is not None and value != "")
                            presence[field + "_missing_count"] += int(value is None or value == "")

                    if study_uid and alias in cases_by_alias:
                        cases_by_alias[alias]["header_studies"].add(study_uid)
                    if series_uid and study_uid:
                        series_key = (alias, study_uid, series_uid)
                        series_record = series_by_key.setdefault(
                            series_key, _new_series_accumulator()
                        )
                        series_record["file_count"] += 1
                        series_record["total_bytes"] += size
                        series_record["modalities"][modality] += 1
                        if len(parts) >= 3:
                            series_record["series_relative_dirs"].add("/".join(parts[:3]))
                        series_record["header_error_count"] += int(
                            row["header_status"] != "PARSED"
                        )
                        if sop_uid:
                            series_record["sop_counts"][sop_uid] += 1
                            modality_sop_uids[modality].add(sop_uid)
                        if rows_value:
                            series_record["rows"].add(rows_value)
                        if columns_value:
                            series_record["columns"].add(columns_value)
                        series_record["frames"].add(frames_value)
                        if pixel_spacing is not None:
                            series_record["pixel_spacing"].add(
                                tuple(round(value, 7) for value in pixel_spacing)
                            )
                        if orientation is not None:
                            series_record["orientation"].add(
                                tuple(round(value, 7) for value in orientation)
                            )
                        if position is not None:
                            series_record["position"].add(
                                tuple(round(value, 5) for value in position)
                            )
                        if projected is not None:
                            series_record["projected_position"].add(projected)
                        if slice_thickness is not None:
                            series_record["slice_thickness"].add(
                                tuple(round(value, 7) for value in slice_thickness)
                            )
                        if slice_spacing is not None:
                            series_record["spacing_between_slices"].add(
                                tuple(round(value, 7) for value in slice_spacing)
                            )
                        if len(parts) >= 3:
                            series_record["series_directory_names"].add(parts[2])
                        modality_series_keys[modality].add(series_key)
                        if study_uid:
                            study_key = (alias, study_uid)
                            study_record = studies_by_key.setdefault(
                                study_key, _new_study_accumulator()
                            )
                            study_record["file_count"] += 1
                            study_record["total_bytes"] += size
                            study_record["modalities"][modality] += 1
                            study_record["series_keys"].add(series_key)
                            if len(parts) >= 2:
                                study_record["study_relative_dirs"].add("/".join(parts[:2]))
                            if sop_uid:
                                study_record["sop_uids"].add(sop_uid)
                            if alias in cases_by_alias:
                                cases_by_alias[alias]["header_series_groups"].add(series_key)

                writer.writerow(row)
                file_rows += 1
                if file_rows % 5000 == 0:
                    elapsed = time.monotonic() - start_time
                    print(f"Header index progress: {file_rows} files ({elapsed:.1f}s)", flush=True)

            stack.extend(reversed(child_directories))

    # Add recursive file/byte totals to the private directory inventory.
    for relative in sorted(
        directories,
        key=lambda value: directories[value]["depth"],
        reverse=True,
    ):
        record = directories[relative]
        record["recursive_file_count"] = record["direct_file_count"]
        record["recursive_bytes"] = record["direct_bytes"]
        for child in record["children"]:
            record["recursive_file_count"] += directories[child]["recursive_file_count"]
            record["recursive_bytes"] += directories[child]["recursive_bytes"]
    for relative, record in directories.items():
        if record["depth"] == 3 and record["directory_kind"] == "series":
            alias = _case_alias(Path(relative).parts[0])
            if alias in cases_by_alias and record["recursive_file_count"] == 0:
                cases_by_alias[alias]["empty_series_directories"] += 1

    return {
        "directories": directories,
        "series_by_key": series_by_key,
        "studies_by_key": studies_by_key,
        "cases_by_alias": cases_by_alias,
        "case_directory_names": case_directory_names,
        "scanned_case_directories": scanned_case_directories,
        "extension_counts": extension_counts,
        "modality_files": modality_files,
        "modality_bytes": modality_bytes,
        "modality_sop_uids": modality_sop_uids,
        "modality_series_keys": modality_series_keys,
        "image_metadata_presence": image_metadata_presence,
        "header_errors": header_errors,
        "basename_counts": basename_counts,
        "duplicate_sop_uids": duplicate_sop_uids,
        "duplicate_sop_conflict_uids": duplicate_sop_conflict_uids,
        "duplicate_sop_size_conflict_uids": duplicate_sop_size_conflict_uids,
        "study_uids": study_uids,
        "series_uids": series_uids,
        "frame_uids": frame_uids,
        "sop_uids": sop_uids,
        "counters": counters,
        "expected_path_checks": expected_path_checks,
        "file_rows": file_rows,
        "header_error_count": sum(header_errors.values()),
        "directory_count_including_root": len(directories),
        "empty_directory_count": sum(
            record["recursive_file_count"] == 0 and not record["children"]
            for record in directories.values()
        ),
        "max_directory_depth": max(record["depth"] for record in directories.values()),
    }


def _rows_for_manifests(scan: dict[str, Any], root: Path) -> dict[str, list[dict[str, Any]]]:
    directories = scan["directories"]
    series_by_key = scan["series_by_key"]
    studies_by_key = scan["studies_by_key"]
    cases_by_alias = scan["cases_by_alias"]
    series_rows: list[dict[str, Any]] = []
    for (alias, study_uid, series_uid), record in sorted(series_by_key.items()):
        sop_counts = record["sop_counts"]
        duplicate_groups = sum(count > 1 for count in sop_counts.values())
        modalities = sorted(record["modalities"])
        frames = sorted(record["frames"], key=lambda value: int(value or 0))
        positions = record["projected_position"]
        is_image = bool(set(modalities).intersection(IMAGE_MODALITIES))
        geometry_complete = (
            len(record["rows"]) == 1
            and len(record["columns"]) == 1
            and len(record["pixel_spacing"]) == 1
            and len(record["orientation"]) == 1
        )
        multi_frame = any(int(value) > 1 for value in frames if value.isdigit())
        unique_sops = len(sop_counts)
        if not is_image:
            volume_status = "NOT_IMAGE_SERIES"
        elif multi_frame and geometry_complete:
            volume_status = "MULTIFRAME_HEADER_CANDIDATE"
        elif unique_sops >= 2 and geometry_complete and len(positions) >= 2:
            volume_status = "MULTISLICE_HEADER_CANDIDATE"
        elif unique_sops <= 1:
            volume_status = "SINGLE_INSTANCE_OR_NO_SOP_UID"
        elif not geometry_complete:
            volume_status = "HEADER_GEOMETRY_INCOMPLETE_OR_INCONSISTENT"
        else:
            volume_status = "NO_MULTISLICE_POSITION_EVIDENCE"

        exact_series_dirs = sorted(record["series_relative_dirs"], key=str.casefold)
        series_relative_dir = (
            exact_series_dirs[0]
            if len(exact_series_dirs) == 1
            else json.dumps(exact_series_dirs, ensure_ascii=False, separators=(",", ":"))
            if exact_series_dirs
            else ""
        )
        directory_match = bool(exact_series_dirs) and all(
            Path(relative_dir).name == series_uid for relative_dir in exact_series_dirs
        )
        modality_directory_match = bool(exact_series_dirs) and all(
            any(
                Path(relative_dir).name == f"{modality}_{series_uid}"
                for modality in modalities
            )
            for relative_dir in exact_series_dirs
        )
        series_rows.append(
            {
                "case_alias": alias,
                "study_uid": study_uid,
                "series_uid": series_uid,
                "series_relative_dir": series_relative_dir,
                "series_relative_dirs": json.dumps(
                    exact_series_dirs, ensure_ascii=False, separators=(",", ":")
                ),
                "modalities": "|".join(modalities),
                "file_count": record["file_count"],
                "unique_sop_instance_count": unique_sops,
                "duplicate_sop_uid_group_count": duplicate_groups,
                "total_bytes": record["total_bytes"],
                "header_error_count": record["header_error_count"],
                "rows_unique_count": len(record["rows"]),
                "columns_unique_count": len(record["columns"]),
                "number_of_frames_values": "|".join(frames),
                "pixel_spacing_unique_count": len(record["pixel_spacing"]),
                "orientation_unique_count": len(record["orientation"]),
                "position_unique_count": len(record["position"]),
                "projected_slice_position_count": len(positions),
                "projected_slice_position_min_mm": min(positions) if positions else "",
                "projected_slice_position_max_mm": max(positions) if positions else "",
                "slice_thickness_values_mm": json.dumps(
                    sorted(record["slice_thickness"]), separators=(",", ":")
                ),
                "spacing_between_slices_values_mm": json.dumps(
                    sorted(record["spacing_between_slices"]), separators=(",", ":")
                ),
                "directory_matches_series_uid": str(directory_match).lower(),
                "directory_matches_modality_series_uid": str(
                    modality_directory_match
                ).lower(),
                "volume_candidate_status": volume_status,
            }
        )

    study_rows: list[dict[str, Any]] = []
    for (alias, study_uid), record in sorted(studies_by_key.items()):
        exact_study_dirs = sorted(record["study_relative_dirs"], key=str.casefold)
        relative_dir = (
            exact_study_dirs[0]
            if len(exact_study_dirs) == 1
            else json.dumps(exact_study_dirs, ensure_ascii=False, separators=(",", ":"))
            if exact_study_dirs
            else ""
        )
        study_rows.append(
            {
                "case_alias": alias,
                "study_uid": study_uid,
                "study_relative_dir": relative_dir,
                "series_group_count": len(record["series_keys"]),
                "file_count": record["file_count"],
                "unique_sop_instance_count": len(record["sop_uids"]),
                "total_bytes": record["total_bytes"],
                "modalities": "|".join(sorted(record["modalities"])),
                "study_relative_dirs": json.dumps(
                    exact_study_dirs, ensure_ascii=False, separators=(",", ":")
                ),
            }
        )

    case_rows: list[dict[str, Any]] = []
    for alias in EXPECTED_CASES:
        record = cases_by_alias[alias]
        case_rows.append(
            {
                "case_alias": alias,
                "case_directory_name": scan["case_directory_names"].get(alias, ""),
                "directory_file_count": record["directory_file_count"],
                "directory_bytes": record["directory_bytes"],
                "study_directory_count": record["study_directories"],
                "series_directory_count": record["series_directories"],
                "empty_series_directory_count": record["empty_series_directories"],
                "header_study_count": len(record["header_studies"]),
                "header_series_group_count": len(record["header_series_groups"]),
                "header_files_with_sop_instance_uid": record["sop_files"],
                "modality_file_counts_json": json.dumps(
                    dict(sorted(record["modalities"].items())),
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            }
        )

    directory_rows: list[dict[str, Any]] = []
    for relative, record in sorted(directories.items(), key=lambda item: item[0].casefold()):
        directory_rows.append(
            {
                "relative_path": relative,
                "depth": record["depth"],
                "directory_kind": record["directory_kind"],
                "direct_file_count": record["direct_file_count"],
                "direct_directory_count": record["direct_directory_count"],
                "recursive_file_count": record["recursive_file_count"],
                "direct_bytes": record["direct_bytes"],
                "recursive_bytes": record["recursive_bytes"],
                "is_empty": str(
                    record["recursive_file_count"] == 0 and not record["children"]
                ).lower(),
                "scan_error_class": record["scan_error_class"],
            }
        )
    return {
        "directories.csv": directory_rows,
        "studies.csv": study_rows,
        "series.csv": series_rows,
        "cases.csv": case_rows,
    }


def _case_summary(scan: dict[str, Any]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for alias in EXPECTED_CASES:
        record = scan["cases_by_alias"][alias]
        output.append(
            {
                "case_alias": alias,
                "directory_present": alias in scan["scanned_case_directories"],
                "files": record["directory_file_count"],
                "bytes": record["directory_bytes"],
                "study_directories": record["study_directories"],
                "series_directories": record["series_directories"],
                "empty_series_directories": record["empty_series_directories"],
                "header_studies": len(record["header_studies"]),
                "header_series_groups": len(record["header_series_groups"]),
                "header_files_with_sop_instance_uid": record["sop_files"],
                "modality_file_counts": dict(sorted(record["modalities"].items())),
            }
        )
    return output


def _make_public_summary(root: Path, scan: dict[str, Any], started_at: str) -> dict[str, Any]:
    counters = scan["counters"]
    directories = scan["directories"]
    modality_summary: dict[str, Any] = {}
    all_modalities = sorted(
        set(scan["modality_files"])
        | set(scan["modality_series_keys"])
        | {"UNKNOWN"}
    )
    for modality in all_modalities:
        bucket = "UNKNOWN" if modality == "MISSING" else modality
        modality_summary[bucket] = {
            "header_parsed_file_count": scan["modality_files"].get(modality, 0),
            "unique_sop_instance_count": len(scan["modality_sop_uids"].get(modality, set())),
            "series_group_count": len(scan["modality_series_keys"].get(modality, set())),
            "total_bytes": scan["modality_bytes"].get(modality, 0),
        }

    current_unique_sop_count = len(scan["sop_uids"])
    current_header_files = counters.get("header_parsed_file_count", 0)
    current_total_bytes = counters.get("total_bytes", 0)
    header_complete = scan["header_error_count"] == 0 and current_header_files == counters.get(
        "file_count", 0
    )
    inventory_complete = (
        counters.get("filesystem_inventory_complete", 1) == 1
        and counters.get("directory_read_error_count", 0) == 0
        and counters.get("metadata_error_count", 0) == 0
        and counters.get("reparse_entry_count", 0) == 0
    )
    return {
        "schema_version": "1.0.0",
        "task_id": "CMRL-11",
        "audit_version": SCRIPT_VERSION,
        "manifest_schema_version": INDEX_SCHEMA_VERSION,
        "generated_at_local": started_at,
        "source_class": "USER-REPORTED-SOURCE; local directory and DICOM headers inspected",
        "dataset_release_context": "IDC Release 25.0.0 reference carried forward from CMRL-06; object completeness is not implied",
        "scan_scope": {
            "dataset_relative_path": DEFAULT_DATA_RELATIVE.as_posix(),
            "root_directory_included_in_directory_counts": True,
            "filesystem_inventory_complete": inventory_complete,
            "dicom_header_parse_complete": header_complete,
            "pixel_data_decoded": False,
            "clinical_values_read": False,
            "file_content_hashes_computed": False,
            "source_files_modified_by_indexer": False,
            "network_or_install_actions": False,
        },
        "filesystem": {
            "regular_file_count": counters.get("file_count", 0),
            "total_bytes": current_total_bytes,
            "directory_count_including_root": scan["directory_count_including_root"],
            "directory_count_excluding_root": max(scan["directory_count_including_root"] - 1, 0),
            "directory_depth_counts_including_root": dict(
                sorted(collections.Counter(
                    record["depth"] for record in directories.values()
                ).items())
            ),
            "maximum_directory_depth_below_root": scan["max_directory_depth"],
            "case_directory_count": sum(
                record["directory_kind"] == "case" for record in directories.values()
            ),
            "expected_case_alias_directory_count": len(scan["scanned_case_directories"]),
            "missing_expected_case_aliases": sorted(
                set(EXPECTED_CASES) - scan["scanned_case_directories"]
            ),
            "unexpected_top_level_directory_count": counters.get(
                "unexpected_top_level_directory_count", 0
            ),
            "unmapped_case_file_count": counters.get("unmapped_case_file_count", 0),
            "unmapped_case_file_bytes": counters.get("unmapped_case_file_bytes", 0),
            "study_directory_count": sum(
                record["directory_kind"] == "study" for record in directories.values()
            ),
            "series_directory_count": sum(
                record["directory_kind"] == "series" for record in directories.values()
            ),
            "empty_directory_count": scan["empty_directory_count"],
            "empty_series_directory_count": sum(
                record["depth"] == 3
                and record["directory_kind"] == "series"
                and record["recursive_file_count"] == 0
                for record in directories.values()
            ),
            "extension_counts": dict(sorted(scan["extension_counts"].items())),
            "zero_byte_file_count": counters.get("zero_byte_file_count", 0),
            "special_nonregular_entry_count": counters.get(
                "special_nonregular_entry_count", 0
            ),
            "reparse_entry_count": counters.get("reparse_entry_count", 0),
            "metadata_error_count": counters.get("metadata_error_count", 0),
            "directory_read_error_count": counters.get("directory_read_error_count", 0),
            "unreadable_access_flag_count": counters.get(
                "unreadable_access_flag_count", 0
            ),
            "duplicate_basename_group_count": sum(
                count > 1 for count in scan["basename_counts"].values()
            ),
            "duplicate_basename_extra_file_count": sum(
                count - 1 for count in scan["basename_counts"].values() if count > 1
            ),
        },
        "dicom_headers": {
            "header_parsed_file_count": current_header_files,
            "header_error_file_count": scan["header_error_count"],
            "header_error_classes": dict(sorted(scan["header_errors"].items())),
            "unique_study_uid_count": len(scan["study_uids"]),
            "unique_series_uid_count": len(scan["series_uids"]),
            "case_study_series_group_count": len(scan["series_by_key"]),
            "unique_sop_instance_uid_count": current_unique_sop_count,
            "unique_frame_of_reference_uid_count": len(scan["frame_uids"]),
            "files_with_all_study_series_sop_uids": counters.get(
                "files_with_all_study_series_sop_uids", 0
            ),
            "files_missing_study_uid": counters.get("files_missing_study_uid", 0),
            "files_missing_series_uid": counters.get("files_missing_series_uid", 0),
            "files_missing_sop_instance_uid": counters.get(
                "files_missing_sop_instance_uid", 0
            ),
            "files_missing_modality": counters.get("files_missing_modality", 0),
            "duplicate_sop_instance_uid_group_count": len(scan["duplicate_sop_uids"]),
            "duplicate_sop_instance_uid_extra_file_count": counters.get(
                "duplicate_sop_instance_uid_extra_file_count", 0
            ),
            "duplicate_sop_identity_conflict_group_count": len(
                scan["duplicate_sop_conflict_uids"]
            ),
            "duplicate_sop_file_size_conflict_group_count": len(
                scan["duplicate_sop_size_conflict_uids"]
            ),
            "path_to_header_mapping_checks": dict(sorted(scan["expected_path_checks"].items())),
            "image_metadata_field_presence_by_modality": {
                modality: dict(sorted(counts.items()))
                for modality, counts in sorted(scan["image_metadata_presence"].items())
            },
            "modality_counts": modality_summary,
            "header_only_volume_candidate_counts": _volume_candidate_counts(scan),
        },
        "case_summaries": _case_summary(scan),
        "previous_audit_comparison": {
            "CMRL-05_local_root": {
                "file_count": 130_424,
                "total_bytes": 28_151_425_416,
                "header_parse_success_count": 130_424,
                "study_uid_count": 171,
                "series_uid_count": 806,
                "directory_count_including_parent_root": 1_017,
                "reference_report": "reports/r0/CMRL-05-TCIA全量DICOM准入审计.md",
            },
            "current_minus_CMRL_05": {
                "file_count": counters.get("file_count", 0) - 130_424,
                "total_bytes": current_total_bytes - 28_151_425_416,
                "study_uid_count": len(scan["study_uids"]) - 171,
                "series_uid_count": len(scan["series_uids"]) - 806,
                "directory_scope_note": "Current root is the named child directory; CMRL-05 counted its enclosing ccth_idc_v25_full root, adding one directory level entry.",
            },
            "IDC_v25_0_0_official_reference": {
                "series_count": 821,
                "instance_count": 131_556,
                "modalities": {
                    "MR": {"series_count": 523, "instance_count": 93_308},
                    "CT": {"series_count": 65, "instance_count": 21_740},
                    "PT": {"series_count": 68, "instance_count": 16_343},
                    "REG": {"series_count": 97, "instance_count": 97},
                    "RTSTRUCT": {"series_count": 68, "instance_count": 68},
                },
                "reference_report": "reports/r0/CMRL-06-IDC-v25逐Series及对象完整性补证.md",
            },
            "current_minus_official_expected": {
                "series_count": len(scan["series_uids"]) - 821,
                "unique_sop_instance_count": current_unique_sop_count - 131_556,
            },
            "interpretation": "Count differences identify inventory gaps at this scope. Empty directory names are not linked to official missing Series without an independently verified UID-level comparison; equal counts do not prove object identity or content integrity.",
        },
        "private_index_files": [
            ".local/dataset-index/files.csv",
            ".local/dataset-index/directories.csv",
            ".local/dataset-index/studies.csv",
            ".local/dataset-index/series.csv",
            ".local/dataset-index/cases.csv",
        ],
        "index_verification": {},
    }


def _volume_candidate_counts(scan: dict[str, Any]) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for modality in IMAGE_MODALITIES:
        counts: collections.Counter[str] = collections.Counter()
        for key, record in scan["series_by_key"].items():
            if record["modalities"].get(modality, 0) == 0:
                continue
            # Recompute the same conservative header-only category used in series.csv.
            sop_counts = record["sop_counts"]
            frames = record["frames"]
            geometry_complete = (
                len(record["rows"]) == 1
                and len(record["columns"]) == 1
                and len(record["pixel_spacing"]) == 1
                and len(record["orientation"]) == 1
            )
            multi_frame = any(int(value) > 1 for value in frames if value.isdigit())
            unique_sops = len(sop_counts)
            if multi_frame and geometry_complete:
                status = "MULTIFRAME_HEADER_CANDIDATE"
            elif unique_sops >= 2 and geometry_complete and len(record["projected_position"]) >= 2:
                status = "MULTISLICE_HEADER_CANDIDATE"
            elif unique_sops <= 1:
                status = "SINGLE_INSTANCE_OR_NO_SOP_UID"
            elif not geometry_complete:
                status = "HEADER_GEOMETRY_INCOMPLETE_OR_INCONSISTENT"
            else:
                status = "NO_MULTISLICE_POSITION_EVIDENCE"
            counts[status] += 1
        result[modality] = dict(sorted(counts.items()))
    return result


def _gib(byte_count: int) -> str:
    return f"{byte_count / (1024**3):.3f}"


def _render_report(summary: dict[str, Any]) -> str:
    fs = summary["filesystem"]
    headers = summary["dicom_headers"]
    scope = summary["scan_scope"]
    previous = summary["previous_audit_comparison"]["CMRL-05_local_root"]
    current_minus_previous = summary["previous_audit_comparison"]["current_minus_CMRL_05"]
    official = summary["previous_audit_comparison"]["IDC_v25_0_0_official_reference"]
    diff = summary["previous_audit_comparison"]["current_minus_official_expected"]
    extension_summary = "; ".join(
        f"{extension}={count:,}"
        for extension, count in sorted(fs["extension_counts"].items())
    ) or "无文件"
    lines = [
        "# TCIA CCTH 本地数据集目录索引与路径合同",
        "",
        f"- **任务：** CMRL-11；索引器版本 `{summary['audit_version']}`；Manifest schema `{summary['manifest_schema_version']}`。",
        f"- **扫描时间：** `{summary['generated_at_local']}`（本机时区）。",
        f"- **扫描根目录：** `{scope['dataset_relative_path']}`（仓库相对路径）。",
        f"- **文件系统索引：** {'完整遍历' if scope['filesystem_inventory_complete'] else '未完整遍历'}；DICOM Header 成功 `{headers['header_parsed_file_count']:,}/{fs['regular_file_count']:,}`。",
        "- **来源状态：** 本地目录为用户指定的已下载数据；IDC Release 25.0.0 数量作为 CMRL-06 官方索引对照，不据此宣称本地对象级完整。",
        "",
        "## 扫描结果",
        "",
        f"目标树包含 **{fs['regular_file_count']:,} 个普通文件**、**{fs['total_bytes']:,} bytes（{_gib(fs['total_bytes'])} GiB）**、**{fs['directory_count_including_root']:,} 个目录（含扫描根）**。扩展名：{extension_summary}。零字节 `{fs['zero_byte_file_count']}`；非普通特殊项 `{fs['special_nonregular_entry_count']}`；reparse 项 `{fs['reparse_entry_count']}`；目录/元数据读取错误 `{fs['directory_read_error_count'] + fs['metadata_error_count']}`；重复 basename 组 `{fs['duplicate_basename_group_count']}`。",
        "",
        "本轮读取标准 DICOM Header 的选定标签，`stop_before_pixels=True`，未使用 `force=True`。未解码 PixelData、未读取临床表、未计算文件内容哈希、未安装依赖，也未写入原始数据目录。",
        "",
        "### 真实目录层级",
        "",
        "脱敏树保留公开病例别名；Study、Series、Instance 的实际 UID 仅保存在本地忽略 Manifest。",
        "",
        "```text",
        "cc_tumor_heterogeneity/",
        "├── A01/ … A12/",
        "│   └── <StudyInstanceUID>/",
        "│       └── <Modality>_<SeriesInstanceUID>/",
        "│           └── <UUID>.dcm",
        "└── B01/ … B11/（同一层级）",
        "```",
        "",
            f"扫描到 `{fs['case_directory_count']}` 个病例目录，其中预期别名目录 `{fs['expected_case_alias_directory_count']}/{len(EXPECTED_CASES)}`；缺失别名 `{', '.join(fs['missing_expected_case_aliases']) or '无'}`；意外顶层目录 `{fs['unexpected_top_level_directory_count']}`；未映射到 A01–B11 的文件 `{fs['unmapped_case_file_count']}`。另有 `{fs['study_directory_count']}` 个 Study 目录、`{fs['series_directory_count']}` 个 Series 目录，最大目录深度为根目录下 `{fs['maximum_directory_depth_below_root']}` 层；空 Series 目录 `{fs['empty_series_directory_count']}`。目录计数描述实际路径结构；Series/Study UID 和文件名与 Header 的匹配率见下表。",
        "",
        "| 文件路径/Header 核对 | 命中 / 可核对 |",
        "|---|---:|",
    ]
    path_checks = headers["path_to_header_mapping_checks"]
    expected_files = path_checks.get("files_at_case_study_series_instance_depth", 0)
    for label, key in (
        ("Study 目录名 = StudyInstanceUID", "study_directory_matches_study_uid"),
        ("Series 目录名 = SeriesInstanceUID（无模态前缀）", "series_directory_matches_series_uid"),
        (
            "Series 目录名 = Modality_SeriesInstanceUID",
            "series_directory_matches_modality_series_uid",
        ),
        ("文件 stem = SOPInstanceUID", "filename_matches_sop_instance_uid"),
        ("文件 stem 为 UUID 格式", "filename_has_uuid_stem_shape"),
    ):
        lines.append(f"| {label} | {path_checks.get(key, 0):,} / {expected_files:,} |")
    lines.extend(
        [
            "",
            "实际命名规律：Study 文件夹名与 Header 的 StudyInstanceUID 相同；Series 文件夹名为 DICOM Modality、下划线和 SeriesInstanceUID；Instance 文件名是 UUID 形态并以 `.dcm` 结尾，与 SOPInstanceUID 字符串不相等。UID 与精确文件路径的连接来自 Header 索引，不应按 SOP UID 拼文件名。",
            "",
            "### 模态与 Study/Series/Instance 统计",
            "",
            "| Modality | Header 文件数 | 唯一 SOP Instance 数 | Series 组数 | 容量（GiB） |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for modality, record in sorted(headers["modality_counts"].items()):
        lines.append(
            f"| {modality} | {record['header_parsed_file_count']:,} | {record['unique_sop_instance_count']:,} | {record['series_group_count']:,} | {_gib(record['total_bytes'])} |"
        )
    lines.extend(
        [
            f"| **合计文件** | **{headers['header_parsed_file_count']:,}** | **{headers['unique_sop_instance_uid_count']:,}** | **{headers['case_study_series_group_count']:,}** | **{_gib(fs['total_bytes'])}** |",
            "",
            f"Header 解析失败 `{headers['header_error_file_count']}`；缺 Study UID `{headers['files_missing_study_uid']}`、Series UID `{headers['files_missing_series_uid']}`、SOP Instance UID `{headers['files_missing_sop_instance_uid']}`；重复 SOP UID 组 `{headers['duplicate_sop_instance_uid_group_count']}`，跨 Study/Series/case 冲突组 `{headers['duplicate_sop_identity_conflict_group_count']}`。",
            "",
            "| 图像模态 | Rows/Columns/PixelSpacing/Orientation/Position 等字段的 Header 覆盖 | Header-only Volume 候选分类 |",
            "|---|---|---|",
        ]
    )
    for modality in IMAGE_MODALITIES:
        presence = headers["image_metadata_field_presence_by_modality"].get(modality, {})
        volume_counts = headers["header_only_volume_candidate_counts"].get(modality, {})
        fields = [
            f"{field}: {presence.get(field + '_present_count', 0):,}/{presence.get('image_instance_count', 0):,}"
            for field in ("rows", "columns", "pixel_spacing", "orientation", "position")
        ]
        volume_text = "; ".join(
            f"{status}={count:,}" for status, count in sorted(volume_counts.items())
        ) or "无"
        lines.append(f"| {modality} | " + "; ".join(fields) + f" | {volume_text} |")
    lines.extend(
        [
            "",
            "Volume 分类只根据 Header 中的维度、spacing、方向和位置字段标记候选；没有检查切片连续性、实际像素、配准、空间叠加或影像质量，不能据此称为通过医学空间质控的体数据。REG 与 RTSTRUCT 按独立 DICOM Series/Instance 计数，不作为图像 Volume。",
            "",
            "### 每个病例目录汇总",
            "",
            "病例标识在公开报告中缩写为公开别名 A01–A12、B01–B11；以下均为本机目录文件聚合数，不含 Study/Series/SOP UID、采集日期或临床字段。",
            "",
            "| 病例别名 | 文件数 | 容量（GiB） | Study 目录 | Series 目录 | 空 Series 目录 | Header Studies | Header Series 组 | MR | CT | PT | REG | RTSTRUCT | 未分类 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for case in summary["case_summaries"]:
        modalities = case["modality_file_counts"]
        unknown = sum(
            count for key, count in modalities.items() if key not in KNOWN_MODALITIES
        )
        lines.append(
            "| {case_alias} | {files:,} | {gib} | {study_directories:,} | {series_directories:,} | {empty_series_directories:,} | {header_studies:,} | {header_series_groups:,} | {mr:,} | {ct:,} | {pt:,} | {reg:,} | {rt:,} | {unknown:,} |".format(
                case_alias=case["case_alias"],
                files=case["files"],
                gib=_gib(case["bytes"]),
                study_directories=case["study_directories"],
                series_directories=case["series_directories"],
                empty_series_directories=case["empty_series_directories"],
                header_studies=case["header_studies"],
                header_series_groups=case["header_series_groups"],
                mr=modalities.get("MR", 0),
                ct=modalities.get("CT", 0),
                pt=modalities.get("PT", 0),
                reg=modalities.get("REG", 0),
                rt=modalities.get("RTSTRUCT", 0),
                unknown=unknown,
            )
        )
    lines.extend(
        [
            "",
            "### 差异与证据等级",
            "",
            f"- **当前本地事实（`FILE-INSPECTED`）：** `{fs['regular_file_count']:,}` 个文件、`{fs['total_bytes']:,}` bytes、Header 解析 `{headers['header_parsed_file_count']:,}`；Header 有 `{headers['unique_study_uid_count']}` 个 Study UID、`{headers['unique_series_uid_count']}` 个 Series UID、`{headers['unique_sop_instance_uid_count']:,}` 个 SOP Instance UID。",
            f"- **与 CMRL-05 本机审计对照：** 旧报告记录 `{previous['file_count']:,}` 个文件、`{previous['total_bytes']:,}` bytes、`{previous['series_uid_count']}` 个 Header Series；本次文件数差 `{current_minus_previous['file_count']:+,}`、容量差 `{current_minus_previous['total_bytes']:+,}` bytes、Series UID 数差 `{current_minus_previous['series_uid_count']:+}`。旧审计从外层目录计数，多计一层根目录；当前只扫描用户指定的子目录。",
            f"- **IDC v25.0.0 官方参考（沿用 CMRL-06）：** `{official['series_count']:,}` 个 Series、`{official['instance_count']:,}` 个 Instance；本次 Header 识别 `{headers['unique_series_uid_count']:,}` 个 Series、`{headers['unique_sop_instance_uid_count']:,}` 个唯一 Instance，差值分别 `{diff['series_count']:+,}` 和 `{diff['unique_sop_instance_count']:+,}`。先前按官方 Series 映射的本地对账记录 15 个 Series、1,132 个 Instance 缺口；本报告不将空目录逐一映射为这些官方缺口。",
            "- **完整性边界：** 目录 Manifest 覆盖扫描到的实际文件；官方 Series/Instance 对照为数量级差异，不验证对象字节、像素可解码性、Volume 几何、ROI 语义或 CCTH 收录成员身份。官方预期、前序 IDC 映射与本地实际扫描是不同证据层。",
            "",
            "## 本地完整 Manifest 与字段说明",
            "",
            "以下文件仅保存在 Git 忽略的 `.local/dataset-index/`，包含精确相对路径和 UID；不得提交或复制到公开报告。",
            "",
            "| 文件 | 粒度与用途 |",
            "|---|---|",
            "| `files.csv` | 每个普通文件一行；相对路径、大小、Header 状态、Modality、Study/Series/SOP/Frame UID、实例号、图像维度/spacing/orientation/position、UID 与目录名匹配标志。 |",
            "| `directories.csv` | 每个目录一行；相对路径、深度、目录层级类型、直接/递归文件数与容量、空目录及读取错误。 |",
            "| `studies.csv` | 每个 case alias + Study UID 一行；Series 组数、文件/唯一 Instance 数、容量、模态与实际相对目录。 |",
            "| `series.csv` | 每个 case alias + Study UID + Series UID 一行；精确 Series 相对目录、文件与唯一 Instance 数、容量、Header 几何字段一致性及候选状态；若一个 UID 映射多个目录，路径列以 JSON 数组记录。 |",
            "| `cases.csv` | 每个公开病例别名一行；目录、Study/Series 数、容量、模态和空 Series 目录数。 |",
            "",
            "关键字段：`relative_path` 可从数据根目录解析；UID 字段按 DICOM 标识 Study、Series、Instance 和 Frame；`modality` 来自 DICOM Header；`rows/columns/number_of_frames/pixel_spacing/image_orientation_patient/image_position_patient` 是 Header 值；`volume_candidate_status` 仅作头信息候选。扫描未读取 PatientName、PatientID、临床工作簿、采集日期、ROI 名称/坐标或像素值。未计算全量文件哈希。",
            "",
            "## 统一路径合同",
            "",
            "- 仓库根目录：`D:\\CS\\CMRL`。默认数据集根目录：`data/raw/tcia/ccth_idc_v25_full/cc_tumor_heterogeneity`。",
            "- 如运行环境不同，可用 `CMRL_CCTH_ROOT` 覆盖；路径由 `pathlib.Path` 解析。相对路径只相对于选定的数据根目录解释。",
            "- DICOM UID 是 Study/Series/Instance 的对象标识；Windows 路径是本地文件位置。只有从 `series.csv` 或 `files.csv` 读取并核对 Header 后，才将索引中的相对路径拼到数据根目录。不要假定任意 UID 字符串都能直接拼成有效目录。",
            "",
            "```python",
            "import os",
            "from pathlib import Path",
            "",
            "repo_root = Path(r\"D:\\CS\\CMRL\")",
            "default_root = repo_root / \"data\" / \"raw\" / \"tcia\" / \"ccth_idc_v25_full\" / \"cc_tumor_heterogeneity\"",
            "data_root = Path(os.environ.get(\"CMRL_CCTH_ROOT\", str(default_root))).expanduser()",
            "if not data_root.is_dir():",
            "    raise FileNotFoundError(data_root)",
            "case_dir = data_root / \"CCTH-A01\"",
            "assert case_dir.is_dir()",
            "print(data_root.resolve())",
            "```",
            "",
            "`CCTH-A01` 仅用于最小路径存在性示例。具体研究 Series 应先按任务条件查询本地 `series.csv`，再用其 `series_relative_dir` 和 UID/Modality 字段回查 `files.csv`；后续是否进入像素或 ROI 空间检查仍需单独授权与用户验收。",
            "",
            "## 可重复生成",
            "",
            "在仓库根目录运行 `python scripts/r0/build_ccth_dataset_index.py`；可用 `--data-root` 显式指定本任务目录，或设置 `CMRL_CCTH_ROOT`。脚本默认拒绝覆盖已有输出；确认重建同名索引后使用 `--replace-generated`，只替换本脚本管理的五个本机 Manifest、此 Markdown 与 JSON。脚本不会递归跟随 reparse point。",
            "",
            "完整私有索引的文件数与容量经写盘后回读校验；安全 JSON 只保留聚合统计、病例别名与公开路径模板。JSON 中不包含 UID、精确病例路径或患者标识。",
            "",
            "## 证据来源与未验证事项",
            "",
            "- 本地审计对照：[CMRL-05 全量 DICOM 报告](../../reports/r0/CMRL-05-TCIA全量DICOM准入审计.md)、[CMRL-06 IDC v25 Series/Instance 对账](../../reports/r0/CMRL-06-IDC-v25逐Series及对象完整性补证.md)。",
            "- 官方 Collection/IDC 统计和许可证沿用前序来源核验；本次未请求网络或下载文件。",
            "- 唯一数量、UID/路径匹配及 header 候选不证明 PixelData 可解码、MRI 切片连续、方向正确、RTSTRUCT 可栅格化、ROI 为肿瘤或患者时点/临床标签正确。R0 仍以项目 Main 决定为准；本报告不表示 R0 COMPLETE。",
            "",
        ]
    )
    return "\n".join(lines)


def _validate_private_outputs(
    index_dir: Path,
    expected_file_count: int,
    expected_bytes: int,
    expected_dir_count: int,
    root: Path,
) -> dict[str, Any]:
    file_manifest = index_dir / "files.csv.partial"
    total_rows = total_bytes = 0
    relative_paths: set[str] = set()
    file_count_by_parent: collections.Counter[str] = collections.Counter()
    bytes_by_parent: collections.Counter[str] = collections.Counter()
    with file_manifest.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        for row in reader:
            total_rows += 1
            size = int(row["file_size_bytes"])
            relative = row["relative_path"]
            relative_path = Path(relative)
            if relative_path.is_absolute() or ".." in relative_path.parts:
                raise AuditError("PRIVATE_FILE_MANIFEST_PATH_NOT_RELATIVE")
            total_bytes += size
            relative_paths.add(relative)
            parent = relative_path.parent.as_posix()
            if parent == ".":
                parent = ""
            file_count_by_parent[parent] += 1
            bytes_by_parent[parent] += size

    directory_count_by_path: dict[str, int] = {}
    directory_bytes_by_path: dict[str, int] = {}
    root_recursive_files = root_recursive_bytes = None
    with (index_dir / "directories.csv.partial").open("r", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            relative = row["relative_path"]
            if relative in directory_count_by_path:
                raise AuditError("PRIVATE_DIRECTORY_MANIFEST_PATH_DUPLICATE")
            directory_count_by_path[relative] = int(row["direct_file_count"])
            directory_bytes_by_path[relative] = int(row["direct_bytes"])
            if relative == "":
                root_recursive_files = int(row["recursive_file_count"])
                root_recursive_bytes = int(row["recursive_bytes"])
    directory_rows = len(directory_count_by_path)
    if total_rows != expected_file_count or total_bytes != expected_bytes:
        raise AuditError("PRIVATE_FILE_MANIFEST_TOTAL_MISMATCH")
    if len(relative_paths) != total_rows:
        raise AuditError("PRIVATE_FILE_MANIFEST_PATH_DUPLICATE")
    if directory_rows != expected_dir_count:
        raise AuditError("PRIVATE_DIRECTORY_MANIFEST_TOTAL_MISMATCH")
    if root_recursive_files != expected_file_count or root_recursive_bytes != expected_bytes:
        raise AuditError("PRIVATE_DIRECTORY_ROOT_RECURSIVE_TOTAL_MISMATCH")
    if set(file_count_by_parent) - set(directory_count_by_path) or any(
        directory_count_by_path[path] != file_count_by_parent.get(path, 0)
        or directory_bytes_by_path[path] != bytes_by_parent.get(path, 0)
        for path in directory_count_by_path
    ):
        raise AuditError("PRIVATE_DIRECTORY_DIRECT_TOTAL_MISMATCH")
    return {
        "private_files_manifest_rows": total_rows,
        "private_files_manifest_bytes_sum": total_bytes,
        "private_files_manifest_unique_relative_paths": len(relative_paths),
        "private_directories_manifest_rows": directory_rows,
        "private_directory_root_recursive_files": root_recursive_files,
        "private_directory_root_recursive_bytes": root_recursive_bytes,
        "file_count_matches_scan": total_rows == expected_file_count,
        "bytes_sum_matches_scan": total_bytes == expected_bytes,
        "directory_count_matches_scan": directory_rows == expected_dir_count,
        "directory_root_recursive_totals_match_scan": True,
        "directory_direct_totals_match_file_manifest": True,
    }


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _preflight_outputs(
    index_dir: Path, report_path: Path, summary_path: Path, replace_generated: bool
) -> None:
    private_root = (REPO_ROOT / ".local").resolve()
    try:
        index_dir.resolve().relative_to(private_root)
    except ValueError as exc:
        raise AuditError("PRIVATE_INDEX_OUTSIDE_GIT_IGNORED_LOCAL") from exc
    owned_paths = [
        index_dir / name
        for name in (
            "files.csv",
            "directories.csv",
            "studies.csv",
            "series.csv",
            "cases.csv",
            "files.csv.partial",
            "directories.csv.partial",
            "studies.csv.partial",
            "series.csv.partial",
            "cases.csv.partial",
        )
    ] + [report_path, summary_path, report_path.with_suffix(report_path.suffix + ".partial"), summary_path.with_suffix(summary_path.suffix + ".partial")]
    existing = [path for path in owned_paths if path.exists()]
    if existing and not replace_generated:
        raise AuditError("GENERATED_OUTPUT_EXISTS_USE_EXPLICIT_REPLACE_FLAG")
    if existing and replace_generated:
        for path in existing:
            if path.is_dir():
                raise AuditError("GENERATED_OUTPUT_PATH_IS_DIRECTORY")
            path.unlink()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Dataset root; defaults to CMRL_CCTH_ROOT or the repository path contract.",
    )
    parser.add_argument(
        "--index-dir", type=Path, default=REPO_ROOT / DEFAULT_INDEX_RELATIVE
    )
    parser.add_argument(
        "--report", type=Path, default=REPO_ROOT / DEFAULT_REPORT_RELATIVE
    )
    parser.add_argument(
        "--summary", type=Path, default=REPO_ROOT / DEFAULT_SUMMARY_RELATIVE
    )
    parser.add_argument(
        "--replace-generated",
        action="store_true",
        help="Replace only this script's known output files after explicit confirmation.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    env_root = os.environ.get("CMRL_CCTH_ROOT")
    configured_root = args.data_root or (Path(env_root) if env_root else REPO_ROOT / DEFAULT_DATA_RELATIVE)
    root = configured_root.expanduser().resolve()
    index_dir = args.index_dir.expanduser().resolve()
    report_path = args.report.expanduser().resolve()
    summary_path = args.summary.expanduser().resolve()
    if not root.is_dir():
        raise SystemExit("DATA_ROOT_NOT_FOUND")
    if _is_reparse(root.lstat()):
        raise SystemExit("DATA_ROOT_IS_REPARSE_POINT")
    for output in (index_dir, report_path, summary_path):
        try:
            output.relative_to(root)
        except ValueError:
            continue
        raise SystemExit("OUTPUT_INSIDE_SOURCE_DATA_ROOT")

    _preflight_outputs(index_dir, report_path, summary_path, args.replace_generated)
    index_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    partial_files = [
        index_dir / "files.csv.partial",
        index_dir / "directories.csv.partial",
        index_dir / "studies.csv.partial",
        index_dir / "series.csv.partial",
        index_dir / "cases.csv.partial",
        report_path.with_suffix(report_path.suffix + ".partial"),
        summary_path.with_suffix(summary_path.suffix + ".partial"),
    ]
    generated_at = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    run_start_time = time.monotonic()
    try:
        scan = _scan(root, index_dir / "files.csv.partial")
        counters = scan["counters"]
        if counters.get("filesystem_inventory_complete", 1) != 1:
            raise AuditError("FILESYSTEM_INVENTORY_INCOMPLETE")

        manifest_rows = _rows_for_manifests(scan, root)
        for filename, rows in manifest_rows.items():
            fields = {
                "directories.csv": DIRECTORY_FIELDS,
                "studies.csv": STUDY_FIELDS,
                "series.csv": SERIES_FIELDS,
                "cases.csv": CASE_FIELDS,
            }[filename]
            _csv_write(index_dir / (filename + ".partial"), fields, rows)

        summary = _make_public_summary(root, scan, generated_at)
        verification = _validate_private_outputs(
            index_dir,
            expected_file_count=counters.get("file_count", 0),
            expected_bytes=counters.get("total_bytes", 0),
            expected_dir_count=scan["directory_count_including_root"],
            root=root,
        )
        summary["index_verification"] = verification
        report_text = _render_report(summary)
        report_path.with_suffix(report_path.suffix + ".partial").write_text(
            report_text, encoding="utf-8", newline="\n"
        )
        _write_json(summary_path.with_suffix(summary_path.suffix + ".partial"), summary)

        if not all(
            verification[key]
            for key in (
                "file_count_matches_scan",
                "bytes_sum_matches_scan",
                "directory_count_matches_scan",
                "directory_root_recursive_totals_match_scan",
                "directory_direct_totals_match_file_manifest",
            )
        ):
            raise AuditError("INDEX_TOTALS_VALIDATION_FAILED")

        for partial in partial_files:
            target = partial.with_suffix("") if partial.parent == index_dir else partial.with_suffix("")
            os.replace(partial, target)

        elapsed = time.monotonic() - run_start_time
        print(
            json.dumps(
                {
                    "status": "INDEX_GENERATED",
                    "elapsed_seconds": round(elapsed, 1),
                    "files": counters.get("file_count", 0),
                    "bytes": counters.get("total_bytes", 0),
                    "header_parsed": counters.get("header_parsed_file_count", 0),
                    "header_errors": scan["header_error_count"],
                    "study_uids": len(scan["study_uids"]),
                    "series_uids": len(scan["series_uids"]),
                    "sop_uids": len(scan["sop_uids"]),
                    "directory_count_including_root": scan["directory_count_including_root"],
                    "index_verification": verification,
                    "public_outputs": [
                        report_path.relative_to(REPO_ROOT).as_posix(),
                        summary_path.relative_to(REPO_ROOT).as_posix(),
                    ],
                    "private_index_directory": index_dir.relative_to(REPO_ROOT).as_posix(),
                    "header_errors_by_class": dict(sorted(scan["header_errors"].items())),
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            flush=True,
        )
        return 0
    except Exception:
        for partial in partial_files:
            try:
                partial.unlink(missing_ok=True)
            except OSError:
                pass
        raise


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuditError as exc:
        raise SystemExit(str(exc)) from None
