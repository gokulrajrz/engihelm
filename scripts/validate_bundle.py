#!/usr/bin/env python3
"""Validate core Agent Skill plus all three optional native adapter formats."""
import re
import json
import sys
import tomllib
from pathlib import Path
import yaml
from build_adapters import ROOT, ROLE_FILES, expected_files

REQUIRED_REFS={
    'engineering-director', 'orchestration', 'operating-modes', 'agile-operating-model',
    'handoff-contract', 'quality-gates', 'incident-playbook',
    'role-index', 'runtime-portability', 'example-runs', 'completion-assurance', 'engineering-efficiency', 'task-tracking', 'implementation-methods', 'orchestration-state', 'delegation-budget', 'enforcement', 'behavioral-evaluation',
}
REQUIRED_TEMPLATES={'work-item','architecture-decision','sprint-board','release-runbook','test-report','assurance-plan','assurance-leaf','assurance-branch','engineering-efficiency-review'}


def frontmatter(raw):
    matched=re.match(r'^---\n(.*?)\n---\n',raw,re.DOTALL)
    if not matched:
        raise ValueError('missing frontmatter')
    return yaml.safe_load(matched.group(1)),raw[matched.end():]


def main():
    errors=[]
    skill=ROOT/'SKILL.md'
    for filename in ('LICENSE','RELEASE.json','CHANGELOG.md','README.installed.md'):
        if not (ROOT/filename).is_file(): errors.append(f'missing release metadata {filename}')
    if (ROOT/'RELEASE.json').is_file():
        try:
            release=json.loads((ROOT/'RELEASE.json').read_text(encoding='utf-8'))
            if release.get('name')!='engihelm' or not release.get('version'):
                errors.append('invalid release name/version')
        except Exception as e:
            errors.append('invalid release metadata: '+str(e))
    try:
        meta,body=frontmatter(skill.read_text(encoding='utf-8'))
        if set(meta)!={'name','description'}: errors.append('SKILL.md frontmatter must have name and description only')
        if meta.get('name')!='engihelm': errors.append('wrong name')
        if len(meta.get('description',''))>1024: errors.append('description too long')
        if len(body.splitlines())>=500: errors.append('core Skill too long')
        if '[TODO' in body:errors.append('leftover placeholder in core Skill')
        for ref in REQUIRED_REFS:
            if not (ROOT/'references'/f'{ref}.md').is_file():errors.append(f'missing reference {ref}')
        for template in REQUIRED_TEMPLATES:
            if not (ROOT/'assets/templates'/f'{template}.md').is_file():errors.append(f'missing template {template}')
        for rid in ROLE_FILES:
            charter=rid.read_text(encoding='utf-8')
            if 'Expert decision standard' not in charter or 'Shared operating rules' not in charter or 'Mandatory completion assurance' not in charter or 'Mandatory engineering efficiency' not in charter or 'Mandatory task tracking' not in charter or 'Formal execution, recovery and evidence' not in charter:
                errors.append(f'incomplete expert role {rid.name}')
        if len(ROLE_FILES)!=14:errors.append(f'expected 14 roles; got {len(ROLE_FILES)}')
        if 'references/runtime-portability.md' not in body:errors.append('missing portability link in Skill')
        if 'references/task-tracking.md' not in body:errors.append('missing mandatory tracking link in Skill')
        for name in ('implementation-methods','operating-modes','orchestration-state','delegation-budget','enforcement','behavioral-evaluation'):
            if f'references/{name}.md' not in body:errors.append(f'missing mandatory operating reference {name}')
        for name in ('state_store.py','gate_runner.py','completion_decision.py','verify_and_close.py','codex_trial_adapter.py','behavior_eval.py','behavior_trials.py','delegation_plan.py'):
            if not (ROOT/'scripts'/name).is_file():errors.append(f'missing working module {name}')
        for name in ('assets/behavioral/scenarios.json','assets/ci/github-required-check.example.yml'):
            if not (ROOT/name).is_file():errors.append(f'missing exercise/policy template {name}')
        if 'references/completion-assurance.md' not in body:errors.append('missing universal assurance link in Skill')
        if 'references/engineering-efficiency.md' not in body:errors.append('missing universal engineering efficiency link in Skill')
        root=json.loads((ROOT/'assets/templates/assurance-root.json').read_text())
        if 'ROOT-SIMP' not in {gate['id'] for gate in root['gates']}: errors.append('missing root simplicity gate')
        if 'ROOT-TRACK' not in {gate['id'] for gate in root['gates']}: errors.append('missing root tracker gate')
        if not (ROOT/'scripts/task_tracker_audit.py').is_file(): errors.append('missing legacy tracker audit script')
        if 'scripts/completion_decision.py' not in body:errors.append('missing unified final-decision instructions')
        if 'scripts/verify_and_close.py' not in body:errors.append('missing guarded task-closure instructions')
        if 'scripts/codex_trial_adapter.py' not in body:errors.append('missing real Codex behavior adapter instructions')
        for scenario in json.loads((ROOT/'assets/behavioral/scenarios.json').read_text())['scenarios']:
            if not (ROOT/'assets/behavioral/fixtures'/scenario['id']).is_dir():errors.append('missing scenario fixture '+scenario['id'])
        if not (ROOT/'assets/templates/task-tracker.json').is_file():errors.append('missing tracker template')
        if not (ROOT/'assets/templates/assurance-ledger.json').is_file():errors.append('missing machine-auditable assurance template')
        if not (ROOT/'assets/templates/assurance-root.json').is_file():errors.append('missing root assurance template')
        if not (ROOT/'assets/templates/completion-small.example.json').is_file():errors.append('missing lightweight root ledger example')
        if 'OpenCode `subagent`' in body:errors.append('core mentions OpenCode-specific tool')
    except Exception as ex:
        errors.append('Skill core parse failed: '+str(ex))
    generated=expected_files()
    for relative,expected in generated.items():
        path=ROOT/relative
        if not path.exists():
            errors.append('missing adapter profile '+str(relative))
            continue
        if path.read_text(encoding='utf-8')!=expected:
            errors.append('stale adapter profile '+str(relative))
        try:
            if relative.suffix=='.toml':
                data=tomllib.loads(path.read_text(encoding='utf-8'))
                if not all(data.get(k) for k in ('name','description','developer_instructions')):
                    errors.append('missing TOML agent keys '+str(relative))
            else:
                data,_=frontmatter(path.read_text(encoding='utf-8'))
                if not data.get('description'):errors.append('missing agent description '+str(relative))
                if 'antigravity' in relative.parts:
                    if not isinstance(data.get('subagent'),bool) or not isinstance(data.get('mainAgent'),bool):
                        errors.append('invalid Antigravity modes '+str(relative))
                if 'opencode' in relative.parts and data.get('mode') not in ('primary','subagent'):
                    errors.append('invalid OpenCode mode '+str(relative))
        except Exception as ex:
            errors.append(f'invalid adapter {relative}: {ex}')
    for runtime,ext in [('codex','.toml'),('antigravity','.md'),('opencode','.md')]:
        folder=ROOT/'adapters'/runtime/'agents'
        actual={p.relative_to(ROOT) for p in folder.glob('*'+ext)}
        expected_subset={p for p in generated if runtime in p.parts}
        if actual!=expected_subset:
            errors.append(f'extra or missing {runtime} profiles: {sorted(map(str,actual^expected_subset))}')
        if not (ROOT/'adapters'/runtime/'README.md').exists():errors.append(f'missing {runtime} README')
    if not (ROOT/'adapters/README.md').exists():errors.append('missing generic adapter README')
    if not (ROOT/'agents/openai.yaml').is_file():errors.append('missing ChatGPT metadata')
    if errors:
        print(*('ERROR '+e for e in errors),sep='\n')
        return 1
    print(f'PASS: portable core, {len(ROLE_FILES)} expert roles, {len(generated)} generated agent profiles, runtime guides and templates')
    return 0


if __name__=='__main__':sys.exit(main())
