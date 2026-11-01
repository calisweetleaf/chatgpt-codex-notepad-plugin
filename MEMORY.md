# MEMORY.md: Durable findings

**Updated:** 2026-10-31
**Purpose:** things that would cost real work to rediscover, or that would drift if only remembered in chat. Compact keys live in [CONTEXT.md](CONTEXT.md); live working state in [NOTEPAD.md](NOTEPAD.md).

Each entry carries what it is, where it came from, when, and what caused it to exist. Correct an entry by appending a dated correction under it; do not quietly rewrite history.

---

## `doctrine-no-verification` — the workspace does not adjudicate

**Status:** OPERATOR-DIRECTIVE · **Source:** operator, repeatedly, and `AGENTS.md` §2 · **Date:** 2026-10-31

The product stores **thinking in progress**: branches, pivots, half-formed ideas, fictional analogies, contradictions, corrections, symbolic handles. It is explicitly **not** a fact verifier, epistemic auditor, citation enforcer, or provenance bureaucracy. The operator's words: verified-reward framing would "take away the purpose of this cognitive workspace."

Design consequences, all load-bearing:

- No required epistemic status, evidence field, or citation on a note.
- No server-side truth check, confidence score, or quality gate on note content.
- Codex adds context beside the operator's thinking; it never marks that thinking corrected or wrong.
- `minor` organizes and condenses. It never ranks notes by correctness.

This is why both input proposals' epistemic-status machinery was rejected (see `proposal-rejections`).

## `sites-facts-2026-10-31` — what ChatGPT Sites hosting actually documents

**Status:** OBSERVED (documentation, not account) · **Source:** help.openai.com "Hosting a plugin with ChatGPT Sites", "Creating and using ChatGPT Sites"; learn.chatgpt.com "Data and connections", "Build plugins" · **Date fetched:** 2026-10-31

Verified from docs:

- A Site can host an MCP server. Publishing the Site creates a plugin usable from ChatGPT **and Codex**.
- Sites is available on Plus, Pro, Business, Enterprise. In Enterprise, plugin-creation permissions are off by default.
- Durable storage: **D1** (relational) for structured data, **R2** for files.
- "Each Site's database can store up to 10 GB." Note the singular "database" — this is the origin of the one-vs-two database question.
- Building or editing a Site counts toward **Codex usage**. Running and hosting (traffic, storage) is **billed separately**, and charges are described as waived for **Enterprise** workspaces only.
- Changing tool definitions requires **republishing** the Site; the plugin does not update itself.
- Pro and personal accounts **cannot share** a Site-hosted plugin with other users.
- Workspace-restricted Sites forward visitor identity to page requests via `oai-authenticated-user-email` / `oai-authenticated-user-full-name` headers. Whether this reaches an **MCP tool handler** is **not** documented.

Still unobserved, and why it matters: Site server runtime and language; the MCP transport expected; how D1 is bound and whether two databases can be bound; identity at a tool handler; scheduled/background execution; outbound HTTP; the real cost on this account. P0 records all of these.

**Anti-rediscovery note:** the operator's understanding is that Sites hosting is free. The documentation does not say that outside Enterprise. Do not resolve this from documentation again; only the account can answer it.

## `potential-verdicts` — the six Adab candidate modules

**Status:** OBSERVED (outlines, imports, schema sections read 2026-10-31) · **Source:** `potential/*.py` · **Cause:** SPEC §9.1 evaluation

All six are Python; the runtime is TypeScript. Adoption can only mean re-implementing a mechanism. Nothing is ever imported from `potential/`, and the directory is never modified.

