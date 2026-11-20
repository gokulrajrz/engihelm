# EngiHelm — Installed Skill

**Edition:** 1.0.0 (2026-11-20). License status: private distribution; no public license grant (`LICENSE`).

This is an **installed runtime copy**, not the complete development source archive.
Use `SKILL.md` as the entrypoint and load only the relevant `references/*.md`.
The Principal Engineering Director coordinates fourteen expert personas; the host
must actually support delegation before claiming independent agents ran.

## What is included

The installed Skill includes expert charters, optional runtime adapter READMEs,
templates, the local SQLite tracker, gate-runner, unified completion checks,
guarded task closure, budget planner and Codex trial *adapter*. It does **not**
include the source-bundle tools `build_adapters.py`, `validate_bundle.py`, or the
Python regression-test suite. Do not try to run those commands here.

## Project-local tracker

Use one project `docs/sdlc/state.db` and its generated `docs/sdlc/TASKS.md`.
Initialize only for genuinely new projects after checking for existing state:

```bash
python <installed-skill>/scripts/state_store.py --db docs/sdlc/state.db init
python <installed-skill>/scripts/state_store.py --db docs/sdlc/state.db resume
```

If the database is missing but a manifest or history indicates prior work,
**do not silently reinitialize**; inspect backups and restore explicitly.
Never delete or reset `docs/sdlc/` as part of installing or upgrading EngiHelm.

## Local verification

```bash
python <installed-skill>/scripts/assurance_audit.py <root-ledger.json> --root --final
python <installed-skill>/scripts/completion_decision.py --help
python <installed-skill>/scripts/verify_and_close.py --help
```

Use `verify_and_close.py` for the only supported `Verified -> Done` transition;
local evidence and local signatures are not external trusted CI proof.
A small task may use a documented same-context review. Standard/high-risk
work requires a distinct reviewer for verified closure. Review risk before use.

## Real agent trials

`scripts/codex_trial_adapter.py` is bundled, but the external authenticated
Codex CLI, model access, safe sandbox and independent scoring are **not** bundled.
Offline tests are not proof of real-agent behavioral improvements.

## Source development and safe upgrades

To edit canonical charters, rebuild native profiles, or run `validate_bundle.py`,
use the **complete extracted `skill.zip` source**, not this installed directory.
When the installer detects an old `agile-sdlc-orchestrator` Skill, it requires
explicit migration acknowledgement. The installer does not remove old profiles
or project data. See the source `README.md` for the migration plan.

This installation has no Jira or GitHub Issues tracker integration.
