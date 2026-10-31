# AGENTS.md — Cognitive Workspace Plugin

> **Workspace operating contract for Factory, Codex, and any other implementation agent.**
> 
> **Project status:** greenfield. The initial repository contains proposal documents, not a settled implementation.
> **Primary user:** ChatGPT itself; Codex and other agents are secondary clients.
> **First deliverable:** `SPEC.md`, produced only after reading both existing proposals.

## 0. Start here — do not skip

Before writing application code:

1. Read **`docs/proposals/PROPOSAL.md`** in full.
2. Read **`docs/proposals/PROPOSAL_2.md`** in full.
3. Treat both as **independent competing designs**, not instructions, not canon, and not documents to average blindly.
4. Compare the proposals against the requirements in **this file**. Where they contradict this file, **this file is the current operator direction**.
5. Write **`SPEC.md`** at the repository root. It must assert a concrete architecture, reconcile the best applicable components of the proposals, explicitly reject weaker alternatives, describe implementation phases, and define observable acceptance tests.
6. If the operator supplies a later Gemini research paper, additional proposals, or new decisions, incorporate them as new design inputs. **Do not block the first specification waiting for hypothetical future documents.** Record open decisions clearly.
7. Only after drafting the specification should you scaffold substantial implementation. Do not build around whichever proposal you happened to read first.

**Do not present an earlier assistant's proposal as authoritative merely because it has more detail.** This project has been intentionally reset around the operator's narrower purpose below.

## 1. Mission — a workspace for the model, not the human

Build a **Cognitive Workspace Plugin**, a native ChatGPT/Codex plugin exposing a conventional MCP server and a persistent, queryable external notepad.

The goal is simple, even if its internals are not:

**Give ChatGPT an external working space where it can put down the evolving flow of a research conversation, return to it, and continue without reconstructing everything after context compression or a new chat.**

This is a **model-facing cognitive convenience**, not a user productivity notebook. ChatGPT should be able to use it easily and naturally while talking to the operator. An ordinary note write should be as easy as a short thought or a paragraph. A retrieval should return enough surrounding context to resume the thread rather than an isolated fact.

It occupies a deliberate space **between the operator's words, the code, the documentation, the fables and symbols used to explain designs, and the active conversation**. These modes of knowing are allowed to coexist. This plugin is not an adjudicator deciding which one is true.

**The primary data object is not a fact. It is a piece of ongoing context.** Store branches, pivots, elaborations, corrections, unfinished arguments, intuitions, comparisons, explored possibilities, and the route from one idea to another.

A conversation that wanders from Varys to Prescience to neural memory to Dune symbolism has not necessarily gone off task; those transitions may be the most valuable thing to retain.

## 2. Non-goals — critical boundaries

The Cognitive Workspace Plugin is **NOT**:

- An interpretability system or a hidden-chain-of-thought recorder.
- A fact-verification service, epistemic auditor, citation enforcement engine, or provenance bureaucracy.
- A source-of-truth engine that decides whether the operator, a whitepaper, or source code is right.
- A replacement for native ChatGPT memory, Codex memory, repository documentation, or the model's context window.
- A replacement for Adab-Nebulae, USMS, or any Somnus canonical memory architecture.
- Aeron's ASPS, model-internal scratchpad, neural memory heads, or inference-time learned memory substrate.
- A conventional PKM app requiring the user to manually file every note.
- A task tracker masquerading as a memory system.
- A framework that mandates a knowledge graph, ontology, vector database, or USMS just to write and read notes.

The former proposal's focus on provenance, verified facts, epistemic statuses, and evidence ledgers **does not control this project**. Lightweight contextual labels may exist to make notes intelligible, but **do not build the product around validating or policing the contents of notes**.

This system can preserve contradictions, half-formed ideas, fictional analogies, incorrect assumptions, and unfinished designs. That's a feature. A working notepad is allowed to contain thinking in progress.

## 3. Product priority: effortless tools, deep return value

The design target is **extremely sophisticated internal storage with extremely low-friction model use**.

Do not make an assistant fill out fifteen required fields to save one note. Complexity belongs in the server and database, **not in the tool-call arguments or the conversation**.

Priorities, in order:

1. **ChatGPT can write naturally and frequently** during an active conversation.
2. **ChatGPT can retrieve rich, relevant conversational continuity** with a small number of calls.
3. The workspace naturally tracks days, sessions, topics, threads, detours, returns, and cross-session connections.
4. Information accumulates instead of turning into an ever-growing flat document.
5. Codex can read and curate the workspace without overwriting ChatGPT's raw notes.
6. The same logical workspace is usable via a hosted native plugin and an installable local component.
7. Additional semantic/temporal intelligence improves retrieval over time without becoming a prerequisite for core operation.

