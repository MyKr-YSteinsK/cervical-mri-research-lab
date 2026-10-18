# TASK_RESULT｜CMRL-04 / r1

## 任务状态

**COMPLETE**：已完成外部 Plan r1 授权的本地离线 DICOM 文件级与 RTSTRUCT 引用审计、脱敏证据、报告和 Draft stacked PR。
**研究状态仍为 R0 NOT COMPLETE**；本任务没有批准 R1、肿瘤分割、Radiomics 或疗效建模。

## 1. 数据输入与文件清单

- **实际输入：** 用户指定的本地目录已现场读取；仓库相对位置为 data/raw/tcia/ccth_manual/。未记录其下病例目录名或原始文件名。
- **来源：** 用户报告从 IDC 的 CC-Tumor-Heterogeneity 页面手动下载，记为 USER-REPORTED-SOURCE。没有 Collection manifest 可以独立确认本地文件确属该 Collection。CMRL-03 的官方 Collection 与 CC BY 4.0 来源证据仍只支持发布页层级。
- **用户报告量：** 约 1.3 GB。
- **本地实测：** 5,959 个普通文件，全部为 .dcm，共 1,387,467,936 bytes（1.387 GB / 1.292 GiB），47 个子目录；零字节、不可访问、特殊文件、符号链接和 reparse point 均为 0。
- **Header 覆盖：** 对全部 5,959 个候选文件进行了标准路径解析；成功 5,959，强制解析 0，失败 0，超限跳过 0。使用 10.406 秒，Plan 上限为 20,000 个 Header 或 20 分钟。
- **工具：** pydicom 3.0.2、Python 3.12.13；仅安装 pydicom 一项依赖至任务分支忽略的 .local 环境，未升级或安装科研框架。使用 stop_before_pixels 与指定标签读取，没有解码 Pixel Data。

## 2. DICOM、MR、RTSTRUCT 与引用结果

- **Modality：** MR 4,334；CT 917；PT 702；REG 3；RTSTRUCT 3；没有 SEG。
- **匿名聚合键：** 1 个不同的 DICOM PatientID 值、6 个 Study UID、39 个 Series UID、6 个 Frame of Reference UID；27 个 Series 为 MR。PatientID 是本地 DICOM 键数量，不等同独立核验的真实人数。所有文件均有 PatientID、Study、Series 与 SOP Instance UID；3 个文件缺少顶层 Frame UID，MR 文件均具备。
- **Series 实例数：** 39 个 Series 的实例数最少 1、中位数 42、最多 1,400；未发现重复 SOP Instance UID。
- **T2WI 候选：** 27 个 MR Series 中，9 个依据 SeriesDescription、SequenceName 或 ImageType 的 T2 文本标记列为候选；EchoTime/序列名的补充启发式没有新增候选。没有凭文字确认时点或序列物理属性。
- **MR 空间字段：** 4,334 个 MR 均具备方向、位置、PixelSpacing、Rows、Columns、SliceThickness 与 Frame UID；简易范围检查通过。SpacingBetweenSlices 仅 1,134 个具备，3,200 个缺失。未做切片排序、体积重建、空间配准或轮廓重合检查。
- **RTSTRUCT：** 3 个全部完成引用序列解析，包含 6 个 ROI 与 6 个 ROIContour 条目；6 个 ROI 名称均存在，但 RTROIInterpretedType 均缺失。粗分类结果为 OTHER 6，未检出 GTV-like、CTV/PTV-like、OAR-like。不能据此确认原发宫颈肿瘤 ROI 或已验收 Mask。
- **直接引用：** 129 条引用记录（每个 RTSTRUCT 内按 SOP Instance UID 去重后汇总）全部解析到本地 MR T2 文本候选 Series；3/3 个 Series 引用也命中候选 MR。129 条记录的 PatientID、Study UID、Referenced Series UID 和 Frame UID 对照均一致；未匹配到非 MR、缺失于本地或未知的引用均为 0。这个结果证实本地 DICOM 引用链，不确认 ROI 临床含义或真实 Collection 归属。

详见 [本地 DICOM 审计报告](CMRL-04-TCIA本地DICOM文件级准入审计.md)、[聚合 JSON](../../evidence/r0/tcia_manual_dicom_profile.json) 和 [审计脚本](../../scripts/r0/audit_tcia_manual_dicom.py)。

## 3. 原始数据与隐私边界

- 原始文件由只读读取路径打开，没有重下载、补下载、移动、重命名、解压覆盖、删除或改写。
- 扫描前后 5,959 个文件的文件数、大小、最后写入时间和属性一致，没有新增或丢失。该检查没有计算内容哈希。
- PatientName、PatientID 值、日期、Accession Number、机构名、任何 UID 值、私有 Tag、文件名、病例目录名、ROI 原名和逐病例映射均未写入 Git、报告、PR、聊天或聚合 JSON；未创建本地病例索引。
- 未读取临床 XLSX，未访问 TCIA/IDC 数据端点，未解码像素，未执行 RTSTRUCT→Mask、配准/重采样、Radiomics、训练或临床解释。仅获取本地元数据解析所需的 pydicom 包。

