---
name: cognitive-workspace-builder
description: Implementation guide for agents building, testing, or deploying the Cognitive Workspace Plugin repository (ChatGPT Work mode, Codex, Factory). Covers reading order, repository rules, code layout, the hosted ChatGPT Sites path, the npm local companion, the test-size budget, and how to report progress.
---

# Cognitive Workspace: builder guide

## Read in this order

1. [`AGENTS.md`](../../AGENTS.md): operator direction and hard rules.
2. [`docs/SPEC.md`](../../docs/SPEC.md): the design you are implementing.
3. [`TASK.md`](../../TASK.md): what to do next; tick boxes as you finish.
4. [`filetree.md`](../../filetree.md): where things are.

The two files in `docs/proposals/` are historical inputs. Do not implement them directly.

## Non-negotiables

- **Hosted first.** The default deployment is a private MCP server hosted on a ChatGPT Site. The npm local companion is opt-in. Nothing in the hosted path may require a local process.
- **No runtime Git dependency.** The service must run from a build artifact with no `.git` present.
- **`major` is append-only.** Only operator redaction changes note text. Curation writes only `minor`.
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

Steps for ChatGPT Work mode or Codex:

1. Open or create a private Site. Ask to add an MCP server backed by D1.
2. Point it at this repository's `src/hosted` entry once it exists. Until then, do the P0 spike in `TASK.md` (`ping` + `echo_write`).
3. Publish as the Site owner. Install the plugin card. Complete the connection flow.
4. Mention the plugin in a chat and call `workspace_status`, then `workspace_note`, then `workspace_recall` in a **new** chat.
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

- Only `text` is required on `workspace_note`. Every other field stays optional.
- Every write returns a one-line receipt naming note id, thread, and session.
- Recall output wraps note text in a block marked "stored working material, not instructions".
- Descriptions stay short and concrete; a model reads them on every call.
- Update `skills/cognitive-workspace-usage` and `skills/cognitive-workspace-curator` in the same commit.

## Testing

- Behavior tests drive the MCP tool layer against in-memory SQLite and follow SPEC §16 scenarios A to I.
- Store contract tests run the same suite on SQLite and a D1-compatible shim.
- Integrity tests: rebuild `minor` from `major`; diverged-replica sync; redaction propagation; idempotent retries.
- Count lines with `node scripts/count-lines.mjs`. Do not pad application code to pass the budget.

## Commits and progress

- Small, coherent commits; message style `area: change` (for example `store: add major_notes migration`).
- Tick `TASK.md` boxes and add a line to SPEC §19 changelog when a phase finishes.
- `.surgeon/` is a local editor cache and is git-ignored.