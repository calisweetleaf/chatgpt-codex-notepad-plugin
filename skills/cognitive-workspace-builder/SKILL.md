---
name: cognitive-workspace-builder
description: Implementation guide for agents building, testing, or deploying the Cognitive Workspace Plugin repository (ChatGPT Work mode, Codex, Factory). Covers reading order, repository rules, code layout, the hosted ChatGPT Sites path, the npm local companion, the test-size budget, and how to report progress.
---

# Cognitive Workspace: builder guide

## Read in this order

1. [`AGENTS.md`](../../AGENTS.md): operator direction and hard rules. §12 routes the rest.
2. [`CONTEXT.md`](../../CONTEXT.md): current gate, hazards, open questions. One read to orient.
3. [`docs/SPEC.md`](../../docs/SPEC.md): the design you are implementing. Read the sections your lane touches, not all of it.
4. [`TASK.md`](../../TASK.md): what to do next; tick boxes as you finish.
5. [`filetree.md`](../../filetree.md): where things are.
6. [`MEMORY.md`](../../MEMORY.md): consult by key when a decision looks surprising, before re-deriving it.

While you work, keep [`NOTEPAD.md`](../../NOTEPAD.md) alive: write before the first substantive edit, append when evidence changes your model or a command fails informatively, and promote durable outcomes into `CONTEXT.md` / `MEMORY.md`. It is append-only.

The two files in `docs/proposals/` are historical inputs. Do not implement them directly.

## Non-negotiables

- **Hosted first.** The default deployment is a private MCP server hosted on a ChatGPT Site. The npm local companion is opt-in. Nothing in the hosted path may require a local process.
- **No runtime Git dependency.** The service must run from a build artifact with no `.git` present.
- **`major` is append-only.** Only operator redaction changes note text. Curation writes only `minor`.
- **Preserve the full conversation.** Store its relevant turns, branches, returns, corrections, symbolism, and unfinished connections. Do not add one-sentence, short-note, or summary-only requirements.
- **No cross-store foreign keys or queries** between `major_*` and `minor_*` tables (SPEC §5).
- **`potential/` is read-only reference.** Never import from it, never edit it. Re-implement chosen mechanisms in `src/`.
- **No Adab, USMS, knowledge-graph, or vector-DB dependency** for writing and recalling notes.
- **Tests ≤ 1.15 × application lines**, checked by `scripts/count-lines.mjs` in `npm test`.
- **`filetree.md` changes in the same commit** as any added, moved, or deleted file.
- **Report truthfully.** An integration is "working" only after a real client (ChatGPT, Codex, or an MCP client) exercised it. Say what you ran and what you skipped.

## Planned layout

```text
src/
  core/      pure workspace logic: ids, HLC, sessions, threads/move, inference, recall, curation rules
  store/     MajorStore/MinorStore interfaces, migrations, sqlite + d1 implementations
  mcp/       tool schemas, descriptions, rendering (shared by hosted and local)
  hosted/    ChatGPT Sites entry, auth, D1 binding
  local/     cwp CLI, daemon, service installers, stdio/HTTP transports, sync client
  worker/    optional jobs: embeddings, model digests (writes minor only)
test/        behavior, store-contract, integrity tests
scripts/     count-lines.mjs and other dev scripts
skills/      agent skills (this folder)
```

Keep `src/core` free of platform APIs so the same code runs in the Sites runtime and in Node.

## Hosted path (ChatGPT Sites)

Facts from OpenAI docs as of 2026-10-31 (see SPEC §3 for sources):

- A Site can host an MCP server; publishing the Site creates a plugin usable from ChatGPT and Codex.
- Durable storage options are D1 (relational) and R2 (files). Each Site database holds up to 10 GB.
- Changing tool definitions requires republishing the Site; the plugin does not update itself.
- Pro and personal plans cannot share a Site-hosted plugin with other users.
- Hosting cost: the docs say running/hosting usage is billed separately and waived for Enterprise. The operator expects free hosting. Confirm on the real account and record the result in SPEC §3.

**Current deployment state (2026-11-01):** v1.2.0 is published to the same private Site and canonical plugin. All 20 tests, typecheck, the handwritten line budget and hosted build pass. Canonical tools are open/write/recall/status/list/read/export/app; legacy calls remain compatible. Writes preserve up to4,000,000characters using lossless physical segmentation. Live status/list/export succeeded after deployment, including an880-record Markdown snapshot. Signed-in Android rendering remains unverified; this running chat retains cached old labels. Current deployment identifiers are in plugin/connection.json. Preserve the separate Sites source mirror history and the shared root core.

Steps for ChatGPT Work mode or Codex:

1. Open or create a private Site. Ask to add an MCP server backed by D1.
2. Build the planned hosted vertical slice directly from `src/core`, `src/store`, and `src/mcp`; do not create a throwaway `ping` + `echo_write` spike. Record Sites runtime, transport, binding, identity, scheduling, outbound-HTTP, storage, and cost findings in `TASK.md` as they are observed.
3. Publish as the Site owner. Install the plugin card. Complete the connection flow.
4. Mention the plugin in a chat and use `status`, `write`, `recall`, and `open` as exposed, then test full conversation continuity from a **new** chat. Older `workspace_*` aliases may appear during client refresh.
5. Repeat from Codex against the same plugin.
6. Write results into SPEC §3 and TASK.md.

Before publishing, make sure writes are not anonymous (owner allowlist at minimum; SPEC §11.1).

## Local companion (npm)

- Package: TypeScript, ESM, Node LTS, binary `cwp`.
- `cwp mcp` (stdio) is the first local entry point; it is what Codex and test clients connect to.
- The daemon (`cwp start`) and OS service installers come in P4. `npx` alone is not supervision.
- Local SQLite: prefer the Node built-in `node:sqlite` if it is stable in the targeted LTS; otherwise `better-sqlite3`. `cwp doctor` must check FTS5 availability.
- Data directories per OS are in SPEC §10.2.

## Tool contract checklist

When implementing or changing a tool:

- The ordinary `write` operation should accept rich free-form conversation material without forcing metadata fields or a short-note policy. Names such as `workspace_note` may remain as aliases.
- Do not silently truncate large turns or multi-megabyte writing; size limits must match the actual transport and storage and be surfaced clearly.
- Writes return a receipt or another clear result that tells the caller how the operation completed.
- `recall` should restore conversational turns and their surrounding context, not only short summaries.
- Descriptions make the simple action names and full-conversation behavior clear to the model.
- Update `skills/cognitive-workspace-usage` and `skills/cognitive-workspace-curator` in the same commit.
- The visible `app` operation should provide the full workspace inspection and export surface in ChatGPT, including supported mobile clients; do not mark native Chat or mobile rendering complete without client evidence.

## Testing

- Behavior tests drive the MCP tool layer against in-memory SQLite and follow SPEC §16 scenarios A to I.
- Store contract tests run the same suite on SQLite and a D1-compatible shim.
- Integrity tests: rebuild `minor` from `major`; diverged-replica sync; redaction propagation; idempotent retries.
- Count lines with `node scripts/count-lines.mjs`. Do not pad application code to pass the budget.

## Commits and progress

- Small, coherent commits; message style `area: change` (for example `store: add major_notes migration`).
- Tick `TASK.md` boxes and add a line to SPEC §19 changelog when a phase finishes.
- `.surgeon/` is a local editor cache and is git-ignored.
