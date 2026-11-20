# OpenCode optional adapter

OpenCode is **one optional runtime**, not the target of the Skill itself. The core instruction set is shared with Codex, Antigravity and any other compliant Agent Skills host.

**Workspace paths:** Skill `.opencode/skills/engihelm/`; native Markdown agents `.opencode/agents/*.md`. Use the native profile named `engihelm` if the installed OpenCode version supports it; otherwise invoke the main Skill directly. Profile capabilities must be verified in the active runtime.

Preview: `python scripts/install.py --runtime opencode --project /repo`
Apply: `python scripts/install.py --runtime opencode --project /repo --apply`

The agent definitions are generated from the same canonical role charters. Do not assume the OpenCode adapter must be installed anywhere else.
