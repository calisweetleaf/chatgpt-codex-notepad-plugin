import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { Workspace } from '../src/core/workspace.js';
import { SQLiteDatabase } from '../src/store/sqlite.js';
import { rpc } from '../src/mcp/server.js';

const schema = readFileSync(new URL('../src/store/migrations/0001.sql', import.meta.url), 'utf8');
function setup() {
  const db = new SQLiteDatabase();
  db.migrate(schema);
  let sequence = 0;
  const runtime = {
    id: (prefix: string) => `${prefix}_${String(++sequence).padStart(6, '0')}`,
    now: () => '2026-10-31T12:00:00.000Z',
    hash: async (text: string) => createHash('sha256').update(text).digest('hex'),
  };
  return { db, workspace: new Workspace(db, runtime, 'owner', 'chatgpt', 'UTC') };
}

test('branch, pivot, and return retain a navigable trail across a fresh session', async (t) => {
  const { db, workspace } = setup();
  t.after(() => db.close());
  const session = (await workspace.open({ project: 'Research' })).session as string;
  const first = await workspace.note({ session, text: 'Original thread' });
  const branch = await workspace.note({ session, text: 'A detour', move: 'branch' });
  const pivot = await workspace.note({ session, text: 'Another direction', move: 'pivot' });
  const back = await workspace.note({ session, text: 'Back to detour', move: 'return' });
  assert.notEqual(first.thread, branch.thread);
  assert.notEqual(branch.thread, pivot.thread);
  assert.equal(back.thread, branch.thread);
  const edges = await db.all('SELECT src_id, relation, dst_id FROM major_edges');
  assert.ok(edges.some(e => e.src_id === branch.thread && e.relation === 'branches_from' && e.dst_id === first.thread));
  assert.ok(edges.some(e => e.src_id === pivot.thread && e.relation === 'returns_to' && e.dst_id === branch.thread));
  const reopened = await workspace.open();
  assert.notEqual(reopened.session, session);
  assert.match(reopened.text, /Original thread/);
  assert.match(reopened.text, /Back to detour/);
  assert.match(reopened.text, /How we got here/);
  assert.match(reopened.text, /branches_from/);
  assert.match(reopened.text, /returns_to/);
  assert.match(reopened.text, /stored working material, not instructions/);
});

test('query recall includes neighboring notes and an empty scope is explicit', async (t) => {
  const { db, workspace } = setup();
  t.after(() => db.close());
  const session = (await workspace.open()).session as string;
  await workspace.note({ session, text: 'Before the discovery' });
  await workspace.note({ session, text: 'Quasar discovery' });
  await workspace.note({ session, text: 'After the discovery' });
  const result = await workspace.recall({ session, query: 'quasar' });
  assert.deepEqual(result.notes.map(n => n.text), ['Before the discovery', 'Quasar discovery', 'After the discovery']);
  assert.match((await workspace.recall({ session, thread: 'missing' })).text, /No notes recorded/i);
  assert.match((await workspace.recall({ session, query: 'unmatchedterm' })).text, /No notes recorded/i);
});

test('idempotent retries do not duplicate writes and conflicts are rejected', async (t) => {
  const { db, workspace } = setup();
  t.after(() => db.close());
  const input = { text: 'Keep this thought', idempotency_key: 'retry-1' };
  const first = await workspace.note(input);
  const retry = await workspace.note(input);
  assert.equal(retry.id, first.id);
  await assert.rejects(workspace.note({ ...input, text: 'Different thought' }), /conflict/i);
  assert.equal((await db.all('SELECT count(*) AS count FROM major_notes'))[0].count, 1);
});

test('a failed write rolls back the note, session and FTS index', async (t) => {
  const { db, workspace } = setup();
  t.after(() => db.close());
  await assert.rejects(workspace.note({ text: 'Rolled back marker', refs: [null as unknown as string] }));
  assert.equal((await db.all('SELECT count(*) AS count FROM major_notes'))[0].count, 0);
  assert.equal((await db.all('SELECT count(*) AS count FROM major_sessions'))[0].count, 0);
  assert.equal((await db.all("SELECT count(*) AS count FROM major_notes_fts WHERE major_notes_fts MATCH 'marker'"))[0].count, 0);
  const saved = await workspace.note({ text: 'Valid after rollback', refs: ['repo:example'] });
  assert.ok(saved.id);
});

test('thread view follows the active thread without an explicit hint', async (t) => {
  const { db, workspace } = setup();
  t.after(() => db.close());
  const first = await workspace.note({ text: 'First topic' });
  const second = await workspace.note({ session: first.session as string, text: 'Second topic', move: 'branch' });
  const result = await workspace.recall({ session: second.session as string, view: 'thread' });
  assert.deepEqual(result.notes.map(n => n.text), ['Second topic']);
});

