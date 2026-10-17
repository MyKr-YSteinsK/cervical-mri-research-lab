# CMRL-04｜TCIA 本地 DICOM 文件级与 RTSTRUCT 引用审计

- **审计日期：** 2026-10-17
- **任务 / Plan：** CMRL-04 / 外部 CMRL-Plan-04 r1
- **研究阶段：** R0-DATA-ACCESS-AUDIT；本报告不批准进入 R1，也不确认肿瘤 ROI 语义。
- **任务状态：** COMPLETE（本地文件级审计范围）；**R0 NOT COMPLETE**。
- **本地数据根：** 仓库相对目录 data/raw/tcia/ccth_manual/，对应用户本轮指定的本机目录。没有记录其下原始文件名或病例子目录名。
- **来源等级：** 用户报告从 IDC 的 CC-Tumor-Heterogeneity 页面手动下载，故本地文件来源为 USER-REPORTED-SOURCE；DICOM Header 为 FILE-INSPECTED。本地文件没有 Collection manifest 可独立确认归属。

## 结论

本地子集包含 **5,959 个 .dcm 文件，共 1,387,467,936 bytes（1.387 GB，1.292 GiB）**，与用户所报约 1.3 GB 一致。全部 5,959 个文件均由标准 DICOM 读取路径成功解析；未使用强制解析，无解析失败、零字节文件、符号链接或跳过的大文件。Header 扫描耗时约 10.4 秒，限制为 20,000 个文件或 20 分钟。没有解码任何影像 Pixel Data。

其中有 **4,334 MR、917 CT、702 PT、3 REG、3 RTSTRUCT**。共观察到 1 个不同的 DICOM PatientID 值、6 个 Study UID、39 个 Series UID 和 6 个 Frame of Reference UID。单一 PatientID 值只是本地 DICOM 键计数，不能独立证明现实身份或临床人数；此键覆盖 6 个 Study。

27 个 MR Series 中有 **9 个 T2 文本候选**。3 个 RTSTRUCT 的 **129 个直接 SOP Instance 引用全部解析到本地 MR，且目标 MR Series 均落在这 9 个候选内**；3 个 Series 引用也都命中本地 T2 文本候选 MR。129 个直接引用的 PatientID、Study、Series 和 Frame 对照均一致，没有引用缺失、冲突或未知项。

RTSTRUCT 共列出 6 个 ROI 名称，但都只能按本次脱敏规则归为 OTHER；6 个 ROI 均没有 RTROIInterpretedType 值。当前证据**不能确认其中任何一个是原发宫颈肿瘤 ROI**，因此没有得到已验收的肿瘤 Mask。DICOM 引用关系可信，不等于临床结构语义已确认。

本地数据足以让用户在自己的 Lab 中开始**单个 MR 序列的 Header 读取和空间元数据质控练习**。开始肿瘤分割、RTSTRUCT 栅格化或 Radiomics 前，仍须由用户在本地查看 ROI 含义并确认目标；Collection 归属也应补充下载 manifest 或来源记录。**R0 仍为 NOT COMPLETE。**

## 清单与解析

| 项目 | 本次实测 |
|---|---:|
| 普通文件 / DICOM 候选 | 5,959 / 5,959 |
| 子目录 | 47 |
| 扩展名 | 全部 .dcm |
| 总字节 | 1,387,467,936 |
| 零字节 / 无法读取 / 特殊文件 / 链接 | 0 / 0 / 0 / 0 |
| 标准 Header 成功 / 强制解析 / 解析失败 | 5,959 / 0 / 0 |
| 解析器 | pydicom 3.0.2；Python 3.12.13 |
| Header 与引用审计用时 | 约 10.4 秒 |
| Pixel Data 解码 | 未运行 |

解析仅选取必要的 DICOM Header 标签并使用 stop_before_pixels=True。RTSTRUCT 深层序列单文件读取上限为 16 MiB；本次 3 个文件均低于上限且全部成功解析。未读取临床 XLSX，也未访问 TCIA/IDC 数据端点。

### 模态与匿名聚合键

| DICOM Modality | 文件数 |
|---|---:|
| MR | 4,334 |
| CT | 917 |
| PT | 702 |
| REG | 3 |
| RTSTRUCT | 3 |

SOP Class 汇总与 Modality 对应：MR Image Storage 4,334、CT Image Storage 917、Positron Emission Tomography Image Storage 702、Spatial Registration Storage 3、RT Structure Set Storage 3；本地子集中没有 SEG。全部文件均有 PatientID、Study UID、Series UID 与 SOP Instance UID；全体文件中有 3 个缺少顶层 Frame of Reference UID，所有 MR 文件均具备该字段。39 个 Series 横跨 6 个 Study，27 个 Series 为 MR；每个 Series 的实例数最少 1、中位数 42、最多 1,400。没有重复 SOP Instance UID。所有这些值仅在进程内用于聚合和关联；证据文件没有保存任何 UID 或逐病例组合。

