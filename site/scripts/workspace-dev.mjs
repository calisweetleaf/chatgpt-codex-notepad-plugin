import { existsSync } from 'node:fs';
const sync=new URL('../../scripts/sync-site-core.mjs',import.meta.url);
if (existsSync(sync)) await import(sync.href);
else if (!existsSync(new URL('../workspace-generated/hosted/index.ts',import.meta.url))) throw new Error('Run node scripts/sync-site-core.mjs at the repository root before starting an isolated Site preview.');
import { spawnSync } from 'node:child_process';
const result=spawnSync(process.execPath,['scripts/run-framework.mjs','dev',...process.argv.slice(2)],{stdio:'inherit'});
process.exit(result.status??1);
