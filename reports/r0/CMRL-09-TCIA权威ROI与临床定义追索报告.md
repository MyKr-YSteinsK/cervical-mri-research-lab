# CMRL-09｜TCIA 权威 ROI 与临床定义追索报告

**Plan：** CMRL-Plan-09 r1（用户提供的仓库外文件；未复制入仓库）
**任务状态：** 来源追索与准入决策准备完成；R0 仍为 NOT COMPLETE
**审计窗口：** 2026-10-17，约 13:45–13:51 UTC
**边界：** 仅查看公开页面/论文与既有脱敏报告；未读取本地 DICOM、Clinical V2 工作簿、私有候选索引或任何病例级数据，未下载附件，未联系作者或 TCIA。

## 1. 结论

1. **没有在本次审阅的发布来源中找到逐个已发布 RTSTRUCT 的 ROI Number / ROI Name / RTROIObservation 到 tumor 或 uterus 的权威 crosswalk。** TCIA 历史页面称 CCTH 含基于 T2 MRI 的肿瘤体积轮廓；Bowen 等论文描述研究中分别勾画 tumor 与 uterus。两者均未给出可对应已发布 DICOM 结构编号/名称的表或适用范围。状态：crosswalk 为 NOT_FOUND_IN_REVIEWED_SOURCES，既有项目状态继续为 ROI_SEMANTIC_UNRESOLVED。
2. TCIA 历史页面同时有“Contours (regions of interest) of the tumor volumes … are included”描述和 Version 1 下独立的“No labels”文字，后者没有说明 labels 的定义或该句适用对象。两句无法从页面本身消解。这里记录发布说明存在歧义，不据此推断 DICOM 是否含肿瘤轮廓，也不把轮廓称为已核实肿瘤 Mask。
3. Bowen 论文确实定义了**研究分析**所用响应与方案时点，但这不构成 Clinical V2 字段 codebook，也不能把论文的 21 人映射到 Collection 的 23 subjects。论文全文搜索索引转录的探索性响应标准为治疗结束后约 1 个月评价、残余肿瘤体积低于基线体积的 10%；适用范围仅限论文报告的研究端点。不得把该阈值套用到 Clinical V2 的“Early response”字段。
4. 官方公开来源未说明 Clinical V2 各事件字段的编码、事件确认、时间零点、时间单位、删失/失访/未知规则、末次随访状态，也未解释五个未键控单格行的记录角色。Clinical 候选键是否与 DICOM PatientID 共用身份命名空间仍未证实。
5. 研究方案时点可从来源中部分定义，但本地 DICOM Series 到 baseline/early/mid 的逐患者对应仍未找到。来源之间的口径保留如下：TCIA Wiki 写 early 2–2.5 周/20–25 Gy、mid 4–5 周/45–50 Gy；Wiley 摘要写 early 2 周、mid 5 周；PMC 全文搜索索引写 mid 40–50 Gy。不可静默归一。
6. TCIA 当前 Collection 页的搜索索引显示 Version 2（2023-02-23）、23 subjects / 171 studies / 821 series / 131,556 images、28.39 GB 与 13.9 kB Clinical XLSX；历史 Wiki 直接页面仍显示 26.0 GB 与 14 kB。数据引用标题标为 Version 1。页面/版本口径差异保留，不据此判断本地完整性或推断变更原因。

## 2. 来源审阅与访问等级

