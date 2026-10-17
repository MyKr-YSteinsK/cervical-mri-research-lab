#!/usr/bin/env python3
"""Read-only, aggregate-only CMRL-05 audit for an existing TCIA/IDC DICOM tree.

This wrapper reuses the reviewed CMRL-04/r2 DICOM parsing and RTSTRUCT logic.
It reads a user-specified manifest as inert text, never executes its commands,
does not contact TCIA/IDC/S3, and never decodes PixelData. Identifiers, names,
coordinates, source paths, and directory mappings stay in process memory.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Mapping

import pydicom

try:
    from . import audit_tcia_manual_dicom as manual
except ImportError:  # direct script invocation from scripts/r0
    import audit_tcia_manual_dicom as manual


TASK_ID = "CMRL-05"
PLAN_REVISION = "r1"
MAX_HEADER_FILES = 200_000
MAX_SECONDS = 60 * 60
EXPECTED_MANIFEST_BYTES = 52_045
EXPECTED_MANIFEST_SHA256 = (
    "f56073583ad4cf931a9a46fac83af2672f5b0248ebcc2a94406e9f662508ee79"
)
EXPECTED_PREFIX_COUNT = 821
MANIFEST_COMMAND = re.compile(r"cp s3://idc-open-data/([^ *]+)/[*] [.]")
RELEASE_RE = re.compile(r"IDC Data Release Version\s+([^\s]+)")
SIZE_RE = re.compile(r"Total manifest size on disk:\s*([0-9.]+\s+[A-Za-z]+)")
REPARSE_POINT = 0x400


class AuditBlocked(RuntimeError):
    """A safe, sanitized reason that prevents the requested scan from starting."""


def parse_manifest_bytes(content: bytes) -> dict[str, Any]:
    """Parse only the narrowly allowed s5cmd manifest grammar; never execute it."""
    try:
        text = content.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError:
        return {
            "_source_prefixes": frozenset(),
            "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "encoding_status": "INVALID",
            "release_version": None,
            "declared_size": None,
            "line_count": 0,
            "comment_count": 0,
            "blank_line_count": 0,
            "command_count": 0,
            "unique_source_prefix_count": 0,
            "duplicate_prefix_command_count": 0,
            "malformed_noncomment_line_count": 0,
            "structure_status": "MANIFEST_STRUCTURE_INVALID",
            "uploaded_copy_sha_matches": False,
        }

    prefixes: set[str] = set()
    comments = blanks = commands = malformed = duplicate = 0
    release: str | None = None
    declared_size: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            blanks += 1
            continue
        if line.startswith("#"):
            comments += 1
            release_match = RELEASE_RE.search(line)
            size_match = SIZE_RE.search(line)
            if release_match:
                release = release_match.group(1)
            if size_match:
                declared_size = size_match.group(1)
            continue
        commands += 1
        match = MANIFEST_COMMAND.fullmatch(line)
        if not match or any(character.isspace() for character in match.group(1)):
            malformed += 1
            continue
        prefix = match.group(1)
        if prefix in prefixes:
            duplicate += 1
        prefixes.add(prefix)

    sha = hashlib.sha256(content).hexdigest()
    structure_ok = (
        release == "25.0"
        and commands == EXPECTED_PREFIX_COUNT
        and len(prefixes) == EXPECTED_PREFIX_COUNT
        and duplicate == 0
        and malformed == 0
    )
    return {
        "_source_prefixes": frozenset(prefixes),
        "bytes": len(content),
        "sha256": sha,
        "encoding_status": "UTF8_VALID",
        "release_version": release,
        "declared_size": declared_size,
        "line_count": len(text.splitlines()),
        "comment_count": comments,
        "blank_line_count": blanks,
        "command_count": commands,
        "unique_source_prefix_count": len(prefixes),
        "duplicate_prefix_command_count": duplicate,
        "malformed_noncomment_line_count": malformed,
        "structure_status": (
            "MANIFEST_STRUCTURE_VERIFIED" if structure_ok else "MANIFEST_STRUCTURE_INVALID"
        ),
        "uploaded_copy_sha_matches": (
            len(content) == EXPECTED_MANIFEST_BYTES
            and sha == EXPECTED_MANIFEST_SHA256
        ),
    }


def public_manifest_summary(parsed: Mapping[str, Any]) -> dict[str, Any]:
    """Drop the private source-prefix set before serialization."""
    return {key: value for key, value in parsed.items() if not key.startswith("_")}


def assess_series_coverage(
    manifest_prefixes: Iterable[str],
    prefix_to_series_uid: Mapping[str, str] | None,
    local_series_file_counts: Mapping[str, int],
) -> dict[str, Any]:
    """Assess coverage only when a separately validated prefix-to-UID map exists."""
    prefixes = set(manifest_prefixes)
    if prefix_to_series_uid is None:
        return {
            "status": "SERIES_COVERAGE_NOT_VERIFIED",
            "manifest_prefix_count": len(prefixes),
            "mapped_prefix_count": 0,
            "unmapped_prefix_count": len(prefixes),
            "ambiguous_mapping_count": 0,
            "mapped_series_missing_or_empty_count": 0,
            "mapping_source_verified": False,
        }

    mapped = [prefix_to_series_uid.get(prefix) for prefix in prefixes]
    valid = [value for value in mapped if value]
    target_counts = collections.Counter(valid)
    ambiguous = sum(count > 1 for count in target_counts.values())
    unmapped = len(prefixes) - len(valid)
    missing_or_empty = sum(
        local_series_file_counts.get(series_uid, 0) <= 0 for series_uid in valid
    )
    mapping_complete = unmapped == 0 and ambiguous == 0
    if not mapping_complete:
        status = "SERIES_COVERAGE_NOT_VERIFIED"
    elif missing_or_empty:
        status = "SERIES_COVERAGE_GAPS_FOUND"
    else:
        status = "SERIES_COVERAGE_VERIFIED"
    return {
        "status": status,
        "manifest_prefix_count": len(prefixes),
        "mapped_prefix_count": len(valid),
        "unmapped_prefix_count": unmapped,
        "ambiguous_mapping_count": ambiguous,
        "mapped_series_missing_or_empty_count": missing_or_empty,
        "mapping_source_verified": mapping_complete,
    }


def assess_object_completeness(
    expected_object_ids: Iterable[str] | None,
    observed_object_ids: Iterable[str],
    *,
    authoritative_source_verified: bool,
) -> dict[str, Any]:
    """Compare object IDs only when an authoritative, version-matched list exists."""
    if expected_object_ids is None or not authoritative_source_verified:
        return {
            "status": "OBJECT_LEVEL_COMPLETENESS_NOT_VERIFIED",
            "expected_object_count": None,
            "observed_object_count": None,
            "missing_object_count": None,
            "unexpected_object_count": None,
        }
    expected = set(expected_object_ids)
    observed = set(observed_object_ids)
    missing = expected - observed
    unexpected = observed - expected
    complete = not missing and not unexpected
    return {
        "status": (
            "OBJECT_LEVEL_COMPLETENESS_VERIFIED"
            if complete
            else "OBJECT_LEVEL_COMPLETENESS_GAPS_FOUND"
        ),
        "expected_object_count": len(expected),
        "observed_object_count": len(observed),
        "missing_object_count": len(missing),
        "unexpected_object_count": len(unexpected),
    }


def summarize_cooccurrence_without_direct_reference(
    rt_items: Iterable[Mapping[str, Any]],
    series_to_records: Mapping[str, list[Mapping[str, Any]]],
    mr_series: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Count same-key MR-Series pairs that have no direct SOP/Series/Frame link."""
    same_patient_without_direct = 0
    same_study_without_direct = 0
    same_frame_without_direct = 0
    rtstruct_count = 0
    for rt in rt_items:
        rtstruct_count += 1
        sop_refs = rt.get("_sop_refs", set())
        series_refs = rt.get("_series_refs", set())
        frame_refs = rt.get("_frame_refs", set())
        for series_uid, info in mr_series.items():
            records = series_to_records.get(series_uid, [])
            direct_sop = any(
                record.get("_sop") and record.get("_sop") in sop_refs
                for record in records
            )
            direct_series = series_uid in series_refs
            direct_frame = bool(set(info.get("frames", set())).intersection(frame_refs))
            has_direct_reference = direct_sop or direct_series or direct_frame
            same_patient = bool(
                rt.get("_patient")
                and rt.get("_patient") in info.get("patients", set())
            )
            same_study = bool(rt.get("_study") and rt.get("_study") in info.get("studies", set()))
            same_frame = direct_frame
            same_patient_without_direct += int(same_patient and not has_direct_reference)
            same_study_without_direct += int(same_study and not has_direct_reference)
            same_frame_without_direct += int(same_frame and not has_direct_reference)
    return {
        "pair_unit": "one RTSTRUCT and one local MR Series",
        "direct_reference_definition": "SOP Instance, Series Instance, or Frame of Reference UID",
        "same_patient_key_without_direct_reference_pair_count": same_patient_without_direct,
        "same_study_key_without_direct_reference_pair_count": same_study_without_direct,
        "same_frame_key_without_direct_reference_pair_count": same_frame_without_direct,
        "rtstruct_count_considered": rtstruct_count,
    }


