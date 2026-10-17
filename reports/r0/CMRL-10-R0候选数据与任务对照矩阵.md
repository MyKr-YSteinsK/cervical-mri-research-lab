# CMRL-10｜R0 候选数据与任务对照矩阵

**状态日期：** 2026-10-18 · **Plan：** CMRL-Plan-10 r1 · **总阶段：** R0 NOT COMPLETE

状态表示当前证据下的准入判断，不代表用户已选定数据集或已运行实验。

- `GO`：当前证据满足该任务最低门槛。
- `CONDITIONAL`：仅在列明的证据/用户检查通过后才考虑；当前不自动授权下载或科研核心运行。
- `NO-GO`：当前证据不足或目标不符；不得开展该任务。

## 1. 来源、资产、许可与队列

| 候选 | 可获得性 / 许可状态 | 模态与空间证据 | ROI / 临床语义 | 患者、中心、时点与重复 | 当前适用性 |
|---|---|---|---|---|---|
| **TCIA CC-Tumor-Heterogeneity（原始）** | 官方 Collection 元数据公开；影像许可 CC BY 4.0。历史任务已限定检查本地文件，但本 Plan 不读本地数据。 | DICOM MR/多模态与 RTSTRUCT；历史本地引用核对不等于像素、完整 Series 或物理几何验收。v25 文件计数仍有 Series/实例短缺。 | 原论文说参考 T2 上画 tumor 与 uterus；发布版 ROI Number/Name/Observation 到语义映射未找到。 | Collection 23 subjects；原论文报告 21 人，关系 UNKNOWN；临床键 namespace、Series 真实时点均未验证。 | 可供用户后续考虑单例空间 QC；不是准入分割真值。 |
| **CVPR-BiomedSegFM CCTH 派生 NPZ** | Hugging Face 卡片可公开读取；卡片许可 CC BY-NC-SA 4.0。7 个目录条目、6,302,340 bytes，文件未下载。衍生数据与原始数据权利链 `LICENSE_UNVERIFIED`。 | 发布者称 `.npz` 为有标签切片堆叠，`spacing` key；只文档化了 spacing，origin/direction 未说明；不是已验收完整原生体。 | `gts` 标成 ground truth，但无逐 ROI/原始标注者/RTSTRUCT 版本映射。 | 文件命名归于 CCTH 来源，按潜在同队列重打包处理；病例级对应和切片所属时点 UNKNOWN。 | 不作为独立患者或外部验证队列。 |
| **MedOtter CCTH 第三方打包** | Hub 页面声明 CC BY 4.0，revision metadata 未见独立 LICENSE 文档；内容再发布权利未核。页面称 18.7 GB，与 TCIA 统计口径不同。 | 页面声称含 DICOM/RTSTRUCT；只读目录元数据，不核实内容、几何或完整性。 | 第三方声称具体 ROI 名称/时间点与“仅 tumor”，无权威 crosswalk/处理代码支持。 | 明确自称源于 CCTH，故不是独立队列；文件/病例对应未知。 | 第三方主张不能解除 CCTH ROI 未决，不作为可用数据资产。 |
| **FlexFair** | Figshare 28639598 v1：CC BY 4.0，348,731,016 bytes。作者 README 另指 28636133（公开 API HTTP 404），记录冲突未解。先前公开 ZIP 按 CMRL-01/02 范围已检查。 | 已检查的发布包是 2D PNG/Mask；无完整 3D MRI、spacing/origin/direction。 | 论文/作者称为 T2WI 肿瘤 ROI，但图像/Mask 与发布标签之外的临床目标未独立重验。 | 论文声称四中心 678 人；发布文件没有可靠 patient/site key。前序文件审计发现跨 split 精确重复。 | 只保留条件性 2D 图像级教学，不作患者级或中心级声明。 |
| **CCMD** | 论文称数据可公开；作者仓库实际要求邮件提供机构/用途以申请密码。`RESTRICTED`；数据/Mask license 未验证。 | 作者描述 T2WI；README 的 DICOM+PNG 与 NRRD 示例冲突；无文件检查。 | 作者报告肿瘤勾画，实际标签、配对和坐标未检。 | 作者称 151 人；patient/site/timepoint 级字段未见，不能与其他队列做去重。 | 当前无授权文件，不可执行。 |
| **MOGaMBO（额外候选）** | Zenodo record open、CC BY 4.0；数据 ZIP 754,352,087 bytes，未下载。 | Zenodo 作者描述 3D T2 MRI；物理 header/实际格式未查。 | 公开登记描述 OAR 手工勾画；未见原发肿瘤 GTV 证据。 | 作者称单中心 94 人；内部患者级索引和外部队列重叠未知。 | 可作为 OAR/解剖空间教学候选；不能满足肿瘤监督目标。 |
| **Cervical-MD（额外候选）** | MICCAI 论文页和作者回复可读；作者称可邮件申请，未公开下载；license 未验证。 | 作者描述五序列 3D MRI；实际文件未公开读取。 | 有报告/FIGO 信息描述，未见肿瘤 Mask；FIGO 不能替代疗效/生存结局。 | 论文页出现 3,137 / 3,177 两种数据量；七院规模为作者报告，病例和中心键未验证。 | 当前访问受限且无目标 Mask，不可执行。 |
| **2022 年宫颈 MRI 分割论文数据（额外候选）** | 论文可读；未找到开放影像/Mask 文件或可复用许可。 | 研究论文称来自机构的 3D MRI 分割实验；无公开资产可检查。 | 文中报告多结构勾画，训练时将 cervix/GTV/uterus 合并，不能作为分离的 GTV 标签。 | 论文报告 22 人与 42 个标注数据集；时点重复可能存在，无法检查/去重。 | 论文结果不是公开数据集，当前不具备实验准入。 |

