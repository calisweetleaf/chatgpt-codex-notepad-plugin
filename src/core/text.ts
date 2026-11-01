import type { Database, Row } from '../store/database.js';

// Keep physical D1 rows small; reconstruct the original text at every public read.
export const textLimit = 4_000_000;
export function textParts(text: string): string[] {
  const parts: string[] = [];
  for (let start=0; start<text.length;) {
    let end=Math.min(start+24000,text.length);
    if (end<text.length && /[\uD800-\uDBFF]/.test(text[end-1]!)) end--;
    parts.push(text.slice(start,end)); start=end;
  }
  return parts;
}
export async function hydrateNotes(db: Database, rows: Row[]): Promise<Row[]> {
  const byId=new Map(rows.map(row=>[String(row.id),row]));
  const ids=[...byId.keys()];
  for (let start=0;start<ids.length;start+=8) {
    const batch=ids.slice(start,start+8);
    const chunks=await db.all(`SELECT note_id,ordinal,text FROM major_note_chunks WHERE note_id IN(${batch.map(()=>'?').join(',')}) ORDER BY note_id,ordinal`,...batch);
    for (const chunk of chunks) { const row=byId.get(String(chunk.note_id)); if(row) row.text=String(row.text)+String(chunk.text); }
  }
  return rows;
}
