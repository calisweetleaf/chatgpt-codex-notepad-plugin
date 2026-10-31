# CONTEXT.md: Current state index

**Updated:** 2026-10-31
**Purpose:** compact routing keys so a fresh agent can orient in one read. Deep material lives in [MEMORY.md](MEMORY.md); live working state in [NOTEPAD.md](NOTEPAD.md); next actions in [TASK.md](TASK.md); design in [docs/SPEC.md](docs/SPEC.md).

Keep entries short and keyed. If an entry needs a paragraph, it belongs in `MEMORY.md` and this file should hold the key plus one line.

---

## Current gate

- **Gate:** P0, the hosted vertical slice on ChatGPT Sites ([TASK.md](TASK.md) → P0).
- **Expected verdict:** a note written in one ChatGPT chat is recoverable from a different chat, and Codex sees the same workspace.
- **Last observed verdict:** implementation in progress. Numbered migrations, SQLite/D1 stores, workspace core, MCP server, local stdio harness, hosted `/mcp` entry source, and source-only build packaging are present. Root reports 13 local tests, typecheck, line budget, packed install, and subprocess persistence checks passed. No cloud deployment or ChatGPT/Codex client integration has occurred.
- **Validation report:** root reran all 13 tests locally, including Workerd D1 and HTTP owner-gate/list/status coverage; typecheck and line budget pass (457 application lines, 234 test lines). Root also reports clean `npm pack` install with `--omit=dev` outside the repo and two compiled stdio processes persisting/retrieving through numbered migrations. These results do not establish cloud D1 or Sites behavior.
- **Deployment hold:** no Site creation, deployment, D1 provisioning, publication, or plugin installation this turn. Resume only after application code, host adapter, MCP layer, migrations, and plugin package are locally ready. This is a sequencing hold, not a separate approval gate.
- **Next action:** complete any remaining local contract and packaging readiness work; D1 tests and packed installation have passed locally. Preserve the deployment hold this turn. In later work, once local readiness is complete, resume P0 and record cloud behavior from direct observations.

## Authoritative surfaces

| Key | Current truth | Route |
| --- | --- | --- |
| `design` | SPEC v0.1 is the design to implement. The two proposals are historical inputs only. | [docs/SPEC.md](docs/SPEC.md) |
| `rules` | `AGENTS.md` routes; §12 holds current developments and the next action. | [AGENTS.md](AGENTS.md) |
| `board` | P0 to P6 with lane assignment. | [TASK.md](TASK.md) |
| `map` | Birds-eye tree with routing hints. | [filetree.md](filetree.md) |
| `skills` | usage (ChatGPT, ships with plugin), curator (Codex), builder (implementers). | [skills/](skills/README.md) |
| `quarantine` | `potential/` is reference only. Verdicts per module in SPEC §9.1. | [MEMORY.md](MEMORY.md) → `potential-verdicts` |

## Architecture keys

| Key | Current truth |
| --- | --- |
| `major-invariant` | `major` note text is never rewritten by curation, rebuild, or sync. Only operator redaction, which tombstones. |
| `store-split` | Two logical stores, hard boundary, no cross-store FK or query. Two physical DBs where the platform allows; prefixed tables where it does not. |
| `tool-surface` | Six planned tools; current server exposes `workspace_open`, `workspace_note`, `workspace_recall`, and `workspace_status`. `workspace_link`/`workspace_curate` are planned P3. `text` is the only required write field; writes return a filing receipt. |
| `binding` | Server-minted sessions. No ChatGPT conversation id is assumed. Best-guess filing + visible receipt + one-call refile; strict mode is config. |
| `no-verification` | Operator doctrine: this is not a fact checker. No epistemic status, no evidence requirement, no scoring of note content. See `MEMORY.md` → `doctrine-no-verification`. |
| `runtime` | One TypeScript core, two hosts. `src/core` holds no platform APIs. |
| `d1-transaction` | Snapshot reads validate `transaction_revision` inside an atomic guard/write/revision-bump batch; only the named guard conflict retries. Network/unknown errors propagate. Callbacks cannot depend on queued-write reads or external effects. A `first-primary` session supports post-commit reads. This is source-backed and locally tested, not cloud-observed. |
| `deps` | No Adab, USMS, knowledge graph, or vector DB for write and recall. |

## Hazards

- `hosting-cost` — operator expects free Sites hosting; docs say hosting usage is separate and waived only for Enterprise. Unresolved. Blocks operator decision 1. → `MEMORY.md` → `sites-facts-2026-10-31`.
- `sites-runtime-unknown` — Site server runtime, MCP transport, DB binding count, and handler identity are all unobserved. Everything in `src/hosted` is provisional until P0 records them.
- `d1-cloud-parity` — Workerd D1 and HTTP tests pass locally; Cloudflare/Sites D1 atomicity and identity forwarding remain unobserved until a later deployment.
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

`AGENTS.md` §12 → `CONTEXT.md` (this file) → `TASK.md` current gate → `NOTEPAD.md` newest entries → `docs/SPEC.md` section named by the task → `MEMORY.md` key if a decision looks surprising.
