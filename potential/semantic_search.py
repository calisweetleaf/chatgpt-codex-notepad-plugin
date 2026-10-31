#!/usr/bin/env python3
"""
Semantic Search Module

This module implements advanced semantic search capabilities providing intelligent search across
the knowledge graph, entity relationships, and intelligence data.

Author: REM-Core Development Team / Forseti Subsystem Team
Classification: Internal Development Use Only
"""

import logging
import json
import re
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from collections import defaultdict, Counter

# Basic imports that are always available
import numpy as np

# Advanced NLP imports with graceful fallback
EMBEDDING_AVAILABLE = False
try:
    from sentence_transformers import SentenceTransformer
    import faiss
    EMBEDDING_AVAILABLE = True
except ImportError:
    print("Warning: Advanced embedding libraries not available. Using basic text search.")

# MCP Memory integration
MCP_AVAILABLE = False
try:
    # These would be implemented as part of the MCP integration layer
    def mcp_memory_search_nodes(query):
        """Placeholder for MCP memory search."""
        return []
    
    MCP_AVAILABLE = True
except Exception:
    print("Warning: MCP memory integration not available. Using local search only.")

# Utilities
from utilities.logger_config import get_logger
from utilities.cache_manager import get_cache_manager
from utilities.data_sanitizer import DataSanitizer


class SearchType(Enum):
    """Enumeration of search types supported by the semantic search engine."""
    ENTITY_SEARCH = "entity_search"
    RELATIONSHIP_SEARCH = "relationship_search"
    INTELLIGENCE_SEARCH = "intelligence_search"
    CROSS_DOMAIN_SEARCH = "cross_domain_search"
    TEMPORAL_SEARCH = "temporal_search"
    SIMILARITY_SEARCH = "similarity_search"
    GRAPH_TRAVERSAL = "graph_traversal"


class SearchScope(Enum):
    """Enumeration of search scopes."""
    LOCAL = "local"
    MEMORY_GRAPH = "memory_graph"
    GLOBAL = "global"
    CACHED = "cached"


@dataclass
class SearchResult:
    """Data structure for search results with relevance scoring."""
    entity_id: str
    entity_type: str
    relevance_score: float
    match_type: str
    content: Dict[str, Any]
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    search_timestamp: datetime = field(default_factory=datetime.now)
    source: str = "local"


@dataclass
class SearchQuery:
    """Data structure for search queries with advanced parameters."""
    query: str
    search_type: SearchType
    search_scope: SearchScope
    entity_types: Optional[List[str]] = None
    relationship_types: Optional[List[str]] = None
    time_range: Optional[Tuple[datetime, datetime]] = None
    max_results: int = 50
    min_relevance_score: float = 0.1
    include_relationships: bool = True
    include_metadata: bool = True
    use_semantic_similarity: bool = True
    cache_results: bool = True


