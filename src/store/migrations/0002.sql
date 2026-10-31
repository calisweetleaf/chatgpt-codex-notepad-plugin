-- Every D1 transaction validates its starting revision inside the atomic batch.
CREATE TABLE major_transaction_guard (
  id TEXT PRIMARY KEY,
  valid INTEGER NOT NULL CONSTRAINT transaction_snapshot_current CHECK(valid=1)
);
INSERT INTO major_meta(key,value) VALUES('transaction_revision','0');
