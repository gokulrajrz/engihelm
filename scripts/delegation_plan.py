#!/usr/bin/env python3
"""Deterministic risk-aware, budget-aware model/task staffing suggestions (no agent calls)."""
import argparse
import json
import sys
from pathlib import Path

TIER={'light':0,'balanced':1,'deep':2}
RISK_MIN={'small':0,'standard':1,'high-risk':2}

def plan(spec):
    if not isinstance(spec,dict):raise ValueError('plan must be object')
    registry=spec.get('models');tasks=spec.get('tasks');max_budget=spec.get('budget_usd')
    max_parallel=spec.get('max_parallel',1)
    if not isinstance(registry,list) or not registry or not isinstance(tasks,list) or not tasks:
        raise ValueError('nonempty models and tasks required')
    if type(max_budget) not in (float,int) or max_budget<0:raise ValueError('budget_usd must be >=0')
    if type(max_parallel) is not int or not 1<=max_parallel<=16:raise ValueError('max_parallel 1..16 required')
    for m in registry:
        if not isinstance(m,dict) or not m.get('id') or m.get('tier') not in TIER:
            raise ValueError('invalid model registry entry')
        if any(type(m.get(k)) not in (float,int) or m[k]<0 for k in ('usd_per_1m_input','usd_per_1m_output')):
            raise ValueError('model prices must be explicit nonnegative numbers')
        if type(m.get('context_tokens')) is not int or m['context_tokens']<1000:
            raise ValueError('model context_tokens must be >=1000')
    if len({m['id'] for m in registry})!=len(registry):raise ValueError('duplicate model IDs')
    assignments=[];spent=0.0
    for t in tasks:
        if not isinstance(t,dict) or not t.get('id') or t.get('risk') not in RISK_MIN or t.get('complexity') not in TIER:
            raise ValueError('invalid task id/risk/complexity')
        if type(t.get('input_tokens')) is not int or type(t.get('output_tokens')) is not int or min(t['input_tokens'],t['output_tokens'])<0:
            raise ValueError('token estimates must be nonnegative integers')
        minimum=max(TIER[t['complexity']],RISK_MIN[t['risk']])
        requests=[('implementer',minimum)]
        if t['risk']!='small' or t.get('review_required') is True:
            requests.append(('independent-reviewer',max(1,minimum)))
        for role,level in requests:
            eligible=[m for m in registry if TIER[m['tier']]>=level and m['context_tokens']>=t['input_tokens']+t['output_tokens']]
            def price(m):return (m['usd_per_1m_input']*t['input_tokens']+m['usd_per_1m_output']*t['output_tokens'])/1_000_000
            eligible.sort(key=lambda m:(price(m),TIER[m['tier']],m['id']))
            if not eligible:
                assignments.append({'task_id':t['id'],'role':role,'status':'BLOCKED','reason':'no available model satisfies capability/context'})
                continue
            selected=eligible[0];cost=price(selected)
            if spent+cost>max_budget+1e-12:
                assignments.append({'task_id':t['id'],'role':role,'status':'BLOCKED','reason':'budget; do not downgrade quality'})
                continue
            spent+=cost
            assignments.append({'task_id':t['id'],'role':role,'status':'PLANNED','model_id':selected['id'],
                                'tier':selected['tier'],'estimated_usd':round(cost,6),
                                'context_note':'send bounded task, relevant files, gates and expected handoff only'})
    return {'estimated_total_usd':round(spent,6),'budget_usd':max_budget,'max_parallel':max_parallel,
            'assignments':assignments,'all_assignable':all(x['status']=='PLANNED' for x in assignments),
            'warning':'Estimates only. Pricing, measured tokens, host tool support and real independent contexts are unverified.'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('spec',type=Path)
    a=p.parse_args()
    try:
        result=plan(json.loads(a.spec.read_text()))
        print(json.dumps(result,indent=2))
        return 0 if result['all_assignable'] else 1
    except (ValueError,FileNotFoundError) as ex:
        print('FAIL: '+str(ex),file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
