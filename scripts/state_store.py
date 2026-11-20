#!/usr/bin/env python3
"""SQLite-backed, optimistic-concurrency task journal for portable SDLC teams.

Single authoritative local store; not cryptographic authorization or a replacement
for any external issue service. All state changes are transactional and journaled.
"""
import argparse
import hashlib
import json
import sqlite3
import sys
import os
import uuid
import shutil
from datetime import datetime, timezone
from pathlib import Path

STATES = ('Inbox','Triaged','Ready','In Progress','In Review','In QA','Ready for Release','Released','Verified','Blocked','Done','Cancelled')
FINAL = ('Done','Cancelled')
EXTRA_COLUMNS = {
    'description': "TEXT NOT NULL DEFAULT ''",
    'desired_outcome': "TEXT NOT NULL DEFAULT ''",
    'work_type': "TEXT NOT NULL DEFAULT 'task'",
    'priority': "TEXT NOT NULL DEFAULT 'normal'",
    'acceptance_details': "TEXT NOT NULL DEFAULT ''",
    'implementation_plan': "TEXT NOT NULL DEFAULT ''",
    'progress_note': "TEXT NOT NULL DEFAULT ''",
    'completed_work': "TEXT NOT NULL DEFAULT ''",
    'remaining_work': "TEXT NOT NULL DEFAULT ''",
    'decision_notes': "TEXT NOT NULL DEFAULT ''",
    'verification_summary': "TEXT NOT NULL DEFAULT ''",
    'created_at': "TEXT NOT NULL DEFAULT ''",
}

def marker_path(path):
    return Path(str(path) + '.manifest.json')

def missing_message(path):
    path = Path(path)
    clues = [marker_path(path),path.parent/'TASKS.md']
    if any(f.exists() for f in clues):
        return f'STATE MISSING: {path}; previous project artifacts exist. STOP; do not reinitialize. Locate a verified backup and run restore --from BACKUP, or escalate data loss.'
    return f'STATE MISSING: {path}; if this is a genuinely new project run init. If prior work existed, recover the database first; never infer that an empty store means no tasks.'

def validate_schema(con):
    fields={r[1] for r in con.execute('PRAGMA table_info(tasks)')}
    if not fields:
        raise ValueError('invalid state database: tasks table missing')
    missing=set(EXTRA_COLUMNS)-fields
    if missing:
        raise ValueError('legacy tracker schema; back up database and run migrate before using this Skill')



def timestamp():
    return datetime.now(timezone.utc).isoformat()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'))


def connect(path):
    p=Path(path)
    if not p.exists():
        raise ValueError(missing_message(p))
    con=sqlite3.connect(p, timeout=10)
    con.row_factory=sqlite3.Row
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('PRAGMA foreign_keys=ON')
    validate_schema(con)
    return con


def initialize(path):
    p=Path(path)
    if p.exists():
        raise ValueError('store already exists; refusing to reset existing work')
    if marker_path(p).exists() or (p.parent/'TASKS.md').exists():
        raise ValueError(missing_message(p))
    p.parent.mkdir(parents=True, exist_ok=True)
    con=sqlite3.connect(p)
    try:
        con.executescript('''
          CREATE TABLE tasks (id TEXT PRIMARY KEY, version INTEGER NOT NULL,
            title TEXT NOT NULL, owner TEXT NOT NULL, state TEXT NOT NULL, risk TEXT NOT NULL,
            acceptance TEXT NOT NULL, dependencies TEXT NOT NULL,
            next_action TEXT NOT NULL, blocked_reason TEXT NOT NULL DEFAULT '',
            unblock_owner TEXT NOT NULL DEFAULT '', unblock_action TEXT NOT NULL DEFAULT '',
            source_commit TEXT NOT NULL DEFAULT '', evidence_ref TEXT NOT NULL DEFAULT '',
            reviewer TEXT NOT NULL DEFAULT '', approval_ref TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL);
          CREATE TABLE events (seq INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL,
            task_version INTEGER NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL,
            payload TEXT NOT NULL, at TEXT NOT NULL,
            prev_hash TEXT NOT NULL, record_hash TEXT NOT NULL,
            FOREIGN KEY(task_id) REFERENCES tasks(id));
          CREATE INDEX idx_task_state ON tasks(state);
        ''')
        for name,sql_type in EXTRA_COLUMNS.items():
            con.execute(f'ALTER TABLE tasks ADD COLUMN {name} {sql_type}')
        con.commit()
    finally:
        con.close()
    manifest={'version':1,'store_id':str(uuid.uuid4()),'created_at':timestamp(),'database':p.name,
              'note':'Marker prevents silent reinitialization if this database disappears. Keep with backups.'}
    marker_path(p).write_text(json.dumps(manifest,indent=2)+'\n')


