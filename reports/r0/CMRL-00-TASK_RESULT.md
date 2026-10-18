# TASK_RESULT｜CMRL-00 / r2

- **Status:** COMPLETE（调查与证据交付完成；数据集没有通过影像/Mask 文件级准入）
- **Plan:** `plans/CMRL-00-科研仓库初始化与候选数据准入审计.md` r2
- **Branch:** `codex/r0-00-data-access-audit`
- **G1 Repo:** PASS — private GitHub 仓库已创建；远端 `main`、README、AGENTS、八份 seed 文档与 Plan 已核；证据和 SHA 详见主审计报告及下方 Git 回执。
- **G2 Contract:** PASS — 仅按任务调整 01/04/08 的权限文字，保留原始 seed 哈希与差异；未宣布 R0 完成。证据：`docs/project/SEED_SHA256.md`、`evidence/r0/seed-permission-changes.patch`。
- **G3 D01:** PASS（调查交付）— Figshare 28639598 返回 200、超预算包未下载；28636133 返回 404；README 链接/ID 冲突与未验证的患者映射均已报告。影像和 Mask 文件级验收 NOT RUN。
- **G4 D02:** PASS — 论文、访问要求、格式冲突和未申请/未下载事实已记录；未代发申请或获取凭据。
- **G5 D03:** PASS（调查交付）— TCIA/IDC 元数据已核；临床 XLSX 成功下载并只读聚合 profile；series API 超时、影像/RTSTRUCT 未检查均有证据。影像门槛 NOT RUN。
- **G6 Privacy:** PASS — 原始 XLSX 位于 Git 忽略的本地 `data/clinical/`；暂存文件清单、扩展名、常见凭据模式和 `git diff --check` 均已检查，没有行级值、病例值、影像、Mask、RTSTRUCT 或凭据进入提交。
- **Git / Remote:** private repo `https://github.com/MyKr-YSteinsK/cervical-mri-research-lab`；初始化 commit `a5eed164319c6ac53caca0643f3a733a1518bf25`；`main` permission commit `9ab1f4fb07154a0392f73ebfcfa3c6ae53db460f`；audit branch `codex/r0-00-data-access-audit` 已推送；draft PR [#1](https://github.com/MyKr-YSteinsK/cervical-mri-research-lab/pull/1) 已创建，未合并。最终 audit HEAD SHA 在主对话回传，避免本文件自引用。
- **G7 Delivery:** PASS — 审计报告、TASK_RESULT、公开元数据、脱敏 clinical profile 与复现脚本已提交并推送；远端分支 SHA 已实查；draft PR 已创建且未合并。
- **Artifacts:** `reports/r0/CMRL-00-三候选数据准入审计.md`；`evidence/r0/`；`scripts/r0/`；Notebook runner 位于 `notebooks/r0/`。本地临床 XLSX 未入 Git。
- **Next Boundary:** 请 Main 审查调查证据并决定候选优先级；如要推进影像检查，需先取得一个合法的小型 Image+Mask/RTSTRUCT 配对样本，再单独确认是否由用户亲自执行 MRI 处理。不得将本任务视作 R0 阶段验收或进入 R1。
