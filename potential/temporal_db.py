"""
Temporal Database for CHRONOS

SQLite-based temporal index with full-text search and vector embeddings.
Optimized for time-range queries and semantic search.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import struct
import zlib
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

logger = logging.getLogger(__name__)

RAW_PAYLOAD_SCHEMA_VERSION = 1
MAX_RAW_PAYLOAD_BYTES = 100 * 1024 * 1024


def _json_safe(value: Any) -> Any:
    """Convert trusted in-process conversation values to JSON-safe primitives."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, datetime):
        return {"type": "datetime", "value": value.isoformat()}
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return _json_safe(asdict(value))
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    raise TypeError(f"Unsupported raw conversation value: {type(value).__name__}")


def _conversation_payload(conversation: Any) -> Dict[str, Any]:
    """Build a bounded, explicit JSON payload from a conversation object."""
    if is_dataclass(conversation):
        raw_conversation = asdict(conversation)
    else:
        field_names = (
            "id",
            "title",
            "create_time",
            "update_time",
            "models_used",
            "dominant_type",
            "quality_score",
            "total_tokens",
            "turn_count",
            "code_density",
            "url_density",
            "messages",
        )
        raw_conversation = {
            name: getattr(conversation, name)
            for name in field_names
            if hasattr(conversation, name)
        }
    safe_conversation = _json_safe(raw_conversation)
    if not isinstance(safe_conversation, dict):
        raise TypeError("Conversation payload must serialize to a dictionary")
    return {
        "schema_version": RAW_PAYLOAD_SCHEMA_VERSION,
        "conversation": safe_conversation,
    }


