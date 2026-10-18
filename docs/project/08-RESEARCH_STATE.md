# CURRENT RESEARCH STATE

更新时间：2026-10-18。仓库历史已整理到 main；此项工程整合不构成科研证据接受或阶段推进。

## 当前阶段

唯一活动阶段仍为 R0-DATA-ACCESS-AUDIT，**R0 NOT COMPLETE**。用户亲自学习、编写、运行和审查 MRI 处理、分割、Radiomics、模型训练与解释性核心。没有任何本次仓库治理操作修改科学目标或实验验收状态。

## CCTH 本地数据

- 数据根目录：data/raw/tcia/ccth_idc_v25_full/cc_tumor_heterogeneity。本地完整文件清单与 UID 映射在 Git 忽略的 .local/dataset-index/；用 pathlib.Path 解析，Series 路径由 Manifest 查询。
- CMRL-11 索引事实：130,424 个 DICOM、171 个 Study、806 个 Series；MR 92,508、CT 21,637、PT 16,129、REG 87、RTSTRUCT 63。130,424 个 Header 均解析成功。此结果不表示像素、几何或 ROI 质控通过。
- CMRL-06 固定 IDC v25.0.0 对照：821 个 Series / 131,556 个实例；本地 15 个 Series 缺失，73 个 Series 合计短缺 1,132 个实例。逐对象位完整性仍未验证。
- CMRL-13 单对象 RTSTRUCT 下载试验通过来源、实例数量和 DICOM Header 标识核对；未验证位级完整性。文件保留在 .local/ccth-recovery-pilot/，没有合并进正式数据目录。

## 标注与科研边界

- CMRL-12 单例结果：PIXEL_QC=PASS；GEOMETRY_QC=FAIL、RTSTRUCT_ALIGNMENT_QC=FAIL、MASK_QC=FAIL；ROI_SEMANTIC_QC=PENDING。
- CMRL-12 的私有 MRI、Mask、QC JSON、图片和部分导入产物目前未找到。提交到 GitHub 的只有脱敏代码和报告；不把私有运行输出称为已备份、可恢复或重建。
- 尚无通过完整几何和语义验收的宫颈原发肿瘤三维 Mask。Clinical-to-DICOM 连接、真实治疗时点、结局定义仍未确认。因此监督式肿瘤分割、体积 Radiomics、纵向治疗分析和临床预测仍为 **NO-GO**。
- 用户已取消 FlexFair-F01 独立教学线；本地 FlexFair 原始数据仍保留。

## 私有资产位置

- 原始医学数据与临床工作簿：本地 data/，Git 忽略并保持原位。
- CMRL-11 完整 Manifest：.local/dataset-index/。
- CMRL-06 固定 IDC v25.0.0 索引/缺口记录：.local/private-evidence/cmrl-06-idc-v25/。
- CMRL-08 私有候选映射：.local/private-evidence/cmrl-08-crosswalk/。
- CMRL-13 下载试验对象：.local/ccth-recovery-pilot/。
- 本地恢复清单：.local/asset-inventory.json。它含本机路径和资产元数据，必须继续留在 Git 忽略目录。

## 下一步建议

先取得可追溯的 ROI 定义并确定一个 MR–RTSTRUCT 候选，再由用户亲自完成单例几何和 Mask 质控。此条件满足前，不进入三维肿瘤分割、体积 Radiomics 或临床结局建模。

完整任务提交与原始审计文件通过[历史归档索引](HISTORY_ARCHIVE.md)定位；当前最短入口是仓库 [README](../../README.md) 和 [CCTH 路径合同](../datasets/CCTH_DATASET_INDEX.md)。
