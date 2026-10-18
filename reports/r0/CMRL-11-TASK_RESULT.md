# TASK_RESULT｜CMRL-11｜TCIA CCTH 本地完整数据集索引

## 状态

**COMPLETE（本地目录与 Header 索引、脱敏报告及 Git 交付范围）**。扫描只建立文件/目录索引并读取指定 DICOM Header 标签；不表示 IDC 对象完整、像素可解码、医学空间质控通过、ROI 可靠或 R0 完成。研究阶段仍为 **R0 NOT COMPLETE**。

## 输入与执行

- **仓库：** `D:\CS\CMRL`；当前任务分支 `codex/cmrl-11-ccth-dataset-index`。
- **本地数据根目录：** 用户指定的 `data/raw/tcia/ccth_idc_v25_full/cc_tumor_heterogeneity`。来源保留为 `USER-REPORTED-SOURCE`；本地索引本身不独立证明每个对象的 Collection 成员关系。
- **既有合同/证据：** 按仓库 `AGENTS.md` 和当前任务合同执行；审阅 CMRL-04 至 CMRL-10 TASK_RESULT/审计报告及 `docs/project/02`、`07`、`08`。官方对照沿用 CMRL-06 固定 IDC Release 25.0.0 结果；本机历史文件清点沿用 CMRL-05。
- **工具：** Python 3.14.6、pydicom 3.0.2（使用本机已有忽略环境/包）；扫描 341.0 秒。没有安装依赖、请求网络、下载数据或计算文件内容哈希。
- **读取边界：** 标准 Header 路径、`stop_before_pixels=True`、`force=False`；只读取 Modality、Study/Series/SOP/Frame UID、实例号、像素维度/spacing/orientation/position、切片间距及 Transfer Syntax。没有读取 PatientName、PatientID、临床工作簿、采集日期或 ROI 值；没有解码 PixelData。
- **原始数据：** 只读访问，审计脚本没有向数据根目录写入文件。

## 本地核实结果

- **文件系统：** 130,424 个普通文件，全部 `.dcm`，总计 28,151,425,416 bytes（26.218 GiB）；目录 1,016 个（含根），根下层级计数为 23 个病例目录、171 个 Study 目录、821 个 Series 目录。全部预期公开病例别名 A01–A12、B01–B11 均存在；未映射文件为 0。
- **异常项：** 空 Series 目录 15；零字节文件、特殊非普通项、reparse 项、不可读取标记、目录/元数据读取错误、重复 basename 组均为 0。
- **Header：** 130,424/130,424 成功，失败 0；识别 171 个 Study UID、806 个 Series UID、130,424 个唯一 SOP Instance UID、171 个 Frame of Reference UID。重复 SOP UID 组及跨 Study/Series/case 冲突组均为 0；必要 Study/Series/SOP UID 与 Modality 均无缺失。
- **模态：** MR 92,508 files / 523 Series；CT 21,637 / 65；PT 16,129 / 68；REG 87 / 87；RTSTRUCT 63 / 63；UNKNOWN 0。容量、每病例分布和 Header 元数据覆盖见公开报告及 JSON。
- **实际目录/文件命名：** Study 文件夹名与 StudyInstanceUID 相同；Series 文件夹名为 `Modality_SeriesInstanceUID`；全部文件 basename 均为 UUID 形态、扩展名 `.dcm`，没有一个文件 stem 等于 SOPInstanceUID。精确 UID→Series/Instance 相对路径关系只记录在本地 Manifest。
- **Header-only Volume 候选：** MR 有 474 个多切片 Header 候选、49 个几何字段不一致/不完整组；CT 65、PT 68 个多切片 Header 候选。该分类没有验证像素、切片连续性、方向、配准或空间质量。

## 历史审计与完整性差异

- 本次指定子目录与 CMRL-05 的父目录盘点在文件数（130,424）、字节数（28,151,425,416）、Study 数（171）和 Header Series 数（806）一致。当前目录统计 1,016 个（含根）；CMRL-05 统计父目录时多计一层，结果为 1,017。
- CMRL-06 固定 IDC v25.0.0 参考为 821 Series、131,556 instances（MR 523/93,308；CT 65/21,740；PT 68/16,343；REG 97/97；RTSTRUCT 68/68）。本次 Header 汇总为 806 Series、130,424 unique SOP，数量差为 -15 Series、-1,132 instances，与既有按 Series 映射对账一致。
- 本地目录恰有 15 个空 Series 目录，但本任务没有逐 UID 将它们与官方缺失 Series 对应；数量相同不证明是同一组目录/Series。既有 v25 对账把 15 Series/1,132 instances 记录为相对固定官方索引的本地短缺；对象字节身份、缺项来源或版本变化成因仍未在此任务核实。

## 产物与验证

- **公开研究报告：** `docs/datasets/CCTH_DATASET_INDEX.md`。
- **公开机器摘要：** `evidence/ccth_inventory_summary.json`。
- **可重复生成脚本：** `scripts/r0/build_ccth_dataset_index.py`。
- **本机私有 Manifest（不提交）：** `.local/dataset-index/files.csv`、`directories.csv`、`studies.csv`、`series.csv`、`cases.csv`。`files.csv` 保留每个文件的相对路径、大小和 Header 映射；其他清单提供目录、Study、Series、病例聚合。
- Manifest 回读验证：文件行数 130,424、唯一路径 130,424、大小合计 28,151,425,416 bytes；目录行数 1,016。根目录递归文件数/容量与全量 Manifest 相同；目录直接文件数和直接容量逐目录与文件 Manifest 对齐。
- 独立元数据复核：130,424 个 Manifest 相对路径均存在且文件大小相同；806/806 个 Series Manifest 路径存在，Series 文件数/容量逐组相符；171 Study 和 23 case 行与统计一致。
- `.local/dataset-index/` 的五份 Manifest 均由根 `.gitignore` 规则忽略。公开 Markdown/JSON 中未发现数字点分 UID 形态或完整数据绝对路径；公开产物只保留 A/B 病例别名和聚合统计。
- 报告声明的 R0 状态、影像/ROI 边界与 CMRL-04～10 既有证据一致；本任务不改变准入状态。

## Git 交付

- **起始基线：** CMRL-10 分支/PR #11 head `4698b0d7d1992a02b6c1330157d5bfc778509b5e`；创建本分支时 PR #11 为 OPEN/Draft，base 为 `codex/r0-09-tcia-authoritative-annotation-review`，原 PR 未改动。
- **分支：** `codex/cmrl-11-ccth-dataset-index`，从上述 PR #11 head 建立。
- **提交、远端 ref、Draft PR 与最终 HEAD：** 待提交及推送后补录。
- 不更新 Main、不合并 PR、不改变 R0 阶段。
