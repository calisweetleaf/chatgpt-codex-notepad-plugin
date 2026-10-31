import { spawnSync } from 'node:child_process';
import { cpSync, readFileSync, rmSync } from 'node:fs';
const root = new URL('../', import.meta.url);
const manifest = readFileSync(new URL('.openai/hosting.json', root), 'utf8');
if (manifest !== readFileSync(new URL('site/.openai/hosting.json', root), 'utf8')) throw new Error('Root and site hosting identities differ');
const result = spawnSync(process.execPath, ['scripts/run-framework.mjs', 'build'], { cwd: new URL('site/', root), stdio: 'inherit' });
if (result.status !== 0) process.exit(result.status ?? 1);
rmSync(new URL('dist/', root), { recursive: true, force: true });
cpSync(new URL('site/dist/', root), new URL('dist/', root), { recursive: true });
