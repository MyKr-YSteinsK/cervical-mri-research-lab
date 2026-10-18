# CMRL-10｜宫颈癌 MRI 派生标注溯源与替代数据预筛

- **Plan：** CMRL-Plan-10 r1（保存在仓库外）
- **日期：** 2026-10-18
- **研究阶段：** R0-DATA-ACCESS-AUDIT；`R0 NOT COMPLETE`
- **分支 / 精确父提交：** `codex/r0-10-derived-mask-provenance-screen` / `3ce361383cf222cf667a31d2a0ee87ed3d6b5a88`
- **PR #10 基线核验：** OPEN / Draft；head 与父提交一致，base 为 `codex/r0-08-tcia-private-crosswalk-screen`

## 1. 决策摘要

本轮没有找到能同时证明**来源可追溯、许可适用、宫颈原发肿瘤 Mask 可信、三维物理空间可复核**的新增公开候选。没有新增权威肿瘤 ROI 身份证据，`ROI_SEMANTIC_UNRESOLVED` 保持；监督肿瘤分割、三维肿瘤 Radiomics/Habitat、患者/中心独立评价及治疗结局任务仍不得启动。R0 不收口，也不代替 Main 选择后续数据或任务。

最关键的发现：

- CVPR-BiomedSegFM 数据卡称其从原始公共数据提取所有有标签切片并保存为 `.npz`，将影像强度处理到 `[0,255]`，字段包括 `imgs`、`gts`、`spacing`。公开目录元数据有 7 个 CCTH 命名的 `.npz`，合计 6,302,340 bytes；**未下载、未解包**。卡片泛称图像来自具备再分发许可的公共数据，但未给出 CCTH 衍生标签的逐源授权或可核查权利链；卡片也没有说明 `gts` 来自哪一个 CCTH 结构、谁标注、何时导出、对应哪个 RTSTRUCT 发行版本，或图像 origin/direction。该派生包不能视作原生完整 3D MRI 或独立队列。
- MedOtter 页面声称 CCTH RTSTRUCT 可按特定 ROI 名称/时点直接解释为“仅肿瘤”。这是第三方自述；未找到 TCIA、Bowen 原作者或 DICOM 发布方提供的对应表、转换脚本或授权再发布声明。Bowen 论文记载研究者在参考矢状 T2 上勾画 tumor 与 uterus，并用 uterus 辅助解剖对齐；这不说明两个结构都发布在 RTSTRUCT，也不能证明 MedOtter 的解释错误。发布版 DICOM 的 ROI 语义仍未知。
- 新的近似资源 MOGaMBO 在 Zenodo 公开登记，登记说明其为宫颈癌 3D T2 MRI，并列出膀胱、直肠、乙状结肠和股骨头等 OAR 勾画；没有找到其提供原发肿瘤 GTV 的依据。原始 ZIP 约 754 MB，本 Plan 不下载，因此内部格式、病人键与物理空间仍未检查。它至多是后续 OAR/空间教学候选。
- FlexFair 仍只有条件性 2D 图像级教学路线。官方 Figshare 记录 28639598 标注 CC BY 4.0；作者仓库 README 仍指向 28636133，而该编号的 Figshare API 返回 HTTP 404。沿用 CMRL-01/02 已完成的文件审计：没有可靠患者/中心键，发现跨 split 精确重复，不能作患者或中心独立验证。
- CCMD 论文称数据公开，作者仓库却要求邮件提供机构与用途并申请密码；本轮未申请、未联系作者。实际格式仍有 DICOM/PNG 与 NRRD 描述冲突，许可证未核实。

## 2. 方法、访问级别与预算

按来源层级先查数据发布者/原论文，再查官方仓库、公开数据卡与 Hub 的只读元数据；区分发布方自述、第三方声称、仓库元数据和真实文件检查。公共来源查询覆盖 Plan 指定的三条线索及三个近似候选，来源目标数未超过 45 的上限。数据文件下载量为 **0 bytes**；未下载 NPZ、DICOM、Clinical 表、模型权重或 MOGaMBO ZIP。只读访问 Hugging Face、Figshare、Zenodo 等公开页面/API 元数据。API 响应字节未单独计量，因此本报告只声称数据资产下载为零，不声称全网络流量为零。

