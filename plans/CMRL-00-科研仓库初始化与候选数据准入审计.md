# CMRL-00｜科研仓库初始化与候选数据准入审计

- **项目**：`Cervical-MRI-Research-Lab`（宫颈癌 MRI 影像科研实践）
- **任务类型**：Bootstrap / Investigation / Research data-access audit
- **Plan Revision**：`r2`（命名规范修订；取代尚未执行的旧文件 `R0-00-科研仓库初始化与候选数据准入审计.md`，研究目标及权限不变）
- **授权依据**：用户于 2026-10-16 明确授权 Codex 承担不影响亲自编码教学的前期自动化核验、建立 GitHub 仓库、提交可共享研究资料及报告。本 Plan 不代表任务已执行。
- **任务编号规则**：项目标识式 `CMRL-NN-中文任务标题.md`，其中 `CMRL` 是 `Cervical-MRI-Research-Lab` 的项目缩写、`NN` 是全项目连续两位编号。本任务 `CMRL-00` 用于仓库初始化；后续新任务依次 `CMRL-01`、`CMRL-02`，与研究阶段 R0–R8 独立。修订同一任务沿用编号，仅更新 Plan Revision。
- **目标远端（待现场核实）**：`MyKr-YSteinsK/cervical-mri-research-lab`。规划时该地址未核实存在可访问的仓库；Codex 必须用自身已认证的 GitHub 会话重新核对。
- **已知研究状态**：仅 R0；无本项目已验证的本地患者数据、MRI 处理环境或训练成果。P01–P06 第一轮技术导读已完成但不属于新项目实测。

## 1. Goal｜任务交付

在一个可供 ChatGPT Main 和 Codex 共同核查的 GitHub 仓库中，完成：

1. **初始仓库与合同接入**：GitHub 仓库、本地 Git 工作区、根 `AGENTS.md`、简洁 `README.md`、适用 `.gitignore`、八份活动项目文档、Plan 与合理的目录布局；验证 Commit、Push 与真实远端一致。
2. **教学 / Codex 权限修订**：最小幅度落实用户新决定——Codex 可自动执行数据源可用性、公共元数据、非敏感文件清点和证据报告等辅助任务；MRI 数据处理、分割、Radiomics、训练与解释性核心代码仍由用户逐步亲自学习、编写和运行，除非用户以后另行授权。保护旧课程项目边界。
3. **R0 三数据源审计**：核对 D01 FlexFair 两个 Figshare article ID 与具体文件元数据；D02 CCMD 申请/许可与影像格式矛盾；D03 TCIA/IDC 的公开文件及最小 Clinical XLSX 的真实可得性、结构，评估单例 MRI/RTSTRUCT 的可获得路径。
4. **可复核报告**：将源证据、实际命令/脚本、请求结果、缺失项、失败原因、审计决定和复现步骤存入仓库；一份中文 TASK_RESULT 回传 GPT Main。

**本任务不是**下载完整数据集、安装 CUDA、建立训练环境、运行模型、确认疗效标签、正式选择唯一数据集或将 R0 判为完成。

## 2. Inputs / Preconditions｜输入和基线

启动资料包随本 Plan 单独提供，解压后预期存在：

```text
<workspace-root>/
  docs/project/01-PROJECT_BRIEF.md
  docs/project/02-DATASET_EVIDENCE_REGISTER.md
  docs/project/03-STAGED_RESEARCH_PLAN.md
  docs/project/04-GPT_TUTORING_AND_EXPERIMENT_PROTOCOL.md
  docs/project/05-SIX_PAPERS_TECHNICAL_BRIDGE.md
  docs/project/06-R0_EXECUTION_RUNBOOK.md
  docs/project/07-SOURCES_AND_OPEN_QUESTIONS.md
  docs/project/08-RESEARCH_STATE.md
  plans/CMRL-00-科研仓库初始化与候选数据准入审计.md
  BOOTSTRAP_INPUTS_README.md
```

这些是 **seed 输入资料，不是已提交的仓库文件**。Codex 开始时要核实真实磁盘路径及内容，不可假设 ChatGPT Project 附件自动存在于 Codex 工作区。若文件缺失，优先报告缺失并请求用户放置启动包；不得依据简述重造八份原文。相对路径以实际解压结果为准。六篇原论文 PDF 本次可从现有 `05` 的 DOI 索引获取背景信息，无须把 PDF 或医院级数据作为首次 Git 仓库的强制依赖。

### 参考权威来源

