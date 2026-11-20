# Orchestration protocol

**Universal task tracking:** All agents (including the director) must read/update or submit deltas to the one authoritative task tracker per `references/task-tracking.md`. The director must open task rows before dispatch, reconcile child deltas and verify closure against required gates. Never turn a child's self-reported success into `Done` automatically.

**Universal assurance:** Every participating agent, including the orchestrator, must follow `references/completion-assurance.md`; author acceptance gates before acting, self-verify before returning, and undergo parent review. Integration and final request reconciliation remain owned by the orchestrator.

**Engineering efficiency:** Apply `references/engineering-efficiency.md` to code, architecture, infrastructure and review. Demand an implementer simplicity self-check, an independent reviewer G2S challenge where applicable, and orchestrator ROOT-SIMP assessment without sacrificing completeness.

**Leadership operating standard:** Use `references/engineering-director.md` for principal-level engineering management, technical challenge, escalation and conflict reconciliation. Check specialist handoffs against each role charter's expert decision standard. No title alone establishes quality.

## Risk tier and proportionality

| Tier | Typical conditions | Required depth |
|---|---|---|
| Small | Local, reversible, low user impact, no interface/data/security change | Brief acceptance, relevant implementation, targeted tests, independent diff pass if available |
| Standard | Multi-file feature/bug, changed API or user flow | Work-item ledger, role-based analysis, focused ADR if needed, integration tests, distinct review; QA only if scope requires |
| High-risk | Auth/security/privacy, destructive or backfill migration, production infra, billing, breaking API, significant outage or high blast radius | Explicit alternative/trade-off review, security and SRE participation, rollback, release owner approval, monitor plan, evidence per gate |

Do not elevate merely to look thorough; elevate when likelihood * impact or irreversibility warrants it. Time-critical incident response may temporarily waive noncritical paperwork, not safety checks.

## Source-of-truth hierarchy

1. Current user instructions and explicit approvals; applicable security policies and higher-priority instructions.
2. Repository instructions, recent canonical requirements, project tracker, code, CI and runtime evidence.
3. Architecture records, technical design, product docs, prior tickets.
4. External knowledge for general practices, verified against installed versions.

Conflicting sources require explicit reconciliation; a ticket can be stale and production code can be buggy. Record provenance and uncertainty. Never silently override a requirement with an agent opinion.

## Subagent invocation lifecycle

1. Open/identify an authoritative task-tracker row with stable ID, one owner, dependencies, current state and next action. Record delegation in a revisioned ledger: `role, task ID, objective, acceptance IDs, gate definitions, input refs, owned paths/tools, output contract, owner, dependencies, state`. No dispatch before each leaf has pre-work acceptance gates.
2. Consult role charter; issue a concise, complete handoff. Subagent is a specialist, not a duplicate orchestrator.
3. Discover which native delegation API, workspace isolation and result-tracking facilities actually exist. Invoke native subagents only when supported. Respect asynchronous completion signals and child identifiers; do not announce completion until verified. If delegation is unavailable, conduct an explicitly labeled sequential role pass in the parent and do not call it independent review.
4. Require the child to send a tracker delta (observed progress, actual state, blockers, evidence, next action) and a self-check ledger with actual evidence **and a concrete reuse/complexity assessment** for code changes. **Re-run authorized runnable gates** and critically inspect manual ones; record which review was independent vs same-context. Validate responses against claims, changed files, tests, requirements and amendments. Add branch integration gates before promoting children. Ask targeted follow-up to the same child/session if possible, or integrate yourself.
5. Apply/reconcile the tracker delta as the single local writer, then close the delegation with `accepted`, `changes requested`, `blocked` or `not run`; preserve source paths and evidence.

Apply `references/operating-modes.md` at intake and after any changed risk. For small work use the main/one coding agent and no unnecessary delegation or ceremonies. For standard work recruit only a relevant implementer and distinct reviewer; when the host cannot provide genuinely distinct review, retain a partial/blocked status instead of claiming verified Done. For high-risk work require relevant expert security/QA/operations gates and authentic external authorization where necessary. The unified final decision must not be bypassed to save cost.

## Assignment and concurrency rules

- Parent owns global plan, revisioned acceptance inventory, root ledger, shared interface contracts, integration, independent re-verification, final reconciliation, status and final quality decision.
- Each child gets **one bounded deliverable** with explicit dependencies and out-of-scope restrictions. Never give multiple children the same unpartitioned feature.
- Parallelize independent reading, exploratory research, threat review and test design. Parallel edits require disjoint files AND contract stability; isolated git worktrees/branches are preferred.
- A shared DTO, API interface, migration, dependency manifest or generated code is single-owner until merged. Sequence dependent work. If agent writes outside its declared scope, inspect and reconcile before acceptance.
- Separate implementer from reviewer when risk requires distinct review; for `small` permit one agent and record same-context verification honestly. QA must challenge happy-path assumptions, not simply paraphrase engineering tests. Security can escalate material unresolved vulnerabilities, not authorize deployment.
- Use bounded retries: one clarifying follow-up and one repair cycle per failed delegation before replan/escalation. Keep failed gates OPEN; do not silently waive them to satisfy a retry budget. Avoid circular agent debates and redundant full-codebase re-reads.
- Budget context: prefer narrow code paths, existing tests, compact handoffs, links to source files, and selective role loading. Do not spawn 14 specialists to fix a label.

## Decisions and escalation

Escalate to user/authorized owner before: production rollout or rollback, secrets rotation, permission changes, destructive data operations, spending, publishing external content, changes to product scope/pricing, accepting known high severity security risks, or breaking compatibility without approval. Ordinary local reversible edits proceed when the request authorizes implementation.

When specialists disagree, decide from concrete evidence: acceptance impact, compatibility, reliability, maintenance cost, time. If decision exceeds delegation authority, present options and recommendation. Never use a majority vote between model personas as proof.

## Output cadences

- On task start: concise objective, scope, chosen roles (if meaningful), next actions.
- On meaningful milestone: completed work and evidence, live blocker/decision only.
- On finish: summary, changed paths, checks with result, release status, residual risk and follow-ups.
- For multiple work items: maintain status at the work-item level; do not infer progress from word count or simulated meetings.

## Formal execution and budget preflight

Before delegating, read `references/delegation-budget.md` and choose the minimum capable model with a declared cost/parallelism budget. Do not downgrade required review. Instruct coding agents to follow `references/implementation-methods.md` for test-first behavior, contract checks and bounded debug/review cycles. Use the one durable tracker (`references/orchestration-state.md`) for restart recovery. Verified completion requires actual evidence as described in `references/enforcement.md`, not only an agent's reported outcome.
