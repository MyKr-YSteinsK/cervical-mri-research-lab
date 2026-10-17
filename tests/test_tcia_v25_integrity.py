from __future__ import annotations

import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

import pyarrow as pa
import pyarrow.parquet as pq

from audit_tcia_v25_integrity import (
    AuditBlocked,
    _public_list_summary,
    compare_object_inventory,
    compare_global_object_names,
    compare_series_instances,
    compare_series_instances_by_modality,
    build_private_series_gap_list,
    map_series_prefixes,
    normalize_series_url,
    parse_s3_list_page,
    public_private_gap_summary,
    run_audit,
    sha256_file,
    validate_private_gap_path,
    verify_parquet,
    list_public_objects,
    write_private_gap_list,
)


class _FakeResponse:
    def __init__(self, body: bytes, status: int = 200):
        self.body = body
        self.status = status
        self.headers = {"Content-Length": str(len(body))}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self, count: int = -1):
        return self.body if count < 0 else self.body[:count]


class IntegrityAuditTests(unittest.TestCase):
    def test_normalizes_only_authorized_bucket_and_safe_path(self):
        self.assertEqual(normalize_series_url("s3://idc-open-data/a-prefix/"), "a-prefix")
        self.assertEqual(normalize_series_url("s3://idc-open-data/a-prefix"), "a-prefix")
        self.assertIsNone(normalize_series_url("s3://other-bucket/a-prefix/"))
        self.assertIsNone(normalize_series_url("s3://idc-open-data/../unsafe/"))
        self.assertIsNone(normalize_series_url("https://idc-open-data.s3.amazonaws.com/a-prefix/"))

    def test_maps_series_one_to_one_and_reports_ambiguity(self):
        rows = [
            {"SeriesInstanceUID": "1.2.840.synthetic.1", "series_aws_url": "s3://idc-open-data/prefix-a/1/"},
            {"SeriesInstanceUID": "1.2.840.synthetic.2", "series_aws_url": "s3://idc-open-data/prefix-b/1"},
        ]
        summary, mapping, _reverse = map_series_prefixes({"prefix-a", "prefix-b"}, rows)
        self.assertEqual(summary["mapping_status"], "MAPPING_VERIFIED")
        self.assertEqual(summary["mapped_unique_prefix_count"], 2)
        self.assertEqual(mapping["prefix-a"], "1.2.840.synthetic.1")

        ambiguous_rows = rows + [
            {"SeriesInstanceUID": "1.2.840.synthetic.3", "series_aws_url": "s3://idc-open-data/prefix-a/"}
        ]
        ambiguous, _mapping, _reverse = map_series_prefixes({"prefix-a", "prefix-b"}, ambiguous_rows)
        self.assertEqual(ambiguous["ambiguous_prefix_count"], 1)
        self.assertEqual(ambiguous["mapping_status"], "MAPPING_PARTIAL")

    def test_parquet_version_and_checksum_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic.parquet"
            table = pa.Table.from_pylist([{"collection_id": "synthetic"}])
            table = table.replace_schema_metadata({b"idc_index_data_version": b"25.0.0-0-gsynthetic"})
            pq.write_table(table, path)
            digest = sha256_file(path)
            ok = verify_parquet(path, digest, "25.0.0-0-gsynthetic", {"collection_id"})
            wrong_version = verify_parquet(path, digest, "25.0.1-0-gsynthetic", {"collection_id"})
            wrong_digest = verify_parquet(path, "0" * 64, "25.0.0-0-gsynthetic", {"collection_id"})
        self.assertTrue(ok["verified"])
        self.assertFalse(wrong_version["verified"])
        self.assertFalse(wrong_digest["verified"])

    def test_series_instance_comparison_catches_missing_shortage_and_excess(self):
        rows = [
            {"SeriesInstanceUID": "1.2.synthetic.1", "instanceCount": 3},
            {"SeriesInstanceUID": "1.2.synthetic.2", "instanceCount": 2},
            {"SeriesInstanceUID": "1.2.synthetic.3", "instanceCount": 1},
        ]
        local = {"unique_sop_count_by_series": {
            "1.2.synthetic.1": 2,
            "1.2.synthetic.2": 4,
        }}
        result = compare_series_instances(rows, local, mapping_verified=True)
        self.assertEqual(result["missing_series_count"], 1)
        self.assertEqual(result["series_with_instance_shortage_count"], 2)
        self.assertEqual(result["series_with_instance_excess_count"], 1)
        self.assertEqual(result["sum_shortage"], 2)
        self.assertEqual(result["sum_excess"], 2)
        self.assertEqual(result["status"], "INSTANCE_COUNT_GAPS_FOUND")

    def test_private_gap_list_is_explicitly_uid_level_and_uses_synthetic_values(self):
        result = build_private_series_gap_list(
            [{"SeriesInstanceUID": "1.2.synthetic.1", "instanceCount": 3}],
            {"unique_sop_count_by_series": {"1.2.synthetic.1": 2}},
            {"1.2.synthetic.1": "synthetic-prefix"},
            raw_metadata_snapshot_verified=True,
            generated_at_utc="2026-10-17T00:00:00+00:00",
        )
        self.assertEqual(result["record_count"], 1)
        self.assertEqual(result["records"][0]["shortage_count"], 1)
        self.assertEqual(result["records"][0]["Modality"], "UNKNOWN/INVALID")
        self.assertEqual(result["records"][0]["series_source_prefix"], "synthetic-prefix")
        self.assertTrue(result["raw_metadata_snapshot_verified"])
        self.assertEqual(result["remote_object_status"], "NOT_ASSESSED_BY_THIS_PRIVATE_SERIES_LIST")

    def test_per_modality_summary_reconciles_all_five_modalities(self):
        rows = [
            {"SeriesInstanceUID": "synthetic-mr-1", "instanceCount": 3, "Modality": "MR"},
            {"SeriesInstanceUID": "synthetic-mr-2", "instanceCount": 2, "Modality": "MR"},
            {"SeriesInstanceUID": "synthetic-ct-1", "instanceCount": 4, "Modality": "CT"},
            {"SeriesInstanceUID": "synthetic-pt-1", "instanceCount": 2, "Modality": "PT"},
            {"SeriesInstanceUID": "synthetic-reg-1", "instanceCount": 1, "Modality": "REG"},
            {"SeriesInstanceUID": "synthetic-rtstruct-1", "instanceCount": 2, "Modality": "RTSTRUCT"},
        ]
        counts = {
            "synthetic-mr-1": 2,
            "synthetic-ct-1": 4,
            "synthetic-pt-1": 3,
            "synthetic-reg-1": 1,
            "synthetic-rtstruct-1": 2,
        }
        local = {
            "unique_sop_count_by_series": counts,
            "series_file_count_by_series": {uid: value for uid, value in counts.items()},
            "header_modalities_by_series": {
                "synthetic-mr-1": ["MR"],
                "synthetic-ct-1": ["CT"],
                "synthetic-pt-1": ["PT"],
                "synthetic-reg-1": ["REG"],
                "synthetic-rtstruct-1": ["RTSTRUCT"],
            },
            "modality_header_missing_or_invalid_file_count_by_series": {},
        }
        result = compare_series_instances_by_modality(rows, local, mapping_verified=True)
        self.assertEqual(result["reconciliation_status"], "RECONCILIATION_VERIFIED")
        self.assertTrue(result["all_modalities_explained"])
        self.assertEqual(set(result["by_modality"]), {"MR", "CT", "PT", "REG", "RTSTRUCT", "UNKNOWN/INVALID"})
        self.assertEqual(result["totals"]["expected_series"], 6)
        self.assertEqual(result["totals"]["local_matched_series"], 5)
        self.assertEqual(result["totals"]["missing_series"], 1)
        self.assertEqual(result["totals"]["equal_count_series"], 3)
        self.assertEqual(result["totals"]["partial_shortage_series"], 1)
        self.assertEqual(result["totals"]["all_shortage_series"], 1)
        self.assertEqual(result["totals"]["excess_series"], 1)
        self.assertEqual(result["totals"]["shortage_series_total"], 2)
        self.assertEqual(result["totals"]["expected_instances"], 14)
        self.assertEqual(result["totals"]["observed_unique_instances"], 12)
        self.assertEqual(result["totals"]["shortage_instances"], 3)
        self.assertEqual(result["totals"]["excess_instances"], 1)
        self.assertEqual(result["by_modality"]["MR"]["missing_series"], 1)
        self.assertEqual(result["by_modality"]["MR"]["partial_shortage_series"], 1)
        self.assertEqual(result["by_modality"]["PT"]["excess_series"], 1)
        self.assertEqual(result["by_modality"]["PT"]["excess_instances"], 1)

    def test_mr_series_count_match_does_not_hide_instance_shortage(self):
        uid = "synthetic-mr-series"
        result = compare_series_instances_by_modality(
            [{"SeriesInstanceUID": uid, "instanceCount": 10, "Modality": "MR"}],
            {
                "unique_sop_count_by_series": {uid: 9},
                "series_file_count_by_series": {uid: 9},
                "header_modalities_by_series": {uid: ["MR"]},
                "modality_header_missing_or_invalid_file_count_by_series": {},
            },
            mapping_verified=True,
        )
        mr = result["by_modality"]["MR"]
        self.assertEqual(mr["expected_series"], 1)
        self.assertEqual(mr["local_matched_series"], 1)
        self.assertEqual(mr["partial_shortage_series"], 1)
        self.assertEqual(mr["shortage_instances"], 1)
        self.assertTrue(result["all_modalities_explained"])

    def test_header_modality_conflict_and_mixed_series_are_flagged(self):
        uid = "synthetic-mr-conflict"
        result = compare_series_instances_by_modality(
            [{"SeriesInstanceUID": uid, "instanceCount": 3, "Modality": "MR"}],
            {
                "unique_sop_count_by_series": {uid: 2},
                "series_file_count_by_series": {uid: 2},
                "header_modalities_by_series": {uid: ["MR", "CT"]},
                "modality_header_missing_or_invalid_file_count_by_series": {},
            },
            mapping_verified=True,
        )
        self.assertEqual(result["by_modality"]["MR"]["header_modality_conflict_series"], 1)
        self.assertEqual(result["by_modality"]["MR"]["mixed_header_modality_series"], 1)
        self.assertEqual(result["unknown_invalid_summary"]["official_vs_header_modality_conflict_series"], 1)
        self.assertEqual(result["unknown_invalid_summary"]["mixed_header_modality_series"], 1)
        self.assertFalse(result["all_modalities_explained"])
        public = json.dumps(result)
        self.assertNotIn(uid, public)

    def test_missing_or_invalid_local_modality_blocks_explained_gate(self):
        uid = "synthetic-mr-missing-modality"
        result = compare_series_instances_by_modality(
            [{"SeriesInstanceUID": uid, "instanceCount": 1, "Modality": "MR"}],
            {
                "unique_sop_count_by_series": {uid: 1},
                "series_file_count_by_series": {uid: 1},
                "header_modalities_by_series": {},
                "modality_header_missing_or_invalid_file_count_by_series": {uid: 1},
                "modality_header_missing_or_invalid_file_count": 1,
            },
            mapping_verified=True,
        )
        self.assertEqual(result["unknown_invalid_summary"]["local_series_with_missing_or_invalid_header_modality"], 1)
        self.assertEqual(result["by_modality"]["MR"]["header_modality_missing_or_invalid_series"], 1)
        self.assertFalse(result["all_modalities_explained"])

    def test_private_gap_path_rejects_outside_and_reparse_locations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo_root = root / "repo"
            local_root = repo_root / ".local"
            local_root.mkdir(parents=True)
            synthetic_script = repo_root / "scripts" / "r0" / "audit.py"
            synthetic_script.parent.mkdir(parents=True)
            synthetic_script.write_text("# synthetic only\n", encoding="utf-8")
            allowed = local_root / "gap.json"
            outside = repo_root / "gap.json"
            with patch("audit_tcia_v25_integrity.__file__", str(synthetic_script)):
                self.assertEqual(validate_private_gap_path(allowed), allowed)
                private_value = {"records": [{"SeriesInstanceUID": "synthetic-only"}]}
                write_private_gap_list(allowed, private_value)
                self.assertEqual(json.loads(allowed.read_text(encoding="utf-8")), private_value)
                with self.assertRaises(AuditBlocked):
                    validate_private_gap_path(outside)
                with patch(
                    "audit_tcia_v25_integrity._path_has_reparse_component",
                    side_effect=lambda candidate: Path(candidate) == local_root,
                ):
                    with self.assertRaises(AuditBlocked):
                        validate_private_gap_path(allowed)

    def test_public_private_gap_summary_never_contains_private_values(self):
        private_value = {
            "record_count": 1,
            "records": [{
                "SeriesInstanceUID": "synthetic-private-uid",
                "series_source_prefix": "synthetic-private-prefix",
            }],
        }
        public = public_private_gap_summary(private_value, "PRIVATE_GAP_LIST_CREATED")
        serialized = json.dumps(public)
        self.assertTrue(public["created"])
        self.assertEqual(public["record_count"], 1)
        self.assertNotIn("synthetic-private-uid", serialized)
        self.assertNotIn("synthetic-private-prefix", serialized)

    def test_plan_r2_refuses_any_public_s3_request(self):
        with self.assertRaisesRegex(AuditBlocked, "NETWORK_REQUESTS_PROHIBITED_BY_PLAN_R2"):
            run_audit(Namespace(list_public_s3=True))

    def test_list_page_parses_pagination_without_publishing_keys(self):
        body = (
            b"<ListBucketResult><Contents><Key>prefix-a%2Fobj-1.dcm</Key><Size>17</Size></Contents>"
            b"<IsTruncated>true</IsTruncated><NextContinuationToken>next%2Btoken</NextContinuationToken></ListBucketResult>"
        )
        objects, truncated, token = parse_s3_list_page(body)
        self.assertEqual(objects, [("prefix-a/obj-1.dcm", 17)])
        self.assertTrue(truncated)
        self.assertEqual(token, "next+token")

    def test_object_inventory_compares_name_and_size_without_bitwise_claim(self):
        prefix = "synthetic-prefix"
        uid = "1.2.synthetic.1"
        local = {"basename_sizes_by_series": {uid: {"image.dcm": [100], "extra.dcm": [20]}}}
        result = compare_object_inventory(
            {prefix: uid},
            {prefix: {f"{prefix}/image.dcm": 101, f"{prefix}/remote-only.dcm": 5}},
            local,
            all_prefixes_listed=True,
        )
        self.assertEqual(result["status"], "OBJECT_INVENTORY_DIFF_FOUND")
        self.assertEqual(result["remote_objects_missing_locally_count"], 1)
        self.assertEqual(result["local_objects_absent_remotely_count"], 1)
        self.assertEqual(result["object_size_mismatch_count"], 1)
        self.assertEqual(result["bitwise_integrity_status"], "NOT_VERIFIED_NO_CONTENT_HASHES")

    def test_global_object_name_match_and_ambiguity(self):
        matched = compare_global_object_names(
            {"prefix": {"prefix/a.dcm": 10, "prefix/b.dcm": 20}},
            {"a.dcm": [10], "b.dcm": [20]},
            all_prefixes_listed=True,
        )
        self.assertEqual(matched["status"], "OBJECT_INVENTORY_AND_SIZE_MATCHED")
        self.assertEqual(matched["object_name_mapping_status"], "UNIQUE_BASENAMES_VERIFIED")
        self.assertEqual(matched["matched_object_name_count"], 2)

        ambiguous = compare_global_object_names(
            {"p1": {"p1/a.dcm": 10}, "p2": {"p2/a.dcm": 10}},
            {"a.dcm": [10]},
            all_prefixes_listed=True,
        )
        self.assertEqual(ambiguous["status"], "OBJECT_INVENTORY_NOT_VERIFIED")
        self.assertEqual(ambiguous["remote_basename_collision_group_count"], 1)

        partial = compare_global_object_names({}, {"local-only.dcm": [10]}, all_prefixes_listed=False)
        self.assertEqual(partial["status"], "OBJECT_INVENTORY_NOT_VERIFIED")
        self.assertIsNone(partial["local_objects_absent_remotely_count"])
        self.assertEqual(partial["remote_object_count_in_listed_scope"], 0)

    def test_global_object_profile_contains_no_identifiers(self):
        result = compare_global_object_names(
            {"private-prefix": {"private-prefix/private-object.dcm": 7}},
            {"private-object.dcm": [7]},
            all_prefixes_listed=True,
        )
        serialized = json.dumps(result)
        self.assertNotIn("private-prefix", serialized)
        self.assertNotIn("private-object.dcm", serialized)

    def test_public_list_summary_drops_private_object_keys(self):
        private = {
            "status": "REMOTE_LIST_COMPLETE",
            "_objects_by_prefix": {"private-prefix": {"private-prefix/private-key.dcm": 1}},
        }
        public = json.dumps(_public_list_summary(private))
        self.assertNotIn("private-prefix", public)
        self.assertNotIn("private-key.dcm", public)

    def test_anonymous_list_paginates_and_refusal_is_sanitized(self):
        first = b"<ListBucketResult><Contents><Key>synthetic%2Fone.dcm</Key><Size>1</Size></Contents><IsTruncated>true</IsTruncated><NextContinuationToken>t1</NextContinuationToken></ListBucketResult>"
        second = b"<ListBucketResult><Contents><Key>synthetic%2Ftwo.dcm</Key><Size>2</Size></Contents><IsTruncated>false</IsTruncated></ListBucketResult>"
        with patch("audit_tcia_v25_integrity.urllib.request.urlopen", side_effect=[_FakeResponse(first), _FakeResponse(second)]):
            result = list_public_objects(["synthetic"], max_requests=2, max_response_bytes=10000)
        self.assertTrue(result["complete"])
        self.assertEqual(result["list_request_count"], 2)
        self.assertEqual(len(result["_objects_by_prefix"]["synthetic"]), 2)

        refusal = HTTPError("https://idc-open-data.s3.amazonaws.com/secret", 403, "denied", {}, None)
        with patch("audit_tcia_v25_integrity.urllib.request.urlopen", side_effect=refusal):
            blocked = list_public_objects(["synthetic"], max_requests=2)
        refusal.close()
        public = json.dumps(_public_list_summary(blocked))
        self.assertEqual(blocked["status"], "REMOTE_LIST_UNAVAILABLE")
        self.assertEqual(blocked["http_status"], 403)
        self.assertNotIn("secret", public)

    def test_mapping_summary_never_serializes_synthetic_identifiers(self):
        uid = "1.2.840.patientless.synthetic"
        prefix = "crdc-private-prefix-sentinel"
        summary, _forward, _reverse = map_series_prefixes(
            {prefix}, [{"SeriesInstanceUID": uid, "series_aws_url": f"s3://idc-open-data/{prefix}/"}]
        )
        serialized = json.dumps(summary)
        self.assertNotIn(uid, serialized)
        self.assertNotIn(prefix, serialized)


if __name__ == "__main__":
    unittest.main()