- 孵化器 Plan / TASK_RESULT 合同：`https://github.com/MyKr-YSteinsK/ai-workflow-assets/blob/main/项目孵化器/05-CODEX_PLAN_SPEC.md`
- 孵化器工程治理：`https://github.com/MyKr-YSteinsK/ai-workflow-assets/blob/main/项目孵化器/06-ENGINEERING_GOVERNANCE.md`
- D01 论文：`https://doi.org/10.1038/s41467-025-58549-0`
- D01 Figshare：`https://api.figshare.com/v2/articles/28639598` 与 `https://api.figshare.com/v2/articles/28636133`
- D01 GitHub：`https://github.com/MaksimXing/FlexFair`
- D02 论文：`https://doi.org/10.1007/s11760-025-04277-3`
- D02 作者仓库：`https://github.com/peekaboo990/CCMD-Cervical-Cancer-MRI-Dataset`
- D03 TCIA：`https://www.cancerimagingarchive.net/collection/cc-tumor-heterogeneity/`
- D03 IDC：`https://portal.imaging.datacommons.cancer.gov/collections/cc_tumor_heterogeneity/`

`01`–`08` 与以上外部资源的作用不同：前者规定研究目标与当前状态，后者用于验证不断变化的外部数据事实。

## 3. Permissions｜本任务的实际权限

**允许**：

- 在用户为本项目选择/提供的独立工作目录内读取、初始化 Git、创建本任务文件、运行小型核验脚本、查看公开网页/API/公开仓库；必要时安装少量 R0 审计依赖（优先标准库，需解释安装用途），不触碰其他项目。
- 以用户已授权的 GitHub 身份创建目标仓库；**初始仓库可见性默认为 private**。若目标库已存在，先核对归属与内容，保护全部现有修改，不重建/覆盖。希望 public 时须用户明确批准后另行操作；本 Plan 不授权自动改为 public。
- 创建且推送初始 `main`（仅初始化合同与 seed），再创建并推送 `codex/r0-00-data-access-audit` 审计分支；可创建对 `main` 的 **draft PR** 供 Main 检视。不得自动合并 PR。
- 上传可安全分享的八份项目文档、Plan、README、AGENTS、审计脚本、经过检查的公开文件元数据、脱敏/聚合审计报告和有保留价值的失败证据。
- 用 GET/HEAD 请求测试公开数据端点；在符合发布方许可和站点条款且不需额外授权的前提下，仅为格式/可得性审计下载**小型文件**，例如 D03 的公开 Clinical XLSX。临时下载保留本地受控目录，不纳入 Git。

**不允许**：自动发送 CCMD 申请邮件、代填研究机构身份、接受未知法律/许可协议、破解或分享密码、访问需专门伦理审批的数据、创建/伪造患者、上传原始 MRI/RTSTRUCT/Clinical XLSX、含患者行级数据的索引、身份键、密钥或鉴权日志、擅自公开 private 库、训练模型、修改旧论文精读 Project、升级 R0 阶段、修改/合并非本任务分支。GitHub 登录等身份交互由用户本人完成；不请求其在对话粘贴 Token。

**下载预算**：不下载 FlexFair 整包（页面声称约 332 MB）或 TCIA 全影像（约 28 GB）；默认仅下载临床表/公开小元数据。单个非元数据文件超过 **30 MB** 或累计数据下载预计超过 **100 MB** 时停止并报告，由 GPT Main/用户再决定；不得为验收而悄悄提高预算。HTTP Range/HEAD 能验证的范围与真实完整下载必须区分，服务器返回不支持 Range 时不能误记为局部文件审计成功。

## 4. FROZEN｜不可突破的研究与治理边界

