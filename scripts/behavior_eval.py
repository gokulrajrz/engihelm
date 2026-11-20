#!/usr/bin/env python3
"""Compare real baseline-vs-Skill run reports against explicit failure probes.

This tool cannot launch an LLM. A separate authorized runtime adapter must run
isolated sessions, collect tool traces and provide observed-evidence reports.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

VALID={'pass','fail','unverified'}

def evaluate(manifest,baseline,skill):
    if manifest.get('version')!=1 or not isinstance(manifest.get('scenarios'),list) or not manifest['scenarios']:
        raise ValueError('scenario manifest invalid')
    spec={s['id']:s for s in manifest['scenarios']}
    if len(spec)!=len(manifest['scenarios']):raise ValueError('duplicate scenario IDs')
    for s in spec.values():
        if not s.get('prompt') or not s.get('checks'):raise ValueError('scenario needs prompt and checks')
    indexed={}
    for mode,report in (('baseline',baseline),('skill',skill)):
        if report.get('mode')!=mode or not isinstance(report.get('runs'),list):raise ValueError(f'invalid {mode} report')
        runs={r.get('scenario_id'):r for r in report['runs'] if isinstance(r,dict)}
        if len(runs)!=len(report['runs']) or set(runs)!=set(spec):raise ValueError(f'{mode}: missing/duplicate/extra scenario runs')
        indexed[mode]=runs
    rows=[];problems=[]
    for sid,scenario in spec.items():
        b=indexed['baseline'][sid];s=indexed['skill'][sid]
        expected_input=hashlib.sha256(json.dumps(scenario,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')).hexdigest()
        if b.get('input_revision')!=expected_input or s.get('input_revision')!=expected_input:
            problems.append(f'{sid}: input_revision must match the actual scenario content')
        if b.get('run_id')==s.get('run_id') or b.get('raw_trace_ref')==s.get('raw_trace_ref'):
            problems.append(f'{sid}: baseline and Skill require distinct runs and traces')
        for common in ('model_id','runtime','source_revision','input_revision'):
            if not b.get(common) or b[common]!=s.get(common):
                problems.append(f'{sid}: {common} differs or absent; cannot compare runs')
        for mode,r in (('baseline',b),('skill',s)):
            if not r.get('run_id') or not r.get('raw_trace_ref'):
                problems.append(f'{sid}: {mode}: missing real run ID or raw trace reference')
            if r.get('simulated') is not False:
                problems.append(f'{sid}: {mode}: missing or simulated run identity cannot certify behavioral improvement')
            seen={}
            for test in scenario['checks']:
                obs=r.get('observations',{}).get(test['id'],{})
                verdict=obs.get('verdict','unverified')
                if verdict not in VALID:
                    problems.append(f'{sid}: {mode}: invalid verdict for {test["id"]}')
                    verdict='unverified'
                if verdict=='pass' and not obs.get('evidence_ref'):
                    problems.append(f'{sid}: {mode}: passing {test["id"]} without observed evidence')
                    verdict='unverified'
                seen[test['id']]=verdict
            rows.append({'scenario_id':sid,'mode':mode,'checks':seen,'all_pass':all(v=='pass' for v in seen.values())})
    paired=[]
    for sid in spec:
        b=next(r for r in rows if r['scenario_id']==sid and r['mode']=='baseline')
        s=next(r for r in rows if r['scenario_id']==sid and r['mode']=='skill')
        paired.append({'scenario_id':sid,'baseline_pass':b['all_pass'],'skill_pass':s['all_pass'],
                       'regression':b['all_pass'] and not s['all_pass'],
                       'improvement':not b['all_pass'] and s['all_pass']})
    return {'valid_comparison':not problems,'problems':problems,'paired_results':paired,
            'summary':{'scenarios':len(paired),'skill_all_pass':sum(x['skill_pass'] for x in paired),
                       'baseline_all_pass':sum(x['baseline_pass'] for x in paired),
                       'improvements':sum(x['improvement'] for x in paired),
                       'regressions':sum(x['regression'] for x in paired)},
            'disclaimer':'Human/independent observation needed; references alone do not authenticate tool activity.'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--skill',type=Path,required=True)
    a=p.parse_args()
    try:
        output=evaluate(*(json.loads(f.read_text()) for f in (a.manifest,a.baseline,a.skill)))
    except (ValueError,KeyError,FileNotFoundError,TypeError) as ex:
        print('FAIL: '+str(ex),file=sys.stderr);return 2
    print(json.dumps(output,indent=2))
    return 0 if output['valid_comparison'] else 1
if __name__=='__main__':sys.exit(main())
