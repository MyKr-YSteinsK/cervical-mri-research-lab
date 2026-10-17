# TASK_RESULT｜CMRL-09 / r1

- **Status:** COMPLETE（Plan 授权的来源追索与决策材料已完成；G7 Git / Draft PR 交付核验待提交后更新）
- **Branch / Base SHA / Final HEAD / PR URL / Draft:** codex/r0-09-tcia-authoritative-annotation-review / 3b79715a49a4ed99183a21499a87d0389056faf5 / PENDING / PENDING / PENDING；新 Draft PR 目标 base 为 codex/r0-08-tcia-private-crosswalk-screen。
- **Sources inspected:** DIRECT：TCIA 历史 Wiki、IDC Collection、Wiley 论文摘要；INDEX-ONLY：TCIA 当前 Collection、PMC 论文正文、官方 FAQ；UNAVAILABLE：TCIA 当前页直接访问、Data Dictionary、Support 直接页面、ClinicalTrials.gov 记录；来源及访问方法见报告和 source register。
- **ROI authoritative crosswalk:** NOT_FOUND_IN_REVIEWED_SOURCES；ROI_SEMANTIC_UNRESOLVED 保持。
- **Clinical codebook & single-cell rows:** 临床字段代码本 NOT_FOUND_IN_REVIEWED_SOURCES；论文响应定义 PARTIAL_SOURCE_DEFINED 且仅适用于作者报告的论文端点；五个未键控单格行角色 UNKNOWN。
- **Cohort & treatment timepoint linkage:** 21 人与 23 subjects 的集合关系、Clinical 候选键与 DICOM PatientID 命名空间、DICOM Series 到逐患者治疗时点均 NOT_FOUND_IN_REVIEWED_SOURCES；研究方案时点 SOURCE_DEFINED，但来源口径差异保留。
- **R0 eligibility matrix:** reports/r0/CMRL-09-R0数据集任务准入决策备忘录.md；没有提前 GO。TCIA 单例空间 QC 为 CANDIDATE/CONDITIONAL；TCIA 分割、Radiomics、纵向与临床结局 NO-GO；FlexFair 仅条件性 2D 图像级教学；CCMD 仍 RESTRICTED。
- **Author/TCIA inquiry:** UNSENT ONLY；草案在来源追索报告内；未发送、未提交。
- **Privacy & no-data-touch evidence:** 本次没有读取本地 DICOM、Clinical V2 或私有索引；没有读 PixelData/ContourData；没有公开数据下载、网络联系人操作或用户身份请求。新增 JSON/报告不含患者键、病例行值、UID、原始 ROI 标签或私有路径。
- **Tests:** NOT APPLICABLE；未新增代码或脚本。执行文档/JSON 检查与 git diff --check。
- **Deliverables and verification:** [来源追索报告](CMRL-09-TCIA权威ROI与临床定义追索报告.md)、[来源登记](../../evidence/r0/tcia_authority_source_register.json)、[准入备忘录](CMRL-09-R0数据集任务准入决策备忘录.md)；项目状态增量见 docs/project/02、07、08。
- **Remaining blockers / next decision for Main:** 权威 ROI crosswalk、Clinical V2 codebook、21/23 cohort provenance、临床命名空间和真实时点连接仍缺；Main/用户决定是否自行咨询发布者、进行单例空间教学或选择条件性 2D 路线。R0 NOT COMPLETE。
