import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { SQLiteDatabase } from '../src/store/sqlite.js';
import { Workspace, type Runtime } from '../src/core/workspace.js';

function setup() {
  const db = new SQLiteDatabase();
  for (const name of ['0001.sql', '0002.sql', '0003.sql']) db.migrate(readFileSync(new URL(`../src/store/migrations/${name}`, import.meta.url), 'utf8'));
  let i = 0;
  const runtime: Runtime = { id: prefix => `${prefix}_${++i}`, now: () => '2026-11-01T12:00:00.000Z', hash: async text => createHash('sha256').update(text).digest('hex') };
  return { db, owner: new Workspace(db, runtime, 'owner', 'chatgpt', 'UTC'), other: new Workspace(db, runtime, 'other', 'chatgpt', 'UTC') };
}

test('inspection paginates a fixed ceiling and returns complete, scoped records', async t => {
  const { db, owner } = setup(); t.after(() => db.close());
  const original = 'Unicode 🌌\n````typescript\nconst value = `note`;\n````\n' + 'long '.repeat(2500);
  const first = await owner.note({ text: original, sources: [{ text: 'Verbatim source', locator: 'repo:test' }] });
  await owner.note({ session: first.session as string, text: 'A second note' });
  const page = await owner.list({ limit: 1 });
  assert.equal(page.records.length, 1);
  assert.equal(page.records[0].text, original);
  assert.ok(page.next_cursor);
  await owner.note({ session: first.session as string, text: 'Later arrival' });
  const next = await owner.list({ limit: 1, cursor: page.next_cursor! });
  assert.equal(next.records[0].text, 'A second note');
  assert.equal(next.next_cursor, null);
  assert.equal((await owner.get({ id: first.id as string })).record.text, original);
  assert.equal((await owner.get({ id: first.id as string })).related.major_sources[0].text, 'Verbatim source');
  const viaRowid = await owner.get(page.record_locators[0]);
  assert.equal(viaRowid.record.id, first.id);
  assert.equal(viaRowid.related.major_sources[0].text, 'Verbatim source');
  await assert.rejects(owner.list({ table: 'sqlite_master' }), /unknown/i);
  await assert.rejects(owner.list({ cursor: 'not a cursor' }), /cursor/i);
  await assert.rejects(owner.list({ cursor: page.next_cursor!, thread: 'other' }), /cursor/i);
  await assert.rejects(owner.get({ id: 'missing' }), /not found/i);
});

test('export preserves every snapshot record and bytes, isolates owners, and remains immutable', async t => {
  const { db, owner, other } = setup(); t.after(() => db.close());
  const text = 'A note 🌌\n````\ninside fence\n````\n' + 'unabridged '.repeat(1200);
  const note = await owner.note({ text, sources: [{ text: 'Original source λ', locator: 'url:example' }] });
  await db.run("INSERT INTO minor_embeddings(note_id,model,dim,vec) VALUES(?,?,?,X'00FF1080')", note.id as string, 'test', 1);
  const exported = await owner.export();
  assert.equal(exported.manifest.counts.major_notes, 1);
  assert.equal(exported.manifest.counts.major_sources, 1);
  assert.equal(exported.manifest.counts.minor_embeddings, 1);
  assert.equal(exported.manifest.total_records, Object.values(exported.manifest.counts).reduce((a,b) => a+b,0));
  const response = await owner.download(exported.id);
  assert.equal(response.status, 200);
  const output = await response.text();
  assert.ok(output.includes(text));
  assert.ok(output.includes('Original source λ'));
  assert.match(output, /"\$encoding": "hex"/);
  assert.match(output, /"data": "00FF1080"/);
  assert.match(output, new RegExp(`END: ${exported.manifest.total_records} records; complete snapshot`));
  assert.equal((await other.download(exported.id)).status, 404);
  const second = await owner.export();
  assert.equal(second.manifest.total_records, exported.manifest.total_records);
  assert.equal(second.manifest.counts.operator_export_rows, undefined);
  await owner.note({ text: 'Later write is outside snapshot' });
  assert.equal(await (await owner.download(exported.id)).text(), output);
  const embeddings = await owner.list({ table: 'minor_embeddings' });
  assert.equal(embeddings.records[0].vec.data, '00FF1080');
  const byRowid = await owner.get(embeddings.record_locators[0]);
  assert.equal(byRowid.record.vec.data, '00FF1080');
  assert.equal(byRowid.record.note_id, note.id);
});

test('large multi-page exports retain every byte and never rewrite source notes', async t => {
  const { db, owner } = setup(); t.after(() => db.close());
  const expected: string[] = [];
  let session: string | undefined;
  for (let i = 0; i < 80; i++) {
    const text = `Original note ${i}\n${'🌌α\n'.repeat(2800)}End ${i}`;
    expected.push(text);
    const receipt = await owner.note({ text, session });
    session = receipt.session as string;
  }
  const before = await db.all('SELECT id,text FROM major_notes ORDER BY rowid');
  const digest = (rows: typeof before) => createHash('sha256').update(JSON.stringify(rows)).digest('hex');
  const exported = await owner.export();
  const output = await (await owner.download(exported.id)).text();
  const after = await db.all('SELECT id,text FROM major_notes ORDER BY rowid');
  assert.ok(Buffer.byteLength(output, 'utf8') > 1_000_000);
  assert.equal(exported.manifest.counts.major_notes, expected.length);
  assert.equal(digest(after), digest(before));
  for (const text of expected) assert.ok(output.includes(text));
  assert.match(output, new RegExp(`END: ${exported.manifest.total_records} records; complete snapshot`));
});
