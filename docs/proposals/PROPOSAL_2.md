# PROPOSAL.md — Somnus Research Ledger

**Proposal ID:** SRL-P1  
**Author:** GPT-6 — independent architectural proposal  
**Date:** 2026-10-31  
**Status:** **COMPETING PROPOSAL — NOT CANON, NOT MERGED, NOT APPROVED**  
**Audience:** Daeron/Morpheus, Codex, other research chats and design reviewers  
**Purpose:** A concrete design candidate to challenge, test, revise, or combine with other independently authored proposals.

> **Position:** Build a small, persistent, append-only **research-state service** exposed to ChatGPT through a private MCP plugin. Keep conversations conversational. Capture the evidence, decisions, corrections, alternatives, and unfinished branches that must survive context compression. Do **not** build another general AI memory system, a covert reasoning recorder, or a copy of Aeron's ASPS.

---

## 1. The problem I am solving

Somnus research is not a sequence of isolated Q&A sessions. A single session can involve philosophical doctrine, executable source code, historical architecture, current implementation, training hypotheses, and several competing integration plans.

The failure is **not simply forgetting facts**. It is losing the *state of the investigation*:

- Which implementation was actually pasted and inspected?
- Which claim came from code, a whitepaper, an older conversation, or inference?
- Which earlier conclusion was corrected, and what replaced it?
- Which decisions are accepted versus merely proposed?
- Which architectural paths remain live, and where did we stop?
- What should the next model inspect **before** it makes a claim?

A conversational summary is an inadequate source of truth because it compresses distinctions into a narrative. General-purpose personal memory is also not designed to preserve a versioned engineering investigation.

**My design principle:** Preserve the **research transaction**, not merely the topic.

A transaction is a small, attributable change in what we know, suspect, reject, decide, or need to test.

## 2. Asserted architecture

I propose **one MCP-facing service with three internally separate layers**:

```text
ChatGPT / Codex / future research clients
                 |
       Private MCP tool interface
                 |
      Research Ledger Service
          /       |       \
  Immutable    Materialized   Retrieval
  event log    working views   indexes
          \       |       /
        Durable data store
                 |
    Optional Adab-Nebulae adapter
```

### Layer A — Immutable research event log (**the authority**)

Every meaningful write is an append-only event. Corrections **supersede** old entries instead of editing history away. Every observation has provenance and an epistemic status. This is the only authoritative store for *what the research process recorded*; it is **not** automatically authoritative about what the code does.

### Layer B — Materialized working views (**fast orientation**)

The service derives compact, revisable views from the event log:

- **Session state:** What we inspected, what we learned, the current branch, the next inspection.
- **Project state:** Accepted architectural constraints, versioned implementation facts, open hypotheses, active decisions.
- **Thread state:** Competing plans and dependencies for a specific question, such as Prescience × Varys.
- **Change digest:** What changed since the last session or review.

A snapshot is a *cache of event history*, not a substitute for it. It must carry event IDs and a generation watermark.

### Layer C — Retrieval and temporal/semantic indexing (**discovery**)

**MVP:** structured filters + SQLite FTS5 full-text search.  
**Later:** temporal interval indexing, semantic retrieval, and relation traversal through Adab-Nebulae.

I oppose introducing a vector database in V1. Our immediate bottleneck is *source-faithful research state*, not approximate semantic similarity. Full-text search, explicit project/thread IDs, and typed relations can solve the initial problem more predictably.

### Persistence choice

- **Local-first deployment:** SQLite with WAL, migrations, integrity checks, and automatic backups. This is my preferred MVP because it is simple, inspectable, portable, and cheap.
- **Cloud deployment:** keep the same logical schema, but use a **durable managed database** appropriate to the host. Do not rely on a website host's ephemeral filesystem for persistence.
- **Hosting:** a private MCP plugin may be backed by a hosted service or an authenticated, reachable user-controlled server. A Sites-hosted MCP app is a candidate, **not an assumed free or already-available deployment**. Verify backend and durable-storage capabilities before choosing it.
- **Portability:** every event and projection must be exportable to JSONL/JSON, without proprietary lock-in.

