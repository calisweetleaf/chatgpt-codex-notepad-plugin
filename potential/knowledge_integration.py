"""
knowledge_integration: A comprehensive toolkit for transforming diverse knowledge sources into datasets through deep knowledge graph representation.

This module provides a robust system for processing various file formats into knowledge graphs,
then transforming those graphs into model-ready training examples optimized for true knowledge
integration rather than surface pattern recognition.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import logging
import math
import os
import random
import re
import stat
# The child parser uses a fixed interpreter, fixed inline program, positional
# arguments, no shell, and an isolated environment.  A process boundary is the
# security control that contains adversarial PDF/DOCX allocator amplification.
import subprocess  # nosec B404
import sys
import tempfile
import uuid
import zipfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Dict, Generator, Iterator, List, Mapping, Optional, Sequence, Set, Tuple, Union, cast

# Third-party libraries
import networkx as nx
import spacy

try:
    from pypdf import PdfReader
except ImportError:  # Optional capability: non-PDF ingestion remains available.
    PdfReader = None  # type: ignore[assignment]

from modules.semantic_db import SemanticMemoryDB

logger = logging.getLogger(__name__)

CACHE_SCHEMA_VERSION = 1
ZIP_MAX_MEMBERS = 10_000
ZIP_MAX_MEMBER_BYTES = 100 * 1024 * 1024
ZIP_MAX_TOTAL_BYTES = 512 * 1024 * 1024
ZIP_MAX_COMPRESSION_RATIO = 100.0
ZIP_COPY_CHUNK_BYTES = 1024 * 1024
SOURCE_MAX_FILES = 10_000
SOURCE_MAX_FILE_BYTES = 100 * 1024 * 1024
SOURCE_MAX_TOTAL_BYTES = 512 * 1024 * 1024
CACHE_MAX_JSON_BYTES = 100 * 1024 * 1024
SOURCE_HASH_CHUNK_BYTES = 1024 * 1024

# The extractor is a production ingress boundary, not an unbounded research
# workspace.  These limits are deliberately shared by every parser and every
# graph-construction path so a small source cannot amplify into an arbitrarily
# large in-memory graph.
SOURCE_MAX_ENTRIES = 20_000
GRAPH_MAX_ENTITIES = 10_000
GRAPH_MAX_RELATIONSHIPS = 25_000
GRAPH_MAX_IDENTIFIER_CHARACTERS = 1_024
GRAPH_MAX_LABEL_CHARACTERS = 16_384
GRAPH_MAX_CONTEXT_CHARACTERS = 64 * 1_024
GRAPH_MAX_STRING_CHARACTERS = 1 * 1_048_576
GRAPH_MAX_ATTRIBUTE_BYTES = 1 * 1_048_576
GRAPH_MAX_SERIALIZED_BYTES = 8 * 1_048_576
GRAPH_SERIALIZATION_OVERHEAD_BYTES = 64 * 1_024
PARENT_PARSER_MAX_SOURCE_BYTES = GRAPH_MAX_SERIALIZED_BYTES
INGEST_MAX_WORKERS = 4
JSON_MAX_DEPTH = 64
JSON_MAX_ITEMS = 100_000
STRUCTURED_MAX_ROWS = 10_000
PLAINTEXT_MAX_SENTENCES = 100_000
PLAINTEXT_MAX_ENTITY_SENTENCE_CHECKS = 2_000_000
PLAINTEXT_MAX_COOCCURRENCE_PAIRS = GRAPH_MAX_RELATIONSHIPS
DOCUMENT_MAX_PAGES = 2_000
DOCUMENT_MAX_TEXT_CHARACTERS = 8 * 1_048_576
DOCUMENT_MAX_ARCHIVE_MEMBERS = 10_000
DOCUMENT_MAX_ARCHIVE_MEMBER_BYTES = 64 * 1_048_576
DOCUMENT_MAX_ARCHIVE_TOTAL_BYTES = 256 * 1_048_576
DOCUMENT_MAX_ARCHIVE_COMPRESSION_RATIO = 100.0
DOCUMENT_WORKER_MEMORY_BYTES = 256 * 1_048_576
DOCUMENT_WORKER_CPU_SECONDS = 10
DOCUMENT_WORKER_TIMEOUT_SECONDS = 15.0

_DOCUMENT_WORKER_CODE = r"""
import json
import resource
import sys

kind = sys.argv[1]
path = sys.argv[2]
maximum_pages = int(sys.argv[3])
maximum_characters = int(sys.argv[4])
memory_bytes = int(sys.argv[5])
cpu_seconds = int(sys.argv[6])

resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1))
resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))

try:
    parts = []
    characters = 0
    if kind == "pdf":
        from pypdf import PdfReader

        with open(path, "rb") as source:
            reader = PdfReader(source)
            page_count = len(reader.pages)
            if page_count > maximum_pages:
                raise ValueError(
                    f"PDF contains {page_count} pages; limit is {maximum_pages}"
                )
            for page_index, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                if not isinstance(page_text, str):
                    raise ValueError(
                        f"PDF page {page_index + 1} returned non-text content"
                    )
                framed = f"\n[page {page_index + 1}]\n{page_text}"
                characters += len(framed)
                if characters > maximum_characters:
                    raise ValueError(
                        f"PDF extracted text exceeds {maximum_characters} characters"
                    )
                parts.append(framed)
    elif kind == "docx":
        import docx

        document = docx.Document(path)
        for paragraph in document.paragraphs:
            paragraph_text = paragraph.text
            characters += len(paragraph_text) + 1
            if characters > maximum_characters:
                raise ValueError(
                    f"DOCX extracted text exceeds {maximum_characters} characters"
                )
            parts.append(paragraph_text)
    elif kind in {"markdown", "html", "xml"}:
        from bs4 import BeautifulSoup

        with open(path, "r", encoding="utf-8") as source:
            source_text = source.read(maximum_characters + 1)
        if len(source_text) > maximum_characters:
            raise ValueError(
                f"{kind.upper()} source text exceeds {maximum_characters} characters"
            )
        if kind == "markdown":
            import markdown

            source_text = markdown.markdown(source_text)
        text = BeautifulSoup(source_text, "html.parser").get_text("\n")
        if len(text) > maximum_characters:
            raise ValueError(
                f"{kind.upper()} extracted text exceeds {maximum_characters} characters"
            )
        parts.append(text)
    else:
        raise ValueError(f"Unsupported bounded document kind: {kind}")

    text = "\n".join(parts).strip()
    json.dump({"text": text}, sys.stdout, ensure_ascii=False)
except BaseException as error:
    message = str(error).replace("\n", " ")[:2000]
    sys.stderr.write(f"{type(error).__name__}: {message}\n")
    raise SystemExit(2)
