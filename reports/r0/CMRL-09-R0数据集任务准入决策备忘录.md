# CMRL-09｜R0 数据集与任务准入决策备忘录

**Plan：** CMRL-Plan-09 r1（外部文件）
**性质：** 提供 Main/用户决策材料；不代替数据集准入或实验选题
**状态：** R0 NOT COMPLETE；无任务获得最终 GO。

## 1. 候选数据 × 任务矩阵

| 数据集 | 现有可用格式及许可 | Image/Mask 语义 | 患者键 / 中心 / 时点 | 监督分割 | 体积 Radiomics | 临床结局 | 解除限制的最小证据 |
|---|---|---|---|---|---|---|---|
| **TCIA CC-Tumor-Heterogeneity** | 官方来源报告 DICOM、多模态影像与 Clinical XLSX，CC BY 4.0；既有 CMRL-04–08 对用户本地文件做过限定范围检查。本次未重读本地文件。公开记录含 63 个本地 RTSTRUCT、15 个缺失 Series 与 73 个实例短缺 Series/合计 1,132 个实例；不是完整性验收。 | 发布页描述 tumor contour，但没有逐发布 RTSTRUCT ROI Number/Name/Observation→tumor/uterus crosswalk；RTSTRUCT 不能直接称作 tumor mask。 | Collection 报告 23 subjects；Clinical 候选键与 DICOM PatientID 命名空间关系未证实；论文 21 人与 Collection 23 人关系 UNKNOWN；真实 DICOM 时点未分配。 | **NO-GO**；先有权威 ROI 身份/适用范围，逐例像素及空间 overlay 人工验收，并确认所选 MR/RTSTRUCT Series 与对象完整。 | **NO-GO**；需有效肿瘤 VOI、空间几何、完整可用体积和预处理可复现。 | **NO-GO**；需 Clinical V2 codebook、事件/时间零点/单位/删失规则、授权患者连接及真实时点。 | ROI 发布 crosswalk；受限 Series 的版本一致完整性证据；用户选定病例的像素/几何/轮廓验收；临床 codebook 与正式 join/timepoint provenance。 |
| **FlexFair** | 已审计 ZIP 为 3,366 对 2D PNG/Mask；发布来源报告 CC BY 4.0。完整文件级内容与命名配对由 CMRL-01/02 检查。 | 作者称 T2WI 肿瘤分割，但发布物只有 2D PNG/Mask 配对，不能等同原始完整 3D DICOM。 | 原论文报告 678 人、四中心；发布文件没有可靠患者/中心键。CMRL-01/02 检出跨 split 精确重复，不能据当前文件做患者级无泄漏结论。 | **CONDITIONAL**：仅可由 Main/用户选择为图像级 2D 教学；需先明确跨 split 重复处置和受限评价范围。不能声称患者级或中心级泛化。 | **NO-GO**：缺少经过验证的完整体积及物理空间信息。 | **NO-GO**：现有证据没有可用且连接可信的临床结局标签。 | 若要患者级/跨中心结论，须取得可信患者、中心与切片映射并重新核查重复和划分；若要 3D Radiomics，须有合法完整原始体积及 spacing/origin/direction。 |
| **CCMD** | 原作者论文/仓库报告 151 人、影像/标注资源；访问需按 README 申请密码/授权，尚未获得。README 与示例格式说明不一致；实际文件未取得。许可证和实际可用格式未验证。 | 作者声称 T2WI 肿瘤标注；实际 image-mask 语义、方向、空间对齐及病例覆盖未检查。 | 没有取得患者键/中心/时间映射，实际队列和 longitudinal 信息未验证。 | **NO-GO（当前不可获得）**：先取得合法授权/访问，再核对图像与掩膜配对及空间定义。 | **NO-GO**：实际格式、三维几何及 ROI 尚未检查。 | **NO-GO**：无已核实的 Clinical 字段或疗效结局。 | 明确访问授权及可复核的许可/使用限制；取得合法文件后逐病例核实影像、掩膜、方向和坐标；若研究临床结局另需 endpoint codebook 与合法连接。 |

**状态解释：** GO/CONDITIONAL/NO-GO 指当前证据下的候选任务状态，不代表 Main 已选定、用户已批准或实验已运行。许可/格式结论保持原有 CMRL-01/02/04–08 的证据范围。

## 2. 供 Main/用户选择的三条路线

| 选项 | 下一步 | 预计成本 | 可得到的证据 | 不能据此声称 |
|---|---|---|---|---|
| A. 继续外部释义 | 由 Main/用户决定是否自行联系论文作者或 TCIA，询问 ROI crosswalk、Clinical V2 codebook、21/23 cohort provenance 与时点映射。CMRL-09 报告附有未发送草案。 | 起草与发送成本低；等待/无回复及后续解释时间不确定。 | 可能取得作者/发布方的官方说明；若回复，应保存来源、范围、版本与日期再审查。 | 本备忘录没有联系任何人；问题草案不等于已获解释或授权。 |
| B. 用户主导 TCIA 单例空间 QC | Main/用户另行选定候选后，由用户亲自载入像素并检查影像方向、几何、轮廓对齐及用户可观察的结构。 | 中等；至少需一个病例的 DICOM 读入、图像/轮廓可视化和记录。 | 可验证所选病例文件能否用于单例空间教学。 | 不确立 ROI 临床语义、整库覆盖、肿瘤真值或监督分割准入。 |
| C. 转向 FlexFair 图像级教学 | Main/用户可考虑限定为 2D PNG/Mask 图像级教学，并明示跨 split 重复和无患者/中心键限制。 | 中等；需明确划分、重复处理、评价范围并由用户亲自运行核心分割代码。 | 可能完成受限的图像级分割学习/演示。 | 不支持患者级拆分、跨中心泛化、3D 体积 Radiomics或临床应答预测。 |

CCMD 是备选的受限资源；在授权、密码及文件结构核实前不作为可开工数据。三条路线均未被本任务选定。R1–R8 不自动开始，R0 仍需 Main 正式审查与用户决定。

## 3. 结论边界

- TCIA：单例空间 QC 维持 CANDIDATE/CONDITIONAL；监督分割、体积 Radiomics、纵向分析和临床结局 NO-GO。
- FlexFair：只存在条件性图像级 2D 教学路径；患者级/中心级主张和 3D 任务不成立。
- CCMD：RESTRICTED、FILE-NOT-INSPECTED。
- 论文发表的 Dice/AUC 不是本项目成果。没有训练、推理、分割或预测运行。
