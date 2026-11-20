#!/usr/bin/env python3
"""Generate optional Codex, Antigravity and OpenCode agent definitions from canonical personas.

Call --check in CI to detect stale or hand-edited generated profiles. This script
never writes to an external project or changes runtime configuration.
"""
import argparse
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
ROLE_FILES = sorted((ROOT / 'references' / 'roles').glob('*.md'))
MAIN = ROOT / 'references' / 'engineering-director.md'


def role_info(src):
    doc = src.read_text(encoding='utf-8')
    title = doc.splitlines()[0].lstrip('#').strip()
    mission = next((line.split('**Mission:**', 1)[1].strip()
                    for line in doc.splitlines() if line.startswith('**Mission:**')), '')
    return src.stem, title, mission, doc


def yaml_header(data):
    return '---\n' + yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=1000) + '---\n\n'


def specialist_body(role, title, doc):
    return (
        f'# Delegated expert: {title}\n\n'
        'Operate as the assigned domain specialist for the **EngiHelm**. '
        'Follow the parent\'s bounded task and the authoritative persona below. '
        'Do not re-orchestrate the team or claim autonomous authority. '
        'Use only tools actually available; prove claims with paths, commands or output. '
        'Track your assigned work in the canonical task tracker or return a structured delta for the Orchestrator to apply; report blockers, ownership, evidence and next action, and never self-mark Done. Follow universal Completion Assurance: author CHECK/EXPECT gates before work, self-check your own deliverable, return gate-by-gate observed evidence and unresolved gaps; never claim self-check as independent verification. See canonical charter. '
        'For coding/design work enforce the Ponytail-inspired G2S simplicity gate: inspect and reuse existing code before adding dependencies or layers, preserve all acceptance and safety requirements, and report material overengineering with a viable simpler alternative rather than subjective style. '
        'For coding/debugging follow references/implementation-methods.md; choose proportional effort via references/operating-modes.md, maintain recoverable work-item state via references/orchestration-state.md, and honor the task capability budget. Never transition directly to Done: the Director must use scripts/verify_and_close.py with a task-scoped COMPLETE root ledger; no complete code claim without the root-ledger + SQLite + gate-receipt decision from scripts/completion_decision.py; never assert trusted executable verification without protected gate runner evidence. '
        'Return the assignment result in the Skill\'s handoff format. '
        'Do not independently authorize production, destructive changes, external communication or expenditure.\n\n'
        '## Canonical expert charter\n\n' + doc.strip() + '\n'
    )


def main_body():
    return (
        '# Principal Engineering Director — EngiHelm\n\n'
        'Act as the principal-level coordinator, **not** a generic task router. '
        'Load and obey the `engihelm` Skill for task intake, risk classification, '
        'expert staffing, bounded delegation, integration, independent assurance, Agile practices and truthful status. '
        'Enforce references/task-tracking.md: maintain the one authoritative tracker for all agents, including your own work, reconcile delegated deltas and block premature Done; use scripts/verify_and_close.py for the only guarded Verified-to-Done transition. Follow references/completion-assurance.md: root gates before work, each specialist prework gates and self-check, orchestrator re-verification, integration gates and original-request reconciliation. Own final completion assurance personally. '
        'Enforce references/engineering-efficiency.md and the G2S/ROOT-SIMP overengineering challenge across architecture, implementation, independent review and the integrated diff. Protect necessary complexity; do not waive completion proof to shorten code. '
        'Use references/implementation-methods.md for coding, references/operating-modes.md for proportionate process, references/orchestration-state.md for durable recovery, references/delegation-budget.md for cost-aware staffing and references/enforcement.md for unified SQLite/ledger/receipt completion decisions; test the Skill with paired real behavior trials. '
        'Use the actual host delegation mechanism if available, otherwise label sequential role passes. '
        'Do not claim approvals or tests without proof.\n\n'
        '## Canonical leadership charter\n\n' + MAIN.read_text(encoding='utf-8').strip() + '\n'
    )


def expected_files():
    generated = {}
    for path in ROLE_FILES:
        role, title, mission, doc = role_info(path)
        body = specialist_body(role, title, doc)
        # TOML multiline literal strings preserve the persona exactly; none of the charters contain '''.
        if "'''" in body:
            raise ValueError(f'TOML literal terminator in {role}')
        descr = f'Expert {title}. Delegate when: {mission}'
        toml = (f'name = "{role}"\n'
                f'description = {toml_quoted(descr)}\n'
                f"developer_instructions = '''\n{body}'''\n")
        generated[Path(f'adapters/codex/agents/{role}.toml')] = toml
        ag = yaml_header({'name': role, 'description': descr,
                          'mainAgent': False, 'subagent': True}) + body
        generated[Path(f'adapters/antigravity/agents/{role}.md')] = ag
        oc = yaml_header({'description': descr, 'mode': 'subagent'}) + body
        generated[Path(f'adapters/opencode/agents/{role}.md')] = oc
    m = main_body()
    name = 'engihelm'
    desc = ('Principal Engineering Director and EngiHelm. '
            'Coordinate only relevant expert specialists with transparent handoffs and evidence-based delivery.')
    generated[Path(f'adapters/antigravity/agents/{name}.md')] = (yaml_header(
        {'name': name, 'description': desc, 'mainAgent': True, 'subagent': False}) + m)
    generated[Path(f'adapters/opencode/agents/{name}.md')] = (yaml_header(
        {'description': desc, 'mode': 'primary'}) + m)
    return generated


def toml_quoted(s):
    # JSON double-quoted scalar is valid TOML for these Unicode text values.
    import json
    return json.dumps(s, ensure_ascii=False)


def run(check=False):
    expected=expected_files()
    stale=[]
    for rel, content in expected.items():
        path=ROOT/rel
        if check:
            if not path.is_file() or path.read_text(encoding='utf-8') != content:
                stale.append(str(rel))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
    # Any obsolete profile means a role exists that the canonical source no longer contains.
    for platform, extension in [('codex', '.toml'), ('antigravity', '.md'), ('opencode', '.md')]:
        d=ROOT/'adapters'/platform/'agents'
        for path in d.glob('*'+extension):
            if path.relative_to(ROOT) not in expected:
                stale.append(str(path.relative_to(ROOT)))
                if not check:
                    path.unlink()
    if check and stale:
        print('FAIL: adapter profiles out of sync:', *stale, sep='\n  ')
        return 1
    print(f'PASS: {len(ROLE_FILES)} specialist personas, 3 adapters, {len(expected)} generated profiles')
    return 0


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify profiles match canonical role charters without writing')
    args=parser.parse_args()
    sys.exit(run(check=args.check))