def _is_reparse(path: Path) -> bool:
    value = os.stat(path, follow_symlinks=False)
    return stat.S_ISLNK(value.st_mode) or bool(
        getattr(value, "st_file_attributes", 0) & REPARSE_POINT
    )


def _assert_safe_roots(project_root: Path, data_root: Path, manual_root: Path) -> None:
    if (
        data_root.name.casefold() != "ccth_idc_v25_full"
        or manual_root.name.casefold() != "ccth_manual"
        or not _is_descendant_or_same(project_root, data_root)
        or not _is_descendant_or_same(project_root, manual_root)
    ):
        raise AuditBlocked("INPUT_ROOT_OUTSIDE_AUTHORIZED_PATH")
    for path in (project_root, data_root, manual_root):
        current = path
        while True:
            if _is_reparse(current):
                raise AuditBlocked("INPUT_PATH_CONTAINS_REPARSE_POINT")
            if current.parent == current:
                break
            current = current.parent
    try:
        common = os.path.commonpath((str(data_root), str(manual_root)))
    except ValueError:
        raise AuditBlocked("INPUT_ROOT_COMPARISON_FAILED") from None
    if os.path.normcase(common) in {
        os.path.normcase(str(data_root)),
        os.path.normcase(str(manual_root)),
    }:
        raise AuditBlocked("FULL_AND_MANUAL_INPUTS_OVERLAP")


