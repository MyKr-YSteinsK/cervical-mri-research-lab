# TASK_RESULT｜CMRL-03 / r1

## 任务状态

**Task / Revision / Status：** `CMRL-03 / r1 / PARTIAL`

公开来源、Collection 元数据和许可核验已完成；本机 TCIA/IDC API 连接不可用，无法完成单受试者 MR 与 RTSTRUCT 发现及文件级验证。

## 仓库与 Git 交付

- **Repo / Visibility：** `MyKr-YSteinsK/cervical-mri-research-lab` / private。
- **Branch：** `codex/r0-03-tcia-minimal-reference-audit`。
- **Parent SHA：** `81d6801cd926a279653e8d6a2eca87f88dc331e9`（CMRL-02 远端 HEAD）。
- **PR chain：** #1 `OPEN / Draft`, `main → codex/r0-00-data-access-audit`；#2 `OPEN / Draft`, `codex/r0-00-data-access-audit → codex/r0-01-flexfair-archive-audit`；#3 `OPEN / Draft`, `codex/r0-01-flexfair-archive-audit → codex/r0-02-site-provenance-and-plan-governance`。均未合并。
- **本任务 PR：** Git 交付完成后回填 URL、base/head 与状态；目标 base 为 `codex/r0-02-site-provenance-and-plan-governance`，保持 Draft，不合并。
- **Final local SHA / Remote SHA：** 由最终分支 HEAD 和 `git ls-remote` 实测值填写在最终交付回执；TASK_RESULT 随其自身提交，不硬编码自引用 Git SHA。
- **Working tree：** 最终检查后应 clean；详见最终交付回执。

## M1–M7

| Gate | 状态 | 证据 |
|---|---|---|
| M1 Git/Contract | `PASS` | 外部 Plan 读取成功；私有状态、PR 链、远端 SHA、忽略规则与空工作区已核验；从 PR #3 最新 HEAD 派生任务分支，没有创建 `plans/` |
| M2 Source | `PASS` | TCIA 官方页面 Version 2、DOI、聚合数量、CC BY 4.0 与引用要求；IDC 官方 Collection 与官方 API 文档；详见 [审计报告](CMRL-03-TCIA最小MR与RTSTRUCT准入审计.md) |
| M3 Discovery | `BLOCKED` | TCIA REST `getSeries` 超时；IDC REST v3 本机 TLS 握手失败；未取得受试者级结果 |
| M4 Bounded File Check | `NOT_RUN` | 身份/引用候选前置条件未满足；MR DICOM 0 个、RTSTRUCT 0 个，没有 Header 读取 |
| M5 Scientific Semantics | `NOT_RUN` | MR/T2WI、同人/同 Study/同 Frame、引用关系、ROI 类别和采集时点均 `UNKNOWN` |
| M6 Privacy | `PASS` | 未下载 DICOM；成果无逐例标识、UID、原始 Header、路径、像素、Contour、临床行值或凭据；提交前完成隐私检查 |
| M7 Git/Delivery | `PENDING` | Push、PR #4 和远端 SHA 核验后更新 |

## 来源与访问

- **TCIA：** `CC-Tumor-Heterogeneity`, Version 2 页面（更新于 2023-02-23），DOI `10.7937/ERZ5-QZ59`；发布统计 23 subjects、171 studies、821 series、131,556 images、28.39 GB；包含 MR、RTSTRUCT、REG、PT、CT；影像为 CC BY 4.0，需引用。
- **IDC：** 官方 Collection 页面确认 23 subjects、MR/RTSTRUCT 与 Clinical supporting data；官方 REST v3 文档公开只读查询路径。
- **调用时间：** 2026-10-16 UTC。
- **HTTP / 失败：** TCIA 本次 Python `urllib` `TimeoutError`，未收到 HTTP 状态、读到 0 bytes；IDC Python TLS `SSLEOFError`、curl HTTP 000/0 bytes；IDC 浏览器文档页 `ERR_CONNECTION_CLOSED`。另有一条 PowerShell 探索性命令包含 MR 与 RTSTRUCT 两条元数据请求，但逐请求状态与正文长度未能从工具捕获，作为未决记录，不被当作零结果证据。
- **单受试者链：** 是否存在可核验 MR/T2WI：`UNKNOWN`；是否有 RTSTRUCT：`UNKNOWN`；同受试者、同 Study、同 Frame of Reference、RTSTRUCT 引用 MR SOP/Series：均 `UNKNOWN`。

## 文件、预算与隐私

- 新增本地 MR DICOM：0；RTSTRUCT：0；下载字节：0。
- 单对象上限 30,000,000 bytes；累计正文上限 100,000,000 bytes。已捕获请求正文合计 0 bytes，但探索性 PowerShell 结果未被捕获，故累计**元数据响应**正文不能完全核算；未发出任何 DICOM 文件读取请求。
- 无文件 SHA、UID、原始路径、Header 值、患者键或实例清单可报告。RTSTRUCT ROI 类别、几何字段均未检查。
- Git 输出仅提交安全的 Collection 级聚合信息、连接状态和未知项。

## 交付物

- [CMRL-03 审计报告](CMRL-03-TCIA最小MR与RTSTRUCT准入审计.md)
- [脱敏聚合证据 JSON](../../evidence/r0/tcia_minimal_mr_rtstruct_audit.json)
- `docs/project/02-DATASET_EVIDENCE_REGISTER.md`：只补充 D03 当前查询阻塞事实。
- `docs/project/08-RESEARCH_STATE.md`：只补充 CMRL-03 的部分调查事实，保持 R0 未完成。

## Next Boundary / Research Status

本次没有形成可供用户本地读取的 MR/RTSTRUCT 教学样本。若之后在能连接官方端点的环境完成受试者级引用核验，再按原 r1 预算决定是否读取一个 RTSTRUCT 和少量被其引用的 MR 实例。当前项目仍为 `R0-DATA-ACCESS-AUDIT / NOT COMPLETE`；不代表 R1/R2/R3、分割、Radiomics 或疗效模型准入。
