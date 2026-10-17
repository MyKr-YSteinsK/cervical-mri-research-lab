# 02｜候选数据与可获得性证据登记（截至 2026-10-17）

## 状态约定

- `SOURCE-VERIFIED`：在官方原文、发布页或仓库 README 核实**发布者所声称的内容**。
- `FILE-NOT-INSPECTED`：没有下载/解包，因此文件结构、患者匹配、实际标签和下载能否完成**尚未验收**。
- `RESTRICTED`：获取须申请、密码、平台授权或机构条件。
- `NOT-FOR-TUMOR-MASK`：提供的 Mask 不对应宫颈原发肿瘤。
- `QUERY-UNAVAILABLE`：当前执行环境对公开元数据端点未获得可用响应；不等于资源不存在或受限。
- `FILE-INSPECTED`：已在本地检查文件，但仅覆盖相应任务写明的范围；不自动表示像素、几何对齐或临床语义已验收。
- `USER-REPORTED-SOURCE`：本地文件来源由用户报告，尚未由 manifest 或其他来源证据独立确认。

本次工具核查包括在线官方来源、论文、公开 GitHub 目录及六篇原 PDF；**没有下载或运行任何医学研究数据**。发布页展示的大小≠本地下载成功。

## D01｜FlexFair 四中心宫颈癌 T2WI 肿瘤分割数据｜新增最高优先核验

状态：`SOURCE-VERIFIED / FILE-NOT-INSPECTED / R0-PRIORITY-1`

- 论文：Xing et al. *Achieving flexible fairness metrics in federated medical imaging*. Nature Communications (2025), DOI https://doi.org/10.1038/s41467-025-58549-0
- 作者声称：四家医院共 **678 名患者**，治疗前轴位 T2WI MRI，肿瘤 ROI 由放射科医生在 ITK-SNAP 标注；四中心患者数 **89、65、278、246**（总计 678）。中心扫描参数/层厚不一致；适合研究中心域差异。
- 发布页：https://figshare.com/articles/dataset/Achieving_Flexible_Fairness_Metrics_in_Federated_Medical_Imaging/28639598 ；页面宣称 **332.58 MB**，CC BY 4.0。
- 作者代码：https://github.com/MaksimXing/FlexFair ；已核实公开仓库存在 `Code/F_Polyp_and_Cervical_Cancer/` 代码目录与 README。
- **关键需审计冲突**：Nature 原论文引用 Figshare **28639598**，GitHub README 另写 **28636133**。须确认两记录之间关系，不能盲选其中一个下载。此外文章另有按中心 **1383/1332/323/328 图像样本**的计数，与 678 名患者不是相同统计口径；必须通过实际文件检验切片/患者映射。原论文使用图像级分割任务，不能假设发布包保留完整 3D 原始体数据、患者 ID 或直接用于 PyRadiomics 的物理空间元数据。
- **R0 Go 门槛**：可以合法获得真实图像与对应掩膜；图像/Mask 数量、分辨率、标签含义可验证；若研究患者级 split/外部验证，必须能可靠识别患者和中心且查重。若仅有切片 PNG 且无患者关联，应限制研究为图像级分割演示，不宣传患者级泛化/体积级 Radiomics。

## D02｜CCMD 宫颈癌 T2WI 肿瘤分割｜第二优先并行申请

状态：`SOURCE-VERIFIED / RESTRICTED / FILE-NOT-INSPECTED / R0-PRIORITY-2`

