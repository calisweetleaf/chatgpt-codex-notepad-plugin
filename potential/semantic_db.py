"""SQLite-backed semantic projection with deterministic scope isolation."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import sqlite3
import uuid
from collections.abc import Iterable, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional

import aiosqlite
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from core.modality_bridge import UnifiedModalityEncoder


DEFAULT_SCOPE_KEY = "global"
SEMANTIC_PROJECTION_EMBEDDING_DIMENSION = 384


@dataclass(frozen=True)
class SemanticProjectionInventoryReconciliation:
    """Counts removed from a service-owned semantic projection database.

    ``SemanticMemoryDB`` is also used by the source-only knowledge-graph lane,
    where relationships, clusters, and access logs are meaningful.  A
    ``MemoryArchiveService`` runtime root has a different ownership contract:
    only its catalogued, USMS-authenticated projection rows may remain there.
    This result makes a destructive reconciliation auditable without treating
    generic semantic-database state as canonical archive state.
    """

    removed_memories: int
    removed_relationships: int
    removed_cluster_mappings: int
    removed_clusters: int
    removed_access_logs: int

    @property
    def removed_dependent_rows(self) -> int:
        """Return the number of non-memory semantic artifacts removed."""
        return (
            self.removed_relationships
            + self.removed_cluster_mappings
            + self.removed_clusters
            + self.removed_access_logs
        )


class SemanticProjectionIntegrityError(RuntimeError):
    """A persisted semantic projection no longer matches its declared source."""

    def __init__(self, memory_id: int, field: str, reason: str) -> None:
        self.memory_id = memory_id
        self.field = field
        super().__init__(
            f"semantic projection {memory_id} failed {field} validation: {reason}"
        )


class SemanticMemoryDB:
    """Semantic Memory Database for AI agents with vector embeddings and clustering."""
    
    def __init__(self, db_path: str = "rag_memory.db", model_path: Optional[str] = None):
        """Initialize the semantic memory database."""
        self.db_path = db_path
        self.text_encoder = UnifiedModalityEncoder(embed_dim=384)
        self.logger = logging.getLogger(__name__)
        self._initialized = False
        self._initialization_lock = asyncio.Lock()
        self._keepalive_connection: Optional[aiosqlite.Connection] = None

        if db_path == ":memory:":
            instance_id = uuid.uuid4().hex
            self._connect_path = f"file:semantic_memory_db_{instance_id}?mode=memory&cache=shared"
            self._connect_uri = True
        else:
            self._connect_path = db_path
            self._connect_uri = False

    async def _configure_connection(self, db: aiosqlite.Connection) -> None:
        """Enable integrity and bounded-lock behavior on a connection."""
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute("PRAGMA busy_timeout = 5000")

    @asynccontextmanager
    async def _open_connection(self) -> AsyncIterator[aiosqlite.Connection]:
        """Yield a configured database connection and close it afterward."""
        db = await aiosqlite.connect(self._connect_path, uri=self._connect_uri)
        try:
            await self._configure_connection(db)
            yield db
        finally:
            await db.close()

    async def initialize(self) -> None:
        """Initialize or migrate the database schema."""
        if self._initialized:
            return
        async with self._initialization_lock:
            if self._initialized:
                return

            if self.db_path == ":memory:":
                if self._keepalive_connection is None:
                    self._keepalive_connection = await aiosqlite.connect(
                        self._connect_path,
                        uri=self._connect_uri,
                    )
                    await self._configure_connection(self._keepalive_connection)
                await self._ensure_schema(self._keepalive_connection)
                await self._keepalive_connection.commit()
            else:
                async with self._open_connection() as db:
                    mode_cursor = await db.execute("PRAGMA journal_mode")
                    mode_row = await mode_cursor.fetchone()
                    journal_mode = str(mode_row[0]).lower() if mode_row else ""
                    if journal_mode != "wal":
                        mode_cursor = await db.execute("PRAGMA journal_mode = WAL")
                        mode_row = await mode_cursor.fetchone()
                        journal_mode = str(mode_row[0]).lower() if mode_row else ""
                    if journal_mode != "wal":
                        raise sqlite3.DatabaseError(
                            "semantic projection database requires SQLite WAL mode"
                        )
                    await self._ensure_schema(db)
                    await db.commit()

            self._initialized = True
            self.logger.info(f"Database initialized at {self.db_path}")

    async def _ensure_schema(self, db: aiosqlite.Connection) -> None:
        """Ensure database schema is created in the given connection."""
        # Create main memories table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                embedding BLOB,
                scope_key TEXT NOT NULL DEFAULT 'global',
                content_hash TEXT NOT NULL UNIQUE,
                memory_type TEXT DEFAULT 'observation',
                importance REAL DEFAULT 0.5,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                metadata JSON
            )
        ''')

        columns_cursor = await db.execute("PRAGMA table_info(memories)")
        columns = {row[1] for row in await columns_cursor.fetchall()}
        scope_column_added = "scope_key" not in columns
        if scope_column_added:
            await db.execute(
                "ALTER TABLE memories ADD COLUMN scope_key TEXT NOT NULL DEFAULT 'global'"
            )

        if scope_column_added:
            legacy_cursor = await db.execute(
                "SELECT id, content, content_hash, scope_key FROM memories"
            )
            for memory_id, content, content_hash, scope_key in await legacy_cursor.fetchall():
                normalized_scope = self._normalize_scope_key(scope_key)
                scoped_hash = self._generate_hash(content, normalized_scope)
                legacy_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                if content_hash is None or content_hash == legacy_hash:
                    await db.execute(
                        "UPDATE memories SET scope_key = ?, content_hash = ? WHERE id = ?",
                        (normalized_scope, scoped_hash, memory_id),
                    )
        
        # Create semantic clusters table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS memory_clusters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope_key TEXT NOT NULL DEFAULT 'global',
                cluster_label TEXT,
                centroid BLOB,
                description TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cluster_columns_cursor = await db.execute("PRAGMA table_info(memory_clusters)")
        cluster_columns = {row[1] for row in await cluster_columns_cursor.fetchall()}
        if "scope_key" not in cluster_columns:
            await db.execute(
                "ALTER TABLE memory_clusters ADD COLUMN scope_key TEXT NOT NULL DEFAULT 'global'"
            )
        
        # Create memory cluster mappings
        await db.execute('''
            CREATE TABLE IF NOT EXISTS memory_cluster_mappings (
                memory_id INTEGER,
                cluster_id INTEGER,
                similarity_score REAL,
                FOREIGN KEY (memory_id) REFERENCES memories(id),
                FOREIGN KEY (cluster_id) REFERENCES memory_clusters(id),
                PRIMARY KEY (memory_id, cluster_id)
            )
        ''')
        
        # Create memory relationships table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS memory_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_memory_id INTEGER,
                target_memory_id INTEGER,
                relationship_type TEXT,
                strength REAL DEFAULT 1.0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_memory_id) REFERENCES memories(id),
                FOREIGN KEY (target_memory_id) REFERENCES memories(id)
            )
        ''')
        
        # Create memory access log
        await db.execute('''
            CREATE TABLE IF NOT EXISTS memory_access_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_id INTEGER,
                query_context TEXT,
                accessed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                usefulness_score REAL,
                FOREIGN KEY (memory_id) REFERENCES memories(id)
            )
        ''')
        
        # Create essential indexes
        await db.execute('CREATE INDEX IF NOT EXISTS idx_memories_timestamp ON memories(timestamp)')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance)')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type)')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_memories_last_accessed ON memories(last_accessed)')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_memories_access_count ON memories(access_count)')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_memories_scope ON memories(scope_key)')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_memory_clusters_scope ON memory_clusters(scope_key)')
        await db.execute(
            'CREATE UNIQUE INDEX IF NOT EXISTS idx_memories_scope_hash '
            'ON memories(scope_key, content_hash)'
        )
        await db.execute('CREATE INDEX IF NOT EXISTS idx_relationships_source ON memory_relationships(source_memory_id)')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_relationships_target ON memory_relationships(target_memory_id)')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_relationships_type ON memory_relationships(relationship_type)')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_access_log_memory ON memory_access_log(memory_id)')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_access_log_time ON memory_access_log(accessed_at)')

    @staticmethod
    def _normalize_scope_key(
        scope_key: Optional[str],
        metadata: Optional[Dict] = None,
    ) -> str:
        """Return a validated scope key, optionally sourced from metadata."""
        candidate = scope_key
        if candidate is None and metadata is not None:
            metadata_scope = metadata.get("scope_key")
            if metadata_scope is not None:
                candidate = str(metadata_scope)
        if candidate is None:
            candidate = DEFAULT_SCOPE_KEY
        if not isinstance(candidate, str) or not candidate.strip():
            raise ValueError("scope_key must be a non-empty string")
        normalized = candidate.strip()
        if len(normalized) > 512:
            raise ValueError("scope_key must not exceed 512 characters")
        return normalized

    def _generate_hash(self, content: str, scope_key: str = DEFAULT_SCOPE_KEY) -> str:
        """Generate a scope-qualified content hash for safe deduplication."""
        digest = hashlib.sha256()
        digest.update(scope_key.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content.encode("utf-8"))
        return digest.hexdigest()
    
    def _serialize_embedding(self, embedding: List[float]) -> bytes:
        """Convert embedding list to bytes for storage."""
        if embedding is None:
            return None
        return np.array(embedding, dtype=np.float32).tobytes()
    
    def _deserialize_embedding(self, embedding_bytes: bytes) -> Optional[List[float]]:
        """Convert stored bytes back to embedding list."""
        if embedding_bytes is None:
            return None
        try:
            return np.frombuffer(embedding_bytes, dtype=np.float32).tolist()
        except Exception as e:
            self.logger.error(f"Error deserializing embedding: {e}")
            return None

    def _encode_text(self, text: str) -> List[float]:
        """Encode text through the repository's core modality bridge."""
        embedding = self.text_encoder.encode_text(text)
        embedding_array = embedding.detach().cpu().numpy().astype(np.float32).reshape(-1)
        return embedding_array.tolist()
    
    async def add_memory(
        self, 
        content: str, 
        embedding: List[float], 
        memory_type: str = "observation", 
        metadata: Optional[Dict] = None,
        scope_key: Optional[str] = None,
    ) -> int:
        """
        Add a new memory to the database. If memory already exists (based on content hash), 
        returns the existing memory's ID.
        
        Args:
            content: The actual memory content
            embedding: Vector embedding for semantic search
            memory_type: Type of memory (observation, reflection, goal, etc.)
            metadata: Flexible metadata storage
            
        Returns:
            The ID of the newly added memory or the existing memory's ID if duplicate
        """
        await self.initialize()

        normalized_scope = self._normalize_scope_key(scope_key, metadata)
        content_hash = self._generate_hash(content, normalized_scope)
        embedding_blob = self._serialize_embedding(embedding)
        
        async with self._open_connection() as db:
            # Ensure schema exists in this connection (important for in-memory databases)
            await self._ensure_schema(db)
            await db.commit()
            
            try:
                await db.execute("BEGIN IMMEDIATE")
                # Check if memory already exists by content hash
                cursor = await db.execute(
                    'SELECT id FROM memories WHERE scope_key = ? AND content_hash = ?',
                    (normalized_scope, content_hash),
                )
                existing_memory = await cursor.fetchone()
                
                if existing_memory:
                    # Memory already exists, update access count and timestamp
                    memory_id = existing_memory[0]
                    await db.execute('''
                        UPDATE memories 
                        SET last_accessed = ?, access_count = access_count + 1
                        WHERE id = ?
                    ''', (datetime.now().isoformat(timespec="microseconds"), memory_id))
                    await db.commit()
                    self.logger.info(f"Memory already exists with ID {memory_id}, updated access info")
                    return memory_id
                
                # Insert new memory
                cursor = await db.execute('''
                    INSERT INTO memories 
                    (content, embedding, scope_key, content_hash, memory_type, metadata, access_count)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                ''', (
                    content,
                    embedding_blob,
                    normalized_scope,
                    content_hash,
                    memory_type,
                    json.dumps(metadata or {}, sort_keys=True),
                ))
                
                memory_id = cursor.lastrowid
                if memory_id is None:
                    raise sqlite3.DatabaseError("SQLite did not return a memory id")
                await db.commit()
                
                self.logger.info(f"Added new memory with ID {memory_id}")
                return memory_id
                
            except sqlite3.Error as e:
                await db.rollback()
                self.logger.error(f"Error adding memory: {e}")
                raise
    
    async def add_memory_from_text(
        self, 
        content: str, 
        memory_type: str = "observation", 
        metadata: Optional[Dict] = None,
        model_path: Optional[str] = None,
        scope_key: Optional[str] = None,
    ) -> int:
        """
        Add a new memory to the database by generating embedding from text.
        
        Args:
            content: The actual memory content as text
            memory_type: Type of memory (observation, reflection, goal, etc.)
            metadata: Flexible metadata storage
            model_path: Optional model path to use for this specific memory (uses default if None)
            
        Returns:
            The ID of the newly added memory or the existing memory's ID if duplicate
        """
        # Generate embedding from content through the core modality bridge.
        embedding = self._encode_text(content)
        
        return await self.add_memory(
            content,
            embedding,
            memory_type,
            metadata,
            scope_key=scope_key,
        )

    async def add_memories_from_text_atomic(
        self,
        records: Iterable[tuple[str, str, Mapping[str, Any]]],
        *,
        scope_key: Optional[str] = None,
    ) -> List[int]:
        """Insert or replay a bounded record set in one SQLite transaction.

        All text encoding and JSON validation completes before ``BEGIN
        IMMEDIATE``.  A database error on any row therefore rolls back every
        insert and access-count update from this call instead of publishing a
        partially persisted graph.
        """
        prepared: list[tuple[str, bytes, str, str, str, str]] = []
        for index, record in enumerate(records):
            if index >= 100_000:
                raise ValueError("atomic semantic batch exceeds 100000 records")
            if not isinstance(record, tuple) or len(record) != 3:
                raise TypeError(
                    "atomic semantic records must be (content, memory_type, metadata) tuples"
                )
            content, memory_type, metadata = record
            if not isinstance(content, str) or not content:
                raise ValueError("atomic semantic record content must be non-empty text")
            if not isinstance(memory_type, str) or not memory_type:
                raise ValueError("atomic semantic memory_type must be non-empty text")
            if not isinstance(metadata, Mapping):
                raise TypeError("atomic semantic metadata must be a mapping")
            normalized_scope = self._normalize_scope_key(
                scope_key,
                dict(metadata),
            )
            try:
                metadata_json = json.dumps(
                    dict(metadata),
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                    allow_nan=False,
                )
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"atomic semantic metadata at index {index} is not JSON-compatible"
                ) from exc
            embedding_blob = self._serialize_embedding(self._encode_text(content))
            prepared.append(
                (
                    content,
                    embedding_blob,
                    normalized_scope,
                    self._generate_hash(content, normalized_scope),
                    memory_type,
                    metadata_json,
                )
            )

        await self.initialize()
        if not prepared:
            return []
        stored_ids: List[int] = []
        async with self._open_connection() as db:
            await self._ensure_schema(db)
            await db.commit()
            try:
                await db.execute("BEGIN IMMEDIATE")
                for (
                    content,
                    embedding_blob,
                    normalized_scope,
                    content_hash,
                    memory_type,
                    metadata_json,
                ) in prepared:
                    cursor = await db.execute(
                        "SELECT id FROM memories WHERE scope_key = ? AND content_hash = ?",
                        (normalized_scope, content_hash),
                    )
                    existing = await cursor.fetchone()
                    if existing is not None:
                        memory_id = int(existing[0])
                        await db.execute(
                            """
                            UPDATE memories
                            SET last_accessed = ?, access_count = access_count + 1
                            WHERE id = ? AND scope_key = ?
                            """,
                            (
                                datetime.now().isoformat(timespec="microseconds"),
                                memory_id,
                                normalized_scope,
                            ),
                        )
                    else:
                        cursor = await db.execute(
                            """
                            INSERT INTO memories
                            (content, embedding, scope_key, content_hash,
                             memory_type, metadata, access_count)
                            VALUES (?, ?, ?, ?, ?, ?, 1)
                            """,
                            (
                                content,
                                embedding_blob,
                                normalized_scope,
                                content_hash,
                                memory_type,
                                metadata_json,
                            ),
                        )
                        if cursor.lastrowid is None:
                            raise sqlite3.DatabaseError(
                                "SQLite did not return a semantic memory id"
                            )
                        memory_id = int(cursor.lastrowid)
                    stored_ids.append(memory_id)
                await db.commit()
            except sqlite3.Error:
                await db.rollback()
                raise
        return stored_ids
    
    async def semantic_search(
        self, 
        query_embedding: List[float], 
        limit: int = 10, 
        similarity_threshold: float = 0.7,
        memory_type: Optional[str] = None,
        scope_key: Optional[str] = None,
    ) -> List[Dict]:
        """
        Perform semantic search based on query embedding.
        
        Args:
            query_embedding: The embedding to search for
            limit: Maximum number of results to return
            similarity_threshold: Minimum similarity score for results
            memory_type: Filter by memory type (optional)
            
        Returns:
            List of matching memories with similarity scores
        """
        await self.initialize()
        normalized_scope = self._normalize_scope_key(scope_key)
        
        query_embedding_array = np.array(query_embedding).reshape(1, -1)
        
        # First, fetch all embeddings to calculate cosine similarity
        async with self._open_connection() as db:
            await self._ensure_schema(db)
            # Build the query based on whether we're filtering by memory type
            if memory_type:
                cursor = await db.execute('''
                    SELECT id, content, embedding, memory_type, importance, timestamp, access_count, metadata, scope_key
                    FROM memories 
                    WHERE scope_key = ? AND memory_type = ?
                ''', (normalized_scope, memory_type))
            else:
                cursor = await db.execute('''
                    SELECT id, content, embedding, memory_type, importance, timestamp, access_count, metadata, scope_key
                    FROM memories
                    WHERE scope_key = ?
                ''', (normalized_scope,))
                
            rows = await cursor.fetchall()
        
        # Calculate similarities
        memories_with_similarity = []
        for row in rows:
            memory_id, content, embedding_bytes, mem_type, importance, timestamp, access_count, metadata_str, row_scope_key = row
            embedding = self._deserialize_embedding(embedding_bytes)
            
            if embedding is not None:
                # Calculate cosine similarity
                memory_embedding_array = np.array(embedding).reshape(1, -1)
                similarity = cosine_similarity(query_embedding_array, memory_embedding_array)[0][0]
                
                if similarity >= similarity_threshold:
                    metadata = json.loads(metadata_str) if metadata_str else {}
                    memories_with_similarity.append({
                        'id': memory_id,
                        'content': content,
                        'memory_type': mem_type,
                        'importance': importance,
                        'timestamp': timestamp,
                        'access_count': access_count,
                        'metadata': metadata,
                        'scope_key': row_scope_key,
                        'similarity': float(similarity)
                    })
        
        # Sort by similarity and return top results
        memories_with_similarity.sort(key=lambda x: x['similarity'], reverse=True)
        return memories_with_similarity[:limit]
    
    async def semantic_search_from_text(
        self, 
        query_text: str, 
        limit: int = 10, 
        similarity_threshold: float = 0.7,
        memory_type: Optional[str] = None,
        scope_key: Optional[str] = None,
    ) -> List[Dict]:
        """
        Perform semantic search based on query text (embedding generated automatically).
        
        Args:
            query_text: The text to search for semantically
            limit: Maximum number of results to return
            similarity_threshold: Minimum similarity score for results
            memory_type: Filter by memory type (optional)
            
        Returns:
            List of matching memories with similarity scores
        """
        # Generate embedding from query text through the core modality bridge.
        query_embedding = self._encode_text(query_text)
        
        return await self.semantic_search(
            query_embedding,
            limit,
            similarity_threshold,
            memory_type,
            scope_key=scope_key,
        )
    
    async def get_memory_by_id(
        self,
        memory_id: int,
        scope_key: Optional[str] = None,
    ) -> Optional[Dict]:
        """Get a specific memory by its ID."""
        await self.initialize()
        normalized_scope = self._normalize_scope_key(scope_key)
        
        async with self._open_connection() as db:
            await self._ensure_schema(db)
            cursor = await db.execute('''
                SELECT id, content, embedding, memory_type, importance, 
                       timestamp, last_accessed, access_count, metadata, scope_key
                FROM memories 
                WHERE id = ? AND scope_key = ?
            ''', (memory_id, normalized_scope))
            
            row = await cursor.fetchone()
            if row:
                memory_id, content, embedding_bytes, memory_type, importance, timestamp, last_accessed, access_count, metadata_str, row_scope_key = row
                return {
                    'id': memory_id,
                    'content': content,
                    'embedding': self._deserialize_embedding(embedding_bytes),
                    'memory_type': memory_type,
                    'importance': importance,
                    'timestamp': timestamp,
                    'last_accessed': last_accessed,
                    'access_count': access_count,
                    'metadata': json.loads(metadata_str) if metadata_str else {},
                    'scope_key': row_scope_key,
                }
        
        return None

    async def get_validated_projection_by_id(
        self,
        memory_id: int,
        *,
        scope_key: str,
        expected_content: str,
        expected_memory_type: str,
        expected_metadata: Mapping[str, object],
    ) -> Optional[Dict[str, Any]]:
        """Return one projection only after complete persisted-row validation.

        This is the authority-boundary read for USMS-backed semantic rows.  It
        verifies values that a normal projection lookup cannot authenticate:
        the scope-qualified content digest, projection type, metadata, and the
        exact deterministic text embedding.  Any malformed or mismatched field
        raises :class:`SemanticProjectionIntegrityError` rather than silently
        returning a row that can pass a partial parity comparison.
        """
        if not isinstance(memory_id, int) or isinstance(memory_id, bool) or memory_id < 1:
            raise ValueError("memory_id must be a positive integer")
        if not isinstance(expected_content, str) or not expected_content:
            raise ValueError("expected_content must be a non-empty string")
        if not isinstance(expected_memory_type, str) or not expected_memory_type:
            raise ValueError("expected_memory_type must be a non-empty string")
        if not isinstance(expected_metadata, Mapping):
            raise TypeError("expected_metadata must be a mapping")

        await self.initialize()
        normalized_scope = self._normalize_scope_key(scope_key)
        async with self._open_connection() as db:
            await self._ensure_schema(db)
            cursor = await db.execute(
                """
                SELECT id, content, embedding, memory_type, importance,
                       timestamp, last_accessed, access_count, metadata,
                       scope_key, content_hash
                FROM memories
                WHERE id = ? AND scope_key = ?
                """,
                (memory_id, normalized_scope),
            )
            row = await cursor.fetchone()

        if row is None:
            return None

        (
            stored_id,
            content,
            embedding_blob,
            memory_type,
            importance,
            timestamp,
            last_accessed,
            access_count,
            metadata_json,
            stored_scope,
            content_hash,
        ) = row

        if not isinstance(content, str):
            self._raise_projection_integrity(memory_id, "content", "value is not text")
        expected_hash = self._generate_hash(content, normalized_scope)
        if content_hash != expected_hash:
            self._raise_projection_integrity(
                memory_id,
                "content_hash",
                "stored digest does not match content and scope",
            )
        if content != expected_content:
            self._raise_projection_integrity(
                memory_id,
                "content",
                "stored text does not match the canonical projection",
            )
        if memory_type != expected_memory_type:
            self._raise_projection_integrity(
                memory_id,
                "memory_type",
                "stored type does not match the canonical projection",
            )

        metadata = self._validated_projection_metadata(memory_id, metadata_json)
        if metadata != dict(expected_metadata):
            self._raise_projection_integrity(
                memory_id,
                "metadata",
                "stored metadata does not match the canonical projection",
            )

        embedding = self._validated_projection_embedding(
            memory_id,
            embedding_blob,
            expected_content,
        )
        return {
            "id": stored_id,
            "content": content,
            "embedding": embedding,
            "memory_type": memory_type,
            "importance": importance,
            "timestamp": timestamp,
            "last_accessed": last_accessed,
            "access_count": access_count,
            "metadata": metadata,
            "scope_key": stored_scope,
            "content_hash": content_hash,
        }

    @staticmethod
    def _raise_projection_integrity(memory_id: int, field: str, reason: str) -> None:
        """Raise the typed semantic-projection corruption signal."""
        raise SemanticProjectionIntegrityError(memory_id, field, reason)

    def _validated_projection_metadata(
        self,
        memory_id: int,
        metadata_json: object,
    ) -> Dict[str, Any]:
        """Decode projection metadata without accepting malformed JSON shapes."""
        if not isinstance(metadata_json, str):
            self._raise_projection_integrity(
                memory_id,
                "metadata",
                "stored value is not JSON text",
            )
        try:
            metadata = json.loads(metadata_json)
        except (json.JSONDecodeError, TypeError) as exc:
            raise SemanticProjectionIntegrityError(
                memory_id,
                "metadata",
                "stored JSON cannot be decoded",
            ) from exc
        if not isinstance(metadata, dict):
            self._raise_projection_integrity(
                memory_id,
                "metadata",
                "decoded JSON is not an object",
            )
        return metadata

    def _validated_projection_embedding(
        self,
        memory_id: int,
        embedding_blob: object,
        expected_content: str,
    ) -> List[float]:
        """Validate the shape, finiteness, and canonical text-vector parity."""
        if not isinstance(embedding_blob, bytes):
            self._raise_projection_integrity(
                memory_id,
                "embedding_bytes",
                "stored value is not a byte string",
            )
        expected_nbytes = (
            SEMANTIC_PROJECTION_EMBEDDING_DIMENSION * np.dtype(np.float32).itemsize
        )
        if len(embedding_blob) != expected_nbytes:
            self._raise_projection_integrity(
                memory_id,
                "embedding_dimension",
                f"expected {SEMANTIC_PROJECTION_EMBEDDING_DIMENSION} float32 values",
            )
        stored_embedding = np.frombuffer(embedding_blob, dtype=np.float32)
        if stored_embedding.shape != (SEMANTIC_PROJECTION_EMBEDDING_DIMENSION,):
            self._raise_projection_integrity(
                memory_id,
                "embedding_dimension",
                f"expected {SEMANTIC_PROJECTION_EMBEDDING_DIMENSION} float32 values",
            )
        if not np.isfinite(stored_embedding).all():
            self._raise_projection_integrity(
                memory_id,
                "embedding_finite",
                "stored vector contains a non-finite value",
            )

        canonical_embedding = np.asarray(
            self._encode_text(expected_content),
            dtype=np.float32,
        )
        if canonical_embedding.shape != (SEMANTIC_PROJECTION_EMBEDDING_DIMENSION,):
            raise RuntimeError(
                "semantic text encoder returned an unexpected projection dimension"
            )
        if not np.array_equal(stored_embedding, canonical_embedding):
            self._raise_projection_integrity(
                memory_id,
                "embedding_content",
                "stored vector does not match the canonical text encoding",
            )
        return stored_embedding.tolist()
    
    async def update_memory(
        self, 
        memory_id: int, 
        content: Optional[str] = None, 
        memory_type: Optional[str] = None, 
        importance: Optional[float] = None, 
        metadata: Optional[Dict] = None,
        update_embedding: bool = False,
        scope_key: Optional[str] = None,
    ) -> bool:
        """
        Update an existing memory with new content or metadata.
        
        Args:
            memory_id: ID of the memory to update
            content: New content for the memory (if updating)
            memory_type: New memory type
            importance: New importance score
            metadata: New metadata dictionary
            update_embedding: Whether to update the embedding if content is changed
            
        Returns:
            True if the memory was updated, False if the memory was not found
        """
        await self.initialize()
        normalized_scope = self._normalize_scope_key(scope_key)

        new_embedding_blob: Optional[bytes] = None
        new_content_hash: Optional[str] = None
        if content is not None:
            # Content, hash, and vector are one consistency unit. The legacy
            # update_embedding flag remains accepted but cannot permit stale vectors.
            new_embedding_blob = self._serialize_embedding(self._encode_text(content))
            new_content_hash = self._generate_hash(content, normalized_scope)

        async with self._open_connection() as db:
            await self._ensure_schema(db)
            await db.commit()
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute(
                """
                SELECT content, embedding, content_hash, memory_type, importance, metadata
                FROM memories
                WHERE id = ? AND scope_key = ?
                """,
                (memory_id, normalized_scope),
            )
            result = await cursor.fetchone()
            
            if not result:
                await db.rollback()
                return False  # Memory doesn't exist

            (
                stored_content,
                stored_embedding,
                stored_hash,
                stored_memory_type,
                stored_importance,
                stored_metadata,
            ) = result
            effective_importance = stored_importance if importance is None else importance
            if not 0 <= effective_importance <= 1:
                await db.rollback()
                raise ValueError("Importance must be between 0 and 1")

            cursor = await db.execute(
                """
                UPDATE memories
                SET content = ?, embedding = ?, content_hash = ?, memory_type = ?,
                    importance = ?, metadata = ?, last_accessed = ?
                WHERE id = ? AND scope_key = ?
                """,
                (
                    stored_content if content is None else content,
                    stored_embedding if content is None else new_embedding_blob,
                    stored_hash if content is None else new_content_hash,
                    stored_memory_type if memory_type is None else memory_type,
                    effective_importance,
                    stored_metadata if metadata is None else json.dumps(metadata, sort_keys=True),
                    datetime.now().isoformat(timespec="microseconds"),
                    memory_id,
                    normalized_scope,
                ),
            )
            await db.commit()
            
            return cursor.rowcount > 0
    
    async def update_memory_importance(
        self,
        memory_id: int,
        importance: float,
        scope_key: Optional[str] = None,
    ) -> None:
        """Update the importance score of a memory."""
        await self.initialize()
        normalized_scope = self._normalize_scope_key(scope_key)
        if not 0 <= importance <= 1:
            raise ValueError("Importance must be between 0 and 1")
        
        async with self._open_connection() as db:
            await self._ensure_schema(db)
            cursor = await db.execute('''
                UPDATE memories SET importance = ?, last_accessed = ?
                WHERE id = ? AND scope_key = ?
            ''', (
                importance,
                datetime.now().isoformat(timespec="microseconds"),
                memory_id,
                normalized_scope,
            ))
            
            await db.commit()
            if cursor.rowcount == 0:
                raise ValueError(f"Memory with ID {memory_id} not found")
    
    async def add_relationship(
        self, 
        source_memory_id: int, 
        target_memory_id: int, 
        relationship_type: str, 
        strength: float = 1.0,
        scope_key: Optional[str] = None,
    ) -> int:
        """
        Add a relationship between two memories.
        
        Args:
            source_memory_id: ID of the source memory
            target_memory_id: ID of the target memory
            relationship_type: Type of relationship (precedes, causes, contradicts, supports, etc.)
            strength: Strength of the relationship (0.0 - 1.0)
            
        Returns:
            The ID of the newly created relationship
        """
        await self.initialize()
        normalized_scope = self._normalize_scope_key(scope_key)
        if not 0 <= strength <= 1:
            raise ValueError("Relationship strength must be between 0 and 1")
        
        async with self._open_connection() as db:
            await self._ensure_schema(db)
            cursor = await db.execute(
                "SELECT id FROM memories WHERE scope_key = ? AND id IN (?, ?)",
                (normalized_scope, source_memory_id, target_memory_id),
            )
            found_ids = {row[0] for row in await cursor.fetchall()}
            expected_ids = {source_memory_id, target_memory_id}
            if found_ids != expected_ids:
                raise ValueError("Both relationship endpoints must exist in the requested scope")
            cursor = await db.execute('''
                INSERT INTO memory_relationships 
                (source_memory_id, target_memory_id, relationship_type, strength)
                VALUES (?, ?, ?, ?)
            ''', (source_memory_id, target_memory_id, relationship_type, strength))
            
            relationship_id = cursor.lastrowid
            await db.commit()
            
            self.logger.info(f"Added relationship with ID {relationship_id}: {source_memory_id} -> {target_memory_id}")
            return relationship_id
    
    async def get_related_memories(
        self, 
        memory_id: int, 
        relationship_types: Optional[List[str]] = None,
        direction: str = 'both',  # 'source', 'target', or 'both'
        scope_key: Optional[str] = None,
    ) -> List[Dict]:
        """
        Get related memories for a given memory.
        
        Args:
            memory_id: ID of the memory to find relationships for
            relationship_types: List of relationship types to filter by (optional)
            direction: Direction of relationships to return ('source', 'target', or 'both')
            
        Returns:
            List of related memories with relationship information
        """
        await self.initialize()
        normalized_scope = self._normalize_scope_key(scope_key)
        
        base_query = '''
            SELECT mr.source_memory_id, mr.target_memory_id, mr.relationship_type, 
                   mr.strength, mr.created_at,
                   m1.content as source_content, m2.content as target_content
            FROM memory_relationships mr
            JOIN memories m1 ON m1.id = mr.source_memory_id
            JOIN memories m2 ON m2.id = mr.target_memory_id
        '''

        if direction == 'source':
            query = base_query + (
                " WHERE m1.scope_key = ? AND m2.scope_key = ? AND mr.source_memory_id = ?"
            )
            params = [normalized_scope, normalized_scope, memory_id]
        elif direction == 'target':
            query = base_query + (
                " WHERE m1.scope_key = ? AND m2.scope_key = ? AND mr.target_memory_id = ?"
            )
            params = [normalized_scope, normalized_scope, memory_id]
        elif direction == 'both':
            query = base_query + (
                " WHERE m1.scope_key = ? AND m2.scope_key = ? "
                "AND (mr.source_memory_id = ? OR mr.target_memory_id = ?)"
            )
            params = [normalized_scope, normalized_scope, memory_id, memory_id]
        else:
            raise ValueError("direction must be 'source', 'target', or 'both'")
        
        async with self._open_connection() as db:
            await self._ensure_schema(db)
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()

        if relationship_types:
            allowed_relationship_types = set(relationship_types)
            rows = [row for row in rows if row[2] in allowed_relationship_types]
        
        related_memories = []
        for row in rows:
            source_id, target_id, rel_type, strength, created_at, source_content, target_content = row
            
            # Determine which is the related memory (not the original memory_id)
            if direction == 'source':
                # We expect source_memory_id to be the one passed in
                related_memory_id = target_id
                related_content = target_content
            elif direction == 'target':
                # We expect target_memory_id to be the one passed in
                related_memory_id = source_id
                related_content = source_content
            else:  # both
                if source_id == memory_id:
                    related_memory_id = target_id
                    related_content = target_content
                else:
                    related_memory_id = source_id
                    related_content = source_content
            
            related_memories.append({
                'related_memory_id': related_memory_id,
                'related_content': related_content,
                'relationship_type': rel_type,
                'strength': strength,
                'created_at': created_at
            })
        
        return related_memories
    
    async def get_memory_cluster(
        self,
        memory_id: int,
        scope_key: Optional[str] = None,
    ) -> Optional[Dict]:
        """Get cluster information for a specific memory."""
        await self.initialize()
        normalized_scope = self._normalize_scope_key(scope_key)
        
        async with self._open_connection() as db:
            await self._ensure_schema(db)
            cursor = await db.execute('''
                SELECT mcm.cluster_id, mc.cluster_label, mc.description, mcm.similarity_score
                FROM memory_cluster_mappings mcm
                JOIN memory_clusters mc ON mcm.cluster_id = mc.id
                JOIN memories m ON mcm.memory_id = m.id
                WHERE mcm.memory_id = ? AND m.scope_key = ? AND mc.scope_key = ?
            ''', (memory_id, normalized_scope, normalized_scope))
            
            row = await cursor.fetchone()
            if row:
                cluster_id, cluster_label, description, similarity_score = row
                return {
                    'cluster_id': cluster_id,
                    'cluster_label': cluster_label,
                    'description': description,
                    'similarity_score': similarity_score
                }
        
        return None
    
    async def get_memories_by_cluster(
        self,
        cluster_id: int,
        scope_key: Optional[str] = None,
    ) -> List[Dict]:
        """Get all memories associated with a specific cluster."""
        await self.initialize()
        normalized_scope = self._normalize_scope_key(scope_key)
        
        async with self._open_connection() as db:
            await self._ensure_schema(db)
            cursor = await db.execute('''
                SELECT m.id, m.content, m.memory_type, m.importance, m.timestamp,
                       mcm.similarity_score
                FROM memories m
                JOIN memory_cluster_mappings mcm ON m.id = mcm.memory_id
                JOIN memory_clusters mc ON mcm.cluster_id = mc.id
                WHERE mcm.cluster_id = ? AND m.scope_key = ? AND mc.scope_key = ?
                ORDER BY mcm.similarity_score DESC
            ''', (cluster_id, normalized_scope, normalized_scope))
            
            rows = await cursor.fetchall()
        
        memories = []
        for row in rows:
            memory_id, content, memory_type, importance, timestamp, similarity_score = row
            memories.append({
                'id': memory_id,
                'content': content,
                'memory_type': memory_type,
                'importance': importance,
                'timestamp': timestamp,
                'similarity_score': similarity_score
            })
        
        return memories
    
    async def create_memory_cluster(
        self,
        memories: List[Dict],
        label: Optional[str] = None,
        description: Optional[str] = None,
        scope_key: Optional[str] = None,
    ) -> int:
        """
        Create a cluster from a list of memories.
        
        Args:
            memories: List of memory dictionaries with 'id' and 'embedding' keys
            label: Label for the cluster
            description: Description of the cluster
            
        Returns:
            The ID of the newly created cluster
        """
        await self.initialize()
        normalized_scope = self._normalize_scope_key(scope_key)
        
        if not memories:
            raise ValueError("Cannot create cluster with no memories")
        
        # Calculate centroid from all memory embeddings
        embeddings = []
        memory_ids = []
        
        for memory in memories:
            if 'embedding' in memory and memory['embedding'] is not None:
                embeddings.append(memory['embedding'])
                memory_ids.append(memory['id'])
        
        if not embeddings:
            raise ValueError("No valid embeddings found in provided memories")
        
        # Calculate centroid
        centroid = np.mean(np.array(embeddings), axis=0)
        centroid_blob = self._serialize_embedding(centroid.tolist())
        
        async with self._open_connection() as db:
            await self._ensure_schema(db)
            for memory_id in memory_ids:
                cursor = await db.execute(
                    "SELECT 1 FROM memories WHERE scope_key = ? AND id = ?",
                    (normalized_scope, memory_id),
                )
                if await cursor.fetchone() is None:
                    raise ValueError(
                        "Every clustered memory must exist in the requested scope"
                    )
            # Create cluster
            cursor = await db.execute('''
                INSERT INTO memory_clusters (scope_key, cluster_label, centroid, description)
                VALUES (?, ?, ?, ?)
            ''', (normalized_scope, label, centroid_blob, description))
            
            cluster_id = cursor.lastrowid
            
            # Create mappings for each memory
            for memory_id in memory_ids:
                # Calculate similarity to centroid for each memory
                memory_embedding = next((m['embedding'] for m in memories if m['id'] == memory_id), None)
                if memory_embedding:
                    similarity = cosine_similarity(
                        np.array(memory_embedding).reshape(1, -1),
                        np.array(centroid).reshape(1, -1)
                    )[0][0]
                    
                    await db.execute('''
                        INSERT INTO memory_cluster_mappings (memory_id, cluster_id, similarity_score)
                        VALUES (?, ?, ?)
                    ''', (memory_id, cluster_id, float(similarity)))
            
            await db.commit()
            self.logger.info(f"Created cluster {cluster_id} with {len(memory_ids)} memories")
            return cluster_id
    
    async def get_all_clusters(
        self,
        scope_key: Optional[str] = None,
    ) -> List[Dict]:
        """Get all memory clusters."""
        await self.initialize()
        normalized_scope = self._normalize_scope_key(scope_key)
        
        async with self._open_connection() as db:
            await self._ensure_schema(db)
            cursor = await db.execute('''
                SELECT id, cluster_label, centroid, description, created_at
                FROM memory_clusters
                WHERE scope_key = ?
            ''', (normalized_scope,))
            
            rows = await cursor.fetchall()
        
        clusters = []
        for row in rows:
            cluster_id, cluster_label, centroid_bytes, description, created_at = row
            centroid = self._deserialize_embedding(centroid_bytes)
            clusters.append({
                'id': cluster_id,
                'cluster_label': cluster_label,
                'centroid': centroid,
                'description': description,
                'created_at': created_at
            })
        
        return clusters
    
    async def log_memory_access(
        self,
        memory_id: int,
        query_context: Optional[str] = None,
        usefulness_score: Optional[float] = None,
        scope_key: Optional[str] = None,
    ) -> None:
        """Log access to a memory for tracking usage patterns."""
        await self.initialize()
        normalized_scope = self._normalize_scope_key(scope_key)
        if usefulness_score is not None and not 0 <= usefulness_score <= 1:
            raise ValueError("usefulness_score must be between 0 and 1")
        
        async with self._open_connection() as db:
            await self._ensure_schema(db)
            cursor = await db.execute(
                "SELECT 1 FROM memories WHERE id = ? AND scope_key = ?",
                (memory_id, normalized_scope),
            )
            if await cursor.fetchone() is None:
                raise ValueError(f"Memory with ID {memory_id} not found in requested scope")
            await db.execute('''
                INSERT INTO memory_access_log (memory_id, query_context, usefulness_score)
                VALUES (?, ?, ?)
            ''', (memory_id, query_context, usefulness_score))
            
            # Update memory access count and timestamp
            await db.execute('''
                UPDATE memories 
                SET last_accessed = ?, access_count = access_count + 1
                WHERE id = ?
            ''', (datetime.now().isoformat(timespec="microseconds"), memory_id))
            
            await db.commit()
    
    async def get_memory_access_log(
        self,
        memory_id: int,
        limit: int = 10,
        scope_key: Optional[str] = None,
    ) -> List[Dict]:
        """Get access log for a specific memory."""
        await self.initialize()
        normalized_scope = self._normalize_scope_key(scope_key)
        if limit < 1:
            raise ValueError("limit must be positive")
        
        async with self._open_connection() as db:
            await self._ensure_schema(db)
            cursor = await db.execute('''
                SELECT mal.id, mal.query_context, mal.accessed_at, mal.usefulness_score
                FROM memory_access_log mal
                JOIN memories m ON mal.memory_id = m.id
                WHERE mal.memory_id = ? AND m.scope_key = ?
                ORDER BY mal.accessed_at DESC
                LIMIT ?
            ''', (memory_id, normalized_scope, limit))
            
            rows = await cursor.fetchall()
        
        log_entries = []
        for row in rows:
            log_id, query_context, accessed_at, usefulness_score = row
            log_entries.append({
                'id': log_id,
                'query_context': query_context,
                'accessed_at': accessed_at,
                'usefulness_score': usefulness_score
            })
        
        return log_entries
    
    async def remove_memory(
        self,
        memory_id: int,
        scope_key: Optional[str] = None,
    ) -> bool:
        """Remove a memory and all its relationships."""
        await self.initialize()
        normalized_scope = self._normalize_scope_key(scope_key)
        
        async with self._open_connection() as db:
            await self._ensure_schema(db)
            await db.commit()
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute(
                "SELECT 1 FROM memories WHERE id = ? AND scope_key = ?",
                (memory_id, normalized_scope),
            )
            if await cursor.fetchone() is None:
                await db.rollback()
                return False
            # Remove relationships first
            await db.execute('DELETE FROM memory_relationships WHERE source_memory_id = ? OR target_memory_id = ?', 
                           (memory_id, memory_id))
            
            # Remove cluster mappings
            await db.execute('DELETE FROM memory_cluster_mappings WHERE memory_id = ?', (memory_id,))
            
            # Remove access logs
            await db.execute('DELETE FROM memory_access_log WHERE memory_id = ?', (memory_id,))
            
            # Remove the memory itself
            await db.execute(
                'DELETE FROM memories WHERE id = ? AND scope_key = ?',
                (memory_id, normalized_scope),
            )
            
            await db.commit()
            self.logger.info(f"Removed memory {memory_id} and all related data")
            return True

    async def reconcile_service_projection_inventory(
        self,
        canonical_memory_ids: Iterable[int],
    ) -> SemanticProjectionInventoryReconciliation:
        """Restrict a service-private database to canonical projection rows.

        The generic semantic database deliberately permits direct knowledge
        graph persistence.  That behavior must not leak into a
        :class:`MemoryArchiveService` runtime root: the service owns that file
        as a disposable projection of signed USMS records.  The caller passes
        the complete, already validated set of semantic row ids associated
        with live canonical archive records.  Every other memory row is
        removed atomically, together with all generic relationship, cluster,
        and access-log state, none of which is an archive authority.

        The method intentionally preserves only row identity here.  The
        service validates content, scope, type, metadata, and deterministic
        embedding parity before supplying this inventory; keeping those checks
        in the service maintains the USMS ownership boundary.
        """
        expected_ids: set[int] = set()
        for memory_id in canonical_memory_ids:
            if (
                not isinstance(memory_id, int)
                or isinstance(memory_id, bool)
                or memory_id < 1
            ):
                raise ValueError(
                    "canonical_memory_ids must contain only positive integer ids"
                )
            expected_ids.add(memory_id)

        await self.initialize()
        async with self._open_connection() as db:
            await self._ensure_schema(db)
            await db.commit()
            try:
                await db.execute("BEGIN IMMEDIATE")
                await db.execute(
                    """
                    CREATE TEMP TABLE service_projection_inventory (
                        memory_id INTEGER PRIMARY KEY
                    )
                    """
                )
                if expected_ids:
                    await db.executemany(
                        "INSERT INTO service_projection_inventory(memory_id) VALUES (?)",
                        ((memory_id,) for memory_id in sorted(expected_ids)),
                    )

                # The archive service does not create generic semantic
                # relationships, clusters, or access logs.  Retaining any of
                # them would permit direct writers to establish durable state
                # beside a signed projection, even when both endpoint memory
                # ids happen to be canonical.
                relationship_cursor = await db.execute("DELETE FROM memory_relationships")
                mapping_cursor = await db.execute("DELETE FROM memory_cluster_mappings")
                access_log_cursor = await db.execute("DELETE FROM memory_access_log")
                cluster_cursor = await db.execute("DELETE FROM memory_clusters")
                memory_cursor = await db.execute(
                    """
                    DELETE FROM memories
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM service_projection_inventory AS expected
                        WHERE expected.memory_id = memories.id
                    )
                    """
                )
                await db.execute("DROP TABLE service_projection_inventory")
                await db.commit()
            except sqlite3.Error:
                await db.rollback()
                raise

        result = SemanticProjectionInventoryReconciliation(
            removed_memories=max(memory_cursor.rowcount, 0),
            removed_relationships=max(relationship_cursor.rowcount, 0),
            removed_cluster_mappings=max(mapping_cursor.rowcount, 0),
            removed_clusters=max(cluster_cursor.rowcount, 0),
            removed_access_logs=max(access_log_cursor.rowcount, 0),
        )
        if result.removed_memories or result.removed_dependent_rows:
            self.logger.warning(
                "Reconciled service-owned semantic projection inventory: "
                "removed %s memory rows and %s dependent rows",
                result.removed_memories,
                result.removed_dependent_rows,
            )
        return result
    
    async def consolidate_memories(
        self,
        importance_threshold: float = 0.3,
        access_count_threshold: int = 1,
        scope_key: Optional[str] = None,
    ) -> int:
        """
        Consolidate memories by removing low importance rarely accessed memories.
        
        Args:
            importance_threshold: Memories with importance below this will be considered for removal
            access_count_threshold: Memories with fewer accesses than this will be considered for removal
            
        Returns:
            Number of memories removed
        """
        await self.initialize()
        normalized_scope = self._normalize_scope_key(scope_key)
        if not 0 <= importance_threshold <= 1:
            raise ValueError("importance_threshold must be between 0 and 1")
        if access_count_threshold < 0:
            raise ValueError("access_count_threshold must not be negative")
        
        async with self._open_connection() as db:
            await self._ensure_schema(db)
            cursor = await db.execute('''
                SELECT id FROM memories 
                WHERE scope_key = ? AND importance < ? AND access_count <= ?
            ''', (normalized_scope, importance_threshold, access_count_threshold))
            
            rows = await cursor.fetchall()
            memory_ids_to_remove = [row[0] for row in rows]
            
            if not memory_ids_to_remove:
                return 0

            await db.commit()
            await db.execute("BEGIN IMMEDIATE")
            for memory_id in memory_ids_to_remove:
                await db.execute(
                    'DELETE FROM memory_relationships '
                    'WHERE source_memory_id = ? OR target_memory_id = ?',
                    (memory_id, memory_id),
                )
                await db.execute(
                    'DELETE FROM memory_cluster_mappings WHERE memory_id = ?',
                    (memory_id,),
                )
                await db.execute(
                    'DELETE FROM memory_access_log WHERE memory_id = ?',
                    (memory_id,),
                )
            removed_count = 0
            for memory_id in memory_ids_to_remove:
                cursor = await db.execute(
                    "DELETE FROM memories WHERE scope_key = ? AND id = ?",
                    (normalized_scope, memory_id),
                )
                removed_count += cursor.rowcount
            await db.commit()
            
            self.logger.info(f"Consolidated memory database: removed {removed_count} memories")
            return removed_count
    
    async def get_memory_stats(
        self,
        scope_key: Optional[str] = None,
    ) -> Dict:
        """Get statistics about the memory database."""
        await self.initialize()
        normalized_scope = self._normalize_scope_key(scope_key)
        
        async with self._open_connection() as db:
            await self._ensure_schema(db)
            # Total memories
            cursor = await db.execute(
                'SELECT COUNT(*) FROM memories WHERE scope_key = ?',
                (normalized_scope,),
            )
            total_memories_row = await cursor.fetchone()
            total_memories = total_memories_row[0] if total_memories_row else 0
            
            # Memory types count
            cursor = await db.execute(
                'SELECT memory_type, COUNT(*) FROM memories '
                'WHERE scope_key = ? GROUP BY memory_type',
                (normalized_scope,),
            )
            memory_types_rows = await cursor.fetchall()
            memory_types = dict(memory_types_rows) if memory_types_rows else {}
            
            # Average importance
            cursor = await db.execute(
                'SELECT AVG(importance) FROM memories WHERE scope_key = ?',
                (normalized_scope,),
            )
            avg_importance_row = await cursor.fetchone()
            avg_importance = avg_importance_row[0] if avg_importance_row else 0.0
            
            # Memories by importance range
            cursor = await db.execute('''
                SELECT 
                    SUM(CASE WHEN importance >= 0.8 THEN 1 ELSE 0 END) AS high_importance,
                    SUM(CASE WHEN importance >= 0.5 AND importance < 0.8 THEN 1 ELSE 0 END) AS medium_importance,
                    SUM(CASE WHEN importance < 0.5 THEN 1 ELSE 0 END) AS low_importance
                FROM memories
                WHERE scope_key = ?
            ''', (normalized_scope,))
            importance_stats = await cursor.fetchone()
            
            # Total relationships
            cursor = await db.execute('''
                SELECT COUNT(*)
                FROM memory_relationships mr
                JOIN memories source ON source.id = mr.source_memory_id
                JOIN memories target ON target.id = mr.target_memory_id
                WHERE source.scope_key = ? AND target.scope_key = ?
            ''', (normalized_scope, normalized_scope))
            total_relationships_row = await cursor.fetchone()
            total_relationships = total_relationships_row[0] if total_relationships_row else 0
            
            # Total clusters
            cursor = await db.execute(
                'SELECT COUNT(*) FROM memory_clusters WHERE scope_key = ?',
                (normalized_scope,),
            )
            total_clusters_row = await cursor.fetchone()
            total_clusters = total_clusters_row[0] if total_clusters_row else 0
            
            return {
                'total_memories': total_memories,
                'memory_types': memory_types,
                'average_importance': avg_importance or 0.0,
                'high_importance_memories': importance_stats[0] if importance_stats else 0,
                'medium_importance_memories': importance_stats[1] if importance_stats else 0,
                'low_importance_memories': importance_stats[2] if importance_stats else 0,
                'total_relationships': total_relationships,
                'total_clusters': total_clusters
            }

    async def close(self) -> None:
        """Close any persistent database resources held by this instance."""
        if self._keepalive_connection is not None:
            await self._keepalive_connection.close()
            self._keepalive_connection = None
