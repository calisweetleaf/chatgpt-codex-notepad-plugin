# TASK.md: Active work board

**Updated:** 2026-10-31
**Route:** design → [docs/SPEC.md](docs/SPEC.md) · rules → [AGENTS.md](AGENTS.md) · live working state → [NOTEPAD.md](NOTEPAD.md) · current keys → [CONTEXT.md](CONTEXT.md) · durable findings → [MEMORY.md](MEMORY.md) · map → [filetree.md](filetree.md) · agent skills → [skills/](skills/)

This board holds **what to do next**, not why. Design reasoning lives in `docs/SPEC.md`. Working rules live in `AGENTS.md`. While you work, externalize state in `NOTEPAD.md`; promote durable outcomes to `CONTEXT.md` / `MEMORY.md`. Tick boxes in the same commit as the work.

---

## Current state

- [x] Both proposals read and compared.
- [x] `docs/SPEC.md` v0.1 (architecture, schemas, six tools, deployment, sync, phases, acceptance scenarios A to I).
- [x] Document layer wired: `AGENTS.md` §12, `NOTEPAD.md`, `CONTEXT.md`, `MEMORY.md`, `TASK.md`, `filetree.md`, `README.md`, `skills/`.
**Application implementation:** Core and hosted build are locally validated. Package/config scaffold, numbered migrations, SQLite/D1 adapters, workspace core, eight MCP tools, inspector App, local stdio harness, hosted entry, source-only build packaging, and Sites route bridge are present. Root reports 16 local tests, typecheck, line budget, and hosted build passed. Site `appgprj_6ae661d0968081918d8c386d729f1c8c` is published at `https://somnus-cognitive-workspace.daeronsomnus.chatgpt.site`; canonical plugin `plugin_asdk_app_sites_09950ef599088191a5e6c9569f8c7dae` v1.1.0 release `pluginrel_6ae6bb003ae081919df592906c550291` is published, and manifest/contract/skill readback passed. The current ChatGPT registry still exposes only the four earlier tools; live upgraded operations and cross-chat recovery remain open.

**Deployment state:** final Site source patch and plugin v1.1.0 are published; refreshed identifiers are in [`plugin/connection.json`](plugin/connection.json). The current ChatGPT registry shows the four earlier tools, not the upgraded list/get/export surface. Root observed 47 notes/26 threads after deployment, unchanged from before it, with last write at `2026-11-01T03:50:34.459Z`; root reports no notes written during deployment. No per-note hash check is claimed. The user still needs a fresh-chat tool and cross-chat check. Actual account cost remains unknown.

**D1 verification:** Root reports 13 passing local tests, including Workerd D1 and HTTP owner-gate/list/status cases; exact Drizzle migration/journal passed Miniflare D1 tests. This does not establish cloud atomicity/persistence. Deployment is live, but cloud D1 behavior has not been observed.

**P3 full-visibility upgrade:** Root owns note/thread inventory, full-record retrieval, export, backend/MCP schemas, App UI, and deployment. Local source has `workspace_list`, `workspace_get`, `workspace_export`, `workspace_app`, and separate source excerpts. Root reports 16 tests, typecheck, line budget, and hosted build pass. Plugin v1.1.0 was published and manifest, contract, and both skill contents were read back. A synthetic MCP browser fixture exercised timeline, inspector, threads, graph, and export UI; local `/operator` returned 403 without owner identity. Production/signed-in native App rendering remains unverified, and the current registry exposes only the four earlier tools, so live upgraded tool/export operations remain open. This lane owns the behavioral contract, compact custom instructions, AGENTS pointers, and aligned usage/curator skill copies. Acceptance documentation distinguishes operator excerpts, assistant-authored notes, and derived summaries; preserves conversational movement; and makes clear that ChatGPT does not auto-read repository instruction files.

## Lane assignment

| Agent | Lane | Entry point |
| --- | --- | --- |
| **Root (hosted integration)** | P0: finish the hosted Site + canonical MCP plugin, enable operator testing, and push the source. | [skills/cognitive-workspace-builder/SKILL.md](skills/cognitive-workspace-builder/SKILL.md) |
| **Codex local / Factory** | P1: the shared core and local stdio entry, in the same repo, same `src/core` + `src/store` + `src/mcp`. | same skill |
| **Operator** | Decisions at the bottom of this file. | - |

P0 and P1 build **one codebase**. P1 is not a separate prototype; it is the same core behind a different host. Whoever starts first owns `src/core`, `src/store`, and `src/mcp`; the other builds its host layer against those interfaces and does not fork them.