- 论文：Liu et al. *An open MRI dataset for cervical cancer with tumor segmentation using nnU-net*. Signal, Image and Video Processing (2025) DOI https://doi.org/10.1007/s11760-025-04277-3
- 官方仓库：https://github.com/peekaboo990/CCMD-Cervical-Cancer-MRI-Dataset
- 原作者声称：**151 名患者**，宫颈肿瘤 T2WI、医生 ROI；标注为分割任务；论文 nnU-Net-3D Dice 0.8181，属于作者实测而非用户成果。
- 获取：仓库 README 显示 Baidu 网盘链接、需要发送研究用途与机构信息到 `n13677994752@163.com` 获取密码；并非无障碍公开下载；遵守限制使用条款。
- **关键需审计冲突**：README 先将数据格式写为 DICOM 原图和 PNG 标注，却在示例目录中列出 `T2wI.nrrd` 与 `tumor_mask.nrrd`；论文自称数据和代码可用，但 2026-10-16 公开 GitHub 根目录核验仅 `README.md`，未见实际训练代码。不能声称仓库附有完整可运行 nnU-Net 代码。
- **R0 Go 门槛**：申请得到合法访问；逐患者原图/Mask 同源且可空间对应；明确具体图像方向（论文/README 报矢状位）、体素间距与 2D/3D 结构；是否含临床疗效标签另行核实，默认 **不具备**。

## D03｜TCIA CC-Tumor-Heterogeneity｜容易核验的公开起点

状态：`SOURCE-VERIFIED / PUBLIC-METADATA / QUERY-UNAVAILABLE / USER-REPORTED-SOURCE / FILE-INSPECTED（本地人工下载子集）/ R0-PRIORITY-3`

- 官方：https://www.cancerimagingarchive.net/collection/cc-tumor-heterogeneity/ ; DOI https://doi.org/10.7937/ERZ5-QZ59
- TCIA 列出：**23 名患者、171 个 studies、821 个 series、131556 张影像**；多模态 MR、RTSTRUCT、REG、PT、CT；临床 `Follow-Up` 与 `Classification` XLSX；影像 **28.39 GB**，临床表 **13.9 KB**；CC BY 4.0，需合规引用。
- IDC 官方也列出该队列：https://portal.imaging.datacommons.cancer.gov/collections/cc_tumor_heterogeneity/ ；可考虑分批检索与下载，而非一次拉取所有 28 GB。
- **R0 优先操作**：先下载 13.9 KB 临床表并检查字段和编码，再看少量患者 DICOM 与 RTSTRUCT 的序列/ROI/时间点；不假设 23 人都有某一疗效、DFS 或 OS 的完整标签。RTSTRUCT 可能包含多种临床勾画结构，需定位真正肿瘤 ROI，不能将膀胱/器官/计划靶区无审查地当作肿瘤 Mask。
- 用途：数据流验证、图像坐标、RTSTRUCT→Mask、纵向/多序列与探索性 Habitat；样本太少，严禁将复杂模型的高 AUC 解释成稳健疗效模型。
- **CMRL-03（2026-10-16）更新**：官方 Collection 元数据、IDC 页面、CC BY 4.0 与数据引用要求已复核；当时本机 TCIA `getSeries` 超时，IDC REST TLS/浏览器连接失败，未取得文件级证据。具体记录见 [`CMRL-03 审计报告`](../../reports/r0/CMRL-03-TCIA最小MR与RTSTRUCT准入审计.md)。查询失败不证明 Collection 无可用 MR/RTSTRUCT。
- **CMRL-04（2026-10-17）更新**：在用户指定的本地 `data/raw/tcia/ccth_manual/` 子集中完成全量有界 Header 检查：5,959 个 `.dcm`、1,387,467,936 bytes；4,334 MR、917 CT、702 PT、3 REG、3 RTSTRUCT。DICOM `PatientID` 有 1 个不同值，包含 6 个 Study、39 个 Series、27 个 MR Series；此键数不等于已独立核实的真实人数。9 个 MR Series 仅按描述文本规则列为 T2 候选。3 个 RTSTRUCT 共 129 条直接 SOP 引用记录全部解析到本地 T2 候选 MR，患者键、Study、Series、Frame 对照均一致。6 个 ROI 名称只能归入 `OTHER`，且未提供 `RTROIInterpretedType`；未确认原发宫颈肿瘤 ROI。来源仍为 `USER-REPORTED-SOURCE`，没有本地 Collection manifest 证明实际包归属。未解码像素；完整边界见 [`CMRL-04 本地 DICOM 审计报告`](../../reports/r0/CMRL-04-TCIA本地DICOM文件级准入审计.md) 与聚合 JSON。

