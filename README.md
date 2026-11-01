# Cognitive Workspace Plugin

Development branch: `main`. Clone with `git clone --branch main https://github.com/calisweetleaf/chatgpt-codex-notepad-plugin.git`.

A persistent external notepad for ChatGPT (and Codex), exposed as an MCP server. It lets the assistant write short working notes during a research conversation and later recover the path of that conversation (threads, detours, returns, open questions) in a new or compacted chat.

**Status:** the final Site source patch and canonical private plugin v1.1.0 are published. Plugin manifest, contract, and both skill contents were read back. P3 source passes 16 tests, typecheck, line budget, and hosted build per root. The current ChatGPT registry still exposes only the four earlier tools; live upgraded list/get/export calls and cross-chat recovery remain unverified. A synthetic MCP browser fixture exercised timeline, inspector, threads, graph, and export UI, but production/signed-in native App rendering remains unverified.

Site ID: `appgprj_6ae661d0968081918d8c386d729f1c8c`; URL: `https://somnus-cognitive-workspace.daeronsomnus.chatgpt.site`. Canonical plugin ID `plugin_asdk_app_sites_09950ef599088191a5e6c9569f8c7dae`; v1.1.0 release `pluginrel_6ae6bb003ae081919df592906c550291`. Current Site deployment identifiers are maintained in [`plugin/connection.json`](plugin/connection.json). The Sites route at `site/app/mcp/route.ts` invokes `src/hosted/index.ts`, and `scripts/build-hosted.mjs` builds the Site artifact while checking the root and Site hosting manifests match.

The P3 full-visibility upgrade is implemented and its plugin release published. Root reports 16 passing tests, typecheck, line budget, and hosted build. A synthetic MCP browser fixture exercised the App views. The local `/operator` preview returned 403 without owner identity, so there is no production/signed-in native App rendering claim. Current tool registry visibility and live upgraded calls remain unverified.

## Documents

| Document | What it is |
| --- | --- |
| [`AGENTS.md`](AGENTS.md) | Operating rules and routing for every agent. **§12 routes the rest of the repository.** Start here. |
| [`CONTEXT.md`](CONTEXT.md) | Current gate, architecture keys, hazards, open questions. One read to orient. |
| [`docs/SPEC.md`](docs/SPEC.md) | The design: architecture, schemas, six tools, deployment, sync, phases, acceptance scenarios. |
| [`TASK.md`](TASK.md) | Active board (P0 to P6), lane assignment, operator decisions. |
| [`NOTEPAD.md`](NOTEPAD.md) | Live append-only agent workbook: working state while the work happens. |
| [`MEMORY.md`](MEMORY.md) | Durable findings by key: operator doctrine, documented Sites facts, `potential/` verdicts, rejected designs, rationale. |
| [`WORKSPACE_CONTRACT.md`](WORKSPACE_CONTRACT.md) | P3 material categories, fidelity boundaries, and open/recall/inspect/note/revisit/export contract. |
| [`docs/CUSTOM_INSTRUCTIONS.md`](docs/CUSTOM_INSTRUCTIONS.md) | Compact text the operator can apply in ChatGPT settings; repository files are not auto-loaded. |
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
- **Six tools:** `workspace_open`, `workspace_note`, `workspace_recall`, `workspace_link`, `workspace_curate`, `workspace_status`. A normal write needs only `text`.
- **Not** a fact checker, a transcript recorder, or a replacement for other memory systems.

This repository is a private development workspace. The deployed service does not depend on Git or on this repository.
