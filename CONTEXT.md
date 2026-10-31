# CONTEXT.md: Current state index

**Updated:** 2026-10-31
**Purpose:** compact routing keys so a fresh agent can orient in one read. Deep material lives in [MEMORY.md](MEMORY.md); live working state in [NOTEPAD.md](NOTEPAD.md); next actions in [TASK.md](TASK.md); design in [docs/SPEC.md](docs/SPEC.md).

Keep entries short and keyed. If an entry needs a paragraph, it belongs in `MEMORY.md` and this file should hold the key plus one line.

---

## Current gate

- **Gate:** P0, the hosted vertical slice on ChatGPT Sites ([TASK.md](TASK.md) → P0).
- **Expected verdict:** a note written in one ChatGPT chat is recoverable from a different chat, and Codex sees the same workspace.
- **Last observed verdict:** Site publication succeeded. Project `appgprj_6ae661d0968081918d8c386d729f1c8c` is live at [somnus-cognitive-workspace.daeronsomnus.chatgpt.site](https://somnus-cognitive-workspace.daeronsomnus.chatgpt.site), deployment `appgdep_6ae662c153f481918c6aa28f86909e99`, version `appgprj_6ae661d0968081918d8c386d729f1c8c~appgver_10a9a41eeeac8191bba2ff6672ea46a5`, source `0c1527ced06a2681d3adc0d957818e624c06b952`, MCP enabled, env revision 1. Plugin Creator provisioned and installed canonical app `plugin_asdk_app_sites_09950ef599088191a5e6c9569f8c7dae`; release `pluginrel_6ae66309e2b88191b922c50853ac4d5d` is v1.0.1, and deployed skill readback was verified. A schema probe using the Site service credential received HTTP 401 at dispatch for `server/discover` and `tools/list`; this does not establish a server defect or exercise MCP handling. The current chat tool registry did not show workspace tools after retry. Cross-chat note recovery is still untested.
- **Validation report:** root reran all 13 tests locally, including Workerd D1 and HTTP owner-gate/list/status coverage; typecheck and line budget pass (457 application lines, 234 test lines). Root also reports clean `npm pack` install with `--omit=dev` outside the repo and two compiled stdio processes persisting/retrieving through numbered migrations. These results do not establish cloud D1 or Sites behavior.
- **Deployment:** publishing and canonical plugin provisioning succeeded; root is syncing the source repository to `main`. The operator can test the installed plugin, but no cross-chat persistence result is recorded yet.
- **Next action:** user performs a fresh-chat plugin availability and note→recall check; record outcomes without inferring server behavior from the service-credential 401 or missing current-chat tool listing. Root is syncing GitHub `main`. Preserve the separate Site source mirror workflow described in `plugin/README.md`.

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

`AGENTS.md` §12 → `CONTEXT.md` (this file) → `TASK.md` current gate → `NOTEPAD.md` newest entries → `docs/SPEC.md` section named by the task → `MEMORY.md` key if a decision looks surprising.
