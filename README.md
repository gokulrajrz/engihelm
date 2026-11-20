# EngiHelm — AI Engineering Orchestration & Verified Delivery

**Release:** 1.0.0 (2026-11-20). See `RELEASE.json`, `CHANGELOG.md`, and `LICENSE`. The bundled license notice is private/no public redistribution grant; obtain the rights holder's decision before public publication.

A **runtime-independent Agent Skill** for Agile, evidence-led software delivery. The main persona is a **Principal Engineering Director & Agile Delivery Leader** coordinating 14 expert specialist roles from discovery to operations.

## One authoritative core

- `SKILL.md`: short, universal operating contract and entrypoint.
- `references/engineering-director.md`: principal-level leader persona and decision authority.
- `references/task-tracking.md`: non-optional, single-source task tracking for all agents including the director; ownership, blockers, handoffs, closure and recovery.
- `references/operating-modes.md`: proportionate small/standard/high-risk workflows to avoid unnecessary documentation, specialist fan-out or duplicate reviews while preserving evidence.
- `scripts/completion_decision.py`: unified read-only SQLite + acceptance ledger + signed/local executable-receipt decision for one Git revision; rejects unrelated evidence, uncovered acceptance and under-tiered work.
- `references/engineering-efficiency.md`: mandatory Ponytail-inspired simplicity discipline, reuse ladder, overengineering/underengineering review and anti-false-positive examples.
- `references/roles/*.md`: fourteen authoritative expert specialist charters.
- `references/orchestration.md`, `agile-operating-model.md`, `handoff-contract.md`, `quality-gates.md`, `incident-playbook.md`: cross-platform operating model.
- `assets/templates/*.md`: optional reusable output artifacts.

Every runtime follows the **same personas, handoffs and evidence standards**. Platform adapters only translate those charters into host-native agent formats.

## Non-optional completion assurance (all 15 personas)

