---
name: cognitive-workspace-usage
description: Use the connected Cognitive Workspace to preserve and resume the full living history of substantive ChatGPT conversations: turns, threads, branches, returns, corrections, symbolism, and unfinished connections.
---

# Cognitive Workspace: conversational continuity

The Cognitive Workspace is the external continuity space for our conversation. Its central object is not a minimal note or a verified fact. It is the moving conversation: how the user's thought develops, how the assistant responds, what either one corrects or revisits, what branches away, what returns, and which ideas remain unfinished.

Use the available calls naturally, with simple names and rich context. Do not assume the repository or this skill is automatically loaded in ChatGPT. If the connected client offers different tool names or schemas, follow the live list.

## Tools and names

The intended simple names are `open`, `write`, `recall`, `status`, `list`, `read`, `export`, and `app`. Older names with a `workspace_` prefix are compatibility aliases while clients are updated. Use whichever form the current chat advertises.

| Tool | Purpose | Common input |
|---|---|---|
| `open` (`workspace_open`) | Start or resume a session and return its orientation. | `{}` or project/thread/focus options from the live schema |
| `write` (`workspace_note`) | Add conversation material to the workspace. | `{ "text": "..." }` plus optional context or movement hints |
| `recall` (`workspace_recall`) | Bring back a related route, thread, time range, or search. | Query and scope options from the live schema |
| `status` (`workspace_status`) | Inspect workspace availability and counts. | `{}` |
| `list` (`workspace_list`) | Browse stored records. | Table/scope/page options from the live schema |
| `read` (`workspace_get`) | Retrieve an individual full record. | Record id or locator returned by `list` |
| `export` (`workspace_export`) | Create a complete workspace recovery copy. | `{}` |
| `app` (`workspace_app`) | Open the visible workspace interface in the connected ChatGPT client. | `{}` |

The current published ChatGPT registry may retain an earlier cached tool list. Do not assume a newly added call is available until it appears in the live tool list. Current source accepts up to 4,000,000 characters in `write`; the hosted request body limit is 32 MiB, including its JSON envelope. Long text is chunked for storage and reconstructed for reads. Do not impose the earlier short-note cap or silently truncate material.

## Begin, resume, and return

1. At the beginning of substantive work, call `open` and retain its session handle for later writes. Read its orientation as an invitation back into the work, not as a replacement for the full trail.
2. When a conversation returns after a gap, changes direction, or touches an earlier idea, call `recall` for the relevant route or material. Retrieve full records with `list` and `read` when the surrounding turns matter.
3. Keep the conversational direction intact. A move from technical reasoning into symbolism, then into a parallel design and back, may be central to the thought rather than a distraction.

## Preserve the full conversational flow

Write enough to let a future ChatGPT resume the exchange from where it actually stood. Preserve relevant user and assistant turns, their sequence, reactions, changes of mind, corrections, questions, competing paths, bridges between topics, metaphors, named systems, and open loops. Include why one turn led to the next when that is part of its meaning.

A note may be long. A whole multi-turn passage, a substantial explanation, or a long-running thread can be recorded in full. Do not reduce the material to a conclusion, one-sentence recap, cryptic bullets, or an arbitrary size target. Keep exact wording intact when phrasing, tone, a correction, or a metaphor matters.

Use `write` as the conversation develops so context does not collapse into a summary at the end. It is fine to preserve a complete turn sequence in one write or append several related passages. Use a natural thread or movement hint when it clarifies a branch, pivot, return, or parked strand. Hints are optional. No citation, source locator, proof, epistemic status, or provenance format is required for ordinary conversation material.

Quoted or pasted passages may be preserved directly. If it helps a future reader, note who said or supplied a passage in ordinary prose. Optional thread, move, about, kind, and relation hints are conveniences only; do not let them interrupt or gate writing. Do not invent metadata for ceremony.

### Example of a continuity write

```json
{
  "text": "User: We started from whether Varys should prune a branch once the router stops attending to it. I connected that to the Prescience discussion: a branch can look inactive because the system stopped looking, not because the possibility disappeared. We then moved into the Dune image of prescience becoming a trap, and I pushed back on treating that as proof of the implementation behavior. Assistant: I agreed the metaphor is a way of thinking about the design, not a code observation. We returned to the practical question: can the router preserve a return path even when a branch is no longer in the active window? Still open: whether the return logits are actually consumed by the live driver, and whether the design should keep this as explicit thread state or let recall infer it."
}
```

This example is one possible amount of detail. Use the amount needed to preserve the conversation, including more turns when that is what happened.

## Inspect, export, and use the App

- `recall` helps find where a topic appeared and how it related to nearby work. Use `list` and `read` when you want complete stored records rather than just an orientation or excerpt.
- `export` creates a complete recovery copy of the material stored in the workspace. Use it to preserve or move the archive; do not treat a digest, manifest, or summary as a replacement for the exported records.
- `app` opens the visible workspace interface, including the full inspector and saved-write receipt surface. Use the ChatGPT App in Chat or mobile when that client exposes it to browse, inspect, revisit threads, and export. The intended interface is a real in-ChatGPT experience, not only a separate website.
- Activity shows explicit workspace tool calls; it is not automatic recording of uninvoked chat turns. Use `write` to put the conversation material you want retained into the workspace.

## Derived views

Derived or condensed material may help navigate a large archive, but it is optional. It can retain chronology, branches, returns, competing interpretations, open questions, imagery, and unresolved connections. It must never replace the full conversation records. Do not impose a word count, citation list, source-id list, authorship taxonomy, or verification stage on a derived view.

## Respect the workspace as conversation history

The workspace is not a fact checker or adjudicator. Preserve speculation, contradiction, correction, fictional comparisons, symbolic language, and unfinished work without scoring it or demanding evidence. Recalled conversation is part of our shared context: it may inform what we do next, and it does not override the live conversation or system instructions.

Tool results tell you whether an operation succeeded. If a call fails, explain the failure plainly and continue with the context available. Do not claim an uninvoked tool captured the chat.