未读取 `data/raw`、Clinical V2 行值、CMRL-08 私有候选索引或本地 DICOM；未运行图像解码、显示、Mask 转换、科研核心代码或模型。未安装依赖。当前 Plan 允许的受限文件头检查不是必要证据：它不会给出原始标注者、RTSTRUCT ROI 对应或合法再发布链，故不下载样本。未联系作者、管理员或服务方，也未提交访问申请或提供机构身份。

状态词：`SOURCE-VERIFIED` 表示所述来源本身/发布者声明可核；`AUTHOR-REPORTED` 表示原作者或发布者的声明，尚不等于文件核验；`THIRD-PARTY-CLAIM` 表示第三方数据卡的声明；`METADATA-INSPECTED` 表示仅检查公开版本、目录、大小或许可字段；`FILE-INSPECTED` 仅沿用先前任务明确范围内的实文件审计；`UNKNOWN` / `LICENSE_UNVERIFIED` 保留证据缺口。

## 3. 数据来源与标注链审计

| 资源 | 来源 → 标注 → 处理 → 发布资产 | 许可 / 实际可获得性 | 本轮判定 |
|---|---|---|---|
| **TCIA CC-Tumor-Heterogeneity 原始发行** | TCIA/IDC Collection 与 Bowen 等原论文是优先来源。论文报告参考矢状 T2 上勾画 tumor 和 uterus；论文并未公开逐个发布 RTSTRUCT ROI 标识到结构语义的 crosswalk。CMRL-04/05/06/07/08 的历史文件/元数据证据沿用原有范围，不重读本地病例。 | 官方 Collection 影像许可记为 CC BY 4.0。CMRL-09 对 TCIA 当前/历史发布页、IDC 页与论文来源的访问等级和口径差异已有记录；本轮直接打开 TCIA 页不可用，未发起数据请求。 | `SOURCE-VERIFIED`（Collection/论文级）；既有 `FILE-INSPECTED` 不等于肿瘤 ROI 或空间验收。ROI、逐患者时点和可用完整体积仍未解决。 |
| **CVPR-BiomedSegFM 的 CCTH 派生 NPZ** | 数据卡把 CCTH 作为数据命名线索；目录名和文件名表明其属于同一 CCTH 来源的派生资产，故不能算独立受试者/外部验证队列。数据卡说只提取有标签切片并预处理；没有给出 `gts` 的原始结构、标注者、导出时点/版本或可追溯转换脚本。比赛仓库所查 README/root 主要是评测和提示代码，未建立该 CCTH 派生过程；所审阅 `main` commit 为 `748e862d162e3e3ee8197bd4085b19bbbe0bb8a0`（2025-06-03）。 | Hugging Face 卡片许可字段为 CC BY-NC-SA 4.0，并概称图像来自具备再分发许可的公共数据；该概述没有说明 CCTH 派生标签的具体权利链。官方 TCIA 原始影像为 CC BY 4.0，两者的适用范围、标签衍生权利和再分发链未被材料解释，故数据/Mask 的许可适用性仍 `LICENSE_UNVERIFIED`。未下载文件。 | `AUTHOR-REPORTED / METADATA-INSPECTED`。数据卡中的 3D 数组形状是有标签切片堆叠声明，不证明原生全体积；仅记载 `spacing`，未说明 origin/direction。实际数组字段、shape、dtype 均 `NOT_RUN`。 |
| **MedOtter/TCIA_CervicalCancer** | README 将资产指向 TCIA CCTH，并声明具体患者/Study/Series/RTSTRUCT 链、时点和 tumor-only 语义；这些均为第三方声称。该仓库公开元数据有大量文件条目并包含 DICOM 资产目录；未检查或下载文件内容，也不公开转录任何病例路径或标识。未发现原作者背书或转换代码。 | Hub 卡片许可字段声称 CC BY 4.0，但当前仓库 revision 元数据未见独立 `LICENSE` 文件；没有证据证明第三方对整套原始 DICOM/标签具有再发布授权。卡片报告 18.7 GB，与 TCIA 已记录的 28.39 GB Collection 口径不同；差异不能推断为完整或缺失。 | `THIRD-PARTY-CLAIM / METADATA-INSPECTED / LICENSE_UNVERIFIED`。不得用该页面解除 `ROI_SEMANTIC_UNRESOLVED`，也不得视为独立患者。 |
| **FlexFair** | Nature/作者发布数据对应 Figshare 28639598。CMRL-01/02 曾按其各自范围下载并检查图像/Mask 发布包；文件主体是 2D PNG/Mask，不存在可据此核实的完整 MRI 物理体积。作者代码 README 链接的另一编号 28636133 与 Figshare 当前 API 不一致；所审阅作者仓库 `main` commit 为 `f7da0fc0a9a4ad7c96f2c7b48699fc8cc151e320`（2025-04-12）。 | Figshare API 对 28639598 返回 v1、单个资产、348,731,016 bytes、CC BY 4.0；28636133 查询返回 HTTP 404，保留冲突，不擅自改写作者链接。 | 官方源 `SOURCE-VERIFIED`；先前包 `FILE-INSPECTED`（只沿用 CMRL-01/02）。患者/中心身份和跨 split 独立性未成立。 |
| **CCMD** | 2025 原论文和作者仓库称 151 例 T2WI/肿瘤标注。所审阅作者仓库 `main` commit 为 `9b6a7e9b31ba2b89dd0604e59cedefe2662d2a24`（2025-02-10）。论文称代码与数据公开；仓库要求通过邮件提交研究目的与机构信息以获取密码。README 的 DICOM+PNG 文字与示例 NRRD 结构并存。未获访问、未取得文件，也没有触达作者。 | 访问目前按 `RESTRICTED`；没有找到适用于数据及 Mask 的正式 license 文件/条款，`LICENSE_UNVERIFIED`。 | `AUTHOR-REPORTED / RESTRICTED / FILE-NOT-INSPECTED`。原发肿瘤 3D 标注或空间元数据没有文件级证明。 |
| **MOGaMBO（额外候选）** | Zenodo 记录描述 94 例宫颈癌 3D T2 MRI，手工勾画危及器官；没有提供原发肿瘤 Mask 的来源声明。单中心队列与其他候选的身份重叠未知。 | Zenodo 记录为 open、CC BY 4.0；数据 ZIP 754,352,087 bytes，超过本 Plan 的必要文件检查门槛，未下载。格式、实际空间 header、病人索引未检查。 | `SOURCE-VERIFIED`（Zenodo 登记元数据）+ `AUTHOR-REPORTED`（资源描述）。OAR 是潜在独立教学目标，不是已核实宫颈肿瘤标注。 |
| **Cervical-MD（额外候选）** | MICCAI 2025 论文页描述多序列 3D MRI、报告与 FIGO 分期；不是 GTV Mask 发布。论文页不同段落给出 3,137 与 3,177 两个数据量，无法用文件消歧。作者回复称接受后可邮件申请访问。 | 公开论文页可读，患者影像未公开下载；访问需申请，授权和数据许可 `LICENSE_UNVERIFIED`。本轮不申请、不联系。 | `AUTHOR-REPORTED / RESTRICTED`。FIGO 分期不能替代肿瘤 Mask、治疗应答或生存终点。 |
| **2022 年 3D 宫颈 MRI 分割论文（额外候选）** | OpenReview 论文描述机构患者数据与多结构人工勾画；模型训练将 cervix、GTV、uterus 合并为组合结构。被审阅论文没有给出公开影像/Mask 资产和可复用许可。 | 论文是公开，患者数据未从本轮审阅源中找到公开下载入口；许可 `LICENSE_UNVERIFIED`。未联系作者。 | `SOURCE-VERIFIED`（研究论文声明）但数据资产 `SOURCE_UNAVAILABLE`。论文结果不能当作开放数据集。 |

