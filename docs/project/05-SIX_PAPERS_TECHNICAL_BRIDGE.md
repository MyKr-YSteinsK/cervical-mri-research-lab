# 05｜六篇原始论文到新研究的技术映射

**目的**：新项目即使不复现其中某一篇的 AUC，也不丢失六篇精读形成的医学影像 AI 研究语境。每篇原 PDF 已在 `SOURCE_PAPERS/` 随包附带；下述摘要不能替代阅读正文。

| 编号 | 原始论文、目标及已讲技术 | 在新项目对应实验 | 主要边界 |
|---|---|---|---|
| P01 Gui (2021) https://doi.org/10.3390/diagnostics11040631 | 183 人 NACRT 后 pCR、T2WI，传统 1889 个手工特征、筛选、Random Forest、重复内部 CV；平均 AUC 约 0.80 | 第一条 PyRadiomics 传统基线与特征稳定性、ROI 的影响 | 自有原始应答标签未公开；不能把新分割 Dice 当作 pCR AUC |
| P02 Chiappa (2023) https://doi.org/10.3390/diagnostics13193139 | 72 人 NACT 应答、手工+ResNet50、ADASYN、RF/SVM/KNN 集成与嵌套 CV | 小样本时的数据泄漏防护、特征选择与算法比较 | 摘要/表格标签统计口径有矛盾；小样本性能难泛化 |
| P03 Jeong (2024) https://doi.org/10.1038/s41598-024-51742-z | 252 人 CRT 临床应答，HCR/SVM vs I3D 3D CNN + 临床融合；有作者公开代码 | CNN 3D tensor、冻结/微调、PyTorch 数据与训练/ROC 代码教学 | 167/85 与 Methods 176/76 划分矛盾；作者医院数据需申请 |
| P04 Yang (2024) https://doi.org/10.3390/diagnostics14010005 | 138 人 NACRT pCR；二维 VGG19 多层特征，传统/深度/临床双分支，八分类器权重融合 | 多尺度特征与分支独立对照；预测模型存在标签后探索决策融合 | 内部重复 CV，不能当独立外部测试 |
| P05 Cai (2024) https://doi.org/10.1038/s41598-024-70055-9 | 360 人 NACRT 应答；T2WI+CE-T1WI，手工与 ResNet50 特征，ElasticNet/SVM-RFE 早期融合、OS/DFS 分析 | 多序列/双表征特征拼接；高维稳定性和亚区域扩展 | 生存分组、标签依据需逐项回原文审读 |
| P06 Zhang (2023) https://doi.org/10.3390/diagnostics13061073 | 正文 285 人：148/72/65，NACT CR/PR vs SD/PD、T2WI/DWI/CE-T1WI；DenseNet121、ICC、SMOTE、LASSO、DLRN、外部验证、Calibration/DCA/DFS | ICC/稳定 Radiomics，跨中心泛化、模型评分融合与统计可靠性 | Figure1 与正文人数矛盾；DFS 人数/评分方向待核；与 pCR 不同终点 |

## 技术增量参照图

- 传统特征 / 统计稳定性：P01 → P06 的 ICC 与跨中心验证。
- CNN 表征：P02/P05 ResNet50；P03 I3D；P04 VGG19 多层；P06 DenseNet121。
- 特征选择：相关性/互信息 → RFE、χ²、ElasticNet → LASSO/ICC。
- 多来源融合：P04 基础分类器决策权重；P05 早期特征融合；P06 基础模型评分的 Logistic 融合；无标签时只能研究表征，不可计算治疗应答 AUC。
- 最终评价：影像分割看 Dice/HD95/NSD；有真实临床分类才看 AUC、Sensitivity、Calibration、DCA；有生存数据再做 KM/HR/C-index。

## 原课程已讲 ≠ 具备真实工程能力

以前只是**纸上认知导读**，没有对六篇数据下载、训练、运行或重现发表指标。用户曾重点追问 DeLong（同患者 ROC-AUC 比较）、SMOTE 的训练与验证边界、AUC 排序与固定阈值分类的区别；在真实实验中这些概念应按需唤醒并通过代码落地。六篇第一轮已覆盖、第二轮未启动，迁移不代表英文精读完成。

## 源 PDF 归档（共六份）

见 `SOURCE_PAPERS/P01`–`P06`。优先直接引用原 PDF 的真实页码/Methods/Figures/Tables，区分论文作者报告与自己在新数据上的新实验。今后发现旧教学摘要的错误，以原文与数据证据纠正，避免将简表当权威。