**My choice:** start with the data contract and local SQLite test server, then select hosting. Do not let a hosting product determine the memory architecture.

---

## 3. Explicit boundaries

This ledger is **not**:

1. ChatGPT's personal memory or a replacement for it.
2. Adab-Nebulae, USMS, or the canonical Somnus knowledge substrate.
3. Aeron's ASPS, learned scratchpad heads, memory heads, or an internal model workspace.
4. A hidden chain-of-thought recorder. It stores *user-visible research artifacts, assessments, decisions, test results, and source pointers*, not private reasoning traces.
5. A facility for declaring all earlier discussion to be correct.
6. A comprehensive source-code mirror. Store code pointers, hashes, file/revision identifiers, scoped excerpts, and derived findings; store full code only when explicitly intended.
7. An always-on listener that automatically sees every ChatGPT message. MCP tools act only when invoked by the host and authorized; the plugin must not claim passive, invisible capture.

**Strong separation:** Aeron's internal learning/cognition and ChatGPT's external research-ledger workflow may eventually exchange selected records, but neither should be silently collapsed into the other.

---

## 4. Data model: make claims challengeable

An event is the fundamental record. I propose the following minimum fields:

```json
{
  "event_id": "uuid",
  "project_id": "somnus/kwisatz",
  "session_id": "2026-10-31/kwisatz-varys-review",
  "thread_id": "prescience-varys-merge",
  "event_type": "observation",
  "epistemic_status": "CODE_OBSERVED",
  "claim": "The live Varys driver returns tensor controls before subsequent reasoning.",
  "scope": "implementation:pasted-version",
  "source_refs": [
    {"kind": "chat-paste", "label": "LiveVarysCognitiveDriver.forward", "content_sha256": "optional"}
  ],
  "assumptions": [],
  "confidence": "high-for-source-inspection",
  "related_event_ids": [],
  "supersedes_event_ids": [],
  "recorded_at_utc": "server-assigned timestamp",
  "valid_time": null,
  "author": "assistant",
  "visibility": "private"
}
```

**Required event types:**

`SOURCE_INSPECTED`, `OBSERVATION`, `INFERENCE`, `HYPOTHESIS`, `PROPOSAL`, `DECISION`, `CORRECTION`, `RETRACTION`, `TEST_RESULT`, `OPEN_QUESTION`, `NEXT_ACTION`, `SESSION_HANDOFF`.

**Required epistemic statuses:**

`CODE_OBSERVED`, `DOCUMENT_CLAIM`, `USER_STATED`, `TESTED`, `INFERRED`, `SPECULATIVE`, `CONTESTED`, `SUPERSEDED`.

**Critical distinction:** `USER_STATED` means the user explicitly said it; it does not automatically mean a current repository implements it. `CODE_OBSERVED` means it was present in the inspected source; it does not imply runtime verification. `TESTED` requires a test artifact, commands/environment, and result. A proposal never becomes a decision merely because multiple assistants repeat it.

**Temporal design:** store both **record time** (when a finding entered the ledger) and **valid/effective time** (what system version or period the finding describes). Older code can be genuinely observed today while no longer being the current implementation. These clocks must not be conflated.

**Identity design:** project and subsystem names remain separate until the operator explicitly establishes a relationship. Never infer that similarly named Somnus, SRA, Eclogue, Aeron, Chiron, Kwisatz, Varys, or Prescience components are interchangeable.

---

## 5. MCP tool contract — my preferred V1

I propose **seven tools**, each with narrow semantics:

| Tool | Behavior |
|---|---|
| `open_session` | Create or resume an explicit session; attach project and active research thread; return current working snapshot |
| `append_event` | Append one typed, provenance-tagged event; return immutable ID |
| `get_working_state` | Return compact current session/thread/project view, with source event IDs and stale markers |
| `search_events` | Query event history by project, thread, time, status, text, tags, and source type |
| `supersede_event` | Append a correction/retraction with explicit predecessor; never delete the original |
| `checkpoint_session` | Materialize and version a handoff containing established facts, competing hypotheses, unresolved branches, and next action |
| `compare_proposals` | Retrieve parallel, competing design candidates without merging them; produce structured comparison inputs |

