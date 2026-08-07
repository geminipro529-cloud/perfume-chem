"""Canonical state diff for target/inventory/build/bottle comparison.

Never directly compare volume (uL) to mass (g) without density. Preserve raw
vs active basis and units throughout.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    try:
        from engine.target.formula import TargetFormula, TargetMaterial
    except ImportError:  # pragma: no cover
        TargetFormula = None  # type: ignore[misc,assignment]
        TargetMaterial = None  # type: ignore[misc,assignment]

    try:
        from engine.bottle.events import BottleBatch
    except ImportError:  # pragma: no cover
        BottleBatch = None  # type: ignore[misc,assignment]

    try:
        from engine.build.ledger import BuildFormula, BuildMaterial
    except ImportError:  # pragma: no cover
        BuildFormula = None  # type: ignore[misc,assignment]
        BuildMaterial = None  # type: ignore[misc,assignment]

# ---------------------------------------------------------------------------
# Runtime-safe imports — these modules may not exist in all environments
# ---------------------------------------------------------------------------

try:
    from engine.bottle.events import compute_replay_state
except ImportError:  # pragma: no cover
    compute_replay_state = None  # type: ignore[misc,assignment]

# ---------------------------------------------------------------------------
# Diff status constants
# ---------------------------------------------------------------------------

EQUAL = "EQUAL"
SUBSTITUTED = "SUBSTITUTED"
MISSING = "MISSING"
AMOUNT_DELTA = "AMOUNT_DELTA"
ADDED = "ADDED"
INCOMPARABLE_MISSING_DENSITY = "INCOMPARABLE_MISSING_DENSITY"
INCOMPARABLE_UNSPECIFIED_BASIS = "INCOMPARABLE_UNSPECIFIED_BASIS"
UNTRACKED = "UNTRACKED"

_ALL_STATUSES = frozenset(
    {
        EQUAL,
        SUBSTITUTED,
        MISSING,
        AMOUNT_DELTA,
        ADDED,
        INCOMPARABLE_MISSING_DENSITY,
        INCOMPARABLE_UNSPECIFIED_BASIS,
        UNTRACKED,
    }
)

# ---------------------------------------------------------------------------
# DiffEntry
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DiffEntry:
    """One row in a state diff between two formula representations.

    Parameters
    ----------
    material : str
        Canonical material name.
    status : str
        One of the status constants defined above.
    target_raw_ul : float
        Raw (stock) volume in microlitres from the target.
    target_active_ul : float
        Active-ingredient volume in microlitres from the target.
    build_raw_ul : float
        Raw (stock) volume in microlitres from the build formula.
    build_active_ul : float
        Active-ingredient volume in microlitres from the build formula.
    bottle_mass_g : float
        Current mass in grams from the bottle replay state.
    basis : str
        ``"comparable"`` when density is available for unit conversion,
        otherwise ``"incomparable_missing_density"`` or
        ``"incomparable_unspecified_basis"``.
    detail : str
        Human-readable explanation of the diff.
    """

    material: str
    status: str
    target_raw_ul: float = 0.0
    target_active_ul: float = 0.0
    build_raw_ul: float = 0.0
    build_active_ul: float = 0.0
    bottle_mass_g: float = 0.0
    basis: str = "comparable"
    detail: str = ""

    def __post_init__(self) -> None:
        if self.status not in _ALL_STATUSES:
            raise ValueError(
                f"Unknown status {self.status!r}. Must be one of {sorted(_ALL_STATUSES)}"
            )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# diff_target_to_build
# ---------------------------------------------------------------------------


def diff_target_to_build(
    target_formula: Any,
    build_formula: Any,
) -> list[DiffEntry]:
    """Compare a target hypothesis to an inventory-mapped build formula.

    For each material in the target:
    - If found in build with the same amounts: ``EQUAL``.
    - If found but amounts differ: ``AMOUNT_DELTA``.
    - If found but the build uses a different material: ``SUBSTITUTED``.
    - If not found in build: ``MISSING``.

    Materials present in build but absent from target are reported as
    ``ADDED``.
    """
    entries: list[DiffEntry] = []

    # Build lookup: material name -> BuildMaterial
    build_by_name: dict[str, Any] = {}
    for mat in getattr(build_formula, "materials", ()):
        name = getattr(mat, "material", getattr(mat, "name", ""))
        if name:
            build_by_name[name] = mat

    # Target materials
    target_materials = getattr(target_formula, "target_materials", ())
    seen_in_target: set[str] = set()

    for tmat in target_materials:
        identity = getattr(tmat, "identity", "")
        if not identity:
            continue
        seen_in_target.add(identity)

        bmat = build_by_name.get(identity)
        if bmat is None:
            # Check for substitution: build material with different name
            # but same functional role or accord membership.
            substituted = _find_substitute(tmat, build_by_name)
            if substituted is not None:
                sub_name, sub_mat = substituted
                entries.append(
                    DiffEntry(
                        material=identity,
                        status=SUBSTITUTED,
                        target_raw_ul=_get_raw_ul(tmat),
                        target_active_ul=_get_active_ul(tmat),
                        build_raw_ul=_get_raw_ul(sub_mat),
                        build_active_ul=_get_active_ul(sub_mat),
                        detail=f"{identity} -> {sub_name} (functional substitute)",
                    )
                )
            else:
                entries.append(
                    DiffEntry(
                        material=identity,
                        status=MISSING,
                        target_raw_ul=_get_raw_ul(tmat),
                        target_active_ul=_get_active_ul(tmat),
                        detail="Not in build formula",
                    )
                )
            continue

        # Exact match found — compare amounts
        target_raw = _get_raw_ul(tmat)
        target_act = _get_active_ul(tmat)
        build_raw = _get_raw_ul(bmat)
        build_act = _get_active_ul(bmat)

        if _approx_equal(target_raw, build_raw) and _approx_equal(target_act, build_act):
            entries.append(
                DiffEntry(
                    material=identity,
                    status=EQUAL,
                    target_raw_ul=target_raw,
                    target_active_ul=target_act,
                    build_raw_ul=build_raw,
                    build_active_ul=build_act,
                    detail="Exact match",
                )
            )
        else:
            entries.append(
                DiffEntry(
                    material=identity,
                    status=AMOUNT_DELTA,
                    target_raw_ul=target_raw,
                    target_active_ul=target_act,
                    build_raw_ul=build_raw,
                    build_active_ul=build_act,
                    detail=f"Target raw {target_raw:.1f} uL vs build raw {build_raw:.1f} uL",
                )
            )

    # ADDED: materials in build but not in target
    for name, bmat in build_by_name.items():
        if name not in seen_in_target:
            entries.append(
                DiffEntry(
                    material=name,
                    status=ADDED,
                    build_raw_ul=_get_raw_ul(bmat),
                    build_active_ul=_get_active_ul(bmat),
                    detail="Present in build only",
                )
            )

    return entries


# ---------------------------------------------------------------------------
# diff_build_to_bottle
# ---------------------------------------------------------------------------


def diff_build_to_bottle(
    build_formula: Any,
    bottle_batch: Any,
    density_map: dict[str, float] | None = None,
) -> list[DiffEntry]:
    """Compare a build formula to the current physical bottle state.

    Unit safety
    -----------
    Build amounts are in uL (volume). Bottle state is in grams (mass).
    When *density_map* provides a density for a material, the build active
    volume is converted to mass (``build_active_ul × density_g_ml / 1000``)
    and compared to the bottle mass.  When density is unknown the entry is
    marked ``INCOMPARABLE_MISSING_DENSITY``.

    Parameters
    ----------
    build_formula : BuildFormula
        The inventory-mapped build formula.
    bottle_batch : BottleBatch
        The event-sourced bottle batch whose state is replayed.
    density_map : dict[str, float] | None
        Optional mapping of material name to density in g/mL.  When
        provided, enables comparable unit conversion.

    Returns
    -------
    list[DiffEntry]
        One entry per material across build and bottle.
    """
    density_map = density_map or {}
    entries: list[DiffEntry] = []

    # Replay bottle state
    bottle_materials = bottle_batch.current_materials()

    # Build materials
    build_materials = getattr(build_formula, "materials", ())
    seen_in_build: set[str] = set()

    for bmat in build_materials:
        name = getattr(bmat, "material", getattr(bmat, "name", ""))
        if not name:
            continue
        seen_in_build.add(name)

        build_raw = _get_raw_ul(bmat)
        build_act = _get_active_ul(bmat)
        bottle_mass = bottle_materials.get(name, 0.0)

        # Check concentration basis
        conc_basis = getattr(bmat, "concentration_basis", "unspecified") or "unspecified"
        if conc_basis == "unspecified":
            entries.append(
                DiffEntry(
                    material=name,
                    status=INCOMPARABLE_UNSPECIFIED_BASIS,
                    build_raw_ul=build_raw,
                    build_active_ul=build_act,
                    bottle_mass_g=bottle_mass,
                    basis="incomparable_unspecified_basis",
                    detail=f"Concentration basis is unspecified for {name}",
                )
            )
            continue

        # Check density
        density = density_map.get(name)
        if density is None or density <= 0:
            entries.append(
                DiffEntry(
                    material=name,
                    status=INCOMPARABLE_MISSING_DENSITY,
                    build_raw_ul=build_raw,
                    build_active_ul=build_act,
                    bottle_mass_g=bottle_mass,
                    basis="incomparable_missing_density",
                    detail=f"Missing density for {name} — cannot convert uL to g",
                )
            )
            continue

        # Comparable: convert build active uL to grams
        build_mass_g = build_act * density / 1000.0

        if _approx_equal(build_mass_g, bottle_mass, rel_tol=0.05):
            entries.append(
                DiffEntry(
                    material=name,
                    status=EQUAL,
                    build_raw_ul=build_raw,
                    build_active_ul=build_act,
                    bottle_mass_g=bottle_mass,
                    basis="comparable",
                    detail=f"Build {build_mass_g:.4f} g ≈ Bottle {bottle_mass:.4f} g (within 5%)",
                )
            )
        else:
            entries.append(
                DiffEntry(
                    material=name,
                    status=AMOUNT_DELTA,
                    build_raw_ul=build_raw,
                    build_active_ul=build_act,
                    bottle_mass_g=bottle_mass,
                    basis="comparable",
                    detail=(
                        f"Build {build_mass_g:.4f} g vs Bottle {bottle_mass:.4f} g "
                        f"(density={density} g/mL)"
                    ),
                )
            )

    # UNTRACKED: materials in bottle but not in build
    for name, mass in bottle_materials.items():
        if name not in seen_in_build:
            entries.append(
                DiffEntry(
                    material=name,
                    status=UNTRACKED,
                    bottle_mass_g=mass,
                    detail=f"Present in bottle ({mass:.4f} g) but not in build formula",
                )
            )

    return entries


# ---------------------------------------------------------------------------
# diff_target_to_bottle
# ---------------------------------------------------------------------------


def diff_target_to_bottle(
    target_formula: Any,
    bottle_batch: Any,
    density_map: dict[str, float] | None = None,
) -> list[DiffEntry]:
    """Compare a target hypothesis directly to the physical bottle state.

    Same unit-safety rules as :func:`diff_build_to_bottle`.  Materials
    present in the bottle but absent from the target are reported as
    ``UNTRACKED``.  When a material is found in the bottle under a different
    name (functional substitute), the entry is labelled ``SUBSTITUTED``.

    Parameters
    ----------
    target_formula : TargetFormula
        The target reconstruction hypothesis.
    bottle_batch : BottleBatch
        The event-sourced bottle batch.
    density_map : dict[str, float] | None
        Optional mapping of material name to density in g/mL.

    Returns
    -------
    list[DiffEntry]
        One entry per material across target and bottle.
    """
    density_map = density_map or {}
    entries: list[DiffEntry] = []

    bottle_materials = bottle_batch.current_materials()
    target_materials = getattr(target_formula, "target_materials", ())
    seen_in_target: set[str] = set()

    for tmat in target_materials:
        identity = getattr(tmat, "identity", "")
        if not identity:
            continue
        seen_in_target.add(identity)

        target_raw = _get_raw_ul(tmat)
        target_act = _get_active_ul(tmat)
        bottle_mass = bottle_materials.get(identity, 0.0)

        # Check concentration basis
        conc_basis = getattr(tmat, "concentration_basis", "unspecified") or "unspecified"
        if conc_basis == "unspecified":
            entries.append(
                DiffEntry(
                    material=identity,
                    status=INCOMPARABLE_UNSPECIFIED_BASIS,
                    target_raw_ul=target_raw,
                    target_active_ul=target_act,
                    bottle_mass_g=bottle_mass,
                    basis="incomparable_unspecified_basis",
                    detail=f"Concentration basis is unspecified for {identity}",
                )
            )
            continue

        # Check density
        density = density_map.get(identity)
        if density is None or density <= 0:
            entries.append(
                DiffEntry(
                    material=identity,
                    status=INCOMPARABLE_MISSING_DENSITY,
                    target_raw_ul=target_raw,
                    target_active_ul=target_act,
                    bottle_mass_g=bottle_mass,
                    basis="incomparable_missing_density",
                    detail=f"Missing density for {identity} — cannot convert uL to g",
                )
            )
            continue

        # Comparable: convert target active uL to grams
        target_mass_g = target_act * density / 1000.0

        if _approx_equal(target_mass_g, bottle_mass, rel_tol=0.05):
            entries.append(
                DiffEntry(
                    material=identity,
                    status=EQUAL,
                    target_raw_ul=target_raw,
                    target_active_ul=target_act,
                    bottle_mass_g=bottle_mass,
                    basis="comparable",
                    detail=f"Target {target_mass_g:.4f} g ≈ Bottle {bottle_mass:.4f} g (within 5%)",
                )
            )
        else:
            entries.append(
                DiffEntry(
                    material=identity,
                    status=AMOUNT_DELTA,
                    target_raw_ul=target_raw,
                    target_active_ul=target_act,
                    bottle_mass_g=bottle_mass,
                    basis="comparable",
                    detail=(
                        f"Target {target_mass_g:.4f} g vs Bottle {bottle_mass:.4f} g "
                        f"(density={density} g/mL)"
                    ),
                )
            )

    # UNTRACKED: materials in bottle but not in target
    for name, mass in bottle_materials.items():
        if name not in seen_in_target:
            entries.append(
                DiffEntry(
                    material=name,
                    status=UNTRACKED,
                    bottle_mass_g=mass,
                    detail=f"Present in bottle ({mass:.4f} g) but not in target",
                )
            )

    return entries


# ---------------------------------------------------------------------------
# format_diff_report
# ---------------------------------------------------------------------------


def format_diff_report(entries: list[DiffEntry]) -> str:
    """Return a formatted text report of diff entries.

    Each line shows status, material, amounts, and a detail message.
    Entries are grouped by status for readability.
    """
    if not entries:
        return "(no differences)"

    # Group by status for readability
    status_order = [
        EQUAL,
        SUBSTITUTED,
        AMOUNT_DELTA,
        MISSING,
        ADDED,
        INCOMPARABLE_MISSING_DENSITY,
        INCOMPARABLE_UNSPECIFIED_BASIS,
        UNTRACKED,
    ]
    grouped: dict[str, list[DiffEntry]] = {s: [] for s in status_order}
    for entry in entries:
        grouped.setdefault(entry.status, []).append(entry)

    lines: list[str] = []
    for status in status_order:
        group = grouped.get(status, [])
        if not group:
            continue
        for entry in group:
            line = _format_entry_line(entry)
            lines.append(line)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _format_entry_line(entry: DiffEntry) -> str:
    """Format a single DiffEntry as a human-readable line."""
    status_padded = f"{entry.status:<14}"

    if entry.status == EQUAL:
        if entry.bottle_mass_g:
            return (
                f"{status_padded}| {entry.material}: "
                f"Target {entry.target_raw_ul:.1f} uL -> Bottle {entry.bottle_mass_g:.4f} g "
                f"({entry.basis}) OK"
            )
        if entry.build_raw_ul:
            return (
                f"{status_padded}| {entry.material}: "
                f"Target {entry.target_raw_ul:.1f} uL -> Build {entry.build_raw_ul:.1f} uL "
                f"({entry.basis}) OK"
            )
        return f"{status_padded}| {entry.material}: {entry.detail} OK"

    if entry.status == SUBSTITUTED:
        return f"{status_padded}| {entry.detail}"

    if entry.status == AMOUNT_DELTA:
        return f"{status_padded}| {entry.material}: {entry.detail}"

    if entry.status == MISSING:
        return (
            f"{status_padded}| {entry.material}: "
            f"Target {entry.target_raw_ul:.1f} uL -> Not in build or bottle"
        )

    if entry.status == ADDED:
        return (
            f"{status_padded}| {entry.material}: Build {entry.build_raw_ul:.1f} uL (not in target)"
        )

    if entry.status in (INCOMPARABLE_MISSING_DENSITY, INCOMPARABLE_UNSPECIFIED_BASIS):
        return (
            f"{status_padded}| {entry.material}: "
            f"Target {entry.target_raw_ul:.1f} uL -> Bottle {entry.bottle_mass_g:.4f} g "
            f"({entry.basis})"
        )

    if entry.status == UNTRACKED:
        return (
            f"{status_padded}| {entry.material}: "
            f"Bottle {entry.bottle_mass_g:.4f} g (not in formula)"
        )

    return f"{status_padded}| {entry.material}: {entry.detail}"


def _get_raw_ul(mat: Any) -> float:
    """Extract raw (stock) volume in uL from a material object."""
    # TargetMaterial uses raw_amount; BuildMaterial may use raw_ul
    raw = getattr(mat, "raw_amount", None)
    if raw is not None:
        return float(raw)
    raw = getattr(mat, "raw_ul", None)
    if raw is not None:
        return float(raw)
    return 0.0


def _get_active_ul(mat: Any) -> float:
    """Extract active-ingredient volume in uL from a material object."""
    # TargetMaterial uses active_amount_median; BuildMaterial may use active_ul
    act = getattr(mat, "active_amount_median", None)
    if act is not None:
        return float(act)
    act = getattr(mat, "active_ul", None)
    if act is not None:
        return float(act)
    return 0.0


def _find_substitute(
    tmat: Any,
    build_by_name: dict[str, Any],
) -> tuple[str, Any] | None:
    """Try to find a functional substitute for *tmat* in the build map.

    Checks accord membership overlap and functional role overlap as
    heuristics for substitution.
    """
    tmat_roles = set(getattr(tmat, "functional_roles", ()))
    tmat_accords = set(getattr(tmat, "accord_membership", ()))

    best_score = 0
    best_pair: tuple[str, Any] | None = None

    for name, bmat in build_by_name.items():
        bmat_roles = set(getattr(bmat, "functional_roles", ()))
        bmat_accords = set(getattr(bmat, "accord_membership", ()))

        score = len(tmat_roles & bmat_roles) + len(tmat_accords & bmat_accords)
        if score > best_score:
            best_score = score
            best_pair = (name, bmat)

    return best_pair if best_score > 0 else None


def _approx_equal(a: float, b: float, rel_tol: float = 0.01) -> bool:
    """Return True if *a* and *b* are approximately equal within *rel_tol*."""
    if a == b:
        return True
    if a == 0.0 or b == 0.0:
        return abs(a - b) < 1e-9
    return abs(a - b) / max(abs(a), abs(b)) <= rel_tol
