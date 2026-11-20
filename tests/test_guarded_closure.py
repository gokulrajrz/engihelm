"""End-to-end local task transition tests (synthetic fixtures, NOT live agents)."""
import json
import sqlite3
import subprocess
import sys
import unittest
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace

import test_unified_completion as fixture_module

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import state_store
import verify_and_close

class GuardedClosureTests(unittest.TestCase):
    def setUp(self):
        # Construct a bona fide passing gate-receipt fixture, with task remaining Verified.
        self.fx=fixture_module.UnifiedCompletionTests(methodName='test_local_small_success_is_honestly_qualified')
        self.fx.setUp()
        self.addCleanup(self.fx.tmp.cleanup)

    def prepare(self,risk='small',signed=False):
        self.fx.build(risk=risk,signed=signed,leave_verified=True)
        return self.args(mode='signed' if signed else 'local',key_file=self.fx.key_file if signed else None)

    def args(self,**patch):
        data=dict(db=self.fx.db,task_id='T-1',expected_version=3,actor='sdlc-orchestrator',
              approval='',root_ledger=self.fx.root_ledger,leaf_ledger=[],repo=self.fx.repo,
              expected_commit=self.fx.head,policy=self.fx.policy,policy_sha256=self.fx.pin,
              receipt=self.fx.receipt,mode='local',key_file=None)
        data.update(patch)
        return SimpleNamespace(**data)

    def state(self):
        with closing(state_store.connect(self.fx.db)) as con:
            return dict(con.execute("SELECT * FROM tasks WHERE id='T-1'").fetchone())

    def test_cli_exposes_the_guarded_transaction(self):
        a=self.prepare()
        p=subprocess.run([sys.executable,str(ROOT/'scripts/verify_and_close.py'),
            '--db',str(a.db),'--task-id',a.task_id,'--expected-version',str(a.expected_version),
            '--actor',a.actor,'--root-ledger',str(a.root_ledger),'--repo',str(a.repo),
            '--expected-commit',a.expected_commit,'--policy',str(a.policy),
            '--policy-sha256',a.policy_sha256,'--receipt',str(a.receipt),'--mode','local'],
            text=True,capture_output=True,timeout=30)
        self.assertEqual(p.returncode,0,p.stderr+p.stdout)
        self.assertEqual(json.loads(p.stdout)['closed'],True)
        self.assertEqual(self.state()['state'],'Done')

    def test_missing_tracker_does_not_reinitialize(self):
        a=self.prepare()
        a.db.unlink()
        with self.assertRaisesRegex(ValueError,'STATE MISSING'):
            verify_and_close.guarded_close(a)
        self.assertFalse(a.db.exists())

    def test_changed_gate_policy_refuses_closure(self):
        a=self.prepare()
        raw=json.loads(a.policy.read_text())
        raw['gates'][0]['stdout_contains']='a different marker'
        a.policy.write_text(json.dumps(raw))
        result=verify_and_close.guarded_close(a)
        self.assertEqual(result['status'],'REJECTED')
        self.assertEqual(self.state()['state'],'Verified')

    def test_closes_once_atomically_and_journals_evidence_hashes(self):
        a=self.prepare()
        result=verify_and_close.guarded_close(a)
        self.assertEqual(result['status'],'LOCAL_CONSISTENT',result)
        self.assertTrue(result['closed'])
        self.assertEqual(self.state()['state'],'Done')
        with closing(state_store.connect(self.fx.db)) as con:
            errors=state_store.verify(con)
            self.assertEqual(errors,[])
            last=json.loads(con.execute('SELECT payload FROM events ORDER BY seq DESC LIMIT 1').fetchone()[0])
            proof=last['closure_proof']
            self.assertEqual(proof['git_revision'],self.fx.head)
            self.assertEqual(proof['decision'],'LOCAL_CONSISTENT')
        self.assertIn('Done',(self.fx.db.parent/'TASKS.md').read_text())

    def test_direct_state_store_cli_done_is_blocked(self):
        self.prepare()
        proc=subprocess.run([sys.executable,str(ROOT/'scripts/state_store.py'),'--db',str(self.fx.db),
            'transition','--id','T-1','--expected-version','3','--state','Done',
            '--actor','sdlc-orchestrator'],capture_output=True,text=True)
        self.assertNotEqual(proc.returncode,0)
        self.assertIn('verify_and_close',proc.stderr)
        self.assertEqual(self.state()['state'],'Verified')

    def test_stale_version_rejected_with_no_write(self):
        a=self.prepare();a.expected_version=2
        with self.assertRaisesRegex(ValueError,'stale task version'):
            verify_and_close.guarded_close(a)
        self.assertEqual(self.state()['version'],3)

    def test_modified_receipt_rejected(self):
        a=self.prepare()
        receipt=json.loads(self.fx.receipt.read_text())
        receipt['all_passed']=False
        self.fx.receipt.write_text(json.dumps(receipt))
        out=verify_and_close.guarded_close(a)
        self.assertEqual(out['status'],'REJECTED')
        self.assertEqual(self.state()['state'],'Verified')

    def test_wrong_acceptance_ledger_rejected(self):
        a=self.prepare()
        ledger=json.loads(self.fx.root_ledger.read_text())
        ledger['requirements']=[ledger['requirements'][0]]
        self.fx.root_ledger.write_text(json.dumps(ledger))
        out=verify_and_close.guarded_close(a)
        self.assertEqual(out['status'],'REJECTED')
        self.assertTrue(any('AC-1 absent' in e for e in out['errors']))
        self.assertEqual(self.state()['state'],'Verified')

    def test_wrong_ledger_task_id_rejected(self):
        a=self.prepare()
        ledger=json.loads(self.fx.root_ledger.read_text())
        ledger['work_item']='OTHER'
        self.fx.root_ledger.write_text(json.dumps(ledger))
        out=verify_and_close.guarded_close(a)
        self.assertEqual(out['status'],'REJECTED')
        self.assertTrue(any('work_item' in e or 'scoped task' in e for e in out['errors']))

    def test_wrong_commit_rejected(self):
        a=self.prepare();a.expected_commit='a'*40
        out=verify_and_close.guarded_close(a)
        self.assertEqual(out['status'],'REJECTED')
        self.assertEqual(self.state()['state'],'Verified')

    def test_open_other_task_does_not_block_task_scoped_close(self):
        a=self.prepare()
        with closing(state_store.connect(self.fx.db)) as con:
            state_store.add(con,SimpleNamespace(id='T-2',title='Separate unfinished work',
                owner='frontend-engineer',acceptance='AC-2',dependencies='',next_action='Implement UI',
                actor='sdlc-orchestrator',risk='standard',description='Unrelated UI task',
                outcome='User flow improved',acceptance_details='AC-2: UI rendering',type='feature',
                priority='normal',plan='Use existing layout'))
        out=verify_and_close.guarded_close(a)
        self.assertEqual(out['status'],'LOCAL_CONSISTENT',out)
        with closing(state_store.connect(self.fx.db)) as con:
            self.assertEqual(dict(con.execute("SELECT id,state FROM tasks WHERE id='T-2'").fetchone())['state'],'Ready')

    def test_open_dependency_refuses_done(self):
        a=self.prepare()
        # Add the dep through the API and explicitly amend the original scope to
        # invalidate evidence: attempting a stale closure must fail, never be Done.
        with closing(state_store.connect(self.fx.db)) as con:
            state_store.add(con,SimpleNamespace(id='DEP',title='Dependency',owner='eng',
                acceptance='DEP-1',dependencies='',next_action='Implement prerequisite',actor='director',
                risk='small',description='Prerequisite',outcome='Ready',
                acceptance_details='DEP-1: complete',type='task',priority='normal',plan=''))
            # Construct a pre-existing dependency fixture plus matching journal event
            # via a new task, rather than mutating canonical task rows directly.
            state_store.add(con,SimpleNamespace(id='CHILD',title='Child depends on DEP',owner='eng',
                acceptance='AC-1',dependencies='DEP',next_action='Review',actor='director',
                risk='small',description='Child',outcome='Verified child',
                acceptance_details='AC-1',type='task',priority='normal',plan=''))
            state_store.transition(con,SimpleNamespace(id='CHILD',state='In Progress',actor='eng',
                expected_version=1,next_action='test',commit='',evidence='',reviewer='',approval='',
                blocked_reason='',unblock_owner='',unblock_action=''))
            child = self.state()
            state_store.transition(con,SimpleNamespace(id='CHILD',state='Verified',actor='eng',
                expected_version=2,next_action='close',commit=child['source_commit'],evidence=child['evidence_ref'],
                reviewer='',approval='',blocked_reason='',unblock_owner='',unblock_action=''))
        # Point the task-specific root ledger at CHILD for a valid scoping attempt.
        ledger=json.loads(self.fx.root_ledger.read_text());ledger['work_item']='CHILD'
        self.fx.root_ledger.write_text(json.dumps(ledger))
        a.task_id='CHILD'
        out=verify_and_close.guarded_close(a)
        self.assertEqual(out['status'],'REJECTED')
        self.assertTrue(any('dependency DEP' in e for e in out['errors']),out)

    def test_orchestrator_owned_standard_task_can_close_with_independent_reviewer(self):
        self.fx.build(risk='standard',leave_verified=True,owner='sdlc-orchestrator')
        a=self.args()
        result=verify_and_close.guarded_close(a)
        self.assertEqual(result['status'],'LOCAL_CONSISTENT',result)
        self.assertEqual(self.state()['state'],'Done')

    def test_high_risk_signed_check_and_approval(self):
        a=self.prepare(risk='high-risk',signed=True)
        a.approval='approved-change-123'
        out=verify_and_close.guarded_close(a)
        self.assertEqual(out['status'],'SIGNED_RECEIPT_MATCH',out)
        self.assertEqual(self.state()['state'],'Done')

    def test_high_risk_missing_approval_refuses_done(self):
        a=self.prepare(risk='high-risk',signed=True)
        out=verify_and_close.guarded_close(a)
        self.assertEqual(out['status'],'REJECTED')
        self.assertEqual(self.state()['state'],'Verified')

if __name__=='__main__':unittest.main()