"""

# ----------------------------------------
# Helper Functions
# ----------------------------------------

def generate_deterministic_id(parts: List[str]) -> str:
    """Generates a deterministic ID based on a list of string parts."""
    return hashlib.sha256("\0".join(parts).encode('utf-8')).hexdigest()

def generate_uuid() -> str:
    """Generates a random UUID."""
    return str(uuid.uuid4())


def _validate_bounded_string(
    value: object,
    *,
    field_name: str,
    maximum_characters: int,
    allow_none: bool = False,
) -> None:
    """Reject non-string and oversized graph string fields."""
    if value is None and allow_none:
        return
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    if not value:
        raise ValueError(f"{field_name} must be non-empty")
    if len(value) > maximum_characters:
        raise ValueError(
            f"{field_name} exceeds {maximum_characters} characters"
        )


def _validate_json_payload(
    payload: object,
    *,
    field_name: str,
    maximum_bytes: int = GRAPH_MAX_ATTRIBUTE_BYTES,
    maximum_depth: int = JSON_MAX_DEPTH,
    maximum_items: int = JSON_MAX_ITEMS,
) -> int:
    """Validate bounded, finite, JSON-compatible state without recursion."""
    stack: List[Tuple[object, int]] = [(payload, 0)]
    item_count = 0
    while stack:
        value, depth = stack.pop()
        item_count += 1
        if item_count > maximum_items:
            raise ValueError(f"{field_name} exceeds {maximum_items} JSON items")
        if depth > maximum_depth:
            raise ValueError(f"{field_name} exceeds JSON depth {maximum_depth}")

        if value is None or isinstance(value, (bool, int)):
            continue
        if isinstance(value, float):
            if not math.isfinite(value):
                raise ValueError(f"{field_name} contains a non-finite number")
            continue
        if isinstance(value, str):
            if len(value) > GRAPH_MAX_STRING_CHARACTERS:
                raise ValueError(
                    f"{field_name} contains a string exceeding "
                    f"{GRAPH_MAX_STRING_CHARACTERS} characters"
                )
            continue
        if isinstance(value, dict):
            if item_count + len(stack) + len(value) > maximum_items:
                raise ValueError(f"{field_name} exceeds {maximum_items} JSON items")
            for key, child in value.items():
                if not isinstance(key, str):
                    raise ValueError(f"{field_name} contains a non-string key")
                if len(key) > GRAPH_MAX_IDENTIFIER_CHARACTERS:
                    raise ValueError(
                        f"{field_name} contains a key exceeding "
                        f"{GRAPH_MAX_IDENTIFIER_CHARACTERS} characters"
                    )
                stack.append((child, depth + 1))
            continue
        if isinstance(value, (list, tuple)):
            if item_count + len(stack) + len(value) > maximum_items:
                raise ValueError(f"{field_name} exceeds {maximum_items} JSON items")
            stack.extend((child, depth + 1) for child in value)
            continue
        raise ValueError(
            f"{field_name} contains a non-JSON value of type "
            f"{type(value).__name__}"
        )

    try:
        encoded_size = len(
            json.dumps(
                payload,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        )
    except (RecursionError, TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{field_name} is not valid bounded JSON") from error
    if encoded_size > maximum_bytes:
        raise ValueError(f"{field_name} exceeds {maximum_bytes} encoded bytes")
    return item_count


def _encoded_json_size(payload: object, *, field_name: str) -> int:
    """Return canonical JSON size while translating unsafe payload failures."""
    try:
        return len(
            json.dumps(
                payload,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        )
    except (RecursionError, TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{field_name} is not valid JSON") from error


def stream_source_sha256(file_path: Union[str, Path]) -> Tuple[str, int]:
    """Hash one bounded regular file without following a final symlink."""
    path = Path(file_path)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except FileNotFoundError:
        raise
    except OSError as error:
        raise ValueError(f"Source must be a readable regular file: {path}") from error

    digest = hashlib.sha256()
    total_read = 0
    try:
        file_stat = os.fstat(descriptor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise ValueError(f"Source is not a regular file: {path}")
        if file_stat.st_size > SOURCE_MAX_FILE_BYTES:
            raise ValueError(
                f"Source file exceeds {SOURCE_MAX_FILE_BYTES} bytes: {path}"
            )
        with os.fdopen(descriptor, "rb", closefd=False) as source:
            while chunk := source.read(SOURCE_HASH_CHUNK_BYTES):
                total_read += len(chunk)
                if total_read > SOURCE_MAX_FILE_BYTES:
                    raise ValueError(
                        f"Source file grew beyond {SOURCE_MAX_FILE_BYTES} bytes: {path}"
                    )
                digest.update(chunk)
    finally:
        os.close(descriptor)

    return digest.hexdigest(), total_read


def _extract_document_text_isolated(kind: str, file_path: Path) -> str:
    """Extract document text behind hard OS memory, CPU, and wall-time limits."""
    if kind not in {"pdf", "docx", "markdown", "html", "xml"}:
        raise ValueError(f"Unsupported bounded document kind: {kind}")
    arguments = [
        sys.executable,
        "-I",
        "-c",
        _DOCUMENT_WORKER_CODE,
        kind,
        os.fspath(file_path),
        str(DOCUMENT_MAX_PAGES),
        str(DOCUMENT_MAX_TEXT_CHARACTERS),
        str(DOCUMENT_WORKER_MEMORY_BYTES),
        str(DOCUMENT_WORKER_CPU_SECONDS),
    ]
    try:
        # Fixed executable/argv and shell=False by construction.
        completed = subprocess.run(  # nosec B603
            arguments,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=DOCUMENT_WORKER_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(
            f"{kind.upper()} parser exceeded "
            f"{DOCUMENT_WORKER_TIMEOUT_SECONDS:.0f} wall-clock seconds"
        ) from error

    maximum_output_bytes = DOCUMENT_MAX_TEXT_CHARACTERS * 6 + 4096
    if len(completed.stdout) > maximum_output_bytes:
        raise RuntimeError(
            f"{kind.upper()} parser returned an oversized response"
        )
    if completed.returncode != 0:
        diagnostic = completed.stderr.decode("utf-8", errors="replace").strip()
        if len(diagnostic) > 2048:
            diagnostic = diagnostic[:2048]
        if completed.returncode < 0:
            diagnostic = (
                f"worker terminated by signal {-completed.returncode}; "
                "resource limit exceeded"
            )
        raise RuntimeError(
            f"{kind.upper()} parser failed inside its resource boundary"
            + (f": {diagnostic}" if diagnostic else "")
        )

    try:
        payload = json.loads(completed.stdout)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError(
            f"{kind.upper()} parser returned an invalid response"
        ) from error
    if not isinstance(payload, dict) or not isinstance(payload.get("text"), str):
        raise RuntimeError(f"{kind.upper()} parser returned no text field")
    text = cast(str, payload["text"])
    if len(text) > DOCUMENT_MAX_TEXT_CHARACTERS:
        raise RuntimeError(
            f"{kind.upper()} parser bypassed the extracted-text bound"
        )
    return text

# ----------------------------------------
# Data Structures and Type Definitions
# ----------------------------------------

class FormatType(Enum):
    """Enumeration of supported file formats."""
    UNKNOWN = 0
    PLAINTEXT = 1
    JSON = 2
    CSV = 3
    JSONL = 4
    XML = 5
    HTML = 6
    MARKDOWN = 7
    PDF = 8
    DOCX = 9
    CHATGPT_EXPORT = 10
    CLAUDE_EXPORT = 11
    DEEPSEEK_EXPORT = 12
    LLAMA_EXPORT = 13
    ZIP_ARCHIVE = 14
    DIRECTORY = 15

class ContentType(Enum):
    """Enumeration of logical content types."""
    UNKNOWN = 0
    CONVERSATION = 1
    ARTICLE = 2
    REFERENCE = 3
    DOCUMENTATION = 4
    STRUCTURED_DATA = 5
    ACADEMIC_PAPER = 6
    CODE = 7
    MIXED = 8

class EntityType(Enum):
    """Types of entities in the knowledge graph."""
    CONCEPT = 1
    PERSON = 2
    ORGANIZATION = 3
    LOCATION = 4
    EVENT = 5
    PRODUCT = 6
    TECHNICAL_TERM = 7
    CODE_ENTITY = 8
    DATETIME = 9
    NUMERICAL_VALUE = 10
    PROCEDURE = 11
    STRUCTURED_DATA = 12
    CUSTOM = 13

class RelationType(Enum):
    """Types of relationships in the knowledge graph."""
    IS_A = 1
    PART_OF = 2
    HAS_PROPERTY = 3
    RELATED_TO = 4
    CAUSES = 5
    DEPENDS_ON = 6
    LOCATED_IN = 7
    OCCURS_AT = 8
    CREATED_BY = 9
    USED_FOR = 10
    INTERACTS_WITH = 11
    BEFORE = 12
    AFTER = 13
    CUSTOM = 14

@dataclass
class Entity:
    """Represents an entity in the knowledge graph."""
    id: str
    label: str
    type: EntityType
    properties: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_doc_id: Optional[str] = None
    text_span: Optional[Tuple[int, int]] = None

    @property
    def name(self) -> str:
        """Compatibility alias for the canonical entity label."""
        return self.label

    @property
    def attributes(self) -> Dict[str, Any]:
        """Compatibility alias for canonical entity properties."""
        return self.properties

@dataclass
class Relationship:
    """Represents a relationship between two entities in the knowledge graph."""
    id: str
    source_id: str
    target_id: str
    label: RelationType
    properties: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_doc_id: Optional[str] = None
    context: Optional[str] = None

    @property
    def type(self) -> RelationType:
        """Compatibility alias for the canonical relationship label."""
        return self.label

    @property
    def attributes(self) -> Dict[str, Any]:
        """Compatibility alias for canonical relationship properties."""
        return self.properties

    @property
    def confidence(self) -> float:
        """Return the bounded relationship confidence stored in properties."""
        raw_confidence = self.properties.get("confidence", 1.0)
        try:
            return min(max(float(raw_confidence), 0.0), 1.0)
        except (TypeError, ValueError):
            return 0.0


class RelationshipCollection(list[Relationship]):
    """List-backed relationship collection with legacy id-map accessors."""

    def values(self) -> "RelationshipCollection":
        """Return relationships in insertion order."""
        return self

    def items(self) -> Iterator[Tuple[str, Relationship]]:
        """Iterate over relationship ids and records."""
        return ((relationship.id, relationship) for relationship in self)

    def __contains__(self, item: object) -> bool:
        """Accept either a relationship record or its identifier."""
        if isinstance(item, str):
            return any(relationship.id == item for relationship in self)
        return super().__contains__(item)

    def __delitem__(self, index: Union[int, slice, str]) -> None:
        """Delete by list index/slice or by relationship identifier."""
        if isinstance(index, str):
            for position, relationship in enumerate(self):
                if relationship.id == index:
                    super().__delitem__(position)
                    return
            raise KeyError(index)
        super().__delitem__(index)

@dataclass
class KnowledgeGraph:
    """Represents the entire knowledge graph."""
    entities: Dict[str, Entity] = field(default_factory=dict)
    relationships: RelationshipCollection = field(default_factory=RelationshipCollection)
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_references: Dict[str, Any] = field(default_factory=dict) # To store info about original documents
    _retained_payload_bytes: int = field(init=False, repr=False, default=0)
    _entity_payload_bytes: Dict[str, int] = field(
        init=False,
        repr=False,
        default_factory=dict,
    )
    _relationship_payload_bytes: List[int] = field(
        init=False,
        repr=False,
        default_factory=list,
    )

    def __post_init__(self) -> None:
        """Validate constructor-supplied state through mutation boundaries."""
        original_entities = dict(self.entities)
        original_relationships = list(self.relationships)
        if not isinstance(self.metadata, dict):
            raise ValueError("Knowledge graph metadata must be a dictionary")
        if not isinstance(self.source_references, dict):
            raise ValueError("Knowledge graph source references must be a dictionary")
        _validate_json_payload(self.metadata, field_name="Knowledge graph metadata")
        _validate_json_payload(
            self.source_references,
            field_name="Knowledge graph source references",
        )
        base_payload_bytes = _encoded_json_size(
            {
                "metadata": self.metadata,
                "source_references": self.source_references,
            },
            field_name="Knowledge graph base state",
        )
        if (
            base_payload_bytes + GRAPH_SERIALIZATION_OVERHEAD_BYTES
            > GRAPH_MAX_SERIALIZED_BYTES
        ):
            raise ValueError(
                "Knowledge graph exceeds "
                f"{GRAPH_MAX_SERIALIZED_BYTES} retained payload bytes"
            )
        self._retained_payload_bytes = base_payload_bytes
        self._entity_payload_bytes = {}
        self._relationship_payload_bytes = []
        self.entities = {}
        self.relationships = RelationshipCollection()
        for entity_id, entity in original_entities.items():
            if entity_id != entity.id:
                raise ValueError(
                    "Knowledge graph entity map key must match the entity id"
                )
            self.add_entity(entity)
        for relationship in original_relationships:
            self.add_relationship(relationship)

    @staticmethod
    def _validate_entity(entity: Entity) -> None:
        """Validate one entity before it reaches graph-owned state."""
        if not isinstance(entity, Entity):
            raise ValueError("Knowledge graph entities must be Entity values")
        _validate_bounded_string(
            entity.id,
            field_name="Entity id",
            maximum_characters=GRAPH_MAX_IDENTIFIER_CHARACTERS,
        )
        _validate_bounded_string(
            entity.label,
            field_name="Entity label",
            maximum_characters=GRAPH_MAX_LABEL_CHARACTERS,
        )
        if not isinstance(entity.type, EntityType):
            raise ValueError("Entity type must be an EntityType value")
        if not isinstance(entity.properties, dict):
            raise ValueError("Entity properties must be a dictionary")
        if not isinstance(entity.metadata, dict):
            raise ValueError("Entity metadata must be a dictionary")
        _validate_json_payload(
            entity.properties,
            field_name=f"Entity {entity.id} properties",
        )
        _validate_json_payload(
            entity.metadata,
            field_name=f"Entity {entity.id} metadata",
        )
        if entity.source_doc_id is not None:
            _validate_bounded_string(
                entity.source_doc_id,
                field_name="Entity source_doc_id",
                maximum_characters=GRAPH_MAX_IDENTIFIER_CHARACTERS,
            )
        if entity.text_span is not None and (
            not isinstance(entity.text_span, tuple)
            or len(entity.text_span) != 2
            or any(type(offset) is not int for offset in entity.text_span)
            or entity.text_span[0] < 0
            or entity.text_span[1] < entity.text_span[0]
        ):
            raise ValueError("Entity text_span must be a non-negative integer range")

    @staticmethod
    def _validate_relationship(relationship: Relationship) -> None:
        """Validate one relationship before it reaches graph-owned state."""
        if not isinstance(relationship, Relationship):
            raise ValueError(
                "Knowledge graph relationships must be Relationship values"
            )
        for field_name, value in (
            ("Relationship id", relationship.id),
            ("Relationship source_id", relationship.source_id),
            ("Relationship target_id", relationship.target_id),
        ):
            _validate_bounded_string(
                value,
                field_name=field_name,
                maximum_characters=GRAPH_MAX_IDENTIFIER_CHARACTERS,
            )
        if not isinstance(relationship.label, RelationType):
            raise ValueError("Relationship label must be a RelationType value")
        if not isinstance(relationship.properties, dict):
            raise ValueError("Relationship properties must be a dictionary")
        if not isinstance(relationship.metadata, dict):
            raise ValueError("Relationship metadata must be a dictionary")
        _validate_json_payload(
            relationship.properties,
            field_name=f"Relationship {relationship.id} properties",
        )
        _validate_json_payload(
            relationship.metadata,
            field_name=f"Relationship {relationship.id} metadata",
        )
        if relationship.source_doc_id is not None:
            _validate_bounded_string(
                relationship.source_doc_id,
                field_name="Relationship source_doc_id",
                maximum_characters=GRAPH_MAX_IDENTIFIER_CHARACTERS,
            )
        if relationship.context is not None:
            if not isinstance(relationship.context, str):
                raise ValueError("Relationship context must be a string or None")
            if len(relationship.context) > GRAPH_MAX_CONTEXT_CHARACTERS:
                raise ValueError(
                    "Relationship context exceeds "
                    f"{GRAPH_MAX_CONTEXT_CHARACTERS} characters"
                )

    @staticmethod
    def _copy_entity(entity: Entity) -> Entity:
        """Copy mutable entity containers for atomic merge preflight."""
        return Entity(
            id=entity.id,
            label=entity.label,
            type=entity.type,
            properties=dict(entity.properties),
            metadata=dict(entity.metadata),
            source_doc_id=entity.source_doc_id,
            text_span=entity.text_span,
        )

    def add_entity(self, entity: Entity) -> None:
        """Adds an entity to the graph."""
        self._validate_entity(entity)
        if entity.id not in self.entities and len(self.entities) >= GRAPH_MAX_ENTITIES:
            raise ValueError(
                f"Knowledge graph exceeds {GRAPH_MAX_ENTITIES} entities"
            )
        if entity.id in self.entities:
            logger.warning(f"Entity with ID {entity.id} already exists. Overwriting.")
        entity_payload_bytes = _encoded_json_size(
            {
                "map_key": entity.id,
                "id": entity.id,
                "label": entity.label,
                "type": entity.type.name,
                "properties": entity.properties,
                "metadata": entity.metadata,
                "source_doc_id": entity.source_doc_id,
                "text_span": entity.text_span,
            },
            field_name=f"Entity {entity.id}",
        )
        replaced_payload_bytes = self._entity_payload_bytes.get(entity.id, 0)
        projected_payload_bytes = (
            self._retained_payload_bytes
            - replaced_payload_bytes
            + entity_payload_bytes
            + GRAPH_SERIALIZATION_OVERHEAD_BYTES
        )
        if projected_payload_bytes > GRAPH_MAX_SERIALIZED_BYTES:
            raise ValueError(
                "Knowledge graph exceeds "
                f"{GRAPH_MAX_SERIALIZED_BYTES} retained payload bytes"
            )
        self.entities[entity.id] = entity
        self._entity_payload_bytes[entity.id] = entity_payload_bytes
        self._retained_payload_bytes = (
            projected_payload_bytes - GRAPH_SERIALIZATION_OVERHEAD_BYTES
        )

    def add_relationship(self, relationship: Relationship) -> None:
        """Adds a relationship to the graph."""
        self._validate_relationship(relationship)
        if relationship.source_id not in self.entities:
            raise ValueError(f"Source entity {relationship.source_id} not found in graph.")
        if relationship.target_id not in self.entities:
            raise ValueError(f"Target entity {relationship.target_id} not found in graph.")
        if len(self.relationships) >= GRAPH_MAX_RELATIONSHIPS:
            raise ValueError(
                f"Knowledge graph exceeds {GRAPH_MAX_RELATIONSHIPS} relationships"
            )
        relationship_payload_bytes = _encoded_json_size(
            {
                "id": relationship.id,
                "source_id": relationship.source_id,
                "target_id": relationship.target_id,
                "label": relationship.label.name,
                "properties": relationship.properties,
                "metadata": relationship.metadata,
                "source_doc_id": relationship.source_doc_id,
                "context": relationship.context,
            },
            field_name=f"Relationship {relationship.id}",
        )
        projected_payload_bytes = (
            self._retained_payload_bytes
            + relationship_payload_bytes
            + GRAPH_SERIALIZATION_OVERHEAD_BYTES
        )
        if projected_payload_bytes > GRAPH_MAX_SERIALIZED_BYTES:
            raise ValueError(
                "Knowledge graph exceeds "
                f"{GRAPH_MAX_SERIALIZED_BYTES} retained payload bytes"
            )
        self.relationships.append(relationship)
        self._relationship_payload_bytes.append(relationship_payload_bytes)
        self._retained_payload_bytes = (
            projected_payload_bytes - GRAPH_SERIALIZATION_OVERHEAD_BYTES
        )

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Retrieves an entity by its ID."""
        return self.entities.get(entity_id)
        
    def get_entity_by_name(self, name: str, entity_type: Optional[EntityType] = None) -> Optional[Entity]:
        """Retrieves an entity by its name/label and optionally type."""
        for entity in self.entities.values():
            if entity.label == name and (entity_type is None or entity.type == entity_type):
                return entity
        return None
        
    def get_entities_by_type(self, entity_type: EntityType) -> List[Entity]:
        """Retrieves all entities of a specific type."""
        return [e for e in self.entities.values() if e.type == entity_type]
        
    def get_relationships_by_type(self, relation_type: RelationType) -> List[Relationship]:
        """Retrieves all relationships of a specific type."""
        return [r for r in self.relationships if r.label == relation_type]
        
    def get_relationships_for_entity(self, entity_id: str, as_source: bool = True, as_target: bool = True) -> List[Relationship]:
        """Retrieves all relationships for a specific entity."""
        result = []
        if as_source:
            result.extend([r for r in self.relationships if r.source_id == entity_id])
        if as_target:
            result.extend([r for r in self.relationships if r.target_id == entity_id])
        return result
        
    def merge(self, other_kg: 'KnowledgeGraph') -> None:
        """Atomically merge another graph after complete bounded preflight."""
        if not isinstance(other_kg, KnowledgeGraph):
            raise ValueError("Can only merge another KnowledgeGraph")
        self.validate()
        other_kg.validate()

        candidate_entities = {
            entity_id: self._copy_entity(entity)
            for entity_id, entity in self.entities.items()
        }
        for entity_id, entity in other_kg.entities.items():
            if entity_id not in candidate_entities:
                candidate_entities[entity_id] = self._copy_entity(entity)
                continue
            existing = candidate_entities[entity_id]
            for key, value in entity.properties.items():
                existing.properties.setdefault(key, value)
            for key, value in entity.metadata.items():
                existing.metadata.setdefault(key, value)
            self._validate_entity(existing)
        if len(candidate_entities) > GRAPH_MAX_ENTITIES:
            raise ValueError(
                f"Knowledge graph merge exceeds {GRAPH_MAX_ENTITIES} entities"
            )

        existing_relationship_ids = {
            relationship.id for relationship in self.relationships
        }
        candidate_relationships = RelationshipCollection(self.relationships)
        for relationship in other_kg.relationships:
            if relationship.id not in existing_relationship_ids:
                candidate_relationships.append(relationship)
                existing_relationship_ids.add(relationship.id)
        if len(candidate_relationships) > GRAPH_MAX_RELATIONSHIPS:
            raise ValueError(
                "Knowledge graph merge exceeds "
                f"{GRAPH_MAX_RELATIONSHIPS} relationships"
            )

        candidate_metadata = dict(self.metadata)
        for key, value in other_kg.metadata.items():
            candidate_metadata.setdefault(key, value)
        candidate_references = dict(self.source_references)
        for key, value in other_kg.source_references.items():
            candidate_references.setdefault(key, value)

        candidate = KnowledgeGraph(
            entities=candidate_entities,
            relationships=candidate_relationships,
            metadata=candidate_metadata,
            source_references=candidate_references,
        )
        candidate.validate(serialized_size=True)
        self.entities = candidate.entities
        self.relationships = candidate.relationships
        self.metadata = candidate.metadata
        self.source_references = candidate.source_references
        self._retained_payload_bytes = candidate._retained_payload_bytes
        self._entity_payload_bytes = candidate._entity_payload_bytes
        self._relationship_payload_bytes = candidate._relationship_payload_bytes
        
    def to_networkx_graph(self) -> nx.MultiDiGraph:
        """Converts the knowledge graph to a NetworkX MultiDiGraph."""
        graph = nx.MultiDiGraph()
        for entity_id, entity in self.entities.items():
            graph.add_node(entity_id, label=entity.label, type=entity.type.name, **entity.properties)
        for rel in self.relationships:
            graph.add_edge(rel.source_id, rel.target_id, key=rel.id, label=rel.label.name, **rel.properties)
        return graph

    def to_networkx(self) -> nx.MultiDiGraph:
        """Return the canonical NetworkX representation."""
        return self.to_networkx_graph()

    def _as_dict_unchecked(self) -> Dict[str, Any]:
        """Build the serialization payload after callers validate graph state."""
        return {
            "metadata": self.metadata,
            "entities": {
                entity_id: {
                    "id": entity.id,
                    "label": entity.label,
                    "type": entity.type.name,
                    "properties": entity.properties,
                    "metadata": entity.metadata,
                    "source_doc_id": entity.source_doc_id,
                    "text_span": entity.text_span,
                }
                for entity_id, entity in self.entities.items()
            },
            "relationships": [
                {
                    "id": relationship.id,
                    "source_id": relationship.source_id,
                    "target_id": relationship.target_id,
                    "label": relationship.label.name,
                    "properties": relationship.properties,
                    "metadata": relationship.metadata,
                    "source_doc_id": relationship.source_doc_id,
                    "context": relationship.context,
                }
                for relationship in self.relationships
            ],
            "source_references": self.source_references,
        }

    def validate(self, *, serialized_size: bool = False) -> None:
        """Validate current graph state, including direct external mutations."""
        if len(self.entities) > GRAPH_MAX_ENTITIES:
            raise ValueError(
                f"Knowledge graph exceeds {GRAPH_MAX_ENTITIES} entities"
            )
        if len(self.relationships) > GRAPH_MAX_RELATIONSHIPS:
            raise ValueError(
                f"Knowledge graph exceeds {GRAPH_MAX_RELATIONSHIPS} relationships"
            )
        _validate_json_payload(self.metadata, field_name="Knowledge graph metadata")
        _validate_json_payload(
            self.source_references,
            field_name="Knowledge graph source references",
        )
        for entity_id, entity in self.entities.items():
            if entity_id != entity.id:
                raise ValueError(
                    "Knowledge graph entity map key must match the entity id"
                )
            self._validate_entity(entity)
        for relationship in self.relationships:
            self._validate_relationship(relationship)
            if relationship.source_id not in self.entities:
                raise ValueError(
                    f"Source entity {relationship.source_id} not found in graph."
                )
            if relationship.target_id not in self.entities:
                raise ValueError(
                    f"Target entity {relationship.target_id} not found in graph."
                )
        if serialized_size:
            encoded_size = _encoded_json_size(
                self._as_dict_unchecked(),
                field_name="Knowledge graph",
            )
            if encoded_size > GRAPH_MAX_SERIALIZED_BYTES:
                raise ValueError(
                    "Knowledge graph exceeds "
                    f"{GRAPH_MAX_SERIALIZED_BYTES} encoded bytes"
                )

    def to_dict(self) -> Dict[str, Any]:
        """Converts the knowledge graph to a dictionary for serialization."""
        self.validate(serialized_size=True)
        return self._as_dict_unchecked()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeGraph":
        """Build a knowledge graph from a validated dictionary representation."""
        if not isinstance(data, dict):
            raise TypeError("Knowledge graph payload must be a dictionary")

        raw_entities = data.get("entities", {})
        raw_relationships = data.get("relationships", [])
        raw_metadata = data.get("metadata", {})
        raw_source_references = data.get("source_references", {})
        if not isinstance(raw_entities, dict):
            raise ValueError("Knowledge graph entities must be a dictionary")
        if not isinstance(raw_relationships, list):
            raise ValueError("Knowledge graph relationships must be a list")
        if not isinstance(raw_metadata, dict):
            raise ValueError("Knowledge graph metadata must be a dictionary")
        if not isinstance(raw_source_references, dict):
            raise ValueError("Knowledge graph source references must be a dictionary")
        if len(raw_entities) > GRAPH_MAX_ENTITIES:
            raise ValueError(
                f"Knowledge graph exceeds {GRAPH_MAX_ENTITIES} entities"
            )
        if len(raw_relationships) > GRAPH_MAX_RELATIONSHIPS:
            raise ValueError(
                f"Knowledge graph exceeds {GRAPH_MAX_RELATIONSHIPS} relationships"
            )

        graph = cls(
            metadata=dict(raw_metadata),
            source_references=dict(raw_source_references),
        )
        
        # Load entities
        for eid, edata in raw_entities.items():
            if not isinstance(edata, dict):
                raise ValueError(f"Entity {eid!r} must be a dictionary")
            entity_type = EntityType[edata["type"]] if isinstance(edata["type"], str) else edata["type"]
            entity = Entity(
                id=edata["id"],
                label=edata["label"],
                type=entity_type,
                properties=edata.get("properties", {}),
                metadata=edata.get("metadata", {}),
                source_doc_id=edata.get("source_doc_id"),
                text_span=(
                    tuple(edata["text_span"])
                    if edata.get("text_span") is not None
                    else None
                ),
            )
            if eid != entity.id:
                raise ValueError(
                    "Knowledge graph entity map key must match the entity id"
                )
            graph.add_entity(entity)
        
        # Load relationships
        for rdata in raw_relationships:
            if not isinstance(rdata, dict):
                raise ValueError("Relationship entries must be dictionaries")
            relation_type = RelationType[rdata["label"]] if isinstance(rdata["label"], str) else rdata["label"]
            relationship = Relationship(
                id=rdata["id"],
                source_id=rdata["source_id"],
                target_id=rdata["target_id"],
                label=relation_type,
                properties=rdata.get("properties", {}),
                metadata=rdata.get("metadata", {}),
                source_doc_id=rdata.get("source_doc_id"),
                context=rdata.get("context"),
            )
            graph.add_relationship(relationship)

        graph.validate(serialized_size=True)
        return graph

@dataclass
class DatasetExample:
    """Represents a single example for fine-tuning or evaluation."""
    prompt: str
    completion: str
    id: str = field(default_factory=generate_uuid)
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_graph_ids: List[str] = field(default_factory=list) # IDs of entities/relationships used
    source_entity_ids: List[str] = field(default_factory=list)
    source_relationship_ids: List[str] = field(default_factory=list)

@dataclass
class Dataset:
    """Represents a collection of dataset examples."""
    examples: List[DatasetExample] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    creation_date: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass(frozen=True)
class SourceFileRecord:
    """Validated source file and its stable manifest-relative path."""

    path: Path
    manifest_path: str
    size_bytes: int

# ----------------------------------------
# Format Detection
# ----------------------------------------

