# TASK_RESULT｜CMRL-10 / Plan r1

- **Status:** COMPLETE（CMRL-10 有界公开来源、元数据与候选准入审计完成）；研究阶段仍为 **R0 NOT COMPLETE**。
- **Branch:** `codex/r0-10-derived-mask-provenance-screen`
- **Exact base:** PR #10 HEAD `3ce361383cf222cf667a31d2a0ee87ed3d6b5a88`; PR #10 当时 OPEN / Draft、base `codex/r0-08-tcia-private-crosswalk-screen`。
- **Plan copy:** 按用户要求，外部 Plan r1 已复制到 `D:\Downloads\CMRL-Plan-10-宫颈癌MRI派生标注溯源与替代数据预筛.md`；复制前目标不存在，源/副本 SHA-256 均为 `9F185535956713B1AAA9DC900A69E9B42C25580F742F46B678F82DCCA848CC4A`。仓库内没有 Plan 副本。
- **Delivery:** 新建独立 Draft PR #11，base/head/最终远端 SHA 将在提交与 push 后填写；不合并、不更新 main、不改动其他 PR。

## G1–G7 Gate 回执

| Gate | 状态 | 结果 |
|---|---|---|
| G1 基线与权限 | PASS | Plan r1 可读；PR #10 为 OPEN/Draft 且 head 为指定精确 SHA；新分支从该 SHA 建立。只按 Plan 做公开来源/元数据审计；Plan 副本只写到用户指定的 `D:\Downloads`。 |
| G2 来源链 | PASS（保留 UNKNOWN） | 审阅 TCIA/Bowen 原始来源、BiomedSegFM、MedOtter、FlexFair、CCMD 与 MOGaMBO、Cervical-MD、2022 机构数据论文。BiomedSegFM `gts`、MedOtter ROI/timepoint 声称无权威转换链；报告没有把第三方声明升级为 TCIA/原作者认可标签。 |
| G3 许可与公开性 | PASS（限制已分层） | TCIA、FlexFair、MOGaMBO 的官方记录许可与范围分别登记；BiomedSegFM 的 NC-SA 卡片与上游 TCIA 许可分开；MedOtter 再发布权利 `LICENSE_UNVERIFIED`；CCMD/Cervical-MD 访问与许可缺口保留。没有绕过密码或申请访问。 |
| G4 维度与标签字段 | PASS（METADATA-ONLY） | BiomedSegFM 只记录数据卡对 `imgs/gts/spacing`、强度和切片预处理的描述；内部 shape/dtype/数组值未检查。文件夹 7 项/6,302,340 bytes 为 Hub 目录元数据，不能证明原生体、tumor ROI 或病例/时点关系；origin/direction 未有证据。 |
| G5 队列与泄漏 | PASS | BiomedSegFM、MedOtter 按 CCTH 来源重打包处理，不能作为新患者或外部验证。FlexFair 继承 CMRL-01/02 的患者键缺口和跨 split 重复结论。其它数据源无患者级跨库身份核查。 |
| G6 安全与执行边界 | PASS | 原始 DICOM、Clinical V2、CMRL-08 私有候选索引均未读取；本轮下载数据资产 0 bytes。无病例级 UID、患者键、日期、路径、ROI 原始名称/编号、像素/Mask、凭据写入报告或 JSON。科研核心代码、图像解码/显示、Mask 转换、Radiomics、模型均 `NOT RUN`；R0 仍 `NOT COMPLETE`。 |
| G7 Git 交付 | PENDING | 报告、矩阵、JSON 与状态增量已写入允许路径；提交前还将检查 staged 文件、隐私模式与 `git diff --check`，随后正常推送并核验 PR #11 的 base/head/draft 与远端 SHA。 |

## Findings and candidate decisions

- **新的权威宫颈原发肿瘤 3D Mask：无。** TCIA 的 `ROI_SEMANTIC_UNRESOLVED` 保持；论文中 tumor/uterus 勾画不是发布 RTSTRUCT 的逐 ROI crosswalk。
- **BiomedSegFM：** 作者说明有标签切片转为 NPZ；CCTH 目录有 7 项/6,302,340 bytes 元数据。`gts` 身份、完整空间与派生许可链 UNKNOWN；不下载任何 NPZ。
- **MedOtter：** 第三方对 ROI 名称、timepoint 和 tumor-only 的具体声称未经权威交叉核验；原始许可不自动证明第三方再发布权。不是独立 CCTH 患者群。
- **FlexFair：** 官方 Figshare 28639598 v1 为 CC BY 4.0、348,731,016 bytes；作者 README 指向的 28636133 查询 HTTP 404，来源冲突保留。既有公开包审计只支持条件性 2D 教学。
- **CCMD：** 仍 RESTRICTED，文件未取得；论文、作者仓库关于“公开”与密码申请并存，格式冲突和 license 未解决。
- **MOGaMBO：** Zenodo open/CC BY 4.0，作者登记描述 3D T2 MRI/OAR；大 ZIP 未下载，无 GTV 证据。
- **Cervical-MD 与 2022 机构研究：** 论文/作者描述不是公开数据可用证明；一个访问需申请，另一个未找到公开资产或许可。
- **许可/任务矩阵：** 见 [CMRL-10 候选数据与任务对照矩阵](CMRL-10-R0候选数据与任务对照矩阵.md)。没有任何模型、实验指标或 R0 接纳结论。

## Execution and safety receipt

- **Public data-asset download:** 0 bytes；**Hub/API/page metadata:** read-only，具体 API 响应字节未计量。
- **File access:** no local raw MRI/DICOM, Clinical row values, patient-level maps, candidate keys, or pixels/masks accessed.
- **Network actions:** public page/API GET only; no authenticated downloads, no outbound upload, no access request, no email, no unknown terms acceptance.
- **Tests:** `NOT APPLICABLE`（无代码/脚本变更；按 Plan 做 JSON 解析、隐私和 Git 文档检查，不运行项目测试）。
- **Next two highest-value actions:** (1) 用户自行决定是否向 BiomedSegFM/竞赛源索取 `gts` 原始 ROI、版本和处理/许可来源说明；(2) Main/用户选择下一步是单例 TCIA 用户主导空间 QC、合法申请 CCMD，或在 OAR 目标下另行规划 MOGaMBO 文件检查。