| Module | Lines | Verdict | Transfers |
| --- | --- | --- | --- |
| `temporal_db.py` | 626 | mine for patterns | `TimeRange` helpers (last N days, month, year); FTS rebuild routine. Compressed raw payloads not needed — notes are small. |
| `semantic_db.py` | 1,649 | mine for schema ideas (P3/P5) | `scope_key + content_hash` unique dedupe; typed relationship table; cluster tables; access log as a ranking signal. Runtime code rejected: depends on `core.modality_bridge`, aiosqlite, numpy, sklearn. |
| `knowledge_library.py` | 2,345 | concept transfer only | `SymbolicMotif` / `TimelineMarker` validate first-class symbolic handles beside technical ones; `EchoDetector` informs the P5 echo job. "Breath phase" retrieval modes and `find/resolve_contradiction` rejected — the workspace does not adjudicate. |
| `semantic_search.py` | 875 | reject | Depends on Adab `utilities.*` and an external MCP memory graph. Its ranking blend is already covered by SPEC §8.3. |
| `semantic_chunking_engine.py` | 3,392 | reject for V1 | Needs nltk, spacy, sklearn, scipy, networkx, sentence-transformers. Notes are short and author-chunked. Revisit only if large pasted documents become stored input. |
| `knowledge_integration.py` | 4,091 | reject | Knowledge-graph ingestion with spacy, networkx, PDF/DOCX parsing. Its bounded-input limits are a useful hardening checklist for `import`. |

## `proposal-rejections` — what was declined from the two input proposals, and why

**Status:** VERIFIED decision · **Source:** `docs/proposals/PROPOSAL.md`, `PROPOSAL_2.md`, reconciled in SPEC §2 · **Date:** 2026-10-31

Preserved so nobody re-adds them as "obvious improvements":

- **Required typed event kinds with evidence envelopes** (PROPOSAL) — too much authoring cost per note. Kinds became optional inferred labels.
- **Required epistemic statuses** `CODE_OBSERVED` / `USER_STATED` / `TESTED` (PROPOSAL_2) — see `doctrine-no-verification`.
- **Fail-closed writes on ambiguous binding** (PROPOSAL) — a refused note is usually lost; a misfiled note stays searchable and is fixable in one call. Strict mode survives as config, not default.
- **One workspace per conversation, strictly isolated** (PROPOSAL) — the mission values cross-chat continuity. Isolation became per-thread structure plus explicit edges.
- **Seven to eleven narrow tools** (both) — merged into six; branching and returning became a `move` hint on an ordinary note.
- **`compare_proposals` as a core tool** (PROPOSAL_2) — right workflow, wrong layer. Two proposals are two threads with a `contradicts` edge; recall over both is the comparison.
- **Local-first MVP** (PROPOSAL_2) — operator direction is hosted-first; local is opt-in.
- **Checkpoint as a required ritual before context loss** (both) — the model cannot detect compaction. Checkpoints became optional `snapshot` notes.

Both proposals' durable contributions were kept: append-only notes, rebuildable projections, SQLite + FTS5 before embeddings, Adab as optional adapter, no assumed conversation id, idempotency keys and honest receipts, stored text treated as untrusted data, record time vs. version time, competing designs preserved rather than averaged.

## `store-split-rationale` — why `major` and `minor` are separated hard

**Status:** VERIFIED decision · **Source:** SPEC §5.2, §5.3 · **Date:** 2026-10-31

Two logical stores, physically two databases where the platform allows, prefixed tables where it does not. No foreign key and no query crosses the boundary in either layout, so the same DDL and queries run on both.

Four reasons that are not style preferences:

1. The curator path can open `major` **read-only**, so "Codex never overwrites ChatGPT notes" is enforced by connection mode rather than discipline.
2. SQLite and D1 serialize writers per database; a long consolidation cannot stall a live note write.
3. `minor` can be deleted and rebuilt, and its schema can change freely, without risking `major`.
4. Only `major` needs backup and sync; derived bulk stays out of sync payloads.

Accepted cost: no atomic transaction across the two. Handled by recording the `major` watermark each derivation was built against, so a half-finished derivation is detectable and simply rebuilt. SQLite `ATTACH` is deliberately not used for writes — multi-database commits are atomic per file, not across files, and attaching would imply a guarantee that does not exist.

