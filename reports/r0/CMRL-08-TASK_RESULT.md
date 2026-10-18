# CMRL-08 TASK_RESULT

- **Plan / revision:** `CMRL-Plan-08-TCIA私有患者连接与MR-RTSTRUCT候选预筛` r1（外部文件，未复制入仓库）。
- **任务状态：** `COMPLETE`，仅表示 Plan 授权的离线 Clinical/DICOM 元数据审计、私有索引、合成测试和脱敏交付完成；**`R0 NOT COMPLETE`**，不代表数据集准入或科研阶段推进。

## G1–G7 实际状态

| Gate | 状态 | 实际结果 |
|---|---|---|
| G1 Git、来源与只读边界 | PASS | 启动时 PR #8 为 Open/Draft、未合并，head `codex/r0-07-tcia-roi-clinical-evidence`=`768333dba3aa17da957861c7826eef83b18d7150`，base `codex/r0-06-idc-v25-integrity`。本分支由该精确 HEAD 派生。原始数据只读；数据源网络请求 0；Plan 留在仓库外。PR #9 按要求创建为 Open/Draft，base 为 `codex/r0-07-tcia-roi-clinical-evidence`，未合并、未转 Ready。|
| G2 Clinical 五行结构 | PASS | 复用与 CMRL-07 一致的 V2 工作簿：14,233 bytes，SHA-256 `a59d29c86bb45bca98649d1eb8c7a533558fd1cf7b6beb35f5175ea47a04d1c9`。1 sheet、9 个命名字段、28 个非空数据行、23 个键控行；另有 5 行仅一个非空单元格。五行同属一个非键字段类别、连续位于表尾且样式不同；未见公式、批注、合并区域交叉或内部解释标记。只能定为 `OBSERVED_LAYOUT`；角色与记录粒度 `UNKNOWN`，未称作注释或患者。终点 codebook 仍 `ENDPOINT_CODEBOOK_UNVERIFIED`。|
| G3 患者键技术连接 | PASS（研究语义未确认） | Clinical 候选键与 DICOM `PatientID` 按原始字符串及类型做精确比较；临床键 23 个、DICOM PatientID 23 个。匹配/未匹配/歧义精确子类保存在受控本机私有审计文件中；公开结果按 `<5` 小单元格及补数抑制，故不披露这些子类的具体数值。总量相等不构成身份关系证据。状态 `JOIN_UNVERIFIED`；`SOURCE_SEMANTICS_CONFIRMED=false`、`CLINICAL_IMAGE_JOIN_AUTHORIZED=false`，无 response/DFS/OS 标签。|
| G4 固定索引、Header 与引用链 | PASS | 使用 CMRL-06/r2 固定 IDC Release `25.0.0`、index version `25.0.0-0-gdbf7fd0`。IDC 索引及 collections 索引 SHA-256 分别为 `450598d6493d800334a8e1ece1fda4a5ec04ca1bd2f73309058f0531f8155572`、`97e5ac3bba296cb3f4e9d87545231275aad66fc89ba07262b7914e72e857489c`。官方 821 个 Series / 131,556 个实例；本地 806 Series、15 缺失，748 个 Series 计数相等，73 个短缺 Series 共少 1,132 个实例，与 CMRL-06/r2 对账一致。一次 Header 扫描解析 130,424/130,424 个文件，错误 0；扫描 253.42 秒、同轮总审计 254.791 秒；前后文件元数据 snapshot 相同。63/63 个 RTSTRUCT 完成允许范围内的引用读取；1,934 个唯一直接 SOP 引用中，1,873 个唯一命中、61 个未命中、歧义 0，与 CMRL-05 一致。ContourData 数值读取 0 bytes，跳过 9,595,982 bytes；未读取 PixelData。形成 56 个 MR Series–RTSTRUCT Series 组合，**不是患者数**。受控本机候选定位索引已生成，至多 3 组；具体小计依披露规则不公开。|
| G5 任务准入矩阵 | PASS（下游门槛保留） | 单例 MRI 像素/空间 QC 为 `CANDIDATE`，尚未进行，必须由用户亲自读取像素并验收空间/叠加。三维肿瘤分割与体积 Radiomics/Habitat 为 `NO-GO`（`ROI_SEMANTIC_UNRESOLVED`、`PIXEL_SPATIAL_NOT_RUN`）；治疗中纵向变化为 `NO-GO`（`TIMEPOINT_UNASSIGNED`、`GROUPING_UNVERIFIED`）；应答/复发/DFS/OS 为 `NO-GO`（`JOIN_UNVERIFIED`、`ENDPOINT_CODEBOOK_UNVERIFIED`，事件与删失定义未核实）。T2 只用 SeriesDescription/ProtocolName/SequenceName 文本启发式，标记 `HEURISTIC_ONLY`，不代表 T2 信号、矢状位或三维可用性。未建训练/验证/测试分组。|
| G6 测试、安全与可追溯 | PASS | 真实运行：Python 3.14.6、pydicom 3.0.2、DuckDB 1.5.6；Clinical 读取：Python 3.12.14、openpyxl 3.1.5。全合成测试 9/9 通过，重复运行 2 次；未用真实病例测试代替合成测试。公开 profile/报告/项目更新的定向隐私扫描：未命中实际 Clinical 候选键、5 个单格文本、PatientID、Study/Series/SOP UID、私有文件路径及 DICOM 私有描述字段；未输出这些原值。`.local/cmrl-08` 写入前后检查均被 Git 忽略；ACL 继承保护开启、3 条显式规则。提交前 `git diff --cached --check` 通过，暂存文件清单无 Plan、原始数据或私有映射。|
| G7 Git 交付 | PASS | 首批审计提交 `4495ff2902067ad17c7482942b8bb736f0b4834e` 已推送至 `codex/r0-08-tcia-private-crosswalk-screen`。PR #9：Open/Draft，base `codex/r0-07-tcia-roi-clinical-evidence`，未合并、未转 Ready。此 TASK_RESULT 作为 PR #9 后续交付提交；分支最终 HEAD 与 clean 工作树在该提交后核验，最终 HEAD 也由任务回传给出。无 Plan、病例级记录或私有索引进入 Git。|

