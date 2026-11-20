# Behavioral Skill evaluation: baseline versus Skill

Structural unit tests of scripts/personas are **not** behavioral evidence that real AI agents follow the Skill.

Use paired scenarios (`assets/behavioral/scenarios.json`) across low/standard/high-risk tasks. For each scenario: hold model version, runtime, tools, repository, prompts and task constraints constant; run **baseline** without this Skill and **skill** with the Skill. Start each run with an isolated fresh repository/worktree and context; pin the same input revision; rotate order and repeat enough times to examine variability. Ensure the baseline is not contaminated by prior Skill instructions or memory.

Each agent runtime needs an adapter that records raw run transcript, actual tool calls, diff/commit, tests, tokens/cost/time (if available) and an independent human/auditor rubric. `scripts/behavior_trials.py` can coordinate baseline/Skill runs through an explicitly supplied approved runtime adapter, but does not provide a model backend or authenticate returned reports. `scripts/behavior_eval.py` is the **read-only paired-results evaluator**; it does not spawn models, infer behavior from prose, or generate a fake baseline. The `assets/behavioral/report-schema.example.json` example explains the machine-readable report format; record only observed evidence. Scenarios intentionally target skipped tests, scope omissions, unnecessary abstractions, fabricated evidence, misleading completion and lost tasks.

Before comparing runs, mark each rubric item `pass`, `fail`, or `unverified` with an observed evidence reference; missing evidence is never a pass. Report per-scenario baseline/Skill results and changes, not a one-number success rate without sample size. If no real agent runner is configured, record **NOT RUN**; fixture-based harness tests prove parsing only.

When the Skill performs poorly, revise the smallest relevant instruction, rerun previously failing scenarios, and watch for regressions/overhead. Measure false positives (overblocking correct behavior), false negatives (accepting wrong behavior), token cost and independent evidence quality. Do not promote a rule solely because it makes instructions longer.

## Runnable trial adapter contract

`python scripts/behavior_trials.py --manifest assets/behavioral/scenarios.json --runner /absolute/path/to/your-authorized-agent-adapter --skill-root . --output-dir /tmp/paired-sdlc-trials` invokes the supplied adapter once per scenario per mode, in different output/work directories, and passes `--skill-root` **only** to the Skill mode. The adapter must expose the command-line contract in the script docstring, provision isolated real repository contexts, record a distinct real run ID and raw trace for each mode, and set `simulated=false` only for genuine runs. It must calculate `input_revision` as SHA-256 of canonical scenario JSON (`json.dumps(scenario, sort_keys=True, separators=(',', ':'), ensure_ascii=False)`). Trials do not install models or grant API keys. Review raw traces for prompt contamination, unexpected tool writes and evidence completeness before scoring.

Then run `python scripts/behavior_eval.py --manifest ... --baseline <output>/baseline.json --skill <output>/skill.json`. The evaluator rejects missing evidence links, missing simulations markers, inconsistent models/inputs and reused trace identities; it cannot establish that externally supplied reports are honest. Retain a human-reviewed evaluation log for critical claims.

## Real Codex CLI adapter (optional, never mocked as genuine)

The package includes `scripts/codex_trial_adapter.py` and seven small, reproducible Git fixture repositories in `assets/behavioral/fixtures/`. With a locally installed, authenticated Codex CLI, run in a sandboxed test environment using an approved model and explicit paid-run opt-in:

```bash
export SDLC_CODEX_MODEL='your-authorized-pinned-model'
export SDLC_ALLOW_REAL_AGENT_TRIALS=1
python scripts/behavior_trials.py \
  --manifest assets/behavioral/scenarios.json \
  --runner scripts/codex_trial_adapter.py --skill-root . \
  --output-dir /tmp/sdlc-trial-results
python scripts/behavior_eval.py \
  --manifest assets/behavioral/scenarios.json \
  --baseline /tmp/sdlc-trial-results/baseline.json \
  --skill /tmp/sdlc-trial-results/skill.json
```

The adapter invokes actual `codex exec --json --ephemeral --ignore-user-config --sandbox workspace-write`, writes raw traces, stable fixture Git IDs and diffs, and assigns every quality check `unverified` until a **separate observer** grades it. It never executes agent-modified test code outside a separate verifier sandbox. Run tests/hidden oracles only in a trusted, isolated execution environment. Review agent traces and potential secrets before sharing them. The adapter may consume real model credits. If Codex CLI/auth is unavailable, record **NOT RUN**; offline contract tests are not proof of real coding-agent behavior. Other runtimes require their own reviewed adapters.
