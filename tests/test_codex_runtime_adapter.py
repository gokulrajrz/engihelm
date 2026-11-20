"""Offline contract tests. These are NOT live Codex behavioral trials."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import codex_trial_adapter as adapter

class CodexAdapterContractTests(unittest.TestCase):
    def test_fixture_git_revision_identical_for_pair(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=adapter.create_fixture('skipped-tests',Path(tmp)/'baseline')
            b=adapter.create_fixture('skipped-tests',Path(tmp)/'skill')
            self.assertEqual(a,b)
            self.assertEqual(len(a),40)

    def test_coding_fixtures_begin_with_observable_failing_tests(self):
        for sid in ('skipped-tests','omitted-requirement','overengineering','unsafe-contract-change'):
            with self.subTest(scenario=sid),tempfile.TemporaryDirectory() as tmp:
                repo=Path(tmp)/'repo'
                adapter.create_fixture(sid,repo)
                result=subprocess.run([sys.executable,'-m','unittest','discover','-v'],
                                      cwd=repo,capture_output=True,text=True,timeout=10)
                self.assertNotEqual(result.returncode,0, 'fixture should start RED')
                self.assertIn('FAILED',result.stderr)

    def test_refuses_real_agent_execution_without_explicit_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)
            scenario={'id':'skipped-tests','prompt':'fix off by one','checks':[]}
            (path/'scenario.json').write_text(json.dumps(scenario))
            args=['--mode','baseline','--scenario',str(path/'scenario.json'),
                  '--output',str(path/'report.json'),'--workdir',str(path)]
            env={**os.environ,'SDLC_ALLOW_REAL_AGENT_TRIALS':'0'}
            result=subprocess.run([sys.executable,str(ROOT/'scripts/codex_trial_adapter.py'),*args],
                env=env,capture_output=True,text=True,timeout=10)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('NOT RUN',result.stderr)
            self.assertFalse((path/'report.json').exists())

    def test_jsonl_parser_requires_thread_and_completion(self):
        self.assertEqual(adapter.parse_events('{}'),(None,False,False))
        good='{"type":"thread.started","thread_id":"real-id"}\n{"type":"turn.completed"}'
        self.assertEqual(adapter.parse_events(good),('real-id',True,False))
        bad=good+'\n{"type":"turn.failed"}'
        self.assertEqual(adapter.parse_events(bad),('real-id',True,True))

    def test_fixture_ids_reject_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,'invalid scenario ID'):
                adapter.create_fixture('../other',Path(tmp)/'repo')

if __name__=='__main__':unittest.main()
