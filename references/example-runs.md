# Example orchestrations

## Example A: Wrong-role login defect

**Input:** "Users can sign in after choosing a role not assigned to their account. Fix it."

- **Intake:** Reproduce expected vs actual role validation, trace routes and server session/auth behavior. Mark security exposure as high-risk if authorization bypass may exist.
- **Team:** BA for expected multi-role semantics if ambiguous; security to review trust boundary; backend or frontend based on root cause; QA; code-reviewer. Tech lead integrates.
- **Slices:** Add failing wrong-role test; enforce server policy where authorization lives; update client route behavior if necessary; re-test valid and invalid role combinations and refresh.
- **Gates:** Auth checks fail closed where required; regression and independent review; release approved before any production change.
- **Final:** Evidence of tests actually run, implemented/blocked status; never declare production fixed until verified there.

## Example B: Course-specific certificate templates

**Input:** "Implement different certificate templates for initiative courses without breaking regular certificates."

- **Intake:** PO/BA define course-to-template rules, legacy defaults, permissioned management, preview and already-issued certificate behavior.
- **Team:** Architect for template storage/retrieval and versioning; data engineer only if schema changes; backend, frontend/UX, QA, reviewer; security for template injection/upload permissions.
- **Slices:** Configuration and safe default fallback; admin management; rendering + issuance; regression for standard courses and historical documents.
- **Gates:** Contract compatibility, authorization, historical records, edge cases, visual/accessibility acceptance if UI.

## Example C: Supabase/Postgres connection timeout incident

**Input:** "Production DB connections time out; identify cause and recover."

- **Intake:** Incident commander establishes blast radius and evidence; SRE traces metrics/logs; backend checks pool saturation and query workload; QA prepares restoration smoke.
- **Mitigation:** Halt unnecessary workload if authorized; preserve diagnostic evidence before considering controlled restart, with impact and approval. Avoid unverified claims about the root cause.
- **Exit:** Observed DB recovery and user paths, backlog for pool/query fixes and monitoring, explicit post-incident writeup if incident verified.

## Example D: Plan a 2-week sprint

**Input:** "Plan next sprint for a backlog of 12 work items."

- **Team:** PO prioritizes outcomes; BA verifies DoR; tech lead maps dependency/capacity; scrum master forms proposed goal and board.
- **Output:** Ranked ready work, explicit not-ready work, tentative scope with confidence, risks and acceptance. No made-up historical throughput or human commitments.
