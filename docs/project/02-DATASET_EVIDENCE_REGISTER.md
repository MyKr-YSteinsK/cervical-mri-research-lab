# Dataset Evidence Register

更新时间：2026-10-18。此登记汇总当前数据来源与准入边界；逐任务原始记录保存在[历史归档](HISTORY_ARCHIVE.md)。

## 状态约定

- SOURCE-VERIFIED：官方页面、论文或发布者确认了其声明，不等于本地文件已检查。
- FILE-INSPECTED：仅对相应任务实际读取的本地文件范围成立，不自动表示像素、空间、语义或临床有效性通过。
- USER-REPORTED-SOURCE：文件来源由用户报告，未独立验证完整来源链。
- RESTRICTED：获取需要申请、密码或其他访问许可。
- UNVERIFIED、NOT-VERIFIED、NO-GO：保留具体未核实或当前不准入状态，不按文件数量或相似命名推断。

## 候选数据

| 候选 | 已核实事实 | 当前限制与准入 |
|---|---|---|
| **TCIA CC-Tumor-Heterogeneity** | 官方 Collection 发布 MR、CT、PT、REG、RTSTRUCT 及临床表。用户本地 IDC v25 候选目录经 CMRL-11 索引：130,424 个 DICOM、171 个 Study、806 个实际 Series；Header 解析 130,424/130,424。 | 固定 IDC idc-index-data Release 25.0.0 逐 Series 对照为 821 个预期 Series，本地缺 15 个，73 个 Series 共短缺 1,132 个实例。对象字节完整性未验证。官方 ROI 定义到本地结构的映射、患者连接、治疗时点和临床终点仍未核实。不得将 RTSTRUCT 名称或轮廓本身称为已验证肿瘤 Mask。 |
| **FlexFair** | 论文与发布页面声称四中心 678 名宫颈癌患者；已审计公开 PNG 包的文件结构与图像/Mask 文件名配对。 | 患者和中心身份、患者级拆分以及 678 人与 PNG 数量的映射仍未核实。独立 F01 教学线已由用户取消；本地原始包继续保留。仅可在重新确认任务边界后考虑 2D 图像级教学。 |
| **CCMD Cervical Cancer MRI** | 论文和作者仓库描述 151 名患者及 T2WI/ROI。 | 数据获取需要申请/密码，当前没有本地文件级证据；格式描述存在差异。保持 RESTRICTED / FILE-NOT-INSPECTED。 |
| **其他替代或派生资源** | 已完成的来源预筛发现部分公开记录描述 OAR 勾画、切片派生数据或申请访问数据。 | 尚无新增可追溯、经空间验证的宫颈原发肿瘤三维标注。不得将同队列派生数据当作独立患者或外部验证。逐来源证据见历史归档。 |

## CCTH 附加证据

- CMRL-13 通过固定 v25.0.0 Series UID 对照确认 15 个空目录对应 15 个官方缺失 Series（REG 10、RTSTRUCT 5），每个预期 1 个实例。试验下载 1 个 RTSTRUCT 对象，来源与对象标识匹配；没有权威逐对象校验和，**位级完整性未验证**。试验文件仍独立保存在忽略目录 .local/ccth-recovery-pilot/，不属于正式原始数据树。
- CMRL-12 报告：PIXEL_QC=PASS、GEOMETRY_QC=FAIL、RTSTRUCT_ALIGNMENT_QC=FAIL、MASK_QC=FAIL、ROI_SEMANTIC_QC=PENDING。私有 MRI、Mask、QC JSON 和图片目前未找到；不可声称已备份或重建。
- 本机精确文件/UID 映射仅存 .local/dataset-index/；CMRL-06 固定 v25.0.0 索引及私有缺口表仅存 .local/private-evidence/cmrl-06-idc-v25/；CMRL-08 私有交叉索引仅存 .local/private-evidence/cmrl-08-crosswalk/。以上均被 Git 忽略，不能发布。

## 当前准入

总体阶段仍为 **R0 NOT COMPLETE**。尚无通过几何及语义验收的宫颈原发肿瘤 Mask；监督式三维分割、体积 Radiomics、纵向治疗分析和临床结局预测均为 **NO-GO**。任何阶段推进或数据集接受仍需用户/项目 Main 的科研审查决定。

来源与逐任务证据请看[07｜Sources and Open Questions](07-SOURCES_AND_OPEN_QUESTIONS.md)和[CMRL 历史归档索引](HISTORY_ARCHIVE.md)。
