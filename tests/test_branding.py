"""Naming regression: user-visible identity is EngiHelm; historic ledger actor stays stable."""
import unittest
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[1]

class BrandingTests(unittest.TestCase):
    def test_entrypoint_and_ui_identity(self):
        entry=(ROOT/'SKILL.md').read_text(encoding='utf-8')
        meta=yaml.safe_load(entry.split('---',2)[1])
        self.assertEqual(meta['name'],'engihelm')
        self.assertIn('EngiHelm',meta['description'])
        self.assertEqual(yaml.safe_load((ROOT/'agents/openai.yaml').read_text())['interface']['display_name'],'EngiHelm')

    def test_native_main_names(self):
        for platform in ('antigravity','opencode'):
            path=ROOT/'adapters'/platform/'agents/engihelm.md'
            self.assertTrue(path.is_file(),path)
            self.assertFalse((path.parent/'sdlc-orchestrator.md').exists())
            self.assertIn('EngiHelm',path.read_text())

    def test_no_legacy_package_paths(self):
        paths=[p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
        for p in paths:
            self.assertNotIn('agile-sdlc-orchestrator',str(p.relative_to(ROOT)))
        self.assertEqual((ROOT/'scripts/install.py').read_text().count("NAME='engihelm'"),1)

    def test_stable_historical_actor(self):
        self.assertIn('sdlc-orchestrator', (ROOT/'assets/templates/assurance-root.json').read_text())
        self.assertIn('sdlc-orchestrator', (ROOT/'scripts/assurance_audit.py').read_text())
        self.assertIn('Renaming from the previous', (ROOT/'README.md').read_text())

if __name__=='__main__':unittest.main()