## 4. 验收门槛

| Gate | 状态 | 证据 |
|---|---|---|
| V1｜Git / 输入路径 | PASS | 从 PR #4 已核实的远端 HEAD 建立隔离工作树；用户指定目录存在且可读，原始数据没有复制到工作树。 |
| V2｜清单与完整性 | PASS | 全目录元数据清点完整：5,959 文件、1,387,467,936 bytes、全部 .dcm；无零字节、链接、特殊文件或元数据错误。 |
| V3｜DICOM 元数据 | PASS | 5,959/5,959 标准 Header 解析；无强制解析、失败或超限；模态、Study、Series、PatientID 聚合及关键字段缺失率已记录。 |
| V4｜MR / RTSTRUCT | PASS | MR 4,334、候选 T2 Series 9、RTSTRUCT 3、REG 3、CT/PT 与 SEG 状态已区分。T2 仍仅为 Header 文本候选。 |
| V5｜引用 / ROI | PASS（语义未确认） | 129 条 SOP 引用、3 条 Series 引用及 Patient/Study/Series/Frame 对照全部核验；ROI 仅归类为 OTHER，不能确认宫颈原发肿瘤。 |
| V6｜隐私与科研边界 | PASS | 输出只含聚合数据；敏感值、UID、文件路径/名称和逐病例索引均未进入交付文件；源文件元数据前后不变。 |
| V7｜报告 / Git 交付 | PASS | 本 TASK_RESULT 纳入 CMRL-04 Draft PR #5；远端 head、base、工作树和 PR 状态在本次最终回执中复核。未合并。 |

## 5. Git 与交付

