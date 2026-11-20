# Agent acceptance ledger: <leaf ID>

**Owner:** <role/agent>  **Requirement revision:** 1  **Owns:** <paths/artifacts>  **Needs:** <dependencies>

| Gate ID | Requirement | CHECK or manual inspection | EXPECT | Status | Self-evidence | Parent recheck evidence |
|---|---|---|---|---|---|---|
| LEAF-A1 | R-1 | `<reviewed test command>` | `<expected observable output>` | PENDING | not run | not run |
| LEAF-A2 | R-1 | manual: `<actual artifact + method>` | `<observable expected property>` | PENDING | none | none |

**Commands reviewed/authorized by:** <human or host permission mechanism>
**Execution environment:** <cwd, shell, version, branch/commit, relevant tool versions>
**Adversarial/edge coverage:** <negative paths and possible false positives>
**Handoff:** SELF_VERIFIED | BLOCKED | PARTIAL; paths and unsatisfied gates

A leaf cannot call itself independently verified. Parent re-runs applicable commands and checks manual evidence after the return.