def migrate(path):
    p=Path(path)
    if not p.exists(): raise ValueError(missing_message(p))
    con=sqlite3.connect(p)
    try:
        existing={r[1] for r in con.execute('PRAGMA table_info(tasks)')}
        if not existing: raise ValueError('not a state-store SQLite database')
        con.execute('BEGIN IMMEDIATE')
        for name,sql_type in EXTRA_COLUMNS.items():
            if name not in existing:
                con.execute(f'ALTER TABLE tasks ADD COLUMN {name} {sql_type}')
        # Explicitly journal imported legacy tasks with no prior event history.
        # This is an import snapshot, NOT proof of the task's earlier provenance.
        con.row_factory=sqlite3.Row
        for row in con.execute('SELECT * FROM tasks'):
            if con.execute('SELECT COUNT(*) FROM events WHERE task_id=?',(row['id'],)).fetchone()[0]==0:
                snapshot={k:row[k] for k in row.keys() if k not in ('id','version','updated_at','created_at')}
                for field in ('acceptance','dependencies'):
                    snapshot[field]=json.loads(snapshot[field])
                record(con,row['id'],row['version'],'migration','import',snapshot)
        con.commit()
    finally:con.close()
    if not marker_path(p).exists():
        marker_path(p).write_text(json.dumps({'version':1,'store_id':str(uuid.uuid4()),
                     'created_at':timestamp(),'database':p.name,'migrated':True},indent=2)+'\n')


def backup(path,destination):
    src=Path(path);dest=Path(destination)
    if not src.exists(): raise ValueError(missing_message(src))
    if dest.resolve()==src.resolve() or dest.exists():
        raise ValueError('backup destination must be a new file different from the live database')
    dest.parent.mkdir(parents=True,exist_ok=True)
    with connect(src) as con:
        tmp=Path(str(dest)+'.partial')
        if tmp.exists():raise ValueError('partial backup already exists; investigate before retry')
        try:
            out=sqlite3.connect(tmp)
            try:con.backup(out)
            finally:out.close()
            test=sqlite3.connect(tmp)
            test.row_factory=sqlite3.Row
            try:
                if test.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or verify(test):
                    raise ValueError('backup consistency check failed')
            finally:test.close()
            tmp.replace(dest)
        finally:
            if tmp.exists():tmp.unlink()
    if marker_path(src).exists():
        shutil.copyfile(marker_path(src),marker_path(dest))


def restore(path,source):
    dest=Path(path);src=Path(source)
    if dest.exists(): raise ValueError('state database exists; refusing to overwrite it')
    if not src.is_file(): raise ValueError('backup missing')
    if not marker_path(dest).exists():
        raise ValueError('no project manifest; cannot safely identify this as a recovery. Escalate for manual recovery.')
    if not marker_path(src).exists():
        raise ValueError('backup manifest missing; cannot verify backup project identity')
    existing=json.loads(marker_path(dest).read_text())
    incoming=json.loads(marker_path(src).read_text())
    if existing['store_id']!=incoming['store_id']:
        raise ValueError('backup belongs to another project state identity')
    check=sqlite3.connect(f'file:{src.resolve()}?mode=ro',uri=True)
    check.row_factory=sqlite3.Row
    try:
        if check.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or verify(check):
            raise ValueError('backup failed integrity or local journal verification')
        validate_schema(check)
    finally:check.close()
    dest.parent.mkdir(parents=True,exist_ok=True)
    tmp=Path(str(dest)+'.recovering')
    if tmp.exists(): raise ValueError('previous incomplete recovery found; investigate')
    try:
        shutil.copyfile(src,tmp)
        tmp.replace(dest)
    finally:
        if tmp.exists():tmp.unlink()


