# Cognitive Workspace Plugin

A persistent external notepad for ChatGPT (and Codex), exposed as an MCP server. It lets the assistant write short working notes during a research conversation and later recover the path of that conversation (threads, detours, returns, open questions) in a new or compacted chat.

**Status:** design settled, implementation not started. Next step is P0 in [`TASK.md`](TASK.md): the hosted Site + MCP server.

## Documents

| Document | What it is |
| --- | --- |
| [`AGENTS.md`](AGENTS.md) | Operating rules and routing for every agent. **§12 routes the rest of the repository.** Start here. |
| [`CONTEXT.md`](CONTEXT.md) | Current gate, architecture keys, hazards, open questions. One read to orient. |
| [`docs/SPEC.md`](docs/SPEC.md) | The design: architecture, schemas, six tools, deployment, sync, phases, acceptance scenarios. |
| [`TASK.md`](TASK.md) | Active board (P0 to P6), lane assignment, operator decisions. |
| [`NOTEPAD.md`](NOTEPAD.md) | Live append-only agent workbook: working state while the work happens. |
| [`MEMORY.md`](MEMORY.md) | Durable findings by key: operator doctrine, documented Sites facts, `potential/` verdicts, rejected designs, rationale. |
| [`skills/`](skills/README.md) | Role skills: plugin usage (ChatGPT), curation (Codex), building and deploying (implementers). |
| [`filetree.md`](filetree.md) | Birds-eye map with routing hints. |
| [`docs/proposals/`](docs/proposals) | The two independent input proposals. Historical; reconciled in SPEC §2. |
| [`potential/`](potential/) | Candidate Adab-Nebulae modules kept for reference. Never imported; verdicts in SPEC §9.1. |

## Design at a glance

- **Hosted first** on ChatGPT Sites (MCP server + D1), with an opt-in npm local companion (`cwp`).
- **Two stores:** `major` holds the append-only conversational trajectory; `minor` holds rebuildable summaries, collections, and indexes.
- **Six tools:** `workspace_open`, `workspace_note`, `workspace_recall`, `workspace_link`, `workspace_curate`, `workspace_status`. A normal write needs only `text`.
- **Not** a fact checker, a transcript recorder, or a replacement for other memory systems.

This repository is a private development workspace. The deployed service does not depend on Git or on this repository.