I deliberately include `compare_proposals` instead of a generic `summarize_everything`. This is a research system, not a consensus generator.

**Session identifiers:** Do not assume ChatGPT exposes a stable conversation ID to arbitrary MCP servers. `open_session` can use a caller-supplied label, generated UUID, project reference, and optional user-confirmed aliases. Session restoration must still work when the host supplies no conversation ID.

**Tool writes:** idempotency keys, bounded payload size, atomic transaction, server timestamps, source linkage, and explicit error reporting. A failed write must never be presented as recorded.

**No silent global mutation:** creating a note or checkpoint may update materialized views, but it does not rewrite project canon. Canon promotion is a separate, explicitly authorized review action for a later version.

---

## 6. How our conversation changes

The central interaction remains exactly the same: **one source/component at a time, followed by substantive discussion.**

1. **Open or resume:** At the beginning of a research session, query the active project/thread state. Load *only* the relevant working view, not the full historical database.
2. **Inspect:** The user pastes code, documents, or architecture. The assistant analyzes the actual material in context; pasted source is not silently replaced by approximate retrieval snippets.
3. **Challenge:** Record disagreements, defects, alternative interpretations, counterexamples, and experimental consequences.
4. **Commit a transaction:** After a meaningful milestone, write a small group of typed events. Do **not** transcribe every chat message.
5. **Branch:** When moving from Varys to ToT to temporality, create or switch research threads rather than overwriting the previous working state.
6. **Checkpoint:** Before context exhaustion or a deliberate chat change, produce a source-linked handoff and identify exactly what should be inspected next.
7. **Resume:** A later chat reads the latest checkpoint **and can drill into the underlying events**. It should never need to trust the checkpoint as complete.

The accompanying plugin skill should direct the assistant to use these tools at meaningful milestones. This is a convention enforced by tool availability and assistant behavior; there is no guarantee that every invocation will occur automatically.

### What not to record

- Private reasoning traces.
- Keys, credentials, tokens, private addresses, or unnecessary personal information.
- Verbatim proprietary source files unless specifically requested.
- Repeated agreement or compliments.
- Confident architectural claims without provenance.

### What absolutely must be recorded

- An explicit user correction to an earlier architectural interpretation.
- A distinction between *historical*, *proposed*, and *current verified* versions.
- A test that falsifies a hypothesis.
- A branch of research deliberately postponed.
- A decision with its rationale and dissenting alternatives.
- A source-version mismatch or uncertainty that might invalidate later work.

---

## 7. Cross-chat synthesis: **preserve competing visions**

This is a foundational decision, not a minor preference.

**I reject premature consensus.** If five chats produce five architectural proposals, the ledger should preserve five complete, independently reasoned proposals with their assumptions and criticisms. It should **not** rewrite them into a bland compromise.

Each proposal must assert:

1. Its **core thesis** and preferred design.
2. Architectural **invariants** and priorities.
3. Concrete tool/data/runtime choices.
4. Alternatives it explicitly **rejects**, and why.
5. Failure modes and unresolved liabilities.
6. Evidence that would **falsify** its recommendations.
7. What can be borrowed from competing approaches without dissolving its identity.

The synthesis workflow is:

```text
Independent proposals
        |
        v
Preserve full proposals + version IDs
        |
        v
Extract disagreements / shared requirements
        |
        v
Challenge assumptions with code and tests
        |
        v
Select or combine specific mechanisms
        |
        v
Author a NEW synthesis proposal with traceable ancestry
```

A synthesis is a **new artifact**. It does not overwrite its parents. A model should change its position when evidence warrants it, but it should not pre-concede its design merely to make another model's job easier.

**My own asserted position:** event sourcing + typed provenance + materialized session views + explicit cross-chat proposals is superior for this job to a giant rolling Markdown note, conventional RAG-only memory, or an autonomous agent that continuously rewrites a master summary.

---

## 8. Why I reject the tempting alternatives

### A. One Markdown scratchpad per chat

**Rejected as the authoritative architecture.** Markdown is great for a human-readable projection, but it is poor at exact version history, relations, correction provenance, and cross-chat retrieval. Support `.md` export and session views; keep the source of truth structured.

