# CMRL-01｜FlexFair 公开数据包文件级准入审计

**任务类型：** Investigation / Research data access / Bounded file inspection  
**Plan Revision：** r1  
**项目：** `Cervical-MRI-Research-Lab`（CMRL）  
**研究阶段：** R0，**不**表示 R0 完成或进入 R1  
**任务身份：** `CMRL-01`；项目 Plan 命名持续使用 `CMRL-NN-中文标题.md`

## 一、任务基线及目标

本任务承接已经由 Main 审查并接受**调查交付范围**的 `CMRL-00 / r2`，不是重新做网页级审计。

**已核实的 Git 身份（启动时重新验证）：**
- 仓库：`MyKr-YSteinsK/cervical-mri-research-lab`，Private。
- `CMRL-00` 审计分支：`codex/r0-00-data-access-audit`。
- 审计 HEAD：`c845b689289897d23d167846519f73ae001630d2`。
- PR #1：`https://github.com/MyKr-YSteinsK/cervical-mri-research-lab/pull/1`，Main 审阅时仍为 Draft / 未合并；开始时不得假定已合并。
- 参考证据：`reports/r0/CMRL-00-三候选数据准入审计.md`、`evidence/r0/public_source_metadata.json`、`docs/project/01`–`08`、根目录 `AGENTS.md`、`plans/CMRL-00-科研仓库初始化与候选数据准入审计.md`。

**D01 来源事实（不是文件级验收）：** 官方 Figshare article `28639598` 提供 `CervicalCancerDataset.zip`，记录大小 **348,731,016 bytes**，`computed_md5=303ae54703fdccc63302cb755aed792a`，许可页面标示 CC BY 4.0；API `28636133` 在 CMRL-00 观察为 404。论文作者报告四中心 678 名患者，患者数为 89/65/278/246；3,366 张图像样本及其与患者的关系仍未通过实际发布文件核验。

**本次目标：** 在受控预算与合法使用前提下，验证唯一公开 ZIP **真正能够下载、校验并安全枚举内部文件**；若可行，再以最少本地样本检查原始影像与 Mask 是否存在可解释的配对，以及是否有可核验的患者与中心键、2D/3D 属性。回答 D01 适合哪一类首个研究任务，而不是训练模型。

## 二、FROZEN｜授权与研究边界

1. **可进行：** 只读查询 Figshare 官方 API、论文/README；在满足下述硬限额后下载这一**单一已确认的公开 ZIP**到本地被 Git 忽略的 `data/` 目录；安全枚举归档、必要时提取极少量合法真实文件作**文件完整性与格式/配对审计**；生成摘要脚本、聚合报告和可复核证据；在授权任务分支 Commit/Push。
2. **下载硬预算：** 仅允许 D01 `CervicalCancerDataset.zip` 这一个正式公开归档，预期 348,731,016 bytes；最大实际单文件 400,000,000 bytes、累计下载/重新请求传输量不超过 800,000,000 bytes。先检查 Content-Length/官方文件记录与实际落盘大小；不满足则停止。不要同时下载 Google Drive、镜像或其它大包来绕过预算。失败时可以合法低成本探测（HEAD、Range），但不能把不遵守 Range 的服务器当成已成功读取 ZIP 尾部。
3. **磁盘与解压安全：** 下载前检查本地目标卷至少 **5 GiB 空闲**；低于阈值停止并反馈，不擅自清理。优先只读枚举 ZIP central directory，**不要整包解压**。若文件列表声明的未压缩总量超过 8 GiB、异常压缩比、路径穿越（`..`、绝对路径）、符号链接、重复冲突路径、疑似 ZIP bomb 或校验错误，停止提取并保留安全的失败摘要。只按允许目录提取极少量 Image+Mask 对，先核对大小和来源；不执行归档内任何脚本、程序或不可信序列化对象。
4. **隐私与许可：** 私有 GitHub 仓库不等于医疗数据可随意共享。不得将原始 ZIP、图像/Mask、病例级文件清单、患者标识、文件名里的患者/中心组合、临床行值、解压内容、私人数据下载链接中的凭据上传 GitHub、聊天或公开服务。只提交已经人工规则审查的汇总统计、字段存在性、经匿名化的文件命名模式、结构性结论和复现脚本。ZIP、样本、临时日志必须放在 Git ignore 的 `data/` / `.local/`。不得修改 `gitignore` 放宽排除。
5. **教学边界：** Codex 仅负责 R0 数据发布文件的可用性与结构完整性自动化审计。不得代替用户编写、运行或封装分割模型、Radiomics 特征提取、影像预处理/重采样、ROI 可视化教学、DL 训练与评价核心代码。可识别常见栅格文件的像素尺寸、通道数、Mask 文件数量等**格式元数据**；涉及实际医学空间对齐/患者级拆分的深入操作留给 Main 的后续用户实践。
6. **科学边界：** 图像数≠患者数≠切片数；文件名模式≠真实患者映射。没有可信患者键、中心键和去重协议，不宣称 patient-wise/cross-site 评价有效。PNG/JPEG 等 2D 栅格不自动拥有毫米 spacing、方向、origin 或真实 3D 体积。没有真实临床应答标签不构造疗效模型。
7. **Git 权限：** 禁止强制推送、历史改写、自动 Merge、PR 转 Ready、发布/公开仓库或提交大数据。不得覆盖用户未提交改动，不得私自修改其他项目。只有用户或 Main 明确批准后才能合并 PR。
8. **项目权威：** Codex 可以报告文件实测事实、推荐准入类型，**不能批准 R0 验收、宣布进入 R1 或替 Main 选定唯一主数据集**。不修改旧“六篇论文精读”项目。

