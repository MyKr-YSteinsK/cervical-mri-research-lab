# CURRENT RESEARCH STATE｜新项目独立初始状态

更新时间：2026-10-17｜状态来源：原课程对话用户明确的迁移意图、六篇 PDF、公开网页/仓库审计、CMRL-01/02 的 FlexFair 发布包审计，以及 CMRL-04/05 对用户本地 TCIA DICOM 的脱敏文件级审计；**无逐病例身份映射、临床行值或模型运行验收**。

## 唯一当前行动

`R0-DATA-ACCESS-AUDIT` 仍是唯一活动阶段，**R0 NOT COMPLETE**。CMRL-00、CMRL-01、CMRL-02 已完成各自外部 Plan 范围内的阶段性来源/结构调查；CMRL-03 完成 Collection 来源与许可核验，但当时的受试者级查询被网络连接阻断；CMRL-04 后续完成用户本地人工下载子集的文件级 Header 与 RTSTRUCT 引用审计；CMRL-05 完成 IDC Release 25.0 全量候选目录的只读 Header、RTSTRUCT 引用和下载证据分层审计。上述任务均不代表 Main 已接受数据集或批准实验。FlexFair 文件级事实见 [CMRL-01 报告](../../reports/r0/CMRL-01-FlexFair文件级准入审计.md) 与 [CMRL-02 分组/身份复核](../../reports/r0/CMRL-02-FlexFair分组与身份线索复核.md)；TCIA 本地子集确认 MR 与 RTSTRUCT 的直接引用链，但原发宫颈肿瘤 ROI 语义及本地包的 Collection 归属仍未确认；CCMD 访问条件仍未解决。见 [CMRL-03 报告](../../reports/r0/CMRL-03-TCIA最小MR与RTSTRUCT准入审计.md) 和 [CMRL-04 报告](../../reports/r0/CMRL-04-TCIA本地DICOM文件级准入审计.md)。

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
- TCIA 官方页面发布 CC-Tumor-Heterogeneity（23 subjects，含 MR 与 RTSTRUCT；DOI `10.7937/ERZ5-QZ59`，影像许可 CC BY 4.0）。CMRL-00 已下载并汇总审计公开 XLSX：23 个不同的候选病例键、28 条非空行；行数与受试者数的关系仍需解释。CMRL-03 对官方来源、许可与 API 文档完成复核，但当时的 TCIA series 查询超时、IDC REST TLS/浏览器连接失败。CMRL-04/r2 复核用户报告从 IDC 手动取得的本地子集：5,959 个 DICOM 文件、4,334 MR、3 RTSTRUCT；129 条按 RTSTRUCT 内去重汇总的 SOP 引用记录全部命中本地，且指向 T2 文本候选 Series。r1 对 ROI 类型的读取位置错误；r2 正确关联 6 个 Observation 与 6 个 ROI，类型标签均存在但为空，名称启发式单独计数为 `OTHER` 6。6 个 ROIContour 条目关联唯一；108 个声明为 `CLOSED_PLANAR` 的轮廓点数和坐标元素数量/有限性均通过元数据检查，并有 ContourImageSequence 引用。未验证共面性、图像空间对齐、目标结构含义或可用 Mask；本地文件与 Collection 的归属没有 manifest 独立证明。没有验证临床结局定义或接纳训练标签。
- **CMRL-05 全量候选目录审计**：本机 manifest 结构与上传副本摘要匹配，821 条 source-prefix 命令有效；本地目录有 130,424 个 DICOM 候选文件、130,424/130,424 标准 Header 解析成功，元数据快照前后未变化。聚合为 23 个 PatientID 键、171 个 Study、806 个 Series；63 个 RTSTRUCT 的直接引用链与 ROI/Contour 元数据结果见 [CMRL-05 报告](../../reports/r0/CMRL-05-TCIA全量DICOM准入审计.md)。当时 source-prefix→Series 映射和对象级期望清单尚未验证；这些缺口由 CMRL-06 后续补证。
- **CMRL-06 IDC v25 映射与完整性补证**：固定 IDC `idc-index-data` Release 25.0.0 索引及集合 crosswalk 通过官方 checksum 与内嵌版本核验；821/821 manifest 前缀一对一映射到官方 Series。最小 Header 对照确认本地 806/821 Series 命中、15 个缺失，73 个 Series 实例数短缺，共短缺 1,132 个实例，超额为 0。两次匿名 S3 LIST 均未取得响应，逐对象完整性仍未验证；统计差异不证明像素/内容哈希一致。61 条未命中 SOP 引用继续保留 `UNKNOWN`，未生成逐 Series UID 私有 gap list。详情见 [CMRL-06 报告](../../reports/r0/CMRL-06-IDC-v25逐Series及对象完整性补证.md)。**Main 尚未接受证据；R0 NOT COMPLETE。**
- P03 有原作者公开研究代码但患者数据未公开。

## 最大阻塞/风险

1. D01 文件级格式和候选 Mask 配对已核；患者/中心键、患者级拆分与 678 人对 3366 个影像文件的对应仍未知。
2. D02 CCMD 授权与格式冲突，仓库公开代码缺失。
3. D03 本地 MR–RTSTRUCT 直接引用及轮廓元数据结构已核实，但 ROI 类型值为空，名称启发式和 `CLOSED_PLANAR` 点列表不足以认定原发宫颈肿瘤 Mask；图像空间关系与来源 Collection 归属仍需确认，不可据此启动分割或 Radiomics。
4. 公开资源是否含可信疗效标签尚未得到证据，因此不可现在启动临床应答预测。
5. OS/GPU/VRAM/磁盘与用户 Python 运行环境未知，不应冻结 CUDA 依赖。
6. CMRL-06 已证明 821 条 manifest 前缀与 v25.0.0 官方 Series 一对一映射，并发现本地 15 个缺失 Series、1,132 个实例短缺；匿名 S3 LIST 不可用，逐对象清单/大小仍未验证，61 条 SOP 引用仍未知。ROI 临床语义、像素空间一致性与临床标签也未解决。

