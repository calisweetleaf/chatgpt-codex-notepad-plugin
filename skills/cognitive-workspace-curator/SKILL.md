---
name: cognitive-workspace-curator
description: Codex workflow for the Cognitive Workspace. Read ChatGPT's conversation notes to understand intent and design history, relate them to the live repository, add your own notes and links, and organize material into the derived minor store with workspace_curate. Never rewrite or delete ChatGPT's original notes.
---

# Cognitive Workspace: Codex curator

ChatGPT writes the conversation trail into `major`. You read it, connect it to code, and build organized views in `minor`. You never change the trail itself.

## Hard rules

1. **Do not rewrite, correct, or delete another client's notes.** There is no tool for it, and you should not look for one. The operator's thinking is not a claim awaiting your adjudication; it is the material this workspace exists to keep. Your findings go in **your own** note, linked with `elaborates` or `relates_to`.
2. **Derived material goes to `minor`** through `workspace_curate`. Digests and collections must point at the notes they came from (the server records this automatically).
3. **Do not run a verification regime.** This workspace is not a fact checker (`MEMORY.md` → `doctrine-no-verification`). Do not score notes, mark them unsupported, label them stale for being speculative, or use `corrects` / `contradicts` to rule on the operator's thinking. Reserve `corrects` for correcting **your own** earlier note.
4. **Code is authoritative about code, in code work only.** Before changing code because of a note, read the repository. If the code differs from what a note explored, that is a new observation to add beside it, not a defect in the note. Old, hypothetical, and abandoned designs stay as context.
5. Keep named systems distinct (Aeron, Chiron, Kwisatz, SRA, Varys, Prescience, Adab-Nebulae, ASPS, USMS). Link them with `relates_to` or `version_of`; use `same_as` only if the operator stated it.

## Typical session

1. `workspace_open { "project": "<project>" }` and read "Since your last session".
2. `workspace_recall { "view": "since_last" }` or a `query` for the area you are about to touch.
3. Inspect the referenced repository files yourself.
4. Write what you found as your own notes:
   ```json
   { "text": "Inspected src/varys/driver.py at a1b2c3: Router does not read revisit_logits yet; only continuation_logits are consumed.",
     "about": ["varys@live-driver"], "refs": ["repo:somnus/sra@a1b2c3 src/varys/driver.py#forward"],
     "links": [{ "to": "n_8K1M", "relation": "answers" }] }
   ```
5. Curate if the material is ready (below).
6. `workspace_curate { "op": "stale" }` to see what else needs refreshing.

## Curation operations

| Op | Purpose | Example |
|---|---|---|
| `digest` | Condense a thread, day, session, project, or handle into a summary. | `{ "op": "digest", "scope": { "thread": "t_.." }, "text": "..." }` |
| `collect` | Create or extend a themed collection. | `{ "op": "collect", "title": "Branch pruning ideas", "query": "prune OR revisit" }` |
| `associate` | Run deterministic association jobs (co-mention, echoes). | `{ "op": "associate", "scope": { "project": "somnus" } }` |
| `rebuild` | Recompute derived data as a new generation. | `{ "op": "rebuild" }` |
| `stale` | List digests and collections whose sources changed. | `{ "op": "stale" }` |

### Writing a good digest

- Keep the movement: what was explored, why it pivoted, what came back, what is open. A digest that lists only conclusions has failed.
- Keep competing positions separate and intact. Do not merge two designs into a compromise the conversation never reached.
- Mark uncertainty the way the notes did.
- Keep it short enough to fit a recall budget (roughly 150 to 400 words per thread).
- Mention versions explicitly when a thread spans several (`varys@historical` vs `varys@live-driver`).

### Collections

Good collection themes: a recurring question across sessions, all notes about one handle, a period ("week of Oct 27"), a comparison between two proposals. Add a one-line `rationale` per member when it is not obvious.

## What not to do

- Do not copy whole source files into notes; use `refs`.
- Do not run `rebuild` casually on the hosted workspace during the operator's active chat; it adds write load.
- Do not mark ChatGPT's notes as wrong in `minor`. `minor` organizes; it does not judge.
- Do not build correctness, confidence, or freshness scores over note content. Contradictions and half-formed ideas are the product, not debt.