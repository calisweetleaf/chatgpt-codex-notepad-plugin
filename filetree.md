# File Tree: chatgpt-codex-notepad-plugin

**Updated:** 2026-10-31
**Root Path:** `c:\Users\trent\OneDrive\Desktop\Trey-Workspace\chatgpt-codex-notepad-plugin`

```
├── docs
│   ├── proposals
│   │   ├── PROPOSAL.md          input proposal 1 (CBCW), historical, non-canonical
│   │   └── PROPOSAL_2.md        input proposal 2 (Research Ledger), historical, non-canonical
│   └── SPEC.md                  current specification (start here)
├── potential                    candidate Adab modules, reference only, never imported
│   ├── knowledge_integration.py
│   ├── knowledge_library.py
│   ├── semantic_chunking_engine.py
│   ├── semantic_db.py
│   ├── semantic_search.py
│   └── temporal_db.py
├── skills                       agent skills (see skills/README.md)
│   ├── README.md
│   ├── cognitive-workspace-builder
│   │   └── SKILL.md             for agents building/deploying this repo
│   ├── cognitive-workspace-curator
│   │   └── SKILL.md             for Codex reading and curating notes
│   └── cognitive-workspace-usage
│       └── SKILL.md             for ChatGPT using the plugin in conversation
├── .gitignore                   ignores .surgeon/, node output, local *.db, .env
├── AGENTS.md                    agent working rules and operator direction (§12 = current state)
├── README.md                    project overview and document links
├── TASK.md                      active work board (P0 to P6)
└── filetree.md                  <this-file>
```

## Notes

- `SPEC.md` lives in `docs/` at operator request.
- `.surgeon/` is a local editor cache; it exists on some machines but is git-ignored.
- Planned code layout (not yet created) is in [docs/SPEC.md](docs/SPEC.md) §15 and [skills/cognitive-workspace-builder/SKILL.md](skills/cognitive-workspace-builder/SKILL.md).
