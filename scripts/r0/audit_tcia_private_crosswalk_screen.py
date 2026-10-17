from __future__ import annotations
import argparse, collections, datetime as dt, hashlib, importlib.util, json, os, re, stat, struct, subprocess, sys, time, warnings
from pathlib import Path
from typing import Any

TASK="CMRL-08"
REVISION="r1"
EXPECTED_CLINICAL_BYTES=14233
EXPECTED_CLINICAL_SHA="a59d29c86bb45bca98649d1eb8c7a533558fd1cf7b6beb35f5175ea47a04d1c9"
EXPECTED_INDEX_SHA="450598d6493d800334a8e1ece1fda4a5ec04ca1bd2f73309058f0531f8155572"
EXPECTED_COLLECTIONS_SHA="97e5ac3bba296cb3f4e9d87545231275aad66fc89ba07262b7914e72e857489c"
EXPECTED_INDEX_VERSION="25.0.0-0-gdbf7fd0"
EXPECTED_COLLECTION="cc_tumor_heterogeneity"
MAX_FILES=150000
MAX_SECONDS=25*60
MAX_RT_BYTES=16*1024*1024
PARSER_MAX_DEPTH=32
PARSER_MAX_ELEMENTS=500000
PARSER_CACHE=os.environ.get("CMRL08_PYDICOM_CACHE","")

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def safe_private_dir(repo: Path, private: Path) -> None:
    repo=repo.resolve(strict=True); expected=repo/".local"/"cmrl-08"
    private.mkdir(parents=True,exist_ok=True); cur=repo
    rel=private.absolute().relative_to(repo)
    for part in rel.parts:
        cur=cur/part
        if getattr(os.stat(cur,follow_symlinks=False),"st_file_attributes",0)&0x400:
            raise RuntimeError("private path contains reparse point")
    if private.resolve(strict=True)!=expected.resolve(strict=True):
        raise RuntimeError("private path escaped authorized location")
    chk=subprocess.run(["git","check-ignore","--quiet","--",str(private/"private_patient_join.json")],cwd=repo,check=False)
    if chk.returncode!=0: raise RuntimeError("private path is not ignored")

def _walk_xlsx(root: Path, limit: int=5000):
    root_st=os.stat(root,follow_symlinks=False)
    if getattr(root_st,"st_file_attributes",0)&0x400: raise RuntimeError("clinical search root is a reparse point")
    resolved_root=root.resolve(strict=True)
    seen=0
    for current,dirs,files in os.walk(root,followlinks=False):
        dirs[:]=[d for d in dirs if not (getattr(os.stat(Path(current)/d,follow_symlinks=False),"st_file_attributes",0)&0x400)]
        for name in files:
            path=Path(current)/name
            if not name.lower().endswith(".xlsx"): continue
            try:
                st=os.stat(path,follow_symlinks=False)
                if getattr(st,"st_file_attributes",0)&0x400 or not stat.S_ISREG(st.st_mode): continue
                if not path.resolve(strict=True).is_relative_to(resolved_root): continue
            except OSError:
                continue
            seen+=1
            if seen>limit: raise RuntimeError("clinical search candidate limit reached")
            yield path

def discover_clinical(data_root: Path, repo: Path) -> Path:
    matches=[]; seen=set()
    for root in (data_root,repo/".local"):
        if not root.exists(): continue
        for path in _walk_xlsx(root):
            try:
                resolved=str(path.resolve(strict=True)).casefold()
                if resolved in seen: continue
                seen.add(resolved)
                if path.stat().st_size==EXPECTED_CLINICAL_BYTES and sha256_file(path)==EXPECTED_CLINICAL_SHA: matches.append(path)
            except OSError: continue
    if len(matches)!=1: raise RuntimeError("clinical file unavailable or ambiguous")
    return matches[0]

def _blank(v: Any) -> bool:
    return v is None or (isinstance(v,str) and not v.strip())

def _cell_kind(c: Any) -> str:
    if c.data_type=="f": return "formula"
    v=c.value
    if _blank(v): return "blank"
    if c.is_date or isinstance(v,(dt.date,dt.datetime,dt.time)): return "date/time"
    if isinstance(v,bool): return "boolean"
    if isinstance(v,int): return "integer"
    if isinstance(v,float): return "number"
    if isinstance(v,str): return "text"
    return "other"

ID_HEADER=re.compile(r"(patient|subject|participant).*(id|no|number)|(case).*(name|id|no|number)|(^|[\s_-])(id|mrn)([\s_-]|$)",re.I)
MARKER=re.compile(r"(?i)(legend|codebook|data dictionary|definition|footnote|annotation|注释|释义|编码说明|图例|脚注)")

def summarize_singleton_specs(rows: list[dict], key_column: int=1) -> dict[str,Any]:
    singles=[r for r in rows if not r["keyed"] and r["nonempty_count"]==1]
    columns={r["column"] for r in singles}
    row_numbers=[r["row"] for r in singles]
    nonempty_row_numbers=[r["row"] for r in rows]
    ordered=sorted(row_numbers)
    return {"unkeyed_single_cell_rows":len(singles),
      "single_cell_types":dict(sorted(collections.Counter(r["kind"] for r in singles).items())),
      "same_nonkey_column_category":len(columns)==1 and bool(columns) and key_column not in columns,
      "single_cell_column_category":"SAME_NAMED_NONKEY_FIELD" if len(columns)==1 and key_column not in columns else "MIXED_OR_UNRESOLVED",
      "contiguous_tail_block":bool(ordered) and all(b-a==1 for a,b in zip(ordered,ordered[1:])) and
        bool(nonempty_row_numbers) and max(ordered)==max(nonempty_row_numbers),
      "distinct_style_from_keyed_rows":bool(singles and any(r["key_style"] is not None for r in rows) and
        {r["style"] for r in singles}.isdisjoint({r["key_style"] for r in rows if r["key_style"] is not None})),
      "singleton_formula_count":sum(bool(r["formula"]) for r in singles),
      "singleton_comment_count":sum(bool(r["comment"]) for r in singles),
      "singleton_merged_count":sum(bool(r["merged"]) for r in singles),
      "explicit_marker_count":sum(bool(r["marker"]) for r in singles)}

def resolve_direct_references(refs: list[str], sop_index: dict[str,list]) -> dict[str,Any]:
    missing=[x for x in set(refs) if not sop_index.get(x)]
    ambiguous=[x for x in set(refs) if len(sop_index.get(x,[]))>1]
    matched=[x for x in set(refs) if len(sop_index.get(x,[]))==1]
    return {"complete":not missing and not ambiguous,"matched":matched,"missing":missing,"ambiguous":ambiguous}

def candidate_pair_gate(mr_expected: int, mr_observed: int, rt_expected: int, rt_observed: int,
                        references_complete: bool, patient_match: bool, reference_chain_complete: bool) -> dict[str,Any]:
    if count_relation(rt_expected,rt_observed)!="COUNT_EQUAL": return {"eligible":False,"reason":"RTSTRUCT_COUNT_NOT_EQUAL"}
    if count_relation(mr_expected,mr_observed)!="COUNT_EQUAL": return {"eligible":False,"reason":"MR_COUNT_NOT_EQUAL"}
    if not references_complete: return {"eligible":False,"reason":"RT_REFERENCES_UNRESOLVED_OR_AMBIGUOUS"}
    if not patient_match: return {"eligible":False,"reason":"PATIENT_ID_MISMATCH"}
    if not reference_chain_complete: return {"eligible":False,"reason":"MR_STUDY_SERIES_SOP_CHAIN_INCONSISTENT"}
    return {"eligible":True,"reason":"DIRECT_REFERENCES_RESOLVED"}

def private_value_hits(public_value: Any, private_values: set[str]) -> list[str]:
    serialized=json.dumps(public_value,ensure_ascii=False)
    return [v for v in private_values if isinstance(v,str) and len(v.strip())>=6 and v in serialized]

