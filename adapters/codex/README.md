# Codex optional adapter

**Main session:** Invoke/load `engihelm` Skill. Codex custom agent definitions are specialist **subagents**, not a substitute for the Skill's main Orchestrator persona.

**Workspace paths:**

- Skill: `.agents/skills/engihelm/SKILL.md`
- Fourteen specialists: `.codex/agents/<role>.toml`

Each TOML profile uses required `name`, `description`, and `developer_instructions`; no model, provider, permission or tool capabilities are hard-coded. The parent assigns a bounded task through whatever delegation facility the active Codex client actually exposes. Do not assume installed profiles are running until invoked and verified.

Preview: `python scripts/install.py --runtime codex --project /repo`
Apply: `python scripts/install.py --runtime codex --project /repo --apply`

Sources (verify again if formats evolve):
- https://learn.chatgpt.com/docs/build-skills
- https://learn.chatgpt.com/docs/agent-configuration/subagents

Keep project `AGENTS.md` and existing configs intact. Do not override human approvals, security policy or repository conventions.
