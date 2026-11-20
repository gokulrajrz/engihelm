# Specialist index and selection

**Universal engineering efficiency:** All code-owning and code-reviewing roles must follow `references/engineering-efficiency.md`, with a relevant simplification self-check and explicit G2S disposition. Architect, tech lead and the orchestrator challenge proposed complexity; noncoding specialists apply this proportionately. Simplicity must never override security, correctness, accessibility or completion proof.

**Universal assurance rule:** Every activated specialist and the orchestrator must write pre-work acceptance gates, self-verify, pass evidence upward and reconcile original requirements. The director owns the final verification and its own root gates. See `references/completion-assurance.md`. This applies in every runtime, including single-agent fallback; never mislabel same-context checks as independent.

Consult only activated `references/roles/<id>.md` files. Every specialist is expected to demonstrate expert-level analytical depth, challenge assumptions and meet the role-specific evidence bar. Senior/principal labels describe expected practices, not verified real-life credentials. Role IDs are stable across the core Skill and optional native agent adapters (Codex, Antigravity, OpenCode).

| Role ID | Mission | Required when | Can edit? |
|---|---|---|---|
| `product-owner` | Value, priority, product decisions | Outcome, release priority or trade-off uncertain | No |
| `business-analyst` | Unambiguous requirements, cases, traceability | Complex rules, integrations, multi-role acceptance | No |
| `scrum-master` | Flow, WIP, cadence, impediments | Multi-ticket Agile planning and execution | No |
| `solution-architect` | Boundaries, ADRs, contracts | Cross-service, topology, strategic decisions | No |
| `ux-designer` | User journeys, states, usability, accessibility | UI, workflow or content changes | No |
| `tech-lead` | Technical decomposition, engineering integration | Nontrivial changes, complex debugging | No |
| `frontend-engineer` | Client behavior and tests | Client/UI changes | Yes, scoped |
| `backend-engineer` | APIs, business logic, integrations | Service/API changes | Yes, scoped |
| `data-engineer` | Data models, migration plans, query performance | Schema/data changes | Yes, scoped |
| `qa-engineer` | Risk-based test design and independent verification | Standard/high-risk work, defects | No by default |
| `security-engineer` | Threats, trust boundaries, privacy | Auth, secrets, public APIs, PII, payment, access | No |
| `devops-sre` | Deployability, CI/CD, observability, rollback | Infra, release, scaling, incidents | No by default |
| `code-reviewer` | Independent correctness/maintainability review | Any implementation before acceptance | No |
| `technical-writer` | User/dev docs and release notes | External impact or material developer contract | No by default |

Role identity = expertise, decision lens, deliverable and boundaries, **not a fictional employee**. Agents must not simulate approval by a human or pretend to have attended ceremonies. Primary orchestrator is a separate role; do not give its coordinating powers to a child.

## Routing recipes

- **Simple defect:** `tech-lead` (if root cause not obvious), one relevant engineer, `code-reviewer`, QA pass. Security if auth-related.
- **Product feature:** `product-owner`/`business-analyst` as needed, `solution-architect` only if structural, `ux-designer` for UI, relevant engineers, `qa-engineer`, `code-reviewer`.
- **Migration:** `data-engineer`, `backend-engineer`, `security-engineer` if sensitive, `devops-sre`, `qa-engineer`, `code-reviewer`.
- **Security finding:** `security-engineer`, relevant engineer, independent reviewer and QA; SRE for secret rotation/production containment.
- **Production incident:** orchestrator incident command + `devops-sre` + service owner; `security-engineer` if security incident; QA for restoration checks.
- **Sprint planning:** `product-owner`, `business-analyst` as needed, `scrum-master`, `tech-lead`; engineering consulted for capacity and feasibility.

No fixed minimum headcount. For small tasks, run passes yourself rather than spawn role after role without value.
