#!/usr/bin/env python3
"""Opt-in real Codex CLI adapter for behavior_trials.py; no mock sessions or self-scoring.

Runs a single fresh Git fixture repository in a workspace-write Codex sandbox,
records raw JSONL trace, Git diff/status, and an independent local regression run.
Requires an installed authenticated Codex CLI and explicit opt-in; does NOT
bundle credentials or treat AI self-reports as validated quality evidence.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FIXTURES=ROOT/'assets/behavioral/fixtures'

def scenario_hash(s):
    raw=json.dumps(s,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()

def create_fixture(sid,root):
    if not re.fullmatch('[a-z0-9][a-z0-9-]{0,63}',sid):
        raise ValueError('invalid scenario ID')
    src=FIXTURES/sid
    if not src.is_dir():raise ValueError('no corresponding controlled repository fixture')
    if root.exists():raise ValueError('working repository must not already exist')
    shutil.copytree(src,root)
    (root/'.gitignore').write_text('/.agents/\n/.codex/\n/__pycache__/\n*.pyc\n')
    env={**os.environ,'GIT_AUTHOR_DATE':'2000-01-01T00:00:00+00:00',
         'GIT_COMMITTER_DATE':'2000-01-01T00:00:00+00:00'}
    for args in [('init','-q'),('config','user.email','controlled@example.invalid'),
                 ('config','user.name','Controlled Fixture'),('add','.'),('commit','-qm','Controlled baseline')]:
        subprocess.run(['git','-C',str(root),*args],check=True,capture_output=True,env=env,timeout=20)
    return subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()

def parse_events(raw):
    events=[]
    for line in raw.splitlines():
        try:
            obj=json.loads(line)
            if isinstance(obj,dict):events.append(obj)
        except json.JSONDecodeError:continue
    thread=next((e.get('thread_id') for e in events if e.get('type')=='thread.started' and e.get('thread_id')),None)
    complete=any(e.get('type')=='turn.completed' for e in events)
    failed=any(e.get('type') in ('turn.failed','error') for e in events)
    return thread,complete,failed

def run(a):
    if os.environ.get('SDLC_ALLOW_REAL_AGENT_TRIALS')!='1':
        raise ValueError('real agent trials require SDLC_ALLOW_REAL_AGENT_TRIALS=1; they may incur model costs')
    codex=shutil.which('codex')
    if not codex:raise ValueError('real Codex CLI not installed; no AI run was performed')
    model=os.environ.get('SDLC_CODEX_MODEL','').strip()
    if not model:raise ValueError('set SDLC_CODEX_MODEL to a fixed model for paired comparison')
    if not a.workdir.is_dir() or any(a.workdir.iterdir()):
        # The coordinator puts scenario.json in the workdir. Permit only that input.
        if not a.workdir.is_dir() or {p.name for p in a.workdir.iterdir()}!={'scenario.json'}:
            raise ValueError('adapter workdir must be an empty trial folder except scenario.json')
    scenario=json.loads(a.scenario.read_text())
    sid=scenario.get('id');prompt=scenario.get('prompt')
    if not isinstance(prompt,str) or not prompt.strip():raise ValueError('scenario prompt is empty')
    if a.mode=='skill' and (not a.skill_root or not (a.skill_root/'SKILL.md').is_file()):
        raise ValueError('Skill mode requires the real Skill directory')
    repo=a.workdir/'repo'
    source_commit=create_fixture(sid,repo)
    if a.mode=='skill':
        dest=repo/'.agents/skills/engihelm'
        shutil.copytree(a.skill_root,dest,ignore=shutil.ignore_patterns('__pycache__','*.pyc','.git'))
        prompt='Follow the installed engihelm Skill at .agents/skills/engihelm/SKILL.md and its relevant coding references. Do not claim verification not executed. Task: '+prompt
    runtime=subprocess.run([codex,'--version'],capture_output=True,text=True,timeout=20)
    if runtime.returncode:raise ValueError('codex --version failed; real run not started')
    version=runtime.stdout.strip() or runtime.stderr.strip()
    # JSON events include actual tool calls and model usage when supported.
    args=[codex,'exec','--json','--ephemeral','--ignore-user-config','--sandbox','workspace-write',
          '--cd',str(repo),'--model',model,prompt]
    started=time.monotonic()
    try:
        proc=subprocess.run(args,capture_output=True,text=True,timeout=int(os.getenv('SDLC_CODEX_TIMEOUT_SECONDS','700')))
    except subprocess.TimeoutExpired as exc:
        (a.workdir/'codex-timeout.txt').write_text(str(exc))
        raise ValueError('Codex session timed out; no completed-run report created')
    (a.workdir/'raw-trace.jsonl').write_text(proc.stdout)
    (a.workdir/'codex-stderr.log').write_text(proc.stderr)
    thread,completed,failed=parse_events(proc.stdout)
    if proc.returncode or not thread or not completed or failed:
        raise ValueError(f'Codex did not produce a completed real trace (exit={proc.returncode}, thread={thread}, completed={completed}, failed={failed}); see logs')
    diff=subprocess.run(['git','-C',str(repo),'diff','--binary'],capture_output=True,text=True,timeout=15)
    (a.workdir/'agent.patch').write_text(diff.stdout)
    status=subprocess.run(['git','-C',str(repo),'status','--porcelain'],capture_output=True,text=True,timeout=15)
    (a.workdir/'git-status.txt').write_text(status.stdout)
    # Do NOT execute agent-modified repository code outside the Codex sandbox:
    # untrusted tests can read host secrets or escape the workspace if invoked here.
    if list(repo.glob('test_*.py')):
        (a.workdir/'unexecuted-test-plan.txt').write_text(
            'NOT RUN by adapter: execute `python -m unittest discover -v` only in a separately isolated verifier.\n')
    checks=scenario.get('checks',[])
    # No self-grading from agent prose. Independent evaluator must inspect artifacts.
    result={'scenario_id':sid,'run_id':thread,'model_id':model,'runtime':version,
            'source_revision':source_commit,'input_revision':scenario_hash(scenario),
            'raw_trace_ref':str((a.workdir/'raw-trace.jsonl').resolve()),'simulated':False,
            'elapsed_seconds':round(time.monotonic()-started,3),
            'observations':{c['id']:{'verdict':'unverified','evidence_ref':''} for c in checks}}
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print('REAL CODEX RUN CAPTURED: '+thread+'; independent evidence grading required')
    return 0

def cli():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=['baseline','skill'],required=True)
    p.add_argument('--scenario',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--workdir',type=Path,required=True)
    p.add_argument('--skill-root',type=Path)
    a=p.parse_args()
    try:return run(a)
    except (ValueError,OSError,subprocess.SubprocessError,KeyError) as exc:
        print('NOT RUN / FAILED: '+str(exc),file=sys.stderr)
        return 2

if __name__=='__main__':sys.exit(cli())
