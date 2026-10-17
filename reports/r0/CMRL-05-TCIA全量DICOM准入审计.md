# CMRL-05｜TCIA 全量 DICOM 与下载完整性准入审计

- **审计日期：** 2026-10-17
- **任务 / Plan：** CMRL-05 / CMRL-Plan-05 r1
- **研究阶段：** R0-DATA-ACCESS-AUDIT；R0 NOT COMPLETE。本报告不批准 R1、肿瘤分割、Radiomics 或临床结局建模。
- **本地目录别名：** data/raw/tcia/ccth_idc_v25_full/；人工下载子集 data/raw/tcia/ccth_manual/ 仅用于确认目录隔离，本任务未重新扫描或操作该子集。
- **来源等级：** manifest 结构经本地文件核验；DICOM Header 与 RTSTRUCT 元数据为 FILE-INSPECTED。全量目录由用户报告为 IDC CC-Tumor-Heterogeneity Release 25.0 下载，但当前没有经验证的本地 Collection 成员映射。

## 结论

本机指定目录有 **130,424 个普通文件，共 28,151,425,416 bytes（28.151 GB / 26.218 GiB）**，全部扩展名为 .dcm。文件系统清点完整，130,424/130,424 个文件均经 pydicom 标准路径成功解析 Header。未发现空文件、读取错误、重名文件、特殊文件或链接；全量 Header 扫描耗时 260.891 秒，清单、清点和扫描合计 287.235 秒，未触及 200,000 文件或 60 分钟预算；单文件 Header 上限为 128 MiB，RTSTRUCT 深解析上限为 16 MiB。审计前后 130,424 个文件的相对位置、字节数、mtime 和属性摘要一致，没有发现新增、删除或元数据变化。

本机 manifest 为 IDC Release 25.0，52,045 bytes，SHA-256 与计划记录副本一致；821 条受限格式 source-prefix 命令均唯一、无格式异常。manifest 使用通配符，不列出每个 Series 下预期的 DICOM 对象。因此结论分层为：

| 证据层级 | 状态 | 依据 |
|---|---|---|
| Manifest 结构 | MANIFEST_STRUCTURE_VERIFIED | 本地摘要匹配；821/821 命令结构有效且前缀不重复 |
| Manifest 前缀到本地 Series 覆盖 | SERIES_COVERAGE_NOT_VERIFIED | 没有经过验证的 source-prefix→DICOM Series 映射；当前没有可验证的映射，821 条均处于未映射状态 |
| 逐对象下载完整性 | OBJECT_LEVEL_COMPLETENESS_NOT_VERIFIED | manifest 通配符不是对象级期望清单；没有版本一致的权威对象清单可逐项比较 |
| 本地候选文件 Header 可解析性 | PASS（130,424/130,424） | 全候选集标准解析成功，强制解析、失败和跳过均为 0 |

本地 806 个 Series 与 Collection 发布统计 821 个 Series 不相等；本地 130,424 个文件与发布页 131,556 张 images 的计数语义未证明一致。官方约 28.39 GB 是四舍五入后的 Collection 统计，本机实测数值接近不构成逐对象完整性证据。发布页的 23 subjects、171 studies、821 series、131,556 images 均是 Collection 级公布值；本机 23 个 PatientID 键、171 个 Study 和 806 个 Series 不是独立患者身份或 Collection 成员关系的证明。没有把 61 条未命中的 SOP 引用直接判为下载失败。

DICOM 直接引用证据显示：63/63 个 RTSTRUCT 的 Series 引用命中本地 MR；1,873 条按每个 RTSTRUCT 内 SOP UID 去重的直接 SOP 引用命中本地 MR，另有 61 条在本地候选对象索引中未命中。命中项的患者键、Study、Series 和 Frame 键一致，全部命中 MR T2 文本/参数候选。此证据只描述本地 DICOM 引用链，不能证明 Collection 来源、影像与轮廓的像素空间对齐，或 ROI 是原发宫颈肿瘤。

## Manifest 与输入边界

本地 manifest 经 UTF-8 严格解析，内容摘要如下：

| 项目 | 结果 |
|---|---:|
| Release | IDC Data Release 25.0 |
| 文件字节数 | 52,045 |
| SHA-256 | f56073583ad4cf931a9a46fac83af2672f5b0248ebcc2a94406e9f662508ee79 |
| manifest 声明总量 | 28.39 GB |
| 受限 cp 命令 / 唯一 source-prefix | 821 / 821 |
| 重复前缀 / 非法非注释行 | 0 / 0 |
| 通配符是否包含对象级预期清单 | 否 |

manifest 只作为惰性文本读取，没有执行其中命令。未访问 TCIA、IDC 或 S3 网络端点，也没有下载、同步、删除或重命名数据。Manifest 前缀值和原始路径没有写入持久证据。

## 文件系统清点与原始数据保护