## 2. 各任务独立准入

| 候选 | R0 单例 MRI 空间 QC | 2D 图像级教学 | 3D 肿瘤分割 | 3D 肿瘤 Radiomics / Habitat | 患者级 / 中心级独立评价 | 治疗应答 / 生存 |
|---|---|---|---|---|---|---|
| TCIA 原始 CCTH | **CONDITIONAL**：用户另选单例并亲自核对图像/RTSTRUCT 几何；先确认文件完整。 | **CONDITIONAL**：限非监督空间/图像练习，RTSTRUCT 未确认前不能当肿瘤标签。 | **NO-GO**：ROI 语义未解、部分系列短缺、像素空间未验。 | **NO-GO**：缺可信 tumor VOI 与已验空间/完整体。 | **NO-GO**：21/23 cohort、患者 crosswalk、中心/时间映射未知。 | **NO-GO**：Clinical codebook、时间起点/事件/删失与患者连接未知。 |
| BiomedSegFM CCTH | **NO-GO**：切片堆叠及空间坐标不足以验原生物理空间。 | **CONDITIONAL**：先确认派生许可与标签目标；仅限不宣称宫颈肿瘤真值的数组/切片教学。 | **NO-GO**：`gts` 来源/结构未证实，完整原生 3D 未证实。 | **NO-GO**：强度、spacing、origin/direction、完整结构均未验。 | **NO-GO**：同源 CCTH 派生数据，不是独立患者；病例映射未知。 | **NO-GO**：无可信临床标签。 |
| MedOtter CCTH | **NO-GO**：来源和再发布权利未核。 | **NO-GO**：第三方身份与 ROI 主张不足以确认教学数据许可。 | **NO-GO**：ROI crosswalk 与标注链未证实。 | **NO-GO**：标签与物理空间均未核。 | **NO-GO**：同源 CCTH 打包，不是新队列，身份链未证。 | **NO-GO**：没有可信临床终点连接。 |
| FlexFair | **NO-GO**：2D PNG 不提供 3D 物理空间。 | **CONDITIONAL**：用户/Main 选择后限 2D 图像级；须明确重复和评价边界。 | **NO-GO**：不是完整 3D MRI。 | **NO-GO**：无 3D 体与空间信息。 | **NO-GO**：无 patient/site key，跨 split 重复未解决。 | **NO-GO**：无合法可信结局标签。 |
| CCMD | **NO-GO（当前）**：需用户自行合法取得访问授权和文件。 | **NO-GO（当前）**：未获文件及许可。 | **NO-GO（当前）**：受限、格式冲突且无文件级配对/空间验收。 | **NO-GO**：空间和 mask 语义未验。 | **NO-GO**：patient/site identity 未核。 | **NO-GO**：无 endpoint 证据。 |
| MOGaMBO | **CONDITIONAL**：未来独立 Plan 再授权下载/小范围 header 与几何检查。 | **CONDITIONAL**：如改为 OAR 教学，先核实实际文件与 mask 对齐。 | **NO-GO**：未见原发肿瘤 GTV 标签来源。 | **NO-GO**：无可信 tumor VOI。 | **CONDITIONAL**：仅可能做同中心患者级内部评价；须先核验病例 ID/重复，不能作中心外验证。 | **NO-GO**：无治疗应答/生存终点。 |
| Cervical-MD | **NO-GO（当前）**：需数据申请与许可。 | **NO-GO**：无公开影像资产。 | **NO-GO**：未报告 GTV mask。 | **NO-GO**：无肿瘤 Mask/空间文件。 | **NO-GO（当前）**：多中心是作者报告，不是可审计拆分。 | **NO-GO**：FIGO/影像报告不是治疗应答或生存终点。 |
| 2022 机构论文数据 | **NO-GO（当前）**：未发现公开数据资产。 | **NO-GO**：无开放许可资产。 | **NO-GO**：数据不可得且所述训练标签合并 cervix/GTV/uterus。 | **NO-GO**：无开放体积/可用 GTV 结构。 | **NO-GO**：病例与重复扫描不可检查。 | **NO-GO**：论文中的患者分期/扫描时间不等于开放疗效终点。 |

## 3. 范围外发现与结论边界

- HNTS-MRG 2024 是公开头颈 MRI 肿瘤标注资源，但其原发肿瘤部位不是宫颈；按 Plan 明确排除，不列入候选矩阵。
- 不把公开数据卡、论文结果、DICOM 文件数量、3D 数组 shape、二值标签或 `spacing` 字段升级为“已验证宫颈原发肿瘤 GTV”。
- CCTH 衍生文件不新增独立患者；原始 TCIA、BiomedSegFM、MedOtter 不能拆作互相独立的验证队列。
- 没有筛选、下载或打开任何病人级文件；所有矩阵状态是 R0 证据判断，不是实验结果或准入决定。