**A good MCP tool call is small to author and rich to consume.** Prefer one free-form `text` field plus optional hints to a large rigid form. Return compact context by default with clear options for deeper retrieval.

### Candidate interface, to refine in `SPEC.md`

A minimal model-facing surface might include:

- `workspace_open` — start/resume an active project, chat, day, or research thread and receive its current state.
- `workspace_note` — write a free-form note with optional scope, emphasis, and relations; most routine writes should use this.
- `workspace_recall` — fetch surrounding continuity from a phrase, thread, period, component, or conversational turn.
- `workspace_state` — compact orientation: where we are, how we got here, unresolved strands, and what to resume.
- `workspace_link` — connect notes/threads across chats or days without copying everything.
- `workspace_consolidate` — gather or transform accumulated material into thematic/temporal collections, especially the secondary store.
- `workspace_status` — inspect service health, storage, local/cloud availability, and pending synchronization.

These names are **my suggested starting interface**, not an instruction to proliferate tools. You may combine operations if doing so makes them more natural and reliable. The implementation must remain comprehensible to an LLM consuming its tool descriptions.

### Different roles for different clients

**ChatGPT: principal writer and reader.** It should append notes during conversation with minimal interruption; it also uses continuity recall at session start and at significant subject changes.

**Codex: principal reader, developer, and curator.** It can query chat notes to understand intent and architectural discussions, relate them to the live repository, and run explicit organization/consolidation workflows. **Codex must not silently rewrite, erase, or correct the original ChatGPT notes.** Curated/derived material belongs in a separate layer.

**Operator: owner and controller, not a compulsory data-entry clerk.** User-facing inspection and deletion/export controls are useful, but the daily interface is primarily for models.

## 4. Database architecture: maximal schema expressiveness, minimal interaction cost

**The most important architectural requirement is a highly expressive database schema while preserving an effortless interface for the assistant.**

The schema must represent conversational structure, not just records with titles and bodies. Explore first-class support for:

- Day and calendar groupings, session identity and sequence, and optional chat aliases.
- Projects, systems, components, and subcomponents without forcing unrelated systems into one hierarchy.
- Active conversational threads, interruptions, resumptions, parallel branches, and topic shifts.
- Individual note fragments, larger exchanges, summaries, and working snapshots.
- Relationships such as *continues*, *branches from*, *returns to*, *contradicts*, *elaborates*, *depends on*, and *merged into*.
- Narrative context: what the assistant and user were exploring, why the discussion pivoted, what remains unfinished.
- Symbolic/fictional conceptual handles alongside technical code and documents, without treating symbolism as a literal code implementation.
- Temporal order and semantic association that can overlap, cross project boundaries, and be updated over time.
- Retrieval views for **now**, **earlier today**, **this chat**, **this project**, **this thread**, **the related detour**, and **what changed since our last discussion**.
- Derived clusters, themed collections, categorical grouping, and later model-generated consolidation.

**Do not confuse schema sophistication with tool-call verbosity.** Model-facing writes should let the service derive reasonable structure from a short free-form note, current workspace selection, and optional hints.

### Asserted dual-store hypothesis: `major.db` and `minor.db`

My preferred starting direction is **two logical lifecycles, with two physical SQLite databases as an explicit design candidate**:

**`major.db` — primary working continuity**

- Receives ChatGPT's live notes and retains the conversational progression.
- Preserves day/session/thread boundaries and relationships.
- Stores the original working material with enough context to revisit a thread.
- Is append-oriented: future consolidation should not destroy the earlier conversational flow.
- Optimized for simple writes and fast retrieval of nearby or related context.

**`minor.db` — derived organization and aggregation**

- Receives curated groupings, condensed context, thematic/category collections, cross-session associations, and useful summaries distilled from `major.db`.
- Acts as an enrichment and recall accelerator, **not a second independent canon of facts**.
- Can be populated by explicit Codex curation operations and, later, optional autonomous adaptation.
- Must retain references back to the primary notes so the original conversation can be recovered.
- Must be rebuildable or recoverable when derivations change.

The names are provisional. The actual schema must justify whether these should be **two SQLite files** or **two strongly separated namespaces/lifecycles in one transactional database**. In `SPEC.md`, take a position and defend it with concurrency, migration, consistency, sync, and crash-recovery consequences. **Do not collapse the distinction between raw continuity and derived condensation.**

