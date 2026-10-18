#!/usr/bin/env python3
"""Read-only, aggregate-only IDC v25 series and object inventory audit.

The official index, manifest prefixes, DICOM UIDs, file names, and S3 keys are
kept in process memory. Public output contains aggregate counts and source/version
evidence only; UID/prefix details are written solely to a validated ignored local
directory when explicitly requested. DICOM PixelData is never read and S3 object
bodies are never fetched.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import os
import platform
import stat
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable, Mapping

import duckdb
import pydicom
import pyarrow
import pyarrow.parquet as pq


TASK_ID = "CMRL-06"
PLAN_REVISION = "r2"
COLLECTION_ID = "cc_tumor_heterogeneity"
COLLECTION_NAME = "CC-Tumor-Heterogeneity"
EXPECTED_MODALITIES = ("MR", "CT", "PT", "REG", "RTSTRUCT")
UNKNOWN_MODALITY = "UNKNOWN/INVALID"
EXPECTED_INDEX_VERSION = "25.0.0-0-gdbf7fd0"
EXPECTED_INDEX_SHA256 = "450598d6493d800334a8e1ece1fda4a5ec04ca1bd2f73309058f0531f8155572"
EXPECTED_COLLECTIONS_SHA256 = "97e5ac3bba296cb3f4e9d87545231275aad66fc89ba07262b7914e72e857489c"
EXPECTED_MANIFEST_SHA256 = "f56073583ad4cf931a9a46fac83af2672f5b0248ebcc2a94406e9f662508ee79"
EXPECTED_MANIFEST_BYTES = 52_045
AUTHORIZED_PROJECT_ROOT = Path("D:/CS/CMRL")
AUTHORIZED_DATA_ROOT = Path("D:/CS/CMRL/data/raw/tcia/ccth_idc_v25_full")
AUTHORIZED_MANUAL_ROOT = Path("D:/CS/CMRL/data/raw/tcia/ccth_manual")
R1_ACCEPTED_MODALITY_BASELINE = {
    "expected_series": 821,
    "local_matched_series": 806,
    "missing_series": 15,
    "equal_count_series": 748,
    "partial_shortage_series": 58,
    "all_shortage_series": 15,
    "excess_series": 0,
    "shortage_series_total": 73,
    "expected_instances": 131_556,
    "observed_unique_instances": 130_424,
    "shortage_instances": 1_132,
    "excess_instances": 0,
}
INDEX_REQUIRED_COLUMNS = {
    "collection_id", "SeriesInstanceUID", "instanceCount", "series_aws_url",
    "Modality", "StudyInstanceUID", "series_size_MB", "crdc_series_uuid",
    "series_init_idc_version", "series_revised_idc_version",
}
MAX_LOCAL_FILES = 150_000
MAX_HEADER_SECONDS = 20 * 60
MAX_LIST_REQUESTS = 2_000
MAX_LIST_RESPONSE_BYTES = 256 * 1024 * 1024
MAX_LIST_SECONDS = 30 * 60
S3_BUCKET = "idc-open-data"


class AuditBlocked(RuntimeError):
    """A sanitized reason that prevents unsafe or unsupported audit claims."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_parquet(
    path: Path, expected_sha256: str, expected_version: str,
    required_columns: set[str] | None = None,
) -> dict[str, Any]:
    if not path.is_file():
        raise AuditBlocked("OFFICIAL_INDEX_FILE_UNAVAILABLE")
    actual_sha = sha256_file(path)
    metadata = pq.read_metadata(path)
    key_values = metadata.metadata or {}
    versions = {
        key.decode("utf-8", "replace"): value.decode("utf-8", "replace")
        for key, value in key_values.items()
        if b"version" in key.lower()
    }
    index_version = versions.get("idc_index_data_version")
    columns = set(metadata.schema.names)
    required = INDEX_REQUIRED_COLUMNS if required_columns is None else required_columns
    return {
        "sha256": actual_sha,
        "verified": actual_sha == expected_sha256 and index_version == expected_version,
        "sha256_matches_official_sidecar": actual_sha == expected_sha256,
        "index_data_version": index_version,
        "expected_version": expected_version,
        "row_count": metadata.num_rows,
        "column_count": len(columns),
        "required_columns_present": required <= columns,
        "missing_required_column_count": len(required - columns),
        "file_bytes": path.stat().st_size,
    }


def normalize_series_url(value: str | None) -> str | None:
    """Return a normalized S3 prefix only for the authorized public bucket."""
    if not value or not isinstance(value, str):
        return None
    parsed = urllib.parse.urlsplit(value.strip())
    if parsed.scheme.lower() != "s3" or parsed.netloc != S3_BUCKET:
        return None
    if parsed.query or parsed.fragment or parsed.username or parsed.password:
        return None
    path = parsed.path.strip("/")
    if not path or any(part in {".", ".."} for part in path.split("/")):
        return None
    return path


def map_series_prefixes(
    manifest_prefixes: Iterable[str], index_rows: Iterable[Mapping[str, Any]]
) -> tuple[dict[str, Any], dict[str, str], dict[str, str]]:
    """Map manifest prefixes to Series UIDs; private identifiers stay in memory."""
    manifest = set(manifest_prefixes)
    prefix_uids: dict[str, set[str]] = collections.defaultdict(set)
    uid_prefixes: dict[str, set[str]] = collections.defaultdict(set)
    prefix_row_counts: collections.Counter[str] = collections.Counter()
    uid_row_counts: collections.Counter[str] = collections.Counter()
    invalid_url_rows = 0
    invalid_uid_rows = 0
    bucket_or_url_mismatch_rows = 0
    outside_manifest_url_rows = 0
    ambiguous_url_rows = 0
    for row in index_rows:
        uid = str(row.get("SeriesInstanceUID") or "").strip()
        if not uid:
            invalid_uid_rows += 1
            continue
        uid_row_counts[uid] += 1
        prefix = normalize_series_url(row.get("series_aws_url"))
        if prefix is None:
            invalid_url_rows += 1
            bucket_or_url_mismatch_rows += 1
            continue
        path_segments = prefix.split("/")
        candidates = {
            "/".join(path_segments[:index])
            for index in range(1, len(path_segments) + 1)
        } & manifest
        if len(candidates) != 1:
            if candidates:
                ambiguous_url_rows += 1
            else:
                outside_manifest_url_rows += 1
            continue
        source_prefix = next(iter(candidates))
        prefix_row_counts[source_prefix] += 1
        prefix_uids[source_prefix].add(uid)
        uid_prefixes[uid].add(source_prefix)

    unique_mapping = {
        prefix: next(iter(uids))
        for prefix, uids in prefix_uids.items()
        if len(uids) == 1
    }
    mapped = {prefix for prefix in manifest if prefix in unique_mapping}
    ambiguous = {prefix for prefix in manifest if len(prefix_uids.get(prefix, ())) > 1}
    unique_index_uids = set(uid_row_counts)
    index_not_in_manifest = {
        uid for uid in unique_index_uids
        if not any(prefix in manifest for prefix in uid_prefixes.get(uid, ()))
    }
    mapping_complete = (
        len(mapped) == len(manifest)
        and not ambiguous
        and len(unique_index_uids) == len(index_rows)
        and invalid_url_rows == 0
        and invalid_uid_rows == 0
        and outside_manifest_url_rows == 0
        and ambiguous_url_rows == 0
        and len(unique_mapping) == len(index_rows)
        and len({unique_mapping[p] for p in mapped}) == len(mapped)
    )
    summary = {
        "manifest_prefix_count": len(manifest),
        "index_series_row_count": len(index_rows),
        "index_unique_series_uid_count": len(unique_index_uids),
        "mapped_unique_prefix_count": len(mapped),
        "unmapped_prefix_count": len(manifest - set(unique_mapping) - ambiguous),
        "ambiguous_prefix_count": len(ambiguous),
        "index_series_not_in_manifest_count": len(index_not_in_manifest),
        "duplicate_index_series_uid_count": sum(n > 1 for n in uid_row_counts.values()),
        "duplicate_index_prefix_count": sum(n > 1 for n in prefix_row_counts.values()),
        "invalid_series_uid_row_count": invalid_uid_rows,
        "invalid_or_wrong_bucket_url_row_count": bucket_or_url_mismatch_rows,
        "index_url_outside_manifest_prefix_row_count": outside_manifest_url_rows,
        "ambiguous_index_url_prefix_row_count": ambiguous_url_rows,
        "mapping_status": "MAPPING_VERIFIED" if mapping_complete else "MAPPING_PARTIAL",
    }
    uid_to_prefix = {
        uid: next(iter(prefixes))
        for uid, prefixes in uid_prefixes.items()
        if len(prefixes) == 1
    }
    return summary, unique_mapping, uid_to_prefix


