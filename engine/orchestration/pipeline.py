"""Atelier Pipeline Orchestrator — Stage 7.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**
**RULE 2: NEVER create new pipeline scripts.**
**RULE 3: Optimize for the name, not just the numbers.**

Stitches the 7 stages of the Atelier pipeline into a single `run()` function.
This is the thin glue layer — actual logic lives in:

  - `engine.orchestration.brief`           (Stage 1: brief)
  - `engine.orchestration.methodology`     (Stage 2: methodology)
  - `engine.orchestration.family_resolver` (Stage 3: Edwards 14)  — Phase 1
  - `engine.orchestration.pyramid_planner` (Stage 4: OAV + PTD)   — Phase 2
  - `engine.orchestration.material_selector` (Stage 5: CAMD)      — Phase 3
  - `engine.orchestration.novelty`         (Stage 5b: Philyra)    — Phase 3
  - `engine.orchestration.iec_loop`        (Stage 6: DE + CMA-ES) — Phase 4
  - `engine.orchestration.pipeline`        (Stage 7: this file)   — Phase 5

**Reference:** docs/ATELIER_PIPELINE_PLAN.md
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Sequence

from engine.orchestration.brief import (
    BRIEF_TRANSLATIONS,
    build_concept_strip,
    generate_constraints,
    translate_brief,
)
from engine.orchestration.iec_loop import (
    IECHyperparameters,
    IECHistory,
    iec_optimize,
    roudnitska_test,
)
from engine.orchestration.methodology import (
    METHODOLOGY_SPECS,
    ConcentrationBracket,
    METHODOLOGY_SPECS as _MS,  # alias for forward reference
    evaluate_pyramid_balance,
    get_pyramid_blueprint,
)


@dataclass(slots=True)
class AtelierConfig:
    """User-facing configuration for the Atelier pipeline."""

    name: str
    brief_text: str = ""
    brief_json_path: str | None = None
    pinned_notes: tuple[str, ...] = ()
    concentration: ConcentrationBracket = ConcentrationBracket.EDP
    batch_volume_ml: float = 30.0
    expected_concentrate_ul: float = 6000.0
    interactive: bool = False
    creative: bool = False
    novelty_min: float = 0.3
    output_dir: str = r"D:\chatbots\perfume-chem\formulas\complete"
    iec_hyperparams: IECHyperparameters = field(default_factory=IECHyperparameters)


@dataclass(slots=True)
class AtelierResult:
    """Result of running the Atelier pipeline."""

    config: AtelierConfig
    brief_summary: dict = field(default_factory=dict)
    methodology_choice: str = ""
    family_archetype: str = ""
    pyramid_blueprint: object = None
    formula_candidate: dict = field(default_factory=dict)
    novelty_score: float = 0.0
    iec_history: IECHistory | None = None
    gate_status: str = "PENDING"
    gate_summary: dict = field(default_factory=dict)
    final_formula_path: str = ""
    elapsed_seconds: float = 0.0
    stage_timings: dict = field(default_factory=dict)


def stage1_brief(cfg: AtelierConfig) -> dict:
    """Stage 1: Translate name + free-text into a structured brief.

    Pure data — no model call. Returns the brief dict.
    """
    brief = {
        "name": cfg.name,
        "concentration": cfg.concentration.value,
        "batch_volume_ml": cfg.batch_volume_ml,
        "expected_concentrate_ul": cfg.expected_concentrate_ul,
        "pinned_notes": list(cfg.pinned_notes),
    }
    if cfg.brief_json_path:
        with open(cfg.brief_json_path, encoding="utf-8") as f:
            loaded = json.load(f)
        brief.update(loaded)
    elif cfg.brief_text:
        elements = [e.strip() for e in cfg.brief_text.split(",") if e.strip()]
        brief["elements"] = elements
        brief["material_translations"] = translate_brief(elements)
        brief["concept_strip"] = list(build_concept_strip(elements))
        brief["constraints"] = generate_constraints(elements)
    return brief


def stage2_methodology(cfg: AtelierConfig, brief: dict) -> dict:
    """Stage 2: Select a construction methodology from the 10 options.

    Pure data — no model call. Returns the methodology dict.
    """
    score_map: dict[str, float] = {}
    elements = brief.get("elements", [])
    elements_text = " ".join(elements).lower() if elements else ""

    for spec in METHODOLOGY_SPECS:
        s = 0.0
        if any(kw in elements_text for kw in ("minimalist", "transparent", "ellena")):
            if "Texture-First" in spec.name or "Minimum-Material" in spec.name or "Single-Material" in spec.name:
                s += 0.4
        if any(kw in elements_text for kw in ("hedonic", "computational")):
            if "Hedonic" in spec.name:
                s += 0.4
        if any(kw in elements_text for kw in ("cost", "commercial", "mass")):
            if "Cost-Optimized" in spec.name or "Constraint-Based" in spec.name:
                s += 0.4
        if any(kw in elements_text for kw in ("performance", "projection", "sillage", "long")):
            if "Performance-First" in spec.name:
                s += 0.4
        if any(kw in elements_text for kw in ("regulatory", "safe", "ifra")):
            if "Constraint-Based" in spec.name:
                s += 0.4
        if not elements:
            if "Pyramid" in spec.name:
                s += 0.3
        s += 0.1
        score_map[spec.name] = s

    sorted_methods = sorted(score_map.items(), key=lambda kv: -kv[1])
    chosen_name = sorted_methods[0][0]
    alternatives = [name for name, _ in sorted_methods[1:4]]
    return {
        "selected_method": chosen_name,
        "selected_score": sorted_methods[0][1],
        "alternatives": alternatives,
        "all_scores": dict(sorted_methods),
    }


def stage3_family_placeholder(cfg: AtelierConfig, brief: dict) -> str:
    """Stage 3: Family resolution (Edwards 14 → 4 mapping).

    Phase 1: keyword-based stub. Phase 1 full implementation will use
    `engine.families.registry.infer_archetype()` + the new Edwards 14 mapping.
    """
    elements_text = " ".join(brief.get("elements", [])).lower()
    name_lower = cfg.name.lower()

    if any(kw in elements_text or kw in name_lower for kw in ("iris", "cathedral", "violet", "orris")):
        return "WOODY_AMBER"  # iris = orris = woody/amber
    if any(kw in elements_text or kw in name_lower for kw in ("chypre", "mossy", "oakmoss")):
        return "CHYPRE"
    if any(kw in elements_text or kw in name_lower for kw in ("fougère", "lavender", "aromatic")):
        return "AROMATIC_FOUGERE"
    if any(kw in elements_text or kw in name_lower for kw in ("oriental", "amber", "incense", "opulent")):
        return "AMBER_ORIENTAL"
    if any(kw in elements_text or kw in name_lower for kw in ("woody", "cedar", "sandalwood", "vetiver", "bleu")):
        return "WOODY_AMBER"
    if any(kw in elements_text or kw in name_lower for kw in ("citrus", "bergamot", "fresh", "aqua")):
        return "CITRUS"
    if any(kw in elements_text or kw in name_lower for kw in ("rose", "jasmine", "floral", "tuberose")):
        return "FLORAL_ROSE"
    return "WOODY_AMBER"


def stage4_pyramid(cfg: AtelierConfig, family: str) -> object:
    """Stage 4: Compute the OAV pyramid blueprint for the family + concentration.

    Phase 2 full implementation will add PTD previews and per-slot material templates.
    """
    return get_pyramid_blueprint(cfg.concentration)


def run_stub_pipeline(cfg: AtelierConfig) -> AtelierResult:
    """Run the stub version of the Atelier pipeline (Phases 0-1 only).

    Stages 5-6 (material selection, novelty, IEC) are stubs that return placeholder
    data. The full implementation lands in Phases 3-4.
    """
    t_start = time.perf_counter()
    timings: dict = {}

    t0 = time.perf_counter()
    brief = stage1_brief(cfg)
    timings["stage1_brief"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    meth = stage2_methodology(cfg, brief)
    timings["stage2_methodology"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    family = stage3_family_placeholder(cfg, brief)
    timings["stage3_family"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    pyramid = stage4_pyramid(cfg, family)
    timings["stage4_pyramid"] = time.perf_counter() - t0

    return AtelierResult(
        config=cfg,
        brief_summary=brief,
        methodology_choice=meth["selected_method"],
        family_archetype=family,
        pyramid_blueprint=pyramid,
        formula_candidate={
            "note": "Phase 0-1 stub: Stages 5-7 not yet implemented",
            "pyramid_targets": {
                "top": pyramid.top_target,
                "heart": pyramid.heart_target,
                "base": pyramid.base_target,
            },
            "methodology": meth["selected_method"],
            "family": family,
        },
        novelty_score=0.0,
        iec_history=None,
        gate_status="PENDING",
        elapsed_seconds=time.perf_counter() - t_start,
        stage_timings=timings,
    )


__all__ = [
    "AtelierConfig",
    "AtelierResult",
    "stage1_brief",
    "stage2_methodology",
    "stage3_family_placeholder",
    "stage4_pyramid",
    "run_stub_pipeline",
]
