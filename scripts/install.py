#!/usr/bin/env python3
"""Non-destructive project installer for the portable SDLC Skill and optional native agents.

Dry-run by default. --apply installs, --overwrite backs up existing changed files.
No runtime configuration, MCP settings or repositories are edited beyond the
explicitly planned Skill and agent profile paths.
"""
import argparse
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME='engihelm'
LEGACY_PATHS=(
    '.agents/skills/agile-sdlc-orchestrator',
    '.opencode/skills/agile-sdlc-orchestrator',
    '.claude/skills/agile-sdlc-orchestrator',
    '.agents/agents/sdlc-orchestrator.md',
    '.opencode/agents/sdlc-orchestrator.md',
    '.codex/agents/sdlc-orchestrator.toml',
)
LAYOUTS={
    'codex': ('.agents/skills', '.codex/agents', 'codex'),
    'antigravity': ('.agents/skills', '.agents/agents', 'antigravity'),
    'opencode': ('.opencode/skills', '.opencode/agents', 'opencode'),
    'skill-only': ('.agents/skills', None, None),
}


def core_files():
    base=[ROOT/'SKILL.md', ROOT/'README.md', ROOT/'agents/openai.yaml', ROOT/'adapters/README.md', ROOT/'LICENSE', ROOT/'RELEASE.json', ROOT/'CHANGELOG.md']
    base.extend((ROOT/'references').rglob('*.md'))
    base.extend([ROOT/'scripts'/n for n in ('assurance_audit.py','task_tracker_audit.py','state_store.py','gate_runner.py','completion_decision.py','verify_and_close.py','codex_trial_adapter.py','behavior_eval.py','behavior_trials.py','delegation_plan.py')])
    base.extend((ROOT/'assets').rglob('*'))
    base.extend((ROOT/'adapters').glob('*/README.md'))
    return sorted((p for p in base if p.is_file()), key=str)


def targets(project, runtime):
    skill_base, agent_base, adapter = LAYOUTS[runtime]
    pairs=[]
    for src in core_files():
        content=ROOT/'README.installed.md' if src == ROOT/'README.md' else src
        pairs.append((content, project/skill_base/NAME/src.relative_to(ROOT)))
    if agent_base:
        for src in sorted((ROOT/'adapters'/adapter/'agents').glob('*')):
            if src.is_file():
                pairs.append((src, project/agent_base/src.name))
    return pairs


def status(src,dst):
    if dst.is_symlink(): return 'unsafe-symlink'
    if not dst.exists(): return 'create'
    if not dst.is_file(): return 'unsafe-nonfile'
    return 'identical' if src.read_bytes()==dst.read_bytes() else 'different'


def unsafe_parent(project, dst):
    rel=dst.relative_to(project)
    cur=project
    for part in rel.parts[:-1]:
        cur=cur/part
        if cur.is_symlink(): return True
        if cur.exists() and not cur.is_dir(): return True
    return False


def existing_legacy(project):
    """Read-only inspection; never follow legacy symlinks or touch project data."""
    found=[]
    for rel in LEGACY_PATHS:
        candidate=project/rel
        if candidate.exists() or candidate.is_symlink():
            found.append((rel, 'symlink' if candidate.is_symlink() else
                          'directory' if candidate.is_dir() else 'file'))
    return found


def show_legacy_plan(items):
    if not items:
        return
    print('WARNING: previous Agile SDLC Orchestrator installation detected:')
    for rel,kind in items:
        print(f'  legacy {kind}: {rel}')
    print('Migration plan (no automatic deletion or modification):')
    print('  1. Back up any modified legacy Skill/profile files and project docs/sdlc/ data.')
    print('  2. Install and validate EngiHelm; temporarily coexist only with --acknowledge-legacy.')
    print('  3. After verifying new Skill discovery, manually retire only the old Skill/profile paths above.')
    print('  4. Never remove docs/sdlc/state.db, TASKS.md, its manifest or backups as part of migration.')


def new_backup(dst):
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup=dst.with_name(f'{dst.name}.backup-{stamp}')
    i=1
    while backup.exists() or backup.is_symlink():
        backup=dst.with_name(f'{dst.name}.backup-{stamp}-{i}')
        i+=1
    return backup


def atomic_copy(src,dst):
    dst.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.sdlc-skill-',dir=dst.parent)
    try:
        with os.fdopen(fd,'wb') as out, src.open('rb') as stream:
            shutil.copyfileobj(stream,out)
        os.replace(tmp,dst)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime',choices=LAYOUTS.keys(),required=True)
    parser.add_argument('--project',type=Path,required=True)
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--overwrite',action='store_true',help='Requires --apply; backup and replace changed files')
    parser.add_argument('--acknowledge-legacy',action='store_true',help='Allow temporary coexistence with detected legacy Skill; never removes old files')
    opts=parser.parse_args(argv)
    project=opts.project.expanduser().resolve()
    if not project.is_dir():parser.error('--project must be an existing directory')
    if opts.overwrite and not opts.apply:parser.error('--overwrite requires --apply')
    if project==ROOT or ROOT in project.parents:parser.error('target must not be inside the Skill source')
    legacy=existing_legacy(project)
    show_legacy_plan(legacy)
    if legacy and opts.apply and not opts.acknowledge_legacy:
        print('BLOCKED: legacy Skill detected; remove/retire legacy files or pass --acknowledge-legacy after reviewing the plan.', file=sys.stderr)
        print('No changes made',file=sys.stderr)
        return 3
    operations=[]
    for src,dst in targets(project,opts.runtime):
        state='unsafe-parent' if unsafe_parent(project,dst) else status(src,dst)
        operations.append((src,dst,state))
    unsafe=[(dst,st) for _,dst,st in operations if st.startswith('unsafe')]
    if unsafe:
        for p,s in unsafe: print(f'ERROR {s}: {p}',file=sys.stderr)
        print('No changes made',file=sys.stderr)
        return 2
    conflicts=[(dst,st) for _,dst,st in operations if st=='different']
    print(f'{"APPLY" if opts.apply else "PREVIEW"}: {opts.runtime} / {project}')
    for _,dst,st in operations:
        if st!='identical': print(f'  {st}: {dst.relative_to(project)}')
    if conflicts and not opts.overwrite:
        print(f'CONFLICT: {len(conflicts)} existing different files; refusing replacement by default')
        if opts.apply: return 2
    if not opts.apply:
        print('Dry run only: add --apply to install. To replace conflicts, explicitly use --apply --overwrite.')
        return 0
    for src,dst,st in operations:
        if st=='identical':continue
        if st=='different':
            backup=new_backup(dst)
            shutil.copy2(dst,backup)
            print(f'  backup: {backup.relative_to(project)}')
        atomic_copy(src,dst)
    print(f'Installed {opts.runtime} Skill and optional native profiles (no runtime settings modified).')
    if legacy:
        print('WARNING: legacy installation remains; manually retire it after verifying EngiHelm (project state untouched).')
    return 0


if __name__=='__main__':sys.exit(main())