def prepare_clinical(data_root: Path, repo: Path, private: Path) -> dict[str,Any]:
    import openpyxl
    path=discover_clinical(data_root,repo)
    if path.stat().st_size!=EXPECTED_CLINICAL_BYTES or sha256_file(path)!=EXPECTED_CLINICAL_SHA: raise RuntimeError("clinical fingerprint mismatch")
    wb=openpyxl.load_workbook(path,read_only=False,data_only=False)
    profile={"status":"FILE_INSPECTED","file_bytes":path.stat().st_size,"sha256":EXPECTED_CLINICAL_SHA,
             "python":sys.version.split()[0],"openpyxl":openpyxl.__version__,"sheet_count":len(wb.worksheets),
             "named_field_count":0,"nonempty_rows":0,"keyed_rows":0,"key_string_values":0,"key_distinct_values":0,
             "unkeyed_single_cell_rows":0,"single_cell_types":{},"same_nonkey_column_category":False,
             "contiguous_tail_block":False,"distinct_style_from_keyed_rows":False,"singleton_formula_count":0,
             "singleton_comment_count":0,"singleton_merged_count":0,"explicit_marker_count":0,
             "internal_codebook_marker_count":0,"row_shape_histogram":{},"candidate_key_column_count":0,"key_field_selection":"CMRL07_FIRST_COLUMN_FIXED",
             "candidate_key_type_counts":{},"key_duplicate_rows":0,"endpoint_codebook":"ENDPOINT_CODEBOOK_UNVERIFIED",
             "role":"OBSERVED_LAYOUT_ONLY"}
    keys=[]; key_types=collections.Counter()
    try:
        if len(wb.worksheets)!=1: raise RuntimeError("unexpected worksheet count")
        ws=wb.worksheets[0]
        sample=list(ws.iter_rows(min_row=1,max_row=min(ws.max_row or 1,15),values_only=False))
        possible=[]
        for ri,row in enumerate(sample,1):
            nb=[c for c in row if _cell_kind(c)!="blank"]
            tx=[c for c in nb if isinstance(c.value,str) and c.data_type!="f"]
            if len(tx)>=2: possible.append((len(tx),len(nb),ri))
        header=max(possible)[2] if possible else 1
        hdr=sample[header-1] if sample else []
        maxcol=ws.max_column or len(hdr)
        headers=[(hdr[i].value if i<len(hdr) and isinstance(hdr[i].value,str) else "") for i in range(maxcol)]
        profile["named_field_count"]=sum(bool(x.strip()) for x in headers)
        key_cols=[0] if maxcol>0 else []
        profile["candidate_key_column_count"]=len(key_cols)
        if len(key_cols)!=1: raise RuntimeError("candidate identifier column is not unique")
        key_col=key_cols[0]; rows=[]; shapes=collections.Counter(); all_marker=0
        for ri,row in enumerate(ws.iter_rows(min_row=header+1,max_col=maxcol,values_only=False),header+1):
            nb=[c for c in row if _cell_kind(c)!="blank"]
            if not nb: continue
            shapes[len(nb)]+=1
            all_marker+=sum(1 for c in row if isinstance(c.value,str) and MARKER.search(c.value))
            keycell=row[key_col] if key_col<len(row) else None
            haskey=keycell is not None and _cell_kind(keycell)!="blank"
            if haskey:
                v=keycell.value; key_types[type(v).__name__]+=1
                keys.append(v if isinstance(v,str) else None)
            rows.append({"row":ri,"cells":nb,"keyed":haskey})
        profile["nonempty_rows"]=len(rows); profile["keyed_rows"]=sum(r["keyed"] for r in rows)
        profile["key_string_values"]=sum(isinstance(v,str) for v in keys); profile["key_distinct_values"]=len({v for v in keys if isinstance(v,str)})
        profile["key_duplicate_rows"]=profile["key_string_values"]-profile["key_distinct_values"]
        profile["candidate_key_type_counts"]=dict(sorted(key_types.items()))
        profile["row_shape_histogram"]={str(k):v for k,v in sorted(shapes.items())}
        specs=[]
        header_values={str(x).strip().casefold() for x in headers if isinstance(x,str) and x.strip()}
        for r in rows:
            cell=r["cells"][0] if len(r["cells"])==1 else None
            marker=bool(cell is not None and isinstance(cell.value,str) and
                        (MARKER.search(cell.value) or cell.value.strip().casefold() in header_values))
            specs.append({"row":r["row"],"keyed":r["keyed"],"nonempty_count":len(r["cells"]),
              "column":cell.column if cell is not None else None,"kind":_cell_kind(cell) if cell is not None else None,
              "style":cell.style_id if cell is not None else None,
              "key_style":ws.cell(r["row"],key_col+1).style_id if r["keyed"] else None,
              "formula":bool(cell is not None and cell.data_type=="f"),
              "comment":bool(cell is not None and cell.comment is not None),
              "merged":bool(cell is not None and any(cell.coordinate in rg for rg in ws.merged_cells.ranges)),
              "marker":marker})
        profile.update(summarize_singleton_specs(specs,key_col+1))
        profile["internal_codebook_marker_count"]=all_marker
        profile["internal_codebook_marker_count"]=all_marker
        profile["data_validation_count"]=len(ws.data_validations.dataValidation)
        profile["table_count"]=len(ws.tables); profile["defined_name_count"]=len(wb.defined_names)
        (private/"clinical_key_values.json").write_text(json.dumps({"keys":keys,"key_types":dict(sorted(key_types.items()))},ensure_ascii=False),encoding="utf-8")
    finally: wb.close()
    (private/"clinical_summary.json").write_text(json.dumps(profile,ensure_ascii=False,indent=2),encoding="utf-8")
    return profile

LONG_VR={b"OB",b"OD",b"OF",b"OL",b"OV",b"OW",b"SQ",b"UC",b"UR",b"UT",b"UN",b"SV",b"UV"}
UID_TAG=0x00081155
REF_SEQ_BY_CONTEXT={"root":{0x30060010:"frame",0x30060039:"roi"},
 "frame":{0x30060012:"study"},"study":{0x30060014:"series"},
 "series":{0x30060016:"image"},"roi":{0x30060040:"contour"},
 "contour":{0x30060016:"image"}}

def _tag(f,endian):
    b=f.read(4)
    if not b: return None
    if len(b)!=4: raise ValueError("truncated tag")
    g,e=struct.unpack(endian+"HH",b); return (g<<16)|e

def _header(f,tag,explicit,endian):
    if tag>>16==0xFFFE:
        b=f.read(4)
        if len(b)!=4: raise ValueError("truncated item length")
        return b"",struct.unpack(endian+"I",b)[0]
    if explicit:
        vr=f.read(2)
        if len(vr)!=2: raise ValueError("truncated VR")
        if vr in LONG_VR:
            reserved=f.read(2); ln=f.read(4)
            if len(reserved)!=2 or len(ln)!=4: raise ValueError("truncated long header")
            return vr,struct.unpack(endian+"I",ln)[0]
        ln=f.read(2)
        if len(ln)!=2: raise ValueError("truncated short header")
        return vr,struct.unpack(endian+"H",ln)[0]
    b=f.read(4)
    if len(b)!=4: raise ValueError("truncated implicit header")
    return b"",struct.unpack(endian+"I",b)[0]

def _read_uid(f,length,stats):
    if length>512: raise ValueError("oversize UID value")
    b=f.read(length); stats["value_bytes_read"]+=len(b)
    if len(b)!=length: raise ValueError("truncated UID")
    return b.decode("ascii","strict").rstrip("\x00 ").lstrip()

def _skip_sequence(f,length,explicit,endian,depth,counter):
    if depth>32: raise ValueError("sequence nesting limit")
    end=None if length==0xFFFFFFFF else f.tell()+length
    while end is None or f.tell()<end:
        if end is not None and end-f.tell()<8: raise ValueError("truncated sequence")
        tag=_tag(f,endian)
        if tag is None: raise ValueError("unexpected EOF in sequence")
        _,itemlen=_header(f,tag,explicit,endian)
        if tag==0xFFFEE0DD: return
        if tag!=0xFFFEE000: raise ValueError("invalid sequence item")
        if itemlen==0xFFFFFFFF: _skip_dataset(f,None,explicit,endian,depth+1,counter,None,{},None)
        else: f.seek(itemlen,1)
    if end is not None and f.tell()!=end: raise ValueError("sequence length mismatch")

