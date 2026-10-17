from __future__ import annotations

import collections
import tempfile
import time
import unittest
from pathlib import Path

from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.sequence import Sequence
from pydicom.tag import Tag
from pydicom.uid import ExplicitVRLittleEndian, RTStructureSetStorage, generate_uid

from scripts.r0 import audit_tcia_manual_dicom as audit


def _roi(number: int = 1, name: str = "synthetic") -> Dataset:
    item = Dataset()
    item.ROINumber = number
    item.ROIName = name
    return item


def _observation(
    number: int = 1, reference: int = 1, interpreted_type: str | None = "GTV"
) -> Dataset:
    item = Dataset()
    item.ObservationNumber = number
    item.ReferencedROINumber = reference
    if interpreted_type is not None:
        item.add_new(Tag("300600A4"), "CS", interpreted_type)
    return item


def _contour(
    *,
    geometric_type: str | None = "CLOSED_PLANAR",
    point_count: int | None = 3,
    data: tuple[str, ...] | None = ("0", "0", "0", "1", "0", "0", "0", "1", "0"),
) -> Dataset:
    item = Dataset()
    if geometric_type is not None:
        item.ContourGeometricType = geometric_type
    if point_count is not None:
        item.NumberOfContourPoints = point_count
    if data is not None:
        item.ContourData = list(data)
    return item


def _rtstruct(
    *,
    rois: list[Dataset] | None = None,
    observations: list[Dataset] | None = None,
    roi_contours: list[Dataset] | None = None,
    include_observations: bool = True,
) -> Dataset:
    dataset = Dataset()
    dataset.StructureSetROISequence = Sequence(rois or [])
    if include_observations:
        dataset.RTROIObservationsSequence = Sequence(observations or [])
    dataset.ROIContourSequence = Sequence(roi_contours or [])
    return dataset


