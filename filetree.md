# File Tree: chatgpt-codex-notepad-plugin

**Updated:** 2026-10-31
**Root Path:** `c:\Users\trent\OneDrive\Desktop\Trey-Workspace\chatgpt-codex-notepad-plugin`

Birds-eye map. Each line says what a path is and where it leads; it does not restate the contents.
Enter at [AGENTS.md](AGENTS.md) §12 → [CONTEXT.md](CONTEXT.md) → the surface your task names.

```
├── docs
│   ├── proposals
│   │   ├── PROPOSAL.md          input 1 (CBCW) — historical; adopted/rejected parts in SPEC §2
│   │   └── PROPOSAL_2.md        input 2 (Research Ledger) — historical; same
│   └── SPEC.md                  the design → §3 platform facts · §5 schemas · §8 tools · §15 phases · §16 acceptance
├── potential                    quarantine: candidate Adab modules, reference only, never imported
│   ├── knowledge_integration.py reject — knowledge-graph ingestion (spacy, networkx)
│   ├── knowledge_library.py     concept only — symbolic handles, echo detection
│   ├── semantic_chunking_engine.py reject for V1 — heavy NLP stack
│   ├── semantic_db.py           mine schema ideas at P3/P5 — dedupe, relations, clusters
│   ├── semantic_search.py       reject — Adab utilities + external memory graph
│   └── temporal_db.py           mine patterns — time ranges, FTS rebuild
├── skills                       role instructions → see skills/README.md
│   ├── README.md                which skill for which audience
│   ├── cognitive-workspace-builder
│   │   └── SKILL.md             building/deploying this repo: reading order, rules, Sites path
│   ├── cognitive-workspace-curator
│   │   └── SKILL.md             Codex: read notes, link to code, curate minor; never adjudicate
│   └── cognitive-workspace-usage
│       └── SKILL.md             ChatGPT in conversation; ships inside the plugin
├── .gitignore                   .surgeon/, node output, local *.db, .env
├── AGENTS.md                    rules + routing; §12 = current developments and next action
├── CONTEXT.md                   current gate, architecture keys, hazards, deferred, open questions
├── MEMORY.md                    durable findings by key: doctrine, Sites facts, verdicts, rationale
├── NOTEPAD.md                   live append-only agent workbook (contract + templates)
├── README.md                    entry overview and document links
├── TASK.md                      active board P0–P6, lanes, operator decisions
└── filetree.md                  <this-file>
```

## Not yet created

Planned code layout, from [docs/SPEC.md](docs/SPEC.md) §15 and [skills/cognitive-workspace-builder/SKILL.md](skills/cognitive-workspace-builder/SKILL.md):

```
src/core/   workspace semantics, no platform APIs      src/hosted/  ChatGPT Sites entry + D1
src/store/  Major/MinorStore interfaces + migrations   src/local/   cwp CLI, daemon, stdio MCP
src/mcp/    tool schemas, descriptions, rendering      src/worker/  optional jobs (minor only)
test/       behavior + store-contract + integrity      scripts/     count-lines.mjs
```

## Notes

- `SPEC.md` lives in `docs/` at operator request.
- `.surgeon/` is a local editor cache; present on some machines, git-ignored.
- Update this map in the same commit as any file add, move, rename, or delete.
