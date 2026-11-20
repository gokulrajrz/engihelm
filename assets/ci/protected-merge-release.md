# Protected CI/CD rollout checklist (requires repository administration)

This Skill cannot turn on GitHub/GitLab protection, approve releases or create a protected execution identity by copying files. Treat the example workflow as a starting point, not an installed enforcement system.

1. Protect the target default and release branches with required pull requests, required status checks (`SDLC required executable gates / executable-gates` or provider equivalent), no self-bypass for coding agents, and appropriate reviewer/ownership rules. Require up-to-date checks on the integrated/merge-queue commit.
2. Protect `.github/workflows/**`, `CODEOWNERS`, `.sdlc/gates.json`, the canonical Skill and any trusted runner scripts using CODEOWNERS, branch/ruleset protection, and dedicated trusted CI administrators. A PR-controlled workflow file can spoof the job; protect workflow changes and tie required checks to the expected source application.
3. Run the checker and policy from a **protected trusted revision**; run the tests against the candidate revision. Verify policy SHA-256 using a separately controlled repository variable or equivalent. Do not compute the trusted pin from the unreviewed PR contents.
4. Execute candidate tests in an unprivileged sandbox: no secrets, narrow filesystem access, no privileged Docker socket, restricted network, CPU/memory/disk limits and timeouts. A runner that invokes arbitrary test commands with CI credentials can leak tokens.
5. For higher assurance, have a separate service identity attest the **trusted CI-produced results** and store signatures/attestations outside agent-writable storage. Do not expose its private signing key to the candidate tests or shared-UID processes. HMAC proof is meaningful only under genuine credential isolation.
6. Configure release-specific environment protection and human approvers, release artifact/revision verification, migration/rollback plans and post-deploy health checks. Merge status does not prove production deployment occurred.
7. Verify negative cases deliberately: a failing gate blocks merge, a renamed gate cannot pass, unreviewed workflow/policy edits require approval, an unsigned or wrong-commit proof cannot be accepted as independent evidence, and an unauthorized deployment is rejected.
8. Record evidence from settings/ruleset/API and a controlled failed-PR test before declaring merge/release enforcement active.

Provider documentation and security controls evolve; verify the native capabilities and exact settings for the actual repository/plan. Never claim this package has configured them automatically.

## Required integration with the unified final decision

This template currently executes only approved code gates. To enforce the complete SQLite/ledger/receipt decision, your protected CI environment must obtain a snapshot of `state.db`, the matching root and actual leaf ledgers, and the exact gate receipt for the same candidate Git commit from an authenticated artifact store. The checked-out repository usually **does not contain** the local-only DB. Invoke the protected copy of `scripts/completion_decision.py` in signed mode after verifying the state snapshot identity, source revision, signer isolation and real approvals. Prevent an untrusted coding agent from replacing the policy pin, ledger requirements or CI job. If that artifact handoff and independent identity have not been implemented, report only "executable gate checks configured"; never claim unified merge/release enforcement.
