# 07｜审计来源、来源可信度与后续科研问题

## A. 原始权威/官方入口（2026-10-16 核查）

| 来源编号 | 权威入口 | 能支持什么 | 不能支持什么 |
|---|---|---|---|
| S01 | https://doi.org/10.1038/s41467-025-58549-0 （2025 Nature Communications，FlexFair） | 四中心 678 名宫颈癌患者；治疗前 T2WI/肿瘤 ROI；中心间扫描参数不同 | 数据包是否完整下载、患者 ID 和全部体积是否实际公开，尚未证实 |
| S02 | https://figshare.com/articles/dataset/Achieving_Flexible_Fairness_Metrics_in_Federated_Medical_Imaging/28639598 | 发布页面声称约 332.58 MB，CC BY 4.0 | 未逐文件下载审计；另有 README DOI 不同 |
| S03 | https://github.com/MaksimXing/FlexFair | 代码公开；README 指向另一个 Figshare DOI 与 Google Drive | 不证明数据文件无权限障碍或可按患者进行验证 |
| S04 | https://doi.org/10.1007/s11760-025-04277-3 （2025 CCMD 论文） | 151 病人 T2WI 肿瘤分割；作者报告 nnU-Net-3D Dice 0.8181 | 不证明已获数据密码或 repo 含全部代码 |
| S05 | https://github.com/peekaboo990/CCMD-Cervical-Cancer-MRI-Dataset | 申请方式、格式描述、使用限制 | README 与实际下载后的结构可能不同；当前 repo 根目录仅 README |
| S06 | https://www.cancerimagingarchive.net/collection/cc-tumor-heterogeneity/ | 23 人、28.39 GB DICOM、RTSTRUCT/REG、XLSX 临床表 | 不证明 23 人完整三时点和疗效终点可用 |
| S07 | https://portal.imaging.datacommons.cancer.gov/collections/cc_tumor_heterogeneity/ | IDC 也确认数据集及可用检索下载方式 | 非具体文件/ROI 标签验证 |
| S08 | https://zenodo.org/records/16934473 | 宫颈癌预后相关影像/特征/骨 Mask 资源 | Mask **非宫颈肿瘤**；不可用于肿瘤分割基线 |
| S09 | https://papers.miccai.org/miccai-2025/0143-Paper0177.html | Cervical-RG/Cervical-MD 多序列报告/FIGO 工作，中心规模介绍 | 不证明可下载原始 MRI 或疗效标签；页面存在数据口径不一致 |
| S10 | https://github.com/youhs4554/radiomics_CRT | P03 有代码/notebooks，依赖旧环境；README 指明患者数据需申请 | 不证明可以直接运行医院原实验 |
| S11 | https://github.com/MyKr-YSteinsK/ai-workflow-assets/tree/main/%E9%A1%B9%E7%9B%AE%E5%AD%B5%E5%8C%96%E5%99%A8 | 用户项目孵化器的目标真实性、研究证据、技术未知、最小充分工程治理参考 | **不继承 Codex 工作流、自动生成巨大治理体系** |
| S12 | `SOURCE_PAPERS/P01`–`P06` 六份 PDF | 六篇具体 Methods、Results、Fig、Table、局限性等的首要学术事实源 | 原 PDF 不是 MRI 患者数据或模型源码 |

各外部链接后续可能发生变更；R0 新 Main 应核对当时网页、实际下载许可、版本与文件哈希，并更新状态，而不是固定依赖本表的时间点。

## B. 需要主动查明的问题（按影响程度）

**会阻止实际开工**

- D01 发布物能否不用单独医院伦理权限获取真实图像/Mask？Figshare 28639598 与 README 28636133 到底各是什么？
- D01 332.58 MB 包是图像+掩膜、结果表，还是混合材料？是否有 678 人患者键与四中心标签？
- D02 是否获授权，文件格式、患者级掩膜是否与 DOI 原文一致？
- D03 是否有可在本地跑通的 DICOM/RTSTRUCT 合法组合？

**影响模型与论文主张**

