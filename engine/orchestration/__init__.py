"""Atelier Pipeline — generative perfume creation orchestrator.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**
**RULE 2: NEVER create new pipeline scripts.**
**RULE 3: Optimize for the name, not just the numbers.**

The 7-stage generative pipeline that creates an amazing perfume from a name:

  [1] BRIEF ─► [2] METHODOLOGY ─► [3] FAMILY (Edwards 14 → 4 mapping)
          ─► [4] OAV PYRAMID + PTD preview (matplotlib)
          ─► [5] MATERIAL SELECTION (CAMD-style hard constraints)
          ─► [5b] NOVELTY CHECK (OAV-space distance vs 214 formulas)
          ─► [6] IEC (sequential DE; CMA-ES fallback; auto-only default)
          ─► [7] GATE + DIAGNOSIS + ARCHIVE (existing pipeline)

Stage 1 (brief) and Stage 2 (methodology) shims are wired in `engine.orchestration.brief`
and `engine.orchestration.methodology`. The IEC loop (Stage 6) is in
`engine.orchestration.iec_loop`.

**Reference:** docs/ATELIER_PIPELINE_PLAN.md
"""

from __future__ import annotations

from engine.orchestration.brief import (  # noqa: F401
    BRIEF_TRANSLATIONS,
    ConceptStrip,
    build_concept_strip,
    generate_constraints,
    get_all_brief_translations,
    translate_brief,
)
from engine.orchestration.iec_loop import (  # noqa: F401
    IECHyperparameters,
    IECHistory,
    iec_optimize,
    roudnitska_test,
)
from engine.orchestration.methodology import (  # noqa: F401
    METHODOLOGY_SPECS,
    evaluate_pyramid_balance,
    get_pyramid_blueprint,
)

__all__ = [
    "BRIEF_TRANSLATIONS",
    "ConceptStrip",
    "IECHyperparameters",
    "IECHistory",
    "METHODOLOGY_SPECS",
    "build_concept_strip",
    "evaluate_pyramid_balance",
    "generate_constraints",
    "get_all_brief_translations",
    "get_pyramid_blueprint",
    "iec_optimize",
    "roudnitska_test",
    "translate_brief",
]
