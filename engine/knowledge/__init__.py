"""Knowledge retrieval engine: vector embeddings + semantic search.

Uses sentence-transformers for embeddings and FAISS for fast similarity search.
Falls back to keyword search if sentence-transformers is not installed.
"""

from .embeddings import KnowledgeIndex

__all__ = ["KnowledgeIndex"]