## 三、RECOMMENDED｜受控工作流

### 1. Preflight：先核实际状态

- 检查工作目录、Git remote、现有改动、分支、可用磁盘、Python 标准库是否足够、网络入口与数据许可证；不预装 PyTorch/CUDA、不构建训练框架。
- 先确认 PR #1 是否已经合并。**若已合并**，从确认后的 `main` 创建 `codex/r0-01-flexfair-archive-audit`；**若尚未合并**，从 `c845b689...` 审计分支 HEAD 派生新的任务分支，PR 目标指向 `codex/r0-00-data-access-audit`，形成显式 stacked PR，避免把旧审计 diff 重复提交给 `main`。不自行合并 PR #1。如远端分支身份不一致、该基线不可用或受用户修改影响，停止受影响 Git 操作并报告。
- 复核单个 Figshare asset 的 article/file ID、文件大小、`computed_md5` 以及许可；保留实际查询时间与重定向 URL，但不要在报告中保存带会话令牌的链接。

### 2. 获取归档与完整性证据

- 优先从 Figshare 官方文件下载入口取得 ZIP；使用流式读取、写入本地临时 `.part`，下载完成后原子改名；不要把整个 ZIP 放入内存。
- 记录请求 HTTP 状态、落盘字节数、实际 MD5（对照公开 `computed_md5`）、额外 SHA-256、下载时长、Range/重试行为与完整/失败原因。不要在失败时将 `.part` 称作合法完整数据。
- 若环境、授权条款、磁盘或网络导致任务无法安全取得 ZIP，**如实保留错误/预算证据后收口**，不扩展到所有备选数据集。

### 3. 只读归档枚举与最小文件审计

- 用 Python 标准库 `zipfile`/`pathlib` 等查看 central directory；优先输出**聚合**文件数量、顶层逻辑目录、扩展名分布、压缩与未压缩总大小、掩膜命名线索、患者键/中心键是否存在及证据可信度（仅名称推断、manifest 或确有明确映射表）。必要时核对单个条目的解压 CRC。不得把未经审查的原始病例 ID 路径上传 Git。
- 若包中有显式 manifest/split/病例映射文件，先验证其来源、语义与结构；在本地建立患者级与中心级**匿名聚合计数**，检查重复键、异常跨度和潜在同人跨拆分证据。不能仅凭 `train/`、`test/` 文件夹推导 patient-wise 隔离。
- 若存在 Image+Mask 成对文件，以最少实例只读检查扩展名、像素尺寸/形状、通道/数值类型、Mask 标签类型及文件对应规则；保留至少一对实际可打开/解码的证据（只在本地），Git 只收聚合摘要。配对成立须有可复核规则，不做影像空间对齐、overlay、模型 Dice 或训练。
- 如果仅为 2D PNG/JPEG，明确不满足三维 spacing 和体积级 Radiomics 的条件；若存在 DICOM/NRRD/NIfTI，仅列出格式证据，不越权完成医学空间质控。
- 研究论文的 678 与作者图像样本统计口径的差异：以发布物实际患者/序列/切片/图片映射为依据；若无法消解，列 `UNRESOLVED`，不要重命名指标。

### 4. 本轮结束时更新合法证据与当前事实

新增并提交：

- `reports/r0/CMRL-01-FlexFair文件级准入审计.md`：来源/许可/预算、ZIP 完整性、归档结构（聚合）、Image+Mask、患者/中心键、研究适用范围及明确阻塞。
- `reports/r0/CMRL-01-TASK_RESULT.md`：执行与交付合同；最终 SHA 在 Push 后聊天回执中补足。
- `evidence/r0/flexfair_archive_profile.json`：**脱敏的聚合**归档统计、审计状态和哈希；失败时真实记录 `UNAVAILABLE`/`NOT_RUN`。
- `scripts/r0/`：最少必要、可阅读的审计脚本，支持无网络情况下对已合法获取 ZIP 做只读本地验证；避免复杂通用框架。

