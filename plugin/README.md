# Canonical ChatGPT plugin handoff

The private Site has been published and Plugin Creator provisioned the canonical app. Do not create a duplicate plugin.

| Identity | Value |
| --- | --- |
| Site project | `appgprj_6ae661d0968081918d8c386d729f1c8c` |
| Site URL | https://somnus-cognitive-workspace.daeronsomnus.chatgpt.site |
| Canonical plugin App | `plugin_asdk_app_sites_09950ef599088191a5e6c9569f8c7dae` |
| Plugin release | `pluginrel_6ae6bb003ae081919df592906c550291` (v1.1.0) |

The Site's final source patch is published. Current deployment identifiers are in [`connection.json`](connection.json). The shared server source lives in `src/hosted/` and `src/mcp/`; `site/` owns the Sites route and build wrapper. Root and Site `.openai/hosting.json` must retain matching project and D1 binding identities. Refreshing the plugin uses its existing App ID; do not provision a duplicate.

This directory contains the Plugin Creator manifests and local skill copies. The root `skills/` directory remains the authored skill source. Plugin Creator published v1.1.0; the manifest, `WORKSPACE_CONTRACT.md`, and both usage/curator skill contents were read back. Preserve the existing App/MCP identity during future refreshes; do not create a second app. Refreshed Site deployment identifiers belong in [`connection.json`](connection.json) and should be updated by the root owner.

**Verification still open:** the current ChatGPT registry exposes only the four earlier tools; the new list/get/export operations and cross-chat note recovery have not been exercised live. Root observed 47 notes/26 threads after the latest deployment, unchanged from before deployment; last write was `2026-11-01T03:50:34.459Z`. Root reports no note writes during deployment. This does not include per-note hash checks. Earlier service-credential probes returned HTTP 401 at dispatch and do not establish a server defect or exercise the handler. Cloud persistence and actual account cost remain unknown.

Root reports 16 passing tests, typecheck, line-budget pass, and hosted build. A synthetic MCP browser fixture exercised timeline, inspector, threads, graph, and export UI. The local `/operator` preview returned 403 without owner identity. Neither result verifies signed-in production rendering in the native MCP App host; no production visual pass is claimed.

## Source mirror workflow

The published Site has a separate source mirror/history from this GitHub repository. Future agents must start from the canonical GitHub `main`, use the supported Site source helper in a separate scratch checkout, and overlay the canonical Git archive while preserving `mirror.git`. Build/package/push from that helper checkout. Do not merge the two histories or force-push one over the other. Keep both hosting manifests identical and refresh the existing plugin identity after publishing; never create another plugin app for an update.
