# CMRL-02｜FlexFair 分组与身份线索复核

**审计日期：** 2026-10-16（UTC）
**任务：** `CMRL-02`，依照用户仓库外提供的 `CMRL-Plan-02-FlexFair分组身份核验与Plan目录治理.md` r1
**分支基线：** `codex/r0-01-flexfair-archive-audit`，`85750090a9828ce1a81e2c8cc59bca75093ad197`
**范围：** 复核原作者公开加载代码与已核验 Figshare ZIP；只做文件结构、命名配对、目录分组、身份线索和影像侧精确像素重复审计，并落实 Plan 存放治理。未进行模型训练、医学影像语义判读或研究阶段验收。

## 结论

当前 Figshare ZIP **没有复现原作者代码所期待的四个组目录，也没有 `Private/train/<group>/` 或 `Private/test/<group>/` 路径**。ZIP 自身存在 train/test 文件夹层级，但其中只有未映射到作者四组代号的图像和 Mask 文件。因此，不能据文件夹位置恢复论文报告的四个临床中心身份，也不能把目录名 `Private` 当成访问限制或患者身份标识。作者代码和其 README 中所说的 `train.zip`/`test.zip` 与当前单一 Figshare ZIP 的发布关系尚无可核验映射。

全包完整性与 CRC 复核通过。作者的 `_label.png` 同目录配对规则和 CMRL-01 文件名规范化规则对 3366 对影像/Mask 候选给出完全相同的配对结果；这只核对了命名规则。对全部 3366 个影像侧 PNG 解码后，以图像宽高及 RGBA 像素矩阵做精确比较，得到 3357 个不同矩阵和 **9 条重复额外记录**。其中一个完全相同的像素矩阵在 train 与 test 文件夹各出现一次；另有 8 条重复额外记录位于同一 split。该结果提示文件级跨 split 重复风险，但不提供患者键，也不能判定重复来自同一患者。

`R0-DATA-ACCESS-AUDIT` 仍为 **NOT COMPLETE**。2D 分割维持 `CONDITIONAL`；3D 分割、体积级 Radiomics 和 Cross-site 为 `NO-GO`；2D Radiomics 未评估。患者级无泄漏拆分、中心映射及公平性评估均未建立。

## 来源与版本