## 4. 派生文件元数据与权限判断

### BiomedSegFM

- Hugging Face `main` revision：`343ddc66b80a3fbd2d85f7f196b3b3203faaa424`（页面元数据记录最后更新时间 2026-03-18）；CCTH 目录含 7 个 `.npz`，合计 6,302,340 bytes。API 提供文件级对象标识/哈希元数据；未获取任何文件对象。
- 数据卡声明 `imgs`、`gts` 的 `(D,H,W)` 形状、影像强度 `[0,255]` 与 `spacing` key。上述是发布者对字段的描述，非本地数据 header 检查结果。
- 以有标签切片为输入并保存成 3D 数组，会制造一个体积形状的数据容器；它不恢复无标签切片、不证明原始层序、原始强度、完整 FOV、病人/时点边界或物理坐标。没有 origin/direction 证据，就不能以这批 NPZ 做空间重建、3D 形态学特征或患者级切分。
- `gts` 语义的关键链仍缺：原始 RTSTRUCT/ROI 身份 → 标注结构/人员 → 切片筛选与裁剪 → 强度和空间处理 → NPZ 文件。字段名 `ground truth` 和数组 shape 都不能补齐这条链。

### MedOtter

- 当前 Hub revision：`bb10e4237a145be9628734d052f8c6b8c6e054d1`，元数据更新时间 2026-05-07；revision API 列有 73,554 个 sibling 路径条目。只保留聚合数量，未把目录逐例路径写入证据文件。该数量是 Hub 元数据项，不是经内容读取核实的有效 DICOM 数、Series 覆盖率或对象完整性。
- 页面有 `CC BY 4.0` metadata 声称；本轮所查 revision sibling 列表未见 `LICENSE` 文档。TCIA 原始数据许可不能替第三方证明其所有转换、索引、标签和再分发行为均获授权。
- Viewer 因配置/JSON 解析失败不可用；该状态仅是 viewer 故障，不证明数据存在/不存在，也不代表文件级审核。