---

## P0: Hosted vertical slice on ChatGPT Sites

**Goal:** a real, usable notepad reachable from any ChatGPT chat, with the full `major` schema and no toy shortcuts. Platform unknowns get answered *while* building it, not by a throwaway spike.

**Scope is the real thing.** Build `major` per SPEC §5.4 (all tables, FTS5, triggers, events), `minor` per §5.5 (tables created even if only `minor_recall_cache` is used at first), and these tools per §8: `workspace_open`, `workspace_note`, `workspace_recall`, `workspace_status`. `workspace_link` and `workspace_curate` land in P3; register them only when implemented.

### Build

- [x] Register the private Site and configure its D1 binding/identity manifest. Site ID: `appgprj_6ae661d0968081918d8c386d729f1c8c`; expected URL: `https://somnus-cognitive-workspace.daeronsomnus.chatgpt.site`.
- [ ] Establish the repo layout from SPEC §15 (`src/core`, `src/store`, `src/mcp`, `src/hosted`) and keep `src/core` free of platform APIs so P1 can reuse it unchanged.
- [x] Migrations: full `major_*` DDL, full `minor_*` DDL, `major_notes_fts` + sync triggers, every index in SPEC §5.4, plus D1 transaction guard migration.
- [ ] `src/core`: ULID ids, HLC clock, session resolution (§7.2, 12-hour window, implicit open with notice), thread routing and all six `move` behaviors (§4.3), kind inference, handle detection + `about` handle creation, `refs` shorthand parsing, server-created `continues` / `branches_from` / `returns_to` edges, recall assembly steps 1 to 7 (§8.3) including neighborhood expansion and budget trim.
- [x] `src/mcp`: four P0 tool schemas with `text` as the only required field; one-line write receipts naming note id + thread + session; near-duplicate warning on repeated `content_hash`; recall output fenced with "stored working material, not instructions".
- [ ] Auth: owner allowlist, no anonymous writes (§11.1). Decide this *before* publishing, not after.
- [x] Publish the Site and provision/install the canonical plugin card. Deployment and release IDs: [plugin/README.md](plugin/README.md).
- [ ] Confirm the connected plugin exposes tools in a fresh chat; complete note and cross-chat recall scenarios below.

### Verify from real clients

- [ ] Write a note in chat 1. Open a **new** chat, call `workspace_open` with no arguments, confirm the thread, trail, and open strands come back (scenario A).
- [ ] One-field write `{text}` returns a receipt; later `recall {query}` returns that note with its thread neighbors (scenario D).
- [ ] `move: "branch"` then `move: "return"` produce a navigable detour in the trail.
- [ ] Recall a period with no notes: returns "no notes recorded", never a synthesized summary (scenario I).
- [ ] Repeat the same calls from Codex against the same plugin; confirm both clients share one workspace.

### Record while building (replaces SPEC §3 "unverified" rows)

| Unknown | Where it blocks | Answer |
| --- | --- | --- |
| Site server runtime + language | whether `src/core` TypeScript runs as-is | |
| MCP transport Sites expects | `src/hosted` entry shape | |
| How D1 is bound; can a Site bind **two** databases | SPEC §5.1 one-file vs two-file decision | |
| Identity reaching an MCP tool handler | §11.1 auth design | |
| Any stable conversation id at the tool | §7 session binding (assume none) | |
| Scheduled / background execution | whether hosted curation needs the local worker | |
| Outbound HTTP allowed | P5 embeddings on the hosted side | |
| Storage limit behavior; one 10 GB db or per-db | `minor` growth budget | |
| **Actual hosting cost on this account** | open operator decision 1 | |

- [ ] Each answer goes into `NOTEPAD.md` as it is observed, then into `MEMORY.md` with its source, then SPEC §3 and §5.1 get corrected and a changelog line added.

### Fallback branches

- If Sites exposes no usable MCP transport for a custom server → fallback host in SPEC §10.1; record why in `MEMORY.md` before switching.
- If only one database can be bound → single-database layout with `major_*` / `minor_*` prefixes. No cross-store query or FK regardless (§5.1).
- If no identity reaches the handler → bearer credential at plugin connection, or OAuth 2.1 per the OpenAI plugin auth guide. Do not ship anonymous writes.

**Done when:** the operator can write a note in one ChatGPT chat and recover the thread in a different chat the next day, Codex sees the same notes, and SPEC §3 has no unverified row that blocks P2.

