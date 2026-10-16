# CMRL-03｜TCIA 最小 MR 与 RTSTRUCT 准入审计

- **审计日期：** 2026-10-16（UTC）
- **任务 / Plan：** `CMRL-03` / 外部 `CMRL-Plan-03-TCIA单病例MR与RTSTRUCT可获得性审计.md` r1
- **研究阶段：** `R0-DATA-ACCESS-AUDIT`；本次不推进 R1，也不决定数据集最终准入。
- **状态：** `PARTIAL`；来源与许可核验完成，受试者级检索和文件核验被当前网络通道阻断。

## 结论

TCIA 官方页面和 IDC 官方页面均确认 `CC-Tumor-Heterogeneity` 是包含 MR、RTSTRUCT、REG、PT、CT 的公开影像 Collection。TCIA 当前页面标为 Version 2，发布统计为 23 subjects、171 studies、821 series、131,556 images，影像许可为 CC BY 4.0 且要求引用数据集。以上只证明 Collection 级发布信息，不证明任一受试者的 MR 与 RTSTRUCT 存在引用关系。

本次尝试 TCIA REST `getSeries` 和 IDC REST v3 元数据通道时，命令行客户端没有得到可用 HTTP 响应；浏览器通道也无法建立连接。故未识别单个受试者、MR 序列或 RTSTRUCT，也未下载任何 DICOM。当前没有 MR/T2WI–RTSTRUCT 的同人、同 Study、同 Frame of Reference 或 SOP/Series 引用证据，均为 `UNKNOWN`。本次没有文件级检查，不能声称已有可供本地 DICOM 教学的真实样本。

`R0` 仍为 **NOT COMPLETE**。CMRL-03 不批准分割、Radiomics、模型或临床终点工作，也不将 Collection 同时出现 MR 与 RTSTRUCT 升格为配对证据。

## 来源、版本与访问条件

