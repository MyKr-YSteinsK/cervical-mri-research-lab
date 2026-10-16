# TASK_RESULT｜CMRL-02 / r1

- **Status:** `COMPLETE`（分组/身份/重复影像调查与 Plan 目录治理交付完成；**不代表 R0 完成、数据 GO 或 Main 已验收**）
- **日期：** 2026-10-16 UTC
- **仓库：** `MyKr-YSteinsK/cervical-mri-research-lab`（Private）
- **Base:** `codex/r0-01-flexfair-archive-audit` @ `85750090a9828ce1a81e2c8cc59bca75093ad197`
- **Branch:** `codex/r0-02-site-provenance-and-plan-governance`
- **Remote:** `origin`；不推送 `main`，不合并。

## A1–A7 验收

| Gate | Status | 结果 |
|---|---|---|
| A1 Git/Plan 目录 | **PASS** | 复核工作区和 Git index 后保留用户已删除的 CMRL-00/01 两份 Plan；提交时从当前树停止跟踪，不重建 `plans/`。`AGENTS.md`、README、`04` 和 `.gitignore` 统一为仓库外 Plan 规则；历史不改写。 |
| A2 作者代码 | **PASS** | 只读核对 `MaksimXing/FlexFair` 的 `main` commit `f7da0fc0a9a4ad7c96f2c7b48699fc8cc151e320`；四个 train loader、`FedTestData.py` 与子项目 README 的路径和命名约定见主报告。 |
| A3 ZIP 目录 | **PASS** | 本地归档 SHA-256/官方 MD5 匹配，6732 个 PNG 的全包 CRC 通过。归档有 train/test 文件夹，但没有作者要求的 `Private/train|test/<group>` 结构或四组目录；聚合计数见主报告及 JSON。 |
| A4 Mask 配对 | **PASS** | 作者 `_label.png` 同目录规则和 CMRL-01 规范化规则均得到 3366 对；交集 3366，双方独有 0，无歧义或孤立候选。仅为命名关系，不验收 Mask 语义/空间。 |
| A5 身份/去重 | **PASS** | 患者/中心键与患者级拆分证据为 `UNKNOWN`。3366 张影像侧 PNG 全部解码；发现 9 条精确像素重复额外记录，其中一组跨 train/test 各出现一次。逐例路径/哈希未输出。 |
| A6 隐私/科研边界 | **PASS** | 无新数据下载、模型训练、核心代码教学替代、病例清单/逐例哈希/像素或凭据入库；R0 与各准入状态未越级。 |
| A7 交付 | **PASS** | 任务分支已推送，远端 HEAD 与最终本地提交核对；Draft PR #3 以 `codex/r0-01-flexfair-archive-audit` 为 base。PR #1/#2 在最终复核时状态、依赖关系见对话交付回执；均不由本任务合并。 |

## 关键结果

- **作者版本/规则：** `main` HEAD `f7da0fc0a9a4ad7c96f2c7b48699fc8cc151e320`。Train loader 期待 `Private/train/<group>/`，测试 loader 期待 `Private/test/<group>/`；组名为 `zhongda`、`shengfuyou`、`zhongzhong`、`new_zhongyi`。排除名称含字面 `label` 的文件，并读取同目录 `name[:-4] + '_label.png'`。代码不解析 patient ID 或 site ID。
- **ZIP：** 348,731,016 bytes；MD5 `303ae54703fdccc63302cb755aed792a`、SHA-256 `4efdfa6b6dbf4174a1b7ce2b0eb8878e739f0365829a89d57fdf5223c82817ec` 与前次核验相同；6732 PNG，CRC 完整复核通过。Train 有 2420 image-side 与 2420 mask-name candidates；test 有 946 与 946。作者四组目录和严格 loader 路径命中数均为 0。
- **身份与重复：** 3357 个不同 RGBA 像素矩阵 / 3366 张影像，重复额外记录 9；其中 1 个矩阵出现在两个 split，各一条，另 8 条额外记录在各自同一 split 内。不能据此推定患者关系或否定不同切片泄漏。
- **科研准入：** 2D segmentation `CONDITIONAL`；3D segmentation `NO-GO`；volumetric Radiomics `NO-GO`，2D Radiomics 未评估；Cross-site/公平性与 patient-wise evaluation `NO-GO`。R0 `NOT COMPLETE`。

## Plan Directory

用户已手动删除仓库根 `plans/`，本任务未恢复。Git 当前树不再跟踪旧 Plan；新增 `/plans/` 忽略规则。根 `AGENTS.md`、README 与 `docs/project/04` 已规定 Plan 仅由用户在仓库外管理并以 Markdown 附件/指定路径提供，命名 `CMRL-Plan-NN-中文标题.md`；任务及报告身份使用 `CMRL-NN`。Plan 缺失时请用户重传，不重建、不复制。旧提交仍保留历史 Plan 内容。未读取或修改外部 Plan 存储目录。

## Artifacts / Unresolved

- [`CMRL-02-FlexFair分组与身份线索复核.md`](CMRL-02-FlexFair分组与身份线索复核.md)
- [`flexfair_site_mapping_audit.json`](../../evidence/r0/flexfair_site_mapping_audit.json)
- [`audit_flexfair_site_structure.py`](../../scripts/r0/audit_flexfair_site_structure.py)
- 治理更新：根 `AGENTS.md`、`README.md`、`.gitignore`、`docs/project/04-GPT_TUTORING_AND_EXPERIMENT_PROTOCOL.md`、`docs/project/08-RESEARCH_STATE.md`；Git 当前树移除两份旧 Plan。
- **Unresolved:** 四组目录与实际临床中心对应、患者 ID、患者级拆分、跨 split 重复处置、Mask 临床语义和医学空间配准。
- **Next Boundary:** 交 Main 审查；不自行验收 R0、不开始模型或分割教学核心实现。