def _skip_dataset(f,end,explicit,endian,depth,counter,context,state,on_element):
    if depth>32: raise ValueError("dataset nesting limit")
    while end is None or f.tell()<end:
        if counter["elements"]>=500000: raise ValueError("element budget reached")
        start=f.tell(); tag=_tag(f,endian)
        if tag is None:
            if end is None: return
            raise ValueError("unexpected EOF in item")
        if tag>>16==0xFFFE:
            _,ln=_header(f,tag,explicit,endian)
            if tag in (0xFFFEE00D,0xFFFEE0DD): return
            if tag==0xFFFEE000:
                if ln==0xFFFFFFFF: _skip_dataset(f,None,explicit,endian,depth+1,counter,None,{},None)
                else: f.seek(ln,1)
                continue
            raise ValueError("unexpected delimiter")
        _,ln=_header(f,tag,explicit,endian); counter["elements"]+=1
        if context=="root" and tag==0x7FE00010: return
        nextctx=REF_SEQ_BY_CONTEXT.get(context or "",{}).get(tag)
        if tag==0x30060050: counter["coordinate_value_bytes_skipped"]+=0 if ln==0xFFFFFFFF else ln
        if nextctx: _parse_sequence(f,ln,explicit,endian,depth+1,counter,nextctx,state)
        elif ln==0xFFFFFFFF: _skip_sequence(f,ln,explicit,endian,depth+1,counter)
        else:
            if on_element: on_element(f,tag,ln,context,state,counter)
            else: f.seek(ln,1)
        if f.tell()<start: raise ValueError("invalid parser position")
    if end is not None and f.tell()!=end: raise ValueError("item length mismatch")

def _parse_sequence(f,length,explicit,endian,depth,counter,childctx,state):
    if depth>32: raise ValueError("sequence nesting limit")
    end=None if length==0xFFFFFFFF else f.tell()+length
    while end is None or f.tell()<end:
        if end is not None and end-f.tell()<8: raise ValueError("truncated sequence")
        tag=_tag(f,endian)
        if tag is None: raise ValueError("unexpected EOF in allowed sequence")
        _,itemlen=_header(f,tag,explicit,endian)
        if tag==0xFFFEE0DD: return
        if tag!=0xFFFEE000: raise ValueError("invalid allowed sequence item")
        child={"context":childctx,"frame":None,"study":None,"series":None,"refs":state.setdefault("refs",[])}
        if childctx=="study": child["frame"]=state.get("frame")
        if childctx in ("series","image","contour"): child.update({k:state.get(k) for k in ("frame","study","series")})
        if itemlen==0xFFFFFFFF: _skip_dataset(f,None,explicit,endian,depth+1,counter,childctx,child,_capture_element)
        else: _skip_dataset(f,f.tell()+itemlen,explicit,endian,depth+1,counter,childctx,child,_capture_element)
    if end is not None and f.tell()!=end: raise ValueError("allowed sequence length mismatch")

def _capture_element(f,tag,length,context,state,counter):
    if tag==0x30060024 and context=="frame": state["frame"]=_read_uid(f,length,counter)
    elif tag==UID_TAG and context=="study": state["study"]=_read_uid(f,length,counter)
    elif tag==0x0020000E and context=="series": state["series"]=_read_uid(f,length,counter)
    elif tag==UID_TAG and context=="image":
        sop=_read_uid(f,length,counter)
        state.setdefault("refs",[]).append({"frame":state.get("frame"),"study":state.get("study"),"series":state.get("series"),"sop":sop})
    else: f.seek(length,1)

def _meta_start(f):
    f.seek(0); prefix=f.read(132)
    if len(prefix)<132 or prefix[128:132]!=b"DICM": raise ValueError("not Part 10")
    syntax=None
    while True:
        pos=f.tell(); tag=_tag(f,"<")
        if tag is None: raise ValueError("missing dataset")
        if tag>>16!=0x0002:
            f.seek(pos); return pos,syntax
        _,ln=_header(f,tag,True,"<")
        if tag==0x00020010:
            if ln>128: raise ValueError("invalid syntax")
            syntax=f.read(ln).decode("ascii","strict").rstrip("\x00 ")
        else: f.seek(ln,1)

def parse_rtstruct_references(path: Path) -> dict[str,Any]:
    stats={"elements":0,"value_bytes_read":0,"coordinate_value_bytes_skipped":0}; refs=[]
    with path.open("rb") as f:
        _,syntax=_meta_start(f)
        if syntax=="1.2.840.10008.1.2.1": explicit,endian=True,"<"
        elif syntax=="1.2.840.10008.1.2": explicit,endian=False,"<"
        elif syntax=="1.2.840.10008.1.2.2": explicit,endian=True,">"
        else: raise ValueError("unsupported transfer syntax")
        _skip_dataset(f,None,explicit,endian,0,stats,"root",{"refs":refs},_capture_element)
    contexts=[{"frame":r["frame"],"study":r["study"],"series":r["series"],"sop":r["sop"]} for r in refs if r.get("series")]
    return {"series_contexts":contexts,"sop_refs":sorted({r["sop"] for r in refs}),
            "frame_refs":sorted({r["frame"] for r in refs if r.get("frame")}),
            "coordinate_value_bytes_read":0,"coordinate_value_bytes_skipped":stats["coordinate_value_bytes_skipped"],
            "value_bytes_read":stats["value_bytes_read"],"element_count":stats["elements"]}


def exact_join(clinical_keys: list[Any], dicom_ids: list[Any]) -> dict[str,Any]:
    c=collections.Counter(x for x in clinical_keys if isinstance(x,str))
    d=collections.Counter(x for x in dicom_ids if isinstance(x,str))
    matches=[]; unmatched=[]; ambiguous=[]
    for key,n in c.items():
        if n!=1 or d.get(key,0)>1: ambiguous.append(key)
        elif d.get(key,0)==1: matches.append(key)
        else: unmatched.append(key)
    nonstring_clinical=sum(not isinstance(x,str) for x in clinical_keys)
    invalid_dicom=sum(not isinstance(x,str) for x in dicom_ids)
    return {"mapping":{k:k for k in matches},"matched_keys":matches,"unmatched_keys":unmatched,
            "ambiguous_keys":ambiguous,"clinical_key_count":len(c),"dicom_id_count":len(d),
            "clinical_duplicate_rows":sum(max(0,n-1) for n in c.values()),
            "dicom_duplicate_rows":sum(max(0,n-1) for n in d.values()),
            "clinical_nonstring_count":nonstring_clinical,"dicom_nonstring_count":invalid_dicom}

def count_relation(expected: int|None, observed: int) -> str:
    if expected is None: return "EXPECTED_UNAVAILABLE"
    if observed==expected: return "COUNT_EQUAL"
    return "COUNT_SHORT" if observed<expected else "COUNT_EXCESS"

def chronology_ranks(series_map: dict[str,dict]) -> dict[tuple[str,str],int|None]:
    by_patient=collections.defaultdict(dict)
    for uid,s in series_map.items():
        if len(s["patients"])!=1 or len(s["studies"])!=1: continue
        patient=next(iter(s["patients"])); study=next(iter(s["studies"]))
        dates=s["study_dates"] or s["series_dates"] or s["acq_dates"]
        times=s["study_times"] or s["series_times"] or s["acq_times"]
        date=min(dates) if dates else ""
        tm=min(times) if times else ""
        key=(date,tm)
        old=by_patient[patient].get(study)
        if old is None or (key[0] and key<old[0]): by_patient[patient][study]=(key,uid)
    out={}
    for patient,studies in by_patient.items():
        valid=[(key,study) for study,(key,_) in studies.items() if key[0]]
        valid.sort(key=lambda x:(x[0][0],x[0][1],x[1]))
        for rank,(_,study) in enumerate(valid,1): out[(patient,study)]=rank
        for study,(key,_) in studies.items():
            if not key[0]: out[(patient,study)]=None
    return out

