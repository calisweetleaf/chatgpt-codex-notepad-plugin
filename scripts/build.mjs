import { rmSync, cpSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
rmSync('dist', { recursive: true, force: true });
const result = spawnSync(process.execPath, ['node_modules/typescript/bin/tsc','-p','tsconfig.build.json'], { stdio: 'inherit' });
if (result.status !== 0) process.exit(result.status ?? 1);
cpSync('src/store/migrations', 'dist/store/migrations', { recursive: true });
