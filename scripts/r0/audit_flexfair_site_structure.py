#!/usr/bin/env python3
"""Privacy-preserving FlexFair ZIP structure, pairing, and exact-duplicate audit.

Only aggregate counts, source integrity values, and audit method metadata are
written. ZIP member names, per-file hashes, image pixels, and case-level records
remain in process memory and are never emitted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from audit_flexfair_archive import RASTER_EXTENSIONS, _role_and_key

EXPECTED_SIZE = 348_731_016
EXPECTED_MD5 = "303ae54703fdccc63302cb755aed792a"
EXPECTED_SHA256 = "4efdfa6b6dbf4174a1b7ce2b0eb8878e739f0365829a89d57fdf5223c82817ec"
AUTHOR_REPO = "https://github.com/MaksimXing/FlexFair"
AUTHOR_COMMIT = "f7da0fc0a9a4ad7c96f2c7b48699fc8cc151e320"
GROUPS = ("zhongda", "shengfuyou", "zhongzhong", "new_zhongyi")
MAX_MEMBER_BYTES = 64 * 1024 * 1024
MAX_PIXELS = 100_000_000


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def hash_archive(path: Path) -> tuple[str, str]:
    md5 = hashlib.md5()
    sha256 = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            md5.update(chunk)
            sha256.update(chunk)
    return md5.hexdigest(), sha256.hexdigest()


def sequence_present(parts: tuple[str, ...], sequence: tuple[str, ...]) -> bool:
    width = len(sequence)
    return any(parts[i:i + width] == sequence for i in range(len(parts) - width + 1))


def classify_path(name: str) -> tuple[str, str, bool, bool]:
    """Return split, public-code group, strict train/test path flags, group ambiguity."""
    all_parts = tuple(p for p in PurePosixPath(name.replace("\\", "/")).parts if p not in {"", "."})
    parts = all_parts[:-1]  # Directory structure only; never classify on a case filename.
    folded = tuple(p.casefold() for p in parts)
    directory_tokens = {
        token
        for part in folded
        for token in re.split(r"[^a-z0-9]+", part)
        if token
    }
    has_train = bool(directory_tokens & {"train", "training"})
    has_test = bool(directory_tokens & {"test", "testing"})
    split = "mixed" if has_train and has_test else "train" if has_train else "test" if has_test else "unclassified"

    found_groups = {group for group in GROUPS if group in folded}
    group = next(iter(found_groups)) if len(found_groups) == 1 else "ambiguous" if found_groups else "unclassified"
    strict_train = any(sequence_present(parts, ("Private", "train", group_name)) for group_name in GROUPS)
    strict_test = any(sequence_present(parts, ("Private", "test", group_name)) for group_name in GROUPS)
    return split, group, strict_train, strict_test


def decoded_pixel_digest(archive: zipfile.ZipFile, info: zipfile.ZipInfo) -> str:
    """Hash a normalized RGBA pixel matrix without returning the digest."""
    if info.file_size > MAX_MEMBER_BYTES:
        raise ValueError("member size limit")
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Pillow unavailable") from exc

    with archive.open(info, "r") as member:
        with Image.open(member) as image:
            width, height = image.size
            if width <= 0 or height <= 0 or width * height > MAX_PIXELS:
                raise ValueError("pixel dimension limit")
            image.load()
            rgba = image.convert("RGBA")
            digest = hashlib.sha256()
            digest.update(b"CMRL-02-FlexFair-RGBA-v1\0")
            digest.update(width.to_bytes(8, "big"))
            digest.update(height.to_bytes(8, "big"))
            digest.update(rgba.tobytes())
            return digest.hexdigest()


def build_audit(archive_path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "audit": "CMRL-02 FlexFair grouping, identity clues, and exact duplicate audit",
        "observed_at_utc": utc_now(),
        "privacy": {
            "archive_member_names_emitted": False,
            "patient_or_site_values_emitted": False,
            "per_file_hashes_emitted": False,
            "image_pixels_emitted": False,
        },
        "source": {
            "figshare_article_id": 28639598,
            "figshare_file_id": 53159216,
            "expected_size_bytes": EXPECTED_SIZE,
            "expected_md5": EXPECTED_MD5,
            "expected_sha256": EXPECTED_SHA256,
        },
        "author_code": {
            "repository": AUTHOR_REPO,
            "commit": AUTHOR_COMMIT,
            "data_directory_groups": list(GROUPS),
            "image_mask_rule": "exclude basename containing literal 'label'; target basename[:-4] + '_label.png' in same directory",
            "train_test_code_paths": ["Private/train/<group>/", "Private/test/<group>/"],
        },
    }

    if not archive_path.is_file() or archive_path.stat().st_size != EXPECTED_SIZE:
        result["status"] = "UNAVAILABLE_OR_SIZE_MISMATCH"
        result["archive"] = {"expected_size_match": False, "zip_opened": False}
        return result

    actual_md5, actual_sha256 = hash_archive(archive_path)
    integrity_ok = actual_md5.casefold() == EXPECTED_MD5 and actual_sha256.casefold() == EXPECTED_SHA256
    result["archive"] = {
        "size_bytes": archive_path.stat().st_size,
        "md5": actual_md5,
        "sha256": actual_sha256,
        "official_md5_match": actual_md5.casefold() == EXPECTED_MD5,
        "cmrl01_sha256_match": actual_sha256.casefold() == EXPECTED_SHA256,
        "zip_opened": False,
    }
    if not integrity_ok:
        result["status"] = "INTEGRITY_MISMATCH_STOPPED"
        return result

    try:
        archive = zipfile.ZipFile(archive_path, "r")
    except Exception as exc:
        result["status"] = "ZIP_OPEN_FAILED"
        result["archive"]["open_error_type"] = type(exc).__name__
        return result

    with archive:
        all_infos = archive.infolist()
        infos = [info for info in all_infos if not info.is_dir()]
        directory_infos = [info for info in all_infos if info.is_dir()]
        png_infos = [info for info in infos if PurePosixPath(info.filename.replace("\\", "/")).suffix.casefold() == ".png"]
        crc_bad = archive.testzip()
        result["archive"].update({
            "zip_opened": True,
            "file_count": len(infos),
            "directory_entry_count": len(directory_infos),
            "png_file_count": len(png_infos),
            "crc_check_completed": True,
            "crc_check_passed": crc_bad is None,
        })
        if crc_bad is not None:
            result["status"] = "CRC_CHECK_FAILED_STOPPED"
            return result

        # The following structures hold raw paths only in memory and are never serialized.
        members_by_path: dict[str, list[zipfile.ZipInfo]] = defaultdict(list)
        normalized_images: dict[str, list[zipfile.ZipInfo]] = defaultdict(list)
        normalized_masks: dict[str, list[zipfile.ZipInfo]] = defaultdict(list)
        author_image_infos: list[zipfile.ZipInfo] = []
        author_mask_infos: list[zipfile.ZipInfo] = []
        author_pairs: set[tuple[int, int]] = set()
        scope_counts: Counter[tuple[str, str, str]] = Counter()
        layout_counts: Counter[tuple[str, str, str]] = Counter()
        manifest_hint_count = 0
        patient_pattern_count = 0
        site_pattern_count = 0
        group_directory_file_counts: Counter[str] = Counter()
        strict_layout_file_counts: Counter[str] = Counter()
        code_group_directory_entries: Counter[str] = Counter()
        expected_layout_directory_entries: Counter[tuple[str, str]] = Counter()
        private_directory_entries = 0

        for info in directory_infos:
            directory_name = info.filename.replace("\\", "/").rstrip("/")
            parts = tuple(p for p in PurePosixPath(directory_name).parts if p not in {"", "."})
            folded = tuple(p.casefold() for p in parts)
            private_directory_entries += int("private" in folded)
            for group in GROUPS:
                if group in folded:
                    code_group_directory_entries[group] += 1
                if parts[-3:] == ("Private", "train", group):
                    expected_layout_directory_entries[("train", group)] += 1
                if parts[-3:] == ("Private", "test", group):
                    expected_layout_directory_entries[("test", group)] += 1

        for info in png_infos:
            name = info.filename.replace("\\", "/")
            path = PurePosixPath(name)
            basename = path.name
            members_by_path[name].append(info)
            split, group, strict_train, strict_test = classify_path(name)
            role, norm_key = _role_and_key(info)
            if role is None:
                role = "other"
            scope_counts[(split, group, role)] += 1
            if strict_train:
                strict_layout_file_counts["train"] += 1
                layout_counts[("train", group, role)] += 1
            if strict_test:
                strict_layout_file_counts["test"] += 1
                layout_counts[("test", group, role)] += 1
            if group in GROUPS:
                group_directory_file_counts[group] += 1

            if norm_key and role == "image":
                normalized_images[norm_key].append(info)
            elif norm_key and role == "mask":
                normalized_masks[norm_key].append(info)

            if "label" in basename:
                author_mask_infos.append(info)
            else:
                author_image_infos.append(info)

            lower_name = basename.casefold()
            if any(token in lower_name for token in ("manifest", "metadata", "split", "patient", "case", "center", "centre", "site", "subject", "mapping", "index", "train", "test", "fold")):
                manifest_hint_count += 1
            patient_pattern_count += int(bool(re.search(r"(?:patient|subject|case|pt)[-_ ]?\d{2,}", name, re.IGNORECASE)))
            site_pattern_count += int(bool(re.search(r"(?:site|center|centre)[-_ ]?\d{1,}", name, re.IGNORECASE)))

        # Rebuild exact author-rule candidates after the full ZIP index is available.
        path_lookup = {name: values for name, values in members_by_path.items()}
        author_pairs.clear()
        for info in author_image_infos:
            name = info.filename.replace("\\", "/")
            path = PurePosixPath(name)
            basename = path.name
            if len(basename) < 4:
                continue
            target_name = str(path.with_name(basename[:-4] + "_label.png"))
            matches = path_lookup.get(target_name, [])
            if len(matches) == 1:
                author_pairs.add((info.header_offset, matches[0].header_offset))

        normalized_pair_keys = set(normalized_images) & set(normalized_masks)
        normalized_unique_keys = {
            key for key in normalized_pair_keys
            if len(normalized_images[key]) == 1 and len(normalized_masks[key]) == 1
        }
        normalized_pairs = {
            (normalized_images[key][0].header_offset, normalized_masks[key][0].header_offset)
            for key in normalized_unique_keys
        }
        ambiguous_keys = sum(
            1 for key in normalized_pair_keys
            if len(normalized_images[key]) != 1 or len(normalized_masks[key]) != 1
        )
        paired_author_mask_offsets = {mask for _, mask in author_pairs}
        repeated_basename_directories: dict[str, set[str]] = defaultdict(set)
        for info in author_image_infos:
            path = PurePosixPath(info.filename.replace("\\", "/"))
            repeated_basename_directories[path.name].add(str(path.parent))
        repeated_basename_count = sum(1 for dirs in repeated_basename_directories.values() if len(dirs) > 1)

        breakdown: dict[str, dict[str, dict[str, int]]] = {}
        all_splits = ("train", "test", "unclassified", "mixed")
        all_groups = (*GROUPS, "unclassified", "ambiguous")
        all_roles = ("image", "mask", "other")
        for split in all_splits:
            breakdown[split] = {}
            for group in all_groups:
                breakdown[split][group] = {role: scope_counts[(split, group, role)] for role in all_roles}

        observed_train_directory_files = sum(value for (split, _, _), value in scope_counts.items() if split == "train")
        observed_test_directory_files = sum(value for (split, _, _), value in scope_counts.items() if split == "test")

        expected_layout: dict[str, dict[str, dict[str, int]]] = {}
        for split in ("train", "test"):
            expected_layout[split] = {}
            for group in (*GROUPS, "unclassified", "ambiguous"):
                expected_layout[split][group] = {role: layout_counts[(split, group, role)] for role in all_roles}

        # Exact decoded-pixel hashes are transient dictionary keys only.
        pixel_hash_counts: Counter[str] = Counter()
        split_pixel_counts: dict[str, Counter[str]] = {"train": Counter(), "test": Counter()}
        group_split_pixel_counts: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
        decode_failures: Counter[str] = Counter()
        decoded_count = 0
        image_candidates = [info for info in png_infos if _role_and_key(info)[0] == "image"]
        try:
            for info in image_candidates:
                split, group, _, _ = classify_path(info.filename)
                try:
                    pixel_hash = decoded_pixel_digest(archive, info)
                except Exception as exc:  # Error messages may contain source paths; only type is retained.
                    decode_failures[type(exc).__name__] += 1
                    continue
                decoded_count += 1
                pixel_hash_counts[pixel_hash] += 1
                if split in {"train", "test"}:
                    split_pixel_counts[split][pixel_hash] += 1
                    group_split_pixel_counts[(split, group)][pixel_hash] += 1
        except Exception as exc:
            result["status"] = "PIXEL_AUDIT_FAILED"
            result["pixel_audit_error_type"] = type(exc).__name__
            return result

        cross_split_hashes = set(split_pixel_counts["train"]) & set(split_pixel_counts["test"])
        cross_split_matching_pairs = sum(
            split_pixel_counts["train"][digest] * split_pixel_counts["test"][digest]
            for digest in cross_split_hashes
        )
        within_group_split_duplicates = sum(
            count - 1
            for counts in group_split_pixel_counts.values()
            for count in counts.values()
            if count > 1
        )
        result["zip_structure"] = {
            "file_count": len(infos),
            "directory_entry_count": len(directory_infos),
            "png_count": len(png_infos),
            "observed_train_directory_png_count": observed_train_directory_files,
            "observed_test_directory_png_count": observed_test_directory_files,
            "private_train_group_file_count": strict_layout_file_counts["train"],
            "private_test_group_file_count": strict_layout_file_counts["test"],
            "code_group_directory_file_counts": {group: group_directory_file_counts[group] for group in GROUPS},
            "code_group_directory_entry_counts": {group: code_group_directory_entries[group] for group in GROUPS},
            "private_directory_entry_count": private_directory_entries,
            "author_expected_loader_directory_entry_counts": {
                split: {group: expected_layout_directory_entries[(split, group)] for group in GROUPS}
                for split in ("train", "test")
            },
            "train_test_group_role_counts": expected_layout,
            "observed_path_group_role_counts": breakdown,
            "manifest_filename_hint_count": manifest_hint_count,
            "patient_token_pattern_match_count": patient_pattern_count,
            "site_token_pattern_match_count": site_pattern_count,
            "patient_or_site_mapping_contents_inspected": False,
        }
        result["pairing"] = {
            "author_rule": {
                "image_candidates": len(author_image_infos),
                "label_name_candidates": len(author_mask_infos),
                "exact_same_directory_pairs": len(author_pairs),
                "unpaired_image_candidates": len(author_image_infos) - len(author_pairs),
                "unpaired_label_name_candidates": len(author_mask_infos) - len(paired_author_mask_offsets),
                "loader_scope_train_test_group_files": {
                    "train": strict_layout_file_counts["train"],
                    "test": strict_layout_file_counts["test"],
                },
            },
            "cmrl01_normalization_rule": {
                "image_candidates": sum(len(v) for v in normalized_images.values()),
                "mask_candidates": sum(len(v) for v in normalized_masks.values()),
                "matched_keys": len(normalized_pair_keys),
                "unambiguous_pairs": len(normalized_pairs),
                "ambiguous_keys": ambiguous_keys,
                "unpaired_image_candidates": sum(len(v) for k, v in normalized_images.items() if k not in normalized_pair_keys),
                "unpaired_mask_candidates": sum(len(v) for k, v in normalized_masks.items() if k not in normalized_pair_keys),
            },
            "cross_rule_comparison": {
                "identical_member_pairs": len(author_pairs & normalized_pairs),
                "author_only_pairs": len(author_pairs - normalized_pairs),
                "normalization_only_pairs": len(normalized_pairs - author_pairs),
            },
            "repeated_image_basenames_in_multiple_directories": repeated_basename_count,
        }
        result["exact_pixel_duplicates"] = {
            "comparison_unit": "decoded RGBA pixel matrix plus width and height",
            "candidate_image_count": len(image_candidates),
            "decoded_image_count": decoded_count,
            "decode_failure_count": sum(decode_failures.values()),
            "decode_failure_types": dict(sorted(decode_failures.items())),
            "distinct_pixel_matrices": len(pixel_hash_counts),
            "duplicate_extra_records_across_all_images": decoded_count - len(pixel_hash_counts),
            "train_directory_present": observed_train_directory_files > 0,
            "test_directory_present": observed_test_directory_files > 0,
            "distinct_matrices_present_in_both_train_and_test": len(cross_split_hashes),
            "cross_split_matching_pairs": cross_split_matching_pairs,
            "within_same_split_duplicate_extra_records": within_group_split_duplicates,
            "within_same_split_and_author_group_duplicate_extra_records": sum(
                count - 1
                for (_, group), counts in group_split_pixel_counts.items()
                if group in GROUPS
                for count in counts.values()
                if count > 1
            ),
            "within_same_split_and_unclassified_group_duplicate_extra_records": sum(
                count - 1
                for (_, group), counts in group_split_pixel_counts.items()
                if group == "unclassified"
                for count in counts.values()
                if count > 1
            ),
            "split_level_interpretation": "Exact duplicate pixel matches are not patient identities and absence does not rule out different slices from one patient across splits.",
        }
        result["identity_evidence"] = {
            "author_code_exposes_patient_key": False,
            "author_code_has_site_like_group_path_labels": True,
            "archive_contains_author_group_directory_labels": False,
            "clinical_site_mapping_from_group_labels_verified": False,
            "patient_wise_split_declaration_verified": False,
            "patient_or_site_mapping_in_archive_verified": False,
            "status": "UNKNOWN; author group labels are not mapped to verified clinical centres and no patient key is established",
        }
        result["status"] = "PROFILED" if decoded_count == len(image_candidates) else "PROFILED_WITH_DECODE_FAILURES"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", nargs="?", default="data/raw/flexfair/CervicalCancerDataset.zip")
    parser.add_argument("--output", default="evidence/r0/flexfair_site_mapping_audit.json")
    args = parser.parse_args()
    project_root = Path(__file__).resolve().parents[2]
    archive_path = Path(args.archive)
    if not archive_path.is_absolute():
        archive_path = project_root / archive_path
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = project_root / output_path
    try:
        output_path.resolve().relative_to((project_root / "evidence" / "r0").resolve())
    except ValueError:
        print(json.dumps({"status": "OUTPUT_PATH_OUTSIDE_EVIDENCE_R0"}))
        return 2

    try:
        result = build_audit(archive_path)
    except Exception as exc:
        # Exception strings and tracebacks can expose archive member names.
        result = {"status": "AUDIT_FAILED", "error_type": type(exc).__name__}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary = {
        "status": result.get("status"),
        "archive_sha256_match": result.get("archive", {}).get("cmrl01_sha256_match"),
        "png_count": result.get("zip_structure", {}).get("png_count"),
        "author_pairs": result.get("pairing", {}).get("author_rule", {}).get("exact_same_directory_pairs"),
        "normalized_pairs": result.get("pairing", {}).get("cmrl01_normalization_rule", {}).get("unambiguous_pairs"),
        "decoded_images": result.get("exact_pixel_duplicates", {}).get("decoded_image_count"),
        "duplicate_extra_records": result.get("exact_pixel_duplicates", {}).get("duplicate_extra_records_across_all_images"),
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if result.get("status") in {"PROFILED", "PROFILED_WITH_DECODE_FAILURES"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
