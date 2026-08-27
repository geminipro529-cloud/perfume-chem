"""Stage-5 material selection shim.

The current implementation uses deterministic, conservative shortlisting from the
resolved brief and family context.
"""

from __future__ import annotations

from engine.orchestration.pipeline import AtelierConfig, Stage5Materials, stage5_select_materials


def select_materials(cfg: AtelierConfig, brief: dict, family: str, pyramid: object) -> Stage5Materials:
    """Select candidate materials for a fast-path run."""
    return stage5_select_materials(cfg, brief, family, pyramid)


__all__ = ["select_materials"]