| ID | 来源、具体位置与版本 | 访问结果 | 可支持的主张 / 适用范围 |
|---|---|---|---|
| A1 | TCIA 当前 Collection：Data Access、Version 2、Citation；2023-02-23 更新。https://www.cancerimagingarchive.net/collection/cc-tumor-heterogeneity/ | 页面本次直接打开返回 HTTP 500；官方搜索索引可读，INDEX-ONLY。访问窗口见报告抬头。 | 当前页索引公布的 subjects/studies/series/images、数据大小、模态、Clinical XLSX 和 CC BY 4.0；版本说明称临床表新增一个远处转移时间值。不能定义字段、患者身份连接或 ROI 语义。 |
| A2 | TCIA 历史 Wiki：Summary、Data Access、Detailed Description、Citations、Versions（lines 49–66、77–89、92–108、112–142）。https://wiki.cancerimagingarchive.net/pages/viewpage.action?pageId=112591753 | 官方 Wiki 页面直接可读，DIRECT；页面标注最后修改 2024-04-11。 | 集合目的、公开描述的肿瘤轮廓与方案时点、23/171/821/131,556 统计、旧页面大小、CC BY 4.0、相关论文引用及 Version 1/2 说明。未提供逐 ROI 标识映射、临床代码本、逐患者时点键。 |
| A3 | IDC Collection Details：Subject Count、Primary Site、Image Modalities、Supporting Data。https://portal.imaging.datacommons.cancer.gov/collections/cc_tumor_heterogeneity/ | 直接可读，DIRECT。 | 23 subjects、宫颈原发部位、CT/MR/PT/REG/RTSTRUCT、Clinical supporting data，并指向 TCIA Wiki。不是文件级检查或身份映射。 |
| A4 | Bowen et al.，Journal of Magnetic Resonance Imaging，47(5):1388–1396，DOI 10.1002/jmri.25874；Wiley 摘要及作者信息。https://onlinelibrary.wiley.com/doi/abs/10.1002/jmri.25874 | Wiley 页面直接可读，DIRECT；页面注明全文暂不可用。 | 摘要报告 21 人；pre-RT、early 2 周、mid 5 周；响应由放射肿瘤科医师在治疗后 1 个月基于手工勾画肿瘤体积变化评估。不能支持发布版 RTSTRUCT 编号映射或 Clinical V2 字段语义。 |
| A5 | Bowen et al. PMC 全文，Methods / Patient and Treatment Characteristics、DCE MRI/DW MRI/PET、Response analysis。https://pmc.ncbi.nlm.nih.gov/articles/PMC5899626/ | 本次直接打开触发 reCAPTCHA；PMC 搜索索引返回正文片段，INDEX-ONLY。未下载 PDF。 | 索引片段支持论文中参考矢状 T2 上分别勾画 tumor/uterus、uterus 用于解剖对齐；论文分析的响应标准为残余肿瘤体积小于基线的 10%。这仍仅是作者报告的论文方法，不能用于 DICOM ROI 身份或 Clinical V2 字段映射。 |
| A6 | TCIA Data Dictionary 入口。https://www.cancerimagingarchive.net/tcia-data-type/data-dictionary/ | 官方页直接获取返回 HTTP 500；UNAVAILABLE。 | 未能读取可引用的字典定义；本次不以其他集合/泛化字段字典替代 CCTH codebook。 |
| A7 | TCIA 官方 FAQ / Support。https://www.cancerimagingarchive.net/faqs/ 与 https://www.cancerimagingarchive.net/support/ | 搜索索引显示官方 FAQ 指向 TCIA Help Desk；FAQ 与 Support 直接访问均返回 HTTP 500。INDEX-ONLY / UNAVAILABLE。 | 仅确认页面存在官方咨询入口；未提交表单、未发送邮件、未联系数据管理员。 |
| A8 | 论文正文引用的 ClinicalTrials.gov NCT01992861。https://clinicaltrials.gov/study/NCT01992861 | 直接打开只呈现通用页面骨架，未返回该试验记录内容；UNAVAILABLE。 | 不据第三方镜像补写试验字段、端点或样本关系。 |

**来源预算：** 至少 12 个互不重复 URL 页面目标被打开或尝试；未超过 Plan 的 60 个目标。公开 PDF/补充文件下载 0 个（上限 6 个）；本次公开新下载 0 bytes（上限 40 MiB）。检索覆盖 TCIA 当前与历史页面、IDC、DOI/出版商/PMC 原文入口、正式补充材料检索、官方数据字典和官方支持入口。正式 supplement 未在审阅页面或定向索引检索中找到，状态为 NOT_FOUND_IN_REVIEWED_SOURCES；不表示全球不存在未链接附件。公共来源机器可读记录见 [tcia_authority_source_register.json](../../evidence/r0/tcia_authority_source_register.json)。

## 3. ROI 语义核验

