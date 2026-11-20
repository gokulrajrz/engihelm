#!/usr/bin/env python3
"""Non-executing structural audit of portable SDLC completion ledgers.

Never runs CHECKs or opens evidence URLs. Verifies recorded status consistency,
requirements coverage, reviewer separation and final claim preconditions. Actual
command execution and evidence authenticity must be verified by the host/user.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT_GATES = {'ROOT-TRACK', 'ROOT-REQ', 'ROOT-DISP', 'ROOT-LEAF', 'ROOT-INT', 'ROOT-RISK', 'ROOT-CLAIM', 'ROOT-SIMP'}
RESULTS = {'PASS', 'FAIL', 'NOT_RUN', 'BLOCKED'}
STATUSES = {'PENDING', 'PASS', 'FAIL', 'BLOCKED', 'NOT_RUN', 'N/A'}
CLAIMS = {'IN_PROGRESS', 'COMPLETE', 'PARTIAL', 'BLOCKED'}
LEVELS = {'root', 'leaf'}


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def audit(ledger, final=False, require_root=False):
    errors = []
    def issue(message): errors.append(message)
    if not isinstance(ledger, dict):
        return ['ledger must be a JSON object']
    if not nonempty(ledger.get('work_item')):
        issue('work_item missing')
    if type(ledger.get('revision')) is not int or ledger['revision'] < 1:
        issue('revision must be a positive integer')
    if ledger.get('tier') not in ('small', 'standard', 'high-risk'):
        issue('tier must be small, standard or high-risk')
    if not nonempty(ledger.get('owner')):
        issue('owner missing')
    level = ledger.get('ledger_level')
    if level not in LEVELS:
        issue('ledger_level must be root or leaf')
    if level == 'root' and ledger.get('owner') != 'sdlc-orchestrator':
        issue('root ledger must be owned by sdlc-orchestrator')
    if level == 'leaf' and ledger.get('owner') == 'sdlc-orchestrator':
        issue('sdlc-orchestrator must use a root ledger')
    if require_root and level != 'root':
        issue('--root requires an orchestrator root ledger')
    artifact_revision = ledger.get('artifact_revision')
    claim = ledger.get('final_claim')
    if claim not in CLAIMS:
        issue('final_claim invalid')
    if claim == 'COMPLETE' and not nonempty(artifact_revision):
        issue('COMPLETE requires an artifact_revision that identifies exact current content')
    requirements = ledger.get('requirements')
    gates = ledger.get('gates')
    if not isinstance(requirements, list) or not requirements:
        issue('requirements must be a nonempty array')
        requirements = []
    if not isinstance(gates, list) or not gates:
        issue('gates must be a nonempty array')
        gates = []

    gate_by_id = {}
    for i, gate in enumerate(gates):
        if not isinstance(gate, dict):
            issue(f'gates[{i}] must be an object')
            continue
        prefix = gate.get('id') if nonempty(gate.get('id')) else f'gates[{i}]'
        gid = gate.get('id')
        if not nonempty(gid): issue(f'{prefix}: missing gate id')
        elif gid in gate_by_id: issue(f'duplicate gate id {gid}')
        else: gate_by_id[gid] = gate
        for key in ('requirement', 'owner', 'expect'):
            if not nonempty(gate.get(key)): issue(f'{prefix}: missing {key}')
        if type(gate.get('required')) is not bool: issue(f'{prefix}: required must be boolean')
        if gate.get('kind') not in ('command', 'manual'): issue(f'{prefix}: kind must be command/manual')
        if not nonempty(gate.get('check')): issue(f'{prefix}: CHECK or manual method is missing')
        status = gate.get('status')
        if status not in STATUSES: issue(f'{prefix}: invalid gate status')
        if status == 'N/A' and gate.get('required') is True:
            issue(f'{prefix}: required gate cannot be N/A')
        if status == 'N/A' and not nonempty(gate.get('reason')):
            issue(f'{prefix}: N/A needs explicit reason')

        child = gate.get('self_check')
        parent = gate.get('parent_check')
        for stage, check in (('self_check', child), ('parent_check', parent)):
            if not isinstance(check, dict):
                issue(f'{prefix}: missing {stage} record')
                continue
            if check.get('result') not in RESULTS:
                issue(f'{prefix}: invalid {stage} result')
            if check.get('result') == 'PASS':
                if not nonempty(check.get('context_id')):
                    issue(f'{prefix}: {stage} PASS requires context_id')
                if not nonempty(check.get('artifact_revision')) or check.get('artifact_revision') != artifact_revision:
                    issue(f'{prefix}: {stage} PASS evidence not bound to current artifact_revision')
                if not nonempty(check.get('reference')) or not nonempty(check.get('observed')):
                    issue(f'{prefix}: {stage} PASS without specific reference and observed result')
                if check.get('scope_revision') != ledger.get('revision'):
                    issue(f'{prefix}: {stage} PASS evidence stale for current requirement revision')
        if isinstance(parent, dict):
            mode = parent.get('mode')
            if mode not in ('independent', 'same-context', 'not-run'):
                issue(f'{prefix}: invalid parent verification mode')
            if parent.get('result') == 'PASS':
                verifier = parent.get('verifier')
                if not nonempty(verifier): issue(f'{prefix}: missing parent verifier')
                if mode == 'not-run': issue(f'{prefix}: PASS but parent mode is not-run')
                if mode == 'independent' and verifier == gate.get('owner'):
                    issue(f'{prefix}: self-review cannot count as independent')
                if mode == 'independent' and isinstance(child, dict) and child.get('context_id') == parent.get('context_id'):
                    issue(f'{prefix}: same execution context cannot count as independent')
        if status == 'PASS':
            if not (isinstance(child, dict) and child.get('result') == 'PASS'):
                issue(f'{prefix}: PASS status without successful self-check')
            if not (isinstance(parent, dict) and parent.get('result') == 'PASS'):
                issue(f'{prefix}: PASS status without successful parent recheck')
        if claim == 'COMPLETE' and gate.get('required') is True and status != 'PASS':
            issue(f'{prefix}: COMPLETE with required gate {status}')
        if claim == 'COMPLETE' and ledger.get('tier') == 'high-risk' and gate.get('required') is True:
            if not (isinstance(parent, dict) and parent.get('mode') == 'independent'):
                issue(f'{prefix}: high-risk COMPLETE requires independent parent verification')

    req_ids = set()
    for i, req in enumerate(requirements):
        if not isinstance(req, dict):
            issue(f'requirements[{i}] must be an object')
            continue
        rid = req.get('id')
        if not nonempty(rid): issue(f'requirements[{i}]: missing id')
        elif rid in req_ids: issue(f'duplicate requirement id {rid}')
        else: req_ids.add(rid)
        if not nonempty(req.get('outcome')): issue(f'{rid}: empty observable outcome')
        ids = req.get('gate_ids')
        if not isinstance(ids, list) or not ids:
            issue(f'{rid}: must have one or more gate ids')
        else:
            if not any(isinstance(gid, str) and isinstance(gate_by_id.get(gid),dict)
                       and gate_by_id[gid].get('required') is True for gid in ids):
                issue(f'{rid}: no required acceptance gate; optional/N-A gates cannot certify a requirement')
            for gid in ids:
                if not isinstance(gid, str):
                    issue(f'{rid}: gate id must be string')
                    continue
                if gid not in gate_by_id: issue(f'{rid}: gate {gid} missing')
                elif gate_by_id[gid].get('requirement') != rid:
                    issue(f'{rid}: gate {gid} belongs to {gate_by_id[gid].get("requirement")}')
    for gid, gate in gate_by_id.items():
        if gate.get('requirement') not in req_ids:
            issue(f'{gid}: references unknown requirement {gate.get("requirement")}')
        elif gid not in next((r.get('gate_ids', []) for r in requirements
                              if isinstance(r, dict) and r.get('id') == gate['requirement']), []):
            issue(f'{gid}: gate not included in requirement coverage map')

    approvals = ledger.get('approvals')
    if not isinstance(approvals, dict) or type(approvals.get('required')) is not bool:
        issue('approvals must define required:boolean')
    elif claim == 'COMPLETE' and approvals['required']:
        if approvals.get('granted') is not True or not nonempty(approvals.get('reference')):
            issue('COMPLETE despite missing documented human approval')
    if claim == 'COMPLETE' and level == 'root':
        mandated = ROOT_GATES if ledger.get('tier') != 'small' else {'ROOT-TRACK'}
        missing = mandated - set(gate_by_id)
        if missing: issue('root completion claim missing director-owned gates: ' + ', '.join(sorted(missing)))
        for gid in mandated & set(gate_by_id):
            if gate_by_id[gid].get('owner') != 'sdlc-orchestrator':
                issue(f'{gid}: required root gate is not owned by sdlc-orchestrator')
            if gate_by_id[gid].get('required') is not True:
                issue(f'{gid}: mandatory root gate cannot be downgraded to optional')
            if gate_by_id[gid].get('status') != 'PASS':
                issue(f'{gid}: mandatory root gate must PASS before COMPLETE')
    if final and claim != 'COMPLETE':
        issue(f'--final rejects non-COMPLETE claim {claim}')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ledger', type=Path, help='JSON assurance ledger (read-only)')
    parser.add_argument('--final', action='store_true', help='Require a full COMPLETE claim')
    parser.add_argument('--root', action='store_true', help='Require an orchestrator root ledger, not a leaf')
    args = parser.parse_args()
    try:
        ledger = json.loads(args.ledger.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        print('FAIL: unable to read JSON ledger:', exc)
        return 2
    problems = audit(ledger, args.final, args.root)
    if problems:
        print('FAIL: ledger inconsistency (no CHECK commands executed)')
        for message in problems: print(' -', message)
        return 1
    print('PASS: ledger structure/status consistent (no CHECK commands executed; evidence not authenticated)')
    return 0

if __name__ == '__main__':
    sys.exit(main())