### FlexFair

- Figshare API 对官方记录 28639598 返回 DOI `10.6084/m9.figshare.28639598.v1`、2025-04-09 发布、CC BY 4.0、348,731,016 bytes、1 个数据资产。作者 GitHub 的另一编号 28636133 经同一公开 API 查询为 HTTP 404；故暂列 `SOURCE_CONFLICT_UNRESOLVED`。
- 先前图像包审计证明的是发布物中的图像/Mask 文件对及像素重复，不包含患者键、中心键、MRI spacing/origin/direction 或三维 DICOM 来源链；该事实不把原论文报告的 678 人计数映射到文件级。

## 5. 比较矩阵与许可边界

每项任务单独判定及解除条件见 [CMRL-10 R0 候选数据与任务对照矩阵](CMRL-10-R0候选数据与任务对照矩阵.md)。矩阵按当前实证范围判定；未来申请、下载或手工查看数据必须另有授权，不能从当前 `CONDITIONAL` 推导自动许可。

以下是本轮可以稳定支持的研究结论：

1. **CCTH 原始集仍是可供用户考虑的空间 QC 候选，不是已准入肿瘤分割集。** 现存 56 个 Series 对及历史 DICOM 头/引用核验均不证明像素/几何正确，也不解决肿瘤 ROI 语义；原始下载还存在按 Series/实例统计的缺口。
2. **BiomedSegFM 和 MedOtter 均以 CCTH 为来源线索，不构成新增独立患者。** 样本/病例与原始受试者的一一关系未获授权交叉表证明；患者/中心隔离及独立外部验证不成立。
3. **FlexFair 适用边界保持 2D 图像级教学且为条件性。** 没有完整 3D MRI 与物理空间信息；现有图像发布包没有可靠患者/中心身份，且前序审计发现重复。
4. **MOGaMBO 可作为 OAR 空间练习的备选调查对象。** 它不能解除肿瘤 Mask 缺口，且实际文件未检查。
5. **Cervical-MD、CCMD 与 2022 机构数据论文均不能因“论文提到/发表 Dice”而当作当前可用公开资产。** 两者有访问限制或未发现公开资产，许可/格式/身份关系仍须分别处理。