class SemanticSearchEngine:
    """
    Advanced semantic search engine for Project Forseti.
    
    This class provides intelligent search capabilities across the knowledge graph,
    entity relationships, and intelligence data, with support for semantic similarity,
    cross-domain correlation, and temporal queries.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", cache_size: int = 1000):
        """
        Initialize the semantic search engine.
        
        Args:
            model_name: Name of the sentence transformer model to use
            cache_size: Size of the search cache
        """
        self.logger = get_logger(__name__, "intelligence")
        self.cache_manager = get_cache_manager()
        self.data_sanitizer = DataSanitizer()
        
        # Initialize embedding model if available
        self.embedding_available = False
        self.embedding_model = None
        self.vector_index = None
        self.entity_id_map = {}
        
        if EMBEDDING_AVAILABLE:
            try:
                self.embedding_model = SentenceTransformer(model_name)
                self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
                self.embedding_available = True
                self.logger.info(f"Initialized semantic search with model: {model_name}")
            except Exception as e:
                self.embedding_available = False
                self.logger.warning(f"Failed to initialize embedding model: {str(e)}")
        
        # Local entity database
        self.entity_database = {}
        self.relationship_database = {}
        self.intelligence_database = {}
        
        # Search statistics
        self.search_stats = {
            'total_searches': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'mcp_searches': 0,
            'local_searches': 0,
            'average_response_time': 0.0,
            'total_response_time': 0.0
        }
        
        # Initialize vector index if embeddings are available
        if self.embedding_available:
            self._initialize_vector_index()
        
        self.logger.info("Semantic search engine initialized")
    
    def _initialize_vector_index(self):
        """Initialize FAISS vector index for semantic similarity search."""
        try:
            if self.embedding_available and EMBEDDING_AVAILABLE:
                # Initialize empty FAISS index
                self.vector_index = faiss.IndexFlatIP(self.embedding_dim)
                self.entity_id_map = {}
                self.logger.info("Vector index initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize vector index: {str(e)}")
            self.vector_index = None
    
    def search(self, query: Union[str, SearchQuery]) -> List[SearchResult]:
        """
        Perform semantic search across the knowledge graph and entity database.
        
        Args:
            query: Search query string or SearchQuery object
            
        Returns:
            List[SearchResult]: List of search results ordered by relevance
        """
        start_time = datetime.now()
        
        # Convert string query to SearchQuery object if needed
        if isinstance(query, str):
            search_query = SearchQuery(
                query=query,
                search_type=SearchType.ENTITY_SEARCH,
                search_scope=SearchScope.GLOBAL
            )
        else:
            search_query = query
        
        # Sanitize query
        sanitized_query = self.data_sanitizer.sanitize_data(search_query.query).sanitized_data
        
        # Check cache first
        cache_key = self._generate_cache_key(search_query)
        
        if search_query.cache_results:
            cached_results = self.cache_manager.get(cache_key)
            if cached_results:
                self.search_stats['cache_hits'] += 1
                return cached_results
        
        self.search_stats['cache_misses'] += 1
        
        # Perform search based on scope
        results = []
        
        if search_query.search_scope in [SearchScope.GLOBAL, SearchScope.MEMORY_GRAPH]:
            # Search MCP memory graph
            mcp_results = self._search_mcp_memory(search_query)
            results.extend(mcp_results)
        
        if search_query.search_scope in [SearchScope.GLOBAL, SearchScope.LOCAL]:
            # Search local database
            local_results = self._search_local_database(search_query)
            results.extend(local_results)
        
        # Apply semantic similarity if enabled and available
        if search_query.use_semantic_similarity and self.embedding_available:
            results = self._apply_semantic_ranking(results, sanitized_query)
        
        # Sort by relevance score
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # Apply filters
        results = self._apply_filters(results, search_query)
        
        # Limit results
        results = results[:search_query.max_results]
        
        # Cache results if enabled
        if search_query.cache_results:
            self.cache_manager.set(cache_key, results, ttl=3600)
        
        # Update statistics
        end_time = datetime.now()
        response_time = (end_time - start_time).total_seconds()
        self.search_stats['total_searches'] += 1
        self.search_stats['total_response_time'] += response_time
        self.search_stats['average_response_time'] = (
            self.search_stats['total_response_time'] / self.search_stats['total_searches']
        )
        
        self.logger.info(f"Search completed: {len(results)} results in {response_time:.2f}s")
        
        return results
    
    def _search_mcp_memory(self, search_query: SearchQuery) -> List[SearchResult]:
        """Search the MCP memory graph."""
        if not MCP_AVAILABLE:
            return []
        
        try:
            self.search_stats['mcp_searches'] += 1
            
            # Use MCP memory search
            mcp_results = mcp_memory_search_nodes(search_query.query)
            
            results = []
            for node in mcp_results:
                # Convert MCP node to SearchResult
                result = SearchResult(
                    entity_id=node.get('name', 'unknown'),
                    entity_type=node.get('entityType', 'unknown'),
                    relevance_score=self._calculate_text_similarity(search_query.query, node.get('name', '')),
                    match_type='mcp_memory',
                    content=node,
                    source='mcp_memory'
                )
                
                # Add relationships if requested
                if search_query.include_relationships:
                    result.relationships = self._get_entity_relationships(result.entity_id)
                
                results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"MCP memory search failed: {str(e)}")
            return []
    
    def _search_local_database(self, search_query: SearchQuery) -> List[SearchResult]:
        """Search the local entity database."""
        self.search_stats['local_searches'] += 1
        
        results = []
        
        # Search entities
        for entity_id, entity_data in self.entity_database.items():
            relevance_score = self._calculate_entity_relevance(search_query, entity_id, entity_data)
            
            if relevance_score >= search_query.min_relevance_score:
                result = SearchResult(
                    entity_id=entity_id,
                    entity_type=entity_data.get('type', 'unknown'),
                    relevance_score=relevance_score,
                    match_type='local_entity',
                    content=entity_data,
                    source='local'
                )
                
                # Add relationships if requested
                if search_query.include_relationships:
                    result.relationships = self._get_entity_relationships(entity_id)
                
                results.append(result)
        
        # Search intelligence data
        for intel_id, intel_data in self.intelligence_database.items():
            relevance_score = self._calculate_intelligence_relevance(search_query, intel_id, intel_data)
            
            if relevance_score >= search_query.min_relevance_score:
                result = SearchResult(
                    entity_id=intel_id,
                    entity_type='intelligence',
                    relevance_score=relevance_score,
                    match_type='intelligence',
                    content=intel_data,
                    source='local'
                )
                
                results.append(result)
        
        return results
    
    def _apply_semantic_ranking(self, results: List[SearchResult], query: str) -> List[SearchResult]:
        """Apply semantic similarity ranking to results."""
        if not self.embedding_available or not results:
            return results
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query])[0]
            
            # Calculate semantic similarity for each result
            for result in results:
                # Extract text content for embedding
                content_text = self._extract_text_content(result.content)
                
                if content_text:
                    content_embedding = self.embedding_model.encode([content_text])[0]
                    
                    # Calculate cosine similarity
                    similarity = np.dot(query_embedding, content_embedding) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(content_embedding)
                    )
                    
                    # Boost relevance score with semantic similarity
                    result.relevance_score = (result.relevance_score + similarity) / 2
                    result.metadata['semantic_similarity'] = float(similarity)
            
        except Exception as e:
            self.logger.error(f"Semantic ranking failed: {str(e)}")
        
        return results
    
    def _apply_filters(self, results: List[SearchResult], search_query: SearchQuery) -> List[SearchResult]:
        """Apply filters to search results."""
        filtered_results = results
        
        # Filter by entity types
        if search_query.entity_types:
            filtered_results = [r for r in filtered_results if r.entity_type in search_query.entity_types]
        
        # Filter by minimum relevance score
        filtered_results = [r for r in filtered_results if r.relevance_score >= search_query.min_relevance_score]
        
        # Filter by time range
        if search_query.time_range:
            filtered_results = self._filter_by_time_range(filtered_results, search_query.time_range)
        
        return filtered_results
    
    def _filter_by_time_range(self, results: List[SearchResult], time_range: Tuple[datetime, datetime]) -> List[SearchResult]:
        """Filter results by time range."""
        start_time, end_time = time_range
        filtered_results = []
        
        for result in results:
            # Check if result has timestamp information
            result_time = result.content.get('timestamp') or result.content.get('created_at')
            
            if result_time:
                if isinstance(result_time, str):
                    try:
                        result_time = datetime.fromisoformat(result_time)
                    except ValueError:
                        continue
                
                if start_time <= result_time <= end_time:
                    filtered_results.append(result)
            else:
                # Include results without timestamps
                filtered_results.append(result)
        
        return filtered_results
    
    def _calculate_entity_relevance(self, search_query: SearchQuery, entity_id: str, entity_data: Dict[str, Any]) -> float:
        """Calculate relevance score for an entity."""
        query_terms = search_query.query.lower().split()
        
        # Calculate text similarity
        text_similarity = self._calculate_text_similarity(search_query.query, entity_id)
        
        # Check entity data content
        content_text = json.dumps(entity_data).lower()
        content_matches = sum(1 for term in query_terms if term in content_text)
        content_score = content_matches / len(query_terms) if query_terms else 0
        
        # Combine scores
        relevance_score = (text_similarity + content_score) / 2
        
        return relevance_score
    
    def _calculate_intelligence_relevance(self, search_query: SearchQuery, intel_id: str, intel_data: Dict[str, Any]) -> float:
        """Calculate relevance score for intelligence data."""
        query_terms = search_query.query.lower().split()
        
        # Calculate text similarity
        text_similarity = self._calculate_text_similarity(search_query.query, intel_id)
        
        # Check intelligence data content
        content_text = json.dumps(intel_data).lower()
        content_matches = sum(1 for term in query_terms if term in content_text)
        content_score = content_matches / len(query_terms) if query_terms else 0
        
        # Boost score for intelligence-specific fields
        boost_fields = ['threat_level', 'risk_score', 'analysis_type', 'entity_type']
        boost_score = 0
        for field in boost_fields:
            if field in intel_data:
                boost_score += 0.1
        
        # Combine scores
        relevance_score = (text_similarity + content_score + boost_score) / 2
        
        return relevance_score
    
    def _calculate_text_similarity(self, query: str, text: str) -> float:
        """Calculate basic text similarity."""
        if not query or not text:
            return 0.0
        
        query_words = set(query.lower().split())
        text_words = set(text.lower().split())
        
        if not query_words or not text_words:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = query_words.intersection(text_words)
        union = query_words.union(text_words)
        
        return len(intersection) / len(union)
    
    def _extract_text_content(self, content: Dict[str, Any]) -> str:
        """Extract text content from entity data for embedding."""
        text_parts = []
        
        # Extract common text fields
        text_fields = ['name', 'description', 'summary', 'content', 'title', 'observations']
        
        for field in text_fields:
            if field in content:
                value = content[field]
                if isinstance(value, str):
                    text_parts.append(value)
                elif isinstance(value, list):
                    text_parts.extend([str(item) for item in value])
        
        return ' '.join(text_parts)
    
    def _get_entity_relationships(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get relationships for an entity."""
        relationships = []
        
        # Search local relationships
        for rel_id, rel_data in self.relationship_database.items():
            if rel_data.get('from_entity') == entity_id or rel_data.get('to_entity') == entity_id:
                relationships.append(rel_data)
        
        # Search MCP memory relationships if available
        if MCP_AVAILABLE:
            try:
                # This would need to be implemented based on MCP memory API
                # For now, return local relationships
                pass
            except Exception as e:
                self.logger.error(f"Failed to get MCP relationships: {str(e)}")
        
        return relationships
    
    def _generate_cache_key(self, search_query: SearchQuery) -> str:
        """Generate cache key for search query."""
        key_data = {
            'query': search_query.query,
            'search_type': search_query.search_type.value,
            'search_scope': search_query.search_scope.value,
            'entity_types': search_query.entity_types,
            'max_results': search_query.max_results,
            'min_relevance_score': search_query.min_relevance_score
        }
        
        key_string = json.dumps(key_data, sort_keys=True)
        return f"search:{hashlib.md5(key_string.encode()).hexdigest()}"
    
    def add_entity(self, entity_id: str, entity_data: Dict[str, Any]):
        """Add entity to local database."""
        self.entity_database[entity_id] = entity_data
        
        # Add to vector index if available
        if self.embedding_available and self.vector_index is not None:
            try:
                content_text = self._extract_text_content(entity_data)
                if content_text:
                    embedding = self.embedding_model.encode([content_text])[0]
                    # Reshape embedding for FAISS
                    embedding_array = np.array([embedding]).astype('float32')
                    self.vector_index.add(embedding_array)
                    self.entity_id_map[self.vector_index.ntotal - 1] = entity_id
            except Exception as e:
                self.logger.error(f"Failed to add entity to vector index: {str(e)}")
    
    def add_relationship(self, relationship_id: str, relationship_data: Dict[str, Any]):
        """Add relationship to local database."""
        self.relationship_database[relationship_id] = relationship_data
    
    def add_intelligence_data(self, intel_id: str, intel_data: Dict[str, Any]):
        """Add intelligence data to local database."""
        self.intelligence_database[intel_id] = intel_data
    
    def search_similar_entities(self, entity_id: str, top_k: int = 10) -> List[SearchResult]:
        """Find entities similar to a given entity."""
        if not EMBEDDING_AVAILABLE or entity_id not in self.entity_database:
            return []
        
        try:
            # Get entity content
            entity_data = self.entity_database[entity_id]
            content_text = self._extract_text_content(entity_data)
            
            if not content_text:
                return []
            
            # Generate embedding
            query_embedding = self.embedding_model.encode([content_text])[0]
            
            # Search vector index
            if self.vector_index is not None and self.vector_index.ntotal > 0:
                scores, indices = self.vector_index.search(np.array([query_embedding]), top_k + 1)
                
                results = []
                for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                    if idx in self.entity_id_map:
                        similar_entity_id = self.entity_id_map[idx]
                        
                        # Skip the original entity
                        if similar_entity_id == entity_id:
                            continue
                        
                        result = SearchResult(
                            entity_id=similar_entity_id,
                            entity_type=self.entity_database[similar_entity_id].get('type', 'unknown'),
                            relevance_score=float(score),
                            match_type='semantic_similarity',
                            content=self.entity_database[similar_entity_id],
                            source='local'
                        )
                        
                        results.append(result)
                
                return results[:top_k]
            
        except Exception as e:
            self.logger.error(f"Similar entity search failed: {str(e)}")
        
        return []
    
    def cross_domain_search(self, query: str, domains: List[str], max_results: int = 20) -> Dict[str, List[SearchResult]]:
        """Perform cross-domain search across multiple intelligence domains."""
        results = {}
        
        for domain in domains:
            # Create domain-specific search query
            domain_query = SearchQuery(
                query=query,
                search_type=SearchType.CROSS_DOMAIN_SEARCH,
                search_scope=SearchScope.GLOBAL,
                entity_types=[domain],
                max_results=max_results
            )
            
            domain_results = self.search(domain_query)
            results[domain] = domain_results
        
        return results
    
    def temporal_search(self, query: str, start_date: datetime, end_date: datetime, max_results: int = 50) -> List[SearchResult]:
        """Perform temporal search for events within a time range."""
        search_query = SearchQuery(
            query=query,
            search_type=SearchType.TEMPORAL_SEARCH,
            search_scope=SearchScope.GLOBAL,
            time_range=(start_date, end_date),
            max_results=max_results
        )
        
        return self.search(search_query)
    
    def graph_traversal_search(self, start_entity: str, max_depth: int = 3, relationship_types: Optional[List[str]] = None) -> List[SearchResult]:
        """Perform graph traversal search from a starting entity."""
        if not start_entity or start_entity not in self.entity_database:
            return []
        
        visited = set()
        results = []
        queue = [(start_entity, 0)]  # (entity_id, depth)
        
        while queue and len(results) < 100:  # Limit to prevent infinite loops
            current_entity, depth = queue.pop(0)
            
            if current_entity in visited or depth > max_depth:
                continue
            
            visited.add(current_entity)
            
            # Add current entity to results
            if current_entity in self.entity_database:
                result = SearchResult(
                    entity_id=current_entity,
                    entity_type=self.entity_database[current_entity].get('type', 'unknown'),
                    relevance_score=1.0 - (depth * 0.2),  # Decrease relevance with depth
                    match_type='graph_traversal',
                    content=self.entity_database[current_entity],
                    metadata={'depth': depth, 'traversal_path': True},
                    source='local'
                )
                results.append(result)
            
            # Find connected entities
            for rel_id, rel_data in self.relationship_database.items():
                if relationship_types and rel_data.get('type') not in relationship_types:
                    continue
                
                # Check if current entity is involved in this relationship
                connected_entity = None
                if rel_data.get('from_entity') == current_entity:
                    connected_entity = rel_data.get('to_entity')
                elif rel_data.get('to_entity') == current_entity:
                    connected_entity = rel_data.get('from_entity')
                
                if connected_entity and connected_entity not in visited:
                    queue.append((connected_entity, depth + 1))
        
        return results
    
    def get_search_statistics(self) -> Dict[str, Any]:
        """Get search engine statistics."""
        return {
            **self.search_stats,
            'entity_count': len(self.entity_database),
            'relationship_count': len(self.relationship_database),
            'intelligence_count': len(self.intelligence_database),
            'vector_index_size': self.vector_index.ntotal if self.vector_index else 0,
            'embedding_enabled': EMBEDDING_AVAILABLE,
            'mcp_enabled': MCP_AVAILABLE
        }
    
    def optimize_search_performance(self):
        """Optimize search performance by rebuilding indices."""
        if EMBEDDING_AVAILABLE:
            try:
                # Rebuild vector index
                self._initialize_vector_index()
                
                # Re-add all entities to vector index
                for entity_id, entity_data in self.entity_database.items():
                    content_text = self._extract_text_content(entity_data)
                    if content_text:
                        embedding = self.embedding_model.encode([content_text])[0]
                        self.vector_index.add(np.array([embedding]))
                        self.entity_id_map[self.vector_index.ntotal - 1] = entity_id
                
                self.logger.info("Search performance optimization completed")
                
            except Exception as e:
                self.logger.error(f"Search optimization failed: {str(e)}")