## 文件与证据

- 报告：[`CMRL-08-TCIA私有连接与候选预筛报告.md`](CMRL-08-TCIA私有连接与候选预筛报告.md)
- 脱敏聚合：[`tcia_private_crosswalk_screen_profile.json`](../../evidence/r0/tcia_private_crosswalk_screen_profile.json)
- 只读审计脚本：[`audit_tcia_private_crosswalk_screen.py`](../../scripts/r0/audit_tcia_private_crosswalk_screen.py)
- 全合成测试：[`test_tcia_private_crosswalk_screen.py`](../../tests/test_tcia_private_crosswalk_screen.py)
- 状态增量：`docs/project/02-DATASET_EVIDENCE_REGISTER.md`、`docs/project/07-SOURCES_AND_OPEN_QUESTIONS.md`、`docs/project/08-RESEARCH_STATE.md`
- 本机私有 join 与候选定位索引均已生成并经忽略/访问边界检查；未提交，也未将其中的值、UID 或路径复制进本文件。

## 未完成与结论边界

- `JOIN_UNVERIFIED`：公开/作者身份命名空间说明、合法临床影像连接批准均缺失；连接子类计数因披露控制留在私有文件。
- `GROUPING_UNVERIFIED`、`TIMEPOINT_UNASSIGNED`：只有本机同 PatientID 的先后顺序，不是治疗时点或已批准的患者分组。
- `ROI_SEMANTIC_UNRESOLVED`：没有逐 ROI 权威 crosswalk；本任务未判定肿瘤轮廓，也未读轮廓坐标值。
- `ENDPOINT_CODEBOOK_UNVERIFIED`：工作簿字段含义、行粒度、事件时间起点与删失规则仍未核实。
- IDC v25.0.0 本地存在 15 个缺失 Series 和 1,132 个实例缺口；计数相等不代表位级完整、PixelData 可解码或空间几何正确。
- MRI 像素/空间 QC、分割、Radiomics、治疗变化、应答/生存分析均未运行。所有核心影像科研仍由用户学习、编写、运行和审查；**`R0 NOT COMPLETE`**。
