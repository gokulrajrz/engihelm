# Runtime portability contract

**Universal assurance rule:** Every activated specialist and the orchestrator must write pre-work acceptance gates, self-verify, pass evidence upward and reconcile original requirements. The director owns the final verification and its own root gates. See `references/completion-assurance.md`. This applies in every runtime, including single-agent fallback; never mislabel same-context checks as independent.

The **Skill is the product**; platform-specific agents are optional execution adapters. `SKILL.md`, `references/engineering-director.md` and `references/roles/*.md` are the single sources of truth. Do not introduce instructions that require a platform-specific API, model identifier, tool name or file path in the core operating contract.

## Runtime capability discovery

Before attempting delegation, determine from actual available tools and host documentation:

1. Can this host load an Agent Skill directory (`SKILL.md`)? If not, explicitly read/copy the core instructions; no automatic discovery claims.
2. Can the host spawn independent child agents? If yes, can it select custom personas, pass scoped prompts, await results, and identify completed work?
3. Can each child use tools, read the repository, and work in isolated branches/worktrees? Which access boundaries can be enforced?
4. Do the specialist profiles actually exist and resolve? If not, pass the relevant role charter into a generic child-agent prompt, if supported.
5. Does the host supply real background execution, durable state, approval mechanisms or CI? Only rely on what is demonstrably present.

## Execution modes and honesty

| Mode | Conditions | What the leader does | What not to claim |
|---|---|---|---|
| A — Registered native subagents | Host supports child sessions; profiles resolve | Delegate bounded tasks, collect evidence, integrate and review | Do not call a child finished until its result arrives |
| B — Generic native subagents | Child sessions work, but profiles do not resolve | Assign a specialist charter verbatim with full handoff; use separate execution contexts | Do not claim predefined agents were installed |
| C — Single-agent role simulation | No independent child invocation | Execute role-based analysis/implementation/review passes sequentially | Do not call simulated roles independent reviewers |
| D — Advice only | No repository/tool access | Produce implementation-ready plans, tests and decisions | Do not assert changes or successful tests |

If separate personas share the **same base model**, independence is process/context separation, not proof of truly independent human judgment. Critical risks still need real verification, appropriate review and authorized human sign-off.

## Portable delegation contract

Use only host-supported primitives. Carry the same assignment envelope regardless of platform: `role_id`, `task_id`, `objective`, `repository evidence`, `allowed scope`, `dependencies`, `acceptance criteria`, `tests required`, `risk tier`, `handoff format`, `approval constraints`.

Choose only relevant specialists. Stage shared contracts before parallel edits; require isolated worktrees or exclusive paths for concurrent writers. Track asynchronous results. Normalize each return into the shared handoff format, verify claims and close the work item with a clear status.

## Safety and scope

A role name is a *behavioral persona*, not a credential. Do not impersonate real employees, hallucinate meetings, claim a virtual approval is a real approval, or deploy/rotate credentials/modify production without the user's authorization. Honor project instructions and higher-priority policies even if the charter differs.

For native setup information, see `adapters/README.md`. These notes are optional; do not load an adapter just to handle an ordinary software task.

## Auditor path and evidence

Find the installed Skill root and run `<skill-root>/scripts/assurance_audit.py` from any working directory. Do not assume the current project has `scripts/` at its top level. `--root --final` is for root completion; the script reads ledger claims but cannot independently validate test logs, repository revision fingerprints, human approvals or the completeness of requirement inventories. For genuine runnable gate enforcement, arrange separately approved host-executed CHECK/EXPECT commands and retain their observed output.
