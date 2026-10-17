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
| V8 Git / 报告 | 待交付 | 完成提交、推送与 Draft stacked PR 后补记 |

## 7. 产物与 Git 交付

- `reports/r0/CMRL-06-IDC-v25逐Series及对象完整性补证.md`
- `evidence/r0/tcia_v25_integrity_profile.json`
- `scripts/r0/audit_tcia_v25_integrity.py`
- `tests/test_tcia_v25_integrity.py`
- `reports/r0/CMRL-06-TASK_RESULT.md`
- `docs/project/02-DATASET_EVIDENCE_REGISTER.md`
- `docs/project/08-RESEARCH_STATE.md`

执行分支为 `codex/r0-06-idc-v25-integrity`，base 为 PR #6 head 分支 `codex/r0-05-tcia-full-dicom-audit`。提交 SHA、推送后 remote SHA 及 Draft PR 编号/状态将在最终回传中填写；不合并、不转 Ready。

## 8. 下一项建议

由 Main 另行决定是否创建候选 `CMRL-07`：核验 TCIA 原始论文、子宫/肿瘤 ROI 语义、采集时点与 clinical XLSX 字段/许可来源。**本任务没有执行该项，也不据此冻结唯一数据集。** MRI/分割/Radiomics/训练与临床解释核心仍由用户本人实践。
