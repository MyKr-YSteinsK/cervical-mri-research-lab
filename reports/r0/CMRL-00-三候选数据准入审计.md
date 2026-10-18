# CMRL-00｜三候选数据准入审计

**审计日期：** 2026-10-16（UTC）

**范围：** R0 数据源与准入调查；不代表 Main 已验收 R0，也不代表任何数据集通过影像级准入。

**任务身份：** `CMRL-00`，依照仓库内 `plans/CMRL-00-科研仓库初始化与候选数据准入审计.md`。

**审计分支：** `codex/r0-00-data-access-audit`

## 结论摘要

| 候选 | 元数据审计 | 2D 分割 | 3D 分割 | Radiomics | 本次关键边界 |
|---|---|---|---|---|---|
| D01 FlexFair | **GO** | **CONDITIONAL** | **NO-GO** | **NO-GO** | Figshare 可读，但 332.58 MiB 压缩包超过 30 MB 单文件预算，没有下载或检查包内影像、掩膜与患者/中心映射。 |
| D02 CCMD | **GO** | **NO-GO（当前）** | **NO-GO（当前）** | **NO-GO（当前）** | 论文和 README 可核；数据需要作者提供访问密码，格式描述冲突，未发申请、未获得数据。 |
| D03 TCIA CC-Tumor-Heterogeneity | **GO** | **CONDITIONAL** | **NO-GO** | **NO-GO** | TCIA/IDC 元数据和小型临床 XLSX 已核；临床表的行粒度与终点语义未确认；影像/RTSTRUCT 配对接口请求超时，未检查任何影像。 |

本次 **`GO-SEGMENTATION` 文件级门槛均未满足**：没有实际检查任何一个 Image+Mask 配对。上述 GO 只指来源或元数据调查可继续，不是数据许可、临床标签有效性或科研路线批准。

## 证据层级与方法

- **来源陈述**：论文、官方数据页、官方 API、公开仓库 README 所描述的内容；标为作者/发布者陈述，不冒充本地样本验证。
- **公开元数据实测**：通过匿名公开请求获取的 JSON、Atom、README 原文；选择性脱敏结果在 [`evidence/r0/public_source_metadata.json`](../../evidence/r0/public_source_metadata.json)。复现入口为 [`scripts/r0/audit_public_sources.py`](../../scripts/r0/audit_public_sources.py)。
- **本地文件实测**：只下载并只读检查了 TCIA 临床 XLSX；原文件保存在本地 `data/clinical/`，由 `.gitignore` 排除，不提交。汇总位于 [`evidence/r0/tcia_clinical_profile.json`](../../evidence/r0/tcia_clinical_profile.json)，脚本与 runner 分别为 [`scripts/r0/inspect_clinical_xlsx.py`](../../scripts/r0/inspect_clinical_xlsx.py) 和 [`notebooks/r0/CMRL-00-tcia-clinical-xlsx-profile.ipynb`](../../notebooks/r0/CMRL-00-tcia-clinical-xlsx-profile.ipynb)。
- **未完成的影像查询**：TCIA `getSeries` 请求没有返回 HTTP 状态或正文；超时证据见 [`evidence/r0/tcia_series_api_probe.json`](../../evidence/r0/tcia_series_api_probe.json)。这不证明数据不可访问。

公开来源脚本于 2026-10-16 UTC 运行，Figshare 28639598 返回 200、28636133 返回 404，TCIA collection API 和 IDC 页面返回 200。GitHub 未认证 REST 请求返回 403；该响应正文未保留，因此不推断其原因。脚本随后对两个仓库的公开 Atom 提交源与 README raw URL 回退请求均返回 200。两个仓库的分支 HEAD 也通过 `git ls-remote --symref` 只读查询交叉核对。未访问或下载 D01 压缩包、D02 受限数据、D03 DICOM/RTSTRUCT。

## D01｜FlexFair 四中心数据

### 已核实