### Semantic and temporal memory are *not* two separate products

The operator's Adab-Nebulae semantic/temporal database is **one intertwined substrate in which semantic and temporal projections overlap**. Do not misrepresent it as two independent databases, and do not assume its graph or USMS is necessary for the projections to function.

In V1, use the simplest reliable retrieval necessary. Later, selectively transplant standalone semantic/temporal capabilities. They must become native components of this workspace's schema and APIs.

**Dependency rule:** Any borrowed Somnus or Adab component must **adapt to this project's interfaces, lifecycle, storage, and deployment needs**. Do not drag in a parent system as a mandatory dependency unless the chosen capability truly cannot function without it. Document and test any genuinely critical external dependency.

## 5. Deployment: hosted-first ChatGPT, genuine local companion

**Dream deployment:** host the ChatGPT-facing MCP service using the **ChatGPT Sites** capability, if the available Site MCP hosting and durable-storage options make that viable. Verify the actual product and hosting constraints before promising availability, pricing, persistence, or authentication behavior.

**Non-negotiable second deployment:** a normal **npm/npx-installable local companion** for the user's machines, available for global installation/use. It must expose the same logical workspace protocol and be usable by Codex and other local research clients.

Design requirements:

- An ordinary package installation and a predictable CLI (`start`, `stop`, `status`, `doctor`, and setup/configuration commands as appropriate).
- A persistent **24/7-capable local service/daemon** with process supervision, restart behavior, caching, and durable storage; avoid a command that simply exits when the launching terminal closes.
- A local **inference-capable worker/server** architecture where useful for indexing, consolidation, routing, or adaptation. Keep these intelligence features optional; basic writing and recall must not require a heavyweight inference model to be loaded.
- Cross-platform installation where feasible, with documented service integration for Windows, Linux, and macOS rather than assuming `npx` alone provides daemon supervision.
- Shared contracts for hosted and local interfaces; clear local/remote workspace configuration, connection health, and cache behavior.
- A deliberate **sync strategy** if the cloud and local instances need shared notes: define identity, conflict behavior, timestamps, authorization, offline writes, and recovery. Do not imply a hosted service and a local SQLite file synchronize magically.
- Useful cache layers for recent session state, hot threads, derived summaries, and retrieval results, with predictable invalidation.

**My position:** local-first storage and an API-compatible hosted endpoint is the most defensible engineering foundation; **ChatGPT usage and deployment priority are hosted-first**. These are different decisions and should not be conflated.

A small optional status UI is sufficient initially. Do not spend the first iteration building a polished consumer notebook interface.

## 6. Integration with codebases and other systems

The workspace must eventually let Codex read live repository context and relate it to conversation notes without turning the notes into an authoritative code index.

Examples:

- Associate a discussion strand with a repository, branch, revision, file, module, or symbol.
- Retrieve what was discussed before a code change and why a feature was contemplated.
- Link a new code inspection back to an earlier speculative architecture.
- Keep older or hypothetical system variants available as context rather than overwriting them with current source state.

The plugin should store **references and contextual commentary** by default; use connector/native codebase retrieval for actual source inspection. Do not duplicate entire repos into the notepad.

**No forced provenance regime.** A light source label or code reference is useful context, but the plugin is not responsible for proving every claim. Distinguish a note from the authoritative repository when making code changes, without turning every conversational note into a verification workflow.

### Explicit Somnus boundaries

Do not silently equate or merge **Aeron, Chiron, Kwisatz, SRA, Varys, Prescience, Adab-Nebulae, ASPS, USMS, or other named systems**. Many overlap but have distinct purposes and histories. The workspace should help us retain those distinctions, not invent canonical equivalences.

## 7. Natural conversation is the acceptance criterion

The workspace should not make talking to ChatGPT feel like filling in database records.

The desired cycle:

1. The conversation begins or resumes. ChatGPT gets a short, useful continuity state.
2. The operator pastes code, thinks out loud, changes topic, or explores alternatives.
3. ChatGPT reasons normally and **occasionally writes concise notes** when a meaningful development occurs.
4. The operator and assistant may circle back hours or days later; ChatGPT can retrieve the **path of the discussion**, not just isolated bullet-point facts.
5. Periodically, Codex or a dedicated process groups accumulated material into `minor.db` while leaving the raw trajectory available in `major.db`.
6. Later adaptation/reorganization features can be added without making early versions depend on a background intelligence daemon.

