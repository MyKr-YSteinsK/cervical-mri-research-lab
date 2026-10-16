# CMRL-01｜FlexFair 公开数据包文件级准入审计

- **审计日期：** 2026-10-16（UTC）
- **任务：** `CMRL-01`，依照 `plans/CMRL-01-FlexFair公开数据包文件级准入审计.md`（r1）
- **研究阶段：** R0；本次完成文件级调查，**不表示 R0 完成或进入 R1**。
- **任务分支：** `codex/r0-01-flexfair-archive-audit`，从 `codex/r0-00-data-access-audit` 的 `c845b689289897d23d167846519f73ae001630d2` 派生。

## 结论摘要

D01 的官方 Figshare ZIP 已完整下载，字节数和公开 MD5 匹配；ZIP 可安全枚举，6732 个文件全部为 PNG。包内有 3366 个影像侧栅格文件、3366 个 Mask 命名候选，按可复现的文件名规则得到 3366 组唯一候选配对。抽取其中一对到被忽略的本地 `data/` 后，两张 PNG 均可解码且尺寸一致（640×640）；Mask 为单通道 8-bit 灰度图，观察到 2 种像素值。

包内没有可识别的 manifest、拆分表或病例/中心映射；文件名也没有识别出患者/中心键。因而**文件级 Image+Mask 格式检查通过，但患者身份、中心归属、患者级去重与训练/测试拆分均未验证**。作者描述的 678 名患者和四中心仍无法映射到包内图像；文件侧的 3366 个影像文件不能据此解释为 3366 名患者、完整 3D 序列或独立样本。

| 用途 | 当前准入建议 | 依据与限制 |
|---|---|---|
| 2D 分割 | **CONDITIONAL** | 存在可解码的 PNG Image+Mask 候选配对；患者键、病例级拆分、Mask 临床语义及文件级重复规则未核实。Main 审查前不启动训练。 |
| 3D 分割 | **NO-GO** | 归档只含 PNG；没有 DICOM、NIfTI、NRRD 或 MetaImage 文件，也没有可用的体积空间元数据。 |
| Radiomics | **NO-GO（体积级）；2D 未准入** | 当前发布包未提供可核验的 3D 体数据、毫米 spacing、方向或 origin；二维特征提取也未评估，须先明确像素间距、标注语义与特征方案。 |
| Cross-site | **NO-GO** | 无可信中心键或患者到中心映射，不能做站点分层、跨中心留出或公平性结论。 |

**调查完成状态与数据准入状态分开：** 本次 D01 文件级调查已完成；数据仍未达到可训练或跨中心验证的 GO 条件。项目 `R0` 仍为 `NOT COMPLETE`，由 Main 决定后续研究门槛。

## 1. 来源、许可与基线对照

