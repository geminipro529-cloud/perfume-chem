"""Stage-3 family resolution shim.

Thin wrapper over :mod:`engine.orchestration.pipeline` so callers can import a
dedicated family resolver module without coupling to orchestration internals.
"""

from __future__ import annotations

from engine.orchestration.pipeline import AtelierConfig, stage3_family


def resolve_family(cfg: AtelierConfig, brief: dict) -> str:
    """Resolve a family archetype key for the provided brief."""
    return stage3_family(cfg, brief)


__all__ = ["resolve_family"]
