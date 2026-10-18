# TCIA CCTH 本地数据集目录索引与路径合同

- **任务：** CMRL-11；索引器版本 `1.0.0`；Manifest schema `1.0.0`。
- **扫描时间：** `2026-10-18T13:16:30+08:00`（本机时区）。
- **扫描根目录：** `data/raw/tcia/ccth_idc_v25_full/cc_tumor_heterogeneity`（仓库相对路径）。
- **文件系统索引：** 完整遍历；DICOM Header 成功 `130,424/130,424`。
- **来源状态：** 本地目录为用户指定的已下载数据；IDC Release 25.0.0 数量作为 CMRL-06 官方索引对照，不据此宣称本地对象级完整。

## 扫描结果

目标树包含 **130,424 个普通文件**、**28,151,425,416 bytes（26.218 GiB）**、**1,016 个目录（含扫描根）**。扩展名：.dcm=130,424。零字节 `0`；非普通特殊项 `0`；reparse 项 `0`；目录/元数据读取错误 `0`；重复 basename 组 `0`。

本轮读取标准 DICOM Header 的选定标签，`stop_before_pixels=True`，未使用 `force=True`。未解码 PixelData、未读取临床表、未计算文件内容哈希、未安装依赖，也未写入原始数据目录。

### 真实目录层级

脱敏树保留公开病例别名；Study、Series、Instance 的实际 UID 仅保存在本地忽略 Manifest。

```text
cc_tumor_heterogeneity/
├── A01/ … A12/
│   └── <StudyInstanceUID>/
│       └── <Modality>_<SeriesInstanceUID>/
│           └── <UUID>.dcm
└── B01/ … B11/（同一层级）
```

扫描到 `23` 个病例目录，其中预期别名目录 `23/23`；缺失别名 `无`；意外顶层目录 `0`；未映射到 A01–B11 的文件 `0`。另有 `171` 个 Study 目录、`821` 个 Series 目录，最大目录深度为根目录下 `3` 层；空 Series 目录 `15`。目录计数描述实际路径结构；Series/Study UID 和文件名与 Header 的匹配率见下表。

| 文件路径/Header 核对 | 命中 / 可核对 |
|---|---:|
| Study 目录名 = StudyInstanceUID | 130,424 / 130,424 |
| Series 目录名 = SeriesInstanceUID（无模态前缀） | 0 / 130,424 |
| Series 目录名 = Modality_SeriesInstanceUID | 130,424 / 130,424 |
| 文件 stem = SOPInstanceUID | 0 / 130,424 |
| 文件 stem 为 UUID 格式 | 130,424 / 130,424 |

实际命名规律：Study 文件夹名与 Header 的 StudyInstanceUID 相同；Series 文件夹名为 DICOM Modality、下划线和 SeriesInstanceUID；Instance 文件名是 UUID 形态并以 `.dcm` 结尾，与 SOPInstanceUID 字符串不相等。UID 与精确文件路径的连接来自 Header 索引，不应按 SOP UID 拼文件名。

### 模态与 Study/Series/Instance 统计

| Modality | Header 文件数 | 唯一 SOP Instance 数 | Series 组数 | 容量（GiB） |
|---|---:|---:|---:|---:|
| CT | 21,637 | 21,637 | 65 | 10.639 |
| MR | 92,508 | 92,508 | 523 | 14.647 |
| PT | 16,129 | 16,129 | 68 | 0.915 |
| REG | 87 | 87 | 87 | 0.007 |
| RTSTRUCT | 63 | 63 | 63 | 0.010 |
| UNKNOWN | 0 | 0 | 0 | 0.000 |
| **合计文件** | **130,424** | **130,424** | **806** | **26.218** |

Header 解析失败 `0`；缺 Study UID `0`、Series UID `0`、SOP Instance UID `0`；重复 SOP UID 组 `0`，跨 Study/Series/case 冲突组 `0`。

| 图像模态 | Rows/Columns/PixelSpacing/Orientation/Position 等字段的 Header 覆盖 | Header-only Volume 候选分类 |
|---|---|---|
| MR | rows: 92,508/92,508; columns: 92,508/92,508; pixel_spacing: 92,508/92,508; orientation: 92,508/92,508; position: 92,508/92,508 | HEADER_GEOMETRY_INCOMPLETE_OR_INCONSISTENT=49; MULTISLICE_HEADER_CANDIDATE=474 |
| CT | rows: 21,637/21,637; columns: 21,637/21,637; pixel_spacing: 21,637/21,637; orientation: 21,637/21,637; position: 21,637/21,637 | MULTISLICE_HEADER_CANDIDATE=65 |
| PT | rows: 16,129/16,129; columns: 16,129/16,129; pixel_spacing: 16,129/16,129; orientation: 16,129/16,129; position: 16,129/16,129 | MULTISLICE_HEADER_CANDIDATE=68 |

Volume 分类只根据 Header 中的维度、spacing、方向和位置字段标记候选；没有检查切片连续性、实际像素、配准、空间叠加或影像质量，不能据此称为通过医学空间质控的体数据。REG 与 RTSTRUCT 按独立 DICOM Series/Instance 计数，不作为图像 Volume。

