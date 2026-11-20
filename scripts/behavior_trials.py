#!/usr/bin/env python3
"""Run paired baseline/with-Skill scenarios via an explicitly supplied agent adapter.

Does not provide an AI backend. The adapter must launch a real isolated agent
session per invocation and record independently observable artifacts/tool traces.
Syntax: runner --mode baseline|skill --scenario <json> --output <json>
               --workdir <empty-dir> [--skill-root <dir>]
"""
import argparse
import json
import random
import re
import subprocess
import sys
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--runner',type=Path,required=True,help='Explicitly approved executable adapter; NOT a shell command')
    p.add_argument('--skill-root',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--seed',type=int,default=42)
    p.add_argument('--timeout-seconds',type=int,default=900)
    a=p.parse_args()
    try:
        manifest=json.loads(a.manifest.read_text())
        if manifest.get('version')!=1 or not isinstance(manifest.get('scenarios'),list) or not manifest['scenarios']:
            raise ValueError('invalid manifest')
        if not a.runner.is_file() or not a.skill_root.joinpath('SKILL.md').is_file():
            raise ValueError('runner executable or Skill entrypoint missing')
        if not 1<=a.timeout_seconds<=3600:raise ValueError('timeout 1..3600 seconds')
        if a.output_dir.exists():raise ValueError('output directory must be new to prevent overwriting results')
        a.output_dir.mkdir(parents=True)
        reports={'baseline':{'mode':'baseline','runs':[]},'skill':{'mode':'skill','runs':[]}}
        if len({s.get('id') for s in manifest['scenarios']})!=len(manifest['scenarios']):
            raise ValueError('duplicate scenario IDs')
        rng=random.Random(a.seed)
        for scenario in manifest['scenarios']:
            if not isinstance(scenario,dict) or not isinstance(scenario.get('id'),str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}',scenario['id']) or not scenario.get('prompt'):
                raise ValueError('scenario needs safe slug ID and prompt')
            modes=['baseline','skill'];rng.shuffle(modes)
            for mode in modes:
                work=a.output_dir/scenario['id']/mode
                work.mkdir(parents=True)
                prompt=work/'scenario.json';prompt.write_text(json.dumps(scenario,indent=2))
                output=work/'report.json'
                executable=[sys.executable,str(a.runner)] if a.runner.suffix=='.py' else [str(a.runner)]
                args=[*executable,'--mode',mode,'--scenario',str(prompt),'--output',str(output),'--workdir',str(work)]
                if mode=='skill':args.extend(['--skill-root',str(a.skill_root)])
                proc=subprocess.run(args,capture_output=True,text=True,timeout=a.timeout_seconds)
                (work/'adapter-stdout.log').write_text(proc.stdout)
                (work/'adapter-stderr.log').write_text(proc.stderr)
                if proc.returncode!=0 or not output.is_file():
                    raise ValueError(f'{scenario["id"]}/{mode}: adapter did not produce a report; see logs')
                result=json.loads(output.read_text())
                if result.get('scenario_id')!=scenario['id']:
                    raise ValueError(f'{scenario["id"]}/{mode}: returned wrong scenario')
                reports[mode]['runs'].append(result)
        for mode,report in reports.items():
            (a.output_dir/f'{mode}.json').write_text(json.dumps(report,indent=2))
        print('PASS: agent adapter returned paired reports. Now independently inspect traces and run behavior_eval.py; do not infer validity from this harness.')
        return 0
    except (ValueError,OSError,json.JSONDecodeError,subprocess.TimeoutExpired) as e:
        print('FAIL: '+str(e),file=sys.stderr)
        return 2

if __name__=='__main__':sys.exit(main())