## MR 序列与空间元数据

“T2 候选”采用保守的字符串启发式：MR Series 的 SeriesDescription、SequenceName 或 ImageType 包含 T2 标记，或满足自旋回波术语且 EchoTime 至少 50 ms。实际 9 个候选均来自文本标记；仅凭描述不能确认序列物理属性、采集时点或临床治疗前状态。

4,334 个 MR 实例均具备 ImageOrientationPatient、ImagePositionPatient、PixelSpacing、Rows、Columns、SliceThickness 和 Frame of Reference UID。按元数据边界检查，方向向量、像素间距、位置字段和尺寸字段均通过简单合理性条件。SpacingBetweenSlices 仅在 1,134 个实例中存在，3,200 个缺失。此结果只说明后续人工空间质控所需的核心字段可读；没有排序切片、计算切片间距、重建体积、配准或验证图像与轮廓的几何重合。

## RTSTRUCT 引用链与 ROI 类别

| 核验层级 | 结果 |
|---|---|
| RTSTRUCT 文件 | 3 个，3 个均完成深层 Header/序列解析 |
| 直接 SOP Instance 引用 | 129 条引用记录（每个 RTSTRUCT 内按 SOP UID 去重后汇总），全部在本地解析到 MR T2 文本候选 Series |
| RTReferencedSeries 引用 | 3/3 命中本地 MR T2 文本候选 Series |
| PatientID 对照 | 129/129 一致 |
| Study UID 对照 | 129/129 一致 |
| Series UID 对照 | 129/129 一致 |
| Frame of Reference UID 对照 | 129/129 一致 |
| 不在本地 / 冲突 / 未知的直接图像引用 | 0 / 0 / 0 |
| ROI | 6 个 ROI 与 6 个 ROIContour 条目；名称字段均存在，RTROIInterpretedType 均缺失 |
| ROI 粗分类 | OTHER 6；GTV-like、CTV/PTV-like、OAR-like 未检出 |

引用关系基于本地 DICOM 的实际 SOP/Series/Frame UID 关联，不用“同一个 PatientID”替代引用证据。所有实例级引用同时与该 RTSTRUCT 的 PatientID、Study、被引用 Series 和 Frame UID 一致。未保存这些 UID 或映射。ROI 分类只保留粗类别，名称及其他逐例元数据未写出；OTHER 表示本次规则无法归类，不代表临床上没有肿瘤轮廓。

## 原始数据、隐私与边界

- 原始 DICOM 以只读方式打开；没有移动、重命名、删除、解压覆盖或改写原始文件，也没有重新下载或补下载影像。
- 扫描前后 5,959 个文件的数量、字节大小、最后写入时间与文件属性均未变化；没有新增或丢失文件。本项是元数据快照核对，不是逐字节哈希比较。
- 没有把 PatientName、PatientID 值、日期、Accession Number、机构名、UID、文件名、病例目录名、ROI 原名或任何患者级索引写入仓库、报告、聊天或聚合 JSON。
- 本任务只为执行元数据审计在分支忽略目录 .local/ 安装了 pydicom 3.0.2（无额外依赖）；未安装影像科研框架。
- 未进行像素解码、RTSTRUCT→Mask 栅格化、配准/重采样、Radiomics、模型训练或临床解释。没有验证临床结局或疗效标签。
- Collection 页面及 CC BY 4.0 来源信息见 [CMRL-03 报告](./CMRL-03-TCIA最小MR与RTSTRUCT准入审计.md)；其 Collection 级发布信息不证明本地这批文件属于该 Collection。

聚合数据和完整审计参数见 [tcia_manual_dicom_profile.json](../../evidence/r0/tcia_manual_dicom_profile.json)，可复跑脚本见 [audit_tcia_manual_dicom.py](../../scripts/r0/audit_tcia_manual_dicom.py)。

## 后续建议

1. 可进入一次用户亲自编写和运行的单序列 DICOM 读取练习；在本机选定 1 个 T2 候选 MR Series，先核对 shape、方向、间距与切片顺序。
2. 若目标是肿瘤分割，先在本地 DICOM 工具中查看结构集的 ROI 名称与轮廓，确认哪个（若有）代表原发宫颈肿瘤；不要根据 OTHER 以外的假设构造 Mask。
3. 保存 IDC 手动下载的来源/选择记录，以确认本地文件对应的 Collection；不要通过追加下载代替来源核对。
4. R0 总体数据准入、标签判断及阶段推进由 Main 决定；本任务没有推进 R1 或批准分割/Radiomics。
