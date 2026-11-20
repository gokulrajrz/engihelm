#!/usr/bin/env python3
"""Guarded per-task closure using one SQLite transaction and completion decision.

Fail closed on stale versions, changed Git revision, invalid acceptance ledgers,
missing/invalid gate receipts or unresolved dependencies. This is a *local*
application control, NOT a tamper-proof security boundary if an agent can modify
this script, state.db, policies or signing material directly.
"""
import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

import completion_decision
import gate_runner
import state_store


def guarded_close(a):
    if not a.db.is_file():
        raise ValueError(state_store.missing_message(a.db))
    con = state_store.connect(a.db)
    try:
        # Serializes writers from reading version to applying the Done transition.
        con.execute('BEGIN IMMEDIATE')
        before = con.execute('SELECT * FROM tasks WHERE id=?',(a.task_id,)).fetchone()
        if before is None:
            raise ValueError(f'unknown task {a.task_id}')
        if before['version'] != a.expected_version:
            raise ValueError(f'stale task version: expected {a.expected_version}, current {before["version"]}')
        if before['state'] != 'Verified':
            raise ValueError('task must be Verified before guarded Done transition')
        if not a.actor or not a.actor.strip():
            raise ValueError('actor must identify the responsible closer')
        # Reject ledger/receipt/policy swaps between verification and committed closure.
        artifacts=[a.root_ledger,*a.leaf_ledger]
        if a.mode != 'lightweight':
            artifacts.extend((a.policy,a.receipt))
        before_digests={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in artifacts}
        decision = completion_decision.check(a, tracker_con=con,
            closing_task_id=a.task_id, closing_approval=a.approval)
        if decision['status'] == 'REJECTED':
            con.rollback()
            return decision
        if any(hashlib.sha256(p.read_bytes()).hexdigest()!=before_digests[str(p.resolve())] for p in artifacts):
            raise ValueError('ledger, policy or receipt changed during verification; stop and retry')
        if before['risk'] == 'high-risk' and decision['status'] != 'SIGNED_RECEIPT_MATCH':
            raise ValueError('high-risk closure requires passing signed receipt decision')
        # The check can take time. Re-read Git before modifying canonical state.
        after_head,clean = gate_runner.git_state(a.repo.resolve())
        if after_head != a.expected_commit or not clean:
            raise ValueError('Git revision/worktree changed after completion decision')
        if any(hashlib.sha256(p.read_bytes()).hexdigest()!=before_digests[str(p.resolve())] for p in artifacts):
            raise ValueError('verification inputs changed before commit')
        proof={'decision':decision['status'],
            'root_ledger_sha256':before_digests[str(a.root_ledger.resolve())],
            'leaf_ledger_sha256':[before_digests[str(x.resolve())] for x in a.leaf_ledger],
            'receipt_ref':decision.get('receipt_ref'),
            'policy_sha256':a.policy_sha256,
            'git_revision':a.expected_commit}
        state_store.transition(con, SimpleNamespace(id=a.task_id,state='Done',
            expected_version=a.expected_version,actor=a.actor,next_action='',
            commit='',evidence='',reviewer='',approval=a.approval or '',
            blocked_reason='',unblock_owner='',unblock_action=''),
            verified_close=True,transaction_open=True,closure_proof=proof)
        # All state checks and the write are in a single SQLite transaction.
        con.commit()
        try:
            state_store.report(con,a.db.parent/'TASKS.md')
        except OSError as err:
            decision['warnings'].append('Done committed, but TASKS.md generation failed: '+str(err))
        return {**decision,'task_id':a.task_id,'task_version':a.expected_version+1,
                'closed':True,'note':'Locally guarded transition; not external CI authorization'}
    finally:
        if con.in_transaction:con.rollback()
        con.close()


def cli(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db',type=Path,required=True)
    p.add_argument('--task-id',required=True)
    p.add_argument('--expected-version',type=int,required=True)
    p.add_argument('--actor',required=True)
    p.add_argument('--approval',default='',help='Required high-risk authorization reference; not authenticated here')
    p.add_argument('--root-ledger',type=Path,required=True,help='Task-scoped orchestrator root ledger, work_item must equal task ID')
    p.add_argument('--leaf-ledger',type=Path,action='append',default=[])
    p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--expected-commit',required=True)
    p.add_argument('--policy',type=Path)
    p.add_argument('--policy-sha256')
    p.add_argument('--receipt',type=Path)
    p.add_argument('--mode',choices=('lightweight','local','signed'),default='local')
    p.add_argument('--key-file',type=Path)
    a=p.parse_args(argv)
    try:
        result=guarded_close(a)
    except (ValueError,sqlite3.Error,OSError,TypeError,KeyError) as exc:
        result={'status':'REJECTED','closed':False,'errors':[str(exc)]}
    print(json.dumps(result,indent=2))
    return 0 if result.get('closed') is True else 1

if __name__=='__main__':sys.exit(cli())