def _encode_raw_conversation(conversation: Any) -> bytes:
    """Encode a conversation as compressed JSON without executable objects."""
    serialized = json.dumps(
        _conversation_payload(conversation),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    if len(serialized) > MAX_RAW_PAYLOAD_BYTES:
        raise ValueError("Raw conversation exceeds the 100 MiB storage limit")
    return zlib.compress(serialized)


def _decode_raw_conversation(raw_data: bytes) -> Dict[str, Any]:
    """Decode only the versioned JSON raw format and reject legacy pickles."""
    decompressor = zlib.decompressobj()
    decoded = decompressor.decompress(raw_data, MAX_RAW_PAYLOAD_BYTES + 1)
    if decompressor.unconsumed_tail or len(decoded) > MAX_RAW_PAYLOAD_BYTES:
        raise ValueError("Compressed raw conversation exceeds the 100 MiB limit")
    decoded += decompressor.flush(MAX_RAW_PAYLOAD_BYTES + 1 - len(decoded))
    if len(decoded) > MAX_RAW_PAYLOAD_BYTES:
        raise ValueError("Compressed raw conversation exceeds the 100 MiB limit")
    try:
        payload = json.loads(decoded.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(
            "Raw conversation is not the safe JSON format; legacy pickle payloads are rejected"
        ) from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != RAW_PAYLOAD_SCHEMA_VERSION:
        raise ValueError("Unsupported raw conversation schema")
    conversation = payload.get("conversation")
    if not isinstance(conversation, dict):
        raise ValueError("Raw conversation payload is malformed")
    return conversation


@dataclass
class TemporalIndex:
    """Compressed temporal index entry for fast lookups"""
    conversation_id: str
    title: str
    create_time: datetime
    models_used: List[str]
    dominant_type: str
    quality_score: float
    token_count: int
    fingerprint: str
    
    # Searchable content (compressed)
    title_tokens: List[str] = field(default_factory=list)
    concept_tags: List[str] = field(default_factory=list)


@dataclass 
class TimeRange:
    """Time range specification for queries"""
    start: datetime
    end: datetime
    granularity: str = "day"  # day, week, month, year
    
    @classmethod
    def last_n_days(cls, n: int) -> 'TimeRange':
        end = datetime.now()
        start = end - timedelta(days=n)
        return cls(start=start, end=end)
    
    @classmethod
    def month(cls, year: int, month: int) -> 'TimeRange':
        start = datetime(year, month, 1)
        if month == 12:
            end = datetime(year + 1, 1, 1)
        else:
            end = datetime(year, month + 1, 1)
        return cls(start=start, end=end)
    
    @classmethod
    def year(cls, year: int) -> 'TimeRange':
        return cls(
            start=datetime(year, 1, 1),
            end=datetime(year + 1, 1, 1)
        )


class TemporalDatabase:
    """
    SQLite-based temporal database for CHRONOS.
    
    Features:
    - Time-indexed conversation storage
    - Full-text search with FTS5
    - Model-based filtering
    - Concept/tag indexing
    - Embedding storage for semantic search
    """
    
    SCHEMA_VERSION = 1
    
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        with self._get_connection() as conn:
            # Main conversations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    create_time REAL,
                    update_time REAL,
                    models_used TEXT,  -- JSON array
                    dominant_type TEXT,
                    quality_score REAL,
                    token_count INTEGER,
                    turn_count INTEGER,
                    code_density REAL,
                    url_density REAL,
                    fingerprint TEXT,
                    raw_data BLOB  -- Compressed full conversation
                )
            """)
            
            # Messages table for granular search
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT,
                    author_role TEXT,
                    model_slug TEXT,
                    content TEXT,
                    create_time REAL,
                    token_estimate INTEGER,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                )
            """)
            
            # FTS5 full-text search index
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                    content,
                    conversation_id UNINDEXED,
                    message_id UNINDEXED,
                    content='messages',
                    content_rowid='rowid'
                )
            """)
            
            # Concepts/tags table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS concepts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    first_seen REAL,
                    occurrence_count INTEGER DEFAULT 1,
                    related_concepts TEXT  -- JSON array
                )
            """)
            
            # Concept-conversation junction
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation_concepts (
                    conversation_id TEXT,
                    concept_id INTEGER,
                    relevance_score REAL,
                    PRIMARY KEY (conversation_id, concept_id),
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
                    FOREIGN KEY (concept_id) REFERENCES concepts(id)
                )
            """)
            
            # Model usage tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS model_usage (
                    model_slug TEXT,
                    conversation_id TEXT,
                    message_count INTEGER,
                    total_tokens INTEGER,
                    first_used REAL,
                    last_used REAL,
                    PRIMARY KEY (model_slug, conversation_id)
                )
            """)
            
            # Embeddings table for semantic search
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    conversation_id TEXT PRIMARY KEY,
                    embedding BLOB,  -- Packed float32 array
                    model_name TEXT,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                )
            """)
            
            # Indexes for common queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_time ON conversations(create_time)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_type ON conversations(dominant_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_quality ON conversations(quality_score)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages(conversation_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_msg_model ON messages(model_slug)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_msg_time ON messages(create_time)")
            
            # Schema version tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            conn.execute(
                "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                ("schema_version", str(self.SCHEMA_VERSION))
            )
            
            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with context management"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def insert_conversation(self, conv: Any, compress: bool = True) -> None:
        """Insert a conversation into the database"""
        with self._get_connection() as conn:
            # Serialize raw data
            raw_data = None
            if compress:
                raw_data = _encode_raw_conversation(conv)
            
            # Insert main conversation record
            conn.execute("""
                INSERT OR REPLACE INTO conversations 
                (id, title, create_time, update_time, models_used, dominant_type,
                 quality_score, token_count, turn_count, code_density, url_density,
                 fingerprint, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                conv.id,
                conv.title,
                conv.create_time.timestamp(),
                conv.update_time.timestamp(),
                json.dumps(conv.models_used),
                conv.dominant_type,
                conv.quality_score,
                conv.total_tokens,
                conv.turn_count,
                conv.code_density,
                conv.url_density,
                conv.get_fingerprint(),
                raw_data
            ))
            
            # Insert messages
            for msg in conv.messages:
                conn.execute("""
                    INSERT OR REPLACE INTO messages
                    (id, conversation_id, author_role, model_slug, content,
                     create_time, token_estimate)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    msg.id,
                    conv.id,
                    msg.author_role,
                    msg.model_slug,
                    msg.content,
                    msg.create_time.timestamp() if msg.create_time else None,
                    msg.token_estimate
                ))
            
            # Update model usage
            for model in conv.models_used:
                model_msgs = [m for m in conv.messages if m.model_slug == model]
                model_tokens = sum(m.token_estimate for m in model_msgs)
                
                conn.execute("""
                    INSERT INTO model_usage 
                    (model_slug, conversation_id, message_count, total_tokens, first_used, last_used)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(model_slug, conversation_id) DO UPDATE SET
                        message_count = excluded.message_count,
                        total_tokens = excluded.total_tokens
                """, (
                    model,
                    conv.id,
                    len(model_msgs),
                    model_tokens,
                    conv.create_time.timestamp(),
                    conv.update_time.timestamp()
                ))
            
            conn.commit()
    
    def bulk_insert(self, conversations: Iterator[Any],
                    batch_size: int = 100, 
                    progress_callback=None):
        """Bulk insert conversations with batching"""
        batch = []
        total_inserted = 0
        
        for conv in conversations:
            batch.append(conv)
            
            if len(batch) >= batch_size:
                for c in batch:
                    self.insert_conversation(c)
                total_inserted += len(batch)
                
                if progress_callback:
                    progress_callback(total_inserted)
                
                batch = []
        
        # Insert remaining
        for c in batch:
            self.insert_conversation(c)
        total_inserted += len(batch)
        
        # Rebuild FTS index
        self._rebuild_fts_index()
        
        return total_inserted
    
    def _rebuild_fts_index(self):
        """Rebuild the FTS5 search index"""
        with self._get_connection() as conn:
            conn.execute("INSERT INTO messages_fts(messages_fts) VALUES('rebuild')")
            conn.commit()
    
    def search_full_text(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Full-text search across all messages"""
        with self._get_connection() as conn:
            results = conn.execute("""
                SELECT 
                    m.conversation_id,
                    c.title,
                    m.content,
                    m.model_slug,
                    m.create_time,
                    rank
                FROM messages_fts f
                JOIN messages m ON f.rowid = m.rowid
                JOIN conversations c ON m.conversation_id = c.id
                WHERE messages_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, limit)).fetchall()
            
            return [dict(r) for r in results]
    
    def get_conversations_in_range(self, time_range: TimeRange) -> List[Dict[str, Any]]:
        """Get conversations within a time range"""
        with self._get_connection() as conn:
            results = conn.execute("""
                SELECT id, title, create_time, models_used, dominant_type,
                       quality_score, token_count, turn_count
                FROM conversations
                WHERE create_time >= ? AND create_time < ?
                ORDER BY create_time DESC
            """, (time_range.start.timestamp(), time_range.end.timestamp())).fetchall()
            
            return [dict(r) for r in results]
    
    def get_model_usage_stats(self) -> Dict[str, Any]:
        """Get aggregated model usage statistics"""
        with self._get_connection() as conn:
            results = conn.execute("""
                SELECT 
                    model_slug,
                    COUNT(DISTINCT conversation_id) as conversation_count,
                    SUM(message_count) as total_messages,
                    SUM(total_tokens) as total_tokens,
                    MIN(first_used) as first_used,
                    MAX(last_used) as last_used
                FROM model_usage
                WHERE model_slug IS NOT NULL
                GROUP BY model_slug
                ORDER BY total_tokens DESC
            """).fetchall()
            
            return {
                r['model_slug']: {
                    'conversation_count': r['conversation_count'],
                    'total_messages': r['total_messages'],
                    'total_tokens': r['total_tokens'],
                    'first_used': datetime.fromtimestamp(r['first_used']) if r['first_used'] else None,
                    'last_used': datetime.fromtimestamp(r['last_used']) if r['last_used'] else None
                }
                for r in results
            }
    
    def get_conversation_by_id(self, conv_id: str, include_raw: bool = False) -> Optional[Dict[str, Any]]:
        """Get a specific conversation by ID"""
        with self._get_connection() as conn:
            result = conn.execute("""
                SELECT * FROM conversations WHERE id = ?
            """, (conv_id,)).fetchone()
            
            if not result:
                return None
            
            conv_dict = dict(result)
            
            # Decompress raw data if requested
            if include_raw and conv_dict.get('raw_data'):
                conv_dict['raw'] = _decode_raw_conversation(conv_dict['raw_data'])
            
            # Get messages
            messages = conn.execute("""
                SELECT * FROM messages WHERE conversation_id = ? ORDER BY create_time
            """, (conv_id,)).fetchall()
            
            conv_dict['messages'] = [dict(m) for m in messages]
            
            
            return conv_dict
    
    def get_conversation_messages(self, conv_id: str) -> List[Dict[str, Any]]:
        """Get just the messages for a conversation"""
        with self._get_connection() as conn:
            messages = conn.execute("""
                SELECT * FROM messages WHERE conversation_id = ? ORDER BY create_time
            """, (conv_id,)).fetchall()
            return [dict(m) for m in messages]
    
    def get_conversations_by_model(self, model_slug: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get conversations that used a specific model"""
        with self._get_connection() as conn:
            results = conn.execute("""
                SELECT c.* 
                FROM conversations c
                WHERE c.models_used LIKE ?
                ORDER BY c.create_time DESC
                LIMIT ?
            """, (f'%"{model_slug}"%', limit)).fetchall()
            
            return [dict(r) for r in results]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get overall database statistics"""
        with self._get_connection() as conn:
            stats = {}
            
            # Conversation counts
            stats['total_conversations'] = conn.execute(
                "SELECT COUNT(*) FROM conversations"
            ).fetchone()[0]
            
            stats['total_messages'] = conn.execute(
                "SELECT COUNT(*) FROM messages"
            ).fetchone()[0]
            
            stats['total_tokens'] = conn.execute(
                "SELECT SUM(token_count) FROM conversations"
            ).fetchone()[0] or 0
            
            # Type distribution
            type_dist = conn.execute("""
                SELECT dominant_type, COUNT(*) as count
                FROM conversations
                GROUP BY dominant_type
            """).fetchall()
            stats['type_distribution'] = {r[0]: r[1] for r in type_dist}
            
            # Quality distribution
            quality_dist = conn.execute("""
                SELECT 
                    CASE 
                        WHEN quality_score >= 0.8 THEN 'excellent'
                        WHEN quality_score >= 0.6 THEN 'good'
                        WHEN quality_score >= 0.4 THEN 'fair'
                        ELSE 'low'
                    END as tier,
                    COUNT(*) as count
                FROM conversations
                GROUP BY tier
            """).fetchall()
            stats['quality_distribution'] = {r[0]: r[1] for r in quality_dist}
            
            # Date range
            date_range = conn.execute("""
                SELECT MIN(create_time), MAX(create_time)
                FROM conversations
            """).fetchone()
            if date_range[0]:
                stats['date_range'] = {
                    'earliest': datetime.fromtimestamp(date_range[0]),
                    'latest': datetime.fromtimestamp(date_range[1])
                }
            
            # Model stats
            stats['model_usage'] = self.get_model_usage_stats()
            
            return stats
    
    def store_embedding(self, conversation_id: str, embedding: List[float], model_name: str):
        """Store an embedding vector for a conversation"""
        with self._get_connection() as conn:
            # Pack floats as binary
            embedding_blob = struct.pack(f'{len(embedding)}f', *embedding)
            
            conn.execute("""
                INSERT OR REPLACE INTO embeddings (conversation_id, embedding, model_name)
                VALUES (?, ?, ?)
            """, (conversation_id, embedding_blob, model_name))
            
            conn.commit()
    
    def search_by_embedding(self, query_embedding: List[float], 
                           limit: int = 10) -> List[Tuple[str, float]]:
        """
        Search conversations by embedding similarity.
        Returns (conversation_id, similarity_score) tuples.
        
        Note: For production, consider using a vector database like Chroma or Faiss.
        This is a simple brute-force implementation.
        """
        import numpy as np
        
        query_vec = np.array(query_embedding)
        
        with self._get_connection() as conn:
            results = conn.execute("""
                SELECT conversation_id, embedding FROM embeddings
            """).fetchall()
            
            similarities = []
            for row in results:
                stored_vec = np.array(struct.unpack(
                    f'{len(row["embedding"])//4}f', 
                    row['embedding']
                ))
                
                # Cosine similarity
                similarity = np.dot(query_vec, stored_vec) / (
                    np.linalg.norm(query_vec) * np.linalg.norm(stored_vec)
                )
                similarities.append((row['conversation_id'], float(similarity)))
            
            # Sort by similarity descending
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            return similarities[:limit]