1. 仅执行 `R0-DATA-ACCESS-AUDIT`。`01-PROJECT_BRIEF.md` 目标与 02–08 的科研安全、分组评价、患者隐私、来源证据优先级继续有效。
2. 区分 `SOURCE-VERIFIED`（源声称）、`FILE-INSPECTED`（实际获取并检查的文件）、`RESTRICTED`、`NOT_RUN`、`UNAVAILABLE`。API 200 或下载链接存在不等于真实压缩包内容、完整病例、患者级映射和掩膜通过验证。
3. 不假定存在治疗应答、pCR、DFS、OS 标签；不要由 FIGO 分期、时间顺序或 RTSTRUCT 类型推断有效终点。RTSTRUCT 可能包含器官、GTV、CTV 等不同轮廓，不能未核对就当原发肿瘤 Mask。
4. 对 D01 严格分开 **678 名患者**和论文不同统计口径的图像样本；若无可信患者键/中心键，不作患者级切分、三维 Radiomics 或跨中心泛化承诺。同患者不同切片、时点、增强结果不得跨 train/val/test。
5. 公开或私有 Git 都不等于获得临床数据再分发许可。敏感/受限的原始影像、Clinical XLSX、行级病例表只放明确 `.gitignore` 排除的本地数据目录；在 `git add/commit` 前二次检查 staged 文件。不要上传任何带凭据的 Figshare/GitHub URL、cookie、网盘提取码。
6. 原 `08-RESEARCH_STATE.md` 的 R0/R1–R8 实验状态及主路线进度由 Main 审查。Codex 可根据本次**已获得用户批准**的权限变化，在相应段落标注新分工；不得写“R0 完成”“数据验收通过”“模型已跑通”。审计结论写入独立报告，不直接替代 Main 正式阶段决定。
7. 初始代码/脚本应仅用于辅助审计，避免搭建分割模型或大型软件框架。未来医学影像教学核心代码不通过本任务预先自动实现。
8. 修改 `01`、`04`、`08` 仅限反映新近明确批准的“辅助 Codex 自动核验”分工，其余已有科研决定、旧项目独立性和历史研究状态不得改写；留下原始输入文件哈希与实际差异以便审查。

## 5. RECOMMENDED｜执行路线与文件归档

### A. Preflight 与仓库初始化

1. 确认 Codex 当前目录是用户批准的本项目独立工作区；检查隐藏文件、现有 `.git`、remote、未提交用户修改，核实 GitHub 登录身份与目标库是否存在。若已有不同身份的仓库，**停止创建/覆盖**并向用户询问；不可破坏性清理。
2. 校验 seed 八份文档均可读；记录 SHA-256 与来源文件名。计划文件本身应放入 `plans/`。保留 `BOOTSTRAP_INPUTS_README.md` 或将其变为一段简洁 `README` 说明后，在确认内容已接入时清理重复临时入口。
3. 建立简洁 `README.md`：研究范围、R0 当前状态、八份合同入口、数据许可证/隐私边界、最小再现命令、Codex/ChatGPT Main 的交接路径。
4. 建立根 `AGENTS.md`：指定研究权限、用户亲自编写教学核心代码的边界、`docs/project/` 合同真实路径、`plans/` 与 `reports/` 回传义务、禁止提交敏感医学数据、分支与 Merge 权限。不要求复制整个孵化器或创建空 `src/`/`models/`。
5. 建立 `.gitignore`：至少保护 `data/`、本地 `.env*`、`.venv/`、缓存、各类临时下载与内部工作目录；避免不加分辨率地屏蔽正式脚本、审计报告与可共享的脱敏测试结果。Commit 前增加 staged 文件清单检查。
6. 初次提交 seed/入口到 `main`；再以独立、可审查 Commit 最小修订 `01`/`04`/`08` 权限条款（若技术/权限允许，可放在一个聚焦提交）；推送 `main`，查询真实远端 HEAD。初始仓库没有必要立即建立 GitHub Actions、DVC、MLflow 或完整 Python 环境。

### B. R0 审计分支与产物

在 `codex/r0-00-data-access-audit` 分支工作。以下路径可依据实际内容小幅调整，但必须在报告中给出真实路径：

```text
reports/r0/CMRL-00-三候选数据准入审计.md
reports/r0/CMRL-00-TASK_RESULT.md
scripts/r0/              # 如确有价值，保存精简可复现的元数据查询/清点脚本
evidence/r0/             # 仅公开来源、经审查可安全提交的机器可读元数据/摘要
```

**D01 / FlexFair（最高优先）**

- 查询 `28639598`、`28636133` 的 Figshare API。逐个记录响应时间（UTC）、HTTP 状态、最终 URL、article ID、DOI、标题、版本、更新时间、license、`files[]` 的名称/字节数/可下载属性及可用 checksum；注意 `size` 和 checksum 有无来源。
- 与 Nature Communications 原文的 Data availability、作者 GitHub README 交叉核对；确认 README 是否存在其他 Google Drive 路径、文件版本或链接有效性。两记录若一个 404/跳转，不直接判断是“笔误”，先记录 API、网页及引用链；将消解不了的分歧标为 `UNRESOLVED`。
- 只有在公开、合法、预算内可获得独立小文件时，才读取实际文件的格式、图像/Mask 配对信息；若只能看到一个超过预算的压缩包，**不下载整包**，报告“发布元数据可访问；内部文件未验收”。不得从文件计数臆造患者映射。
- 单独解释 678 患者与论文各中心图像计数的统计口径关系目前能证实到哪一步，患者 ID/中心 ID/spacing/3D volume 到底哪些未核实。

