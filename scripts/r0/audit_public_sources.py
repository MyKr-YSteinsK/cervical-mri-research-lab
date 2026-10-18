#!/usr/bin/env python3
"""Capture sanitized public metadata for the CMRL-00 R0 access audit.

This script makes unauthenticated GET requests only. It never downloads dataset
archives or DICOM, and it stores only selected public metadata and response hashes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import xml.etree.ElementTree as ET
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

USER_AGENT = "CMRL-00-R0-audit/1.0"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def request(url: str, timeout: float) -> tuple[dict[str, Any], bytes | None]:
    started = utc_now()
    tick = time.monotonic()
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json,text/html,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read(8_000_001)
            record = {
                "requested_url": url,
                "final_url": response.geturl(),
                "observed_at_utc": started,
                "elapsed_ms": round((time.monotonic() - tick) * 1000),
                "status": response.status,
                "content_type": response.headers.get("Content-Type"),
                "content_length_header": response.headers.get("Content-Length"),
                "bytes_read": len(body),
                "body_truncated_at_8mb": len(body) > 8_000_000,
                "body_sha256": hashlib.sha256(body).hexdigest(),
            }
            return record, body
    except urllib.error.HTTPError as exc:
        body = exc.read(4096)
        return ({
            "requested_url": url,
            "final_url": exc.geturl(),
            "observed_at_utc": started,
            "elapsed_ms": round((time.monotonic() - tick) * 1000),
            "status": exc.code,
            "content_type": exc.headers.get("Content-Type") if exc.headers else None,
            "bytes_read": len(body),
            "body_sha256": hashlib.sha256(body).hexdigest(),
        }, body)
    except Exception as exc:
        return ({
            "requested_url": url,
            "final_url": None,
            "observed_at_utc": started,
            "elapsed_ms": round((time.monotonic() - tick) * 1000),
            "status": None,
            "error_kind": type(exc).__name__,
        }, None)


def figshare_article(article_id: int, timeout: float) -> dict[str, Any]:
    url = f"https://api.figshare.com/v2/articles/{article_id}"
    response, body = request(url, timeout)
    result: dict[str, Any] = {"request": response, "article_id_requested": article_id}
    if response.get("status") == 200 and body is not None:
        obj = json.loads(body)
        result["article"] = {
            "id": obj.get("id"),
            "doi": obj.get("doi"),
            "title": obj.get("title"),
            "version": obj.get("version"),
            "published_date": obj.get("published_date"),
            "modified_date": obj.get("modified_date"),
            "license": (obj.get("license") or {}).get("name"),
            "files": [{
                "name": f.get("name"),
                "size_bytes": f.get("size"),
                "md5": f.get("md5"),
                "computed_md5": f.get("computed_md5"),
                "is_link_only": f.get("is_link_only"),
                "download_url": f.get("download_url"),
            } for f in obj.get("files", [])],
        }
    return result


def github_repo(owner: str, name: str, timeout: float) -> dict[str, Any]:
    base = f"https://api.github.com/repos/{owner}/{name}"
    repo_response, repo_body = request(base, timeout)
    result: dict[str, Any] = {"repository_request": repo_response}
    branch = "main"
    if repo_response.get("status") == 200 and repo_body is not None:
        repo = json.loads(repo_body)
        branch = repo.get("default_branch") or branch
        result["repository"] = {
            "full_name": repo.get("full_name"),
            "html_url": repo.get("html_url"),
            "default_branch": branch,
            "created_at": repo.get("created_at"),
            "updated_at": repo.get("updated_at"),
            "pushed_at": repo.get("pushed_at"),
            "archived": repo.get("archived"),
            "license_spdx_id": (repo.get("license") or {}).get("spdx_id"),
        }
        commit_url = f"{base}/commits/{branch}"
        commit_response, commit_body = request(commit_url, timeout)
        result["latest_commit_request"] = commit_response
        if commit_response.get("status") == 200 and commit_body is not None:
            commit = json.loads(commit_body)
            result["latest_commit"] = {
                "sha": commit.get("sha"),
                "committed_at": commit.get("commit", {}).get("committer", {}).get("date"),
                "message": (commit.get("commit", {}).get("message") or "").splitlines()[0],
            }
    else:
        # The candidate repositories' main branch was separately resolved
        # with `git ls-remote --symref ... HEAD` during this audit. Use public
        # raw and Atom endpoints as a metadata-only fallback, never git clone.
        result["fallback_branch"] = branch
        feed_url = f"https://github.com/{owner}/{name}/commits/{branch}.atom"
        commit_response, commit_body = request(feed_url, timeout)
        result["latest_commit_feed_request"] = commit_response
        if commit_response.get("status") == 200 and commit_body is not None:
            try:
                root = ET.fromstring(commit_body)
                atom = "{http://www.w3.org/2005/Atom}"
                entry = root.find(f"{atom}entry")
                if entry is not None:
                    commit_id = entry.findtext(f"{atom}id", default="")
                    sha = commit_id.rsplit("/", 1)[-1]
                    result["latest_commit"] = {
                        "sha": sha if re.fullmatch(r"[0-9a-f]{40}", sha) else None,
                        "updated_at": entry.findtext(f"{atom}updated"),
                        "source": "GitHub public Atom feed",
                    }
            except ET.ParseError:
                result["latest_commit_parse_error"] = "invalid_atom_xml"

    readme_url = f"https://raw.githubusercontent.com/{owner}/{name}/{branch}/README.md"
    readme_response, readme_body = request(readme_url, timeout)
    result["readme_request"] = readme_response
    if readme_response.get("status") == 200 and readme_body is not None:
        text = readme_body.decode("utf-8", "replace")
        result["readme_facts"] = {
            "sha256": hashlib.sha256(readme_body).hexdigest(),
            "figshare_id_mentions": sorted(set(re.findall(r"m9\.figshare\.(\d+)", text))),
            "figshare_anchor_targets": re.findall(r"\[Figshare\]\((https://doi\.org/10\.6084/m9\.figshare\.\d+[^)]*)\)", text, re.I),
            "mentions_google_drive_links": "drive.google.com" in text.casefold(),
            "mentions_dicom_png": bool(re.search(r"DICOM\s*\([^)]*\)\s*\+\s*PNG", text, re.I)),
            "mentions_nrrd_pair": "T2wI.nrrd" in text and "tumor_mask.nrrd" in text,
            "mentions_access_password_request": "request access password" in text.casefold(),
        }
    return result


def tcia_collection(timeout: float) -> dict[str, Any]:
    url = "https://www.cancerimagingarchive.net/api/v1/collections/41813"
    response, body = request(url, timeout)
    result: dict[str, Any] = {"request": response}
    if response.get("status") == 200 and body is not None:
        obj = json.loads(body)
        result["collection"] = {
            "id": obj.get("id"),
            "title": obj.get("collection_title"),
            "slug": obj.get("slug"),
            "page_url": obj.get("link"),
            "doi": obj.get("collection_doi"),
            "version_number": obj.get("version_number"),
            "published_date": obj.get("date"),
            "modified_gmt": obj.get("modified_gmt"),
            "date_updated": obj.get("date_updated"),
            "subject_count": int(obj["subjects"]) if str(obj.get("subjects", "")).isdigit() else None,
            "data_types": obj.get("data_types") if isinstance(obj.get("data_types"), list) else [],
            "collection_download_entry_count": len(obj.get("collection_downloads", [])) if isinstance(obj.get("collection_downloads"), list) else None,
        }
    return result


def idc_collection(timeout: float) -> dict[str, Any]:
    url = "https://portal.imaging.datacommons.cancer.gov/collections/cc_tumor_heterogeneity/"
    response, body = request(url, timeout)
    result: dict[str, Any] = {"request": response}
    if response.get("status") == 200 and body is not None:
        html = body.decode("utf-8", "replace")
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text)
        result["collection_page_facts"] = {
            "page_sha256": hashlib.sha256(body).hexdigest(),
            "mentions_23_subjects": "Subject Count: 23" in text or "Subject Count 23" in text,
            "mentions_mr": bool(re.search(r"Image Modalities[^.]{0,200}\bMR\b", text, re.I)),
            "mentions_rtstruct": "RTSTRUCT" in text,
            "mentions_clinical_support": "Supporting Data: Clinical" in text or "Supporting Data Clinical" in text,
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("evidence/r0/public_source_metadata.json"))
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()
    payload = {
        "audit": "CMRL-00 / R0 public source metadata",
        "run_started_at_utc": utc_now(),
        "authentication": "unauthenticated public GET requests; no GitHub token or cookies used",
        "downloads_performed": False,
        "sources": {
            "figshare_28639598": figshare_article(28639598, args.timeout),
            "figshare_28636133": figshare_article(28636133, args.timeout),
            "flexfair_github": github_repo("MaksimXing", "FlexFair", args.timeout),
            "ccmd_github": github_repo("peekaboo990", "CCMD-Cervical-Cancer-MRI-Dataset", args.timeout),
            "tcia_collection": tcia_collection(args.timeout),
            "idc_collection": idc_collection(args.timeout),
        },
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