## 学习与执行证据

已讲过 MRI 基础/机器学习/统计概念；CMRL-04/05 有限授权审计使用了任务专用的忽略目录 Python/pydicom 环境并完成 DICOM 元数据审计，但这不构成用户 Lab 环境验收。尚未完成 MRI 处理/模型代码运行、模型训练与评价；**所有科学实验验收均为 NOT STARTED**。没有已经建立并验收的项目 Python 环境或科研核心流程可凭此文件宣称成功。

## 与原课程关系

原课程第一轮六篇技术导读与横向阶段回顾已覆盖，第二轮英文原文精读暂停。原课程的有效 Checkpoint 独立保留；新项目不修改、迁移或覆盖它。旧课程能力掌握未正式验收。

## 下一次 Main 必做

读取 `01`–`07`、本文件及 [CMRL-01 报告](../../reports/r0/CMRL-01-FlexFair文件级准入审计.md)、[CMRL-02 报告](../../reports/r0/CMRL-02-FlexFair分组与身份线索复核.md)、[CMRL-03 报告](../../reports/r0/CMRL-03-TCIA最小MR与RTSTRUCT准入审计.md)、[CMRL-04 报告](../../reports/r0/CMRL-04-TCIA本地DICOM文件级准入审计.md) 和 [CMRL-05 报告](../../reports/r0/CMRL-05-TCIA全量DICOM准入审计.md)、[CMRL-06 报告](../../reports/r0/CMRL-06-IDC-v25逐Series及对象完整性补证.md) 和 [CMRL-07 报告](../../reports/r0/CMRL-07-TCIA原始研究ROI时点与临床字段核验.md)，将 FlexFair 的二维条件性准入、分组/身份缺口与跨 split 完全重复影像，以及 TCIA 本地引用链、下载完整性缺口和 ROI 语义限制纳入 R0 总体决策。再决定是否由用户亲自开展单序列 DICOM 读取/空间质控教学、如何确认 ROI 语义与本地文件来源，以及后续数据使用范围。不要据此推进 3D 分割、Radiomics、Cross-site 或模型实验；R0 仍需 Main 正式审查和决定。


## CMRL-06/r2｜IDC v25 按模态缺口补证

2026-10-17 的 r2 补证沿用固定 Release 25.0.0 索引与 manifest 映射，一次最小 Header 扫描后按官方 Modality 对账：821 个预期 Series 中本地命中 806 个，15 个完全缺失；73 个 Series 有实例短缺（58 个部分短缺、15 个完全缺失），合计短缺 1,132 个实例，数量相等 748 个，超额 0。MR 523 个 Series 均命中，但 55 个 MR Series 少 800 个实例；数量相等不能代表影像体完整。RTSTRUCT 有 5 个 Series 缺失；CMRL-05 的 61 条未命中 SOP 引用仍为 `UNKNOWN`，没有推断两者对应关系。另在本机忽略目录生成 73 行私有 Series 差异表，未公开 UID 或 source-prefix。r1 两次 S3 LIST 仍 `REMOTE_LIST_UNAVAILABLE`，r2 网络请求为 0；对象级库存及位级完整性仍未验证。此段更新 r1 的阶段性记录，不表示 Main 已接受证据、R0 已完成或数据已批准进入监督训练。详见 [`CMRL-06 r2 报告`](../../reports/r0/CMRL-06-IDC-v25逐Series及对象完整性补证.md)。

## CMRL-07｜TCIA ROI、时点与临床字段（2026-10-17）

- **任务：** Plan-07 r1 证据审计 COMPLETE；**R0 NOT COMPLETE**。Main 未接受数据或批准实验。
- **临床文件：** 本机只读副本与当前 TCIA 官方 XLSX 端点的大小及 SHA-256 匹配，clinical Version 2；28 非空数据行、9 个字段、候选键 23 个互异非空值/5 行缺键。记录粒度及患者身份未证实；没有 event/time-origin/censoring codebook。
- **ROI：** 论文作者报告参考矢状 T2 上的 tumor 和 uterus 勾画，uterus 辅助配准；未找到发布版 DICOM 逐 ROI Number/name 映射。ROI_SEMANTIC_UNRESOLVED，不能作为肿瘤分割监督真值。
- **身份与时点：** Clinical 候选键→DICOM PatientID 为 JOIN_UNVERIFIED；文献计划时点 SOURCE_DEFINED，本地逐患者时点 UNASSIGNED。21 人论文与 23 人 Collection 的关系未核实。
- **IDC v25.0.0：** 沿用 CMRL-06/r2，官方 821 Series 映射已核；本地 15 Series 缺失，73 Series 实例短缺 1,132 个。对象级完整性仍未核实。
- **准入：** 单例 MRI 空间教学 CONDITIONAL；3D 肿瘤分割、体积 Radiomics、跨时点分析、应答/DFS/OS NO-GO。
- **报告：** [CMRL-07 报告](../../reports/r0/CMRL-07-TCIA原始研究ROI时点与临床字段核验.md)、[脱敏证据 profile](../../evidence/r0/tcia_source_roi_clinical_profile.json)、[TASK_RESULT](../../reports/r0/CMRL-07-TASK_RESULT.md)。Main 须决定是否继续官方文档/作者确认或仅转入用户自主持的单例空间 QC 教学。
