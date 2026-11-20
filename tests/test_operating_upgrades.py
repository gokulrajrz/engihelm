"""Executable module integration/adversarial tests; not actual LLM behavior tests."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PY=sys.executable

def cmd(*args, cwd=None):
    return subprocess.run([str(a) for a in args],capture_output=True,text=True,cwd=cwd,timeout=35)

def write(path, data):
    path.write_text(json.dumps(data,indent=2))

class DurableJournalTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.db=self.root/'tasks.db'
        self.tool=ROOT/'scripts/state_store.py'
        self.assertEqual(self.run_db('init').returncode,0)
    def tearDown(self):self.temp.cleanup()
    def run_db(self,*args):return cmd(PY,self.tool,'--db',self.db,*args)
    def add(self,id,owner='eng',deps='',risk='standard'):
        return self.run_db('add','--id',id,'--title','Verified change','--owner',owner,
                           '--acceptance','AC-1,AC-2','--actor','director','--risk',risk,
                           '--dependencies',deps,'--next-action','implement',
                           '--description','Regression in user flow with measurable impact',
                           '--outcome','Feature behaves as specified',
                           '--acceptance-details','AC-1: expected behavior; AC-2: regression passes')
    def transition(self,id,ver,state,**kw):
        args=['transition','--id',id,'--expected-version',str(ver),'--state',state,
              '--actor','director','--next-action',kw.get('next_action','review')]
        for k,v in kw.items():
            if k=='next_action':continue
            args.extend(['--'+k.replace('_','-'),str(v)])
        return self.run_db(*args)
    def test_conflict_recovery_and_blocked_fields(self):
        self.assertEqual(self.add('T1').returncode,0)
        self.assertEqual(self.transition('T1',1,'In Progress').returncode,0)
        conflict=self.transition('T1',1,'In Review')
        self.assertNotEqual(conflict.returncode,0)
        self.assertIn('conflict',conflict.stderr)
        self.assertNotEqual(self.transition('T1',2,'Blocked').returncode,0)
        self.assertEqual(self.transition('T1',2,'Blocked',blocked_reason='Dependency missing',unblock_owner='tech-lead',unblock_action='collect input').returncode,0)
        tasks=json.loads(self.run_db('resume').stdout)
        self.assertEqual(tasks[0]['state'],'Blocked')
        self.assertEqual(tasks[0]['unblock_owner'],'tech-lead')
        self.assertEqual(self.run_db('verify').returncode,0)
    def test_done_requires_verified_and_independent_reviewer(self):
        self.assertEqual(self.add('T1').returncode,0)
        self.assertNotEqual(self.transition('T1',1,'Done',commit='abc',evidence='ci-1',reviewer='qa').returncode,0)
        self.assertEqual(self.transition('T1',1,'In Progress').returncode,0)
        self.assertNotEqual(self.transition('T1',2,'Verified',commit='abc',evidence='ci-1',reviewer='eng').returncode,0)
        self.assertEqual(self.transition('T1',2,'Verified',commit='abc',evidence='ci-1',reviewer='qa').returncode,0)
        blocked=self.transition('T1',3,'Done',next_action='')
        self.assertNotEqual(blocked.returncode,0)
        self.assertIn('verify_and_close',blocked.stderr)
        self.assertEqual(json.loads(self.run_db('show').stdout)[0]['state'],'Verified')
        self.assertNotEqual(self.run_db('init').returncode,0)
    def test_unresolved_dependency_blocks_done(self):
        self.assertEqual(self.add('D',risk='small').returncode,0)
        self.assertEqual(self.add('T',deps='D',risk='small').returncode,0)
        self.assertEqual(self.transition('T',1,'In Progress').returncode,0)
        self.assertEqual(self.transition('T',2,'Verified',commit='abc',evidence='ci-1').returncode,0)
        result=self.transition('T',3,'Done')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('verify_and_close',result.stderr)
    def test_scope_amendment_invalidates_old_evidence_and_audit(self):
        self.assertEqual(self.add('T').returncode,0)
        self.assertEqual(self.transition('T',1,'In Progress').returncode,0)
        self.assertEqual(self.transition('T',2,'Verified',commit='abc',evidence='ci',reviewer='qa').returncode,0)
        self.assertNotEqual(self.transition('T',3,'Done',next_action='').returncode,0)
        self.assertNotEqual(self.run_db('audit').returncode,0)
        self.assertEqual(self.run_db('amend','--id','T','--expected-version','3','--acceptance','AC-3',
                      '--reason','User changed requirements','--next-action','implement new scope','--actor','director').returncode,0)
        row=json.loads(self.run_db('show').stdout)[0]
        self.assertEqual(row['state'],'Ready');self.assertEqual(row['acceptance'],['AC-3'])
        self.assertEqual(row['evidence_ref'],'')
        self.assertEqual(self.run_db('verify').returncode,0)
        self.assertEqual(self.run_db('audit').returncode,1)

    def test_local_hash_chain_detects_tamper(self):
        import sqlite3
        self.add('T')
        con=sqlite3.connect(self.db)
        con.execute("UPDATE events SET actor='fraud' WHERE seq=1")
        con.commit();con.close()
        result=self.run_db('verify')
        self.assertEqual(result.returncode,1)
        self.assertIn('changed content',result.stdout)

class ApprovedGateRunnerTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.repo=self.root/'repo';self.repo.mkdir()
        for a in (['init','-q'],['config','user.email','test@example.invalid'],['config','user.name','Test']):
            p=cmd('git',*a,cwd=self.repo)
            assert p.returncode==0,p.stderr
        (self.repo/'main.py').write_text('print("PASS-MARKER")\n')
        for a in (['add','main.py'],['commit','-qm','initial']):
            p=cmd('git',*a,cwd=self.repo);assert p.returncode==0,p.stderr
        self.head=cmd('git','rev-parse','HEAD',cwd=self.repo).stdout.strip()
        self.policy=self.root/'approved.json'
        self.gates=[{'id':'PY','argv':[PY,'main.py'],'expected_exit':0,'timeout_seconds':4,'stdout_contains':'PASS-MARKER'}]
        self.set_policy(self.gates)
        self.key=self.root/'signing.key';self.key.write_bytes(os.urandom(64));self.key.chmod(0o600)
        self.receipt=self.root/'evidence.json';self.tool=ROOT/'scripts/gate_runner.py'
    def tearDown(self):self.temp.cleanup()
    def set_policy(self,gates):
        write(self.policy,{'version':1,'mandatory_gate_ids':[g['id'] for g in gates],'gates':gates})
        import hashlib
        self.hash=hashlib.sha256(self.policy.read_bytes()).hexdigest()
    def run_gate(self,*more, policy_hash=None, receipt=None, key=None):
        args=[PY,self.tool,'run','--policy',self.policy,'--policy-sha256',policy_hash or self.hash,
              '--repo',self.repo,'--receipt',receipt or self.receipt,'--allow-run']
        if key is not False:args.extend(['--key-file',key or self.key,'--assert-executor-isolation'])
        return cmd(*args,*more)
    def verify(self,*more, receipt=None, key=None, policy_hash=None, commit=None):
        args=[PY,self.tool,'verify','--policy',self.policy,'--policy-sha256',policy_hash or self.hash,
              '--repo',self.repo,'--receipt',receipt or self.receipt,'--expected-commit',commit or self.head]
        if key is not False:args.extend(['--key-file',key or self.key])
        return cmd(*args,*more)
    def test_signing_without_isolation_assertion_rejected(self):
        args=[PY,self.tool,'run','--policy',self.policy,'--policy-sha256',self.hash,'--repo',self.repo,
              '--receipt',self.receipt,'--allow-run','--key-file',self.key]
        self.assertEqual(cmd(*args).returncode,2)

    def test_good_signed_evidence(self):
        a=self.run_gate();self.assertEqual(a.returncode,0,a.stderr)
        x=json.loads(self.receipt.read_text())
        self.assertTrue(x['all_passed']);self.assertEqual(x['repo_head'],self.head)
        self.assertEqual(self.verify().returncode,0)
    def test_corrupted_signature_or_wrong_commit_rejected(self):
        self.assertEqual(self.run_gate().returncode,0)
        tampered=json.loads(self.receipt.read_text());tampered['results'][0]['status']='FAIL'
        self.receipt.write_text(json.dumps(tampered))
        self.assertNotEqual(self.verify().returncode,0)
        self.assertIn('signature',self.verify().stderr)
    def test_receipt_rejected_after_repository_changes(self):
        self.assertEqual(self.run_gate().returncode,0)
        (self.repo/'main.py').write_text('print("CHANGED")')
        self.assertNotEqual(self.verify().returncode,0)

    def test_unsigned_does_not_verify(self):
        self.assertEqual(self.run_gate(key=False).returncode,0)
        self.assertNotEqual(self.verify().returncode,0)
    def test_wrong_commit_policy_and_dirty_repo(self):
        self.assertEqual(self.run_gate(policy_hash='0'*64).returncode,2)
        (self.repo/'uncommitted.txt').write_text('dirty')
        self.assertNotEqual(self.run_gate().returncode,0)
        (self.repo/'uncommitted.txt').unlink()
        self.assertEqual(self.run_gate().returncode,0)
        self.assertNotEqual(self.verify(commit='f'*40).returncode,0)
        self.set_policy([{'id':'PY','argv':[PY,'-c','print(1)'],'expected_exit':0,'timeout_seconds':4}])
        self.assertNotEqual(self.verify(policy_hash='0'*64).returncode,0)
    def test_failed_check_fails_and_cannot_verify(self):
        self.set_policy([{'id':'FAIL','argv':[PY,'-c','import sys;sys.exit(3)'],'expected_exit':0,'timeout_seconds':4}])
        r=self.run_gate();self.assertEqual(r.returncode,1,r.stderr)
        self.assertFalse(json.loads(self.receipt.read_text())['all_passed'])
        self.assertNotEqual(self.verify().returncode,0)
    def test_timeout_and_signer_permissions(self):
        self.set_policy([{'id':'TIMEOUT','argv':[PY,'-c','import time;time.sleep(5)'],'expected_exit':0,'timeout_seconds':1}])
        self.assertEqual(self.run_gate().returncode,1)
        self.assertEqual(json.loads(self.receipt.read_text())['results'][0]['status'],'TIMEOUT')
        self.key.chmod(0o644)
        self.assertNotEqual(self.verify().returncode,0)
    def test_key_inside_project_rejected(self):
        copy=self.repo/'key';copy.write_bytes(self.key.read_bytes());copy.chmod(0o600)
        self.assertNotEqual(self.run_gate(key=copy).returncode,0)
    def test_missing_allow_run_rejected(self):
        args=[PY,self.tool,'run','--policy',self.policy,'--policy-sha256',self.hash,'--repo',self.repo,'--receipt',self.receipt]
        self.assertEqual(cmd(*args).returncode,2)
    def test_modified_policy_rejected_before_execution(self):
        original=self.hash
        self.set_policy([{'id':'MALICIOUS','argv':[PY,'-c','print("NO")'],'expected_exit':0,'timeout_seconds':2}])
        self.assertEqual(self.run_gate(policy_hash=original).returncode,2)
        self.assertFalse(self.receipt.exists())

class BehavioralComparisonTest(unittest.TestCase):
    def test_valid_report_pair_and_failure_classification(self):
        sys.path.insert(0,str(ROOT/'scripts'))
        from behavior_eval import evaluate
        manifest={'version':1,'scenarios':[{'id':'one','prompt':'task','checks':[{'id':'a'}]}]}
        import hashlib
        input_hash=hashlib.sha256(json.dumps(manifest['scenarios'][0],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
        def r(mode,verdict):return {'mode':mode,'runs':[{'scenario_id':'one','run_id':mode+'1','model_id':'same','runtime':'same',
                 'source_revision':'abc','input_revision':input_hash,'raw_trace_ref':mode+'trace','simulated':False,
                 'observations':{'a':{'verdict':verdict,'evidence_ref':'external-log-1' if verdict=='pass' else ''}}}]}
        result=evaluate(manifest,r('baseline','fail'),r('skill','pass'))
        self.assertTrue(result['valid_comparison']);self.assertEqual(result['summary']['improvements'],1)
        corrupted=r('skill','pass');corrupted['runs'][0]['simulated']=True
        self.assertFalse(evaluate(manifest,r('baseline','fail'),corrupted)['valid_comparison'])
        corrupted=r('skill','pass');corrupted['runs'][0]['observations']['a']['evidence_ref']=''
        self.assertEqual(evaluate(manifest,r('baseline','fail'),corrupted)['summary']['skill_all_pass'],0)
    def test_real_scenario_manifest_coverage(self):
        data=json.loads((ROOT/'assets/behavioral/scenarios.json').read_text())
        self.assertGreaterEqual(len(data['scenarios']),6)
        self.assertEqual(len({s['id'] for s in data['scenarios']}),len(data['scenarios']))

class BudgetPlannerTest(unittest.TestCase):
    def test_budget_and_independent_review(self):
        sys.path.insert(0,str(ROOT/'scripts'))
        from delegation_plan import plan
        models=[{'id':'tiny','tier':'light','context_tokens':30000,'usd_per_1m_input':1,'usd_per_1m_output':1},
                {'id':'medium','tier':'balanced','context_tokens':30000,'usd_per_1m_input':2,'usd_per_1m_output':2},
                {'id':'strong','tier':'deep','context_tokens':100000,'usd_per_1m_input':4,'usd_per_1m_output':4}]
        spec={'models':models,'budget_usd':1,'max_parallel':2,'tasks':[{'id':'T','risk':'high-risk','complexity':'light','input_tokens':10000,'output_tokens':1000}]}
        result=plan(spec)
        self.assertTrue(result['all_assignable'])
        self.assertEqual(len(result['assignments']),2)
        self.assertTrue(all(x['model_id']=='strong' for x in result['assignments']))
        spec['budget_usd']=0.06
        result=plan(spec)
        self.assertFalse(result['all_assignable'])
        self.assertIn('budget',result['assignments'][1]['reason'])
        spec['budget_usd']=1;spec['models']=models[:2]
        self.assertFalse(plan(spec)['all_assignable'])

class ActualTrialAdapterContractTest(unittest.TestCase):
    def test_pairs_use_separate_contexts_and_baseline_gets_no_skill(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            runner=root/'adapter.py'
            runner.write_text('''#!/usr/bin/env python3
import argparse,json,hashlib
from pathlib import Path
p=argparse.ArgumentParser()
for name in ('mode','scenario','output','workdir'):p.add_argument('--'+name,required=True)
p.add_argument('--skill-root')
a=p.parse_args()
assert (a.mode=='skill')==(a.skill_root is not None)
s=json.loads(Path(a.scenario).read_text())
Path(a.output).write_text(json.dumps({'scenario_id':s['id'],'run_id':a.mode+'-fixture','model_id':'stub',
 'runtime':'stub','source_revision':'abc','input_revision':hashlib.sha256(json.dumps(s,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest(),'raw_trace_ref':a.mode+'-trace',
 'simulated':True,'observations':{x['id']:{'verdict':'unverified','evidence_ref':''} for x in s['checks']}}))
''')
            runner.chmod(0o755)
            output=root/'runs'
            r=cmd(PY,ROOT/'scripts/behavior_trials.py','--manifest',ROOT/'assets/behavioral/scenarios.json',
                  '--runner',runner,'--skill-root',ROOT,'--output-dir',output,'--timeout-seconds','20')
            self.assertEqual(r.returncode,0,r.stderr)
            for mode in ('baseline','skill'):
                result=json.loads((output/f'{mode}.json').read_text())
                self.assertEqual(len(result['runs']),7)
                self.assertTrue(all(x['simulated'] for x in result['runs']))
            # The evaluator correctly refuses fixtures as proof of live Skill behavior.
            r=cmd(PY,ROOT/'scripts/behavior_eval.py','--manifest',ROOT/'assets/behavioral/scenarios.json',
                  '--baseline',output/'baseline.json','--skill',output/'skill.json')
            self.assertEqual(r.returncode,1)
            self.assertIn('simulated',r.stdout)

class InstalledModulesTest(unittest.TestCase):
    def test_install_complete_optional_modules(self):
        for runtime in ('codex','antigravity','opencode','skill-only'):
            with self.subTest(runtime=runtime),tempfile.TemporaryDirectory() as tmp:
                r=cmd(PY,ROOT/'scripts/install.py','--runtime',runtime,'--project',tmp,'--apply')
                self.assertEqual(r.returncode,0,r.stderr)
                base='.opencode/skills' if runtime=='opencode' else '.agents/skills'
                inst=Path(tmp)/base/'engihelm'
                for file in ('scripts/gate_runner.py','scripts/behavior_eval.py','scripts/behavior_trials.py','scripts/state_store.py','scripts/delegation_plan.py',
                             'assets/behavioral/scenarios.json','assets/ci/github-required-check.example.yml',
                             'references/implementation-methods.md','references/enforcement.md'):
                    self.assertTrue((inst/file).is_file(),file)
                p=cmd(PY,inst/'scripts/gate_runner.py','digest','--policy',inst/'assets/templates/approved-gates.example.json')
                self.assertEqual(p.returncode,0,p.stderr)

if __name__=='__main__':unittest.main()
