# Mandatory descriptive project-local task tracking

**Apply to all 15 agents, including the Principal Engineering Director.** The default tracker is the project's `docs/sdlc/state.db` (SQLite). The CLI maintains `docs/sdlc/TASKS.md` as its regenerated, read-only human-friendly view. Never use Jira, GitHub Issues, remote project boards or their connectors; never create competing trackers. A pre-existing local JSON template is legacy documentation, not a second live tracker.

## Project structure and first-run safety

- `docs/sdlc/state.db` — only authoritative task/dependency/progress state.
- `docs/sdlc/state.db.manifest.json` — project identity/recovery marker; preserve across backups.
- `docs/sdlc/TASKS.md` — generated readable status, task descriptions, detailed progress, next steps and recent event history; never edit directly.
- `docs/sdlc/backups/*.db` — optional, explicit SQLite snapshots; protect separately from working copy.
- **Git cleanliness:** The gate runner requires a clean committed source revision. Keep mutable `state.db`, WAL sidecars and generated `TASKS.md` out of the Git worktree index (e.g., reviewed `.gitignore` rules) and preserve verified external backups. Do not silently ignore tracker files if doing so would lose the only durable copy. If they are tracked and updated after a gate run, that receipt becomes stale; checkpoint/reconcile state and rerun against the final code revision.
- Never include raw secrets or private keys in tracker descriptions. Do not treat project-local DB event hashes as security-proof against agents with filesystem write permissions.

Before any task: run `resume`/`show` and inspect existing records. If `state.db` is absent, the CLI **fails closed**. For a verified new project with no prior manifest/report, the Orchestrator may run `init` once, then create descriptive task records. If the manifest or prior report exists but DB is missing, STOP and recover from a verified backup; never create an empty replacement or assert tasks are complete. If both database and manifest were lost, absence alone does not prove the project is new: consult repository history, backups and user before starting new state. `restore --from` accepts only a consistent, matching project backup when the manifest survives. Never silently overwrite an existing database. Reconcile recovered task evidence with Git before resuming.

## Required description and progress

Every newly created task must include a stable local ID, meaningful title, **problem/context description**, **expected observable outcome**, **narrative acceptance criteria plus requirement IDs**, owner, state, risk/priority/type and next action. Capture approach, completed work, current findings, remaining work, decisions/trade-offs, verification, dependencies, blockers/unblock details, Git revision, evidence/ref and reviewer as they become known. Do not fill blank fields with imaginary evidence.

Use `add` to create work and `update` with `--expected-version` for meaningful implementation progress: `--plan`, `--progress`, `--completed`, `--remaining`, `--decisions`, `--verification`, accompanied by a factual `--note`. Use `transition` to change active/intermediate state, **never to mark `Done`**. After a task reaches `Verified`, use `scripts/verify_and_close.py` (one guarded transaction with unified acceptance/Git/receipt decision). Use `amend` for changed acceptance scope (which invalidates old proof), and `enrich` only to populate missing descriptions on migrated legacy tasks. No noisy per-command updates. The task must describe *what changed, why it matters, what is left and who acts next*, not just a bare status.

## Ownership, verification and session recovery

The Orchestrator creates and reconciles all tasks, including architecture/integration/release responsibilities owned by itself. Subagents read their assignments and return structured deltas with task ID, observed progress, blockers, referenced evidence and next action; coordinate writes, never overwrite another role's state. Completion requires source revision, relevant evidence and required independent reviewer/approval as determined by the state store. For executable code-completion claims store `receipt-sha256:<exact-receipt-file-SHA256>` as the `--evidence` reference in each Verified/Done task; the same receipt must back required command gates in the root/leaf assurance ledgers, and each Done task must name the exact Git HEAD. The Orchestrator uses **`scripts/verify_and_close.py` for each task closure** and `scripts/completion_decision.py` for a read-only final cross-check. The target root ledger `work_item` must match the task ID for a task-scoped closure, even if unrelated tasks remain active. `Done` means locally closed to the declared evidence level, not automatically deployed or independently authenticated. Local `audit` remains a helpful **structural preflight**, not final proof. See `references/operating-modes.md` for proportional documentation and review.

Use small tasks with proportionate detail; do not split trivial work into empty substeps. On handoff/context compaction, `resume`, inspect the generated readable tracker, check the actual repository revision, and continue from the recorded next action. Do not treat `Done` as deployed unless actual release proof exists and release was in scope. Every persistent mutation automatically refreshes the Markdown view; a failure to generate the view is a report-generation error, not loss of the committed state.

## CLI example

```bash
S=/path/to/engihelm/scripts/state_store.py
python "$S" --db docs/sdlc/state.db init     # new projects only
python "$S" --db docs/sdlc/state.db add --id TASK-1 --title 'Fix login' --owner backend-engineer --actor sdlc-orchestrator --acceptance AC-1,AC-2 --description 'Inactive accounts can access private pages' --outcome 'Every inactive account is rejected' --acceptance-details 'Regression tests for inactive, missing and active accounts pass' --plan 'Reuse existing auth middleware' --next-action 'Reproduce and write failing tests'
python "$S" --db docs/sdlc/state.db update --id TASK-1 --expected-version 1 --actor backend-engineer --note 'Root cause reproduced' --progress 'JWT-only validation confirmed' --completed 'Created failing regression case' --remaining 'Add status check and verify'
python "$S" --db docs/sdlc/state.db resume
python "$S" --db docs/sdlc/state.db backup --output docs/sdlc/backups/state-001.db
python "$S" --db docs/sdlc/state.db audit
```

If `state.db` is unexpectedly missing, use `restore --from docs/sdlc/backups/state-001.db` only after checking the backup and project marker. Old databases require an explicit `migrate` after an external backup, followed by `enrich` for any legacy record missing descriptive fields.