- [TCIA 官方 Collection 页面](https://www.cancerimagingarchive.net/collection/cc-tumor-heterogeneity/) 标记 Version 2（页面更新时间 2023-02-23）、DOI `10.7937/ERZ5-QZ59`、23 subjects、171 studies、821 series、131,556 images、28.39 GB；列出的模态为 MR、RTSTRUCT、REG、PT、CT，影像与临床 XLSX 均列 CC BY 4.0。此为发布元数据，不是本地文件核验。
- [IDC 官方 Collection 页面](https://portal.imaging.datacommons.cancer.gov/collections/cc_tumor_heterogeneity/) 也列出 23 subjects、MR、RTSTRUCT 及 Clinical supporting data，并链接同一 DOI。此为 Collection 级交叉核对。
- [TCIA REST API Usage Guide](https://wiki.cancerimagingarchive.net/pages/viewpage.action?navigatingVersions=true&pageId=70230690) 说明公开 Collection 元数据不再需要 API key，并列出 `getSeries`、`getSOPInstanceUIDs` 和单对象读取接口。可用于公开元数据查询的接口说明不等同于本机请求成功。
- [IDC REST API 文档](https://api.imaging.datacommons.cancer.gov/v3/docs) 列有公开的 v3 API、Collection/表元数据及只读 SQL 接口。当前运行版本未能从本机读取。

### 本机执行环境

- Python：`3.14.6`；`pydicom` 未安装。本次只需访问元数据，因此没有安装新依赖或医学影像科研环境。
- `D:` 卷预检可用空间：`149,419,892,736` bytes。
- 仓库忽略目录中已有 TCIA 临床工作簿；本次未打开、读取或修改该工作簿。
- 查询的是无需登录的公开端点；未使用账户、API key、Cookie 或其他凭据。

## 访问尝试与结果

| 通道 | 查询范围 | 观察结果 | HTTP / 正文 | 解释 |
|---|---|---|---|---|
| TCIA REST v4 `getSeries` | 公开 Collection 的 MR series 元数据 | Python `urllib` 在 8 秒超时后抛出 `TimeoutError` | 未取得 HTTP 状态；已读正文 0 bytes | API 当前对本执行环境无响应；不是零结果证据 |
| IDC REST v3 `/version` | API 版本探测 | Python `urllib` 抛出 TLS `SSLEOFError`；`curl.exe` 报 Schannel 握手失败 | Python 约 5.2 秒；curl HTTP 000、正文 0 bytes | HTTPS 握手在本机失败，无法核实 IDC 当前运行版本 |
| IDC REST 文档页 | 官方 API 文档 | 浏览器返回 `ERR_CONNECTION_CLOSED` | 约 10.8 秒；无 HTTP 状态、无响应正文 | 浏览器也无法连通 IDC API 主机 |
| TCIA PowerShell 探索性命令 | MR 与 RTSTRUCT series 元数据各一条子请求 | 执行超出 30 秒捕获边界，逐请求结果没有回传 | 超过 30 秒；HTTP 与正文长度未记录 | 仅作为未决尝试，不作为访问或零结果证据；因此累计元数据正文总字节数无法完全核算 |

CMRL-00 已记录一次更早的 TCIA `getSeries` 超时；其结果同样没有 HTTP 状态或正文，且不证明数据不可访问。本次没有对 TCIA 或 IDC 访问控制进行绕过，没有使用账户、凭据或受限数据端点。

## 单受试者链与文件级检查

| 核验项 | 结果 | 依据 / 限制 |
|---|---|---|
| 受试者级 MR series | `UNKNOWN` | Collection 页面只给出聚合元数据；series 查询未返回结果 |
| MR 是否为 T2WI | `UNKNOWN` | 未读到逐序列标签或 DICOM Header；不能凭 Collection 描述推断具体候选 |
| 受试者级 RTSTRUCT | `UNKNOWN` | 未返回逐序列元数据，也未取到 RTSTRUCT 文件 |
| MR 与 RTSTRUCT 同一受试者 | `UNKNOWN` | 没有可比较的受试者级映射 |
| 同一 Study | `UNKNOWN` | 没有 study/series 级结果 |
| 同一 Frame of Reference | `UNKNOWN` | 未读 DICOM Header |
| RTSTRUCT 引用 MR SOP Instance / Series | `UNKNOWN` | 未读 Structure Set 引用序列 |
| ROI 类别线索 | `UNKNOWN` | 无 RTSTRUCT Header 检查；不能判断 GTV、CTV、PTV、OAR 或原发肿瘤 ROI |
| 最小本地 MR / RTSTRUCT 输入 | `NO` | 本次新下载 MR DICOM 0 个、RTSTRUCT 0 个；既有临床工作簿不是影像输入 |

S2 的受试者身份与引用候选来源核对没有通过，故 Plan 的条件步骤 S3 未运行。没有进行批量下载、影像解码、可视化、重建、Contour 栅格化、配准、重采样、Radiomics 或模型工作。

### 下载预算与隐私

- 单文件上限：30,000,000 bytes；总响应正文上限：100,000,000 bytes。
- 本次新增 DICOM/RTSTRUCT 下载：0 个；已确认 DICOM 响应正文：0 bytes。
- 已完整捕获的失败请求未读到响应正文。另有一条 PowerShell 探索性命令包含 MR 与 RTSTRUCT 两条元数据子请求，但未能回传逐请求状态和正文长度，因此**累计元数据响应正文无法完全核算**；没有证据显示任何 DICOM 对象曾被请求或下载。为守住预算，本任务未继续发出对象下载请求。
- 仓库成果只记录 Collection 级事实、连接错误类别及布尔核验状态；不保存或输出受试者标识、Study/Series/SOP UID、原始 Header、逐例映射、实例路径、像素、Contour、临床行值或凭据。没有新的医学文件进入 Git。

## M1–M7 验收状态

| Gate | 状态 | 证据 |
|---|---|---|
| M1 Git / Contract | `PASS` | 外部 Plan 可读；私有仓库、干净工作区、PR 链和远端 SHA 已在执行前实查；新分支从 PR #3 最新远端 HEAD 派生；未创建 `plans/` |
| M2 Source | `PASS` | TCIA 官方 Collection、IDC Collection 与官方 API 文档均已核对；TCIA DOI、CC BY 4.0 和引用要求有官方来源支持；API 连接错误如实分类 |
| M3 Discovery | `BLOCKED` | TCIA 请求超时，IDC API HTTPS/TLS 连接失败；未取得单受试者的 MR/RTSTRUCT 元数据 |
| M4 Bounded File Check | `NOT_RUN` | S2 候选前置条件不满足；没有文件下载或 Header 检查；未尝试任何 DICOM 对象读取 |
| M5 Scientific Semantics | `NOT_RUN` | T2WI、时点、Frame of Reference、引用链和 ROI 意义均未知；没有将 RTSTRUCT 等同肿瘤 Mask 或临床标签 |
| M6 Privacy | `PASS` | 本次没有下载或提交患者级影像；脱敏输出经提交前路径与内容检查 |
| M7 Git / Delivery | `PENDING` | 在提交、Push 和 Draft PR #4 远端核验后回填至 TASK_RESULT 和最终回执；不合并、不改变 PR ready 状态 |

## D03 研究含义与下一边界

D03 维持 `SOURCE-VERIFIED / PUBLIC-METADATA / FILE-NOT-INSPECTED`，并增加“当前执行环境的受试者级查询不可用”说明；不能将其改判为无数据或资源不可访问。D01 FlexFair 仍只有 2D PNG/Mask 学习性输入，患者级无泄漏证据未建立；D02 CCMD 访问状态不变。

下一步若在可连通官方端点的环境重新执行，应先只读查询一个受试者候选，核验其 MR 与 RTSTRUCT 引用关系并记录逐例映射到被 Git 忽略的本地目录；只有确证候选、许可及单对象大小预算后，才可请求少量文件。公开证据仍只保留聚合计数和布尔关系。任何后续教学也应由用户亲自编写并运行 DICOM 读取代码。

## 主要复核来源

1. [TCIA CC-Tumor-Heterogeneity Collection](https://www.cancerimagingarchive.net/collection/cc-tumor-heterogeneity/)（DOI `10.7937/ERZ5-QZ59`）。
2. [IDC CC-Tumor-Heterogeneity Collection](https://portal.imaging.datacommons.cancer.gov/collections/cc_tumor_heterogeneity/)。
3. [TCIA REST API Usage Guide](https://wiki.cancerimagingarchive.net/pages/viewpage.action?navigatingVersions=true&pageId=70230690)。
4. [IDC REST API v3 文档](https://api.imaging.datacommons.cancer.gov/v3/docs)。

本报告仅回传本次 CMRL-03 r1 调查结果。是否接受某个数据集、是否进入 R1 或启动分割/Radiomics，由 Main 依据证据另行决定。
