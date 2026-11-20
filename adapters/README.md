# Optional runtime adapters

The **core Skill is platform-neutral**. These adapters translate the same 14 expert charters into host-native configuration formats; they do not change the rules of the Skill. Use an adapter only if its host supports the corresponding agent mechanism.

| Host | Skill discovery (project) | Native specialist profiles (project) | Primary Orchestrator |
|---|---|---|---|
| Codex | `.agents/skills/engihelm/` | `.codex/agents/*.toml` | Invoke the Skill in the main Codex session; custom profiles define children |
| Antigravity | `.agents/skills/engihelm/` | `.agents/agents/*.md` | Optional `engihelm.md` main-agent profile |
| OpenCode | `.opencode/skills/engihelm/` | `.opencode/agents/*.md` | Optional `engihelm.md` primary-agent profile |
| Other Agent Skills host | Host-defined Skill path | Host-defined; not assumed | Invoke the main Skill and detect capabilities |

Install safely with `python scripts/install.py --runtime {codex,antigravity,opencode,skill-only} --project /repo`, preview first, then `--apply`. Profiles are static examples; native support, access policies and product UI can change. See runtime-specific READMEs for links to authoritative documentation. Do not transplant one runtime's files into another.

Canonical source of all personas: `references/roles/*.md` and `references/engineering-director.md`. **Source-bundle maintainers only:** In the complete extracted source ZIP, run `python scripts/build_adapters.py` after editing charters and `python scripts/build_adapters.py --check` to validate generated content. The project installer intentionally excludes those developer scripts; do not attempt these commands from a project-installed Skill.
