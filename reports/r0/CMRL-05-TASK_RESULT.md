# TASK_RESULT｜CMRL-05 / r1

## 任务状态

**COMPLETE**：已完成 Plan-05 r1 授权的本地离线全量 DICOM/manifest 审计、脱敏报告、复核脚本和合成测试，并推送到专用分支、创建 Draft stacked PR #6。

**科研证据状态另列：** 本地候选文件 Header 可解析性 `PASS`；`MANIFEST_STRUCTURE_VERIFIED`；`SERIES_COVERAGE_NOT_VERIFIED`；`OBJECT_LEVEL_COMPLETENESS_NOT_VERIFIED`；本地 MR–RTSTRUCT 直接 DICOM 引用元数据已核验；ROI 临床含义、空间叠加、患者级身份和本地 Collection 成员关系未验证。**R0 NOT COMPLETE**；本任务没有批准 R1、肿瘤 Mask、Radiomics 或模型。

## 1. 输入、工具与预算

- **本地输入别名：** `data/raw/tcia/ccth_idc_v25_full/`。与既有 `data/raw/tcia/ccth_manual/` 目录相互独立；人工子集没有重扫、复制、合并或修改。
- **来源等级：** 用户报告本地全量候选目录来自 IDC CC-Tumor-Heterogeneity Release 25.0。manifest 结构已本地核验，但没有权威映射证明本地文件均属于该 Collection。
- **manifest：** IDC Release 25.0；52,045 bytes；SHA-256 `f56073583ad4cf931a9a46fac83af2672f5b0248ebcc2a94406e9f662508ee79`，与计划记录副本匹配。821 条 `cp s3://idc-open-data/<prefix>/* .` 命令、821 个唯一前缀；重复和非法行均为 0。manifest 只解析为惰性文本，未执行命令；通配符不包含对象级期望清单。
- **运行：** 2026-10-17；Python 3.12.14、pydicom 3.0.2；Header 使用标准解析、指定元数据标签和 `stop_before_pixels`。单文件 Header 上限 128 MiB，RTSTRUCT 深解析上限 16 MiB；全局强制解析上限为 0。
- **有界预算：** 最多 200,000 个 Header、60 分钟；实际 130,424 个，Header 扫描 260.891 秒，manifest/清点/扫描合计 287.235 秒。没有超限、跳过或强制解析。

## 2. 文件清点与 DICOM 汇总

- **本地清点：** 130,424 个普通文件、28,151,425,416 bytes、1,016 个子目录；扩展名全部为 `.dcm`。零字节、元数据错误、不可读取标记、重名 basename、特殊文件及 symlink/reparse 项均为 0。与用户报告字节数一致。
- **扫描前后：** 130,424 个文件均按相对位置、大小、mtime、属性摘要保持一致；新增、删除或元数据变化均为 0。没有计算内容哈希，故这是元数据快照证据。
- **Header 覆盖：** 130,424/130,424 标准解析成功；解析失败、强制解析和超限跳过均为 0。未解码任何 Pixel Data。
- **Modality：** MR 92,508；CT 21,637；PT 16,129；REG 87；RTSTRUCT 63；SEG/其他/缺失为 0。
- **DICOM 聚合键：** 23 个不同 PatientID 键、171 个 Study UID、806 个 Series UID、171 个 Frame UID。SOP Instance UID 全部存在且无重复，故本地不同 SOP 键 130,424。63 个文件缺少顶层 Frame UID。PatientID 键数不等于独立核实的真实人数；23 个键均覆盖多个 Study。
- **Series 分布：** 139 个 Study 含多个 Series；806 个 Series 的实例数最少 1、中位数 36、最多 1,400。没有 Series 跨越多个不同的直接父目录。
- **MR：** 92,508 个实例、523 个 Series；202 个 Series 是 T2 文本/参数启发式候选（196 个有文本信号，24 个有自旋回波与 TE 信号，类别有重叠）。7 项核心空间字段对全部 MR 实例存在，基础有限性/正值/范围检查通过；SpacingBetweenSlices 有 62,936 个存在、29,572 个缺失。没有重建体积或验证真实切片几何。

## 3. 下载完整性层级与官方统计口径

| 层级 | 结论 | 解释 |
|---|---|---|
| manifest 结构 | `MANIFEST_STRUCTURE_VERIFIED` | 821 条 Release 25.0 命令唯一且语法有效，SHA 与记录副本匹配 |
| 821 source-prefix → 本地 Series 覆盖 | `SERIES_COVERAGE_NOT_VERIFIED` | 没有经过来源/版本核验的前缀到 Series 映射；数字相近或相等不能替代映射 |
| 逐对象下载完整性 | `OBJECT_LEVEL_COMPLETENESS_NOT_VERIFIED` | 通配符未列出逐对象预期值；没有版本一致的权威对象清单或逐对象比对 |
| 本地文件 Header 可解析性 | `PASS` | 扫描目录候选集 130,424/130,424 标准 Header 成功，仅证明该本地集合的 Header 可读 |

既有官方来源记录公布 23 subjects、171 studies、821 series、131,556 images、约 28.39 GB。现场得到 23 个 PatientID 键、171 个 Study、806 个 Series 和 130,424 个普通文件。统计口径并非已证明相同：PatientID 键不等于来源身份，官方 images 数不等同于本地 `.dcm` 文件数，官方体量又是舍入统计。本地大小与用户回报相同、且接近官方约数，均不证明 Collection 成员关系或逐对象完整。

## 4. RTSTRUCT、引用与 ROI 证据

