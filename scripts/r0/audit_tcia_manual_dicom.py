#!/usr/bin/env python3
"""Bounded, read-only, aggregate-only DICOM metadata audit for CMRL-04.

The scanner opens source files read-only, stops before PixelData, does not
decode image pixels, and emits only aggregate counts. Patient identifiers,
UID values, source paths, and file names remain in memory only for reference
resolution. ROI names and contour coordinates are inspected only for bounded
metadata checks; none are written to the output.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import math
import os
import random
import re
import stat
import sys
import tempfile
import time
import warnings
from pathlib import Path
from typing import Any

import pydicom
from pydicom.tag import Tag


TASK_ID = "CMRL-04"
PLAN_REVISION = "r2"
MAX_HEADER_FILES = 20_000
MAX_SECONDS = 20 * 60
MAX_IMAGE_FILE_BYTES = 128 * 1024 * 1024
MAX_RTSTRUCT_FILE_BYTES = 16 * 1024 * 1024
FORCED_PARSE_TRIAL_LIMIT = 5
DICOM_EXTENSIONS = {".dcm", ".dicom", ".ima"}
REPARSE_POINT = 0x400

BASE_TAGS = [
    Tag(value)
    for value in (
        "00080016",  # SOPClassUID
        "00080018",  # SOPInstanceUID
        "00080008",  # ImageType
        "00080060",  # Modality
        "0008103E",  # SeriesDescription
        "00100020",  # PatientID (in-memory key only)
        "00180024",  # SequenceName
        "00180050",  # SliceThickness
        "00180081",  # EchoTime
        "00180088",  # SpacingBetweenSlices
        "0020000D",  # StudyInstanceUID (in-memory key only)
        "0020000E",  # SeriesInstanceUID (in-memory key only)
        "00200032",  # ImagePositionPatient
        "00200037",  # ImageOrientationPatient
        "00200052",  # FrameOfReferenceUID (in-memory key only)
        "00280010",  # Rows
        "00280011",  # Columns
        "00280030",  # PixelSpacing
        "00280008",  # NumberOfFrames
    )
]
RTSTRUCT_TAGS = [
    Tag("30060010"),  # ReferencedFrameOfReferenceSequence
    Tag("30060020"),  # StructureSetROISequence
    Tag("30060039"),  # ROIContourSequence
    Tag("30060080"),  # RTROIObservationsSequence
]

# DICOM PS3.3 2026d, C.8.8.8.1 defined terms.
RTROI_DEFINED_TYPES = {
    "EXTERNAL",
    "PTV",
    "CTV",
    "GTV",
    "TREATED_VOLUME",
    "IRRAD_VOLUME",
    "OAR",
    "BOLUS",
    "AVOIDANCE",
    "ORGAN",
    "MARKER",
    "REGISTRATION",
    "ISOCENTER",
    "CONTRAST_AGENT",
    "CAVITY",
    "BRACHY_CHANNEL",
    "BRACHY_ACCESSORY",
    "BRACHY_SRC_APP",
    "BRACHY_CHNL_SHLD",
    "SUPPORT",
    "FIXATION",
    "DOSE_REGION",
    "CONTROL",
    "DOSE_MEASUREMENT",
    "DEVICE",
}
# DICOM PS3.3 2026d, C.8.8.6.1 enumerated geometric types.
CONTOUR_GEOMETRIC_TYPES = {
    "POINT",
    "OPEN_PLANAR",
    "OPEN_NONPLANAR",
    "CLOSED_PLANAR",
    "CLOSEDPLANAR_XOR",
}
RTSTRUCT_SEQUENCE_NAMES = (
    "StructureSetROISequence",
    "RTROIObservationsSequence",
    "ROIContourSequence",
)
RTSTRUCT_COUNTER_NAMES = (
    "roi_number_status_counts",
    "roi_observation_number_status_counts",
    "roi_observation_reference_status_counts",
    "roi_observation_interpreted_type_presence_counts",
    "interpreted_type_category_counts",
    "roi_type_mapping_status_counts",
    "roi_type_category_counts",
    "roi_name_presence_counts",
    "roi_name_heuristic_category_counts",
    "roi_name_type_comparison_counts",
    "roi_contour_reference_status_counts",
    "contour_sequence_state_counts",
    "contour_geometric_type_counts",
    "contour_point_count_status_counts",
    "contour_data_check_counts",
    "point_geometry_consistency_counts",
    "contour_image_sequence_state_counts",
    "contour_image_reference_value_status_counts",
)

REQUIRED_TAGS = {
    "PatientID": "PatientID",
    "StudyInstanceUID": "StudyInstanceUID",
    "SeriesInstanceUID": "SeriesInstanceUID",
    "SOPInstanceUID": "SOPInstanceUID",
    "FrameOfReferenceUID": "FrameOfReferenceUID",
    "SOPClassUID": "SOPClassUID",
    "Modality": "Modality",
}
MR_SPATIAL_TAGS = {
    "ImageOrientationPatient": "ImageOrientationPatient",
    "ImagePositionPatient": "ImagePositionPatient",
    "PixelSpacing": "PixelSpacing",
    "SliceThickness": "SliceThickness",
    "SpacingBetweenSlices": "SpacingBetweenSlices",
    "Rows": "Rows",
    "Columns": "Columns",
    "FrameOfReferenceUID": "FrameOfReferenceUID",
}
CORE_MR_GEOMETRY_FIELDS = {
    "ImageOrientationPatient",
    "ImagePositionPatient",
    "PixelSpacing",
    "Rows",
    "Columns",
    "FrameOfReferenceUID",
}

SOP_CLASS_ALLOWLIST = {
    "CT Image Storage",
    "MR Image Storage",
    "Enhanced MR Image Storage",
    "Enhanced CT Image Storage",
    "Positron Emission Tomography Image Storage",
    "RT Structure Set Storage",
    "RT Plan Storage",
    "RT Dose Storage",
    "Spatial Registration Storage",
    "Spatial Fiducials Storage",
    "Segmentation Storage",
    "Surface Segmentation Storage",
    "Secondary Capture Image Storage",
    "Computed Radiography Image Storage",
    "Ultrasound Image Storage",
    "Digital X-Ray Image Storage",
    "Digital Mammography X-Ray Image Storage",
    "Nuclear Medicine Image Storage",
    "Basic Text SR",
    "Enhanced SR",
    "Comprehensive SR",
}

T2_TOKEN = re.compile(r"(?:^|[^A-Z0-9])T2(?:W|WI)?(?:$|[^A-Z0-9])", re.IGNORECASE)
SPIN_ECHO_TOKEN = re.compile(
    r"(?:^|[^A-Z0-9])(?:TSE|FSE|SE|FAST SPIN|TURBO SPIN)(?:$|[^A-Z0-9])",
    re.IGNORECASE,
)


def _is_reparse(st: os.stat_result) -> bool:
    return stat.S_ISLNK(st.st_mode) or bool(
        getattr(st, "st_file_attributes", 0) & REPARSE_POINT
    )


def _file_signature(path: str) -> tuple[int, int, int]:
    st = os.stat(path, follow_symlinks=False)
    return (
        int(st.st_size),
        int(st.st_mtime_ns),
        int(getattr(st, "st_file_attributes", 0)),
    )


def _safe_extension(name: str) -> str:
    lower = name.lower()
    if lower.endswith(".dcm.gz"):
        return ".dcm.gz"
    suffix = Path(name).suffix.lower()
    if suffix in DICOM_EXTENSIONS or suffix in {
        ".zip",
        ".7z",
        ".gz",
        ".json",
        ".xml",
        ".csv",
        ".xlsx",
        ".txt",
        ".pdf",
    }:
        return suffix
    return "<none>" if not suffix else "<other>"


def inventory(root: Path, deadline: float) -> dict[str, Any]:
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError("input directory unavailable")
    root_st = os.stat(root, follow_symlinks=False)
    if _is_reparse(root_st):
        raise RuntimeError("input directory is a reparse point")

    stack = [str(root)]
    snapshots: dict[str, tuple[int, int, int]] = {}
    candidates: list[tuple[str, int]] = []
    extension_counts: collections.Counter[str] = collections.Counter()
    metadata_errors: collections.Counter[str] = collections.Counter()
    file_count = directory_count = total_bytes = zero_bytes = 0
    reparse_count = special_count = 0
    complete = True

    while stack:
        if time.monotonic() >= deadline:
            complete = False
            break
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    if time.monotonic() >= deadline:
                        complete = False
                        break
                    try:
                        st = entry.stat(follow_symlinks=False)
                        if _is_reparse(st):
                            reparse_count += 1
                            continue
                        if stat.S_ISDIR(st.st_mode):
                            directory_count += 1
                            stack.append(entry.path)
                        elif stat.S_ISREG(st.st_mode):
                            file_count += 1
                            size = int(st.st_size)
                            total_bytes += size
                            zero_bytes += int(size == 0)
                            extension = _safe_extension(entry.name)
                            extension_counts[extension] += 1
                            signature = (
                                size,
                                int(st.st_mtime_ns),
                                int(getattr(st, "st_file_attributes", 0)),
                            )
                            snapshots[entry.path] = signature
                            if entry.name.lower().endswith(".dcm.gz"):
                                candidates.append((entry.path, size))
                            elif Path(entry.name).suffix.lower() in DICOM_EXTENSIONS:
                                candidates.append((entry.path, size))
                        else:
                            special_count += 1
                    except Exception as exc:  # aggregate class only
                        metadata_errors[type(exc).__name__] += 1
                if not complete:
                    break
        except Exception as exc:
            metadata_errors[type(exc).__name__] += 1
            complete = False
            break

    return {
        "complete": complete,
        "file_count": file_count,
        "directory_count": directory_count,
        "total_bytes": total_bytes,
        "zero_byte_file_count": zero_bytes,
        "extension_counts": dict(sorted(extension_counts.items())),
        "dicom_candidate_count": len(candidates),
        "reparse_or_symlink_entries_skipped": reparse_count,
        "special_entry_count": special_count,
        "metadata_error_count": sum(metadata_errors.values()),
        "metadata_error_classes": dict(sorted(metadata_errors.items())),
        "snapshots": snapshots,
        "candidates": candidates,
    }


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return " ".join(_text(item) for item in value)
    return str(value).strip()


def _number(value: Any) -> float | None:
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _numbers(value: Any) -> list[float] | None:
    if value is None:
        return None
    try:
        items = list(value) if not isinstance(value, (str, bytes)) else [value]
    except TypeError:
        items = [value]
    result: list[float] = []
    for item in items:
        number = _number(item)
        if number is None:
            return None
        result.append(number)
    return result


def _modality(value: Any) -> str:
    raw = _text(value).upper()
    if not raw:
        return "MISSING"
    return raw if re.fullmatch(r"[A-Z0-9]{1,12}", raw) else "OTHER"


def _sop_class(value: Any) -> str:
    raw = _text(value)
    if not raw:
        return "MISSING"
    try:
        name = pydicom.uid.UID(raw).name
    except Exception:
        name = None
    return name if name in SOP_CLASS_ALLOWLIST else "OTHER"


def _parse_dataset(
    path: str, *, force: bool = False, specific_tags: list[Tag] | None = None
) -> Any:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return pydicom.dcmread(
            path,
            stop_before_pixels=True,
            force=force,
            defer_size="1 MB",
            specific_tags=specific_tags,
        )


def _valid_orientation(values: list[float] | None) -> bool:
    if values is None or len(values) != 6:
        return False
    first, second = values[:3], values[3:]
    norm_a = math.sqrt(sum(v * v for v in first))
    norm_b = math.sqrt(sum(v * v for v in second))
    dot = sum(a * b for a, b in zip(first, second))
    return 0.8 <= norm_a <= 1.2 and 0.8 <= norm_b <= 1.2 and abs(dot) <= 0.1


def _field_present(ds: Any, name: str) -> bool:
    value = getattr(ds, name, None)
    return value is not None and value != ""


def _build_record(path: str, size: int, ds: Any, forced: bool) -> dict[str, Any]:
    record: dict[str, Any] = {
        "_path": path,
        "_size": size,
        "_forced": forced,
        "_patient": _text(getattr(ds, "PatientID", None)),
        "_study": _text(getattr(ds, "StudyInstanceUID", None)),
        "_series": _text(getattr(ds, "SeriesInstanceUID", None)),
        "_sop": _text(getattr(ds, "SOPInstanceUID", None)),
        "_frame": _text(getattr(ds, "FrameOfReferenceUID", None)),
        "_modality": _modality(getattr(ds, "Modality", None)),
        "_sop_class": _sop_class(getattr(ds, "SOPClassUID", None)),
        "_series_text": " ".join(
            _text(getattr(ds, name, None))
            for name in ("SeriesDescription", "SequenceName", "ImageType")
        ),
        "_echo_time": _number(getattr(ds, "EchoTime", None)),
        "_present": {name: _field_present(ds, name) for name in REQUIRED_TAGS},
    }
    if record["_modality"] == "MR":
        record["_spatial_present"] = {
            name: _field_present(ds, name) for name in MR_SPATIAL_TAGS
        }
        record["_orientation_plausible"] = _valid_orientation(
            _numbers(getattr(ds, "ImageOrientationPatient", None))
        )
        pixel_spacing = _numbers(getattr(ds, "PixelSpacing", None))
        record["_pixel_spacing_plausible"] = bool(
            pixel_spacing
            and len(pixel_spacing) == 2
            and all(0 < value <= 10 for value in pixel_spacing)
        )
        position = _numbers(getattr(ds, "ImagePositionPatient", None))
        record["_position_finite"] = bool(position and len(position) == 3)
        rows = _number(getattr(ds, "Rows", None))
        columns = _number(getattr(ds, "Columns", None))
        record["_dimensions_present"] = bool(
            rows is not None and columns is not None and rows > 0 and columns > 0
        )
        for attribute, key in (
            ("SliceThickness", "_slice_thickness_plausible"),
            ("SpacingBetweenSlices", "_slice_spacing_plausible"),
        ):
            value = _number(getattr(ds, attribute, None))
            record[key] = bool(value is not None and 0 < value <= 100)
    return record


def _sample_candidates(
    candidates: list[tuple[str, int]], limit: int
) -> tuple[list[tuple[str, int]], str]:
    if len(candidates) <= limit:
        return candidates, "FULL_LOCAL_CANDIDATE_SET"
    rng = random.Random(20261017)
    chosen = set(rng.sample(range(len(candidates)), limit))
    return [candidate for index, candidate in enumerate(candidates) if index in chosen], (
        "UNIFORM_RANDOM_SAMPLE"
    )


def _roi_name_heuristic(name: str) -> str:
    label = name.casefold()
    if not label:
        return "UNDETERMINED"
    if re.search(
        r"(?:^|[^a-z0-9])gtv(?:p|n|primary|nodal)?(?=$|[^a-z0-9]|[0-9])|"
        r"(?:^|[^a-z0-9])tumou?r(?=$|[^a-z0-9]|[0-9])|"
        r"gross[\s_-]*tumou?r|primary[\s_-]*tumou?r|"
        r"tumou?r[\s_-]*primary|cervix[\s_-]*tumou?r|tumou?r[\s_-]*cervix",
        label,
    ):
        return "GTV-like"
    if re.search(
        r"(?:^|[^a-z0-9])(?:ctv|ptv)(?:p|n|primary|nodal|boost|elective)?"
        r"(?=$|[^a-z0-9]|[0-9])|"
        r"clinical[\s_-]*target|planning[\s_-]*target",
        label,
    ):
        return "CTV/PTV-like"
    if re.search(
        r"(?:^|[^a-z0-9])oar(?=$|[^a-z0-9]|[0-9])|organ[\s_-]*at[\s_-]*risk|"
        r"bladder|rectum|bowel|sigmoid|"
        r"femur|femoral|kidney|ureter|small[\s_-]*intestine|"
        r"large[\s_-]*intestine|spinal[\s_-]*cord",
        label,
    ):
        return "OAR-like"
    return "OTHER"


def _field_value(dataset: Any, keyword: str) -> tuple[Any, bool]:
    try:
        return getattr(dataset, keyword), True
    except AttributeError:
        return None, False


def _sequence_items(dataset: Any, keyword: str) -> tuple[list[Any], str]:
    value, present = _field_value(dataset, keyword)
    if not present:
        return [], "MISSING"
    if value is None:
        return [], "EMPTY"
    try:
        items = list(value)
    except TypeError:
        return [], "INVALID"
    return items, "PRESENT" if items else "EMPTY"


def _dicom_integer(value: Any, present: bool) -> tuple[int | None, str]:
    if not present:
        return None, "MISSING"
    text = _text(value)
    if not text:
        return None, "EMPTY"
    try:
        number = int(text, 10)
    except (TypeError, ValueError, OverflowError):
        return None, "INVALID"
    return number, "PRESENT"


def _positive_dicom_integer(value: Any, present: bool) -> tuple[int | None, str]:
    number, status = _dicom_integer(value, present)
    if status != "PRESENT":
        return None, status
    if number is None or number <= 0:
        return None, "NON_POSITIVE"
    return number, "PRESENT"


def _roi_number_link_status(
    value: Any, present: bool, structure_rois: dict[int, list[int]]
) -> tuple[str, int | None]:
    number, number_status = _dicom_integer(value, present)
    if number_status != "PRESENT":
        return number_status, None
    matches = structure_rois.get(number, [])
    if not matches:
        return "ORPHAN_REFERENCE", number
    if len(matches) > 1:
        return "AMBIGUOUS_REFERENCE", number
    return "UNIQUE_REFERENCE", number


def _interpreted_type_category(value: Any) -> str:
    normalized = _text(value).upper()
    if normalized in {"GTV", "CTV", "PTV", "OAR"}:
        return normalized
    if normalized in RTROI_DEFINED_TYPES:
        return "OTHER_VALID_DEFINED_TERM"
    return "UNRECOGNIZED_VALUE"


def _empty_rtstruct_summary() -> dict[str, Any]:
    return {
        "sequence_state_counts": {
            name: collections.Counter() for name in RTSTRUCT_SEQUENCE_NAMES
        },
        "sequence_entry_counts": collections.Counter(),
        "counts": {name: collections.Counter() for name in RTSTRUCT_COUNTER_NAMES},
        "scalars": collections.Counter(),
        "_contour_sop_refs": set(),
    }


def _summarize_rtstruct_dataset(dataset: Any) -> dict[str, Any]:
    summary = _empty_rtstruct_summary()
    sequences: dict[str, list[Any]] = {}
    for name in RTSTRUCT_SEQUENCE_NAMES:
        items, state = _sequence_items(dataset, name)
        sequences[name] = items
        summary["sequence_state_counts"][name][state] += 1
        summary["sequence_entry_counts"][name] += len(items)

    counts = summary["counts"]
    scalars = summary["scalars"]
    roi_entries: list[dict[str, Any]] = []
    structure_rois: dict[int, list[int]] = collections.defaultdict(list)
    for index, roi in enumerate(sequences["StructureSetROISequence"]):
        value, present = _field_value(roi, "ROINumber")
        number, status = _dicom_integer(value, present)
        counts["roi_number_status_counts"][status] += 1
        if number is not None:
            structure_rois[number].append(index)
        name_value, name_present = _field_value(roi, "ROIName")
        name = _text(name_value)
        counts["roi_name_presence_counts"][
            "MISSING" if not name_present else "PRESENT" if name else "EMPTY"
        ] += 1
        counts["roi_name_heuristic_category_counts"][_roi_name_heuristic(name)] += 1
        roi_entries.append({"number": number, "name": name})

    duplicate_roi_numbers = {
        number: indexes for number, indexes in structure_rois.items() if len(indexes) > 1
    }
    scalars["roi_number_duplicate_value_count"] += len(duplicate_roi_numbers)
    scalars["roi_entries_with_duplicate_number_count"] += sum(
        len(indexes) for indexes in duplicate_roi_numbers.values()
    )

    observation_links: dict[int, list[dict[str, Any]]] = collections.defaultdict(list)
    observation_numbers: collections.Counter[int] = collections.Counter()
    for observation in sequences["RTROIObservationsSequence"]:
        observation_number_value, observation_number_present = _field_value(
            observation, "ObservationNumber"
        )
        observation_number, observation_number_status = _dicom_integer(
            observation_number_value, observation_number_present
        )
        counts["roi_observation_number_status_counts"][observation_number_status] += 1
        if observation_number is not None:
            observation_numbers[observation_number] += 1

        reference_value, reference_present = _field_value(
            observation, "ReferencedROINumber"
        )
        reference_status, reference_number = _roi_number_link_status(
            reference_value, reference_present, structure_rois
        )
        counts["roi_observation_reference_status_counts"][reference_status] += 1

        type_value, type_present = _field_value(observation, "RTROIInterpretedType")
        type_text = _text(type_value)
        type_status = "MISSING" if not type_present else "PRESENT" if type_text else "EMPTY"
        counts["roi_observation_interpreted_type_presence_counts"][type_status] += 1
        type_category = _interpreted_type_category(type_text) if type_text else None
        if type_category:
            counts["interpreted_type_category_counts"][type_category] += 1
        if reference_status == "UNIQUE_REFERENCE" and reference_number is not None:
            observation_links[reference_number].append(
                {"type_status": type_status, "type_category": type_category}
            )

    duplicate_observation_numbers = {
        number: count for number, count in observation_numbers.items() if count > 1
    }
    scalars["duplicate_observation_number_value_count"] += len(
        duplicate_observation_numbers
    )
    scalars["observation_entries_with_duplicate_number_count"] += sum(
        duplicate_observation_numbers.values()
    )
    for observations in observation_links.values():
        if len(observations) > 1:
            scalars["unique_roi_numbers_with_multiple_observations_count"] += 1
            distinct_types = {
                (item["type_status"], item["type_category"]) for item in observations
            }
            if len(distinct_types) > 1:
                scalars["roi_numbers_with_conflicting_observation_types_count"] += 1

    for roi in roi_entries:
        number = roi["number"]
        if number is None:
            counts["roi_type_mapping_status_counts"]["ROI_NUMBER_UNRESOLVED"] += 1
            counts["roi_name_type_comparison_counts"]["ROI_NUMBER_UNRESOLVED"] += 1
            continue
        if len(structure_rois[number]) > 1:
            counts["roi_type_mapping_status_counts"]["ROI_NUMBER_DUPLICATE"] += 1
            counts["roi_name_type_comparison_counts"]["ROI_NUMBER_DUPLICATE"] += 1
            continue
        observations = observation_links.get(number, [])
        if not observations:
            counts["roi_type_mapping_status_counts"]["NO_OBSERVATION"] += 1
            counts["roi_name_type_comparison_counts"]["NO_OBSERVATION"] += 1
            continue
        if len(observations) > 1:
            counts["roi_type_mapping_status_counts"]["MULTIPLE_OBSERVATIONS_UNRESOLVED"] += 1
            counts["roi_name_type_comparison_counts"]["MULTIPLE_OBSERVATIONS_UNRESOLVED"] += 1
            continue

        observation = observations[0]
        type_status = observation["type_status"]
        type_category = observation["type_category"]
        if type_status != "PRESENT":
            mapping_status = "TYPE_" + type_status
            counts["roi_type_mapping_status_counts"][mapping_status] += 1
            counts["roi_name_type_comparison_counts"][mapping_status] += 1
            continue
        counts["roi_type_category_counts"][type_category] += 1
        counts["roi_type_mapping_status_counts"][type_category] += 1
        if type_category not in {"GTV", "CTV", "PTV", "OAR"}:
            counts["roi_name_type_comparison_counts"]["NON_TARGET_OR_UNRECOGNIZED_TYPE"] += 1
            continue
        name_category = _roi_name_heuristic(roi["name"])
        if name_category not in {"GTV-like", "CTV/PTV-like", "OAR-like"}:
            comparison = "NAME_HEURISTIC_UNRESOLVED"
        else:
            type_name_category = {
                "GTV": "GTV-like",
                "CTV": "CTV/PTV-like",
                "PTV": "CTV/PTV-like",
                "OAR": "OAR-like",
            }[type_category]
            comparison = "MATCH" if name_category == type_name_category else "CONFLICT"
        counts["roi_name_type_comparison_counts"][comparison] += 1

    roi_contour_links: dict[int, list[int]] = collections.defaultdict(list)
    for index, roi_contour in enumerate(sequences["ROIContourSequence"]):
        reference_value, reference_present = _field_value(
            roi_contour, "ReferencedROINumber"
        )
        reference_status, reference_number = _roi_number_link_status(
            reference_value, reference_present, structure_rois
        )
        counts["roi_contour_reference_status_counts"][reference_status] += 1
        if reference_status == "UNIQUE_REFERENCE" and reference_number is not None:
            roi_contour_links[reference_number].append(index)

        contour_items, contour_state = _sequence_items(roi_contour, "ContourSequence")
        counts["contour_sequence_state_counts"][contour_state] += 1
        for contour in contour_items:
            scalars["contour_item_count"] += 1
            geometry_value, geometry_present = _field_value(contour, "ContourGeometricType")
            geometry_text = _text(geometry_value).upper()
            if not geometry_present:
                geometry_status = "MISSING"
            elif not geometry_text:
                geometry_status = "EMPTY"
            elif geometry_text in CONTOUR_GEOMETRIC_TYPES:
                geometry_status = geometry_text
            else:
                geometry_status = "UNRECOGNIZED"
            counts["contour_geometric_type_counts"][geometry_status] += 1

            point_value, point_present = _field_value(contour, "NumberOfContourPoints")
            point_count, point_status = _positive_dicom_integer(point_value, point_present)
            counts["contour_point_count_status_counts"][point_status] += 1

            data_value, data_present = _field_value(contour, "ContourData")
            if not data_present:
                data_status = "DATA_MISSING"
            elif data_value is None:
                data_status = "DATA_EMPTY"
            elif isinstance(data_value, (str, bytes, bytearray)):
                data_status = "DATA_EMPTY" if not data_value else "DATA_UNREADABLE"
            else:
                try:
                    data_length = len(data_value)
                    if data_length == 0:
                        data_status = "DATA_EMPTY"
                    elif point_count is None:
                        data_status = "POINT_COUNT_UNAVAILABLE"
                    else:
                        length_matches = data_length == 3 * point_count
                        finite = all(_number(value) is not None for value in data_value)
                        if not length_matches:
                            data_status = "LENGTH_MISMATCH"
                        elif finite:
                            data_status = "LENGTH_MATCH_FINITE"
                        else:
                            data_status = "LENGTH_MATCH_NONFINITE_OR_INVALID"
                except (TypeError, ValueError, OverflowError):
                    data_status = "DATA_UNREADABLE"
            counts["contour_data_check_counts"][data_status] += 1

            if geometry_status != "POINT":
                point_geometry_status = (
                    "NOT_APPLICABLE"
                    if geometry_status in CONTOUR_GEOMETRIC_TYPES
                    else "UNRESOLVED"
                )
            elif point_count is None:
                point_geometry_status = "UNRESOLVED"
            else:
                point_geometry_status = "MATCH" if point_count == 1 else "CONFLICT"
            counts["point_geometry_consistency_counts"][point_geometry_status] += 1

            image_items, image_state = _sequence_items(contour, "ContourImageSequence")
            counts["contour_image_sequence_state_counts"][image_state] += 1
            has_contour_image_reference = False
            for image_item in image_items:
                uid_value, uid_present = _field_value(
                    image_item, "ReferencedSOPInstanceUID"
                )
                uid_text = _text(uid_value)
                if uid_present and uid_text:
                    counts["contour_image_reference_value_status_counts"]["PRESENT"] += 1
                    summary["_contour_sop_refs"].add(uid_text)
                    has_contour_image_reference = True
                else:
                    counts["contour_image_reference_value_status_counts"][
                        "MISSING" if not uid_present else "EMPTY"
                    ] += 1
            scalars["contours_with_any_image_reference_count"] += int(
                has_contour_image_reference
            )
            scalars["contour_image_reference_item_count"] += len(image_items)

    duplicate_roi_contour_links = {
        number: indexes
        for number, indexes in roi_contour_links.items()
        if len(indexes) > 1
    }
    scalars["roi_contour_duplicate_reference_value_count"] += len(
        duplicate_roi_contour_links
    )
    scalars["roi_contour_entries_with_duplicate_reference_count"] += sum(
        len(indexes) for indexes in duplicate_roi_contour_links.values()
    )
    scalars["contour_image_unique_sop_reference_count"] += len(
        summary["_contour_sop_refs"]
    )
    return summary


def _merge_rtstruct_summary(aggregate: dict[str, Any], summary: dict[str, Any]) -> None:
    for name, statuses in summary["sequence_state_counts"].items():
        aggregate["sequence_state_counts"][name].update(statuses)
    aggregate["sequence_entry_counts"].update(summary["sequence_entry_counts"])
    for name, values in summary["counts"].items():
        aggregate["counts"][name].update(values)
    aggregate["scalars"].update(summary["scalars"])
    aggregate["_contour_sop_refs"].update(summary["_contour_sop_refs"])


def _iter_rt_references(ds: Any) -> tuple[set[str], set[str], set[str]]:
    sop_refs: set[str] = set()
    series_refs: set[str] = set()
    frame_refs: set[str] = set()

    for frame_item in getattr(ds, "ReferencedFrameOfReferenceSequence", []) or []:
        frame_uid = _text(getattr(frame_item, "FrameOfReferenceUID", None))
        if frame_uid:
            frame_refs.add(frame_uid)
        for study_item in getattr(frame_item, "RTReferencedStudySequence", []) or []:
            for series_item in getattr(study_item, "RTReferencedSeriesSequence", []) or []:
                series_uid = _text(getattr(series_item, "SeriesInstanceUID", None))
                if series_uid:
                    series_refs.add(series_uid)
                for image_item in getattr(series_item, "ContourImageSequence", []) or []:
                    sop_uid = _text(getattr(image_item, "ReferencedSOPInstanceUID", None))
                    if sop_uid:
                        sop_refs.add(sop_uid)

    for roi_item in getattr(ds, "ROIContourSequence", []) or []:
        for contour_item in getattr(roi_item, "ContourSequence", []) or []:
            for image_item in getattr(contour_item, "ContourImageSequence", []) or []:
                sop_uid = _text(getattr(image_item, "ReferencedSOPInstanceUID", None))
                if sop_uid:
                    sop_refs.add(sop_uid)
    return sop_refs, series_refs, frame_refs


def _deep_parse_rtstruct(
    rt_record: dict[str, Any], counters: dict[str, Any], deadline: float
) -> dict[str, Any] | None:
    if time.monotonic() >= deadline:
        counters["time_limit_reached"] = True
        return None
    if rt_record["_size"] > MAX_RTSTRUCT_FILE_BYTES:
        counters["oversize_file_skipped"] += 1
        return None
    try:
        ds = _parse_dataset(
            rt_record["_path"],
            force=rt_record["_forced"],
            specific_tags=RTSTRUCT_TAGS,
        )
    except Exception as exc:
        counters["deep_parse_error_classes"][type(exc).__name__] += 1
        return None

    sop_refs, series_refs, frame_refs = _iter_rt_references(ds)
    summary = _summarize_rtstruct_dataset(ds)
    _merge_rtstruct_summary(counters["rtstruct_summary"], summary)

    counters["deep_parse_success"] += 1
    counters["files_without_frame_reference"] += int(not frame_refs)
    counters["files_without_series_reference"] += int(not series_refs)
    counters["files_without_sop_reference"] += int(not sop_refs)

    # The maps below exist only in process memory; none of their keys are serialized.
    return {
        "_patient": rt_record["_patient"],
        "_study": rt_record["_study"],
        "_series": rt_record["_series"],
        "_sop_refs": sop_refs,
        "_series_refs": series_refs,
        "_frame_refs": frame_refs,
        "_contour_sop_refs": summary["_contour_sop_refs"],
    }


def _reference_audit(
    rt_items: list[dict[str, Any]],
    sop_to_records: dict[str, list[dict[str, Any]]],
    series_to_records: dict[str, list[dict[str, Any]]],
    mr_series: dict[str, dict[str, Any]],
    all_headers_resolved: bool,
) -> dict[str, Any]:
    sop_status: collections.Counter[str] = collections.Counter()
    series_status: collections.Counter[str] = collections.Counter()
    non_mr_modalities: collections.Counter[str] = collections.Counter()
    patient_concordance: collections.Counter[str] = collections.Counter()
    study_concordance: collections.Counter[str] = collections.Counter()
    frame_concordance: collections.Counter[str] = collections.Counter()
    series_concordance: collections.Counter[str] = collections.Counter()
    matched_mr_sop_rt_files = matched_mr_series_rt_files = 0
    rt_files_with_t2_candidate_sop_ref = 0
    rt_files_with_t2_candidate_series_ref = 0
    t2_candidate_sop_ref_count = noncandidate_mr_sop_ref_count = 0
    t2_candidate_series_ref_count = noncandidate_mr_series_ref_count = 0
    files_with_any_image_or_series_ref = 0
    referenced_frames_with_mr_series = 0
    same_patient_pairs = same_study_pairs = same_frame_pairs = 0

    for rt in rt_items:
        sop_refs = rt["_sop_refs"]
        series_refs = rt["_series_refs"]
        frame_refs = rt["_frame_refs"]
        files_with_any_image_or_series_ref += int(bool(sop_refs or series_refs))
        has_mr_sop = False
        has_mr_series = False
        has_t2_candidate_sop = False
        has_t2_candidate_series = False

        for sop_uid in sop_refs:
            targets = sop_to_records.get(sop_uid, [])
            if not targets:
                sop_status[
                    "NOT_IN_DOWNLOADED_SUBSET" if all_headers_resolved else "UNKNOWN"
                ] += 1
                continue
            if len(targets) != 1:
                sop_status["UNKNOWN"] += 1
                continue
            target = targets[0]
            modality = target["_modality"]
            if modality in {"MISSING", "OTHER"}:
                sop_status["UNKNOWN"] += 1
                continue
            if modality != "MR":
                sop_status["MISMATCH"] += 1
                non_mr_modalities[modality] += 1
            else:
                has_mr_sop = True
                target_series_info = mr_series.get(target["_series"], {})
                if target_series_info.get("_t2_candidate", False):
                    t2_candidate_sop_ref_count += 1
                    has_t2_candidate_sop = True
                else:
                    noncandidate_mr_sop_ref_count += 1
                mismatch = False
                if rt["_patient"] and target["_patient"]:
                    if rt["_patient"] == target["_patient"]:
                        patient_concordance["MATCHED"] += 1
                    else:
                        patient_concordance["MISMATCH"] += 1
                        mismatch = True
                else:
                    patient_concordance["UNKNOWN"] += 1

                if rt["_study"] and target["_study"]:
                    study_concordance[
                        "MATCHED" if rt["_study"] == target["_study"] else "MISMATCH"
                    ] += 1
                else:
                    study_concordance["UNKNOWN"] += 1

                if target["_series"] and series_refs:
                    equal_series = target["_series"] in series_refs
                    series_concordance["MATCHED" if equal_series else "MISMATCH"] += 1
                    if not equal_series:
                        mismatch = True
                else:
                    series_concordance["UNKNOWN"] += 1

                if target["_frame"] and frame_refs:
                    equal_frame = target["_frame"] in frame_refs
                    frame_concordance["MATCHED" if equal_frame else "MISMATCH"] += 1
                    if not equal_frame:
                        mismatch = True
                else:
                    frame_concordance["UNKNOWN"] += 1
                sop_status["MISMATCH" if mismatch else "MATCHED"] += 1

        if has_mr_sop:
            matched_mr_sop_rt_files += 1
        if has_t2_candidate_sop:
            rt_files_with_t2_candidate_sop_ref += 1

        for series_uid in series_refs:
            targets = series_to_records.get(series_uid, [])
            if not targets:
                series_status[
                    "NOT_IN_DOWNLOADED_SUBSET" if all_headers_resolved else "UNKNOWN"
                ] += 1
                continue
            modalities = {target["_modality"] for target in targets}
            if len(modalities) != 1:
                series_status["UNKNOWN"] += 1
            elif modalities == {"MR"}:
                series_status["MATCHED"] += 1
                has_mr_series = True
                if mr_series.get(series_uid, {}).get("_t2_candidate", False):
                    t2_candidate_series_ref_count += 1
                    has_t2_candidate_series = True
                else:
                    noncandidate_mr_series_ref_count += 1
            elif modalities.issubset({"MISSING", "OTHER"}):
                series_status["UNKNOWN"] += 1
            else:
                series_status["MISMATCH"] += 1
                non_mr_modalities.update(modalities)
        if has_mr_series:
            matched_mr_series_rt_files += 1
        if has_t2_candidate_series:
            rt_files_with_t2_candidate_series_ref += 1

        for frame_uid in frame_refs:
            if any(
                frame_uid in series_info["frames"]
                for series_info in mr_series.values()
            ):
                referenced_frames_with_mr_series += 1

        # Co-occurrence is intentionally kept separate from direct DICOM references.
        for series_info in mr_series.values():
            if rt["_patient"] and rt["_patient"] in series_info["patients"]:
                same_patient_pairs += 1
            if rt["_study"] and rt["_study"] in series_info["studies"]:
                same_study_pairs += 1
            if frame_refs and frame_refs.intersection(series_info["frames"]):
                same_frame_pairs += 1

    return {
        "instance_reference_counting_unit": (
            "unique referenced SOP Instance UID per RTSTRUCT, summed across RTSTRUCT files"
        ),
        "instance_reference_status_counts": {
            status: int(sop_status[status])
            for status in (
                "MATCHED",
                "MISMATCH",
                "NOT_IN_DOWNLOADED_SUBSET",
                "UNKNOWN",
            )
        },
        "series_reference_status_counts": {
            status: int(series_status[status])
            for status in (
                "MATCHED",
                "MISMATCH",
                "NOT_IN_DOWNLOADED_SUBSET",
                "UNKNOWN",
            )
        },
        "matched_non_mr_target_modality_counts": dict(sorted(non_mr_modalities.items())),
        "direct_sop_reference_to_mr_t2_candidate_counts": {
            "t2_candidate_series": t2_candidate_sop_ref_count,
            "not_flagged_as_t2_candidate": noncandidate_mr_sop_ref_count,
        },
        "direct_series_reference_to_mr_t2_candidate_counts": {
            "t2_candidate_series": t2_candidate_series_ref_count,
            "not_flagged_as_t2_candidate": noncandidate_mr_series_ref_count,
        },
        "patient_id_concordance_counts": dict(sorted(patient_concordance.items())),
        "study_instance_uid_concordance_counts": dict(sorted(study_concordance.items())),
        "referenced_series_uid_concordance_counts": dict(sorted(series_concordance.items())),
        "referenced_frame_uid_concordance_counts": dict(sorted(frame_concordance.items())),
        "rtstruct_file_count_with_any_local_mr_sop_reference": matched_mr_sop_rt_files,
        "rtstruct_file_count_with_any_local_mr_series_reference": matched_mr_series_rt_files,
        "rtstruct_file_count_with_direct_t2_candidate_sop_reference": rt_files_with_t2_candidate_sop_ref,
        "rtstruct_file_count_with_direct_t2_candidate_series_reference": rt_files_with_t2_candidate_series_ref,
        "rtstruct_file_count_with_any_image_or_series_reference": files_with_any_image_or_series_ref,
        "referenced_frame_count_with_local_mr_series": referenced_frames_with_mr_series,
        "weak_cooccurrence_mr_series_pair_counts": {
            "same_patient_id": same_patient_pairs,
            "same_study_instance_uid": same_study_pairs,
            "same_frame_of_reference_uid": same_frame_pairs,
            "interpretation": "co-occurrence only; not a substitute for direct SOP/Series reference",
        },
    }


def run_audit(args: argparse.Namespace) -> dict[str, Any]:
    started = time.monotonic()
    deadline = started + args.time_limit_seconds
    root = Path(os.path.abspath(os.path.expanduser(args.data_dir)))
    ancestor = root
    while True:
        ancestor_stat = os.stat(ancestor, follow_symlinks=False)
        if _is_reparse(ancestor_stat):
            raise RuntimeError("input path contains a reparse point")
        if ancestor.parent == ancestor:
            break
        ancestor = ancestor.parent
    if not root.is_dir():
        raise FileNotFoundError("input directory unavailable")
    output = Path(args.output).resolve()
    try:
        if os.path.commonpath((str(root), str(output))) == str(root):
            raise ValueError("output must be outside the source directory")
    except ValueError as exc:
        if str(exc) == "output must be outside the source directory":
            raise
        raise ValueError("input and output paths are not comparable") from None

    fs = inventory(root, deadline)
    if fs["reparse_or_symlink_entries_skipped"]:
        raise RuntimeError("reparse or symlink entry detected; scan halted")

    selected, sample_method = _sample_candidates(fs["candidates"], args.max_headers)
    modality_counts: collections.Counter[str] = collections.Counter()
    sop_class_counts: collections.Counter[str] = collections.Counter()
    parse_errors: collections.Counter[str] = collections.Counter()
    missing_counts: collections.Counter[str] = collections.Counter()
    spatial_counts: collections.Counter[str] = collections.Counter()
    spatial_plausibility: collections.Counter[str] = collections.Counter()
    patient_ids: set[str] = set()
    study_uids: set[str] = set()
    series_uids: set[str] = set()
    frame_uids: set[str] = set()
    patient_studies: dict[str, set[str]] = collections.defaultdict(set)
    study_series: dict[str, set[str]] = collections.defaultdict(set)
    sop_to_records: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    series_to_records: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    series_info: dict[str, dict[str, Any]] = {}
    records: list[dict[str, Any]] = []
    rt_records: list[dict[str, Any]] = []
    headers_attempted = standard_parse_count = forced_parse_count = 0
    force_attempts_left = FORCED_PARSE_TRIAL_LIMIT
    oversized_image_files = 0

    for path, size in selected:
        if headers_attempted >= args.max_headers or time.monotonic() >= deadline:
            break
        headers_attempted += 1
        if size > MAX_IMAGE_FILE_BYTES:
            oversized_image_files += 1
            continue
        try:
            ds = _parse_dataset(path, specific_tags=BASE_TAGS)
            forced = False
            standard_parse_count += 1
        except Exception as exc:
            parse_errors[type(exc).__name__] += 1
            if force_attempts_left <= 0:
                continue
            force_attempts_left -= 1
            try:
                ds = _parse_dataset(path, force=True, specific_tags=BASE_TAGS)
                forced = True
                forced_parse_count += 1
            except Exception as force_exc:
                parse_errors["FORCE_" + type(force_exc).__name__] += 1
                continue

        record = _build_record(path, size, ds, forced)
        records.append(record)
        modality_counts[record["_modality"]] += 1
        sop_class_counts[record["_sop_class"]] += 1
        for name, present in record["_present"].items():
            if not present:
                missing_counts[name] += 1
        for key, value in (
            ("_patient", patient_ids),
            ("_study", study_uids),
            ("_series", series_uids),
            ("_frame", frame_uids),
        ):
            if record[key]:
                value.add(record[key])
        if record["_patient"] and record["_study"]:
            patient_studies[record["_patient"]].add(record["_study"])
        if record["_study"] and record["_series"]:
            study_series[record["_study"]].add(record["_series"])
        if record["_sop"]:
            sop_to_records[record["_sop"]].append(record)
        if record["_series"]:
            series_to_records[record["_series"]].append(record)
            info = series_info.setdefault(
                record["_series"],
                {
                    "modalities": set(),
                    "patients": set(),
                    "studies": set(),
                    "frames": set(),
                    "texts": set(),
                    "echo_times": [],
                },
            )
            info["modalities"].add(record["_modality"])
            if record["_patient"]:
                info["patients"].add(record["_patient"])
            if record["_study"]:
                info["studies"].add(record["_study"])
            if record["_frame"]:
                info["frames"].add(record["_frame"])
            if record["_series_text"]:
                info["texts"].add(record["_series_text"])
            if record["_echo_time"] is not None:
                info["echo_times"].append(record["_echo_time"])
        if record["_modality"] == "MR":
            for name, present in record["_spatial_present"].items():
                if present:
                    spatial_counts[name] += 1
            if all(
                record["_spatial_present"].get(name, False)
                for name in CORE_MR_GEOMETRY_FIELDS
            ):
                spatial_plausibility["core_geometry_fields_present"] += 1
            if all(record["_spatial_present"].values()):
                spatial_plausibility["all_selected_geometry_fields_present"] += 1
            if record["_orientation_plausible"]:
                spatial_plausibility["orientation_vectors_plausible"] += 1
            if record["_pixel_spacing_plausible"]:
                spatial_plausibility["pixel_spacing_plausible"] += 1
            if record["_position_finite"]:
                spatial_plausibility["image_position_finite_3_values"] += 1
            if record["_dimensions_present"]:
                spatial_plausibility["rows_columns_positive"] += 1
            if record["_slice_thickness_plausible"]:
                spatial_plausibility["slice_thickness_in_range"] += 1
            if record["_slice_spacing_plausible"]:
                spatial_plausibility["spacing_between_slices_in_range"] += 1
        if (
            record["_modality"] == "RTSTRUCT"
            or record["_sop_class"] == "RT Structure Set Storage"
        ):
            rt_records.append(record)

    mr_series = {
        uid: info for uid, info in series_info.items() if info["modalities"] == {"MR"}
    }
    text_t2_series = 0
    echo_t2_series = 0
    echo_supported_series = 0
    for info in mr_series.values():
        text = " ".join(info["texts"])
        text_signal = bool(T2_TOKEN.search(text))
        spin_echo = bool(SPIN_ECHO_TOKEN.search(text))
        long_echo = any(value >= 50 for value in info["echo_times"])
        text_t2_series += int(text_signal)
        echo_signal = spin_echo and long_echo
        echo_t2_series += int(echo_signal)
        echo_supported_series += int(text_signal or echo_signal)
        info["_t2_text_signal"] = text_signal
        info["_t2_echo_signal"] = echo_signal
        info["_t2_candidate"] = text_signal or echo_signal

    patient_study_counts = [len(studies) for studies in patient_studies.values()]
    series_instance_counts = [
        len(items) for items in series_to_records.values() if items
    ]
    duplicate_sop_uid_count = sum(
        1 for items in sop_to_records.values() if len(items) > 1
    )

    rt_counters: dict[str, Any] = {
        "deep_parse_success": 0,
        "oversize_file_skipped": 0,
        "deep_parse_error_classes": collections.Counter(),
        "rtstruct_summary": _empty_rtstruct_summary(),
        "files_without_frame_reference": 0,
        "files_without_series_reference": 0,
        "files_without_sop_reference": 0,
        "time_limit_reached": False,
    }
    rt_items = []
    for rt_record in rt_records:
        item = _deep_parse_rtstruct(rt_record, rt_counters, deadline)
        if item is not None:
            rt_items.append(item)
        if rt_counters["time_limit_reached"]:
            break

    all_headers_resolved = bool(
        fs["complete"]
        and headers_attempted == len(fs["candidates"])
        and not parse_errors
        and not oversized_image_files
    )
    references = _reference_audit(
        rt_items,
        sop_to_records,
        series_to_records,
        mr_series,
        all_headers_resolved and rt_counters["deep_parse_success"] == len(rt_records),
    )

    final_fs = inventory(root, deadline)
    before = fs["snapshots"]
    after = final_fs["snapshots"]
    common = set(before).intersection(after)
    unchanged = sum(1 for path in common if before[path] == after[path])
    changed = sum(1 for path in common if before[path] != after[path])
    removed = len(set(before) - set(after))
    added = len(set(after) - set(before))
    source_unchanged = bool(
        fs["complete"]
        and final_fs["complete"]
        and changed == 0
        and removed == 0
        and added == 0
    )

    full_header_coverage = bool(
        sample_method == "FULL_LOCAL_CANDIDATE_SET"
        and headers_attempted == len(fs["candidates"])
    )
    limits_ok = (
        time.monotonic() < deadline
        and headers_attempted <= args.max_headers
        and not rt_counters["time_limit_reached"]
    )
    audit_status = (
        "COMPLETE"
        if full_header_coverage
        and limits_ok
        and source_unchanged
        and not parse_errors
        and not rt_counters["deep_parse_error_classes"]
        and rt_counters["deep_parse_success"] == len(rt_records)
        and not oversized_image_files
        and not rt_counters["oversize_file_skipped"]
        else "PARTIAL"
    )
    if not fs["complete"] or fs["reparse_or_symlink_entries_skipped"]:
        audit_status = "BLOCKED"

    total_mr_instances = modality_counts["MR"]
    total_rtstruct_instances = len(rt_records)
    result = {
        "task_id": TASK_ID,
        "plan_revision": PLAN_REVISION,
        "audit_status": audit_status,
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_attribution": {
            "dataset_reported_by_user": "IDC CC-Tumor-Heterogeneity manual download",
            "local_collection_membership_verified": False,
            "clinical_workbook_read": False,
        },
        "filesystem": {
            "source_path_redacted": True,
            "inventory_complete": fs["complete"],
            "file_count": fs["file_count"],
            "directory_count": fs["directory_count"],
            "total_bytes": fs["total_bytes"],
            "zero_byte_file_count": fs["zero_byte_file_count"],
            "extension_counts": fs["extension_counts"],
            "dicom_candidate_count": fs["dicom_candidate_count"],
            "reparse_or_symlink_entries_skipped": fs[
                "reparse_or_symlink_entries_skipped"
            ],
            "special_entry_count": fs["special_entry_count"],
            "metadata_error_count": fs["metadata_error_count"],
            "metadata_error_classes": fs["metadata_error_classes"],
        },
        "coverage": {
            "header_files_attempted": headers_attempted,
            "header_files_limit": args.max_headers,
            "coverage_method": sample_method,
            "full_local_candidate_coverage": full_header_coverage,
            "standard_parse_count": standard_parse_count,
            "forced_parse_uncertain_count": forced_parse_count,
            "parse_failure_count": sum(parse_errors.values()),
            "parse_failure_classes": dict(sorted(parse_errors.items())),
            "oversized_image_header_skipped_count": oversized_image_files,
            "time_limit_seconds": args.time_limit_seconds,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "pixel_data_decoded": False,
        },
        "tool": {
            "reader": "pydicom",
            "reader_version": pydicom.__version__,
            "python_version": sys.version.split()[0],
            "read_mode": "stop_before_pixels; selected metadata tags only",
            "forced_parse_trial_limit": FORCED_PARSE_TRIAL_LIMIT,
            "maximum_image_file_bytes_for_header_parse": MAX_IMAGE_FILE_BYTES,
            "maximum_rtstruct_file_bytes_for_deep_parse": MAX_RTSTRUCT_FILE_BYTES,
        },
        "dicom": {
            "parsed_file_count": len(records),
            "modality_counts": dict(sorted(modality_counts.items())),
            "sop_class_counts": dict(sorted(sop_class_counts.items())),
            "distinct_patient_id_values": len(patient_ids),
            "patient_id_missing_count": missing_counts["PatientID"],
            "distinct_study_instance_uid_count": len(study_uids),
            "study_instance_uid_missing_count": missing_counts["StudyInstanceUID"],
            "distinct_series_instance_uid_count": len(series_uids),
            "series_instance_uid_missing_count": missing_counts["SeriesInstanceUID"],
            "distinct_frame_of_reference_uid_count": len(frame_uids),
            "frame_of_reference_uid_missing_count": missing_counts[
                "FrameOfReferenceUID"
            ],
            "sop_instance_uid_missing_count": missing_counts["SOPInstanceUID"],
            "sop_class_uid_missing_count": missing_counts["SOPClassUID"],
            "modality_missing_count": missing_counts["Modality"],
            "duplicate_sop_instance_uid_value_count": duplicate_sop_uid_count,
            "patient_id_values_with_multiple_studies": sum(
                1 for count in patient_study_counts if count > 1
            ),
            "study_instance_uid_values_with_multiple_series": sum(
                1 for study, values in study_series.items() if len(values) > 1
            ),
            "instances_per_series_summary": {
                "series_count": len(series_instance_counts),
                "minimum": min(series_instance_counts) if series_instance_counts else None,
                "median": (
                    sorted(series_instance_counts)[len(series_instance_counts) // 2]
                    if series_instance_counts
                    else None
                ),
                "maximum": max(series_instance_counts) if series_instance_counts else None,
            },
        },
        "mr": {
            "instance_count": total_mr_instances,
            "series_count": len(mr_series),
            "series_text_t2_signal_count": text_t2_series,
            "series_spin_echo_and_echo_time_signal_count": echo_t2_series,
            "heuristic_t2_candidate_series_count": echo_supported_series,
            "t2_candidate_rule": (
                "MR series text contains a T2 token, or contains a spin-echo token "
                "and at least one EchoTime >= 50 ms; candidate only, not sequence confirmation"
            ),
            "spatial_tag_presence_counts": dict(sorted(spatial_counts.items())),
            "spatial_tag_missing_counts": {
                name: max(0, total_mr_instances - spatial_counts[name])
                for name in sorted(MR_SPATIAL_TAGS)
            },
            "echo_time_present_instance_count": sum(
                1
                for record in records
                if record["_modality"] == "MR" and record["_echo_time"] is not None
            ),
            "spatial_field_plausibility_counts": dict(
                sorted(spatial_plausibility.items())
            ),
            "geometry_checks_are_metadata_only": True,
        },
        "rtstruct": {
            "instance_count": total_rtstruct_instances,
            "deep_parse_success_count": rt_counters["deep_parse_success"],
            "deep_parse_failure_classes": dict(
                sorted(rt_counters["deep_parse_error_classes"].items())
            ),
            "oversize_file_skipped_count": rt_counters["oversize_file_skipped"],
            "sequence_state_counts": {
                name: dict(sorted(statuses.items()))
                for name, statuses in sorted(
                    rt_counters["rtstruct_summary"]["sequence_state_counts"].items()
                )
            },
            "sequence_entry_counts": dict(
                sorted(rt_counters["rtstruct_summary"]["sequence_entry_counts"].items())
            ),
            "aggregate_counts": {
                name: dict(sorted(values.items()))
                for name, values in sorted(
                    rt_counters["rtstruct_summary"]["counts"].items()
                )
            },
            "aggregate_totals": dict(
                sorted(rt_counters["rtstruct_summary"]["scalars"].items())
            ),
            "roi_type_source": "RTROIObservationsSequence.RTROIInterpretedType",
            "roi_type_link": (
                "RTROIObservationsSequence.ReferencedROINumber to unique "
                "StructureSetROISequence.ROINumber"
            ),
            "roi_name_heuristic_is_separate_from_dicom_type": True,
            "r1_correction": {
                "r1_type_lookup_sequence_was_incorrect": "StructureSetROISequence",
                "r2_type_lookup_sequence": "RTROIObservationsSequence",
                "r1_interpreted_type_absence_claim_valid": False,
                "r1_combined_roi_category_counts_valid": False,
                "r1_roi_contour_entry_count_proves_geometry_or_mask": False,
            },
            "files_without_frame_reference_count": rt_counters[
                "files_without_frame_reference"
            ],
            "files_without_series_reference_count": rt_counters[
                "files_without_series_reference"
            ],
            "files_without_sop_reference_count": rt_counters[
                "files_without_sop_reference"
            ],
        },
        "reference_audit": references,
        "source_snapshot_check": {
            "rechecked_complete": final_fs["complete"],
            "file_metadata_unchanged_count": unchanged,
            "file_metadata_changed_count": changed,
            "file_removed_count": removed,
            "file_added_count": added,
            "unchanged_definition": "relative source file path, byte size, last-write time, and file attributes",
            "all_source_files_unchanged_by_metadata": source_unchanged,
        },
        "privacy": {
            "patient_values_serialized": False,
            "uid_values_serialized": False,
            "file_names_or_paths_serialized": False,
            "roi_names_serialized": False,
            "source_file_hashes_serialized": False,
            "private_case_index_created": False,
        },
        "research_boundary": {
            "image_pixels_decoded": False,
            "volume_reconstruction_run": False,
            "rtstruct_to_mask_rasterization_run": False,
            "registration_or_resampling_run": False,
            "radiomics_or_model_run": False,
            "r0_complete": False,
        },
    }
    return result


def _write_json(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, help="Existing local DICOM input directory")
    parser.add_argument("--output", required=True, help="Aggregate JSON output outside the input directory")
    parser.add_argument("--max-headers", type=int, default=MAX_HEADER_FILES)
    parser.add_argument("--time-limit-seconds", type=int, default=MAX_SECONDS)
    args = parser.parse_args()
    if not 1 <= args.max_headers <= MAX_HEADER_FILES:
        parser.error(f"--max-headers must be between 1 and {MAX_HEADER_FILES}")
    if not 1 <= args.time_limit_seconds <= MAX_SECONDS:
        parser.error(f"--time-limit-seconds must be between 1 and {MAX_SECONDS}")

    output = Path(args.output).resolve()
    result = run_audit(args)
    _write_json(output, result)
    # No paths, identifiers, names, or raw parser messages are printed.
    print(
        json.dumps(
            {
                "task_id": TASK_ID,
                "audit_status": result["audit_status"],
                "file_count": result["filesystem"]["file_count"],
                "total_bytes": result["filesystem"]["total_bytes"],
                "header_files_attempted": result["coverage"]["header_files_attempted"],
                "parsed_file_count": result["dicom"]["parsed_file_count"],
                "modality_counts": result["dicom"]["modality_counts"],
                "rtstruct_count": result["rtstruct"]["instance_count"],
                "elapsed_seconds": result["coverage"]["elapsed_seconds"],
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return 0 if result["audit_status"] == "COMPLETE" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        # Do not echo exception text because parser/library messages may contain a source path.
        print(
            json.dumps(
                {
                    "task_id": TASK_ID,
                    "audit_status": "BLOCKED",
                    "error_class": type(exc).__name__,
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        raise SystemExit(2)
