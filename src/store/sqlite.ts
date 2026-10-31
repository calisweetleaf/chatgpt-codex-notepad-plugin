import { DatabaseSync } from 'node:sqlite';
import { AsyncLocalStorage } from 'node:async_hooks';
import type { Database, Row, Value } from './database.js';

/** Local implementation and executable contract for the portable engine. */
export class SQLiteDatabase implements Database {
  private readonly connection: DatabaseSync;
  private queue: Promise<unknown> = Promise.resolve();
  private scope = new AsyncLocalStorage<boolean>();
  constructor(path = ':memory:') {
    this.connection = new DatabaseSync(path);
    this.connection.exec('PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;');
  }
  migrate(sql: string): void { this.connection.exec(sql); }
  close(): void { this.connection.close(); }
  async all<T extends Row = Row>(sql: string, ...values: Value[]): Promise<T[]> {
    if (!this.scope.getStore()) return this.transaction(() => this.all<T>(sql, ...values));
    return this.connection.prepare(sql).all(...values) as T[];
  }
  async run(sql: string, ...values: Value[]): Promise<void> {
    if (!this.scope.getStore()) return this.transaction(() => this.run(sql, ...values));
    this.connection.prepare(sql).run(...values);
  }
  async transaction<T>(work: (database: Database) => Promise<T>): Promise<T> {
    if (this.scope.getStore()) throw new Error('Nested transactions are not supported');
    const execute = async (): Promise<T> => {
      this.connection.exec('BEGIN IMMEDIATE');
      try {
        const result = await this.scope.run(true, () => work(this));
        this.connection.exec('COMMIT');
        return result;
      } catch (error) {
        this.connection.exec('ROLLBACK');
        throw error;
      }
    };
    const pending = this.queue.then(execute, execute);
    this.queue = pending.catch(() => undefined);
    return pending;
  }
}
