---
name: cognitive-workspace-curator
description: Codex workflow for entering, understanding, and adding to Cognitive Workspace conversations while preserving their full turns, branches, returns, corrections, symbolism, and unresolved connections.
---

# Cognitive Workspace: Codex conversation curator

ChatGPT and Codex use the Cognitive Workspace to continue shared lines of thought. Read the conversational trail as living context, not as a collection of verified claims. The goal is to help a later session re-enter the ideas, turns, detours, and unfinished work without erasing what happened along the way.

## Tool names and availability

The source advertises `open`, `write`, `recall`, `status`, `list`, `read`, `export`, and `app`. Older `workspace_` names are compatibility aliases. Current source accepts up to 4,000,000 characters in `write`, with a 32 MiB hosted request body limit and chunked storage/read reconstruction. Use the exact tools and fields available in the current client; the published registry may lag.

1. `open` gives current orientation and a session handle.
2. `recall` returns material near a query, thread, time, or continuation point.
3. `list` navigates records; `read` returns a full record.
4. `write` adds your continuation or observation into the conversation history.
5. `export` provides the full stored archive; `app` opens the visible inspection UI.

## Preserve the original conversation

- Preserve the full sequence of relevant user and assistant turns. Include the line of thought, reactions, why it moved, what branches opened, what returned, corrections, symbolic or fictional links, alternatives, and what remains unresolved.
- Do not recast the trail as a concise technical conclusion. A long, multi-turn continuation is appropriate. Do not apply the previous short-note limit or truncate it to fit a summary.
- Add a new continuation; do not rewrite or delete prior conversational material. The underlying workspace is designed to keep primary material intact.
- Speaker cues can be written naturally when useful, but no citations, source locators, provenance fields, verification statuses, or mandatory labels are required.
- Derived views and collections are optional navigation aids. Keep the conversation material available in full; a derived summary never replaces it.

## Typical session

1. Call `open` at the start of substantive repository work and carry its session handle through later calls.
2. Use `recall` when a note mentions an earlier decision, when a new implementation question connects to old discussion, or when a branch is being resumed. Bring back enough of the actual exchange to understand the connection.
3. Use `list` to browse and `read` to inspect full relevant records. An orientation or search excerpt can point to context; it is not a reason to impose a verification process on the note.
4. Inspect current repository code when making a code change. If code has moved on from an earlier discussion, add that as another moment in the history rather than recasting the earlier conversation as wrong.
5. Use `write` to capture what happened across the relevant turns, with the sequence and relationships intact. A `thread`, movement, `about`, or `refs` hint is optional; ordinary prose is enough.
6. Return to the prior thread when continuing it. Preserve the bridge between the old branch and what is happening now.
7. Use `export` for a complete recovery copy. Use the App view when the connected ChatGPT client offers it, including its Chat or mobile surface.

### Writing a continuation

Do not write only the final code result or decision when the conversation that led there matters. Capture the user’s framing and corrections, assistant reasoning or response, explored options, metaphorical connections, changes in direction, what was learned, what remains uncertain, and how the current action grew out of that path.

For example, instead of recording only “Router should preserve inactive branches,” a continuation might retain that this came from a Varys pruning discussion, returned through the Dune prescience metaphor, was challenged as not proving code behavior, and left an open question about whether return logits or explicit thread state preserve the route. Include the actual turns or wording at whatever length is needed to keep that distinction and movement clear.

## Optional derived material

The current everyday tools do not expose the planned `digest`, `collect`, `associate`, `rebuild`, or `stale` operations. If such tools appear in a future registry, derived work remains optional. Preserve competing ideas and chronology, keep the whole original trail available, and avoid turning a digest into a quality score, evidence report, or provenance ledger. No fixed word range or source-id citation format is required.

## No adjudication workflow

Do not score, certify, suppress, or label notes unsupported or stale because they contain speculation, symbolism, contradictory ideas, or a mistaken hunch. This workspace preserves thought as it develops; it is not a fact checker. In coding work, reading the current code is how you learn current code behavior, not a process for judging past notes.
