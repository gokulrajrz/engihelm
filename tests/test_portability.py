"""Quick integration tests for adapter synchronization and non-destructive installation."""
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[1]
PY=sys.executable


def run(*args):
    return subprocess.run([PY,*map(str,args)],capture_output=True,text=True)


class PortableSkillTests(unittest.TestCase):
    def test_validation_and_build_check(self):
        for script in ('build_adapters.py','validate_bundle.py'):
            args=['--check'] if script=='build_adapters.py' else []
            result=run(ROOT/'scripts'/script,*args)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_efficiency_rules_reach_every_agent_and_installed_skill(self):
        policy=(ROOT/'references/engineering-efficiency.md').read_text()
        for phrase in ('material overengineering','underengineering','reuse','G2S'):
            self.assertIn(phrase,policy)
        for p in (ROOT/'references/roles').glob('*.md'):
            self.assertIn('Mandatory engineering efficiency',p.read_text(),p.name)
        for p in (ROOT/'adapters/codex/agents').glob('*.toml'):
            self.assertIn('Ponytail-inspired G2S',tomllib.loads(p.read_text())['developer_instructions'])
        for platform in ('codex','antigravity','opencode','skill-only'):
            with self.subTest(runtime=platform), tempfile.TemporaryDirectory() as tmp:
                r=run(ROOT/'scripts/install.py','--runtime',platform,'--project',tmp,'--apply')
                self.assertEqual(r.returncode,0,r.stdout+r.stderr)
                base='.opencode/skills' if platform=='opencode' else '.agents/skills'
                installed=Path(tmp)/base/'engihelm'
                self.assertTrue((installed/'references/engineering-efficiency.md').is_file())
                self.assertTrue((installed/'references/operating-modes.md').is_file())
                self.assertTrue((installed/'scripts/completion_decision.py').is_file())
                self.assertTrue((installed/'assets/templates/engineering-efficiency-review.md').is_file())

    def test_format_and_role_count(self):
        codex=list((ROOT/'adapters/codex/agents').glob('*.toml'))
        antigravity=list((ROOT/'adapters/antigravity/agents').glob('*.md'))
        self.assertEqual(len(codex),14)
        self.assertEqual(len(antigravity),15)
        for p in codex:
            obj=tomllib.loads(p.read_text())
            self.assertTrue(obj['developer_instructions'].startswith('# Delegated expert'))
            self.assertEqual(obj['name'],p.stem)
        for p in antigravity:
            meta=yaml.safe_load(p.read_text().split('---',2)[1])
            self.assertEqual(meta['name'],p.stem)
            self.assertEqual(meta['mainAgent'],p.stem=='engihelm')
            self.assertEqual(meta['subagent'],p.stem!='engihelm')

    def test_install_each_platform_and_idempotency(self):
        for platform in ('codex','antigravity','opencode','skill-only'):
            with self.subTest(runtime=platform),tempfile.TemporaryDirectory() as temp:
                path=Path(temp)
                cmd=[ROOT/'scripts/install.py','--runtime',platform,'--project',path]
                result=run(*cmd)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertEqual(list(path.iterdir()),[], 'Dry run must never write')
                for _ in range(2):
                    result=run(*cmd,'--apply')
                    self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                skill_base='.opencode/skills' if platform=='opencode' else '.agents/skills'
                self.assertTrue((path/skill_base/'engihelm/SKILL.md').exists())
                self.assertTrue((path/skill_base/'engihelm/scripts/assurance_audit.py').is_file(), 'Installed Skill must include runnable auditor')
                if platform=='codex':self.assertEqual(len(list((path/'.codex/agents').glob('*.toml'))),14)
                if platform=='antigravity':self.assertEqual(len(list((path/'.agents/agents').glob('*.md'))),15)
                if platform=='opencode':self.assertEqual(len(list((path/'.opencode/agents').glob('*.md'))),15)
                if platform=='skill-only':self.assertFalse((path/'.agents/agents').exists())

    def test_installed_assurance_auditor_is_runnable(self):
        with tempfile.TemporaryDirectory() as temp:
            project=Path(temp)
            result=run(ROOT/'scripts/install.py','--runtime','skill-only','--project',project,'--apply')
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            installed=project/'.agents/skills/engihelm'
            ledger=installed/'assets/templates/assurance-ledger.json'
            auditor=installed/'scripts/assurance_audit.py'
            result=run(auditor,ledger)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('no CHECK commands executed',result.stdout)

    def test_existing_file_conflict_safety_and_backup(self):
        with tempfile.TemporaryDirectory() as temp:
            project=Path(temp)
            target=project/'.codex/agents/qa-engineer.toml'
            target.parent.mkdir(parents=True)
            target.write_text('this is mine')
            cmd=[ROOT/'scripts/install.py','--runtime','codex','--project',project]
            result=run(*cmd,'--apply')
            self.assertEqual(result.returncode,2)
            self.assertEqual(target.read_text(),'this is mine')
            self.assertFalse((project/'.agents/skills').exists())
            result=run(*cmd,'--apply','--overwrite')
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertNotEqual(target.read_text(),'this is mine')
            backups=list(target.parent.glob('qa-engineer.toml.backup-*'))
            self.assertEqual(len(backups),1)
            self.assertEqual(backups[0].read_text(),'this is mine')

    def test_symlink_path_rejection(self):
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as other:
            project=Path(temp)
            (project/'.codex').symlink_to(Path(other),target_is_directory=True)
            result=run(ROOT/'scripts/install.py','--runtime','codex','--project',project,'--apply')
            self.assertEqual(result.returncode,2,result.stdout+result.stderr)
            self.assertEqual(list(Path(other).iterdir()),[])


if __name__=='__main__':unittest.main()