def _load_support(repo: Path):
    if PARSER_CACHE and PARSER_CACHE not in sys.path: sys.path.insert(0,PARSER_CACHE)
    import pydicom
    if pydicom.__version__!="3.0.2": raise RuntimeError("unexpected pydicom version")
    spec=importlib.util.spec_from_file_location("cmrl08_manual_helpers",repo/"scripts"/"r0"/"audit_tcia_manual_dicom.py")
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return pydicom,module

def _get_text(ds: Any, keyword: str) -> str|None:
    try: value=getattr(ds,keyword)
    except Exception: return None
    if value is None or not isinstance(value,str): return None
    return str(value)

def _top_tags(pydicom):
    return [pydicom.tag.Tag(x) for x in (
        0x00080016,0x00080018,0x00080020,0x00080021,0x00080022,0x00080030,0x00080031,0x00080032,
        0x00080060,0x0008103E,0x00081030,0x00081090,0x00100020,0x00180020,0x00180021,0x00180022,
        0x00180023,0x00180024,0x00180050,0x00180080,0x00180081,0x00180086,0x00180088,
        0x00181020,0x00181030,0x0020000D,0x0020000E,0x00200052,0x00200011,0x00200012,
        0x0008002A,0x0008002B)]

def _new_series():
    return {"patients":set(),"studies":set(),"frames":set(),"modalities":set(),"sops":collections.defaultdict(list),
            "files":[],"descriptions":set(),"protocols":set(),"sequence_names":set(),"image_types":set(),
            "study_dates":set(),"study_times":set(),"series_dates":set(),"series_times":set(),
            "acq_dates":set(),"acq_times":set(),"conflict_fields":set()}

def _safe_add(s,key,value):
    if value is not None and value!="": s[key].add(value)

def scan_headers(root: Path, repo: Path) -> dict[str,Any]:
    pydicom,manual=_load_support(repo)
    start=time.monotonic(); deadline=start+MAX_SECONDS
    before=manual.inventory(root,deadline)
    out={"runtime":{"python":sys.version.split()[0],"pydicom":pydicom.__version__},
         "limits":{"max_files":MAX_FILES,"max_seconds":MAX_SECONDS,"max_rtstruct_bytes":MAX_RT_BYTES},
         "snapshot_before":{k:before.get(k) for k in ("complete","file_count","directory_count","total_bytes","zero_byte_file_count","dicom_candidate_count","reparse_or_symlink_entries_skipped","special_entry_count","metadata_error_count")},
         "parsed_file_count":0,"parse_error_classes":collections.Counter(),"missing_patient":0,"missing_study":0,
         "missing_series":0,"missing_sop":0,"modalities":collections.Counter(),"series":{},
         "sop_index":collections.defaultdict(list),"rtstruct_files":[],"deadline_reached":False}
    if not before.get("complete") or before["file_count"]>MAX_FILES or before["dicom_candidate_count"]>MAX_FILES:
        out["stop_reason"]="INITIAL_INVENTORY_INCOMPLETE_OR_OVER_LIMIT"; return out
    tags=_top_tags(pydicom)
    for i,(path,size) in enumerate(before["candidates"],1):
        if time.monotonic()>=deadline:
            out["deadline_reached"]=True; out["stop_reason"]="25_MINUTE_BUDGET"; break
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                ds=manual._parse_dataset(path,force=False,specific_tags=tags)
            patient=_get_text(ds,"PatientID"); study=_get_text(ds,"StudyInstanceUID")
            series=_get_text(ds,"SeriesInstanceUID"); sop=_get_text(ds,"SOPInstanceUID")
            modality=_get_text(ds,"Modality")
            frame=_get_text(ds,"FrameOfReferenceUID")
            rec={"path":path,"size":int(size),"patient":patient,"study":study,"series":series,"sop":sop,
                 "modality":modality,"frame":frame}
            out["parsed_file_count"]+=1
            out["modalities"][modality or "MISSING"]+=1
            out["missing_patient"]+=int(not patient); out["missing_study"]+=int(not study)
            out["missing_series"]+=int(not series); out["missing_sop"]+=int(not sop)
            if sop: out["sop_index"][sop].append(rec)
            if series:
                s=out["series"].setdefault(series,_new_series())
                for field,val in (("patients",patient),("studies",study),("frames",frame),("modalities",modality),
                                  ("descriptions",_get_text(ds,"SeriesDescription")),("protocols",_get_text(ds,"ProtocolName")),
                                  ("sequence_names",_get_text(ds,"SequenceName")),("image_types",_get_text(ds,"ImageType")),
                                  ("study_dates",_get_text(ds,"StudyDate")),("study_times",_get_text(ds,"StudyTime")),
                                  ("series_dates",_get_text(ds,"SeriesDate")),("series_times",_get_text(ds,"SeriesTime")),
                                  ("acq_dates",_get_text(ds,"AcquisitionDate")),("acq_times",_get_text(ds,"AcquisitionTime"))):
                    _safe_add(s,field,val)
                if sop: s["sops"][sop].append(path)
                s["files"].append(path)
            if modality=="RTSTRUCT": out["rtstruct_files"].append(rec)
        except Exception as exc:
            out["parse_error_classes"][type(exc).__name__]+=1
        if i%10000==0: print(f"HEADER_PROGRESS parsed={i} elapsed_s={int(time.monotonic()-start)}")
    out["parse_error_classes"]=dict(sorted(out["parse_error_classes"].items()))
    if not out.get("stop_reason"):
        after=manual.inventory(root,deadline)
        out["snapshot_after"]={k:after.get(k) for k in ("complete","file_count","directory_count","total_bytes","zero_byte_file_count","dicom_candidate_count","reparse_or_symlink_entries_skipped","special_entry_count","metadata_error_count")}
        out["snapshots_equal"]=bool(after.get("complete") and before["snapshots"]==after["snapshots"])
    else:
        out["snapshot_after"]=None; out["snapshots_equal"]=False
    out["elapsed_seconds"]=round(time.monotonic()-start,3)
    out["patient_id_count"]=len({r["patient"] for v in out["sop_index"].values() for r in v if r.get("patient")})
    out["sop_duplicate_file_count"]=sum(len(v)-1 for v in out["sop_index"].values() if len(v)>1)
    out["unique_sop_count"]=sum(len(s["sops"]) for s in out["series"].values())
    out["local_series_count"]=len(out["series"])
    return out

def official_expected(index_path: Path, collections_path: Path, gap_path: Path) -> tuple[dict,dict]:
    if sha256_file(index_path)!=EXPECTED_INDEX_SHA or sha256_file(collections_path)!=EXPECTED_COLLECTIONS_SHA:
        raise RuntimeError("fixed IDC v25.0.0 cache fingerprint mismatch")
    import duckdb
    con=duckdb.connect(database=":memory:")
    rows=con.execute("SELECT SeriesInstanceUID, Modality, instanceCount FROM read_parquet(?) WHERE collection_id=?",
                     [str(index_path),EXPECTED_COLLECTION]).fetchall()
    con.close()
    expected={}
    for uid,modality,count in rows:
        if uid in expected: raise RuntimeError("duplicate official series UID")
        expected[str(uid)]={"modality":str(modality),"count":int(count)}
    if len(expected)!=821 or sum(x["count"] for x in expected.values())!=131556:
        raise RuntimeError("fixed collection aggregate mismatch")
    gaps=json.loads(gap_path.read_text(encoding="utf-8"))
    if gaps.get("source_index_release")!="25.0.0" or gaps.get("source_index_version")!=EXPECTED_INDEX_VERSION:
        raise RuntimeError("gap list release mismatch")
    return expected,gaps

