#!/usr/bin/env python3
"""Pinned-policy executable gate runner with optional HMAC-signed receipts.

WARNING: Commands execute repository code. Use only in a sandboxed, least-privilege
trusted CI identity. An HMAC is trustworthy ONLY when agents cannot access the key
or invoke the signer. No platform integrations/branch rules are auto-configured.
"""
import argparse
import hashlib
import hmac
import json
import os
import signal
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

MAX_OUTPUT_BYTES=2*1024*1024


def data_bytes(d):return json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
def digest(raw):return hashlib.sha256(raw).hexdigest()
def utc():return datetime.now(timezone.utc).isoformat()
def read_policy(path):
    raw=Path(path).read_bytes()
    parsed=json.loads(raw)
    if not isinstance(parsed,dict) or parsed.get('version')!=1:raise ValueError('policy version must be 1')
    gates=parsed.get('gates');mandated=parsed.get('mandatory_gate_ids')
    if not isinstance(gates,list) or not gates or not isinstance(mandated,list) or not mandated:
        raise ValueError('policy requires gates and mandatory_gate_ids')
    ids=[]
    for gate in gates:
        if not isinstance(gate,dict) or not isinstance(gate.get('id'),str) or not gate['id'].strip():
            raise ValueError('invalid gate id')
        if not isinstance(gate.get('argv'),list) or not gate['argv'] or not all(isinstance(x,str) and x and '\x00' not in x for x in gate['argv']):
            raise ValueError(f'{gate["id"]}: argv must be a literal nonempty string array')
        if any(any(x in t for x in ('\n','\r')) for t in gate['argv']):
            raise ValueError('argv cannot contain control newlines')
        if type(gate.get('expected_exit')) is not int or gate['expected_exit']!=0:
            raise ValueError('only expected_exit 0 is accepted as success')
        timeout=gate.get('timeout_seconds')
        if type(timeout) not in (int,float) or not 1<=timeout<=600:
            raise ValueError('timeout_seconds must be 1..600')
        if 'stdout_contains' in gate and (not isinstance(gate['stdout_contains'],str) or not gate['stdout_contains']):
            raise ValueError('stdout_contains must be nonempty text')
        ids.append(gate['id'])
    if len(ids)!=len(set(ids)) or len(mandated)!=len(set(mandated)) or not set(mandated)<=set(ids):
        raise ValueError('duplicate or missing mandatory gate IDs')
    return parsed,digest(raw)


def git(repo,*args):
    cp=subprocess.run(['git','-C',str(repo),*args],capture_output=True,text=True,timeout=15)
    if cp.returncode!=0:raise ValueError('git failed: '+cp.stderr.strip())
    return cp.stdout.strip()


def git_state(repo):
    root=git(repo,'rev-parse','--show-toplevel')
    if Path(root).resolve()!=repo.resolve():raise ValueError('repo must identify the Git root')
    return git(repo,'rev-parse','HEAD'),not bool(git(repo,'status','--porcelain','--untracked-files=all'))


def signer_key(path,repo):
    if path is None:return None
    candidate=Path(path).expanduser()
    if candidate.is_symlink():raise ValueError('signing key symlinks are refused')
    p=candidate.resolve()
    if p==repo.resolve() or repo.resolve() in p.parents:raise ValueError('signing key cannot be in the agent project/repository')
    if not p.is_file() or p.is_symlink():raise ValueError('signing key must be a regular file')
    if os.name=='posix' and stat.S_IMODE(p.stat().st_mode)&0o077:
        raise ValueError('signing key permissions must restrict group/others (chmod 600)')
    key=p.read_bytes()
    if len(key)<32:raise ValueError('signing key must contain >=32 random bytes')
    return key


def run_one(gate,repo):
    started=utc()
    with tempfile.TemporaryDirectory(prefix='sdlc-gate-') as tmp:
        outpath=Path(tmp)/'stdout';errpath=Path(tmp)/'stderr'
        env={'PATH':os.environ.get('PATH','/usr/bin:/bin'),'LC_ALL':'C','LANG':'C','CI':'true','HOME':tmp}
        timed_out=False;exit_code=None
        with outpath.open('wb') as out,errpath.open('wb') as err:
            p=subprocess.Popen(gate['argv'],cwd=repo,env=env,stdin=subprocess.DEVNULL,
                               stdout=out,stderr=err,start_new_session=True)
            try:exit_code=p.wait(timeout=gate['timeout_seconds'])
            except subprocess.TimeoutExpired:
                timed_out=True
                if os.name=='posix':os.killpg(p.pid,signal.SIGKILL)
                else:p.kill()
                p.wait()
        stdout=outpath.read_bytes() if outpath.stat().st_size<=MAX_OUTPUT_BYTES else b''
        size_out=outpath.stat().st_size;size_err=errpath.stat().st_size
        output_limit=size_out>MAX_OUTPUT_BYTES or size_err>MAX_OUTPUT_BYTES
        expected=(gate.get('stdout_contains') or '').encode()
        check=not timed_out and not output_limit and exit_code==0 and (not expected or expected in stdout)
        return {'id':gate['id'],'status':'PASS' if check else ('TIMEOUT' if timed_out else 'FAIL'),
                'exit_code':exit_code,'started_at':started,'finished_at':utc(),
                'stdout_sha256':digest(outpath.read_bytes()) if not output_limit else None,
                'stderr_sha256':digest(errpath.read_bytes()) if not output_limit else None,
                'stdout_bytes':size_out,'stderr_bytes':size_err,
                'reason':('timeout' if timed_out else 'output-size-limit' if output_limit else
                          'exit-code-or-stdout-mismatch' if not check else 'passed')}


