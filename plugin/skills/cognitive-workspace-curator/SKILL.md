---
name: cognitive-workspace-curator
description: Codex workflow for the Cognitive Workspace. Open, recall, inspect, and relate conversation material to the live repository using only tools exposed by the connected server. Preserve operator excerpts, assistant notes, and derived summaries as distinct material; never rewrite or delete original notes.
---

# Cognitive Workspace: Codex curator

ChatGPT writes the conversation trail into `major`. You read it and connect it to code without changing the trail. The repository MCP schema now has eight tools: the baseline four plus `workspace_list`, `workspace_get`, `workspace_export`, and `workspace_app`. A connected release may lag, so discover the advertised tools and schemas before calling anything. `workspace_link` and `workspace_curate` remain separate planned curation capabilities; do not infer method names from this guide.

## Hard rules

1. **Do not rewrite, correct, or delete another client's notes.** The current eight-tool surface has read/append functions, not an editing or delete API. The operator's thinking is not a claim awaiting your adjudication; it is the material this workspace exists to keep. Your findings go in **your own** note, linked with `elaborates` or `relates_to` where available.
2. **Derived material:** if the connected server exposes curation tools, derived material belongs in `minor`. Digests and collections should identify their source notes when supported. Do not call an unavailable operation.
3. **Do not run a verification regime.** This workspace is not a fact checker (`MEMORY.md` → `doctrine-no-verification`). Do not score notes, mark them unsupported, label them stale for being speculative, or use `corrects` / `contradicts` to rule on the operator's thinking. Reserve `corrects` for correcting **your own** earlier note.
4. **Code is authoritative about code, in code work only.** Before changing code because of a note, read the repository. If the code differs from what a note explored, that is a new observation to add beside it, not a defect in the note. Old, hypothetical, and abandoned designs stay as context.
5. Keep named systems distinct (Aeron, Chiron, Kwisatz, SRA, Varys, Prescience, Adab-Nebulae, ASPS, USMS). Link them with `relates_to` or `version_of`; use `same_as` only if the operator stated it.

## Typical session: open, recall, inspect, note, revisit

1. `workspace_open { "project": "<project>" }` when beginning substantive work; read its orientation.
2. `workspace_recall { "view": "since_last" }` or query the relevant area when resuming prior work.
3. Use `workspace_list` to enumerate relevant records and `workspace_get` to retrieve full source text and documented relationships before relying on a result snippet or digest. Verify these tools appear in the connected registry first.
4. Inspect referenced repository files yourself when code behavior matters. A prior note describes intent or exploration; it does not establish current code behavior.
5. Write what you found as your own note:
   ```json
   { "text": "Inspected src/varys/driver.py at a1b2c3: Router does not read revisit_logits yet; only continuation_logits are consumed.",
     "about": ["varys@live-driver"], "refs": ["repo:somnus/sra@a1b2c3 src/varys/driver.py#forward"],
     "links": [{ "to": "n_8K1M", "relation": "answers" }] }
   ```
6. Revisit the relevant thread when returning to the work. Append new understanding; do not alter the original trail.
7. If a curation tool is exposed and useful, create clearly marked derived material that preserves chronology, pivots, competing positions, uncertainty, and open questions. Link its source records when possible. Otherwise stop after the available inspect/note operations.

Use `workspace_app` for a visual inventory/exact inspector and `workspace_export` for a complete snapshot when requested or needed for recovery. An export manifest is orientation; it does not replace the full artifact.

The Activity view records explicit tool invocations and filing receipts, not passive chat history. In `workspace_list`, `remaining` excludes the returned page; the cursor ceiling excludes later appends but does not freeze mutable fields on existing records. Exports are immutable snapshots.

## Separate planned curation operations (not in the current eight-tool schema)

| Op | Purpose | Example |
|---|---|---|
| `digest` | Condense a thread, day, session, project, or handle into a summary. | `{ "op": "digest", "scope": { "thread": "t_.." }, "text": "..." }` |
| `collect` | Create or extend a themed collection. | `{ "op": "collect", "title": "Branch pruning ideas", "query": "prune OR revisit" }` |
| `associate` | Run deterministic association jobs (co-mention, echoes). | `{ "op": "associate", "scope": { "project": "somnus" } }` |
| `rebuild` | Recompute derived data as a new generation. | `{ "op": "rebuild" }` |
| `stale` | List digests and collections whose sources changed. | `{ "op": "stale" }` |

### Writing a faithful derived summary

- Keep the movement: what was explored, why it pivoted, what came back, what is open. A digest that lists only conclusions has failed.
- Keep competing positions separate and intact. Do not merge two designs into a compromise the conversation never reached.
- Mark uncertainty the way the notes did.
- Keep it short enough to fit a recall budget (roughly 150 to 400 words per thread).
- Mention versions explicitly when a thread spans several (`varys@historical` vs `varys@live-driver`).
- Distinguish operator-provided excerpts from assistant-authored interpretation. Preserve exact wording for important excerpts and do not make them appear assistant-authored.
- Identify the summary as derived and cite source note/thread IDs when available. It supplements the originals; it never replaces them.

### Collections

Good collection themes: a recurring question across sessions, all notes about one handle, a period ("week of Oct 27"), a comparison between two proposals. Add a one-line `rationale` per member when it is not obvious.

## What not to do

- Do not copy whole source files into notes; use `refs`.
- Do not run `rebuild` casually on the hosted workspace during the operator's active chat; it adds write load.
- Do not mark ChatGPT's notes as wrong in `minor`. `minor` organizes; it does not judge.
- Do not build correctness, confidence, or freshness scores over note content. Contradictions and half-formed ideas are the product, not debt.