- 是否有必要做 3D MRI 体积实验，还是只能做 2D 切片级分割？如果是切片级，patient-wise 独立划分如何建立？
- 能否识别真实原发肿瘤，而非生殖器官、盆骨或放疗计划目标的 ROI？
- 是否存在同一患者多时点、中心重复病例或者同人图像出现在多个发布资源？
- 使用 MedSAM/nnU-Net/ViT/Transformer 是必要对照还是为了复杂而复杂？
- 哪种具体分割稳定性或域泛化问题尚未被已有研究充分解决？须先做近三年前沿文献差距梳理及可信 baseline，才提出“创新”。

## C. 初步研究假设（不是已确认 Core）

H1：相比人工或强制固定 ROI 下的传统影像组学流程，引入分割扰动训练/推断不确定性后可以提高部分影像特征在中心间的稳定性。测：ICC、特征变化率、分中心差距和分割 Dice；需足够 ROI/患者映射。

H2：真实三维肿瘤 MRI 的全肿瘤平均特征可能遗漏局部亚区域信息；经空间一致性约束的 Habitat 表征可能提供额外稳定信息。测：区域面积/体积、跨重采样一致性、全肿瘤 vs Habitat 的受控消融；**没有患者疗效标签时，不以治疗应答 AUC 作结果**。

H3：多医院 T2WI 扫描协议差异会影响基础模型与 Radiomics 的输出，域特异预处理/特征归一化等措施可能改善留一中心测试的稳定性。测：中心独立 Dice/HD95、特征变异、置信区间；前提是可核实中心与患者身份。

H4（以后，有真实终点才激活）：稳定 Radiomics + 深度特征 + 临床变量可能改善宫颈癌治疗应答区分/校准；按 P01–P06 对照明确治疗方式、影像时点、标签与相同数据划分。

这些都是**反事实可检验的方向**。先复现/建立 baseline、用实验反馈收敛；不要求一次将四个研究假设全部实施。

## D. 源冲突处理规则

发现两个官方来源矛盾：同时记录版本、原句/数据表、来源链接与查询日期；实际下载文件可直接消解的则用文件证据，仍无法消解的则列 `UNRESOLVED` 并降低适用性评级。不得为了设计一条顺畅的研发路线而静默修正患者数、文件格式、算法参数或标签。

## CMRL-07 补充核验（2026-10-17）

- **S06 当前 TCIA Collection 页面**：当前页面报告 23 subjects、171 studies、821 series、131,556 images、28.39 GB，含 DICOM 与 Follow-Up / Classification XLSX，CC BY 4.0；Clinical changelog 标为 Version 2（2023-02-23），记载为一名受试者补入一个 Time to Distant Metastasis 值。当前页面直接读取超时，采用官方搜索索引文本；官方文件端点另以 HTTP 200 实际取得小型 XLSX 并与本机副本 SHA-256 比对。数据集引用标题写 Version 1，与临床文件 changelog 分开记录。
- **S06 历史 TCIA Wiki 页面**：记载治疗前、约 2–2.5 周/20–25 Gy、约 4–5 周/45–50 Gy 三个计划时点；说明 tumor volume contours 由 T2 MRI 定义并与 PET/CT 配准。历史页的图像大小为 26.0 GB，当前页为 28.39 GB，属于发布页口径/时间记录差异，不据此判断本地缺失。
- **S13 Bowen et al. 2018，DOI 10.1002/jmri.25874 / PMID 29044908 / PMCID PMC5899626**：作者报告 21 人、pre-RT/early 20–25 Gy/mid 40–50 Gy；参考矢状 T2 上勾画 tumor 与 uterus，uterus 辅助配准，tumor ROI 用于多时点多模态分析。论文未给出发布版 DICOM 的逐 ROI Number/name crosswalk。TCIA 的 23 subjects 与论文 21 人的对应及差额原因仍 UNKNOWN。
- **Clinical 字段和临床连接**：官方当前 XLSX 实测 1 sheet、28 非空行、9 命名字段；候选键 23 个非空互异值，5 行为空。没有公开 codebook 解释实际行粒度、临床编码、时间起点、删失或随访；候选键到本地 DICOM PatientID 仍 JOIN_UNVERIFIED。当前完整审计见 [CMRL-07 报告](../../reports/r0/CMRL-07-TCIA原始研究ROI时点与临床字段核验.md)。
- **ROI 与本地时点**：文献双结构勾画不等于 DICOM ROI 语义映射；本地 ROI 语义仍 ROI_SEMANTIC_UNRESOLVED。文献时点 SOURCE_DEFINED；本地实际 DICOM 时点 UNASSIGNED。CMRL-07 不读取像素、不重扫 DICOM、不联系作者。

