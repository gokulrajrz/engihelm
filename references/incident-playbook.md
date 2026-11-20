# Incident and hotfix operating procedure

## Priorities

Protect people, data, availability and evidence. Incident command is separate from sprint planning. Do not execute destructive mitigations or contact users without appropriate authorization. Prioritize safe containment and restoration over perfect root-cause certainty.

1. **Detect and bound:** symptoms, start time, affected users/roles/regions, severity, known good state; state uncertainty.
2. **Establish command:** orchestrator tracks timeline, roles, decisions and communications; SRE handles infrastructure, service owner behavior; security joins on suspected compromise; QA handles restoration proof.
3. **Preserve evidence:** logs, traces, metrics, config changes, deployed hashes, data integrity signs. Avoid losing evidence with unnecessary restarts.
4. **Mitigate:** select safest reversible action (traffic shift, disable feature, revert deploy, throttle load) based on evidence and approval. Record blast radius and rollback option.
5. **Diagnose:** formulate/falsify hypotheses, minimize additional changes, reproduce in staging where feasible; add regression test for fix.
6. **Restore and verify:** affected transactions and user flows, alerts, queue depth, errors, latency, side effects, data reconciliation; monitor for recurrence.
7. **Communicate truthfully:** facts, impact, current status, next decision. Never invent customer communications or timestamped incident events.
8. **Follow up:** blameless incident write-up with timeline, root cause confidence, contributing factors, corrective/preventive actions with owners, test gaps and detection improvements.

## Incident severity and stop signals

Determine severity from user impact and data/security exposure, not from an agent's emotion. If sensitive data or active exploit risk is plausible, escalate security/incident response immediately and avoid exposing secrets or exploit details in public artifacts. Release freezes and out-of-band approvals are organization-specific; check policy rather than assuming.

## Output

`Incident status | confirmed impact | evidence | mitigation actually performed vs proposed | verification | open risks | human decisions required | next update owner`.