# Global semantic search engine instance
_semantic_search_engine = None


def get_semantic_search_engine(model_name: str = "all-MiniLM-L6-v2") -> SemanticSearchEngine:
    """
    Get or create the global semantic search engine instance.
    
    Args:
        model_name: Name of the sentence transformer model
        
    Returns:
        SemanticSearchEngine: Global search engine instance
    """
    global _semantic_search_engine
    
    if _semantic_search_engine is None:
        _semantic_search_engine = SemanticSearchEngine(model_name)
    
    return _semantic_search_engine


def search_entities(query: str, entity_types: Optional[List[str]] = None, max_results: int = 20) -> List[SearchResult]:
    """
    Convenience function to search for entities.
    
    Args:
        query: Search query
        entity_types: Optional list of entity types to filter by
        max_results: Maximum number of results
        
    Returns:
        List[SearchResult]: Search results
    """
    search_engine = get_semantic_search_engine()
    
    search_query = SearchQuery(
        query=query,
        search_type=SearchType.ENTITY_SEARCH,
        search_scope=SearchScope.GLOBAL,
        entity_types=entity_types,
        max_results=max_results
    )
    
    return search_engine.search(search_query)


def search_intelligence(query: str, max_results: int = 20) -> List[SearchResult]:
    """
    Convenience function to search intelligence data.
    
    Args:
        query: Search query
        max_results: Maximum number of results
        
    Returns:
        List[SearchResult]: Search results
    """
    search_engine = get_semantic_search_engine()
    
    search_query = SearchQuery(
        query=query,
        search_type=SearchType.INTELLIGENCE_SEARCH,
        search_scope=SearchScope.GLOBAL,
        max_results=max_results
    )
    
    return search_engine.search(search_query)