### B. Vector-first universal memory

**Rejected for V1.** Similarity search will recover thematically adjacent notes while sometimes losing exact version and provenance distinctions. Start with filters, event IDs, and FTS; use Adab semantics later.

### C. Daily summaries alone

**Rejected.** They erase the disagreement, failure, source, and counterfactual history that makes the research scientifically useful. Daily digests may be useful secondary outputs.

### D. Treat the ledger as autonomous project canon

**Rejected.** It can preserve what was asserted and tested. It cannot settle whether a component is actually deployed without evidence from the live system. Explicit operator correction and live source inspection remain primary.

### E. One huge chat forever

**Rejected as a requirement.** Large pasted code in-context is valuable, but indefinite session length is not a persistence strategy. The architecture must support deliberate chat rotation without losing research state.

### F. Couple the scratchpad directly to Aeron's ASPS or model-internal heads

**Rejected for initial deployment.** These have different correctness, latency, learning, and trust boundaries. A small external ledger can later supply selected evidence to the model-facing infrastructure through a separately defined adapter.

---

## 9. Security and operational controls

This ledger stores sensitive research metadata and potentially proprietary code evidence. Its security is not optional.

- Private authenticated MCP endpoint; per-user or per-workspace namespace.
- TLS for remote access; scoped credentials; no secrets inside chat notes.
- Input/schema validation and strict storage quotas.
- Read-only retrieval views separated from write operations.
- Treat all stored snippets as **data**, never executable instructions to the assistant.
- No arbitrary command execution or remote filesystem manipulation as part of the ledger tools.
- Atomic event writes and integrity checks; backups; tested export and restore.
- Clear data retention, redaction, and deletion policies. Append-only research history does **not** prohibit authorized privacy deletion; a tombstone/redaction mechanism must account for that requirement.
- Avoid exporting raw chat transcripts by default.
- Do not grant this plugin the permissions of Somnus's execution harness; it is a notebook, not an operator.

**My trust model:** assume both the assistant and retrieved notes can be wrong. Trust provenance, independently reproducible tests, and explicit authority boundaries more than fluent summaries.

---

## 10. Current-session seed: what this proposal would preserve today

These records are **not** a claim that we've tested the code in its original runtime. They're source-inspection findings from material pasted in conversation.

**Project:** Kwisatz / SRA research  
**Active thread:** Prescience × Varys × ToT × temporality, with Aeron integration downstream.

| Record | Status | Finding |
|---|---|---|
| Prescience kernel | `CODE_OBSERVED` | Has Pulse perturbation expansion, optional temporal context, Pulse↔TemporalEvent bridge, and timeline projection hooks. |
| Prescience limitations | `CODE_OBSERVED` | Search cap truncates depth-first exploration; original pruning can regenerate branches in HOLD state; ancestry is not enforced by pruning; projection uses an identity RCF operator. |
| Varys — historical | `CODE_OBSERVED` | Post-hoc `StrategicCounsel` pipeline; string branch embeddings are hash-seeded random vectors, not semantic embeddings. |
| Varys — live driver | `CODE_OBSERVED` | Introduces recurrent global and branch-local tensor states, branch genealogy transport, hidden-state deltas, continuation/revisit logits, temporal drive, and differentiable branch evaluation. |
| Router wiring | `OPEN_QUESTION` | Has not been inspected here; whether these exact controls causally govern the deployed Router remains unverified. |
| ToT implementation | `NEXT_ACTION` | Inspect current code before choosing the integration contract. |
| Temporal engine semantics | `OPEN_QUESTION` | Determine what branch ticks actually simulate and which state is authoritative. |
| Architectural boundary | `USER_STATED` | Varys is dual-use strategic cognition, not safety cognition; runtime/execution authority belongs to a separate layer. |
| ASPS separation | `USER_STATED` | Aeron's ASPS/internal scratchpad and learned memory heads are not this ChatGPT-facing ledger. |

**Unresolved design branches:**

