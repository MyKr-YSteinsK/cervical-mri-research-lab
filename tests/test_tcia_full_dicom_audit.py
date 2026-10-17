from __future__ import annotations

from contextlib import contextmanager
import tempfile
import unittest
from pathlib import Path

from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, MRImageStorage, generate_uid

from scripts.r0 import audit_tcia_full_dicom as full
from scripts.r0 import audit_tcia_manual_dicom as manual


class ManifestTests(unittest.TestCase):
    def test_valid_manifest_counts_prefixes_without_exposing_values(self) -> None:
        lines = ["# IDC Data Release Version 25.0 2026-10-01"]
        lines.extend(f"cp s3://idc-open-data/group/series-{i}/* ." for i in range(821))
        parsed = full.parse_manifest_bytes(("\n".join(lines) + "\n").encode())

        self.assertEqual(parsed["structure_status"], "MANIFEST_STRUCTURE_VERIFIED")
        self.assertEqual(parsed["command_count"], 821)
        self.assertEqual(parsed["unique_source_prefix_count"], 821)
        public = full.public_manifest_summary(parsed)
        self.assertNotIn("_source_prefixes", public)
        self.assertNotIn("group/series-0", str(public))

    def test_duplicate_source_prefix_is_reported(self) -> None:
        text = "\n".join(
            ["# IDC Data Release Version 25.0"]
            + ["cp s3://idc-open-data/same/* ."] * 821
        )
        parsed = full.parse_manifest_bytes(text.encode())

        self.assertEqual(parsed["command_count"], 821)
        self.assertEqual(parsed["unique_source_prefix_count"], 1)
        self.assertEqual(parsed["duplicate_prefix_command_count"], 820)
        self.assertEqual(parsed["structure_status"], "MANIFEST_STRUCTURE_INVALID")

    def test_unrecognized_shell_command_invalidates_structure(self) -> None:
        lines = ["# IDC Data Release Version 25.0"]
        lines.extend(f"cp s3://idc-open-data/group/series-{i}/* ." for i in range(820))
        lines.append("Remove-Item -Recurse data")
        parsed = full.parse_manifest_bytes(("\n".join(lines) + "\n").encode())

        self.assertEqual(parsed["malformed_noncomment_line_count"], 1)
        self.assertEqual(parsed["structure_status"], "MANIFEST_STRUCTURE_INVALID")

    def test_invalid_encoding_is_aggregate_only(self) -> None:
        parsed = full.parse_manifest_bytes(b"\xff\xfe\x00")

        self.assertEqual(parsed["encoding_status"], "INVALID")
        self.assertEqual(parsed["structure_status"], "MANIFEST_STRUCTURE_INVALID")
        self.assertNotIn("_source_prefixes", full.public_manifest_summary(parsed))


class CoverageTests(unittest.TestCase):
    def test_no_trusted_mapping_never_claims_series_coverage(self) -> None:
        result = full.assess_series_coverage({"p1", "p2"}, None, {})

        self.assertEqual(result["status"], "SERIES_COVERAGE_NOT_VERIFIED")
        self.assertFalse(result["mapping_source_verified"])

    def test_verified_mapping_requires_each_local_series_nonempty(self) -> None:
        result = full.assess_series_coverage(
            {"p1", "p2"},
            {"p1": "synthetic-a", "p2": "synthetic-b"},
            {"synthetic-a": 2, "synthetic-b": 1},
        )

        self.assertEqual(result["status"], "SERIES_COVERAGE_VERIFIED")
        self.assertEqual(result["mapped_prefix_count"], 2)

    def test_missing_local_series_is_a_coverage_gap(self) -> None:
        result = full.assess_series_coverage(
            {"p1", "p2"},
            {"p1": "synthetic-a", "p2": "synthetic-b"},
            {"synthetic-a": 2},
        )

        self.assertEqual(result["status"], "SERIES_COVERAGE_GAPS_FOUND")
        self.assertEqual(result["mapped_series_missing_or_empty_count"], 1)

    def test_ambiguous_mapping_does_not_verify_coverage(self) -> None:
        result = full.assess_series_coverage(
            {"p1", "p2"},
            {"p1": "synthetic-a", "p2": "synthetic-a"},
            {"synthetic-a": 2},
        )

        self.assertEqual(result["status"], "SERIES_COVERAGE_NOT_VERIFIED")
        self.assertEqual(result["ambiguous_mapping_count"], 1)

    def test_wildcard_manifest_without_object_list_is_not_complete_evidence(self) -> None:
        result = full.assess_object_completeness(
            None, (), authoritative_source_verified=False
        )

        self.assertEqual(result["status"], "OBJECT_LEVEL_COMPLETENESS_NOT_VERIFIED")
        self.assertIsNone(result["missing_object_count"])

    def test_authoritative_object_list_detects_missing_file(self) -> None:
        result = full.assess_object_completeness(
            {"object-a", "object-b", "object-c"},
            {"object-a", "object-b"},
            authoritative_source_verified=True,
        )

        self.assertEqual(result["status"], "OBJECT_LEVEL_COMPLETENESS_GAPS_FOUND")
        self.assertEqual(result["missing_object_count"], 1)


