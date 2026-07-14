"""Knowledge retrieval engine: vector embeddings + semantic search + perfume taxonomy.

Uses sentence-transformers for embeddings and FAISS for fast similarity search.
Falls back to keyword search if sentence-transformers is not installed.

Submodules:
    perfume_taxonomy  — complete fragrance family/subfamily hierarchy
    accord_library    — 37+ verified accord recipes with material ratios
    soliflore_structures — 19 single-flower perfume templates
    pyramid_targets   — per-family top/heart/base ratios and OAV targets
    perfume_knowledge — unified API bridging all knowledge to the pipeline
"""

from .embeddings import KnowledgeIndex

__all__ = ["KnowledgeIndex"]
