-- Identity and bookkeeping
CREATE TABLE major_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
-- keys: schema_version, node_id, timezone, created_at

CREATE TABLE major_projects (
  id TEXT PRIMARY KEY,                 -- 'p_' + ULID
  slug TEXT NOT NULL UNIQUE,           -- normalized lowercase
  title TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE major_handles (
  id TEXT PRIMARY KEY,                 -- 'h_' + ULID
  name TEXT NOT NULL,                  -- display form, e.g. 'Varys'
  name_norm TEXT NOT NULL,             -- casefolded, whitespace-collapsed
  kind TEXT NOT NULL DEFAULT 'concept'
    CHECK (kind IN ('system','component','symbol','concept','artifact','person')),
  project_id TEXT,                     -- optional home project
  parent_id TEXT,                      -- optional component-of, never required
  note TEXT,                           -- one-line gloss, optional
  created_at TEXT NOT NULL,
  UNIQUE (name_norm, project_id)
);

CREATE TABLE major_sessions (
  id TEXT PRIMARY KEY,                 -- 's_' + ULID; returned to the model as a short handle
  client TEXT NOT NULL CHECK (client IN ('chatgpt','codex','local','other')),
  principal TEXT NOT NULL,             -- authenticated identity (email or token name)
  label TEXT,                          -- optional model- or user-supplied alias
  project_id TEXT,
  prev_session_id TEXT,                -- previous session of the same principal+project
  local_day TEXT NOT NULL,             -- 'YYYY-MM-DD' in workspace timezone
  opened_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  origin_node TEXT NOT NULL
);
CREATE INDEX major_sessions_principal ON major_sessions(principal, last_seen_at);

CREATE TABLE major_threads (
  id TEXT PRIMARY KEY,                 -- 't_' + ULID
  project_id TEXT,
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','parked','closed')),
  parent_thread_id TEXT,
  opened_in_session TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL             -- mirrors the latest thread event
);

CREATE TABLE major_notes (
  rowid INTEGER PRIMARY KEY,           -- local watermark; not stable across nodes
  id TEXT NOT NULL UNIQUE,             -- 'n_' + ULID; stable across nodes
  session_id TEXT NOT NULL,
  thread_id TEXT NOT NULL,
  seq INTEGER NOT NULL,                -- order within the session
  local_day TEXT NOT NULL,
  recorded_at TEXT NOT NULL,           -- server clock, ISO-8601 UTC
  hlc TEXT NOT NULL,                   -- hybrid logical clock for sync ordering
  author_client TEXT NOT NULL,
  author_principal TEXT NOT NULL,
  kind TEXT NOT NULL DEFAULT 'note',
  kind_source TEXT NOT NULL DEFAULT 'default' CHECK (kind_source IN ('default','hint','inferred')),
  move TEXT,                           -- continue | branch | pivot | return | park | close
  emphasis INTEGER NOT NULL DEFAULT 0 CHECK (emphasis BETWEEN 0 AND 2),
  text TEXT NOT NULL,                  -- the note; never updated except by redaction
  content_hash TEXT NOT NULL,          -- sha256(text) for dedupe hints
  idempotency_key TEXT UNIQUE,
  origin_node TEXT NOT NULL,
  redacted_at TEXT                     -- set only by operator redaction
);
CREATE INDEX major_notes_thread ON major_notes(thread_id, recorded_at);
CREATE INDEX major_notes_session ON major_notes(session_id, seq);
CREATE INDEX major_notes_day ON major_notes(local_day);

CREATE VIRTUAL TABLE major_notes_fts USING fts5(
  text, content='major_notes', content_rowid='rowid', tokenize='unicode61 remove_diacritics 2'
);
-- kept in sync by AFTER INSERT/UPDATE triggers; rebuildable with 'rebuild' command

CREATE TABLE major_mentions (          -- write-time index; rebuildable from text + handles
  note_id TEXT NOT NULL,
  handle_id TEXT NOT NULL,
  source TEXT NOT NULL CHECK (source IN ('hint','detected')),
  PRIMARY KEY (note_id, handle_id)
);

CREATE TABLE major_refs (              -- pointers into code/docs; never content copies
  id TEXT PRIMARY KEY,
  note_id TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('repo','branch','commit','file','symbol','doc','url','other')),
  locator TEXT NOT NULL,               -- 'github.com/x/y', 'src/router.py#Router.forward'
  version TEXT,                        -- optional version label or SHA
  created_at TEXT NOT NULL
);