def compare_series_instances(
    rows: Iterable[Mapping[str, Any]], local: Mapping[str, Any], mapping_verified: bool
) -> dict[str, Any]:
    expected: dict[str, int] = {}
    invalid_expected = 0
    for row in rows:
        uid = str(row.get("SeriesInstanceUID") or "").strip()
        try:
            count = int(row.get("instanceCount"))
        except (TypeError, ValueError):
            invalid_expected += 1
            continue
        if not uid or count <= 0 or uid in expected:
            invalid_expected += 1
            continue
        expected[uid] = count
    observed = local["unique_sop_count_by_series"]
    missing = {uid for uid in expected if observed.get(uid, 0) == 0}
    matched = {uid for uid in expected if observed.get(uid, 0) > 0}
    shortage_by_series = {
        uid: max(expected[uid] - observed.get(uid, 0), 0) for uid in expected
    }
    excess_by_series = {
        uid: max(observed.get(uid, 0) - expected[uid], 0) for uid in expected
    }
    shortages = sum(shortage_by_series.values())
    excess = sum(excess_by_series.values())
    return {
        "status": (
            "NOT_VERIFIED" if not mapping_verified or invalid_expected
            else "INSTANCE_COUNT_GAPS_FOUND" if missing or shortages or excess
            else "SERIES_INSTANCE_COUNTS_MATCHED"
        ),
        "expected_series_count": len(expected),
        "locally_matched_series_count": len(matched),
        "missing_series_count": len(missing),
        "unexpected_local_series_count": len(set(observed) - set(expected)),
        "series_with_instance_shortage_count": sum(v > 0 for v in shortage_by_series.values()),
        "series_with_instance_excess_count": sum(v > 0 for v in excess_by_series.values()),
        "total_expected_instances": sum(expected.values()),
        "total_observed_instances_in_expected_series": sum(observed.get(uid, 0) for uid in expected),
        "sum_shortage": shortages,
        "sum_excess": excess,
        "count_equal_series": sum(observed.get(uid, 0) == count for uid, count in expected.items()),
        "invalid_expected_instance_count_rows": invalid_expected,
    }