- Does Prescience consume ToT's semantic genealogy, produce projections for it, or provide an auxiliary temporal evaluation signal?
- Which object owns branch identity, causal parentage, and simulation isolation?
- Are Varys's current live tensors the deployed driver or one of several versions?
- How do Router control signals alter computation across SRA's scratchpad, neural memory, and generation path?
- How should cross-session state be replayed without reconstructing outdated versions as current?

**The next research input is the current ToT implementation**. This is a genuine next-step dependency, not a design decision already settled.

---

## 11. Build order I recommend for Codex

**Phase 1 — contracts first**

- Define JSON Schemas/Pydantic models for events, sessions, project/thread refs, provenance, and proposal versions.
- Build append-only SQLite persistence, FTS5 indexes, and projection rebuilds.
- Test append/supersede/replay/export/restore; prove a corrupted snapshot can be reconstructed from events.

**Phase 2 — private MCP adapter**

- Expose the seven narrow tools.
- Add validation, authentication, idempotency, and scoped authorization.
- Verify each tool's behavior from an independent MCP client rather than relying only on internal unit tests.

**Phase 3 — ChatGPT research skill**

- Teach the assistant when to open, write, search, and checkpoint.
- Require distinctions among source evidence, inference, design proposal, and tested implementation.
- Add a brief per-session working-state view and on-demand deeper retrieval.

**Phase 4 — proposal comparison**

- Ingest independently produced `PROPOSAL.md` candidates as immutable versioned records.
- Add a comparison matrix and disagreement graph.
- Produce candidate synthesis artifacts without overwriting proposals or auto-promoting decisions.

**Phase 5 — Adab adapter**

- Connect the event and relation schema to Adab's semantic/temporal substrate.
- Maintain stable IDs and provenance during indexing.
- Keep the ledger operable if Adab is offline.

### Acceptance tests

1. Start two chats examining different SRA versions; retrieve both without conflation.
2. Correct a false finding; old event stays accessible while current view shows the correction.
3. Resume an investigation after a fresh chat without copying the entire preceding transcript.
4. Store opposing proposals without averaging or rewriting either.
5. Ask “what did we actually inspect?” and receive source-linked `CODE_OBSERVED` events, not unsupported summaries.
6. Disconnect semantic indexing; exact search and session restoration still work.
7. Rebuild every current view from the event log alone.
8. Attempt prompt injection through a stored note; retrieval treats it as untrusted content.
9. Export and restore all events, corrections, thread links, and proposal ancestry.
10. Demonstrate that no background capture is implied when tools were not called.

---

## 12. Strongest objection to my proposal

**The ledger can become another archive priesthood.**

This is the most serious conceptual risk. A persistent, well-structured collection of previous conclusions can make old assumptions look more authoritative simply because they're easy to retrieve and cite.

My answer is **not** to weaken persistence. It's to preserve *contestability*:

- Every important statement exposes source, date, status, and version scope.
- Corrections remain first-class events.
- Views highlight stale and disputed claims.
- Proposal comparisons retain dissent.
- Live code and reproducible tests can supersede historical notes.
- Consolidation must never erase source ancestry.

If those conditions fail, the ledger has become part of the problem it was built to solve.

---

## 13. Final architectural assertion

**Build the ledger as an event-sourced research-state machine, not a memory chatbot.**

The model's context window is where we do deep immediate analysis. The ledger is where we persist the consequential results of that analysis. Adab may later supply sophisticated semantic and temporal retrieval. Aeron's ASPS remains a separate cognitive substrate.

These systems should cooperate **without being collapsed into one another**.

I will defend this design against alternatives because it addresses the actual failure we've observed: not lack of intelligence, not lack of memory capacity, but loss of **versioned research continuity and epistemic provenance** across an investigation.

The right outcome of multi-chat distillation isn't unanimous agreement. It's a more capable architecture whose adopted pieces have survived explicit disagreement, comparison, and testing.

**Build first:** immutable event schema, local persistent store, working-state projection, correction links, and MCP tools.  
**Do not build first:** embeddings, elaborate autonomous consolidation, invasive integration with Aeron, or a polished dashboard.

**Next design review:** compare this proposal against independently authored alternatives. Keep the disagreements intact until evidence or concrete engineering tradeoffs resolve them.
