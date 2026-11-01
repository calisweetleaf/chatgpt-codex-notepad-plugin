import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { Miniflare } from 'miniflare';
import { D1Store, type D1Binding } from '../src/store/d1.js';
import { Workspace } from '../src/core/workspace.js';
import type { Row, Value } from '../src/store/database.js';
import hosted from '../src/hosted/index.js';

test('D1 executes workspace operations and guarded atomic transactions', async (t) => {
  const mf = new Miniflare({ modules: true, script: 'export default { fetch() { return new Response("ok") } }', d1Databases: ['DB'], compatibilityDate: '2025-01-01' });
  t.after(() => mf.dispose());
  const db = await mf.getD1Database('DB');
  const journal = JSON.parse(readFileSync(new URL('../drizzle/meta/_journal.json', import.meta.url), 'utf8')) as { entries: { tag: string }[] };
  for (const entry of journal.entries) {
    const migration = readFileSync(new URL(`../drizzle/${entry.tag}.sql`, import.meta.url), 'utf8');
    await db.batch(migration.split('--> statement-breakpoint').map(sql => sql.trim()).filter(Boolean).map(sql => db.prepare(sql)));
  }
  const binding = db as unknown as D1Binding;
  const environment = { DB: binding, OWNER_USER_ID: 'owner', WORKSPACE_TIMEZONE: 'UTC' };
  const request = (body: string, headers: Record<string, string> = { 'content-type': 'application/json', 'oai-authenticated-user-id': 'owner' }) =>
    new Request('https://example.test/mcp', { method: 'POST', headers, body });
  assert.equal((await hosted.fetch(request('{}'), { ...environment, OWNER_USER_ID: '' })).status, 503);
  assert.equal((await hosted.fetch(request('{}', { 'content-type': 'application/json', 'oai-authenticated-user-id': 'intruder' }), environment)).status, 403);
  assert.equal((await hosted.fetch(new Request('https://example.test/mcp', { headers: { 'oai-authenticated-user-id': 'owner' } }), environment)).status, 405);
  assert.equal((await hosted.fetch(request('{}', { 'content-type': 'text/plain', 'oai-authenticated-user-id': 'owner' }), environment)).status, 415);
  assert.equal((await hosted.fetch(request('x'.repeat(32 * 1024 * 1024 + 1)), environment)).status, 413);
  const privateEnvironment = { DB: binding, TRUST_PRIVATE_SITE: 'true' };
  const discovery = request(JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'tools/list' }), { 'content-type': 'application/json' });
  assert.equal((await hosted.fetch(discovery, privateEnvironment)).status, 200);
  const anonymousWrite = request(JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'tools/call', params: { name: 'workspace_note', arguments: { text: 'forbidden' } } }), { 'content-type': 'application/json' });
  assert.equal((await hosted.fetch(anonymousWrite, privateEnvironment)).status, 403);
  for (const method of ['tools/list', 'tools/call']) {
    const response = await hosted.fetch(request(JSON.stringify({ jsonrpc: '2.0', id: 1, method, params: { name: 'workspace_status', arguments: {} } })), environment);
    assert.equal(response.status, 200);
    const body = await response.json() as { result: { tools?: unknown[]; isError?: boolean; structuredContent?: { notes: number } } };
    if (method === 'tools/list') assert.ok((body.result.tools?.length ?? 0) >= 4);
    else { assert.notEqual(body.result.isError, true); assert.equal(body.result.structuredContent?.notes, 0); }
  }
  const listing = await hosted.fetch(request(JSON.stringify({ jsonrpc: '2.0', id: 2, method: 'tools/list' })), environment);
  const names = ((await listing.json()) as { result: { tools: { name: string }[] } }).result.tools.map(tool => tool.name);
  assert.deepEqual(names, ['open', 'write', 'recall', 'status', 'list', 'read', 'export', 'app']);
  for (const name of ['status', 'workspace_status']) {
    const result = await hosted.fetch(request(JSON.stringify({ jsonrpc: '2.0', id: 3, method: 'tools/call', params: { name, arguments: {} } })), environment);
    assert.notEqual(((await result.json()) as { result: { isError?: boolean } }).result.isError, true);
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
  const artifact = await workspace.export();
  assert.equal(artifact.manifest.counts.major_notes, 3);
  const download = await (await workspace.download(artifact.id)).text();
  assert.match(download, /Original continuity/);
  assert.match(download, /Quasar detour/);
  assert.match(download, /complete snapshot/);
  const endpoint = `https://example.test/exports/${artifact.id}/download`;
  const get = (identity?: string) => new Request(endpoint, { headers: identity ? { 'oai-authenticated-user-id': identity } : {} });
  assert.equal((await hosted.fetch(get(), environment)).status, 403);
  assert.equal((await hosted.fetch(get('intruder'), environment)).status, 403);
  const response = await hosted.fetch(get('owner'), environment);
  assert.equal(response.status, 200);
  assert.match(response.headers.get('content-type') ?? '', /text\/markdown/);
  assert.equal(await response.text(), download);
  const ui = await hosted.fetch(new Request('https://example.test/operator', { headers: { 'oai-authenticated-user-id': 'owner' } }), environment);
  assert.equal(ui.status, 200);
  assert.match(await ui.text(), /data-transport="http"/);
  const alias = await hosted.fetch(new Request('https://example.test/api/workspace', { method: 'POST', headers: { 'oai-authenticated-user-id': 'owner', 'content-type': 'application/json' }, body: JSON.stringify({ name: 'workspace_list', arguments: { limit: 1 } }) }), environment);
  assert.equal(alias.status, 200);
  assert.equal(((await alias.json()) as { structuredContent: { records: unknown[] } }).structuredContent.records.length, 1);
  let resume!: () => void, reached!: () => void, paused = false;
  const snapshotGate = new Promise<void>(resolve => { resume = resolve; });
  const ready = new Promise<void>(resolve => { reached = resolve; });
  class PausedStore extends D1Store {
    override async all<T extends Row = Row>(sql: string, ...values: Value[]): Promise<T[]> {
      const rows = await super.all<T>(sql, ...values);
      if (!paused && sql.includes('count(*) AS count FROM "major_notes"')) { paused = true; reached(); await snapshotGate; }
      return rows;
    }
  }
  let ids = 0;
  const clock = { id: (prefix: string) => `${prefix}_race_${++ids}`, now: () => '2026-11-01T12:00:00.000Z', hash: async (text: string) => createHash('sha256').update(text).digest('hex') };
  const exporting = new Workspace(new PausedStore(binding), clock, 'owner', 'chatgpt', 'UTC').export();
  await ready;
  await new Workspace(new D1Store(binding), clock, 'owner', 'chatgpt', 'UTC').note({ text: 'Committed during export' });
  resume();
  const concurrent = await exporting;
  assert.equal(concurrent.manifest.counts.major_notes, 4);
  assert.match(await (await workspace.download(concurrent.id)).text(), /Committed during export/);
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

  for (const [canonical, legacy, args] of [
    ['open', 'workspace_open', {}], ['write', 'workspace_note', { text: 'Alias continuity' }],
    ['recall', 'workspace_recall', {}], ['status', 'workspace_status', {}],
    ['list', 'workspace_list', { limit: 1 }], ['read', 'workspace_get', { id: first.id }],
    ['export', 'workspace_export', {}], ['app', 'workspace_app', {}],
  ] as const) {
    for (const name of [canonical, legacy]) {
      const response = await hosted.fetch(request(JSON.stringify({ jsonrpc: '2.0', id: 9, method: 'tools/call', params: { name, arguments: args } })), environment);
      const body = await response.json() as { result: { isError?: boolean; content: { text?: string }[] } };
      assert.notEqual(body.result.isError, true, `${name}: ${body.result.content[0].text}`);
    }
  }
  const longText = ` \n\t${'🌌α\n'.repeat(450000)}\n \t `;
  assert.ok(Buffer.byteLength(longText, 'utf8') > 2_000_000);
  const longWrite = await hosted.fetch(request(JSON.stringify({ jsonrpc: '2.0', id: 10, method: 'tools/call', params: { name: 'write', arguments: { text: longText } } })), environment);
  const written = (await longWrite.json()) as { result: { isError?: boolean; structuredContent: { id: string } } };
  assert.notEqual(written.result.isError, true);
  const longRead = await hosted.fetch(request(JSON.stringify({ jsonrpc: '2.0', id: 11, method: 'tools/call', params: { name: 'read', arguments: { id: written.result.structuredContent.id } } })), environment);
  const read = (await longRead.json()) as { result: { structuredContent: { record: { text: string } } } };
  assert.equal(read.result.structuredContent.record.text, longText);
  const finalArtifact = await workspace.export();
  assert.ok((await (await workspace.download(finalArtifact.id)).text()).includes(longText));

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