def reconcile_series(scan: dict, expected: dict, gap_doc: dict) -> dict[str,Any]:
    series=scan["series"]; local={uid:len(s["sops"]) for uid,s in series.items()}
    extra=set(local)-set(expected); missing=set(expected)-set(local)
    rel=collections.Counter(); shortage_sum=0; gap_uids=set()
    for uid,meta in expected.items():
        obs=local.get(uid,0); status=count_relation(meta["count"],obs)
        rel[(meta["modality"],status)]+=1
        shortage_sum+=max(0,meta["count"]-obs)
        if status=="COUNT_SHORT": gap_uids.add(uid)
    listed={}
    for r in gap_doc.get("records",[]):
        uid=r.get("SeriesInstanceUID")
        if not uid or uid in listed: raise RuntimeError("invalid private gap list")
        listed[uid]=r
    gap_match=len(listed)==len(gap_uids) and set(listed)==gap_uids
    if gap_match:
        for uid,r in listed.items():
            m=expected[uid]; obs=local.get(uid,0)
            gap_match &= (int(r.get("expected_instance_count",-1))==m["count"]
                          and int(r.get("observed_unique_sop_count",-1))==obs
                          and int(r.get("shortage_count",-1))==m["count"]-obs)
    modalities={}
    for mod in sorted({x["modality"] for x in expected.values()}):
        exp_n=sum(x["modality"]==mod for x in expected.values())
        local_n=sum(1 for u,s in series.items() if mod in s["modalities"])
        equal=rel[(mod,"COUNT_EQUAL")]; short=rel[(mod,"COUNT_SHORT")]; excess=rel[(mod,"COUNT_EXCESS")]
        modalities[mod]={"expected_series":exp_n,"local_series":local_n,"count_equal_series":equal,
                         "short_series":short,"excess_series":excess,
                         "missing_series":sum(1 for u,x in expected.items() if x["modality"]==mod and u not in local)}
    summary={"expected_series":len(expected),"local_series":len(local),"missing_series":len(missing),
             "extra_local_series":len(extra),"count_equal_series":sum(v for (m,s),v in rel.items() if s=="COUNT_EQUAL"),
             "short_series":len(gap_uids),"excess_series":sum(v for (m,s),v in rel.items() if s=="COUNT_EXCESS"),
             "instance_shortage":shortage_sum,"gap_list_rows":len(listed),"gap_list_matches_recomputed":gap_match,
             "modalities":modalities,"local_files":scan["snapshot_before"].get("file_count"),
             "local_bytes":scan["snapshot_before"].get("total_bytes"),"unique_sops":scan.get("unique_sop_count"),
             "duplicate_sop_file_count":scan.get("sop_duplicate_file_count"),
             "parsed_files":scan.get("parsed_file_count"),"parse_errors":sum(scan.get("parse_error_classes",{}).values()),
             "snapshots_equal":scan.get("snapshots_equal"),"snapshot_complete":bool(scan.get("snapshot_after",{}).get("complete"))}
    baseline_ok=(summary["expected_series"]==821 and summary["local_series"]==806 and summary["missing_series"]==15
      and summary["extra_local_series"]==0 and summary["count_equal_series"]==748 and summary["short_series"]==73
      and summary["excess_series"]==0 and summary["instance_shortage"]==1132 and summary["gap_list_matches_recomputed"]
      and summary["local_files"]==130424 and summary["local_bytes"]==28151425416
      and summary["unique_sops"]==130424 and summary["duplicate_sop_file_count"]==0
      and summary["parsed_files"]==130424 and summary["parse_errors"]==0 and summary["snapshots_equal"]
      and summary["snapshot_complete"] and scan.get("missing_patient")==0 and scan.get("missing_study")==0
      and scan.get("missing_series")==0 and scan.get("missing_sop")==0
      and scan["snapshot_before"].get("zero_byte_file_count")==0
      and scan["snapshot_before"].get("reparse_or_symlink_entries_skipped")==0
      and scan["snapshot_before"].get("special_entry_count")==0
      and scan["snapshot_before"].get("metadata_error_count")==0
      and scan["modalities"]=={"CT":21637,"MR":92508,"PT":16129,"REG":87,"RTSTRUCT":63})
    mr=modalities.get("MR",{})
    rt=modalities.get("RTSTRUCT",{})
    baseline_ok &= (mr.get("expected_series")==523 and mr.get("local_series")==523 and mr.get("count_equal_series")==468
                    and mr.get("short_series")==55 and mr.get("missing_series")==0)
    baseline_ok &= (rt.get("expected_series")==68 and rt.get("local_series")==63 and rt.get("missing_series")==5)
    summary["baseline_consistent"]=bool(baseline_ok)
    summary["status"]="BASELINE_MATCHED" if baseline_ok else "BASELINE_CONFLICT_STOP"
    return summary

def _text_t2(s: dict) -> bool:
    for field in ("descriptions","protocols","sequence_names"):
        for value in s.get(field,set()):
            if re.search(r"(?i)(^|[^A-Z0-9])T2([A-Z0-9_-]*)(?=$|[^A-Z0-9])",value):
                return True
    return False

def _series_frame_status(mr: dict, contexts: list[dict]) -> str:
    frames=set(mr.get("frames",set()))
    rtframes={c.get("frame") for c in contexts if c.get("frame")}
    if not frames or not rtframes: return "FRAME_RELATION_UNKNOWN"
    return "SAME_FRAME_REFERENCE" if frames & rtframes else "DIFFERENT_FRAME_UNRESOLVED"

def select_candidates(scan: dict, expected: dict, rt_ref_results: list[dict]) -> tuple[list[dict],dict,dict]:
    series=scan["series"]; sop_index=scan["sop_index"]; candidates=[]
    counts=collections.Counter(); reasons=collections.Counter()
    for rt in rt_ref_results:
        counts["rtstruct_files_parsed"]+=1
        rt_rec=rt["record"]; rt_series=rt_rec.get("series")
        if not rt_series or rt_series not in series: reasons["RT_SERIES_UNAVAILABLE"]+=1; continue
        rt_s=series[rt_series]; rt_expected=expected.get(rt_series)
        if rt_expected is None or rt_expected["modality"]!="RTSTRUCT": reasons["RT_SERIES_NOT_IN_FIXED_COLLECTION"]+=1; continue
        if count_relation(rt_expected["count"],len(rt_s["sops"]))!="COUNT_EQUAL": reasons["RTSTRUCT_COUNT_NOT_EQUAL"]+=1; continue
        all_refs=rt["refs"]["sop_refs"]; contexts=rt["refs"]["series_contexts"]
        if not all_refs: reasons["NO_DIRECT_SOP_REFERENCES"]+=1; continue
        ref_resolution=resolve_direct_references(all_refs,sop_index)
        if not ref_resolution["complete"]: reasons["RT_REFERENCES_UNRESOLVED_OR_AMBIGUOUS"]+=1; continue
        rt_patient=rt_rec.get("patient")
        if not rt_patient or len(rt_s["patients"])!=1: reasons["RT_PATIENT_ID_UNAVAILABLE_OR_CONFLICTING"]+=1; continue
        mr_uids={c.get("series") for c in contexts if c.get("series")}
        # ROI contour SOP references without hierarchy are assigned only by exact SOP lookup.
        for sop in all_refs:
            rec=sop_index[sop][0]
            if rec.get("modality")=="MR": mr_uids.add(rec.get("series"))
        eligible_this_rt=[]
        for mr_uid in mr_uids:
            mr=series.get(mr_uid); meta=expected.get(mr_uid)
            if not mr or not meta or meta["modality"]!="MR": continue
            if count_relation(meta["count"],len(mr["sops"]))!="COUNT_EQUAL": reasons["MR_COUNT_NOT_EQUAL"]+=1; continue
            if len(mr["patients"])!=1 or next(iter(mr["patients"]))!=rt_patient: reasons["PATIENT_ID_MISMATCH"]+=1; continue
            declared=[c for c in contexts if c.get("series")==mr_uid]
            if not declared: reasons["MR_REFERENCE_CHAIN_MISSING"]+=1; continue
            target_sops={c.get("sop") for c in declared if c.get("sop")}
            roi_or_other_sops=set(all_refs)
            target_sops|={x for x in roi_or_other_sops if sop_index[x][0].get("series")==mr_uid}
            if not target_sops: reasons["MR_HAS_NO_DIRECT_SOP_REFERENCE"]+=1; continue
            chain_ok=True
            studies={c.get("study") for c in declared if c.get("study")}
            for sop in target_sops:
                hit=sop_index[sop][0]
                if hit.get("series")!=mr_uid or hit.get("patient")!=rt_patient:
                    chain_ok=False; break
                if studies and hit.get("study") not in studies:
                    chain_ok=False; break
            gate=candidate_pair_gate(meta["count"],len(mr["sops"]),rt_expected["count"],len(rt_s["sops"]),
                ref_resolution["complete"],len(mr["patients"])==1 and next(iter(mr["patients"]))==rt_patient,
                bool(target_sops) and chain_ok)
            if not gate["eligible"]: reasons[gate["reason"]]+=1; continue
            contexts_for_mr=[c for c in declared if c.get("series")==mr_uid]
            frame_status=_series_frame_status(mr,contexts_for_mr)
            mr_patient=next(iter(mr["patients"]))
            candidates.append({"rt_record":rt_rec,"rt_series":rt_series,"mr_series":mr_uid,
                "mr_patient":mr_patient,"rt_patient":rt_patient,"mr":mr,"rt":rt_s,
                "refs":rt["refs"],"target_sop_count":len(target_sops),"all_ref_count":len(all_refs),
                "frame_status":frame_status,"t2_text_candidate":_text_t2(mr),
                "mr_file_count":len(mr["files"]),"rt_file_path":rt_rec["path"],
                "mr_files":sorted(mr["files"]),"rt_study":rt_rec.get("study"),
                "chronology_rank":None})
            eligible_this_rt.append(mr_uid)
        if eligible_this_rt: counts["rtstruct_with_complete_mr_pair"]+=1
    # Deduplicate each RT/MR pair, then rank T2 text, same frame, smaller local file count, fewer refs.
    unique={}
    for c in candidates: unique[(c["rt_series"],c["mr_series"])]=c
    candidates=list(unique.values())
    candidates.sort(key=lambda c:(not c["t2_text_candidate"],c["frame_status"]!="SAME_FRAME_REFERENCE",
                                  c["mr_file_count"],c["all_ref_count"],c["rt_series"],c["mr_series"]))
    counts["complete_pair_count"]=len(candidates)
    counts["t2_text_pair_count"]=sum(c["t2_text_candidate"] for c in candidates)
    counts["same_frame_pair_count"]=sum(c["frame_status"]=="SAME_FRAME_REFERENCE" for c in candidates)
    return candidates[:3],dict(counts),dict(reasons)