class FormatDetector:
    """
    Detects the format and content type of input data.
    """
    
    # File extension mappings
    EXTENSION_MAP = {
        '.txt': FormatType.PLAINTEXT,
        '.json': FormatType.JSON,
        '.csv': FormatType.CSV,
        '.jsonl': FormatType.JSONL,
        '.xml': FormatType.XML,
        '.html': FormatType.HTML,
        '.htm': FormatType.HTML,
        '.md': FormatType.MARKDOWN,
        '.pdf': FormatType.PDF,
        '.docx': FormatType.DOCX,
        '.zip': FormatType.ZIP_ARCHIVE,
        # Add mappings for chat exports if they have specific extensions
        # '.chatgpt.json': FormatType.CHATGPT_EXPORT, # Example
    }
    
    @staticmethod
    def detect_format(file_path: Union[str, Path]) -> FormatType:
        """Detects file format based on extension and potentially content sniffing."""
        p = Path(file_path)
        if p.is_dir():
            return FormatType.DIRECTORY
        
        ext = p.suffix.lower()
        if ext in FormatDetector.EXTENSION_MAP:
            # Further checks for ambiguous JSON types (e.g., ChatGPT export vs generic JSON)
            if FormatDetector.EXTENSION_MAP[ext] == FormatType.JSON:
                try:
                    with open(p, 'r', encoding='utf-8') as f:
                        content_sample = f.read(2048) # Read a sample
                        # A real export normally exceeds this bounded sniff
                        # window. Parsing a truncated JSON prefix therefore
                        # produced false negatives. Detection selects the
                        # fail-loud parser; that parser validates the complete
                        # bounded document before graph construction.
                        if (
                            content_sample.lstrip().startswith("[")
                            and '"mapping"' in content_sample
                            and '"create_time"' in content_sample
                        ):
                            logger.debug(
                                "Detected %s as CHATGPT_EXPORT from bounded markers.",
                                p,
                            )
                            return FormatType.CHATGPT_EXPORT
                except (OSError, UnicodeError) as e:
                    logger.warning(f"Could not sniff content for {p}: {e}")
            return FormatDetector.EXTENSION_MAP[ext]
        
        # Fallback: content sniffing for unknown extensions (e.g. if .txt could be JSONL)
        try:
            with open(p, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                if first_line.startswith('{') and first_line.endswith('}'):
                    try:
                        json.loads(first_line)
                        # Could be JSON or JSONL. If multiple lines and all are valid JSON, it's JSONL.
                        # For simplicity, if extension is unknown but looks like JSON, assume JSONL as a common data format.
                        logger.debug(f"Detected {p} as JSONL based on content sniffing.")
                        return FormatType.JSONL
                    except json.JSONDecodeError as error:
                        logger.debug("Unknown-extension content is not JSON: %s", error)
        except (OSError, UnicodeError) as error:
            logger.debug("Could not read unknown-extension content from %s: %s", p, error)
            
        logger.warning(f"Could not determine format for {p}, defaulting to UNKNOWN.")
        return FormatType.UNKNOWN
    
    @staticmethod
    def detect_content_type(file_path: Union[str, Path], format_type: FormatType, content_sample: Optional[str] = None) -> ContentType:
        """Detects logical content type based on format and content clues."""
        if content_sample is None:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content_sample = f.read(4096) # Read a larger sample for content type detection
            except Exception:
                return ContentType.UNKNOWN

        if format_type in [FormatType.CHATGPT_EXPORT, FormatType.CLAUDE_EXPORT, FormatType.DEEPSEEK_EXPORT, FormatType.LLAMA_EXPORT]:
            return ContentType.CONVERSATION
        
        if format_type == FormatType.JSON:
            # Heuristic: if JSON looks like a conversation transcript
            if content_sample and ('"messages"' in content_sample or '"turns"' in content_sample or '"conversation_id"' in content_sample):
                 if re.search(r'("role"\s*:\s*"(user|assistant|system)")', content_sample, re.IGNORECASE):
                    logger.debug(f"Detected {file_path} as CONVERSATION based on JSON content.")
                    return ContentType.CONVERSATION
            if content_sample and ('"title"' in content_sample and '"text"' in content_sample and len(content_sample) > 500):
                logger.debug(f"Detected {file_path} as ARTICLE based on JSON content.")
                return ContentType.ARTICLE
            logger.debug(f"Detected {file_path} as STRUCTURED_DATA based on JSON format.")
            return ContentType.STRUCTURED_DATA

        if format_type == FormatType.JSONL:
             # Similar checks as JSON, but on the first few lines
            lines = content_sample.split('\n', 5)
            first_lines_sample = " ".join(lines[:3])
            if '"messages"' in first_lines_sample or '"turns"' in first_lines_sample or '"conversation_id"' in first_lines_sample:
                 if re.search(r'("role"\s*:\s*"(user|assistant|system)")', first_lines_sample, re.IGNORECASE):
                    logger.debug(f"Detected {file_path} as CONVERSATION based on JSONL content.")
                    return ContentType.CONVERSATION
            logger.debug(f"Detected {file_path} as STRUCTURED_DATA based on JSONL format.")
            return ContentType.STRUCTURED_DATA

        if format_type == FormatType.MARKDOWN:
            if content_sample and ('#' in content_sample or '- ' in content_sample or '* ' in content_sample):
                if "API" in content_sample or "SDK" in content_sample or "documentation" in content_sample.lower():
                    logger.debug(f"Detected {file_path} as DOCUMENTATION based on Markdown content.")
                    return ContentType.DOCUMENTATION
                logger.debug(f"Detected {file_path} as ARTICLE based on Markdown content.")
                return ContentType.ARTICLE # Or MIXED
        
        if format_type == FormatType.PLAINTEXT:
            # Simple heuristic for conversations in plain text
            if content_sample and re.search(r'(User|Human|Person|Customer):\s', content_sample, re.IGNORECASE) and \
               re.search(r'(Assistant|AI|Bot|Claude|GPT):\s', content_sample, re.IGNORECASE):
                logger.debug(f"Detected {file_path} as CONVERSATION based on plain text content.")
                return ContentType.CONVERSATION
            if content_sample and len(content_sample.split()) > 100: # Arbitrary length
                logger.debug(f"Detected {file_path} as ARTICLE based on plain text content.")
                return ContentType.ARTICLE
        
        # Add more rules for PDF, DOCX, CODE etc.
        # For PDF/DOCX, might need to extract text first then apply similar heuristics
        # For CODE, check for common code keywords, syntax patterns.

        logger.debug(f"Defaulting content type for {file_path} to UNKNOWN or based on format.")
        if format_type in [FormatType.CSV, FormatType.XML]: # Usually structured
            return ContentType.STRUCTURED_DATA
        if format_type == FormatType.PLAINTEXT:
            return ContentType.ARTICLE # A common default for text
            
        return ContentType.UNKNOWN
    
    @staticmethod
    def get_file_id(file_path: Union[str, Path]) -> str:
        """Generate a deterministic identity from the source bytes."""
        content_digest, _ = stream_source_sha256(file_path)
        return content_digest


# ----------------------------------------
# Knowledge Extraction
# ----------------------------------------

class KnowledgeExtractor:
    """
    Base class for extractors that process different file formats.
    """
    
    def extract(self, file_path: Union[str, Path]) -> KnowledgeGraph:
        """Extracts knowledge from a file, returning a knowledge graph."""
        p = Path(file_path)
        file_id = FormatDetector.get_file_id(p)
        kg = KnowledgeGraph(metadata={'source_file_path': str(p), 'source_file_id': file_id})
        logger.info(f"Starting extraction for {p} (ID: {file_id})")
        return kg # Base class returns empty KG, subclasses should populate it

class PlaintextExtractor(KnowledgeExtractor):
    """
    Extracts knowledge from plaintext files.
    """
    
    def extract(self, file_path: Union[str, Path]) -> KnowledgeGraph:
        p = Path(file_path)
        kg = super().extract(file_path) # Get initial KG with metadata
        file_id = kg.metadata['source_file_id']

        try:
            with open(p, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Error reading plaintext file {p}: {e}")
            raise RuntimeError(f"Error reading plaintext file {p}") from e

        # Regex-based baseline extraction keeps ingestion deterministic and local.
        self._extract_entities_simple(content, kg, file_id)
        self._extract_relationships_simple(content, kg, file_id)
        
        logger.info(f"Extracted {len(kg.entities)} entities and {len(kg.relationships)} relationships from {p}.")
        return kg
    
    def _extract_entities_simple(self, content: str, kg: KnowledgeGraph, file_id: str) -> None:
        """Very basic entity extraction (e.g., capitalized words, terms in quotes)."""
        # Extract capitalized words as potential CONCEPTS or TECHNICAL_TERMS
        paragraphs = content.split('\n\n')
        current_pos = 0
        for para_idx, para_content in enumerate(paragraphs):
            # Proper nouns (simple regex)
            for match in re.finditer(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b', para_content):
                term = match.group(1)
                entity_id = generate_deterministic_id([file_id, "entity", term])
                if not kg.get_entity_by_name(term, EntityType.CONCEPT):
                    entity = Entity(
                        id=entity_id,
                        label=term,
                        type=EntityType.CONCEPT, 
                        metadata={
                            'source_paragraph': para_idx, 
                            'start_char': match.start() + current_pos, 
                            'end_char': match.end() + current_pos
                        },
                        source_doc_id=file_id,
                        text_span=(match.start() + current_pos, match.end() + current_pos)
                    )
                    kg.add_entity(entity)
            
            # Terms in quotes
            for match in re.finditer(r'["`\'](.+?)["`\']', para_content):
                term = match.group(1)
                entity_id = generate_deterministic_id([file_id, "entity", term])
                if not kg.get_entity_by_name(term, EntityType.TECHNICAL_TERM):
                    entity = Entity(
                        id=entity_id,
                        label=term,
                        type=EntityType.TECHNICAL_TERM,
                        metadata={
                            'source_paragraph': para_idx, 
                            'start_char': match.start() + current_pos, 
                            'end_char': match.end() + current_pos
                        },
                        source_doc_id=file_id,
                        text_span=(match.start() + current_pos, match.end() + current_pos)
                    )
                    kg.add_entity(entity)
            current_pos += len(para_content) + 2 # +2 for \n\n

    def _extract_relationships_simple(self, content: str, kg: KnowledgeGraph, file_id: str) -> None:
        """Extract bounded co-occurrence pairs after a no-allocation preflight."""
        entities = tuple(kg.entities.values())
        sentence_matches: List[Tuple[int, int, str, Tuple[Entity, ...]]] = []
        sentence_count = 0
        entity_checks = 0
        candidate_pair_work = 0

        def iter_sentences() -> Iterator[Tuple[int, int, str]]:
            """Yield sentence indexes, source offsets, and text incrementally."""
            start_char = 0
            sentence_index = 0
            for separator in re.finditer(r'[.!?]+\s*', content):
                yield sentence_index, start_char, content[start_char:separator.start()]
                sentence_index += 1
                start_char = separator.end()
            yield sentence_index, start_char, content[start_char:]

        for sent_idx, start_char, sentence_text in iter_sentences():
            sentence_count += 1
            if sentence_count > PLAINTEXT_MAX_SENTENCES:
                raise ValueError(
                    "Plaintext contains more than "
                    f"{PLAINTEXT_MAX_SENTENCES} sentences"
                )
            entity_checks += len(entities)
            if entity_checks > PLAINTEXT_MAX_ENTITY_SENTENCE_CHECKS:
                raise ValueError(
                    "Plaintext entity co-occurrence scan exceeds "
                    f"{PLAINTEXT_MAX_ENTITY_SENTENCE_CHECKS} comparisons"
                )
            matched_entities = tuple(
                entity for entity in entities if entity.label in sentence_text
            )
            if len(matched_entities) >= 2:
                if len(sentence_text) > GRAPH_MAX_CONTEXT_CHARACTERS:
                    raise ValueError(
                        "Plaintext relationship context exceeds "
                        f"{GRAPH_MAX_CONTEXT_CHARACTERS} characters"
                    )
                pair_count = (
                    len(matched_entities) * (len(matched_entities) - 1) // 2
                )
                candidate_pair_work += pair_count
                if candidate_pair_work > PLAINTEXT_MAX_COOCCURRENCE_PAIRS:
                    raise ValueError(
                        "Plaintext co-occurrence expansion exceeds "
                        f"{PLAINTEXT_MAX_COOCCURRENCE_PAIRS} candidate pairs"
                    )
                sentence_matches.append(
                    (sent_idx, start_char, sentence_text, matched_entities)
                )

        existing_relationship_ids = {
            relationship.id for relationship in kg.relationships
        }
        for sent_idx, start_char, sentence_text, matched_entities in sentence_matches:
            for left_index, left_entity in enumerate(matched_entities):
                for right_entity in matched_entities[left_index + 1:]:
                    relationship_id = generate_deterministic_id(
                        [
                            file_id,
                            "relation",
                            left_entity.id,
                            "related_to",
                            right_entity.id,
                        ]
                    )
                    if relationship_id in existing_relationship_ids:
                        continue
                    kg.add_relationship(
                        Relationship(
                            id=relationship_id,
                            source_id=left_entity.id,
                            target_id=right_entity.id,
                            label=RelationType.RELATED_TO,
                            properties={"confidence": 0.3},
                            metadata={
                                "context_sentence_idx": sent_idx,
                                "start_char": start_char,
                            },
                            source_doc_id=file_id,
                            context=sentence_text,
                        )
                    )
                    existing_relationship_ids.add(relationship_id)

class JsonExtractor(KnowledgeExtractor):
    """
    Extracts knowledge from JSON files.
    """
    
    def extract(self, file_path: Union[str, Path]) -> KnowledgeGraph:
        p = Path(file_path)
        kg = super().extract(file_path)
        file_id = kg.metadata['source_file_id']

        try:
            with open(p, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, RecursionError) as e:
            logger.error(f"Invalid JSON in file {p}: {e}")
            raise ValueError(f"Invalid JSON in file {p}") from e
        except (OSError, UnicodeError) as e:
            logger.error(f"Error reading JSON file {p}: {e}")
            raise RuntimeError(f"Error reading JSON file {p}") from e

        _validate_json_payload(
            data,
            field_name=f"JSON document {p}",
            maximum_bytes=SOURCE_MAX_FILE_BYTES,
        )

        if isinstance(data, list):
            self._process_json_list(data, kg, file_id, parent_id_path=[])
        elif isinstance(data, dict):
            self._process_json_dict(data, kg, file_id, parent_id_path=[])
        else:
            logger.warning(f"Root of JSON file {p} is not a list or dict. Cannot extract structured data.")
            raise ValueError(f"Root of JSON file {p} is not a list or dict.")

        logger.info(f"Extracted {len(kg.entities)} entities and {len(kg.relationships)} relationships from JSON {p}.")
        return kg
    
    def _process_json_list(self, data: List, kg: KnowledgeGraph, file_id: str, parent_id_path: List[str]) -> None:
        """Processes a list of JSON objects."""
        for index, item in enumerate(data):
            item_id_path = parent_id_path + [str(index)]
            if isinstance(item, dict):
                self._process_json_dict(item, kg, file_id, parent_id_path=item_id_path)
            elif isinstance(item, list):
                self._process_json_list(item, kg, file_id, parent_id_path=item_id_path)
            # else: simple values in a list are usually attributes of a parent or ignored if no clear parent
    
    def _process_json_dict(self, data: Dict, kg: KnowledgeGraph, file_id: str, 
                           parent_id_path: List[str], parent_entity_id: Optional[str] = None) -> None:
        """Processes a JSON dictionary, creating entities and relationships."""
        # Try to identify a name or ID for the current dictionary to form an entity
        current_entity_name = data.get('name', data.get('id', data.get('title')))
        current_entity_id_str = None
        entity_attributes = {}

        if current_entity_name and isinstance(current_entity_name, str):
            current_entity_id_str = generate_deterministic_id([file_id, "entity"] + parent_id_path + [current_entity_name])
            entity = Entity(
                id=current_entity_id_str,
                label=current_entity_name,
                type=EntityType.CONCEPT, # Default, could be refined
                properties={k: v for k, v in data.items() if isinstance(v, (str, int, float, bool))},
                metadata={},
                source_doc_id=file_id
            )
            kg.add_entity(entity)
            if parent_entity_id:
                rel_id = generate_deterministic_id([file_id, "relation", parent_entity_id, "has_property_or_child", current_entity_id_str])
                relationship = Relationship(
                    id=rel_id,
                    source_id=parent_entity_id,
                    target_id=current_entity_id_str,
                    label=RelationType.HAS_PROPERTY, # Or PART_OF depending on semantics
                    properties={"confidence": 0.8},
                    metadata={},
                    source_doc_id=file_id
                )
                kg.add_relationship(relationship)
        else: # No clear name/id, treat keys as attributes of parent or create generic entity
            # If it's a flat dict without a clear identity, its keys might be attributes of parent_entity_id
            # Or, create a generic entity for this level if parent_id_path is not too deep
            if len(parent_id_path) < 5: # Arbitrary depth limit for anonymous entities
                current_entity_id_str = generate_deterministic_id([file_id, "anon_entity"] + parent_id_path)
                entity = Entity(
                    id=current_entity_id_str,
                    label="_".join(["anon"] + parent_id_path),
                    type=EntityType.STRUCTURED_DATA, # Generic type for anonymous dicts
                    properties={k: v for k, v in data.items() if isinstance(v, (str, int, float, bool))},
                    metadata={},
                    source_doc_id=file_id
                )
                kg.add_entity(entity)
                if parent_entity_id:
                    rel_id = generate_deterministic_id([file_id, "relation", parent_entity_id, "has_child_structure", current_entity_id_str])
                    relationship = Relationship(
                        id=rel_id,
                        source_id=parent_entity_id,
                        target_id=current_entity_id_str,
                        label=RelationType.PART_OF,
                        properties={"confidence": 0.7},
                        metadata={},
                        source_doc_id=file_id
                    )
                    kg.add_relationship(relationship)
            else: # Too deep or no parent, just process children
                current_entity_id_str = parent_entity_id

        # Recursively process nested structures
        for key, value in data.items():
            child_id_path = parent_id_path + [str(key)]
            if isinstance(value, dict):
                self._process_json_dict(value, kg, file_id, parent_id_path=child_id_path, parent_entity_id=current_entity_id_str)
            elif isinstance(value, list):
                self._process_json_list(value, kg, file_id, parent_id_path=child_id_path) # List items might relate to current_entity_id_str
                                                                                        # This part needs more sophisticated handling for list items relating to parent
            # Simple values were added as attributes if current_entity_id_str was created from this dict

    # _process_json_list_with_parent is removed as its logic is integrated into _process_json_list and _process_json_dict

class JsonlExtractor(KnowledgeExtractor):
    """Extracts knowledge from newline-delimited JSON files."""

    def extract(self, file_path: Union[str, Path]) -> KnowledgeGraph:
        p = Path(file_path)
        kg = super().extract(file_path)
        file_id = kg.metadata['source_file_id']

        record_count = 0
        total_json_items = 0
        try:
            with open(p, 'r', encoding='utf-8') as f:
                for line_no, raw_line in enumerate(f, start=1):
                    line = raw_line.strip()
                    if not line:
                        continue
                    if record_count >= STRUCTURED_MAX_ROWS:
                        raise ValueError(
                            f"JSONL contains more than {STRUCTURED_MAX_ROWS} records"
                        )
                    try:
                        data = json.loads(line)
                    except (json.JSONDecodeError, RecursionError) as e:
                        raise ValueError(f"Invalid JSONL in {p} at line {line_no}") from e
                    total_json_items += _validate_json_payload(
                        data,
                        field_name=f"JSONL record {line_no}",
                    )
                    if total_json_items > JSON_MAX_ITEMS:
                        raise ValueError(
                            f"JSONL exceeds {JSON_MAX_ITEMS} aggregate JSON items"
                        )

                    record_id = generate_deterministic_id([file_id, "jsonl", str(line_no)])
                    record_entity = Entity(
                        id=record_id,
                        label=f"{p.name}:line:{line_no}",
                        type=EntityType.STRUCTURED_DATA,
                        properties={"line": line_no},
                        metadata={"json": data if isinstance(data, (dict, list)) else {"value": data}},
                        source_doc_id=file_id,
                    )
                    kg.add_entity(record_entity)
                    record_count += 1

                    if isinstance(data, dict):
                        JsonExtractor()._process_json_dict(
                            data,
                            kg,
                            file_id,
                            parent_id_path=[str(line_no)],
                            parent_entity_id=record_id,
                        )
        except ValueError:
            raise
        except (OSError, UnicodeError) as e:
            logger.error(f"Error reading JSONL file {p}: {e}")
            raise RuntimeError(f"Error reading JSONL file {p}") from e

        if record_count == 0:
            raise ValueError(f"No JSONL records found in {p}")

        logger.info(f"Extracted {len(kg.entities)} entities and {len(kg.relationships)} relationships from JSONL {p}.")
        return kg


class CsvExtractor(KnowledgeExtractor):
    """Extracts row and column structure from CSV files."""

    def extract(self, file_path: Union[str, Path]) -> KnowledgeGraph:
        p = Path(file_path)
        kg = super().extract(file_path)
        file_id = kg.metadata['source_file_id']

        row_count = 0
        try:
            with open(p, 'r', encoding='utf-8', newline='') as f:
                sample = f.read(4096)
                f.seek(0)
                dialect = csv.Sniffer().sniff(sample) if sample else csv.excel
                has_header = csv.Sniffer().has_header(sample) if sample else False
                if has_header:
                    reader = csv.DictReader(f, dialect=dialect)
                    headers = reader.fieldnames or []
                    for row_index, row in enumerate(reader, start=1):
                        if row_index > STRUCTURED_MAX_ROWS:
                            raise ValueError(
                                f"CSV contains more than {STRUCTURED_MAX_ROWS} rows"
                            )
                        row_id = generate_deterministic_id([file_id, "csv-row", str(row_index)])
                        kg.add_entity(Entity(
                            id=row_id,
                            label=f"{p.name}:row:{row_index}",
                            type=EntityType.STRUCTURED_DATA,
                            properties={key: value for key, value in row.items() if key is not None},
                            metadata={"row_index": row_index, "headers": headers},
                            source_doc_id=file_id,
                        ))
                        row_count += 1
                else:
                    reader = csv.reader(f, dialect=dialect)
                    for row_index, row in enumerate(reader, start=1):
                        if row_index > STRUCTURED_MAX_ROWS:
                            raise ValueError(
                                f"CSV contains more than {STRUCTURED_MAX_ROWS} rows"
                            )
                        row_id = generate_deterministic_id([file_id, "csv-row", str(row_index)])
                        kg.add_entity(Entity(
                            id=row_id,
                            label=f"{p.name}:row:{row_index}",
                            type=EntityType.STRUCTURED_DATA,
                            properties={f"column_{idx}": value for idx, value in enumerate(row)},
                            metadata={"row_index": row_index},
                            source_doc_id=file_id,
                        ))
                        row_count += 1
        except ValueError:
            raise
        except (csv.Error, OSError, UnicodeError) as e:
            logger.error(f"Error reading CSV file {p}: {e}")
            raise RuntimeError(f"Error reading CSV file {p}") from e

        if row_count == 0:
            raise ValueError(f"No CSV rows found in {p}")

        logger.info(f"Extracted {len(kg.entities)} entities and {len(kg.relationships)} relationships from CSV {p}.")
        return kg


class TextDerivedExtractor(KnowledgeExtractor):
    """Base extractor for formats that first decode into text."""

    def _extract_text_graph(self, text: str, kg: KnowledgeGraph, file_id: str) -> KnowledgeGraph:
        if not text.strip():
            source = kg.metadata.get('source_file_path', '<unknown>')
            raise ValueError(f"No extractable text found in {source}")
        PlaintextExtractor()._extract_entities_simple(text, kg, file_id)
        PlaintextExtractor()._extract_relationships_simple(text, kg, file_id)
        return kg


class MarkdownExtractor(TextDerivedExtractor):
    """Extracts text semantics from Markdown files."""

    def extract(self, file_path: Union[str, Path]) -> KnowledgeGraph:
        p = Path(file_path)
        kg = super().extract(file_path)
        file_id = kg.metadata['source_file_id']

        try:
            text = _extract_document_text_isolated("markdown", p)
        except Exception as e:
            logger.error(f"Error reading Markdown file {p}: {e}")
            raise RuntimeError(f"Error reading Markdown file {p}") from e

        return self._extract_text_graph(text, kg, file_id)


class HtmlExtractor(TextDerivedExtractor):
    """Extracts text semantics from HTML files."""

    def extract(self, file_path: Union[str, Path]) -> KnowledgeGraph:
        p = Path(file_path)
        kg = super().extract(file_path)
        file_id = kg.metadata['source_file_id']

        try:
            text = _extract_document_text_isolated("html", p)
        except Exception as e:
            logger.error(f"Error reading HTML file {p}: {e}")
            raise RuntimeError(f"Error reading HTML file {p}") from e

        return self._extract_text_graph(text, kg, file_id)


class XmlExtractor(TextDerivedExtractor):
    """Extracts text semantics from XML files."""

    def extract(self, file_path: Union[str, Path]) -> KnowledgeGraph:
        p = Path(file_path)
        kg = super().extract(file_path)
        file_id = kg.metadata['source_file_id']

        try:
            text = _extract_document_text_isolated("xml", p)
        except Exception as e:
            logger.error(f"Error reading XML file {p}: {e}")
            raise RuntimeError(f"Error reading XML file {p}") from e

        return self._extract_text_graph(text, kg, file_id)


class PdfExtractor(TextDerivedExtractor):
    """Extracts text semantics from PDF files."""

    def extract(self, file_path: Union[str, Path]) -> KnowledgeGraph:
        if PdfReader is None:
            raise ImportError(
                "PDF extraction requires the optional 'pypdf' dependency. "
                "Install project dependencies before processing PDF inputs."
            )

        p = Path(file_path)
        kg = super().extract(file_path)
        file_id = kg.metadata['source_file_id']

        try:
            text = _extract_document_text_isolated("pdf", p)
        except Exception as e:
            logger.error(f"Error reading PDF file {p}: {e}")
            raise RuntimeError(f"Error reading PDF file {p}: {e}") from e

        if not text:
            raise ValueError(f"No extractable text found in PDF file {p}")
        return self._extract_text_graph(text, kg, file_id)


class DocxExtractor(TextDerivedExtractor):
    """Extracts text semantics from DOCX files."""

    def extract(self, file_path: Union[str, Path]) -> KnowledgeGraph:
        p = Path(file_path)
        kg = super().extract(file_path)
        file_id = kg.metadata['source_file_id']

        try:
            seen_members: Set[str] = set()
            total_uncompressed = 0
            with zipfile.ZipFile(p, "r") as archive:
                members = archive.infolist()
                if len(members) > DOCUMENT_MAX_ARCHIVE_MEMBERS:
                    raise ValueError(
                        f"DOCX contains {len(members)} archive members; limit is "
                        f"{DOCUMENT_MAX_ARCHIVE_MEMBERS}"
                    )
                for member in members:
                    normalized_name = member.filename.replace("\\", "/")
                    member_path = PurePosixPath(normalized_name)
                    if (
                        not normalized_name
                        or member_path.is_absolute()
                        or ".." in member_path.parts
                        or any(part in {"", "."} for part in member_path.parts)
                    ):
                        raise ValueError(
                            f"Unsafe DOCX archive member: {member.filename!r}"
                        )
                    if normalized_name in seen_members:
                        raise ValueError(
                            f"Duplicate DOCX archive member: {member.filename!r}"
                        )
                    seen_members.add(normalized_name)
                    if member.flag_bits & 0x1:
                        raise ValueError(
                            f"Encrypted DOCX archive member is not supported: "
                            f"{member.filename!r}"
                        )
                    unix_mode = (member.external_attr >> 16) & 0xFFFF
                    file_type = stat.S_IFMT(unix_mode)
                    if file_type not in {0, stat.S_IFREG, stat.S_IFDIR}:
                        raise ValueError(
                            f"DOCX archive member is a link or special file: "
                            f"{member.filename!r}"
                        )
                    if member.file_size > DOCUMENT_MAX_ARCHIVE_MEMBER_BYTES:
                        raise ValueError(
                            f"DOCX member exceeds "
                            f"{DOCUMENT_MAX_ARCHIVE_MEMBER_BYTES} bytes: "
                            f"{member.filename!r}"
                        )
                    total_uncompressed += member.file_size
                    if total_uncompressed > DOCUMENT_MAX_ARCHIVE_TOTAL_BYTES:
                        raise ValueError(
                            "DOCX archive expands beyond "
                            f"{DOCUMENT_MAX_ARCHIVE_TOTAL_BYTES} bytes"
                        )
                    if member.file_size:
                        if member.compress_size == 0:
                            raise ValueError(
                                f"DOCX member has an invalid compression size: "
                                f"{member.filename!r}"
                            )
                        compression_ratio = member.file_size / member.compress_size
                        if compression_ratio > DOCUMENT_MAX_ARCHIVE_COMPRESSION_RATIO:
                            raise ValueError(
                                f"DOCX member compression ratio "
                                f"{compression_ratio:.1f}:1 exceeds "
                                f"{DOCUMENT_MAX_ARCHIVE_COMPRESSION_RATIO:.0f}:1: "
                                f"{member.filename!r}"
                            )
            text = _extract_document_text_isolated("docx", p)
        except Exception as e:
            logger.error(f"Error reading DOCX file {p}: {e}")
            raise RuntimeError(f"Error reading DOCX file {p}: {e}") from e

        if not text:
            raise ValueError(f"No extractable text found in DOCX file {p}")
        return self._extract_text_graph(text, kg, file_id)


class ConversationExtractor(KnowledgeExtractor):
    """
    Extracts knowledge from conversation data (ChatGPT, Claude, etc.).
    """
    
    def __init__(self):
        self.max_examples = None
    
    def extract(self, file_path: Union[str, Path]) -> KnowledgeGraph:
        p = Path(file_path)
        kg = super().extract(file_path)
        file_id = kg.metadata['source_file_id']
        fmt = FormatDetector.detect_format(p) # Re-detect to be sure, or pass from manager

        # Basic structure for conversation: User and Assistant entities, turns as relationships or structured entities
        # This is a simplified model. A richer model might have entities for topics, questions, answers.
        user_entity_id = generate_deterministic_id([file_id, "entity", "User"]) 
        assistant_entity_id = generate_deterministic_id([file_id, "entity", "Assistant"])

        if not kg.get_entity_by_name("User", EntityType.PERSON):
            kg.add_entity(Entity(id=user_entity_id, label="User", type=EntityType.PERSON, source_doc_id=file_id))
        if not kg.get_entity_by_name("Assistant", EntityType.ORGANIZATION): # Or a custom BOT type
            kg.add_entity(Entity(id=assistant_entity_id, label="Assistant", type=EntityType.ORGANIZATION, source_doc_id=file_id))

        try:
            if fmt != FormatType.CHATGPT_EXPORT:
                raise ValueError(
                    f"Conversation export format {fmt.name} is not supported"
                )
            turn_count = self._extract_chatgpt(
                p,
                kg,
                file_id,
                user_entity_id,
                assistant_entity_id,
            )
            if turn_count < 1:
                raise ValueError(
                    "ChatGPT export contains no valid user or assistant turns"
                )
        except Exception as e:
            logger.error(f"Error processing conversation file {p} with format {fmt}: {e}")
            raise RuntimeError(
                f"Error processing conversation file {p} with format {fmt}: {e}"
            ) from e

        logger.info(f"Extracted {len(kg.entities)} entities and {len(kg.relationships)} relationships from Conversation {p}.")
        return kg
    
    def _extract_chatgpt(
        self,
        file_path: Path,
        kg: KnowledgeGraph,
        file_id: str,
        user_id: str,
        assistant_id: str,
    ) -> int:
        """Extracts from ChatGPT JSON export format."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                conversations_data = json.load(f)
        except (OSError, UnicodeError, json.JSONDecodeError) as e:
            raise ValueError(
                f"Could not read or parse ChatGPT export {file_path}: {e}"
            ) from e

        _validate_json_payload(
            conversations_data,
            field_name="ChatGPT export",
            maximum_bytes=SOURCE_MAX_FILE_BYTES,
        )
        if not isinstance(conversations_data, list) or not conversations_data:
            raise ValueError("ChatGPT export root must be a non-empty list")
        if len(conversations_data) > STRUCTURED_MAX_ROWS:
            raise ValueError(
                f"ChatGPT export exceeds {STRUCTURED_MAX_ROWS} conversations"
            )

        turn_counter = 0
        for convo_idx, convo in enumerate(conversations_data):
            if not isinstance(convo, dict) or "mapping" not in convo:
                raise ValueError(
                    f"ChatGPT conversation {convo_idx} has no mapping object"
                )
            
            convo_id_str = str(
                convo.get("id", convo.get("conversation_id", f"convo_{convo_idx}"))
            )
            _validate_bounded_string(
                convo_id_str,
                field_name="ChatGPT conversation id",
                maximum_characters=GRAPH_MAX_IDENTIFIER_CHARACTERS,
            )
            convo_entity_id = generate_deterministic_id([file_id, "conversation", convo_id_str])
            convo_title = convo.get("title", f"Conversation {convo_idx + 1}")
            if not isinstance(convo_title, str):
                raise ValueError(
                    f"ChatGPT conversation {convo_idx} title must be text"
                )
            
            kg.add_entity(Entity(
                id=convo_entity_id,
                label=convo_title,
                type=EntityType.PROCEDURE, # Representing a sequence of interactions
                properties={'raw_conversation_id': convo_id_str, 'create_time': convo.get('create_time')},
                source_doc_id=file_id
            ))

            last_turn_entity_id = None

            # Iterate through messages in the conversation tree
            # This requires traversing the 'mapping' structure of ChatGPT exports
            # Simplified: assumes messages are somewhat ordered or can be processed sequentially by node_id
            # A proper traversal would follow parent/child links in the mapping.
            # For now, iterate sorted by key (node_id) as a heuristic for order.
            mapping = convo["mapping"]
            if not isinstance(mapping, dict) or not mapping:
                raise ValueError(
                    f"ChatGPT conversation {convo_idx} mapping must be a non-empty object"
                )
            sorted_mapping_keys = sorted(mapping, key=str)

            for node_id in sorted_mapping_keys:
                message_node = mapping.get(node_id)
                if not message_node or "message" not in message_node or not message_node["message"]:
                    continue
                
                message_data = message_node["message"]
                author_role = message_data.get("author", {}).get("role")
                content_parts = message_data.get("content", {}).get("parts", [])
                if not isinstance(content_parts, list):
                    raise ValueError(
                        f"ChatGPT message {node_id!r} content parts must be a list"
                    )
                text_parts: List[str] = []
                text_character_count = 0
                for part in content_parts:
                    if not isinstance(part, str):
                        continue
                    text_character_count += len(part)
                    if text_character_count > GRAPH_MAX_STRING_CHARACTERS:
                        raise ValueError(
                            "ChatGPT message text exceeds the graph string bound"
                        )
                    text_parts.append(part)
                text_content = " ".join(text_parts).strip()
                
                if not text_content:
                    continue

                speaker_entity_id = None

                if author_role == "user":
                    speaker_entity_id = user_id
                elif author_role == "assistant":
                    speaker_entity_id = assistant_id
                elif author_role == "system": # System messages might be metadata or instructions
                    continue
                else: # Unknown role, skip or create generic speaker
                    logger.debug(f"Unknown author role '{author_role}' in {file_path}")
                    continue

                turn_counter += 1
                turn_entity_id = generate_deterministic_id(
                    [file_id, "turn", convo_id_str, str(turn_counter)]
                )

                # Create an entity for the turn/utterance itself
                kg.add_entity(Entity(
                    id=turn_entity_id,
                    label=f"Turn {turn_counter} ({author_role})",
                    type=EntityType.CONCEPT, # Or a specific UTTERANCE type
                    properties={'text': text_content, 'role': author_role, 'timestamp': message_data.get('create_time')},
                    source_doc_id=file_id
                ))

                # Link turn to conversation
                kg.add_relationship(Relationship(
                    id=generate_deterministic_id([file_id, "rel", convo_entity_id, "has_turn", turn_entity_id]),
                    source_id=convo_entity_id,
                    target_id=turn_entity_id,
                    label=RelationType.PART_OF,
                    properties={'confidence': 0.9},
                    source_doc_id=file_id
                ))

                # Link speaker to turn (who said it)
                kg.add_relationship(Relationship(
                    id=generate_deterministic_id([file_id, "rel", speaker_entity_id, "spoke", turn_entity_id]),
                    source_id=speaker_entity_id,
                    target_id=turn_entity_id,
                    label=RelationType.CREATED_BY, # Or a custom SPEAKS type
                    properties={'confidence': 0.95},
                    source_doc_id=file_id
                ))

                # Link to previous turn if applicable (sequential relationship)
                if last_turn_entity_id:  # Link this turn to the previous turn
                    kg.add_relationship(Relationship(
                        id=generate_deterministic_id([file_id, "rel", last_turn_entity_id, "followed_by", turn_entity_id]),
                        source_id=last_turn_entity_id,
                        target_id=turn_entity_id,
                        label=RelationType.BEFORE, 
                        properties={'sequence': turn_counter-1},
                        source_doc_id=file_id
                    ))
                    
                last_turn_entity_id = turn_entity_id  # Update for next iteration
                
                # Extract entities/relations from the turn content itself (can reuse PlaintextExtractor logic)
                # For simplicity, this is omitted here but would be crucial for deep knowledge.
                # self._extract_entities_from_text(text_content, kg, file_id, turn_entity_id) 

        return turn_counter
    
    def _extract_claude(self, file_path: Path, kg: KnowledgeGraph, file_id: str, user_id: str, assistant_id: str) -> None:
        logger.warning(f"Claude JSON export parsing is not yet fully implemented for {file_path}. Placeholder.")
        # Placeholder: Assumes a list of turns, each with 'speaker' and 'text'
        # Actual Claude format needs to be inspected and parsed accordingly.
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, list):
                logger.error(f"Claude export {file_path} is not a list as expected by placeholder.")
                return

            convo_entity_id = generate_deterministic_id([file_id, "conversation", Path(file_path).stem])
            kg.add_entity(Entity(
                id=convo_entity_id, 
                label=f"Claude Conversation from {Path(file_path).name}", 
                type=EntityType.PROCEDURE, 
                source_doc_id=file_id
            ))

            last_turn_entity_id = None
            for idx, turn_data in enumerate(data):
                speaker = turn_data.get('speaker')
                text = turn_data.get('text')
                if not speaker or not text:
                    continue

                turn_entity_id = generate_deterministic_id([file_id, "turn", convo_entity_id, str(idx)])
                speaker_entity_id = user_id if speaker.lower() == 'human' else assistant_id
                
                kg.add_entity(Entity(
                    id=turn_entity_id, 
                    label=f"Turn {idx+1} ({speaker})", 
                    type=EntityType.CONCEPT, 
                    properties={'text': text}, 
                    source_doc_id=file_id
                ))
                
                kg.add_relationship(Relationship(
                    id=generate_deterministic_id([file_id, "rel", convo_entity_id, "has_turn", turn_entity_id]),
                    source_id=convo_entity_id, 
                    target_id=turn_entity_id, 
                    label=RelationType.PART_OF, 
                    source_doc_id=file_id
                ))
                
                kg.add_relationship(Relationship(
                    id=generate_deterministic_id([file_id, "rel", speaker_entity_id, "spoke", turn_entity_id]),
                    source_id=speaker_entity_id, 
                    target_id=turn_entity_id, 
                    label=RelationType.CREATED_BY, 
                    source_doc_id=file_id
                ))
                
                # Link to previous turn for sequence
                if last_turn_entity_id:
                    kg.add_relationship(Relationship(
                        id=generate_deterministic_id([file_id, "rel", last_turn_entity_id, "followed_by", turn_entity_id]),
                        source_id=last_turn_entity_id,
                        target_id=turn_entity_id,
                        label=RelationType.BEFORE,
                        properties={'sequence': idx},
                        source_doc_id=file_id
                    ))
                
                last_turn_entity_id = turn_entity_id

        except Exception as e:
            logger.error(f"Error in placeholder Claude parsing for {file_path}: {e}")
    
    def _extract_deepseek(self, file_path: Path, kg: KnowledgeGraph, file_id: str, user_id: str, assistant_id: str) -> None:
        """Extracts from DeepSeek JSON export format."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Create a conversation entity
            convo_entity_id = generate_deterministic_id([file_id, "conversation", Path(file_path).stem])
            kg.add_entity(Entity(
                id=convo_entity_id, 
                label=f"DeepSeek Conversation from {Path(file_path).name}", 
                type=EntityType.PROCEDURE, 
                source_doc_id=file_id
            ))
            
            # Process the conversation structure
            # Assuming a list structure like [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
            # Adjust based on actual DeepSeek format
            if isinstance(data, list):
                last_turn_entity_id = None
                for idx, msg in enumerate(data):
                    if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
                        continue
                    
                    role = msg["role"]
                    content = msg["content"]
                    
                    turn_entity_id = generate_deterministic_id([file_id, "turn", convo_entity_id, str(idx)])
                    
                    # Determine speaker entity ID based on role
                    speaker_entity_id = None
                    if role.lower() == "user":
                        speaker_entity_id = user_id
                    elif role.lower() == "assistant":
                        speaker_entity_id = assistant_id
                    else:
                        logger.debug(f"Unknown role '{role}' in DeepSeek conversation {file_path}")
                        continue
                    
                    # Create turn entity
                    kg.add_entity(Entity(
                        id=turn_entity_id,
                        label=f"Turn {idx+1} ({role})",
                        type=EntityType.CONCEPT,
                        properties={'text': content, 'role': role},
                        source_doc_id=file_id
                    ))
                    
                    # Link turn to conversation
                    kg.add_relationship(Relationship(
                        id=generate_deterministic_id([file_id, "rel", convo_entity_id, "has_turn", turn_entity_id]),
                        source_id=convo_entity_id,
                        target_id=turn_entity_id,
                        label=RelationType.PART_OF,
                        source_doc_id=file_id
                    ))
                    
                    # Link speaker to turn
                    kg.add_relationship(Relationship(
                        id=generate_deterministic_id([file_id, "rel", speaker_entity_id, "spoke", turn_entity_id]),
                        source_id=speaker_entity_id,
                        target_id=turn_entity_id,
                        label=RelationType.CREATED_BY,
                        source_doc_id=file_id
                    ))
                    
                    # Link to previous turn for sequence
                    if last_turn_entity_id:
                        kg.add_relationship(Relationship(
                            id=generate_deterministic_id([file_id, "rel", last_turn_entity_id, "followed_by", turn_entity_id]),
                            source_id=last_turn_entity_id,
                            target_id=turn_entity_id,
                            label=RelationType.BEFORE,
                            properties={'sequence': idx},
                            source_doc_id=file_id
                        ))
                    
                    last_turn_entity_id = turn_entity_id
            else:
                logger.warning(f"DeepSeek export {file_path} is not in the expected format (list of messages)")
                
            logger.info(f"Processed DeepSeek conversation from {file_path}")
        except Exception as e:
            logger.error(f"Error processing DeepSeek export {file_path}: {e}")
    
    def _extract_generic_conversation_from_json(self, file_path: Path, kg: KnowledgeGraph, file_id: str, user_id: str, assistant_id: str) -> None:
        """Tries to parse a generic JSON structure that might represent a conversation."""
        logger.info(f"Attempting generic conversation extraction from JSON: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Could not read/parse generic JSON for conversation: {file_path}: {e}")
            return

        # Heuristics to find conversation turns
        # 1. A list of dictionaries, each with 'role'/'speaker' and 'content'/'text'
        if isinstance(data, list):
            convo_entity_id = generate_deterministic_id([file_id, "conversation", Path(file_path).stem])
            kg.add_entity(Entity(id=convo_entity_id, label=f"Generic Conversation from {Path(file_path).name}", type=EntityType.PROCEDURE, source_doc_id=file_id))
            
            for idx, item in enumerate(data):
                if isinstance(item, dict):
                    role = item.get('role', item.get('speaker'))
                    content = item.get('content', item.get('text', item.get('message')))
                    
                    if role and content and isinstance(content, str):
                        turn_entity_id = generate_deterministic_id([file_id, "turn", convo_entity_id, str(idx)])
                        speaker_entity_id = None
                        if str(role).lower() in ['user', 'human', 'customer']:
                            speaker_entity_id = user_id
                        elif str(role).lower() in ['assistant', 'ai', 'bot', 'gpt', 'claude']:
                            speaker_entity_id = assistant_id
                        else: # Unknown role, could create a new entity or skip
                            logger.debug(f"Generic conversation: unknown role '{role}' in {file_path}")
                            continue
                        
                        kg.add_entity(Entity(id=turn_entity_id, label=f"Turn {idx+1} ({role})", type=EntityType.CONCEPT, properties={'text': content}, source_doc_id=file_id))
                        kg.add_relationship(Relationship(id=generate_deterministic_id([file_id, "rel", convo_entity_id, "has_turn", turn_entity_id]),
                                                       source_id=convo_entity_id, target_id=turn_entity_id, label=RelationType.PART_OF, source_doc_id=file_id))
                        kg.add_relationship(Relationship(id=generate_deterministic_id([file_id, "rel", speaker_entity_id, "spoke", turn_entity_id]),
                                                       source_id=speaker_entity_id, target_id=turn_entity_id, label=RelationType.CREATED_BY, source_doc_id=file_id))
        # 2. A dictionary with a key like 'messages' or 'turns' containing a list (similar to above)
        elif isinstance(data, dict):
            possible_turn_keys = ['messages', 'turns', 'conversation', 'log', 'exchanges']
            found_turns_list = None
            for key in possible_turn_keys:
                if key in data and isinstance(data[key], list):
                    found_turns_list = data[key]
                    break
            if found_turns_list:
                # Essentially the same logic as if data was a list directly
                # This is a simplified call; ideally, pass the parent dict's context if needed
                self._extract_generic_conversation_from_json_list_part(found_turns_list, kg, file_id, user_id, assistant_id, Path(file_path).stem)
            else:
                logger.warning(f"Generic JSON conversation: Could not find a list of turns in dict for {file_path}")
        else:
            logger.warning(f"Generic JSON conversation: Root is not list or dict for {file_path}")

    def _extract_generic_conversation_from_json_list_part(self, turns_list: List[Dict], kg: KnowledgeGraph, file_id: str, user_id: str, assistant_id: str, convo_name_prefix: str):
        """Helper for _extract_generic_conversation_from_json when turns are in a list within a dict."""
        convo_entity_id = generate_deterministic_id([file_id, "conversation", convo_name_prefix])
        kg.add_entity(Entity(id=convo_entity_id, label=f"Generic Conversation ({convo_name_prefix})", type=EntityType.PROCEDURE, source_doc_id=file_id))
        
        for idx, item in enumerate(turns_list):
            if isinstance(item, dict):
                role = item.get('role', item.get('speaker'))
                content = item.get('content', item.get('text', item.get('message')))
                
                if role and content and isinstance(content, str):
                    turn_entity_id = generate_deterministic_id([file_id, "turn", convo_entity_id, str(idx)])
                    speaker_entity_id = None
                    if str(role).lower() in ['user', 'human', 'customer']:
                        speaker_entity_id = user_id
                    elif str(role).lower() in ['assistant', 'ai', 'bot', 'gpt', 'claude']:
                        speaker_entity_id = assistant_id
                    else:
                        logger.debug(f"Generic conversation list part: unknown role '{role}'")
                        continue
                    
                    kg.add_entity(Entity(id=turn_entity_id, label=f"Turn {idx+1} ({role})", type=EntityType.CONCEPT, properties={'text': content}, source_doc_id=file_id))
                    kg.add_relationship(Relationship(id=generate_deterministic_id([file_id, "rel", convo_entity_id, "has_turn", turn_entity_id]),
                                                   source_id=convo_entity_id, target_id=turn_entity_id, label=RelationType.PART_OF, source_doc_id=file_id))
                    kg.add_relationship(Relationship(id=generate_deterministic_id([file_id, "rel", speaker_entity_id, "spoke", turn_entity_id]),
                                                   source_id=speaker_entity_id, target_id=turn_entity_id, label=RelationType.CREATED_BY, source_doc_id=file_id))

class ExtractorFactory:
    """
    Factory for creating appropriate extractors based on file format.
    """
    
    @staticmethod
    def get_extractor(format_type: FormatType) -> Optional[KnowledgeExtractor]:
        """Returns an appropriate extractor for the given format type."""
        if format_type == FormatType.PLAINTEXT:
            return PlaintextExtractor()
        elif format_type == FormatType.JSON:
            # Could be generic JSON or a specific conversation JSON not caught by FormatDetector
            # For now, JsonExtractor handles generic, ConversationExtractor handles specific if format is CHATGPT_EXPORT etc.
            return JsonExtractor() 
        elif format_type == FormatType.JSONL:
            return JsonlExtractor()
        elif format_type == FormatType.CHATGPT_EXPORT:
            return ConversationExtractor()
        elif format_type in {
            FormatType.CLAUDE_EXPORT,
            FormatType.DEEPSEEK_EXPORT,
            FormatType.LLAMA_EXPORT,
        }:
            raise ValueError(
                f"Conversation export format {format_type.name} is not supported"
            )
        elif format_type == FormatType.CSV:
            return CsvExtractor()
        elif format_type == FormatType.XML:
            return XmlExtractor()
        elif format_type == FormatType.HTML:
            return HtmlExtractor()
        elif format_type == FormatType.MARKDOWN:
            return MarkdownExtractor()
        elif format_type == FormatType.PDF:
            return PdfExtractor()
        elif format_type == FormatType.DOCX:
            return DocxExtractor()
        # elif format_type == FormatType.DOCX:
        #     return DocxExtractor() # Requires python-docx
        else:
            logger.warning(f"No specific extractor available for format type {format_type}. No extraction will be performed for this type.")
            return None

# ----------------------------------------
# Knowledge Graph Management
# ----------------------------------------

class KnowledgeManager:
    """
    Manages the extraction, merging, and storage of knowledge graphs.
    """
    
    def __init__(
        self,
        cache_dir: Optional[Union[str, Path]] = None,
        force_no_cache: bool = False,
        semantic_db_path: Optional[Union[str, Path]] = None,
    ):
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.force_no_cache = force_no_cache
        self.semantic_db_path = str(semantic_db_path) if semantic_db_path else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"KnowledgeManager initialized with cache directory: {self.cache_dir}")
        else:
            logger.info("KnowledgeManager initialized without caching.")
        if self.semantic_db_path:
            logger.info(f"KnowledgeManager semantic archive path: {self.semantic_db_path}")

    @staticmethod
    def _validate_source_entry(path: Path) -> os.stat_result:
        """Validate one source entry without following symbolic links."""
        try:
            entry_stat = path.lstat()
        except FileNotFoundError:
            raise FileNotFoundError(f"Input path does not exist: {path}") from None
        if stat.S_ISLNK(entry_stat.st_mode):
            raise ValueError(f"Symbolic-link sources are not allowed: {path}")
        if not (stat.S_ISREG(entry_stat.st_mode) or stat.S_ISDIR(entry_stat.st_mode)):
            raise ValueError(f"Special-file sources are not allowed: {path}")
        if stat.S_ISREG(entry_stat.st_mode) and entry_stat.st_size > SOURCE_MAX_FILE_BYTES:
            raise ValueError(
                f"Source file exceeds {SOURCE_MAX_FILE_BYTES} bytes: {path}"
            )
        return entry_stat

    @classmethod
    def _source_descriptor(cls, path: Path) -> Dict[str, Any]:
        """Return verified byte-level provenance for one regular source."""
        entry_stat = cls._validate_source_entry(path)
        if not stat.S_ISREG(entry_stat.st_mode):
            raise ValueError(f"Expected a regular source file: {path}")
        content_digest, bytes_read = stream_source_sha256(path)
        if bytes_read != entry_stat.st_size:
            raise RuntimeError(f"Source changed while it was being hashed: {path}")
        return {
            "source_content_sha256": content_digest,
            "source_size_bytes": bytes_read,
        }

    @classmethod
    def _snapshot_regular_source(
        cls,
        source_path: Path,
        staging_root: Path,
    ) -> Tuple[Path, Dict[str, Any]]:
        """Copy and hash one source from the same anchored no-follow descriptor."""
        absolute = Path(os.path.abspath(os.fspath(source_path)))
        if absolute.name in {"", ".", ".."}:
            raise ValueError(f"Source path has no regular filename: {source_path}")
        directory_flags = (
            os.O_RDONLY
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0)
        )
        source_flags = (
            os.O_RDONLY
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0)
        )
        directory_descriptor = os.open(absolute.anchor, directory_flags)
        source_descriptor_fd: Optional[int] = None
        try:
            for component in absolute.parts[1:-1]:
                next_descriptor = os.open(
                    component,
                    directory_flags,
                    dir_fd=directory_descriptor,
                )
                os.close(directory_descriptor)
                directory_descriptor = next_descriptor
            source_descriptor_fd = os.open(
                absolute.name,
                source_flags,
                dir_fd=directory_descriptor,
            )
        except OSError as error:
            raise ValueError(
                f"Source path cannot be opened without following links: {source_path}"
            ) from error
        finally:
            os.close(directory_descriptor)

        snapshot_path = staging_root / absolute.name
        destination_descriptor: Optional[int] = None
        digest = hashlib.sha256()
        total_bytes = 0
        try:
            initial_status = os.fstat(source_descriptor_fd)
            if not stat.S_ISREG(initial_status.st_mode):
                raise ValueError(f"Source is not a regular file: {source_path}")
            if initial_status.st_size > SOURCE_MAX_FILE_BYTES:
                raise ValueError(
                    f"Source file exceeds {SOURCE_MAX_FILE_BYTES} bytes: {source_path}"
                )
            destination_descriptor = os.open(
                snapshot_path,
                os.O_CREAT
                | os.O_EXCL
                | os.O_WRONLY
                | getattr(os, "O_NOFOLLOW", 0),
                0o600,
            )
            while block := os.read(source_descriptor_fd, SOURCE_HASH_CHUNK_BYTES):
                total_bytes += len(block)
                if total_bytes > SOURCE_MAX_FILE_BYTES:
                    raise ValueError(
                        f"Source grew beyond {SOURCE_MAX_FILE_BYTES} bytes: {source_path}"
                    )
                digest.update(block)
                view = memoryview(block)
                while view:
                    written = os.write(destination_descriptor, view)
                    view = view[written:]
            os.fsync(destination_descriptor)
            final_status = os.fstat(source_descriptor_fd)
            stable_fields = (
                initial_status.st_dev,
                initial_status.st_ino,
                initial_status.st_size,
                initial_status.st_mtime_ns,
                initial_status.st_ctime_ns,
            )
            final_fields = (
                final_status.st_dev,
                final_status.st_ino,
                final_status.st_size,
                final_status.st_mtime_ns,
                final_status.st_ctime_ns,
            )
            if stable_fields != final_fields or total_bytes != initial_status.st_size:
                raise RuntimeError(
                    f"Source changed while its ingestion snapshot was created: {source_path}"
                )
        finally:
            if destination_descriptor is not None:
                os.close(destination_descriptor)
            os.close(source_descriptor_fd)

        os.chmod(snapshot_path, 0o400)

        return snapshot_path, {
            "source_content_sha256": digest.hexdigest(),
            "source_size_bytes": total_bytes,
        }

    @classmethod
    def _rebind_graph_paths(
        cls,
        graph: KnowledgeGraph,
        old_root: Union[str, Path],
        new_root: Union[str, Path],
    ) -> KnowledgeGraph:
        """Replace controlled snapshot paths before graph data becomes durable."""
        old_text = str(old_root)
        new_text = str(new_root)

        def replace(value: object) -> object:
            if isinstance(value, dict):
                return {str(key): replace(item) for key, item in value.items()}
            if isinstance(value, list):
                return [replace(item) for item in value]
            if isinstance(value, tuple):
                return tuple(replace(item) for item in value)
            if isinstance(value, str):
                return value.replace(old_text, new_text)
            return value

        rebound = replace(graph.to_dict())
        if not isinstance(rebound, dict):
            raise ValueError("Knowledge graph path rebinding did not produce an object")
        return KnowledgeGraph.from_dict(rebound)

    @classmethod
    def _collect_source_files(
        cls,
        file_paths: Sequence[Union[str, Path]],
    ) -> List[SourceFileRecord]:
        """Collect a deterministic, bounded set of regular input files."""
        records: List[SourceFileRecord] = []
        seen_paths: Set[Path] = set()
        aggregate_size = 0
        source_entry_count = 0

        def count_entry() -> None:
            nonlocal source_entry_count
            source_entry_count += 1
            if source_entry_count > SOURCE_MAX_ENTRIES:
                raise ValueError(
                    f"Input contains more than {SOURCE_MAX_ENTRIES} filesystem entries"
                )

        def validate_discovered_entry(
            path: Path,
            entry_stat: os.stat_result,
        ) -> None:
            if stat.S_ISLNK(entry_stat.st_mode):
                raise ValueError(f"Symbolic-link sources are not allowed: {path}")
            if not (
                stat.S_ISREG(entry_stat.st_mode)
                or stat.S_ISDIR(entry_stat.st_mode)
            ):
                raise ValueError(f"Special-file sources are not allowed: {path}")
            if (
                stat.S_ISREG(entry_stat.st_mode)
                and entry_stat.st_size > SOURCE_MAX_FILE_BYTES
            ):
                raise ValueError(
                    f"Source file exceeds {SOURCE_MAX_FILE_BYTES} bytes: {path}"
                )

        def walk_directory(
            root: Path,
        ) -> Iterator[Tuple[Path, os.stat_result]]:
            pending: List[Tuple[Path, os.stat_result]] = []

            def scan_directory(directory: Path) -> List[Tuple[Path, os.stat_result]]:
                discovered: List[Tuple[Path, os.stat_result]] = []
                try:
                    with os.scandir(directory) as entries:
                        for entry in entries:
                            count_entry()
                            entry_path = Path(entry.path)
                            entry_stat = entry.stat(follow_symlinks=False)
                            validate_discovered_entry(entry_path, entry_stat)
                            discovered.append((entry_path, entry_stat))
                except FileNotFoundError as error:
                    raise RuntimeError(
                        f"Source directory changed during traversal: {directory}"
                    ) from error
                discovered.sort(
                    key=lambda item: item[0].relative_to(root).as_posix()
                )
                return discovered

            pending.extend(reversed(scan_directory(root)))
            while pending:
                candidate, candidate_stat = pending.pop()
                if stat.S_ISREG(candidate_stat.st_mode):
                    yield candidate, candidate_stat
                    continue
                pending.extend(reversed(scan_directory(candidate)))

        def add_regular(path: Path, manifest_path: str, entry_stat: os.stat_result) -> None:
            nonlocal aggregate_size
            canonical_path = path.absolute()
            if canonical_path in seen_paths:
                return
            seen_paths.add(canonical_path)
            if len(records) >= SOURCE_MAX_FILES:
                raise ValueError(
                    f"Input contains more than {SOURCE_MAX_FILES} accepted files"
                )
            aggregate_size += entry_stat.st_size
            if aggregate_size > SOURCE_MAX_TOTAL_BYTES:
                raise ValueError(
                    f"Input sources exceed {SOURCE_MAX_TOTAL_BYTES} aggregate bytes"
                )
            records.append(
                SourceFileRecord(
                    path=path,
                    manifest_path=manifest_path,
                    size_bytes=entry_stat.st_size,
                )
            )

        for input_index, raw_path in enumerate(file_paths):
            path = Path(raw_path)
            entry_stat = cls._validate_source_entry(path)
            count_entry()
            if stat.S_ISREG(entry_stat.st_mode):
                add_regular(path, f"{input_index}/{path.name}", entry_stat)
                continue

            for descendant, descendant_stat in walk_directory(path):
                relative_path = descendant.relative_to(path).as_posix()
                add_regular(
                    descendant,
                    f"{input_index}/{relative_path}",
                    descendant_stat,
                )

        return sorted(records, key=lambda record: record.manifest_path)

    @classmethod
    def _build_source_manifest(
        cls,
        records: Sequence[SourceFileRecord],
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Hash a deterministic tree manifest and verify sources stayed stable."""
        manifest: List[Dict[str, Any]] = []
        for record in records:
            descriptor = cls._source_descriptor(record.path)
            if descriptor["source_size_bytes"] != record.size_bytes:
                raise RuntimeError(f"Source changed during collection: {record.path}")
            manifest.append(
                {
                    "path": record.manifest_path,
                    "size_bytes": record.size_bytes,
                    "sha256": descriptor["source_content_sha256"],
                }
            )
        canonical_manifest = json.dumps(
            manifest,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(canonical_manifest).hexdigest(), manifest

    @staticmethod
    def _namespace_graph_provenance(
        graph: KnowledgeGraph,
        namespace_digest: str,
    ) -> None:
        """Namespace extracted graph identities under container source bytes."""
        entity_id_map = {
            entity_id: generate_deterministic_id([namespace_digest, entity_id])
            for entity_id in graph.entities
        }
        namespaced_entities: Dict[str, Entity] = {}
        for old_entity_id, entity in graph.entities.items():
            entity.id = entity_id_map[old_entity_id]
            if entity.source_doc_id:
                entity.source_doc_id = generate_deterministic_id(
                    [namespace_digest, entity.source_doc_id]
                )
            entity.metadata = {
                **entity.metadata,
                "container_source_sha256": namespace_digest,
            }
            namespaced_entities[entity.id] = entity
        graph.entities = namespaced_entities

        namespaced_relationships = RelationshipCollection()
        for relationship in graph.relationships:
            relationship.id = generate_deterministic_id(
                [namespace_digest, relationship.id]
            )
            relationship.source_id = entity_id_map[relationship.source_id]
            relationship.target_id = entity_id_map[relationship.target_id]
            if relationship.source_doc_id:
                relationship.source_doc_id = generate_deterministic_id(
                    [namespace_digest, relationship.source_doc_id]
                )
            relationship.metadata = {
                **relationship.metadata,
                "container_source_sha256": namespace_digest,
            }
            namespaced_relationships.append(relationship)
        graph.relationships = namespaced_relationships
        # Re-enter the graph mutation boundary so cumulative byte accounting
        # reflects the namespaced identifiers and metadata exactly.
        graph.__post_init__()
    
    def _get_cache_path(self, file_path: Path) -> Optional[Path]:
        if not self.cache_dir:
            return None
        try:
            file_id = FormatDetector.get_file_id(file_path)
            cache_filename = f"v{CACHE_SCHEMA_VERSION}_{file_id}.json"
            return self.cache_dir / cache_filename
        except FileNotFoundError:
            logger.warning(f"File not found for cache path generation: {file_path}")
            return None
        except OSError as e:
            logger.error(f"Error generating cache path for {file_path}: {e}")
            raise RuntimeError(f"Unable to hash input for cache key: {file_path}") from e

    def _get_cache_path_for_digest(self, source_digest: str) -> Optional[Path]:
        """Return the cache path without reopening a source pathname."""
        if not self.cache_dir:
            return None
        if not re.fullmatch(r"[0-9a-f]{64}", source_digest):
            raise ValueError("Source digest must be a lowercase SHA-256 value")
        return self.cache_dir / f"v{CACHE_SCHEMA_VERSION}_{source_digest}.json"

    def _load_from_cache(self, cache_path: Path) -> Optional[KnowledgeGraph]:
        """Decode a cache artifact for diagnostics; ingress never trusts it."""
        if self.force_no_cache:
            return None
        try:
            if cache_path.exists():
                cache_stat = cache_path.lstat()
                if stat.S_ISLNK(cache_stat.st_mode) or not stat.S_ISREG(cache_stat.st_mode):
                    raise ValueError("cache path is not a regular file")
                if cache_stat.st_size > CACHE_MAX_JSON_BYTES:
                    raise ValueError(
                        f"cache exceeds {CACHE_MAX_JSON_BYTES} bytes"
                    )
                logger.info(f"Loading knowledge graph from cache: {cache_path}")
                with cache_path.open("r", encoding="utf-8") as cache_file:
                    payload = json.load(cache_file)
                if not isinstance(payload, dict) or payload.get("schema_version") != CACHE_SCHEMA_VERSION:
                    raise ValueError("unsupported cache schema")
                graph_payload = payload.get("knowledge_graph")
                if not isinstance(graph_payload, dict):
                    raise ValueError("cache does not contain a knowledge graph")
                return KnowledgeGraph.from_dict(graph_payload)
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError, KeyError) as e:
            logger.warning(f"Ignoring invalid cache {cache_path}: {e}. Re-processing.")
        return None

    def _save_to_cache(self, kg: KnowledgeGraph, cache_path: Path) -> None:
        if self.force_no_cache:
            return
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path: Optional[Path] = None
        try:
            descriptor, raw_temp_path = tempfile.mkstemp(
                prefix=f".{cache_path.name}.",
                suffix=".tmp",
                dir=cache_path.parent,
            )
            temp_path = Path(raw_temp_path)
            with os.fdopen(descriptor, "w", encoding="utf-8") as cache_file:
                json.dump(
                    {
                        "schema_version": CACHE_SCHEMA_VERSION,
                        "knowledge_graph": kg.to_dict(),
                    },
                    cache_file,
                    ensure_ascii=False,
                    sort_keys=True,
                )
                cache_file.flush()
                os.fsync(cache_file.fileno())
            if temp_path.stat().st_size > CACHE_MAX_JSON_BYTES:
                logger.warning(
                    "Skipping oversized knowledge cache %s (%s bytes)",
                    cache_path,
                    temp_path.stat().st_size,
                )
                temp_path.unlink(missing_ok=True)
                temp_path = None
                return
            os.replace(temp_path, cache_path)
            temp_path = None
            logger.info(f"Saved knowledge graph to cache: {cache_path}")
        except (OSError, TypeError, ValueError) as e:
            raise RuntimeError(f"Unable to save knowledge cache {cache_path}") from e
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    def _process_file_wrapper(self, file_path: Union[str, Path]) -> KnowledgeGraph:
        """Ingest one descriptor-anchored immutable source snapshot."""
        provenance_path = Path(os.path.abspath(os.fspath(file_path)))
        logger.info("Processing file: %s", provenance_path)
        with tempfile.TemporaryDirectory(prefix="archive-ingest-") as staging:
            snapshot_path, source_descriptor = self._snapshot_regular_source(
                provenance_path,
                Path(staging),
            )
            return self._process_file_snapshot(
                snapshot_path,
                provenance_path,
                source_descriptor,
            )

    def _process_file_snapshot(
        self,
        snapshot_path: Path,
        provenance_path: Path,
        source_descriptor: Mapping[str, Any],
    ) -> KnowledgeGraph:
        """Parse a private snapshot while retaining only stable provenance."""
        source_digest = source_descriptor.get("source_content_sha256")
        source_size = source_descriptor.get("source_size_bytes")
        if not isinstance(source_digest, str) or not isinstance(source_size, int):
            raise ValueError("Snapshot source descriptor is malformed")
        cache_path = self._get_cache_path_for_digest(source_digest)
        # Cache files are never an authority boundary.  They have no independent
        # signing key, so a same-user attacker can rewrite both payload and any
        # embedded checksum.  Always parse the controlled source snapshot and
        # overwrite the JSON cache only as a diagnostic/reproducibility artifact.

        initial_snapshot_status = snapshot_path.stat()
        format_type = FormatDetector.detect_format(snapshot_path)
        if (
            format_type not in {FormatType.PDF, FormatType.DOCX}
            and source_size > PARENT_PARSER_MAX_SOURCE_BYTES
        ):
            raise ValueError(
                "Parent-process parser source exceeds "
                f"{PARENT_PARSER_MAX_SOURCE_BYTES} bytes: {provenance_path}"
            )
        extractor = ExtractorFactory.get_extractor(format_type)
        kg = KnowledgeGraph(
            metadata={
                "source_file_path": str(provenance_path),
                "source_file_id": source_digest,
                "source_content_sha256": source_digest,
                "source_size_bytes": source_size,
            }
        )
        if extractor:
            try:
                extracted_kg = extractor.extract(snapshot_path)
                extracted_kg = self._rebind_graph_paths(
                    extracted_kg,
                    snapshot_path,
                    provenance_path,
                )
                kg.merge(extracted_kg)
            except Exception as e:
                logger.error(
                    "Failed to extract knowledge from %s using %s: %s",
                    provenance_path,
                    type(extractor).__name__,
                    e,
                    exc_info=True,
                )
                raise RuntimeError(
                    f"Knowledge extraction failed for {provenance_path} "
                    f"using {type(extractor).__name__}"
                ) from e
        else:
            raise ValueError(
                f"No suitable extractor found for {provenance_path} "
                f"(format: {format_type})."
            )

        final_snapshot_status = snapshot_path.stat()
        stable_fields = (
            "st_dev",
            "st_ino",
            "st_mode",
            "st_size",
            "st_mtime_ns",
            "st_ctime_ns",
        )
        if any(
            getattr(initial_snapshot_status, field_name)
            != getattr(final_snapshot_status, field_name)
            for field_name in stable_fields
        ):
            raise RuntimeError(
                f"Controlled ingestion snapshot changed while parsing: "
                f"{provenance_path}"
            )
        final_digest, final_size = stream_source_sha256(snapshot_path)
        if final_digest != source_digest or final_size != source_size:
            raise RuntimeError(
                f"Controlled ingestion snapshot bytes changed while parsing: "
                f"{provenance_path}"
            )

        if cache_path:
            self._save_to_cache(kg, cache_path)

        return kg

    @staticmethod
    def _jsonable(value: Any) -> Any:
        """Normalize metadata for JSON-backed semantic memory storage."""
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, tuple):
            return list(value)
        if isinstance(value, list):
            return [KnowledgeManager._jsonable(item) for item in value]
        if isinstance(value, dict):
            return {str(key): KnowledgeManager._jsonable(item) for key, item in value.items()}
        return value

    def _entity_semantic_text(self, entity: Entity) -> str:
        # Canonical graph identity participates in semantic-row deduplication.
        # Distinct entities may intentionally share every rendered attribute;
        # omitting the id would collapse them into one scope+content row and
        # discard the second entity's authority metadata.
        sections = [
            f"{entity.label} ({entity.type.name})",
            f"Entity ID: {entity.id}",
        ]
        if entity.source_doc_id:
            sections.append(f"Source document: {entity.source_doc_id}")
        if entity.properties:
            sections.append(json.dumps(self._jsonable(entity.properties), sort_keys=True))
        if entity.metadata:
            sections.append(json.dumps(self._jsonable(entity.metadata), sort_keys=True))
        return "\n".join(sections)

    def _relationship_semantic_text(self, relationship: Relationship, kg: KnowledgeGraph) -> str:
        source = kg.get_entity(relationship.source_id)
        target = kg.get_entity(relationship.target_id)
        source_label = source.label if source else relationship.source_id
        target_label = target.label if target else relationship.target_id
        text = (
            f"{source_label} {relationship.label.name} {target_label}"
            f"\nRelationship ID: {relationship.id}"
        )
        if relationship.source_doc_id:
            text = f"{text}\nSource document: {relationship.source_doc_id}"
        if relationship.context:
            text = f"{text}\n{relationship.context}"
        if relationship.properties:
            text = f"{text}\n{json.dumps(self._jsonable(relationship.properties), sort_keys=True)}"
        return text

    async def persist_knowledge_graph_to_semantic_db(
        self,
        kg: KnowledgeGraph,
        memory_type: str = "knowledge_graph",
        *,
        scope_key: str,
    ) -> int:
        """Persist graph entities and relationships into the semantic memory DB."""
        if not self.semantic_db_path:
            raise RuntimeError(
                "KnowledgeManager.semantic_db_path is not configured; "
                "pass semantic_db_path to enable semantic archive persistence."
            )
        if not isinstance(kg, KnowledgeGraph):
            raise TypeError("kg must be a KnowledgeGraph value")
        # ``KnowledgeGraph`` intentionally remains a mutable public value.
        # Revalidate its live state at the persistence boundary so direct
        # post-add mutations cannot bypass per-record or aggregate limits.
        kg.validate(serialized_size=True)

        db = SemanticMemoryDB(self.semantic_db_path)
        await db.initialize()
        try:
            records: List[Tuple[str, str, Mapping[str, Any]]] = []
            for entity in kg.entities.values():
                records.append(
                    (
                        self._entity_semantic_text(entity),
                        f"{memory_type}:entity",
                        {
                            "kind": "entity",
                            "entity_id": entity.id,
                            "entity_type": entity.type.name,
                            "source_doc_id": entity.source_doc_id,
                            "text_span": self._jsonable(entity.text_span),
                            "properties": self._jsonable(entity.properties),
                            "metadata": self._jsonable(entity.metadata),
                        },
                    )
                )

            for relationship in kg.relationships:
                records.append(
                    (
                        self._relationship_semantic_text(relationship, kg),
                        f"{memory_type}:relationship",
                        {
                            "kind": "relationship",
                            "relationship_id": relationship.id,
                            "relationship_type": relationship.label.name,
                            "source_id": relationship.source_id,
                            "target_id": relationship.target_id,
                            "source_doc_id": relationship.source_doc_id,
                            "properties": self._jsonable(relationship.properties),
                            "metadata": self._jsonable(relationship.metadata),
                        },
                    )
                )
            stored_ids = await db.add_memories_from_text_atomic(
                records,
                scope_key=scope_key,
            )
        finally:
            close = getattr(db, "close", None)
            if close is not None:
                await close()

        stored_count = len(stored_ids)
        logger.info(
            "Persisted %s graph records atomically to semantic archive: %s",
            stored_count,
            self.semantic_db_path,
        )
        return stored_count

    def persist_knowledge_graph_to_semantic_db_sync(
        self,
        kg: KnowledgeGraph,
        memory_type: str = "knowledge_graph",
        *,
        scope_key: str,
    ) -> int:
        """Synchronous boundary for scripts and CLI paths."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(
                self.persist_knowledge_graph_to_semantic_db(
                    kg,
                    memory_type,
                    scope_key=scope_key,
                )
            )
        raise RuntimeError(
            "Cannot use sync semantic persistence inside an active event loop; "
            "await persist_knowledge_graph_to_semantic_db(...) instead."
        )

    def process_file_to_semantic_archive(
        self,
        file_path: Union[str, Path],
        *,
        scope_key: str,
    ) -> KnowledgeGraph:
        """Process one input and persist the resulting graph to the semantic archive."""
        kg = self.process_file(file_path)
        self.persist_knowledge_graph_to_semantic_db_sync(
            kg,
            scope_key=scope_key,
        )
        return kg

    def process_multiple_files_to_semantic_archive(
        self,
        file_paths: Sequence[Union[str, Path]],
        max_workers: int = 4,
        max_files: Optional[int] = None,
        *,
        scope_key: str,
    ) -> KnowledgeGraph:
        """Process multiple inputs and persist the merged graph to the semantic archive."""
        kg = self.process_multiple_files(file_paths, max_workers=max_workers, max_files=max_files)
        self.persist_knowledge_graph_to_semantic_db_sync(
            kg,
            scope_key=scope_key,
        )
        return kg

    def process_file(self, file_path: Union[str, Path]) -> KnowledgeGraph:
        """Processes a single file, directory, or ZIP archive."""
        p = Path(file_path)
        entry_stat = self._validate_source_entry(p)
        master_kg = KnowledgeGraph(metadata={'processed_input': str(p.resolve())})

        if stat.S_ISREG(entry_stat.st_mode):
            if p.suffix.lower() == '.zip':
                extracted_kg = self._process_zip(p)
                master_kg.merge(extracted_kg)
            else:
                file_kg = self._process_file_wrapper(p)
                master_kg.merge(file_kg)
        elif stat.S_ISDIR(entry_stat.st_mode):
            extracted_kg = self._process_directory(p)
            master_kg.merge(extracted_kg)
        else:
            raise FileNotFoundError(f"Input path {p} is not a valid file or directory.")
        
        return master_kg
    
    def process_multiple_files(self, file_paths: Sequence[Union[str, Path]], 
                               max_workers: int = 4, max_files: Optional[int] = None) -> KnowledgeGraph:
        """Processes multiple files/directories in parallel and merges their knowledge graphs."""
        if type(max_workers) is not int or not 1 <= max_workers <= INGEST_MAX_WORKERS:
            raise ValueError(
                f"max_workers must be an integer from 1 through {INGEST_MAX_WORKERS}"
            )
        if max_files is not None and (type(max_files) is not int or max_files < 1):
            raise ValueError("max_files must be positive when provided")

        source_records = self._collect_source_files(file_paths)

        if max_files is not None and len(source_records) > max_files:
            logger.info(f"Limiting processing to {max_files} files out of {len(source_records)} found.")
            source_records = source_records[:max_files]

        if not source_records:
            raise ValueError("No valid files found to process.")

        manifest_digest, source_manifest = self._build_source_manifest(source_records)
        actual_paths_to_process = [record.path for record in source_records]
        expected_digest_by_path = {
            record.path: cast(str, source_manifest[index]["sha256"])
            for index, record in enumerate(source_records)
        }
        master_kg = KnowledgeGraph(
            metadata={
                'processed_inputs_count': len(file_paths),
                'processed_file_count': len(source_records),
                'source_total_bytes': sum(record.size_bytes for record in source_records),
                'source_tree_manifest_sha256': manifest_digest,
                'source_tree_manifest': source_manifest,
            }
        )

        logger.info(f"Starting parallel processing of {len(actual_paths_to_process)} files with {max_workers} workers.")
        results_by_path: Dict[Path, KnowledgeGraph] = {}
        failures_by_path: Dict[Path, BaseException] = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_path = {executor.submit(self.process_file, path_item): path_item for path_item in actual_paths_to_process}
            
            for future in as_completed(future_to_path):
                path_item = future_to_path[future]
                try:
                    result = future.result()
                    actual_digest = result.metadata.get("source_content_sha256")
                    if (
                        actual_digest is not None
                        and actual_digest != expected_digest_by_path[path_item]
                    ):
                        raise RuntimeError(
                            "Source bytes changed between manifest creation and "
                            f"anchored ingestion: {path_item}"
                        )
                    results_by_path[path_item] = result
                    logger.debug(f"Successfully processed KG from: {path_item}")
                except Exception as e:
                    logger.error(f"Error processing file {path_item} in parallel: {e}", exc_info=True)
                    failures_by_path[path_item] = e

        if failures_by_path:
            ordered_failures = [
                (path, failures_by_path[path])
                for path in actual_paths_to_process
                if path in failures_by_path
            ]
            failure_list = "; ".join(
                f"{path}: {error}" for path, error in ordered_failures[:5]
            )
            if len(ordered_failures) > 5:
                failure_list += f"; ... {len(ordered_failures) - 5} more"
            raise RuntimeError(
                f"Failed to process {len(ordered_failures)} file(s): {failure_list}"
            )

        # Completion order is scheduler-dependent.  Merge only after all workers
        # return, strictly following the signed source-manifest order.
        for path_item in actual_paths_to_process:
            master_kg.merge(results_by_path[path_item])
            logger.debug(f"Merged KG in manifest order from: {path_item}")
        
        logger.info(f"Finished processing all files. Master KG has {len(master_kg.entities)} entities and {len(master_kg.relationships)} relationships.")
        return master_kg
    
    def _process_directory(self, dir_path: Path) -> KnowledgeGraph:
        """Process a bounded tree and reject membership/content drift."""
        logger.info(f"Processing directory: {dir_path}")
        initial_status = dir_path.lstat()
        if not stat.S_ISDIR(initial_status.st_mode):
            raise ValueError(f"Directory source is no longer a directory: {dir_path}")
        directory_graph = self.process_multiple_files([dir_path])
        final_records = self._collect_source_files([dir_path])
        final_manifest_digest, _ = self._build_source_manifest(final_records)
        if (
            final_manifest_digest
            != directory_graph.metadata.get("source_tree_manifest_sha256")
        ):
            raise RuntimeError(
                f"Directory membership or bytes changed during ingestion: {dir_path}"
            )
        final_status = dir_path.lstat()
        stable_fields = (
            "st_dev",
            "st_ino",
            "st_mode",
            "st_mtime_ns",
            "st_ctime_ns",
        )
        if any(
            getattr(initial_status, field_name) != getattr(final_status, field_name)
            for field_name in stable_fields
        ):
            raise RuntimeError(f"Directory source changed during ingestion: {dir_path}")
        directory_graph.metadata['source_directory'] = str(dir_path.resolve())
        return directory_graph
    
    def _process_zip(self, zip_path: Path) -> KnowledgeGraph:
        """Safely extract one descriptor-anchored bounded ZIP snapshot."""
        provenance_path = Path(os.path.abspath(os.fspath(zip_path)))
        with tempfile.TemporaryDirectory(prefix="archive-zip-source-") as staging:
            snapshot_path, source_descriptor = self._snapshot_regular_source(
                provenance_path,
                Path(staging),
            )
            return self._process_zip_snapshot(
                snapshot_path,
                provenance_path,
                source_descriptor,
            )

    def _process_zip_snapshot(
        self,
        snapshot_path: Path,
        provenance_path: Path,
        source_descriptor: Mapping[str, Any],
    ) -> KnowledgeGraph:
        """Parse an isolated ZIP snapshot and normalize transient paths."""
        source_digest = source_descriptor.get("source_content_sha256")
        source_size = source_descriptor.get("source_size_bytes")
        if not isinstance(source_digest, str) or not isinstance(source_size, int):
            raise ValueError("ZIP snapshot source descriptor is malformed")
        zip_kg = KnowledgeGraph(
            metadata={
                "source_zip_file": str(provenance_path),
                "source_content_sha256": source_digest,
                "source_size_bytes": source_size,
            }
        )
        logger.info("Processing ZIP archive: %s", provenance_path)
        initial_snapshot_status = snapshot_path.stat()
        try:
            with tempfile.TemporaryDirectory(prefix="archive-zip-unpack-") as tmpdir:
                tmpdir_path = Path(tmpdir).resolve()
                member_manifest: List[Dict[str, Any]] = []
                with zipfile.ZipFile(snapshot_path, 'r') as zip_ref:
                    members = zip_ref.infolist()
                    if len(members) > ZIP_MAX_MEMBERS:
                        raise ValueError(
                            f"ZIP contains {len(members)} members; limit is {ZIP_MAX_MEMBERS}"
                        )

                    total_uncompressed = 0
                    for member in members:
                        normalized_name = member.filename.replace("\\", "/")
                        member_path = PurePosixPath(normalized_name)
                        if (
                            not normalized_name
                            or member_path.is_absolute()
                            or ".." in member_path.parts
                            or any(part in {"", "."} for part in member_path.parts)
                        ):
                            raise ValueError(f"Unsafe ZIP member path: {member.filename!r}")
                        if not member.is_dir() and member_path.suffix.lower() == ".zip":
                            raise ValueError(f"Nested ZIP archives are not allowed: {member.filename!r}")

                        unix_mode = (member.external_attr >> 16) & 0xFFFF
                        file_type = stat.S_IFMT(unix_mode)
                        if file_type not in {0, stat.S_IFREG, stat.S_IFDIR}:
                            raise ValueError(f"ZIP member is a link or special file: {member.filename!r}")
                        if stat.S_ISLNK(unix_mode):
                            raise ValueError(f"ZIP symbolic links are not allowed: {member.filename!r}")

                        if member.file_size > ZIP_MAX_MEMBER_BYTES:
                            raise ValueError(
                                f"ZIP member exceeds {ZIP_MAX_MEMBER_BYTES} bytes: {member.filename!r}"
                            )
                        total_uncompressed += member.file_size
                        if total_uncompressed > ZIP_MAX_TOTAL_BYTES:
                            raise ValueError(
                                f"ZIP expands beyond {ZIP_MAX_TOTAL_BYTES} total bytes"
                            )
                        if member.file_size:
                            if member.compress_size == 0:
                                raise ValueError(
                                    f"ZIP member has an invalid compression size: {member.filename!r}"
                                )
                            compression_ratio = member.file_size / member.compress_size
                            if compression_ratio > ZIP_MAX_COMPRESSION_RATIO:
                                raise ValueError(
                                    f"ZIP member compression ratio {compression_ratio:.1f}:1 exceeds "
                                    f"{ZIP_MAX_COMPRESSION_RATIO:.0f}:1: {member.filename!r}"
                                )

                    for member in members:
                        normalized_name = member.filename.replace("\\", "/")
                        target = (tmpdir_path / normalized_name).resolve()
                        if not target.is_relative_to(tmpdir_path):
                            raise ValueError(f"ZIP member escapes extraction root: {member.filename!r}")
                        if member.is_dir():
                            target.mkdir(parents=True, exist_ok=True)
                            continue

                        target.parent.mkdir(parents=True, exist_ok=True)
                        copied = 0
                        member_digest = hashlib.sha256()
                        with zip_ref.open(member, "r") as source, target.open("xb") as destination:
                            while chunk := source.read(ZIP_COPY_CHUNK_BYTES):
                                copied += len(chunk)
                                if copied > member.file_size or copied > ZIP_MAX_MEMBER_BYTES:
                                    raise ValueError(
                                        f"ZIP member expanded beyond declared bounds: {member.filename!r}"
                                    )
                                destination.write(chunk)
                                member_digest.update(chunk)
                        if copied != member.file_size:
                            raise ValueError(
                                f"ZIP member size mismatch for {member.filename!r}: "
                                f"expected {member.file_size}, read {copied}"
                            )
                        member_manifest.append(
                            {
                                "path": normalized_name,
                                "size_bytes": copied,
                                "sha256": member_digest.hexdigest(),
                            }
                        )

                member_manifest.sort(key=lambda entry: entry["path"])
                canonical_manifest = json.dumps(
                    member_manifest,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("utf-8")
                zip_kg.metadata['source_tree_manifest_sha256'] = hashlib.sha256(
                    canonical_manifest
                ).hexdigest()
                zip_kg.metadata['source_tree_manifest'] = member_manifest
                zip_kg.metadata['source_total_bytes'] = sum(
                    entry['size_bytes'] for entry in member_manifest
                )
                logger.info(
                    "Extracted ZIP %s to controlled temporary storage",
                    provenance_path,
                )
                
                # Route the controlled tree through the same deterministic,
                # entry-counted traversal used by ordinary directories.
                temp_km = KnowledgeManager(
                    cache_dir=None,
                    force_no_cache=True,
                    semantic_db_path=self.semantic_db_path,
                )
                extracted_contents_kg = temp_km.process_multiple_files(
                    [tmpdir_path],
                    max_workers=1,
                )
                extracted_contents_kg = self._rebind_graph_paths(
                    extracted_contents_kg,
                    tmpdir_path,
                    f"{provenance_path}!",
                )
                self._namespace_graph_provenance(
                    extracted_contents_kg,
                    source_digest,
                )
                zip_kg.merge(extracted_contents_kg)

            final_snapshot_status = snapshot_path.stat()
            stable_fields = (
                "st_dev",
                "st_ino",
                "st_mode",
                "st_size",
                "st_mtime_ns",
                "st_ctime_ns",
            )
            if any(
                getattr(initial_snapshot_status, field_name)
                != getattr(final_snapshot_status, field_name)
                for field_name in stable_fields
            ):
                raise RuntimeError(
                    f"Controlled ZIP snapshot changed while parsing: "
                    f"{provenance_path}"
                )
            final_digest, final_size = stream_source_sha256(snapshot_path)
            if final_digest != source_digest or final_size != source_size:
                raise RuntimeError(
                    f"Controlled ZIP snapshot bytes changed while parsing: "
                    f"{provenance_path}"
                )

        except zipfile.BadZipFile:
            logger.error("Invalid or corrupted ZIP file: %s", provenance_path)
            raise
        except (OSError, RuntimeError, ValueError, zipfile.LargeZipFile) as e:
            logger.error(
                "Error processing ZIP file %s: %s",
                provenance_path,
                e,
                exc_info=True,
            )
            raise RuntimeError(
                f"Error processing ZIP file {provenance_path}: {e}"
            ) from e
        return zip_kg
    
    def save_knowledge_graph(self, kg: KnowledgeGraph, output_path: Union[str, Path]) -> None:
        """Saves the knowledge graph to a JSON file."""
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(p, 'w', encoding='utf-8') as f:
                json.dump(kg.to_dict(), f, indent=2, ensure_ascii=False)
        except (OSError, TypeError, ValueError) as e:
            raise RuntimeError(f"Error saving knowledge graph to {p}") from e
        logger.info(f"Knowledge graph saved to: {p}")
    
    def load_knowledge_graph(self, input_path: Union[str, Path]) -> Optional[KnowledgeGraph]:
        """Loads a knowledge graph from a JSON file."""
        p = Path(input_path)
        if not p.exists():
            logger.error(f"Knowledge graph file not found: {p}")
            return None
        try:
            with open(p, 'r', encoding='utf-8') as f:
                data = json.load(f)
            kg = KnowledgeGraph.from_dict(data)
            logger.info(f"Knowledge graph loaded from: {p}")
            return kg
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in knowledge graph file {p}: {e}")
        except (OSError, TypeError, ValueError, KeyError) as e:
            logger.error(f"Error loading knowledge graph from {p}: {e}")
        return None

# ----------------------------------------
# Knowledge Analysis and Enrichment
# (Using the more complete version from attachment, with fixes)
# ----------------------------------------

class KnowledgeAnalyzer:
    """
    Analyzes and enriches knowledge graphs.
    """
    
    @staticmethod
    def identify_core_concepts(kg: KnowledgeGraph, top_n: int = 10) -> List[Entity]:
        """
        Identify the most central concepts in the knowledge graph.
        
        Args:
            kg: Knowledge graph to analyze
            top_n: Number of top concepts to return
            
        Returns:
            List of top entities by centrality
        """
        if not kg.entities:
            return []
        G = kg.to_networkx()
        if not G.nodes:
            return []
        
        try:
            degree_centrality = nx.degree_centrality(G)
        except Exception as e:
            logger.error(f"Error calculating degree centrality: {e}")
            return []
        
        sorted_entities_data = sorted(
            [(entity_id_obj, degree_centrality.get(entity_id_obj, 0.0)) 
             for entity_id_obj in G.nodes()],
            key=lambda x: x[1],
            reverse=True
        )
        
        core_entities = []
        for entity_id_obj, score in sorted_entities_data[:top_n]:
            entity_id_str = str(entity_id_obj)
            if entity_id_str in kg.entities:
                core_entities.append(kg.entities[entity_id_str])
            else:
                logger.warning(f"Entity ID {entity_id_str} (score: {score}) from NetworkX graph not found in KnowledgeGraph entities.")
        return core_entities
    
    @staticmethod
    def cluster_entities(kg: KnowledgeGraph, n_clusters: Optional[int] = None, algorithm: str = 'greedy_modularity') -> Dict[int, List[Entity]]:
        """
        Cluster entities based on their relationships using community detection.
        If n_clusters is None, the number of clusters will be determined by the algorithm.
        Supported algorithms: 'greedy_modularity', 'louvain' (if python-louvain is installed).
        
        Args:
            kg: Knowledge graph to analyze
            n_clusters: Desired number of clusters (approximate for some algorithms)
            algorithm: Community detection algorithm to use.
            
        Returns:
            Dictionary mapping cluster IDs to lists of entities
        """
        if not kg.entities:
            return {}
        G = kg.to_networkx()
        if not G.nodes or G.number_of_edges() == 0: # Community detection needs edges
            logger.warning("Cannot cluster entities: graph has no nodes or no edges.")
            if n_clusters and kg.entities: # Fallback to random if clusters are requested
                entities_list = list(kg.entities.values())
                random.shuffle(entities_list)
                clusters = {}
                chunk_size = max(1, len(entities_list) // n_clusters)
                for i in range(n_clusters):
                    start_idx = i * chunk_size
                    end_idx = (i + 1) * chunk_size if i < n_clusters - 1 else len(entities_list)
                    if start_idx >= len(entities_list):
                        break
                    clusters[i] = entities_list[start_idx:end_idx]
                return clusters
            return {}
        
        return KnowledgeAnalyzer.detect_communities(kg, n_clusters, algorithm, G)

    @staticmethod
    def detect_communities(kg: 'KnowledgeGraph', n_clusters: Optional[int], algorithm: str, G: nx.Graph) -> Dict[int, List['Entity']]:
        """Detect communities in the knowledge graph using various algorithms."""
        G_undirected = G.to_undirected()
        
        clusters: Dict[int, List['Entity']] = {}
        
        def _extract_communities_with_greedy_modularity() -> List[List[str]]:
            """Extract communities using greedy modularity algorithm."""
            try:
                communities_generator_raw = nx.algorithms.community.greedy_modularity_communities(G_undirected)
                # The type checker might infer a type like ArrayLike which it considers non-iterable here.
                # We cast to the documented return type: a generator of frozensets of node IDs (strings).
                typed_communities_generator = cast(Generator[frozenset[str], None, None], communities_generator_raw)
                
                # Convert generator to list first, then process each community
                communities_list = list(typed_communities_generator)
                return [list(community) for community in communities_list]
            except Exception as e:
                logger.warning(f"Error in greedy modularity community detection: {e}")
                return []
        
        try:
            if algorithm == 'louvain':
                try:
                    logger.warning("Louvain algorithm selected but not fully integrated/installed; falling back to greedy_modularity.")
                    communities = _extract_communities_with_greedy_modularity()
                except ImportError:
                    logger.warning("Louvain community detection algorithm not available (python-louvain not installed?). Falling back to greedy_modularity.")
                    communities = _extract_communities_with_greedy_modularity()
            elif algorithm == 'greedy_modularity':
                communities = _extract_communities_with_greedy_modularity()
                logger.info(f"Detected {len(communities)} communities using greedy_modularity.")
            else:
                logger.error(f"Unsupported clustering algorithm: {algorithm}. Using greedy_modularity.")
                communities = _extract_communities_with_greedy_modularity()
        except Exception as e:
            logger.warning(f"Error in community detection ({algorithm}): {e}. Falling back to random assignment if n_clusters specified.")
            communities = []
            if n_clusters is not None and kg.entities: 
                entities_list = list(kg.entities.values())
                random.shuffle(entities_list)
                chunk_size = max(1, len(entities_list) // n_clusters)
                for i in range(n_clusters):
                    start_idx = i * chunk_size
                    end_idx = (i + 1) * chunk_size if i < n_clusters - 1 else len(entities_list)
                    if start_idx >= len(entities_list):
                        break
                    clusters[i] = entities_list[start_idx:end_idx]
                return clusters
            else:
                logger.warning("No clusters generated due to error and n_clusters not specified for fallback.")
        
        # Convert communities list to clusters dict with proper entity mapping
        for i, community_nodes in enumerate(communities):
            cluster_entities = []
            for node_id in community_nodes:
                if str(node_id) in kg.entities:
                    cluster_entities.append(kg.entities[str(node_id)])
            if cluster_entities:  # Only add non-empty clusters
                clusters[i] = cluster_entities
        
        return clusters
    
    @staticmethod
    def identify_knowledge_gaps(kg: KnowledgeGraph) -> List[Dict[str, Any]]:
        """
        Identify potential gaps in the knowledge graph.
        
        Args:
            kg: Knowledge graph to analyze
            
        Returns:
            List of dictionaries describing potential gaps
        """
        gaps: List[Dict[str, Any]] = []
        if not kg.entities:
            return gaps
            
        G = kg.to_networkx()
        if not G.nodes: 
            return gaps
        
        if G.is_directed():
            components_iter = nx.weakly_connected_components(G)
        else:
            # Should be G_undirected if we want to check for general connectivity
            components_iter = nx.connected_components(G.to_undirected() if G.is_directed() else G)
        
        components = [list(comp) for comp in components_iter]
        if len(components) > 1:
            gaps.append({
                'type': 'disconnected_components',
                'description': f"Found {len(components)} disconnected components in the graph.",
                'details': {'component_count': len(components), 'component_sizes': sorted([len(c) for c in components], reverse=True)}
            })
        
        isolated_entity_ids = list(nx.isolates(G))
        if isolated_entity_ids:
            isolated_entities_sample = [kg.entities[str(eid)].name for eid in isolated_entity_ids[:10] if str(eid) in kg.entities]
            gaps.append({
                'type': 'isolated_entities',
                'description': f"Found {len(isolated_entity_ids)} entities with no (outgoing or incoming if directed) relationships.",
                'details': {'count': len(isolated_entity_ids), 'sample_entities': isolated_entities_sample}
            })
        
        if kg.relationships:
            rel_type_counts = Counter(rel.type for rel in kg.relationships.values())
            threshold = max(3, int(0.01 * len(kg.relationships))) 
            rare_rel_types = {rt.name: count for rt, count in rel_type_counts.items() if count < threshold}
            if rare_rel_types:
                gaps.append({
                    'type': 'rare_relationship_types',
                    'description': f"Found relationship types with fewer than {threshold} instances.",
                    'details': {'types': rare_rel_types}
                })
        return gaps
    
    @staticmethod
    def enrich_knowledge_graph(kg: KnowledgeGraph, infer_relations: bool = True, prune_isolated: bool = False, confidence_threshold: Optional[float] = None) -> KnowledgeGraph:
        """
        Enrich the knowledge graph with metadata, optionally inferred relationships, and pruning.
        Modifies the KG in place.
        
        Args:
            kg: Knowledge graph to enrich
            infer_relations: Whether to attempt to infer new relationships
            prune_isolated: Whether to remove isolated entities (no relationships)
            confidence_threshold: If set, prune relationships (and then entities if they become isolated) below this confidence.
            
        Returns:
            The enriched knowledge graph (modified in place)
        """
        kg.metadata['last_enriched_at'] = datetime.now(timezone.utc).isoformat()
        kg.metadata['statistics_before_enrichment'] = {
            'entity_count': len(kg.entities),
            'relationship_count': len(kg.relationships),
        }
        
        if confidence_threshold is not None:
            rels_to_prune = [rid for rid, rel in kg.relationships.items() if rel.confidence < confidence_threshold]
            if rels_to_prune:
                logger.info(f"Pruning {len(rels_to_prune)} relationships with confidence < {confidence_threshold}")
                for rid in rels_to_prune:
                    del kg.relationships[rid]
        
        if prune_isolated:
            G_temp = kg.to_networkx() # Rebuild graph if relationships were pruned
            isolated_ids = list(nx.isolates(G_temp))
            if isolated_ids:
                logger.info(f"Pruning {len(isolated_ids)} isolated entities.")
                for eid_obj in isolated_ids:
                    eid_str = str(eid_obj)
                    if eid_str in kg.entities:
                        del kg.entities[eid_str]
                        # Also remove any relationships that might still point to this entity (though isolates should mean no edges)
                        rels_to_remove_due_to_pruned_entity = [
                            r_id for r_id, r in kg.relationships.items() if r.source_id == eid_str or r.target_id == eid_str
                        ]
                        for r_id_remove in rels_to_remove_due_to_pruned_entity:
                            del kg.relationships[r_id_remove]

        if infer_relations:
            logger.info("Attempting to infer new relationships...")
            G = kg.to_networkx() # Rebuild graph if entities/relations were pruned
            new_relationships_count = 0
            
            for source_id_str in list(kg.entities.keys()): # list() for safe iteration if modified
                if not G.has_node(source_id_str): continue
                for target_id_str in list(kg.entities.keys()):
                    if not G.has_node(target_id_str): continue
                    if source_id_str == target_id_str: continue
                    
                    direct_rel_exists = any(
                        (rel.source_id == source_id_str and rel.target_id == target_id_str) or \
                        (rel.source_id == target_id_str and rel.target_id == source_id_str) # Check both directions
                        for rel in kg.relationships.values()
                    )
                    if direct_rel_exists: continue

                    try:
                        for path in nx.all_simple_paths(G, source=source_id_str, target=target_id_str, cutoff=2):
                            if len(path) == 3: 
                                intermediate_id_str = str(path[1])
                                inferred_rel_id = generate_deterministic_id([source_id_str, "inferred_related_to", target_id_str, "via", intermediate_id_str])
                                
                                if inferred_rel_id not in kg.relationships:
                                    inferred_rel = Relationship(
                                        id=inferred_rel_id,
                                        source_id=source_id_str,
                                        target_id=target_id_str,
                                        label=RelationType.RELATED_TO,
                                        properties={
                                            'inferred_via': intermediate_id_str,
                                            'inference_type': 'path_length_2',
                                            'confidence': 0.4,
                                        },
                                    )
                                    kg.add_relationship(inferred_rel)
                                    new_relationships_count += 1
                                    if new_relationships_count % 100 == 0 and new_relationships_count > 0:
                                        logger.debug(f"Added {new_relationships_count} inferred relationships so far...")
                    except nx.NodeNotFound: # If a node was pruned during iteration
                        logger.debug(f"Node not found during path finding, likely pruned: {source_id_str} or {target_id_str}")
                        continue # Skip to next pair
                            
            if new_relationships_count > 0:
                logger.info(f"Added {new_relationships_count} inferred relationships.")
        
        # Update final metadata
        kg.metadata['statistics_after_enrichment'] = {
            'entity_count': len(kg.entities),
            'relationship_count': len(kg.relationships),
            'entity_types_count': Counter(entity.type.name for entity in kg.entities.values()),
            'relationship_types_count': Counter(rel.type.name for rel in kg.relationships.values())
        }
        core_concepts = KnowledgeAnalyzer.identify_core_concepts(kg, top_n=20)
        kg.metadata['core_concepts_analysis'] = [
            {'id': entity.id, 'name': entity.name, 'type': entity.type.name}
            for entity in core_concepts
        ]
        kg.metadata['knowledge_gaps_analysis'] = KnowledgeAnalyzer.identify_knowledge_gaps(kg)
        
        return kg

# ----------------------------------------
# Output Formatter
# ----------------------------------------

class OutputFormatter:
    """
    Formats knowledge graphs into training examples for language models.
    """
    
    def __init__(self, knowledge_density: float = 0.7, max_examples: Optional[int] = 1000, 
                 min_entities_per_example: int = 2, seed: Optional[int] = None):
        self.knowledge_density = min(max(float(knowledge_density), 0.0), 1.0)
        self.max_examples = max_examples
        self.min_entities_per_example = min_entities_per_example
        # This PRNG controls reproducible dataset ordering only. It never
        # generates credentials, trust decisions, identifiers, or secrets.
        self.random_state = random.Random(seed)  # nosec B311
        logger.info(f"OutputFormatter initialized with density={knowledge_density}, max_examples={max_examples}, seed={seed}")
    
    def create_dataset(self, kg: KnowledgeGraph) -> Dataset:
        """Creates a dataset of training examples from the knowledge graph."""
        dataset = Dataset(metadata={'source_kg_id': kg.metadata.get('id', generate_uuid()), 'creation_date': datetime.now(timezone.utc).isoformat()})
        if not kg.entities:
            logger.warning("Knowledge graph has no entities. Cannot create dataset.")
            return dataset

        # Prioritize core concepts for example generation
        core_entities = KnowledgeAnalyzer.identify_core_concepts(kg, top_n=max(50, int(len(kg.entities) * 0.2))) # Get a good pool of core entities
        other_entities = [e for e in kg.entities.values() if e not in core_entities]
        self.random_state.shuffle(core_entities)
        self.random_state.shuffle(other_entities)
        
        # Blend example types
        example_generators = [
            self._create_fact_examples, 
            self._create_relation_examples, 
            self._create_contextual_qa_examples, # New type: Q&A based on entity attributes/relations
        ]
        self.random_state.shuffle(example_generators)

        generated_example_count = 0
        for generator_func in example_generators:
            if self.max_examples and generated_example_count >= self.max_examples:
                break
            # Pass both core and other entities, let generator decide how to use them
            # Or, alternate focus between core and other entities
            target_entities_for_generator = core_entities + other_entities 
            self.random_state.shuffle(target_entities_for_generator)

            for example in generator_func(kg, target_entities_for_generator):
                if self.max_examples and generated_example_count >= self.max_examples:
                    break
                dataset.examples.append(example)
                generated_example_count += 1
                
            logger.info(f"Generated {generated_example_count} examples so far (after {generator_func.__name__}).")

        if self.max_examples and len(dataset.examples) > self.max_examples:
            # Use random.sample instead of random.choice for sampling without numpy
            dataset.examples = self.random_state.sample(dataset.examples, self.max_examples)
        
        logger.info(f"Created dataset with {len(dataset.examples)} examples.")
        return dataset

    def _format_entity_for_prompt(self, entity: Entity) -> str:
        attrs = ", ".join(f"{k}: {v}" for k, v in entity.attributes.items() if isinstance(v, (str, int, float))) 
        return f"{entity.name} (Type: {entity.type.name}{f', Attributes: {attrs}' if attrs else ''})"

    def _create_fact_examples(self, kg: KnowledgeGraph, entities_pool: List[Entity]) -> Iterator[DatasetExample]:
        """Generate examples describing individual entities (What is X? Describe X.)."""
        count = 0
        for entity in entities_pool:
            if self.max_examples and count >= self.max_examples // 2: # Allocate budget per type
                break
            if not entity.attributes and entity.type == EntityType.CONCEPT: # Skip bare concepts unless they have some detail
                # Could also check number of relationships if attributes are empty
                pass # Allow for now, but could be filtered

            description_parts = []
            if entity.attributes:
                for k, v in entity.attributes.items():
                    if isinstance(v, str) and len(v) < 200: # Avoid overly long attribute values in direct description
                        description_parts.append(f"Its {k.replace('_',' ')} is {v}.")
                    elif isinstance(v, (int, float, bool)):
                        description_parts.append(f"Its {k.replace('_',' ')} is {v}.")
            
            # Add info about a few key relationships
            related_info_count = 0
            for rel in kg.relationships.values():
                if related_info_count >= 2: break
                if rel.source_id == entity.id and rel.target_id in kg.entities:
                    target_entity = kg.entities[rel.target_id]
                    description_parts.append(f"It {rel.type.name.lower().replace('_',' ')} {target_entity.name}.")
                    related_info_count += 1
                elif rel.target_id == entity.id and rel.source_id in kg.entities:
                    source_entity = kg.entities[rel.source_id]
                    description_parts.append(f"{source_entity.name} {rel.type.name.lower().replace('_',' ')} it.")
                    related_info_count += 1
            
            if not description_parts and not entity.attributes: # If still no info, skip
                continue

            completion_text = f"{entity.name} is a {entity.type.name.lower().replace('_',' ')}. {' '.join(description_parts)}"
            
            # Vary prompt style
            if self.random_state.random() < 0.5:
                prompt = f"Tell me about {entity.name}."
            else:
                prompt = f"What is {entity.name} and what are its key characteristics?"
            
            if self.random_state.random() > self.knowledge_density: # More conversational
                prompt = f"Hey, can you explain what {entity.name} is?"
                completion_text = f"Sure! {completion_text}"

            yield DatasetExample(
                prompt=prompt,
                completion=completion_text,
                source_entity_ids=[entity.id],
                metadata={'example_type': 'entity_description'}
            )
            count += 1
    
    def _create_relation_examples(self, kg: KnowledgeGraph, entities_pool: List[Entity]) -> Iterator[DatasetExample]:
        """Generate examples describing relationships between entities (How are X and Y related?)."""
        count = 0
        relationships_shuffled = list(kg.relationships.values())
        self.random_state.shuffle(relationships_shuffled)

        for rel in relationships_shuffled:
            if self.max_examples and count >= self.max_examples // 2: # Budget
                break
            if rel.source_id not in kg.entities or rel.target_id not in kg.entities:
                continue
            
            source_entity = kg.entities[rel.source_id]
            target_entity = kg.entities[rel.target_id]

            # Ensure we have at least min_entities_per_example involved if we consider attributes
            if self.min_entities_per_example > 2 and not (source_entity.attributes or target_entity.attributes):
                 # This check might be too strict, depends on desired example complexity
                 pass 

            relation_phrase = rel.type.name.lower().replace('_', ' ')
            
            # Prompt variations
            if self.random_state.random() < 0.33:
                prompt = f"How are {source_entity.name} and {target_entity.name} related?"
            elif self.random_state.random() < 0.66:
                prompt = f"What is the relationship between {source_entity.name} and {target_entity.name}?"
            else:
                prompt = f"Describe the connection between {source_entity.name} ({source_entity.type.name}) and {target_entity.name} ({target_entity.type.name})."

            completion_text = f"{source_entity.name} {relation_phrase} {target_entity.name}."
            if rel.attributes:
                attrs_desc = ", ".join(f"{k} is {v}" for k,v in rel.attributes.items() if isinstance(v, (str,int,float,bool)))
                if attrs_desc:
                    completion_text += f" This relationship has properties: {attrs_desc}."
            
            if self.random_state.random() > self.knowledge_density: # Conversational
                prompt = f"I'm curious about {source_entity.name} and {target_entity.name}. What's their deal?"
                completion_text = f"Well, {completion_text}"

            yield DatasetExample(
                prompt=prompt,
                completion=completion_text,
                source_entity_ids=[source_entity.id, target_entity.id],
                source_relationship_ids=[rel.id],
                metadata={'example_type': 'relationship_description'}
            )
            count += 1

    def _create_contextual_qa_examples(self, kg: KnowledgeGraph, entities_pool: List[Entity]) -> Iterator[DatasetExample]:
        """Generate Q&A examples based on entity attributes or specific relationships."""
        count = 0
        for entity in entities_pool:
            if self.max_examples and count >= self.max_examples // 2: # Budget
                break

            # Q&A about attributes
            if entity.attributes:
                for attr_name, attr_value in entity.attributes.items():
                    if isinstance(attr_value, (str, int, float, bool)) and len(str(attr_value)) < 100: # Keep answers concise
                        prompt = f"What is the {attr_name.replace('_',' ')} of {entity.name}?"
                        completion = str(attr_value)
                        if self.random_state.random() > self.knowledge_density:
                            prompt = f"Tell me, what's {entity.name}'s {attr_name.replace('_',' ')}?"
                            completion = f"The {attr_name.replace('_',' ')} of {entity.name} is {attr_value}."
                        
                        yield DatasetExample(
                            prompt=prompt, completion=completion,
                            source_entity_ids=[entity.id], metadata={'example_type': 'attribute_qa'}
                        )
                        count += 1
                        if self.max_examples and count >= self.max_examples // 2: return
            
            # Q&A about specific relationships (e.g., "What does X CAUSE?")
            outgoing_relationships = [r for r in kg.relationships.values() if r.source_id == entity.id and r.target_id in kg.entities]
            if outgoing_relationships:
                rel_sample = self.random_state.choice(outgoing_relationships)
                target_entity = kg.entities[rel_sample.target_id]
                prompt = f"What {rel_sample.type.name.lower().replace('_',' ')} {entity.name}?" # e.g. What IS_A Animal? (bad) -> What is an example of something X is part of?
                # Rephrase prompt based on relation type for natural Q&A
                q_type = rel_sample.type
                if q_type == RelationType.CAUSES: prompt = f"What does {entity.name} cause?"
                elif q_type == RelationType.HAS_PROPERTY: prompt = f"What is a property of {entity.name} related to {target_entity.name}?"
                elif q_type == RelationType.PART_OF: prompt = f"What is {entity.name} a part of, concerning {target_entity.name}?"
                else: prompt = f"How is {entity.name} related to {target_entity.name} in terms of {q_type.name}?"
                
                completion = f"{entity.name} {rel_sample.type.name.lower().replace('_',' ')} {target_entity.name}."
                if self.random_state.random() > self.knowledge_density:
                    completion = f"Regarding {entity.name}, it {rel_sample.type.name.lower().replace('_',' ')} {target_entity.name}."

                yield DatasetExample(
                    prompt=prompt, completion=completion,
                    source_entity_ids=[entity.id, target_entity.id], source_relationship_ids=[rel_sample.id],
                    metadata={'example_type': 'relation_qa'}
                )
                count += 1
                if self.max_examples and count >= self.max_examples // 2: return

    def format_for_finetuning(self, dataset: Dataset, output_format: str = 'jsonl', system_prompt: Optional[str] = None) -> Union[str, List[Dict]]:
        """Formats the dataset for specific model fine-tuning requirements."""
        output_data_list = []
        if not dataset.examples:
            return "" if output_format == 'jsonl' else []

        for ex in dataset.examples:
            if ex.prompt is None or ex.completion is None: # Skip if essential parts are missing
                logger.warning(f"Skipping example {ex.id} due to missing prompt or completion.")
                continue

            if output_format == 'jsonl': # Generic JSONL: {"prompt": ..., "completion": ...}
                output_data_list.append({'prompt': ex.prompt, 'completion': ex.completion, 'id': ex.id, 'metadata': ex.metadata})
            elif output_format == 'chatgpt': # OpenAI chat format: {"messages": [...]} 
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": ex.prompt})
                messages.append({"role": "assistant", "content": ex.completion})
                output_data_list.append({"messages": messages, 'id': ex.id, 'metadata': ex.metadata})
            elif output_format == 'claude': # Anthropic Claude format (example, verify actual) Human: ... Assistant: ...
                # This usually means a single string with specific prefixes
                # For JSONL output for Claude, it might be: {"text": "Human: ...\n\nAssistant: ..."}
                # Assuming a JSONL of dicts for now, where each dict is a turn or a prompt/completion pair.
                # If it needs to be a single text field per line:
                # text_entry = f"Human: {ex.prompt}\n\nAssistant: {ex.completion}"
                # output_data_list.append({"text": text_entry, 'id': ex.id, 'metadata': ex.metadata})
                # For now, stick to prompt/completion as it's more general for JSONL
                 output_data_list.append({'prompt': f"Human: {ex.prompt}", 'completion': f"Assistant: {ex.completion}", 'id': ex.id, 'metadata': ex.metadata})
            elif output_format == 'llama': # Llama format (often Alpaca style instruction tuning)
                # Example: {"instruction": "...", "input": "...", "output": "..."}
                # Mapping our prompt/completion to this:
                # If prompt is a question, it's instruction. If it needs context, that's input.
                # Simple mapping: prompt is instruction, completion is output.
                output_data_list.append({
                    "instruction": ex.prompt, 
                    "input": "", # Assuming no separate input field for now, could be derived
                    "output": ex.completion, 
                    'id': ex.id, 
                    'metadata': ex.metadata
                })
            else:
                logger.error(f"Unsupported fine-tuning format: {output_format}. Defaulting to generic JSONL.")
                output_data_list.append({'prompt': ex.prompt, 'completion': ex.completion, 'id': ex.id, 'metadata': ex.metadata})
        
        if output_format == 'jsonl' or True: # Default to returning list of dicts for JSONL-like structures
            # If the request was specifically for a single string JSONL, the CLI part would handle writing it.
            return output_data_list # This list of dicts can be written line by line as JSONL
        # This function might be better if it always returns the list of dicts, 
        # and the CLI handles the final string formatting/file writing.

# ----------------------------------------
# CLI Interface
# ----------------------------------------

def main_module_func(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line interface for the knowledge integration toolkit."""
    # This function should ideally be in knowledge-integration-cli.py
    # For now, keeping a basic structure here for testing if run directly.
    parser = argparse.ArgumentParser(
        description='Knowledge Integration Toolkit - Extract, transform, and format knowledge for model fine-tuning'
    )
    
    parser.add_argument('input', nargs='+', help='Input file(s) or directory')
    parser.add_argument('--output-kg', default='knowledge_graph.json', help='Output knowledge graph file')
    parser.add_argument('--output-dataset', default='dataset.jsonl', help='Output dataset file')
    parser.add_argument('--cache-dir', default='.cache_ki', help='Directory for caching results')
    parser.add_argument('--semantic-db', help='Optional SQLite path for semantic archive persistence')
    parser.add_argument(
        '--scope-key',
        help='Required explicit authority partition when --semantic-db is used',
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=INGEST_MAX_WORKERS,
        help=f'Number of parallel workers (1-{INGEST_MAX_WORKERS})',
    )
    parser.add_argument('--force-no-cache', action='store_true', help='Disable caching')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])

    args = parser.parse_args(argv)
    if args.semantic_db and not args.scope_key:
        parser.error("--scope-key is required when --semantic-db is used")

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()],
    )
    logger.info(f"Starting knowledge integration process with args: {args}")

    km = KnowledgeManager(
        cache_dir=args.cache_dir,
        force_no_cache=args.force_no_cache,
        semantic_db_path=args.semantic_db,
    )
    if args.semantic_db:
        master_kg = km.process_multiple_files_to_semantic_archive(
            args.input,
            max_workers=args.workers,
            scope_key=args.scope_key,
        )
    else:
        master_kg = km.process_multiple_files(args.input, max_workers=args.workers)
    
    if master_kg:
        logger.info("Enriching knowledge graph...")
        KnowledgeAnalyzer.enrich_knowledge_graph(master_kg, infer_relations=True, prune_isolated=False)
        km.save_knowledge_graph(master_kg, args.output_kg)

        logger.info("Formatting dataset...")
        formatter = OutputFormatter(knowledge_density=0.7, max_examples=2000, seed=42)
        dataset = formatter.create_dataset(master_kg)
        
        # The format_for_finetuning now returns a list of dicts
        formatted_data_list = formatter.format_for_finetuning(dataset, output_format='jsonl')
        
        # Write to JSONL file
        with open(args.output_dataset, 'w', encoding='utf-8') as f_out:
            for item in formatted_data_list:
                f_out.write(json.dumps(item) + '\n')
        logger.info(f"Dataset saved to {args.output_dataset}")

    logger.info("Knowledge integration process finished.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main_module_func())
