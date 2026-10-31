import type { Database, Row, Value } from './database.js';

type Statement = { bind(...values: Value[]): Statement; all<T>(): Promise<{ results: T[] }> };
export interface D1Binding {
  withSession(bookmark: 'first-primary'): {
    prepare(sql: string): Statement;
    batch(statements: Statement[]): Promise<unknown>;
  };
}
type Session = ReturnType<D1Binding['withSession']>;

/** Snapshot reads plus a guarded atomic batch. Callbacks must not read their staged writes.
 * All writers must use this adapter so transaction_revision covers every mutation.
 * Only a proven guard conflict is retried; uncertain network results propagate to the caller.
 */
export class D1Store implements Database {
  private queue: Promise<unknown> = Promise.resolve();
  private active?: { session: Session; writes: Statement[] };
  constructor(private binding: D1Binding, private attempts = 5) {}
  async all<T extends Row = Row>(sql: string, ...values: Value[]): Promise<T[]> {
    if (!this.active) throw new Error('D1 queries require a transaction');
    return (await this.active.session.prepare(sql).bind(...values).all<T>()).results;
  }
  async run(sql: string, ...values: Value[]): Promise<void> {
    if (!this.active) throw new Error('D1 writes require a transaction');
    this.active.writes.push(this.active.session.prepare(sql).bind(...values));
  }
  async transaction<T>(work: (database: Database) => Promise<T>): Promise<T> {
    const execute = async (): Promise<T> => {
      for (let attempt = 0; attempt < this.attempts; attempt++) {
        const session = this.binding.withSession('first-primary');
        this.active = { session, writes: [] };
        try {
          const revision = (await this.all("SELECT coalesce((SELECT value FROM major_meta WHERE key='transaction_revision'),'0') AS value"))[0]!.value;
          const result = await work(this);
          const token = crypto.randomUUID();
          const guard = session.prepare("INSERT INTO major_transaction_guard(id,valid) VALUES(?,CASE WHEN coalesce((SELECT value FROM major_meta WHERE key='transaction_revision'),'0')=? THEN 1 ELSE 0 END)").bind(token, revision);
          const writes = this.active.writes;
          const bump = session.prepare("INSERT INTO major_meta(key,value) VALUES('transaction_revision','1') ON CONFLICT(key) DO UPDATE SET value=cast(cast(value AS INTEGER)+1 AS TEXT)");
          const cleanup = session.prepare('DELETE FROM major_transaction_guard WHERE id=?').bind(token);
          await session.batch([guard, ...writes, ...(writes.length ? [bump] : []), cleanup]);
          return result;
        } catch (error) {
          const detail = error instanceof Error ? `${error.message} ${String(error.cause ?? '')}` : String(error);
          if (!detail.includes('transaction_snapshot_current') || attempt === this.attempts - 1) throw error;
        } finally { this.active = undefined; }
      }
      throw new Error('D1 transaction retry budget exhausted');
    };
    const pending = this.queue.then(execute, execute);
    this.queue = pending.catch(() => undefined);
    return pending;
  }
}