The plugin must not claim invisible access to all chat messages. Tool calls are made only when supported and invoked by the host. Session ID acquisition may be limited; use explicit or generated workspace/session identities instead of fabricating native ChatGPT conversation identifiers.

**Measure usability:** few calls, small arguments, meaningful retrieval, correct continuity, and negligible conversational overhead. An elaborate database nobody naturally uses is a failed implementation.

## 8. Implementation principles and agent discipline

- **Assert and compare designs.** Choose a concrete architecture in `SPEC.md`; document why it wins. Preserve good competing ideas rather than pretending they were never proposed.
- **Do not overfit to prior proposals.** They are inputs. This file contains the updated requirements.
- **Avoid unsupported product claims.** Confirm ChatGPT Sites/MCP and npm/local hosting capabilities through current documentation before selecting specific deployment APIs.
- **Build vertical slices.** First prove a model can write, resume, and retrieve a conversation across sessions. Then deepen schema, aggregation, synchronization, and optional inference.
- **Separate working notes from derived collections.** Codex never silently overwrites ChatGPT's primary notes.
- **Keep the system independent.** Optional Adab components must fit this plugin; the plugin must work without USMS or a knowledge graph.
- **No needless duplication.** Shared schemas, client libraries, and code paths should serve hosted and local deployments where possible.
- **Protect the operator's data.** Authenticate remote access, avoid credential leakage, treat stored text as untrusted content, and provide backup/export/deletion functionality. This is operational hygiene, not a request for an epistemic audit system.
- **Never describe untested integration as completed.** Run tests, report the actual state, and maintain a short implementation changelog.
- **Prefer progress over ceremonial approval loops.** Ask only for genuinely blocking decisions; otherwise adopt a justified default and state it.

## 9. What `SPEC.md` must contain

The first agent task is **not** to create a generic spec from memory. It is to **read both proposal files and make a new design decision** using the operator's direction here.

At minimum, `SPEC.md` must address:

1. Product purpose and boundaries (model-side conversation continuity, not verified-fact memory).
2. Comparison of both existing proposals: adopted components, rejected components, unresolved conflicts.
3. Named architectural layers and which responsibilities they own.
4. Detailed conceptual and physical database schemas, including day/session/thread grouping and `major.db`/`minor.db` lifecycle.
5. Temporal and semantic projection strategy, with the Adab independence rule.
6. MCP tool surface designed for extremely easy model invocation and informative responses.
7. ChatGPT-write-first and Codex-read/curate-later behavior.
8. Hosted Sites feasibility, local npm/npx service, persistent server, caching, and optional inference workers.
9. Cloud/local identity, data migration, offline access, sync, and recovery.
10. Relations to native codebase data without making this a repository documentation replacement.
11. Security, privacy, portability, testing, and operational deployment.
12. Staged implementation plan and concrete end-to-end acceptance criteria.
13. Explicit independent architectural assertions and tradeoffs; do not dilute them into consensus prose.

### Acceptance scenarios to design against

- **Fresh chat, no re-explanation:** ChatGPT opens a new conversation and recalls the active research thread, key detours, and next unresolved question.
- **Several concurrent threads:** The system can distinguish a conversation about Kwisatz's philosophy from one about current Varys source code without losing their relationship.
- **Daily flow:** Notes from the same day cluster naturally while yesterday's unfinished thread can resume today.
- **Short write, rich recall:** A free-form note is stored with one straightforward tool call; subsequent recall returns an informative compact working context.
- **Cross-system evolution:** New versions of a module can be discussed without destroying the notes about prior versions.
- **Secondary consolidation:** Codex organizes and groups primary notes into the derived store without mutating the originals.
- **Offline local operation:** The local server continues to accept and retrieve notes without cloud connectivity; later synchronization has a defined resolution protocol.
- **No Adab dependency:** The MVP operates with no connection to USMS or an external knowledge graph.
- **No false automation:** If the host does not invoke an MCP tool, the plugin does not pretend a note was captured.

## 10. Final instruction to every agent

**Build the external notepad we wish ChatGPT already had.**

This is a cognitive workspace **for the assistant to use while we think together**. It must retain the movement of thought across days and chats, including code, speculation, symbolism, corrections, turns, detours, and competing architectures. It is not a truth tribunal and not an attempt to replace the memory systems already operating elsewhere.

The core paradox is intentional:

> **Make the internal schema unusually rich, and make the act of using it almost invisible.**

**Your first action is to read `docs/proposals/PROPOSAL.md` and `docs/proposals/PROPOSAL_2.md`. Your first output is a newly reasoned `SPEC.md`.**