def _private_patient_tree(scan: dict, expected: dict, join: dict, ranks: dict) -> list[dict]:
    result=[]
    for patient in sorted({p for s in scan["series"].values() for p in s["patients"]}):
        matched=patient in join["mapping"]
        studies={}
        for uid,s in scan["series"].items():
            if patient not in s["patients"] or len(s["studies"])!=1: continue
            study=next(iter(s["studies"]))
            meta=expected.get(uid)
            studies.setdefault(study,[]).append({"series_uid":uid,
                "modality":sorted(s["modalities"])[0] if s["modalities"] else None,
                "local_unique_sop_count":len(s["sops"]),
                "official_expected_instance_count":meta["count"] if meta else None,
                "count_status":count_relation(meta["count"],len(s["sops"])) if meta else "NOT_IN_FIXED_INDEX"})
        study_rows=[]
        for study,series_rows in studies.items():
            study_rows.append({"study_uid":study,"chronology_rank":ranks.get((patient,study)),
                               "chronology_basis":"DICOM date/time ordering only",
                               "series":sorted(series_rows,key=lambda x:(x["modality"] or "",x["series_uid"]))})
        result.append({"dicom_patient_id":patient,"clinical_key_exact_match":matched,
                       "clinical_key":patient if matched else None,
                       "grouping_status":"GROUPING_UNVERIFIED",
                       "studies":sorted(study_rows,key=lambda x:(x["chronology_rank"] is None,x["chronology_rank"] or 0,x["study_uid"]))})
    return result

def _write_private_outputs(private: Path, scan: dict, expected: dict, join: dict, ranks: dict,
                           candidates: list[dict], candidate_counts: dict, ref_stats: dict) -> None:
    mapping=[]
    for key in join["matched_keys"]:
        mapping.append({"clinical_key":key,"dicom_patient_id":join["mapping"][key],
                        "status":"KEY_STRING_EXACT_MATCHED","source_semantics":"UNCONFIRMED",
                        "clinical_image_join_authorized":False})
    for key in join["unmatched_keys"]:
        mapping.append({"clinical_key":key,"dicom_patient_id":None,"status":"UNMATCHED_EXACT_STRING",
                        "source_semantics":"UNCONFIRMED","clinical_image_join_authorized":False})
    for key in join["ambiguous_keys"]:
        mapping.append({"clinical_key":key,"dicom_patient_id":None,"status":"AMBIGUOUS_EXACT_STRING",
                        "source_semantics":"UNCONFIRMED","clinical_image_join_authorized":False})
    private_join={"task_id":TASK,"plan_revision":REVISION,"clinical_file_sha256":EXPECTED_CLINICAL_SHA,
                  "source_index_release":"25.0.0","source_index_version":EXPECTED_INDEX_VERSION,
                  "exact_join_counts":{"clinical_keys":join["clinical_key_count"],"dicom_patient_ids":join["dicom_id_count"],
                   "matched":len(join["matched_keys"]),"unmatched":len(join["unmatched_keys"]),
                   "ambiguous":len(join["ambiguous_keys"]),"clinical_duplicate_rows":join["clinical_duplicate_rows"],
                   "dicom_duplicate_rows":join["dicom_duplicate_rows"],"clinical_nonstring":join["clinical_nonstring_count"],
                   "dicom_nonstring":join["dicom_nonstring_count"]},
                  "source_semantics":"UNCONFIRMED","clinical_image_join_authorized":False,
                  "patient_key_records":mapping,"dicom_patient_study_series_index":_private_patient_tree(scan,expected,join,ranks),
                  "grouping_status":"GROUPING_UNVERIFIED","timepoint_evidence":"CHRONOLOGY_ONLY"}
    (private/"private_patient_join.json").write_text(json.dumps(private_join,ensure_ascii=False,indent=2),encoding="utf-8")
    selected=[]
    for rank,c in enumerate(candidates,1):
        mr=c["mr"]
        selected.append({"private_rank":rank,"patient_id":c["mr_patient"],
          "mr_series_uid":c["mr_series"],"mr_study_uids":sorted(mr["studies"]),
          "mr_absolute_file_paths":c["mr_files"],"mr_required_file_count":c["mr_file_count"],
          "mr_count_status":"MR_COUNT_MATCHED","t2_text_candidate":c["t2_text_candidate"],
          "t2_heuristic":"HEURISTIC_ONLY","series_description_private":sorted(mr["descriptions"]),
          "protocol_name_private":sorted(mr["protocols"]),"sequence_name_private":sorted(mr["sequence_names"]),
          "frame_relation":c["frame_status"],"referenced_target_sop_count":c["target_sop_count"],
          "all_rt_sop_references_resolved":True,"rtstruct_series_uid":c["rt_series"],
          "rtstruct_study_uid":c["rt_study"],"rtstruct_absolute_file_path":c["rt_file_path"],
          "rtstruct_required_file_count":len(c["rt"]["files"]),"rtstruct_count_status":"RTSTRUCT_PRESENT_COUNT_MATCHED",
          "reference_chain_status":"DIRECT_REFERENCES_RESOLVED",
          "chronology_rank":ranks.get((c["mr_patient"],next(iter(mr["studies"])))) if len(mr["studies"])==1 else None,
          "timepoint_status":"CHRONOLOGY_ONLY","treatment_timepoint":"UNASSIGNED",
          "roi_semantics":"ROI_SEMANTIC_UNRESOLVED","ranking_basis":{
             "t2_text_candidate":c["t2_text_candidate"],"same_frame_reference":c["frame_status"]=="SAME_FRAME_REFERENCE",
             "fewer_mr_files":c["mr_file_count"],"fewer_referenced_sops":c["all_ref_count"]}})
    private_candidates={"task_id":TASK,"plan_revision":REVISION,"maximum_selected":3,
       "candidate_group_count_total":candidate_counts.get("complete_pair_count",0),
       "candidate_groups_selected":len(selected),"reference_audit_private":ref_stats,
       "candidates":selected,"patient_grouping":"GROUPING_UNVERIFIED",
       "pixel_and_spatial_qc":"NOT_RUN","contour_coordinate_values_read":0,
       "roi_semantics":"ROI_SEMANTIC_UNRESOLVED"}
    (private/"private_series_candidate_index.json").write_text(json.dumps(private_candidates,ensure_ascii=False,indent=2),encoding="utf-8")

