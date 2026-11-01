-- Additive lossless storage for long research entries; existing notes are untouched.
CREATE TABLE major_note_chunks (
  note_id TEXT NOT NULL,
  ordinal INTEGER NOT NULL,
  text TEXT NOT NULL,
  PRIMARY KEY(note_id,ordinal)
);
CREATE VIRTUAL TABLE major_note_chunks_fts USING fts5(text,content='major_note_chunks',content_rowid='rowid');
CREATE TRIGGER major_note_chunks_ai AFTER INSERT ON major_note_chunks BEGIN
  INSERT INTO major_note_chunks_fts(rowid,text) VALUES(new.rowid,new.text);
END;
CREATE TRIGGER major_note_chunks_ad AFTER DELETE ON major_note_chunks BEGIN
  INSERT INTO major_note_chunks_fts(major_note_chunks_fts,rowid,text) VALUES('delete',old.rowid,old.text);
END;
CREATE TRIGGER major_note_chunks_au AFTER UPDATE ON major_note_chunks BEGIN
  INSERT INTO major_note_chunks_fts(major_note_chunks_fts,rowid,text) VALUES('delete',old.rowid,old.text);
  INSERT INTO major_note_chunks_fts(rowid,text) VALUES(new.rowid,new.text);
END;
UPDATE major_meta SET value='4' WHERE key='schema_version';
