# Formal engineering execution and review protocols

**Read before implementation, debugging, refactoring, migration or code review.** Apply proportionately; the mandatory outcome is justified behavior and fresh evidence, not performative ceremony. Every agent, including the Director when writing code, follows these protocols.

## Test-first development (preferred for observable code changes)

1. Characterize expected behavior using acceptance IDs, API/UI/data contracts and an executable test at the closest stable boundary. Check the current repo's test conventions before adding libraries.
2. **RED:** Run the new/changed test and capture the expected failure for the intended reason. A syntax error, missing dependency, failing unrelated test or broken fixture does **not** count as a useful RED.
3. **GREEN:** Apply the smallest complete behavior change; run the focused test and capture success.
4. **REFACTOR:** Remove duplication and unnecessary complexity while preserving the safety/compatibility requirements; rerun the focused and relevant regression suite.
5. Record actual commands, exit codes, commit/artifact revisions and test references in the task ledger. The independent verifier checks relevant assertions and integration behavior rather than accepting a prose summary.

For pure prose, generated artifacts, infrastructure lacking a safe harness, legacy code without isolated test seams, and emergency incident containment, explicitly record why test-first is inappropriate and use an alternate characterization test, dry-run, reproducible manual check, or staged validation. Never label an exception as passing TDD. Never avoid a necessary safety check to save time.

## Systematic debugging (no speculative patch cascade)

1. Reproduce the observed failure or preserve diagnostic logs/evidence if reproduction is risky; specify actual versus expected and affected scope.
2. Inspect the entire relevant data/control path, caller, environment, recent changes, and working patterns. Enumerate plausible hypotheses with discriminating observations.
3. Test the *leading* hypothesis with the smallest probe. Update the hypothesis after new evidence; do not repeatedly apply untested edits.
4. Repair the identified root cause while respecting contracts, data integrity and regression boundaries.
5. Add a regression check that fails for the original defect and passes after repair; verify adjacent paths. Report uncertainty if root cause is not established.
6. After two materially failed attempts at the same hypothesis or three nonproductive attempts overall, stop changing code, escalate to the Tech Lead/Orchestrator, and revise the diagnostic plan. Escalation is not permission to claim completion.

## Contract-first implementation preflight

For changes crossing module/package/API/DB/role boundaries, define producer and consumer, schema/shape, status/error cases, auth/tenancy, idempotency, backward compatibility, migration/backfill, ordering/timeouts and rollback, as applicable. Compare with real callers. Obtain review of significant breaking contracts before parallel implementation. Capture contract-test evidence for both sides. Declare speculative assumptions and revisit when reality differs.

## Review/fix loop and reviewer adjudication

- Use the smallest useful set of independent reviews: specification/acceptance coverage, code quality/complexity, and risk-specific QA/security when warranted. A review by the same context is not independent.
- Classify each finding as `blocking`, `nonblocking`, `false-positive` (with evidence), or `deferred` (authorized scope change). Demand reproduction or a concrete reason; do not obey incorrect review suggestions blindly.
- Implement focused fixes, rerun affected tests, and ask for targeted re-review. Limit unproductive back-and-forth to two rounds; escalate unresolved material disagreements to the Director with both arguments and evidence. Never waive a security-critical issue just because the retry limit is reached.
- Run a final integration and requirement-reconciliation pass on the combined changes; task-level green tests do not prove integrated success.

## Git and branch finishing

Before merging, check changed files, unrelated work, tracked/untracked changes, contract migration status, acceptance coverage, fresh tests and approved review decisions. Reverify against the target merge commit (or merge queue result) and capture that revision. Never merge, push, deploy, delete worktrees or discard user changes without appropriate authorization. Record delivered versus merely implementation-complete status distinctly.

## Task-closure handoff

After implementation and review, record actual observed evidence in the task and ledgers, transition the local task to `Verified`, then request the Director to use `scripts/verify_and_close.py`. Never use `state_store.py transition --state Done` or self-certify through an improvised SQL update. No new tracking layer: use the existing `state.db`, scoped root ledger, and existing gate receipt. If the guard rejects, return the precise unresolved acceptance/receipt/commit issue and the next action; never bypass the guard to make the tracker green.