### 每个病例目录汇总

病例标识在公开报告中缩写为公开别名 A01–A12、B01–B11；以下均为本机目录文件聚合数，不含 Study/Series/SOP UID、采集日期或临床字段。

| 病例别名 | 文件数 | 容量（GiB） | Study 目录 | Series 目录 | 空 Series 目录 | Header Studies | Header Series 组 | MR | CT | PT | REG | RTSTRUCT | 未分类 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A01 | 6,390 | 1.114 | 30 | 66 | 0 | 30 | 66 | 4,770 | 890 | 697 | 30 | 3 | 0 |
| A02 | 6,224 | 1.106 | 6 | 33 | 0 | 6 | 33 | 4,655 | 907 | 656 | 3 | 3 | 0 |
| A03 | 6,222 | 1.111 | 7 | 35 | 0 | 7 | 35 | 4,650 | 919 | 645 | 5 | 3 | 0 |
| A04 | 6,129 | 1.088 | 6 | 33 | 0 | 6 | 33 | 4,549 | 896 | 678 | 3 | 3 | 0 |
| A05 | 6,097 | 1.087 | 7 | 33 | 0 | 7 | 33 | 4,480 | 909 | 702 | 3 | 3 | 0 |
| A06 | 3,899 | 0.710 | 5 | 22 | 0 | 5 | 22 | 3,036 | 578 | 281 | 2 | 2 | 0 |
| A07 | 6,095 | 1.076 | 6 | 33 | 2 | 6 | 31 | 4,490 | 909 | 692 | 2 | 2 | 0 |
| A08 | 5,992 | 1.057 | 6 | 33 | 3 | 6 | 30 | 4,398 | 908 | 683 | 0 | 3 | 0 |
| A09 | 5,985 | 1.079 | 7 | 33 | 2 | 7 | 31 | 4,414 | 915 | 652 | 2 | 2 | 0 |
| A10 | 6,069 | 1.059 | 6 | 33 | 4 | 6 | 29 | 4,522 | 872 | 673 | 0 | 2 | 0 |
| A11 | 5,995 | 1.301 | 6 | 33 | 3 | 6 | 30 | 4,709 | 770 | 513 | 1 | 2 | 0 |
| A12 | 6,620 | 1.436 | 6 | 33 | 1 | 6 | 32 | 4,937 | 949 | 729 | 3 | 2 | 0 |
| B01 | 5,268 | 1.318 | 8 | 37 | 0 | 8 | 37 | 2,977 | 1,453 | 832 | 3 | 3 | 0 |
| B02 | 5,959 | 1.292 | 6 | 39 | 0 | 6 | 39 | 4,334 | 917 | 702 | 3 | 3 | 0 |
| B03 | 5,751 | 1.306 | 6 | 38 | 0 | 6 | 38 | 3,914 | 1,045 | 786 | 3 | 3 | 0 |
| B04 | 5,525 | 1.227 | 7 | 39 | 0 | 7 | 39 | 3,763 | 1,011 | 745 | 3 | 3 | 0 |
| B05 | 4,929 | 1.160 | 7 | 37 | 0 | 7 | 37 | 2,989 | 1,174 | 760 | 3 | 3 | 0 |
| B06 | 5,661 | 1.309 | 6 | 39 | 0 | 6 | 39 | 3,636 | 1,209 | 810 | 3 | 3 | 0 |
| B07 | 5,498 | 1.217 | 8 | 38 | 0 | 8 | 38 | 3,728 | 1,016 | 748 | 3 | 3 | 0 |
| B08 | 5,382 | 1.199 | 6 | 39 | 0 | 6 | 39 | 3,594 | 1,018 | 764 | 3 | 3 | 0 |
| B09 | 5,537 | 1.273 | 6 | 39 | 0 | 6 | 39 | 3,496 | 1,217 | 818 | 3 | 3 | 0 |
| B10 | 5,383 | 1.265 | 6 | 37 | 0 | 6 | 37 | 3,462 | 1,155 | 760 | 3 | 3 | 0 |
| B11 | 3,814 | 0.430 | 7 | 19 | 0 | 7 | 19 | 3,005 | 0 | 803 | 3 | 3 | 0 |

### 差异与证据等级

- **当前本地事实（`FILE-INSPECTED`）：** `130,424` 个文件、`28,151,425,416` bytes、Header 解析 `130,424`；Header 有 `171` 个 Study UID、`806` 个 Series UID、`130,424` 个 SOP Instance UID。
- **与 CMRL-05 本机审计对照：** 旧报告记录 `130,424` 个文件、`28,151,425,416` bytes、`806` 个 Header Series；本次文件数差 `+0`、容量差 `+0` bytes、Series UID 数差 `+0`。旧审计从外层目录计数，多计一层根目录；当前只扫描用户指定的子目录。
- **IDC v25.0.0 官方参考（沿用 CMRL-06）：** `821` 个 Series、`131,556` 个 Instance；本次 Header 识别 `806` 个 Series、`130,424` 个唯一 Instance，差值分别 `-15` 和 `-1,132`。先前按官方 Series 映射的本地对账记录 15 个 Series、1,132 个 Instance 缺口；本报告不将空目录逐一映射为这些官方缺口。
- **完整性边界：** 目录 Manifest 覆盖扫描到的实际文件；官方 Series/Instance 对照为数量级差异，不验证对象字节、像素可解码性、Volume 几何、ROI 语义或 CCTH 收录成员身份。官方预期、前序 IDC 映射与本地实际扫描是不同证据层。

