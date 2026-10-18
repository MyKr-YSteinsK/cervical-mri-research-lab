# CMRL Repository Instructions

## Project source of truth

- This repository is `Cervical-MRI-Research-Lab` (`CMRL`), a cervical-cancer MRI research project. It is independent from the earlier six-paper reading course.
- Before acting, read the current Plan supplied by the user as an external Markdown attachment or at a user-designated path, together with the relevant project contracts and current research state. Preserve the Plan revision, decisions, scope, and state.
- Formal Plan files use the external filename `CMRL-Plan-NN-中文标题.md`. Task, report, and `TASK_RESULT` identity use `CMRL-NN`; research stages R0–R8 are separate from task numbering.
- Never store or copy a Plan, working draft, or reconstructed Plan into this repository. If the current Plan is not actually readable from the supplied attachment or path, report that it is missing and ask the user to provide it again; do not recover it from prior repository copies or history.
- Only describe work as verified when actual source, file, command, or runtime evidence supports it. Keep `SOURCE-VERIFIED`, `FILE-INSPECTED`, `RESTRICTED`, `NOT_RUN`, and `UNAVAILABLE` distinct.

## Teaching and Codex authority

- The user learns and writes the scientific core: MRI processing, segmentation, radiomics, model training, and interpretability. Codex may explain, review, or diagnose those tasks in the small steps agreed by the user.
- The historical CMRL-00 Plan granted a task-specific exception for repository bootstrap and bounded checks of public sources, metadata, non-sensitive file inventories, and evidence reports. It did not authorize Codex to implement or run the scientific core, and it does not grant authority to later tasks. Each current task follows its own user-supplied Plan and explicit scope.
- Do not send access requests, provide institutional identity, accept unknown terms, bypass passwords, or access data requiring approval. Follow each source's license and access terms.

## Data safety

- Never commit raw MRI, RTSTRUCT, patient-level clinical data, identity keys, passwords, tokens, cookies, or authenticated download URLs.
- Keep local data and temporary downloads under ignored `data/` or `.local/` paths. Before every commit, review the staged file list and inspect any metadata or derived output for patient-level values and credentials.
- Public metadata is not proof that archive contents, patient mapping, masks, labels, or image geometry have been validated. Do not infer response labels, tumor masks, or patient/site keys.
- Do not download an entire dataset unless the active Plan explicitly authorizes it and its size is within the Plan's budget.

## Git and delivery

- Follow the current user-supplied Plan for base branch, working branch, authorized remote, commit, push, and review. Never force-push, rewrite pushed history, or merge a review branch without explicit authority.
- Keep bootstrap, research audit, and later scientific implementation changes scoped and reviewable. Store durable reports and handoffs in the paths named by the Plan, and public safe evidence in `evidence/`. Plans remain outside the repository.
- Do not create empty `src/`, `models/`, or framework scaffolding before a Plan requires it. Do not claim R0 completion, evidence acceptance, or stage advancement unless the appropriate owner has made that decision.
