# CMRL-12｜真实单例 MRI–RTSTRUCT 像素、几何与 Mask 质控

- **任务范围：** 用户提供的 CMRL-Lab 单例质控任务；本文件是隐私审查后的汇总，不复制外部 Plan 或本地候选索引。
- **任务状态：** 首个候选的工程质控完成；按要求停止，不扩展到其他候选。
- **研究状态：** `R0 NOT COMPLETE`；未修改研究总控状态，不确认任何医学 ROI 语义。
- **分支：** `codex/cmrl-12-real-mri-rtstruct-qc`。

## 本次处理与边界

从 CMRL-08 已有的忽略区候选索引中选择了一组本地文件数匹配、直接 SOP 引用链完整的 MR Series–RTSTRUCT 组合。没有重做全库扫描、下载或其他病例的读取。原始 DICOM 以只读方式使用；Slicer DICOM 临时数据库位于忽略区，并以 `copyFiles=False` 建库。只使用本机已有的 3D Slicer 5.12.4、SlicerRT 与随附 Python 依赖；没有安装软件或扩展。

病例标识、UID、源路径、原始 ROI 名称及对应关系、精确数组/几何数值、MRI、Mask、文件级 Manifest 和日志均保存在本地忽略目录 `.local/cmrl-12/`，没有进入 Git。

## 验收状态

| 项目 | 状态 | 实际结果与判据 |
|---|---|---|
| `PIXEL_QC` | **PASS** | Slicer 导入并解码选定 MR Series 的全部预期切片；三维数组维度与切片/行/列计数一致，dtype 与有限像素统计已写入本地私有 QC。没有像素解码异常。精确 shape 和数值仅见本地 QC。 |
| `GEOMETRY_QC` | **FAIL** | ImagePositionPatient 沿切片法向的中心间距不均匀，含一个显著大间隙；DICOM `SliceThickness`、`SpacingBetweenSlices` 与实测中心间距不能互相替代。Slicer 将输入导入为均匀网格，但逐层 IPP 映射不能在既定容差内一一对应，故这个 Volume 不可作为已验证的规则三维几何。无重复中心；方向余弦和面内位置漂移检查未发现相应异常。 |
| `RTSTRUCT_ALIGNMENT_QC` | **FAIL** | RTSTRUCT 与 MR 的 Frame of Reference 相同；DICOM 层级引用及轮廓到具体 MR SOP 的直接引用均可解析，轮廓平面残差和图像内边界检查通过。失败原因在于 Slicer 导入的均匀 Volume 几何不能代表全部原始切片中心，因此不能验收轮廓到该三维 Volume 的可靠空间叠加。没有应用 REG。 |
| `MASK_QC` | **FAIL** | SlicerRT 成功载入结构并通过 Segmentations API 导出非空逐 ROI Labelmap；文件 shape 与 Slicer 导入网格一致。但该网格未通过几何验收，故这些 Mask 只证明转换和写盘成功，不构成空间可靠的 Mask。Slicer 未找到 RTSTRUCT segmentation 容器写入器；逐 ROI Labelmap 已分别保存。 |
| `ROI_SEMANTIC_QC` | **PENDING** | 未找到可将本病例发布版 `ROINumber`/`ROIName`/观察记录映射到原发宫颈肿瘤的权威逐 ROI crosswalk。保留本地名称及来源映射，不将任何 ROI 认定为肿瘤。 |

### 几何与引用解释

- 几何判据在本地 JSON 中完整记录：重复位置容差、方向余弦容差、轮廓平面残差容差、中心间距容差及 IJK→RAS 矩阵容差。报告不公开病例级的具体坐标和间距列表。
- 当前病例的图像切片中心间距不等于 `SliceThickness`。`SpacingBetweenSlices` 只是 DICOM 头字段；中心间距按 `ImagePositionPatient` 在法向投影后测量。
- RTSTRUCT 的 DICOM contour 引用经私有 SOP 映射逐个核对。SlicerRT reader 的参考 UID getter 按其实现按 ROI 遍历更新，因此按单 ROI 引用集合对照，未误将单 ROI 返回值当成整个结构集的 UID 并集。
- `RTSTRUCT_ALIGNMENT_QC=FAIL` 并不表示 DICOM 层级或 Frame of Reference 不一致；它表示轮廓无法在当前失败的均匀 Volume 几何上完成可接受的空间叠加。

