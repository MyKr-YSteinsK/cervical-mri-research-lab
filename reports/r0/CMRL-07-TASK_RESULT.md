# TASK_RESULT｜CMRL-07 / Plan r1

## 状态

**COMPLETE**：在 CMRL-Plan-07 r1 授权范围内完成 TCIA 官方来源/原始论文核验、Clinical XLSX 当前版本与本地副本字节核对、逐字段脱敏结构审计、ROI/时间点/患者连接分级、准入矩阵和项目状态更新。关键 ROI 语义、临床结局定义、患者连接与本地实际时点仍 UNKNOWN/UNVERIFIED。科研阶段保持 **R0 NOT COMPLETE**；未批准分割、Radiomics、临床模型或下一阶段。

## Gate 回执

| Gate | 状态 | 实际结果 |
|---|---|---|
| G1｜Plan、仓库基线与 PR 链 | PASS | Plan-07 r1 可读；从 PR #7 head 31b40652758f5804ade9d95d3145ff70b1a93d9b 建立独立分支。PR #7 复核为 OPEN / Draft / 未合并；其 head/base 未改。 |
| G2｜官方来源、原文、ROI | PASS（结论保留 UNKNOWN） | TCIA 当前页、历史页、IDC v25.0.0 已核验记录和 Bowen 原文进入来源矩阵；作者报告的双结构勾画与逐 ROI DICOM 映射分开。权威 ROINumber/name→tumor/uterus 映射未找到，ROI_SEMANTIC_UNRESOLVED。 |
| G3｜Clinical XLSX | PASS | 官方端点返回 14,233 bytes，HTTP 200、XLSX MIME；SHA-256 与本机只读副本一致。只读扫描 1 sheet、28 非空行、9 命名字段；聚合 profile 隐藏身份字段标题及所有小类别频数/行值。事件、起点与删失 codebook 未找到。 |
| G4｜病例连接与影像时点 | PASS（受限结论） | Clinical 候选键到 DICOM PatientID 为 JOIN_UNVERIFIED；文献计划时点 SOURCE_DEFINED，本地实际时点 UNASSIGNED；未重扫 130,424 个 DICOM。 |
| G5｜任务准入与泄漏风险 | PASS | 已覆盖单例空间教学、3D 分割、体积 Radiomics、跨时点、应答/DFS/OS 五类；仅单例教学为 CONDITIONAL，其余 NO-GO。要求 patient-level 分组，baseline 预测不可使用未来影像/结局。 |
| G6｜运行、隐私与代码 | PASS（无新增脚本） | Python 3.14.6 / openpyxl 3.1.5；复用既有 read-only profile 函数。仅 1 次官方 XLSX HTTPS GET，14,233 bytes 在内存；无 DICOM/S3 请求、原始文件改动或外部上传。没有新增脚本，合成脚本测试 NOT RUN；检查聚合 JSON 与报告不含患者行值、键、UID、ROI 原名/编号或本地原始路径。 |
| G7｜Git 与交付 | PENDING | 报告及脱敏 profile 已准备；完成检查、提交、推送及创建 Draft PR #8 后追加最终远端 HEAD 和 PR URL。未合并、未改 PR #1–#7 状态、未转 Ready、未 force-push。 |

## 核心证据

- TCIA 当前页列 23 subjects、171 studies、821 series、131,556 images，含 DICOM 与 Follow-Up / Classification XLSX，CC BY 4.0；Clinical changelog 标为 Version 2（2023-02-23），所述变化为向一名受试者补入一项远处转移时间。页面数据集 citation 标签仍写 Version 1；影像 IDC Release 与 Clinical XLSX 版本分别记录。
- Clinical 本地副本与 TCIA 官方当前端点返回文件的 SHA-256 均为 a59d29c86bb45bca98649d1eb8c7a533558fd1cf7b6beb35f5175ea47a04d1c9，大小均 14,233 bytes。没有保存第二份或覆盖原文件。
- Clinical XLSX：28 行、9 个发布字段；候选键 23 个互异非空值、5 行缺失，记录粒度 UNKNOWN。没有可信定义可解码 response、event、时间起点、删失、DFS/OS 或末次随访状态。
- Bowen et al. 2018 报告 21 名患者、pre/early/mid RT 影像时点，在参考矢状 T2 上勾画 tumor 与 uterus；论文说明 uterus 辅助配准，tumor ROI 用于多时点多模态强度分析。TCIA 当前页报告 23 subjects；两者关系未证实。论文未提供已核实的发布版 DICOM ROINumber/ROIName 对照。
- CMRL-04/05 文件级记录中 6/126 个 ROI 的 RTROIInterpretedType 值为空，ROI 名称启发式不是语义证据。CMRL-06/r2 映射到 821/821 官方 Series，但本地仍缺 15 Series、73 Series 实例数短缺、总计少 1,132 实例；逐对象完整性未验证。
- 文献时点为 SOURCE_DEFINED；本地 MR SeriesDescription 只能算 DESCRIPTION_ONLY，当前没有患者级实际治疗时点 crosswalk，具体本地时点映射 UNASSIGNED。
- 具体字段频数、来源限制、ROI 问题草案和五类任务 Gate 见 CMRL-07 主报告；机器可读安全聚合见 tcia_source_roi_clinical_profile.json。

## 官方来源清单

- TCIA 当前 Collection 与 Clinical 版本记录：[当前 Collection 页面](https://www.cancerimagingarchive.net/collection/cc-tumor-heterogeneity/)；官方 Clinical 文件端点：[XLSX](https://wiki.cancerimagingarchive.net/download/attachments/112591753/TCIA_CCTH_Patient%20data_02.06.23.xlsx?api=v2)。
- TCIA 历史 Collection 页面：[Wiki 页面](https://wiki.cancerimagingarchive.net/pages/viewpage.action?pageId=112591753)。
- Bowen et al. 2018 原始研究：[PMC 全文](https://pmc.ncbi.nlm.nih.gov/articles/PMC5899626/)、[PubMed 记录](https://pubmed.ncbi.nlm.nih.gov/29044908/)、DOI [10.1002/jmri.25874](https://doi.org/10.1002/jmri.25874)。
- IDC CC-Tumor-Heterogeneity：[IDC Collection 页面](https://portal.imaging.datacommons.cancer.gov/collections/cc_tumor_heterogeneity/)；固定 v25.0.0 资产、Series 对照与本地差额沿用 [CMRL-06 报告](CMRL-06-IDC-v25逐Series及对象完整性补证.md)。
- 本地 RTSTRUCT 元数据依据：[CMRL-04 报告](CMRL-04-TCIA本地DICOM文件级准入审计.md)、[CMRL-05 报告](CMRL-05-TCIA全量DICOM准入审计.md)。

## 产物

- reports/r0/CMRL-07-TCIA原始研究ROI时点与临床字段核验.md
- evidence/r0/tcia_source_roi_clinical_profile.json
- 本次更新 docs/project/02-DATASET_EVIDENCE_REGISTER.md、docs/project/07-SOURCES_AND_OPEN_QUESTIONS.md、docs/project/08-RESEARCH_STATE.md

**后续由 Main 决定**：是否继续查找官方 ROI crosswalk/codebook，是否由用户自行联络作者，以及是否只批准一个有官方映射、实例数完整的单例 MRI 空间教学候选。当前任务不代表 Main 接受数据或 R0 收口。