- 论文报告 678 名患者、来自四个中心，中心患者数为 89、65、278、246；数据描述为治疗前轴位 T2WI MRI 与 ITK-SNAP 肿瘤 ROI。该数字是论文的患者口径。来源：[Nature Communications 论文](https://www.nature.com/articles/s41467-025-58549-0)。
- Nature 数据可用性声明链接到 Figshare article **28639598**。该记录的 DOI 是 `10.6084/m9.figshare.28639598.v1`，标题为 *Achieving Flexible Fairness Metrics in Federated Medical Imaging*，版本 1，CC BY 4.0。
- Figshare API 在 2026-10-16 09:44 UTC 返回 HTTP 200。文件清单只列出 `CervicalCancerDataset.zip`，大小 **348,731,016 bytes**（十进制约 348.7 MB / 二进制约 332.6 MiB）；记录给出的 `computed_md5` 为 `303ae54703fdccc63302cb755aed792a`。压缩包超过 Plan 的单文件 30 MB 上限，故没有下载、解压或检查内部文件。
- 第二个候选 ID **28636133** 的独立 Figshare API 请求在 09:44 UTC 返回 HTTP 404。不能仅凭此结果推断 ID 来源或与另一个记录之间的原因。
- FlexFair README 文本同时提到 `28636133`、`28639598`，其 Figshare 链接目标为 DOI `10.6084/m9.figshare.28639598`。公开 GitHub REST API 本次返回 403；Atom 和 raw README 回退成功。HEAD 为 `f7da0fc0a9a4ad7c96f2c7b48699fc8cc151e320`。README 还包含 Google Drive 链接；本次打开链接跳转到 Google 登录页，没有检视文件列表或内容，故不能判断这些链接是否失效。

### 未核实与风险

- 仓库种子登记中的 1383/1332/323/328 是“image sample”计数，本次没有在可访问的论文正文中独立找到并核对；不得将其解释为患者数、切片数、序列数或压缩包文件数，也不得与 678 人建立映射。
- 论文的 678 人及中心计数不证明公开压缩包包含可识别患者/中心的拆分键，也不证明其包含完整 3D 体数据、物理空间信息或与图像同源的可用 Mask。
- README 中的 Google Drive 登录跳转只说明本运行环境未看到内容，不等于链接不可用或数据被限制。

### 建议

- **元数据审计 GO**；可以继续解析公开论文、README 与发布记录。
- **2D 分割 CONDITIONAL**：只有在有授权且预算内获得实际影像与对应 Mask 后，验证数量、标签含义、患者/中心键和查重，方可考虑图像级 2D 实验。
- **3D 分割 / Radiomics NO-GO**：当前没有包内文件清单和实际图像空间信息；不得将论文的分割任务推定为可进行体积级分析。

## D02｜CCMD

### 已核实

- 论文称数据集包含 **151 名患者**，按 121/30 分为训练/测试，使用 DICOM 影像和矢状位 T2WI 肿瘤标注；文中称可按请求获取。来源：[Springer 论文](https://link.springer.com/article/10.1007/s11760-025-04277-3)。这些是论文描述，并非本地审计结果。
- [作者 GitHub 仓库](https://github.com/peekaboo990/CCMD-Cervical-Cancer-MRI-Dataset) 本次 REST API 返回 403；公开 Atom 源和 raw README 回退请求返回 200。当前 `main` HEAD 为 `9b6a7e9b31ba2b89dd0604e59cedefe2662d2a24`，提交日期为 2025-02-10。此前检查的仓库根目录仅展示 README，未找到公开训练代码。
- README 一处称 `DICOM (Original scans) + PNG (Annotations)`，示例目录却列出 `T2wI.nrrd` 与 `tumor_mask.nrrd`；这是 README 内部描述冲突，实际文件格式未验证。
- README 指示通过邮件请求访问密码，并提交机构归属和研究用途；描述预计 3–5 个工作日。README 另称商业用途需要书面许可。此次没有发送请求、提供机构信息、获取密码或接受任何条件。无论论文使用 “open” 一词还是 README 的访问描述，本次均未取得数据授权。

### 建议

- **元数据审计 GO**；申请及法律条件需由用户基于真实机构信息自行决定。
- **2D/3D 分割与 Radiomics 当前均 NO-GO**：没有权限或实际文件，格式、图像/Mask 配对、方向、间距、临床字段均未检查。若未来获授权，再先核实格式与空间配准；不依据论文指标推断本项目结果。

## D03｜TCIA CC-Tumor-Heterogeneity / IDC

### 发布来源与访问

- [TCIA 官方 collection 页面](https://www.cancerimagingarchive.net/collection/cc-tumor-heterogeneity/) 和 [TCIA collection API](https://www.cancerimagingarchive.net/api/v1/collections/41813) 将该数据集标为 Version 2，DOI `10.7937/ERZ5-QZ59`。collection 页面列出的来源统计为 23 Patients、171 Studies、821 Series、131,556 Images，28.39 GB；包含 MR、RTSTRUCT、REG、PT、CT 和 Clinical 随访资料，许可栏列 CC BY 4.0。此处是发布统计，不是本地下载数。TCIA 更新日期为 2023-02-23；API 的 `modified_gmt` 为 2026-10-14，属于页面 CMS 修改时间，不能当成数据版本更新日期。
- [IDC collection 页面](https://portal.imaging.datacommons.cancer.gov/collections/cc_tumor_heterogeneity/) 也列出该队列；本次页面请求返回 HTTP 200，并出现 23 subjects、MR、RTSTRUCT、Clinical supporting data 等字段。
- [TCIA 公共 REST API 文档](https://wiki.cancerimagingarchive.net/display/Public/TCIA+Programmatic+Interface+(REST+API)+Usage+Guide) 说明公开 collection 的元数据查询不再需要 API key。本次只尝试一个 series 元数据查询；没有触发 IDC 全量下载命令。

### 临床 XLSX 文件检查

- 从 TCIA 官方页面列出的 [临床工作簿](https://www.cancerimagingarchive.net/wp-content/uploads/TCIA_CCTH_Patient-data_02.06.23.xlsx) 下载成功：HTTP 200，14,233 bytes；SHA-256 `a59d29c86bb45bca98649d1eb8c7a533558fd1cf7b6beb35f5175ea47a04d1c9`。该文件只保存在被忽略的本地 `data/clinical/`，未进入 Git。
- 用 Python 3.12.14、openpyxl 3.1.5 以只读模式扫描；未修改工作簿，未输出或保存任一单元格值、病例标识或样例行。实际结果是一个 sheet、9 个带标题字段、28 条非空记录行；工作表范围为 A1:K33，J/K 无数据。TCIA 发布统计为 23 名受试者，表内有 28 行，故**不能直接把 28 行当作 28 人**。
- `Case Name` 有 23 个非空值，23 个值均不同；另有 5 行没有该候选标识。这只是候选键的局部完整性统计，不证明与 TCIA subject ID 或影像序列的可靠关联。
- 这 5 条无 Case Name 的记录每行只含一个非空单元格，字段均为 `Early response (1-2 months post-therapy)`。该字段在 28 行中都有值，但来源未定义其编码和临床判定标准；**不能认定为 pCR、治疗应答、疗效标签或可训练终点**。

| 字段 | 28 行中空值数 | 空值率 | 观察 / 限制 |
|---|---:|---:|---|
| Case Name | 5 | 17.9% | 候选标识；值不输出 |
| Early response (1-2 months post-therapy) | 0 | 0% | 仅字段名线索，含义与编码未核实 |
| Local Recurrence (y/n) | 5 | 17.9% | 另有 1 个 `N/A` 哨兵值 |
| Time to Local Recurrence (weeks) | 23 | 82.1% | 时间字段，事件/删失规则未核实 |
| Distant Metastasis (y/n) | 5 | 17.9% | 事件定义与随访口径未核实 |
| Time to Distant Metastasis (weeks) | 22 | 78.6% | 时间字段，缺失/删失原因未知 |
| Death from Cervical Cancer (y/n) | 5 | 17.9% | 死因与终点判定未核实 |
| Time to Death from Cervical Cancer (weeks) | 20 | 71.4% | 时间字段，缺失/删失原因未知 |
| Disease Status (at last contact) | 5 | 17.9% | 定义、评估时间与类别编码未核实 |

上述比例的分母固定为工作表中的 28 条记录行；它们不是确认的 28 位患者比例。没有通过 `Case Name` 与影像映射，没有对端点做临床解释，因而本次**没有接纳任何训练标签**。

### 影像与分割门槛

对 TCIA `getSeries` 公开 API 发出一个候选 series 查询。PowerShell 请求在 30 秒工具执行边界内未捕获响应；Python 标准库诊断重试在 15 秒 timeout 下耗时 15.99 秒并返回 `TimeoutError`。未得到 HTTP 状态或响应正文；未请求或下载 DICOM/RTSTRUCT 文件。证据见 [`tcia_series_api_probe.json`](../../evidence/r0/tcia_series_api_probe.json)。因此尚未确认：具体 T2WI、RTSTRUCT 是否配对、ROI 名称/含义、Frame of Reference、空间对齐、时点或纵向患者对应关系。

### 建议

- **元数据和 XLSX schema 检查 GO**，仅限当前报告中的来源与结构事实。
- **2D 分割 CONDITIONAL**：下一步先合法获取一个小型、可审查的 T2WI 与 RTSTRUCT 实例，人工确认 ROI 是目标肿瘤、影像参考帧和空间配准。
- **3D 分割 / Radiomics NO-GO**：图像和结构尚未落地检查，临床表粒度与随访端点也未确认；样本数小，不能据此承诺可训练的疗效预测数据。

## 种子登记差异、隐私与交付边界

- 种子文件 [`02-DATASET_EVIDENCE_REGISTER.md`](../../docs/project/02-DATASET_EVIDENCE_REGISTER.md) 对 D01 的 678 人及中心人数与论文相符；其中 1383/1332/323/328 的图像样本说法本次没有独立核实。D02 的访问和格式差异在上文细化。D03 的“小型 XLSX 未下载”状态已因本任务实际下载并做 schema profile 而过时；只修订了本任务的独立报告，没有改 Main 持有的研究阶段状态文件。
- 仓库内 seed 修改限于 01、04、08 三份权限约定。原始 seed 哈希记录于 [`docs/project/SEED_SHA256.md`](../../docs/project/SEED_SHA256.md)，对应差异副本为 [`evidence/r0/seed-permission-changes.patch`](../../evidence/r0/seed-permission-changes.patch)。本次没有把 R0 改标完成或宣称数据通过。
- 单元格/患者值、患者影像、Mask、DICOM、RTSTRUCT、CCMD 访问口令均未纳入 Git。本地 XLSX 路径位于受 `.gitignore` 保护的 `data/`。提交前还需检查 staged 文件清单与忽略规则。
- 本报告提供来源与结构调查结论，不替代 Main 对候选数据、研究终点或阶段推进的正式决定。**当前项目仍无任何 Image+Mask 文件级验收。**

## 主要来源

1. [Nature Communications / FlexFair 论文](https://www.nature.com/articles/s41467-025-58549-0)；[Figshare 28639598](https://figshare.com/articles/dataset/Achieving_Flexible_Fairness_Metrics_in_Federated_Medical_Imaging/28639598)；[Figshare API 28636133](https://api.figshare.com/v2/articles/28636133)；[FlexFair GitHub](https://github.com/MaksimXing/FlexFair)。
2. [Springer / CCMD 论文](https://link.springer.com/article/10.1007/s11760-025-04277-3)；[CCMD GitHub](https://github.com/peekaboo990/CCMD-Cervical-Cancer-MRI-Dataset)。
3. [TCIA collection](https://www.cancerimagingarchive.net/collection/cc-tumor-heterogeneity/)；[TCIA collection API](https://www.cancerimagingarchive.net/api/v1/collections/41813)；[TCIA 临床 XLSX](https://www.cancerimagingarchive.net/wp-content/uploads/TCIA_CCTH_Patient-data_02.06.23.xlsx)；[IDC collection](https://portal.imaging.datacommons.cancer.gov/collections/cc_tumor_heterogeneity/)；[TCIA REST API 指南](https://wiki.cancerimagingarchive.net/display/Public/TCIA+Programmatic+Interface+(REST+API)+Usage+Guide)。
