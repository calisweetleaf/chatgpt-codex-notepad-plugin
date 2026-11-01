# NOTEPAD — Agent Workbook

> External working notebook for agents operating in this repository.
>
> **This file is for the model, not the operator.**
> Its value is not presentation quality. Its value is the work behavior it induces:
> inspect → write → act → observe → write → redirect → validate → write → persist.
>
> `NOTEPAD.md` is the live, append-only workspace between repository instructions and durable
> codebase memory.
>
> **Hierarchy:** `AGENTS.md` → `NOTEPAD.md` → `CONTEXT.md` → `MEMORY.md`
>
> - `AGENTS.md` tells the agent how to operate.
> - `NOTEPAD.md` is where the agent externalizes active working state while operating.
> - `CONTEXT.md` indexes the durable state that survives the turn.
> - `MEMORY.md` stores the deep durable findings, provenance, architecture truth, failures,
>   verification, and historical strata.
>
> Do not make the operator reconstruct your work from chat. Keep the notebook alive while you work.

---

## Workbook Contract

1. **Write before substantial work begins.**
   - Record what you think the task is.
   - Record the repo state you actually observed.
   - Record what you are about to inspect first and why.
   - Record uncertainty, contradictions, and assumptions that could redirect the work.

2. **Write while working.**
   - The notebook is not a retrospective handoff generated after the work is done.
   - Append when new evidence changes your working model.
   - Append when a command/test fails in an informative way.
   - Append when a file, symbol, import, API, syntax, dependency, contract, artifact, or runtime
     behavior differs from what you expected.
   - Append before changing lanes or abandoning an approach.
   - Append a deferred observation immediately if it matters but is outside the current task.

3. **Write after substantial work.**
   - Record what actually changed.
   - Record verification truth.
   - Record remaining uncertainty/hazards.
   - Record what should be promoted into `CONTEXT.md` and `MEMORY.md`.
   - Leave the next agent a runnable re-entry point.

4. **Append only.**
   - Never rewrite history merely because your understanding changed.
   - Correct an earlier note with a new dated correction/addendum.
   - Historical confusion is useful provenance when the correction is explicit.

5. **Use this as a workbook, not a status report.**
   - Fragments are allowed.
   - Partial hypotheses are allowed.
   - Temporary maps, tables, pseudocode, equations, command output excerpts, candidate file paths,
     symbol lists, and competing interpretations are allowed.
   - Polished prose is not required.
   - Useful state is required.

6. **Do not wait for certainty.**
   - Mark epistemic status instead:
     - `OBSERVED`
     - `INFERRED`
     - `HYPOTHESIS`
     - `OPERATOR-DIRECTIVE`
     - `VERIFIED`
     - `DISPROVEN`
     - `DEFERRED`
     - `BLOCKED`
     - `SUPERSEDED`

7. **Do not confuse scratch with canon.**
   - A NOTEPAD hypothesis does not become repository truth merely because it was written here.
   - Promote durable outcomes through `CONTEXT.md` and `MEMORY.md`.
   - Point to live code, tests, docs, artifacts, manifests, logs, or source evidence whenever possible.

8. **Do not suppress useful failures.**
   - A missing import, wrong signature, stale path, malformed fixture, unexpected branch, dirty tree,
     failed assertion, contradictory document, absent checkpoint, or suspicious metric belongs here
     when it changes the work.
   - If it cannot be investigated now, capture it under `DEFERRED` and continue the authorized lane.

9. **Every substantial entry must route somewhere.**
   - Into an immediate next action.
   - Into a file/symbol/test to inspect.
   - Into a deferred thread.
   - Into `CONTEXT.md`.
   - Into `MEMORY.md`.
   - Or explicitly nowhere because it was disproven/noise.

10. **Do not manufacture a notebook after the fact.**
    - If the only NOTEPAD write is at handoff, the workbook contract was not followed.

---

## Write Triggers

Append a checkpoint whenever any of these occur:

- task/session start
- repo/context re-entry after a pause
- before first code edit
- architecture interpretation changes
- unexpected file or symbol discovered
- missing file/import/API/syntax/dependency encountered
- current docs disagree with live code
- command/test produces informative failure
- experiment changes the hypothesis
- scope or implementation lane changes
- an approach is rejected
- a new hazard appears
- a useful observation must be deferred
- another agent's work changes your assumptions
- before a risky/destructive/large edit
- after a coherent implementation slice lands
- validation result changes
- before handoff/session close
- before promoting durable findings to `CONTEXT.md` / `MEMORY.md`

A checkpoint can be three lines. Do not avoid writing because the full entry template feels too large.

---

## Entry Identity

Use a stable header so other agents and memory files can route back here.

```text
## <YYYY-MM-DDTHH:MM:SS±TZ> | <agent> | <lane/task> | <phase>
```

Recommended `phase` values:

- `OPEN`
- `WORK`
- `CHECKPOINT`
- `PIVOT`
- `FAILURE`
- `DEFER`
- `VALIDATE`
- `CLOSE`
- `CORRECTION`
- `HANDOFF`

Reuse high-signal nouns across NOTEPAD, CONTEXT, and MEMORY:
filenames, symbols, task IDs, artifact names, subsystem names, run IDs, capability names.

---

# Active Workbook

> Append new entries below. Newest-at-bottom is recommended for multi-agent append safety.
> If repository doctrine explicitly requires newest-first, follow repository doctrine.

---

## <YYYY-MM-DDTHH:MM:SS±TZ> | <agent> | <lane/task> | OPEN

### Intake

- **Task as understood:** <WHAT I AM ACTUALLY TRYING TO ACCOMPLISH>
- **Operator constraint:** <EXPLICIT CONSTRAINTS / NONE>
- **Current lane:** <IMPLEMENTATION / DEBUG / AUDIT / RESEARCH / DOCS / EXPERIMENT / OTHER>
- **Authority loaded:** `<AGENTS.md>` · `<SPEC>` · `<STATE>` · `<OTHER REQUIRED SURFACES>`
- **Base state:** <BRANCH / COMMIT / DIRTY STATE / RUNTIME STATE / N-A>
- **Existing relevant context:** `<CONTEXT KEY / MEMORY ENTRY / TASK / PRIOR HANDOFF>`