对 `docs/project/08-RESEARCH_STATE.md` 允许进行一次 **Main 已审查事实的最小同步**：将 TCIA 临床工作簿“尚未实际下载”修正为“CMRL-00 已下载公开 XLSX 并完成字段及缺失汇总审计；23 个候选病例键/28 个非空行仍需解释；未核验任何 MRI/RTSTRUCT 或临床结局”，并将 D01 的本任务**确已验证**事实分开记载。明确 `R0 NOT COMPLETE`。若本分支仍基于未合并的 PR #1，说明这些变更需随依赖分支进入 main，不提前声称 main 已更新。

`01/04/AGENTS` 的 Codex 授权只按当前自包含 Plan 生效；如发现原文仍将一切辅助任务仅限于 CMRL-00，报告该过时限制与本 Plan 经用户启动的授权差异；**不要**在本任务顺带大规模重写研究治理条款。

## 四、DELEGATED_TO_CODEX｜现场判断

- 官方下载服务器是否支持稳定 Range/resume，以及有限次数重试如何避免重复大额传输；必须遵守总预算。
- 如何区分文件名命名模式与可靠患者 ID/中心 ID 映射；可设计少量不暴露患者的完整性断言，不猜测映射。
- 文件数量很多时如何利用抽样/聚合而非暴露目录清单；优先完整索引元数据、最小文件解码。
- 若 ZIP 加密/损坏/安全异常/无法下载，决定最有诊断价值且仍在预算内的下一项只读验证。疑似资料敏感或许可不清时停下并报告 Main。

以上仅委托技术路径选择，不扩大下载、Git、数据公开或科研阶段决策权限。

## 五、验收与停止条件

1. **V1 Source：** 实际下载对象能追溯到官方 Figshare 记录与许可；与 CMRL-00 元数据对照并记录差异。
2. **V2 Transfer：** 报告下载成功并有文件实际字节大小、MD5/SHA256、时间/请求证据；失败时具备可核查的网络/空间/预算阻塞说明。**未经下载不得标 FILE-INSPECTED**。
3. **V3 Archive safety：** 完整 ZIP 可只读打开、通过结构/限额安全检查，或明确记录无法检查的原因；不解压恶意/超大归档。
4. **V4 Real image pair：** 若真实包具有可识别 Image+Mask，则至少一对本地合法文件可被只读解码并证实匹配基础维度、掩膜类型。若映射缺失，标 `CONDITIONAL/UNRESOLVED`；**不以文件存在即宣布 GO-SEGMENTATION**。
5. **V5 Identity：** 报告 678 患者、图像样本与发布包计数的可解释程度，患者与中心键的证据类型；对不能证明的 claim 明确保留未知。
6. **V6 Privacy：** 本地 ZIP、解码样本、临床/患者级索引没有进入 Git；审查 staged diff、扩展名、敏感 ID/凭据模式及输出目录。
7. **V7 Delivery：** 审计报告、脚本、聚合证据、TASK_RESULT 聚焦 Commit/Push；远端 HEAD 核实；按真实分支依赖创建 Draft PR，**不合并**。

**任务状态与研究数据门槛分离：** 调查完整且获得可信负面结论可以是 `COMPLETE`，但数据 GO 仍可为否；如果必要作业因权限、网络或磁盘缺口无从继续，按 `BLOCKED` 回报；执行后按预算与合法替代手段仍不达标，报告 `FAILED` 或 `PARTIAL` 并明确可复现限制。必要 Gate 未执行不得伪称 PASS。

## 六、TASK_RESULT 与 ChatGPT Main 交接

最终返回一份中文、可复制的 `TASK_RESULT｜CMRL-01 / r1`，至少包括：

- `Status` 与 V1–V7 的 `PASS / FAIL / NOT_RUN / UNAVAILABLE`；`COMPLETE` 绝不直接代表数据准入 GO。
- 实际 repo、工作目录、base/head SHA、任务分支、远端 SHA、工作树、PR 状态（特别说明 stacked PR）、是否 Merge。
- ZIP 下载对象、字节、哈希、请求时间、实际传输量/失败原因、空闲磁盘检查；文件级验证只以真实运行事实为准。
- 聚合归档清单、真实 Image+Mask 检验结果、患者/中心键证据与未解释的数据统计差异。
- 数据准入建议：分别给 `2D segmentation / 3D segmentation / Radiomics / cross-site` 的当前状态，明确是当前证据限制还是数据结构本身限制。
- 证据与代码的 GitHub 相对路径，以及敏感数据没有入库的核验说明；不要复制含患者标识的目录/行值。
- `Next Boundary`：推荐 Main 是否允许首个**用户亲自执行**的影像读取与空间质控任务；Codex 不自行推进 R1–R3。

**全局收口边界：** 当前任务只针对 D01 文件级审计。D02 的密码申请、D03 的一例 RTSTRUCT 对齐可以在后续独立 Plan 处理；它们不是 CMRL-01 必交付。模型与思考档位不写入本 Plan。
