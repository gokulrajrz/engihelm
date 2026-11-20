"""Adversarial integration checks for the ONE final-decision entrypoint."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from contextlib import closing
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import assurance_audit
import completion_decision
import gate_runner
import state_store


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()


def gate(id_, req, kind, commit, receipt_ref, *, mode='same-context'):
    evidence = lambda name: dict(result='PASS', reference=(receipt_ref if kind == 'command' and name == 'parent' else 'local-observation'),
                                 observed='Checked required outcome', scope_revision=1,
                                 artifact_revision=commit, context_id=('ctx-parent' if name == 'parent' else 'ctx-owner'))
    g = dict(id=id_, requirement=req, owner='sdlc-orchestrator', required=True,
             kind=kind, check=('test-run' if kind == 'command' else 'manual: inspect actual evidence'),
             expect='Observable requirement satisfied', status='PASS', self_check=evidence('self'),
             parent_check={**evidence('parent'), 'mode': mode, 'verifier':'reviewer-agent'})
    if kind == 'command':g['execution_gate_id']='UNIT'
    return g


class UnifiedCompletionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.repo = self.base/'repo';self.repo.mkdir()
        subprocess.run(['git', '-C', str(self.repo), 'init', '-q'], check=True)
        subprocess.run(['git', '-C', str(self.repo), 'config', 'user.email', 'test@example.test'], check=True)
        subprocess.run(['git', '-C', str(self.repo), 'config', 'user.name', 'Test'], check=True)
        (self.repo/'source.txt').write_text('hello\n')
        (self.repo/'.gitignore').write_text('docs/sdlc/\n')
        subprocess.run(['git', '-C', str(self.repo), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(self.repo), 'commit', '-qm', 'Test base'], check=True)
        self.head = git(self.repo, 'rev-parse', 'HEAD')
        self.policy = self.base/'policy.json'
        self.policy.write_text(json.dumps({'version':1,'mandatory_gate_ids':['UNIT'],'gates':[
            {'id':'UNIT','argv':[sys.executable,'-c',"print('ok')"],
             'expected_exit':0,'timeout_seconds':20,'stdout_contains':'ok'}]}))
        self.pin = hashlib.sha256(self.policy.read_bytes()).hexdigest()
        self.receipt = self.base/'receipt.json'
        self.db = self.repo/'docs'/'sdlc'/'state.db'
        state_store.initialize(self.db)
        self.key_file = self.base/'external-signing.key'
        self.root_ledger = self.base/'root.json'

    def build(self, *, risk='small', signed=False, root_tier=None, evidence_override=None, leave_verified=False, owner='backend-engineer'):
        if signed:
            self.key_file.write_bytes(os.urandom(48))
            os.chmod(self.key_file, 0o600)
        status = gate_runner.run(SimpleNamespace(repo=self.repo, policy=self.policy, policy_sha256=self.pin,
            receipt=self.receipt, allow_run=True, key_file=(self.key_file if signed else None),
            assert_executor_isolation=signed))
        self.assertEqual(status,0)
        receipt_ref='receipt-sha256:'+hashlib.sha256(self.receipt.read_bytes()).hexdigest()
        with closing(state_store.connect(self.db)) as con, con:
            state_store.add(con,SimpleNamespace(id='T-1',title='Fix bug',owner=owner,
                acceptance='AC-1',dependencies='',next_action='Reproduce error',actor='sdlc-orchestrator',risk=risk,
                description='Bug in a reversible local function', outcome='Correct user behavior',
                acceptance_details='AC-1: observed regression must pass',type='bug',priority='normal',plan='Minimal fix'))
            state_store.transition(con,SimpleNamespace(id='T-1',state='In Progress',actor='backend-engineer',
                expected_version=1,next_action='Test fix',commit='',evidence='',reviewer='',approval='',
                blocked_reason='',unblock_owner='',unblock_action=''))
            state_store.transition(con,SimpleNamespace(id='T-1',state='Verified',actor='backend-engineer',
                expected_version=2,next_action='Obtain signoff',commit=self.head,evidence=evidence_override or receipt_ref,
                reviewer=('code-reviewer' if risk != 'small' else ''),approval='',
                blocked_reason='',unblock_owner='',unblock_action=''))
            if not leave_verified:
                state_store.transition(con,SimpleNamespace(id='T-1',state='Done',actor='sdlc-orchestrator',
                expected_version=3,next_action='',commit='',evidence='',reviewer='',
                approval=('authorized-approval-reference' if risk=='high-risk' else ''),
                blocked_reason='',unblock_owner='',unblock_action=''),
                verified_close=True,closure_proof={'decision':'LOCAL_CONSISTENT','root_ledger_sha256':'test-fixture-only'})
        tier = root_tier or risk
        root_ids = (sorted(assurance_audit.ROOT_GATES) if tier!='small' else ['ROOT-TRACK'])
        mode='independent' if tier=='high-risk' else 'same-context'
        gates=[gate(g,'R-ROOT','manual',self.head,receipt_ref,mode=mode) for g in root_ids]
        gates.append(gate('G-AC1','AC-1','command',self.head,receipt_ref,mode=mode))
        ledger={'work_item':'T-1','revision':1,'ledger_level':'root','tier':tier,
                'owner':'sdlc-orchestrator','artifact_revision':self.head,'final_claim':'COMPLETE',
                'requirements':[{'id':'R-ROOT','outcome':'Orchestrator reconciled all work','gate_ids':root_ids},
                                {'id':'AC-1','outcome':'Original acceptance is satisfied','gate_ids':['G-AC1']}],
                'gates':gates,'approvals':{'required':False}}
        self.root_ledger.write_text(json.dumps(ledger))
        return ledger,receipt_ref

    def decision(self, *, mode='local', key_file=None):
        return completion_decision.check(SimpleNamespace(db=self.db,root_ledger=self.root_ledger,
            leaf_ledger=[],repo=self.repo,expected_commit=self.head,
            policy=self.policy,policy_sha256=self.pin,receipt=self.receipt,
            mode=mode,key_file=key_file))

    def test_local_small_success_is_honestly_qualified(self):
        self.build()
        result=self.decision()
        self.assertEqual(result['status'],'LOCAL_CONSISTENT',result)
        self.assertTrue(any('LOCAL ONLY' in w for w in result['warnings']))

    def test_small_lightweight_is_explicitly_unverified_and_skips_receipt(self):
        self.build()
        self.receipt.unlink()
        self.policy.unlink()
        result=self.decision(mode='lightweight')
        self.assertEqual(result['status'],'LIGHTWEIGHT_DECLARED',result)
        self.assertTrue(any('not authenticated' in w for w in result['warnings']))

    def test_standard_cannot_bypass_checks_in_lightweight_mode(self):
        self.build(risk='standard')
        result=self.decision(mode='lightweight')
        self.assertEqual(result['status'],'REJECTED')
        self.assertTrue(any('prohibited for standard' in e for e in result['errors']))

    def test_standard_success_with_full_root_gates(self):
        self.build(risk='standard')
        result=self.decision()
        self.assertEqual(result['status'],'LOCAL_CONSISTENT',result)

    def test_standard_missing_non_delegable_gate_rejected(self):
        l,_=self.build(risk='standard')
        l['gates']=[g for g in l['gates'] if g['id']!='ROOT-REQ']
        self.root_ledger.write_text(json.dumps(l))
        self.assertTrue(any('mandatory root gate' in e or 'missing director-owned' in e for e in self.decision()['errors']))

    def test_failure_when_receipt_not_linked_to_tracker(self):
        self.build(evidence_override='fake-success')
        r=self.decision()
        self.assertEqual(r['status'],'REJECTED')
        self.assertTrue(any('tracker evidence' in e for e in r['errors']))

    def test_failure_when_receipt_changed_after_linking(self):
        self.build()
        data=json.loads(self.receipt.read_text());data['all_passed']=False
        self.receipt.write_text(json.dumps(data))
        self.assertEqual(self.decision()['status'],'REJECTED')

    def test_failure_when_root_command_gate_not_linked(self):
        l,_=self.build()
        l['gates'][-1]['parent_check']['reference']='fake-result'
        self.root_ledger.write_text(json.dumps(l))
        self.assertTrue(any('parent evidence not linked' in e for e in self.decision()['errors']))

    def test_failure_when_approval_or_risk_downgraded(self):
        self.build(risk='standard',root_tier='small')
        self.assertTrue(any('tier is lower' in e for e in self.decision()['errors']))

    def test_failure_when_requirement_missing(self):
        l,_=self.build()
        l['requirements']=l['requirements'][:1]
        self.root_ledger.write_text(json.dumps(l))
        self.assertTrue(any('AC-1 absent' in e for e in self.decision()['errors']))

    def test_failure_when_git_is_dirty(self):
        self.build()
        (self.repo/'source.txt').write_text('new code\n')
        self.assertTrue(any('dirty' in e for e in self.decision()['errors']))

    def test_failure_when_tracker_missing(self):
        self.build()
        self.db.unlink()
        r=self.decision()
        self.assertEqual(r['status'],'REJECTED')
        self.assertTrue(any('STOP' in e for e in r['errors']))
        self.assertFalse(self.db.exists())

    def test_high_risk_requires_signed_receipt(self):
        self.build(risk='high-risk')
        self.assertTrue(any('high-risk completion requires signed' in e for e in self.decision()['errors']))

    def test_signed_mode_verifies_cryptography_but_not_isolation(self):
        self.build(risk='high-risk',signed=True)
        r=self.decision(mode='signed',key_file=self.key_file)
        self.assertEqual(r['status'],'SIGNED_RECEIPT_MATCH',r)
        self.assertTrue(any('isolation' in w for w in r['warnings']))

    def test_signed_mode_wrong_key_rejected(self):
        self.build(signed=True)
        wrong=self.base/'wrong.key';wrong.write_bytes(os.urandom(48));os.chmod(wrong,0o600)
        self.assertTrue(any('signed receipt verification' in e for e in self.decision(mode='signed',key_file=wrong)['errors']))

    def test_unjournaled_sqlite_title_edit_rejected(self):
        self.build()
        with closing(state_store.connect(self.db)) as c, c:
            c.execute("UPDATE tasks SET title='fabricated' WHERE id='T-1'")
            c.commit()
        result=self.decision()
        self.assertEqual(result['status'],'REJECTED')
        self.assertTrue(any('title differs from replayed' in e for e in result['errors']))


if __name__=='__main__':unittest.main()
