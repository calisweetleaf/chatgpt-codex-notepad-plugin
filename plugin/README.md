# Canonical ChatGPT plugin handoff

The private Site has been published and Plugin Creator provisioned the canonical app. Do not create a duplicate plugin.

| Identity | Value |
| --- | --- |
| Site project | `appgprj_6ae661d0968081918d8c386d729f1c8c` |
| Site URL | https://somnus-cognitive-workspace.daeronsomnus.chatgpt.site |
| Deployment | `appgdep_6ae662c153f481918c6aa28f86909e99` |
| Published version | `appgprj_6ae661d0968081918d8c386d729f1c8c~appgver_10a9a41eeeac8191bba2ff6672ea46a5` |
| Published source | `0c1527ced06a2681d3adc0d957818e624c06b952` |
| Canonical plugin App | `plugin_asdk_app_sites_09950ef599088191a5e6c9569f8c7dae` |
| Plugin release | `pluginrel_6ae66309e2b88191b922c50853ac4d5d` (v1.0.1) |

The deployment reports MCP enabled and environment revision 1. The shared server source lives in `src/hosted/` and `src/mcp/`; `site/` owns the Sites route and build wrapper. Root and Site `.openai/hosting.json` must retain matching project and D1 binding identities. Refreshing the plugin uses its existing App ID; do not provision a duplicate.

This directory contains the Plugin Creator manifests and deployed skill copies. The root `skills/` directory remains the authored skill source. Plugin Creator overlaid the usage and curator skills onto the existing app; preserve App/MCP identity when updating them.

**Verification still open:** provisioning and installation are confirmed, and usage/curator skill readback was verified. A `get_site` service-credential probe received HTTP 401 at dispatch for `server/discover` and `tools/list`; this did not exercise or diagnose the MCP handler. The current chat registry did not expose workspace tools after retry. No user tool call, cloud D1 persistence, or cross-chat note recovery is confirmed. Actual account cost is unknown.

## Source mirror workflow

The published Site has a separate source mirror/history from this GitHub repository. Future agents must start from the canonical GitHub `main`, use the supported Site source helper in a separate scratch checkout, and overlay the canonical Git archive while preserving `mirror.git`. Build/package/push from that helper checkout. Do not merge the two histories or force-push one over the other. Keep both hosting manifests identical and refresh the existing plugin identity after publishing; never create another plugin app for an update.
