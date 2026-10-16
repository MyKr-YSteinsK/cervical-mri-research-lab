# Cervical MRI Research Lab

**Project ID:** `Cervical-MRI-Research-Lab` (`CMRL`)

This repository supports a staged, reproducible research project on cervical cancer MRI. It is a new project, separate from the earlier six-paper reading course.

## Current research state

The only active stage is `R0-DATA-ACCESS-AUDIT`. FlexFair's published PNG archive has been structurally audited and a sample image/mask pair decoded, but its author-code site directories do not map to the archive, patient/site identities remain unverified, and an exact image duplicate was found across its observed train/test folders. This does not establish a patient-wise split or validate mask semantics. CMRL-00 also profiled the public TCIA clinical workbook without validating endpoints or accepting training labels. No segmentation experiment, model run, or local imaging environment is represented as validated here. See the [CMRL-00 audit](reports/r0/CMRL-00-三候选数据准入审计.md), [CMRL-01 archive audit](reports/r0/CMRL-01-FlexFair文件级准入审计.md), [CMRL-02 grouping and identity audit](reports/r0/CMRL-02-FlexFair分组与身份线索复核.md), [current research state](docs/project/08-RESEARCH_STATE.md), and [staged research plan](docs/project/03-STAGED_RESEARCH_PLAN.md) before proposing experiments.

## Project contracts

- [Project brief](docs/project/01-PROJECT_BRIEF.md)
- [Dataset evidence register](docs/project/02-DATASET_EVIDENCE_REGISTER.md)
- [Staged research plan](docs/project/03-STAGED_RESEARCH_PLAN.md)
- [GPT tutoring and experiment protocol](docs/project/04-GPT_TUTORING_AND_EXPERIMENT_PROTOCOL.md)
- [Six papers technical bridge](docs/project/05-SIX_PAPERS_TECHNICAL_BRIDGE.md)
- [R0 execution runbook](docs/project/06-R0_EXECUTION_RUNBOOK.md)
- [Sources and open questions](docs/project/07-SOURCES_AND_OPEN_QUESTIONS.md)
- [Research state](docs/project/08-RESEARCH_STATE.md)
- [Seed SHA-256 manifest](docs/project/SEED_SHA256.md)

## Plans and task authority

The user manages formal Plans outside this repository and supplies the current Markdown Plan with each task. Plan files follow `CMRL-Plan-NN-中文标题.md`; reports and task results use `CMRL-NN`. This repository keeps the durable evidence, code, reports, and applicable long-term workflow rules, but no Plan files or Plan copies. If a supplied Plan is missing or unreadable, request that it be provided again instead of reconstructing it.

## Data and privacy

Patient-level images, masks, clinical spreadsheets, identifiers, access credentials, and restricted files stay outside Git. Local `data/`, `.local/`, and downloaded files are ignored. Only public source metadata and reviewed aggregate summaries may be committed, subject to source terms. A public download link does not establish redistribution permission or image/mask validity.

## Teaching and execution roles

The user learns, writes, and runs the medical-imaging processing, segmentation, radiomics, training, and interpretability core. ChatGPT Main owns research decisions and evidence review. Codex may perform only the support tasks explicitly authorized by the user's current external Plan. The CMRL-00 bootstrap and public-source exception was limited to that task; it does not authorize implementation or execution of the scientific core in later tasks.

## Reproduction and handoff

Start from the user-supplied external Plan and use its exact commands, source URLs, download limits, and acceptance gates. CMRL-00 through CMRL-02 keep their authorized audit scripts, safe evidence, reports, and `TASK_RESULT` under `scripts/r0/`, `evidence/r0/`, and `reports/r0/`. Work is delivered on the Plan-authorized branch. Push does not mean merge; Main reviews the evidence and decides whether to accept it.

To reproduce the CMRL-00 aggregate audit from the repository root, use Python with `openpyxl` for the local workbook profile:

```powershell
python -X utf8 scripts/r0/audit_public_sources.py
python -X utf8 scripts/r0/inspect_clinical_xlsx.py data/clinical/TCIA_CCTH_Patient-data_02.06.23.xlsx --output evidence/r0/tcia_clinical_profile.json
```

The first command makes bounded public metadata requests and does not download dataset archives. The second requires the TCIA workbook to be present locally; it emits aggregate field counts only. Keep the workbook under ignored `data/` and do not stage it.

The startup ZIP was supplied as input and is not itself a repository artifact. Its eight seed documents were copied unchanged; their SHA-256 values are recorded in `docs/project/SEED_SHA256.md`.