### Initial Working Model

- `OBSERVED` — <FACT FROM CURRENT REPO / SOURCE>
- `OBSERVED` — <FACT>
- `INFERRED` — <CURRENT INTERPRETATION>
- `UNKNOWN` — <THING THAT MUST BE RESOLVED>
- `HAZARD` — <THING THAT COULD INVALIDATE THE PLAN>

### First Traversal

I will inspect:

1. `<file/symbol/artifact>` — <WHY>
2. `<file/symbol/artifact>` — <WHY>
3. `<test/command/evidence>` — <WHAT QUESTION IT ANSWERS>

### Immediate Route

`<first action>` → `<expected observation>` → `<next branch if true/false>`

Do not over-plan past evidence you have not inspected yet.

---

## <YYYY-MM-DDTHH:MM:SS±TZ> | <agent> | <lane/task> | WORK

### Observation

- `OBSERVED` — <NEW FACT>
- Source: `<path:symbol / command / artifact / source id>`

### Working Interpretation

- <CONCISE EXTERNALIZED REASONING SUMMARY>
- <WHAT THIS CHANGES ABOUT THE CURRENT MODEL>
- <WHAT IT DOES NOT YET PROVE>

### Action

- <WHAT I AM DOING NEXT BECAUSE OF THIS OBSERVATION>

### Route

- If <CONDITION>: inspect/do `<X>`
- Else: inspect/do `<Y>`

---

## Micro-Checkpoint — Use Freely

> Use this smaller form whenever stopping to fill a full block would interrupt the work.

```text
### <HH:MM> | CHECKPOINT | <key>
OBSERVED: <fact>
MEANS: <concise interpretation>
DO: <next action>
ROUTE: <file/symbol/test/deferred/memory key>
```

Example shape:

```text
### 14:22 | CHECKPOINT | parser-import
OBSERVED: `foo.py` imports `Bar` from `runtime.types`, but `Bar` now lives in `runtime.contracts`.
MEANS: likely stale import, not a parser algorithm failure.
DO: verify call sites + git history before editing.
ROUTE: `foo.py:parse_*` → `runtime/contracts.py:Bar`
```

---

## Discovery / Contradiction Checkpoint

Use when reality disagrees with instructions, docs, assumptions, or another agent's handoff.

### Discovery

- `OBSERVED`: <WHAT THE LIVE SURFACE SAYS>
- `EXPECTED`: <WHAT I EXPECTED>
- `CONFLICTS WITH`: `<doc / context / memory / prior entry / assumption>`
- `EVIDENCE`: `<path / command / lines / artifact>`

### Interpretation

- <MOST LIKELY EXPLANATION>
- Confidence: `<LOW | MEDIUM | HIGH>`
- Do not silently reconcile the conflict.

### Resolution Route

- [ ] verify live code
- [ ] inspect provenance/history
- [ ] test runtime behavior
- [ ] append correction to NOTEPAD
- [ ] promote correction to CONTEXT
- [ ] promote durable explanation to MEMORY
- [ ] defer with explicit key

---

## Failure Checkpoint

> A failure is working-state information. Capture it before blindly patching around it.

### Failure

- **Command/action:** `<WHAT FAILED>`
- **Failure surface:** `<ERROR / ASSERTION / SYMPTOM>`
- **Expected:** <EXPECTED RESULT>
- **Observed:** <ACTUAL RESULT>

### Diagnosis State

- `RULED OUT` — <THING>
- `POSSIBLE` — <THING>
- `POSSIBLE` — <THING>
- `UNKNOWN` — <THING>

### Next Probe

- <SMALLEST HIGH-INFORMATION ACTION>

### Anti-Loop Note

- Do not repeat: <COMMAND / APPROACH / ASSUMPTION> unless <NEW CONDITION>

---

## Deferred Thread

> Use this immediately when something matters but should not hijack the current lane.

### <HH:MM> | DEFERRED | <stable-key>

- **Found while:** <CURRENT TASK>
- **Observation:** <THING WORTH RETURNING TO>
- **Why not now:** <SCOPE / TIME / DEPENDENCY / OPERATOR OWNERSHIP>
- **Re-entry key:** `<exact filename/symbol/error/artifact/search phrase>`
- **Suggested first probe:** <ONE ACTION>
- **Promotion:** `<NOTEPAD ONLY | CONTEXT | MEMORY>` pending verification

Then return to the current task.

---

## Hypothesis / Experiment Block

> Useful for research, architecture exploration, debugging, and ambiguous systems work.

### Question

<WHAT AM I TRYING TO EXPLAIN OR DISTINGUISH?>

### Candidate Hypotheses

| ID | Hypothesis | Supporting evidence | Contradicting evidence | Status |
|---|---|---|---|---|
| H1 | <...> | <...> | <...> | OPEN |
| H2 | <...> | <...> | <...> | OPEN |
| H3 | <...> | <...> | <...> | OPEN |

### Discriminating Probe

- <TEST / SOURCE / FILE / EXPERIMENT THAT BEST SEPARATES THE HYPOTHESES>

### Result

- <OBSERVED RESULT>

### Update

- H1: `<SUPPORTED / WEAKENED / DISPROVEN / OPEN>`
- H2: `<...>`
- Working model: <CURRENT BEST EXPLANATION>
- Route: <NEXT PROBE OR PROMOTION TARGET>

---

## Investigation / Evidence Dump

> For OSINT, corpus analysis, architecture forensics, large-codebase archaeology, or any lane where
> preserving raw structured observations is more useful than prematurely compressing them.

### Objective

<QUESTION / TARGET>

### Raw Findings

- `<evidence-key>` — <FINDING> — source: `<source/path/artifact>`
- `<evidence-key>` — <FINDING> — source: `<source/path/artifact>`

