# CMRL-08｜TCIA 私有连接与 MR–RTSTRUCT 候选预筛报告

**Plan：** CMRL-Plan-08 r1（外部文件，未复制入仓库）
**任务状态：** COMPLETE（仅指本 Plan 授权的离线元数据审计）
**研究阶段：** R0-DATA-ACCESS-AUDIT；**R0 NOT COMPLETE**
**证据边界：** 不读取 MRI PixelData，不读取/解码 ContourData 值，不赋予临床语义或治疗时点。

## 1. 结论摘要

1. Clinical V2 本机文件与 Plan/CMRL-07 固定字节数及 SHA-256 一致。工作簿有 28 个非空数据行、9 个命名字段；沿用 CMRL-07 候选身份键字段口径，23 行有候选键，另有 5 行仅一个文本单元格。五行均落在同一非键字段类别，连续位于数据表尾，样式与键控记录不同；没有公式、批注、合并交叉或明确注释标记。工作簿本身没有可识别的 codebook/legend 标记。**这些事实只能描述布局，不能证明五行是注释、脚注、患者记录或可排除记录；行粒度仍 UNKNOWN。**
2. Clinical 候选键与本地 DICOM PatientID 做了仅字符串、无规范化的精确连接。公开汇总中的匹配/未匹配/歧义子类按小单元格与补数规则抑制。状态保留 **JOIN_UNVERIFIED**；患者键来源语义未确认，Clinical-image join 未获授权。23 对 23 的集合大小不构成身份依据。
3. IDC 官方固定 Release 25.0.0 与本地重算结果一致：官方 821 个 Series；本地 806 个，其中 15 个缺失；748 个 Series 实例数相等，73 个短缺，共短缺 1,132 个实例、超额 0。MR 523/523 个 Series 命中，但 55 个短缺 800 个实例；RTSTRUCT 本地 63/68，缺 5 个。所有 Series 的计数相等只表示实例数量相等，不表示对象字节、像素或空间完整。
4. 一次全库最小 Header 扫描解析 130,424/130,424 个文件，错误 0；总计 28,151,425,416 bytes。扫描前后文件元数据 snapshot 完全一致。63 个 RTSTRUCT 均完成允许范围内的引用解析；全局唯一直接 SOP 引用 1,934 条，其中本地唯一命中 1,873、未命中 61、歧义 0，与 CMRL-05 未命中数一致。RTSTRUCT ContourData 值读取字节为 0；9,595,982 个坐标值字节通过 seek 跳过。
5. 逐 MR Series 计数与 RTSTRUCT 直接引用链筛选得到 **56 个唯一 MR Series–RTSTRUCT Series 组合**（不是独立患者数）。文本 T2 候选采用 SeriesDescription / ProtocolName / SequenceName 的 T2 字符串启发式，只用于排序；不证明 T2 信号、矢状位、可用体积或空间吻合。按 Plan 至多 3 组的私有定位索引已写入忽略区；被选清单的精确小计不在公开材料中披露。每组均记录计数、直接引用、患者键一致性、Study/Series 链和 Frame 关系；Frame 不同或未知时保留未解决状态，不推定 REG 可叠加。
6. 时点只有本机私有的同一 DICOM PatientID 日期/时间先后排序 CHRONOLOGY_ONLY；去标识化日期可能偏移。没有真实治疗日程映射，所有实际 PRE/EARLY/MID 仍 UNASSIGNED；患者分组定义仍 GROUPING_UNVERIFIED。
7. ROI_SEMANTIC_UNRESOLVED、ENDPOINT_CODEBOOK_UNVERIFIED 均未改变。单例 MRI 像素/空间 QC 可列为 CANDIDATE，但须由用户亲自读取像素并验证方向、spacing、origin、切片顺序和 RTSTRUCT 空间关系；三维肿瘤分割、体积 Radiomics、纵向治疗变化及应答/DFS/OS 仍 NO-GO。

## 2. 来源与版本锚定

- IDC：固定 idc-index-data Release 25.0.0；index data version 25.0.0-0-gdbf7fd0。主索引 SHA-256：450598d6493d800334a8e1ece1fda4a5ec04ca1bd2f73309058f0531f8155572；collections_index SHA-256：97e5ac3bba296cb3f4e9d87545231275aad66fc89ba07262b7914e72e857489c。仅本地读已验证缓存；没有请求 TCIA、IDC REST 或 S3。
- Clinical：Version 2，与 IDC Release 轨道分开；14,233 bytes，SHA-256 a59d29c86bb45bca98649d1eb8c7a533558fd1cf7b6beb35f5175ea47a04d1c9。未重新下载。
- 固定索引期望 821 Series / 131,556 instances；本地私有差异清单 73 行，其 Series、期望/观察计数和短缺合计与本次重算一致。该私有清单未复制入 Git。