def filesystem_supplement(root: Path, deadline: float) -> dict[str, Any]:
    """Collect aggregate metadata without reading file contents or following links."""
    counts: collections.Counter[str] = collections.Counter()
    extensions: collections.Counter[str] = collections.Counter()
    basename_counts: collections.Counter[str] = collections.Counter()
    metadata_errors: collections.Counter[str] = collections.Counter()
    snapshot_hash = hashlib.sha256()
    stack = [root]
    counts["directories_including_root"] = 1

    while stack:
        if time.monotonic() >= deadline:
            counts["time_limit_reached"] = 1
            break
        current = stack.pop()
        try:
            with os.scandir(current) as iterator:
                entries = sorted(iterator, key=lambda item: item.name.casefold())
        except Exception as exc:
            metadata_errors[type(exc).__name__] += 1
            counts["directory_read_errors"] += 1
            continue
        child_directories: list[str] = []
        for entry in entries:
            if time.monotonic() >= deadline:
                counts["time_limit_reached"] = 1
                break
            try:
                item_stat = entry.stat(follow_symlinks=False)
                attributes = int(getattr(item_stat, "st_file_attributes", 0))
                reparse = stat.S_ISLNK(item_stat.st_mode) or bool(
                    attributes & REPARSE_POINT
                )
                is_directory = entry.is_dir(follow_symlinks=False)
            except Exception as exc:
                metadata_errors[type(exc).__name__] += 1
                counts["metadata_error_count"] += 1
                continue
            if reparse:
                counts["reparse_entry_count"] += 1
                if is_directory:
                    counts["reparse_directory_not_followed_count"] += 1
                else:
                    counts["reparse_file_not_followed_count"] += 1
                continue
            if is_directory:
                counts["directories_including_root"] += 1
                child_directories.append(entry.path)
                continue
            if not stat.S_ISREG(item_stat.st_mode):
                counts["special_nonregular_entry_count"] += 1
                continue

            counts["file_count"] += 1
            size = int(item_stat.st_size)
            counts["total_bytes"] += size
            counts["zero_byte_file_count"] += int(size == 0)
            basename_counts[entry.name.casefold()] += 1
            extension = manual._safe_extension(entry.name)
            extensions[extension] += 1
            if extension not in {".dcm", ".dicom", ".ima", ".dcm.gz"}:
                counts["nonstandard_extension_file_count"] += 1
            try:
                counts["unreadable_access_flag_count"] += int(
                    not os.access(entry.path, os.R_OK)
                )
            except Exception as exc:
                metadata_errors[type(exc).__name__] += 1
                counts["read_access_probe_error_count"] += 1

            relative = os.path.relpath(entry.path, root).replace(os.sep, "/")
            encoded = relative.encode("utf-8", errors="surrogateescape")
            snapshot_hash.update(len(encoded).to_bytes(4, "big"))
            snapshot_hash.update(encoded)
            snapshot_hash.update(size.to_bytes(8, "big", signed=False))
            snapshot_hash.update(int(item_stat.st_mtime_ns).to_bytes(8, "big", signed=True))
            snapshot_hash.update(attributes.to_bytes(8, "big", signed=False))
        stack.extend(reversed(child_directories))

    collisions = [count for count in basename_counts.values() if count > 1]
    disk = shutil.disk_usage(root)
    result = dict(counts)
    result.update(
        {
            "inventory_complete": not counts["time_limit_reached"]
            and not counts["directory_read_errors"]
            and not counts["metadata_error_count"],
            "extension_counts": dict(sorted(extensions.items())),
            "duplicate_basename_group_count": len(collisions),
            "duplicate_basename_extra_file_count": sum(count - 1 for count in collisions),
            "metadata_error_classes": dict(sorted(metadata_errors.items())),
            "disk_total_bytes": disk.total,
            "disk_free_bytes": disk.free,
            "_metadata_snapshot_sha256": snapshot_hash.hexdigest(),
        }
    )
    return result


