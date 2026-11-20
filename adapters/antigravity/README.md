# Antigravity optional adapter

**Workspace paths:**

- Skill: `.agents/skills/engihelm/SKILL.md`
- Expert specialist profiles: `.agents/agents/<role>.md` with `subagent: true`, `mainAgent: false`
- Optional main persona: `.agents/agents/engihelm.md` with `mainAgent: true`, `subagent: false`

Profiles use YAML frontmatter with `name`, `description`, `mainAgent`, `subagent` and a Markdown persona body. They intentionally omit tool and model IDs; those depend on workspace, host version and configured permissions. The main orchestrator is still obligated to load/use the Skill. A profile file alone does not authorize changes, grant tools or guarantee a child session.

Preview: `python scripts/install.py --runtime antigravity --project /repo`
Apply: `python scripts/install.py --runtime antigravity --project /repo --apply`

Sources (verify again if formats evolve):
- https://antigravity.google/docs/skills
- https://antigravity.google/docs/cli-subagents