## 3. Clinical 异常行：观察事实与解释边界

| 项目 | 文件级观察 |
|---|---|
| 非空数据行 / 候选键 | 28 / 23 个互异字符串键 |
| 未键控单格行 | 5 行，均为文本，唯一非空格位于同一非键字段类别 |
| 布局 | 五行连续处于数据表尾；单元格样式与键控记录不同 |
| 工作簿结构 | 9 个命名字段；这五个单元格无公式、批注、合并交叉或显式注释标记 |
| 内部释义 | 未发现工作簿内部 codebook/legend 标记；终点 codebook 仍未核实 |

**解释：** OBSERVED_LAYOUT 支持把五行作为一个结构上不同的尾部区块审查，但 INTERPRETED_ROLE 仍 UNKNOWN。没有文件内标记可以把它们确定称为注释/图例；也没有权威字段定义可证明它们是有效病例记录。当前不删除、不计为患者、不派生标签。

## 4. 患者键精确连接

- Clinical 候选键和本地 DICOM PatientID 按原字符串、同类型进行精确连接；无 fuzzy、大小写转换、空白修剪、行序或日期推断。
- 两侧集合各有 23 个键；单纯数量相等不证明键命名空间相同。
- 匹配、未匹配、歧义的具体数量位于本机忽略区私有 crosswalk；公开 profile 对小于 5 的类别及补数实施联合抑制，因此不在本报告披露子类计数。
- 证据等级：JOIN_UNVERIFIED；SOURCE_SEMANTICS_CONFIRMED = false；CLINICAL_IMAGE_JOIN_AUTHORIZED = false。不从 Clinical 表构造 response、DFS、OS 或复发标签。

## 5. IDC v25 与本地文件完整性对账

| Modality | 官方 Series | 本地 Series | 数量相等 | 短缺 Series | 完全缺失 |
|---|---:|---:|---:|---:|---:|
| CT | 65 | 65 | 64 | 1 | 0 |
| MR | 523 | 523 | 468 | 55 | 0 |
| PT | 68 | 68 | 66 | 2 | 0 |
| REG | 97 | 87 | 87 | 10 | 10 |
| RTSTRUCT | 68 | 63 | 63 | 5 | 5 |
| **总计** | **821** | **806** | **748** | **73** | **15** |

短缺合计 CT 103、MR 800、PT 214、REG 10、RTSTRUCT 5，共 1,132；超额 0。文件级全库统计为 MR 92,508、CT 21,637、PT 16,129、REG 87、RTSTRUCT 63。Header 缺失 PatientID / Study UID / Series UID / SOP UID 均为 0；重复 SOP 文件为 0。

同一次输入元数据 snapshot：普通文件 130,424、字节 28,151,425,416；DICOM 候选 130,424；零字节、reparse/link、special entry 和 snapshot 元数据错误均为 0；前后 snapshot 相等。**Snapshot 只比较文件元数据，不是内容哈希或像素校验。**

## 6. RTSTRUCT 引用与候选组合

自定义受限解析器只沿以下标准嵌套引用读取 UID：ReferencedFrameOfReference → RTReferencedStudy → RTReferencedSeries → ContourImage，以及 ROIContour → Contour → ContourImage。其他值 seek 跳过；ROI 名称、ROI Number 及 ContourData 数值不读。

- 63/63 个本地 RTSTRUCT 通过限定解析；全局直接 SOP 引用 1,934 个唯一值，1,873 个唯一命中、61 个未命中、0 个多重本地命中。61 个缺失仍单独保留，未因局部候选对而消解；它们与 RTSTRUCT Series 缺失的关系仍 UNKNOWN。
- 候选对必须同时满足：目标 MR Series 官方期望计数与本地唯一 SOP 计数相等；RTSTRUCT Series 计数相等；RTSTRUCT 所有直接 SOP 引用在本地唯一命中；目标 MR 的患者键与 RTSTRUCT 一致；目标引用链的 Study → Series → SOP 一致。目标引用之外的直接引用单独保留其本地解析状态，不据此推定配准或空间叠加。
- 通过组合数为 56（Series 对，不是患者数）。文本 T2 仅是启发式。排序优先 T2 文本、相同 Frame、较少 MR 文件和较少引用；不依据 ROI 名称、轮廓大小、病灶外观或结局。
- 本机私有定位文件记录最多 3 组；患者私有映射和候选路径均不提交。精确入选小计因小单元格抑制不公开。候选不是已验收的影像或肿瘤 Mask。