Every one of the 14 specialist agents **and the Principal Engineering Director** must write observable acceptance gates before work, self-check its deliverables, and report exact failures/unverified gaps. The Orchestrator also owns root completion assurance: independent parent re-verification (when the host genuinely supports it), integration gates, requirement amendments reconciliation, adversarial false-positive probes, and a final claim audit. This follows the strongest portable ideas in [Leonxlnx/unlazy](https://github.com/Leonxlnx/unlazy) without requiring its platform-specific hooks. See `references/completion-assurance.md` and the `assets/templates/assurance-*` Markdown templates and separate root/leaf JSON examples.

`python scripts/assurance_audit.py <ledger.json> --final` is an optional dependency-free structural audit of machine-readable gate ledgers. It **never executes CHECK commands** and cannot verify evidence authenticity, actual repository state, or requirements omitted from the input ledger. Use `--root --final` for the final orchestrator claim. PASS records must identify the current artifact revision and execution context. The installer includes this auditor in the installed Skill; run it using the installed Skill directory, not an assumed project-root `scripts/` directory. All check commands require host-mediated review/authorization. Small tasks keep 1-2 gates; high-risk work receives stricter independent verification and branch integration.

## Mandatory engineering efficiency and complexity challenge

For coding/design/infrastructure work, **every relevant specialist and the Orchestrator** must assess whether the change reuses existing code, avoids speculative features and needless dependencies, and fully covers affected callers, tests and safety requirements. The independent Code Reviewer must distinguish material overengineering (blocking, with specific evidence and viable simpler alternative) from personal style preferences (nonblocking). The Orchestrator separately owns the cross-team `G2S` / `ROOT-SIMP` check; Completion Assurance remains mandatory even when the implementation becomes smaller. See `references/engineering-efficiency.md` and `assets/templates/engineering-efficiency-review.md`.

Inspired by the [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) project (MIT license); these rules are independently drafted and **do not bundle or depend on** its platform-specific plugin, hooks or commands.

## Mandatory task tracking for all 15 personas

Every agent owns updates to its assigned task. The Orchestrator creates/reconciles the single authoritative tracker, including its own leadership/integration work. Use project-local `docs/sdlc/state.db` as the authoritative multi-session tracker and auto-generated `docs/sdlc/TASKS.md` as the human-readable view. Agents submit structured updates; the Orchestrator owns reconciliation. No Jira, GitHub Issues or external issue tracker integrations. The legacy JSON tracker template/auditor remains for importing/inspecting old local files only and must not become a second authority. `ROOT-TRACK` is mandatory for a root COMPLETE claim.

## Multi-agent capability modes

1. **Native multi-agent:** If the host exposes real child-agent invocation, delegate scoped work to installed specialist profiles; verify returned results before integration.
2. **Ad-hoc native delegation:** If the host only offers generic child sessions, include the relevant authoritative persona as an instruction in each scoped handoff.
3. **Single-agent fallback:** If no child-agent facility exists, run explicitly named sequential expert passes. Do **not** describe those passes as independent subagents or independent verification.

No platform can be made to spawn real agents merely by placing a `SKILL.md` file on disk. External tools, access, approvals, persistence and scheduling still depend on the host.

## Installation

The core is compatible with Agent Skills-compliant hosts. On Codex and Antigravity, the workspace-standard Skill directory is `.agents/skills/engihelm/`. Native subagent profiles are optional, **separate** from the Skill, and live in platform-specific locations.

Preview the installation of the core Skill and relevant optional profiles:

```bash
python scripts/install.py --runtime codex --project /path/to/repository
python scripts/install.py --runtime antigravity --project /path/to/repository
python scripts/install.py --runtime opencode --project /path/to/repository
python scripts/install.py --runtime skill-only --project /path/to/repository
```

Rerun with `--apply` to write files. The installer refuses to overwrite different files by default; pass `--overwrite` **only** after inspecting the preview, and it creates backups. **Legacy migration:** if an older `agile-sdlc-orchestrator` Skill or legacy primary profile is present, installation stops before writing until you inspect the migration plan and pass `--acknowledge-legacy` (or retire the old installation manually). Acknowledgement deliberately leaves the old files in place; delete/retire them only after verifying EngiHelm, never delete `docs/sdlc` project state. See `adapters/README.md` for runtime-specific facts and limitations.

If your host supports Skills but uses a different discovery path, copy the **core Skill directory** to that path and adapt the persona files manually. Do not copy platform-specific agent config into a different runtime.

## Example invocation

> Use engihelm to implement the requested feature. Inspect the code first, choose the smallest expert team, delegate safely if native agents exist, enforce independent checks when possible, and report only verified outcomes. Do not deploy to production without approval.

## Validate and extend — source distribution only

The commands below require the **complete source repository or extracted `skill.zip` source bundle**. A project installation made by `scripts/install.py` intentionally contains only runtime-facing files, not developer tools such as `build_adapters.py`, `validate_bundle.py` or test source. Run these commands from the full source directory, never from the installed Skill directory. Use Python 3.11 or newer.

```bash
python -m pip install -r requirements-dev.txt
python scripts/build_adapters.py --check
python scripts/validate_bundle.py
python scripts/assurance_audit.py assets/templates/assurance-ledger.json
python scripts/task_tracker_audit.py assets/templates/task-tracker.json
python -m unittest discover -s tests -v
```

In the extracted source bundle, edit `references/roles/*.md`, `references/engineering-director.md`, and `references/engineering-efficiency.md` as the canonical sources. Regenerate optional adapters with `python scripts/build_adapters.py`. The adapter generator does **not** edit any repository's working files. Human approval and real test evidence remain required wherever relevant.

## Added: formal implementation, recovery, budgeting, behavioral evaluation and executable gates

These are **working portable modules plus policies**, not automatic multi-agent runtime installation or production CI configuration.

| Improvement | Delivered in package | What is *not* automatic |
|---|---|---|
| Behavioral Skill tests | `assets/behavioral/scenarios.json`, `scripts/behavior_trials.py` for real adapter-driven paired runs, `scripts/behavior_eval.py` for observed rubric comparison | A Codex CLI trial adapter **is included**; an authenticated Codex CLI, approved model/credits, safe runtime and independent grading are **not provided**. Fixtures cannot prove agent compliance. |
| Formal implementation workflows | `references/implementation-methods.md`: appropriate RED/GREEN/REFACTOR, hypothesis-driven debugging, contract preflight, independent review/fix adjudication, branch finishing | Agents must load/follow policy; no magical editor hook for all runtimes |
| Durable orchestration | `scripts/state_store.py`: SQLite WAL, descriptive task fields, automatic Markdown view, versioned updates, explicit first-run/recovery behavior, verified backup/restore, audit, and local event chain | No external issue tracker integration or cryptographic tamper protection |
| Cost-aware delegation | `references/delegation-budget.md`, `scripts/delegation_plan.py`, sample budget/capability registry; balanced risk/context/cost assignments | No real model provisioning, price discovery or automatic invocation |
| Independent enforcement | `scripts/gate_runner.py` pinned executable check policy, clean Git revision check, actual process results, optional HMAC receipts and verifier; CI example | No sandbox/security principal creation, signer isolation, repository rulesets or production approvals configured |

### Required setup to use executable gates

Copy and **review** `assets/templates/approved-gates.example.json` to a project-maintained gate policy and replace the example commands with real project checks. A gate policy can execute arbitrary code with the runner's privileges: run only within an approved isolated runner with least privilege and explicit authorization.

```bash
# Preview the SHA-256 of a reviewed policy (bind this digest in trusted configuration).
python scripts/gate_runner.py digest --policy /path/to/reviewed-gates.json

# Explicitly run the pinned policy against a committed, clean Git repository.
python scripts/gate_runner.py run \
  --repo /path/to/repository \
  --policy /path/to/reviewed-gates.json \
  --policy-sha256 ACTUAL_REVIEWED_SHA256 \
  --receipt /secure/reports/run-001.json --allow-run
```

An unsigned local receipt **never** qualifies for independently authenticated completion. The optional HMAC mode requires a key inaccessible to agents *and* execution isolation provided by a separately controlled service. The `--assert-executor-isolation` flag records an operator assertion and does **not** establish that isolation; a key file merely placed outside the repository can still be read by untrusted code running as the same OS user. Signed receipt verification also checks the current Git revision. See `references/enforcement.md`.

To introduce CI protection, review `assets/ci/github-required-check.example.yml`, install a protected reviewed policy, configure admin-controlled policy SHA, protected checks, protected workflows/review rules, production environment approvals, and CI execution isolation. **The template by itself does not block merges or releases.**

### Persistent state and delegation

```bash
python scripts/state_store.py --db /path/to/project/docs/sdlc/state.db init
python scripts/state_store.py --db /path/to/project/docs/sdlc/state.db resume
python scripts/delegation_plan.py assets/templates/delegation-budget.example.json
```

Use `docs/sdlc/state.db` as the authoritative tracker for writable project work. The auto-generated `docs/sdlc/TASKS.md` is only a view. Do not use Jira/GitHub Issues or other external issue boards. The JSON template/auditor is a legacy local format, not a second source of truth. The example model names/prices are fictional placeholders.

### Evaluating actual agent behavior

```bash
python scripts/behavior_trials.py \
  --manifest assets/behavioral/scenarios.json \
  --runner /path/to/your-real-agent-adapter \
  --skill-root . --output-dir /tmp/paired-trials
python scripts/behavior_eval.py \
  --manifest assets/behavioral/scenarios.json \
  --baseline /tmp/paired-trials/baseline.json \
  --skill /tmp/paired-trials/skill.json
```

The external adapter must launch isolated baseline/Skill sessions against the **same repo revision** and record raw trace evidence, test runs, and results. This package includes evaluator unit tests and a simulated-adapter contract test; it does **not** claim to have executed real Codex, Antigravity or OpenCode agent sessions.

## Descriptive tracker and missing-DB behavior

`docs/sdlc/state.db` is the **only authoritative tracker** for ongoing project work. On `init` and every task mutation, the CLI regenerates `docs/sdlc/TASKS.md`: a readable backlog plus per-task problem, goal, acceptance, implementation notes, progress, completed/remaining work, decisions, blockers, evidence and recent activity. It is a view, not a competing task database. External issue services (including Jira and GitHub Issues) are **out of scope**.

If the DB is missing, `resume`, `audit` and task operations fail. For a **new** project with no prior artifacts, use `init`. When a manifest or prior Markdown report survives, `init` refuses to create an empty replacement. Use `backup --output` and `restore --from` for explicit verified snapshots; there is no automatic recovery of deleted work. Refer to `references/task-tracking.md` for safe CLI examples.

## One final code-completion decision (new)

After a reviewed gate policy is pinned, run the approved executable checks through `scripts/gate_runner.py` on a clean committed revision. Set the SQLite tracker task evidence to `receipt-sha256:<sha256-of-exact-receipt-file>`, use the same digest in required command-ledger parent checks, and bind those checks to mandatory policy IDs via `execution_gate_id`. Then run:

```bash
python scripts/completion_decision.py --db docs/sdlc/state.db \
  --root-ledger docs/sdlc/assurance-root.json --repo . \
  --expected-commit "$(git rev-parse HEAD)" \
  --policy /trusted/approved-gates.json --policy-sha256 "$APPROVED_POLICY_SHA256" \
  --receipt /trusted/receipts/gates.json --mode local
```

`--mode lightweight` is available only for small tasks when an advisory declared-evidence result is sufficient; omit `--policy`, `--policy-sha256` and `--receipt` and report the status as `LIGHTWEIGHT_DECLARED`, not verified execution. `LOCAL_CONSISTENT` is a local-only consistency decision, not a trusted authorization. `--mode signed --key-file` checks a separately issued cryptographic receipt; a genuinely isolated signer, real review/approvals and protected CI/merge policy must still be configured outside this Skill. For high-risk tasks the local-only mode refuses completion. The tool cannot independently determine whether the recorded risk tier was understated; reviewers must inspect actual scope and elevate sensitive work. Do not Git-track mutable SQLite/WAL/report files unless the exact final revision workflow is deliberately designed for them; maintain protected backups so local state is not lost. No Jira or GitHub Issues support.

### Guarded, task-scoped coding closure

`state_store.py transition --state Done` is blocked. From a `Verified` task, the Director uses `scripts/verify_and_close.py` with `--task-id`, `--expected-version`, a task-scoped COMPLETE root ledger, Git commit and approved verification receipt. The command correlates evidence and writes the completed state within one SQLite transaction, rejecting stale/mismatched inputs. This is **local application enforcement**, not an OS/CI permission boundary. Project-wide read-only audit remains `completion_decision.py`.

### Real coding-agent behavior trials

A Codex CLI adapter is now available in `scripts/codex_trial_adapter.py`, together with seven controlled Git fixtures. It can run real baseline-versus-Skill sessions when the user provides an installed, authenticated Codex CLI, pins a model (`SDLC_CODEX_MODEL`) and explicitly opts in (`SDLC_ALLOW_REAL_AGENT_TRIALS=1`). It captures traces and diffs but does not self-assign passing grades or execute agent-modified tests outside a verifier sandbox. An offline adapter contract test cannot substitute for a real agent trial. See `references/behavioral-evaluation.md`.

## Renaming from the previous Agile SDLC Orchestrator edition

The new Skill identifier and installation directory are **`engihelm`**. Existing
installations named `agile-sdlc-orchestrator` are **detected before install** and never deleted or overwritten
by the installer. `--apply` fails closed until the user removes the old installation safely or supplies `--acknowledge-legacy` to permit temporary coexistence. To avoid ambiguous Skill discovery, back up and manually retire
the obsolete installed Skill directory **after** confirming EngiHelm works. For
Antigravity and OpenCode, similarly retire obsolete native main profiles named
`sdlc-orchestrator.md` after reviewing local customizations. Never remove project
`docs/sdlc/state.db`, its manifest, `TASKS.md`, or backups during migration; those
are project data, not the Skill installation.

The internal event/ledger actor identifier **`sdlc-orchestrator` remains stable**
for compatibility with previously persisted tracker and assurance records. It is
not the public Skill name, package name, or native main-profile filename.