CREATE TABLE major_edges (             -- append-only; removal is a new row with retracted=1
  id TEXT PRIMARY KEY,
  src_kind TEXT NOT NULL CHECK (src_kind IN ('note','thread','handle')),
  src_id TEXT NOT NULL,
  relation TEXT NOT NULL,
  dst_kind TEXT NOT NULL CHECK (dst_kind IN ('note','thread','handle')),
  dst_id TEXT NOT NULL,
  why TEXT,
  created_by TEXT NOT NULL,            -- 'server' or a principal
  created_at TEXT NOT NULL,
  hlc TEXT NOT NULL,
  retracted INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX major_edges_src ON major_edges(src_id, relation);
CREATE INDEX major_edges_dst ON major_edges(dst_id, relation);

CREATE TABLE major_events (            -- every mutation of a mutable header; the sync log
  id TEXT PRIMARY KEY,
  hlc TEXT NOT NULL,
  actor TEXT NOT NULL,
  type TEXT NOT NULL,                  -- thread.status, thread.retitle, thread.reparent,
                                       -- note.refile, note.redact, handle.create, session.open, ...
  target_id TEXT NOT NULL,
  payload TEXT NOT NULL,               -- JSON
  origin_node TEXT NOT NULL
);
CREATE INDEX major_events_hlc ON major_events(hlc);
CREATE TABLE minor_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
-- keys: schema_version, generation, built_against_major_watermark, node_id

CREATE TABLE minor_collections (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL CHECK (kind IN ('theme','period','category','cluster','comparison','reading_list')),
  title TEXT NOT NULL,
  description TEXT,
  created_by TEXT NOT NULL,            -- principal or 'job:<name>'
  method TEXT NOT NULL,                -- 'manual' | 'fts' | 'embedding' | 'model:<id>'
  generation INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','stale','retired')),
  created_at TEXT NOT NULL
);

CREATE TABLE minor_members (
  collection_id TEXT NOT NULL,
  member_kind TEXT NOT NULL CHECK (member_kind IN ('note','thread','handle','session')),
  member_id TEXT NOT NULL,             -- ID in major; no FK by design
  weight REAL,
  rationale TEXT,
  PRIMARY KEY (collection_id, member_kind, member_id)
);

CREATE TABLE minor_digests (           -- condensed context, always citing its sources
  id TEXT PRIMARY KEY,
  scope_kind TEXT NOT NULL CHECK (scope_kind IN ('thread','session','day','project','collection','handle')),
  scope_id TEXT NOT NULL,
  text TEXT NOT NULL,
  source_note_ids TEXT NOT NULL,       -- JSON array of major note IDs
  covers_until_watermark INTEGER NOT NULL,
  author TEXT NOT NULL,                -- principal or model id
  generation INTEGER NOT NULL,
  stale INTEGER NOT NULL DEFAULT 0,
  built_at TEXT NOT NULL
);
CREATE INDEX minor_digests_scope ON minor_digests(scope_kind, scope_id, built_at);

CREATE TABLE minor_associations (      -- machine-suggested links, separate from authored edges
  a_kind TEXT NOT NULL, a_id TEXT NOT NULL,
  b_kind TEXT NOT NULL, b_id TEXT NOT NULL,
  relation TEXT NOT NULL,              -- 'echo' | 'similar' | 'recurs' | 'co_mentioned'
  score REAL NOT NULL,
  method TEXT NOT NULL,
  generation INTEGER NOT NULL,
  PRIMARY KEY (a_id, b_id, relation)
);

CREATE TABLE minor_embeddings (        -- phase 5; optional
  note_id TEXT NOT NULL,
  model TEXT NOT NULL,
  dim INTEGER NOT NULL,
  vec BLOB NOT NULL,                   -- little-endian float32
  PRIMARY KEY (note_id, model)
);

CREATE TABLE minor_recall_cache (
  key TEXT PRIMARY KEY,                -- hash(view, scope, query, budget)
  payload TEXT NOT NULL,
  major_watermark INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE minor_jobs (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('queued','running','done','failed')),
  params TEXT, error TEXT,
  created_at TEXT NOT NULL, finished_at TEXT
);

CREATE UNIQUE INDEX major_notes_seq ON major_notes(session_id, seq);
CREATE UNIQUE INDEX major_handles_global ON major_handles(name_norm) WHERE project_id IS NULL;
CREATE INDEX major_notes_hash ON major_notes(content_hash, recorded_at);
CREATE TRIGGER major_notes_insert AFTER INSERT ON major_notes BEGIN
  INSERT INTO major_notes_fts(rowid,text) VALUES(new.rowid,new.text);
END;
CREATE TRIGGER major_notes_delete AFTER DELETE ON major_notes BEGIN
  INSERT INTO major_notes_fts(major_notes_fts,rowid,text) VALUES('delete',old.rowid,old.text);
END;
CREATE TRIGGER major_notes_update AFTER UPDATE OF text ON major_notes BEGIN
  INSERT INTO major_notes_fts(major_notes_fts,rowid,text) VALUES('delete',old.rowid,old.text);
  INSERT INTO major_notes_fts(rowid,text) VALUES(new.rowid,new.text);
END;
CREATE TABLE major_session_state (
  session_id TEXT PRIMARY KEY,
  active_thread_id TEXT,
  return_thread_id TEXT
);
