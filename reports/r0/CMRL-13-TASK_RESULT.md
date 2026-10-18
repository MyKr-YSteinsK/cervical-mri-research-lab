# TASK_RESULT｜CMRL-13｜IDC v25 CCTH 缺失 Series 定位与 RTSTRUCT 小规模补全验证

## 状态

**COMPLETE（缺口 UID 对照与一个 RTSTRUCT Series 下载试验完成）**。本任务没有把试验文件并入正式数据目录，也没有补齐其他缺口。CMRL-11 的正式本地 Manifest 仍代表下载试验前的数据树；研究阶段仍为 **R0 NOT COMPLETE**。

## 范围与证据基线

- 工作分支：`codex/cmrl-13-ccth-recovery-pilot`，从 CMRL-11 已提交分支快照 `9e67912479353a48126d66362c2ec51c521d5ba8` 建立。
- IDC 对照固定为 CMRL-06 已核验的 `idc-index-data` Release `25.0.0`；本地固定 Parquet 为 74,108,345 bytes，本轮 SHA-256 与 CMRL-06 记录的官方校验值一致。未改用当前最新版索引。
- 本地事实来自 CMRL-11 的 `directories.csv`、`series.csv` 和 `files.csv`；官方缺口来自 CMRL-06 的忽略目录 UID 级差异表。只读取所需字段，没有重建全库 Manifest。
- 原始 DICOM 数据目录未作为下载目标；试验输出写入 Git 忽略的 `.local/ccth-recovery-pilot/`。

## 15 个空 Series 目录的精确对照

对照键为 DICOM `SeriesInstanceUID`。逐条比较本地空目录名、CMRL-11 Series Manifest、CMRL-06 固定 v25.0.0 Series 索引和私有缺口表后，15/15 个目录 UID 均唯一映射至官方缺失 Series；Study UID 与目录父级一致，官方 Modality 与目录前缀一致，本地 Series Manifest 均无该 UID。此结论来自 UID 对照，不是由目录数相等推断。

15 个 Series 的官方预期实例数均为 1，本地实例数均为 0。病例别名是公开目录别名；表中不含 UID 或患者级目录路径。

| 病例别名 | 模态 | 缺失 Series 数 | 官方预期实例 | 本地实例 | 官方索引体量估算（bytes） |
|---|---|---:|---:|---:|---:|
| A07 | REG | 1 | 1 | 0 | 94,460 |
| A07 | RTSTRUCT | 1 | 1 | 0 | 130,766 |
| A08 | REG | 3 | 3 | 0 | 284,048 |
| A09 | REG | 1 | 1 | 0 | 95,706 |
| A09 | RTSTRUCT | 1 | 1 | 0 | 192,472 |
| A10 | REG | 3 | 3 | 0 | 283,342 |
| A10 | RTSTRUCT | 1 | 1 | 0 | 118,050 |
| A11 | REG | 2 | 2 | 0 | 181,232 |
| A11 | RTSTRUCT | 1 | 1 | 0 | 69,486 |
| A12 | RTSTRUCT | 1 | 1 | 0 | 208,600 |
| **合计** | **REG 10；RTSTRUCT 5** | **15** | **15** | **0** | **1,658,162** |

体量估算来自固定索引 `series_size_MB` 按十进制 MB 换算；其他 14 个 Series 未逐对象列举，因此这些体量仍是官方索引估算，不是本轮实际远端对象清单。CMRL-06 的全模态对账另记录 73 个短缺 Series、共 1,132 个短缺实例；本表覆盖其中 15 个完全缺失 Series。

## 用户提供的 AWS manifest 核验

