# CONTEXT.md: Current state index

**Updated:** 2026-10-31
**Purpose:** compact routing keys so a fresh agent can orient in one read. Deep material lives in [MEMORY.md](MEMORY.md); live working state in [NOTEPAD.md](NOTEPAD.md); next actions in [TASK.md](TASK.md); design in [docs/SPEC.md](docs/SPEC.md).

Keep entries short and keyed. If an entry needs a paragraph, it belongs in `MEMORY.md` and this file should hold the key plus one line.

---

## Current gate

- **Gate:** P0, the hosted vertical slice on ChatGPT Sites ([TASK.md](TASK.md) → P0).
- **Expected verdict:** a note written in one ChatGPT chat is recoverable from a different chat, and Codex sees the same workspace.
- **Last observed verdict:** not started. No application code exists.
- **First action:** create a private Site with an MCP server + D1, then `src/core` + `src/store` + `src/mcp` per SPEC §5 and §8.

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
| `tool-surface` | Six tools. `text` is the only required field anywhere. Every write returns a filing receipt. |
| `binding` | Server-minted sessions. No ChatGPT conversation id is assumed. Best-guess filing + visible receipt + one-call refile; strict mode is config. |
| `no-verification` | Operator doctrine: this is not a fact checker. No epistemic status, no evidence requirement, no scoring of note content. See `MEMORY.md` → `doctrine-no-verification`. |
| `runtime` | One TypeScript core, two hosts. `src/core` holds no platform APIs. |
| `deps` | No Adab, USMS, knowledge graph, or vector DB for write and recall. |

## Hazards

- `hosting-cost` — operator expects free Sites hosting; docs say hosting usage is separate and waived only for Enterprise. Unresolved. Blocks operator decision 1. → `MEMORY.md` → `sites-facts-2026-10-31`.
- `sites-runtime-unknown` — Site server runtime, MCP transport, DB binding count, and handler identity are all unobserved. Everything in `src/hosted` is provisional until P0 records them.
- `doc-drift` — `NOTEPAD.md` references `CONTEXT.md` and `MEMORY.md`; all three must stay in step with `TASK.md` or the routing layer lies.

## Deferred queue

- `potential-mining` — time-range helpers (`temporal_db.py`), dedupe + relationship + cluster schema (`semantic_db.py`), echo detection (`knowledge_library.py`). Re-enter at P3/P5. Re-implement in TypeScript; never import.
- `spec-p0-row` — SPEC §15 originally described P0 as a `ping` + `echo_write` spike; superseded by the dense P0 in `TASK.md`. SPEC updated 2026-10-31.

## Open questions

- `[OPEN] misfile-rate` — is best-guess session filing good enough, or is strict binding needed? Measure during P0/P1 dogfood (SPEC §2.3).
- `[OPEN] granularity` — are free-text notes + edges + handles enough for dense architecture work? Revisit after ~1,000 real notes.
- `[BLOCKED] hosted-curation` — can consolidation run on the hosted side? Waiting on the scheduled-execution finding in P0.

## Re-entry route

`AGENTS.md` §12 → `CONTEXT.md` (this file) → `TASK.md` current gate → `NOTEPAD.md` newest entries → `docs/SPEC.md` section named by the task → `MEMORY.md` key if a decision looks surprising.