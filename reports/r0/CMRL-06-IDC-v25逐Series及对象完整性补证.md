# CMRL-06｜IDC v25 逐 Series 映射与对象完整性补证

**Plan:** CMRL-Plan-06 r1 · **日期：** 2026-10-17 · **研究阶段：** R0-DATA-ACCESS-AUDIT（R0 NOT COMPLETE）

## 结论

- **索引来源/版本：** `SOURCE_VERSION_VERIFIED`。使用 IDC 官方 `idc-index-data` Release `25.0.0` 固定 Parquet 发布资产，校验官方 GCS SHA-256 sidecar，并验证 Parquet 内嵌版本 `25.0.0-0-gdbf7fd0`。索引字段、发布号与目标 collection machine ID 均经现场核验。
- **Manifest / Series：** `MAPPING_VERIFIED`。821 条 manifest 前缀与官方 collection 的 821 个唯一 Series UID 一对一对应，未映射、歧义、重复和索引外 Series 均为 0。
- **本地逐 Series：** `INSTANCE_COUNT_GAPS_FOUND`。完成 130,424/130,424 个本地文件的最小 Header 扫描；821 个期望 Series 中 806 个本地出现、15 个本地缺失。73 个 Series 的唯一 SOP 数低于索引 `instanceCount`，合计短缺 1,132 个实例；748 个 Series 数量相等，超额为 0。
- **远端逐对象：** `REMOTE_LIST_UNAVAILABLE` / `OBJECT_INVENTORY_NOT_VERIFIED`。两次匿名 `ListObjectsV2` 尝试均未取得响应页；总响应字节 0，成功列举前缀 0。对象名/大小、对象内容 SHA 均未核验。
- **61 条 RTSTRUCT 未命中 SOP 引用：** 仍为 `UNKNOWN`。当前 Series-level index 不提供这些 SOP UID 到 S3 object key 的权威交叉表，远端 LIST 也未返回对象。

以上结论不证明远端当前对象存在或不存在，不证明本地内容与 IDC 对象逐位相同，也不验收 MRI 像素空间、RTSTRUCT 的肿瘤语义或临床标签。Main 尚未接受数据证据；R0 不得收口。

## 官方来源、版本与集合身份

执行时读取 IDC 官方 GCS 固定版本资产，不使用 `current`：

| 资产 | Release / 内嵌版本 | 字节数 | SHA-256 | 校验 |
|---|---|---:|---|---|
| `idc_index.parquet` | `25.0.0` / `25.0.0-0-gdbf7fd0` | 74,108,345 | `450598d6493d800334a8e1ece1fda4a5ec04ca1bd2f73309058f0531f8155572` | 与官方 `.sha256` sidecar 一致 |
| `collections_index.parquet` | `25.0.0` / `25.0.0-0-gdbf7fd0` | 102,477 | `97e5ac3bba296cb3f4e9d87545231275aad66fc89ba07262b7914e72e857489c` | 与官方 `.sha256` sidecar 一致 |

主索引包含 1,044,191 行、31 列，含 Plan 要求的 `collection_id`、`SeriesInstanceUID`、`instanceCount`、`series_aws_url`，以及 Modality、Study UID、大小、CRDC Series UUID 和系列版本字段。发布版 `collections_index` 以 `CC-Tumor-Heterogeneity` 对应机器 ID `cc_tumor_heterogeneity`，仅命中一条集合行；本审计没有把 CRDC UUID、S3 路径前缀和 DICOM UID 当作同一字段。

目标 collection 在固定 v25.0.0 主索引中有 821 行、821 个唯一 Series UID，`instanceCount` 合计 131,556。模态 Series 行数为 MR 523、CT 65、PT 68、REG 97、RTSTRUCT 68。系列级 `series_init_idc_version` 和 `series_revised_idc_version` 在这 821 行均为 15；这是系列首次出现/最近修订版本字段，不是主索引快照版本。权威快照身份来自固定 Release 25.0.0 资产、sidecar 与内嵌版本。

用户指定 manifest 为 52,045 bytes，SHA-256 与 CMRL-05 记录一致，标注 IDC Data Release 25.0（2026-10-01），包含 821 条唯一源前缀。对每一条官方 `series_aws_url`，审计限制为同一 `idc-open-data` bucket 下的路径边界匹配；URL 路径可位于 manifest 前缀子路径内。821/821 命中且不存在歧义，因此没有用“行数接近”或 `crdc_series_uuid` 替代 URL 连接。

官方 IDC 的索引字段说明 `instanceCount` 是 Series 实例数、`series_aws_url` 是系列级公开批量 URL；IDC 的版本文档说明数据集会随版本变更，应以具体版本复现。官方 Release 25.0.0 发布页记录该 tag 及其提交；TCIA 公开页面另列 821 Series、131,556 images、28.39 GB（2023 页面口径）。这两个公开计数与 v25.0.0 索引一致，但大小显示口径不替代本地对象级比对。

## 本地只读 Header 对照