### Emerging Structure

- <PATTERN / CLUSTER / DATA FLOW / ACTOR-SYSTEM RELATION / CODE TOPOLOGY>
- <PATTERN>

### Anomalies

- <ABSENCE / CONTRADICTION / OUTLIER / UNEXPECTED RELATION>
- <WHY IT MATTERS>

### Collection / Inspection Requirements

1. <NEXT REQUIRED SOURCE OR CODE SURFACE>
2. <NEXT REQUIRED SOURCE OR CODE SURFACE>
3. <DISCRIMINATING EVIDENCE>

### Current Hypothesis

`HYPOTHESIS` — <CURRENT MODEL>

### Confidence / Boundary

- Confidence: <LOW/MEDIUM/HIGH>
- Verified: <WHAT IS ACTUALLY ESTABLISHED>
- Not established: <WHAT MUST NOT BE PROMOTED AS FACT>

---

## Before-Edit Checkpoint

> Write before the first substantive edit or before a high-impact structural edit.

### Edit Intent

- Target: `<file(s)/symbol(s)>`
- Why this surface: <REASON>
- Invariant to preserve: <INVARIANT>
- Expected blast radius: <FILES / TESTS / CALLERS / ARTIFACTS>
- Rollback/recovery: <GIT / BACKUP / REGEN / REVERT PATH>

### Evidence Justifying Edit

- <FACT>
- <FACT>

### Post-Edit Gate

```bash
<COMMAND OR VALIDATION SEQUENCE>
```

---

## Post-Slice Checkpoint

> Use after a coherent implementation/research slice. Do not wait for the whole task.

### Changed / Learned

- <CHANGE OR FINDING>
- <CHANGE OR FINDING>

### Validation So Far

- `<command/test/check>` → `<PASS | FAIL | PARTIAL>`
- <key metric / evidence>

### Working State

- What is now true: <...>
- What is still open: <...>
- Next slice: <...>

---

## Multi-Agent Handoff Checkpoint

### Lane State

- **Agent:** <NAME/MODEL/LANE>
- **Base:** <COMMIT / TREE / ARTIFACT SET>
- **Owns:** <CURRENT LANE>
- **Must not assume:** <BOUNDARY>
- **Did:** <WHAT LANDED / WAS LEARNED>
- **Read-only:** `<YES/NO>`

### Validation

- `<command>` → `<RESULT>`
- `<command>` → `<RESULT>`

### Proof / Evidence Facts

- <ONLY THE FACTS THE NEXT AGENT NEEDS>

### Next Agent Route

- **Objective:** <ONE COHERENT OBJECTIVE>
- **Start at:** `<file/symbol/task/source>`
- **First command/probe:** `<...>`
- **Preserve:** <INVARIANTS>
- **Do not reopen:** <LANDED/SUPERSEDED WORK>

### Hazards

- <REAL BLOCKER / DRIFT / DIRTY STATE / CONFLICT>
- `none` if genuinely none

---

## <YYYY-MM-DDTHH:MM:SS±TZ> | <agent> | <lane/task> | VALIDATE

### Validation Matrix

| Surface | Command / method | Expected | Observed | Verdict |
|---|---|---|---|---|
| <unit> | `<...>` | <...> | <...> | PASS/FAIL |
| <integration> | `<...>` | <...> | <...> | PASS/FAIL |
| <artifact> | `<...>` | <...> | <...> | PASS/FAIL |
| <invariant> | `<...>` | <...> | <...> | PASS/FAIL |

### Validation Interpretation

- <WHAT THE RESULTS ESTABLISH>
- <WHAT THEY DO NOT ESTABLISH>
- <ANY FALSE POSITIVE / TOY / PARTIAL / ENVIRONMENT BOUNDARY>

### Fail-Loud State

- Remaining failures: <...>
- Accepted/expected failures: <...>
- Unexpected failures: <...>

---

## <YYYY-MM-DDTHH:MM:SS±TZ> | <agent> | <lane/task> | CLOSE

### Outcome

- **Verdict:** `<LANDED | PARTIAL | BLOCKED | FAILED | READ-ONLY | SUPERSEDED>`
- **Task result:** <ONE-PARAGRAPH MAX>
- **Base/end state:** <COMMIT / DIRTY STATE / ARTIFACT / SESSION STATE>

### What Changed

- `<path/symbol/artifact>` — <CHANGE>
- `<path/symbol/artifact>` — <CHANGE>

### What Was Learned

- <DURABLE FINDING>
- <DURABLE FINDING>
- <CORRECTED ASSUMPTION>

### Verification Truth

- `<command/check>` → `<RESULT>`
- `<metric/invariant>` → `<RESULT>`

### Remaining State

- `OPEN` — <THREAD>
- `DEFERRED` — <THREAD + RE-ENTRY KEY>
- `HAZARD` — <THREAD>
- `none` if closed cleanly

### Persistence Routing

#### Promote to `CONTEXT.md`

Compact keys/state the next agent should see immediately:

- `<context-key>` — <SHORT CURRENT TRUTH>
- `<context-key>` — <SHORT CURRENT TRUTH>

#### Promote to `MEMORY.md`

Deep durable material worth preserving:

- `<memory-title/key>` — <FINDING / PROVENANCE / FAILURE / ARCHITECTURE TRUTH>
- `<memory-title/key>` — <FINDING>

#### Keep only in `NOTEPAD.md`

- <EPHEMERAL / DISPROVEN / LOW-VALUE DETAIL THAT SHOULD NOT POLLUTE DURABLE MEMORY>

### Next Re-Entry

`AGENTS.md`
→ `NOTEPAD.md` search `<key>`
→ `CONTEXT.md` search `<key>`
→ `MEMORY.md` search `<key>`
→ inspect `<file/symbol/artifact>`
→ run `<command/probe>`

### Handoff

- Next objective: <...>
- First action: <...>
- Preserve: <...>
- Avoid repeating: <...>

---

## Correction / Addendum

> Never rewrite an old entry just to make history cleaner.

