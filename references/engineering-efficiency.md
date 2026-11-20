# Engineering efficiency and overengineering prevention

This is the **mandatory Ponytail-inspired design discipline** for code, architecture, infrastructure, testing strategy and review. It complements, but never weakens, `references/completion-assurance.md`. Attribution: inspired by the [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) MIT-licensed Skill; this is an independently written integration, not a bundled copy or a request to install its platform-specific plugin.

## Prime principle and boundaries

**Build the smallest complete, comprehensible, maintainable solution that meets the accepted requirements and passes relevant assurance.** Be efficient about implementation, never lazy about correctness. Do not silently lower scope, skip tests, delete safety measures, or hide consequences to improve apparent simplicity. The orchestrator and all activated specialists must apply the relevant checks; code-owning agents and reviewers must explicitly report the result.

## Mandatory pre-implementation simplicity assessment

For code or material design, record a concise assessment (one sentence per relevant item is enough; an existing work-item note can hold it):

1. **Problem and boundaries:** What observable change is necessary? Identify callers, contracts, tests, fixtures, configuration, migrations and documentation affected; distinguish genuine requirements from speculative nice-to-haves.
2. **Eliminate unnecessary work:** Can the requirement be met with no change, a configuration choice, a corrected existing behavior, or a smaller user-facing scope? Never reinterpret explicit acceptance criteria as optional.
3. **Reuse before invention:** Search the affected codebase for existing helpers, components, services, patterns and tests. Prefer the project's established abstractions when they already solve the problem; otherwise consider standard-library or native platform facilities, then installed dependencies, before adding new code or packages.
4. **Smallest coherent implementation:** Favor clear, local, reviewable changes with all necessary callers and safety checks updated. Do not optimize blindly for lines changed: fewer lines/files can make correctness or clarity worse.
5. **Complexity budget:** Justify each new dependency, abstraction, configuration switch, compatibility layer, queue/service, data store, generic framework or migration with a present requirement, demonstrated risk or credible measured need. Name alternatives rejected and the reason if the choice is material.
6. **Safety and lifecycle:** Preserve security, authorization, validation, error handling, accessibility, privacy, data integrity, backwards compatibility, operability, observability and recovery as applicable. Necessary complexity is not overengineering.

For tiny tasks, a compact `reuse -> change -> tests -> risks` line suffices. For cross-service/high-risk work, capture the trade-off in an ADR or technical decision as appropriate. Avoid generating documentation solely to satisfy a checklist.

## Mandatory code-review simplicity gate (G2S)

The implementer must self-check before handoff. A different reviewer must assess the proposed/actual diff whenever independent review is required or available. The orchestrator is **also accountable** for its own pre-design challenge and the integrated solution's simplicity, in addition to all Unlazy-inspired completion gates.

Review the diff and its context, then answer:

- Did we first examine existing reuse opportunities and nearby architecture conventions? Which specific paths or functions were considered?
- Are the new code, dependencies, files, abstractions, configuration, and infrastructure justified by current requirements or demonstrable constraints?
- Could a concrete, smaller alternative preserve all invariants and acceptance conditions with lower maintenance burden?
- Did the implementation update every affected caller/test/fixture/config/migration and avoid unrelated churn?
- Does any simplification remove a required behavior, necessary security/reliability layer, or tested edge case?

**Classification:**

- **PASS:** Minimal or justified complexity; include brief evidence and accepted trade-offs.
- **CHANGES REQUESTED (blocking):** Cite concrete changed paths, observable impact, a simpler viable alternative, and why the excess matters materially (cost, risk, comprehension, operations, maintainability). Recheck after revisions.
- **NONBLOCKING:** A style preference or minor optional simplification; do not block merely for taste, abstractions used consistently in the project, or an arbitrary line/file count.
- **UNKNOWN/BLOCKED:** Relevant context or independent review unavailable; disclose missing proof, do not invent a PASS.

Do not score complexity by raw LOC, number of files, import count or cyclomatic complexity alone. These signals may prompt inspection but cannot establish overengineering. Do not mandate rewriting stable code for unrelated cleanup, and do not introduce abstraction purely to enforce DRY when duplication is clearer.

## False-positive / underengineering safeguards

- Multiple security checks (e.g., login-time denial, request-time authorization and session revocation) can be justified defense-in-depth, not accidental duplication. Validate distinct threat boundaries before proposing removal.
- A migration's safety checks, idempotency, rollback/forward-fix, observability and consumer compatibility can be essential even if they add code.
- A well-established project component may be preferable to a native widget when design, accessibility, localization or integration contracts demand it.
- A focused integration/E2E test is not unnecessary ceremony when it validates a cross-component behavior missed by unit tests.
- A simple implementation with unbounded data cost, missing authorization, fragile concurrency or unsafe failure behavior is **underengineered**, not an acceptable optimization.

## Agent-specific application

- **Frontend, backend, data engineers:** Apply the reuse ladder before changes; include an `Efficiency review` line in handoff with existing code reused, new dependencies/abstractions and why, alternative rejected if material, and any accepted limits.
- **Solution architect and tech lead:** Examine whether new services, layers, generic patterns or infrastructure are actually needed; prefer existing boundaries and clearly justify necessary exceptions.
- **DevOps/SRE:** Challenge extra jobs, queues, provisioning and operational dependencies, without relaxing deploy safety, monitoring, recovery or permissions.
- **Code reviewer:** Independently classify material overengineering with code-path evidence and a complete simpler alternative. Challenge over-simplified solutions too.
- **QA and security:** Verify that proposed simplifications preserve test coverage, negative cases, exploit resistance and system invariants.
- **Product, BA, UX, Scrum Master, technical writer:** Favor minimum useful process/artifacts and avoid speculative scope; never waive acceptance or domain standards.
- **Main Orchestrator:** Assess simplicity before delegation, resolve disagreements with observed facts and acceptance, reconcile at integration, and own a `ROOT-SIMP` assurance gate on substantial work. Never self-award independent verification.

## Interaction with Completion Assurance and runtime limits

Use `G2S` as the policy gate and `ROOT-SIMP` in substantial root assurance ledgers. For code-owning leaves, add a named `LEAF-SIMP` or clearly mapped equivalent review criterion to the gate ledger/handoff; link reviewer findings and recheck after revisions. A structural ledger checker cannot determine whether code is actually overengineered: evidence must be manually examined, and external checks/CI only enforce what they actually run.

**Precedence:** Explicit acceptance, safety/security invariants, repository instructions and actual verification outrank code minimization. Ponytail-style simplicity determines *how to implement the complete task*, while Unlazy-style discipline determines *how to prove it is complete*. If these appear to conflict, retain correct behavior, explain trade-offs, and seek the authorized decision when scope genuinely changes.