| 待回答项 | 状态 | 证据与适用范围 |
|---|---|---|
| Collection 层面的肿瘤轮廓发布说明 | SOURCE_DEFINED（仅为发布方描述） | TCIA 历史 Wiki Detailed Description 称肿瘤体积 ROI 以 T2 MRI 定义，且包含在 CCTH 的各病例/影像时点。该描述没有声明具体 DICOM SOP/RTSTRUCT 版本、ROI Number/Name、病例覆盖表或结构映射。 |
| 发布版 RTSTRUCT 逐 ROI Number/Name/Observation → tumor/uterus 对照 | NOT_FOUND_IN_REVIEWED_SOURCES | TCIA 当前/历史页面、IDC 页面、Bowen Wiley 摘要、PMC 正文可检索片段均未给出该 crosswalk。正文“研究勾画了 tumor 与 uterus”不是发布 DICOM 的结构编号身份。 |
| 论文提及的 uterus ROI 是否也作为 Collection DICOM 轮廓发布 | NOT_FOUND_IN_REVIEWED_SOURCES | 论文描述研究操作；历史 Collection 页面只明确提及肿瘤轮廓，未逐结构声明发布范围。 |
| Collection 中标注/轮廓发布范围 | CONFLICTING_SOURCES（页面措辞无法消解） | 同一历史 Wiki 先称含 tumor volume contours，Version 1 下又出现未解释的“No labels”。该注记没有定义 label，也没有说明是否指 RTSTRUCT；不据其判断轮廓是否存在。 |
| 本地 RTSTRUCT 的临床语义或空间正确性 | NOT ASSESSED IN CMRL-09 | 沿用 CMRL-04/05/08 的已报告文件级元数据事实；本任务未读取本地 DICOM、像素或 ContourData。 |

因此发布对象语义继续为 **ROI_SEMANTIC_UNRESOLVED**。没有从名称、颜色、轮廓大小、数量或论文双结构描述推断真实 ROI；没有尝试把标注升级为监督 Mask。若后续找到部分映射，须限定其版本、病例、时点与导出格式并另做用户主导的空间验证。

## 4. Clinical V2 字段定义核验

既有 CMRL-07/08 文件级检查记录：Clinical V2 官方字节锚点为 14,233 bytes、SHA-256 a59d29c86bb45bca98649d1eb8c7a533558fd1cf7b6beb35f5175ea47a04d1c9；28 个非空数据行中有 23 个候选键和 5 个未键控单格行。以上是复用的既有任务证据，本次没有重读工作簿或行值。

| 字段/问题 | 发布定义状态 | 追索结论 |
|---|---|---|
| Early response (1–2 months post-therapy) | PARTIAL_SOURCE_DEFINED（仅论文端点）；Clinical V2 codebook 为 NOT_FOUND_IN_REVIEWED_SOURCES | Wiley 摘要称治疗结束后 1 个月由医师依据肿瘤体积变化评估；PMC 正文搜索索引将时间写为 brachytherapy 完成后 1 个月并另外给出论文分析阈值，保留两处原文范围措辞。没有来源证明它就是 Clinical V2 字段的编码、类别或阈值。 |
| Local Recurrence | NOT_FOUND_IN_REVIEWED_SOURCES | 未找到病例级事件确认、阴性/未知/缺失编码、判定来源或日期规则。 |
| Distant Metastasis | NOT_FOUND_IN_REVIEWED_SOURCES | Version 2 更新说明仅报告有一项 Time to Distant Metastasis 值被补入；未定义事件编码、单位、起点或删失。 |
| Death from Cervical Cancer | NOT_FOUND_IN_REVIEWED_SOURCES | 未找到死因裁定或事件/缺失编码说明。 |
| Time to Local Recurrence / Time to Distant Metastasis / Time to Death | NOT_FOUND_IN_REVIEWED_SOURCES | 无时间零点、时间单位、事件计算、未发生事件/删失/失访处理代码本。 |
| Disease Status (at last contact) 与随访 | NOT_FOUND_IN_REVIEWED_SOURCES | 无随访截点、末次接触规则、失访定义或状态编码。 |
| 五个未键控单格尾行 | NOT_FOUND_IN_REVIEWED_SOURCES | 复用 CMRL-08 的 OBSERVED_LAYOUT；来源审阅没有找到解释这些行是注释、病例、图例或其他记录的说明，角色/行粒度继续 UNKNOWN。 |
| Clinical 候选键与 DICOM PatientID 命名空间关系 | NOT_FOUND_IN_REVIEWED_SOURCES | 没有发布方命名空间声明或公开 crosswalk。23 对 23 的计数相等不构成身份链接证据，JOIN_UNVERIFIED 保持。 |