## <YYYY-MM-DDTHH:MM:SS±TZ> | <agent> | <original-key> | CORRECTION

- **Corrects:** `<prior timestamp / heading / claim>`
- **Old claim:** <SHORT DESCRIPTION>
- **New evidence:** <WHAT CHANGED>
- **Corrected truth:** <CURRENT INTERPRETATION>
- **Propagation required:** `<CONTEXT | MEMORY | DOC | CODE | NONE>`
- **Route:** `<relevant file/symbol/artifact>`

---

# Optional Live Boards

These are useful in long-running sessions. They are not required for every repository.

## Active Questions

- `[OPEN] <key>` — <question>
- `[BLOCKED] <key>` — <question> — waiting on <dependency>
- `[RESOLVED] <key>` — <answer> — see `<entry>`

## Deferred Queue

- `<key>` — <observation> — re-enter at `<file/symbol/test>`
- `<key>` — <observation> — re-enter at `<file/symbol/test>`

## Current Hypothesis Board

| Key | Working hypothesis | Confidence | Next discriminator |
|---|---|---:|---|
| `<H1>` | <...> | low/med/high | <...> |

## Current Hazard Board

- `<key>` — <hazard> — <mitigation / required check>

## Current Gate Board

- Current gate: `<task/test/milestone>`
- Expected verdict: `<...>`
- Last observed verdict: `<...>`
- Required command: `<...>`
- Next gate: `<...>`

---

# Promotion Rules

## NOTEPAD → CONTEXT

Promote when a finding becomes useful for rapid future routing:

- current task/gate changed
- active architecture interpretation changed
- important file/symbol/artifact became authoritative
- meaningful hazard or blocker exists
- a prior assumption was superseded
- a durable open thread needs a re-entry key
- validation meaningfully changed current posture

Keep the CONTEXT version compressed. Preserve the same keys.

## NOTEPAD → MEMORY

Promote when rediscovering the information later would waste serious work or risk architectural drift:

- durable architecture truth
- implementation lineage/provenance
- important experiment result
- failed approach + why it failed
- contradiction resolution
- non-obvious runtime behavior
- important test/verification boundary
- artifact lineage
- operator doctrine affecting the repository
- decisions plus rationale/consequences
- unresolved research question with meaningful accumulated evidence

MEMORY may be much larger than the NOTEPAD entry if the durable finding needs full reconstruction.

## Do Not Promote

Usually keep only here when:

- typo-level detour
- disproven hypothesis with no anti-rediscovery value
- transient command chatter
- obvious observation future agents can instantly rediscover
- formatting-only work with no repository consequence

---

# Anti-Patterns

Do **not** turn NOTEPAD into:

- a polished report written only after finishing
- a duplicate of `CONTEXT.md`
- a duplicate of `MEMORY.md`
- a user-facing progress diary
- a giant paste of raw terminal output with no interpretation
- a task board containing only future work
- a changelog containing only completed edits
- a hidden place for unsupported claims
- a graveyard of TODOs with no re-entry keys
- an excuse to narrate instead of inspecting/acting
- a requirement to write an essay after every shell command

The desired pattern is **small, frequent, useful state externalization**.

---

# The Workbook Loop

When in doubt:

```text
READ
↓
WRITE what is currently known / unknown
↓
ACT
↓
OBSERVE
↓
WRITE what changed in the working model
↓
ACT or PIVOT
↓
VALIDATE
↓
WRITE the evidence boundary
↓
PROMOTE durable state to CONTEXT / MEMORY
↓
LEAVE a re-entry route
```

The notebook should make interruption cheap.

A fresh agent should be able to open the newest relevant NOTEPAD entries and recover:
- what was being attempted,
- what reality looked like,
- what changed during the attempt,
- what failed,
- what is still uncertain,
- where to inspect next,
- and which findings already graduated into durable codebase memory.

That is the contract.

---

## 2026-10-31 | Factory/Opus | doc-layer: route NOTEPAD/CONTEXT/MEMORY, rescope P0 | CLOSE

### Outcome

- **Verdict:** `LANDED` (documentation only; no application code).
- **Task result:** Operator added `NOTEPAD.md` and corrected two things: the document layer must **route** rather than absorb, and the first hosted slice must be **dense, not minimal**. Wired `NOTEPAD.md` into the layer, created the `CONTEXT.md` / `MEMORY.md` it depends on, rescoped P0 from a `ping`+`echo_write` spike to the real hosted server, and removed verification-flavored language from the Codex curator skill.
- **Base/end state:** clean tree at the commit named below; `src/` still does not exist.

### What changed

- `TASK.md` — rewritten. P0 is now the hosted vertical slice (full `major` DDL, `minor` tables, four tools, auth before publish) with the platform unknowns as a fill-in table and explicit fallback branches. Added lane assignment: P0 and P1 are one codebase, P1 must not fork `src/core`.
- `CONTEXT.md` — new. Current gate, authoritative surfaces, architecture keys, hazards, deferred queue, open questions, re-entry route.
- `MEMORY.md` — new. Keys: `doctrine-no-verification`, `sites-facts-2026-10-31`, `potential-verdicts`, `proposal-rejections`, `store-split-rationale`, `document-layer-roles`.
- `AGENTS.md` §12 — replaced body with a "document layer routes; it does not absorb" table, the expanded inventory, a density-over-minimalism note bounding §11's "stay small", and a routing-first next action.
- `skills/cognitive-workspace-curator/SKILL.md` — hard rules 1, 3, 4 rewritten. `corrects` is now reserved for Codex correcting its own note; no scoring, no "unsupported" labels, no adjudicating the operator's thinking.
- `skills/cognitive-workspace-builder/SKILL.md` — reading order now routes through `CONTEXT.md` and `MEMORY.md` and requires keeping `NOTEPAD.md` alive.
- `docs/SPEC.md` — §15 P0 row rescoped; §19 changelog entry added.
- `filetree.md` — birds-eye map plus one-line routing hints per path, a "not yet created" `src/` block, and per-module `potential/` verdicts.
- `README.md` — document table reordered to the routing path; status line points at P0.

