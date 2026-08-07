"""Stage-5b novelty shim."""

from __future__ import annotations

from engine.orchestration.pipeline import AtelierConfig, Stage5Novelty, stage5b_novelty


def assess_novelty(cfg: AtelierConfig, family: str, materials: list[dict]) -> Stage5Novelty:
    """Compute lightweight novelty signal for a candidate material set."""
    return stage5b_novelty(cfg, family, materials)


__all__ = ["assess_novelty"]
