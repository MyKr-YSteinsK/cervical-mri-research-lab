from __future__ import annotations
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"scripts"/"r0"/"audit_tcia_private_crosswalk_screen.py"
spec=importlib.util.spec_from_file_location("cmrl08_audit",SCRIPT)
audit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

class SyntheticCrosswalkScreenTests(unittest.TestCase):
    def test_anonymous_single_cell_rows_are_layout_only(self):
        specs=[
            {"row":2,"keyed":True,"nonempty_count":6,"column":1,"kind":"text","style":1,"key_style":1},
            {"row":3,"keyed":True,"nonempty_count":6,"column":1,"kind":"text","style":1,"key_style":1},
        ]
        specs.extend({"row":r,"keyed":False,"nonempty_count":1,"column":5,"kind":"text",
                      "style":9,"key_style":None,"formula":False,"comment":False,"merged":False,"marker":False}
                     for r in range(4,9))
        p=audit.summarize_singleton_specs(specs,1)
        self.assertEqual(p["unkeyed_single_cell_rows"],5)
        self.assertEqual(p["single_cell_types"],{"text":5})
        self.assertTrue(p["same_nonkey_column_category"])
        self.assertTrue(p["contiguous_tail_block"])
        self.assertTrue(p["distinct_style_from_keyed_rows"])
        self.assertEqual(p["explicit_marker_count"],0)
        self.assertNotIn("role_semantics",p)

    def test_exact_join_and_equal_counts_do_not_prove_identity(self):
        r=audit.exact_join(["C-A","C-B"],["C-A","D-C"])
        self.assertEqual((r["clinical_key_count"],r["dicom_id_count"]),(2,2))
        self.assertEqual(len(r["matched_keys"]),1)
        self.assertEqual(len(r["unmatched_keys"]),1)
        dup=audit.exact_join(["C-X","C-X"],["C-X"])
        self.assertEqual(len(dup["ambiguous_keys"]),1)
        typed=audit.exact_join([123],["123"])
        self.assertEqual(typed["clinical_nonstring_count"],1)
        self.assertEqual(typed["matched_keys"],[])

    def test_count_equal_and_short_are_distinct(self):
        self.assertEqual(audit.count_relation(12,12),"COUNT_EQUAL")
        self.assertEqual(audit.count_relation(12,11),"COUNT_SHORT")
        self.assertEqual(audit.count_relation(12,13),"COUNT_EXCESS")

    def test_reference_resolution_and_candidate_gate(self):
        index={"1.2.3":[object()],"1.2.4":[object(),object()]}
        ok=audit.resolve_direct_references(["1.2.3"],index)
        self.assertTrue(ok["complete"])
        missing=audit.resolve_direct_references(["1.2.9"],index)
        self.assertFalse(missing["complete"])
        multiple=audit.resolve_direct_references(["1.2.4"],index)
        self.assertEqual(len(multiple["ambiguous"]),1)
        good=audit.candidate_pair_gate(10,10,1,1,True,True,True)
        self.assertTrue(good["eligible"])
        for args in ((10,9,1,1,True,True,True),(10,10,1,1,False,True,True),
                     (10,10,1,1,True,False,True),(10,10,1,1,True,True,False)):
            self.assertFalse(audit.candidate_pair_gate(*args)["eligible"])
        no_pair=audit.candidate_pair_gate(10,9,1,1,True,True,True)
        self.assertEqual(no_pair["reason"],"MR_COUNT_NOT_EQUAL")

    def test_chronology_is_not_treatment_timepoint(self):
        s={
          "S1":{"patients":{"P"},"studies":{"ST1"},"study_dates":{"20200101"},"study_times":{"090000"},
                "series_dates":set(),"series_times":set(),"acq_dates":set(),"acq_times":set()},
          "S2":{"patients":{"P"},"studies":{"ST2"},"study_dates":{"20210101"},"study_times":{"090000"},
                "series_dates":set(),"series_times":set(),"acq_dates":set(),"acq_times":set()},
        }
        ranks=audit.chronology_ranks(s)
        self.assertEqual(ranks[("P","ST1")],1)
        self.assertEqual(ranks[("P","ST2")],2)
        self.assertNotIn("treatment_timepoint",ranks)

    def test_t2_text_is_heuristic_only(self):
        self.assertTrue(audit._text_t2({"descriptions":{"sag T2W"},"protocols":set(),"sequence_names":set()}))
        self.assertFalse(audit._text_t2({"descriptions":{"sag T1"},"protocols":set(),"sequence_names":set()}))

    def test_public_serialization_rejects_private_values(self):
        public={"task_id":"CMRL-08","aggregate":True}
        self.assertEqual(audit.private_value_hits(public,{"SYNTHETIC-PATIENT-ABC","1.2.840.113619.2","C:/private/image.dcm"}),[])
        public["unexpected"]="SYNTHETIC-PATIENT-ABC"
        self.assertEqual(len(audit.private_value_hits(public,{"SYNTHETIC-PATIENT-ABC"})),1)

    def test_private_paths_are_git_ignored(self):
        check=subprocess.run(["git","check-ignore","--quiet","--",".local/cmrl-08/private_patient_join.json"],
                             cwd=ROOT,check=False)
        self.assertEqual(check.returncode,0)

    def test_rtstruct_parser_skips_contour_values_and_roi_names(self):
        if audit.PARSER_CACHE not in sys.path:
            sys.path.insert(0,audit.PARSER_CACHE)
        import pydicom
        from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
        from pydicom.sequence import Sequence
        from pydicom.uid import ExplicitVRLittleEndian, RTStructureSetStorage, generate_uid
        sop_uid=generate_uid(); series_uid=generate_uid(); study_uid=generate_uid(); frame_uid=generate_uid()
        meta=FileMetaDataset()
        meta.MediaStorageSOPClassUID=RTStructureSetStorage
        meta.MediaStorageSOPInstanceUID=generate_uid()
        meta.TransferSyntaxUID=ExplicitVRLittleEndian
        meta.ImplementationClassUID=generate_uid()
        ds=FileDataset(None,{},file_meta=meta,preamble=b"\0"*128)
        ds.SOPClassUID=RTStructureSetStorage; ds.SOPInstanceUID=meta.MediaStorageSOPInstanceUID
        ds.Modality="RTSTRUCT"; ds.PatientID="SYNTHETIC-PATIENT-ABC"
        frame=Dataset(); frame.ReferencedFrameOfReferenceUID=frame_uid
        study=Dataset(); study.ReferencedSOPClassUID=generate_uid(); study.ReferencedSOPInstanceUID=study_uid
        series=Dataset(); series.SeriesInstanceUID=series_uid
        image=Dataset(); image.ReferencedSOPClassUID=generate_uid(); image.ReferencedSOPInstanceUID=sop_uid
        series.ContourImageSequence=Sequence([image])
        study.RTReferencedSeriesSequence=Sequence([series])
        frame.RTReferencedStudySequence=Sequence([study])
        ds.ReferencedFrameOfReferenceSequence=Sequence([frame])
        roi_def=Dataset(); roi_def.ROINumber=1; roi_def.ROIName="Tumor"
        roi_def.ReferencedFrameOfReferenceUID=frame_uid
        ds.StructureSetROISequence=Sequence([roi_def])
        contour=Dataset(); contour.ContourImageSequence=Sequence([image])
        contour.ContourData=[1.0,2.0,3.0,4.0,5.0,6.0,7.0,8.0,9.0]
        roi=Dataset(); roi.ReferencedROINumber=1; roi.ContourSequence=Sequence([contour])
        ds.ROIContourSequence=Sequence([roi])
        with tempfile.TemporaryDirectory(dir=ROOT/".local"/"cmrl-08") as td:
            path=Path(td)/"synthetic_rtstruct.dcm"
            ds.save_as(path,enforce_file_format=True)
            result=audit.parse_rtstruct_references(path)
        self.assertEqual(result["sop_refs"],[sop_uid])
        self.assertEqual(len(result["series_contexts"]),1)
        self.assertEqual(result["series_contexts"][0]["series"],series_uid)
        self.assertGreater(result["coordinate_value_bytes_skipped"],0)
        self.assertEqual(result["coordinate_value_bytes_read"],0)
        self.assertNotIn("roi_names",result)
        self.assertNotIn("Tumor",str(result))

if __name__=="__main__":
    unittest.main()