def search_relationships(query: str, relationship_types: Optional[List[str]] = None, max_results: int = 20) -> List[SearchResult]:
    """
    Convenience function to search for relationships.
    
    Args:
        query: Search query
        relationship_types: Optional list of relationship types to filter by
        max_results: Maximum number of results
        
    Returns:
        List[SearchResult]: Search results
    """
    search_engine = get_semantic_search_engine()
    
    search_query = SearchQuery(
        query=query,
        search_type=SearchType.RELATIONSHIP_SEARCH,
        search_scope=SearchScope.GLOBAL,
        relationship_types=relationship_types,
        max_results=max_results
    )
    
    return search_engine.search(search_query)


def add_entity_to_search(entity_id: str, entity_data: Dict[str, Any]):
    """
    Add entity to search engine database.
    
    Args:
        entity_id: Entity identifier
        entity_data: Entity data
    """
    search_engine = get_semantic_search_engine()
    search_engine.add_entity(entity_id, entity_data)


def add_intelligence_to_search(intel_id: str, intel_data: Dict[str, Any]):
    """
    Add intelligence data to search engine database.
    
    Args:
        intel_id: Intelligence identifier
        intel_data: Intelligence data
    """
    search_engine = get_semantic_search_engine()
    search_engine.add_intelligence_data(intel_id, intel_data)


