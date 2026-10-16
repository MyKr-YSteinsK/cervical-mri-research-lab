# CMRL Repository Instructions

## Project source of truth

- This repository is `Cervical-MRI-Research-Lab` (`CMRL`), a cervical-cancer MRI research project. It is independent from the earlier six-paper reading course.
- Before acting, read the active Plan in `plans/` and the relevant contracts in `docs/project/01-PROJECT_BRIEF.md` through `08-RESEARCH_STATE.md`. Preserve their current revision, decisions, task numbering, and state.
- Task IDs use `CMRL-NN-中文任务标题.md`, sequential across this repository. Research stages R0–R8 are separate from task numbering.
- Only describe work as verified when actual source, file, command, or runtime evidence supports it. Keep `SOURCE-VERIFIED`, `FILE-INSPECTED`, `RESTRICTED`, `NOT_RUN`, and `UNAVAILABLE` distinct.

## Teaching and Codex authority

- The user learns and writes the scientific core: MRI processing, segmentation, radiomics, model training, and interpretability. Codex may explain, review, or diagnose those tasks in the small steps agreed by the user.
- The CMRL-00 Plan grants a task-specific exception for repository bootstrap and automated checks of public-source availability, public metadata, non-sensitive file inventories, and evidence reports. It does not authorize Codex to implement or run the scientific core. Any later expansion requires a new explicit user authorization and applicable Plan.
- Do not send access requests, provide institutional identity, accept unknown terms, bypass passwords, or access data requiring approval. Follow each source's license and access terms.

## Data safety

- Never commit raw MRI, RTSTRUCT, patient-level clinical data, identity keys, passwords, tokens, cookies, or authenticated download URLs.
- Keep local data and temporary downloads under ignored `data/` or `.local/` paths. Before every commit, review the staged file list and inspect any metadata or derived output for patient-level values and credentials.
- Public metadata is not proof that archive contents, patient mapping, masks, labels, or image geometry have been validated. Do not infer response labels, tumor masks, or patient/site keys.
- Do not download an entire dataset unless the active Plan explicitly authorizes it and its size is within the Plan's budget.

## Git and delivery

- Follow the active Plan for base branch, working branch, authorized remote, commit, push, and review. Never force-push, rewrite pushed history, or merge a review branch without explicit authority.
- Keep bootstrap, research audit, and later scientific implementation changes scoped and reviewable. Put Plans in `plans/`, durable reports and handoffs in the paths named by the Plan, and public safe evidence in `evidence/`.
- Do not create empty `src/`, `models/`, or framework scaffolding before a Plan requires it. Do not claim R0 completion, evidence acceptance, or stage advancement unless the appropriate owner has made that decision.
