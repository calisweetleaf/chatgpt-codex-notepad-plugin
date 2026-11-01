import type { Database, Row, Value } from '../store/database.js';
import type { Runtime } from './workspace.js';
import { hydrateNotes } from './text.js';

type Column = { name: string; type: string; pk: number };
type Table = { name: string; columns: Column[]; order: string };
// Schema-only cache. Keyed by actual CREATE TABLE SQL, never by user data.
const columnCache = new Map<string,Column[]>();
export interface ListInput { table?: string; limit?: number; cursor?: string; thread?: string; project?: string; order?: 'asc'|'desc'; since?: string; until?: string }
export interface GetInput { id?: string; table?: string; rowid?: number }
const quoted = (value: string) => '"' + value.replaceAll('"','""') + '"';
const cursorEncode = (value: unknown) => btoa(String.fromCharCode(...new TextEncoder().encode(JSON.stringify(value)))).replaceAll('+','-').replaceAll('/','_').replace(/=+$/,'');
const cursorDecode = (value: string) => JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(value.replaceAll('-','+').replaceAll('_','/')), character => character.charCodeAt(0))));
const fence = (text: string) => { let length=3; for (const match of text.matchAll(/`+/g)) length=Math.max(length,match[0].length+1); return '`'.repeat(length); };

/** Exact operator reads and server-side immutable export snapshots, on the existing store. */
export class Inspection {
  constructor(private db: Database, private principal: string, private runtime: Runtime) {}
  private async tables(): Promise<Table[]> {
    const rows = await this.db.all("SELECT name,sql FROM sqlite_master WHERE type='table' AND (name GLOB 'major_*' OR name GLOB 'minor_*') AND name NOT GLOB 'major_notes_fts*' AND name NOT GLOB 'major_note_chunks_fts*' AND name<>'major_transaction_guard' ORDER BY name");
    const result: Table[] = [];
    for (const row of rows) {
      const cacheKey=String(row.sql);
      let columns=columnCache.get(cacheKey);
      if (!columns) {
        columns=(await this.db.all(`PRAGMA table_info(${quoted(String(row.name))})`)).map(column => ({ name:String(column.name),type:String(column.type),pk:Number(column.pk) }));
        columnCache.set(cacheKey,columns);
      }
      const time = ['recorded_at','created_at','opened_at','built_at','hlc'].find(name => columns.some(column => column.name === name));
      const keys = columns.filter(column => column.pk).sort((a,b) => a.pk-b.pk).map(column => column.name);
      const order = [...new Set([...(time ? [time] : []), ...keys])].map(quoted).join(',') || 'rowid';
      result.push({ name: String(row.name), columns, order });
    }
    return result;
  }
  private projection(table: Table): string {
    const groups: string[] = [];
    for (let index=0;index<table.columns.length;index+=12) groups.push('json_object(' + table.columns.slice(index,index+12).map(column => {
      const value=quoted(column.name);
      return `'${column.name.replaceAll("'","''")}',CASE WHEN typeof(${value})='blob' THEN json_object('$encoding','hex','data',hex(${value})) ELSE ${value} END`;
    }).join(',') + ')');
    // json_patch removes explicit null fields; merge fragments as JSON text instead.
    return groups.length===1?groups[0]!:"'{' || " + groups.map(group=>`substr(${group},2,length(${group})-2)`).join(" || ',' || ") + " || '}'";
  }
  async list(input: ListInput = {}) {
    return this.db.transaction(async () => {
      const catalog = await this.tables();
      const table = catalog.find(table => table.name === (input.table ?? 'major_notes'));
      if (!table) throw new Error('Unknown record table');
      const limit = input.limit ?? 50;
      if (!Number.isInteger(limit) || limit < 1 || limit > 200) throw new Error('limit must be 1–200');
      let last = 0, ceiling: number;
      const descending=input.order==='desc';
      const scope = JSON.stringify([table.name,input.thread ?? null,input.project ?? null,input.order??'asc',input.since??null,input.until??null]);
      if (input.cursor) {
        let cursor;
        try { cursor = cursorDecode(input.cursor); } catch { throw new Error('Invalid cursor'); }
        if (cursor.scope !== scope || !Number.isSafeInteger(cursor.last) || !Number.isSafeInteger(cursor.ceiling) || cursor.last < 0 || cursor.ceiling < cursor.last) throw new Error('Cursor scope or range mismatch');
        last = cursor.last; ceiling = cursor.ceiling;
      } else ceiling = Number((await this.db.all(`SELECT coalesce(max(rowid),0) AS ceiling FROM ${quoted(table.name)}`))[0]!.ceiling);
      if(descending && !input.cursor) last=ceiling+1;
      let where = (descending?'rowid<?':'rowid>?')+' AND rowid<=?';
      const values: Value[] = [last,ceiling];
      if (input.thread) {
        if (!table.columns.some(column => column.name === 'thread_id')) throw new Error('This table has no thread scope');
        where += ' AND thread_id=?'; values.push(input.thread);
      }
      if (input.project) {
        if (table.name === 'major_notes') where += ' AND thread_id IN(SELECT id FROM major_threads WHERE project_id=?)';
        else if (table.columns.some(column => column.name === 'project_id')) where += ' AND project_id=?';
        else throw new Error('This table has no project scope');
        values.push(input.project);
      }
      const timeColumn=['recorded_at','created_at','opened_at','built_at'].find(name=>table.columns.some(column=>column.name===name));
      for(const [boundary,operator] of [[input.since,'>='],[input.until,'<=']] as const) if(boundary){if(!timeColumn || !Number.isFinite(Date.parse(boundary)))throw Error('Time filter requires a valid date and a dated table');where+=` AND ${quoted(timeColumn)}${operator}?`;values.push(new Date(boundary).toISOString());}
      const rows = await this.db.all(`SELECT rowid AS _cursor,${this.projection(table)} AS payload FROM ${quoted(table.name)} WHERE ${where} ORDER BY rowid ${descending?'DESC':'ASC'} LIMIT ?`, ...values, limit + 1);
      const page = rows.slice(0,limit);
      const total = Number((await this.db.all(`SELECT count(*) AS total FROM ${quoted(table.name)} WHERE ${where}`, ...values))[0]!.total);
      const records=page.map(row => JSON.parse(String(row.payload)));
      if(table.name==='major_notes') await hydrateNotes(this.db,records);
      return { table: table.name, records,
        record_locators: page.map(row => ({ table:table.name,rowid:Number(row._cursor) })),
        next_cursor: rows.length > limit ? cursorEncode({ scope,last:Number(page.at(-1)!._cursor),ceiling }) : null,
        snapshot_max_rowid: ceiling, remaining: Math.max(0,total-page.length), tables: catalog.map(table => table.name) };
    });
  }
  async get(input: GetInput) {
    if (!input.id?.trim() && !(input.table && Number.isSafeInteger(input.rowid) && input.rowid! > 0)) throw new Error('Provide id, or table and positive rowid');
    return this.db.transaction(async () => {
      const catalog = await this.tables();
      if (input.table && !catalog.some(table => table.name === input.table)) throw new Error('Unknown record table');
      for (const table of catalog.filter(table => !input.table || table.name === input.table)) {
        const key = table.columns.some(column => column.name === 'id') ? 'id' : table.columns.some(column => column.name === 'key') ? 'key' : null;
        if (!key && input.rowid === undefined) continue;
        const row = (await this.db.all(`SELECT ${this.projection(table)} AS payload FROM ${quoted(table.name)} WHERE ${input.rowid !== undefined ? 'rowid' : quoted(key!)}=?`,input.rowid ?? input.id!))[0];
        if (!row) continue;
        const related: Record<string, Row[]> = {};
        const record = JSON.parse(String(row.payload));
        if (table.name === 'major_notes') {
          await hydrateNotes(this.db,[record]);
          for (const name of ['major_mentions','major_refs','major_sources']) related[name] = await this.db.all(`SELECT * FROM ${quoted(name)} WHERE note_id=?`,record.id);
          related.major_edges = await this.db.all('SELECT * FROM major_edges WHERE src_id=? OR dst_id=? ORDER BY created_at,id',record.id,record.id);
        }
        return { table: table.name, record, related };
      }
      throw new Error('Record not found');
    });
  }
  async export() {
    const id = this.runtime.id('x');
    const manifest = await this.db.transaction(async () => {
      const tables = await this.tables();
      const counts: Record<string, number> = {};
      for (const table of tables) counts[table.name] = Number((await this.db.all(`SELECT count(*) AS count FROM ${quoted(table.name)}`))[0]!.count);
      const manifest = { format: 'cognitive-workspace-markdown-v3', total_records: Object.values(counts).reduce((a,b) => a+b,0), counts,
        text_representation:'The complete JSON record retains the exact text value, including trailing newlines; a literal copy follows for human reading.',
        columns: Object.fromEntries(tables.map(table => [table.name,table.columns])),
        excluded: { major_note_chunks_fts:'Rebuildable full-text index and shadows duplicate entry segments.', major_notes_fts: 'Rebuildable full-text index and its shadow tables duplicate note text.', major_transaction_guard: 'Ephemeral transaction guard.', operator_exports: 'Generated artifacts excluded to avoid recursive exports.', operator_export_rows: 'Generated artifact payloads excluded to avoid recursive exports.' },
        binary_encoding: 'BLOB fields are tagged {$encoding:"hex",data:"..."}; no bytes are discarded.',
        long_entries:'Large entries are stored losslessly across major_notes and major_note_chunks; each research entry is reconstructed in full below.' };
      await this.db.run('INSERT INTO operator_exports VALUES(?,?,?,?)',id,this.principal,JSON.stringify(manifest),this.runtime.now());
      for (let index=0;index<tables.length;index++) {
        const table = tables[index]!;
        await this.db.run(`INSERT INTO operator_export_rows(export_id,table_index,ordinal,payload) SELECT ?,?,row_number() OVER(ORDER BY ${table.order}),${this.projection(table)} FROM ${quoted(table.name)}`,id,index);
      }
      return manifest;
    });
    return { id, url: `${this.runtime.baseUrl ?? ''}/exports/${id}/download`, uri: `workspace-export://${id}`, manifest,
      text: `Full database snapshot ready: ${manifest.total_records} stored records. Download the Markdown artifact; its contents are not substituted by a summary.` };
  }
  async download(id: string): Promise<Response> {
    // Export rows are immutable after the atomic materialization commit; avoid a guard batch per streamed page.
    const read = (sql:string,...values:Value[]) => this.db.immutableRead ? this.db.immutableRead(sql,...values) : this.db.transaction(()=>this.db.all(sql,...values));
    const artifact = (await read('SELECT manifest FROM operator_exports WHERE id=? AND owner_principal=?',id,this.principal))[0];
    if (!artifact) return new Response('Export not found', { status:404 });
    const manifest = JSON.parse(String(artifact.manifest));
    let lastTable = -1, lastOrdinal = 0, emitted = 0, header = true;
    let buffered:Row[]=[];
    const encoder = new TextEncoder();
    const stream = new ReadableStream<Uint8Array>({
      pull: async controller => {
        try {
          if (header) { header=false; controller.enqueue(encoder.encode('# Cognitive Workspace — complete database export\n\n## Manifest\n\n```json\n'+JSON.stringify(manifest,null,2)+'\n```\n')); return; }
          if(!buffered.length) buffered = await read(`WITH candidates AS (SELECT table_index,ordinal,payload FROM operator_export_rows WHERE export_id=? AND (table_index>? OR (table_index=? AND ordinal>?)) ORDER BY table_index,ordinal LIMIT 1024), sized AS (SELECT *,sum(length(cast(payload AS BLOB))) OVER(ORDER BY table_index,ordinal) AS bytes FROM candidates) SELECT table_index,ordinal,payload FROM sized WHERE bytes<=16000000 ORDER BY table_index,ordinal`,id,lastTable,lastTable,lastOrdinal);
          if (!buffered.length) {
            if (emitted !== manifest.total_records) throw new Error('Export snapshot record count mismatch');
            controller.enqueue(encoder.encode(`\n<!-- END: ${emitted} records; complete snapshot -->\n`)); controller.close(); return;
          }
          let text = '';
          for (const row of [buffered.shift()!]) {
            lastTable=Number(row.table_index); lastOrdinal=Number(row.ordinal); emitted++;
            const table = Object.keys(manifest.counts)[lastTable]!;
            const record = JSON.parse(String(row.payload));
            if(table==='major_notes' && manifest.format==='cognitive-workspace-markdown-v3' && 'major_note_chunks' in manifest.counts) {
              const chunkTable=Object.keys(manifest.counts).indexOf('major_note_chunks');
              const chunks=manifest.counts.major_note_chunks?await read("SELECT payload FROM operator_export_rows WHERE export_id=? AND table_index=? AND json_extract(payload,'$.note_id')=? ORDER BY cast(json_extract(payload,'$.ordinal') AS INTEGER)",id,chunkTable,record.id):[];
              for(const chunk of chunks) record.text+=JSON.parse(String(chunk.payload)).text;
            }
            const raw = typeof record.text === 'string' ? record.text : null;
            const metadata = { ...record };
            // Keep already-created v1 artifact bytes stable across renderer upgrades.
            if (manifest.format === 'cognitive-workspace-markdown-v1' && raw !== null) delete metadata.text;
            const body = JSON.stringify(metadata,null,2), marker=fence(body);
            text += `\n## Record ${emitted}: ${table} / ${record.id ?? record.key ?? lastOrdinal}\n\n${marker}json\n${body}\n${marker}\n`;
            if (raw !== null) { const delimiter=fence(raw); const label = table === 'minor_digests' ? 'Derived summary — exact stored text' : table === 'major_sources' ? (manifest.format==='cognitive-workspace-markdown-v3'?'Attached text':'Verbatim source excerpt') : 'Original text'; text += `\n### ${label}\n\n${delimiter}text\n${raw}\n${delimiter}\n`; }
          }
          controller.enqueue(encoder.encode(text));
        } catch (error) { controller.error(error); }
      },
    });
    return new Response(stream,{headers:{'content-type':'text/markdown; charset=utf-8','content-disposition':`attachment; filename="cognitive-workspace-${id.replace(/[^a-zA-Z0-9_-]/g,'')}.md"`,'cache-control':'private, no-store','x-content-type-options':'nosniff'}});
  }
}
