#!/usr/bin/env python3
"""Offline, privacy-preserving profile of the authorized FlexFair ZIP.

The script never prints or stores archive member names or image pixels. It can
optionally extract one unambiguous filename-paired raster image/mask to generic
names under ignored local data/ storage after archive safety and CRC checks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

EXPECTED_SIZE = 348_731_016
EXPECTED_MD5 = "303ae54703fdccc63302cb755aed792a"
MAX_ARCHIVE_BYTES = 400_000_000
MAX_EXPANDED_BYTES = 8 * 1024**3
MAX_MEMBER_RATIO = 1_000.0
MAX_SAMPLE_MEMBER_BYTES = 64 * 1024**2
MAX_SAMPLE_TOTAL_BYTES = 128 * 1024**2
RASTER_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".gif"}
MASK_TOKENS = {"mask", "masks", "seg", "segmentation", "label", "labels", "roi", "gt", "groundtruth"}
IMAGE_TOKENS = {"image", "images", "img", "scan", "t2", "t2wi"}
SAFE_TOP_LEVEL_LABELS = {
    "train", "training", "test", "testing", "valid", "validation", "val",
    "image", "images", "mask", "masks", "label", "labels", "data",
    "seg", "segmentation", "t2", "t2wi",
}
SUPPORTED_ZIP_METHODS = {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED, zipfile.ZIP_BZIP2, zipfile.ZIP_LZMA}
SAFE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".gif", ".zip",
    ".csv", ".tsv", ".json", ".xlsx", ".txt", ".xml", ".yaml", ".yml",
    ".md", ".nii", ".gz", ".nrrd", ".mha", ".mhd", ".dcm", ".dicom",
    ".npy", ".npz", ".mat", ".pdf", ".py",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def hash_file(path: Path) -> tuple[str, str]:
    md5 = hashlib.md5()
    sha256 = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            md5.update(chunk)
            sha256.update(chunk)
    return md5.hexdigest(), sha256.hexdigest()


def _normalized_path_key(value: str) -> str:
    normalized = value.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.casefold()


def _safe_extension(name: str) -> str:
    suffix = Path(PurePosixPath(name.replace("\\", "/")).name).suffix.casefold()
    return suffix if suffix in SAFE_EXTENSIONS else ("[no extension]" if not suffix else "[other extension]")


def _path_flags(name: str) -> tuple[bool, bool, bool]:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    absolute = path.is_absolute() or bool(re.match(r"^[A-Za-z]:", normalized))
    traversal = ".." in path.parts
    malformed = "\x00" in normalized or not normalized
    return absolute, traversal, malformed


def _role_and_key(info: zipfile.ZipInfo) -> tuple[str | None, str | None]:
    path = PurePosixPath(info.filename.replace("\\", "/"))
    suffix = Path(path.name).suffix.casefold()
    if suffix not in RASTER_EXTENSIONS:
        return None, None
    stem = path.name[:-len(suffix)] if suffix else path.name
    stem_tokens = [t for t in re.split(r"[^a-z0-9]+", stem.casefold()) if t]
    directory_tokens = [
        t for part in path.parts[:-1]
        for t in re.split(r"[^a-z0-9]+", part.casefold())
        if t
    ]
    in_mask_dir = any(t in MASK_TOKENS for t in directory_tokens)
    in_mask_name = any(t in MASK_TOKENS for t in stem_tokens)
    role = "mask" if in_mask_dir or in_mask_name else "image"
    removable = MASK_TOKENS | IMAGE_TOKENS
    key_dirs = [t for t in directory_tokens if t not in removable]
    key_stem = [t for t in stem_tokens if t not in removable]
    if not key_stem:
        return role, None
    key = "/".join(key_dirs + key_stem)
    return role, key


def _decode_sample(path: Path, *, is_mask: bool) -> dict[str, Any]:
    try:
        from PIL import Image
    except ImportError:
        return {"decoded": False, "reason": "Pillow unavailable"}

    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            width, height = image.size
            if width <= 0 or height <= 0 or width * height > 100_000_000:
                return {"decoded": False, "reason": "pixel dimension safety limit"}
            image.load()
            result: dict[str, Any] = {
                "decoded": True,
                "format": image.format,
                "width": width,
                "height": height,
                "mode": image.mode,
                "channels": {"1": 1, "L": 1, "P": 1, "I": 1, "F": 1, "I;16": 1, "LA": 2, "RGB": 3, "RGBA": 4, "CMYK": 4}.get(image.mode),
                "sample_type": {"1": "1-bit", "L": "8-bit unsigned", "P": "8-bit indexed", "I;16": "16-bit integer", "I": "32-bit integer", "F": "32-bit float"}.get(image.mode, "channel format from mode"),
            }
            if is_mask:
                colors = image.getcolors(maxcolors=257)
                result["unique_value_count"] = len(colors) if colors is not None else ">256"
            return result
    except Exception as exc:  # Store the error kind only; no member names or pixel data.
        return {"decoded": False, "reason": type(exc).__name__}


def profile_archive(archive_path: Path, *, expected_md5: str, extract_one_pair: bool, sample_dir: Path) -> dict[str, Any]:
    archive_path = archive_path.resolve()
    profile: dict[str, Any] = {
        "audit": "CMRL-01 FlexFair archive file-level admission audit",
        "observed_at_utc": utc_now(),
        "source": {
            "figshare_article_id": 28639598,
            "figshare_file_id": 53159216,
            "expected_filename": "CervicalCancerDataset.zip",
            "expected_size_bytes": EXPECTED_SIZE,
            "expected_computed_md5": expected_md5,
        },
        "privacy": {
            "archive_member_names_emitted": False,
            "patient_or_site_identifiers_emitted": False,
            "pixel_values_emitted": False,
        },
        "archive": {"filename": archive_path.name, "size_bytes": archive_path.stat().st_size},
    }

    if archive_path.stat().st_size > MAX_ARCHIVE_BYTES:
        profile["status"] = "SAFETY_STOP_ARCHIVE_SIZE_LIMIT"
        profile["archive_safety"] = {"max_archive_bytes": MAX_ARCHIVE_BYTES, "zip_opened": False}
        return profile

    actual_md5, sha256 = hash_file(archive_path)
    profile["archive"].update({
        "md5": actual_md5,
        "sha256": sha256,
        "official_md5_match": actual_md5.casefold() == expected_md5.casefold(),
        "expected_size_match": archive_path.stat().st_size == EXPECTED_SIZE,
    })
    if not profile["archive"]["official_md5_match"] or not profile["archive"]["expected_size_match"]:
        profile["status"] = "FILE_INTEGRITY_MISMATCH"
        profile["archive_safety"] = {"zip_opened": False}
        return profile

    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            infos = archive.infolist()
            files = [info for info in infos if not info.is_dir()]
            extension_counts: Counter[str] = Counter()
            top_level_counts: Counter[str] = Counter()
            method_counts: Counter[str] = Counter()
            medical_format_counts: Counter[str] = Counter()
            image_count = 0
            mask_name_count = 0
            manifest_candidate_count = 0
            absolute_count = traversal_count = malformed_count = symlink_count = special_file_count = 0
            encrypted_count = unsupported_method_count = duplicate_path_count = 0
            expanded_bytes = 0
            compressed_bytes = 0
            max_ratio = 0.0
            zero_compressed_nonempty = 0
            seen_paths: set[str] = set()
            archive_paths: set[str] = set()
            archive_basenames: Counter[str] = Counter()
            image_keys: dict[str, list[zipfile.ZipInfo]] = defaultdict(list)
            mask_keys: dict[str, list[zipfile.ZipInfo]] = defaultdict(list)
            manifest_filename_hint_count = 0
            filename_patient_pattern_count = 0
            filename_site_pattern_count = 0

            for info in infos:
                name = info.filename
                absolute, traversal, malformed = _path_flags(name)
                absolute_count += int(absolute)
                traversal_count += int(traversal)
                malformed_count += int(malformed)
                collision_key = name.replace("\\", "/").rstrip("/").casefold()
                if collision_key in seen_paths:
                    duplicate_path_count += 1
                seen_paths.add(collision_key)
                mode = info.external_attr >> 16
                symlink_count += int(stat.S_ISLNK(mode))
                mode_type = stat.S_IFMT(mode)
                special_file_count += int(bool(mode_type and mode_type not in {stat.S_IFREG, stat.S_IFDIR, stat.S_IFLNK}))
                encrypted_count += int(bool(info.flag_bits & 0x1))
                unsupported_method_count += int(info.compress_type not in SUPPORTED_ZIP_METHODS)
                method_counts[str(info.compress_type)] += 1
                if info.is_dir():
                    continue

                normalized_file_name = _normalized_path_key(name)
                archive_paths.add(normalized_file_name)
                archive_basenames[PurePosixPath(normalized_file_name).name] += 1

                expanded_bytes += info.file_size
                compressed_bytes += info.compress_size
                if info.compress_size == 0 and info.file_size > 0:
                    zero_compressed_nonempty += 1
                elif info.compress_size > 0:
                    max_ratio = max(max_ratio, info.file_size / info.compress_size)
                suffix = Path(PurePosixPath(name.replace("\\", "/")).name).suffix.casefold()
                extension_counts[_safe_extension(name)] += 1
                lowered_name = name.casefold().replace("\\", "/")
                for medical_suffix in (".nii.gz", ".nii", ".nrrd", ".mha", ".mhd", ".dcm", ".dicom", ".npy", ".npz"):
                    if lowered_name.endswith(medical_suffix):
                        medical_format_counts[medical_suffix] += 1
                        break
                first = PurePosixPath(name.replace("\\", "/")).parts[0].casefold() if "/" in name or "\\" in name else ""
                if not first:
                    top_level_counts["[root files]"] += 1
                else:
                    top_level_counts[first if first in SAFE_TOP_LEVEL_LABELS else "[other]"] += 1
                base = PurePosixPath(name.replace("\\", "/")).name.casefold()
                manifest_name_hint = any(token in base for token in ("manifest", "metadata", "split", "patient", "case", "center", "centre", "site", "subject", "mapping", "index", "label", "annotation", "train", "test", "valid", "fold"))
                if suffix in {".csv", ".tsv", ".json", ".xlsx"} or (suffix in {".txt", ".xml", ".yaml", ".yml"} and manifest_name_hint):
                    manifest_candidate_count += 1
                    manifest_filename_hint_count += int(manifest_name_hint)
                filename_patient_pattern_count += int(bool(re.search(r"(?:patient|subject|case|pt)[-_ ]?\d{2,}", name, re.IGNORECASE)))
                filename_site_pattern_count += int(bool(re.search(r"(?:site|center|centre)[-_ ]?\d{1,}", name, re.IGNORECASE)))
                role, key = _role_and_key(info)
                if role == "image":
                    image_count += 1
                    if key:
                        image_keys[key].append(info)
                elif role == "mask":
                    mask_name_count += 1
                    if key:
                        mask_keys[key].append(info)

            pair_keys = sorted(set(image_keys) & set(mask_keys))
            unique_pair_keys = [key for key in pair_keys if len(image_keys[key]) == 1 and len(mask_keys[key]) == 1]
            candidate_pairs = sum(min(len(image_keys[key]), len(mask_keys[key])) for key in pair_keys)
            safety_flags = {
                "expanded_size_over_limit": expanded_bytes > MAX_EXPANDED_BYTES,
                "max_member_ratio_over_limit": max_ratio > MAX_MEMBER_RATIO,
                "zero_compressed_nonempty_member": zero_compressed_nonempty > 0,
                "absolute_paths": absolute_count > 0,
                "path_traversal": traversal_count > 0,
                "malformed_paths": malformed_count > 0,
                "symbolic_links": symlink_count > 0,
                "special_file_members": special_file_count > 0,
                "duplicate_or_case_colliding_paths": duplicate_path_count > 0,
                "encrypted_members": encrypted_count > 0,
                "unsupported_compression": unsupported_method_count > 0,
            }
            safe_to_read = not any(safety_flags.values())
            crc_passed: bool | None = None
            crc_error_present = False
            if safe_to_read:
                try:
                    crc_error_present = archive.testzip() is not None
                    crc_passed = not crc_error_present
                except (OSError, RuntimeError, zipfile.BadZipFile, NotImplementedError):
                    crc_passed = False
                    crc_error_present = True

            profile["archive_safety"] = {
                "zip_opened": True,
                "member_count_including_directories": len(infos),
                "file_count": len(files),
                "expanded_bytes": expanded_bytes,
                "compressed_bytes": compressed_bytes,
                "max_expanded_bytes": MAX_EXPANDED_BYTES,
                "max_member_compression_ratio": round(max_ratio, 4),
                "max_member_ratio_limit": MAX_MEMBER_RATIO,
                "compression_methods": dict(sorted(method_counts.items())),
                "extension_counts": dict(sorted(extension_counts.items())),
                "medical_imaging_or_array_format_counts": dict(sorted(medical_format_counts.items())),
                "top_level_logical_counts": dict(sorted(top_level_counts.items())),
                "image_like_raster_count": image_count,
                "mask_name_candidate_count": mask_name_count,
                "filename_pair_candidate_count": candidate_pairs,
                "unambiguous_filename_pair_candidate_count": len(unique_pair_keys),
                "structured_metadata_candidate_count": manifest_candidate_count,
                "manifest_filename_hint_count": manifest_filename_hint_count,
                "manifest_contents_inspected": False,
                "filename_patient_token_candidate_count": filename_patient_pattern_count,
                "filename_site_token_candidate_count": filename_site_pattern_count,
                "path_names_emitted": False,
                "safety_flags": safety_flags,
                "safe_to_read_members": safe_to_read,
                "crc_check_completed": crc_passed is not None,
                "crc_check_passed": crc_passed,
                "crc_error_present": crc_error_present,
            }
            profile["identity_evidence"] = {
                "patient_key_evidence": "structured metadata candidate exists; contents require separate review" if manifest_candidate_count else "filename patterns only; no authoritative patient mapping established",
                "site_key_evidence": "structured metadata candidate exists; contents require separate review" if manifest_candidate_count else "no authoritative site mapping established",
                "patient_key_manifest_file_count": 0,
                "site_key_manifest_file_count": 0,
                "patient_or_site_values_emitted": False,
            }
            profile["status"] = "PROFILED" if safe_to_read and crc_passed else "SAFETY_STOP_OR_CRC_FAILURE"

            sample_result: dict[str, Any] = {"requested": extract_one_pair, "extracted": False}
            if extract_one_pair and safe_to_read and crc_passed and unique_pair_keys:
                if sample_dir.exists():
                    sample_result["reason"] = "sample output already exists; refusing overwrite"
                else:
                    key = unique_pair_keys[0]
                    image_info = image_keys[key][0]
                    mask_info = mask_keys[key][0]
                    sizes_ok = image_info.file_size <= MAX_SAMPLE_MEMBER_BYTES and mask_info.file_size <= MAX_SAMPLE_MEMBER_BYTES and image_info.file_size + mask_info.file_size <= MAX_SAMPLE_TOTAL_BYTES
                    if not sizes_ok:
                        sample_result["reason"] = "candidate exceeds sample extraction size limits"
                    else:
                        sample_dir.mkdir(parents=True, exist_ok=False)
                        image_suffix = Path(image_info.filename).suffix.casefold() or ".bin"
                        mask_suffix = Path(mask_info.filename).suffix.casefold() or ".bin"
                        image_out = sample_dir / f"sample_image{image_suffix}"
                        mask_out = sample_dir / f"sample_mask{mask_suffix}"
                        try:
                            for info, destination in ((image_info, image_out), (mask_info, mask_out)):
                                written = 0
                                with archive.open(info, "r") as src, destination.open("xb") as dst:
                                    while chunk := src.read(1024 * 1024):
                                        written += len(chunk)
                                        if written > MAX_SAMPLE_MEMBER_BYTES:
                                            raise ValueError("sample member exceeded extraction size limit")
                                        dst.write(chunk)
                            image_profile = _decode_sample(image_out, is_mask=False)
                            mask_profile = _decode_sample(mask_out, is_mask=True)
                            sample_result.update({
                                "extracted": True,
                                "sample_files_saved_locally": True,
                                "image": image_profile,
                                "mask": mask_profile,
                                "dimensions_match": bool(image_profile.get("decoded") and mask_profile.get("decoded") and image_profile.get("width") == mask_profile.get("width") and image_profile.get("height") == mask_profile.get("height")),
                                "member_names_emitted": False,
                            })
                        except Exception as exc:
                            sample_result.update({"extracted": False, "reason": type(exc).__name__})
            profile["sample_pair_check"] = sample_result
    except (OSError, zipfile.BadZipFile, EOFError, ValueError) as exc:
        profile["status"] = "ZIP_OPEN_OR_PROFILE_ERROR"
        profile["error_kind"] = type(exc).__name__
    return profile


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="local authorized ZIP path; do not put under Git")
    parser.add_argument("--output", type=Path, default=Path("evidence/r0/flexfair_archive_profile.json"))
    parser.add_argument("--expected-md5", default=EXPECTED_MD5)
    parser.add_argument("--extract-one-pair", action="store_true", help="extract one safe, unambiguous raster pair under local data/ after CRC checks")
    parser.add_argument("--sample-dir", type=Path, default=Path("data/raw/flexfair/audit_sample"))
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    data_root = (repo_root / "data").resolve()
    archive_path = args.archive.resolve()
    sample_dir = args.sample_dir.resolve()
    if archive_path.name != "CervicalCancerDataset.zip" or not archive_path.is_relative_to(data_root):
        parser.error("archive must be the authorized CervicalCancerDataset.zip stored under this repository's data/ directory")
    if args.extract_one_pair and not sample_dir.is_relative_to(data_root):
        parser.error("sample output must stay under this repository's ignored data/ directory")
    profile = profile_archive(archive_path, expected_md5=args.expected_md5, extract_one_pair=args.extract_one_pair, sample_dir=sample_dir)
    if args.output.is_file():
        try:
            prior_profile = json.loads(args.output.read_text(encoding="utf-8"))
            same_archive = prior_profile.get("archive", {}).get("sha256") == profile.get("archive", {}).get("sha256")
            if same_archive:
                if isinstance(prior_profile.get("transfer"), dict):
                    profile["transfer"] = prior_profile["transfer"]
                prior_sample = prior_profile.get("sample_pair_check")
                if (isinstance(prior_sample, dict) and prior_sample.get("extracted")
                        and len(list(sample_dir.glob("sample_image.*"))) == 1
                        and len(list(sample_dir.glob("sample_mask.*"))) == 1):
                    profile["sample_pair_check"] = {**prior_sample, "reused_prior_extraction_evidence": True}
        except (OSError, json.JSONDecodeError, AttributeError):
            pass
    rendered = json.dumps(profile, ensure_ascii=False, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return 0 if profile.get("status") == "PROFILED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
