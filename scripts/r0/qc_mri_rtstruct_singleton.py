#!/usr/bin/env python
"""Run bounded one-pair MR/RTSTRUCT QC inside an existing 3D Slicer Python runtime.
Environment: CMRL_SINGLETON_MANIFEST, CMRL_SINGLETON_OUTDIR.
All patient-level inputs and outputs stay under the ignored private output directory.
"""
import json, math, os, struct, sys, traceback, zlib
from pathlib import Path
import numpy as np
import pydicom
import slicer, vtk, ctk
from DICOMLib import DICOMUtils

POS_TOL = 0.1
ORIENT_TOL = 1e-4
PLANE_TOL = 0.5
MATRIX_TOL = 1e-5
MR_TAGS = ["PatientID","StudyInstanceUID","SeriesInstanceUID","SOPClassUID","SOPInstanceUID",
 "FrameOfReferenceUID","Modality","Rows","Columns","ImageOrientationPatient","ImagePositionPatient",
 "PixelSpacing","SliceThickness","SpacingBetweenSlices","InstanceNumber","BitsAllocated","BitsStored",
 "HighBit","PixelRepresentation","SamplesPerPixel","PhotometricInterpretation","RescaleSlope","RescaleIntercept"]

def v(ds, key, default=None):
    x = getattr(ds, key, default)
    if x is None: return default
    if isinstance(x, (str,int,float)): return x
    try: return [float(y) for y in x]
    except Exception: return str(x)

def uniq(xs):
    return sorted({str(x) for x in xs if x not in (None,"")})

def mtx(node):
    m = vtk.vtkMatrix4x4()
    node.GetIJKToRASMatrix(m)
    return np.asarray([[m.GetElement(r,c) for c in range(4)] for r in range(4)], dtype=float)

