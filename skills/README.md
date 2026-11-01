# skills/

Agent skills for this project. Each folder holds one `SKILL.md` with YAML front matter (`name`, `description`) followed by instructions. They are plain Markdown so ChatGPT plugins, Codex, Factory, and other agents can load them.

| Skill | Audience | Use when |
|---|---|---|
| [`cognitive-workspace-usage/`](cognitive-workspace-usage/SKILL.md) | ChatGPT (and any model using the plugin in conversation) | Talking with the operator while the workspace plugin is connected. This is the skill to ship inside the plugin. |
| [`cognitive-workspace-curator/`](cognitive-workspace-curator/SKILL.md) | Codex | Reading notes to understand intent, relating them to code, and organizing them into the derived `minor` store. |
| [`cognitive-workspace-builder/`](cognitive-workspace-builder/SKILL.md) | Implementation agents (ChatGPT Work mode, Codex, Factory) | Building, testing, or deploying this repository. |

The usage and curator skills follow [`WORKSPACE_CONTRACT.md`](../WORKSPACE_CONTRACT.md) and the live tool schemas. During P3, update both authored skills and `plugin/skills/` copies when the connected tool surface changes. Do not guess unadvertised operations. ChatGPT does not auto-read repository files; the operator must apply [`docs/CUSTOM_INSTRUCTIONS.md`](../docs/CUSTOM_INSTRUCTIONS.md) separately when desired.
