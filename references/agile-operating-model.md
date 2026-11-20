# Agile operating model

## Principles

Deliver customer outcomes in thin, validated increments. Use Scrum-style sprints for planned multi-item product delivery; use Kanban/expedite lanes for ad hoc fixes and incidents. Apply continuous integration and feedback regardless of framework. AI personas may prepare ceremonies and records, but only real people can actually attend or approve them.

## Work-item hierarchy and states

**Mandatory operational tracking:** Apply `references/task-tracking.md` to *all* SDLC tasks, including the director's own. Use the project-local SQLite `docs/sdlc/state.db` as the canonical tracker, with `docs/sdlc/TASKS.md` generated as its readable view. Do not connect any external issue board. In local multi-agent work use Orchestrator-coordinated deltas. An in-chat one-row record suffices only when no persistent writable store exists, with the limitation disclosed. The tracker is not the separate acceptance gate ledger.

`Outcome / initiative -> epic -> user story or defect -> implementation tasks / test cases`.

States: `Inbox -> Triaged -> Ready -> In Progress -> In Review -> In QA -> Ready for Release -> Released -> Verified -> Done`; `Blocked` is a flagged condition with owner and unblock action, not an invisible holding state. A planning-only request can stop at Ready and be marked `planned, not implemented`.

Update at each meaningful state change, blocker, handoff, review, or verified closure. Always keep owner, next action, last update actor and verification/gate reference current. The orchestrator must reconcile all issued assignments against tracked IDs before claiming completion.

Record at minimum: ID, title, user/business impact, measurable acceptance criteria, priority, dependencies, owner, scope/non-goals, estimate/confidence, risk tier, state, evidence links, approval needed, next action. Never create fake tracker IDs or modify external boards absent access/authorization.

## Definition of Ready (DoR)

- Outcome and user are identified; acceptance is observable and testable, with negative/edge cases.
- Business rules and affected roles, states and integrations are identified.
- Dependencies and major assumptions are visible; API/data/UX contracts are stable enough for the chosen slice.
- Work is small enough to complete and verify as one vertical slice; risk/approvals are known.
- No hidden blocker; otherwise keep in refinement rather than promising a commitment.

## Definition of Done (DoD)

- Acceptance criteria demonstrably met; scoped change merged/approved where applicable.
- Tests appropriate to risk pass, new/changed behavior has regression coverage; important failure cases covered.
- Independent review findings resolved or explicitly accepted by authorized owner.
- Security, privacy, accessibility, performance, migration and observability checks performed where relevant.
- Documentation, release notes, flags, compatibility and rollback plan updated as needed.
- Production deployed and verified **only if release was part of authorized scope**; otherwise label `implementation ready / awaiting deployment` rather than `released`.

## Sprint / flow ceremonies (artifacts, not fake meetings)

- **Backlog refinement:** PO/BA prioritize, split and clarify stories with tech/QA. Output DoR evidence, dependencies and candidate order.
- **Planning:** Select a sprint goal and few high-value ready stories based on actual historical throughput or human-supplied capacity. If no data, show a tentative forecast with uncertainty; never invent velocity or capacity.
- **Daily sync:** Summarize each active item: yesterday's verified work, next concrete step, blocker, aging/WIP. Avoid generated human standup quotes.
- **Review/demo:** Link functional evidence to acceptance. Distinguish verified demo from a proposed demo script; capture stakeholder feedback if actually supplied.
- **Retrospective:** Use real incident/rework/cycle-time data. Output 1–3 improvement experiments with owner and review date; do not fabricate team sentiment.
- **Release planning:** Distinguish sprint completion from release readiness; backlog work not automatically production-shipped.

Use 1–2-week sprints as a reasonable default only if the user wants sprint planning and no cadence exists. For single tasks, use lightweight continuous flow. WIP limit by available engineering capacity rather than a fixed universal number; minimize partially completed work.

## Estimation and reporting

Use relative size or ranges, not unsupported precise hours. Mark dependencies and confidence. Track throughput, cycle time, escaped defects, deployment recovery and acceptance coverage if real data exists. Don't optimize story points or claim velocity from simulated contributors. Present risks and next actions over ceremony volume.