def save_json(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    def encode_extra(value):
        if isinstance(value,np.generic): return value.item()
        if isinstance(value,np.ndarray): return value.tolist()
        if isinstance(value,Path): return str(value)
        raise TypeError("not JSON serializable: "+type(value).__name__)
    Path(path).write_text(json.dumps(obj, ensure_ascii=True, indent=2, default=encode_extra), encoding="utf-8")

def write_progress(path, stage, detail=None):
    save_json(path, {"stage":stage,"detail":detail})

def png_chunk(kind, payload):
    return struct.pack(">I",len(payload))+kind+payload+struct.pack(">I",zlib.crc32(kind+payload)&0xffffffff)

def write_png(path, rgb):
    a=np.asarray(rgb,dtype=np.uint8); h,w,_=a.shape
    raw=b"".join(b"\x00"+a[y].tobytes() for y in range(h))
    data=b"\x89PNG\r\n\x1a\n"+png_chunk(b"IHDR",struct.pack(">2I5B",w,h,8,2,0,0,0))
    data+=png_chunk(b"IDAT",zlib.compress(raw,6))+png_chunk(b"IEND",b"")
    Path(path).write_bytes(data)

def edge(mask):
    b=np.asarray(mask,dtype=bool); p=np.pad(b,1)
    inner=b&p[:-2,1:-1]&p[2:,1:-1]&p[1:-1,:-2]&p[1:-1,2:]
    return b&~inner

def line(rgb, a, b, color=(30,255,60)):
    h,w,_=rgb.shape
    x0,y0=int(round(a[0])),int(round(a[1])); x1,y1=int(round(b[0])),int(round(b[1]))
    dx,sx=abs(x1-x0),(1 if x0<x1 else -1); dy,sy=-abs(y1-y0),(1 if y0<y1 else -1); err=dx+dy
    while True:
        if 0<=x0<w and 0<=y0<h: rgb[y0,x0]=color
        if x0==x1 and y0==y1: break
        e=2*err
        if e>=dy: err+=dy; x0+=sx
        if e<=dx: err+=dx; y0+=sy

def render(img, mask, contour_lines=()):
    finite=np.asarray(img)[np.isfinite(img)]
    lo=float(np.percentile(finite,1)) if finite.size else 0.
    hi=float(np.percentile(finite,99.5)) if finite.size else 1.
    if hi<=lo: hi=lo+1.
    gray=np.clip((np.asarray(img,dtype=float)-lo)*255/(hi-lo),0,255).astype(np.uint8)
    rgb=np.repeat(gray[:,:,None],3,axis=2); rgb[edge(mask)]=[255,30,210]
    for pts in contour_lines:
        for p0,p1 in zip(pts[:-1],pts[1:]): line(rgb,p0,p1)
        if len(pts)>2: line(rgb,pts[-1],pts[0])
    return rgb

def save_visuals(out_dir, image, mask, contours, ijk_to_ras, sop_to_k):
    folder=Path(out_dir)/"visuals"; folder.mkdir(parents=True,exist_ok=True)
    k=int(np.argmax(mask.sum(axis=(1,2)))); j=int(np.argmax(mask.sum(axis=(0,2)))); i=int(np.argmax(mask.sum(axis=(0,1))))
    ras_to_ijk=np.linalg.inv(ijk_to_ras); lps_to_ras=np.diag([-1.,-1.,1.,1.]); lines=[]
    for c in contours:
        ks=[sop_to_k[x] for x in c["refs"] if x in sop_to_k]
        if not ks or k not in ks or len(c["pts"])<2: continue
        pts=np.asarray(c["pts"],dtype=float)
        ras=(lps_to_ras@np.c_[pts,np.ones(len(pts))].T).T
        ijk=(ras_to_ijk@ras.T).T[:,:3]
        if np.max(np.abs(ijk[:,2]-k))<=0.5:
            lines.append([(float(p[0]),float(p[1])) for p in ijk])
    entries=[("native_k",image[k,:,:],mask[k,:,:],lines),("native_j",image[:,j,:],mask[:,j,:],[]),("native_i",image[:,:,i],mask[:,:,i],[])]
    files=[]
    for name,img2,mask2,contour_lines in entries:
        path=folder/(name+".png"); write_png(path,render(img2,mask2,contour_lines)); files.append(str(path))
    return {"files":files,"representative_indices_ijk":{"i":i,"j":j,"k":k},"views":"native IJK planes; direction matrix in private QC record"}

def save_source_contour_visual(out_dir, paths, sops, iops, ipps, pixel_spacings, rows, cols, contours, normal):
    if normal is None: return {"status":"UNAVAILABLE_NO_VALID_SLICE_NORMAL"}
    sop_index={s:i for i,s in enumerate(sops)}; lines_by_sop={}; pixels={}
    for i,path in enumerate(paths):
        ds=pydicom.dcmread(path); image=np.asarray(ds.pixel_array)
        if image.shape!=(rows,cols): raise RuntimeError("source DICOM pixel shape mismatch")
        pixels[sops[i]]=image
    for c in contours:
        pts=np.asarray(c["pts"],dtype=float)
        if len(pts)<2: continue
        for sop in c["refs"]:
            if sop not in sop_index: continue
            i=sop_index[sop]; delta=pts-ipps[i]
            col=(delta@iops[i][:3])/pixel_spacings[i][1]
            row=(delta@iops[i][3:])/pixel_spacings[i][0]
            lines_by_sop.setdefault(sop,[]).append([(float(x),float(y)) for x,y in zip(col,row)])
    if not lines_by_sop: return {"status":"UNAVAILABLE_NO_RESOLVED_CONTOUR_SLICE"}
    representative=max(lines_by_sop,key=lambda s:sum(len(x) for x in lines_by_sop[s]))
    image=pixels[representative]; blank=np.zeros(image.shape,dtype=bool)
    path=Path(out_dir)/"visuals"/"source_dicom_contours.png"
    write_png(path,render(image,blank,lines_by_sop[representative]))
    return {"status":"CREATED","file":str(path),"source_slice_index":int(sop_index[representative]),
        "contour_count":len(lines_by_sop[representative]),"point_count":sum(len(x) for x in lines_by_sop[representative]),
        "coordinate_basis":"exact referenced DICOM slice IPP, IOP, and PixelSpacing"}

def find_patient_regs(db, study_uid, mr_series_uid, rt_series_uid):
    info={"database_open":bool(getattr(db,"isOpen",False)),"reg_status":"NOT_RUN","reg_objects":[]}
    if not info["database_open"]: info["reg_status"]="UNAVAILABLE_DATABASE_CLOSED"; return info
    try:
        info["database_directory"]=str(db.databaseDirectory)
        info["database_patient_count"]=int(db.patientsCount())
        info["database_series_count"]=int(db.seriesCount())
        info["selected_mr_series_present"]=bool(db.filesForSeries(mr_series_uid))
        info["selected_rt_series_present"]=bool(db.filesForSeries(rt_series_uid))
        patient_uid=db.patientForStudy(study_uid)
        studies=db.studiesForPatient(patient_uid) if patient_uid else []
        regs=[]
        for study in studies:
            for series in db.seriesForStudy(study):
                files=db.filesForSeries(series)
                if files and str(db.fileValue(files[0],"0008,0060"))=="REG":
                    regs.extend(str(x) for x in files)
        for path in regs:
            ds=pydicom.dcmread(path,stop_before_pixels=True)
            info["reg_objects"].append({
                "file_path":path,"sop_instance_uid":str(getattr(ds,"SOPInstanceUID","")),
                "study_instance_uid":str(getattr(ds,"StudyInstanceUID","")),
                "series_instance_uid":str(getattr(ds,"SeriesInstanceUID","")),
                "frame_of_reference_uid":str(getattr(ds,"FrameOfReferenceUID","")),
                "registration_frame_uids":uniq([getattr(x,"FrameOfReferenceUID","") for x in getattr(ds,"RegistrationSequence",[])]),
                "registration_sequence_count":len(getattr(ds,"RegistrationSequence",[])),
                "deformable_registration_sequence_count":len(getattr(ds,"DeformableRegistrationSequence",[])),
            })
        info["reg_status"]="REG_FOUND_NOT_APPLIED" if regs else "NO_REG_FOUND_IN_EXISTING_INDEX"
        return info
    except Exception as exc:
        info["reg_status"]="UNAVAILABLE"; info["error_type"]=type(exc).__name__; return info

def main():
    manifest=os.environ.get("CMRL_SINGLETON_MANIFEST","")
    out_dir=os.environ.get("CMRL_SINGLETON_OUTDIR","")
    if not manifest or not out_dir: raise RuntimeError("task-specific environment variables missing")
    out_dir=str(Path(out_dir).resolve()); Path(out_dir,"private").mkdir(parents=True,exist_ok=True); Path(out_dir,"visuals").mkdir(parents=True,exist_ok=True)
    output=Path(out_dir,"private","quality_qc.json")
    progress_path=Path(out_dir,"private","progress.json")
    result={"tool":"qc_mri_rtstruct_singleton.py",
      "software":{"slicer":str(slicer.app.applicationVersion),"slicer_python":sys.version.split()[0],"pydicom":str(pydicom.__version__)},
      "criteria":{"position_duplicate_tolerance_mm":POS_TOL,"orientation_component_tolerance":ORIENT_TOL,
       "contour_plane_tolerance_mm":PLANE_TOL,"center_spacing_tolerance":"max(0.1 mm, 1% median measured center spacing)",
       "center_spacing_source":"ImagePositionPatient projected on slice normal","slice_thickness_is_not_center_spacing":True,
       "mask_matrix_tolerance":MATRIX_TOL},
      "status":{"PIXEL_QC":"NOT_RUN","GEOMETRY_QC":"NOT_RUN","RTSTRUCT_ALIGNMENT_QC":"NOT_RUN","MASK_QC":"NOT_RUN","ROI_SEMANTIC_QC":"PENDING"},
      "private_source_paths":[],"private_workflow":{}}
    stage="manifest"; original_db_dir=None; db_switched=False
    try:
        write_progress(progress_path,stage)
        case=json.loads(Path(manifest).read_text(encoding="utf-8")); c=case["candidate"]
        mr_paths=list(c["mr_absolute_file_paths"]); rt_path=str(c["rtstruct_absolute_file_path"])
        mr_uid=str(c["mr_series_uid"]); rt_uid=str(c["rtstruct_series_uid"])
        n_expected=int(c["mr_required_file_count"]); rt_expected=int(c["rtstruct_required_file_count"])
        if len(mr_paths)!=n_expected or not mr_paths or not all(os.path.isfile(x) for x in mr_paths) or not os.path.isfile(rt_path):
            raise FileNotFoundError("selected source files/count invalid")
        result["private_source_paths"]=mr_paths+[rt_path]
        stage="mr_metadata"
        write_progress(progress_path,stage)
        mrs=[pydicom.dcmread(x,stop_before_pixels=True,specific_tags=MR_TAGS) for x in mr_paths]
        patient=uniq([v(d,"PatientID") for d in mrs]); studies=uniq([v(d,"StudyInstanceUID") for d in mrs])
        series=uniq([v(d,"SeriesInstanceUID") for d in mrs]); frames=uniq([v(d,"FrameOfReferenceUID") for d in mrs])
        sops=[str(v(d,"SOPInstanceUID","")) for d in mrs]
        rows=[int(v(d,"Rows",0) or 0) for d in mrs]; cols=[int(v(d,"Columns",0) or 0) for d in mrs]
        ps=[np.asarray(v(d,"PixelSpacing",[]),dtype=float) for d in mrs]
        iops=[np.asarray(v(d,"ImageOrientationPatient",[]),dtype=float) for d in mrs]
        ipps=[np.asarray(v(d,"ImagePositionPatient",[]),dtype=float) for d in mrs]
        errors=[]
        if len(patient)!=1 or len(studies)!=1 or len(series)!=1 or series[0]!=mr_uid: errors.append("mixed_or_mismatched_patient_study_series")
        if len(set(sops))!=len(mrs) or any(not x for x in sops): errors.append("duplicate_or_missing_sop_uid")
        if len(set(rows))!=1 or rows[0]<=0 or len(set(cols))!=1 or cols[0]<=0: errors.append("mixed_or_invalid_rows_columns")
        if any(len(x)!=2 or not np.all(np.isfinite(x)) or np.any(x<=0) for x in ps): errors.append("invalid_pixel_spacing")
        if any(len(x)!=6 or not np.all(np.isfinite(x)) for x in iops): errors.append("invalid_orientation")
        if any(len(x)!=3 or not np.all(np.isfinite(x)) for x in ipps): errors.append("invalid_position")
        if ps and all(len(x)==2 for x in ps) and any(np.max(np.abs(x-ps[0]))>1e-5 for x in ps[1:]): errors.append("inconsistent_pixel_spacing")
        normal=None; proj=np.asarray([]); gaps=np.asarray([]); spacing=None; duplicates=0; irregular=[]; suspect=[]; max_inplane_shift=None
        if iops and all(len(x)==6 for x in iops):
            if any(np.max(np.abs(x-iops[0]))>ORIENT_TOL for x in iops[1:]): errors.append("inconsistent_orientation")
            xd,yd=iops[0][:3],iops[0][3:]; cross=np.cross(xd,yd); nlen=float(np.linalg.norm(cross))
            if abs(np.linalg.norm(xd)-1)>ORIENT_TOL or abs(np.linalg.norm(yd)-1)>ORIENT_TOL or abs(float(np.dot(xd,yd)))>ORIENT_TOL: errors.append("non_orthonormal_orientation")
            if nlen>0:
                normal=cross/nlen; proj=np.asarray([float(np.dot(p,normal)) for p in ipps]); order=np.argsort(proj); sorted_proj=proj[order]; gaps=np.diff(sorted_proj)
                if len(sorted_proj):
                    ipps_array=np.asarray(ipps,dtype=float); origin=ipps_array[order[0]]
                    expected=origin[None,:]+(sorted_proj-sorted_proj[0])[:,None]*normal[None,:]
                    max_inplane_shift=float(np.max(np.linalg.norm(ipps_array[order]-expected,axis=1)))
                pos=gaps[gaps>1e-6]
                if len(pos):
                    spacing=float(np.median(pos)); tol=max(POS_TOL,0.01*spacing)
                    duplicates=int(np.sum(np.abs(gaps)<=1e-6))
                    irregular=[float(x) for x in gaps if abs(float(x)-spacing)>tol]
                    suspect=[float(x) for x in gaps if float(x)>spacing+tol]
            else: errors.append("invalid_normal")
        if len(mrs)<2 or spacing is None: geom_status="PENDING"
        elif duplicates or irregular or suspect or (max_inplane_shift is not None and max_inplane_shift>POS_TOL):
            geom_status="FAIL"
            if duplicates: errors.append("duplicate_slice_centers")
            if irregular: errors.append("nonuniform_slice_centers")
            if suspect: errors.append("large_gap_possible_missing_slice")
            if max_inplane_shift is not None and max_inplane_shift>POS_TOL: errors.append("in_plane_image_position_shift")
        else: geom_status="FAIL" if errors else "PASS"
        rt=pydicom.dcmread(rt_path,stop_before_pixels=True)
        roi_names={}; roi_frames={}; observations={}
        for x in getattr(rt,"StructureSetROISequence",[]):
            n=str(getattr(x,"ROINumber","")); roi_names[n]=str(getattr(x,"ROIName","")); roi_frames[n]=str(getattr(x,"ReferencedFrameOfReferenceUID",""))
        for x in getattr(rt,"RTROIObservationsSequence",[]):
            observations[str(getattr(x,"ReferencedROINumber",""))]={"interpreted_type":str(getattr(x,"RTROIInterpretedType","")),"observation_number":str(getattr(x,"ObservationNumber",""))}
        rt_frames=[]; ref_series=[]; ref_study=[]
        for f in getattr(rt,"ReferencedFrameOfReferenceSequence",[]):
            if getattr(f,"FrameOfReferenceUID",None): rt_frames.append(str(f.FrameOfReferenceUID))
            for st in getattr(f,"RTReferencedStudySequence",[]):
                if getattr(st,"ReferencedSOPInstanceUID",None): ref_study.append(str(st.ReferencedSOPInstanceUID))
                for sr in getattr(st,"RTReferencedSeriesSequence",[]):
                    if getattr(sr,"SeriesInstanceUID",None): ref_series.append(str(sr.SeriesInstanceUID))
        sop_idx={sops[i]:i for i in range(len(sops))}; contours=[]; roi_map=[]
        for roi_item in getattr(rt,"ROIContourSequence",[]):
            rn=str(getattr(roi_item,"ReferencedROINumber",""))
            roi_map.append({"roi_number":rn,"roi_name":roi_names.get(rn,""),"referenced_frame_uid":roi_frames.get(rn,""),
                            "observation":observations.get(rn,{"interpreted_type":"","observation_number":""})})
            for x in getattr(roi_item,"ContourSequence",[]):
                raw=np.asarray(getattr(x,"ContourData",[]),dtype=float); n=int(getattr(x,"NumberOfContourPoints",0) or 0)
                count_ok=raw.size==3*n and raw.size>0 and raw.size%3==0; finite=bool(np.all(np.isfinite(raw))) if raw.size else False
                pts=raw.reshape((-1,3)) if count_ok else np.empty((0,3)); refs=[str(getattr(y,"ReferencedSOPInstanceUID","")) for y in getattr(x,"ContourImageSequence",[])]
                residual=[]; in_bounds=[]
                if normal is not None and len(pts):
                    for ref in refs:
                        if ref not in sop_idx: continue
                        idx=sop_idx[ref]; delta=pts-ipps[idx]; residual.extend(np.abs(delta@normal).tolist())
                        colidx=(delta@iops[idx][:3])/ps[idx][1]; rowidx=(delta@iops[idx][3:])/ps[idx][0]
                        in_bounds.append(bool(np.all((colidx>=-.5)&(colidx<=cols[idx]-.5)&(rowidx>=-.5)&(rowidx<=rows[idx]-.5))))
                contours.append({"roi_number":rn,"type":str(getattr(x,"ContourGeometricType","")),"npoints":n,"count_ok":bool(count_ok),
                    "finite":finite,"pts":pts.tolist() if finite and count_ok else [],"refs":refs,
                    "refs_resolved":bool(refs) and all(y in sop_idx for y in refs),
                    "max_plane_residual_mm":float(max(residual)) if residual else None,
                    "inside_referenced_image":all(in_bounds) if in_bounds else None})
        rt_frames=uniq(rt_frames+[x["referenced_frame_uid"] for x in roi_map])
        frame_rel="SAME_FRAME" if len(frames)==1 and len(rt_frames)==1 and frames[0]==rt_frames[0] else "DIFFERENT_FRAME" if frames and rt_frames else "FRAME_UID_UNKNOWN"
        refs_ok=bool(contours) and all(x["refs_resolved"] for x in contours)
        chain_ok=mr_uid in set(ref_series) and bool(set(studies)&set(ref_study)) and refs_ok
        contour_ok=bool(contours) and all(x["count_ok"] and x["finite"] and x["type"]=="CLOSED_PLANAR" and x["max_plane_residual_mm"] is not None and x["max_plane_residual_mm"]<=PLANE_TOL for x in contours)
        existing_db=slicer.dicomDatabase
        reg_info={"status":"NOT_REQUIRED_SAME_FRAME","objects":[]} if frame_rel=="SAME_FRAME" else find_patient_regs(existing_db,studies[0] if studies else "",mr_uid,rt_uid)
        alignment="FAIL" if not chain_ok or not contour_ok else "PENDING"
        result["status"]["GEOMETRY_QC"]=geom_status
        result["status"]["RTSTRUCT_ALIGNMENT_QC"]=alignment
        result["private_case_identity"]={"patient_id":patient,"mr_study_uids":studies,"mr_series_uid":mr_uid,"mr_frame_uids":frames,
            "mr_file_paths":mr_paths,"rtstruct_path":rt_path,"rtstruct_sop_uid":str(getattr(rt,"SOPInstanceUID","")),
            "rtstruct_series_uid":rt_uid,"rtstruct_study_uid":str(getattr(rt,"StudyInstanceUID","")),
            "rtstruct_frame_uids":rt_frames,"rt_referenced_series_uids":uniq(ref_series),"rt_referenced_study_sops":uniq(ref_study)}
        result["private_mr_geometry"]={"file_count":len(mrs),"expected_count":n_expected,"shape_kji":[len(mrs),rows[0],cols[0]],
            "rows":rows[0],"columns":cols[0],"pixel_spacing_row_col_mm":ps[0].tolist(),"image_orientation_patient":iops[0].tolist(),
            "slice_normal_lps":normal.tolist() if normal is not None else None,"slice_thickness_mm_values":uniq([v(x,"SliceThickness") for x in mrs]),
            "spacing_between_slices_mm_values":uniq([v(x,"SpacingBetweenSlices") for x in mrs]),"center_spacing_median_mm":spacing,
            "center_spacing_min_mm":float(np.min(gaps)) if len(gaps) else None,"center_spacing_max_mm":float(np.max(gaps)) if len(gaps) else None,
            "duplicate_position_count":duplicates,"irregular_spacing_count":len(irregular),"potential_missing_gap_count":len(suspect),
            "sorted_center_gaps_mm":[float(x) for x in gaps],"max_in_plane_shift_mm":max_inplane_shift,
            "projection_range_mm":[float(np.min(proj)),float(np.max(proj))] if len(proj) else None,
            "unique_patient_study_series_frame":len(patient)==len(studies)==len(series)==len(frames)==1,
            "transfer_syntax_uids":uniq([str(getattr(getattr(x,"file_meta",None),"TransferSyntaxUID","")) for x in mrs]),
            "geometry_errors":errors,"status":geom_status}
        result["private_rtstruct"]={"roi_mapping":roi_map,"contour_count":len(contours),"contour_types":uniq([x["type"] for x in contours]),
            "coordinate_count_mismatch":sum(not x["count_ok"] for x in contours),"nonfinite_contours":sum(not x["finite"] for x in contours),
            "contours_without_refs":sum(not x["refs"] for x in contours),"reference_count":sum(len(x["refs"]) for x in contours),
            "unique_reference_count":len({r for x in contours for r in x["refs"]}),
            "unresolved_contour_reference_count":sum(not x["refs_resolved"] for x in contours),
            "max_plane_residual_mm":max((x["max_plane_residual_mm"] or 0 for x in contours),default=None),
            "contours_outside_image_bounds":sum(x["inside_referenced_image"] is False for x in contours),
            "reference_chain_ok":chain_ok,"contour_geometry_ok":contour_ok,"frame_relation":frame_rel,"reg_qc":reg_info,
            "contours":contours,"semantic_state":"SEMANTIC_PENDING"}
        refs_by_roi={}
        for c in contours: refs_by_roi.setdefault(c["roi_number"],set()).update(c["refs"])
        result["private_workflow"].update({"selected_candidate_rank":case.get("selection_rank"),"manifest_path":manifest,"source_files_readonly":True,
            "no_pixeldata_read_by_metadata_stage":True,"raw_source_copied":False})

        stage="slicerrt_reader"
        write_progress(progress_path,stage,"before_reader_update")
        reader=slicer.vtkSlicerDicomRtReader(); reader.SetFileName(rt_path); reader.Update()
        write_progress(progress_path,stage,"reader_update_returned")
        reader_ok=bool(reader.GetLoadRTStructureSetSuccessful()); reader_sops=str(reader.GetRTStructureSetReferencedSOPInstanceUIDs() or "").split()
        reader_reference_matches=[rn for rn,refs in refs_by_roi.items() if set(reader_sops)==refs]
        reader_rois=[]
        for ix in range(int(reader.GetNumberOfRois())):
            poly=reader.GetRoiPolyData(ix)
            reader_rois.append({"roi_number":int(reader.GetRoiNumber(ix)),"roi_name":str(reader.GetRoiName(ix) or ""),
                "referenced_series_uid":str(reader.GetRoiReferencedSeriesUid(ix) or ""),
                "polydata_points":int(poly.GetNumberOfPoints()) if poly else 0,"polydata_lines":int(poly.GetNumberOfLines()) if poly else 0})
        result["private_rtstruct"]["slicerrt_reader"]={"success":reader_ok,"roi_count":int(reader.GetNumberOfRois()),
            "roi_mapping":reader_rois,"referenced_sop_uids":reader_sops,
            "reference_list_scope":"per_roi_reference_set","matches_per_roi_reference_set":bool(reader_reference_matches),
            "matching_roi_numbers":reader_reference_matches}

        stage="temporary_dicom_database"
        write_progress(progress_path,stage)
        db_dir=Path(out_dir)/"private"/"dicomdb"; db_dir.mkdir(parents=True,exist_ok=True)
        original_db_dir=DICOMUtils.openTemporaryDatabase(str(db_dir)); db_switched=True
        indexer=ctk.ctkDICOMIndexer()
        for path in mr_paths+[rt_path]: indexer.addFile(slicer.dicomDatabase,path,False)
        write_progress(progress_path,stage,"before_index_wait")
        indexer.waitForImportFinished()
        write_progress(progress_path,stage,"index_wait_returned")
        db_mr=list(slicer.dicomDatabase.filesForSeries(mr_uid)); db_rt=list(slicer.dicomDatabase.filesForSeries(rt_uid))
        allowed={os.path.normcase(os.path.realpath(x)) for x in mr_paths+[rt_path]}
        if len(db_mr)!=n_expected or len(db_rt)!=rt_expected or any(os.path.normcase(os.path.realpath(x)) not in allowed for x in db_mr+db_rt):
            raise RuntimeError("temporary DICOM database count/path mismatch")
        stage="dicom_plugins_load"
        write_progress(progress_path,stage)
        messages=[]; mr_ids=DICOMUtils.loadSeriesByUID([mr_uid],messages=messages); rt_ids=DICOMUtils.loadSeriesByUID([rt_uid],messages=messages)
        write_progress(progress_path,stage,"series_load_returned")
        all_ids=mr_ids+rt_ids
        nodes=[slicer.mrmlScene.GetNodeByID(x) for x in all_ids if slicer.mrmlScene.GetNodeByID(x)]
        volumes=[x for x in nodes if x.IsA("vtkMRMLScalarVolumeNode")]
        segs=[x for x in nodes if x.IsA("vtkMRMLSegmentationNode")]
        volume=None
        for x in volumes:
            if x.GetAttribute("DICOM.SeriesInstanceUID")==mr_uid: volume=x; break
        if volume is None:
            expected=(cols[0],rows[0],len(mrs))
            candidates=[x for x in volumes if x.GetImageData() and tuple(x.GetImageData().GetDimensions())==expected]
            if len(candidates)==1: volume=candidates[0]
        if volume is None or not volume.GetImageData(): raise RuntimeError("Slicer DICOM loader produced no selected MR volume")
        arr=np.asarray(slicer.util.arrayFromVolume(volume))
        write_progress(progress_path,"pixel_decode","array_from_volume_returned")
        if arr.ndim!=3: raise RuntimeError("decoded volume is not 3D")
        finite=bool(np.all(np.isfinite(arr))); dims=[int(x) for x in volume.GetImageData().GetDimensions()]
        matrix=mtx(volume); ras_to_lps=np.diag([-1.,-1.,1.,1.]); spacing_axis=[float(np.linalg.norm(matrix[:3,i])) for i in range(3)]
        origin_ras=[float(x) for x in volume.GetOrigin()]; origin_lps=(ras_to_lps@np.asarray(origin_ras+[1.]))[:3]
        origin_error=float(np.min(np.linalg.norm(np.asarray(ipps)-origin_lps[None,:],axis=1)))
        expected_dirs=[np.asarray([-iops[0][0],-iops[0][1],iops[0][2]]),np.asarray([-iops[0][3],-iops[0][4],iops[0][5]]),
            np.asarray([-normal[0],-normal[1],normal[2]])]
        dots=[abs(float(np.dot(matrix[:3,i]/spacing_axis[i],expected_dirs[i]/np.linalg.norm(expected_dirs[i])))) for i in range(3)]
        dims_ok=list(arr.shape)==[len(mrs),rows[0],cols[0]] and dims==[cols[0],rows[0],len(mrs)]
        spacing_ok=abs(spacing_axis[0]-ps[0][1])<=.01 and abs(spacing_axis[1]-ps[0][0])<=.01 and spacing is not None and abs(spacing_axis[2]-spacing)<=max(POS_TOL,.01*spacing)
        orientation_ok=all(x>=.999 for x in dots); origin_ok=origin_error<=.5
        slice_pos_lps=[]
        for k in range(dims[2]):
            ras=matrix@np.asarray([0.,0.,float(k),1.]); slice_pos_lps.append((ras_to_lps@ras)[:3])
        sop_to_k={}; slice_mapping_errors=[]
        for k,pos in enumerate(slice_pos_lps):
            distances=np.linalg.norm(np.asarray(ipps)-pos[None,:],axis=1); idx=int(np.argmin(distances))
            sop_to_k[sops[idx]]=int(k); slice_mapping_errors.append(float(distances[idx]))
        each_slice_maps=len(sop_to_k)==len(mrs)
        sorted_indices=np.argsort(proj) if len(proj)==len(sops) else []
        mapped_order=[sop_to_k.get(sops[int(i)],-1) for i in sorted_indices]
        map_order_ok=bool(mapped_order) and (all(a<b for a,b in zip(mapped_order,mapped_order[1:])) or all(a>b for a,b in zip(mapped_order,mapped_order[1:])))
        max_slice_mapping_error=max(slice_mapping_errors,default=None)
        volume_geom_ok=bool(dims_ok and spacing_ok and orientation_ok and origin_ok and each_slice_maps and map_order_ok
            and max_slice_mapping_error is not None and max_slice_mapping_error<=.5 and geom_status=="PASS")
        result["status"]["PIXEL_QC"]="PASS" if finite and dims_ok and len(db_mr)==n_expected else "FAIL"
        result["status"]["GEOMETRY_QC"]="FAIL" if not volume_geom_ok or geom_status=="FAIL" else geom_status
        result["private_mr_volume"]={"decoded_array_shape_kji":[int(x) for x in arr.shape],"decoded_dtype":str(arr.dtype),
            "finite_pixel_count":int(np.isfinite(arr).sum()),"nonfinite_pixel_count":int(arr.size-np.isfinite(arr).sum()),
            "minimum":float(np.nanmin(arr)),"maximum":float(np.nanmax(arr)),"dimensions_ijk":dims,
            "spacing_axis_mm":spacing_axis,"origin_ras_mm":origin_ras,"ijk_to_ras":matrix.tolist(),
            "direction_axis_abs_dot_vs_dicom":dots,"origin_to_nearest_ipp_mm":origin_error,
            "all_slices_map_to_unique_dicom_instances":each_slice_maps,"slice_order_mapping_monotonic":map_order_ok,
            "max_slice_center_mapping_error_mm":max_slice_mapping_error,
            "matches_dicom_geometry":volume_geom_ok,"temporary_db_mr_files":len(db_mr),"temporary_db_rtstruct_files":len(db_rt),
            "volume_file":str(Path(out_dir)/"private"/"mr_volume.nrrd")}
        if not slicer.util.saveNode(volume,result["private_mr_volume"]["volume_file"]): raise RuntimeError("MR volume save failed")

        stage="slicerrt_mask_conversion"
        write_progress(progress_path,stage)
        if not reader_ok or not segs:
            result["status"]["RTSTRUCT_ALIGNMENT_QC"]="FAIL" if not reader_ok else "PENDING"
            result["status"]["MASK_QC"]="FAIL" if not reader_ok else "NOT_RUN"
            raise RuntimeError("SlicerRT did not create an RTSTRUCT segmentation")
        seg=segs[0]; segmentation=seg.GetSegmentation(); ids=vtk.vtkStringArray(); segmentation.GetSegmentIDs(ids)
        seg_pairs=[]
        for ix in range(ids.GetNumberOfValues()):
            sid=ids.GetValue(ix); seg_pairs.append({"segment_id":str(sid),"segment_name":str(segmentation.GetSegment(sid).GetName())})
        names={}
        for pair in seg_pairs: names.setdefault(pair["segment_name"],[]).append(pair["segment_id"])
        ordered=len(seg_pairs)==len(reader_rois) and all(seg_pairs[i]["segment_name"]==reader_rois[i]["roi_name"] for i in range(len(seg_pairs)))
        save_seg=str(Path(out_dir)/"private"/"rtstruct_import.seg.nrrd")
        write_progress(progress_path,stage,"before_segmentation_file_save")
        segmentation_saved=bool(slicer.util.saveNode(seg,save_seg))
        if not segmentation_saved and Path(save_seg).exists(): Path(save_seg).unlink()
        write_progress(progress_path,stage,"segmentation_file_save_returned")
        masks=[]; mask_rows=[]; map_failed=False; geom_failed=False; empty=0
        seg_logic=slicer.modules.segmentations.logic()
        for ix,roi in enumerate(reader_rois,1):
            sid=seg_pairs[ix-1]["segment_id"] if ordered else (names.get(roi["roi_name"],[None])[0] if len(names.get(roi["roi_name"],[]))==1 else None)
            if sid is None or any(x["segment_id"]==sid for x in mask_rows):
                map_failed=True; mask_rows.append({"roi_number":roi["roi_number"],"roi_name":roi["roi_name"],"mask_status":"SEGMENT_MAPPING_AMBIGUOUS"}); continue
            label=slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode","private_roi_mask_"+str(ix).zfill(3))
            sid_arr=vtk.vtkStringArray(); sid_arr.InsertNextValue(sid)
            write_progress(progress_path,stage,"before_mask_export_"+str(ix))
            ok=bool(seg_logic.ExportSegmentsToLabelmapNode(seg,sid_arr,label,volume))
            write_progress(progress_path,stage,"mask_export_returned_"+str(ix))
            if not ok or not label.GetImageData():
                map_failed=True; mask_rows.append({"roi_number":roi["roi_number"],"roi_name":roi["roi_name"],"segment_id":sid,"mask_status":"EXPORT_FAILED"})
                slicer.mrmlScene.RemoveNode(label); continue
            ma=np.asarray(slicer.util.arrayFromVolume(label)).copy(); mm=mtx(label); same=ma.shape==arr.shape and np.max(np.abs(mm-matrix))<=MATRIX_TOL
            if not same: geom_failed=True
            nz=int(np.count_nonzero(ma)); empty+=int(nz==0)
            mask_path=str(Path(out_dir)/"private"/("mask_roi_"+str(ix).zfill(3)+".nrrd"))
            saved=bool(slicer.util.saveNode(label,mask_path))
            if saved: masks.append(ma>0)
            mask_rows.append({"roi_number":roi["roi_number"],"roi_name":roi["roi_name"],"segment_id":sid,
                "mask_status":"PASS" if saved and same and nz>0 else "PENDING" if saved and same else "FAIL",
                "mask_file":mask_path if saved else "","shape_kji":[int(x) for x in ma.shape],"spacing_mm":[float(x) for x in label.GetSpacing()],
                "origin_ras_mm":[float(x) for x in label.GetOrigin()],"ijk_to_ras":mm.tolist(),"nonzero_voxels":nz,"matches_mr_geometry":same})
            slicer.mrmlScene.RemoveNode(label)
        result["private_rtstruct"]["slicer_segmentation"]={"node_name":str(seg.GetName()),"segments":seg_pairs,"segment_name_order_matches_slicerrt_reader":ordered,"mask_rows":mask_rows,
            "segmentation_file":save_seg if segmentation_saved else "","segmentation_saved":segmentation_saved,
            "segmentation_storage_error_type":"NO_WRITER" if not segmentation_saved else ""}
        result["status"]["MASK_QC"]="FAIL" if map_failed or geom_failed or not volume_geom_ok else "PENDING" if not mask_rows or empty else "PASS"
        union=np.zeros(arr.shape,dtype=bool)
        for ma in masks:
            if ma.shape==union.shape: union|=ma
        result["private_visuals"]={"slicer_imported_grid_views":save_visuals(out_dir,arr,union,[],matrix,sop_to_k),
            "grid_interpretation":"Slicer uniform grid; do not interpret spatially when GEOMETRY_QC is FAIL"}
        result["private_visuals"]["source_contour_overlay"]=save_source_contour_visual(out_dir,mr_paths,sops,iops,ipps,ps,rows[0],cols[0],contours,normal)
        write_progress(progress_path,stage,"visuals_completed")
        reader_reference_scope_ok=bool(reader_reference_matches)
        result["private_rtstruct"]["slicerrt_reference_scope_matches_pydicom"]=reader_reference_scope_ok
        if not chain_ok or not contour_ok or not reader_reference_scope_ok:
            result["status"]["RTSTRUCT_ALIGNMENT_QC"]="FAIL"
        elif frame_rel=="SAME_FRAME" and volume_geom_ok:
            result["status"]["RTSTRUCT_ALIGNMENT_QC"]="PASS"
        elif frame_rel=="SAME_FRAME" and not volume_geom_ok:
            result["status"]["RTSTRUCT_ALIGNMENT_QC"]="FAIL"
        else:
            result["status"]["RTSTRUCT_ALIGNMENT_QC"]="PENDING"
        result["private_rtstruct"]["alignment_reason"]={"PASS":"direct SOP references, contour geometry, shared frame, and reference volume geometry passed",
            "FAIL":"a direct reference, contour geometry, frame registration, or reference volume geometry check failed",
            "PENDING":"Frame of Reference relation or transform application remains unresolved"}[result["status"]["RTSTRUCT_ALIGNMENT_QC"]]
        result["private_workflow"].update({"temporary_dicom_database":str(db_dir),"copy_files":False,"slicerrt_import_plugin_present":True,
            "input_dicom_paths_unchanged":True,"slicer_version":str(slicer.app.applicationVersion)})
    except Exception as exc:
        result["private_error"]={"stage":stage,"exception_type":type(exc).__name__,"exception_message":str(exc),"traceback":traceback.format_exc()}
        write_progress(progress_path,stage,"exception_"+type(exc).__name__)
    finally:
        if db_switched:
            result["private_workflow"]["temporary_database_restore"]="NOT_NEEDED_SEPARATE_HEADLESS_PROCESS"
            write_progress(progress_path,"finalize","temporary_database_left_for_process_exit")
    result["status"]["ROI_SEMANTIC_QC"]="PENDING"
    write_progress(progress_path,"finalize","serializing_qc_json")
    save_json(output,result)
    write_progress(progress_path,"complete")
    for gate in ["PIXEL_QC","GEOMETRY_QC","RTSTRUCT_ALIGNMENT_QC","MASK_QC","ROI_SEMANTIC_QC"]:
        print(gate+"="+result["status"][gate])
    sys.exit(0 if "private_error" not in result else 1)

if __name__=="__main__":
    main()