### What was learned

- `OPERATOR-DIRECTIVE` — "Density matters; smaller is not more efficient." Minimalism was the wrong instinct for the first deployable slice. Scope discipline belongs to *how much of `potential/` gets transplanted at once*, not to how complete the real server is. → `AGENTS.md` §12, `MEMORY.md` → `document-layer-roles`.
- `OPERATOR-DIRECTIVE` — the extensive doc setup exists to make the codebase proactively helpful, not to save tokens. Spend tokens by routing into the right surface and evolving it, so the next session resumes without reconstruction.
- `CORRECTED ASSUMPTION` — my earlier curator-skill wording ("if code and note disagree, write a note saying so", plus a `corrects` link) imported exactly the verified-reward posture the operator rejects. Fixed; the doctrine now has a `MEMORY.md` key so it is not re-derived loosely.
- `OBSERVED` — `NOTEPAD.md` arrived referencing `CONTEXT.md` and `MEMORY.md`, which did not exist. The routing layer was advertising dead ends. Resolved by creating both with real seeded content rather than stubs.
- `OBSERVED` — uncommitted `AGENTS.md` delta before this session was a markdown formatter pass only (trailing whitespace, blank lines, table separators). No operator prose was lost.

### Verification truth

- `surgeon op=check` on every changed file → `{"diagnostics": []}`.
- No tests exist to run; no code was written. Nothing here has been exercised against a live client.
- `sites-facts-2026-10-31` remains documentation-only. Hosting cost on this account is still unobserved.

### Remaining state

- `OPEN` — P0 has not started. No `src/`, no `package.json`.
- `HAZARD` — `hosting-cost`: operator expects free Sites hosting; docs say otherwise outside Enterprise. Only the account can settle it. Blocks operator decision 1.
- `HAZARD` — `sites-runtime-unknown`: runtime, MCP transport, DB binding count, handler identity all unobserved. Everything planned for `src/hosted` is provisional.
- `DEFERRED` — `potential-mining`: re-enter at P3 (time ranges, dedupe/relation/cluster schema) and P5 (echo detection). Re-implement in TypeScript; never import.

### Persistence routing

- Promoted to `CONTEXT.md`: `current gate`, `major-invariant`, `store-split`, `tool-surface`, `binding`, `no-verification`, `hosting-cost`, `sites-runtime-unknown`, `doc-drift`.
- Promoted to `MEMORY.md`: the six keys listed above.
- Kept only here: the formatter-delta observation.

### Next re-entry

`AGENTS.md` §12 → `CONTEXT.md` current gate → `TASK.md` P0 → `docs/SPEC.md` §5 (schemas) and §8 (tools) → open a new `NOTEPAD.md` entry before the first substantive change.

### Handoff

- **Next objective:** P0. Create the private Site with an MCP server + D1, stand up `src/core` / `src/store` / `src/mcp` / `src/hosted`, and record each platform finding here as it is observed.
- **First action:** create the Site and ask it to add an MCP server with D1 storage; capture the runtime and transport it gives you before writing host code.
- **Preserve:** `major` append-only; no cross-store query or FK; `text` as the only required tool field; auth decided before publishing.
- **Avoid repeating:** re-reading both proposals (reconciled in SPEC §2), re-evaluating `potential/` (verdicts in `MEMORY.md`), and re-checking hosting cost in documentation.

## 2026-10-31 | Codex | P0 implementation documentation | OPEN

### Intake

- **Task as understood:** Keep `NOTEPAD.md`, `TASK.md`, `CONTEXT.md`, and `filetree.md` aligned with the first application code landing; report current documentation contradictions to the implementation owner.
- **Operator constraint:** Build now; do not restart the specification cycle. This lane owns documentation only.
- **Current lane:** DOCS.
- **Authority loaded:** `AGENTS.md`, `CONTEXT.md`, `TASK.md`, `skills/cognitive-workspace-builder/SKILL.md`, `docs/SPEC.md`, and the supplied `defense-grade-doc-engine` instructions.
- **Base state:** clone at `9872573`; working tree clean at intake; no application code had landed when this entry was written.
- **Role allocation:** root owns implementation/deployment; `prod_finalizer` and `fletcher` handle their assigned implementation lanes; this agent maintains documentation alignment as code lands.

### Initial Working Model

- `OBSERVED` — `git log -1 --oneline` identifies the clone as `9872573`; `git status --short` was empty at intake.
- `OBSERVED` — `src/` and `package.json` were absent at intake; `filetree.md` lists the planned code layout as not yet created.
- `OBSERVED` — the implementation is beginning now, so the prior “not started” status is accurate only for this intake point and must be updated as files land.
- `UNKNOWN` — hosted runtime, MCP transport, storage bindings, and deployed-client behavior remain unobserved.
- `HAZARD` — do not document code, validation, or deployment as complete until directly observed.

### Immediate Route

Track code landing from the implementation owners → update the task checklist and file map for actual files → record only observed validation and leave hosted-client claims open until exercised.

### Tooling boundary

- `OBSERVED` — this session exposes neither the role-scoped Colony nor native Surgeon tools; the documented Surgeon package is unavailable through the session skill loader. Root authorized `apply_patch` as the available fallback for this documentation lane.
- `UNKNOWN` — no Colony sniff/claim or Surgeon receipt is available from this session; do not claim either occurred.

### 2026-10-31 | CHECKPOINT | implementation-scaffold

- `OBSERVED` — shared tree now contains `package.json`, `package-lock.json`, `tsconfig.json`, `scripts/count-lines.mjs`, and `src/store/migrations/0001.sql`; no other `src/` files were present at the check.
- `OBSERVED` — prod_finalizer reports `npm install` succeeded, the line-budget script succeeded with no source/tests, and initial typecheck returned TS18003 because no TypeScript inputs had landed. These are agent-reported results, not independently rerun here.
- `MEANS` — implementation has started, but core/tool/host behavior and the P0 client outcome remain unverified.
- `DO` — keep TASK, CONTEXT, and filetree aligned as core/MCP/host files land; do not check off complete schema/behavior or deployment steps until their acceptance evidence exists.