def run(a):
    repo=a.repo.resolve()
    policy,hash_=read_policy(a.policy)
    if hash_!=a.policy_sha256:raise ValueError('policy SHA-256 does not match approved pin')
    if not a.allow_run:raise ValueError('run requires --allow-run acknowledgement after trusted policy review')
    head,clean=git_state(repo)
    if not clean:raise ValueError('dirty working tree; commit exact revision before final evidence run')
    key=signer_key(a.key_file,repo)
    if key is not None and not a.assert_executor_isolation:
        raise ValueError('signed receipt requires --assert-executor-isolation; file permissions alone do not isolate same-UID test code')
    receipt_path=a.receipt.resolve()
    if key is not None and (receipt_path==repo or repo in receipt_path.parents):
        raise ValueError('signed evidence receipt must be written outside the agent repository')
    records=[]
    for gate in policy['gates']:
        try:records.append(run_one(gate,repo))
        except OSError as e:
            records.append({'id':gate['id'],'status':'ERROR','reason':str(e),'started_at':utc(),'finished_at':utc()})
    after,still_clean=git_state(repo)
    intact=after==head and still_clean
    passed=intact and all(g['status']=='PASS' for g in records)
    payload={'schema':1,'issued_at':utc(),'repo_head':head,'worktree_clean':intact,
             'policy_sha256':hash_,'mandatory_gate_ids':policy['mandatory_gate_ids'],
             'results':records,'all_passed':passed,'trust_level':'operator-asserted-isolation' if key else 'local-observation'}
    if key:payload['signature']={'algorithm':'HMAC-SHA256','value':hmac.new(key,data_bytes(payload),hashlib.sha256).hexdigest()}
    receipt_path.parent.mkdir(parents=True,exist_ok=True)
    if receipt_path.exists():raise ValueError('receipt already exists; refusing overwrite')
    with receipt_path.open('x',encoding='utf-8') as f:json.dump(payload,f,indent=2)
    print(('PASS' if passed else 'FAIL')+f': {len(records)} gates; signed={bool(key)}; receipt={receipt_path}')
    return 0 if passed else 1


def verify(a):
    policy,hash_=read_policy(a.policy)
    if hash_!=a.policy_sha256:raise ValueError('policy pin mismatch')
    receipt=json.loads(a.receipt.read_text(encoding='utf-8'))
    if not isinstance(receipt,dict):raise ValueError('receipt must be object')
    signature=receipt.get('signature')
    if not isinstance(signature,dict) or signature.get('algorithm')!='HMAC-SHA256':
        raise ValueError('signed receipt required; unsigned local observations cannot certify completion')
    key=signer_key(a.key_file,a.repo.resolve())
    if key is None:raise ValueError('--key-file required to verify authenticated receipt')
    unsigned={k:v for k,v in receipt.items() if k!='signature'}
    actual=hmac.new(key,data_bytes(unsigned),hashlib.sha256).hexdigest()
    if not isinstance(signature.get('value'),str) or not hmac.compare_digest(signature['value'],actual):
        raise ValueError('invalid receipt signature')
    expected_ids=[g['id'] for g in policy['gates']]
    results=receipt.get('results',[])
    if not isinstance(results,list) or [r.get('id') for r in results if isinstance(r,dict)]!=expected_ids or len(results)!=len(expected_ids):
        raise ValueError('missing, reordered or extra gate results')
    current_head,current_clean=git_state(a.repo.resolve())
    if current_head!=a.expected_commit or not current_clean:
        raise ValueError('current repository must be clean and at the expected revision')
    if receipt.get('repo_head')!=a.expected_commit or receipt.get('policy_sha256')!=hash_:
        raise ValueError('wrong source revision or policy hash')
    if receipt.get('mandatory_gate_ids')!=policy['mandatory_gate_ids']:
        raise ValueError('mandatory gate set mismatch')
    if receipt.get('trust_level')!='operator-asserted-isolation' or receipt.get('worktree_clean') is not True or receipt.get('all_passed') is not True:
        raise ValueError('receipt does not qualify for trusted completion')
    if any(r.get('status')!='PASS' or r.get('exit_code')!=0 for r in results):
        raise ValueError('unpassed gate in receipt')
    print('PASS: HMAC integrity, policy pin, exact commit and gate results match; executor isolation requires external verification')
    return 0


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='action',required=True)
    d=sub.add_parser('digest');d.add_argument('--policy',type=Path,required=True)
    for name in ('run','verify'):
        cmd=sub.add_parser(name)
        cmd.add_argument('--policy',type=Path,required=True)
        cmd.add_argument('--policy-sha256',required=True)
        cmd.add_argument('--repo',type=Path,required=True)
        cmd.add_argument('--receipt',type=Path,required=True)
        cmd.add_argument('--key-file',type=Path)
        if name=='run':
            cmd.add_argument('--allow-run',action='store_true')
            cmd.add_argument('--assert-executor-isolation',action='store_true',help='Requires independently established OS/container isolation for untrusted test code; not verified by this script')
        if name=='verify':cmd.add_argument('--expected-commit',required=True)
    a=p.parse_args()
    try:
        if a.action=='digest':
            policy,hash_=read_policy(a.policy);print(hash_);return 0
        return run(a) if a.action=='run' else verify(a)
    except (ValueError,FileNotFoundError,PermissionError,subprocess.TimeoutExpired,json.JSONDecodeError) as ex:
        print('FAIL: '+str(ex),file=sys.stderr);return 2

if __name__=='__main__':sys.exit(main())