def _normalized_modality(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().upper()
    return text if text in EXPECTED_MODALITIES else None


def _empty_modality_summary() -> dict[str, int]:
    return {
        "expected_series": 0,
        "expected_instances": 0,
        "local_matched_series": 0,
        "missing_series": 0,
        "equal_count_series": 0,
        "partial_shortage_series": 0,
        "all_shortage_series": 0,
        "excess_series": 0,
        "shortage_series_total": 0,
        "observed_unique_instances": 0,
        "shortage_instances": 0,
        "excess_instances": 0,
        "header_modality_missing_or_invalid_series": 0,
        "header_modality_conflict_series": 0,
        "mixed_header_modality_series": 0,
        "unexpected_local_series": 0,
        "unexpected_local_unique_instances": 0,
    }


def compare_series_instances_by_modality(
    rows: Iterable[Mapping[str, Any]],
    local: Mapping[str, Any],
    mapping_verified: bool,
    expected_baseline: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """Classify unique SOP counts by authoritative v25 modality, without identifiers."""
    buckets = {modality: _empty_modality_summary() for modality in EXPECTED_MODALITIES}
    buckets[UNKNOWN_MODALITY] = _empty_modality_summary()
    observed = local["unique_sop_count_by_series"]
    header_modalities = local.get("header_modalities_by_series", {})
    modality_issue_files = local.get("modality_header_missing_or_invalid_file_count_by_series", {})
    local_series_files = local.get("series_file_count_by_series", {})
    expected_by_uid: dict[str, tuple[int, str]] = {}
    invalid_expected_rows = 0

    for row in rows:
        uid = str(row.get("SeriesInstanceUID") or "").strip()
        try:
            expected = int(row.get("instanceCount"))
        except (TypeError, ValueError):
            invalid_expected_rows += 1
            continue
        if not uid or expected <= 0 or uid in expected_by_uid:
            invalid_expected_rows += 1
            continue
        modality = _normalized_modality(row.get("Modality")) or UNKNOWN_MODALITY
        expected_by_uid[uid] = (expected, modality)

    for uid, (expected, modality) in expected_by_uid.items():
        bucket = buckets[modality]
        count = int(observed.get(uid, 0))
        bucket["expected_series"] += 1
        bucket["expected_instances"] += expected
        bucket["local_matched_series"] += int(count > 0)
        bucket["observed_unique_instances"] += count
        if count == 0:
            bucket["missing_series"] += 1
            bucket["all_shortage_series"] += 1
            bucket["shortage_instances"] += expected
        elif count == expected:
            bucket["equal_count_series"] += 1
        elif count < expected:
            bucket["partial_shortage_series"] += 1
            bucket["shortage_instances"] += expected - count
        else:
            bucket["excess_series"] += 1
            bucket["excess_instances"] += count - expected

        modalities = {
            normalized
            for value in header_modalities.get(uid, ())
            if (normalized := _normalized_modality(value)) is not None
        }
        has_local_files = uid in local_series_files
        has_header_issue = has_local_files and (
            not modalities or int(modality_issue_files.get(uid, 0)) > 0
        )
        bucket["header_modality_missing_or_invalid_series"] += int(has_header_issue)
        bucket["mixed_header_modality_series"] += int(len(modalities) > 1)
        if modality != UNKNOWN_MODALITY and any(value != modality for value in modalities):
            bucket["header_modality_conflict_series"] += 1

    expected_uids = set(expected_by_uid)
    local_series_uids = set(observed) | set(local_series_files)
    unexpected_uids = local_series_uids - expected_uids
    unexpected_instances = sum(int(observed[uid]) for uid in unexpected_uids)
    buckets[UNKNOWN_MODALITY]["unexpected_local_series"] = len(unexpected_uids)
    buckets[UNKNOWN_MODALITY]["unexpected_local_unique_instances"] = unexpected_instances
    buckets[UNKNOWN_MODALITY]["observed_unique_instances"] += unexpected_instances

    additive_fields = (
        "expected_series",
        "expected_instances",
        "local_matched_series",
        "missing_series",
        "equal_count_series",
        "partial_shortage_series",
        "all_shortage_series",
        "excess_series",
        "shortage_series_total",
        "observed_unique_instances",
        "shortage_instances",
        "excess_instances",
    )
    for bucket in buckets.values():
        bucket["shortage_series_total"] = (
            bucket["missing_series"] + bucket["partial_shortage_series"]
        )
    totals = {
        field: sum(bucket[field] for bucket in buckets.values())
        for field in additive_fields
    }
    header_issue_uids = {
        uid
        for uid in set(expected_by_uid) | set(local_series_files)
        if uid in local_series_files
        and (
            not header_modalities.get(uid)
            or int(modality_issue_files.get(uid, 0)) > 0
        )
    }
    conflict_series = sum(
        bucket["header_modality_conflict_series"] for bucket in buckets.values()
    )
    mixed_series = sum(
        bucket["mixed_header_modality_series"] for bucket in buckets.values()
    )
    unknown_expected_series = buckets[UNKNOWN_MODALITY]["expected_series"]
    unassignable_header_issues = {
        "parse_error_file_count": int(local.get("parse_error_count", 0)),
        "missing_series_uid_file_count": int(local.get("missing_series_uid_file_count", 0)),
        "missing_sop_uid_file_count": int(local.get("missing_sop_uid_file_count", 0)),
    }
    has_unassignable_header_issue = any(unassignable_header_issues.values())

    arithmetic_consistent = bool(
        totals["expected_series"] == len(expected_by_uid)
        and totals["local_matched_series"] + totals["missing_series"]
        == totals["expected_series"]
        and totals["equal_count_series"]
        + totals["partial_shortage_series"]
        + totals["all_shortage_series"]
        + totals["excess_series"]
        == totals["expected_series"]
        and totals["shortage_series_total"]
        == totals["missing_series"] + totals["partial_shortage_series"]
        and totals["expected_instances"]
        == sum(expected for expected, _modality in expected_by_uid.values())
        and totals["observed_unique_instances"]
        == sum(int(value) for value in observed.values())
    )
    baseline_matches = expected_baseline is None or all(
        totals.get(key) == value for key, value in expected_baseline.items()
    )
    reconciliation_status = (
        "RECONCILIATION_VERIFIED"
        if mapping_verified and invalid_expected_rows == 0
        and arithmetic_consistent and baseline_matches
        else "RECONCILIATION_FAILED"
    )
    all_modalities_explained = bool(
        mapping_verified
        and invalid_expected_rows == 0
        and unknown_expected_series == 0
        and not unexpected_uids
        and not header_issue_uids
        and conflict_series == 0
        and mixed_series == 0
        and not has_unassignable_header_issue
    )
    return {
        "classification_basis": "OFFICIAL_IDC_V25_SERIES_MODALITY",
        "by_modality": buckets,
        "totals": totals,
        "unknown_invalid_summary": {
            "expected_series": buckets[UNKNOWN_MODALITY]["expected_series"],
            "expected_instances": buckets[UNKNOWN_MODALITY]["expected_instances"],
            "local_series_with_missing_or_invalid_header_modality": len(header_issue_uids),
            "local_files_with_missing_or_invalid_header_modality": int(
                local.get("modality_header_missing_or_invalid_file_count", 0)
            ),
            "mixed_header_modality_series": mixed_series,
            "official_vs_header_modality_conflict_series": conflict_series,
            "unexpected_local_series": len(unexpected_uids),
            "unexpected_local_unique_instances": unexpected_instances,
            "unassignable_header_issues": unassignable_header_issues,
            "invalid_official_series_rows": invalid_expected_rows,
        },
        "reconciliation_status": reconciliation_status,
        "arithmetic_consistent": arithmetic_consistent,
        "matches_r1_accepted_aggregate_baseline": baseline_matches,
        "all_modalities_explained": all_modalities_explained,
    }


def build_private_series_gap_list(
    rows: Iterable[Mapping[str, Any]],
    local: Mapping[str, Any],
    uid_to_prefix: Mapping[str, str],
    raw_metadata_snapshot_verified: bool,
    generated_at_utc: str | None = None,
) -> dict[str, Any]:
    """Build the UID/prefix-level difference file for ignored local storage only."""
    observed = local["unique_sop_count_by_series"]
    header_modalities = local.get("header_modalities_by_series", {})
    modality_issue_files = local.get("modality_header_missing_or_invalid_file_count_by_series", {})
    gaps = []
    for row in rows:
        uid = str(row.get("SeriesInstanceUID") or "").strip()
        try:
            expected = int(row.get("instanceCount"))
        except (TypeError, ValueError):
            continue
        if not uid or expected <= 0:
            continue
        local_count = int(observed.get(uid, 0))
        if local_count != expected:
            source_prefix = uid_to_prefix.get(uid)
            if not source_prefix:
                raise AuditBlocked("PRIVATE_GAP_LIST_SOURCE_MAPPING_INCOMPLETE")
            modality = _normalized_modality(row.get("Modality")) or UNKNOWN_MODALITY
            header_values = sorted({
                normalized
                for value in header_modalities.get(uid, ())
                if (normalized := _normalized_modality(value)) is not None
            })
            gaps.append({
                "SeriesInstanceUID": uid,
                "Modality": modality,
                "expected_instance_count": expected,
                "observed_unique_sop_count": local_count,
                "shortage_count": max(expected - local_count, 0),
                "excess_count": max(local_count - expected, 0),
                "series_source_prefix": source_prefix,
                "observed_header_modalities": header_values,
                "header_modality_missing_or_invalid_file_count": int(
                    modality_issue_files.get(uid, 0)
                ),
            })
    return {
        "task_id": TASK_ID,
        "source_index_release": "25.0.0",
        "source_index_version": EXPECTED_INDEX_VERSION,
        "generated_at_utc": generated_at_utc or dt.datetime.now(dt.timezone.utc).isoformat(),
        "raw_metadata_snapshot_verified": bool(raw_metadata_snapshot_verified),
        "record_count": len(gaps),
        "status": "SERIES_INSTANCE_GAPS_FOUND" if gaps else "SERIES_INSTANCE_COUNTS_MATCHED",
        "records": gaps,
        "remote_object_status": "NOT_ASSESSED_BY_THIS_PRIVATE_SERIES_LIST",
    }


def public_private_gap_summary(private_value: Mapping[str, Any] | None, status: str) -> dict[str, Any]:
    """Return only safe aggregate facts about a local-only private difference file."""
    return {
        "created": private_value is not None,
        "status": status,
        "record_count": (
            int(private_value["record_count"]) if private_value is not None else None
        ),
        "storage_scope": "IGNORED_WORKTREE_LOCAL_ONLY",
        "identifiers_serialized_to_public_profile": False,
    }


def _path_has_reparse_component(path: Path) -> bool:
    absolute = Path(os.path.abspath(path))
    for component in [*reversed(absolute.parents), absolute]:
        try:
            item = os.stat(component, follow_symlinks=False)
        except FileNotFoundError:
            continue
        except OSError:
            raise AuditBlocked("PRIVATE_GAP_PATH_VALIDATION_FAILED") from None
        attributes = int(getattr(item, "st_file_attributes", 0))
        if stat.S_ISLNK(item.st_mode) or attributes & 0x400:
            return True
    return False


def validate_private_gap_path(path: Path, require_absent: bool = True) -> Path:
    """Validate a private output path lexically and physically below this worktree .local."""
    repo_root = Path(os.path.abspath(__file__)).parents[2]
    private_root = repo_root / ".local"
    candidate = Path(os.path.abspath(path))
    if (
        not private_root.is_dir()
        or not candidate.is_relative_to(private_root)
        or _path_has_reparse_component(repo_root)
        or _path_has_reparse_component(private_root)
        or _path_has_reparse_component(candidate)
    ):
        raise AuditBlocked("PRIVATE_GAP_OUTPUT_MUST_BE_UNDER_SAFE_WORKTREE_LOCAL")
    try:
        if not candidate.resolve(strict=False).is_relative_to(private_root.resolve(strict=True)):
            raise AuditBlocked("PRIVATE_GAP_OUTPUT_MUST_BE_UNDER_SAFE_WORKTREE_LOCAL")
    except (OSError, ValueError):
        raise AuditBlocked("PRIVATE_GAP_OUTPUT_MUST_BE_UNDER_SAFE_WORKTREE_LOCAL") from None
    if require_absent and (candidate.exists() or candidate.with_suffix(candidate.suffix + ".tmp").exists()):
        raise AuditBlocked("PRIVATE_GAP_OUTPUT_ALREADY_EXISTS")
    return candidate


def write_private_gap_list(path: Path, private_value: Mapping[str, Any]) -> None:
    """Write sensitive series identifiers only below this worktree's ignored .local."""
    candidate = validate_private_gap_path(path, require_absent=True)
    candidate.parent.mkdir(parents=True, exist_ok=True)
    candidate = validate_private_gap_path(candidate, require_absent=True)
    temporary = candidate.with_suffix(candidate.suffix + ".tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    try:
        descriptor = os.open(temporary, flags, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(private_value, ensure_ascii=False, indent=2) + "\n")
        temporary.rename(candidate)
    except AuditBlocked:
        raise
    except OSError:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise AuditBlocked("PRIVATE_GAP_WRITE_FAILED") from None


def parse_s3_list_page(body: bytes) -> tuple[list[tuple[str, int]], bool, str | None]:
    """Parse one ListObjectsV2 page without returning diagnostics containing keys."""
    root = ET.fromstring(body)
    if not root.tag.endswith("ListBucketResult"):
        raise AuditBlocked("UNEXPECTED_S3_LIST_RESPONSE")
    namespace = ""
    if root.tag.startswith("{"):
        namespace = root.tag.split("}", 1)[0] + "}"
    objects: list[tuple[str, int]] = []
    for contents in root.findall(f"{namespace}Contents"):
        key_value = contents.findtext(f"{namespace}Key")
        size_value = contents.findtext(f"{namespace}Size")
        if key_value is None or size_value is None:
            continue
        key = urllib.parse.unquote(key_value)
        try:
            size = int(size_value)
        except ValueError:
            continue
        objects.append((key, size))
    truncated = root.findtext(f"{namespace}IsTruncated", "false").lower() == "true"
    token = root.findtext(f"{namespace}NextContinuationToken")
    return objects, truncated, urllib.parse.unquote(token) if token else None


def compare_object_inventory(
    prefix_to_uid: Mapping[str, str],
    remote_objects_by_prefix: Mapping[str, Mapping[str, int]],
    local: Mapping[str, Any],
    all_prefixes_listed: bool,
) -> dict[str, Any]:
    remote_count = sum(len(objects) for objects in remote_objects_by_prefix.values())
    remote_bytes = sum(size for objects in remote_objects_by_prefix.values() for size in objects.values())
    missing_local = local_extra = size_mismatch = ambiguous_names = matched = 0
    listed_series = 0
    for prefix, objects in remote_objects_by_prefix.items():
        uid = prefix_to_uid.get(prefix)
        if uid is None:
            continue
        listed_series += 1
        local_names: Mapping[str, list[int]] = local["basename_sizes_by_series"].get(uid, {})
        remote_by_name: dict[str, list[int]] = collections.defaultdict(list)
        for key, size in objects.items():
            basename = key.rsplit("/", 1)[-1].casefold()
            remote_by_name[basename].append(size)
        for name in set(remote_by_name) | set(local_names):
            remote_sizes = remote_by_name.get(name, [])
            local_sizes = local_names.get(name, [])
            if len(remote_sizes) > 1 or len(local_sizes) > 1:
                ambiguous_names += 1
            common = min(len(remote_sizes), len(local_sizes))
            matched += common
            if len(remote_sizes) > len(local_sizes):
                missing_local += len(remote_sizes) - len(local_sizes)
            if len(local_sizes) > len(remote_sizes):
                local_extra += len(local_sizes) - len(remote_sizes)
            for remote_size, local_size in zip(sorted(remote_sizes), sorted(local_sizes)):
                size_mismatch += remote_size != local_size
    complete = all_prefixes_listed and listed_series == len(prefix_to_uid)
    status = (
        "OBJECT_INVENTORY_NOT_VERIFIED" if not complete
        else "OBJECT_INVENTORY_AND_SIZE_MATCHED"
        if not (missing_local or local_extra or size_mismatch or ambiguous_names)
        else "OBJECT_INVENTORY_DIFF_FOUND"
    )
    return {
        "status": status,
        "listed_series_count": listed_series,
        "remote_object_count": remote_count if complete else None,
        "remote_object_count_in_listed_scope": remote_count,
        "remote_object_bytes": remote_bytes if complete else None,
        "remote_object_bytes_in_listed_scope": remote_bytes,
        "matched_object_name_count": matched if complete else None,
        "remote_objects_missing_locally_count": missing_local if complete else None,
        "local_objects_absent_remotely_count": local_extra if complete else None,
        "object_size_mismatch_count": size_mismatch if complete else None,
        "ambiguous_basename_group_count": ambiguous_names,
        "listed_scope_is_complete": complete,
        "bitwise_integrity_status": "NOT_VERIFIED_NO_CONTENT_HASHES",
    }


def compare_global_object_names(
    remote_objects_by_prefix: Mapping[str, Mapping[str, int]],
    local_basename_sizes: Mapping[str, list[int]],
    all_prefixes_listed: bool,
) -> dict[str, Any]:
    """Compare globally unique object basenames against local filenames and sizes."""
    remote_sizes: dict[str, list[int]] = collections.defaultdict(list)
    for objects in remote_objects_by_prefix.values():
        for key, size in objects.items():
            remote_sizes[key.rsplit("/", 1)[-1].casefold()].append(size)
    local_count = sum(len(values) for values in local_basename_sizes.values())
    remote_count = sum(len(values) for values in remote_sizes.values())
    remote_bytes = sum(size for values in remote_sizes.values() for size in values)
    local_collisions = sum(len(values) > 1 for values in local_basename_sizes.values())
    remote_collisions = sum(len(values) > 1 for values in remote_sizes.values())
    matched = missing_local = local_extra = size_mismatch = 0
    for name in set(remote_sizes) | set(local_basename_sizes):
        remote_values = remote_sizes.get(name, [])
        local_values = local_basename_sizes.get(name, [])
        common = min(len(remote_values), len(local_values))
        matched += common
        missing_local += max(len(remote_values) - len(local_values), 0)
        local_extra += max(len(local_values) - len(remote_values), 0)
        size_mismatch += sum(
            remote_size != local_size
            for remote_size, local_size in zip(sorted(remote_values), sorted(local_values))
        )
    mapping_unambiguous = all_prefixes_listed and not local_collisions and not remote_collisions
    complete = all_prefixes_listed and mapping_unambiguous
    status = (
        "OBJECT_INVENTORY_NOT_VERIFIED" if not complete
        else "OBJECT_INVENTORY_AND_SIZE_MATCHED"
        if not (missing_local or local_extra or size_mismatch)
        else "OBJECT_INVENTORY_DIFF_FOUND"
    )
    return {
        "status": status,
        "object_name_mapping_status": (
            "NOT_VERIFIED" if not all_prefixes_listed else
            "AMBIGUOUS_BASENAMES" if local_collisions or remote_collisions else
            "UNIQUE_BASENAMES_VERIFIED"
        ),
        "local_file_count": local_count,
        "remote_object_count": remote_count if complete else None,
        "remote_object_count_in_listed_scope": remote_count,
        "remote_object_bytes": remote_bytes if complete else None,
        "remote_object_bytes_in_listed_scope": remote_bytes,
        "matched_object_name_count": matched if complete else None,
        "remote_objects_missing_locally_count": missing_local if complete else None,
        "local_objects_absent_remotely_count": local_extra if complete else None,
        "object_size_mismatch_count": size_mismatch if complete else None,
        "local_basename_collision_group_count": local_collisions,
        "remote_basename_collision_group_count": remote_collisions,
        "listed_scope_is_complete": complete,
        "bitwise_integrity_status": "NOT_VERIFIED_NO_CONTENT_HASHES",
    }


def _previous_audit_helpers():
    scripts_dir = str(Path(__file__).resolve().parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    try:
        import audit_tcia_full_dicom as prior
    except Exception:
        raise AuditBlocked("PRIOR_AUDIT_HELPERS_UNAVAILABLE") from None
    return prior


def _safe_path_check(path: Path) -> bool:
    current = path.absolute()
    while True:
        try:
            item = os.stat(current, follow_symlinks=False)
        except OSError:
            return False
        attrs = int(getattr(item, "st_file_attributes", 0))
        if stat.S_ISLNK(item.st_mode) or attrs & 0x400:
            return False
        if current.parent == current:
            return True
        current = current.parent


def scan_minimal_headers(root: Path, deadline: float) -> dict[str, Any]:
    """Read only four public DICOM header fields; never decode PixelData."""
    scan_started = time.monotonic()
    from pydicom.tag import Tag

    tags = [Tag(0x0020000E), Tag(0x00080018), Tag(0x00080060), Tag(0x0020000D)]
    file_count = parse_errors = missing_series = missing_sop = zero_bytes = 0
    modality_header_missing_or_invalid_file_count = 0
    modality_header_missing_file_count = 0
    modality_header_invalid_file_count = 0
    exception_counts: collections.Counter[str] = collections.Counter()
    series_files: collections.Counter[str] = collections.Counter()
    sops_by_series: dict[str, set[str]] = collections.defaultdict(set)
    header_modalities_by_series: dict[str, set[str]] = collections.defaultdict(set)
    modality_header_missing_or_invalid_file_count_by_series: collections.Counter[str] = collections.Counter()
    basename_sizes: dict[str, dict[str, list[int]]] = collections.defaultdict(
        lambda: collections.defaultdict(list)
    )
    duplicate_sop_files = 0
    stack = [root]
    stopped_reason = None
    while stack:
        if time.monotonic() >= deadline:
            stopped_reason = "TIME_LIMIT"
            break
        current = stack.pop()
        try:
            entries = sorted(os.scandir(current), key=lambda entry: entry.name.casefold())
        except Exception as exc:
            exception_counts[type(exc).__name__] += 1
            continue
        dirs: list[Path] = []
        for entry in entries:
            if time.monotonic() >= deadline:
                stopped_reason = "TIME_LIMIT"
                break
            try:
                item = entry.stat(follow_symlinks=False)
                attributes = int(getattr(item, "st_file_attributes", 0))
                if stat.S_ISLNK(item.st_mode) or attributes & 0x400:
                    raise AuditBlocked("REPARSE_ENTRY_FOUND")
                if entry.is_dir(follow_symlinks=False):
                    dirs.append(Path(entry.path))
                    continue
                if not stat.S_ISREG(item.st_mode):
                    continue
            except AuditBlocked:
                raise
            except Exception as exc:
                exception_counts[type(exc).__name__] += 1
                continue
            file_count += 1
            if file_count > MAX_LOCAL_FILES:
                stopped_reason = "FILE_LIMIT"
                break
            zero_bytes += item.st_size == 0
            try:
                dataset = pydicom.dcmread(
                    entry.path,
                    stop_before_pixels=True,
                    specific_tags=tags,
                    force=False,
                )
                uid = str(getattr(dataset, "SeriesInstanceUID", "") or "").strip()
                sop = str(getattr(dataset, "SOPInstanceUID", "") or "").strip()
                raw_modality = str(getattr(dataset, "Modality", "") or "").strip()
                normalized_modality = _normalized_modality(raw_modality)
                if normalized_modality is None:
                    modality_header_missing_or_invalid_file_count += 1
                    if raw_modality:
                        modality_header_invalid_file_count += 1
                    else:
                        modality_header_missing_file_count += 1
                if not uid:
                    missing_series += 1
                    continue
                series_files[uid] += 1
                if normalized_modality is None:
                    modality_header_missing_or_invalid_file_count_by_series[uid] += 1
                else:
                    header_modalities_by_series[uid].add(normalized_modality)
                basename = entry.name.casefold()
                basename_sizes[uid][basename].append(int(item.st_size))
                if not sop:
                    missing_sop += 1
                    continue
                if sop in sops_by_series[uid]:
                    duplicate_sop_files += 1
                sops_by_series[uid].add(sop)
            except Exception as exc:
                parse_errors += 1
                exception_counts[type(exc).__name__] += 1
        stack.extend(reversed(dirs))
    return {
        "file_count": file_count,
        "parse_error_count": parse_errors,
        "missing_series_uid_file_count": missing_series,
        "missing_sop_uid_file_count": missing_sop,
        "zero_byte_file_count": zero_bytes,
        "duplicate_sop_file_count": duplicate_sop_files,
        "exception_class_counts": dict(sorted(exception_counts.items())),
        "scanned_unique_series_count": len(series_files),
        "header_modalities_by_series": {
            uid: sorted(values) for uid, values in header_modalities_by_series.items()
        },
        "modality_header_missing_or_invalid_file_count": modality_header_missing_or_invalid_file_count,
        "modality_header_missing_file_count": modality_header_missing_file_count,
        "modality_header_invalid_file_count": modality_header_invalid_file_count,
        "modality_header_missing_or_invalid_file_count_by_series": dict(
            modality_header_missing_or_invalid_file_count_by_series
        ),
        "unique_sop_count_by_series": {uid: len(sops) for uid, sops in sops_by_series.items()},
        "series_file_count_by_series": dict(series_files),
        "basename_sizes_by_series": {
            uid: {name: sizes for name, sizes in names.items()}
            for uid, names in basename_sizes.items()
        },
        "complete": stopped_reason is None and parse_errors == 0,
        "stopped_reason": stopped_reason,
        "elapsed_seconds": round(time.monotonic() - scan_started, 3),
    }


def list_public_objects(
    prefixes: Iterable[str], *, max_requests: int = MAX_LIST_REQUESTS,
    max_response_bytes: int = MAX_LIST_RESPONSE_BYTES,
    max_seconds: int = MAX_LIST_SECONDS,
) -> dict[str, Any]:
    """Anonymous ListObjectsV2 only; never requests object bodies or credentials."""
    start = time.monotonic()
    deadline = start + max_seconds
    total_bytes = requests = pages = 0
    results: dict[str, dict[str, int]] = {}
    failure_class = None
    failure_reason_class = None
    http_status = None
    for prefix in sorted(set(prefixes)):
        continuation = None
        objects: dict[str, int] = {}
        while True:
            if time.monotonic() >= deadline:
                failure_class = "TIME_LIMIT"
                break
            if requests >= max_requests:
                failure_class = "REQUEST_LIMIT"
                break
            if total_bytes >= max_response_bytes:
                failure_class = "RESPONSE_BYTE_LIMIT"
                break
            params = {"list-type": "2", "prefix": prefix.rstrip("/") + "/", "encoding-type": "url"}
            if continuation:
                params["continuation-token"] = continuation
            url = f"https://{S3_BUCKET}.s3.amazonaws.com/?{urllib.parse.urlencode(params)}"
            request = urllib.request.Request(url, headers={"User-Agent": "CMRL-06-read-only-audit"})
            requests += 1
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    http_status = response.status
                    remaining = max_response_bytes - total_bytes
                    content_length = response.headers.get("Content-Length")
                    if content_length and int(content_length) > remaining:
                        failure_class = "RESPONSE_BYTE_LIMIT"
                        break
                    body = response.read(remaining)
                    if content_length and len(body) != int(content_length):
                        failure_class = "INCOMPLETE_RESPONSE"
                        break
                    if not content_length and len(body) == remaining:
                        failure_class = "RESPONSE_BYTE_LIMIT"
                        break
                    total_bytes += len(body)
                page_objects, truncated, next_token = parse_s3_list_page(body)
                pages += 1
                for key, size in page_objects:
                    if not key.startswith(prefix.rstrip("/") + "/"):
                        failure_class = "OUT_OF_PREFIX_KEY"
                        break
                    objects[key] = size
                if failure_class:
                    break
                if not truncated:
                    results[prefix] = objects
                    break
                if not next_token:
                    failure_class = "MISSING_CONTINUATION_TOKEN"
                    break
                continuation = next_token
            except urllib.error.HTTPError as exc:
                http_status = int(exc.code)
                failure_class = "HTTP_ERROR"
                break
            except urllib.error.URLError as exc:
                failure_class = "URLError"
                failure_reason_class = type(exc.reason).__name__
                break
            except Exception as exc:
                failure_class = type(exc).__name__
                break
        if failure_class:
            break
    complete = not failure_class and len(results) == len(set(prefixes))
    return {
        "status": "REMOTE_LIST_COMPLETE" if complete else (
            "REMOTE_LIST_UNAVAILABLE" if failure_class in {"HTTP_ERROR", "URLError", "TimeoutError"}
            else "REMOTE_LIST_PARTIAL"
        ),
        "complete": complete,
        "series_prefixes_listed": len(results),
        "list_request_count": requests,
        "list_page_count": pages,
        "response_bytes": total_bytes,
        "elapsed_seconds": round(time.monotonic() - start, 3),
        "failure_class": failure_class,
        "failure_reason_class": failure_reason_class,
        "http_status": http_status,
        "_objects_by_prefix": results,
    }


def _public_list_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if not key.startswith("_")}


def _query_official_rows(index_path: Path) -> list[dict[str, Any]]:
    query = """
        SELECT SeriesInstanceUID, instanceCount, series_aws_url, Modality,
               series_init_idc_version, series_revised_idc_version
        FROM read_parquet(?) WHERE collection_id = ?
    """
    columns = ["SeriesInstanceUID", "instanceCount", "series_aws_url", "Modality",
               "series_init_idc_version", "series_revised_idc_version"]
    records = duckdb.connect().execute(query, [str(index_path), COLLECTION_ID]).fetchall()
    return [dict(zip(columns, row)) for row in records]


def _collection_crosswalk(collection_path: Path) -> dict[str, Any]:
    rows = duckdb.connect().execute(
        "SELECT collection_name, collection_id FROM read_parquet(?) WHERE collection_id = ?",
        [str(collection_path), COLLECTION_ID],
    ).fetchall()
    verified = rows == [(COLLECTION_NAME, COLLECTION_ID)]
    return {"verified": verified, "matching_collection_row_count": len(rows)}


def _load_prior_r1_profile(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    candidate = Path(os.path.abspath(path))
    if not _safe_path_check(candidate) or not candidate.is_file():
        raise AuditBlocked("PRIOR_R1_PROFILE_UNAVAILABLE_OR_UNSAFE")
    try:
        value = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise AuditBlocked("PRIOR_R1_PROFILE_INVALID") from None
    if not isinstance(value, dict):
        raise AuditBlocked("PRIOR_R1_PROFILE_INVALID")
    remote = value.get("remote_list", {})
    objects = value.get("object_inventory", {})
    if not (
        value.get("task_id") == TASK_ID
        and value.get("plan_revision") == "r1"
        and value.get("official_index", {}).get("sha256") == EXPECTED_INDEX_SHA256
        and value.get("manifest_mapping", {}).get("mapping_status") == "MAPPING_VERIFIED"
        and remote.get("status") == "REMOTE_LIST_UNAVAILABLE"
        and objects.get("status") == "OBJECT_INVENTORY_NOT_VERIFIED"
        and objects.get("bitwise_integrity_status") == "NOT_VERIFIED_NO_CONTENT_HASHES"
    ):
        raise AuditBlocked("PRIOR_R1_PROFILE_DOES_NOT_MATCH_ACCEPTED_BASELINE")
    return value


def _load_previous_manifest_parser():
    return _previous_audit_helpers()


def inventory_local_basenames(root: Path) -> dict[str, Any]:
    """Collect local filename and size mappings in memory without opening files."""
    files: dict[str, list[int]] = collections.defaultdict(list)
    file_count = total_bytes = 0
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = sorted(os.scandir(current), key=lambda entry: entry.name.casefold())
        except Exception:
            raise AuditBlocked("LOCAL_FILENAME_INVENTORY_FAILED") from None
        dirs: list[Path] = []
        for entry in entries:
            try:
                item = entry.stat(follow_symlinks=False)
                attributes = int(getattr(item, "st_file_attributes", 0))
                if stat.S_ISLNK(item.st_mode) or attributes & 0x400:
                    raise AuditBlocked("LOCAL_FILENAME_INVENTORY_FOUND_REPARSE_ENTRY")
                if entry.is_dir(follow_symlinks=False):
                    dirs.append(Path(entry.path))
                elif stat.S_ISREG(item.st_mode):
                    files[entry.name.casefold()].append(int(item.st_size))
                    file_count += 1
                    total_bytes += int(item.st_size)
                else:
                    raise AuditBlocked("LOCAL_FILENAME_INVENTORY_FOUND_SPECIAL_ENTRY")
            except AuditBlocked:
                raise
            except Exception:
                raise AuditBlocked("LOCAL_FILENAME_INVENTORY_METADATA_FAILED") from None
        stack.extend(reversed(dirs))
    return {
        "file_count": file_count,
        "total_bytes": total_bytes,
        "basename_collision_group_count": sum(len(values) > 1 for values in files.values()),
        "_basename_sizes": dict(files),
    }


def resume_with_remote_audit(args: argparse.Namespace) -> dict[str, Any]:
    """Resume LIST and filename evidence from a completed same-task Header scan."""
    profile_path = Path(args.resume_profile).absolute()
    try:
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
    except Exception:
        raise AuditBlocked("PRIOR_AGGREGATE_PROFILE_UNAVAILABLE") from None
    if profile.get("task_id") != TASK_ID or profile.get("plan_revision") != PLAN_REVISION:
        raise AuditBlocked("PRIOR_AGGREGATE_PROFILE_IDENTITY_MISMATCH")

    index_path = Path(args.index).absolute()
    collection_path = Path(args.collections_index).absolute()
    manifest_path = Path(args.manifest).absolute()
    data_root = Path(args.data_root).absolute()
    if os.path.normcase(str(data_root)) != os.path.normcase(str(AUTHORIZED_DATA_ROOT)):
        raise AuditBlocked("DATA_ROOT_NOT_AUTHORIZED")
    if not _safe_path_check(manifest_path) or not manifest_path.is_file():
        raise AuditBlocked("MANIFEST_PATH_UNAVAILABLE_OR_UNSAFE")
    if not collection_path.is_file():
        raise AuditBlocked("OFFICIAL_COLLECTION_INDEX_UNAVAILABLE")
    prior = _load_previous_manifest_parser()
    prior._assert_safe_roots(AUTHORIZED_PROJECT_ROOT, data_root, AUTHORIZED_MANUAL_ROOT)

    index_version = verify_parquet(index_path, EXPECTED_INDEX_SHA256, EXPECTED_INDEX_VERSION)
    collection_version = verify_parquet(
        collection_path, EXPECTED_COLLECTIONS_SHA256, EXPECTED_INDEX_VERSION,
        {"collection_id", "collection_name"},
    )
    crosswalk = _collection_crosswalk(collection_path)
    version_verified = bool(
        index_version["verified"] and index_version["required_columns_present"]
        and collection_version["verified"] and collection_version["required_columns_present"]
        and crosswalk["verified"]
    )
    manifest = prior.parse_manifest_bytes(manifest_path.read_bytes())
    manifest_valid = bool(
        manifest.get("structure_status") == "MANIFEST_STRUCTURE_VERIFIED"
        and manifest.get("bytes") == EXPECTED_MANIFEST_BYTES
        and manifest.get("sha256") == EXPECTED_MANIFEST_SHA256
        and manifest.get("uploaded_copy_sha_matches")
    )
    manifest_prefixes = manifest.get("_source_prefixes", frozenset())
    rows = _query_official_rows(index_path)
    mapping, _prefix_to_uid, _uid_to_prefix = map_series_prefixes(manifest_prefixes, rows)
    mapping_verified = bool(
        version_verified and manifest_valid and mapping["mapping_status"] == "MAPPING_VERIFIED"
    )

    previous_local = profile.get("local_header_comparison", {})
    header_complete = bool(
        previous_local.get("file_count") == previous_local.get("parsed_file_count")
        and previous_local.get("parse_error_count") == 0
        and previous_local.get("missing_series_uid_file_count") == 0
        and previous_local.get("missing_sop_uid_file_count") == 0
        and previous_local.get("header_file_count_matches_inventory") is True
        and previous_local.get("header_scan_stop_reason") is None
        and previous_local.get("raw_metadata_before_after_match") is True
        and previous_local.get("raw_file_count_before") == previous_local.get("raw_file_count_after")
        and previous_local.get("raw_total_bytes_before") == previous_local.get("raw_total_bytes_after")
    )
    before = prior.filesystem_supplement(data_root, time.monotonic() + MAX_HEADER_SECONDS)
    if (not before.get("inventory_complete") or before.get("reparse_entry_count", 0)
            or before.get("special_nonregular_entry_count", 0)
            or before.get("file_count") != previous_local.get("raw_file_count_after")
            or before.get("total_bytes") != previous_local.get("raw_total_bytes_after")):
        raise AuditBlocked("RAW_INPUT_DOES_NOT_MATCH_COMPLETED_HEADER_SCAN")

    local_names = inventory_local_basenames(data_root)
    after = prior.filesystem_supplement(data_root, time.monotonic() + MAX_HEADER_SECONDS)
    snapshot_stable = prior._inventory_snapshots_match(before, after)
    local_names_stable = bool(
        snapshot_stable
        and local_names["file_count"] == before.get("file_count")
        and local_names["total_bytes"] == before.get("total_bytes")
    )
    if not local_names_stable:
        raise AuditBlocked("RAW_INPUT_CHANGED_DURING_OBJECT_NAME_INVENTORY")

    local_series_status = (
        "NOT_VERIFIED" if not (mapping_verified and header_complete)
        else "INSTANCE_COUNT_GAPS_FOUND"
        if previous_local.get("missing_series_count", 0)
        or previous_local.get("series_with_instance_shortage_count", 0)
        or previous_local.get("series_with_instance_excess_count", 0)
        else "SERIES_INSTANCE_COUNTS_MATCHED"
    )
    previous_local["status"] = local_series_status
    previous_local["header_scan_status"] = "LOCAL_HEADER_SCAN_COMPLETE" if header_complete else "LOCAL_HEADER_SCAN_PARTIAL"
    previous_local["aggregate_reused_after_mapping_correction"] = True
    previous_local["raw_metadata_before_after_match"] = snapshot_stable

    if args.list_public_s3 and mapping_verified and header_complete and local_names_stable:
        listed = list_public_objects(manifest_prefixes)
        objects = compare_global_object_names(
            listed["_objects_by_prefix"], local_names["_basename_sizes"], listed["complete"]
        )
        objects["listed_series_prefix_count"] = listed["series_prefixes_listed"]
        list_summary = _public_list_summary(listed)
    else:
        listed = None
        objects = {
            "status": "OBJECT_INVENTORY_NOT_VERIFIED", "object_name_mapping_status": "NOT_RUN",
            "local_file_count": local_names["file_count"], "remote_object_count": None,
            "remote_object_bytes": None, "matched_object_name_count": None,
            "remote_objects_missing_locally_count": None, "local_objects_absent_remotely_count": None,
            "object_size_mismatch_count": None,
            "local_basename_collision_group_count": local_names["basename_collision_group_count"],
            "remote_basename_collision_group_count": 0,
            "bitwise_integrity_status": "NOT_VERIFIED_NO_CONTENT_HASHES",
        }
        list_summary = {"status": "NOT_RUN_GATE_BLOCKED", "complete": False,
                        "series_prefixes_listed": 0, "list_request_count": 0,
                        "list_page_count": 0, "response_bytes": 0, "elapsed_seconds": 0,
                        "failure_class": None, "failure_reason_class": None, "http_status": None}

    index_summary = profile.get("official_index", {})
    index_summary.update(index_version)
    index_summary.update({
        "release_tag": "25.0.0",
        "source": "IDC official idc-index-data GCS release artifact",
        "artifact_url": "https://storage.googleapis.com/idc-index-data-artifacts/25.0.0/release_artifacts/idc_index.parquet",
        "checksum_url": "https://storage.googleapis.com/idc-index-data-artifacts/25.0.0/release_artifacts/idc_index.parquet.sha256",
        "collection_id": COLLECTION_ID,
        "collection_name": COLLECTION_NAME,
        "collection_name_crosswalk_verified": crosswalk["verified"],
    })
    index_summary["collections_index"] = {
        "artifact_url": "https://storage.googleapis.com/idc-index-data-artifacts/25.0.0/release_artifacts/collections_index.parquet",
        "checksum_url": "https://storage.googleapis.com/idc-index-data-artifacts/25.0.0/release_artifacts/collections_index.parquet.sha256",
        **collection_version,
        "row_count": pq.read_metadata(collection_path).num_rows,
    }
    profile["official_index"] = index_summary
    profile["manifest_mapping"] = mapping
    profile["local_header_comparison"] = previous_local
    profile["local_filename_inventory"] = {
        "file_count": local_names["file_count"],
        "total_bytes": local_names["total_bytes"],
        "basename_collision_group_count": local_names["basename_collision_group_count"],
        "raw_metadata_before_after_match": local_names_stable,
    }
    profile["remote_list"] = _public_list_summary(listed) if listed else list_summary
    profile["object_inventory"] = objects
    profile["source_claims"] = {
        "source_version_status": "SOURCE_VERSION_VERIFIED" if version_verified and manifest_valid else "VERSION_NOT_VERIFIED",
        "series_coverage_status": local_series_status,
        "object_inventory_status": objects["status"],
        "bitwise_integrity_status": objects["bitwise_integrity_status"],
    }
    profile["completion_method"] = "RESUMED_FROM_SAME_TASK_AGGREGATE_AFTER_PREFIX_NORMALIZATION_CORRECTION"
    profile["generated_at_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    return profile


def run_audit(args: argparse.Namespace) -> dict[str, Any]:
    started = dt.datetime.now(dt.timezone.utc)
    if args.list_public_s3:
        raise AuditBlocked("NETWORK_REQUESTS_PROHIBITED_BY_PLAN_R2")
    previous_profile = _load_prior_r1_profile(
        Path(args.previous_profile) if args.previous_profile else None
    )
    index_path = Path(args.index).absolute()
    collection_path = Path(args.collections_index).absolute()
    manifest_path = Path(args.manifest).absolute()
    data_root = Path(args.data_root).absolute()
    if os.path.normcase(str(data_root)) != os.path.normcase(str(AUTHORIZED_DATA_ROOT)):
        raise AuditBlocked("DATA_ROOT_NOT_AUTHORIZED")
    if not _safe_path_check(manifest_path) or not manifest_path.is_file():
        raise AuditBlocked("MANIFEST_PATH_UNAVAILABLE_OR_UNSAFE")
    private_gap_path = (
        validate_private_gap_path(Path(args.private_gap_output), require_absent=True)
        if args.private_gap_output
        else None
    )
    prior = _load_previous_manifest_parser()
    prior._assert_safe_roots(AUTHORIZED_PROJECT_ROOT, data_root, AUTHORIZED_MANUAL_ROOT)
    if not collection_path.is_file():
        raise AuditBlocked("OFFICIAL_COLLECTION_INDEX_UNAVAILABLE")

    index_version = verify_parquet(index_path, EXPECTED_INDEX_SHA256, EXPECTED_INDEX_VERSION)
    collection_version = verify_parquet(
        collection_path,
        EXPECTED_COLLECTIONS_SHA256,
        EXPECTED_INDEX_VERSION,
        {"collection_id", "collection_name"},
    )
    collection_crosswalk = _collection_crosswalk(collection_path)
    version_verified = bool(index_version["verified"] and collection_version["verified"]
                            and index_version["required_columns_present"] and collection_crosswalk["verified"])

    manifest_bytes = manifest_path.read_bytes()
    manifest = prior.parse_manifest_bytes(manifest_bytes)
    manifest_valid = (
        manifest.get("structure_status") == "MANIFEST_STRUCTURE_VERIFIED"
        and manifest.get("bytes") == EXPECTED_MANIFEST_BYTES
        and manifest.get("sha256") == EXPECTED_MANIFEST_SHA256
        and manifest.get("uploaded_copy_sha_matches") is True
    )
    manifest_prefixes = manifest.get("_source_prefixes", frozenset())
    rows = _query_official_rows(index_path)
    row_count = len(rows)
    mapping, prefix_to_uid, uid_to_prefix = map_series_prefixes(manifest_prefixes, rows)
    mapping_verified = version_verified and manifest_valid and mapping["mapping_status"] == "MAPPING_VERIFIED"

    modality_counts = dict(sorted(collections.Counter(str(row.get("Modality") or "UNKNOWN") for row in rows).items()))
    version_values = {
        "series_init_idc_version_values": sorted({str(row.get("series_init_idc_version") or "") for row in rows}),
        "series_revised_idc_version_values": sorted({str(row.get("series_revised_idc_version") or "") for row in rows}),
    }
    index_summary = {
        **index_version,
        "release_tag": "25.0.0",
        "source": "IDC official idc-index-data GCS release artifact",
        "artifact_url": "https://storage.googleapis.com/idc-index-data-artifacts/25.0.0/release_artifacts/idc_index.parquet",
        "checksum_url": "https://storage.googleapis.com/idc-index-data-artifacts/25.0.0/release_artifacts/idc_index.parquet.sha256",
        "collections_index": {
            "artifact_url": "https://storage.googleapis.com/idc-index-data-artifacts/25.0.0/release_artifacts/collections_index.parquet",
            "checksum_url": "https://storage.googleapis.com/idc-index-data-artifacts/25.0.0/release_artifacts/collections_index.parquet.sha256",
            **collection_version,
            "row_count": pq.read_metadata(collection_path).num_rows,
        },
        "collection_id": COLLECTION_ID,
        "collection_name": COLLECTION_NAME,
        "collection_name_crosswalk_verified": collection_crosswalk["verified"],
        "collection_series_row_count": row_count,
        "collection_unique_series_uid_count": len({str(row.get("SeriesInstanceUID") or "") for row in rows if row.get("SeriesInstanceUID")}),
        "collection_instance_count_sum": sum(int(row["instanceCount"]) for row in rows if row.get("instanceCount") is not None),
        "modality_series_row_counts": modality_counts,
        "version_field_distinct_counts": version_values,
        "manifest_source": {
            "status": manifest.get("structure_status"),
            "sha256_matches_prior_record": manifest_valid,
            "bytes": manifest.get("bytes"),
            "command_count": manifest.get("command_count"),
        },
    }

    before = prior.filesystem_supplement(data_root, time.monotonic() + MAX_HEADER_SECONDS)
    if (not before.get("inventory_complete") or before.get("reparse_entry_count", 0)
            or before.get("special_nonregular_entry_count", 0)):
        raise AuditBlocked("RAW_INPUT_PRE_SCAN_INVENTORY_INCOMPLETE_OR_UNSAFE")
    header_started = time.monotonic()
    local = scan_minimal_headers(data_root, header_started + MAX_HEADER_SECONDS)
    after = prior.filesystem_supplement(data_root, time.monotonic() + MAX_HEADER_SECONDS)
    metadata_snapshot_matches = prior._inventory_snapshots_match(before, after)
    safe_directory_snapshot = all(
        snapshot.get("reparse_entry_count", 0) == 0
        and snapshot.get("special_nonregular_entry_count", 0) == 0
        for snapshot in (before, after)
    )
    unchanged = metadata_snapshot_matches and safe_directory_snapshot
    header_complete = local["complete"] and local["file_count"] == before.get("file_count")
    local_series = compare_series_instances(
        rows, local, mapping_verified and header_complete and unchanged
    )
    modality_gap_summary = compare_series_instances_by_modality(
        rows,
        local,
        mapping_verified and header_complete and unchanged,
        expected_baseline=R1_ACCEPTED_MODALITY_BASELINE,
    )
    local_summary = {
        "status": (
            "LOCAL_HEADER_SCAN_COMPLETE"
            if header_complete and unchanged
            else "LOCAL_HEADER_SCAN_PARTIAL_OR_SNAPSHOT_CHANGED"
        ),
        "file_count": local["file_count"],
        "parsed_file_count": local["file_count"] - local["parse_error_count"],
        "parse_error_count": local["parse_error_count"],
        "missing_series_uid_file_count": local["missing_series_uid_file_count"],
        "missing_sop_uid_file_count": local["missing_sop_uid_file_count"],
        "zero_byte_file_count": local["zero_byte_file_count"],
        "duplicate_sop_file_count": local["duplicate_sop_file_count"],
        "header_missing_or_invalid_modality_file_count": local[
            "modality_header_missing_or_invalid_file_count"
        ],
        "header_missing_modality_file_count": local["modality_header_missing_file_count"],
        "header_invalid_modality_file_count": local["modality_header_invalid_file_count"],
        "local_unique_series_count": local["scanned_unique_series_count"],
        "raw_metadata_before_after_match": unchanged,
        "raw_file_count_before": before.get("file_count"),
        "raw_file_count_after": after.get("file_count"),
        "raw_total_bytes_before": before.get("total_bytes"),
        "raw_total_bytes_after": after.get("total_bytes"),
        "raw_directory_count_before": before.get("directories_including_root"),
        "raw_directory_count_after": after.get("directories_including_root"),
        "raw_reparse_entry_count_before": before.get("reparse_entry_count", 0),
        "raw_reparse_entry_count_after": after.get("reparse_entry_count", 0),
        "raw_special_entry_count_before": before.get("special_nonregular_entry_count", 0),
        "raw_special_entry_count_after": after.get("special_nonregular_entry_count", 0),
        "header_scan_elapsed_seconds": local["elapsed_seconds"],
        "header_scan_stop_reason": local["stopped_reason"],
        "header_file_count_matches_inventory": local["file_count"] == before.get("file_count"),
        **local_series,
    }

    private_value = None
    private_status = "NOT_REQUESTED"
    if private_gap_path is not None:
        private_ready = bool(
            mapping_verified
            and header_complete
            and unchanged
            and local["missing_series_uid_file_count"] == 0
            and local["missing_sop_uid_file_count"] == 0
            and local["zero_byte_file_count"] == 0
            and modality_gap_summary["reconciliation_status"] == "RECONCILIATION_VERIFIED"
        )
        if not private_ready:
            private_status = "PRIVATE_GAP_LIST_BLOCKED_INCOMPLETE_OR_UNRECONCILED_SCAN"
        else:
            private_value = build_private_series_gap_list(
                rows,
                local,
                uid_to_prefix,
                raw_metadata_snapshot_verified=unchanged,
            )
            if private_value["record_count"] != 73:
                private_value = None
                private_status = "PRIVATE_GAP_LIST_BLOCKED_UNEXPECTED_GAP_COUNT"
            else:
                write_private_gap_list(private_gap_path, private_value)
                private_status = "PRIVATE_GAP_LIST_CREATED"
    private_gap_summary = public_private_gap_summary(private_value, private_status)

    list_summary: dict[str, Any]
    object_summary: dict[str, Any]
    if previous_profile is not None:
        list_summary = dict(previous_profile["remote_list"])
        object_summary = dict(previous_profile["object_inventory"])
        object_summary["local_file_count"] = local["file_count"]
    elif args.list_public_s3 and version_verified and manifest_valid and mapping_verified and header_complete:
        listed = list_public_objects(manifest_prefixes)
        object_summary = compare_object_inventory(
            prefix_to_uid, listed["_objects_by_prefix"], local, listed["complete"]
        )
        list_summary = _public_list_summary(listed)
    elif args.list_public_s3:
        list_summary = {"status": "NOT_RUN_GATE_BLOCKED", "complete": False,
                        "series_prefixes_listed": 0, "list_request_count": 0,
                        "list_page_count": 0, "response_bytes": 0,
                        "elapsed_seconds": 0, "failure_class": None,
                        "failure_reason_class": None, "http_status": None}
        object_summary = {"status": "OBJECT_INVENTORY_NOT_VERIFIED", "listed_series_count": 0,
                          "remote_object_count": None, "remote_object_bytes": None,
                          "matched_object_name_count": None, "remote_objects_missing_locally_count": None,
                          "local_objects_absent_remotely_count": None, "object_size_mismatch_count": None,
                          "ambiguous_basename_group_count": 0,
                          "bitwise_integrity_status": "NOT_VERIFIED_NO_CONTENT_HASHES"}
    else:
        list_summary = {"status": "NOT_RUN_NOT_REQUESTED", "complete": False,
                        "series_prefixes_listed": 0, "list_request_count": 0,
                        "list_page_count": 0, "response_bytes": 0,
                        "elapsed_seconds": 0, "failure_class": None,
                        "failure_reason_class": None, "http_status": None}
        object_summary = {"status": "OBJECT_INVENTORY_NOT_VERIFIED", "listed_series_count": 0,
                          "remote_object_count": None, "remote_object_bytes": None,
                          "matched_object_name_count": None, "remote_objects_missing_locally_count": None,
                          "local_objects_absent_remotely_count": None, "object_size_mismatch_count": None,
                          "ambiguous_basename_group_count": 0,
                          "bitwise_integrity_status": "NOT_VERIFIED_NO_CONTENT_HASHES"}

    result = {
        "task_id": TASK_ID,
        "plan_revision": PLAN_REVISION,
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "started_at_utc": started.isoformat(),
        "runtime": {
            "python": platform.python_version(),
            "duckdb": duckdb.__version__,
            "pyarrow": pyarrow.__version__,
            "pydicom": pydicom.__version__,
            "header_limit_files": MAX_LOCAL_FILES,
            "header_limit_seconds": MAX_HEADER_SECONDS,
            "public_list_request_limit": MAX_LIST_REQUESTS,
            "public_list_response_limit_bytes": MAX_LIST_RESPONSE_BYTES,
            "public_list_time_limit_seconds": MAX_LIST_SECONDS,
        },
        "official_index": index_summary,
        "manifest_mapping": mapping,
        "local_header_comparison": local_summary,
        "modality_gap_summary": modality_gap_summary,
        "private_series_gap_list": private_gap_summary,
        "remote_list": list_summary,
        "object_inventory": object_summary,
        "rtstruct_unmatched_reference_count": 61,
        "rtstruct_unmatched_reference_status": "UNKNOWN_NO_AUTHORIZED_SOP_TO_OBJECT_KEY_CROSSWALK",
        "source_claims": {
            "source_version_status": "SOURCE_VERSION_VERIFIED" if version_verified and manifest_valid else "VERSION_NOT_VERIFIED",
            "series_coverage_status": local_series["status"],
            "modality_reconciliation_status": modality_gap_summary["reconciliation_status"],
            "all_modalities_explained": modality_gap_summary["all_modalities_explained"],
            "object_inventory_status": object_summary["status"],
            "bitwise_integrity_status": object_summary["bitwise_integrity_status"],
        },
    }
    if previous_profile is not None:
        result["r1_history"] = previous_profile
        previous_filename_inventory = previous_profile.get("local_filename_inventory", {})
        result["local_filename_inventory"] = {
            **previous_filename_inventory,
            "file_count": local["file_count"],
            "total_bytes": after.get("total_bytes"),
            "basename_collision_group_count": after.get("duplicate_basename_group_count"),
            "raw_metadata_before_after_match": unchanged,
        }
    result["network_activity_r2"] = {
        "request_count": 0,
        "status": "NO_NETWORK_REQUESTS",
    }
    result["completion_method"] = (
        "R2_SINGLE_MINIMAL_HEADER_SCAN_WITH_MODALITY_SUMMARY_AND_PRIVATE_GAP_LIST"
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", required=True)
    parser.add_argument("--collections-index", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--previous-profile", help="Preserve accepted r1 aggregate and remote LIST evidence without network requests")
    parser.add_argument("--resume-profile", help="Reuse this task's completed aggregate Header scan and only verify mapping/LIST metadata")
    parser.add_argument("--private-gap-output", help="Optional UID-level shortage list; must be placed below this worktree's ignored .local")
    parser.add_argument("--list-public-s3", action="store_true",
                        help="Make anonymous ListObjectsV2 metadata requests within hard budgets")
    args = parser.parse_args(argv)
    try:
        if args.list_public_s3:
            raise AuditBlocked("NETWORK_REQUESTS_PROHIBITED_BY_PLAN_R2")
        if args.resume_profile and (args.private_gap_output or args.previous_profile):
            raise AuditBlocked("PRIVATE_GAP_LIST_REQUIRES_A_LIVE_HEADER_MAP")
        result = resume_with_remote_audit(args) if args.resume_profile else run_audit(args)
        output = Path(args.output).absolute()
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(output.suffix + ".tmp")
        temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(output)
        print(json.dumps({
            "status": "AUDIT_WRITTEN",
            "source_version_status": result["source_claims"]["source_version_status"],
            "series_coverage_status": result["source_claims"]["series_coverage_status"],
            "modality_reconciliation_status": result["source_claims"]["modality_reconciliation_status"],
            "object_inventory_status": result["source_claims"]["object_inventory_status"],
            "remote_list_request_count": result["remote_list"]["list_request_count"],
            "raw_metadata_before_after_match": result["local_header_comparison"]["raw_metadata_before_after_match"],
            "private_gap_list_created": result["private_series_gap_list"]["created"],
        }))
        return 0
    except AuditBlocked as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}))
        return 2
    except Exception as exc:
        print(json.dumps({"status": "FAILED", "error_class": type(exc).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