def _disclosure_counts(items: dict[str,int]) -> dict[str,Any]:
    if any(v<5 for v in items.values()):
        return {k:{"value":None,"status":"SUPPRESSED_LT5_OR_COMPLEMENT"} for k in items}
    return {k:{"value":v,"status":"REPORTED"} for k,v in items.items()}

def _public_profile(clinical: dict, scan: dict, reconcile: dict, join: dict|None,
                    rt_parse: dict, candidates: list, candidate_counts: dict, reasons: dict,
                    duration: float, status: str) -> dict[str,Any]:
    clin_keep={k:clinical.get(k) for k in ("status","file_bytes","sha256","python","openpyxl","sheet_count",
      "named_field_count","nonempty_rows","keyed_rows","key_string_values","key_distinct_values",
      "unkeyed_single_cell_rows","single_cell_types","same_nonkey_column_category","single_cell_column_category","contiguous_tail_block",
      "distinct_style_from_keyed_rows","singleton_formula_count","singleton_comment_count","singleton_merged_count",
      "explicit_marker_count","internal_codebook_marker_count","row_shape_histogram","candidate_key_column_count","key_field_selection",
      "candidate_key_type_counts","key_duplicate_rows","endpoint_codebook","role","cmrl07_regression_match")}
    join_public={"status":"JOIN_UNVERIFIED","clinical_candidate_key_count":clinical.get("key_distinct_values"),
      "dicom_patient_id_count":scan.get("patient_id_count"),"source_semantics":"UNCONFIRMED",
      "clinical_image_join_authorized":False,"counts":_disclosure_counts({
       "matched":len(join["matched_keys"]) if join else 0,
       "unmatched":len(join["unmatched_keys"]) if join else int(clinical.get("key_distinct_values",0) or 0),
       "ambiguous":len(join["ambiguous_keys"]) if join else 0})}
    if join and join["matched_keys"]: join_public["status"]="KEY_STRING_EXACT_MATCHED"
    if join and join["ambiguous_keys"]: join_public["status"]="JOIN_AMBIGUOUS_UNVERIFIED"
    pairs=candidate_counts.get("complete_pair_count",0)
    t2=candidate_counts.get("t2_text_pair_count",0)
    candidate_status="NO_SAFE_CANDIDATE" if pairs==0 else ("CANDIDATES_FOUND_COUNT_SUPPRESSED_LT5" if pairs<5 else "CANDIDATES_FOUND")
    t2_status="NONE" if t2==0 else ("T2_CANDIDATES_COUNT_SUPPRESSED_LT5" if t2<5 else "T2_CANDIDATES_FOUND")
    rtrefs={"parsed_rtstruct_count":rt_parse.get("parsed_count",0),
      "parse_error_count":rt_parse.get("parse_error_count",0),
      "oversize_skipped_count":rt_parse.get("oversize_skipped_count",0),
      "unique_direct_sop_reference_count":rt_parse.get("unique_reference_count",0),
      "matched_unique_reference_count":rt_parse.get("matched_reference_count",0),
      "unmatched_unique_reference_count":rt_parse.get("unmatched_reference_count",0),
      "ambiguous_unique_reference_count":rt_parse.get("ambiguous_reference_count",0),
      "coordinate_value_bytes_read":rt_parse.get("coordinate_value_bytes_read",0),
      "coordinate_value_bytes_skipped":rt_parse.get("coordinate_value_bytes_skipped",0),
      "cmrl05_unmatched_reference_baseline":61,
      "cmrl05_reference_count_reconciled":rt_parse.get("unmatched_reference_count")==61}
    return {"task_id":TASK,"plan_revision":REVISION,"status":status,
      "generated_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
      "source_versions":{"idc_release":"25.0.0","idc_index_data_version":EXPECTED_INDEX_VERSION,
        "idc_index_sha256":EXPECTED_INDEX_SHA,"collections_index_sha256":EXPECTED_COLLECTIONS_SHA,
        "clinical_version":"Version 2 (separate version track)","clinical_file_bytes":EXPECTED_CLINICAL_BYTES,
        "clinical_sha256":EXPECTED_CLINICAL_SHA},
      "runtime":{"python":scan.get("runtime",{}).get("python"),"pydicom":scan.get("runtime",{}).get("pydicom"),
        "openpyxl":clinical.get("openpyxl"),"clinical_python":clinical.get("python"),
        "duckdb":scan.get("duckdb_version"),"header_scan_elapsed_seconds":scan.get("elapsed_seconds"),
        "combined_audit_elapsed_seconds":round(duration,3),"network_requests":0},
      "input_snapshot":{"file_count":scan.get("snapshot_before",{}).get("file_count"),
        "total_bytes":scan.get("snapshot_before",{}).get("total_bytes"),
        "directory_count":scan.get("snapshot_before",{}).get("directory_count"),
        "zero_byte_file_count":scan.get("snapshot_before",{}).get("zero_byte_file_count"),
        "dicom_candidate_count":scan.get("snapshot_before",{}).get("dicom_candidate_count"),
        "reparse_or_symlink_entries_skipped":scan.get("snapshot_before",{}).get("reparse_or_symlink_entries_skipped"),
        "special_entry_count":scan.get("snapshot_before",{}).get("special_entry_count"),
        "metadata_error_count_before":scan.get("snapshot_before",{}).get("metadata_error_count"),
        "metadata_error_count_after":scan.get("snapshot_after",{}).get("metadata_error_count") if scan.get("snapshot_after") else None,
        "snapshot_before_after_equal":scan.get("snapshots_equal")},
      "clinical_extra_rows_profile":clin_keep,
      "patient_key_join_status":join_public,
      "series_count_reconciliation":reconcile,
      "rtstruct_reference_profile":rtrefs,
      "mr_rtstruct_candidate_counts":{"status":candidate_status,"complete_pair_count":None if pairs<5 else pairs,
        "candidate_unit":"unique MR Series–RTSTRUCT Series pairs; not unique patients",
        "t2_text_candidate_status":t2_status,"selected_private_candidate_count":len(candidates) if len(candidates)>=5 else None,
        "selected_private_candidate_count_status":"REPORTED" if len(candidates)>=5 else ("SUPPRESSED_LT5_PRIVATE_INDEX_EXISTS" if candidates else "NONE"),
        "private_candidate_index_generated":bool(candidates),"count_suppression":"counts below 5 and complements are withheld"},
      "timepoint_evidence_grade":{"status":"CHRONOLOGY_ONLY","treatment_timepoint":"UNASSIGNED",
        "grouping":"GROUPING_UNVERIFIED","deidentified_date_shift_warning":True},
      "roi_semantic_status":"ROI_SEMANTIC_UNRESOLVED",
      "task_gates":{"single_case_mri_pixel_spatial_qc":"CANDIDATE" if candidates else "CONDITIONAL",
        "3d_tumor_segmentation":"NO-GO","volume_radiomics_habitat":"NO-GO",
        "longitudinal_treatment_change":"NO-GO","response_recurrence_dfs_os":"NO-GO"},
      "limits":{"pixel_data_read":False,"contour_data_value_read":False,"contour_data_bytes_read":0,
        "treatment_timepoint_verified":False,"clinical_outcomes_created":False,"roi_semantics_changed":False,
        "clinical_image_join_authorized":False,"r0":"NOT COMPLETE",
        "candidate_failure_reason_counts_private_only":True},
      "scan_status":{"parsed_header_count":scan.get("parsed_file_count"),"parse_error_count":sum(scan.get("parse_error_classes",{}).values()),
        "parse_error_classes":scan.get("parse_error_classes",{}),"missing_patient_id_count":scan.get("missing_patient"),
        "missing_study_uid_count":scan.get("missing_study"),"missing_series_uid_count":scan.get("missing_series"),
        "missing_sop_uid_count":scan.get("missing_sop"),"file_modalities":dict(sorted(scan.get("modalities",{}).items())),
        "stop_reason":scan.get("stop_reason"),"baseline_status":reconcile.get("status")},
      "privacy":{"patient_keys_uids_paths_dates_series_text_and_clinical_values_excluded":True,
        "public_evidence_is_aggregate_only":True}}

