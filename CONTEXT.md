# CONTEXT.md: Current state index

**Updated:** 2026-11-01
**Purpose:** compact routing keys so a fresh agent can orient in one read. Deep material lives in [MEMORY.md](MEMORY.md); live working state in [NOTEPAD.md](NOTEPAD.md); next actions in [TASK.md](TASK.md); design in [docs/SPEC.md](docs/SPEC.md).

Keep entries short and keyed. If an entry needs a paragraph, it belongs in `MEMORY.md` and this file should hold the key plus one line.

---

## Current gate

- **Gate:** P3 full-visibility workflow upgrade ([TASK.md](TASK.md) → P3); root owns implementation, backend/MCP schemas, App UI, and deployment.
- **Expected verdict:** a note written in one ChatGPT chat is recoverable from a different chat, and Codex sees the same workspace.
- **Last observed verdict:** the Site is live at [somnus-cognitive-workspace.daeronsomnus.chatgpt.site](https://somnus-cognitive-workspace.daeronsomnus.chatgpt.site). Canonical plugin `plugin_asdk_app_sites_09950ef599088191a5e6c9569f8c7dae` release v1.1.0 (`pluginrel_6ae6bb003ae081919df592906c550291`) is published; manifest, contract, and both skill contents were read back. The current ChatGPT registry still exposes only the four earlier tools, so the upgraded list/get/export calls have not been observed live. Earlier service-credential probes returned HTTP 401 at dispatch and do not diagnose the MCP handler. Live note/export calls and cross-chat recovery remain untested.
- **Validation report:** root reports 16 tests passing, including >1 MB exports, Unicode/fence handling, original-hash preservation, D1 concurrent guard retry, all eight tools/resource, auth, and download. Typecheck, budget, and hosted build pass. A synthetic MCP browser fixture exercised timeline, inspector, threads, graph, and export UI. The local `/operator` preview returned 403 without owner identity; no production visual pass or signed-in native App rendering is claimed.
- **Deployment:** plugin v1.1.0 and the final Site source patch are published. The manifest, contract, and usage/curator skill contents were read back. Refreshed Site and plugin identifiers are kept in [`plugin/connection.json`](plugin/connection.json). Current registry visibility and live upgraded operations remain to be retested; no cross-chat persistence result is recorded.
- **Next action:** verify that a fresh chat advertises the updated tools, then exercise note/list/get/export and cross-chat recall. Preserve the Site source mirror workflow in `plugin/README.md`.
- **P3 workflow:** local source exposes eight tools and the inspector resource. Activity is explicit read/write tool invocations and filing receipts, not passive conversation capture. List `remaining` excludes the returned page; cursor ceiling excludes later appends but does not freeze existing mutable fields; exports are immutable snapshots. Root observed 47 notes/26 threads after deployment, unchanged from the predeployment count, with last write `2026-11-01T03:50:34.459Z`. Root reports no notes were written during deployment; no per-note hash verification is claimed.

## Authoritative surfaces

| Key | Current truth | Route |
| --- | --- | --- |
| `design` | SPEC v0.1 is the design to implement. The two proposals are historical inputs only. | [docs/SPEC.md](docs/SPEC.md) |
| `rules` | `AGENTS.md` routes; §12 holds current developments and the next action. | [AGENTS.md](AGENTS.md) |
| `board` | P0 to P6 with lane assignment. | [TASK.md](TASK.md) |
| `map` | Birds-eye tree with routing hints. | [filetree.md](filetree.md) |
| `skills` | usage (ChatGPT, ships with plugin), curator (Codex), builder (implementers). | [skills/](skills/README.md) |
| `workflow-contract` | Source/excerpt/note/derived distinctions, fidelity boundaries, and inspection workflow. | [WORKSPACE_CONTRACT.md](WORKSPACE_CONTRACT.md) |
| `chatgpt-instructions` | Compact text the operator applies in settings; repository files are not auto-loaded. | [docs/CUSTOM_INSTRUCTIONS.md](docs/CUSTOM_INSTRUCTIONS.md) |
| `quarantine` | `potential/` is reference only. Verdicts per module in SPEC §9.1. | [MEMORY.md](MEMORY.md) → `potential-verdicts` |

## Architecture keys

| Key | Current truth |
| --- | --- |
| `major-invariant` | `major` note text is never rewritten by curation, rebuild, or sync. Only operator redaction, which tombstones. |
| `store-split` | Two logical stores, hard boundary, no cross-store FK or query. Two physical DBs where the platform allows; prefixed tables where it does not. |
| `tool-surface` | Local source exposes eight tools: baseline open/note/recall/status plus `workspace_list`, `workspace_get`, `workspace_export`, `workspace_app`. The published plugin can lag; use only its advertised tools. `workspace_link`/`workspace_curate` remain separate planned curation capabilities. |
| `material-types` | Preserve operator excerpts, assistant-authored notes, and derived summaries as distinct forms. Labels aid reading; they do not prove truth or confidence. See [WORKSPACE_CONTRACT.md](WORKSPACE_CONTRACT.md). |
| `binding` | Server-minted sessions. No ChatGPT conversation id is assumed. Best-guess filing + visible receipt + one-call refile; strict mode is config. |
| `no-verification` | Operator doctrine: this is not a fact checker. No epistemic status, no evidence requirement, no scoring of note content. See `MEMORY.md` → `doctrine-no-verification`. |
| `runtime` | One TypeScript core, two hosts. `src/core` holds no platform APIs. |
| `d1-transaction` | Snapshot reads validate `transaction_revision` inside an atomic guard/write/revision-bump batch; only the named guard conflict retries. Network/unknown errors propagate. Callbacks cannot depend on queued-write reads or external effects. A `first-primary` session supports post-commit reads. This is source-backed and locally tested, not cloud-observed. |
| `deps` | No Adab, USMS, knowledge graph, or vector DB for write and recall. |

## Hazards

- `hosting-cost` — operator expects free Sites hosting; docs say hosting usage is separate and waived only for Enterprise. Unresolved. Blocks operator decision 1. → `MEMORY.md` → `sites-facts-2026-10-31`.
- `sites-runtime-unknown` — Site publication and plugin provisioning are observed; the service-credential probe returned 401 at dispatch, and no live MCP handling, cloud persistence, or client use is confirmed.
- `sites-identity` — `TRUST_PRIVATE_SITE=true` and timezone `America/Chicago` were set through the native Sites tool. Private-site trust allows schema discovery without visitor identity; tool calls require forwarded user ID. Owner ID is optional. Live forwarding check is pending.
- `d1-cloud-parity` — Workerd D1 and HTTP tests pass locally; no cloud atomicity/persistence or cross-chat recovery result is recorded yet.
- `sites-cost` — actual account cost is still unknown; do not infer from docs or successful publication.
- `doc-drift` — `NOTEPAD.md` references `CONTEXT.md` and `MEMORY.md`; all three must stay in step with `TASK.md` or the routing layer lies.

## Deferred queue

- `potential-mining` — time-range helpers (`temporal_db.py`), dedupe + relationship + cluster schema (`semantic_db.py`), echo detection (`knowledge_library.py`). Re-enter at P3/P5. Re-implement in TypeScript; never import.
- `spec-p0-row` — SPEC §15 originally described P0 as a `ping` + `echo_write` spike; superseded by the dense P0 in `TASK.md`. SPEC updated 2026-10-31.

## Open questions

- `[OPEN] misfile-rate` — is best-guess session filing good enough, or is strict binding needed? Measure during P0/P1 dogfood (SPEC §2.3).
- `[OPEN] granularity` — are free-text notes + edges + handles enough for dense architecture work? Revisit after ~1,000 real notes.
- `[RESOLVED] recall-view-scope` — `thread` defaults to the active thread, `handle` requires `about`, and `project`/`now` intentionally share a broad note scope; `now` adds route and open-strand orientation. See SPEC §8.3.
- `[BLOCKED] hosted-curation` — can consolidation run on the hosted side? Waiting on the scheduled-execution finding in P0.

## Re-entry route

`AGENTS.md` §12 → `CONTEXT.md` (this file) → `TASK.md` P3 → `NOTEPAD.md` newest entries → [WORKSPACE_CONTRACT.md](WORKSPACE_CONTRACT.md) → `docs/CUSTOM_INSTRUCTIONS.md` if installing the ChatGPT workflow → current MCP tool schemas.
