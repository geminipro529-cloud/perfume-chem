"""engine.ingestion — generic external reconstruction candidate ingestion adapter.

Canonical interchange socket (deterministic JSON/JSONL, XLSX-free). Additive,
read-only w.r.t. domain models: it validates + normalizes into canonical interchange
and structured rejection; it never mutates formulas, inventory, or empirical state.
"""

from .ingest import IngestionResult, canonical_json, deterministic_hash, ingest_external_candidate
from .schema import SCHEMA_VERSION, StructuredRejection

__all__ = [
    "IngestionResult",
    "StructuredRejection",
    "canonical_json",
    "deterministic_hash",
    "ingest_external_candidate",
    "SCHEMA_VERSION",
]
