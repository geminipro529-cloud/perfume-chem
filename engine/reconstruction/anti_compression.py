"""Anti-compression audit for perfume reconstruction.

Ports the 12 independence criteria from PROTOCOL.md Section 2.3.
Prevents over-compression where distinct materials with different odor
functions are silently merged during reconstruction.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from engine.domain_errors import ReconstructionInputError
from engine.name_utils import names_match

# ═══════════════════════════════════════════════════════════════════════════════
# Data
# ═══════════════════════════════════════════════════════════════════════════════


class EvidenceMatch(StrEnum):
    """Three-valued evidence result for one equivalence axis."""

    MATCH = "MATCH"
    DIFFER = "DIFFER"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True, init=False)
class CompressionCheck:
    """Result of a single anti-compression criterion check.

    Parameters
    ----------
    criterion_name : str
        Machine-readable criterion key (e.g. ``"same_cas"``).
    passed : bool
        True if the two materials satisfy this criterion (i.e. they *are*
        the same along this axis — a pass means they could be merged).
    detail : str
        Human-readable explanation of the check outcome.
    material_a : str
        First material name (canonical).
    material_b : str
        Second material name (canonical).
    """

    criterion_name: str
    result: EvidenceMatch
    detail: str
    material_a: str
    material_b: str

    def __init__(
        self,
        criterion_name: str,
        result: EvidenceMatch | str | bool | None = None,
        detail: str = "",
        material_a: str = "",
        material_b: str = "",
        *,
        passed: bool | None = None,
    ) -> None:
        if passed is not None:
            if result is not None:
                raise TypeError("provide result or passed, not both")
            result = passed
        if isinstance(result, bool):
            evidence = EvidenceMatch.MATCH if result else EvidenceMatch.DIFFER
        elif result is None:
            evidence = EvidenceMatch.UNKNOWN
        else:
            evidence = EvidenceMatch(result)
        object.__setattr__(self, "criterion_name", criterion_name)
        object.__setattr__(self, "result", evidence)
        object.__setattr__(self, "detail", detail)
        object.__setattr__(self, "material_a", material_a)
        object.__setattr__(self, "material_b", material_b)

    @property
    def passed(self) -> bool:
        """Compatibility view; only an evidence MATCH is a pass."""

        return self.result is EvidenceMatch.MATCH

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CompressionCheck:
        return cls(
            criterion_name=str(data.get("criterion_name", "")),
            result=data.get(
                "result",
                bool(data.get("passed", False))
                if "passed" in data
                else EvidenceMatch.UNKNOWN,
            ),
            detail=str(data.get("detail", "")),
            material_a=str(data.get("material_a", "")),
            material_b=str(data.get("material_b", "")),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "criterion_name": self.criterion_name,
            "result": self.result.value,
            "passed": self.passed,
            "detail": self.detail,
            "material_a": self.material_a,
            "material_b": self.material_b,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Criteria registry
# ═══════════════════════════════════════════════════════════════════════════════

ANTI_COMPRESSION_CRITERIA: list[dict[str, str]] = [
    {
        "name": "chemical_scaffold_isomer",
        "description": "Same chemical scaffold and isomer profile",
        "check_type": "identity",
    },
    {
        "name": "supplier_grade",
        "description": "Same supplier, grade, and nominal purity",
        "check_type": "identity",
    },
    {
        "name": "volatility_time_window",
        "description": "Same volatility tier and temporal position in the fragrance",
        "check_type": "function",
    },
    {
        "name": "odor_quality",
        "description": "Same dominant odor descriptors under trained panel",
        "check_type": "function",
    },
    {
        "name": "diffusion_behavior",
        "description": "Same calculated and observed diffusion into headspace",
        "check_type": "chemical",
    },
    {
        "name": "texture",
        "description": "Same tactile and textural effect",
        "check_type": "function",
    },
    {
        "name": "substantivity",
        "description": "Same residual behavior after drydown",
        "check_type": "temporal",
    },
    {
        "name": "matrix_partitioning",
        "description": "Same partitioning behavior in the product matrix",
        "check_type": "chemical",
    },
    {
        "name": "gc_peak_ri_evidence",
        "description": "Same observed GC peak behavior at matching RI",
        "check_type": "identity",
    },
    {
        "name": "gco_odor_event",
        "description": "Same characterized odor event in GC-O runs",
        "check_type": "function",
    },
    {
        "name": "official_note_support",
        "description": "Both supported by official notes/identity roster",
        "check_type": "identity",
    },
    {
        "name": "source_roster_identity",
        "description": "Same source roster identity entry",
        "check_type": "identity",
    },
]

EQUIVALENCE_SCOPE_QUESTIONS: tuple[str, ...] = (
    "same chemical entity?",
    "same stereoisomer?",
    "same trade grade?",
    "same supplier product?",
    "same lot?",
    "same stock solution?",
    "same physical dose?",
    "functionally substitutable?",
)

_EQUIVALENCE_SCOPE_FIELDS: tuple[str, ...] = (
    "cas",
    "stereoisomer",
    "trade_grade",
    "supplier_product",
    "lot",
    "stock_solution",
    "physical_dose",
)


def _scope_result(left: object, right: object) -> EvidenceMatch:
    if left is None or right is None or left == "" or right == "":
        return EvidenceMatch.UNKNOWN
    return EvidenceMatch.MATCH if left == right else EvidenceMatch.DIFFER


def evaluate_equivalence_scopes(
    left: dict[str, Any],
    right: dict[str, Any],
    *,
    functionally_substitutable: bool | None,
) -> dict[str, EvidenceMatch]:
    """Answer all eight equivalence questions from declared evidence."""

    results = {
        question: _scope_result(left.get(field_name), right.get(field_name))
        for question, field_name in zip(
            EQUIVALENCE_SCOPE_QUESTIONS[:-1],
            _EQUIVALENCE_SCOPE_FIELDS,
            strict=True,
        )
    }
    results[EQUIVALENCE_SCOPE_QUESTIONS[-1]] = (
        EvidenceMatch.UNKNOWN
        if functionally_substitutable is None
        else (
            EvidenceMatch.MATCH
            if functionally_substitutable
            else EvidenceMatch.DIFFER
        )
    )
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# Default heuristic profile
# ═══════════════════════════════════════════════════════════════════════════════

_DEFAULT_PROFILE: dict[str, Any] = {
    "cas": None,
    "role": None,
    "vp": None,
    "odor_family": None,
    "temporal_window": None,
    "receptor": None,
    "supplier_grade": None,
    "stereochemistry": None,
    "natural_origin": None,
    "chemotype": None,
    "supplier": None,
    "supplier_product": None,
    "nominal_purity": None,
    "lot": None,
    "synergy_partners": None,
    "accord_contexts": None,
    "dose_range_min": None,
    "dose_range_max": None,
    "sensory_independent": None,
    "texture": None,
    "logp": None,
    "odt_ppm": None,
    "analytical_ri": None,
    "gco_intensity": None,
    "note_list": None,
}


def _default_get_profile(name: str) -> dict[str, Any]:
    """Return an evidence-empty profile; names never fabricate properties."""

    return dict(_DEFAULT_PROFILE)


# ═══════════════════════════════════════════════════════════════════════════════
# Check runners
# ═══════════════════════════════════════════════════════════════════════════════


def _compare_declared_dimensions(
    pa: dict[str, Any],
    pb: dict[str, Any],
    fields: tuple[str, ...],
) -> tuple[EvidenceMatch, str]:
    """Compare only declared identity dimensions without treating absence as a match."""

    matched: list[str] = []
    incomplete: list[str] = []
    different: list[str] = []
    for field_name in fields:
        left = pa.get(field_name)
        right = pb.get(field_name)
        left_known = left is not None and left != ""
        right_known = right is not None and right != ""
        if not left_known and not right_known:
            continue
        if not left_known or not right_known:
            incomplete.append(field_name)
        elif left != right:
            different.append(field_name)
        else:
            matched.append(field_name)

    if different:
        return EvidenceMatch.DIFFER, "declared dimensions differ: " + ", ".join(different)
    if incomplete:
        return EvidenceMatch.UNKNOWN, "one-sided declared dimensions: " + ", ".join(incomplete)
    if matched:
        return EvidenceMatch.MATCH, "declared dimensions match: " + ", ".join(matched)
    return EvidenceMatch.UNKNOWN, "no declared dimensions"


def _check_same_cas(a: str, b: str, pa: dict[str, Any], pb: dict[str, Any]) -> CompressionCheck:
    """Check chemical scaffold plus declared stereo/natural identity dimensions."""
    cas_a = pa.get("cas")
    cas_b = pb.get("cas")
    if cas_a is None or cas_a == "" or cas_b is None or cas_b == "":
        result = EvidenceMatch.UNKNOWN
        detail = "insufficient CAS evidence"
    elif cas_a != cas_b:
        result = EvidenceMatch.DIFFER
        detail = f"CAS {cas_a} != {cas_b}"
    else:
        result, dimension_detail = _compare_declared_dimensions(
            pa,
            pb,
            ("stereochemistry", "natural_origin", "chemotype"),
        )
        detail = f"CAS {cas_a} matches; {dimension_detail}"
    return CompressionCheck(
        criterion_name="chemical_scaffold_isomer",
        result=result,
        detail=detail,
        material_a=a,
        material_b=b,
    )


def _check_same_supplier_grade(
    a: str, b: str, pa: dict[str, Any], pb: dict[str, Any]
) -> CompressionCheck:
    """Check supplier, product, grade, purity, and lot when declared."""
    result, dimension_detail = _compare_declared_dimensions(
        pa,
        pb,
        (
            "supplier",
            "supplier_product",
            "supplier_grade",
            "nominal_purity",
            "lot",
        ),
    )
    detail = f"supplier identity: {dimension_detail}"
    return CompressionCheck(
        criterion_name="supplier_grade",
        result=result,
        detail=detail,
        material_a=a,
        material_b=b,
    )


def _check_same_vp_tier(a: str, b: str, pa: dict[str, Any], pb: dict[str, Any]) -> CompressionCheck:
    """Check: same volatility tier and temporal position in the fragrance."""
    vp_a = pa.get("vp")
    vp_b = pb.get("vp")

    def _tier(vp: float) -> str:
        if vp > 2.0:
            return "top"
        elif vp >= 0.1:
            return "heart"
        else:
            return "base"

    if vp_a is None or vp_b is None:
        result = EvidenceMatch.UNKNOWN
        detail = "insufficient volatility evidence"
    else:
        tier_a = _tier(float(vp_a))
        tier_b = _tier(float(vp_b))
        result = EvidenceMatch.MATCH if tier_a == tier_b else EvidenceMatch.DIFFER
        detail = (
            f"both VP tier={tier_a} (VP={vp_a:.4g}, {vp_b:.4g})"
            if result is EvidenceMatch.MATCH
            else f"VP tier={tier_a} vs tier={tier_b} (VP={vp_a:.4g}, {vp_b:.4g})"
        )
    return CompressionCheck(
        criterion_name="volatility_time_window",
        result=result,
        detail=detail,
        material_a=a,
        material_b=b,
    )


def _check_same_odor_family(
    a: str, b: str, pa: dict[str, Any], pb: dict[str, Any]
) -> CompressionCheck:
    """Check: same dominant odor descriptors (odor family)."""
    fam_a = pa.get("odor_family")
    fam_b = pb.get("odor_family")
    result = _scope_result(fam_a, fam_b)
    detail = (
        "insufficient odor-quality evidence"
        if result is EvidenceMatch.UNKNOWN
        else (
            f"both odor_family={fam_a}"
            if result is EvidenceMatch.MATCH
            else f"odor_family={fam_a} vs {fam_b}"
        )
    )
    return CompressionCheck(
        criterion_name="odor_quality",
        result=result,
        detail=detail,
        material_a=a,
        material_b=b,
    )


def _check_diffusion_behavior(
    a: str, b: str, pa: dict[str, Any], pb: dict[str, Any]
) -> CompressionCheck:
    """Check: same calculated and observed diffusion into headspace (VP-based heuristic)."""
    vp_a = pa.get("vp")
    vp_b = pb.get("vp")
    # Materials within 1 order of magnitude VP are considered similar diffusers
    if vp_a is None or vp_b is None:
        result = EvidenceMatch.UNKNOWN
        detail = "insufficient diffusion evidence"
    elif vp_a > 0 and vp_b > 0:
        ratio = max(vp_a, vp_b) / min(vp_a, vp_b)
        result = EvidenceMatch.MATCH if ratio <= 10.0 else EvidenceMatch.DIFFER
        detail = (
            f"VP ratio={ratio:.2g} (similar diffusion)"
            if result is EvidenceMatch.MATCH
            else f"VP ratio={ratio:.2g} (different diffusion)"
        )
    else:
        result = EvidenceMatch.MATCH if vp_a == vp_b else EvidenceMatch.DIFFER
        detail = (
            "both VP=0"
            if result is EvidenceMatch.MATCH
            else "VP data mismatch"
        )
    return CompressionCheck(
        criterion_name="diffusion_behavior",
        result=result,
        detail=detail,
        material_a=a,
        material_b=b,
    )


def _check_texture(a: str, b: str, pa: dict[str, Any], pb: dict[str, Any]) -> CompressionCheck:
    """Check: same tactile and textural effect."""
    tex_a = pa.get("texture")
    tex_b = pb.get("texture")
    result = _scope_result(tex_a, tex_b)
    detail = (
        "insufficient texture evidence"
        if result is EvidenceMatch.UNKNOWN
        else (
            f"both texture={tex_a}"
            if result is EvidenceMatch.MATCH
            else f"texture={tex_a} vs {tex_b}"
        )
    )
    return CompressionCheck(
        criterion_name="texture",
        result=result,
        detail=detail,
        material_a=a,
        material_b=b,
    )


def _check_substantivity(
    a: str, b: str, pa: dict[str, Any], pb: dict[str, Any]
) -> CompressionCheck:
    """Check: same residual behavior after drydown (ODT/VP-based persistence proxy)."""
    vp_a = pa.get("vp")
    vp_b = pb.get("vp")
    odt_a = pa.get("odt_ppm")

    # Persistence proxy: low VP + low ODT = high substantivity
    # Compare persistence tiers: high (VP<0.01), medium (VP<0.1), low (VP>=0.1)
    def _persistence_tier(vp: float) -> str:
        if vp < 0.01:
            return "high"
        elif vp < 0.1:
            return "medium"
        else:
            return "low"

    if vp_a is None or vp_b is None or odt_a is None:
        result = EvidenceMatch.UNKNOWN
        detail = "insufficient substantivity evidence"
    else:
        tier_a = _persistence_tier(float(vp_a))
        tier_b = _persistence_tier(float(vp_b))
        result = EvidenceMatch.MATCH if tier_a == tier_b else EvidenceMatch.DIFFER
        detail = (
            f"both persistence={tier_a} (VP={vp_a:.4g}, ODT={odt_a:.4g})"
            if result is EvidenceMatch.MATCH
            else f"persistence={tier_a} vs {tier_b} (VP={vp_a:.4g}/{vp_b:.4g})"
        )
    return CompressionCheck(
        criterion_name="substantivity",
        result=result,
        detail=detail,
        material_a=a,
        material_b=b,
    )


def _check_matrix_partitioning(
    a: str, b: str, pa: dict[str, Any], pb: dict[str, Any]
) -> CompressionCheck:
    """Check: same partitioning behavior in the product matrix (logP proxy)."""
    logp_a = pa.get("logp")
    logp_b = pb.get("logp")
    # Within 1 log unit = similar partitioning
    if logp_a is not None and logp_b is not None:
        diff = abs(logp_a - logp_b)
        result = EvidenceMatch.MATCH if diff <= 1.0 else EvidenceMatch.DIFFER
        detail = (
            f"logP diff={diff:.2g} (similar partitioning)"
            if result is EvidenceMatch.MATCH
            else f"logP diff={diff:.2g} (different partitioning)"
        )
    else:
        result = EvidenceMatch.UNKNOWN
        detail = "insufficient logP data"
    return CompressionCheck(
        criterion_name="matrix_partitioning",
        result=result,
        detail=detail,
        material_a=a,
        material_b=b,
    )


def _check_gc_peak_ri(a: str, b: str, pa: dict[str, Any], pb: dict[str, Any]) -> CompressionCheck:
    """Check: same observed GC peak behavior at matching RI."""
    ri_a = pa.get("analytical_ri")
    ri_b = pb.get("analytical_ri")
    if ri_a is not None and ri_b is not None:
        diff = abs(ri_a - ri_b)
        result = EvidenceMatch.MATCH if diff <= 20 else EvidenceMatch.DIFFER
        detail = (
            f"RI diff={diff} (same peak)"
            if result is EvidenceMatch.MATCH
            else f"RI diff={diff} (different peaks)"
        )
    else:
        result = EvidenceMatch.UNKNOWN
        detail = "insufficient analytical_ri data"
    return CompressionCheck(
        criterion_name="gc_peak_ri_evidence",
        result=result,
        detail=detail,
        material_a=a,
        material_b=b,
    )


def _check_gco_odor_event(
    a: str, b: str, pa: dict[str, Any], pb: dict[str, Any]
) -> CompressionCheck:
    """Check: same characterized odor event in GC-O runs."""
    gco_a = pa.get("gco_intensity")
    gco_b = pb.get("gco_intensity")
    if gco_a is not None and gco_b is not None:
        result = EvidenceMatch.MATCH if gco_a == gco_b else EvidenceMatch.DIFFER
        detail = (
            f"both gco_intensity={gco_a}"
            if result is EvidenceMatch.MATCH
            else f"gco_intensity={gco_a} vs {gco_b}"
        )
    else:
        result = EvidenceMatch.UNKNOWN
        detail = "insufficient gco_intensity data"
    return CompressionCheck(
        criterion_name="gco_odor_event",
        result=result,
        detail=detail,
        material_a=a,
        material_b=b,
    )


def _check_official_note_support(
    a: str, b: str, pa: dict[str, Any], pb: dict[str, Any]
) -> CompressionCheck:
    """Check: both supported by official notes/identity roster."""
    notes_a = pa.get("note_list")
    notes_b = pb.get("note_list")
    # Both must have at least one note entry to be "officially supported"
    if notes_a and notes_b:
        result = EvidenceMatch.MATCH
        detail = f"both have note entries ({len(notes_a)} / {len(notes_b)})"
    else:
        result = EvidenceMatch.UNKNOWN
        detail = "insufficient official-note evidence"
    return CompressionCheck(
        criterion_name="official_note_support",
        result=result,
        detail=detail,
        material_a=a,
        material_b=b,
    )


def _check_source_roster_identity(
    a: str, b: str, pa: dict[str, Any], pb: dict[str, Any]
) -> CompressionCheck:
    """Check: same source roster identity entry (names_match)."""
    result = EvidenceMatch.MATCH if names_match(a, b) else EvidenceMatch.DIFFER
    detail = (
        "names match (same roster identity)"
        if result is EvidenceMatch.MATCH
        else "names differ (distinct roster entries)"
    )
    return CompressionCheck(
        criterion_name="source_roster_identity",
        result=result,
        detail=detail,
        material_a=a,
        material_b=b,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Dispatcher
# ═══════════════════════════════════════════════════════════════════════════════

_CHECK_DISPATCHER: dict[str, Callable[..., CompressionCheck]] = {
    "chemical_scaffold_isomer": _check_same_cas,
    "supplier_grade": _check_same_supplier_grade,
    "volatility_time_window": _check_same_vp_tier,
    "odor_quality": _check_same_odor_family,
    "diffusion_behavior": _check_diffusion_behavior,
    "texture": _check_texture,
    "substantivity": _check_substantivity,
    "matrix_partitioning": _check_matrix_partitioning,
    "gc_peak_ri_evidence": _check_gc_peak_ri,
    "gco_odor_event": _check_gco_odor_event,
    "official_note_support": _check_official_note_support,
    "source_roster_identity": _check_source_roster_identity,
}


# ═══════════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════════


def should_merge(
    material_a: str,
    material_b: str,
    checks: list[CompressionCheck],
) -> bool:
    """Return True only if ALL 12 anti-compression criteria pass.

    Parameters
    ----------
    material_a : str
        First material name.
    material_b : str
        Second material name.
    checks : list[CompressionCheck]
        Full list of 12 checks for this pair.

    Returns
    -------
    bool
        True only when every check has ``passed=True``.  Any single failure
        means the materials should NOT be merged.
    """
    expected_axes = {criterion["name"] for criterion in ANTI_COMPRESSION_CRITERIA}
    observed_axes = {check.criterion_name for check in checks}
    if len(checks) != len(ANTI_COMPRESSION_CRITERIA) or observed_axes != expected_axes:
        return False
    return all(check.result is EvidenceMatch.MATCH for check in checks)


def audit_formula(
    materials: list[str],
    get_profile_fn: Callable[[str], dict[str, Any]] | None = None,
) -> dict[str, list[CompressionCheck]]:
    """Run all 12 anti-compression checks for every pair in *materials*.

    Parameters
    ----------
    materials : list[str]
        Material names in the formula.
    get_profile_fn : Callable[[str], dict[str, Any]] | None
        Optional callable that returns a material's property dict.
        If not provided, a default heuristic based on name matching is used.

    Returns
    -------
    dict[str, list[CompressionCheck]]
        Mapping ``"{a}<->{b}"`` → list of 12 ``CompressionCheck`` results.
    """
    if not materials:
        raise ReconstructionInputError("anti-compression roster cannot be empty")
    if get_profile_fn is None:
        get_profile_fn = _default_get_profile

    results: dict[str, list[CompressionCheck]] = {}
    n = len(materials)
    for i in range(n):
        for j in range(i + 1, n):
            a = materials[i]
            b = materials[j]
            pa = get_profile_fn(a)
            pb = get_profile_fn(b)
            pair_key = f"{a}<->{b}"
            pair_checks: list[CompressionCheck] = []
            for criterion in ANTI_COMPRESSION_CRITERIA:
                name = criterion["name"]
                runner = _CHECK_DISPATCHER[name]
                pair_checks.append(runner(a, b, pa, pb))
            results[pair_key] = pair_checks

    return results


def restore_from_roster(
    compressed: list[str],
    full_roster: list[str],
) -> list[str]:
    """Expand a compressed material list against a full identity roster.

    Parameters
    ----------
    compressed : list[str]
        Material names that survived compression.
    full_roster : list[str]
        Complete ordered list of all known identities.

    Returns
    -------
    list[str]
        Full roster with all identities present.  Materials from
        *compressed* that match a roster entry are kept once (in roster
        order).  Any roster entries not present in *compressed* are
        appended at the end.
    """
    if not compressed:
        raise ReconstructionInputError("compressed roster cannot be empty")
    if not full_roster:
        raise ReconstructionInputError("full identity roster cannot be empty")

    result: list[str] = []
    seen: set[str] = set()

    # Walk the roster first — keep compressed matches in roster order
    for roster_item in full_roster:
        for comp_item in compressed:
            if names_match(roster_item, comp_item):
                if roster_item not in seen:
                    result.append(roster_item)
                    seen.add(roster_item)
                break

    # Append any compressed items not yet present
    for comp_item in compressed:
        found = False
        for existing in result:
            if names_match(comp_item, existing):
                found = True
                break
        if not found:
            result.append(comp_item)
            seen.add(comp_item)

    # Append any roster items not yet present
    for roster_item in full_roster:
        if roster_item not in seen:
            result.append(roster_item)
            seen.add(roster_item)

    return result


def compression_report(audit_results: dict[str, list[CompressionCheck]]) -> list[str]:
    """Format audit results into human-readable warning lines.

    Parameters
    ----------
    audit_results : dict[str, list[CompressionCheck]]
        Output from :func:`audit_formula`.

    Returns
    -------
    list[str]
        One warning line per pair that should NOT be merged, listing the
        criteria that failed.
    """
    warnings: list[str] = []
    for _pair_key, checks in audit_results.items():
        if should_merge(checks[0].material_a, checks[0].material_b, checks):
            continue
        failed = [c.criterion_name for c in checks if not c.passed]
        a = checks[0].material_a
        b = checks[0].material_b
        warnings.append(f"WARNING: {a} and {b} should NOT be merged: {', '.join(failed)}")
    return warnings
