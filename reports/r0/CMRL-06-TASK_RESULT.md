# TASK_RESULT｜CMRL-06 / r1

## 1. 任务运行状态与科研状态

**任务状态：PARTIAL。** Plan-06 r1 的官方索引、manifest 映射、本地最小 Header 对照、预算内匿名 S3 尝试、合成测试与脱敏报告均已完成。公开 S3 LIST 未取得响应，因此逐对象证据不可用；计划要求的逐 Series 私有差异 UID 文件也未生成，见第 6 节。

**科研证据结论：** 官方索引 `SOURCE_VERSION_VERIFIED`；manifest→官方 Series `MAPPING_VERIFIED`；本地 Series `INSTANCE_COUNT_GAPS_FOUND`；逐对象 `OBJECT_INVENTORY_NOT_VERIFIED`；内容位级完整性 `NOT_VERIFIED_NO_CONTENT_HASHES`。**R0 NOT COMPLETE**，不接受数据集、不进入下一阶段。

## 2. 来源、版本与运行环境

- IDC 官方 `idc-index-data` Release `25.0.0` 固定资产：`idc_index.parquet` SHA-256 `450598d6493d800334a8e1ece1fda4a5ec04ca1bd2f73309058f0531f8155572`，74,108,345 bytes；内嵌 `idc_index_data_version=25.0.0-0-gdbf7fd0`。官方 sidecar 匹配。
- 官方 `collections_index.parquet` SHA-256 `97e5ac3bba296cb3f4e9d87545231275aad66fc89ba07262b7914e72e857489c`，102,477 bytes；内嵌版本相同，sidecar 匹配；官方集合名 `CC-Tumor-Heterogeneity` 与机器 ID `cc_tumor_heterogeneity` 一对一对应。
- 主索引 1,044,191 行、31 列；目标集合 821 个 Series 行和唯一 UID，`instanceCount` 合计 131,556。集合模态行数：MR 523、CT 65、PT 68、REG 97、RTSTRUCT 68。
- manifest 52,045 bytes，SHA-256 `f56073583ad4cf931a9a46fac83af2672f5b0248ebcc2a94406e9f662508ee79`；标注 IDC Data Release 25.0（2026-10-01），821 条唯一命令。命令按惰性文本解析，未执行。
- 来源与字段权威：官方 [Release 25.0.0](https://github.com/ImagingDataCommons/idc-index-data/releases/tag/25.0.0)、[索引字段参考](https://idc-index.readthedocs.io/en/latest/indices_reference.html)、[IDC 版本说明](https://learn.canceridc.dev/data/data-versioning)。索引/集合 Parquet 与 checksum sidecar 的 URL、SHA 和实测行列数记录在 `evidence/r0/tcia_v25_integrity_profile.json`。
- 读取时间：2026-10-17。环境：Python 3.14.6、pydicom 3.0.2、DuckDB 1.5.6、PyArrow 26.0.0；复用既有 Python 3.14 IDC 下载环境，未改包或配置。

## 3. Manifest 映射与本地 Series

- 821/821 manifest 前缀映射至 821/821 官方 Series，唯一、一对一；未映射 0、歧义 0、重复 Series UID/前缀 0、索引中未见于 manifest 的 Series 0。按同一公开 S3 bucket 的路径边界匹配官方 `series_aws_url` 父级前缀，没有用 `crdc_series_uuid` 或 DICOM UID 代替 URL 连接。
- 最小 Header 扫描：130,424/130,424 文件解析成功；零错误、缺失 Series/SOP UID、零字节及重复 SOP 文件均为 0；本地唯一 Series 806。标签限于 `SeriesInstanceUID`、`SOPInstanceUID`、`Modality`、`StudyInstanceUID`；不解码 PixelData、不做 RTSTRUCT 深度解析。
- 对照：期望 Series 821，本地命中 806，缺失 15，非预期 0；748 个 Series 实例数相等，73 个短缺，0 个超额。预期实例 131,556，本地唯一 SOP 130,424，净短缺 1,132。
- TCIA 公开页记录的旧发布统计为 821 Series、131,556 images、28.39 GB；其 Series/Images 数与 v25.0.0 索引一致。本地文件数差额以 v25.0.0 `instanceCount` 为参照，不表示已经观察到 S3 对象缺失。

## 4. 远端对象与完整性分层

- 两次匿名 `ListObjectsV2` 尝试，0 成功页、0 前缀成功、0 response bytes。首次返回 `URLError`；第二次出站代理连接在无响应状态停滞，超过四分钟总重试耗时后手动终止；无 HTTP 状态。不再重试。
- 预算：2/2,000 请求；0/256 MiB 响应；重试总过程约 4 分 25 秒（含本地 metadata 复核），低于 D 阶段 30 分钟上限。
- `REMOTE_LIST_UNAVAILABLE`；远端对象总量/大小/缺失/额外/大小不符均为 `NOT VERIFIED`，不报告为 0。没有 `HEAD`、`GetObject`、DICOM 正文下载、ETag/内容 SHA 核验。
- `OBJECT_INVENTORY_AND_SIZE` 未通过，`BITWISE_INTEGRITY` 未验证。Local basename 重复组为 0 只说明本地文件名唯一，远端 LIST 未成功，因此对象名匹配方案仍未获远端实测。

## 5. 61 条未命中 SOP 引用

CMRL-05 的 61 条本地未命中引用维持 `UNKNOWN`。Series-level `instanceCount` 不能判定对应 SOP 是否在远端对象集合，且没有获得 SOP UID↔S3 object key 的权威实例级映射。

## 6. 输入保护、隐私、测试与 Gates

- 两次本地 metadata snapshot 均稳定：130,424 个普通文件、28,151,425,416 bytes；未复制、移动、改名、删除或修改原始 DICOM，未读取 clinical XLSX。未算全文件内容 hash。
- 没有找到可复用的 CMRL-05 逐 Series UID 本地映射。CMRL-06 的首轮最小扫描保留聚合统计，不保留 UID 明细；为了避免重复读取全量 Header，没有生成逐 Series 私有 gap-list。因此 profile/报告只含聚合短缺数量。
- 12 项合成单元测试通过；`py_compile` 通过；合成隐私测试确认公开汇总不输出 UID、前缀、对象 key 或文件名。

| Gate | 结果 | 依据 |
|---|---|---|
| V1 输入与 Git 基线 | PASS | PR #6 open/Draft，head 为 `8980595c2b3d6a06a9f75b096f48c23e91bb8dde`；原始目录在授权位置，只读 |
| V2 同版本官方索引 | PASS | 固定 v25.0.0 资产、sidecar、嵌入版本与集合 crosswalk 核实 |
| V3 manifest 映射 | PASS | 821/821 一对一，0 歧义/遗漏 |
| V4 本地 Series | PASS（发现缺口） | 全量本地 Header 覆盖；15 个 Series 缺失、73 个 Series 实例短缺 |
| V5 逐对象 | REMOTE_LIST_UNAVAILABLE | 2 次匿名请求无响应；对象 Inventory 未验证 |
| V6 科研边界 | PASS | 61 条引用保留 UNKNOWN，不推断 ROI、Mask 或标签 |
| V7 安全与测试 | PASS（聚合输出） | 12 项合成测试；真实 UID 明细未写入仓库或对话 |
| V8 Git / 报告 | PASS | 独立分支已推送；PR #7 Open/Draft，base 正确，未合并 |

## 7. 产物与 Git 交付

- `reports/r0/CMRL-06-IDC-v25逐Series及对象完整性补证.md`
- `evidence/r0/tcia_v25_integrity_profile.json`
- `scripts/r0/audit_tcia_v25_integrity.py`
- `tests/test_tcia_v25_integrity.py`
- `reports/r0/CMRL-06-TASK_RESULT.md`
- `docs/project/02-DATASET_EVIDENCE_REGISTER.md`
- `docs/project/08-RESEARCH_STATE.md`

执行分支为 `codex/r0-06-idc-v25-integrity`，base 为 PR #6 head 分支 `codex/r0-05-tcia-full-dicom-audit`。主要审计提交 `33b42b88cf2a3b0840f1c00f022c4a2122b7b172` 已推送到 `origin`，并于远端确认一致。Draft PR [#7](https://github.com/MyKr-YSteinsK/cervical-mri-research-lab/pull/7) 状态为 OPEN / Draft / 未合并，base/head 正确。TASK_RESULT 最终补记另成 follow-up commit；最终分支 HEAD 以本次回传中复核的 SHA 为准。不合并、不转 Ready，也未改动 PR #1–#6。

## 8. 下一项建议

由 Main 另行决定是否创建候选 `CMRL-07`：核验 TCIA 原始论文、子宫/肿瘤 ROI 语义、采集时点与 clinical XLSX 字段/许可来源。**本任务没有执行该项，也不据此冻结唯一数据集。** MRI/分割/Radiomics/训练与临床解释核心仍由用户本人实践。

## r2 ADDENDUM｜CMRL-06 按模态缺口与私有差异清单

### 1. 状态

`CMRL-06/r2` 任务范围完成；本补记保留上文 r1 执行记录，不将 r1 的远端对象审计改写为已完成。科研阶段仍为 **R0 NOT COMPLETE**；Main 尚未接受本轮新增证据，监督训练和科研核心均未获准。

### 2. 来源、扫描与输入保护

- 复用已核验的 IDC `idc-index-data` Release `25.0.0` 主索引、`collections_index` 与 CMRL-06/r1 manifest；固定版本/sidecar SHA 未重新抓取或替换。821 个官方 Series 与 821 个唯一 manifest source-prefix 保持一对一映射。
- 只执行一次最小 DICOM Header 扫描，读取 Series/SOP UID、Modality、必要的 Study 键及普通文件盘点元数据；标准解析、止于 PixelData 前。扫描耗时 **279.886 秒**。运行环境 Python 3.14.6、pydicom 3.0.2、DuckDB 1.5.6、PyArrow 26.0.0；测试复用同一 IDC Python 及进程级 pydicom 搜索路径，未安装或改动依赖。
- 扫描开始/完成 profile 时间：`2026-10-17T11:49:03.301795+00:00` / `2026-10-17T11:54:09.519814+00:00`。本地 metadata 快照前后均为 130,424 个文件、28,151,425,416 bytes、1,017 个目录；reparse 与特殊非普通条目均为 0，文件数一致。没有修改、复制、移动、重命名原始 DICOM；未读临床 XLSX。此检查不等于逐文件内容哈希。
- r2 发生的网络请求为 **0**；没有重新发起 S3 LIST、HEAD、GetObject 或下载。r1 两次匿名 LIST 失败保持为历史状态。

### 3. 五模态对账

分类以官方 v25.0.0 Series Modality 为权威。`equal_count_series` 只说明数量相同，不表示内容、像素或空间质量已核验。

| Modality | Expected Series | Local matched | Missing Series | Equal count | Partial shortage | All shortage | Shortage Series total | Expected instances | Observed unique instances | Shortage instances | Excess instances |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| MR | 523 | 523 | 0 | 468 | 55 | 0 | 55 | 93,308 | 92,508 | 800 | 0 |
| CT | 65 | 65 | 0 | 64 | 1 | 0 | 1 | 21,740 | 21,637 | 103 | 0 |
| PT | 68 | 68 | 0 | 66 | 2 | 0 | 2 | 16,343 | 16,129 | 214 | 0 |
| REG | 97 | 87 | 10 | 87 | 0 | 10 | 10 | 97 | 87 | 10 | 0 |
| RTSTRUCT | 68 | 63 | 5 | 63 | 0 | 5 | 5 | 68 | 63 | 5 | 0 |
| **Total** | **821** | **806** | **15** | **748** | **58** | **15** | **73** | **131,556** | **130,424** | **1,132** | **0** |
| UNKNOWN/INVALID | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

五模态 reconciliation 为 `RECONCILIATION_VERIFIED`，所有模态已解释。缺失/无效 Header Modality、Series 内混合 Modality、官方与 Header 冲突、非预期 Series、Series/SOP UID 缺失、解析错误、零字节文件、重复 SOP 均为 0。上述数据还原了 821 / 806 / 15 / 73 / 748 / 131,556 / 130,424 / 1,132 / 0 的 Plan 回归值。

### 4. MR 与 RTSTRUCT 影响

- MR 的 523 个 Series 均命中本地，但 55 个 Series 部分短缺，共少 800 个实例；这 55 个 Series 暂不列入首轮实验候选池，待缺口解释。其余数量相等也不证明 MRI 体、像素、切片方向、spacing 或几何完整。
- RTSTRUCT 有 63/68 Series 命中且数量相等，5 个 Series 完全缺失，共少 5 个实例。没有证据把它们与 CMRL-05 的 61 条未命中 SOP 引用对应；61 条引用继续是 `UNKNOWN`。没有推断 ROI、Mask 或临床标签含义。

### 5. 本机私有表

同一次 Header 扫描生成了 73 行逐 Series 私有差异表，记录数及原始目录快照核验通过；`git check-ignore` 证明文件位于本机 worktree 的忽略范围。公开 profile 只记录生成状态、行数和本地忽略范围标记；不包含 UID 或 source-prefix。未将私有表加入 Git、报告或对话，也没有自动补下载。

### 6. 未解决项

`REMOTE_LIST_UNAVAILABLE`、对象名/数量/大小 `NOT VERIFIED`、位级完整性 `NOT VERIFIED`、61 条 RTSTRUCT 引用 `UNKNOWN` 均保持。r2 不改变这些结论，也不代表完成像素/空间质控、ROI 语义、`OBJECT_INVENTORY_AND_SIZE_VERIFIED`、`BITWISE_INTEGRITY_VERIFIED` 或 `R0 COMPLETE`。

### 7. 验证、Gates 与 Git

- 全仓库 45 项合成单元测试通过；`py_compile` 通过。实测聚合 reconciliation、raw metadata snapshot、私有表 73 行与忽略状态、远端/科研边界断言通过。
- `git diff --check` / staged diff check 通过；暂存清单仅含本轮授权的聚合证据、报告、状态、审计代码和合成测试；对私有 UID/source-prefix 的 staged 内容匹配为 0。
- Gate：V1 `PASS`（执行前远端 SHA 与 PR 链符合 Plan；PR #6、#7 均 Open/Draft/未合并，base/head 正确）；V2 `PASS`（复用固定来源和映射，一次完整扫描，前后 metadata 快照一致）；V3 `PASS`（五模态 reconciliation）；V4 `PASS`（73 行本机忽略表）；V5 `PASS`（合成测试、编译、脱敏与 staged 检查）；V6 `PASS`（更新现有 PR #7，未创建 PR #8）。
- 主审计提交：`62d2422958d050b553bfc2780a19b14b4db4dca6`，已推送；推送后 `origin/codex/r0-06-idc-v25-integrity` 与该 SHA 一致。核验时 PR #7 为 OPEN / Draft / 未合并，base `codex/r0-05-tcia-full-dicom-audit`，head `codex/r0-06-idc-v25-integrity`；PR #6 保持原状态及 SHA。此后追加本 TASK_RESULT r2 回传记录作为 follow-up。
- 本轮变更文件：`scripts/r0/audit_tcia_v25_integrity.py`、`tests/test_tcia_v25_integrity.py`、`evidence/r0/tcia_v25_integrity_profile.json`、本报告、`docs/project/02-DATASET_EVIDENCE_REGISTER.md`、`docs/project/08-RESEARCH_STATE.md`，以及本 TASK_RESULT。

### 8. 下一项候选

仅建议 Main 另行评估是否启动 `CMRL-07`：核验 TCIA 原始研究、ROI 标注定义、采集时点及 Clinical XLSX 来源和字段。本轮没有启动该任务。MRI 处理/空间质控、分割、Radiomics、训练与临床解释仍由用户亲自实践。
