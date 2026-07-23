"""Multi-objective formula optimizer engine.

SciPy-backed OAV objective exports stay lazy so importing a lightweight
optimizer submodule does not initialize SciPy.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

from .models import (
    FormulaVector,
    ObjectiveWeights,
    OptimizationConstraints,
    OptimizationResult,
)
from .optimizer import FormulaOptimizer
from .scoring import FormulaScorer

if TYPE_CHECKING:
    from .oav_objective import (
        OAVObjective,
        differential_evolution_oav,
        score_formula_oav,
    )


__all__ = [
    "FormulaVector",
    "ObjectiveWeights",
    "OptimizationConstraints",
    "OptimizationResult",
    "FormulaScorer",
    "FormulaOptimizer",
    "OAVObjective",
    "score_formula_oav",
    "differential_evolution_oav",
]

_LAZY_EXPORTS = {
    "OAVObjective": (".oav_objective", "OAVObjective"),
    "score_formula_oav": (".oav_objective", "score_formula_oav"),
    "differential_evolution_oav": (
        ".oav_objective",
        "differential_evolution_oav",
    ),
}


def __getattr__(name: str) -> Any:
    try:
        module_name, attribute_name = _LAZY_EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    value = getattr(import_module(module_name, __name__), attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