- 当前文件为 52,045 bytes，SHA-256 `f56073583ad4cf931a9a46fac83af2672f5b0248ebcc2a94406e9f662508ee79`，与 CMRL-06 TASK_RESULT 记录相同。
- 解析得到 821 条唯一 AWS Series 前缀命令；与固定 v25.0.0 的 821 个 Series 前缀逐条比对，覆盖 821/821。15 个空目录对应的 15 个前缀全部存在，A11 RTSTRUCT 前缀也存在。
- 821 条命令均为 `cp <AWS Series 通配前缀> .`。manifest 没有固定本地数据根目录；若直接运行这些 s5cmd 命令，`.` 取决于启动命令时的当前目录。实际使用的下载器参数、工作目录和下载日志不在本任务证据中，所以无法确认当时是否把对象写入预期位置。
- 因此，现有证据不支持“manifest 漏掉这些 Series 前缀”；但 `.` 目标使落盘位置依赖执行上下文，仍有可能造成对象未进入本地数据树。具体下载中断或落盘原因仍未核实。

## 单 Series 匿名下载试验

- 候选：病例公开别名 A11 的 RTSTRUCT；固定索引预期 1 个实例、69,486 bytes，低于 128 MiB 预算。
- 使用固定 v25.0.0 `series_aws_url` 对应的 IDC 公共 AWS 桶，匿名执行一次 S3 `ListObjectsV2`，HTTP 200，响应 785 bytes，列出 1 个对象、69,486 bytes；对象数量和体量与固定索引相符。
- 对该对象执行一次匿名下载，HTTP 200，写入 69,486 bytes，下载耗时 1.431 秒。AWS 列举耗时 1.280 秒。AWS 已成功，未尝试 Google Cloud 镜像；未使用凭据、未安装工具。
- 下载器使用 Python 标准库直接访问索引指定的公开 AWS 对象前缀；DICOM 解析复用本机 pydicom 3.0.2。IDC 官方文档列出按 Series/manifest 下载方式及公开 AWS/GCS 访问路径，见文末来源。

## 文件级验证

- 试验目录内 1 个非空文件，数量与索引预期一致；`pydicom.dcmread(force=False, stop_before_pixels=True)` 标准 Header 解析成功，未解码 PixelData。
- SOP Class、Modality、Series UID 均与固定 v25.0.0 索引预期一致。下载对象的 SOP Instance UID 与 CMRL-11 原始 `files.csv` 中 130,424 个本地实例均不重复。
- 未发现额外文件、零字节文件或 Header 解析错误。
- IDC 未提供本次对象的逐对象权威校验和。本轮未计算或宣称位级完整性；证据状态为 **SOURCE AND OBJECT IDENTIFIERS MATCH**，**BITWISE INTEGRITY NOT VERIFIED**。

## 停止点与后续边界

- 试验对象保留在忽略目录 `.local/ccth-recovery-pilot/`；未写入、覆盖或删除 `data/raw/tcia/` 下文件，未将试验对象并入正式数据集。
- 未下载其余 14 个空 Series，也未处理 58 个部分短缺 Series；正式数据树仍保留 CMRL-06 所记 1,132 个实例缺口。未重新生成全库 Manifest。
- 这次成功验证了一个小型 RTSTRUCT Series 的匿名公开访问、数量与 Header 标识核对，说明后续可以设计受预算约束的批量补全方案；它没有验证其余 1,131 个实例的远端对象、大小、完整性或可下载性。任何批量补全须由后续任务单独授权并逐 Series 核定预算与对象映射。
- 本任务没有执行像素解码、影像几何/空间质控、ROI 语义或临床字段分析；不表示 CMRL-11 的研究候选准入、R0 完成或 CMRL-12 单病例 MRI 质控通过。

## 官方来源

- [IDC 官方数据下载入口](https://learn.canceridc.dev/data/downloading-data)
- [IDC 官方 s5cmd 下载与 AWS/GCS 端点说明](https://learn.canceridc.dev/data/downloading-data/downloading-data-with-s5cmd)
- [IDC `idc-index-data` Release 25.0.0](https://github.com/ImagingDataCommons/idc-index-data/releases/tag/25.0.0)
- 固定版本索引与完整性核验细节见 [CMRL-06 报告](CMRL-06-IDC-v25%E9%80%90Series%E5%8F%8A%E5%AF%B9%E8%B1%A1%E5%AE%8C%E6%95%B4%E6%80%A7%E8%A1%A5%E8%AF%81.md) 和 [CMRL-06 TASK_RESULT](CMRL-06-TASK_RESULT.md)。
