# Canonical ChatGPT plugin handoff

The same private Site and canonical plugin are published. Preserve their identities and database; do not create a duplicate.

| Identity | Current value |
| --- | --- |
| Site project | `appgprj_6ae661d0968081918d8c386d729f1c8c` |
| Site URL | https://somnus-cognitive-workspace.daeronsomnus.chatgpt.site |
| Canonical plugin | `plugin_asdk_app_sites_09950ef599088191a5e6c9569f8c7dae` |
| Plugin version | `1.2.0` |
| Release | `pluginrel_6ae73322176c8191a94fe4b74cf26f54` |

Current source, deployment, saved version and App entrypoint are in [connection.json](connection.json). Server source is shared under `src/`; `site/` provides the host routes. Root skills and WORKSPACE_CONTRACT are the authored package inputs, copied by `scripts/pack-plugin.mjs`. The plugin manifest, complete contract and both skill files were read back after update. Ordinary Chat behavior is independently described in tool descriptions and the self-contained instruction block; skill loading is not required.

v1.2.0 is published to the same private Site and canonical plugin. All 20 tests, typecheck, the handwritten line budget and hosted build pass. Canonical tools are open/write/recall/status/list/read/export/app; legacy calls remain compatible. Writes preserve up to4,000,000characters using lossless physical segmentation. Live status/list/export succeeded after deployment, including an880-record Markdown snapshot. Signed-in Android rendering remains unverified; this running chat retains cached old labels.

The live database retained52entries/28threads and the same lastWrite across deployment. No test entries were added to production. The screenshot request failure was not reproduced; Worker error logs were empty for the queried window. A service-credential download probe lacks the owner identity and returned403; this does not replace owner-authenticated download acceptance. Native App/Android interaction still needs direct client acceptance.

## Source mirror workflow

The published Site has a separate source mirror/history from this GitHub repository. Future agents must start from the canonical GitHub `main`, use the supported Site source helper in a separate scratch checkout, and overlay the canonical Git archive while preserving `mirror.git`. Build/package/push from that helper checkout. Do not merge the two histories or force-push one over the other. Keep both hosting manifests identical and refresh the existing plugin identity after publishing; never create another plugin app for an update.