def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    os.replace(tmp,path)

def run_scan(args) -> int:
    begin=time.monotonic(); repo=args.repo.resolve(strict=True); private=args.private
    safe_private_dir(repo,private)
    expected,gap_doc=official_expected(args.index,args.collections,args.gaps)
    clinical_summary=json.loads((private/"clinical_summary.json").read_text(encoding="utf-8"))
    clinical_keys=json.loads((private/"clinical_key_values.json").read_text(encoding="utf-8"))
    # Validate the input root by exact resolved path before touching the dataset.
    authorized=Path("D:/CS/CMRL/data/raw/tcia/ccth_idc_v25_full")
    if args.root.resolve(strict=True)!=authorized.resolve(strict=True):
        raise RuntimeError("raw data root does not match Plan")
    scan=scan_headers(args.root,repo)
    import duckdb
    scan["duckdb_version"]=duckdb.__version__
    reconcile=reconcile_series(scan,expected,gap_doc)
    rt_results=[]; rt_classes=collections.Counter(); ref_uids=set(); coord_read=0; coord_skipped=0; rt_budget_cut=False
    for rec in scan.get("rtstruct_files",[]):
        if time.monotonic()-begin>=MAX_SECONDS: rt_budget_cut=True; break
        if rec["size"]>MAX_RT_BYTES:
            rt_classes["oversize_skipped"]+=1; continue
        try:
            parsed=parse_rtstruct_references(Path(rec["path"]))
            if parsed["coordinate_value_bytes_read"]!=0: raise RuntimeError("contour value was read")
            coord_read+=parsed["coordinate_value_bytes_read"]; coord_skipped+=parsed["coordinate_value_bytes_skipped"]
            ref_uids.update(parsed["sop_refs"]); rt_results.append({"record":rec,"refs":parsed})
        except Exception as exc: rt_classes[type(exc).__name__]+=1
    matched=sum(1 for uid in ref_uids if len(scan["sop_index"].get(uid,[]))==1)
    ambiguous=sum(1 for uid in ref_uids if len(scan["sop_index"].get(uid,[]))>1)
    unmatched=sum(1 for uid in ref_uids if not scan["sop_index"].get(uid))
    rt_parse={"parsed_count":len(rt_results),"parse_error_count":sum(v for k,v in rt_classes.items() if k!="oversize_skipped"),
      "oversize_skipped_count":rt_classes["oversize_skipped"],"parse_error_classes":dict(rt_classes),
      "unique_reference_count":len(ref_uids),"matched_reference_count":matched,
      "unmatched_reference_count":unmatched,"ambiguous_reference_count":ambiguous,
      "coordinate_value_bytes_read":coord_read,"coordinate_value_bytes_skipped":coord_skipped}
    expected_clinical_hist={"1":5,"6":15,"8":5,"9":3}
    clinical_ok=(clinical_summary.get("sha256")==EXPECTED_CLINICAL_SHA and clinical_summary.get("file_bytes")==EXPECTED_CLINICAL_BYTES
      and clinical_summary.get("nonempty_rows")==28 and clinical_summary.get("keyed_rows")==23
      and clinical_summary.get("key_distinct_values")==23 and clinical_summary.get("unkeyed_single_cell_rows")==5
      and clinical_summary.get("row_shape_histogram")==expected_clinical_hist
      and clinical_summary.get("candidate_key_type_counts")=={"str":23} and clinical_summary.get("key_duplicate_rows")==0)
    clinical_summary["cmrl07_regression_match"]=bool(clinical_ok)
    can_continue=(clinical_ok and reconcile.get("baseline_consistent") and len(rt_results)==len(scan.get("rtstruct_files",[]))
                  and not rt_budget_cut and coord_read==0 and unmatched==61 and ambiguous==0 and scan.get("snapshots_equal"))
    join=exact_join(clinical_keys.get("keys",[]),sorted({p for s in scan["series"].values() for p in s["patients"]}))
    candidates=[]; pair_counts={}; failure_reasons={}
    ranks=chronology_ranks(scan["series"])
    if can_continue:
        candidates,pair_counts,failure_reasons=select_candidates(scan,expected,rt_results)
        for c in candidates:
            c["chronology_rank"]=ranks.get((c["mr_patient"],next(iter(c["mr"]["studies"])))) if len(c["mr"]["studies"])==1 else None
        _write_private_outputs(private,scan,expected,join,ranks,candidates,pair_counts,
            {"parse":rt_parse,"failure_reasons":failure_reasons})
    else:
        pair_counts={"complete_pair_count":0,"t2_text_pair_count":0}
        failure_reasons={"BASELINE_OR_REFERENCE_STOP":1}
    overall="COMPLETE" if can_continue else "PARTIAL"
    profile=_public_profile(clinical_summary,scan,reconcile,join,rt_parse,candidates,pair_counts,
                            failure_reasons,time.monotonic()-begin,overall)
    profile["mr_rtstruct_candidate_counts"]["complete_pair_count"]=(
        None if 0<pair_counts.get("complete_pair_count",0)<5 else pair_counts.get("complete_pair_count",0))
    profile["mr_rtstruct_candidate_counts"]["selected_private_candidate_count"]=(
        None if 0<len(candidates)<5 else len(candidates))
    profile["candidate_failure_reason_categories"]=sorted(set(failure_reasons)) if not can_continue else ["DETAILS_PRIVATE"]
    scan_private_values=set(x for x in clinical_keys.get("keys",[]) if isinstance(x,str))
    for recs in scan.get("sop_index",{}).values():
        for rec in recs:
            scan_private_values.update(x for x in (rec.get("patient"),rec.get("study"),rec.get("series"),rec.get("sop"),rec.get("frame"),rec.get("path")) if isinstance(x,str))
    for s in scan.get("series",{}).values():
        for field in ("descriptions","protocols","sequence_names","study_dates","study_times","series_dates","series_times","acq_dates","acq_times"):
            scan_private_values.update(x for x in s.get(field,set()) if isinstance(x,str))
    privacy_hits=private_value_hits(profile,scan_private_values)
    if privacy_hits: raise RuntimeError("public serialization contains private value")
    _atomic_json(args.profile,profile)
    # Delete scratch key and Clinical aggregates after embedding only safe facts in public output/private join.
    for name in ("clinical_key_values.json","clinical_summary.json"):
        p=private/name
        if p.exists(): p.unlink()
    selected_label="NONE" if not candidates else "SUPPRESSED_LT5" if len(candidates)<5 else str(len(candidates))
    print(f"AUDIT_STATUS={overall} headers={scan.get('parsed_file_count',0)} rtstruct_parsed={len(rt_results)} candidates_selected={selected_label} elapsed_s={round(time.monotonic()-begin,1)}")
    return 0 if overall=="COMPLETE" else 2

def main() -> int:
    parser=argparse.ArgumentParser(description="Private metadata-only CMRL-08 crosswalk and candidate audit.")
    sub=parser.add_subparsers(dest="phase",required=True)
    c=sub.add_parser("clinical")
    c.add_argument("--repo",type=Path,required=True); c.add_argument("--data-root",type=Path,required=True)
    c.add_argument("--private",type=Path,required=True)
    d=sub.add_parser("scan")
    for name in ("repo","root","private","index","collections","gaps","profile"): d.add_argument("--"+name,type=Path,required=True)
    args=parser.parse_args()
    try:
        if args.phase=="clinical":
            safe_private_dir(args.repo,args.private)
            p=prepare_clinical(args.data_root,args.repo,args.private)
            print(f"CLINICAL_PREPARED rows={p['nonempty_rows']} keys={p['key_distinct_values']} singleton_rows={p['unkeyed_single_cell_rows']} sha256_verified=true")
            return 0
        return run_scan(args)
    except Exception as exc:
        # Never print exception messages: they can contain paths or source values.
        print(f"AUDIT_ABORTED error_class={type(exc).__name__}")
        return 1

if __name__=="__main__":
    raise SystemExit(main())
