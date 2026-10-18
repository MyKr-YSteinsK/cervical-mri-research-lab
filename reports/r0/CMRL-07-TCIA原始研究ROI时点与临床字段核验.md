# CMRL-07｜TCIA 原始研究、ROI 时点与临床字段证据核验

- **任务 / Plan：** CMRL-07 / CMRL-Plan-07 r1
- **核验日期：** 2026-10-17
- **任务状态：** COMPLETE（完成授权范围内证据审计；关键语义和连接仍 UNKNOWN）
- **科研阶段：** R0-DATA-ACCESS-AUDIT，**R0 NOT COMPLETE**。本报告不接受数据，不批准 R1–R3、肿瘤 Mask、Radiomics、训练或临床预测。
- **工作基线：** 从 PR #7 head 31b40652758f5804ade9d95d3145ff70b1a93d9b 建立独立分支 codex/r0-07-tcia-roi-clinical-evidence。
- **边界：** 未重新下载或改写原始 DICOM；未重扫 DICOM、读取 Pixel Data、转 Mask、进行图像空间验收或联系作者。Clinical XLSX 只在本机 read-only 处理，未输出真实单元格值。

## 1. 结论摘要

1. **研究原文确实报告 tumor 与 uterus 两种体积勾画。** Bowen 等在参考矢状位 T2 MRI 上勾画 tumor 与 uterus；uterus 用于辅助解剖对齐；论文称每个时点的 tumor contour 被刚性复制到 DCE MRI、DWI ADC 和 FDG PET 图像集。文献能说明研究者的分析流程，不能证明本地 DICOM 中哪个 ROINumber 或 ROIName 是 tumor、哪个是 uterus。
2. **权威逐 ROI 映射没有找到，状态为 ROI_SEMANTIC_UNRESOLVED。** CMRL-04/05 本地 RTSTRUCT 审计分别记录 6 个和 126 个 ROI 的 RTROIInterpretedType 为空，名称启发式结果不具诊断力；轮廓几何字段检查也不等于肿瘤语义或 MR 像素空间验收。Plan 记录的 Slicer 同名轮廓观察是 USER-OBSERVED；本任务未重读该对象，不能据此分类。
3. **Clinical XLSX 已证实与 TCIA 当前官方文件逐字节相同。** 官方下载端点在内存中返回 HTTP 200、14,233 bytes；SHA-256 与本机既有只读副本相同：a59d29c86bb45bca98649d1eb8c7a533558fd1cf7b6beb35f5175ea47a04d1c9。TCIA 页面标为 clinical Version 2，2023-02-23 更新；更新说明是为一名受试者补入一个 Time to Distant Metastasis 值。没有取得旧版 XLSX，故未做 V1/V2 逐行差分。
4. **临床表可作结构描述，不能建立可用疗效或生存标签。** 实测为 1 个工作表、28 条非空数据行、9 个命名字段；候选键有 23 个非空且互异值、5 行缺键。没有公开行级 codebook 说明记录粒度、事件标准、时间起点、删失规则或随访定义。列名和空缺率本身不能定义端点。
5. **患者/临床/DICOM 连接未证实，本地时点仍未分配。** CMRL-06 已将 821 个 manifest 前缀逐一映射到固定 IDC v25.0.0 官方 Series；本地对照仍有 15 个 Series 缺失、73 个 Series 的实例数短缺，共少 1,132 个实例。现有 CMRL-05 安全汇总不提供 Clinical 候选键到 DICOM PatientID 的可信 crosswalk；本轮不重扫全库，JOIN_UNVERIFIED。文献三时点是 SOURCE_DEFINED，本地具体检查日期/剂量与这些时点的关系是 UNASSIGNED。

## 2. 来源证据矩阵

