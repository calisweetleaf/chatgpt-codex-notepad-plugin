# Cognitive Workspace Plugin

A persistent external notepad for ChatGPT (and Codex), exposed as an MCP server. It lets the assistant write short working notes during a research conversation and later recover the path of that conversation (threads, detours, returns, open questions) in a new or compacted chat.

**Status:** specification stage. No application code yet.

## Documents

| Document | What it is |
|---|---|
| [`docs/SPEC.md`](docs/SPEC.md) | The current specification: architecture, schemas, tools, deployment, sync, phases, acceptance tests. Start here. |
| [`AGENTS.md`](AGENTS.md) | Operator direction and working rules for every agent. Takes precedence over the proposals. |
| [`docs/proposals/PROPOSAL.md`](docs/proposals/PROPOSAL.md) | Input proposal 1: Conversation-Bound Cognitive Workspace (CBCW). Non-canonical. |
| [`docs/proposals/PROPOSAL_2.md`](docs/proposals/PROPOSAL_2.md) | Input proposal 2: Somnus Research Ledger. Non-canonical. |
| [`TASK.md`](TASK.md) | Active work board: what to build next, phase by phase. |
| [`skills/`](skills/README.md) | Agent skills: plugin usage (ChatGPT), curation (Codex), and building/deploying this repo. |
| [`filetree.md`](filetree.md) | Map of the repository. |
| [`potential/`](potential/) | Candidate Adab-Nebulae modules kept for reference. Not part of the runtime; see `docs/SPEC.md` §9.1. |

## Design at a glance

- **Hosted first** on ChatGPT Sites (MCP server + D1), with an opt-in npm local companion (`cwp`).
- **Two stores:** `major` holds the append-only conversational trajectory; `minor` holds rebuildable summaries, collections, and indexes.
- **Six tools:** `workspace_open`, `workspace_note`, `workspace_recall`, `workspace_link`, `workspace_curate`, `workspace_status`. A normal write needs only `text`.
- **Not** a fact checker, a transcript recorder, or a replacement for other memory systems.

This repository is a private development workspace. The deployed service does not depend on Git or on this repository.