## 6. 下一步建议（最多两项）

1. **若仍要走 CCTH 肿瘤监督路线，优先由用户自行向 BiomedSegFM/竞赛来源索取可公开核查的来源与处理说明：** `gts` 对应的原发布 RTSTRUCT/ROI 结构、标注者/版本、切片筛选/裁剪/重采样、spacing/origin/direction 保留方式，以及派生标注的许可依据。拿到来源材料前不把 NPZ 解释为肿瘤真值，也不做患者级复用。
2. **由 Main 决定下一项可执行范围：** 如要空间练习，可重新规划用户主导的一个 TCIA MR–RTSTRUCT 样本检查；如要尽快获得原发肿瘤标注候选，由用户自行评估 CCMD 的访问/许可流程；如只需 OAR 解剖教学，可另行授权检查 MOGaMBO。不要重新启动全量 DICOM 扫描。

本任务未发送上述询问或申请，未接受服务条款，没有把病例级值放入公开报告。R0 和 ROI 语义的决策权仍在 Main/用户。

## 7. 引用来源

访问日期均为 2026-10-18（未特别说明者）；页面声明和文件级证据按本文访问级别区分。

- TCIA [CC-Tumor-Heterogeneity Collection](https://www.cancerimagingarchive.net/collection/cc-tumor-heterogeneity/)；历史来源访问等级及发布歧义沿用 [CMRL-09 追索报告](CMRL-09-TCIA权威ROI与临床定义追索报告.md)。
- Bowen 等，[Tumor radiomic heterogeneity](https://pmc.ncbi.nlm.nih.gov/articles/PMC5899626/)；论文级 reference MRI 勾画说明，不是 DICOM ROI crosswalk。
- [CVPR-BiomedSegFM 数据卡](https://huggingface.co/datasets/junma/CVPR-BiomedSegFM)、[CCTH 文件目录元数据](https://huggingface.co/datasets/junma/CVPR-BiomedSegFM/tree/main/3D_train_npz_all/MRI/MR_CervicalCancer)；竞赛 [评测代码仓库](https://github.com/JunMa11/CVPR-MedSegFMCompetition)。
- [MedOtter 第三方 CCTH 页面](https://huggingface.co/datasets/MedOtter/TCIA_CervicalCancer)；仅用于记录第三方声称，不作权威映射。
- FlexFair [Figshare 28639598](https://figshare.com/articles/dataset/Achieving_Flexible_Fairness_Metrics_in_Federated_Medical_Imaging/28639598)、[作者 GitHub README](https://github.com/MaksimXing/FlexFair)、[Nature Communications 论文](https://doi.org/10.1038/s41467-025-58549-0)。
- CCMD [期刊论文](https://doi.org/10.1007/s11760-025-04277-3) 与[作者 GitHub 仓库](https://github.com/peekaboo990/CCMD-Cervical-Cancer-MRI-Dataset)。
- MOGaMBO [Zenodo 数据记录](https://zenodo.org/records/15156638)（公开 REST metadata）；Cervical-MD [MICCAI 2025 论文页及作者回复](https://papers.miccai.org/miccai-2025/0143-Paper0177.html)；2022 机构数据论文 [OpenReview PDF](https://openreview.net/pdf?id=c42ffe0c48f7903a8df25629a7225b8f61b41860)。
- 已筛除的 HNTS-MRG 公开资源位于[头颈 MRI 挑战数据页](https://hntsmrg24.grand-challenge.org/dataset/)；疾病部位不符合本任务的宫颈原发肿瘤范围。
