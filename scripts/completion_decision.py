#!/usr/bin/env python3
"""Unified, read-only SDLC completion decision.

Correlates the authoritative SQLite tracker, root/leaf acceptance ledgers and a
real gate-runner receipt for ONE exact Git revision. Local decisions verify
consistency, not trust; signed receipt integrity still needs separate signer
and executor isolation externally established by an operator/CI owner.
"""
import argparse
import contextlib
import io
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

import assurance_audit
import gate_runner
import state_store

TIERS = {'small': 0, 'standard': 1, 'high-risk': 2}
CLOSED = {'Done', 'Cancelled'}
RECEIPT_PREFIX = 'receipt-sha256:'


def check(a, *, tracker_con=None, closing_task_id=None, closing_approval=None):
    errors = []
    warnings = []
    checks = {}
    def fail(message): errors.append(message)

    # A missing DB must never turn into an empty successful result. Never write to it.
    if not a.db.is_file():
        return {'status': 'REJECTED', 'errors': [state_store.missing_message(a.db)], 'warnings': []}
    if not state_store.marker_path(a.db).is_file():
        fail('tracker recovery marker missing; confirm project identity before final closure')
    try:
        owned = tracker_con is None
        if owned:
            con = sqlite3.connect('file:' + str(a.db.resolve()) + '?mode=ro', uri=True, timeout=10)
            con.row_factory = sqlite3.Row
            con.execute('PRAGMA query_only=ON')
            con.execute('BEGIN')  # stable snapshot of canonical tracker
        else:
            con = tracker_con  # caller holds BEGIN IMMEDIATE until guarded close commits
        state_store.validate_schema(con)
        if con.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            fail('SQLite integrity check failed')
        errors.extend('tracker: ' + x for x in state_store.verify(con))
        all_tasks = state_store.show(con)
        if not all_tasks: fail('tracker contains no tasks; empty project cannot be certified complete')
        scope = closing_task_id or getattr(a, 'task_id', None)
        tasks = all_tasks
        if scope:
            selected = next((t for t in all_tasks if t['id'] == scope), None)
            if selected is None:
                fail(f'task {scope} does not exist in authoritative tracker')
                tasks = []
            else:
                if closing_task_id:
                    if selected['state'] != 'Verified':
                        fail(f'{scope}: guarded close requires Verified state')
                    selected = {**selected, 'state':'Done',
                        'approval_ref':closing_approval or selected['approval_ref']}
                tasks = [selected]
        if owned:
            con.rollback()
            con.close()
    except (sqlite3.Error, ValueError, OSError) as e:
        return {'status': 'REJECTED', 'errors': errors + ['tracker cannot be audited: ' + str(e)], 'warnings': warnings}

    # Independently inspect actual Git revision and reviewed policy + receipt.
    receipt = None
    receipt_link = None
    policy = None
    try:
        if not re.fullmatch(r'[0-9a-f]{40,64}', a.expected_commit):
            fail('expected commit must be a full Git object ID')
        head, clean = gate_runner.git_state(a.repo.resolve())
        if head != a.expected_commit: fail('current repository revision differs from expected commit')
        if not clean: fail('working tree is dirty; no current exact-revision completion decision')
        if a.mode == 'lightweight':
            warnings.append('LIGHTWEIGHT: tracker and ledger are structurally checked, but executable results and manual evidence are not authenticated. Do not claim independent verification.')
        else:
            if not a.policy or not a.policy_sha256 or not a.receipt:
                raise ValueError('local/signed mode requires --policy, --policy-sha256 and --receipt')
            policy, actual_policy_hash = gate_runner.read_policy(a.policy)
            if actual_policy_hash != a.policy_sha256: fail('approved gate policy pin mismatch')
            raw_receipt = a.receipt.read_bytes()
            receipt_link = RECEIPT_PREFIX + hashlib.sha256(raw_receipt).hexdigest()
            receipt = json.loads(raw_receipt)
            if not isinstance(receipt, dict): raise ValueError('receipt is not an object')
            ids = [g['id'] for g in policy['gates']]
            results = receipt.get('results')
            if not isinstance(results, list) or len(results) != len(ids) or any(
                not isinstance(r, dict) or r.get('id') != gid or r.get('status') != 'PASS' or r.get('exit_code') != 0
                for gid, r in zip(ids, results)
            ):
                fail('receipt must contain exact ordered, passing policy gate results')
            if (receipt.get('repo_head') != a.expected_commit or
                    receipt.get('policy_sha256') != a.policy_sha256 or
                    receipt.get('mandatory_gate_ids') != policy['mandatory_gate_ids'] or
                    receipt.get('all_passed') is not True or receipt.get('worktree_clean') is not True):
                fail('receipt not bound to current commit, approved policy and successful execution')
            if a.mode == 'signed':
                if not a.key_file: fail('signed mode requires independent verifier key')
                else:
                    try:
                        with contextlib.redirect_stdout(io.StringIO()):
                            gate_runner.verify(SimpleNamespace(policy=a.policy, policy_sha256=a.policy_sha256,
                                receipt=a.receipt, repo=a.repo, key_file=a.key_file,
                                expected_commit=a.expected_commit))
                    except (ValueError, OSError, KeyError, TypeError) as e:
                        fail('signed receipt verification: ' + str(e))
                warnings.append('Signature validity does not establish independent executor isolation or real human approval; configure these outside the Skill.')
            else:
                warnings.append('LOCAL ONLY: receipt can be agent-created; no independent authentication or CI protection claimed.')
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as e:
        fail('gate receipt/policy/revision check failed: ' + str(e))

    # The assurance auditor checks scope/version, required gates, review context,
    # owner separation and all non-delegable root gates. Correlate it with tasks.
    ledgers = []
    for label, p, root in [('root', a.root_ledger, True)] + [
        (f'leaf[{i}]', p, False) for i, p in enumerate(a.leaf_ledger)
    ]:
        try:
            data = json.loads(p.read_text(encoding='utf-8'))
            for problem in assurance_audit.audit(data, final=True, require_root=root):
                fail(f'{label}: {problem}')
            if root and data.get('ledger_level') != 'root': fail('root ledger level is not root')
            if not root and data.get('ledger_level') != 'leaf': fail(f'{label}: ledger level is not leaf')
            if data.get('artifact_revision') != a.expected_commit:
                fail(f'{label}: artifact_revision differs from actual Git commit')
            ledgers.append((label, data))
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as e:
            fail(f'{label}: invalid ledger: {e}')

    if ledgers and (closing_task_id or getattr(a, 'task_id', None)):
        target = closing_task_id or getattr(a, 'task_id', None)
        if ledgers[0][1].get('work_item') != target:
            fail(f'root assurance ledger must identify scoped task {target}')
    if ledgers:
        declared_tier = ledgers[0][1].get('tier')
        highest = max((TIERS.get(t.get('risk'), 2) for t in tasks), default=0)
        if TIERS.get(declared_tier, -1) < highest:
            fail('root assurance tier is lower than highest tracker task risk')
        if highest == 2 and a.mode != 'signed':
            fail('high-risk completion requires signed verification mode; local-only receipt is insufficient')
        if highest >= 1 and a.mode == 'lightweight':
            fail('lightweight declaration is prohibited for standard/high-risk tasks')
        if highest <= 1 and a.mode == 'local':
            warnings.append('Manual gate findings and approvals are declared by agents and remain unauthenticated.')

    req_by_id = {}
    command_gate_ids = set()
    manually_verified = 0
    for label, l in ledgers:
        for req in l.get('requirements', []):
            if not isinstance(req, dict): continue
            rid = req.get('id')
            if isinstance(rid, str):
                if rid in req_by_id: fail(f'duplicate requirement ID across ledgers: {rid}')
                req_by_id[rid] = (label, req, l)
        for gate in l.get('gates', []):
            if not isinstance(gate, dict) or gate.get('required') is not True: continue
            if gate.get('kind') == 'manual' and gate.get('status') == 'PASS':
                manually_verified += 1
            if gate.get('kind') == 'command':
                gid = gate.get('execution_gate_id')
                if a.mode == 'lightweight':
                    warnings.append(f'{label}/{gate.get("id")}: command evidence declared but not executed by the verifier')
                    continue
                if not isinstance(gid, str) or not gid:
                    fail(f'{label}/{gate.get("id")}: required command gate needs execution_gate_id')
                    continue
                if policy is not None and gid not in policy['mandatory_gate_ids']:
                    fail(f'{label}/{gate.get("id")}: execution gate {gid} is not mandatory in approved policy')
                if gate.get('status') != 'PASS':
                    fail(f'{label}/{gate.get("id")}: required execution gate is not PASS')
                parent = gate.get('parent_check')
                if receipt_link and (not isinstance(parent, dict) or parent.get('reference') != receipt_link):
                    fail(f'{label}/{gate.get("id")}: parent evidence not linked to exact receipt SHA-256')
                command_gate_ids.add(gid)

    if policy:
        missing = set(policy['mandatory_gate_ids']) - command_gate_ids
        if missing: fail('approved mandatory execution gates not linked from assurance ledger: ' + ', '.join(sorted(missing)))
    if not command_gate_ids and a.mode != 'lightweight':
        fail('no required command gate links current executable evidence to acceptance ledgers')

    by_id = {t['id']: t for t in all_tasks}
    if closing_task_id and tasks:
        by_id[closing_task_id] = tasks[0]
    for t in tasks:
        name = t['id']
        for field in ('description', 'desired_outcome', 'acceptance_details', 'owner'):
            if not isinstance(t.get(field), str) or not t[field].strip():
                fail(f'{name}: missing {field}')
        state = t['state']
        if state not in CLOSED: fail(f'{name}: unresolved state {state}')
        if state == 'Cancelled':
            if not t['approval_ref']: fail(f'{name}: cancelled without authorized scope-change reference')
            warnings.append(f'{name}: cancellation authorization is a declared reference, not independently authenticated.')
            continue
        if t['source_commit'] != a.expected_commit:
            fail(f'{name}: tracker source commit differs from exact verified commit')
        if a.mode == 'lightweight':
            if not t['evidence_ref']:
                fail(f'{name}: lightweight tracker entry must retain a concrete evidence reference')
        elif t['evidence_ref'] != receipt_link:
            fail(f'{name}: tracker evidence is not linked to exact gate receipt digest')
        if t['risk'] in ('standard', 'high-risk') and (not t['reviewer'] or t['reviewer'] == t['owner']):
            fail(f'{name}: independent reviewer missing or same as implementer')
        if t['risk'] == 'high-risk' and not t['approval_ref']:
            fail(f'{name}: high-risk task has no approval reference')
        for dep in t['dependencies']:
            if dep not in by_id or by_id[dep]['state'] != 'Done':
                fail(f'{name}: dependency {dep} is not Done')
        for rid in t['acceptance']:
            if rid not in req_by_id:
                fail(f'{name}: acceptance ID {rid} absent from submitted ledgers')
                continue
            label, req, ledger = req_by_id[rid]
            gates_by_id = {g['id']: g for g in ledger.get('gates', []) if isinstance(g, dict) and 'id' in g}
            if not any(gates_by_id.get(gid, {}).get('required') is True and
                       gates_by_id[gid].get('status') == 'PASS'
                       for gid in req.get('gate_ids', [])):
                fail(f'{name}: acceptance {rid} lacks passing required assurance gate')

    checks['tasks'] = len(tasks)
    checks['requirements'] = len(req_by_id)
    checks['execution_gate_links'] = len(command_gate_ids)
    checks['manual_gate_attestations'] = manually_verified
    status = 'REJECTED' if errors else ('LIGHTWEIGHT_DECLARED' if a.mode == 'lightweight' else 'SIGNED_RECEIPT_MATCH' if a.mode == 'signed' else 'LOCAL_CONSISTENT')
    return {'status': status, 'expected_commit': a.expected_commit, 'receipt_ref': receipt_link,
            'checks': checks, 'errors': errors, 'warnings': warnings}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db', type=Path, required=True)
    p.add_argument('--root-ledger', type=Path, required=True)
    p.add_argument('--leaf-ledger', type=Path, action='append', default=[])
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--expected-commit', required=True)
    p.add_argument('--policy', type=Path)
    p.add_argument('--policy-sha256')
    p.add_argument('--receipt', type=Path)
    p.add_argument('--mode', choices=['lightweight', 'local', 'signed'], default='local')
    p.add_argument('--task-id', help='Read-only scope to one already completed task (not a close operation)')
    p.add_argument('--key-file', type=Path)
    args = p.parse_args()
    try:
        result = check(args)
    except Exception as e:
        print(json.dumps({'status': 'REJECTED', 'errors': ['unexpected verification failure: ' + str(e)]}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result['status'] != 'REJECTED' else 1


if __name__ == '__main__':
    sys.exit(main())
