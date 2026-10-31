export type Row = Record<string, string | number | null>;
export type Value = string | number | null;

/** Core SQL boundary. A transaction validates a coherent committed read snapshot and
 * atomically applies writes. Reads must not depend on writes queued in that callback:
 * D1 stages writes until its revision-guarded batch commits. Construct new rows in core.
 * A conflicting callback may be replayed; do not perform external effects inside it.
 */
export interface Database {
  all<T extends Row = Row>(sql: string, ...values: Value[]): Promise<T[]>;
  run(sql: string, ...values: Value[]): Promise<void>;
  transaction<T>(work: (database: Database) => Promise<T>): Promise<T>;
}
