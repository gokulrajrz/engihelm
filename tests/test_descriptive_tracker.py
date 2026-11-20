"""Project-local descriptive tracker, absence safety, and recovery regression tests."""
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'scripts/state_store.py'

class DescriptiveTrackerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)
        self.db=self.path/'docs/sdlc/state.db'
    def tearDown(self):self.tmp.cleanup()
    def cli(self,*args):
        return subprocess.run([sys.executable,str(SCRIPT),'--db',str(self.db),*args],
                              capture_output=True,text=True,timeout=18)
    def init(self):self.assertEqual(self.cli('init').returncode,0)
    def add(self,extra=()):
        return self.cli('add','--id','T-1','--title','Resolve access bug',
                        '--owner','backend-engineer','--actor','orchestrator',
                        '--acceptance','AC-1','--next-action','Write failing test',
                        '--description','Inactive users remain authenticated',
                        '--outcome','Inactive users denied access','--acceptance-details','403 on inactive session',*extra)
    def test_missing_db_fails_no_silent_autocreate(self):
        r=self.cli('resume');self.assertNotEqual(r.returncode,0)
        self.assertIn('STATE MISSING',r.stderr)
        self.assertFalse(self.db.exists())
    def test_first_init_and_readable_report(self):
        self.init()
        self.assertTrue(self.db.exists())
        self.assertTrue(Path(str(self.db)+'.manifest.json').exists())
        self.assertTrue((self.db.parent/'TASKS.md').exists())
        self.assertEqual(self.add().returncode,0)
        text=(self.db.parent/'TASKS.md').read_text()
        for label in ('Problem / context','Expected outcome','Acceptance criteria', 'Completed work','Remaining work','Recent activity'):
            self.assertIn(label,text)
        self.assertIn('Inactive users remain authenticated',text)
    def test_required_descriptive_fields_are_enforced(self):
        self.init()
        r=self.cli('add','--id','T','--title','Task','--owner','x','--actor','y',
                   '--next-action','Do','--acceptance','A')
        self.assertNotEqual(r.returncode,0)
        self.assertIn('required',r.stderr)
    def test_progress_writes_history_and_conflict_blocks_overwrite(self):
        self.init();self.assertEqual(self.add().returncode,0)
        r=self.cli('update','--id','T-1','--expected-version','1','--actor','backend-engineer',
                   '--note','Root cause reproduced','--completed','Added failing test',
                   '--remaining','Fix middleware')
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(self.cli('verify').returncode,0)
        content=(self.db.parent/'TASKS.md').read_text()
        self.assertIn('Added failing test',content)
        self.assertIn('Root cause reproduced',content)
        conflict=self.cli('update','--id','T-1','--expected-version','1','--actor','other',
                          '--note','Stale','--completed','Overwrite')
        self.assertNotEqual(conflict.returncode,0)
        self.assertIn('conflict',conflict.stderr)
    def test_lost_database_refuses_reinitialization(self):
        self.init();self.assertEqual(self.add().returncode,0)
        self.db.unlink()
        self.assertNotEqual(self.cli('resume').returncode,0)
        r=self.cli('init')
        self.assertNotEqual(r.returncode,0)
        self.assertIn('STOP',r.stderr)
        self.assertFalse(self.db.exists())
    def test_verified_backup_and_explicit_restore(self):
        self.init();self.assertEqual(self.add().returncode,0)
        dest=self.path/'backups/store.db'
        self.assertEqual(self.cli('backup','--output',str(dest)).returncode,0)
        self.assertTrue(Path(str(dest)+'.manifest.json').exists())
        self.db.unlink()
        self.assertEqual(self.cli('restore','--from',str(dest)).returncode,0)
        self.assertEqual(self.cli('verify').returncode,0)
        self.assertIn('Resolve access bug',(self.db.parent/'TASKS.md').read_text())
    def test_mismatched_project_backup_rejected(self):
        self.init();self.assertEqual(self.add().returncode,0)
        backup=self.path/'backup.db'
        self.assertEqual(self.cli('backup','--output',str(backup)).returncode,0)
        manifest=Path(str(backup)+'.manifest.json')
        raw=json.loads(manifest.read_text());raw['store_id']='other-project'
        manifest.write_text(json.dumps(raw));self.db.unlink()
        r=self.cli('restore','--from',str(backup))
        self.assertNotEqual(r.returncode,0)
        self.assertIn('another project',r.stderr)
        self.assertFalse(self.db.exists())
    def test_migration_retains_prior_records_and_requests_enrichment(self):
        self.db.parent.mkdir(parents=True)
        db=sqlite3.connect(self.db)
        db.executescript('''CREATE TABLE tasks(id TEXT PRIMARY KEY, version INTEGER NOT NULL,
                title TEXT NOT NULL, owner TEXT NOT NULL, state TEXT NOT NULL, risk TEXT NOT NULL,
                acceptance TEXT NOT NULL, dependencies TEXT NOT NULL, next_action TEXT NOT NULL,
                blocked_reason TEXT NOT NULL DEFAULT '', unblock_owner TEXT NOT NULL DEFAULT '',
                unblock_action TEXT NOT NULL DEFAULT '',source_commit TEXT NOT NULL DEFAULT '',
                evidence_ref TEXT NOT NULL DEFAULT '', reviewer TEXT NOT NULL DEFAULT '',
                approval_ref TEXT NOT NULL DEFAULT '',updated_at TEXT NOT NULL);
                CREATE TABLE events(seq INTEGER PRIMARY KEY AUTOINCREMENT,task_id TEXT NOT NULL,
                task_version INTEGER NOT NULL,actor TEXT NOT NULL,action TEXT NOT NULL,
                payload TEXT NOT NULL,at TEXT NOT NULL,prev_hash TEXT NOT NULL,record_hash TEXT NOT NULL);''')
        db.execute("INSERT INTO tasks(id,version,title,owner,state,risk,acceptance,dependencies,next_action,updated_at) VALUES ('OLD',1,'Old task','eng','Ready','small','[\"AC-1\"]','[]','Enrich task','old')")
        db.commit();db.close()
        self.assertIn('migrate',self.cli('resume').stderr)
        self.assertEqual(self.cli('migrate').returncode,0)
        self.assertEqual(self.cli('enrich','--id','OLD','--expected-version','1','--actor','director',
                                  '--description','Existing task imported','--outcome','Expected behavior achieved',
                                  '--acceptance-details','AC-1: observable outcome').returncode,0)
        self.assertEqual(self.cli('verify').returncode,0)
        self.assertEqual(json.loads(self.cli('show').stdout)[0]['title'],'Old task')

if __name__=='__main__':unittest.main()