### 2026-10-31 | CHECKPOINT | local-core-tests-reported

- `OBSERVED` — shared tree now also contains `src/core/workspace.ts`, `src/store/database.ts`, `src/store/sqlite.ts`, and `test/workspace.test.ts`.
- `SMELL` — prod_finalizer reports `npm test` passes four SQLite behavior tests, typecheck, and the line budget (229 application lines; 64 test lines). This is not independently verified in the documentation lane. `[UNVERIFIED — CONFIRM BEFORE OPERATIONAL USE]`
- `OBSERVED` — fletcher says a recall view-scope question has been sent to root; this lane has not resolved it.
- `MEANS` — local engine validation, if the reported result is confirmed, does not establish hosted runtime, authentication, Sites storage, publishing, or cross-client behavior.
- `DO` — keep hosted and real-client acceptance open; align the map to the new test file.

### 2026-10-31 | CHECKPOINT | recall-scope-and-test-update

- `OBSERVED` — inspection of `src/core/workspace.ts` confirms distinct predicates for `today`, `session`, `since_last`, and `detours`; `thread` filtering is conditional on `input.thread`; `project`, `handle`, and default `now` have no separate base predicate.
- `OPEN` — this does not match the full enum/scope contract described in SPEC §8.3. Root has been notified; keep `recall-view-scope` open until implementation or contract is reconciled.
- `SMELL` — prod_finalizer reports a later `npm test` run with nine passing SQLite tests, typecheck, and line budget (254 source lines; 103 test lines); ULID is now a runtime dependency. Not independently verified in this documentation lane. `[UNVERIFIED — CONFIRM BEFORE OPERATIONAL USE]`
- `MEANS` — reported local tests do not establish hosted runtime, authentication, publishing, or cross-client behavior.

### 2026-10-31 | CHECKPOINT | mcp-dispatcher-landed

- `OBSERVED` — `src/mcp/server.ts` is now present with four tool schemas, argument validation, `callTool` dispatch, and JSON-RPC routing.
- `OBSERVED` — no test file for the MCP dispatcher or hosted entry was present at the check; hosted entry and real-client behavior remain unverified.
- `MEANS` — the earlier reported `npm test` result predates this file and does not establish its behavior.
- `DO` — keep TASK acceptance for MCP calls, hosting, and cross-client use open until validated.

### 2026-10-31 | CHECKPOINT | recall-contract-resolved-and-mcp-rpc-tests

- `OBSERVED` — root clarified that `project` and default `now` intentionally use a broad project scope; `now` adds route ancestry, open strands, and unanswered questions. `thread` uses the active thread when no thread is named; `handle` requires `about`.
- `OBSERVED` — the corresponding view semantics are now explicit in SPEC §8.3. The previous `recall-view-scope` concern is resolved as a design clarification.
- `SMELL` — prod_finalizer reports eleven passing tests, including in-process MCP RPC discovery/list/call and validation/error paths, plus typecheck and line budget. Not independently run in this documentation lane; live transport and client integration are untested. `[UNVERIFIED — CONFIRM BEFORE OPERATIONAL USE]`
- `OBSERVED` — direct `SQLiteDatabase.all`/`run` calls bypass the transaction callback queue; `Workspace` currently invokes operations inside transaction callbacks. Bounded hazard recorded in CONTEXT.

### 2026-10-31 | CHECKPOINT | local-stdio-harness-landed

- `OBSERVED` — `src/local/stdio.ts` now reads one JSON-RPC request per stdin line, writes responses to stdout, opens the SQLite database from argv (default `:memory:`), and applies the migration on first open.
- `UNKNOWN` — no manual client session across the process boundary has been reported; the P1 stdio acceptance item remains open.
- `OPEN` — TASK P1 specifies `@modelcontextprotocol/sdk`; current `stdio.ts` uses the project's internal JSON-RPC router. Root has been asked whether that dependency requirement is intentionally superseded.

### 2026-10-31 | CHECKPOINT | subprocess-stdio-check-reported

- `OBSERVED` — root reports a subprocess JSONL MCP check passed `tools/list`, write, process restart using the same disk-backed SQLite file, then open/query of the saved marker.
- `MEANS` — this covers the current custom JSON-RPC-over-stdio development harness across process restart. It does not satisfy the still-open SDK-backed local product item or prove ChatGPT Sites deployment/client sharing.
- `OBSERVED` — root directs that P0 remains unchecked because no hosted Site has been created; the current delivery is partial P0 groundwork.

### 2026-10-31 | CHECKPOINT | sqlite-serialization-limitation-resolved

- `OBSERVED` — root reports SQLite direct-query bypass is fixed through AsyncLocalStorage transaction-scope serialization.
- `OBSERVED` — root reports Terra's deterministic commit/rollback regression and the final 12-test suite pass (356 application lines; 150 test lines).
- `CORRECTION` — the earlier `sqlite-direct-access` hazard in `CONTEXT.md` is resolved and removed from current hazards.
- `UNKNOWN` — this documentation lane did not independently run the test suite; these results are attributed to root.

## 2026-10-31 | Codex | P0 deployment sequencing hold | OPEN

- **Operator direction:** hold all deployment this turn. Do not create/configure a Site, provision deployed D1, publish, or install the plugin.
- **Resume condition:** application code, host adapter, MCP layer, migrations, and plugin package are locally ready.
- **Approval boundary:** this is a sequencing hold only; the operator did not add a separate approval gate after readiness.
- **Current work:** continue local implementation and validation. Root is investigating D1 adapter atomicity/read-your-writes behavior; no confirmed finding has been received by this documentation lane yet.
- **Docs updated:** `CONTEXT.md`, `TASK.md`, and the builder skill now route around deployment until readiness.

