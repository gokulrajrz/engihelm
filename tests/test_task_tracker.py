"""Task tracking discipline: positive and negative audit scenarios."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from task_tracker_audit import audit


def sample():
    return json.loads((ROOT / 'assets/templates/task-tracker.json').read_text())


def closed(doc):
    row = doc['items'][0]
    row['state'] = 'Done'
    row['evidence_refs'] = ['ci/build-13']
    row['closure'] = {
        'accepted_by': 'sdlc-orchestrator',
        'accepted_at': '2026-11-19T10:00:00Z',
        'self_check_ref': 'ci/build-13',
        'parent_check_ref': 'ci/review-14',
        'scope_revision': row['scope_revision'],
        'artifact_revision': row['artifact_revision'],
        'release_in_scope': False,
    }
    return row


class TaskTrackerTests(unittest.TestCase):
    def test_ready_template_structurally_valid_but_not_complete(self):
        doc=sample()
        self.assertEqual(audit(doc), [])
        self.assertTrue(any('unresolved' in p for p in audit(doc, True)))

    def test_good_done(self):
        doc=sample();closed(doc)
        self.assertEqual(audit(doc, True), [])

    def test_done_without_evidence_fails(self):
        doc=sample();closed(doc)
        doc['items'][0]['evidence_refs']=[]
        self.assertTrue(any('without evidence' in p for p in audit(doc, True)))

    def test_blocked_needs_owner_reason_and_action(self):
        doc=sample();row=doc['items'][0]
        row['blocked']=True;row['blocker']={'reason':'API not ready'}
        self.assertTrue(any('unblock_action' in p for p in audit(doc)))

    def test_done_cannot_be_blocked(self):
        doc=sample();row=closed(doc)
        row['blocked']=True;row['blocker']={'reason':'Waiting','owner':'PO','unblock_action':'Approve'}
        self.assertTrue(any('Done cannot be blocked' in p for p in audit(doc, True)))

    def test_dependency_not_done_disallows_closure(self):
        doc=sample();row=closed(doc)
        dep=copy.deepcopy(row)
        dep['id']='LOCAL-2';dep['state']='Ready';dep['closure']=None
        row['dependencies']=['LOCAL-2']
        doc['items'].append(dep)
        self.assertTrue(any('dependency LOCAL-2 is not Done' in p for p in audit(doc)))

    def test_unknown_and_cyclic_dependency(self):
        doc=sample();doc['items'][0]['dependencies']=['unknown']
        self.assertTrue(any('unknown dependency' in p for p in audit(doc)))
        doc=sample();row=doc['items'][0]
        other=copy.deepcopy(row);other['id']='LOCAL-2';other['dependencies']=['LOCAL-1']
        row['dependencies']=['LOCAL-2'];doc['items'].append(other)
        self.assertTrue(any('dependency cycle' in p for p in audit(doc)))

    def test_duplicate_ids(self):
        doc=sample();doc['items'].append(copy.deepcopy(doc['items'][0]))
        self.assertTrue(any('duplicate id' in p for p in audit(doc)))

    def test_no_untracked_owner_or_next_action(self):
        doc=sample();row=doc['items'][0]
        row['owner']='';row['next_action']=''
        self.assertTrue(any('missing owner' in p for p in audit(doc)))
        self.assertTrue(any('missing next_action' in p for p in audit(doc)))

    def test_stale_scope_and_artifact_revision(self):
        doc=sample();row=closed(doc);row['scope_revision']+=1
        self.assertTrue(any('stale closure scope_revision' in p for p in audit(doc)))
        doc=sample();row=closed(doc);row['artifact_revision']='DIFFERENT'
        self.assertTrue(any('stale closure artifact_revision' in p for p in audit(doc)))

    def test_high_risk_requires_independent_review(self):
        doc=sample();row=closed(doc);row['risk']='high-risk';row['reviewer']=row['owner']
        errs=audit(doc)
        self.assertTrue(any('independent_review_ref' in p for p in errs))
        self.assertTrue(any('reviewer must differ' in p for p in errs))

    def test_release_in_scope_requires_deploy_proof(self):
        doc=sample();row=closed(doc);row['closure']['release_in_scope']=True
        self.assertTrue(any('release verification' in p for p in audit(doc)))

    def test_cancelled_requires_reason(self):
        doc=sample();row=doc['items'][0];row['state']='Cancelled'
        self.assertTrue(any('Cancelled requires' in p for p in audit(doc)))

    def test_cancelled_in_final_requires_authorized_scope_change(self):
        doc=sample();row=doc['items'][0]
        row['state']='Cancelled';row['cancellation']={'reason':'No longer required'}
        self.assertTrue(any('authorized scope change' in p for p in audit(doc, True)))
        row['cancellation']['authorization_ref']='user/decision-1'
        self.assertEqual(audit(doc, True), [])

    def test_small_root_still_requires_tracking(self):
        root=json.loads((ROOT/'assets/templates/assurance-root.json').read_text())
        root['tier']='small';root['final_claim']='COMPLETE'
        root['gates']=[g for g in root['gates'] if g['id']!='ROOT-TRACK']
        from assurance_audit import audit as gate_audit
        self.assertTrue(any('ROOT-TRACK' in p for p in gate_audit(root, True, True)))

    def test_done_must_explicitly_declare_release_scope(self):
        doc=sample();row=closed(doc)
        del row['closure']['release_in_scope']
        self.assertTrue(any('release was in scope' in p for p in audit(doc)))

    def test_external_sources_are_rejected(self):
        doc=sample();doc['source_of_truth']='external'
        self.assertTrue(any('external issue services' in p for p in audit(doc)))

    def test_root_assurance_includes_tracker_gate(self):
        root=json.loads((ROOT/'assets/templates/assurance-root.json').read_text())
        self.assertIn('ROOT-TRACK',{g['id'] for g in root['gates']})
        from assurance_audit import audit as gate_audit
        root['gates']=[g for g in root['gates'] if g['id']!='ROOT-TRACK']
        root['final_claim']='COMPLETE'
        self.assertTrue(any('ROOT-TRACK' in p for p in gate_audit(root, True, True)))

    def test_installed_tracker_auditor_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            project=Path(tmp)
            proc=subprocess.run([sys.executable,str(ROOT/'scripts/install.py'),
                                '--runtime','skill-only','--project',str(project),'--apply'],
                                capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
            installed=project/'.agents/skills/engihelm'
            script=installed/'scripts/task_tracker_audit.py'
            template=installed/'assets/templates/task-tracker.json'
            self.assertTrue(script.is_file())
            proc=subprocess.run([sys.executable,str(script),str(template)],capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)

    def test_profiles_all_include_tracking(self):
        roles=list((ROOT/'references/roles').glob('*.md'))
        self.assertEqual(len(roles),14)
        for role in roles:
            self.assertIn('Mandatory task tracking',role.read_text())
            for runtime,ext in [('codex','.toml'),('opencode','.md'),('antigravity','.md')]:
                text=(ROOT/'adapters'/runtime/'agents'/f'{role.stem}{ext}').read_text()
                self.assertIn('Mandatory task tracking',text)
        for runtime in ('opencode','antigravity'):
            self.assertIn('Non-delegable tracker ownership',
                          (ROOT/'adapters'/runtime/'agents/engihelm.md').read_text())

if __name__=='__main__':
    unittest.main()
