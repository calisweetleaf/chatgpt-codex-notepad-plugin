import { createInterface } from 'node:readline';
import { readFileSync, readdirSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { ulid } from 'ulid';
import { Workspace } from '../core/workspace.js';
import { SQLiteDatabase } from '../store/sqlite.js';
import { rpc } from '../mcp/server.js';

// Development client transport. The supervised companion remains a later phase.
const database = new SQLiteDatabase(process.argv[2] ?? ':memory:');
const tables = await database.all("SELECT name FROM sqlite_master WHERE name='major_meta'");
const version = tables.length ? Number((await database.all("SELECT value FROM major_meta WHERE key='schema_version'"))[0]?.value ?? 1) : 0;
const migrations = new URL('../store/migrations/', import.meta.url);
for (const file of readdirSync(migrations).filter(file => /^\d+\.sql$/.test(file)).sort()) {
  const next = Number(file.replace('.sql',''));
  if (next <= version) continue;
  const sql = readFileSync(new URL(file, migrations), 'utf8');
  database.migrate(`BEGIN IMMEDIATE;\n${sql}\nINSERT INTO major_meta(key,value) VALUES('schema_version','${next}') ON CONFLICT(key) DO UPDATE SET value=excluded.value;\nCOMMIT;`);
}
const workspace = new Workspace(database, {
  id: prefix => `${prefix}_${ulid()}`,
  now: () => new Date().toISOString(),
  hash: async text => createHash('sha256').update(text).digest('hex'),
}, 'local-owner', 'local');
const lines = createInterface({ input: process.stdin, crlfDelay: Infinity });
try {
  for await (const line of lines) {
    let response: unknown;
    try { response = await rpc(workspace, JSON.parse(line)); }
    catch { response = { jsonrpc: '2.0', id: null, error: { code: -32700, message: 'Parse error' } }; }
    if (response !== undefined) process.stdout.write(JSON.stringify(response) + '\n');
  }
} finally { database.close(); }
