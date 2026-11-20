#!/usr/bin/env python3
"""Read-only structural audit of a project-local SDLC task tracker.

Does not run test commands, inspect evidence destinations or authorize actions.
Exit 0 only when the supplied tracker is structurally consistent. --final also
requires all non-cancelled tasks to be Done and acceptance fields present.
"""
import argparse
import json
import sys
from pathlib import Path

STATES = {'Inbox', 'Triaged', 'Ready', 'In Progress', 'In Review', 'In QA',
          'Ready for Release', 'Released', 'Verified', 'Done', 'Cancelled'}
RISKS = {'small', 'standard', 'high-risk'}


def filled(value):
    return isinstance(value, str) and bool(value.strip())


def audit(doc, final=False):
    errors = []
    def fail(msg): errors.append(msg)
    if not isinstance(doc, dict):
        return ['tracker must be a JSON object']
    if doc.get('schema_version') != 1:
        fail('schema_version must be 1')
    if not filled(doc.get('tracker_id')):
        fail('missing tracker_id')
    if doc.get('source_of_truth') != 'local':
        fail('only local tracker data is supported; external issue services are not integrated')
    if type(doc.get('revision')) is not int or doc['revision'] < 1:
        fail('revision must be a positive integer')
    items = doc.get('items')
    if not isinstance(items, list) or not items:
        return errors + ['items must be a nonempty list']
    by_id = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            fail(f'items[{index}] must be an object')
            continue
        name = item.get('id') if filled(item.get('id')) else f'items[{index}]'
        if not filled(item.get('id')):
            fail(f'{name}: missing id')
        elif name in by_id:
            fail(f'{name}: duplicate id')
        else:
            by_id[name] = item
        for field in ('title', 'type', 'priority', 'owner', 'next_action', 'gate_ledger_ref'):
            if not filled(item.get(field)):
                fail(f'{name}: missing {field}')
        if item.get('risk') not in RISKS:
            fail(f'{name}: invalid risk')
        if item.get('state') not in STATES:
            fail(f'{name}: invalid state')
        acceptance = item.get('acceptance_ids')
        if not isinstance(acceptance, list) or not acceptance or any(not filled(a) for a in acceptance):
            fail(f'{name}: acceptance_ids must contain at least one real requirement ID')
        elif len(acceptance) != len(set(acceptance)):
            fail(f'{name}: duplicate acceptance_ids')
        dependencies = item.get('dependencies')
        if not isinstance(dependencies, list) or any(not filled(d) for d in dependencies):
            fail(f'{name}: dependencies must be an array of item IDs')
        elif len(dependencies) != len(set(dependencies)):
            fail(f'{name}: duplicate dependencies')
        if type(item.get('blocked')) is not bool:
            fail(f'{name}: blocked must be boolean')
        if item.get('blocked') is True:
            b = item.get('blocker')
            if not isinstance(b, dict) or any(not filled(b.get(k)) for k in ('reason', 'owner', 'unblock_action')):
                fail(f'{name}: blocked item must name a reason, owner and unblock_action')
        elif item.get('blocker') is not None:
            fail(f'{name}: nonblocked item has a stale blocker record')
        update = item.get('last_update')
        if not isinstance(update, dict) or any(not filled(update.get(k)) for k in ('actor', 'at', 'note')):
            fail(f'{name}: missing last_update actor, at or note')
        if type(item.get('scope_revision')) is not int or item['scope_revision'] < 1:
            fail(f'{name}: invalid scope_revision')
        if not filled(item.get('artifact_revision')):
            fail(f'{name}: missing artifact_revision')
        refs = item.get('evidence_refs')
        if not isinstance(refs, list) or any(not filled(r) for r in refs):
            fail(f'{name}: evidence_refs must be an array of strings')
        if item.get('state') == 'Done':
            if item.get('blocked'):
                fail(f'{name}: Done cannot be blocked')
            if not isinstance(refs, list) or not refs:
                fail(f'{name}: Done without evidence_refs')
            closure = item.get('closure')
            if not isinstance(closure, dict):
                fail(f'{name}: Done without closure record')
            else:
                for key in ('accepted_by', 'accepted_at', 'self_check_ref', 'parent_check_ref',
                            'scope_revision', 'artifact_revision'):
                    if key in ('scope_revision',):
                        if closure.get(key) != item.get(key): fail(f'{name}: stale closure scope_revision')
                    elif not filled(closure.get(key)) or (key == 'artifact_revision' and closure.get(key) != item.get(key)):
                        fail(f'{name}: missing or stale closure {key}')
                if closure.get('accepted_by') != 'sdlc-orchestrator':
                    fail(f'{name}: closure acceptance must be by orchestrator')
                if item.get('risk') == 'high-risk':
                    if not filled(closure.get('independent_review_ref')):
                        fail(f'{name}: high-risk Done requires independent_review_ref')
                    if not filled(item.get('reviewer')) or item.get('reviewer') == item.get('owner'):
                        fail(f'{name}: high-risk reviewer must differ from implementer')
                if type(closure.get('release_in_scope')) is not bool:
                    fail(f'{name}: closure must state whether release was in scope')
                if closure.get('release_in_scope') is True and not filled(closure.get('release_verification_ref')):
                    fail(f'{name}: release in scope requires actual release verification reference')
        if item.get('state') == 'Cancelled':
            if not isinstance(item.get('cancellation'), dict) or not filled(item['cancellation'].get('reason')):
                fail(f'{name}: Cancelled requires explicit rationale; do not silently drop scope')
            elif final and not filled(item['cancellation'].get('authorization_ref')):
                fail(f'{name}: final claim cannot treat cancellation as accepted without authorized scope change')
        if final and item.get('state') not in ('Done', 'Cancelled'):
            fail(f'{name}: final full-completion claim with unresolved {item.get("state")}')
    for name, item in by_id.items():
        deps = item.get('dependencies', [])
        if not isinstance(deps, list):
            continue
        for dep in deps:
            if dep == name:
                fail(f'{name}: self-dependency')
            elif dep not in by_id:
                fail(f'{name}: unknown dependency {dep}')
            elif item.get('state') == 'Done' and by_id[dep].get('state') != 'Done':
                fail(f'{name}: Done while dependency {dep} is not Done')
    # Detect multi-item dependency cycles even when all items are otherwise valid.
    visited, active = set(), set()
    def visit(name):
        if name in active:
            fail(f'{name}: dependency cycle')
            return
        if name in visited:
            return
        visited.add(name); active.add(name)
        for dep in by_id[name].get('dependencies', []):
            if dep in by_id:
                visit(dep)
        active.remove(name)
    for name in by_id:
        visit(name)
    return errors


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tracker', type=Path)
    parser.add_argument('--final', action='store_true', help='Require every active item to be Done')
    args=parser.parse_args()
    try:
        tracker=json.loads(args.tracker.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        print(f'FAIL: unable to read tracker: {exc}', file=sys.stderr)
        return 2
    problems=audit(tracker, args.final)
    if problems:
        for problem in problems: print(f'FAIL: {problem}')
        return 1
    print('PASS: tracker structure and declared states consistent (no external evidence authenticated)')
    return 0


if __name__=='__main__':
    sys.exit(main())