| 项目 | 实测 |
|---|---:|
| 普通文件 / DICOM 候选 | 130,424 / 130,424 |
| 文件总字节 | 28,151,425,416 |
| 子目录（不含根目录） | 1,016 |
| 扩展名 | .dcm：130,424 |
| 零字节 / 读取标记不可用 | 0 / 0 |
| 元数据错误 / 特殊项 / symlink 或 reparse point | 0 / 0 / 0 |
| 重复 basename | 0 |
| 两个本地目录重叠 | 否 |
| 文件内容哈希 | 未计算 |
| 扫描前后源文件元数据变化 | 0 |

用户报告的 28,151,425,416 bytes 与现场清点一致。前后快照按相对路径、大小、最后写入时间和文件属性比较；不是内容哈希，不能排除这些字段不变时的内容改写。审计中所有原始文件只读打开，没有向 DICOM 源目录写入。无临床工作簿、下载日志或像素数据读取。

## DICOM Header、键计数与模态

Header 读取使用 pydicom 3.0.2、Python 3.12.14 的标准路径和 stop_before_pixels，仅取审计所需元数据标签；未强制解析，未解码 Pixel Data。

| 项目 | 数量 |
|---|---:|
| 标准 Header 成功 / 失败 / 强制解析 / 超限跳过 | 130,424 / 0 / 0 / 0 |
| 不同 PatientID 键 / Study UID / Series UID / Frame UID | 23 / 171 / 806 / 171 |
| 缺少顶层 Frame UID / 重复 SOP UID | 63 / 0 |
| Study 含多个 Series | 139 |
| 每个 PatientID 键均对应多个 Study | 是，23 个键均如此 |
| 每个 Series 实例数：最小 / 中位数 / 最大 | 1 / 36 / 1,400 |

PatientID 是本地 DICOM 键数量，不等价于独立核实的真实患者数。所有值只在进程内用于聚合与关联，没有写出 UID、患者级索引或逐病例记录。

| Modality | 文件数 |
|---|---:|
| MR | 92,508 |
| CT | 21,637 |
| PT | 16,129 |
| REG | 87 |
| RTSTRUCT | 63 |
| SEG / 其他 / 缺少 Modality | 0 |

## MR 候选与空间元数据

92,508 个 MR 实例分布在 523 个 Series。202 个 Series 按启发式列为 T2 候选：Series 文本中有 T2 标记的 196 个，满足自旋回波术语和 EchoTime 阈值的 24 个；规则来源有重叠，候选总数按并集计数。文字/参数标记不能确认物理序列属性或采集时点。

所有 92,508 个 MR 实例均有 Rows、Columns、PixelSpacing、ImagePositionPatient、ImageOrientationPatient、SliceThickness 和 FrameOfReferenceUID；存在值的正值/有限性与基础范围检查通过。SpacingBetweenSlices 有 62,936 个存在、29,572 个缺失；SliceThickness 不能替代相邻切片间距。本任务没有排序切片、重建体积或验证切片堆叠与空间方向。

## RTSTRUCT、ROI 与直接引用

63 个 RTSTRUCT 均低于 16 MiB 深层解析上限，全部完成元数据解析。ROI 类型依 CMRL-04/r2 正确逻辑，从 RTROIObservationsSequence 读取 RTROIInterpretedType，并通过 ReferencedROINumber 与 StructureSetROISequence.ROINumber 关联。

| RTSTRUCT/轮廓指标 | 聚合结果 |
|---|---:|
| Structure Set ROI / Observation / ROIContour | 126 / 126 / 126 |
| ROI、Observation 和 ROIContour 唯一关联 | 126 / 126 / 126 |
| RTROIInterpretedType：EMPTY | 126 |
| 名称启发式 OTHER（与 DICOM 类型分开统计） | 126 |
| Contour item | 1,482 |
| CLOSED_PLANAR / 点数为正 / 数据长度匹配且有限 | 1,482 / 1,482 / 1,482 |
| 带 ContourImageSequence 的 contour | 1,482 |
| 去重后的 contour SOP 引用数 | 857 |
| 深层解析失败 / 超过大小上限 | 0 / 0 |

| 直接引用类别 | 结果 |
|---|---:|
| RTSTRUCT 直接 Series 引用命中本地 MR | 63/63 |
| RTSTRUCT 有直接 SOP 引用命中本地 MR | 63/63 |
| 去重后的 SOP 引用命中 MR / 未在本地候选对象中命中 | 1,873 / 61 |
| 已命中引用的 PatientID、Study、Series、Frame 一致 | 各 1,873/1,873 |
| 已命中 SOP 引用指向 T2 启发式候选 | 1,873/1,873 |

