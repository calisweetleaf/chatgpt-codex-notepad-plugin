# CONTEXT.md: Current state index

**Updated:** 2026-11-01
**Purpose:** compact routing keys so a fresh agent can orient in one read. Deep material lives in [MEMORY.md](MEMORY.md); live working state in [NOTEPAD.md](NOTEPAD.md); next actions in [TASK.md](TASK.md); design in [docs/SPEC.md](docs/SPEC.md).

Keep entries short and keyed. If an entry needs a paragraph, it belongs in `MEMORY.md` and this file should hold the key plus one line.

---

## Current gate

- **Gate:** P3 full-visibility workflow upgrade ([TASK.md](TASK.md) → P3); root owns implementation, backend/MCP schemas, App UI, and deployment.
- **Expected verdict:** a full conversational trail written in one ChatGPT chat can be resumed from another chat; ChatGPT and Codex share the workspace, and its visible App works in Chat and mobile clients.
- **Last observed verdict:** v1.1.0 exposed all eight operations in this chat; full export successfully captured 857 records including 51 notes/27 threads. Before the v1.2.0 deployment, status reports 52 notes/28 threads. No new production test entries were written during this correction.
- **Validation report:** Full conversational continuity release: canonical open/write/recall/status/list/read/export/app, backward-compatible calls, lossless long-entry storage, full Markdown export, inline write/export receipts and live inspector. All 20 tests, typecheck, line budget and hosted build pass. Latest published identifiers are in plugin/connection.json. Android/native host rendering remains a separate acceptance boundary.
- **Deployment:** Same private Site and canonical plugin; current native IDs and URLs are in plugin/connection.json. Preserve D1 and existing records. The v1.2.0 source is ready for publication; root appends the observed outcome.
- **Next action:** Publish the validated full-continuity correction, refresh the existing plugin, exercise live discovery/list/read/export and verify native Android rendering when that client is available.
- **P3 workflow:** Complete conversational development is the contract. No short-note policy or imposed condensation. No citation, proof, epistemic or provenance requirements. Primary originals survive; derived views remain optional and additive.

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
| `tool-surface` | Source advertises `open/write/recall/status/list/read/export/app` and accepts `workspace_*` compatibility aliases. Published v1.1.0 chat registry still shows four earlier tools. |
| `continuity` | Keep the full conversational flow and turns. Do not require short notes, citations, proof, source locators, or provenance labels. Derived material is optional and never replaces originals. See [WORKSPACE_CONTRACT.md](WORKSPACE_CONTRACT.md). |
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