## 本地检查材料

以下均在 `.local/cmrl-12/`，受忽略规则保护，不应上传：

- `private/mr_volume.nrrd`：Slicer 解码并保存的三维 Volume；几何状态仍为 FAIL。
- `private/mask_roi_*.nrrd`：逐 ROI Labelmap；仅是失败几何网格上的工程转换结果。
- `private/quality_qc.json`：完整私有记录，含病例标识、UID、ROI 原名/映射、精确 shape/几何、每个 Mask 的统计及源路径。
- `private/selected_case.json`：本次单例的私有文件级输入清单。
- `visuals/source_dicom_contours.png`：按原始 DICOM 像素、IPP/IOP/PixelSpacing 与引用 SOP 绘制的代表性源切片轮廓图。
- `visuals/native_k.png`、`native_j.png`、`native_i.png`：Slicer 导入网格上 MRI 与 Labelmap 的三个原生 IJK 正交视图。由于几何失败，这些图只用于排查，不代表真实患者空间通过。
- `visuals/README.txt`：本地图片用途和限制。

没有把原始 DICOM 轮廓与导出 Mask 叠在同一源切片图上，因为当前 Slicer 网格不能可靠映射所有源切片中心；强行合成会制造错误的空间对应印象。

## ROI 医学语义证据

TCIA 当前 Collection 页面描述发布集包含基于 T2 MRI 的肿瘤体积轮廓；Bowen 等论文描述参考矢状 T2 上分别勾画 tumor 与 uterus，且 uterus 用于辅助对齐。这些来源没有给出本地发布 RTSTRUCT 中每个 ROI 编号/名称到上述结构的权威映射。[TCIA Collection](https://www.cancerimagingarchive.net/collection/cc-tumor-heterogeneity/)、[Bowen et al. 2018 全文](https://pmc.ncbi.nlm.nih.gov/articles/PMC5899626/)。既有 [CMRL-07](../../docs/project/HISTORY_ARCHIVE.md#按任务查找) 与 [CMRL-09](../../docs/project/HISTORY_ARCHIVE.md#按任务查找) 审计也未找到该 crosswalk，因此维持 `SEMANTIC_PENDING`。

## 最小复现

从仓库根目录的 PowerShell 会话运行；将 `<Slicer.exe>` 替换为已有 Slicer 5.12.4 可执行文件路径。Manifest 已在本地忽略目录内，不需要把病例路径或 UID 写入命令行：

```powershell
$env:CMRL_SINGLETON_MANIFEST = (Resolve-Path '.local/cmrl-12/private/selected_case.json').Path
$env:CMRL_SINGLETON_OUTDIR = (Resolve-Path '.local/cmrl-12').Path
& '<Slicer.exe>' --no-splash --no-main-window --python-script (Resolve-Path 'scripts/r0/qc_mri_rtstruct_singleton.py').Path
```

`qc_mri_rtstruct_singleton.py` 是通用辅助脚本；图像、病例清单和实际运行结果不在脚本中。脚本使用临时 DICOM DB 的 `copyFiles=False` 模式，并用 SlicerRT 与官方 Segmentations 导出 API 执行轮廓读取/栅格化。[Slicer Segmentations API](https://github.com/Slicer/Slicer/blob/main/Docs/developer_guide/script_repository/segmentations.md)、[SlicerRT reader implementation](https://github.com/SlicerRt/SlicerRT/blob/master/DicomRtImportExport/Logic/vtkSlicerDicomRtReader.cxx)。

## 停止条件与剩余阻塞

仅完成这一组候选后停止。开展可靠三维 Mask 工作前，至少需由 Lab 审查原始切片中心的大间隙及本地视觉材料，并厘清该 Series 的不规则采样/间隙是否符合预期；同时仍需官方逐 ROI 语义映射。当前不进行第二组候选、肿瘤分割训练、模型评价或 R0 推进。