## 本地完整 Manifest 与字段说明

以下文件仅保存在 Git 忽略的 `.local/dataset-index/`，包含精确相对路径和 UID；不得提交或复制到公开报告。

| 文件 | 粒度与用途 |
|---|---|
| `files.csv` | 每个普通文件一行；相对路径、大小、Header 状态、Modality、Study/Series/SOP/Frame UID、实例号、图像维度/spacing/orientation/position、UID 与目录名匹配标志。 |
| `directories.csv` | 每个目录一行；相对路径、深度、目录层级类型、直接/递归文件数与容量、空目录及读取错误。 |
| `studies.csv` | 每个 case alias + Study UID 一行；Series 组数、文件/唯一 Instance 数、容量、模态与实际相对目录。 |
| `series.csv` | 每个 case alias + Study UID + Series UID 一行；精确 Series 相对目录、文件与唯一 Instance 数、容量、Header 几何字段一致性及候选状态；若一个 UID 映射多个目录，路径列以 JSON 数组记录。 |
| `cases.csv` | 每个公开病例别名一行；目录、Study/Series 数、容量、模态和空 Series 目录数。 |

关键字段：`relative_path` 可从数据根目录解析；UID 字段按 DICOM 标识 Study、Series、Instance 和 Frame；`modality` 来自 DICOM Header；`rows/columns/number_of_frames/pixel_spacing/image_orientation_patient/image_position_patient` 是 Header 值；`volume_candidate_status` 仅作头信息候选。扫描未读取 PatientName、PatientID、临床工作簿、采集日期、ROI 名称/坐标或像素值。未计算全量文件哈希。

## 统一路径合同

- 仓库根目录：`D:\CS\CMRL`。默认数据集根目录：`data/raw/tcia/ccth_idc_v25_full/cc_tumor_heterogeneity`。
- 如运行环境不同，可用 `CMRL_CCTH_ROOT` 覆盖；路径由 `pathlib.Path` 解析。相对路径只相对于选定的数据根目录解释。
- DICOM UID 是 Study/Series/Instance 的对象标识；Windows 路径是本地文件位置。只有从 `series.csv` 或 `files.csv` 读取并核对 Header 后，才将索引中的相对路径拼到数据根目录。不要假定任意 UID 字符串都能直接拼成有效目录。

```python
import os
from pathlib import Path

repo_root = Path(r"D:\CS\CMRL")
default_root = repo_root / "data" / "raw" / "tcia" / "ccth_idc_v25_full" / "cc_tumor_heterogeneity"
data_root = Path(os.environ.get("CMRL_CCTH_ROOT", str(default_root))).expanduser()
if not data_root.is_dir():
    raise FileNotFoundError(data_root)
case_dir = data_root / "CCTH-A01"
assert case_dir.is_dir()
print(data_root.resolve())
```

`CCTH-A01` 仅用于最小路径存在性示例。具体研究 Series 应先按任务条件查询本地 `series.csv`，再用其 `series_relative_dir` 和 UID/Modality 字段回查 `files.csv`；后续是否进入像素或 ROI 空间检查仍需单独授权与用户验收。

## 可重复生成

在仓库根目录运行 `python scripts/r0/build_ccth_dataset_index.py`；可用 `--data-root` 显式指定本任务目录，或设置 `CMRL_CCTH_ROOT`。脚本默认拒绝覆盖已有输出；确认重建同名索引后使用 `--replace-generated`，只替换本脚本管理的五个本机 Manifest、此 Markdown 与 JSON。脚本不会递归跟随 reparse point。

完整私有索引的文件数与容量经写盘后回读校验；安全 JSON 只保留聚合统计、病例别名与公开路径模板。JSON 中不包含 UID、精确病例路径或患者标识。

## 证据来源与未验证事项

- 本地审计对照：[CMRL-05 全量 DICOM 报告](../../reports/r0/CMRL-05-TCIA全量DICOM准入审计.md)、[CMRL-06 IDC v25 Series/Instance 对账](../../reports/r0/CMRL-06-IDC-v25逐Series及对象完整性补证.md)。
- 官方 Collection/IDC 统计和许可证沿用前序来源核验；本次未请求网络或下载文件。
- 唯一数量、UID/路径匹配及 header 候选不证明 PixelData 可解码、MRI 切片连续、方向正确、RTSTRUCT 可栅格化、ROI 为肿瘤或患者时点/临床标签正确。R0 仍以项目 Main 决定为准；本报告不表示 R0 COMPLETE。
