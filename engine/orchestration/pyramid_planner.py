"""Stage-4 pyramid planning shim."""

from __future__ import annotations

from engine.orchestration.pipeline import AtelierConfig, stage4_pyramid


def build_pyramid_plan(cfg: AtelierConfig, family: str) -> object:
    """Compute the phase-4 OAV pyramid blueprint for this config + family."""
    return stage4_pyramid(cfg, family)


__all__ = ["build_pyramid_plan"]
