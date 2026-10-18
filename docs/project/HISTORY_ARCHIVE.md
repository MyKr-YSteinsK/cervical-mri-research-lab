# CMRL 历史归档索引

仓库 main 保留当前合同、研究状态、CCTH 路径索引、CMRL-12 质控代码/报告和 CMRL-13 下载试验回执。为精简日常文件树，较早的一次性审计报告、TASK_RESULT、聚合 profile、脚本和测试从当前树退役；它们的完整提交仍通过以下远端 Tag 可恢复，提交历史未改写。

## 固定 GitHub 归档 Tag

| 覆盖范围 | Tag | GitHub |
|---|---|---|
| CMRL-00～11 与 CMRL-13 的整条原始提交链 | archive/cmrl-00-11-13-20261018 | [查看归档树](https://github.com/MyKr-YSteinsK/cervical-mri-research-lab/tree/archive/cmrl-00-11-13-20261018) |
| 独立的 CMRL-12 提交、脚本与脱敏报告 | archive/cmrl-12-20261018 | [查看 CMRL-12 归档树](https://github.com/MyKr-YSteinsK/cervical-mri-research-lab/tree/archive/cmrl-12-20261018) |

两个 Tag 已推送并通过远端引用核验。CMRL-12 的私有 MRI、Mask、QC JSON 和图片不在 Git Tag 中；当前没有找到这些私有输出。

## 按任务查找

- **CMRL-00～02：** 候选数据准入、FlexFair 文件审计、分组与来源线索。CMRL-02 起也包含已取消的 FlexFair-F01 教学线准备记录。
- **CMRL-03～05：** TCIA 可访问性、人工 DICOM 子集及全量候选 DICOM 文件审计。
- **CMRL-06～10：** 固定 IDC v25.0.0 对账、ROI/临床字段、私有候选连接和替代标注来源审计。
- **CMRL-11：** 本地完整目录索引与路径合同；当前版本保留在 docs/datasets/CCTH_DATASET_INDEX.md，详细回执在归档 Tag。
- **CMRL-12：** 单例像素/几何/Mask 质控代码和报告；其科研失败状态保留在当前 reports/r0/。
- **CMRL-13：** 一个缺失 RTSTRUCT Series 的小规模恢复试验；当前 TASK_RESULT 保留在 reports/r0/，原始下载对象仅在本地忽略目录。

## 本地恢复方法

从仓库根目录运行 git fetch origin --tags 获取归档引用。随后可运行 git show archive/cmrl-00-11-13-20261018:reports/r0/CMRL-06-TASK_RESULT.md 查阅 CMRL-06 回执，或运行 git show archive/cmrl-12-20261018:scripts/r0/qc_mri_rtstruct_singleton.py 查阅 CMRL-12 脚本。

需要检查完整历史树时，可运行 git switch --detach <Tag>；返回日常开发时切回 main。不要重建或提交任何外部 Plan 文件。
