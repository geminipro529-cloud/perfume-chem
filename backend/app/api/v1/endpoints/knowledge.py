"""Knowledge retrieval API endpoints: semantic search over perfume knowledge base."""

import sys
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel, Field

# Add project root to path so engine module is importable
_project_root = str(Path(__file__).resolve().parent.parent.parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from engine.knowledge import KnowledgeIndex

from app.services.validation_pipeline import validate_search_query

router = APIRouter()

# Singleton index instance
_index: KnowledgeIndex | None = None


def _get_index() -> KnowledgeIndex:
    global _index
    if _index is None:
        _index = KnowledgeIndex()
        _index.build()  # loads existing or builds
    return _index


class SearchRequest(BaseModel):
    query: str = Field(..., description="Natural language query")
    k: int = Field(5, ge=1, le=20, description="Number of results")
    include_context: bool = Field(False, description="Include surrounding chunks")


class SearchResult(BaseModel):
    text: str
    source: str
    chunk_idx: int
    score: float
    context_before: str = ""
    context_after: str = ""


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]


class BuildResponse(BaseModel):
    n_files: int
    n_chunks: int
    index_path: str
    status: str


@router.post("/search", response_model=SearchResponse)
def search_knowledge(body: SearchRequest):
    """Semantic search over the perfume knowledge base."""
    validate_search_query(body.query)
    idx = _get_index()
    if body.include_context:
        results = idx.search_with_context(body.query, k=body.k)
    else:
        results = idx.search(body.query, k=body.k)
    return {"query": body.query, "results": results}


@router.post("/rebuild", response_model=BuildResponse)
def rebuild_index():
    """Rebuild the knowledge index from source files."""
    global _index
    _index = KnowledgeIndex()
    return _index.build(force=True)