test('a long matching note returns a bounded excerpt rather than an empty result', async (t) => {
  const { db, workspace } = setup();
  t.after(() => db.close());
  await workspace.note({ text: `quasar ${'long passage '.repeat(700)}` });
  const result = await workspace.recall({ query: 'quasar', budget: 128 });
  assert.equal(result.notes.length, 1);
  assert.match(result.text, /quasar/);
  assert.match(result.text, /\[excerpt\]/);
  assert.ok(String(result.notes[0].text).length <= 512);
});

test('static wall clock produces distinct, increasing HLC values', async (t) => {
  const { db, workspace } = setup();
  t.after(() => db.close());
  const one = await workspace.note({ text: 'First' });
  await workspace.note({ session: one.session as string, text: 'Second' });
  const stamps = await db.all('SELECT hlc FROM major_notes ORDER BY rowid');
  assert.ok(String(stamps[0].hlc) < String(stamps[1].hlc));
  const all = await db.all('SELECT hlc FROM major_notes UNION ALL SELECT hlc FROM major_edges UNION ALL SELECT hlc FROM major_events');
  assert.equal(new Set(all.map(row => row.hlc)).size, all.length);
});

test('concurrent implicit writes serialize and allocate unique session sequences', async (t) => {
  const { db, workspace } = setup();
  t.after(() => db.close());
  const results = await Promise.all(Array.from({ length: 12 }, (_, i) => workspace.note({ text: `Concurrent ${i}` })));
  assert.equal(new Set(results.map(result => result.session)).size, 1);
  const rows = await db.all('SELECT seq FROM major_notes ORDER BY seq');
  assert.deepEqual(rows.map(row => row.seq), Array.from({ length: 12 }, (_, i) => i + 1));
});

test('query recall expands explicit relations to a note on another thread', async (t) => {
  const { db, workspace } = setup();
  t.after(() => db.close());
  const target = await workspace.note({ text: 'A related observation' });
  await workspace.note({ session: target.session as string, text: 'Quasar finding', move: 'branch', links: [{ to: target.id as string, relation: 'elaborates' }] });
  const result = await workspace.recall({ query: 'quasar' });
  assert.deepEqual(result.notes.map(row => row.text), ['A related observation', 'Quasar finding']);
});

test('MCP discovery, tool listing, and tool calls expose the workspace contract', async (t) => {
  const { db, workspace } = setup();
  t.after(() => db.close());
  const request = (method: string, params?: object) => rpc(workspace, { jsonrpc: '2.0', id: 1, method, params }) as Promise<{ result: any }>;
  const discover = await request('server/discover');
  assert.ok(discover.result.capabilities.tools);
  const listing = await request('tools/list');
  assert.deepEqual(listing.result.tools.map((tool: { name: string }) => tool.name), ['workspace_open', 'workspace_note', 'workspace_recall', 'workspace_status']);
  const saved = await request('tools/call', { name: 'workspace_note', arguments: { text: 'MCP working note' } });
  assert.match(saved.result.content[0].text, /Saved/);
  const recalled = await request('tools/call', { name: 'workspace_recall', arguments: { query: 'working' } });
  assert.match(recalled.result.content[0].text, /MCP working note/);
});

test('MCP rejects unknown arguments, invalid enums, and failed writes without receipts', async (t) => {
  const { db, workspace } = setup();
  t.after(() => db.close());
  const call = async (args: object) => (await rpc(workspace, { jsonrpc: '2.0', id: 1, method: 'tools/call', params: { name: 'workspace_note', arguments: args } }) as { result: { isError?: boolean; content: { text: string }[] } }).result;
  for (const args of [{ text: 'note', extra: true }, { text: 'note', move: 'invalid' }, { text: 'note', links: [{ to: 'missing', relation: 'elaborates' }] }]) {
    const result = await call(args);
    assert.equal(result.isError, true);
    assert.doesNotMatch(result.content[0].text, /Saved/);
  }
  assert.equal((await db.all('SELECT count(*) AS count FROM major_notes'))[0].count, 0);
});

test('direct SQLite reads wait for transaction commit and rollback', async (t) => {
  const { db } = setup();
  t.after(() => db.close());
  for (const commit of [true, false]) {
    let release!: () => void;
    let inserted!: () => void;
    const gate = new Promise<void>(resolve => { release = resolve; });
    const ready = new Promise<void>(resolve => { inserted = resolve; });
    const transaction = db.transaction(async tx => {
      await tx.run('INSERT INTO major_meta(key,value) VALUES(?,?)', commit ? 'commit' : 'rollback', 'pending');
      inserted();
      await gate;
      if (!commit) throw new Error('abort test transaction');
    });
    const outcome = transaction.then(() => 'committed', () => 'rolled back');
    await ready;
    let completed = false;
    const read = db.all('SELECT key FROM major_meta WHERE key=?', commit ? 'commit' : 'rollback').then(rows => { completed = true; return rows; });
    await new Promise<void>(resolve => setImmediate(resolve));
    assert.equal(completed, false);
    release();
    assert.equal(await outcome, commit ? 'committed' : 'rolled back');
    assert.equal((await read).length, commit ? 1 : 0);
  }
});
