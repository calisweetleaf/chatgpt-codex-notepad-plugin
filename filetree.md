# File Tree: chatgpt-codex-notepad-plugin

**Updated:** 2026-10-31
**Root Path:** `/workspace/scratch/b5bc4e96f6a6/chatgpt-codex-notepad-plugin`

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
├── package.json                 private TypeScript ESM package; build, typecheck, test, line-budget scripts
├── package-lock.json            locked npm dependency tree
├── tsconfig.json                TypeScript compiler configuration
├── tsconfig.build.json          source-only TypeScript build configuration
├── scripts
│   ├── build.mjs                clean source build and copy migrations to dist
│   ├── build-hosted.mjs          verifies hosting identity and builds/copies the Sites artifact
│   └── count-lines.mjs          enforces the handwritten test/source line budget
├── src
│   ├── core
│   │   └── workspace.ts         note/session/thread and recall engine
│   ├── mcp
│   │   └── server.ts            four tool schemas, validation, dispatch, JSON-RPC routing
│   ├── local
│   │   └── stdio.ts             JSONL stdin/stdout harness over the internal RPC + SQLite
│   ├── hosted
│   │   └── index.ts             owner-ID-gated bounded POST /mcp entry; deployed via Sites
│   └── store
│       ├── database.ts          async database interface
│       ├── d1.ts                snapshot reads + revision-guarded atomic batch
│       ├── sqlite.ts            SQLite adapter
│       └── migrations
│           └── 0001.sql         initial major/minor schema, FTS triggers, indexes, session state
│           └── 0002.sql         D1 transaction guard and revision schema
├── site
│   ├── app/page.tsx              minimal Cognitive Workspace service landing page
│   ├── app/mcp/route.ts          dispatches GET/POST to src/hosted/index.ts
│   ├── app/chatgpt-auth.ts       Sites identity helper
│   ├── db/                       D1 binding/schema scaffold
│   ├── drizzle/0000_workspace.sql schema-only D1 migration copy
│   ├── worker/index.ts           Vinext Worker entry
│   ├── scripts/                  Sites install/build/preview lifecycle helpers
│   ├── .openai/hosting.json       registered Sites identity and D1 binding manifest
│   ├── package.json              Sites app dependencies and local commands
│   ├── pnpm-lock.yaml            locked scaffold dependencies
│   └── README.md                 Site identity, route/build and source-mirror handoff
├── plugin
│   ├── README.md                 published Site/plugin identities and mirror update workflow
│   ├── plugin.json                Plugin Creator manifest, release v1.0.1
│   ├── .app.json                  canonical App connection binding
│   ├── .codex-plugin/plugin.json  Codex plugin manifest
│   ├── connection.json            non-secret Site/plugin IDs, URLs, version, source
│   └── skills/                    usage and curator skills overlaid by Plugin Creator
├── test
│   ├── d1.test.ts               Workerd D1 + HTTP owner-gate/list/status tests
│   └── workspace.test.ts        SQLite behavior + in-process MCP RPC coverage
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

## Remaining implementation and deployment surfaces

The core, stores, four-tool MCP server, local stdio harness, hosted entry, and Sites route/build bridge are present. Root reports 13 local tests and the hosted build pass. Site `appgprj_6ae661d0968081918d8c386d729f1c8c` is published at `https://somnus-cognitive-workspace.daeronsomnus.chatgpt.site`; deployment/version/source and canonical plugin release IDs are in `plugin/README.md`. Live MCP schema/HTTP behavior and cross-chat note recovery remain unverified. The Site migration file is a schema copy; do not infer cloud migration state from it.

## Deployment handoff surfaces

- `src/hosted/` — primary hosted server source.
- `site/` — Sites app and route bridge; `scripts/build-hosted.mjs` builds its deployable artifact. Future source refreshes follow the separate-mirror procedure in `plugin/README.md`.
- `plugin/` — Plugin Creator manifests, canonical skill copies, identity record, and source-mirror handoff. Preserve existing App ID on updates.

```
src/worker/  optional jobs (minor only)
```

## Notes

- `SPEC.md` lives in `docs/` at operator request.
- `.surgeon/` is a local editor cache; present on some machines, git-ignored.
- Update this map in the same commit as any file add, move, rename, or delete.
