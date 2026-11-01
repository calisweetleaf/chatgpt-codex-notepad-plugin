-- Additive operator visibility. Existing research records are untouched.
CREATE TABLE major_sources (
  id TEXT PRIMARY KEY,
  note_id TEXT NOT NULL,
  text TEXT NOT NULL,
  locator TEXT,
  recorded_at TEXT NOT NULL,
  author_principal TEXT NOT NULL
);
--> statement-breakpoint
CREATE INDEX major_sources_note ON major_sources(note_id);
--> statement-breakpoint
CREATE TABLE major_activity (
  id TEXT PRIMARY KEY,
  recorded_at TEXT NOT NULL,
  principal TEXT NOT NULL,
  operation TEXT NOT NULL,
  receipt TEXT NOT NULL
);
--> statement-breakpoint
CREATE TABLE operator_exports (
  id TEXT PRIMARY KEY,
  owner_principal TEXT NOT NULL,
  manifest TEXT NOT NULL,
  created_at TEXT NOT NULL
);
--> statement-breakpoint
CREATE TABLE operator_export_rows (
  export_id TEXT NOT NULL,
  table_index INTEGER NOT NULL,
  ordinal INTEGER NOT NULL,
  payload TEXT NOT NULL,
  PRIMARY KEY(export_id,table_index,ordinal)
);
