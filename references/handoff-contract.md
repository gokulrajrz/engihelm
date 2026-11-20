# Delegation and handoff contract

Pass only essential context and links to authoritative artifacts. No vague "implement this" assignments.

## Required delegation envelope

```yaml
work_item: WI-123 # existing canonical tracker ID, real ID if it exists; otherwise local label
tracker: "authoritative tracker reference / link; do not create a competing board"
from: sdlc-orchestrator
role: backend-engineer
purpose: "One sentence, user-visible outcome"
context:
  repo_root: "."
  authoritative_sources: ["file or issue refs"]
  observed_baseline: "tests/behavior/known limitations"
  requirement_revision: 1
  acceptance_ids: ["R-1", "R-2"]
responsibility:
  owned_paths: ["service/api/**"]
  allowed_actions: ["inspect", "edit", "test"]
  forbidden_actions: ["production deploy", "DB destructive migration", "modify client/**"]
acceptance_criteria:
  - "Given X, when Y, then Z"
  - "Given invalid input, return controlled error"
dependencies: ["API contract v1 confirmed"]
quality_expectations: ["unit tests", "relevant integration test", "no new secrets", "G2S simplicity self-review: reuse, alternatives, justified new complexity"]
completion_assurance:
  before_work: "Write or read scoped gate ledger and confirm CHECK + EXPECT"
  gates:
    - {id: "LEAF-A1", requirement: "R-1", check: "appropriate test command", expect: "observable result"}
    - {id: "LEAF-A2", requirement: "R-2", check: "manual: review actual permission-denial behavior", expect: "unauthorized request denied"}
  self_verify: "Run authorized checks and report actual output"
  parent_verify: "Orchestrator re-runs checks, evaluates G2S, and integrates after handoff"
  engineering_efficiency: "For code/design work add LEAF-SIMP or equivalent explicit review criterion; necessary complexity must be preserved"
expected_return:
  - "tracker delta: ID, actor, progress/state, blockers, dependencies, evidence refs, next action"
  - "summary and changed paths"
  - "test command and exact result"
  - "gate ID, expectation, self-evidence and failures/unverified gaps"
  - "efficiency review: reused code, dependencies added, necessary complexity, rejected smaller option if material"
  - "tradeoffs, risks, residual questions"
  - "review-ready diff / suggested next role"
```

Use simple prose instead of YAML when the runtime lacks structured payloads, but preserve all fields. Adjust tool/permission set to actual runtime rather than claiming enforcement from text alone.

## Subagent response contract

```text
Role: <id>
Tracker: <canonical item ID and source; actual update applied or delta returned, not fictitious sync>
Task delta: <state, observed progress, blockers, dependencies, next action, last actor>
Status: self-verified | blocked | needs-decision | partial (never self-certified independent)
Requirement revision: <current>
Gate ledger: <path/ref, gate ID -> state and evidence>
Evidence: <observed file locations, code lines, commands, logs>
Deliverables: <changed files OR proposed specification>
Acceptance: <criterion -> verified / unverified / fails>
Checks: <command, result, why skipped>
Efficiency review: <existing reuse, added complexity/deps, justification, smaller alternative if material; for code/design>
Risks: <severity, impact, mitigation>
Handoff: <next owner, input needed, unresolved dependency>
```

Every agent (including PO, QA, design and writers) must define acceptance gates **before** substantive work and record its own self-checks; the orchestrator has separate root/integration gates. Reject ungrounded `all tests pass` claims. If a task wasn't executed, say `not run`. If subagent work is asynchronous, keep state `in progress` until actual result arrives. Require code owner to identify migration ordering, feature flags, API compatibility and cleanup when relevant.

## Persistent artifacts

If a repo already has PRD/TSD/ticket/ADR structure, reuse it. Otherwise for substantial work use `docs/sdlc/work-items/<real-id-or-descriptive-slug>/` with only the needed files: `work-item.md`, `decision.md` (if material), `test-evidence.md`, and `release.md`. Do **not** write credentials or user personal data into artifacts. If no filesystem exists, keep a compact in-chat ledger.

## Roles and approvals

PO decides business tradeoffs but cannot authorize production by roleplay. Architect makes a technical recommendation, not a unilateral breaking-change commitment. Tech lead owns implementation integrity; QA can refuse to mark tests passed; security can escalate high-risk vulnerabilities; SRE owns deploy/rollback plan. Orchestrator reports the true status and seeks real approvals for external consequences.

## Resilient implementation return fields

For implementation work include test-first RED/GREEN/REFACTOR or an explicit justified exception, observed root cause (for bugs), affected producer/consumer contract, reviewer findings and dispositions, source revision, trusted evidence reference if available, durable tracker version/delta, model/cost constraints and restart next action. Never present review/tool execution as independent if the same session produced it. See `references/implementation-methods.md`, `references/orchestration-state.md`, and `references/delegation-budget.md`.