**D02 / CCMD（并行来源审计，不申请权限）**

- 查期刊原文与 GitHub README 当前版本、Last update/Commit；核对 151 患者、T2WI/Mask、许可/用途、申请步骤（邮箱仅用作者公开方式）、机构条件、数据镜像/获取限制。
- 分栏保留 `DICOM image + PNG annotation` 与 `T2wI.nrrd + tumor_mask.nrrd` 的矛盾，区分文档描述与本地文件实测；未获得授权不能填写实测格式、三维 spacing 或病人映射。
- 输出用户可执行的**合规申请材料要点**，但不自动发送邮件、填写虚构机构或接受条款。若作者提供的访问入口需要密码，标 `RESTRICTED`，不尝试规避。

**D03 / TCIA-CC-Tumor-Heterogeneity（公开小文件优先）**

- 检查 TCIA collection、IDC collection、数据使用许可、DICOM/RTSTRUCT/Clinical XLSX 的真实入口与版本。记录 collection 公布的 Patients / Studies / Series / Instances 与发布页更新信息；这些是来源统计，不是已下载样本数。
- 若公开 XLSX 能合法无须人工批准直接取得且在预算内：下载到本地 `data/`，计算 SHA-256，仅读取工作表名、字段名、字段类型、记录数、空值数/占比、可用字段含义和编码问题；提交**字段字典与聚合缺失统计**，不提交原 XLSX 或行级患者数据。记录读取程序及异常；如官方接口不可访问则标 `UNAVAILABLE` 并给出人工核验链接。
- 检查 1 例对应 T2WI / RTSTRUCT 的准确下载流程与 ROI 结构类型能否从公开元数据辨认。如需要下载较大 DICOM/RTSTRUCT 或无法确定同一 Frame of Reference 与 ROI 类型，停在“单例待检查”；不可声称已经完成 Mask 配准与空间 QC。

### C. 审计报告必须明确的范围

报告建议按 `数据集 → 来源 / 权限 → 可复核网页/API/具体文件 → 与旧登记表的差异 → 已证实 → 尚未证实 → 风险与下一步` 写。每条数据结论均注明**来源日期、直接链接、证据类型**，必要时附 HTTP 状态、文件名、长度、哈希、运行环境与可复现命令；保留有意义的网络失败证据但移除 token、cookie、敏感 ID。

给三个候选各自作 `GO` / `CONDITIONAL` / `NO-GO` 建议时说明该建议适用的**具体任务**（元数据审计、2D 分割、3D 分割、Radiomics 等）；此次不是用户/ Main 正式批准研究阶段。若没有真正检查一对 Image+Mask，必须明确 `GO-SEGMENTATION` 的必要文件级门槛**尚未满足**。

## 6. DELEGATED_TO_CODEX｜现场可自主解决的技术问题

可自行选择合适的标准库/轻量读取工具、GitHub CLI/已有认证方式、官方 API 与 HTML 的互证方法、文件元数据保存格式，以及失效链接的合法替代来源；调整无意义的脚本细节时记录原因。优先低副作用、可重复、可回滚的方式。

不可将自主方法选择扩展为公开仓库、破密获取、批量下载、真实患者数据发布、选择训练目标或修改研究任务。被权限/条款阻塞时停止受影响步骤；其余独立审计可以继续。

## 7. Acceptance / Exit Gate｜必要验收

