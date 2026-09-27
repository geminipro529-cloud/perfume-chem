"""Activity-coefficient estimates for the canonical headspace model.

The production calculation currently uses a Hansen-distance
regular-solution-style heuristic. It is a useful non-ideal comparison model,
but it is not fitted to perfume headspace measurements and is not an
experimental activity coefficient.

UNIFAC requires a supported implementation, molecular subgroup assignments,
and interaction parameters for every mixture component. Those prerequisites
are reported explicitly; the code never claims that UNIFAC is active merely
because an optional package can be imported.
"""

from __future__ import annotations

import importlib.util
import math
from functools import lru_cache
from typing import Mapping, Sequence

_HAS_THERMO = importlib.util.find_spec("thermo") is not None
_UNIFAC_IMPLEMENTED = False

# Default Hansen solubility parameters (delta_D, delta_P, delta_H, MPa^0.5).
_HSP_ETHANOL = (15.8, 8.8, 19.4)
_HSP_WATER = (15.5, 16.0, 42.3)
_HSP_DEFAULT_FRAGRANCE = (17.0, 4.0, 6.0)


def activity_model_capabilities() -> dict[str, object]:
    """Return the executable activity-model boundary without loading providers."""
    return {
        "selected_model": "hansen_distance_regular_solution_heuristic",
        "selected_model_authority": "HEURISTIC_UNCALIBRATED",
        "thermo_library_available": _HAS_THERMO,
        "unifac_implemented": _UNIFAC_IMPLEMENTED,
        "unifac_active": False,
        "unifac_requirements": [
            "supported UNIFAC implementation and parameter version",
            "molecular subgroup assignments for every mixture component",
            "interaction parameters covering every subgroup pair",
            "formula-domain validation against measured VLE or headspace data",
        ],
        "ideal_gamma_authority": "COMPARISON_SCENARIO_ONLY",
        "release_authority": False,
    }


def _hansen_distance_sq(a: Sequence[float], b: Sequence[float]) -> float:
    return (
        4.0 * (a[0] - b[0]) ** 2
        + (a[1] - b[1]) ** 2
        + (a[2] - b[2]) ** 2
    )


@lru_cache(maxsize=4096)
def _gamma_heuristic(
    hsp_solute: tuple[float, float, float],
    hsp_solvent: tuple[float, float, float],
    T_K: float,  # noqa: N803
) -> float:
    """Return the uncalibrated Hansen-distance gamma heuristic.

    The exponential form is regular-solution-inspired. Its prefactor was
    selected to reproduce one limonene-in-ethanol checkpoint, so the result is
    a diagnostic estimate rather than a generally validated thermodynamic
    model.
    """
    distance_sq = _hansen_distance_sq(hsp_solute, hsp_solvent)
    calibration_prefactor = 0.0055
    return math.exp(calibration_prefactor * distance_sq * 298.15 / T_K)


def mixture_hsp(
    composition: Mapping[str, float],
    *,
    hsp_table: Mapping[str, tuple[float, float, float]] | None = None,
) -> tuple[float, float, float] | None:
    """Return the composition-weighted Hansen vector used by ``gamma``.

    The vector depends only on the mixture, not on the solute being evaluated.
    Exposing the exact existing calculation lets a formula evaluation compute
    it once and reuse it for every row without changing the heuristic or its
    authority boundary.  ``None`` preserves the prior empty/non-positive
    composition behavior.
    """

    hsp = hsp_table or {}
    positive_components = {
        component: fraction
        for component, fraction in composition.items()
        if fraction > 0
    }
    total = sum(positive_components.values())
    if total <= 0:
        return None

    average_hsp = [0.0, 0.0, 0.0]
    for component, fraction in positive_components.items():
        component_hsp = hsp.get(component)
        if component_hsp is None:
            normalized = component.lower()
            if "ethanol" in normalized or normalized in ("etoh", "ethyl alcohol"):
                component_hsp = _HSP_ETHANOL
            elif "water" in normalized:
                component_hsp = _HSP_WATER
            else:
                component_hsp = _HSP_DEFAULT_FRAGRANCE
        for index in range(3):
            average_hsp[index] += fraction / total * component_hsp[index]

    return tuple(average_hsp)


def gamma(
    name: str,
    composition: Mapping[str, float],
    T_K: float = 298.15,  # noqa: N803
    *,
    hsp_table: Mapping[str, tuple[float, float, float]] | None = None,
    smiles_table: Mapping[str, str] | None = None,
    mixture_hsp_override: tuple[float, float, float] | None = None,
) -> float:
    """Estimate gamma for ``name`` in a mole-fraction composition.

    ``smiles_table`` is retained for API compatibility and future, explicitly
    versioned UNIFAC work. It has no effect while UNIFAC is unimplemented.
    """
    del smiles_table
    if not composition or name not in composition:
        return 1.0

    hsp = hsp_table or {}
    solute_hsp = hsp.get(name) or _HSP_DEFAULT_FRAGRANCE

    average_hsp = mixture_hsp_override or mixture_hsp(
        composition,
        hsp_table=hsp,
    )
    if average_hsp is None:
        return 1.0

    return _gamma_heuristic(tuple(solute_hsp), tuple(average_hsp), T_K)


if __name__ == "__main__":
    hsp = {
        "Ethanol": _HSP_ETHANOL,
        "Limonene": (16.5, 1.1, 4.2),
    }
    composition = {"Ethanol": 0.95, "Limonene": 0.05}
    limonene_gamma = gamma("Limonene", composition, hsp_table=hsp)
    ethanol_gamma = gamma("Ethanol", composition, hsp_table=hsp)
    print(f"gamma(limonene in ethanol) = {limonene_gamma:.2f} (diagnostic)")
    print(f"gamma(ethanol in mixture) = {ethanol_gamma:.2f} (diagnostic)")
