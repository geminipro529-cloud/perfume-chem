"""Canonical material identity registry.

Implements the identity chain from chemical entity through supplier lot
to physical dose. Separates identity resolution from name normalisation.

Identity chain:
  chemical_entity -> stereoisomer/isomer_mixture -> trade_grade
    -> supplier_product -> supplier_lot -> stock_solution -> physical_dose

Natural chain:
  botanical_species -> plant_part -> chemotype -> origin
    -> extraction_method -> supplier_lot -> analytical_composition -> stock_solution

Non-equivalent names prevent the resolver from silently conflating materials
that perfumers and suppliers treat as distinct.

Usage:
    from engine.identity.resolver import resolve_identity, MaterialIdentity

    ident = resolve_identity("Alpha Isomethyl Ionone", "Methyl Ionone Gamma Coeur")
    if ident.is_equivalent:
        ...
    else:
        print(ident.non_equivalent_names)

RULE: Do not use parenthetical equating in formula rows
(e.g. "Alpha Isomethyl Ionone (Methyl Ionone Pure)").
Use the identity registry to verify equivalence, and if not verified,
store separate target rows with explicit substitution mappings.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from engine.name_utils import normalize_name


class IdentityGrade:
    CHEMICAL_ENTITY = "chemical_entity"
    ISOMER_MIXTURE = "isomer_mixture"
    TRADE_GRADE = "trade_grade"
    SUPPLIER_PRODUCT = "supplier_product"
    SUPPLIER_LOT = "supplier_lot"
    STOCK_SOLUTION = "stock_solution"
    PHYSICAL_DOSE = "physical_dose"


class NaturalGrade:
    BOTANICAL_SPECIES = "botanical_species"
    PLANT_PART = "plant_part"
    CHEMOTYPE = "chemotype"
    ORIGIN = "origin"
    EXTRACTION_METHOD = "extraction_method"
    SUPPLIER_LOT = "supplier_lot"
    ANALYTICAL_COMPOSITION = "analytical_composition"
    STOCK_SOLUTION = "stock_solution"


IDENTITY_GRADES: frozenset[str] = frozenset(
    {
        IdentityGrade.CHEMICAL_ENTITY,
        IdentityGrade.ISOMER_MIXTURE,
        IdentityGrade.TRADE_GRADE,
        IdentityGrade.SUPPLIER_PRODUCT,
        IdentityGrade.SUPPLIER_LOT,
        IdentityGrade.STOCK_SOLUTION,
        IdentityGrade.PHYSICAL_DOSE,
    }
)

NATURAL_GRADES: frozenset[str] = frozenset(
    {
        NaturalGrade.BOTANICAL_SPECIES,
        NaturalGrade.PLANT_PART,
        NaturalGrade.CHEMOTYPE,
        NaturalGrade.ORIGIN,
        NaturalGrade.EXTRACTION_METHOD,
        NaturalGrade.SUPPLIER_LOT,
        NaturalGrade.ANALYTICAL_COMPOSITION,
        NaturalGrade.STOCK_SOLUTION,
    }
)

CONTROLLED_GRADES: frozenset[str] = IDENTITY_GRADES | NATURAL_GRADES


@dataclass(frozen=True, slots=True)
class MaterialIdentity:
    """A resolved material identity at a specific grade level.

    Two identities are equivalent only if all confirmed fields match.
    Different supplier, lot, grade, or chemotype breaks equivalence.
    """

    identity_id: str
    name: str
    canonical_name: str
    grade: str
    supplier: str | None = None
    lot: str | None = None
    cas: str | None = None
    stereoisomer: str | None = None
    trade_grade: str | None = None
    supplier_product: str | None = None
    stock_solution: str | None = None
    physical_dose: str | None = None
    botanical_species: str | None = None
    plant_part: str | None = None
    chemotype: str | None = None
    natural_origin: str | None = None
    extraction_method: str | None = None
    trade_names: tuple[str, ...] = ()
    non_equivalent_names: frozenset[str] = field(default_factory=frozenset)

    def __hash__(self) -> int:
        return hash(self.identity_id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MaterialIdentity):
            return NotImplemented
        return self.identity_id == other.identity_id

    @property
    def is_synthetic(self) -> bool:
        return self.grade in IDENTITY_GRADES and not self.is_natural

    @property
    def is_natural(self) -> bool:
        return self.grade in NATURAL_GRADES and (
            self.grade
            not in {
                NaturalGrade.SUPPLIER_LOT,
                NaturalGrade.STOCK_SOLUTION,
            }
            or any(
                value
                for value in (
                    self.botanical_species,
                    self.plant_part,
                    self.chemotype,
                    self.natural_origin,
                    self.extraction_method,
                )
            )
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MaterialIdentity:
        return cls(
            identity_id=str(data["identity_id"]),
            name=str(data["name"]),
            canonical_name=str(data["canonical_name"]),
            grade=str(data["grade"]),
            supplier=str(data["supplier"]) if data.get("supplier") else None,
            lot=str(data["lot"]) if data.get("lot") else None,
            cas=str(data["cas"]) if data.get("cas") else None,
            stereoisomer=str(data["stereoisomer"]) if data.get("stereoisomer") else None,
            trade_grade=str(data["trade_grade"]) if data.get("trade_grade") else None,
            supplier_product=str(data["supplier_product"])
            if data.get("supplier_product")
            else None,
            stock_solution=str(data["stock_solution"]) if data.get("stock_solution") else None,
            physical_dose=str(data["physical_dose"]) if data.get("physical_dose") else None,
            botanical_species=str(data["botanical_species"])
            if data.get("botanical_species")
            else None,
            plant_part=str(data["plant_part"]) if data.get("plant_part") else None,
            chemotype=str(data["chemotype"]) if data.get("chemotype") else None,
            natural_origin=str(data["natural_origin"]) if data.get("natural_origin") else None,
            extraction_method=str(data["extraction_method"])
            if data.get("extraction_method")
            else None,
            trade_names=tuple(str(x) for x in data.get("trade_names") or ()),
            non_equivalent_names=frozenset(str(x) for x in data.get("non_equivalent_names") or ()),
        )


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _are_equivalent_synthetic(a: MaterialIdentity, b: MaterialIdentity) -> bool:
    """Two synthetic identities are equivalent if all confirmed fields match."""
    if a.grade != b.grade:
        return False
    if a.canonical_name != b.canonical_name:
        return False
    if (a.cas is None) != (b.cas is None):
        return False
    if a.cas is not None and a.cas != b.cas:
        return False

    scoped_fields = (
        "stereoisomer",
        "trade_grade",
        "supplier",
        "supplier_product",
        "lot",
        "stock_solution",
        "physical_dose",
    )
    for field_name in scoped_fields:
        left = getattr(a, field_name)
        right = getattr(b, field_name)
        if (left is not None or right is not None) and left != right:
            return False

    if a.cas is None:
        strong_scope = any(
            getattr(a, field_name) is not None
            and getattr(a, field_name) == getattr(b, field_name)
            for field_name in (
                "supplier_product",
                "lot",
                "stock_solution",
                "physical_dose",
            )
        )
        if not strong_scope:
            return False
    return True


def _are_equivalent_natural(a: MaterialIdentity, b: MaterialIdentity) -> bool:
    """Two natural identities are equivalent only when declared scope matches."""
    if a.grade != b.grade:
        return False
    if a.canonical_name != b.canonical_name:
        return False
    for field_name in (
        "botanical_species",
        "plant_part",
        "chemotype",
        "natural_origin",
        "extraction_method",
        "supplier",
        "lot",
        "stock_solution",
    ):
        left = getattr(a, field_name)
        right = getattr(b, field_name)
        if (left is not None or right is not None) and left != right:
            return False
    return True


def are_equivalent(a: MaterialIdentity, b: MaterialIdentity) -> bool:
    """Return True if two material identities are functionally equivalent.

    This is stricter than same_canonical_name() — different grades,
    suppliers, lots, or chemotypes may produce different materials
    even if the canonical name matches.
    """
    if a.identity_id == b.identity_id:
        return True
    if a.canonical_name != b.canonical_name:
        return False
    if a.is_synthetic and b.is_synthetic:
        return _are_equivalent_synthetic(a, b)
    if a.is_natural and b.is_natural:
        return _are_equivalent_natural(a, b)
    return False


# ---------------------------------------------------------------------------
# Non-equivalent pairs — materials that SHOULD NOT be silently collapsed
# ---------------------------------------------------------------------------
_NON_EQUIVALENT_PAIRS: list[tuple[str, str]] = [
    ("alpha isomethyl ionone", "methyl ionone gamma coeur"),
    ("habanolide", "galaxolide"),
    ("muscenone delta", "exaltolide"),
    ("bacdanol", "sandalore"),
    ("haitian vetiver", "indian vetiver"),
    ("lavender", "lavandin"),
    ("ambroxan", "ambrofix"),
    ("patchouli oil", "clearwood"),
    ("javanol", "ebanol"),
    ("alpha ionone", "methyl ionone"),
    ("isoraldeine 95", "alpha-isomethyl ionone"),
    ("hedione", "hedione hc"),
    ("cashmeran", "ambermax"),
]

_NON_EQUIV_SET: frozenset = frozenset(  # type: ignore[type-arg]
    tuple(sorted((normalize_name(a), normalize_name(b))))
    for a, b in _NON_EQUIVALENT_PAIRS
    if normalize_name(a) != normalize_name(b)
)


def get_non_equivalent_names(material_name: str) -> frozenset[str]:
    """Return the set of names this material explicitly should NOT be collapsed into."""
    key = normalize_name(material_name)
    result: set[str] = set()
    for a, b in _NON_EQUIV_SET:
        if a == key:
            result.add(b)
        elif b == key:
            result.add(a)
    return frozenset(result)


KNOWN_NON_EQUIVALENT: frozenset[str] = frozenset(
    name
    for pair in _NON_EQUIV_SET
    for name in pair  # type: ignore[assignment]
)


def resolve_identity(
    name: str,
    *,
    grade: str = IdentityGrade.TRADE_GRADE,
    supplier: str | None = None,
    lot: str | None = None,
    cas: str | None = None,
    stereoisomer: str | None = None,
    trade_grade: str | None = None,
    supplier_product: str | None = None,
    stock_solution: str | None = None,
    physical_dose: str | None = None,
    botanical_species: str | None = None,
    plant_part: str | None = None,
    chemotype: str | None = None,
    natural_origin: str | None = None,
    extraction_method: str | None = None,
) -> MaterialIdentity:
    """Resolve a material name into a MaterialIdentity with grade metadata.

    If grade/supplier/lot/cas are not provided, defaults to TRADE_GRADE
    with an empty identity — this is the weakest resolution and
    should be upgraded when evidence becomes available.
    """
    if grade not in CONTROLLED_GRADES:
        raise ValueError(
            f"grade {grade!r} is not in the controlled identity vocabulary"
        )
    canonical = normalize_name(name)
    if not canonical:
        raise ValueError("material name cannot be empty")
    non_eq = get_non_equivalent_names(name)
    identity_id = _new_id()
    return MaterialIdentity(
        identity_id=identity_id,
        name=name,
        canonical_name=canonical,
        grade=grade,
        supplier=supplier,
        lot=lot,
        cas=cas,
        stereoisomer=stereoisomer,
        trade_grade=trade_grade,
        supplier_product=supplier_product,
        stock_solution=stock_solution,
        physical_dose=physical_dose,
        botanical_species=botanical_species,
        plant_part=plant_part,
        chemotype=chemotype,
        natural_origin=natural_origin,
        extraction_method=extraction_method,
        non_equivalent_names=non_eq,
    )


__all__ = [
    "IdentityGrade",
    "IDENTITY_GRADES",
    "CONTROLLED_GRADES",
    "KNOWN_NON_EQUIVALENT",
    "MaterialIdentity",
    "NaturalGrade",
    "NATURAL_GRADES",
    "are_equivalent",
    "get_non_equivalent_names",
    "resolve_identity",
]
