"""Regression tests for non-executing claim audit and universal role gates."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from assurance_audit import audit


def fresh():
    return json.loads((ROOT/'assets/templates/assurance-ledger.json').read_text())


def pass_gate(gate, mode='independent'):
    gate['status']='PASS'
    gate['self_check']={'result':'PASS','reference':'ci/run-1','observed':'exit 0; one test passed','scope_revision':1,'artifact_revision':'EXAMPLE-ARTIFACT-REV-1','context_id':'builder-ctx'}
    gate['parent_check']={'result':'PASS','reference':'ci/run-2','observed':'exit 0; one test passed',
                          'mode':mode,'verifier':'qa-engineer','scope_revision':1,'artifact_revision':'EXAMPLE-ARTIFACT-REV-1','context_id':'qa-ctx'}


class AssuranceTests(unittest.TestCase):
    def test_root_simplicity_is_required_for_substantial_complete_claims(self):
        doc=json.loads((ROOT/'assets/templates/assurance-root.json').read_text())
        self.assertIn('ROOT-SIMP',{g['id'] for g in doc['gates']})
        del doc['gates'][next(i for i,g in enumerate(doc['gates']) if g['id']=='ROOT-SIMP')]
        doc['final_claim']='COMPLETE'
        failures=audit(doc,True,True)
        self.assertTrue(any('ROOT-SIMP' in f for f in failures),failures)

    def test_root_simplicity_cannot_be_marked_optional_or_not_applicable(self):
        doc=json.loads((ROOT/'assets/templates/assurance-root.json').read_text())
        simp=next(g for g in doc['gates'] if g['id']=='ROOT-SIMP')
        simp['required']=False
        simp['status']='N/A'
        simp['reason']='too complicated to review'
        doc['final_claim']='COMPLETE'
        failures=audit(doc,True,True)
        self.assertTrue(any('ROOT-SIMP: mandatory root gate cannot be downgraded' in f for f in failures),failures)
        self.assertTrue(any('ROOT-SIMP: mandatory root gate must PASS' in f for f in failures),failures)

    def test_root_template_has_director_gates_but_is_not_claimed_complete(self):
        doc=json.loads((ROOT/'assets/templates/assurance-root.json').read_text())
        self.assertEqual(audit(doc,require_root=True),[])
        doc['final_claim']='COMPLETE'
        self.assertTrue(any('required gate' in issue for issue in audit(doc,True,True)))

    def test_template_is_valid_not_complete(self):
        self.assertEqual(audit(fresh()),[])

    def test_full_claim_requires_proof(self):
        doc=fresh();doc['final_claim']='COMPLETE'
        self.assertTrue(any('required gate' in x for x in audit(doc, True)))
        pass_gate(doc['gates'][0]);self.assertEqual(audit(doc, True),[])

    def test_stale_evidence_rejected_after_requirement_amendment(self):
        doc=fresh();doc['final_claim']='COMPLETE';pass_gate(doc['gates'][0]);doc['revision']=2
        self.assertTrue(any('evidence stale' in x for x in audit(doc, True)))

    def test_artifact_edit_invalidates_completed_gate(self):
        doc=fresh();doc['final_claim']='COMPLETE';pass_gate(doc['gates'][0]);doc['artifact_revision']='POST-EDIT-REV'
        self.assertTrue(any('artifact_revision' in x for x in audit(doc, True)))

    def test_same_context_does_not_count_as_independent(self):
        doc=fresh();doc['final_claim']='COMPLETE';pass_gate(doc['gates'][0])
        doc['gates'][0]['parent_check']['context_id']='builder-ctx'
        self.assertTrue(any('same execution context' in x for x in audit(doc, True)))

    def test_root_claim_cannot_hide_behind_arbitrary_owner(self):
        doc=fresh();doc['final_claim']='COMPLETE';pass_gate(doc['gates'][0]);doc['ledger_level']='root'
        doc['owner']='engineering-manager'
        problems=audit(doc, True, True)
        self.assertTrue(any('root ledger must be owned' in x for x in problems))
        self.assertTrue(any('missing director-owned gates' in x for x in problems))

    def test_leaf_cannot_be_used_as_final_root_audit(self):
        doc=fresh();doc['final_claim']='COMPLETE';pass_gate(doc['gates'][0])
        self.assertTrue(any('--root requires' in x for x in audit(doc, True, True)))

    def test_no_optional_only_coverage(self):
        doc=fresh();doc['final_claim']='COMPLETE';pass_gate(doc['gates'][0])
        doc['gates'][0]['required']=False
        self.assertTrue(any('no required acceptance gate' in x for x in audit(doc, True)))

    def test_self_certification_is_not_independence(self):
        doc=fresh();doc['final_claim']='COMPLETE';pass_gate(doc['gates'][0])
        doc['gates'][0]['parent_check']['verifier']='backend-engineer'
        self.assertTrue(any('self-review' in x for x in audit(doc, True)))

    def test_parent_not_run_no_false_pass(self):
        doc=fresh();doc['final_claim']='COMPLETE'
        doc['gates'][0]['status']='PASS'
        doc['gates'][0]['self_check']={'result':'PASS','reference':'ci/run-1','observed':'pass'}
        self.assertTrue(any('without successful parent' in x for x in audit(doc, True)))

    def test_uncited_pass_fails(self):
        doc=fresh();doc['final_claim']='COMPLETE';pass_gate(doc['gates'][0]);doc['gates'][0]['self_check']['reference']=''
        self.assertTrue(any('without specific reference' in x for x in audit(doc, True)))

    def test_coverage_and_approval(self):
        doc=fresh();doc['final_claim']='COMPLETE';pass_gate(doc['gates'][0])
        doc['requirements'][0]['gate_ids']=[]
        self.assertTrue(any('one or more gate ids' in x for x in audit(doc, True)))
        doc=fresh();doc['final_claim']='COMPLETE';pass_gate(doc['gates'][0])
        doc['approvals']['required']=True
        self.assertTrue(any('human approval' in x for x in audit(doc, True)))

    def test_high_risk_requires_real_independence(self):
        doc=fresh();doc['tier']='high-risk';doc['final_claim']='COMPLETE';pass_gate(doc['gates'][0], 'same-context')
        self.assertTrue(any('high-risk' in x for x in audit(doc, True)))

    def test_untrusted_check_never_executes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'marker'
            doc=fresh()
            doc['gates'][0]['check']=f'{sys.executable} -c "open({str(path)!r}, \"w\").write(\"bad\")"'
            ledger=Path(tmp)/'ledger.json';ledger.write_text(json.dumps(doc))
            tool=subprocess.run([sys.executable,str(ROOT/'scripts/assurance_audit.py'),str(ledger)],
                               text=True,capture_output=True)
            self.assertEqual(tool.returncode,0,tool.stdout+tool.stderr)
            self.assertFalse(path.exists())

    def test_native_agent_profiles_include_assurance(self):
        for role in (ROOT/'references/roles').glob('*.md'):
            for runtime,ext in [('codex','toml'),('opencode','md'),('antigravity','md')]:
                path=ROOT/'adapters'/runtime/'agents'/f'{role.stem}.{ext}'
                self.assertIn('Mandatory completion assurance',path.read_text())
        for runtime in ('opencode','antigravity'):
            path=ROOT/'adapters'/runtime/'agents'/'engihelm.md'
            self.assertIn('Non-delegable completion assurance',path.read_text())

    def test_agents_all_have_binding_clause(self):
        role_files=list((ROOT/'references/roles').glob('*.md'))
        self.assertEqual(len(role_files),14)
        for path in role_files:
            self.assertIn('Mandatory completion assurance',path.read_text())
        self.assertIn('Non-delegable completion assurance',
                      (ROOT/'references/engineering-director.md').read_text())

if __name__=='__main__':unittest.main()
