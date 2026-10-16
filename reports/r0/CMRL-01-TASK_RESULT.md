# TASK_RESULT｜CMRL-01 / r1

- **Status:** `COMPLETE`（文件级调查和授权交付完成；**不代表数据 GO、R0 验收或进入 R1**）
- **日期：** 2026-10-16 UTC
- **仓库：** `MyKr-YSteinsK/cervical-mri-research-lab`（Private）
- **工作目录：** `D:\CS\CMRL`

## V1–V7

| Gate | Status | 结果 |
|---|---|---|
| V1 Source | **PASS** | 官方 Figshare article `28639598` / file `53159216`，CC BY 4.0；大小和 MD5 与 CMRL-00 记录一致。 |
| V2 Transfer | **PASS** | 官方文件完整下载；最终大小、MD5 与 SHA-256 已实测。首次 HTTP 200 流只收到 69,312,040 bytes，未提升为正式文件；通过 17 个范围精确匹配的 HTTP 206 请求续传，没有重头重下。 |
| V3 Archive safety | **PASS** | ZIP 可打开；6732 个 PNG 文件、11 个目录项；体积/压缩比在限额内；安全标志全 false，全包 CRC 通过。 |
| V4 Real image pair | **PASS** | 一组唯一文件名候选已在本地解码；Image 与 Mask 均为 640×640 灰度 PNG，尺寸一致，Mask 有 2 种灰度值。只证明基础文件格式和候选配对。 |
| V5 Identity | **PASS** | 已核查结构化映射文件、文件名模式及患者/中心证据；未发现可信身份键。`678 人 ↔ 3366 个影像文件` 关系仍为 `UNRESOLVED`。此 Gate PASS 表示证据边界已查清，不表示映射存在。 |
| V6 Privacy | **PASS** | ZIP 和两张样本均由 `.gitignore` 的 `/data/` 排除；staged/committed 文件仅为 Plan 工作副本、审计脚本、聚合 JSON、报告和 `08` 状态说明；未提交病例清单、原成员路径、图像、Mask、临床值或凭据。 |
| V7 Delivery | **PASS** | 分支已推送，Draft PR #2 为 Open，目标依赖分支 `codex/r0-00-data-access-audit`；未合并。最终远端 HEAD 见本文件后的聊天交付回执。 |

## 传输与文件审计

- **官方资产：** Figshare article `28639598`，file `53159216`，`CervicalCancerDataset.zip`，许可 CC BY 4.0。
- **文件：** `348,731,016 bytes`；MD5 `303ae54703fdccc63302cb755aed792a`（匹配）；SHA-256 `4efdfa6b6dbf4174a1b7ce2b0eb8878e739f0365829a89d57fdf5223c82817ec`。
- **请求：** metadata API 正文 6191 bytes；HEAD 403（未读取正文）；Range 预检 1 byte；首个完整流提前结束后，1 KiB Range 探测成功，随后 17 个 HTTP 206 范围请求准确续传剩余 `279,418,976 bytes`。累计已知正文传输 `348,738,232 bytes`，低于 800,000,000 bytes；无整包重试。续传从 `2026-10-16T10:32:25Z` 开始，用时 1038.61 s。
- **空间：** 续传前 D: 空闲 `150,813,462,528 bytes`；下载后 `150,534,000,640 bytes`；均高于 5 GiB 门槛。
- **归档：** 6732 文件全部 `.png`；未压缩总量 `349,883,720 bytes`，压缩数据 `347,443,592 bytes`，最大单文件压缩比 `7.1069`；未发现路径穿越、绝对路径、符号链接、重复冲突路径、加密或不支持的压缩方式；全包 CRC 通过。
- **Image/Mask：** 3366 个影像侧栅格候选、3366 个 Mask 命名候选和 3366 组唯一文件名配对候选；未检出 manifest/split/患者/中心映射。单对样本只做了二维解码和尺寸/Mask 像素值数量审计。

## 数据准入状态

| 用途 | 当前状态 |
|---|---|
| 2D segmentation | **CONDITIONAL**：文件级配对及样本解码成立；患者键、无泄漏拆分、Mask 语义和重复规则仍待 Main 审查。 |
| 3D segmentation | **NO-GO**：当前包仅为 2D PNG，没有可验证的医学体数据空间信息。 |
| Radiomics | **NO-GO（体积级）；2D 未评估/未准入**。 |
| Cross-site | **NO-GO**：没有患者到中心的可信映射。 |

**Next Boundary：** 可建议 Main 决定是否让用户亲自完成一个最小本地 PNG/Mask 读取与语义检查任务。Codex 不自行推进 R1–R3，不运行训练、Radiomics 或模型评价。Main 仍负责数据选择与阶段验收。

## Git 与证据

- 分支：`codex/r0-01-flexfair-archive-audit`。
- base 分支：`codex/r0-00-data-access-audit`，base SHA `c845b689289897d23d167846519f73ae001630d2`。
- 首次审计提交：`05e87455a69f878b6396b0e3b741803409e99713`。Task Result/PR 链接补充作为后续提交；最终远端 SHA 在交付回执中给出，避免在提交内容中写入自引用 SHA。
- [Draft PR #2](https://github.com/MyKr-YSteinsK/cervical-mri-research-lab/pull/2)：base `codex/r0-00-data-access-audit`，head `codex/r0-01-flexfair-archive-audit`，Open/Draft/未合并。它依赖 [PR #1](https://github.com/MyKr-YSteinsK/cervical-mri-research-lab/pull/1)，后者在本次确认时仍为 Open/Draft/未合并。
- 主要产物：[`CMRL-01-FlexFair文件级准入审计.md`](CMRL-01-FlexFair文件级准入审计.md)、[`flexfair_archive_profile.json`](../../evidence/r0/flexfair_archive_profile.json)、[`audit_flexfair_archive.py`](../../scripts/r0/audit_flexfair_archive.py)、[`08-RESEARCH_STATE.md`](../../docs/project/08-RESEARCH_STATE.md)。
- 仓库内 Plan 副本根据完整读取的用户附件重建；源附件在复制前消失，故未作字节比较。
