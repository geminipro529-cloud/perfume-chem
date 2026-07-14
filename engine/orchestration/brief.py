"""Stage 1 — Brief Translation.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**
**RULE 3: Optimize for the name, not just the numbers.**

Translates a perfume name + free-text brief into structured formulation choices:
  - Material anchors (the 3-5 defining materials for the concept)
  - OAV target range (how strong the formula should smell)
  - Family candidates (which Edwards sub-families fit)
  - Character keywords (the perfumery vocabulary)
  - Forbidden materials (the anti-patterns)
  - Methodology suggestion (which of 10 construction methods to use)
  - Pinned notes (materials the user insists on)

Re-exports the existing brief-translation logic from `future_modules.brief_translation`
so the pipeline can import from the canonical `engine.orchestration` namespace.

**Inspired by:**
- Osmo Inspire (text → POM → sample)
- Sniff-AI (ksek87/sniff_ai): NER + TF-IDF on 13,644 fragrances
- Carles pyramid + Roudnitska material anchors

**Reference:** docs/ATELIER_PIPELINE_PLAN.md, Stage 1.
"""

from __future__ import annotations

from future_modules.brief_translation import (  # type: ignore[import-not-found]
    BRIEF_TRANSLATIONS,
    MATERIAL_EMOTION_MAP,
    BriefTranslation,
    ConceptStrip,
    build_concept_strip,
    find_materials_by_emotion,
    generate_constraints,
    get_all_brief_translations,
    get_emotions_for_material,
    translate_brief,
    translate_brief_element,
)

__all__ = [
    "BRIEF_TRANSLATIONS",
    "MATERIAL_EMOTION_MAP",
    "BriefTranslation",
    "ConceptStrip",
    "build_concept_strip",
    "find_materials_by_emotion",
    "generate_constraints",
    "get_all_brief_translations",
    "get_emotions_for_material",
    "translate_brief",
    "translate_brief_element",
]