本轮读取真实数据目录的文件元数据与最小 DICOM Header，未解码 PixelData。标签限于 `SeriesInstanceUID`、`SOPInstanceUID`、`Modality`、`StudyInstanceUID`，标准解析，不使用 `force`。运行环境为 Python 3.14.6、pydicom 3.0.2、DuckDB 1.5.6、PyArrow 26.0.0。完整扫描耗时未由首轮 runner 单独写入 profile；扫描完成且未触及 150,000 文件/20 分钟止损条件。

| 指标 | 结果 |
|---|---:|
| 本地普通文件 / 总字节 | 130,424 / 28,151,425,416 |
| 标准 Header 成功 / 解析失败 | 130,424 / 0 |
| 缺失 Series UID / SOP UID、零字节文件、重复 SOP 文件 | 0 / 0 / 0 / 0 |
| 本地唯一 Series | 806 |
| 期望 Series / 本地命中 / 缺失 / 非预期 | 821 / 806 / 15 / 0 |
| Series 实例数相等 / 短缺 / 超额 | 748 / 73 / 0 |
| 期望实例 / 本地唯一 SOP / 短缺 / 超额 | 131,556 / 130,424 / 1,132 / 0 |

本轮前后本地目录 metadata snapshot 均一致：文件数 130,424、总字节 28,151,425,416；未计算内容哈希，故这不是位级不变性证明。第二次只读文件名/大小盘点也未读文件正文，且前后 snapshot 一致。本地文件名 basename 重复组数为 0，但远端对象名未取得，所以它不能验证远端命名对应关系。

TCIA 官方页面报告该 Collection 的 2023 发布统计为 821 Series、131,556 images、28.39 GB。v25.0.0 的两项计数与之相同；本地 130,424 个文件比索引少 1,132 个。由于具体 archive 对象未从 S3 获得，本报告把缺项严格表述为“相对 v25.0.0 Series instanceCount 的本地短缺”，没有把远端当前不存在当作事实。

## 公开 S3 对象清单尝试

在来源、版本、映射和本地 Header 对照门槛成立后，只尝试对 manifest 授权前缀执行匿名 `ListObjectsV2`；不发起 `GetObject`、HEAD、下载或凭据访问。第一次请求快速返回 `URLError`；第二次诊断请求建立到本机出站代理的连接但持续无响应，整体重试过程超过四分钟后手动终止。两次请求均没有 HTTP 状态、成功页或响应字节。累计 2 次请求、0 页、0 bytes，未超过 2,000 次 / 256 MiB / 30 分钟预算；没有继续重试。

所以远端对象数、大小、缺失/额外对象名和逐对象文件大小差异均为 **NOT VERIFIED**，不是 0。即使未来 LIST 得到相同大小，也不会自动成为 SHA-256/位级完整性证据；本任务没有 ETag 或内容哈希证据。

## RTSTRUCT 引用、隐私与限制

CMRL-05 的 61 条本地未命中 RTSTRUCT SOP 引用在本任务仍不能归类为远端存在、Release 外对象或下载缺失；保留 `UNKNOWN`。没有为这些引用读取或推断 ROI 临床含义，也没有读取 clinical XLSX。

为了避免真实 UID、文件名或 S3 key 出现在仓库，第一轮扫描只保留聚合统计。只检查 CMRL-05 的两个候选 JSON 后，未找到可复用的 Series UID 私有映射；没有为生成另一份逐 Series UID 缺口文件而重复读取全量 Header。公共 JSON 和报告不含真实 Series/SOP UID、PatientID、文件名、源前缀、对象键或病例稳定哈希。原始 DICOM 未修改、复制或下载。

## 验证与来源

- 新增 12 项全合成单元测试：固定版本/校验、桶和 URL 规范化、父级前缀匹配、歧义、实例短缺/超额、LIST 分页/拒绝、文件名冲突、对象大小差异、隐私序列化和私有 gap-list 构造均通过。
- `python -m py_compile scripts/r0/audit_tcia_v25_integrity.py` 通过。
- 数据文件原始哈希、像素解码、临床工作簿、SOP-to-object 权威交叉表与对象正文均未读取。

官方来源：

