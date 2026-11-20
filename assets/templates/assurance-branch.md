# Branch / root integration assurance: <branch>

**Parent/orchestrator:** <role>  **Requirement revision:** 1

| Gate ID | Input leaves | CHECK or review method | EXPECT | Status | Parent evidence |
|---|---|---|---|---|---|
| ROOT-REQ | all | reconcile original + amended request with ID inventory | every user-visible requirement accounted for | PENDING | none |
| ROOT-DISP | all | inspect real assignment records + limits | no false dispatch, overlapping ownership or missing leaf gates | PENDING | none |
| ROOT-LEAF | all | re-run authorized leaf checks, inspect manual proof | all required leaf gates verified or open gaps reported | PENDING | none |
| ROOT-INT | all | run/inspect integration contract and regression checks | compatible, observable end-to-end behavior | PENDING | none |
| ROOT-RISK | all | inspect security, data, rollback and approval evidence | material risks/approvals resolved or explicitly blocking | PENDING | none |
| ROOT-CLAIM | all | compare final report with current revision and evidence | no unsupported complete/deployed/independent-review claims | PENDING | none |

**Remaining failed/not-run gates:** <ids and impacts>
**Final claim:** COMPLETE | PARTIAL | BLOCKED
**Verification independence:** genuine separate reviewer | same-context second pass | unavailable