class ReferenceCooccurrenceTests(unittest.TestCase):
    def test_same_patient_and_study_without_any_direct_reference_are_separate(self) -> None:
        rt_items = [
            {
                "_patient": "synthetic-patient",
                "_study": "synthetic-study",
                "_sop_refs": set(),
                "_series_refs": set(),
                "_frame_refs": set(),
            }
        ]
        series_to_records = {
            "synthetic-series": [{"_sop": "synthetic-sop"}],
        }
        mr_series = {
            "synthetic-series": {
                "patients": {"synthetic-patient"},
                "studies": {"synthetic-study"},
                "frames": {"synthetic-frame"},
            }
        }

        result = full.summarize_cooccurrence_without_direct_reference(
            rt_items, series_to_records, mr_series
        )

        self.assertEqual(result["same_patient_key_without_direct_reference_pair_count"], 1)
        self.assertEqual(result["same_study_key_without_direct_reference_pair_count"], 1)

    def test_direct_sop_series_or_frame_reference_excludes_weak_cooccurrence(self) -> None:
        rt_items = [
            {
                "_patient": "synthetic-patient",
                "_study": "synthetic-study",
                "_sop_refs": {"synthetic-sop"},
                "_series_refs": set(),
                "_frame_refs": set(),
            },
            {
                "_patient": "synthetic-patient",
                "_study": "synthetic-study",
                "_sop_refs": set(),
                "_series_refs": {"synthetic-series"},
                "_frame_refs": set(),
            },
            {
                "_patient": "synthetic-patient",
                "_study": "synthetic-study",
                "_sop_refs": set(),
                "_series_refs": set(),
                "_frame_refs": {"synthetic-frame"},
            },
        ]
        series_to_records = {
            "synthetic-series": [{"_sop": "synthetic-sop"}],
        }
        mr_series = {
            "synthetic-series": {
                "patients": {"synthetic-patient"},
                "studies": {"synthetic-study"},
                "frames": {"synthetic-frame"},
            }
        }

        result = full.summarize_cooccurrence_without_direct_reference(
            rt_items, series_to_records, mr_series
        )

        self.assertEqual(result["same_patient_key_without_direct_reference_pair_count"], 0)
        self.assertEqual(result["same_study_key_without_direct_reference_pair_count"], 0)
        self.assertEqual(result["same_frame_key_without_direct_reference_pair_count"], 0)


class SyntheticDicomTests(unittest.TestCase):
    @contextmanager
    def _scratch(self):
        scratch_root = Path.cwd() / ".local" / "cmrl05-test-scratch"
        scratch_root.mkdir(parents=True, exist_ok=True)
        try:
            with tempfile.TemporaryDirectory(dir=scratch_root) as directory:
                yield Path(directory)
        finally:
            try:
                scratch_root.rmdir()
            except OSError:
                pass

    def test_serialized_synthetic_mr_header_stops_before_pixel_data(self) -> None:
        with self._scratch() as directory:
            path = directory / "synthetic.dcm"
            file_meta = FileMetaDataset()
            file_meta.MediaStorageSOPClassUID = MRImageStorage
            file_meta.MediaStorageSOPInstanceUID = generate_uid()
            file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
            file_meta.ImplementationClassUID = generate_uid()
            dataset = FileDataset(str(path), {}, file_meta=file_meta, preamble=b"\0" * 128)
            dataset.SOPClassUID = MRImageStorage
            dataset.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
            dataset.Modality = "MR"
            dataset.PatientID = "SYNTHETIC-ONLY"
            dataset.StudyInstanceUID = generate_uid()
            dataset.SeriesInstanceUID = generate_uid()
            dataset.FrameOfReferenceUID = generate_uid()
            dataset.SeriesDescription = "T2 synthetic"
            dataset.Rows = 2
            dataset.Columns = 2
            dataset.PixelSpacing = [1, 1]
            dataset.ImagePositionPatient = [0, 0, 0]
            dataset.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
            dataset.SliceThickness = 3
            dataset.SpacingBetweenSlices = 3
            dataset.PixelData = b"\0" * 8
            dataset.save_as(path, enforce_file_format=True)

            parsed = manual._parse_dataset(str(path), specific_tags=manual.BASE_TAGS)
            record = manual._build_record(str(path), path.stat().st_size, parsed, False)

            self.assertNotIn("PixelData", parsed)
            self.assertEqual(record["_modality"], "MR")
            self.assertTrue(record["_dimensions_present"])
            self.assertTrue(record["_position_finite"])

    def test_unreadable_or_missing_path_fails_without_path_echo(self) -> None:
        with self._scratch() as directory:
            missing = directory / "missing.dcm"
            with self.assertRaises(Exception) as context:
                manual._parse_dataset(str(missing), specific_tags=manual.BASE_TAGS)

            self.assertNotIn(str(missing), type(context.exception).__name__)


if __name__ == "__main__":
    unittest.main()