### CMRL-07 待 Main 决策

先独立复核 ROI crosswalk/codebook 是否存在；若无，是否由用户自行联系作者。即使后续选取一组作单例空间教学，也须由用户实测方向、spacing 与 contour 几何，未确认结构语义前不把轮廓称为肿瘤真值。临床建模需另行取得正式事件/时间/删失定义和合法精确患者 crosswalk。


### CMRL-08｜本地 Clinical 键、日期顺序与 MR–RTSTRUCT 候选

Plan-08 r1 的只读元数据审计完成；没有数据源网络请求。Clinical V2 的五条单格文本行在布局上构成同一非键字段类别的连续表尾区块，样式不同且无内部注释/图例标记；语义与记录粒度仍 UNKNOWN。Clinical 候选键到本地 DICOM PatientID 的匹配子类受小单元格抑制，来源语义未确认，状态 JOIN_UNVERIFIED。

固定 IDC v25.0.0 对账复现 CMRL-06/r2：821 期望、806 本地、15 缺失；748 计数相等、73 个短缺 Series/1,132 个实例。全量 Header 解析 130,424/130,424，前后文件元数据 snapshot 相同。63 个 RTSTRUCT 允许范围内解析，唯一直接 SOP 引用 1,873 个本地命中、61 个未命中。通过 MR/RTSTRUCT 计数与目标引用链预筛得到 56 个唯一 Series 对；这不是患者数，也不是空间/肿瘤语义验收。私有定位索引最多保存 3 组，精确小计不公开。时间证据只有 CHRONOLOGY_ONLY；真实治疗时点仍 UNASSIGNED，患者分组仍 GROUPING_UNVERIFIED。ROI_SEMANTIC_UNRESOLVED、ENDPOINT_CODEBOOK_UNVERIFIED 和 R0 NOT COMPLETE 不变。见 [CMRL-08 报告](../../reports/r0/CMRL-08-TCIA私有连接与候选预筛报告.md) 与 [脱敏 profile](../../evidence/r0/tcia_private_crosswalk_screen_profile.json)。
## CMRL-09｜权威定义追索（2026-10-17）

- 新增来源：TCIA 历史 Wiki（直接可读）确认 collection-level tumor contours/方案时点描述；IDC 页面直接确认 23 subjects 和模态/Clinical supporting data；Wiley 直接摘要支持论文 21 人、2/5 周方案时点及论文级 response assessment。PMC 正文仅 INDEX-ONLY；TCIA 当前 Collection 索引为 INDEX-ONLY；TCIA Data Dictionary、Support 与 ClinicalTrials.gov 正文本次不可读。
- 未找到发布版逐 RTSTRUCT ROI 标识到 tumor/uterus 的 crosswalk、Clinical V2 codebook、21 人论文队列到 23 subjects 的具体关系、Clinical key 到 DICOM PatientID namespace 说明、DICOM Series 的逐患者治疗时点映射。
- 源内歧义：TCIA Wiki 的 tumor contour 描述与 Version 1 下“No labels”单句未能消解；当前/历史页面大小不同；论文与 Wiki 的 mid timepoint 周次/剂量范围不同。逐项引用与访问等级见 [CMRL-09 报告](../../reports/r0/CMRL-09-TCIA权威ROI与临床定义追索报告.md)。
- 仅准备 UNSENT 作者/TCIA 问题草案，未发送；R0 NOT COMPLETE。