| Claim | 来源与证据级别 | 本次核验内容 | 限制 / 对准入的影响 |
|---|---|---|---|
| S1｜Collection 当前规模、类别和许可 | [TCIA 当前 Collection 页面](https://www.cancerimagingarchive.net/collection/cc-tumor-heterogeneity/)；COLLECTION_REPORTED | 官方当前页检索结果列 23 subjects、171 studies、821 series、131,556 images、28.39 GB；模态含 MR、RTSTRUCT、REG、PT、CT；Clinical 文件类型为 Follow-Up / Classification XLSX，CC BY 4.0。 | 页面直接打开超时；保留官方搜索索引返回的页面正文作为来源证据。Collection 计数不是本地文件或逐人影像完整性证明。 |
| S2｜历史 Collection 页面和研究方案 | [TCIA 历史页面](https://wiki.cancerimagingarchive.net/pages/viewpage.action?pageId=112591753)；COLLECTION_REPORTED | 页面记载治疗前、约 2–2.5 周/20–25 Gy、约 4–5 周/45–50 Gy 三个计划时点，并描述以 T2 MRI 定义 tumor volume contours、PET/CT 辅助配准。 | 历史页不提供每位患者的剂量/日期映射，也没有 DICOM ROINumber↔结构名称表。该页影像大小栏为 26.0 GB，当前页为 28.39 GB；只记录页面口径差异，不据此推断下载缺失。 |
| S3｜原始研究勾画与分析时点 | [Bowen et al., 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC5899626/)；AUTHOR_REPORTED | 论文报告 21 名患者；MRI/PET 在 pre-RT、early-RT（20–25 Gy）及 mid-RT（40–50 Gy）采集。参考矢状 T2 上勾画 tumor 与 uterus；uterus 辅助解剖对齐；各时点 tumor contour 用于 DCE、DWI ADC、PET 的 tumor voxel 强度直方图分析。 | PMC 直接抓取触发 reCAPTCHA；可读到 PMC 索引的论文全文内容及 Wiley 摘要。论文没有提供公开 DICOM ROI 编号/名称映射或与 23 个发布对象的逐人对应。 |
| S4｜Clinical XLSX 版本和字节 | [TCIA 当前页面](https://www.cancerimagingarchive.net/collection/cc-tumor-heterogeneity/)及其官方 [XLSX 下载端点](https://wiki.cancerimagingarchive.net/download/attachments/112591753/TCIA_CCTH_Patient%20data_02.06.23.xlsx?api=v2)；FILE-INSPECTED | 官方端点 HTTP 200、XLSX MIME、14,233 bytes，仅内存接收；SHA-256 与本机只读副本相同。TCIA 将 Clinical 文件列为 Version 2，更新日 2023-02-23，记载补入一个 Time to Distant Metastasis 值。 | 未写入新文件或覆盖旧文件。TCIA 数据集引用文本标题仍写 Version 1；citation 标签与 Clinical changelog 是不同发布标记，不能混为一个版本号。没有旧 XLSX，不能逐行比较 changelog 所述变化。 |
| S5｜IDC v25.0.0 官方 Series 与本地差额 | CMRL-06/r2 的 [报告](CMRL-06-IDC-v25%E9%80%90Series%E5%8F%8A%E5%AF%B9%E8%B1%A1%E5%AE%8C%E6%95%B4%E6%80%A7%E8%A1%A5%E8%AF%81.md)及[聚合 profile](../../evidence/r0/tcia_v25_integrity_profile.json)；SOURCE-VERIFIED + FILE-INSPECTED | 固定 Release 25.0.0 官方索引、校验和与 821/821 manifest→Series 映射已由 CMRL-06 核验；本地命中 806 Series、15 缺失、73 Series 实例短缺，共短缺 1,132。 | 官方匿名对象 LIST 不可用，逐对象和位级完整性仍未核实。Series 来源映射不是病例身份或临床行映射。 |
| S6｜本地 RTSTRUCT ROI 字段 | CMRL-04/r2、CMRL-05 的[文件级报告](CMRL-05-TCIA全量DICOM准入审计.md)；FILE-INSPECTED | 人工子集 6/6 与全量候选目录 126/126 的 RTROIInterpretedType 值为空；名称启发式不能决定临床含义。既有报告未验证轮廓与 MR 像素网格叠加。 | 本轮不重读 RTSTRUCT；不输出 ROI 原名、编号、坐标或病例级对象。 |

### 证据等级约定

SOURCE-VERIFIED 表示来源/版本经过核验；COLLECTION_REPORTED 和 AUTHOR_REPORTED 表示发布机构或作者的总体陈述；FILE-INSPECTED 表示本地文件实际检查；USER-OBSERVED 表示用户在图形界面的观察；INFERENCE 是受限推论；UNKNOWN/UNVERIFIED 表示当前证据不能确定。各层级不互相替代。

## 3. ROI 语义与研究流程

### 3.1 原论文支持的内容

Bowen 等 Methods 将参考 MRI 指定为矢状位 T2 加权 MRI，并在 tumor 与 uterus 上勾画体积。论文描述 uterus 用于辅助最终解剖对齐，因为膀胱/直肠充盈可改变 uterus 位置；然后把每个时间点的 tumor contour 刚性复制到 DCE SI ratio、DWI ADC 和 FDG PET 图像集，再转换到各自原生数字网格。这说明论文中的肿瘤分析确实使用 tumor ROI，并有 uterus 辅助结构。

TCIA 历史页面只概述按 T2 MRI 生成 tumor contours 并借助 PET/CT 配准；Collection 页面列出 RTSTRUCT 模态。资料没有提供已发布 RTSTRUCT 中每个 Structure Set ROI 的编号、名称、观察标签与论文中 tumor/uterus 的权威交叉表。论文有两种勾画结构并不能推出某一对本地轮廓的临床类别。

### 3.2 本地 DICOM 证据及 UNKNOWN

- CMRL-04/r2 对用户报告的人工子集审计 6 个 ROI；CMRL-05 对 IDC v25 本地候选目录审计 126 个 ROI。两者均从 RTROIObservationsSequence 读取 RTROIInterpretedType 并与 ReferencedROINumber 关联，全部类型值为空；名称规则结果不是临床判断。
- 既有审计核验了 ROI/Observation/ROIContour 关联、Contour 数组基本结构和直接 DICOM 引用，但没有验证病灶语义、平面/空间叠加、图像实际显示或影像方向。
- Plan 输入记录的同名轮廓观察仅为 USER-OBSERVED；相同显示名称、面积、颜色、内部序号或轮廓大小都不足以确定 tumor 与 uterus。
- **权威逐 ROI 编号/标签映射：未找到。状态：ROI_SEMANTIC_UNRESOLVED。** 任何候选结构都不能当作监督肿瘤分割真值。

### 3.3 尚需官方/作者确认的问题草案（本任务没有发送）

1. 对 TCIA CC-Tumor-Heterogeneity 发布的各 RTSTRUCT，是否存在 Structure Set ROI Number / ROI Name / RTROIObservations 到论文 tumor contour、uterus contour 的逐结构映射？若有，请指出正式表格、supplement、标注模板或具体字段。
2. 论文所述 tumor 与 uterus 是否在每个 pre-, early-, mid-treatment 时点均独立勾画？发布的 RTSTRUCT 中每个 ROI 分别对应哪个原始 T2 Series/时点，是否有官方 crosswalk 可核对？
3. Clinical XLSX 的 early response、局部复发、远处转移、癌症死亡和时间字段是否与 Bowen et al. 的 21 人论文分析属于同一队列及相同定义？请说明行粒度、事件定义、计时起点、删失规则、末次随访规则和缺失/不适用编码。
4. TCIA Collection 23 subjects 与论文 21 人分析之间的关系是否由原始研究明确说明？本报告未构造逐人对照表。

## 4. Clinical XLSX 文件级结构审计

### 4.1 文件来源与检查方法

TCIA 当前 Clinical download 链接指向 cancerimagingarchive.net Wiki 官方下载端点。对该端点仅发出一次 HTTPS GET：状态 200，Content-Type 为官方 XLSX 类型，响应 14,233 bytes、SHA-256 为 a59d29c86bb45bca98649d1eb8c7a533558fd1cf7b6beb35f5175ea47a04d1c9。响应只保存在当前进程内存，没有写入磁盘。本机原有只读文件大小与 SHA-256 完全一致，因此用它完成结构审计；没有覆盖或改写旧文件。

检查使用 Python 3.14.6、openpyxl 3.1.5 和仓库既有 inspect_clinical_xlsx.py 的只读函数（read_only=True）。完整扫描一张工作表，不输出行值或临床类别值。小于 5 的类型频数及全部类别频数均不进入公共 profile。TCIA 当前 Collection 页直接打开超时，但官方页面搜索索引返回 Version 2 和 changelog；官方文件下载端点实际返回并与本机副本逐字节匹配。

### 4.2 工作表、行粒度与字段缺失

工作簿有 1 张工作表，声明范围 A1:K33；首行识别为表头，9 个命名字段；28 条非空数据行。候选身份字段标题在公共表中脱敏。该字段有 23 个非空、互异的文本值，5 行为空；未发现重复非空值。其他 8 个发布字段的结构如下。数量是非空/空值，不是结局类别计数。

| 发布字段（身份字段标题脱敏） | 非空 / 空 | 实测存储类型（仅安全聚合） | 可支持的含义 |
|---|---:|---|---|
| 候选身份字段（标题已脱敏） | 23 / 5 | 文本 23 | 只能称为候选键；不是已验证 TCIA Subject ID 或 DICOM PatientID |
| Early response (1-2 months post-therapy) | 28 / 0 | 文本 28 | 标题提示早期治疗反应；没有公开编码字典 |
| Local Recurrence (y/n) | 23 / 5 | 文本 23 | 候选事件字段；y/n 与缺失/不适用语义未由 codebook 核验 |
| Time to Local Recurrence (weeks) | 5 / 23 | 数值型 5 | 单位仅来自字段标题；计时起点与阴性/删失处理未知 |
| Distant Metastasis (y/n) | 23 / 5 | 文本 23 | 候选事件字段；不解释实际类别值 |
| Time to Distant Metastasis (weeks) | 6 / 22 | 数值型 6 | 版本 2 更新说明提及一个补值；不从数量推断事件人数或对应行 |
| Death from Cervical Cancer (y/n) | 23 / 5 | 文本 23 | 候选事件字段；事件归因及无事件如何编码未知 |
| Time to Death from Cervical Cancer (weeks) | 8 / 20 | 数值型 8 | 计时起点、死因判定与删失规则未定义 |
| Disease Status (at last contact) | 23 / 5 | 文本 23 | 标题提示随访状态，但没有定义日期、状态表或截止日期 |

未发现公式或日期/时间类型单元格。工作簿有字段标题而非完整 codebook；所查 TCIA 发布页没有附独立公开数据字典。字段频数汇总不含原始行值。候选身份键的 23 个互异值与 Collection 的 23 subjects 数值相同，只是数量相同，不能证明行粒度、身份或影像配对。

### 4.3 终点/删失可用性

该表具有治疗反应、局部复发、远处转移、癌症死亡、对应时间数值及末次接触状态等候选标签。仅凭字段名和存储类型，不能确定：

- 事件诊断/判定标准、时间起点、时间单位是否真为周、随访截止时间；
- 空值、非适用值、事件未发生、失访、删失和末次随访之间的区别；
- 是否可定义 DFS、OS、局部控制或任何标准应答分类；
- 每行是否代表一位患者，或是否存在访视/时间点/多终点行。

Bowen 论文报告其研究分析在治疗结束后约一个月依肿瘤体积变化进行响应评估，并用残余体积相对基线的阈值（文中表述为低于基线 10%）区分分析组；一名患者因随访不足未纳入该项响应分析。Clinical 表中的 early response 标题是治疗后 1–2 个月，但没有来源说明证明它采用相同评估者、同一体积算法、同一阈值或同一 21 人队列。因此不得用论文阈值重编码 Clinical 表，也不得将发布表标签作为已验证预测目标。21 人论文样本与 TCIA 23 人 Collection 的具体差额原因在查阅来源中未明确。

## 5. 临床连接与时点映射

### 5.1 Patient/Clinical/DICOM join

现有 CMRL-05 只公开安全聚合的 DICOM PatientID 键计数；CMRL-06 的 821/821 连接是 manifest source prefix 到官方 Series 的来源映射，不是 Clinical 候选键到 DICOM PatientID 的患者身份 crosswalk。本次查阅的 CMRL-05 报告/profile 只含安全聚合；在其已知忽略区产物中也未识别可信 patient-to-clinical 映射工件，因此不发起 join。本轮未比较任何候选键与 PatientID，也未重扫 DICOM。

**状态：JOIN_UNVERIFIED。** 不能用同为 23 的计数、行号、模糊文本、日期猜测、哈希前缀或 ROI 命名建立身份对应。

### 5.2 文献时间轴与本地时间点分级

| 层级 | 当前证据 | 状态 |
|---|---|---|
| SOURCE_DEFINED | TCIA 页面：治疗前 0 Gy；约 2–2.5 周、20–25 Gy；约 4–5 周、45–50 Gy。Bowen 等：pre-RT、20–25 Gy early、40–50 Gy mid。 | 已证实研究计划/论文分析时点；两个来源 mid-RT 剂量范围略异，照录不合并成更精确的患者事实。 |
| DICOM_LINKED | 没有经验证的患者、实际治疗日期/剂量、Study/Series 与 Clinical row crosswalk。 | NOT VERIFIED |
| DESCRIPTION_ONLY | CMRL-05/06 曾将部分 MR Series 按名称/序列参数列为 T2 候选。描述文本不是治疗时点或剂量证据。 | DESCRIPTION_ONLY |
| UNASSIGNED | 没有对本地每位候选患者的 baseline / early / mid 实际 Series 指派。 | 当前本地时点映射 |

不能从研究计划推断发布的 23 名受试者人人具备三时点影像；也不能从 SeriesDescription 中数字、StudyDate 或 RTSTRUCT 文本将本地序列自动分配为治疗时点。若日后获批纵向任务，必须为输入影像和结果建立患者级分组；同一人的所有 Study、Series、时点、多模态图像和派生副本必须留在同一训练/验证/测试分区。baseline 预测不能使用 mid-RT 图像或治疗后结局信息。

## 6. 五类任务准入矩阵

| 任务 | 状态 | 缺少的最低证据 / 下一步 |
|---|---|---|
| 单例 MRI 读取、方向与 spacing 教学 | CONDITIONAL | 后续由用户从官方映射可识别且本地实例数完整的一个 MR Series 中选样；用户在本机实测解码、方向、spacing 与空间质量。现有任务未读像素，不能称为 R2 或空间 QC 已通过。 |
| 3D 宫颈肿瘤分割 | NO-GO | 需权威 tumor ROI 编号/语义映射、逐时点 MR-RTSTRUCT 关联、像素空间核验及可审计的 patient-level split。 |
| 体积级 Radiomics | NO-GO | 需确证 tumor VOI、几何有效性、稳定物理空间/预处理与可复现特征定义；当前无可信 tumor VOI。 |
| 跨时点变化分析 | NO-GO | 需实际 patient-level timepoint/series 连接、完整影像和协议可追溯；文献时点不等同于本地时点映射。 |
| 治疗应答 / DFS / OS | NO-GO | 需被证实的临床定义、终点时间起点、事件/删失规则、治疗信息与影像患者键精确连接；现表不足以定义这些任务。 |

## 7. 最小后续补证与隐私

1. 优先查找 TCIA/IDC 官方发布的 ROI crosswalk、原始标注模板、补充材料或数据字典；若没有，用户可自行决定是否发送第 3.3 节的问题草案给作者。本任务没有发信。
2. 若将来开展空间教学，先由用户明确选一个本地实例数与官方索引相符的 MR Series 和其直接引用的 RTSTRUCT，再由用户在本机查看器实测图像方向与 contour 叠加。未确认 tumor ROI 前只作结构/空间练习，不称为肿瘤 Mask。
3. 临床端点继续准入至少需要正式 codebook（事件标准、起点、单位、删失、失访和末次接触定义）、与 21/23 cohort 关系的官方说明，以及合法、精确、不含模糊碰撞的病例 crosswalk。私有映射不得提交或显示。
4. 若上述补证无法取得，保留 UNKNOWN，并在 R0 总体审查中考虑将 TCIA 限定为 DICOM/引用/空间 QC 教学候选，而不是监督分割或临床建模数据。

公共报告/profile 没有患者字段值、候选键、DICOM UID、真实日期、医院、原始路径、RTSTRUCT 原名/编号、坐标、截图或私有映射。原始 DICOM 未在本轮读取或写入；临床表只在内存/本机只读处理；未向网络传输任何临床行值。

## 8. 运行与限制

- 本地 XLSX 结构扫描：1 个工作簿、1 个 sheet、28 条非空数据行、9 个命名字段；Python 3.14.6、openpyxl 3.1.5；全程 read-only。
- 网络：公开页面/论文查询；官方 XLSX 下载端点 1 次 HTTPS GET，14,233 bytes 仅在内存，不写盘。无 DICOM、S3、HEAD 或对象列表请求；无外部上传。
- 真实 DICOM 重扫 / RTSTRUCT 复查 / PixelData 解码 / 图像空间显示：NOT RUN（按 Plan 不需要新证据且禁止全量重扫）。
- 新增审计代码 / 合成单元测试：NOT RUN；本任务复用了既有工作簿只读 profile 函数，未新增脚本。已检查聚合 JSON 与报告不含患者行值、键、UID、ROI 原名/编号或本地原始路径；本地工作簿行值没有进入持久输出。
- 本任务未合并 PR、未转 Ready、未改写历史。Main 仍须独立审查，不据此宣称 R0 完成。

## 9. 来源

- Mayr et al. TCIA Collection: [TCIA current page](https://www.cancerimagingarchive.net/collection/cc-tumor-heterogeneity/), [historical TCIA page](https://wiki.cancerimagingarchive.net/pages/viewpage.action?pageId=112591753), DOI [10.7937/ERZ5-QZ59](https://doi.org/10.7937/ERZ5-QZ59).
- Bowen SR et al. *Tumor radiomic heterogeneity: Multiparametric functional imaging to characterize variability and predict response following cervical cancer radiation therapy*. J Magn Reson Imaging. 2018;47:1388–1396. DOI [10.1002/jmri.25874](https://doi.org/10.1002/jmri.25874), [PMC full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC5899626/), PMID [29044908](https://pubmed.ncbi.nlm.nih.gov/29044908/).
- CMRL-04、CMRL-05 与 CMRL-06 报告列于来源矩阵和项目证据登记。
