# CURRENT RESEARCH STATE｜新项目独立初始状态

更新时间：2026-10-16｜状态来源：原课程对话用户明确的迁移意图、六篇 PDF、公开网页/仓库审计，以及 CMRL-01/02 的 FlexFair 发布包审计；**无患者身份映射、临床行值或模型运行验收**。

## 唯一当前行动

`R0-DATA-ACCESS-AUDIT` 仍是唯一活动阶段，**R0 NOT COMPLETE**。CMRL-00、CMRL-01、CMRL-02 已完成各自外部 Plan 范围内的阶段性来源/结构调查；CMRL-03 来源与许可核验完成，但受试者级查询因当前执行环境连接失败而为 `PARTIAL`。这些任务均不代表 Main 接受数据集或批准实验。FlexFair 文件级事实见 [CMRL-01 报告](../../reports/r0/CMRL-01-FlexFair文件级准入审计.md) 与 [CMRL-02 分组/身份复核](../../reports/r0/CMRL-02-FlexFair分组与身份线索复核.md)；TCIA 的 Collection 级来源与许可已复核，但当前执行环境无法取得受试者级元数据，尚无 MRI/RTSTRUCT 配对或文件检查证据；CCMD 访问条件仍未解决。见 [CMRL-03 审计报告](../../reports/r0/CMRL-03-TCIA最小MR与RTSTRUCT准入审计.md)。

## 用户已确认

以**宫颈癌 MRI** 为研究主线；与六篇论文的影像处理/影像组学/深度表征保持联系；允许先完成分割与前期影像研究，不强制当下患者级疗效二分类；未来追求真实、有根据的模型改进或新方法。采用 GPT 教学＋用户亲自编写和运行代码，常规不使用 Codex。未来工作独立迁移新 ChatGPT Project。

**专项任务权限**：CMRL-00 的授权限于其自身 Plan。CMRL-01 另由用户启动的 Plan 授权公开 ZIP 的有限下载、安全枚举及最小样本格式检查；CMRL-02 授权对同一已核验 ZIP 与原作者公开代码进行分组、身份线索、配对和精确像素重复审计，并治理仓库 Plan 存放规则。这些授权均不扩大未来 Codex 权限。MRI 空间质控、分割、Radiomics、训练及解释性核心代码仍由用户亲自学习、编写和运行。

## 不要代替用户确认的建议

- 当前首选**审计** FlexFair 678 例四中心数据、CCMD 151 例和 TCIA 23 例，并非已选定唯一实验数据集。
- R3 2D/3D 分割、R4 稳健 Radiomics、R5 Habitat/深度表征、R6 跨中心、R7 应答等是分层候选，不是全部承诺。
- 项目名称、数据下载、计算环境、代码托管位置、研究成果公开范围还未最终确定。

## 已核实的正面证据

- 六篇用户提供的原 PDF 在此次迁移制品中存在并进行基本 PDF 打开/页数/校验。
- FlexFair (Nature Communications 2025) 作者报告 678 患者、四中心 T2WI/ROI。CMRL-01 实测的 Figshare ZIP 有 6732 张 PNG，其中 3366 个影像侧文件和 3366 个 Mask 命名候选形成唯一文件名配对；CMRL-02 将全部 3366 对按作者 `_label.png` 规则与 CMRL-01 规范化规则独立交叉核对，结果一致。原作者代码预期的 `Private/train|test/<四组>` 路径在 ZIP 中没有对应文件；ZIP 的 train/test 目录各有 2420/946 个影像侧 PNG 及等量 Mask。对 3366 张影像解码像素比较发现 9 条重复额外记录，其中一组完全相同图像跨 train/test 各出现一次；文件名/目录仍未建立患者或临床中心键，不能证明患者级无泄漏。2D 分割仍仅 `CONDITIONAL`，3D 分割/体积级 Radiomics/Cross-site 当前 `NO-GO`，2D Radiomics 未评估。
- CCMD (2025) 论文和仓库描述 151 人 T2WI/ROI，下载申请受限；**尚未获密码**。
- TCIA 官方页面发布 CC-Tumor-Heterogeneity（23 subjects，含 MR 与 RTSTRUCT；DOI `10.7937/ERZ5-QZ59`，影像许可 CC BY 4.0）。CMRL-00 已下载并汇总审计公开 XLSX：23 个不同的候选病例键、28 条非空行；行数与受试者数的关系仍需解释。CMRL-03 对官方来源、许可与 API 文档完成复核，但 TCIA series 查询超时、IDC REST TLS/浏览器连接失败；没有核验 MRI/RTSTRUCT 配对，没有下载 DICOM，也没有验证临床结局定义或接纳训练标签。
- P03 有原作者公开研究代码但患者数据未公开。

## 最大阻塞/风险

1. D01 文件级格式和候选 Mask 配对已核；患者/中心键、患者级拆分与 678 人对 3366 个影像文件的对应仍未知。
2. D02 CCMD 授权与格式冲突，仓库公开代码缺失。
3. 公开资源是否含可信疗效标签尚未得到证据，因此不可现在启动临床应答预测。
4. OS/GPU/VRAM/磁盘与用户 Python 运行环境未知，不应冻结 CUDA 依赖。

## 学习与执行证据

已讲过 MRI 基础/机器学习/统计概念，但尚未通过当前项目完成 Python/MRI/模型的真实代码运行、数据审计、模型训练与评价；**所有实验验收均为 NOT STARTED**。没有已经建立的 Python 环境、仓库或数据下载可凭此文件宣称成功。

## 与原课程关系

原课程第一轮六篇技术导读与横向阶段回顾已覆盖，第二轮英文原文精读暂停。原课程的有效 Checkpoint 独立保留；新项目不修改、迁移或覆盖它。旧课程能力掌握未正式验收。

## 下一次 Main 必做

读取 `01`–`07`、本文件及 [CMRL-01 报告](../../reports/r0/CMRL-01-FlexFair文件级准入审计.md)、[CMRL-02 报告](../../reports/r0/CMRL-02-FlexFair分组与身份线索复核.md) 和 [CMRL-03 报告](../../reports/r0/CMRL-03-TCIA最小MR与RTSTRUCT准入审计.md)，审查 FlexFair 的二维条件性准入、分组/身份缺口与跨 split 完全重复影像，并将 TCIA 当前仅到 Collection 元数据、单病例查询阻塞、无文件级证据纳入 R0 决策。再决定是否让用户亲自进行 PNG/Mask 语义检查，以及后续如何处理网络/访问环境和 split 泄漏风险。不要据此推进 3D/Radiomics/Cross-site 或模型实验；R0 仍需 Main 正式审查和决定。