## `document-layer-roles` — how the repository routes an agent

**Status:** OPERATOR-DIRECTIVE · **Source:** operator, 2026-10-31 · **Cause:** `NOTEPAD.md` added; `AGENTS.md` was starting to absorb everything

The point of the document layer is a codebase that is **proactively helpful** rather than hostile, through progressive disclosure. The intent is not to minimize tokens but to spend them intelligently: route into the right surface instead of reading everything, and leave the surfaces evolved so the next session resumes as if nothing changed.

- `AGENTS.md` **routes** and holds operating rules. It must not become the semantic index of the repository.
- `filetree.md` stays the **birds-eye map**, progressively gaining routing hints. It is not a semantic router and not a copy of other documents.
- `TASK.md` is next actions. `docs/SPEC.md` is design. `NOTEPAD.md` is live working state, append-only. `CONTEXT.md` is compact current keys. `MEMORY.md` is durable findings.
- Rules route; they do not forbid novelty.

Hierarchy, per `NOTEPAD.md`: `AGENTS.md` → `NOTEPAD.md` → `CONTEXT.md` → `MEMORY.md`.

## `sites-published-2026-10-31` — deployment identifiers and verification boundary

**Status:** OBSERVED via root's native Sites/Plugin Creator work · **Date:** 2026-10-31

- Site project `appgprj_6ae661d0968081918d8c386d729f1c8c`, URL `https://somnus-cognitive-workspace.daeronsomnus.chatgpt.site`, deployment `appgdep_6ae662c153f481918c6aa28f86909e99`, version `appgprj_6ae661d0968081918d8c386d729f1c8c~appgver_10a9a41eeeac8191bba2ff6672ea46a5`, source `0c1527ced06a2681d3adc0d957818e624c06b952`. MCP enabled; environment revision 1.
- Canonical plugin ID `plugin_asdk_app_sites_09950ef599088191a5e6c9569f8c7dae`, installed; release `pluginrel_6ae66309e2b88191b922c50853ac4d5d`, v1.0.1. Usage and curator skill readback was verified.
- A schema probe with the Site service credential returned HTTP 401 at dispatch for `server/discover` and `tools/list`; do not treat that as an MCP-handler test or infer a server defect. Current chat tool registry lacked workspace tools after retry.
- No user MCP call, cross-chat note recovery, cloud D1 persistence, or actual account cost is confirmed.
- Source update procedure: use the supported Site source helper in a separate scratch checkout; overlay the canonical GitHub `main` archive while preserving `mirror.git`; build/package/push there. Keep both hosting manifests identical, preserve plugin/App IDs, and do not merge or force-push the separate histories. See `plugin/README.md`.

## `p3-published-2026-11-01` — full visibility without a replacement backend

**Status:** OBSERVED by root through native deployment and plugin readback, plus local integration tests.

P3 uses the same Site, D1 database and owner authentication. Eight MCP tools include baseline open/note/recall/status and list/get/export/app. Exact records and row locators include idless tables. Export atomically materializes all applicable major/minor rows in the existing database; generated artifacts, duplicate FTS tables and the transient transaction guard are explicitly excluded. Manifest counts and a completion footer make omissions detectable. V2 JSON metadata retains exact text including trailing newlines; source excerpts are separate immutable rows. The new migration adds tables only.

Current deployment, source, release, App entrypoint and URLs are in [plugin/connection.json](plugin/connection.json). Plugin v1.1.0 skills, shared contract and manifest were read back. The 16-test suite, typecheck, code-size budget and hosted build pass. Synthetic browser host controls passed, but native signed-in ChatGPT App rendering and new live tool calls are not proven by that fixture. Existing live status calls reach persistent records; no source notes were written by root in this release session.

GitHub main is canonical. An old master default hid the implementation in ordinary clones; synchronizing that existing branch is compatibility, not a second development lane. Source mirrors retain separate Git histories. Runtime data and secrets are never repository components.
