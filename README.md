# Cervical MRI Research Lab

CMRL 是宫颈癌 MRI 研究仓库。当前仍处于 `R0-DATA-ACCESS-AUDIT`，**R0 尚未完成**。仓库整合只整理工程成果，不代表数据准入、临床标签、ROI 或实验已经通过验收。

## 从这里开始

1. 阅读[当前研究状态](docs/project/08-RESEARCH_STATE.md)和[数据证据登记](docs/project/02-DATASET_EVIDENCE_REGISTER.md)。
2. 需要定位 CCTH 文件时，使用[本地目录索引与路径合同](docs/datasets/CCTH_DATASET_INDEX.md)及忽略 Git 的 `.local/dataset-index/series.csv`、`files.csv`。
3. 查看[项目合同](docs/project/)中的 Brief、分阶段计划、辅导协议和 R0 Runbook。所有 MRI 处理、分割、Radiomics、训练和解释性核心由用户学习、编写、运行和审查。
4. 查找完整历史时，使用[归档索引](docs/project/HISTORY_ARCHIVE.md)。

## 当前数据与质控状态

- 本地 CCTH 索引记录 **130,424 个 DICOM 文件、171 个 Study、806 个实际 Series**。固定 IDC v25.0.0 对照为 821 个 Series、131,556 个实例；既有逐 Series 对账记录本地缺 15 个 Series、短缺 1,132 个实例。对象级位完整性仍未验证。
- CMRL-13 恢复试验下载了一个 RTSTRUCT 实例，保存在忽略目录 `.local/ccth-recovery-pilot/`，没有并入原始数据树。
- CMRL-12 的代码和脱敏报告已纳入历史。报告结论为 `PIXEL_QC=PASS`、`GEOMETRY_QC=FAIL`、`RTSTRUCT_ALIGNMENT_QC=FAIL`、`MASK_QC=FAIL`、`ROI_SEMANTIC_QC=PENDING`。其私有 MRI、Mask、QC JSON 和图片目前未找到。
- 目前没有通过几何与语义验收的宫颈原发肿瘤三维 Mask；患者连接、治疗时点和临床终点仍未核实。不得据此启动监督式肿瘤分割、体积 Radiomics 或疗效预测。
- 用户已取消独立的 FlexFair-F01 教学实验线。其原始数据仍留在本地 `data/raw/flexfair/`。

## 本地路径

默认数据目录为 `data/raw/tcia/ccth_idc_v25_full/cc_tumor_heterogeneity`。Python 程序应使用 `pathlib.Path` 解析路径，并可用环境变量 `CMRL_CCTH_ROOT` 覆盖；具体 Series 目录从私有 Manifest 查询，不通过拼接 DICOM UID 猜测路径。完整示例见[路径合同](docs/datasets/CCTH_DATASET_INDEX.md)。

原始影像和临床文件只在本地 `data/`，UID、精确文件映射和私有审计证据只在忽略 Git 的 `.local/`。提交前检查暂存清单和公开产物，禁止提交患者级数据、原始 DICOM、凭证或私有 Manifest。

## 唯一建议的下一步

先取得可追溯的 ROI 定义并选定一个候选 MRI–RTSTRUCT 组合，再由用户亲自完成单例几何与 Mask 质控；未通过前不进入三维肿瘤分割或 Radiomics。