- **Base：** codex/r0-03-tcia-minimal-reference-audit，PR #4 在创建分支时为 Open / Draft / 未合并，远端 SHA 为 f4289001e55457eb42f283a1e118ed5a94e30505。
- **Branch：** codex/r0-04-manual-dicom-audit，建立于上述已核验的 PR #4 HEAD。
- **审计首提交：** 29ebaff6a102c96e7162c998870f3b3fc3a4c7be；推送后远端 ref 已核验与本地一致。
- **Draft stacked PR：** [PR #5](https://github.com/MyKr-YSteinsK/cervical-mri-research-lab/pull/5)，base 为 codex/r0-03-tcia-minimal-reference-audit，head 为 codex/r0-04-manual-dicom-audit。TASK_RESULT 后续提交会更新该 PR head；最终 head SHA 由本次对话回执报告。
- 未合并、未转 Ready、未改写历史。原始工作分支仍保持干净。

## 6. 下一步最低成本动作

现有本地数据足以支持用户亲自编写并运行一次单 MR Series 的读取与空间元数据质控练习。若以后要将 RTSTRUCT 当作肿瘤 Mask，用户仍需在本机 DICOM 工具中核对 6 个 ROI 的结构语义并确认目标；不要按 OTHER 类别推定肿瘤。随后由 Main 决定本地来源证据是否足够、D03 是否可进入下一步教学，以及 R0 的总体数据准入结论。

## 7. TASK_RESULT 补充｜CMRL-04 / r2 定点纠错（2026-10-17）

### 任务状态

**COMPLETE（r2 范围）**：修正 RTSTRUCT ROI 类型读取、轮廓元数据聚合和 r1 证据表述；完成合成 DICOM 回归、全量本地 Header 复核、报告与项目状态同步，并更新同一 Draft PR #5。原始 r1 回执保留为历史记录；以下纠正取代 r1 中未经有效读取支持的类型与轮廓判断。**R0 NOT COMPLETE**。

### r1 缺陷复现与修复

- r1 脚本只选取 `ReferencedFrameOfReferenceSequence`、`StructureSetROISequence` 和 `ROIContourSequence`；其 ROI 类型读取表达式从 `StructureSetROISequence` item 获取 `RTROIInterpretedType`。该字段应从 `RTROIObservationsSequence` item 读取，再以 `ReferencedROINumber` 对应 `StructureSetROISequence.ROINumber`。因此 r1 的“6/6 类型缺失”没有检查真实字段位置，合并类型/名称的“OTHER 6”不能作为 DICOM 类型结论。
- r2 在仅含正确 Observation Sequence 的合成 Part 10 DICOM 上验证了特异标签读取与编号关联；夹具中 `StructureSetROISequence` ROI item 本身没有该字段，而修复后的解析器读取到对应 Observation 的 GTV 类别。另有回归覆盖缺失 Observation Sequence、缺失/空类型、孤立编号、多 Observation 冲突、缺失/空 ContourSequence、Contour Data 为空/点数不一致、重复 ROIContour 编号及零值 ROI 编号键；共 12 项测试全部通过。

### r2 实测聚合结果

- **执行环境：** 隔离工作树分支 `codex/r0-04-manual-dicom-audit`；Python 3.12.13、pydicom 3.0.2。输入仍为用户指定的本地原始目录；3 个 RTSTRUCT 均低于单文件 16 MiB 限额。
- **全量复核：** 5,959/5,959 个 DICOM Header 标准解析成功，0 强制解析、0 失败；1,387,467,936 bytes；扫描 13.359 秒，低于 20,000 Header / 20 分钟上限。源文件扫描前后 5,959 项的路径相对键、字节数、mtime 和属性均一致，无新增/删除；这是元数据快照比较，不是内容哈希。
- **ROI 类型：** `StructureSetROISequence` 6 项、`RTROIObservationsSequence` 6 项、`ROIContourSequence` 6 项；3 个文件中的三种 Sequence 均存在且非空。6/6 个 Observation Number、ROI Number 及 Referenced ROI Number 可唯一关联；重复/孤立/未匹配/多 Observation/类型冲突均为 0。6 个 `RTROIInterpretedType` 字段均存在但值为空，故可报告 `EMPTY 6`，不能报告类型值全部缺失或推断 `OTHER` 为类型。独立名称启发式为 `OTHER 6`；因类型字段为空，名称与 DICOM 类型不可比较。
- **轮廓几何元数据：** 6 个 ROIContour 均唯一连接到一个 Structure Set ROI，无重复 ROIContour 编号关联。6 个 ContourSequence 均非空，合计 108 个 Contour item；声明几何类型 `CLOSED_PLANAR` 108，其他/缺失/空/未识别为 0。NumberOfContourPoints 108/108 为正；Contour Data 108/108 与声明点数对应的三维坐标元素数量一致且所有数值有限。108/108 个 contour item 有 ContourImageSequence 引用，按 RTSTRUCT 内去重汇总 60 条 SOP 引用；这些引用包含在 129 条总直接 SOP 引用中。
- **原 r1 引用链复核：** 129/129 条直接 SOP 引用仍在本地命中 MR T2 文本候选 Series；PatientID、Study、Series、Frame 对照 129/129 一致；Series 引用 3/3 命中候选 MR。该结论只说明 DICOM 引用关系，不证明图像与轮廓空间重合或临床结构含义。
- **科学边界：** `CLOSED_PLANAR` 是文件中声明的几何枚举；本任务只检查枚举、点数、数据列表长度/有限性和图像引用字段，不检验共面性、拓扑闭合、栅格化可行性、像素空间配准或 ROI 是否为宫颈原发肿瘤。没有解码 MR Pixel Data、栅格化、配准、重采样、体积重建、Radiomics、训练或临床判读；未读临床 XLSX、未访问/下载 TCIA/IDC 数据。Collection manifest 仍未提供，本地 Collection 归属仍为 `USER-REPORTED-SOURCE`。

### R2 验收

| Gate | 状态 | 证据 |
|---|---|---|
| R2-V1｜Git / 输入 | PASS | PR #5 复核时仍为 Open / Draft，head 为预期 r1 SHA `e1a0ced4b20a9d328d4b1d1b2121ed9c199bc6ac`，base 为 PR #4 分支；目标工作树及原始项目工作树初始均干净。指定数据目录可读。 |
| R2-V2｜ROI 类型 | PASS | 已从 Observation Sequence 正确读取，按 Referenced ROI Number 唯一关联；实际 6 个类型值均为空，Presence/Empty 与关联统计均在聚合 JSON；12 项合成 DICOM 单元测试通过。 |
| R2-V3｜轮廓结构 | PASS | 检查 6 项 ROIContour 和 108 个 Contour item 的编号关联、声明几何、正点数、坐标元素数/有限性与图像引用；没有把 ROIContour 条目当成 Mask。 |
| R2-V4｜科研边界 | PASS | 独立区分类型值、名称启发式、轮廓元数据、MR SOP 引用与临床语义；R0 保持 NOT COMPLETE。 |
| R2-V5｜隐私与源文件 | PASS | 只读重查原始路径；快照前后相同；未下载、未解码像素；仓库聚合证据不含原名、患者值、UID、文件名/路径或坐标。 |
| R2-V6｜交付 | PASS | 仅在原 CMRL-04 分支聚焦提交并推送到授权 remote，更新同一 Draft PR #5；未合并、未转 Ready、未改写历史。最终远端 SHA 与 PR 状态在本次对话最终回执中复核。 |

### 产物与复核

更新了原脚本、聚合证据 JSON、本 DICOM 审计报告、本 TASK_RESULT 的 r2 追加段，以及 D03 数据集登记和研究状态中的必要事实。新增 12 项轻量合成 DICOM 单元测试；不包含患者或临床数据。Plan 仍保存在仓库外。精确远端 head SHA 见本次对话的完整 r2 回执。

### 最小后续核对

由用户在本机 DICOM 查看器中，将原始 ROI 名称/结构与对应 MR 图像人工对照，确认是否有结构代表原发宫颈肿瘤，以及引用切片与轮廓点的空间关系；该人工确认完成前不得把当前 RTSTRUCT 视为已准入的肿瘤 Mask。