def record(con, task_id, version, actor, action, payload):
    prev=con.execute('SELECT record_hash FROM events ORDER BY seq DESC LIMIT 1').fetchone()
    previous=prev[0] if prev else 'GENESIS'
    at=timestamp()
    body={'task_id':task_id,'task_version':version,'actor':actor,'action':action,'payload':payload,'at':at}
    digest=hashlib.sha256((previous+'\n'+canonical(body)).encode()).hexdigest()
    con.execute('INSERT INTO events(task_id,task_version,actor,action,payload,at,prev_hash,record_hash) VALUES (?,?,?,?,?,?,?,?)',
                (task_id,version,actor,action,canonical(payload),at,previous,digest))


def add(con,a):
    acceptance=sorted(set(x.strip() for x in a.acceptance.split(',') if x.strip()))
    if not all((a.description.strip(),a.outcome.strip(),a.acceptance_details.strip())):
        raise ValueError('descriptive tasks require --description, --outcome and --acceptance-details')
    deps=sorted(set(x.strip() for x in a.dependencies.split(',') if x.strip()))
    if not all([a.id.strip(),a.title.strip(),a.owner.strip(),a.next_action.strip(),a.actor.strip()]) or not acceptance:
        raise ValueError('id, title, owner, actor, next-action and acceptance IDs are required')
    if a.id in deps: raise ValueError('self-dependency')
    con.execute('BEGIN IMMEDIATE')
    for dep in deps:
        if con.execute('SELECT 1 FROM tasks WHERE id=?',(dep,)).fetchone() is None:
            raise ValueError(f'unknown dependency {dep}')
    now=timestamp()
    con.execute('''INSERT INTO tasks(id,version,title,owner,state,risk,acceptance,dependencies,next_action,updated_at,
                description,desired_outcome,work_type,priority,acceptance_details,implementation_plan,remaining_work,created_at)
                VALUES(?,1,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (a.id,a.title,a.owner,'Ready',a.risk,canonical(acceptance),canonical(deps),a.next_action,now,
                 a.description,a.outcome,a.type,a.priority,a.acceptance_details,a.plan,a.next_action,now))
    payload=dict(id=a.id,title=a.title,owner=a.owner,state='Ready',risk=a.risk,acceptance=acceptance,dependencies=deps,next_action=a.next_action,description=a.description,desired_outcome=a.outcome,work_type=a.type,priority=a.priority,acceptance_details=a.acceptance_details,implementation_plan=a.plan,remaining_work=a.next_action)
    record(con,a.id,1,a.actor,'add',payload)
    con.commit()


def transition(con,a, *, verified_close=False, transaction_open=False, closure_proof=None):
    if a.state=='Done' and not verified_close:
        raise ValueError('Done is guarded: use verify_and_close.py, never transition --state Done')
    if a.state=='Done' and verified_close and (not isinstance(closure_proof,dict) or
        closure_proof.get('decision') not in ('LIGHTWEIGHT_DECLARED','LOCAL_CONSISTENT','SIGNED_RECEIPT_MATCH') or
        not closure_proof.get('root_ledger_sha256')):
        raise ValueError('internal closure requires a verified completion proof and root ledger digest')
    if not transaction_open:
        con.execute('BEGIN IMMEDIATE')
    row=con.execute('SELECT * FROM tasks WHERE id=?',(a.id,)).fetchone()
    if not row: raise ValueError('unknown task')
    old=dict(row)
    if old['version']!=a.expected_version:
        raise ValueError(f'conflict: expected version {a.expected_version}, current {old["version"]}; reread and reconcile')
    if a.state==old['state']:
        raise ValueError('state unchanged; use a meaningful transition, do not generate activity noise')
    if old['state'] in FINAL and a.state not in ('In Progress','Ready'):
        raise ValueError('closed task must reopen to In Progress or Ready')
    if a.state=='Done' and old['state']!='Verified':
        raise ValueError('Done requires Verified state first')
    if a.state=='Verified' and old['state'] not in ('In Review','In QA','Ready for Release','Released','In Progress'):
        raise ValueError('Verified requires implementation or review progress')
    next_action=a.next_action.strip()
    blocked_reason=a.blocked_reason.strip() if a.state=='Blocked' else ''
    unblock_owner=a.unblock_owner.strip() if a.state=='Blocked' else ''
    unblock_action=a.unblock_action.strip() if a.state=='Blocked' else ''
    if a.state=='Blocked' and not all((blocked_reason,unblock_owner,unblock_action,next_action)):
        raise ValueError('Blocked requires reason, unblock owner/action and next action')
    if a.state not in FINAL and not next_action:
        raise ValueError('active state requires next action')
    commit=a.commit.strip() or old['source_commit']
    evidence=a.evidence.strip() or old['evidence_ref']
    reviewer=a.reviewer.strip() or old['reviewer']
    approval=a.approval.strip() or old['approval_ref']
    if a.state in ('Verified','Done'):
        if not commit or not evidence: raise ValueError(f'{a.state} requires source commit and evidence reference')
        if old['risk'] in ('standard','high-risk') and (not reviewer or reviewer==old['owner']):
            raise ValueError(f'{a.state} requires different reviewer for {old["risk"]} risk')
    if a.state=='Cancelled' and not approval:
        raise ValueError('Cancelled requires authorized scope-change reference')
    if a.state=='Done' and old['risk']=='high-risk' and not approval:
        raise ValueError('high-risk Done requires approval reference')
    if a.state=='Done':
        for dep in json.loads(old['dependencies']):
            dep_state=con.execute('SELECT state FROM tasks WHERE id=?',(dep,)).fetchone()
            if not dep_state or dep_state[0]!='Done': raise ValueError(f'open dependency: {dep}')
    fields={'state':a.state,'next_action':next_action,'blocked_reason':blocked_reason,
            'unblock_owner':unblock_owner,'unblock_action':unblock_action,
            'source_commit':commit,'evidence_ref':evidence,'reviewer':reviewer,'approval_ref':approval,
            'updated_at':timestamp(),'version':old['version']+1}
    # Any reopening after closure clears stale verification evidence.
    if old['state'] in FINAL and a.state in ('Ready','In Progress'):
        fields['source_commit']='';fields['evidence_ref']='';fields['reviewer']='';fields['approval_ref']=''
    con.execute('''UPDATE tasks SET state=:state,next_action=:next_action,
      blocked_reason=:blocked_reason,unblock_owner=:unblock_owner,
      unblock_action=:unblock_action,source_commit=:source_commit,
      evidence_ref=:evidence_ref,reviewer=:reviewer,approval_ref=:approval_ref,updated_at=:updated_at,version=:version
      WHERE id=:id''', {**fields,'id':a.id})
    event_payload={'from':old['state'],'to':a.state,**fields}
    if closure_proof is not None:
        event_payload['closure_proof']=closure_proof
    record(con,a.id,fields['version'],a.actor,'transition',event_payload)
    if not transaction_open:
        con.commit()


def update(con,a):
    con.execute('BEGIN IMMEDIATE')
    row=con.execute('SELECT * FROM tasks WHERE id=?',(a.id,)).fetchone()
    if not row:raise ValueError('unknown task')
    if row['version']!=a.expected_version:raise ValueError(f'conflict: expected version {a.expected_version}, current {row["version"]}')
    fields={'implementation_plan':a.plan,'progress_note':a.progress,'completed_work':a.completed,
            'remaining_work':a.remaining,'decision_notes':a.decisions,'verification_summary':a.verification}
    changes={k:v.strip() for k,v in fields.items() if v is not None and v.strip()!=row[k]}
    if not changes or not a.note.strip():raise ValueError('update requires meaningful changed content and --note describing observed progress')
    if row['state'] in FINAL:
        raise ValueError('closed task: reopen with transition before updating progress')
    new_version=row['version']+1
    vals={**changes,'id':a.id,'version':new_version,'updated_at':timestamp()}
    assignments=','.join(f'{k}=:{k}' for k in changes)
    con.execute(f'UPDATE tasks SET {assignments},version=:version,updated_at=:updated_at WHERE id=:id',vals)
    record(con,a.id,new_version,a.actor,'update',{'state':row['state'],'changes':changes,'note':a.note.strip()})
    con.commit()


def enrich(con,a):
    # Recover descriptive metadata of pre-upgrade tasks; never overwrite documented scope.
    con.execute('BEGIN IMMEDIATE')
    row=con.execute('SELECT * FROM tasks WHERE id=?',(a.id,)).fetchone()
    if not row:raise ValueError('unknown task')
    if row['version']!=a.expected_version:raise ValueError(f'conflict: expected version {a.expected_version}, current {row["version"]}')
    fields={'description':a.description.strip(),'desired_outcome':a.outcome.strip(),'acceptance_details':a.acceptance_details.strip()}
    if any(row[k] for k in fields):raise ValueError('enrich is only for migrated tasks with empty descriptive fields; scope changes require amend')
    if not all(fields.values()):raise ValueError('all three descriptive fields are required')
    new_version=row['version']+1
    con.execute('''UPDATE tasks SET description=?,desired_outcome=?,acceptance_details=?,version=?,updated_at=? WHERE id=?''',
                (*fields.values(),new_version,timestamp(),a.id))
    record(con,a.id,new_version,a.actor,'enrich',{'state':row['state'],'fields':fields,'note':'legacy task description recovery'})
    con.commit()


def amend(con,a):
    # Revise acceptance scope; invalidate old proof and reopen.
    con.execute('BEGIN IMMEDIATE')
    row=con.execute('SELECT * FROM tasks WHERE id=?',(a.id,)).fetchone()
    if not row:raise ValueError('unknown task')
    old=dict(row)
    if old['version']!=a.expected_version:
        raise ValueError(f'conflict: expected version {a.expected_version}, current {old["version"]}')
    acceptance=sorted(set(x.strip() for x in a.acceptance.split(',') if x.strip()))
    if not acceptance or not a.reason.strip() or not a.next_action.strip():
        raise ValueError('amend requires acceptance IDs, scope-change reason and next action')
    next_ver=old['version']+1
    con.execute("""UPDATE tasks SET version=?,acceptance=?,state='Ready',
          evidence_ref='',source_commit='',reviewer='',approval_ref='',blocked_reason='',unblock_owner='',unblock_action='',
          next_action=?,updated_at=? WHERE id=?""",
          (next_ver,canonical(acceptance),a.next_action,timestamp(),a.id))
    record(con,a.id,next_ver,a.actor,'amend',{'from_state':old['state'],'old_acceptance':json.loads(old['acceptance']),
             'acceptance':acceptance,'reason':a.reason,'state':'Ready','next_action':a.next_action})
    con.commit()


def rows(con):
    return [dict(r) for r in con.execute('SELECT * FROM tasks ORDER BY id')]


def show(con, remaining=False):
    items=rows(con)
    if remaining: items=[i for i in items if i['state'] not in FINAL]
    for i in items:
        i['acceptance']=json.loads(i['acceptance'])
        i['dependencies']=json.loads(i['dependencies'])
    return items


def verify(con):
    """Validate journal hashes *and* replay recorded mutations into current state.

    Hashes detect accidental history corruption but not an attacker who can rewrite
    the database; protect state outside agent write access for trusted assurance.
    """
    errors=[];prev='GENESIS';expected={};last_version={}
    tracked_fields={
        'title','owner','state','risk','acceptance','dependencies','next_action',
        'blocked_reason','unblock_owner','unblock_action','source_commit',
        'evidence_ref','reviewer','approval_ref','description','desired_outcome',
        'work_type','priority','acceptance_details','implementation_plan',
        'progress_note','completed_work','remaining_work','decision_notes',
        'verification_summary'
    }
    for r in con.execute('SELECT * FROM events ORDER BY seq'):
        e=dict(r)
        if e['prev_hash']!=prev: errors.append(f'event {e["seq"]}: broken previous hash')
        try:
            payload=json.loads(e['payload'])
            data={'task_id':e['task_id'],'task_version':e['task_version'],
                  'actor':e['actor'],'action':e['action'],'payload':payload,'at':e['at']}
            actual=hashlib.sha256((prev+'\n'+canonical(data)).encode()).hexdigest()
            if e['record_hash']!=actual:errors.append(f'event {e["seq"]}: changed content')
            if not isinstance(payload,dict):raise ValueError('payload not an object')
        except (ValueError,TypeError) as ex:
            errors.append(f'event {e["seq"]}: invalid event payload {ex}')
            prev=e['record_hash'];continue
        tid=e['task_id'];action=e['action'];version=e['task_version']
        if action in ('add','import'):
            if tid in expected: errors.append(f'{tid}: duplicate creation event')
            expected[tid]={k:v for k,v in payload.items() if k in tracked_fields}
            last_version[tid]=version
            if action=='add' and version!=1: errors.append(f'{tid}: creation version must be 1')
        else:
            if tid not in expected: errors.append(f'{tid}: event before creation')
            if version!=last_version.get(tid,version-1)+1:
                errors.append(f'{tid}: nonsequential event version')
            last_version[tid]=version
            snap=expected.setdefault(tid,{})
            if action=='transition':
                snap.update({k:v for k,v in payload.items() if k in tracked_fields})
                snap['state']=payload.get('to')
            elif action=='update':
                snap.update({k:v for k,v in payload.get('changes',{}).items() if k in tracked_fields})
            elif action=='enrich':
                snap.update({k:v for k,v in payload.get('fields',{}).items() if k in tracked_fields})
            elif action=='amend':
                snap.update({'state':'Ready','acceptance':payload.get('acceptance'),
                    'next_action':payload.get('next_action'),'evidence_ref':'',
                    'source_commit':'','reviewer':'','approval_ref':'',
                    'blocked_reason':'','unblock_owner':'','unblock_action':''})
            else:
                errors.append(f'{tid}: unknown event action {action}')
        prev=e['record_hash']
    rows_by_id={r['id']:r for r in rows(con)}
    for tid in expected:
        if tid not in rows_by_id: errors.append(f'{tid}: journal references deleted task')
    for tid,row in rows_by_id.items():
        if tid not in expected:
            errors.append(f'{tid}: current task has no creation event');continue
        if row['version']!=last_version.get(tid):
            errors.append(f'{tid}: task state/event version mismatch')
        for field,value in expected[tid].items():
            if field not in tracked_fields:continue
            stored=json.loads(row[field]) if field in ('acceptance','dependencies') else row[field]
            if stored!=value:
                errors.append(f'{tid}: {field} differs from replayed event journal')
    return errors


def report(con,output):
    items=show(con)
    counts={name:sum(item['state']==name for item in items) for name in STATES}
    def line(value):return str(value or 'Not recorded').replace('|','\\|').replace('\r',' ').replace('\n','  ')
    def label_list(v):return ', '.join(v) if v else 'None'
    result=['# SDLC Task Tracker','',f'> Read-only snapshot generated {timestamp()} from **state.db**. Edit using `state_store.py`; this file is not authoritative.','',
            f'**Total tasks:** {len(items)} | **Done:** {counts["Done"]} | **Blocked:** {counts["Blocked"]} | **Active:** {sum(1 for item in items if item["state"] not in FINAL)}','',
            '| ID | Outcome | Owner | State | Priority | Next action |','| --- | --- | --- | --- | --- | --- |']
    for x in items:
        result.append('| '+' | '.join(line(v) for v in [x['id'],x['title'],x['owner'],x['state'],x['priority'],x['next_action']])+' |')
    for x in items:
        history=list(con.execute('SELECT action,actor,at,payload FROM events WHERE task_id=? ORDER BY seq DESC LIMIT 6',(x['id'],)))
        result += ['',f'## {x["id"]}: {line(x["title"])}','',
                   f'**Owner:** {line(x["owner"])} · **State:** {line(x["state"])} · **Type:** {line(x["work_type"])} · **Priority:** {line(x["priority"])} · **Risk:** {line(x["risk"])} · **Version:** {x["version"]}',
                   '',f'**Problem / context:** {line(x["description"])}','',f'**Expected outcome:** {line(x["desired_outcome"])}',
                   '',f'**Acceptance criteria:** {line(x["acceptance_details"])} (IDs: {line(label_list(x["acceptance"]))})',
                   '',f'**Approach:** {line(x["implementation_plan"])}',
                   '',f'**Progress summary:** {line(x["progress_note"])}',
                   '',f'**Completed work:** {line(x["completed_work"])}',
                   '',f'**Remaining work:** {line(x["remaining_work"])}',
                   '',f'**Decisions / trade-offs:** {line(x["decision_notes"])}',
                   '',f'**Verification:** {line(x["verification_summary"])}',
                   '',f'**Evidence:** {line(x["evidence_ref"])} · **Commit:** {line(x["source_commit"])} · **Reviewer:** {line(x["reviewer"])}',
                   '',f'**Dependencies:** {line(label_list(x["dependencies"]))}',
                   '',f'**Blocker:** {line(x["blocked_reason"])} · **Unblock owner:** {line(x["unblock_owner"])} · **Unblock action:** {line(x["unblock_action"])}',
                   '',f'**Next action:** {line(x["next_action"])}',
                   '',f'**Created:** {line(x["created_at"])} · **Last updated:** {line(x["updated_at"])}',
                   '', '**Recent activity (newest first):**','']
        for event in history:
            payload=json.loads(event['payload'])
            detail=payload.get('note') or payload.get('reason') or payload.get('to') or payload.get('state') or event['action']
            result.append(f'- {line(event["at"])} · {line(event["actor"])} · **{line(event["action"])}** — {line(detail)}')
        result.append('')
    if not items: result += ['', '_No tracked tasks. This is not evidence that there is no work._','']
    output=Path(output)
    if output.suffix.lower()!='.md':raise ValueError('readable tracker output must be a .md file')
    output.parent.mkdir(parents=True,exist_ok=True)
    tmp=output.with_name(output.name+'.partial')
    if tmp.exists():raise ValueError('existing partial report; investigate before overwriting')
    try:
        tmp.write_text('\n'.join(result)+'\n')
        tmp.replace(output)
    finally:
        if tmp.exists():tmp.unlink()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db',type=Path,required=True)
    s=p.add_subparsers(dest='action',required=True)
    s.add_parser('init')
    s.add_parser('migrate',help='upgrade old schema without discarding tasks; back up first')
    enrichp=s.add_parser('enrich',help='populate descriptive fields on a migrated legacy task without rewriting scope')
    for key in ('id','expected-version','actor','description','outcome','acceptance-details'):
        enrichp.add_argument('--'+key,required=True,type=int if key=='expected-version' else str)
    bp=s.add_parser('backup');bp.add_argument('--output',required=True)
    rp=s.add_parser('restore');rp.add_argument('--from',dest='source',required=True)
    rep=s.add_parser('report');rep.add_argument('--output',required=True)
    up=s.add_parser('update',help='write descriptive progress without changing acceptance scope')
    for field in ('id','expected-version','actor','note'):
        up.add_argument('--'+field,required=True,type=int if field=='expected-version' else str)
    for field in ('plan','progress','completed','remaining','decisions','verification'):
        up.add_argument('--'+field)

    addp=s.add_parser('add')
    for key in ('id','title','owner','acceptance','next-action','actor'):
        addp.add_argument('--'+key,required=True)
    addp.add_argument('--risk',choices=['small','standard','high-risk'],default='standard')
    addp.add_argument('--dependencies',default='')
    for key in ('description','outcome','acceptance-details'):
        addp.add_argument('--'+key,required=True)
    addp.add_argument('--type',default='task')
    addp.add_argument('--priority',choices=['low','normal','high','critical'],default='normal')
    addp.add_argument('--plan',default='')
    t=s.add_parser('transition')
    for key in ('id','state','actor'):
        t.add_argument('--'+key,required=True)
    t.add_argument('--expected-version',type=int,required=True)
    t.add_argument('--next-action',default='')
    t.add_argument('--commit',default='');t.add_argument('--evidence',default='');t.add_argument('--reviewer',default='');t.add_argument('--approval',default='')
    t.add_argument('--blocked-reason',default='');t.add_argument('--unblock-owner',default='');t.add_argument('--unblock-action',default='')
    amended=s.add_parser('amend',help='change accepted scope; reopen task and invalidate stale proof')
    for key in ('id','expected-version','acceptance','reason','next-action','actor'):
        amended.add_argument('--'+key,required=True,type=int if key=='expected-version' else str)
    s.add_parser('show');s.add_parser('resume');s.add_parser('verify')
    s.add_parser('audit',help='Reject unresolved work and incomplete closure references')
    a=p.parse_args()
    try:
        if a.action=='init':
            initialize(a.db)
            with connect(a.db) as initialized:report(initialized,a.db.parent/'TASKS.md')
            print('PASS: created NEW durable store, recovery marker and readable TASKS.md');return 0
        if a.action=='migrate':
            migrate(a.db)
            with connect(a.db) as upgraded:report(upgraded,a.db.parent/'TASKS.md')
            print('PASS: updated schema without resetting work; enrich missing descriptions before final closure');return 0
        if a.action=='restore':
            restore(a.db,a.source)
            with connect(a.db) as restored:report(restored,a.db.parent/'TASKS.md')
            print('PASS: restored verified backup and regenerated TASKS.md; reconcile Git revisions');return 0
        if a.action=='backup':backup(a.db,a.output);print('PASS: created verified backup and matching marker');return 0
        con=connect(a.db)
        try:
            if a.action=='add':add(con,a);print('PASS: task created')
            elif a.action=='update':update(con,a);print('PASS: descriptive task progress recorded')
            elif a.action=='enrich':enrich(con,a);print('PASS: legacy description recorded')
            elif a.action=='report':report(con,a.output);print('PASS: generated readable non-authoritative tracker')
            elif a.action=='amend':amend(con,a);print('PASS: changed acceptance scope and invalidated prior evidence')
            elif a.action=='transition':
                if a.state not in STATES:raise ValueError('unknown state')
                transition(con,a);print('PASS: task transitioned')
            elif a.action in ('show','resume'):print(json.dumps(show(con,a.action=='resume'),indent=2))
            elif a.action=='audit':
                errs=verify(con)
                for item in rows(con):
                    if not all(item[k].strip() for k in ('description','desired_outcome','acceptance_details')):
                        errs.append(f'{item["id"]}: incomplete descriptive tracker record')
                    if item['state'] not in FINAL:errs.append(f'{item["id"]}: unresolved {item["state"]}')
                    if item['state']=='Done':
                        if not item['evidence_ref'] or not item['source_commit']:errs.append(f'{item["id"]}: missing proof')
                        if item['risk']=='high-risk' and not item['approval_ref']:errs.append(f'{item["id"]}: missing approval')
                    if item['state']=='Cancelled' and not item['approval_ref']:errs.append(f'{item["id"]}: missing cancellation authorization')
                if errs:print(*errs,sep='\n');return 1
                print('PASS: local declared task closure consistent (references and approvals NOT externally authenticated)')
            elif a.action=='verify':
                errs=verify(con)
                if errs:print(*errs,sep='\n');return 1
                print('PASS: local event chain and task versions consistent (not externally authenticated)')
            if a.action in ('add','update','enrich','amend','transition'):
                report(con,a.db.parent/'TASKS.md')
        finally: con.close()
    except (ValueError,sqlite3.Error,OSError) as ex:
        print('FAIL: '+str(ex),file=sys.stderr);return 2
    return 0

if __name__=='__main__':sys.exit(main())
