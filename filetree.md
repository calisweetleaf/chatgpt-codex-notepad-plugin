# File Tree: chatgpt-codex-notepad-plugin

**Updated:** 2026-11-01
**Root Path:** `/workspace/scratch/b5bc4e96f6a6/chatgpt-codex-notepad-plugin`

Birds-eye map. Each line says what a path is and where it leads; it does not restate the contents.
Enter at [AGENTS.md](AGENTS.md) §12 → [CONTEXT.md](CONTEXT.md) → the surface your task names.

```
├── docs
│   ├── CUSTOM_INSTRUCTIONS.md    self-contained ChatGPT workflow instructions the operator explicitly applies
│   ├── proposals
│   │   ├── PROPOSAL.md          input 1 (CBCW) — historical; adopted/rejected parts in SPEC §2
│   │   └── PROPOSAL_2.md        input 2 (Research Ledger) — historical; same
│   └── SPEC.md                  the design → §3 platform facts · §5 schemas · §8 tools · §15 phases · §16 acceptance
├── WORKSPACE_CONTRACT.md         full conversational continuity, tool-name transition, complete export, and visible App contract
├── drizzle
│   ├── 0000_workspace.sql        initial Sites D1 schema copy
│   ├── 0001_operator_visibility.sql additive excerpt/export tables
│   ├── 0002_full_research.sql   chunk storage and FTS for full-length notes
│   └── meta/_journal.json        Drizzle migration journal
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
│   ├── docsnagv2.py              standalone docs extraction utility; not an app runtime dependency
│   ├── requirements-docsnag.txt  Python dependencies for the standalone docs utility
│   ├── pack-plugin.mjs           stages local plugin package content, including contract and skills
│   ├── sync-site-core.mjs        copies root source into ignored site/workspace-generated for Site builds
│   └── count-lines.mjs          enforces the handwritten test/source line budget
├── src
│   ├── core
│   │   ├── inspection.ts        authenticated list/get and immutable export snapshot logic
│   │   ├── text.ts              chunking, storage limits, and exact-text hydration
│   │   └── workspace.ts         note/session/thread and recall engine
│   ├── app
│   │   ├── receipt.ts           inline write/export receipt App resource
│   │   └── view.ts              native MCP App inspector UI and hosted operator view
│   ├── mcp
│   │   └── server.ts            simple eight-operation names, legacy aliases, MCP App resources
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
│           └── 0003.sql         additive source excerpt and operator export tables
│           └── 0004.sql         chunk storage and full-text search for long notes
├── site
│   ├── app/page.tsx              minimal Cognitive Workspace service landing page
│   ├── app/mcp/route.ts          dispatches GET/POST to src/hosted/index.ts
│   ├── app/[...workspace]/route.ts catch-all for generated shared hosted handler routes
│   ├── app/chatgpt-auth.ts       Sites identity helper
│   ├── lib/connector-contract.mts Sites connector contract helper
│   ├── db/                       D1 binding + starter schema only; numbered root SQL migrations are authoritative
│   ├── drizzle/0000_workspace.sql schema-only D1 migration copy
│   ├── drizzle/0001_operator_visibility.sql additive source/export schema copy
│   ├── drizzle/0002_full_research.sql chunk storage and FTS migration copy
│   ├── drizzle/meta/_journal.json Drizzle migration journal
│   ├── worker/index.ts           Vinext Worker entry
│   ├── scripts/workspace-dev.mjs syncs shared source before local Site development
│   ├── workspace-generated/      ignored build/preview copy generated from root src/
│   ├── .openai/hosting.json       registered Sites identity and D1 binding manifest
│   ├── package.json              Sites app dependencies and local commands
│   ├── pnpm-lock.yaml            locked scaffold dependencies
│   └── README.md                 Site identity, route/build and source-mirror handoff
├── plugin
│   ├── README.md                 published Site/plugin identities and mirror update workflow
│   ├── plugin.json                local package manifest and published release v1.2.0
│   ├── .app.json                  canonical App connection binding
│   ├── .codex-plugin/plugin.json  Codex plugin manifest
│   ├── connection.json            non-secret Site/plugin IDs, URLs, version, source
│   ├── WORKSPACE_CONTRACT.md      updated continuity contract for next package release
│   └── skills/                    updated usage and curator copies; not yet republished
├── test
│   ├── d1.test.ts               Workerd D1 + HTTP owner-gate/list/status tests
│   ├── operator.test.ts         source excerpt, pagination, exact get, export fidelity/ownership tests
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

v1.2.0 is published to the same private Site and canonical plugin. All 20 tests, typecheck, the handwritten line budget and hosted build pass. Canonical tools are open/write/recall/status/list/read/export/app; legacy calls remain compatible. Writes preserve up to4,000,000characters using lossless physical segmentation. Live status/list/export succeeded after deployment, including an880-record Markdown snapshot. Signed-in Android rendering remains unverified; this running chat retains cached old labels.

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

## Full continuity correction — 2026-11-01

Full conversational continuity release: canonical open/write/recall/status/list/read/export/app, backward-compatible calls, lossless long-entry storage, full Markdown export, inline write/export receipts and live inspector. All 20 tests, typecheck, line budget and hosted build pass. Latest published identifiers are in plugin/connection.json. Android/native host rendering remains a separate acceptance boundary. The former four-tool registry limitation is historical; all eight original operations were successfully available before this correction. The previous export snapshot was created live. Current ChatGPT-host rendering still needs direct client acceptance.

### Publication outcome

v1.2.0 is published to the existing private Site and canonical plugin. All 20 tests, typecheck, line budget and hosted build pass. Live status remains52notes/28threads after deployment; newest-first list and v3 full export succeeded (880records). Plugin manifest, complete contract and both skills were read back. This running chat retains cached old tool labels; server discovery advertises the canonical names, and the old calls remain compatible. Native Android rendering and the screenshot request failure are not established by these backend checks. Current deployment, release, source and App entrypoint are in `plugin/connection.json` (relative to repository root).
