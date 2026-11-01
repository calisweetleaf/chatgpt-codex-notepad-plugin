# Cognitive Workspace Plugin

Development branch: `main`. Clone with `git clone --branch main https://github.com/calisweetleaf/chatgpt-codex-notepad-plugin.git`.

A persistent external continuity space for ChatGPT (and Codex), exposed as an MCP server. It preserves the full path of a conversation—relevant turns, threads, detours, returns, corrections, symbols, and unfinished questions—so another or compacted chat can re-enter the ideas instead of reconstructing them from a short summary.

**Status:** the final Site source patch and canonical private plugin v1.1.0 are published. That release's manifest, contract, and skills were read back before the current local continuity-doc revisions. Source now advertises simple tool names (`open`, `write`, `recall`, `status`, `list`, `read`, `export`, `app`) with `workspace_*` compatibility aliases; writes accept up to 4,000,000 characters, using chunked storage and read reconstruction. Root reports 20 tests, typecheck, and line-budget checks passed twice; newer App receipt/live-refresh/mobile-graph and bounded export-download changes await the final test/build pass. The current ChatGPT registry still exposes only the four earlier tools, so the upgraded behavior has not been live-tested. Full conversational continuity and export are the contract; no short-note, citation, verification, or provenance requirement applies. The visible App must work in real ChatGPT Chat and mobile clients; synthetic browser checks are not production rendering evidence.

Site ID: `appgprj_6ae661d0968081918d8c386d729f1c8c`; URL: `https://somnus-cognitive-workspace.daeronsomnus.chatgpt.site`. Canonical plugin ID `plugin_asdk_app_sites_09950ef599088191a5e6c9569f8c7dae`; v1.1.0 release `pluginrel_6ae6bb003ae081919df592906c550291`. Current Site deployment identifiers are maintained in [`plugin/connection.json`](plugin/connection.json). The Sites route at `site/app/mcp/route.ts` invokes `src/hosted/index.ts`, and `scripts/build-hosted.mjs` builds the Site artifact while checking the root and Site hosting manifests match.

## Editable components

| Path | Responsibility |
| --- | --- |
| [`src/app/view.ts`](src/app/view.ts) | Native MCP App and hosted inspector UI: timeline, explorer, exact notes, activity, graph and export. |
| [`src/core/inspection.ts`](src/core/inspection.ts) | Exact reads, pagination and immutable full-database Markdown export. |
| [`src/mcp/server.ts`](src/mcp/server.ts) / [`src/hosted/index.ts`](src/hosted/index.ts) | Tool schemas, App resource, authenticated HTTP/MCP routes and download endpoint. |
| [`site/`](site/) | Sites scaffold, auth integration, routes, migrations, build and preview scripts. |
| [`plugin/`](plugin/) | Installed plugin manifests, skill copies, contract and deployment identifiers. |
| [`scripts/docsnagv2.py`](scripts/docsnagv2.py) | Documentation capture utility; Python dependencies in `scripts/requirements-docsnag.txt`. |

The native App entrypoint is [Research workspace](https://chatgpt.com/plugins/plugin_asdk_app_sites_09950ef599088191a5e6c9569f8c7dae/app/workspace_app); the same inspector is served at authenticated `/operator`. See [WORKSPACE_CONTRACT.md](WORKSPACE_CONTRACT.md) for exact tool contracts. Generated build output, caches, credentials and runtime database files are excluded from Git. Build with `npm run build:hosted`; package the plugin with `node scripts/pack-plugin.mjs /absolute/path/plugin.tar.gz` after installing dependencies. Development stays on `main`; the existing default `master` branch is synchronized for ordinary clones.

## Documents

| Document | What it is |
| --- | --- |
| [`AGENTS.md`](AGENTS.md) | Operating rules and routing for every agent. **§12 routes the rest of the repository.** Start here. |
| [`CONTEXT.md`](CONTEXT.md) | Current gate, architecture keys, hazards, open questions. One read to orient. |
| [`docs/SPEC.md`](docs/SPEC.md) | Historical baseline design and architecture; current tool and continuity contract is in [`WORKSPACE_CONTRACT.md`](WORKSPACE_CONTRACT.md). |
| [`TASK.md`](TASK.md) | Active board (P0 to P6), lane assignment, operator decisions. |
| [`NOTEPAD.md`](NOTEPAD.md) | Live append-only agent workbook: working state while the work happens. |
| [`MEMORY.md`](MEMORY.md) | Durable findings by key: operator doctrine, documented Sites facts, `potential/` verdicts, rejected designs, rationale. |
| [`WORKSPACE_CONTRACT.md`](WORKSPACE_CONTRACT.md) | Full conversational continuity, fidelity, simple tool names, complete export, and visible App contract. |
| [`docs/CUSTOM_INSTRUCTIONS.md`](docs/CUSTOM_INSTRUCTIONS.md) | Self-contained instructions the operator can apply in ChatGPT settings; repository files and skills are not auto-loaded. |
| [`skills/`](skills/README.md) | Role skills: plugin usage (ChatGPT), curation (Codex), building and deploying (implementers). |
| [`filetree.md`](filetree.md) | Birds-eye map with routing hints. |
| [`src/`](src/) and [`test/`](test/) | TypeScript workspace/store/MCP implementation and local SQLite/Workerd coverage, including the hosted handler. |
| [`package.json`](package.json) and [`scripts/count-lines.mjs`](scripts/count-lines.mjs) | Build/typecheck/test commands and the handwritten test-size budget. |
| [`site/README.md`](site/README.md) | ChatGPT Sites/Vinext scaffold and local development lifecycle. |
| [`docs/proposals/`](docs/proposals) | The two independent input proposals. Historical; reconciled in SPEC §2. |
| [`potential/`](potential/) | Candidate Adab-Nebulae modules kept for reference. Never imported; verdicts in SPEC §9.1. |

## Design at a glance

- **Hosted first** on ChatGPT Sites (MCP server + D1), with an opt-in npm local companion (`cwp`).
- **Two stores:** `major` holds the append-only conversational trajectory; `minor` holds rebuildable summaries, collections, and indexes.
- **Eight implemented tools:** `workspace_open`, `workspace_note`, `workspace_recall`, `workspace_status`, `workspace_list`, `workspace_get`, `workspace_export`, `workspace_app`. A normal write needs only `text`; link/curate tools remain planned.
- **Not** a fact checker, a transcript recorder, or a replacement for other memory systems.

This repository is a private development workspace. The deployed service does not depend on Git or on this repository.

## Full continuity correction — 2026-11-01

Full conversational continuity release: canonical open/write/recall/status/list/read/export/app, backward-compatible calls, lossless long-entry storage, full Markdown export, inline write/export receipts and live inspector. All 20 tests, typecheck, line budget and hosted build pass. Latest published identifiers are in plugin/connection.json. Android/native host rendering remains a separate acceptance boundary. The former four-tool registry limitation is historical; all eight original operations were successfully available before this correction. The previous export snapshot was created live. Current ChatGPT-host rendering still needs direct client acceptance.
