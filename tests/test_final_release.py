"""EngiHelm 1.0.0 migration, installed documentation and review policy regression."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def run(*args):
    return subprocess.run([sys.executable,*map(str,args)],capture_output=True,text=True)

class FinalReleaseTests(unittest.TestCase):
    def test_release_identity_and_license_status(self):
        m=json.loads((ROOT/'RELEASE.json').read_text())
        self.assertEqual((m['name'],m['version']),('engihelm','1.0.0'))
        self.assertEqual(m['compatibility']['historical_actor_id'],'sdlc-orchestrator')
        self.assertIn('No public license', (ROOT/'LICENSE').read_text())
        self.assertTrue((ROOT/'CHANGELOG.md').is_file())

    def test_install_full_source_and_installed_docs_are_separate(self):
        with tempfile.TemporaryDirectory() as t:
            project=Path(t)
            result=run(ROOT/'scripts/install.py','--runtime','skill-only','--project',project,'--apply')
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            path=project/'.agents/skills/engihelm'
            installed=(path/'README.md').read_text()
            self.assertIn('Installed Skill',installed)
            self.assertIn('external authenticated',installed)
            self.assertNotIn('python scripts/build_adapters.py',installed)
            self.assertFalse((path/'scripts/build_adapters.py').exists())
            self.assertFalse((path/'scripts/validate_bundle.py').exists())
            for x in ('LICENSE','RELEASE.json','CHANGELOG.md','scripts/codex_trial_adapter.py'):
                self.assertTrue((path/x).is_file(),x)
            self.assertNotEqual(installed,(ROOT/'README.md').read_text())

    def test_preview_legacy_and_block_before_writes(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            old=p/'.agents/skills/agile-sdlc-orchestrator'
            old.mkdir(parents=True)
            (old/'SKILL.md').write_text('custom old skill')
            existing=p/'docs/sdlc/state.db'
            existing.parent.mkdir(parents=True)
            existing.write_bytes(b'historical tracker test bytes')
            prev=run(ROOT/'scripts/install.py','--runtime','codex','--project',p)
            self.assertEqual(prev.returncode,0,prev.stdout+prev.stderr)
            self.assertIn('legacy directory',prev.stdout)
            self.assertIn('docs/sdlc',prev.stdout)
            self.assertFalse((p/'.agents/skills/engihelm').exists())
            blocked=run(ROOT/'scripts/install.py','--runtime','codex','--project',p,'--apply')
            self.assertEqual(blocked.returncode,3,blocked.stdout+blocked.stderr)
            self.assertIn('BLOCKED',blocked.stderr)
            self.assertFalse((p/'.agents/skills/engihelm').exists())
            self.assertEqual(existing.read_bytes(),b'historical tracker test bytes')
            self.assertEqual((old/'SKILL.md').read_text(),'custom old skill')
            ack=run(ROOT/'scripts/install.py','--runtime','codex','--project',p,'--apply','--acknowledge-legacy')
            self.assertEqual(ack.returncode,0,ack.stdout+ack.stderr)
            self.assertTrue((p/'.agents/skills/engihelm/SKILL.md').is_file())
            self.assertEqual(existing.read_bytes(),b'historical tracker test bytes')
            self.assertEqual((old/'SKILL.md').read_text(),'custom old skill')
            self.assertIn('legacy installation remains',ack.stdout)

    def test_legacy_native_profile_alone_blocks_upgrade(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            profile=p/'.opencode/agents/sdlc-orchestrator.md'
            profile.parent.mkdir(parents=True)
            profile.write_text('old customized profile')
            result=run(ROOT/'scripts/install.py','--runtime','opencode','--project',p,'--apply')
            self.assertEqual(result.returncode,3,result.stdout+result.stderr)
            self.assertFalse((p/'.opencode/skills/engihelm').exists())
            self.assertEqual(profile.read_text(),'old customized profile')

    def test_review_rules_are_risk_scoped_and_not_contradictory(self):
        skill=(ROOT/'SKILL.md').read_text()
        mode=(ROOT/'references/operating-modes.md').read_text()
        quality=(ROOT/'references/quality-gates.md').read_text()
        self.assertNotIn('Appoint one accountable owner per deliverable and one reviewer independent',skill)
        self.assertIn('For `standard`, require a distinct reviewer for `Done`',skill)
        self.assertIn('same-context',skill)
        self.assertIn('distinct reviewer for verified task closure',mode)
        self.assertIn('`small`: named self-review/second pass',quality)

if __name__=='__main__':unittest.main()