- 官方 [Figshare article 28639598](https://springernature.figshare.com/articles/dataset/Achieving_Flexible_Fairness_Metrics_in_Federated_Medical_Imaging/28639598) 对应 DOI `10.6084/m9.figshare.28639598.v1`，版本 1，标题为 *Achieving Flexible Fairness Metrics in Federated Medical Imaging*。本次于 **2026-10-16 10:22:19 UTC** 查询官方 API，记录为一项公开文件 `CervicalCancerDataset.zip`，file ID `53159216`、大小 `348,731,016` bytes、`computed_md5=303ae54703fdccc63302cb755aed792a`，许可标示 **CC BY 4.0**。
- 以上文章、单文件、大小、MD5 和许可与 CMRL-00 留存的 Figshare 元数据一致。CMRL-00 对另一个候选 ID `28636133` 的 404 是独立旧观察；本次没有据此推断原因，也没有下载其他来源或镜像。
- [Nature Communications 论文](https://www.nature.com/articles/s41467-025-58549-0) 与 Figshare 描述支持“678 名患者、四中心”的作者发布口径；这不是包内身份映射的验证。原论文的采集说明包含轴位 T2 加权 MRI 与肿瘤 ROI，但本地归档实际格式以本报告的 ZIP 检查为准。
- 用户提供的 Plan 源文件在执行前复核时已从其原路径消失。仓库中的 Plan 文件是根据已完整读取的附件内容重建的工作副本；未与源附件做字节比较。执行范围仍以用户所启动的这份 r1 合同内容为准。

## 2. 下载和完整性（V1–V2）

- 下载对象仅为上述官方 Figshare 文件。官方 API 返回 6191-byte 元数据正文；下载未使用认证、Cookie 或私人凭据。最终重定向到 S3 对象路径 `https://s3-eu-west-1.amazonaws.com/pstorage-npg-968563215/53159216/CervicalCancerDataset.zip`；没有保存带查询参数的重定向 URL。
- 预检 HEAD 返回 HTTP 403（未读取正文）；1-byte Range 探测返回 HTTP 206 和 `Content-Range: bytes 0-0/348731016`。第一次完整 GET 返回 HTTP 200，但正文在 **69,312,040 bytes** 处结束；文件仅留为 `.part`，未被称为完整数据或提升为正式 ZIP。
- 随后对现有偏移做 1 KiB Range 探测，服务器精确返回 `bytes 69312040-69313063/348731016`。之后以 **17 个** 206 Range 请求补齐剩余 `279,418,976` bytes；每段的 `Content-Range`、`Content-Length` 和对象路径均与请求一致。未重新从头下载，也没有失败后重试。
- 文件落盘为 **348,731,016 bytes**，与官方预期一致。官方 MD5 **匹配**：`303ae54703fdccc63302cb755aed792a`。SHA-256：`4efdfa6b6dbf4174a1b7ce2b0eb8878e739f0365829a89d57fdf5223c82817ec`。续传区间从 `2026-10-16 10:32:25 UTC` 开始，耗时约 **1038.61 s**。已知响应正文累计 **348,738,232 bytes**（包含 API 与两次 Range 探测；不含 HTTP 头及未读取的 HEAD 正文）。
- 续传前 D: 卷空闲 **150,813,462,528 bytes**，下载后约 **150,534,000,640 bytes**，均高于 Plan 要求的 5 GiB。正式 ZIP 位于 Git 忽略的 `data/raw/flexfair/`。

传输和归档的脱敏机器汇总见 [`evidence/r0/flexfair_archive_profile.json`](../../evidence/r0/flexfair_archive_profile.json)；该证据记录了未完成 GET、Range 探测与续传、落盘哈希及卷空间。

## 3. ZIP 安全与文件结构（V3）

离线脚本 [`scripts/r0/audit_flexfair_archive.py`](../../scripts/r0/audit_flexfair_archive.py) 先核文件大小和 MD5，再用 Python `zipfile` 枚举 central directory；没有整包解压或执行归档内容。归档结构检查结果：

- ZIP 可打开；**6743** 个条目（**6732 个文件、11 个目录条目**）。6732 个文件扩展名均为 `.png`。
- 文件声明的未压缩总量 **349,883,720 bytes**；压缩数据总量 **347,443,592 bytes**；最大单文件压缩比 **7.1069**，低于 1000 的停止阈值；未压缩总量低于 8 GiB 限额。
- 未发现绝对路径、路径穿越、畸形路径、符号链接或特殊文件、重复/大小写冲突路径、加密成员、未知压缩方法或零压缩大小异常。**CRC 全包检查已运行并通过**。
- 文件名和病例/中心值不输出。安全摘要只保存了白名单扩展名、受限顶层逻辑分类和匿名计数。

## 4. Image+Mask 与最少样本读取（V4）

- 按文件名与目录中的 `image`/`mask`/`seg`/`label` 等角色标记，得到 **3366** 个非 Mask 栅格候选、**3366** 个 Mask 命名候选；经规范化角色词后的唯一文件名配对候选为 **3366** 组，没有歧义冲突。该配对是文件名规则支持的候选关系，不等于 DICOM 空间配准或患者身份映射。
- 脚本按排序后第一个唯一候选，在完整 ZIP CRC 通过后只提取一对到 `data/raw/flexfair/audit_sample/`，使用通用文件名保存，不输出成员原名或像素值。两者均能由 Pillow 解码：格式 PNG，尺寸均为 **640×640**，mode `L`，单通道、8-bit unsigned。该 Mask 有 **2 种**不同灰度像素值；只统计数量，没有输出具体值或像素内容。
- 样本仅证明一对文件可打开且基础二维尺寸相同；不证明真实解剖学空间对齐、ROI 临床含义或整个包的标注正确性。抽样文件与完整 ZIP 均留在 `.gitignore` 排除的本地 `data/`。

## 5. 患者键、中心键及 678/3366 口径（V5）

- 未发现 CSV、TSV、JSON 或表格候选 manifest/split/mapping 文件；没有可审查的患者级或中心级映射表。文件名也没有识别到显式 patient/subject/case/site/center 编号模式。
- 因此，患者键证据仅到“文件名角色及候选配对”层级；**没有可信 patient ID、site ID、患者到中心映射或患者级 split**。无法对重复患者、同人跨拆分或中心内患者数作可靠计数。
- 发布说明的 **678 人、四中心** 与本次实测的 **3366 个影像侧 PNG** 之间没有包内映射可供核验。包内 3366 个影像侧文件与 CMRL-00 曾记录、但当时未独立验证的 1383/1332/323/328 算术总数一致；这个吻合只是一项文件计数观察，不证明那些数值分别代表中心、患者、序列或切片。**678 名患者与 3366 个文件的样本关系标记为 `UNRESOLVED`。**

## 6. 数据准入与下一步边界

1. 当前只可建议 Main 审查是否给用户安排一个**用户亲自执行**的二维 PNG/Mask 读取与标注语义检查任务。接下来应由用户结合学习目标检查本地样本、目录组织和实际拆分策略；不能从文件名推导患者级无泄漏拆分。
2. 3D 分割和体积级 Radiomics 暂不准入：本包的文件实测均为 PNG，未发现可识别的 DICOM/NIfTI/NRRD/MetaImage 体数据或可核验的医学空间信息。二维 PNG 的像素矩阵不构成毫米 spacing、orientation 或 origin 的体积依据；本次也未评估 2D Radiomics。
3. Cross-site 与公平性评估暂不准入：未建立患者到站点的可信键，无法验证分站点人数、重复患者或站点留出。
4. Codex 本次只完成来源/许可、下载、ZIP 安全、聚合清单和单对格式检查；没有编写或运行分割、影像预处理、Radiomics、模型训练或评价代码，也没有把任何样本/临床值发送到外部服务。
5. `docs/project/08-RESEARCH_STATE.md` 按 Plan 只做一次最小事实同步，并明确 `R0 NOT COMPLETE`。根目录 `AGENTS.md` 以及 `docs/project/01`、`04` 保留其历史 CMRL-00 专项授权原文；当前 CMRL-01 的独立、有限支持权限来自用户启动的自包含 Plan，不据此扩大未来 Codex 授权。

## 7. 隐私和复现

- Git 只包含审计代码、经规则审查的汇总 JSON、报告及项目状态说明。完整 ZIP、两张泛化命名的抽样 PNG、TCIA 临床工作簿均在被忽略的 `data/` 中；没有提交文件清单、原成员路径、病例标识、像素值或凭据。
- 复核本地文件是否被 Git 排除：`git check-ignore -v data/raw/flexfair/CervicalCancerDataset.zip data/raw/flexfair/audit_sample/sample_image.png data/raw/flexfair/audit_sample/sample_mask.png`。
- 从仓库根目录重新运行本地结构审计：

  ```powershell
  python -X utf8 scripts/r0/audit_flexfair_archive.py data/raw/flexfair/CervicalCancerDataset.zip --extract-one-pair
  ```

- 本任务的工作分支依赖 CMRL-00 审计分支；远端状态为 [Draft PR #2](https://github.com/MyKr-YSteinsK/cervical-mri-research-lab/pull/2)，base 是 `codex/r0-00-data-access-audit`，PR #1 仍为 Open/Draft/未合并。详见同目录的 [`CMRL-01-TASK_RESULT.md`](CMRL-01-TASK_RESULT.md) 与最终交付回执。本次不合并 PR。