## 7. 时点、研究单位与准入

| 研究任务 | 本次状态 | 限制依据 |
|---|---|---|
| 单例 MRI 像素/空间 QC 教学 | **CANDIDATE** | 只能按私有索引定位；用户须亲自验证像素、方向、体素间距、origin、切片顺序与 RTSTRUCT 空间关系。当前 PIXEL_SPATIAL_NOT_RUN。 |
| 三维肿瘤分割 | **NO-GO** | ROI_SEMANTIC_UNRESOLVED、空间未验收、Series 实例缺口；引用不等于 tumor mask。 |
| 体积 Radiomics / Habitat | **NO-GO** | 未确认肿瘤 VOI 与像素/空间质量，且存在 INSTANCE_GAP。 |
| 纵向治疗变化 | **NO-GO** | 当前只有 CHRONOLOGY_ONLY；TIMEPOINT_UNASSIGNED、GROUPING_UNVERIFIED。 |
| 应答/复发/DFS/OS | **NO-GO** | JOIN_UNVERIFIED、ENDPOINT_CODEBOOK_UNVERIFIED；不得从字段名或键连接推造终点。 |

不创建 train/val/test 划分，不做特征选择、标准化、SMOTE 或模型训练。Main 审查后才决定是否进入用户主导的单例空间实践。

## 8. 执行、隐私与复现记录

- Header 环境：Python 3.14.6、pydicom 3.0.2、DuckDB 1.5.6；Clinical 阶段：Python 3.12.14、openpyxl 3.1.5。
- Header 扫描与前后 snapshot 约 253.4 秒；包含索引校验、引用处理和写 profile 的 combined audit 约 254.8 秒；扫描预算 150,000 文件 / 25 分钟，实扫 130,424 个文件。
- 全合成 unittest：9 项通过，约 0.9 秒；包含 Clinical 单格布局、精确 join/类型/重复、数量相等与短缺、引用缺失/多重命中、无候选、T2 启发式、日期排序不等于治疗时点、私有字符串序列化拦截、Git ignore、合成 RTSTRUCT 坐标值跳过。合成测试不作为真实 DICOM 成功证据。
- 原始 DICOM 仅以只读方式打开；不读取 PixelData，不读取 ContourData 值；Plan 网络请求预算 0，实际数据源网络请求 0。
- 完成一次真实扫描后，只对同轮 JSON/私有索引做序列化补充（运行版本、snapshot 错误计数、Series 对口径及非目标引用汇总），并给后续运行脚本增加 Clinical reparse 路径拒绝与 profile 字段声明；未进行第二次全库 DICOM 扫描。补充值来自本轮已记录统计和同一 Python 环境核对；Clinical 文件本身另做过受限路径/普通文件检查。
- 私有区位于任务 worktree 忽略目录，git check-ignore 命中，目录 ACL 继承已关闭并限制为 3 条本地管理规则。公开序列化的患者键、UID、路径、DICOM 文本、日期及 Clinical 值扫描无命中。
- 输出：本报告、脱敏聚合 evidence/r0/tcia_private_crosswalk_screen_profile.json、受限脚本 scripts/r0/audit_tcia_private_crosswalk_screen.py、全合成测试 tests/test_tcia_private_crosswalk_screen.py。

## 9. 未解决事项与最低成本后续证据

1. 若要确立 Clinical ↔ DICOM 身份语义，需官方/作者命名空间说明或可信 crosswalk；当前精确字符串比较本身不能升级为研究连接。
2. 若要判断五条 Clinical 单格行，需文件制作者解释其用途/记录粒度；不得仅凭尾部位置或样式改称注释。
3. 若要区分实际治疗时点，需患者级治疗日期/权威时点 crosswalk；DICOM 排序不能替代。
4. 若 Main 决定继续，用户可从私有索引选择一个组合，亲自完成单例像素/空间 QC；ROI 名称到 tumor/uterus 的权威映射与临床 endpoint codebook 仍须独立补证。
5. 本报告不接受数据集、不宣称 ROI 真值、不批准监督分割或临床模型；R0 保持 NOT COMPLETE。
