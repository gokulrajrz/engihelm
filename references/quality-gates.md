# Evidence-based quality gates

**Mandatory tracker gate:** Ensure task ID, accountable owner, current state, blocker/next action and actual acceptance evidence remain synchronized in the authoritative tracker. Before closing an item or a root request, reconcile `references/task-tracking.md`; a green audit of a ledger alone does not close an untracked task.


Every agent, including the parent orchestrator, first writes its own pre-work acceptance ledger per `references/completion-assurance.md`. Treat SDLC gates G0-G9 as cross-stage policy gates; the per-agent CHECK/EXPECT ledgers are their concrete proof obligations. The parent re-runs child checks when safe, adds branch integration gates, and completes root requirement reconciliation before claiming completion.

Only claim a gate passed with observed, linked evidence. Gates are risk-proportionate; mark not applicable with rationale or not run with consequence. No single test suite proves all gates.

| Gate | Minimum evidence | Stop/escalate if |
|---|---|---|
| G0 Intake | Outcome, scope/non-goals, acceptance, risk | Contradictory requirements affecting safety |
| G1 Ready | Testable slice, dependencies/owners, contract assumptions | Unknown critical dependency |
| G2 Design | Reuse assessment, interface decisions, failure modes, ADR if substantial | Breaking contract lacks owner decision |
| G2S Engineering efficiency | Relevant existing-code/stdlib/installed-dependency reuse assessed; implementation and reviewer evaluate justified complexity and preservation of all requirements | Material avoidable complexity with specific impact + viable simpler solution; or underengineering that drops required safeguards |
| G3 Implementation | Scoped diff, readable code, reviewable commits, no secrets | Unexpected changes, privileged credential exposure |
| G4 Verification | Appropriate automated tests, negatives, regression, lint/build/type checks if configured | Key behavior untested or failing |
| G5 Risk-based review | `small`: named self-review/second pass; `standard`: distinct reviewer required for local Done (if unavailable, remain partial/blocked); `high-risk`: genuinely independent reviewer evidence before independent-verification claim. Findings resolved or disclosed | Required independent review unavailable or unresolved blocking correctness/security finding |
| G6 Security/NFR | Threat check where required, authN/authZ, privacy, a11y, reliability, performance | Known critical/high risk not explicitly accepted by authorized party |
| G7 Release readiness | CI green, compatibility, migration plan, flags, rollback, health checks, approvals | Unrecoverable migration or missing authorization |
| G8 Production verification | Real deployed version, smoke tests, telemetry/error rate, rollback readiness | Signs of regression or missing confirmation |
| G9 Learning | Docs/backlog/debt/incident follow-ups, stakeholder evidence | Incomplete closure of known remediation |

## Avoiding complexity-review false positives

The G2S gate is mandatory to **evaluate** on code/design work, not automatically blocking for extra lines, more files, security layers or a reviewer preference. Block only on evidence-backed material overengineering (with a complete, viable simpler alternative) or serious underengineering, and re-evaluate after change. Preserve the repository's established patterns and requirements. See `references/engineering-efficiency.md`. Record the implementer's review, reviewer findings (or lack of independent review), and orchestrator integration decision.

## Behavioral tests

- Map each acceptance criterion to observable proof, including negative, boundary and role-based paths.
- Prefer existing test harness, deterministic fixtures, unit tests for logic, integration tests for boundaries, E2E for critical journeys.
- Detect false positives: test accidentally skipped, mocked behavior not matching production, wrong environment, flaky green, tests that assert implementation rather than contract, hidden authorization bypass, empty assertions. Re-run relevant checks after implementation and integration changes; record any stale earlier proof as pending.
- Report actual commands, environment, pass/fail counts and meaningful warnings. Never infer `passed` because code looks correct.

## Compatibility / data gates

- For API changes: request/response contracts, consumers, auth scopes, backward compatibility, versioning and error semantics.
- For DB: expand/backfill/contract when possible, indexes/query plans for impactful changes, lock duration, idempotent reruns, constraints, historical data, nullability, rollback or forward fix.
- For messaging: retries, idempotency, ordering assumptions, outbox semantics, duplication and poison messages.
- For distributed auth: revoke/refresh/session behavior, missing account records, denial path, auditability, fail-open vs fail-closed choice.
- For frontend: loading/empty/error states, keyboard/screen-reader behavior, responsive breakpoints, localization and secure client-side rendering.

## Release controls

Never deploy solely because a subagent says "ship it". Require appropriate human/project authorization and tool permission. Stage deploy: preflight -> deploy -> smoke -> monitor -> close, with rollback triggers and owner; do not run irreversible steps without approval. For high-risk migrations rehearse/backup and clarify whether rollback can restore data; a compensating forward migration may be safer.

If code implementation is done but no release access exists, report `ready for authorized release` and give executable runbook, not an invented green production status.

## Real, approved execution and post-merge proof

Use `references/implementation-methods.md` for red/green/refactor and systematic debugging; record actual command outcomes. `scripts/gate_runner.py` can run approved pinned command gates against a clean Git revision. Receipts are merely local observations unless a separately controlled signer protects the signing key and job. The optional CI template is **not** configured branch protection or approval. Revalidate the integrated merge revision and deployment separately.

**Final cross-check:** Use `scripts/completion_decision.py` against authoritative SQLite, all relevant acceptance ledgers and a pinned exact-revision receipt. Individual auditors and a green CI badge are not substitutes. See `references/operating-modes.md` to avoid blanket processes on small changes; do not waive security/verification just to reduce overhead.