class RTStructSummaryTests(unittest.TestCase):
    def test_observation_sequence_type_is_linked_by_referenced_roi_number(self) -> None:
        dataset = _rtstruct(
            rois=[_roi(1, "synthetic target")],
            observations=[_observation(1, 1, "GTV")],
        )

        summary = audit._summarize_rtstruct_dataset(dataset)

        self.assertFalse(
            hasattr(dataset.StructureSetROISequence[0], "RTROIInterpretedType")
        )
        self.assertEqual(summary["counts"]["interpreted_type_category_counts"]["GTV"], 1)
        self.assertEqual(summary["counts"]["roi_type_mapping_status_counts"]["GTV"], 1)
        self.assertEqual(
            summary["counts"]["roi_name_type_comparison_counts"][
                "NAME_HEURISTIC_UNRESOLVED"
            ],
            1,
        )

    def test_zero_roi_identifiers_remain_linkable_integer_keys(self) -> None:
        dataset = _rtstruct(
            rois=[_roi(0)], observations=[_observation(0, 0, "GTV")]
        )

        summary = audit._summarize_rtstruct_dataset(dataset)

        self.assertEqual(summary["counts"]["roi_number_status_counts"]["PRESENT"], 1)
        self.assertEqual(
            summary["counts"]["roi_observation_reference_status_counts"][
                "UNIQUE_REFERENCE"
            ],
            1,
        )
        self.assertEqual(summary["counts"]["roi_type_mapping_status_counts"]["GTV"], 1)

    def test_missing_observation_sequence_is_not_reported_as_missing_type_value(self) -> None:
        dataset = _rtstruct(rois=[_roi()], include_observations=False)

        summary = audit._summarize_rtstruct_dataset(dataset)

        self.assertEqual(
            summary["sequence_state_counts"]["RTROIObservationsSequence"]["MISSING"],
            1,
        )
        self.assertEqual(
            summary["counts"]["roi_observation_interpreted_type_presence_counts"], {}
        )
        self.assertEqual(
            summary["counts"]["roi_type_mapping_status_counts"]["NO_OBSERVATION"],
            1,
        )

    def test_empty_interpreted_type_is_distinct_from_missing(self) -> None:
        dataset = _rtstruct(rois=[_roi()], observations=[_observation(interpreted_type="")])

        summary = audit._summarize_rtstruct_dataset(dataset)

        self.assertEqual(
            summary["counts"]["roi_observation_interpreted_type_presence_counts"][
                "EMPTY"
            ],
            1,
        )
        self.assertEqual(
            summary["counts"]["roi_type_mapping_status_counts"]["TYPE_EMPTY"], 1
        )

    def test_missing_interpreted_type_element_is_counted_separately(self) -> None:
        dataset = _rtstruct(rois=[_roi()], observations=[_observation(interpreted_type=None)])

        summary = audit._summarize_rtstruct_dataset(dataset)

        self.assertEqual(
            summary["counts"]["roi_observation_interpreted_type_presence_counts"][
                "MISSING"
            ],
            1,
        )
        self.assertEqual(
            summary["counts"]["roi_type_mapping_status_counts"]["TYPE_MISSING"], 1
        )
    def test_unmatched_observation_reference_is_orphaned(self) -> None:
        dataset = _rtstruct(rois=[_roi(1)], observations=[_observation(reference=2)])

        summary = audit._summarize_rtstruct_dataset(dataset)

        self.assertEqual(
            summary["counts"]["roi_observation_reference_status_counts"][
                "ORPHAN_REFERENCE"
            ],
            1,
        )
        self.assertEqual(
            summary["counts"]["roi_type_mapping_status_counts"]["NO_OBSERVATION"], 1
        )

    def test_multiple_observations_preserve_conflict_without_forcing_type(self) -> None:
        dataset = _rtstruct(
            rois=[_roi()],
            observations=[
                _observation(1, 1, "GTV"),
                _observation(2, 1, "OAR"),
            ],
        )

        summary = audit._summarize_rtstruct_dataset(dataset)

        self.assertEqual(
            summary["scalars"]["unique_roi_numbers_with_multiple_observations_count"],
            1,
        )
        self.assertEqual(
            summary["scalars"]["roi_numbers_with_conflicting_observation_types_count"],
            1,
        )
        self.assertEqual(
            summary["counts"]["roi_type_mapping_status_counts"][
                "MULTIPLE_OBSERVATIONS_UNRESOLVED"
            ],
            1,
        )

    def test_missing_and_empty_contour_sequence_are_distinct(self) -> None:
        missing = Dataset()
        missing.ReferencedROINumber = 1
        empty = Dataset()
        empty.ReferencedROINumber = 2
        empty.ContourSequence = Sequence([])
        dataset = _rtstruct(rois=[_roi(1), _roi(2)], roi_contours=[missing, empty])

        summary = audit._summarize_rtstruct_dataset(dataset)

        self.assertEqual(summary["counts"]["contour_sequence_state_counts"]["MISSING"], 1)
        self.assertEqual(summary["counts"]["contour_sequence_state_counts"]["EMPTY"], 1)
        self.assertEqual(summary["scalars"]["contour_item_count"], 0)

    def test_contour_data_length_mismatch_is_counted_without_retaining_coordinates(self) -> None:
        roi_contour = Dataset()
        roi_contour.ReferencedROINumber = 1
        roi_contour.ContourSequence = Sequence([_contour(point_count=4)])
        dataset = _rtstruct(rois=[_roi()], roi_contours=[roi_contour])

        summary = audit._summarize_rtstruct_dataset(dataset)

        self.assertEqual(
            summary["counts"]["contour_data_check_counts"]["LENGTH_MISMATCH"], 1
        )
        self.assertNotIn("ContourData", str(summary))

    def test_empty_contour_data_is_separate_from_missing_data(self) -> None:
        contour = _contour(geometric_type="POINT", point_count=1, data=None)
        contour.add_new(Tag("30060050"), "DS", "")
        roi_contour = Dataset()
        roi_contour.ReferencedROINumber = 1
        roi_contour.ContourSequence = Sequence([contour])
        dataset = _rtstruct(rois=[_roi()], roi_contours=[roi_contour])

        summary = audit._summarize_rtstruct_dataset(dataset)

        self.assertEqual(
            summary["counts"]["contour_data_check_counts"]["DATA_EMPTY"], 1
        )

    def test_duplicate_contour_roi_entries_are_reported_as_many_to_one(self) -> None:
        first = Dataset()
        first.ReferencedROINumber = 1
        first.ContourSequence = Sequence([])
        second = Dataset()
        second.ReferencedROINumber = 1
        second.ContourSequence = Sequence([])
        dataset = _rtstruct(rois=[_roi()], roi_contours=[first, second])

        summary = audit._summarize_rtstruct_dataset(dataset)

        self.assertEqual(summary["scalars"]["roi_contour_duplicate_reference_value_count"], 1)
        self.assertEqual(
            summary["scalars"]["roi_contour_entries_with_duplicate_reference_count"], 2
        )

    def test_deep_parser_reads_observation_sequence_from_serialized_dicom(self) -> None:
        dataset = FileDataset(None, {}, file_meta=FileMetaDataset(), preamble=b"\0" * 128)
        dataset.file_meta.MediaStorageSOPClassUID = RTStructureSetStorage
        dataset.file_meta.MediaStorageSOPInstanceUID = generate_uid()
        dataset.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
        dataset.SOPClassUID = RTStructureSetStorage
        dataset.SOPInstanceUID = dataset.file_meta.MediaStorageSOPInstanceUID
        dataset.Modality = "RTSTRUCT"
        dataset.StructureSetROISequence = Sequence([_roi()])
        dataset.RTROIObservationsSequence = Sequence([_observation(1, 1, "GTV")])
        dataset.ROIContourSequence = Sequence([])

        repo_root = Path(__file__).resolve().parents[1]
        scratch = repo_root / ".local"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="cmrl04-rtstruct-test-", dir=scratch) as temp:
            path = Path(temp) / "synthetic.dcm"
            dataset.save_as(path, enforce_file_format=True)
            counters = {
                "time_limit_reached": False,
                "oversize_file_skipped": 0,
                "deep_parse_error_classes": collections.Counter(),
                "deep_parse_success": 0,
                "rtstruct_summary": audit._empty_rtstruct_summary(),
                "files_without_frame_reference": 0,
                "files_without_series_reference": 0,
                "files_without_sop_reference": 0,
            }
            result = audit._deep_parse_rtstruct(
                {
                    "_path": str(path),
                    "_size": path.stat().st_size,
                    "_forced": False,
                    "_patient": "synthetic",
                    "_study": "synthetic",
                    "_series": "synthetic",
                    "_sop": "synthetic",
                    "_frame": "synthetic",
                },
                counters,
                time.monotonic() + 30,
            )

        self.assertIsNotNone(result)
        self.assertEqual(counters["deep_parse_success"], 1)
        self.assertEqual(
            counters["rtstruct_summary"]["counts"]["roi_type_mapping_status_counts"][
                "GTV"
            ],
            1,
        )


if __name__ == "__main__":
    unittest.main()