| Gate | 可观察通过条件 |
|---|---|
| G1 Repo | 目标 GitHub 仓库存在且归属正确；可从远端读取实际 `main`、`AGENTS.md`、`README.md`、八份项目文档及当前 Plan；初始 SHA/remote/visibility 实测可追溯。 |
| G2 Contract | 新分工已在 `01`/`04`（必要时 `08`）最小修订，并有原 seed 哈希与差异；R0 仍未越级、旧项目独立性未受损。 |
| G3 D01 | 两条 ID 的独立请求结果与来源冲突追踪可复核；文件 manifest 的可见范围、是否**真实下载检查**以及患者映射未知项明确。即便返回 404/不可访问，也必须如实存证。 |
| G4 D02 | 申请与研究用途限制、格式描述冲突与具体证据有记录；未申请/未下载的事实清楚。 |
| G5 D03 | TCIA/IDC 来源信息核验；临床 XLSX 若成功获取则有 sha256/字段字典/聚合缺失报告，否则有准确失败状态与手动下载路径；RTSTRUCT 是否实际检查清楚。 |
| G6 Privacy | 可提交文件经过许可/敏感性审查；Git staged 内容无原始医学数据、行级临床表、身份键、访问口令或密钥；保存 `.gitignore` 和检查结论。 |
| G7 Delivery | 独立审计分支的报告、必要复现脚本、TASK_RESULT 已 Commit/Push；GitHub 远端 HEAD 已实查；最好提供 draft PR，**不 Merge**。完成态必须满足本任务适用的全部必要 Gate。 |

**可完成的负面核验**：外部来源确实 404、不可下载或文件不完整，也可能产生高价值且验收通过的调查结论；但必须保存有效访问证据，并且不能把未尝试/网络超时当作“已证伪”。

## 8. Verification｜Codex 执行前后要检查

- Seed 输入文件存在、UTF-8 与基本 Markdown 链接/引用真实；对本次允许的文档变更给出简短 diff；确保没有覆盖其它用户工作。
- Git 首次 Commit 前与最终 Push 前检查 staged file list、被忽略的数据路径、疑似敏感文件与大文件；`git status` 清楚，没有意外修改。
- 复现脚本至少能对公开 API 在成功/HTTP 错误/超时路径输出区别状态；在无法联网时不得伪造输出或将未运行标 PASS。
- 数据字典字段数量与 missingness 必须源于实际 XLSX 的本地读取；有无 `patient_id`、`mask_meaning`、治疗应答事件等都不可凭猜测填值。
- 远端核验以实际 `git ls-remote` / GitHub API 观察为准；Local Commit、Push 返回码和远端 SHA 应分别记录。若不能初始化 GitHub 访问，准确标 `BLOCKED`，而不是悄悄跳过 G1/G7。

## 9. Delivery / TASK_RESULT｜交回 Main 的唯一结果

仓库文件：`reports/r0/CMRL-00-TASK_RESULT.md`，另有主审计报告 `reports/r0/CMRL-00-三候选数据准入审计.md`。

最终 Codex 对话以一份**可直接复制**的中文 `TASK_RESULT` 回传（可引用仓库报告，不用再造第二套结论），最低包含：

```text
## TASK_RESULT｜CMRL-00 / r2
- Status：COMPLETE / PARTIAL / BLOCKED / FAILED
- Repo / Visibility / Branch / Base SHA / Final SHA / Remote SHA / Working Tree：...
- Changes & Decisions：初始化产物、01/04/08 修订摘要、实际技术决定及偏离
- G1–G7 Acceptance：逐项 PASS / FAIL / NOT_RUN / UNAVAILABLE，附证据路径
- D01：两个 Figshare IDs 的响应、manifest / 实体检查边界、患者映射结论
- D02：申请条件、格式冲突、未申请/已申请的真实状态
- D03：临床 XLSX 与 RTSTRUCT 的实际检查边界、字段级结论
- Data Safety：扫描与排除结果；可否安全读取公开仓库
- Git / Remote：真实 remote URL、commit、push、远端核验、draft PR、是否合并（默认否）
- Deviations / Limitations / Open Questions：...
- Artifacts：仓库内报告、元数据、脚本链接；本地未入 Git 的数据所在受控目录（不暴露隐私路径）
- Next Boundary：建议 Main 下一步决策，不自行宣布 R0 验收或进入 R1
```

其中任务整体 `COMPLETE` 只在所有适用的必要工作与 Git 交付完成后成立；阻塞/失败按 `05-CODEX_PLAN_SPEC.md` 的四态语义记录。对于文件级数据检查无法实际完成的情形，G3/G5 可以以可信的“未验收且阻塞原因明确”的**调查交付**收口，但绝不可声称数据通过文件级验收。

**Git 回执细节**：入库 TASK_RESULT 可省略包含自身的最终提交 SHA，最后一次真实 Commit/Push 后在对话里补充最终 SHA、远端观察与工作树状态；不要为了回填 SHA 无限改写结果文件。未经 Main 审查，不将 `TASK_COMPLETE` 等同于 `EVIDENCE_ACCEPTED`、`STAGE_ADVANCED` 或对 `main` 合并许可。