- [IDC idc-index-data Release 25.0.0](https://github.com/ImagingDataCommons/idc-index-data/releases/tag/25.0.0)
- [IDC 固定 v25.0.0 主索引及校验 sidecar](https://storage.googleapis.com/idc-index-data-artifacts/25.0.0/release_artifacts/idc_index.parquet) · [SHA-256](https://storage.googleapis.com/idc-index-data-artifacts/25.0.0/release_artifacts/idc_index.parquet.sha256)
- [IDC 固定 v25.0.0 collection 索引及校验 sidecar](https://storage.googleapis.com/idc-index-data-artifacts/25.0.0/release_artifacts/collections_index.parquet) · [SHA-256](https://storage.googleapis.com/idc-index-data-artifacts/25.0.0/release_artifacts/collections_index.parquet.sha256)
- [IDC index 字段参考](https://idc-index.readthedocs.io/en/latest/indices_reference.html) · [IDC 数据版本说明](https://learn.canceridc.dev/data/data-versioning)
- [TCIA CC-Tumor-Heterogeneity 公开页](https://www.cancerimagingarchive.net/collection/cc-tumor-heterogeneity/)

## r2 附录｜按模态缺口与本机私有差异表（2026-10-17）

### 执行范围与快照

本附录按外部 Plan r2 接续 CMRL-06/r1，没有创建新任务号。复用已经核验的 IDC Release 25.0.0 主索引、集合索引及 821/821 manifest 映射；没有抓取新索引、访问 S3、发起 HEAD/GetObject 或读取临床信息。本轮只进行了一次完整的最小 DICOM Header 扫描，标签限于 Series/SOP UID、Modality、必要的 Study 键；使用 `stop_before_pixels=True`，不解码 PixelData、不解析 RTSTRUCT 轮廓、不计算内容哈希。扫描时间 279.886 秒；运行环境 Python 3.14.6、pydicom 3.0.2、DuckDB 1.5.6、PyArrow 26.0.0。pydicom 通过已有忽略环境的进程级 `PYTHONPATH` 复用，未安装或更改依赖。

本地 metadata 快照前后均为 130,424 个文件、28,151,425,416 bytes、1,017 个目录；reparse 与特殊非普通条目计数均为 0，扫描文件数与盘点一致，快照判定一致。原始数据未复制、移动、重命名、删除或修改。此项是文件元数据快照，不是内容哈希或逐文件字节不变证明。r2 网络请求数为 0；r1 的两次匿名 LIST 失败仍是历史事实。

### 五模态数量对照

分类权威是固定 IDC v25.0.0 主索引的官方 Modality。`equal_count_series` 只表示唯一 SOP 数量相等，不代表内容完整或影像空间质量通过。

| Modality | Expected Series | Local matched | Missing Series | Equal count | Partial shortage | All shortage | Shortage Series total | Expected instances | Observed unique instances | Shortage instances | Excess instances |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| MR | 523 | 523 | 0 | 468 | 55 | 0 | 55 | 93,308 | 92,508 | 800 | 0 |
| CT | 65 | 65 | 0 | 64 | 1 | 0 | 1 | 21,740 | 21,637 | 103 | 0 |
| PT | 68 | 68 | 0 | 66 | 2 | 0 | 2 | 16,343 | 16,129 | 214 | 0 |
| REG | 97 | 87 | 10 | 87 | 0 | 10 | 10 | 97 | 87 | 10 | 0 |
| RTSTRUCT | 68 | 63 | 5 | 63 | 0 | 5 | 5 | 68 | 63 | 5 | 0 |
| **Total** | **821** | **806** | **15** | **748** | **58** | **15** | **73** | **131,556** | **130,424** | **1,132** | **0** |
| UNKNOWN/INVALID | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

模态缺失/无效、Series 内混合 Header Modality、Header 与官方 Modality 冲突、非预期本地 Series、缺失 Series/SOP UID、解析错误、零字节文件、重复 SOP 均为 0。五模态合计与 r1 已接受的聚合基线一致，状态为 `RECONCILIATION_VERIFIED`，`all_modalities_explained=true`。

### MRI 与 RTSTRUCT 的数量层面影响

MR 的 Series 数为 523/523，但 55 个 MR Series 存在部分实例短缺，共少 800 个实例；因此这 55 个 Series 暂时不进入首轮实验候选池，直到本机差异得到解释。另有 468 个 MR Series 仅在计数层面相等；仍需用户后续亲自执行像素解码、切片排序、spacing/direction 与空间质控，不能由计数相等推断 MRI 体完整。

RTSTRUCT 有 63/68 Series 本地命中且数量相等，另有 5 个 Series 完全缺失，共少 5 个实例。此结果不说明这 5 个 Series 与 CMRL-05 的 61 条未命中 SOP 引用有对应关系；该 61 条引用仍为 `UNKNOWN`。本轮没有做 ROI 语义、Mask 或临床标签判断。

### 私有差异表、远端证据与边界

同一次 Header 扫描同时生成了 73 行逐 Series 私有差异表，公开 profile 仅保留已生成布尔值、行数和忽略目录范围标记。`git check-ignore` 验证其位于本机 Git 忽略范围。UID 与 source-prefix 明细不写入仓库或本报告；不执行自动补下载。

r1 的 `REMOTE_LIST_UNAVAILABLE` 仍保留；r2 不产生远端对象库存证据。对象名映射、对象数量/大小仍 `NOT VERIFIED`，位级完整性仍 `NOT VERIFIED`。CMRL-05 的 61 条 RTSTRUCT 引用仍为 `UNKNOWN`。本次结果只补充按模态 Series/实例数量和供后续本机定位的私有映射，Main 尚须独立复核证据；R0 仍为 `NOT COMPLETE`。

全仓库 45 项合成测试通过，审计脚本 `py_compile` 通过；实际聚合 reconciliation、raw metadata snapshot、私有表行数/忽略状态及既有远端证据边界断言均通过。完整 Git 与 PR #7 最终交付状态记录于 `CMRL-06 TASK_RESULT` 的 r2 补记。