### 2026-10-31 | CHECKPOINT | local-readiness-validation-and-reentry

- `OBSERVED` — root reports commit `1ce67b2` contains source, tests, build packaging, and filetree; documentation changes remain separate.
- `OBSERVED` — root reran `npm test`: all 13 passed, including Workerd D1 and HTTP tests; typecheck and line budget passed at 457 application / 234 test lines.
- `OBSERVED` — root reports clean `npm pack` installation with `--omit=dev` outside the repo, and two compiled stdio processes persisted/recalled data across restart with numbered migrations.
- `MEANS` — this is local validation only. Cloud D1/Sites behavior, deployment, and ChatGPT/Codex integration remain unverified.
- `OBSERVED` — usage and curator skills now distinguish the current four tools from planned P3 `workspace_link` and `workspace_curate`; P0 migration, four-tool schema, and P1 line-budget checks are marked complete in TASK.
- `PRESERVE` — deployment remains held this turn. Re-entry: `1ce67b2` → `TASK.md` current gate → complete any local readiness work; do not create/publish a Site this turn.

## 2026-10-31 | Codex | deployment hold lifted | OPEN

- **Operator directive:** the previous deployment hold is explicitly lifted. Finish the hosted side, deploy the canonical Site plugin, let the operator test it, and push all source to `main`.
- **Ownership:** root owns Site creation/publication and the live deployment route; this lane keeps repository navigation and handoff docs accurate.
- **Source/artifact split:** `src/hosted/` remains the server implementation. `site/` is planned for the deployment bridge; `plugin/` is planned for plugin instructions and metadata. Neither directory is present in the live tree at this checkpoint.
- **Evidence boundary:** deployment is authorized but not yet recorded as completed. D1 Workerd/HTTP results are local evidence only; cloud identity, transport, storage, publication, and client behavior remain to be observed.
- **Re-entry:** [TASK.md](TASK.md) P0 → root deployment messages → update `CONTEXT.md` and `filetree.md` as `site/` and `plugin/` artifacts land.

### 2026-10-31 | CHECKPOINT | sites-scaffold-created

- `OBSERVED` — `site/` now exists with a Vinext/Cloudflare scaffold, local auth helper, Worker entry, D1/schema scaffolding, and install/build/preview scripts. `site/app/page.tsx` is still a generic starter placeholder; this lane has not observed a connection to `src/hosted/` or a deployment.
- `OBSERVED` — `plugin/` does not exist at this checkpoint; it remains planned for instructions and metadata.
- `OBSERVED` — current scaffold includes `site/.openai/hosting.json`, `site/drizzle/0000_workspace.sql`, and `site/pnpm-lock.yaml`; these are scaffold assets, not proof of a deployed or source-wired MCP plugin.
- `OBSERVED` — README and filetree now route to `site/`; builder guide distinguishes the Site scaffold from the hosted server source.
- `PRESERVE` — deployment is authorized and root-owned; document the actual canonical Site/plugin, live test route, and push only when root reports them.

### 2026-10-31 | CHECKPOINT | d1-and-hosted-source-landed

- `OBSERVED` — new files are present: `src/store/d1.ts`, `src/store/migrations/0002.sql`, `src/hosted/index.ts`, `scripts/build.mjs`, `tsconfig.build.json`, and `test/d1.test.ts`.
- `OBSERVED` — D1 adapter contract: reads use the transaction snapshot; writes are staged into a revision-guarded batch, and retry is limited to the named guard conflict. Core operations must not rely on reading queued writes from the same callback.
- `OBSERVED` — hosted source gates `/mcp` on configured owner ID, requires the matching identity header, accepts POST JSON, and bounds the body. Sites behavior and identity forwarding remain unverified because no deployment occurred.
- `UNKNOWN` — D1 test execution is pending Terra. No D1 atomicity result is claimed yet.
- `OBSERVED` — build config compiles source only and copies migrations to `dist`; local stdio now applies numbered migrations.
- `PRESERVE` — deployment hold remains active until all named local-readiness conditions are met; no Site setup or publication this turn.


## 2026-10-31 — Published ChatGPT testing release (root)

- User explicitly authorized publication after the prior deployment hold. Sites deployment `appgdep_6ae662c153f481918c6aa28f86909e99` succeeded with MCP enabled, environment revision 1, and source commit `0c1527ced06a2681d3adc0d957818e624c06b952`. Durable connection identifiers are in `plugin/connection.json`; credentials are not stored.
- Canonical Site plugin was already installed. Plugin Creator updated it to 1.0.1 and read-back verified both usage and curator skills with the existing App binding preserved. No duplicate plugin was created.
- Local exact hosted migration, HTTP checks, and core suite pass (13 tests). A service-access live HTTP probe returned 401 at dispatch. Current chat has no workspace tools in its registry. Do not claim a live note write/recall or cross-chat continuity test; the next fresh chat with the plugin selected is the real user acceptance test.
- Canonical source is GitHub `main`. New agents should clone with `--branch main`; use root AGENTS, CONTEXT, TASK, and site/README. Sites has a separate source mirror: open it with the supported helper and overlay canonical source rather than merging/force-pushing histories. Hosting cost remains unobserved.

## 2026-11-01 | Codex | P3 full-visibility documentation | OPEN

- **Assigned lane:** docs only. Create `WORKSPACE_CONTRACT.md` and compact `docs/CUSTOM_INSTRUCTIONS.md`; update `AGENTS.md` pointers and root/plugin usage and curator skills. Root owns the list/get/export backend, MCP/App UI, deployment, and source mirror.
- **Goal:** active use flow is open → recall → inspect/list/get → note → revisit. Distinguish operator-provided excerpts, assistant-authored working notes, and derived summaries. Preserve faithful context and narrative movement; avoid flattened/caveman summaries. Do not add fact-checking or verification policing.
- **Starting evidence from root:** live status tool returned 44 notes, 23 threads, last write `2026-11-01T03:20:21.457Z` before this root session. No fresh acceptance behavior claimed by this docs lane.
- **Constraints:** do not suggest ChatGPT auto-reads `AGENTS.md`; compact custom instructions must be explicitly installed/applied. No separate skill product requested. GitHub default branch was `master`; root is synchronizing existing history to new canonical `main` for clone compatibility.
- **Role/tool note:** read the uploaded `defense-grade-doc-engine (3).md`. It specifies Surgeon/Colony calls unavailable in this session; continue with available documentation edit tooling without claiming those calls. Keep claims source-backed and unknowns explicit.
- **Re-entry:** [WORKSPACE_CONTRACT.md](WORKSPACE_CONTRACT.md), [docs/CUSTOM_INSTRUCTIONS.md](docs/CUSTOM_INSTRUCTIONS.md), then usage/curator skills and root `AGENTS.md` / `TASK.md`.