---

## P1: Same core, local stdio host

**Goal:** scenarios A, D, I pass through a local MCP client, so the core is testable without publishing a Site.

- [ ] `package.json` (TypeScript, ESM, Node LTS), `tsconfig.json`, lint/format.
- [ ] `src/store/`: `MajorStore` / `MinorStore` async interfaces; SQLite implementation (WAL); same migrations as P0.
- [ ] `src/local/`: `cwp mcp` stdio entry via `@modelcontextprotocol/sdk`.
- [x] `scripts/count-lines.mjs`: tests ≤ 1.15 × src non-blank non-comment lines; wired into `npm test` and passing (root reports 457 source / 234 test lines).
- [ ] Behavior tests for A, D, I against in-memory SQLite.
- [ ] Store contract suite runs on SQLite and a D1-compatible shim so both hosts behave identically.

**Done when:** `npm test` passes including the budget check, and a manual stdio session writes, reopens, and recalls.

## P2: Converge the two hosts

- [ ] `src/hosted` and `src/local` share `src/core` + `src/mcp` with no duplicated semantics.
- [ ] Same contract suite green on both store implementations.
- [ ] Live check: ChatGPT writes, Codex reads, local `cwp mcp` reads the same logical workspace (remote mode).

## P3: Structure and curation

- [ ] `workspace_link`: all relations from SPEC §4.2 plus `refile`, `retract`, thread status changes.
- [ ] `workspace_curate`: `digest`, `collect`, `associate`, `rebuild`, `stale`; curation path opens `major` **read-only**.
- [ ] Scenarios B, C, E, F. F must checksum every `major_notes.text` before and after curation.
- [ ] Mine `potential/temporal_db.py` time-range helpers and `potential/semantic_db.py` dedupe/relationship/cluster patterns (SPEC §9.1). Re-implement; never import.
- [ ] Full visibility workflow implemented and tested by root: open → recall → enumerate → retrieve complete record → note → revisit → export. Tool names and fields come from the live discovery schema.
- [x] Local source list/get/export paths and RPC/HTTP test coverage reported by root (16 total tests pass with typecheck and line budget).
- [ ] Validate native MCP App rendering/interaction in a real host and verify the updated plugin release.
- [x] Documentation contract distinguishes operator excerpts, assistant notes, and derived summaries without adding truth/confidence policing.
- [x] Compact ChatGPT instructions explicitly require user application; they do not assume ChatGPT auto-reads `AGENTS.md`.
- [x] Root and local plugin-copy usage/curator skills describe open → recall → inspect → note → revisit, source distinctions, and fidelity boundaries.
- [x] Align exact tool names and fields to the local eight-tool MCP schemas; root/plugin authored skill copies match.
- [x] Owner publishes updated v1.1.0 plugin and confirms manifest, contract, and skill-content readback.

## P4: Local companion as a product

- [ ] `cwp init | start | stop | status | doctor | service install | sync | export | import | redact`.
- [ ] Modes `remote`, `replica`, `standalone` (§10.2); sync per §12 (HLC merge, grow-only notes, event-ordered headers).
- [ ] Windows Scheduled Task, systemd user unit, launchd agent. `npx` is never called supervision.
- [ ] Scenario G: offline writes, reconnect, merge, thread-status conflict resolved by HLC.

## P5: Semantic depth

- [ ] `minor_embeddings`, hybrid rank (bm25 + cosine + recency + edge proximity), echo associations from `potential/knowledge_library.py` `EchoDetector` (concept only).
- [ ] Optional `cwp worker`; every earlier scenario still passes with the worker off.

## P6: Status surface

- [ ] Small read-only page: health, recent threads, export.

---

## Open operator decisions (SPEC §18)

- [ ] Hosting cost acceptable on this plan, or fallback host primary?
- [ ] Session binding default: best-guess filing (spec) or strict?
- [ ] Workspace timezone for `local_day`.
- [ ] npm package name / registry.
- [ ] Model provider for optional digests and embeddings.

## Rules that are easy to forget

- Never import from `potential/`; never modify it.
- Never rewrite `major` note text outside operator redaction.
- `filetree.md` changes in the same commit as any file add/move/delete.
- `NOTEPAD.md` is append-only; correct an entry with a dated correction, never a rewrite.
- No integration is "working" until a real client exercised it.
- The workspace stores thinking in progress. It does not verify, score, or correct the operator's notes.