## D04｜盆骨骨 MRI 预后分析 Zenodo 资源｜有条件支线

状态：`SOURCE-VERIFIED / NOT-FOR-TUMOR-MASK / FILE-NOT-INSPECTED / LOWER PRIORITY`

- https://zenodo.org/records/16934473 DOI https://doi.org/10.5281/zenodo.16934473
- 页面列出 `data.zip` 约 2.1 GB、`masks.zip` 20.1 MB、`slice_cache0_224.zip` 291.3 MB，含临床/影像组学/深度特征表及生存相关结果。
- **关键事实**：其 Mask 是 **盆骨骨骼 segmentation**，而非宫颈原发肿瘤 ROI，不能作为肿瘤自动分割训练集。适合作为潜在预后/表格特征建模支线，前提是合法可获得、事件时间与删失状态完整。

## D05｜Cervical-MD / Cervical-RG｜暂不作为数据依赖

状态：`RESTRICTED / FILE-NOT-INSPECTED / NOT CORE`

- MICCAI 2025 论文：https://papers.miccai.org/miccai-2025/0143-Paper0177.html ; 源代码：https://github.com/LongYu-LY/Cervical-RG
- 是 MRI 多序列报告生成/FIGO 分期的研究，而非疗效二分类；页面有摘要 **3137 MRI-报告 pairs** 与同行评审文本中 **3177 cases** 等不同口径。不能无核实混用，也不能声称全部数据已公开直接下载。

## D06｜原六篇患者数据及 P03 作者代码

- 原六篇中医院级患者原始影像、病理应答标签与精确实验划分没有确认存在无需申请的完整公开包，因此**不选任何一篇为精确数值复现的当前承诺**。
- P03 作者代码：https://github.com/youhs4554/radiomics_CRT ；有 HCR/DLR notebooks、`datasets.py` 与旧版 env；README 明确因患者隐私数据需向作者请求，代码另依赖不公开的路径与 XLSX 划分。可用作**技术学习参考**，不可当作有现成可运行医院实验环境。

## 标签/权限决策矩阵

| 数据 | T2WI | 肿瘤 Mask | 患者 ID/中心 ID | 疗效标签 | 适合最早实验 |
|---|---|---|---|---|---|
| D01 FlexFair | 论文已证实 | 论文已证实 | 实际发布包待检 | 未证实 | 分割/域差异，须核患者映射 |
| D02 CCMD | 论文已证实 | 论文已证实 | 实际包待检 | 未证实 | 分割、Radiomics 稳定性 |
| D03 CC-Tumor | TCIA 有 MR；具体序列待检 | 有 RTSTRUCT；肿瘤 ROI 待检 | TCIA 患者 ID 可查 | 随访/分类字段待检 | DICOM/RTSTRUCT、纵向分析 |
| D04 盆骨骨 | 预处理 T1WI 资源 | **不是肿瘤** | 文件待检 | 生存信息可能有 | 表格特征/生存支线 |
| D05 Cervical-MD | 论文有 | 非核心公开任务 | 未取得 | 不是治疗应答 | 暂不依赖 |

## 不能跨越的边界

- Figure/Abstract 的样本数不等于实际包可训练的患者数。
- 包下载成功不等于拥有可用医学标签；原始影像、切片、ROI、临床标签、时间点必须逐人对应。
- 四中心在论文出现不代表发布包提供中心可识别的拆分键。
- 未验证临床应答标签前不得训练/评估 NACT、NACRT 或 CRT 预测；不能用 FIGO 分期代替疗效。
- 论文发表的 Dice/AUC 非本项目已获得性能。