### 2026-11-01 | P3 documentation pass | IN PROGRESS

- `WORKSPACE_CONTRACT.md` defines excerpt/source, assistant note, and derived summary handling; faithful context and the open → recall → inspect → note → revisit → export workflow; and the no-verification boundary.
- `docs/CUSTOM_INSTRUCTIONS.md` is a compact user-applied ChatGPT prompt. It explicitly says this repository and `AGENTS.md` are not auto-loaded.
- Root and plugin usage/curator skill copies now describe the source-level eight-tool schema and use `workspace_list`, `workspace_get`, `workspace_export`, and `workspace_app` only when advertised. `workspace_note.sources` stores excerpts separately.
- Source inspection confirms native resource `ui://cognitive-workspace/inspector`, `/operator`, `/api/workspace`, and `/exports/:id/download`. These are local source facts; the current deployed plugin may lag.
- `prod_finalizer` reports 15 local tests, typecheck, and line budget pass, including RPC/HTTP coverage. No real MCP host rendering or upgraded plugin-release verification is recorded. This docs lane ran no tests and used no native Site/Plugin APIs.
- **Next:** root validates and deploys the P3 release; update exact status after reports. Operator cross-chat acceptance remains separate. Do not create a separate skill product.

### 2026-11-01 | P3 docs sync | PREPUBLICATION FREEZE

- `OBSERVED (root report)` — 16 tests pass, typecheck and handwritten line budget pass, and hosted build succeeds. Reported coverage includes >1 MB export, Unicode/fence behavior, original-hash preservation, D1 concurrent guard retry, all eight tools/resource, authentication, and download.
- `OBSERVED (root report)` — source build/dev wrappers now sync root `src/` into ignored `site/workspace-generated/`; Site package declares `ulid` directly. Source map now includes inspector UI, inspection core, migration 0003, Sites catch-all/connector helper/dev wrapper, package and sync scripts, docs utility, and local plugin contract.
- `OBSERVED (root report)` — browser preview reached `/operator` but got 403 without owner identity. This is not a visual rendering or native MCP host verification. The deployed release is still plugin v1.0.1; local 1.1.0 candidate is not published. Root owns publication and will append exact outcome identifiers.
- `PRESERVE` — Activity records explicit invoked reads/writes and filing receipts, not passive conversation capture. Pagination `remaining` excludes the returned page; cursor ceiling excludes later appends but does not freeze mutable fields. Export is an immutable snapshot.
- `DO` — documentation is synced and frozen for the source helper. Do not claim upgraded release, live tool registry, cross-chat recovery, or host rendering until root reports direct evidence.

### 2026-11-01 | P3 root acceptance and publication | COMPLETE WITH CLIENT LIMITS

- Corrects the prepublication freeze above: same private Site now runs P3. Final source `905afadf071c439e7398a186780b2da4e9c4299b`, deployment `appgdep_6ae6bcf6b2508191b8bd6ee1aa613d18`, version `appgprj_6ae661d0968081918d8c386d729f1c8c~appgver_024f22cf04d48191a14930ba99e5fb41`; native status succeeded with MCP enabled and env revision 1. Existing project, D1 binding, private audience and authentication retained. Migrations are additive; no source records rewritten/deleted.
- Canonical installed plugin updated to v1.1.0, release `pluginrel_6ae6bb003ae081919df592906c550291`. Readback confirms manifest, WORKSPACE_CONTRACT and both skills; App binding retained. Runtime core remains shared; site/ and plugin/ are authored components in canonical GitHub main.
- Root independently ran all 16 tests, typecheck, line budget (668 application/363 test lines) and hosted build successfully after final patch. Cases cover original tools, exact/idless inspection, Unicode/code fences/BLOBs, >1MB export, count manifests, source hashes, authentication, immutable repeat downloads, pagination and concurrent D1 transaction guard retry.
- Export v2 retains note text in complete JSON metadata as well as literal Markdown text, making trailing newlines recoverable; v1 downloads retain their old bytes. Authenticated downloadable artifact is materialized server-side in the existing database. Excluded tables are explicit in its manifest.
- Browser test used an isolated synthetic MCP host fixture with no real research data: timeline, exact inspector, thread navigation, graph and export controls exercised. Fixture removed before packaging. This does not prove native ChatGPT App rendering. Unauthenticated /operator correctly returned 403. Signed-in cloud browser required login and was not bypassed.
- The running chat registry still exposes the original four tools; upgraded live App/export interactions and cross-chat recovery require a fresh client registry. No fabricated acceptance claim. Live status is checked separately after publication; root wrote no research notes.
- GitHub default branch was master at an old specification-only commit, causing incomplete normal clones. Root will fast-forward that existing branch to the canonical main snapshot without force; development remains main. Future source pushes use expected-head leases. Cached/generated output, credentials and runtime records remain excluded.

- Post-deployment live status returned 47 notes, 26 threads and lastWrite `2026-11-01T03:50:34.459Z`, matching the predeployment status. This is availability/count evidence, not a per-note live hash audit.

- GitHub main and existing default master were fast-forwarded to the same P3 snapshot; remote tree matched local exactly, including executable helper permissions. README now maps editable components and corrects the historical six-tool design list to the implemented eight-tool surface.