弱同现对照以“一个 RTSTRUCT × 一个本地 MR Series”为单位：1,450 对 PatientID 键相同，其中 1,019 对没有 SOP/Series/Frame 直接引用；431 对 Study 相同，均有直接引用；431 对 Frame 相同，均有直接引用。弱同现不替代 DICOM 直接引用。61 条未命中引用可能指向本次扫描目录以外的对象，现有证据无法区分它们的来源或完整性状态。

以上仅核验 DICOM 声明的引用关系、ROI 字段关联、轮廓几何枚举、点数和坐标元素有效性。未检验点共面性、闭合轮廓、与 MR 像素网格的实际对齐，也未解释 ROI 的临床含义。即使名称像 GTV 或标签非空，也不能据此认定原发宫颈肿瘤；本次所有 ROI 类型字段为空、名称规则结果为 OTHER。没有创建 Mask 或开展可视化叠加。

## 研究准入矩阵

| 维度 | 状态 | 判定 |
|---|---|---|
| 本地候选文件标准 Header 可解析性 | PASS | 130,424/130,424 成功；仅限所扫描本地目录与 Header |
| manifest 结构与发布版本 | PASS | Release 25.0、SHA 匹配、821 条合法唯一命令 |
| Series 逐项覆盖 | NOT_VERIFIED | 没有可信 source-prefix→Series 映射 |
| 逐对象下载完整性 | NOT_VERIFIED | 没有对象级期望清单；不能由 28.39 GB 或目录计数推断 |
| MR 核心空间字段可读 | PASS（字段层） | 关键字段齐全且基础数值检查通过；未验收体积/几何 |
| MR–RTSTRUCT DICOM 直接引用 | PASS（本地元数据层） | 63 个 Series 引用命中 MR；1,873 个 SOP 引用命中 MR，另 61 个未命中 |
| MR 与 RTSTRUCT 同时存在 | PASS | 本地 Header 与引用记录已检查；不代表同一研究目标/像素对齐 |
| ROI 名称/标准类型线索 | PARTIAL / NO-GO for tumor claim | DICOM 类型为空；OTHER 名称启发式无诊断力 |
| 3D 教学候选前提 | CONDITIONAL | 可考虑由用户选一组有直接引用的 MR+RTSTRUCT，在本机查看器先检查；不得视为可用 3D Mask |
| 患者级分组与独立身份 | NOT_VERIFIED | PatientID 键数与来源身份映射未独立确认 |
| 临床结局/疗效标签 | NOT_VERIFIED | 未读临床工作簿，未核对标签定义、时间和逐人配对 |
| 研究阶段 | R0 NOT COMPLETE | 本任务不批准或启动后续阶段 |

## 隐私、边界与复现

只持久化集合/模态/质量层聚合数字。仓库证据、报告和脚本没有 PatientID/Name 值、Study/Series/SOP/Frame UID 值、真实检查日期、医院、文件名、原始路径、ROI 名称/坐标、病例级关联或 manifest source-prefix。manifest 命令没有执行；TCIA/IDC/S3 没有访问；没有读取临床工作簿、解码像素、重建体积、配准、栅格化 RTSTRUCT、Radiomics、模型或临床解释。原始 DICOM 文件未被修改。

脚本在隔离分支的忽略目录中使用 Python 3.12.14 与 pydicom 3.0.2；未修改用户下载 venv，也未安装影像科研栈。审核入口见 [audit_tcia_full_dicom.py](../../scripts/r0/audit_tcia_full_dicom.py)，脱敏结果见 [tcia_full_dicom_profile.json](../../evidence/r0/tcia_full_dicom_profile.json)。合成 manifest、映射/完整性、引用共现、合成 DICOM PixelData 截断和错误分类测试通过；全任务合计 26 项测试通过（本脚本 14 项、既有 CMRL-04/r2 RTSTRUCT 回归 12 项）。

来源背景与 DICOM 定义可参考 [TCIA CC-Tumor-Heterogeneity](https://www.cancerimagingarchive.net/collection/cc-tumor-heterogeneity/)、[DICOM RT ROI Observations Module](https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_c.8.8.8.html) 与 [DICOM ROI Contour Module](https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_c.8.8.6.html)。官方统计数字来自既有来源记录及 Plan-05，不代表本次在线复核或本地 Collection 成员确认。

## 最低成本后续补证

1. 由用户在本机医学影像查看器中挑选一组存在直接 DICOM 引用的 MR+RTSTRUCT，检查 ROI 名称、轮廓位置与图像空间关系；记录是否确认为原发宫颈肿瘤结构。此操作由用户在 Lab 亲自完成，本报告不替用户判断。
2. 如需证明下载完整性，提供与 Release 25.0 同版本、可信来源的逐对象期望清单或可核对的对象级下载记录；用本地目录逐对象比较。当前 821 条通配符 manifest 和目录体量不能替代该证据。
3. 将本报告交 Main 纳入 R0 综合准入审查；由 Main 决定研究阶段与下一项教学，不因本任务自动创建后继 Plan。