# Example usage and testing
if __name__ == "__main__":
    # Test semantic search engine
    search_engine = SemanticSearchEngine()
    
    # Add test entities
    test_entities = {
        "openai": {
            "name": "OpenAI",
            "type": "corporation",
            "description": "AI research company developing GPT models",
            "threat_level": "high",
            "observations": ["Large language models", "AI safety research", "Commercial AI products"]
        },
        "sam_altman": {
            "name": "Sam Altman",
            "type": "person",
            "description": "CEO of OpenAI, former president of Y Combinator",
            "threat_level": "high",
            "observations": ["Tech entrepreneur", "AI advocate", "Y Combinator alumnus"]
        },
        "anthropic": {
            "name": "Anthropic",
            "type": "corporation",
            "description": "AI safety company developing Claude AI assistant",
            "threat_level": "medium",
            "observations": ["Constitutional AI", "AI safety research", "Large language models"]
        }
    }
    
    # Add entities to search engine
    for entity_id, entity_data in test_entities.items():
        search_engine.add_entity(entity_id, entity_data)
    
    # Test different search types
    print("Testing entity search:")
    results = search_entities("AI research company", max_results=5)
    for result in results:
        print(f"  {result.entity_id}: {result.relevance_score:.3f} ({result.match_type})")
    
    print("\nTesting semantic similarity search:")
    if test_entities:
        similar_entities = search_engine.search_similar_entities("openai", top_k=3)
        for result in similar_entities:
            print(f"  {result.entity_id}: {result.relevance_score:.3f}")
    
    print("\nTesting cross-domain search:")
    domains = ["corporation", "person"]
    cross_results = search_engine.cross_domain_search("AI development", domains, max_results=3)
    for domain, results in cross_results.items():
        print(f"  {domain}: {len(results)} results")
    
    # Test statistics
    stats = search_engine.get_search_statistics()
    print(f"\nSearch engine statistics:")
    print(f"  Entities: {stats['entity_count']}")
    print(f"  Relationships: {stats['relationship_count']}")
    print(f"  Intelligence: {stats['intelligence_count']}")
    print(f"  Total searches: {stats['total_searches']}")
    
    print("Semantic search engine testing completed.")
