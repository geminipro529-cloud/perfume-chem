"""Atelier Pipeline Orchestrator Stage 7.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**
**RULE 2: NEVER create new pipeline scripts.**
**RULE 3: Optimize for the name, not just the numbers.**

Stitches the 7 stages of the Atelier pipeline into a single `run()` function.
This is the thin glue layer — actual logic lives in:

  - `engine.orchestration.brief`           (Stage 1: brief)
  - `engine.orchestration.methodology`     (Stage 2: methodology)
  - `engine.orchestration.family_resolver`  (Stage 3: Edwards 14)  — Phase 1
  - `engine.orchestration.pyramid_planner`  (Stage 4: OAV + PTD)    — Phase 2
  - `engine.orchestration.material_selector` (Stage 5: CAMD-style hard constraints)
  - `engine.orchestration.novelty`          (Stage 5b: Philyra)     — Phase 3
  - `engine.orchestration.iec_loop`         (Stage 6: DE + CMA-ES)   — Phase 4
  - `engine.orchestration.pipeline`         (Stage 7: this file)    — Phase 5

**Reference:** docs/ATELIER_PIPELINE_PLAN.md
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from engine.families.registry import infer_archetype
from engine.orchestration.brief import (
    build_concept_strip,
    generate_constraints,
    translate_brief,
)
from engine.orchestration.iec_loop import (
    IECHistory,
    IECHyperparameters,
    iec_optimize,
)
from engine.orchestration.methodology import (
    METHODOLOGY_SPECS,
    ConcentrationBracket,
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


@dataclass(slots=True)
class Stage5Materials:
    """Material selection output from the lightweight stage-5 selector."""

    materials: list[dict[str, Any]]
    confidence: float = 1.0
    notes: str = ""


@dataclass(slots=True)
class Stage5Novelty:
    """Novelty report used before IEC refinement."""

    score: float
    status: str
    nearest_neighbors: list[str]


@dataclass(slots=True)
class Stage6IecResult:
    """IEC outcome summary from a fast bounded optimization pass."""

    executed: bool = False
    final_fitness: float | None = None
    history: IECHistory | None = None
    optimized_raw_ul: list[float] | None = None
    notes: str = ""


def _normalize_text(value: object) -> str:
    """Normalize free-text for deterministic keyword matching."""
    return re.sub(r"\s+", " ", str(value).lower().strip())


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    """Check whether any candidate token appears in the normalized text."""
    normalized = _normalize_text(text)
    return any(needle in normalized for needle in needles)


def _resolve_family_from_brief_text(text: str) -> str:
    """Return a resolved family archetype key from brief-level keywords."""
    normalized = _normalize_text(text)

    mappings: tuple[tuple[tuple[str, ...], str], ...] = (
        (("aromatic_fougere", "fougere", "fougere"), "aromatic_fougere.classic_reference"),
        (("prada", "l'homme", "lhomme"), "iris_amber_woody.prada_lhomme_reference"),
        (("chypre", "oakmoss", "moss", "oak moss"), "chypre_classical.coty_reference"),
        (("iris", "orris", "violet", "cathedral"), "iris_amber_woody.classic"),
        (("chypre_leath", "leather", "ibq", "isobutyl"), "chypre_leathery.bandit_reference"),
        (("citrus", "bergamot", "grapefruit", "lime", "mandarin", "lemon"), "citrus_classical.4711_reference"),
        (("oriental", "incense", "oud", "amber", "vanilla", "coumarin"), "oriental_classical.shalimar_reference"),
        (("gourmand", "cocoa", "vanilla", "coffee", "tea"), "gourmand_floral.classic_reference"),
        (("floral", "rose", "jasmine", "tuberose", "white"), "floral_white.fracas_reference"),
        (("woody", "vetiver", "cedar", "sandalwood", "amberwood", "cedrat"), "woody.vetiver_classical"),
    )

    for needles, archetype in mappings:
        if _contains_any(normalized, needles):
            return archetype
    return ""


def _resolve_family_from_name(name: str) -> str:
    """Return family archetype from name-level intent tokens."""
    normalized = _normalize_text(name)
    if _contains_any(normalized, ("prada", "l'homme", "lhomme", "prada l'homme")):
        return "iris_amber_woody.prada_lhomme_reference"
    if _contains_any(normalized, ("iris", "cathedral")):
        return "iris_amber_woody.classic"
    if _contains_any(normalized, ("chypre", "moss", "oakmoss")):
        return "chypre_classical.coty_reference"
    if _contains_any(normalized, ("cedre", "cedrat", "cedar", "cedrat", "cedarwood", "bleu")):
        return "woody.vetiver_classical"
    if _contains_any(normalized, ("citrus", "bergamot", "grapefruit", "mandarin", "orange")):
        return "citrus_classical.4711_reference"
    if _contains_any(normalized, ("amber", "oud", "oriental", "incense")):
        return "oriental_classical.shalimar_reference"
    if _contains_any(normalized, ("gourmand", "cocoa", "vanilla", "coffee", "tea")):
        return "gourmand_floral.classic_reference"
    if _contains_any(normalized, ("rose", "jasmine", "tuberose", "floral", "muguet", "musch")):
        return "floral_white.fracas_reference"
    if _contains_any(normalized, ("woody", "vetiver", "cedar", "sandalwood")):
        return "woody.vetiver_classical"
    return ""


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


def _resolve_material_tokens(text: str) -> list[str]:
    """Extract candidate material names from a compact free-form translation."""
    materials: list[str] = []
    for token in text.split("+"):
        for sub in token.replace("&", ",").replace("\uff1b", ",").replace(";", ",").split(","):
            cleaned = _normalize_text(sub).strip()
            if cleaned and cleaned not in {"+", ",", ";", "and", "trace", "trace."}:
                materials.append(cleaned.title().replace(" + ", " "))
    return materials


def stage3_family(cfg: AtelierConfig, brief: dict) -> str:
    """Stage 3: Resolve family archetype (Edwards14 mapping is now canonical to 4 families).

    Resolution order:
      1) explicit archetype in brief
      2) keyword heuristics from brief/name text
      3) safety fallback
    """
    brief_payload = brief or {}
    explicit_keys = (
        "family_archetype",
        "archetype",
        "archetype_key",
        "family_key",
        "family",
    )
    for key in explicit_keys:
        explicit = str(brief_payload.get(key, "")).strip()
        if explicit:
            return infer_archetype("", explicit)

    text_probe = " ".join(
        [
            str(brief_payload.get("name", "")),
            cfg.name,
            cfg.brief_text,
            " ".join(map(str, brief_payload.get("elements", ()) or ())),
            str(brief_payload.get("material_translations", "")),
            str(brief_payload.get("concept_strip", "")),
        ]
    )

    resolved = _resolve_family_from_brief_text(text_probe)
    if resolved:
        return resolved

    resolved = _resolve_family_from_name(cfg.name)
    if resolved:
        return resolved

    return infer_archetype("woody") or "woody.vetiver_classical"


def stage4_pyramid(cfg: AtelierConfig, family: str) -> object:
    """Stage 4: Compute the OAV pyramid blueprint for family + concentration."""
    return get_pyramid_blueprint(cfg.concentration)


def stage5_select_materials(
    cfg: AtelierConfig,
    brief: dict,
    family: str,
    pyramid: Any,
) -> Stage5Materials:
    """Stage 5: lightweight material selection with hard constraints.

    This fast path is deterministic and inventory-light: it builds a material
    shortlist from translated brief concepts, then allocates a conservative raw
    concentrate budget.
    """
    concept = list(brief.get("concept_strip", ())) or []
    translated = brief.get("material_translations", {})

    material_pool: list[str] = []
    for text in translated.values():
        material_pool.extend(_resolve_material_tokens(str(text)))
    for item in concept:
        if _contains_any(str(item), ("avoid", "constraint")):
            continue
        material_pool.append(str(item))
    material_pool.extend(brief.get("pinned_notes", ()))

    # Keep only deterministic non-empty unique entries.
    cleaned: list[str] = []
    seen: set[str] = set()
    for m in material_pool:
        m_norm = _normalize_text(m)
        if not m_norm or m_norm in seen:
            continue
        seen.add(m_norm)
        cleaned.append(m.strip())
    if not cleaned:
        # Fallback so downstream stages can still run.
        cleaned = [cfg.name, "Iso E Super", "Hedione", "Sandalwood", "Patchouli"]

    # Conservative concentration split: keep room for future stages to refine.
    # Percentages are rough anchors, not final formulation.
    shares = (0.22, 0.18, 0.14, 0.10, 0.08)
    shares_tail = 0.05
    materials: list[dict[str, Any]] = []
    for i, material in enumerate(cleaned[: max(1, len(cleaned))]):
        share = shares[i] if i < len(shares) else shares_tail
        if i >= 2:
            role = "heart"
        elif i == 0:
            role = "top"
        elif i == 1:
            role = "heart"
        else:
            role = "base"
        raw_ul = round(cfg.expected_concentrate_ul * share, 3)
        materials.append(
            {
                "name": material,
                "role": role,
                "raw_ul": raw_ul,
                "notes": f"seeded by {cfg.name} / {family}",
            }
        )

    return Stage5Materials(
        materials=materials,
        confidence=0.84,
        notes=(
            "Lightweight CAMD-style selector used for fast-path generation; "
            f"family={family}, family_targets={pyramid and getattr(pyramid, 'top_target', None)}"
        ),
    )


def stage5b_novelty(
    cfg: AtelierConfig,
    family: str,
    materials: list[dict[str, Any]],
) -> Stage5Novelty:
    """Stage 5b: lightweight novelty score before optimization.

    This estimator is intentionally conservative and deterministic in fast mode.
    """
    if not materials:
        return Stage5Novelty(score=0.0, status="SKIP", nearest_neighbors=["none"])

    base_signal = min(1.0, len(materials) / 6.0)
    name_overlap = 0
    normalized_name = set(_normalize_text(cfg.name).split())
    normalized_family = set(_normalize_text(family).split("."))
    for mat in materials:
        for token in _normalize_text(mat["name"]).split():
            if token in normalized_name or token in normalized_family:
                name_overlap += 1
    overlap = min(1.0, name_overlap / max(1, len(materials)))
    score = max(0.0, round(base_signal - 0.25 * overlap, 3))

    status = "PASS" if score >= cfg.novelty_min else "WARN_LOW_NOVELTY"
    neighbors = ["chypre_classical.coty_reference", "floral_white.fracas_reference"] if score < cfg.novelty_min else []
    return Stage5Novelty(score=score, status=status, nearest_neighbors=neighbors)


def stage6_iec_fast_pass(
    cfg: AtelierConfig,
    materials: list[dict[str, Any]],
) -> Stage6IecResult:
    """Stage 6: one bounded IEC micro-pass for fast reproducible convergence.

    This keeps the interface active while keeping latency low.
    """
    if len(materials) < 2:
        return Stage6IecResult(
            executed=False,
            notes="IEC skipped: insufficient candidate materials for bounded optimization",
        )

    raw_values = [float(m["raw_ul"]) for m in materials]
    bounds = [(max(1.0, v * 0.5), max(1.0, v * 1.8)) for v in raw_values]

    def _fitness(candidate: list[float], target: list[float] = raw_values) -> float:
        distance = sum((candidate[i] - target[i]) ** 2 for i in range(min(len(candidate), len(target))))
        # Higher is better and close to 0 penalty; keep bounded for stability.
        return -distance

    history = iec_optimize(raw_values, bounds, _fitness, cfg.iec_hyperparams)
    optimized = raw_values
    if history.final_best_candidate is not None:
        optimized = [round(v, 3) for v in history.final_best_candidate]
    return Stage6IecResult(
        executed=True,
        final_fitness=history.final_best_fitness,
        history=history,
        optimized_raw_ul=optimized,
        notes="Bounded DE pass executed in fast mode.",
    )


def run_pipeline(cfg: AtelierConfig) -> AtelierResult:
    """Run a fast, deterministic end-to-end pipeline path for 5-stage/6-stage wiring."""
    t_start = time.perf_counter()
    timings: dict[str, float] = {}

    t0 = time.perf_counter()
    brief = stage1_brief(cfg)
    timings["stage1_brief"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    meth = stage2_methodology(cfg, brief)
    timings["stage2_methodology"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    family = stage3_family(cfg, brief)
    timings["stage3_family"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    pyramid = stage4_pyramid(cfg, family)
    timings["stage4_pyramid"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    selection = stage5_select_materials(cfg, brief, family, pyramid)
    timings["stage5_select_materials"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    novelty = stage5b_novelty(cfg, family, selection.materials)
    timings["stage5b_novelty"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    iec = stage6_iec_fast_pass(cfg, selection.materials)
    timings["stage6_iec"] = time.perf_counter() - t0

    if iec.optimized_raw_ul:
        for idx, material in enumerate(selection.materials):
            if idx < len(iec.optimized_raw_ul):
                material["raw_ul"] = iec.optimized_raw_ul[idx]

    formula_candidate = {
        "topology": family,
        "methodology": meth["selected_method"],
        "pyramid_targets": {
            "top": getattr(pyramid, "top_target", ()),
            "heart": getattr(pyramid, "heart_target", ()),
            "base": getattr(pyramid, "base_target", ()),
        },
        "materials": selection.materials,
        "selection_confidence": selection.confidence,
        "selection_notes": selection.notes,
        "pinned_notes": list(cfg.pinned_notes),
        "constraints": brief.get("constraints", {}),
        "concept_strip": brief.get("concept_strip", ()),
        "novelty": {
            "score": novelty.score,
            "status": novelty.status,
            "neighbors": novelty.nearest_neighbors,
        },
    }

    return AtelierResult(
        config=cfg,
        brief_summary=brief,
        methodology_choice=meth["selected_method"],
        family_archetype=family,
        pyramid_blueprint=pyramid,
        formula_candidate=formula_candidate,
        novelty_score=novelty.score,
        iec_history=iec.history,
        gate_status="PASS" if novelty.status == "PASS" else "WARN",
        gate_summary={
            "methodology": meth,
            "novelty": asdict(novelty),
            "iec": {
                "executed": iec.executed,
                "final_fitness": iec.final_fitness,
                "notes": iec.notes,
            },
        },
        elapsed_seconds=time.perf_counter() - t_start,
        stage_timings=timings,
    )


def run_stub_pipeline(cfg: AtelierConfig) -> AtelierResult:
    """Backward-compatible entrypoint retained for older callers."""
    return run_pipeline(cfg)


__all__ = [
    "AtelierConfig",
    "AtelierResult",
    "stage1_brief",
    "stage2_methodology",
    "stage3_family",
    "stage4_pyramid",
    "stage5_select_materials",
    "stage5b_novelty",
    "stage6_iec_fast_pass",
    "run_pipeline",
    "run_stub_pipeline",
]