不从这些字段生成 response、复发、DFS、OS 或生存时间标签；不定义删失，不剔除五行，也不按键连接临床与影像。

## 5. Cohort 与真实时点连接

| 问题 | 状态 | 依据与边界 |
|---|---|---|
| 21 人论文与 23-subject Collection 的人数 | 两个计数 SOURCE_DEFINED；集合关系 NOT_FOUND_IN_REVIEWED_SOURCES | TCIA 历史页面将 Bowen 论文列作该 Collection 的相关出版物；Wiley 论文摘要报告 21 人，TCIA/IDC 报告 23 subjects。未找到差额解释、纳入排除表或逐人 provenance。 |
| Clinical 候选键与 DICOM PatientID 关系 | NOT_FOUND_IN_REVIEWED_SOURCES | 无官方 namespace 定义或公共 crosswalk；JOIN_UNVERIFIED。 |
| 研究方案级时点 | SOURCE_DEFINED，但来源口径有差异 | TCIA 历史 Wiki：dose 0、20–25 Gy/2–2.5 周、45–50 Gy/4–5 周。Wiley 摘要：pre-RT、early 2 周、mid 5 周。PMC 正文搜索索引：early 20–25 Gy、mid 40–50 Gy。只作为方案级证据，保留原始差异。 |
| DICOM Series → baseline/early/mid 逐患者映射 | NOT_FOUND_IN_REVIEWED_SOURCES | 没有 Collection 发布的逐 Series 时点表、正式时点码本或 Clinical↔DICOM 映射。既有私有日期先后只有 CHRONOLOGY_ONLY，不是本次重现，也不是治疗时点。 |

## 6. 不发送的咨询草案

**UNSENT DRAFT — 未发送、未提交、未包含病例标识**

> Subject: Clarification request for the public CC-Tumor-Heterogeneity collection
>
> Hello,
>
> I am reviewing the public CC-Tumor-Heterogeneity release and would appreciate clarification of its published documentation:
>
> 1. Is there an authoritative, version-specific mapping from each released RTSTRUCT ROI Number/ROI Name/observation to tumor, uterus, or other structures? If so, what released files, subjects, timepoints, or export versions does the mapping cover?
> 2. Does the 21-participant Bowen et al. analysis cohort map to all or a documented subset of the collection’s 23 subjects? Is there a public, authorized cohort-level provenance statement?
> 3. Is there a Clinical V2 codebook defining the response, recurrence, metastasis, cervical-cancer death, time-to-event, last-contact, censoring, and missing-value fields? What is the role of the five unkeyed single-cell rows?
> 4. Does the Clinical key use the same identity namespace as DICOM PatientID, and is there an authorized public mapping?
> 5. Is there a released Series-level key for the planned baseline, early-treatment, and mid-treatment imaging timepoints?
>
> I am not including patient identifiers or requesting restricted records. Thank you.

可用但未使用的公开联系渠道：论文列出的通讯作者 Stephen R. Bowen, PhD（PMC 正文索引给出的公开邮箱 srbowen@uw.edu；Wiley 页面直接确认通讯作者，但地址在该页面显示为遮蔽链接）；TCIA Help Desk（TCIA 官方 FAQ 索引显示 help@cancerimagingarchive.net，Support 页面直接访问失败）。以上仅作渠道记录；没有发送邮件、提交表单、联系管理员或提供用户身份。

## 7. R0 implications

- Keep ROI_SEMANTIC_UNRESOLVED, ENDPOINT_CODEBOOK_UNVERIFIED, JOIN_UNVERIFIED, TIMEPOINT_UNASSIGNED and R0 NOT COMPLETE.
- Continue to classify a single-case TCIA MRI spatial QC as CANDIDATE/CONDITIONAL for a later user-led task; this report does not select a subject or inspect private candidate locations.
- Supervised tumor segmentation and volume Radiomics/Habitat remain NO-GO until ROI identity, pixel/geometry alignment and usable Series completeness are separately verified.
- Longitudinal treatment analysis remains NO-GO until real treatment timepoints are mapped per patient.
- Clinical response/recurrence/survival modeling remains NO-GO until the Clinical codebook and authorized patient-level join are established.
- FlexFair and CCMD are compared only using existing CMRL-01/02 evidence in the separate decision memo; no new dataset files were accessed.