- 63/63 个 RTSTRUCT 在 16 MiB 限制内完成深层解析；126 个 Structure Set ROI、126 个 Observation、126 个 ROIContour 均有唯一关联。
- 按 CMRL-04/r2 修正逻辑读取 `RTROIObservationsSequence.RTROIInterpretedType` 并经 ReferencedROINumber 连接；126 个类型值均为空。独立名称启发式为 `OTHER` 126，不作为语义判断。
- 1,482 个 Contour item 均声明 `CLOSED_PLANAR`；点数均为正，Contour Data 元素数匹配声明点数且数值有限；1,482/1,482 有 ContourImageSequence，RTSTRUCT 内去重后有 857 个轮廓 SOP 引用。
- 63/63 个 RTSTRUCT 的直接 Series 引用命中本地 MR Series；1,873 个去重 SOP 引用命中本地 MR，61 个未命中本地候选对象索引。已命中 SOP 引用的 PatientID、Study、Series、Frame 键各 1,873/1,873 一致；全部指向 T2 启发式候选。61 个未命中不单独证明下载缺失。
- 弱同现按“一个 RTSTRUCT × 一个本地 MR Series”配对计：1,450 对 PatientID 键相同，其中 1,019 对没有直接 SOP/Series/Frame 引用；431 对 Study 相同和 431 对 Frame 相同的配对均有直接引用。弱同现不替代直接引用。
- 这些结果**不证明原发宫颈肿瘤 Mask**，不证明轮廓与 MR 像素网格对齐，也不验证闭合/共面或临床结构含义。

## 5. 原始数据、隐私与未运行项

原始 DICOM 只读；没有重新下载、同步、删除、改名、移动、解压覆盖或写入源目录。manifest 命令未执行，未访问 TCIA/IDC/S3，也未读取临床工作簿。未解码像素，未创建体积或 Mask，未做配准、重采样、Radiomics、训练、推理或临床解释。脱敏证据只保存集合/模态/质量聚合；不包含患者值、UID 值、真实检查日期、医院、源路径/文件名、manifest 前缀值、ROI 原名/坐标或病例级索引。

## 6. 验收 Gate

| Gate | 状态 | 证据摘要 |
|---|---|---|
| V1｜基线/数据源 | PASS | 基于 PR #5 当前 HEAD 建立隔离工作树；数据根存在、只读、受 Git ignore，前后元数据稳定 |
| V2｜Manifest | PASS | 本地 SHA/格式核验，821 条命令结构有效 |
| V3｜文件清单 | PASS | 130,424 文件、28,151,425,416 bytes、扩展/错误/前后状态已记录 |
| V4｜完整性分层 | PASS（分层判定完成） | 明确 `SERIES_COVERAGE_NOT_VERIFIED` 和 `OBJECT_LEVEL_COMPLETENESS_NOT_VERIFIED`，未伪造 PASS |
| V5｜Header/UID | PASS | 全候选 Header 覆盖、模态、键数、缺失/重复和 MR 字段已统计 |
| V6｜RTSTRUCT | PASS | r2 Observation 类型逻辑、Contour 元数据、直接引用与弱同现分开核验 |
| V7｜隐私/测试 | PASS | 26 项合成与回归测试通过；仅提交聚合证据，敏感内容扫描无路径或 UID 值 |
| V8｜Git/报告 | PASS | 专用分支已推送，远端 SHA 实查，Draft PR #6 已创建且 base/head 正确 |

## 7. 文件与 Git 交付

首个审计成果提交包含以下 6 个文件；TASK_RESULT 本文件随后在同一分支追加：

- `docs/project/02-DATASET_EVIDENCE_REGISTER.md`
- `docs/project/08-RESEARCH_STATE.md`
- `evidence/r0/tcia_full_dicom_profile.json`
- `reports/r0/CMRL-05-TCIA全量DICOM准入审计.md`
- `scripts/r0/audit_tcia_full_dicom.py`
- `tests/test_tcia_full_dicom_audit.py`
- `reports/r0/CMRL-05-TASK_RESULT.md`

- **基线：** `codex/r0-04-manual-dicom-audit`，PR #5 base；审计分支父提交 `2dfeeacdaf2c114d277d48a57f4c63c4225856d2`。
- **工作分支：** `codex/r0-05-tcia-full-dicom-audit`。
- **审计成果提交：** `544bbc1e28e58df2b945d9d536130c950c4bbd8e`；推送目标 `origin/codex/r0-05-tcia-full-dicom-audit`。该提交推送后 `git ls-remote` 返回同一 SHA。
- **Draft PR #6：** https://github.com/MyKr-YSteinsK/cervical-mri-research-lab/pull/6 ；base `codex/r0-04-manual-dicom-audit`，head `codex/r0-05-tcia-full-dicom-audit`；创建时为 OPEN / Draft / 未合并，head SHA 为 `544bbc1e28e58df2b945d9d536130c950c4bbd8e`。TASK_RESULT 追加后已再次推送同一 PR 分支，最终远端 HEAD 和 PR 状态由交付回执复核。
- 没有合并 PR、转 Ready、改写历史或修改 PR #1–#5。仓库当前未发现部署 workflow。

## 8. 给 Main 的最低成本建议

由用户在本机医学影像查看器中选择一个有直接 DICOM 引用的 MR+RTSTRUCT 组合，检查 ROI 名称和轮廓相对 MR 的空间位置；在用户确认临床结构含义前，不把它称作原发宫颈肿瘤 Mask。若需证明下载对象完整，补充 Release 25.0 同版本、来源可信的对象级期望清单或下载记录，再逐项比对本地对象。Main 收到本结果后再决定 R0 总体准入与下一项教学；本任务不启动新阶段实验。