- 本地归档仍是 Figshare article `28639598` / file `53159216` 的 `CervicalCancerDataset.zip`，大小 `348,731,016` bytes。此次实算 SHA-256 `4efdfa6b6dbf4174a1b7ce2b0eb8878e739f0365829a89d57fdf5223c82817ec`、MD5 `303ae54703fdccc63302cb755aed792a`，均与 CMRL-01 记录一致；未重新下载。
- 作者仓库 `MaksimXing/FlexFair` 的 `main` HEAD 在本次查询时为 `f7da0fc0a9a4ad7c96f2c7b48699fc8cc151e320`，与 CMRL-00 记录的 HEAD 相同。对同一 ZIP 重新运行 `ZipFile.testzip()`，6732 个文件 CRC 检查通过。
- [Nature Communications 论文](https://www.nature.com/articles/s41467-025-58549-0)报告 678 名患者、四中心及中心患者数 89/65/278/246。这些是作者研究队列口径，不是 ZIP 中已核实的患者或中心清单。

本次只读核对的公开代码版本与位置：

| 作者代码/说明 | 可观察到的约定 |
|---|---|
| [DataNewZhongda.py](https://github.com/MaksimXing/FlexFair/blob/f7da0fc0a9a4ad7c96f2c7b48699fc8cc151e320/Code/F_Polyp_and_Cervical_Cancer/src/FedBasicFunc/Data/DataNewZhongda.py) | 训练加载器枚举 `Private/train/zhongda/`，排除 basename 中含字面子串 `label` 的名称，并以 `name[:-4] + '_label.png'` 同目录找 Mask。 |
| [DataShengfuyou.py](https://github.com/MaksimXing/FlexFair/blob/f7da0fc0a9a4ad7c96f2c7b48699fc8cc151e320/Code/F_Polyp_and_Cervical_Cancer/src/FedBasicFunc/Data/DataShengfuyou.py) | 训练路径 `Private/train/shengfuyou/`，采用相同命名规则。 |
| [DataNewZhongzhong.py](https://github.com/MaksimXing/FlexFair/blob/f7da0fc0a9a4ad7c96f2c7b48699fc8cc151e320/Code/F_Polyp_and_Cervical_Cancer/src/FedBasicFunc/Data/DataNewZhongzhong.py) | 训练路径 `Private/train/zhongzhong/`，采用相同命名规则。 |
| [DataNewZhongyi.py](https://github.com/MaksimXing/FlexFair/blob/f7da0fc0a9a4ad7c96f2c7b48699fc8cc151e320/Code/F_Polyp_and_Cervical_Cancer/src/FedBasicFunc/Data/DataNewZhongyi.py) | 训练路径 `Private/train/new_zhongyi/`，采用相同命名规则。 |
| [FedTestData.py](https://github.com/MaksimXing/FlexFair/blob/f7da0fc0a9a4ad7c96f2c7b48699fc8cc151e320/Code/F_Polyp_and_Cervical_Cancer/src/FedBasicFunc/FedTestData.py) | 测试加载器将对应四组路径放在 `Private/test/<group>/`，用相同 `_label.png` 后缀读取 Mask。 |
| [仓库 README](https://github.com/MaksimXing/FlexFair/blob/f7da0fc0a9a4ad7c96f2c7b48699fc8cc151e320/README.md) 与 [宫颈癌/息肉子项目 README](https://github.com/MaksimXing/FlexFair/blob/f7da0fc0a9a4ad7c96f2c7b48699fc8cc151e320/Code/F_Polyp_and_Cervical_Cancer/readme.md) | 根 README 把 Figshare DOI 写为 `28636133`，并提及 Google Drive 中的 `train.zip`、`test.zip`；子项目 README 也要求使用这两个 ZIP。 |

宫颈癌/息肉子项目 README 还说明，代码中用 `Private` 作为宫颈癌数据路径标签、`Public_5` 作为息肉数据路径标签。它是作者代码的任务目录命名，不是临床中心、患者身份或数据访问权限的证明。论文链接至 Figshare `28639598`，而仓库根 README 中另一个 ID `28636133` 在 CMRL-00 的独立查询为 HTTP 404；此处不推断两个 ID 的版本关系。

## ZIP 目录与作者分组对照

| ZIP 中观察到的 split | 影像侧 PNG | Mask 命名候选 | 同目录命名配对 | 作者四组目录归属 |
|---|---:|---:|---:|---|
| train | 2,420 | 2,420 | 2,420 | 未映射；四组代码目录均为 0 |
| test | 946 | 946 | 946 | 未映射；四组代码目录均为 0 |
| **合计** | **3,366** | **3,366** | **3,366** | **无可核验的中心键** |

ZIP 共 6732 个 PNG 和 11 个目录项；目录项中没有 `Private` 或四个作者组代号。归档中没有原作者 `Private/train/<group>/` 和 `Private/test/<group>/` 所需的文件路径或目录项；按作者代码的严格目录约定，两种 loader scope 都未命中任何文件。归档有 train/test 目录，但没有四个作者组代号。故可以报告文件处于归档中的 train 或 test 目录，不能说这就是患者级拆分、中心留出或作者原训练包的等价版本。

论文报告的 678 人和四组患者数与文件数口径不同，无法与 3366 个影像候选建立映射。数据登记中先前记录的 `1383/1332/323/328` 合计也是 3366；其来源口径此前未被独立复核，本次也未找到可将这些数值关联到 ZIP 路径或患者的证据。总数相等不验证各组对应关系。

## 配对复核

- 作者规则：3366 个非 `label` PNG 候选；3366 个含 `label` 的 PNG 候选；同目录后缀规则成功配对 3366 对，无孤立候选。
- CMRL-01 规范化规则：3366 个影像侧候选、3366 个 Mask 候选、3366 个唯一键配对，无歧义键或孤立候选。
- 独立交叉比较：3366 对成员完全一致；作者规则独有 0 对，规范化规则独有 0 对。
- 这次对全包文件名应用作者的 basename 规则来核对命名一致性；由于 ZIP 缺少作者 loader 所需的 `Private/train|test/<group>/` 目录，不能据此声称原作者 loader 可以直接从这个 ZIP 实例化出相同数据集。
- 复核范围覆盖全部 6732 个 PNG 的目录名与文件名；此次没有解码全部 Mask。全包 CRC 通过，CMRL-01 曾解码一对 640×640 灰度 PNG 并确认尺寸一致。文件名配对不证明 Mask 的临床语义、全包像素解码质量或医学空间配准。

## 身份与重复影像证据

| 证据问题 | 结果与等级 |
|---|---|
| 作者代码是否读取 patient ID | **UNKNOWN / 未见**。四个 loader 按目录枚举文件名并逐文件读入，没有解析患者键。 |
| ZIP 是否含可信 patient/site manifest 或 split 映射 | **UNKNOWN / 未建立**。本次目录名中作者四组代号均未出现；患者/中心关键词文件名线索计数为 0；没有读取或输出任何病例名。 |
| train/test 是否患者级无泄漏 | **UNKNOWN**。代码路径显示 train/test 目录，不表示按患者拆分；无可复核患者 ID 或 split 清单。 |
| 精确重复影像 | **FILE-INSPECTED**。全体 3366 个影像侧 PNG 解码成功；按宽高及 RGBA 解码像素比较得 3357 个不同矩阵，9 条重复额外记录。 |
| train/test 之间的完全重复 | **FILE-INSPECTED，风险信号**。一个不同像素矩阵在 train 与 test 各出现一次，形成 1 个跨目录完全重复配对。此为图像级观察，不证明患者身份。 |
| 患者级无重复或无泄漏 | **无法证明**。没有完全相同像素也不能排除同一患者的不同切片或重采样图像跨 split。 |

像素摘要、逐图哈希和路径均只在本地进程内使用，不进入 JSON、报告、终端汇总或 Git。JSON 仅保存聚合数。该重复发现使当前 test 文件夹不适合作为未经复核的独立患者测试集；后续如何处理须由 Main 在身份键可用性及任务定义下决定。本任务不重切分、不训练，也不把图像去重冒充患者去重。

## 数据准入与研究边界

- **2D segmentation：`CONDITIONAL`**。文件级候选配对成立，但四中心映射、患者 ID/拆分、Mask 语义和跨 split 重复处理尚未通过 Main 审查。
- **3D segmentation：`NO-GO`**。归档为二维 PNG，无可核验体积空间元数据。
- **Volumetric Radiomics：`NO-GO`；2D Radiomics：未评估、未准入。**
- **Cross-site 与公平性：`NO-GO`**。没有病例到可信临床中心的映射，也无法验证每中心的患者分组或中心留出。
- **Patient-wise Dice、外部验证与患者级泛化结论：不准入**，直至可信 patient ID 和患者级 split 证据可复核。
- 本任务没有下载任何新数据，没有执行作者模型或其他训练，没有编写分割/Radiomics 教学核心，没有读取外部独立 Plan 存储目录。

## 复现与隐私

从仓库根目录、在原始 ZIP 已按授权存在于被忽略的 `data/` 时运行：

```powershell
python -X utf8 scripts/r0/audit_flexfair_site_structure.py
```

脚本仅向 `evidence/r0/flexfair_site_mapping_audit.json` 写入脱敏聚合证据；会校验全包 SHA-256/官方 MD5、CRC，解析目录/文件名配对，并解码全部影像侧 PNG 计算精确像素重复计数。逐图路径、哈希与像素均不写入文件或终端。需本机已有 Python 与 Pillow；脚本不下载、不解压保存图像、不修改 ZIP。

**隐私检查：** ZIP 和 PNG 继续位于 `.gitignore` 保护的 `data/`；JSON、脚本和报告不含原成员路径、病例名、逐例哈希、像素值、临床值或凭据。Plan 没有复制入仓库，项目根 `plans/` 不重建。

## Plan 目录治理结果

用户已删除项目根 `plans/`。本分支保留该删除并停止跟踪此前 Git 中的 CMRL-00 与 CMRL-01 两份 Plan；新增根级 `.gitignore` 保护规则，未重建目录、未改写 Git 历史，也未触碰仓库外 Plan。根 `AGENTS.md`、README 与教学/实验协议已统一为：Plan 由用户在仓库外管理并随任务提供；命名 `CMRL-Plan-NN-中文标题.md`；报告和 `TASK_RESULT` 使用 `CMRL-NN`；附件或指定路径失联时报告缺失并请用户重传，不自行恢复、重建或复制。

删除历史 Plan 仅使其不再出现在当前树；旧提交仍保留历史内容。CMRL-00/01 报告中的路径是当时执行依据的历史记录，不是当前可用 Plan 链接。
