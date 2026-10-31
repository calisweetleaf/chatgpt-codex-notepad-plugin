import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { Miniflare } from 'miniflare';
import { D1Store, type D1Binding } from '../src/store/d1.js';
import { Workspace } from '../src/core/workspace.js';
import hosted from '../src/hosted/index.js';

function migration(name: string): string[] {
  const sql = readFileSync(new URL(`../src/store/migrations/${name}`, import.meta.url), 'utf8');
  const statements: string[] = [];
  let current = '', trigger = false;
  for (const raw of sql.split('\n')) {
    const line = raw.replace(/--.*$/, '').trim();
    if (!line) continue;
    current += `${line}\n`;
    if (/^CREATE TRIGGER\b/i.test(line)) trigger = true;
    if ((trigger && /^END;$/i.test(line)) || (!trigger && line.endsWith(';'))) {
      statements.push(current); current = ''; trigger = false;
    }
  }
  if (current.trim()) throw new Error('Incomplete migration statement');
  return statements;
}

test('D1 executes workspace operations and guarded atomic transactions', async (t) => {
  const mf = new Miniflare({ modules: true, script: 'export default { fetch() { return new Response("ok") } }', d1Databases: ['DB'], compatibilityDate: '2025-01-01' });
  t.after(() => mf.dispose());
  const db = await mf.getD1Database('DB');
  for (const name of ['0001.sql', '0002.sql']) {
    await db.batch(migration(name).map(sql => db.prepare(sql)));
  }
  const binding = db as unknown as D1Binding;
  const environment = { DB: binding, OWNER_USER_ID: 'owner', WORKSPACE_TIMEZONE: 'UTC' };
  const request = (body: string, headers: Record<string, string> = { 'content-type': 'application/json', 'oai-authenticated-user-id': 'owner' }) =>
    new Request('https://example.test/mcp', { method: 'POST', headers, body });
  assert.equal((await hosted.fetch(request('{}'), { ...environment, OWNER_USER_ID: '' })).status, 503);
  assert.equal((await hosted.fetch(request('{}', { 'content-type': 'application/json', 'oai-authenticated-user-id': 'intruder' }), environment)).status, 403);
  assert.equal((await hosted.fetch(new Request('https://example.test/mcp', { headers: { 'oai-authenticated-user-id': 'owner' } }), environment)).status, 405);
  assert.equal((await hosted.fetch(request('{}', { 'content-type': 'text/plain', 'oai-authenticated-user-id': 'owner' }), environment)).status, 415);
  assert.equal((await hosted.fetch(request('x'.repeat(128001)), environment)).status, 413);
  for (const method of ['tools/list', 'tools/call']) {
    const response = await hosted.fetch(request(JSON.stringify({ jsonrpc: '2.0', id: 1, method, params: { name: 'workspace_status', arguments: {} } })), environment);
    assert.equal(response.status, 200);
    const body = await response.json() as { result: { tools?: unknown[]; isError?: boolean; structuredContent?: { notes: number } } };
    if (method === 'tools/list') assert.equal(body.result.tools?.length, 4);
    else { assert.notEqual(body.result.isError, true); assert.equal(body.result.structuredContent?.notes, 0); }
  }
  const store = new D1Store(binding);
  let next = 0;
  const workspace = new Workspace(store, {
    id: prefix => `${prefix}_${String(++next).padStart(8, '0')}`,
    now: () => '2026-10-31T12:00:00.000Z',
    hash: async text => createHash('sha256').update(text).digest('hex'),
  }, 'owner', 'chatgpt', 'UTC');
  const first = await workspace.note({ text: 'Original continuity', about: ['Varys', 'varys'] });
  const branch = await workspace.note({ session: first.session as string, move: 'branch', text: 'Quasar detour' });
  const returned = await workspace.note({ session: first.session as string, move: 'return', text: 'Return to continuity' });
  assert.equal(returned.thread, first.thread);
  assert.notEqual(branch.thread, first.thread);
  assert.match((await workspace.recall({ query: 'quasar' })).text, /Quasar detour/);
  assert.equal((await db.prepare('SELECT count(*) AS n FROM major_handles').first<{ n: number }>())?.n, 1);
  await assert.rejects(workspace.note({ text: 'Should roll back', links: [{ to: 'missing', relation: 'elaborates' }] }));
  assert.equal((await db.prepare("SELECT count(*) AS n FROM major_notes WHERE text='Should roll back'").first<{ n: number }>())?.n, 0);

  await assert.rejects(store.transaction(async tx => {
    await tx.run("INSERT INTO major_meta(key,value) VALUES('batch-rollback','pending')");
    await tx.run("INSERT INTO major_events VALUES('invalid','clock',NULL,'type','target','{}','host')");
  }));
  assert.equal((await db.prepare("SELECT count(*) AS n FROM major_meta WHERE key='batch-rollback'").first<{ n: number }>())?.n, 0);

  let arrivals = 0, release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  const stores = [new D1Store(binding), new D1Store(binding)];
  const attempts = [0, 0];
  await Promise.all(stores.map((instance, i) => instance.transaction(async tx => {
    attempts[i]++;
    await tx.all("SELECT value FROM major_meta WHERE key='transaction_revision'");
    if (attempts[i] === 1 && ++arrivals === 2) release();
    if (attempts[i] === 1) await gate;
    await tx.run('INSERT INTO major_meta(key,value) VALUES(?,?)', `concurrent-${i}`, 'ok');
  })));
  assert.ok(attempts.some(count => count > 1));
  assert.equal((await db.prepare("SELECT count(*) AS n FROM major_meta WHERE key LIKE 'concurrent-%'").first<{ n: number }>())?.n, 2);

  for (const [message, shouldRetry] of [['CHECK constraint failed: transaction_snapshot_current', true], ['ambiguous transport failure', false]] as const) {
    let calls = 0;
    const failing: D1Binding = { withSession() {
      const session = binding.withSession('first-primary');
      return { prepare: sql => session.prepare(sql), batch: async statements => {
        if (++calls === 1) throw new Error(message);
        return session.batch(statements);
      } };
    } };
    const action = new D1Store(failing).transaction(async tx => { await tx.all('SELECT 1'); });
    if (shouldRetry) await action; else await assert.rejects(action, /ambiguous transport failure/);
    assert.equal(calls, shouldRetry ? 2 : 1);
  }
});