def _inventory_snapshots_match(before: Mapping[str, Any], after: Mapping[str, Any]) -> bool:
    return bool(
        before.get("inventory_complete")
        and after.get("inventory_complete")
        and before.get("_metadata_snapshot_sha256")
        == after.get("_metadata_snapshot_sha256")
        and before.get("file_count") == after.get("file_count")
        and before.get("total_bytes") == after.get("total_bytes")
    )


def _public_inventory(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if not key.startswith("_")}


def _is_descendant_or_same(parent: Path, child: Path) -> bool:
    try:
        return os.path.commonpath((str(parent), str(child))) == str(parent)
    except ValueError:
        return False


def run_audit(args: argparse.Namespace) -> dict[str, Any]:
    started = time.monotonic()
    deadline = started + args.time_limit_seconds
    project_root = Path(os.path.abspath(args.project_root))
    data_root = project_root / "data" / "raw" / "tcia" / "ccth_idc_v25_full"
    manual_root = project_root / "data" / "raw" / "tcia" / "ccth_manual"
    manifest_path = Path(os.path.abspath(args.manifest))
    output_path = Path(os.path.abspath(args.output))
    if output_path.exists():
        raise AuditBlocked("OUTPUT_ALREADY_EXISTS")
    _assert_safe_roots(project_root, data_root, manual_root)
    if not data_root.is_dir() or not manifest_path.is_file():
        raise AuditBlocked("REQUIRED_INPUT_UNAVAILABLE")
    manifest_ancestor = manifest_path
    while True:
        if _is_reparse(manifest_ancestor):
            raise AuditBlocked("MANIFEST_PATH_CONTAINS_REPARSE_POINT")
        if manifest_ancestor.parent == manifest_ancestor:
            break
        manifest_ancestor = manifest_ancestor.parent
    if _is_descendant_or_same(data_root, output_path):
        raise AuditBlocked("OUTPUT_INSIDE_SOURCE_DATA")

    try:
        manifest_content = manifest_path.read_bytes()
    except Exception as exc:
        raise AuditBlocked("MANIFEST_READ_FAILED_" + type(exc).__name__) from None
    manifest = parse_manifest_bytes(manifest_content)
    if manifest["structure_status"] != "MANIFEST_STRUCTURE_VERIFIED":
        raise AuditBlocked("MANIFEST_STRUCTURE_INVALID")

    before = filesystem_supplement(data_root, deadline)
    if not before.get("inventory_complete"):
        raise AuditBlocked("FILESYSTEM_INVENTORY_INCOMPLETE")
    if before.get("reparse_entry_count", 0):
        raise AuditBlocked("REPARSE_ENTRY_DETECTED")
    if before.get("disk_free_bytes", 0) <= 0:
        raise AuditBlocked("DISK_STATUS_UNAVAILABLE")

    # The CMRL-04/r2 scanner supplies the reviewed DICOM and RTSTRUCT parsing.
    # Setting this limit to zero guarantees no force=True parse attempt occurs.
    original_task_id = manual.TASK_ID
    original_plan_revision = manual.PLAN_REVISION
    original_header_limit = manual.MAX_HEADER_FILES
    original_force_limit = manual.FORCED_PARSE_TRIAL_LIMIT
    original_builder = manual._build_record
    original_reference_audit = manual._reference_audit
    series_parent_directories: dict[str, set[str]] = collections.defaultdict(set)

    def record_series_directory(
        path: str, size: int, dataset: Any, forced: bool
    ) -> dict[str, Any]:
        record = original_builder(path, size, dataset, forced)
        series_uid = record.get("_series")
        if series_uid:
            relative_parent = os.path.relpath(os.path.dirname(path), data_root)
            directory_key = os.path.normcase(relative_parent).replace(os.sep, "/")
            directory_digest = hashlib.sha256(
                directory_key.encode("utf-8", errors="surrogateescape")
            ).hexdigest()
            series_parent_directories[series_uid].add(directory_digest)
        return record

    def audit_reference_cooccurrence(
        rt_items: list[dict[str, Any]],
        sop_to_records: dict[str, list[dict[str, Any]]],
        series_to_records: dict[str, list[dict[str, Any]]],
        mr_series: dict[str, dict[str, Any]],
        all_headers_resolved: bool,
    ) -> dict[str, Any]:
        summary = original_reference_audit(
            rt_items,
            sop_to_records,
            series_to_records,
            mr_series,
            all_headers_resolved,
        )
        summary["cooccurrence_without_direct_reference"] = (
            summarize_cooccurrence_without_direct_reference(
                rt_items, series_to_records, mr_series
            )
        )
        return summary

    try:
        manual.TASK_ID = TASK_ID
        manual.PLAN_REVISION = PLAN_REVISION
        manual.MAX_HEADER_FILES = MAX_HEADER_FILES
        manual.FORCED_PARSE_TRIAL_LIMIT = 0
        manual._build_record = record_series_directory
        manual._reference_audit = audit_reference_cooccurrence
        remaining_seconds = int(deadline - time.monotonic())
        if remaining_seconds < 1:
            raise AuditBlocked("TIME_BUDGET_EXHAUSTED_BEFORE_HEADER_SCAN")
        run_args = argparse.Namespace(
            data_dir=str(data_root),
            output=str(output_path),
            max_headers=args.max_headers,
            time_limit_seconds=remaining_seconds,
        )
        result = manual.run_audit(run_args)
    finally:
        manual.TASK_ID = original_task_id
        manual.PLAN_REVISION = original_plan_revision
        manual.MAX_HEADER_FILES = original_header_limit
        manual.FORCED_PARSE_TRIAL_LIMIT = original_force_limit
        manual._build_record = original_builder
        manual._reference_audit = original_reference_audit

    after = filesystem_supplement(data_root, deadline)
    supplement_unchanged = _inventory_snapshots_match(before, after)
    source_unchanged = bool(
        supplement_unchanged
        and result.get("source_snapshot_check", {}).get(
            "all_source_files_unchanged_by_metadata"
        )
    )
    if not source_unchanged:
        result["audit_status"] = "BLOCKED"
    elif not before.get("inventory_complete") or not after.get("inventory_complete"):
        result["audit_status"] = "PARTIAL"

    official_size_bytes_approx = 28_390_000_000
    local_bytes = result.get("filesystem", {}).get("total_bytes", 0)
    local_series_count = result.get("dicom", {}).get(
        "distinct_series_instance_uid_count", 0
    )
    prefixes = manifest["_source_prefixes"]
    result.update(
        {
            "manifest": public_manifest_summary(manifest)
            | {
                "source_command_shape": "cp s3://idc-open-data/<prefix>/* .",
                "wildcard_contains_object_level_expected_list": False,
                "source_prefix_values_serialized": False,
            },
            "integrity_levels": {
                "manifest_structure": manifest["structure_status"],
                "manifest_source_prefix_count": manifest["unique_source_prefix_count"],
                "trusted_prefix_to_series_uid_mapping_available": False,
                "series_coverage": "SERIES_COVERAGE_NOT_VERIFIED",
                "local_unique_series_uid_count": local_series_count,
                "official_collection_series_count": 821,
                "numeric_series_count_agreement_is_mapping_evidence": False,
                "object_level_completeness": "OBJECT_LEVEL_COMPLETENESS_NOT_VERIFIED",
                "object_level_reason": (
                    "Manifest source prefixes use /* and do not enumerate expected objects."
                ),
            },
            "directory_structure": {
                "full_and_manual_directories_are_disjoint": True,
                "full_data_root_alias": "data/raw/tcia/ccth_idc_v25_full",
                "manual_subset_alias": "data/raw/tcia/ccth_manual",
                "series_uids_spanning_multiple_immediate_parent_directories_count": sum(
                    len(directories) > 1
                    for directories in series_parent_directories.values()
                ),
            },
            "filesystem_supplement": {
                "before": _public_inventory(before),
                "after": _public_inventory(after),
                "metadata_snapshot_unchanged": supplement_unchanged,
                "snapshot_definition": (
                    "relative path, byte size, last-write timestamp, and file attributes"
                ),
                "content_hashes_computed": False,
            },
            "official_collection_comparison": {
                "official_subjects_reported": 23,
                "official_studies_reported": 171,
                "official_series_reported": 821,
                "official_images_reported": 131_556,
                "official_image_size_reported": "28.39 GB (rounded publication statistic)",
                "local_dicom_file_count": result.get("filesystem", {}).get("file_count"),
                "local_bytes": local_bytes,
                "local_decimal_gb": round(local_bytes / 1_000_000_000, 6),
                "local_gib": round(local_bytes / (1024**3), 6),
                "difference_from_28_39_decimal_gb_approx_bytes": (
                    official_size_bytes_approx - local_bytes
                ),
                "user_reported_byte_count_matches_local": local_bytes == 28_151_425_416,
                "counts_have_identical_semantics": False,
                "independent_collection_membership_verified": False,
            },
            "series_coverage_assessment": assess_series_coverage(
                prefixes, None, {}
            ),
            "object_completeness_assessment": assess_object_completeness(
                None, (), authoritative_source_verified=False
            ),
            "privacy": {
                **result.get("privacy", {}),
                "manifest_prefix_values_serialized": False,
                "directory_mapping_serialized": False,
                "case_level_rows_serialized": False,
            },
            "research_boundary": {
                **result.get("research_boundary", {}),
                "r0_complete": False,
                "tcia_idc_s3_accessed": False,
                "manifest_commands_executed": False,
                "original_files_written": False,
                "clinical_workbook_read": False,
                "roi_clinical_semantics_verified": False,
                "tumor_mask_created": False,
            },
            "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "task_elapsed_seconds_including_manifest_and_inventory": round(
                time.monotonic() - started, 3
            ),
            "plan_budget": {
                "header_file_limit": args.max_headers,
                "time_limit_seconds": args.time_limit_seconds,
                "standard_parse_only": True,
                "rtstruct_max_deep_parse_bytes": manual.MAX_RTSTRUCT_FILE_BYTES,
            },
        }
    )
    manual._write_json(output_path, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-headers", type=int, default=MAX_HEADER_FILES)
    parser.add_argument("--time-limit-seconds", type=int, default=MAX_SECONDS)
    args = parser.parse_args()
    if not 1 <= args.max_headers <= MAX_HEADER_FILES:
        parser.error(f"--max-headers must be between 1 and {MAX_HEADER_FILES}")
    if not 1 <= args.time_limit_seconds <= MAX_SECONDS:
        parser.error(f"--time-limit-seconds must be between 1 and {MAX_SECONDS}")
    try:
        result = run_audit(args)
    except AuditBlocked as exc:
        print(json.dumps({"task_id": TASK_ID, "audit_status": "BLOCKED", "reason": str(exc)}))
        return 2
    except Exception as exc:
        print(
            json.dumps(
                {"task_id": TASK_ID, "audit_status": "BLOCKED", "error_class": type(exc).__name__}
            ),
            file=sys.stderr,
        )
        return 2

    print(
        json.dumps(
            {
                "task_id": TASK_ID,
                "audit_status": result["audit_status"],
                "file_count": result["filesystem"]["file_count"],
                "total_bytes": result["filesystem"]["total_bytes"],
                "header_files_attempted": result["coverage"]["header_files_attempted"],
                "standard_parse_count": result["coverage"]["standard_parse_count"],
                "parse_failure_count": result["coverage"]["parse_failure_count"],
                "modality_counts": result["dicom"]["modality_counts"],
                "distinct_patient_id_values": result["dicom"]["distinct_patient_id_values"],
                "distinct_study_count": result["dicom"]["distinct_study_instance_uid_count"],
                "distinct_series_count": result["dicom"]["distinct_series_instance_uid_count"],
                "rtstruct_count": result["rtstruct"]["instance_count"],
                "source_metadata_unchanged": result["source_snapshot_check"][
                    "all_source_files_unchanged_by_metadata"
                ],
                "elapsed_seconds": result["coverage"]["elapsed_seconds"],
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return 0 if result["audit_status"] == "COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
