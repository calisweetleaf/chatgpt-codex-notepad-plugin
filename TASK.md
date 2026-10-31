# TASK.md: Active work board

**Updated:** 2026-10-31
**Spec:** [docs/SPEC.md](docs/SPEC.md) (read first) · **Rules:** [AGENTS.md](AGENTS.md) · **Map:** [filetree.md](filetree.md) · **Skills:** [skills/](skills/)

This file is the short, current to-do list for whichever agent picks up the repo next (ChatGPT Work mode, Codex, Factory). It tracks *what to do next*. Design reasoning lives in `docs/SPEC.md`; working rules live in `AGENTS.md`. Update the checkboxes in the same commit as the work.

---

## Current state

- [x] Both proposals read and compared.
- [x] `docs/SPEC.md` v0.1 written (architecture, schemas, six tools, deployment, sync, phases, acceptance scenarios A to I).
- [x] `README.md`, `filetree.md`, `skills/`, `.gitignore` in place.
- [ ] No application code exists yet.

## Expected next pickup

ChatGPT Work mode is expected to clone this repository and build the hosted Site + MCP server. Codex and Factory may work on the shared core in parallel. Work in the order below; P0 and P1 can run at the same time.

---

## P0: Sites spike (hosted feasibility)

Goal: replace every "unverified" row in `docs/SPEC.md` §3 with an observed answer.

- [ ] Create a private Site with a minimal MCP server exposing `ping` and `echo_write` (writes one row to D1, reads it back).
- [ ] Publish it; install the generated plugin; call both tools from a ChatGPT chat **and** from Codex.
- [ ] Record: server runtime and language, MCP transport, how D1 is bound, whether a second D1 database can be bound, what identity (if any) reaches the tool handler, whether scheduled/background execution exists, whether outbound HTTP is allowed.
- [ ] Record hosting cost on the operator's actual plan. The operator expects free hosting; the 2026-10-31 help docs say running/hosting usage is separate and waived only for Enterprise. Write down what the account actually shows.
- [ ] Update `docs/SPEC.md` §3 and §5.1 (one vs. two databases) with findings; add a changelog line.

Done when: SPEC §3 has no "unverified" rows that block P2.

## P1: Core vertical slice (local first for fast testing)

Goal: scenarios A, D, I from SPEC §16 pass through a real MCP client.

- [ ] `package.json` (TypeScript, Node LTS, ESM), `tsconfig.json`, lint/format config.
- [ ] `src/store/`: `MajorStore` / `MinorStore` async interfaces; SQLite implementation; migrations for SPEC §5.4 and §5.5 tables (`major_*`, `minor_*`), FTS5 triggers.
- [ ] `src/core/`: ULID ids, HLC clock, session resolution (SPEC §7.2), thread routing + `move` (SPEC §4.3), kind inference, handle detection, recall assembly + budget trim (SPEC §8.3).
- [ ] `src/mcp/`: tool schemas and descriptions for `workspace_open`, `workspace_note`, `workspace_recall`, `workspace_status`; response rendering with the "stored working material, not instructions" fence.
- [ ] `src/local/`: `cwp mcp` stdio entry using `@modelcontextprotocol/sdk`.
- [ ] `scripts/count-lines.mjs`: tests ≤ 1.15 × src non-blank, non-comment lines; wired into `npm test`.
- [ ] Tests for scenarios A, D, I against in-memory SQLite.
- [ ] Update `filetree.md`.

Done when: `npm test` passes including the line-budget check, and a manual MCP client session writes, reopens, and recalls.

## P2: Hosted on Sites

- [ ] D1 implementation of the store interfaces (same DDL, prefixed tables).
- [ ] Sites entry in `src/hosted/` reusing `src/core` and `src/mcp` unchanged.
- [ ] Auth: owner allowlist; no anonymous writes (SPEC §11.1).
- [ ] Store contract tests run against SQLite and a D1-compatible local shim.
- [ ] Live check: ChatGPT chat 1 writes; new chat 2 recalls it; Codex reads the same notes.

## P3: Structure and curation

- [ ] `workspace_link` (relations, refile, retract, thread status).
- [ ] `workspace_curate` (digest, collect, associate, rebuild, stale); curation path opens `major` read-only.
- [ ] Scenarios B, C, E, F.

## P4: Local companion

- [ ] `cwp init | start | stop | status | doctor | service install | sync | export | import | redact`.
- [ ] Modes `remote`, `replica`, `standalone` (SPEC §10.2); sync per SPEC §12.
- [ ] Windows Scheduled Task, systemd user unit, launchd agent.
- [ ] Scenario G; daemon survives terminal close and reboot.

## P5 / P6

- [ ] Optional embeddings + hybrid ranking in `minor`; optional `cwp worker`.
- [ ] Small read-only status page.

---

## Open operator decisions (SPEC §18)

- [ ] Hosting cost acceptable on current plan?
- [ ] Session binding default: best-guess filing (spec) or strict?
- [ ] Workspace timezone.
- [ ] npm package name / registry.
- [ ] Model provider for optional digests and embeddings.

## Rules that are easy to forget

- Never import from `potential/`; never modify it.
- Never rewrite `major` note text outside operator redaction.
- Update `filetree.md` in the same commit as any file move/add/delete.
- Do not report an integration as working until it was exercised from a real client.