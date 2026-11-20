# Cost-aware, risk-aware expert delegation

**Read during task planning and whenever model/subagent budget is material.** Model selection is a capability decision, not a claim that one vendor/model has universally superior quality. Actual availability, token pricing, tools and policy are host-specific.

1. Determine complexity, risk, uncertainty, context size and capability needed before assigning a model. Never lower security, tests or independent review merely to save tokens.
2. `light`: bounded lookup, straightforward drafting, mechanical modifications after contracts are fixed. `balanced`: ordinary implementation, focused analysis and routine QA. `deep`: architecture, novel debugging, concurrency/security/data migrations, disputed review and high-stakes integration. Upgrade after observed failures, not arbitrary iterations.
3. Use one accountable implementer per overlapping file scope. Parallelize only genuinely independent work. Apply a maximum concurrency and token/cost allowance; when budget is exhausted, stop and report a blocker or request approval, not silent quality reductions.
4. Send each specialist only the bounded task, relevant files, constraints, gate IDs and expected output. Do not flood contexts with the entire project or every role persona. Cache stable repository facts in documented artifacts, not in unverifiable prose.
5. Do not launch a new reviewer if an existing competent *independent* reviewer already covers the same acceptance/risk boundaries. Ensure review findings are reconciled; independence requires distinct agent context or authorized human, not merely a persona switch.
6. For `small` work, prefer one coding agent with its focused checks; for `standard`, add relevant review; for `high-risk`, require strong review and explicit approvals. Avoid a fixed 14-agent fan-out.
7. For executable planning use `scripts/delegation_plan.py` against a declared capability registry and budget. Its output is a deterministic staffing suggestion, **not** an actual model invocation, price quote or quality certification.
