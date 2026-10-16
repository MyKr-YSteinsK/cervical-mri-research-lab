# Cervical MRI Research Lab

**Project ID:** `Cervical-MRI-Research-Lab` (`CMRL`)

This repository supports a staged, reproducible research project on cervical cancer MRI. It is a new project, separate from the earlier six-paper reading course.

## Current research state

The only active stage is `R0-DATA-ACCESS-AUDIT`. Candidate datasets have not passed file-level image/mask inspection. CMRL-00 downloaded the public TCIA clinical workbook into ignored local storage and profiled its schema and missingness; it did not validate clinical endpoints or accept training labels. No patient MRI, segmentation, model run, or local imaging environment is represented as validated here. See the [CMRL-00 audit report](reports/r0/CMRL-00-三候选数据准入审计.md), [current research state](docs/project/08-RESEARCH_STATE.md), and [staged research plan](docs/project/03-STAGED_RESEARCH_PLAN.md) before proposing experiments.

## Project contracts

- [Project brief](docs/project/01-PROJECT_BRIEF.md)
- [Dataset evidence register](docs/project/02-DATASET_EVIDENCE_REGISTER.md)
- [Staged research plan](docs/project/03-STAGED_RESEARCH_PLAN.md)
- [GPT tutoring and experiment protocol](docs/project/04-GPT_TUTORING_AND_EXPERIMENT_PROTOCOL.md)
- [Six papers technical bridge](docs/project/05-SIX_PAPERS_TECHNICAL_BRIDGE.md)
- [R0 execution runbook](docs/project/06-R0_EXECUTION_RUNBOOK.md)
- [Sources and open questions](docs/project/07-SOURCES_AND_OPEN_QUESTIONS.md)
- [Research state](docs/project/08-RESEARCH_STATE.md)
- [CMRL-00 bootstrap and data-access audit Plan](plans/CMRL-00-科研仓库初始化与候选数据准入审计.md)
- [Seed SHA-256 manifest](docs/project/SEED_SHA256.md)

## Data and privacy

Patient-level images, masks, clinical spreadsheets, identifiers, access credentials, and restricted files stay outside Git. Local `data/`, `.local/`, and downloaded files are ignored. Only public source metadata and reviewed aggregate summaries may be committed, subject to source terms. A public download link does not establish redistribution permission or image/mask validity.

## Teaching and execution roles

The user learns, writes, and runs the medical-imaging processing, segmentation, radiomics, training, and interpretability core. ChatGPT Main owns research decisions and evidence review. Codex may perform only the support tasks explicitly authorized by the active Plan. The CMRL-00 Plan specifically authorizes repository bootstrap and bounded checks of public-source availability, public metadata, non-sensitive file inventories, and evidence reports; it does not authorize implementation or execution of the scientific core.

## Reproduction and handoff

Start from the active Plan and use its exact commands, source URLs, download limits, and acceptance gates. CMRL-00 keeps its audit script, safe evidence, report, and `TASK_RESULT` under `scripts/r0/`, `evidence/r0/`, and `reports/r0/`. Work is delivered on the Plan-authorized branch. Push does not mean merge; Main reviews the evidence and decides whether to accept it.

To reproduce the CMRL-00 aggregate audit from the repository root, use Python with `openpyxl` for the local workbook profile:

```powershell
python -X utf8 scripts/r0/audit_public_sources.py
python -X utf8 scripts/r0/inspect_clinical_xlsx.py data/clinical/TCIA_CCTH_Patient-data_02.06.23.xlsx --output evidence/r0/tcia_clinical_profile.json
```

The first command makes bounded public metadata requests and does not download dataset archives. The second requires the TCIA workbook to be present locally; it emits aggregate field counts only. Keep the workbook under ignored `data/` and do not stage it.

The startup ZIP was supplied as input and is not itself a repository artifact. Its eight seed documents were copied unchanged; their SHA-256 values are recorded in `docs/project/SEED_SHA256.md`.
