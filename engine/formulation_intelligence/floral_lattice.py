"""Structural-only floral morphology ontology and hypothesis generation.

The lattice describes target intent, possible flower facets, bouquet relations,
and decision-relevant failure hypotheses.  It deliberately does not select
materials, import recipes, inspect inventory, calculate OAV, predict persistence,
or authorize sensory, hedonic, safety, physical, formula, purchasing, compounding,
stability, performance, or release conclusions.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from types import MappingProxyType
from typing import Any, ClassVar

from .contracts import (
    AssessmentScope,
    AuthorityCeiling,
    ClaimKind,
    CriterionDirection,
    CriterionValue,
    EvidenceClass,
    ParetoCriterion,
    PlaneAssessment,
    PlaneId,
    ProvenanceRef,
    ScopedClaim,
    SupportInterval,
    SupportMeasure,
    UnitInterval,
    UnknownFact,
    _canonical_json_bytes,
    _CanonicalRecord,
    _merged_provenance,
    _normalized_identifier,
    _normalized_text,
    _normalized_text_tuple,
)


def _stable_id(prefix: str, payload: object) -> str:
    digest = sha256(_canonical_json_bytes(payload)).hexdigest()
    return f"{prefix}:{digest[:24]}"


def _slug(value: str) -> str:
    normalized = _normalized_identifier(value, "identifier")
    slug = "".join(character if character.isalnum() else "-" for character in normalized)
    return "-".join(part for part in slug.split("-") if part)


def _strict_bool(value: object, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} must be bool")
    return value


def _unique_records_by_key(
    values: Iterable[Any],
    *,
    key_name: str,
    field_name: str,
) -> tuple[Any, ...]:
    by_key: dict[object, Any] = {}
    for value in values:
        key = getattr(value, key_name)
        if key in by_key:
            raise ValueError(f"{field_name} must contain unique {key_name} values")
        by_key[key] = value
    return tuple(sorted(by_key.values(), key=lambda item: item.content_sha256))


class FloralSubject(str, Enum):
    """Flower subject families required by the design contract."""

    ROSE = "rose"
    JASMINE = "jasmine"
    TUBEROSE = "tuberose"
    MUGUET_LILY = "muguet_lily"
    ORANGE_BLOSSOM_NEROLI = "orange_blossom_neroli"
    IRIS_ORRIS_VIOLET = "iris_orris_violet"
    MAGNOLIA_CHAMPACA = "magnolia_champaca"
    YLANG_GARDENIA_FRANGIPANI = "ylang_gardenia_frangipani"
    OSMANTHUS = "osmanthus"
    MIMOSA_CASSIE_ACACIA = "mimosa_cassie_acacia"
    NARCISSUS_HYACINTH_LILAC_CARNATION_PEONY_LINDEN = (
        "narcissus_hyacinth_lilac_carnation_peony_linden"
    )
    BOUQUET_HYBRID = "bouquet_hybrid"


class FloralSubtype(str, Enum):
    """Exact floral identities carried beneath the broader subject families."""

    ROSE = "rose"
    JASMINE = "jasmine"
    TUBEROSE = "tuberose"
    MUGUET = "muguet"
    LILY = "lily"
    ORANGE_BLOSSOM = "orange_blossom"
    NEROLI = "neroli"
    IRIS = "iris"
    ORRIS = "orris"
    VIOLET = "violet"
    MAGNOLIA = "magnolia"
    CHAMPACA = "champaca"
    YLANG_YLANG = "ylang_ylang"
    GARDENIA = "gardenia"
    FRANGIPANI = "frangipani"
    OSMANTHUS = "osmanthus"
    MIMOSA = "mimosa"
    CASSIE = "cassie"
    ACACIA = "acacia"
    NARCISSUS = "narcissus"
    HYACINTH = "hyacinth"
    LILAC = "lilac"
    CARNATION = "carnation"
    PEONY = "peony"
    LINDEN = "linden"


class FloralAbstraction(str, Enum):
    NATURALISTIC = "naturalistic"
    STYLIZED = "stylized"
    ABSTRACT = "abstract"
    HYBRID = "hybrid"


class FloralFacet(str, Enum):
    """Optional morphology facets; none is a mandatory checklist item."""

    PETAL = "petal"
    POLLEN_STAMEN = "pollen_stamen"
    NECTAR_HONEY = "nectar_honey"
    GREEN_STEM_LEAF = "green_stem_leaf"
    AQUEOUS_DEW = "aqueous_dew"
    SPICE = "spice"
    FRUIT = "fruit"
    TEA = "tea"
    WAX = "wax"
    LACTONE_CREAM = "lactone_cream"
    INDOLIC_ANIMALIC = "indolic_animalic"
    EARTH_ROOT_RHIZOME = "earth_root_rhizome"
    SENESCENT_DRIED = "senescent_dried"
    LEATHER_SUEDE = "leather_suede"
    POWDER_COSMETIC = "powder_cosmetic"
    MINERAL_CONCRETE = "mineral_concrete"
    SOAP = "soap"
    SOLAR = "solar"
    CAMPHOR_MENTHOL = "camphor_menthol"
    RUBBER = "rubber"
    WOOD = "wood"
    HAY = "hay"
    ALMOND = "almond"
    MUSHROOM_PHENOLIC = "mushroom_phenolic"
    AIR_LUMINOSITY = "air_luminosity"
    HUMID = "humid"
    DARK_SHADOW = "dark_shadow"


class FacetRole(str, Enum):
    CORE_RECOGNIZER = "core_recognizer"
    SUPPORT = "support"
    BRIDGE = "bridge"
    CONTRAST = "contrast"
    SHADOW = "shadow"
    TEXTURE = "texture"


class TemporalWindow(str, Enum):
    OPENING = "opening"
    FIVE_MIN = "5m"
    THIRTY_MIN = "30m"
    TWO_HOUR = "2h"
    FOUR_HOUR = "4h"
    EIGHT_HOUR = "8h"
    TWENTY_FOUR_HOUR = "24h"

    @property
    def order(self) -> int:
        return {
            TemporalWindow.OPENING: 0,
            TemporalWindow.FIVE_MIN: 1,
            TemporalWindow.THIRTY_MIN: 2,
            TemporalWindow.TWO_HOUR: 3,
            TemporalWindow.FOUR_HOUR: 4,
            TemporalWindow.EIGHT_HOUR: 5,
            TemporalWindow.TWENTY_FOUR_HOUR: 6,
        }[self]


class TransformationKind(str, Enum):
    CONTINUITY = "continuity"
    REVEAL = "reveal"
    HANDOFF = "handoff"
    CONTRAST = "contrast"
    RESIDUE = "residue"


class BouquetRole(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    BRIDGE = "bridge"
    CONTRAST = "contrast"
    SHADOW = "shadow"


class BouquetRelationKind(str, Enum):
    """Typed relationship semantics between exact bouquet members."""

    OVERLAP = "overlap"
    BRIDGE = "bridge"
    CONTRAST = "contrast"
    SHADOW = "shadow"
    ANTI_TAKEOVER = "anti_takeover"


class FloralCaricature(str, Enum):
    INDOLE = "indole"
    LACTONE = "lactone"
    SALICYLATE = "salicylate"
    IONONE = "ionone"
    ALDEHYDE = "aldehyde"
    GREEN_STEM = "green_stem"


class NaturalMixtureTreatment(str, Enum):
    NOT_APPLICABLE = "not_applicable"
    COMPOSITE = "composite"
    MONOMOLECULAR = "monomolecular"
    UNKNOWN = "unknown"


class PersistenceEvidence(str, Enum):
    NOT_CLAIMED = "not_claimed"
    INTENDED_HYPOTHESIS = "intended_hypothesis"
    MODELED_ONLY = "modeled_only"
    OBSERVED_SCOPED = "observed_scoped"


class FloralFailureMode(str, Enum):
    GENERIC_FLORAL_HEART = "generic floral-heart substitution"
    CANNED_RATIO_REUSE = "canned-ratio reuse without target evidence"
    WHITE_FLORAL_TAKEOVER = "white-floral takeover"
    DISCONNECTED_FRUIT_CITRUS = "disconnected fruit/citrus foreground"
    COMFORT_FOR_DEVELOPMENT = "sweet/musk comfort substituted for development"
    ANONYMOUS_DRYDOWN = "anonymous wood-musk-amber drydown"
    PETAL_BASE_DISCONTINUITY = "petal-to-base discontinuity"
    FACET_CARICATURE = (
        "indole/lactone/salicylate/ionone/aldehyde/green-stem caricature"
    )
    MATERIAL_COUNT_INFLATION = "material-count inflation"
    NATURAL_MIXTURE_MONOMOLECULAR = "natural mixture treated as monomolecular"
    PRESTIGE_TARGET_FIT = "prestige used as target-fit evidence"
    MODELED_PERSISTENCE_AS_OBSERVED = "modeled persistence used as observed continuity"


_SUBTYPE_SPACE: Mapping[FloralSubject, tuple[FloralSubtype, ...]] = MappingProxyType(
    {
        FloralSubject.ROSE: (FloralSubtype.ROSE,),
        FloralSubject.JASMINE: (FloralSubtype.JASMINE,),
        FloralSubject.TUBEROSE: (FloralSubtype.TUBEROSE,),
        FloralSubject.MUGUET_LILY: (FloralSubtype.MUGUET, FloralSubtype.LILY),
        FloralSubject.ORANGE_BLOSSOM_NEROLI: (
            FloralSubtype.ORANGE_BLOSSOM,
            FloralSubtype.NEROLI,
        ),
        FloralSubject.IRIS_ORRIS_VIOLET: (
            FloralSubtype.IRIS,
            FloralSubtype.ORRIS,
            FloralSubtype.VIOLET,
        ),
        FloralSubject.MAGNOLIA_CHAMPACA: (
            FloralSubtype.MAGNOLIA,
            FloralSubtype.CHAMPACA,
        ),
        FloralSubject.YLANG_GARDENIA_FRANGIPANI: (
            FloralSubtype.YLANG_YLANG,
            FloralSubtype.GARDENIA,
            FloralSubtype.FRANGIPANI,
        ),
        FloralSubject.OSMANTHUS: (FloralSubtype.OSMANTHUS,),
        FloralSubject.MIMOSA_CASSIE_ACACIA: (
            FloralSubtype.MIMOSA,
            FloralSubtype.CASSIE,
            FloralSubtype.ACACIA,
        ),
        FloralSubject.NARCISSUS_HYACINTH_LILAC_CARNATION_PEONY_LINDEN: (
            FloralSubtype.NARCISSUS,
            FloralSubtype.HYACINTH,
            FloralSubtype.LILAC,
            FloralSubtype.CARNATION,
            FloralSubtype.PEONY,
            FloralSubtype.LINDEN,
        ),
        FloralSubject.BOUQUET_HYBRID: (),
    }
)


_MULTI_SUBTYPE_SUBJECTS = frozenset(
    subject for subject, subtypes in _SUBTYPE_SPACE.items() if len(subtypes) > 1
)


_EXPRESSION_SPACE: Mapping[FloralSubject, tuple[str, ...]] = MappingProxyType(
    {
        FloralSubject.ROSE: (
            "dark",
            "dewy",
            "dried/potpourri",
            "fresh garden",
            "fruity/damask",
            "green-stemmed",
            "jammy",
            "leathery",
            "mineral",
            "peppery",
            "tea",
        ),
        FloralSubject.JASMINE: (
            "creamy",
            "fruity",
            "green",
            "indolic",
            "luminous",
            "narcotic",
            "nocturnal",
            "tea-like",
        ),
        FloralSubject.TUBEROSE: (
            "animalic",
            "creamy/lactonic",
            "green/camphoraceous",
            "mentholic",
            "narcotic",
            "rubbery",
            "solar",
        ),
        FloralSubject.MUGUET_LILY: (
            "airy",
            "green",
            "pollen",
            "soapy",
            "stem",
            "watery",
            "waxy",
        ),
        FloralSubject.ORANGE_BLOSSOM_NEROLI: (
            "citrus-flower",
            "honeyed",
            "indolic",
            "leafy",
            "solar",
            "waxy",
        ),
        FloralSubject.IRIS_ORRIS_VIOLET: (
            "buttery",
            "carrot",
            "concrete-like",
            "cool",
            "cosmetic",
            "mineral",
            "petal",
            "powder",
            "root/rhizome",
            "suede",
            "woody",
        ),
        FloralSubject.MAGNOLIA_CHAMPACA: (
            "creamy",
            "fruity",
            "green",
            "humid",
            "lemony",
            "pollen",
            "shadowed",
            "spicy",
            "tea",
            "watery",
            "waxy",
        ),
        FloralSubject.YLANG_GARDENIA_FRANGIPANI: (
            "banana-fruity",
            "creamy",
            "green",
            "indolic",
            "lactonic",
            "mushroomy",
            "solar",
            "tropical",
            "waxy",
        ),
        FloralSubject.OSMANTHUS: (
            "apricot",
            "floral",
            "hay",
            "honey",
            "leather/suede",
            "tea",
        ),
        FloralSubject.MIMOSA_CASSIE_ACACIA: (
            "almond",
            "green",
            "honey",
            "pollen",
            "powder",
            "suede",
        ),
        FloralSubject.NARCISSUS_HYACINTH_LILAC_CARNATION_PEONY_LINDEN: (
            "flower-specific green",
            "honeyed",
            "phenolic",
            "pollen",
            "spicy",
            "textural",
            "watery",
        ),
        FloralSubject.BOUQUET_HYBRID: (
            "anti-takeover",
            "bridged",
            "contrasted",
            "hierarchical",
            "overlapping",
        ),
    }
)


_BASE_PETAL = frozenset(
    {
        FloralFacet.PETAL,
        FloralFacet.POLLEN_STAMEN,
        FloralFacet.GREEN_STEM_LEAF,
    }
)
_SUBJECT_FACETS: Mapping[FloralSubject, frozenset[FloralFacet]] = MappingProxyType(
    {
        FloralSubject.ROSE: _BASE_PETAL
        | {
            FloralFacet.NECTAR_HONEY,
            FloralFacet.AQUEOUS_DEW,
            FloralFacet.SPICE,
            FloralFacet.FRUIT,
            FloralFacet.TEA,
            FloralFacet.WAX,
            FloralFacet.INDOLIC_ANIMALIC,
            FloralFacet.SENESCENT_DRIED,
            FloralFacet.LEATHER_SUEDE,
            FloralFacet.MINERAL_CONCRETE,
            FloralFacet.DARK_SHADOW,
        },
        FloralSubject.JASMINE: _BASE_PETAL
        | {
            FloralFacet.NECTAR_HONEY,
            FloralFacet.AQUEOUS_DEW,
            FloralFacet.FRUIT,
            FloralFacet.TEA,
            FloralFacet.WAX,
            FloralFacet.LACTONE_CREAM,
            FloralFacet.INDOLIC_ANIMALIC,
            FloralFacet.AIR_LUMINOSITY,
            FloralFacet.DARK_SHADOW,
        },
        FloralSubject.TUBEROSE: _BASE_PETAL
        | {
            FloralFacet.NECTAR_HONEY,
            FloralFacet.WAX,
            FloralFacet.LACTONE_CREAM,
            FloralFacet.INDOLIC_ANIMALIC,
            FloralFacet.SOLAR,
            FloralFacet.CAMPHOR_MENTHOL,
            FloralFacet.RUBBER,
            FloralFacet.AIR_LUMINOSITY,
        },
        FloralSubject.MUGUET_LILY: _BASE_PETAL
        | {
            FloralFacet.AQUEOUS_DEW,
            FloralFacet.WAX,
            FloralFacet.SOAP,
            FloralFacet.AIR_LUMINOSITY,
        },
        FloralSubject.ORANGE_BLOSSOM_NEROLI: _BASE_PETAL
        | {
            FloralFacet.NECTAR_HONEY,
            FloralFacet.FRUIT,
            FloralFacet.WAX,
            FloralFacet.INDOLIC_ANIMALIC,
            FloralFacet.SOLAR,
        },
        FloralSubject.IRIS_ORRIS_VIOLET: _BASE_PETAL
        | {
            FloralFacet.AQUEOUS_DEW,
            FloralFacet.WAX,
            FloralFacet.LACTONE_CREAM,
            FloralFacet.EARTH_ROOT_RHIZOME,
            FloralFacet.LEATHER_SUEDE,
            FloralFacet.POWDER_COSMETIC,
            FloralFacet.MINERAL_CONCRETE,
            FloralFacet.WOOD,
            FloralFacet.AIR_LUMINOSITY,
        },
        FloralSubject.MAGNOLIA_CHAMPACA: _BASE_PETAL
        | {
            FloralFacet.AQUEOUS_DEW,
            FloralFacet.SPICE,
            FloralFacet.FRUIT,
            FloralFacet.TEA,
            FloralFacet.WAX,
            FloralFacet.LACTONE_CREAM,
            FloralFacet.SOLAR,
            FloralFacet.HUMID,
            FloralFacet.DARK_SHADOW,
        },
        FloralSubject.YLANG_GARDENIA_FRANGIPANI: _BASE_PETAL
        | {
            FloralFacet.NECTAR_HONEY,
            FloralFacet.FRUIT,
            FloralFacet.WAX,
            FloralFacet.LACTONE_CREAM,
            FloralFacet.INDOLIC_ANIMALIC,
            FloralFacet.SOLAR,
            FloralFacet.MUSHROOM_PHENOLIC,
        },
        FloralSubject.OSMANTHUS: _BASE_PETAL
        | {
            FloralFacet.NECTAR_HONEY,
            FloralFacet.FRUIT,
            FloralFacet.TEA,
            FloralFacet.LEATHER_SUEDE,
            FloralFacet.HAY,
        },
        FloralSubject.MIMOSA_CASSIE_ACACIA: _BASE_PETAL
        | {
            FloralFacet.NECTAR_HONEY,
            FloralFacet.POWDER_COSMETIC,
            FloralFacet.LEATHER_SUEDE,
            FloralFacet.ALMOND,
        },
        FloralSubject.NARCISSUS_HYACINTH_LILAC_CARNATION_PEONY_LINDEN: _BASE_PETAL
        | {
            FloralFacet.NECTAR_HONEY,
            FloralFacet.AQUEOUS_DEW,
            FloralFacet.SPICE,
            FloralFacet.MUSHROOM_PHENOLIC,
            FloralFacet.AIR_LUMINOSITY,
        },
        FloralSubject.BOUQUET_HYBRID: frozenset(FloralFacet),
    }
)


_WHITE_FLORAL_SUBJECTS = frozenset(
    {
        FloralSubject.JASMINE,
        FloralSubject.TUBEROSE,
        FloralSubject.ORANGE_BLOSSOM_NEROLI,
        FloralSubject.YLANG_GARDENIA_FRANGIPANI,
    }
)


def expression_space_for(subject: FloralSubject) -> tuple[str, ...]:
    """Return the immutable expression vocabulary for one subject family."""

    return _EXPRESSION_SPACE[FloralSubject(subject)]


def subtype_space_for(subject: FloralSubject) -> tuple[FloralSubtype, ...]:
    """Return exact identities admitted beneath one subject family."""

    return _SUBTYPE_SPACE[FloralSubject(subject)]


def facet_space_for(subject: FloralSubject) -> tuple[FloralFacet, ...]:
    """Return optional, target-eligible facets without implying a checklist."""

    return tuple(sorted(_SUBJECT_FACETS[FloralSubject(subject)], key=lambda item: item.value))


@dataclass(frozen=True, slots=True)
class CustomFloralExpression(_CanonicalRecord):
    """Explicit target vocabulary outside the embedded heuristic expression list."""

    SCHEMA_VERSION: ClassVar[str] = "custom_floral_expression_v1"

    expression_id: str
    label: str
    rationale: str

    def __post_init__(self) -> None:
        expression_id = _normalized_identifier(self.expression_id, "expression_id")
        built_in_ids = {
            _slug(expression)
            for expressions in _EXPRESSION_SPACE.values()
            for expression in expressions
        }
        if expression_id in built_in_ids:
            raise ValueError(
                "custom expression duplicates embedded vocabulary; use requested_expression"
            )
        object.__setattr__(self, "expression_id", expression_id)
        object.__setattr__(self, "label", _normalized_text(self.label, "label"))
        object.__setattr__(
            self,
            "rationale",
            _normalized_text(self.rationale, "rationale"),
        )


@dataclass(frozen=True, slots=True)
class CustomFloralFacet(_CanonicalRecord):
    """Explicit optional facet outside the embedded heuristic facet list."""

    SCHEMA_VERSION: ClassVar[str] = "custom_floral_facet_v1"

    facet_id: str
    label: str

    def __post_init__(self) -> None:
        facet_id = _normalized_identifier(self.facet_id, "facet_id")
        if facet_id in {facet.value for facet in FloralFacet}:
            raise ValueError("custom facet duplicates embedded vocabulary; use FloralFacet")
        object.__setattr__(self, "facet_id", facet_id)
        object.__setattr__(self, "label", _normalized_text(self.label, "label"))


def _normalize_facet(value: FloralFacet | CustomFloralFacet) -> FloralFacet | CustomFloralFacet:
    if isinstance(value, CustomFloralFacet):
        return value
    try:
        return FloralFacet(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(
            "facet must be FloralFacet or an explicit CustomFloralFacet"
        ) from exc


def _facet_key(value: FloralFacet | CustomFloralFacet) -> str:
    if isinstance(value, CustomFloralFacet):
        return f"custom.{value.facet_id}"
    return value.value


def _facet_label(value: FloralFacet | CustomFloralFacet) -> str:
    if isinstance(value, CustomFloralFacet):
        return value.label
    return value.value


@dataclass(frozen=True, slots=True)
class FacetSelection(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "floral_facet_selection_v1"

    subject: FloralSubject
    facet: FloralFacet | CustomFloralFacet
    role: FacetRole
    rationale: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "subject", FloralSubject(self.subject))
        object.__setattr__(self, "facet", _normalize_facet(self.facet))
        object.__setattr__(self, "role", FacetRole(self.role))
        object.__setattr__(self, "rationale", _normalized_text(self.rationale, "rationale"))

    @property
    def selection_key(self) -> tuple[FloralSubject, str]:
        return (self.subject, _facet_key(self.facet))


@dataclass(frozen=True, slots=True)
class FacetOmission(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "floral_facet_omission_v1"

    subject: FloralSubject
    facet: FloralFacet | CustomFloralFacet
    rationale: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "subject", FloralSubject(self.subject))
        object.__setattr__(self, "facet", _normalize_facet(self.facet))
        object.__setattr__(self, "rationale", _normalized_text(self.rationale, "rationale"))

    @property
    def omission_key(self) -> tuple[FloralSubject, str]:
        return (self.subject, _facet_key(self.facet))


@dataclass(frozen=True, slots=True)
class TemporalTransformation(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "floral_temporal_transformation_v1"

    transformation_id: str
    subject: FloralSubject
    from_window: TemporalWindow
    to_window: TemporalWindow
    kind: TransformationKind
    intended_change: str
    protected_recognizers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "transformation_id",
            _normalized_identifier(self.transformation_id, "transformation_id"),
        )
        subject = FloralSubject(self.subject)
        if subject is FloralSubject.BOUQUET_HYBRID:
            raise ValueError("temporal transformations must identify a concrete floral subject")
        object.__setattr__(self, "subject", subject)
        start = TemporalWindow(self.from_window)
        end = TemporalWindow(self.to_window)
        if start.order >= end.order:
            raise ValueError("from_window must precede to_window")
        object.__setattr__(self, "from_window", start)
        object.__setattr__(self, "to_window", end)
        object.__setattr__(self, "kind", TransformationKind(self.kind))
        object.__setattr__(
            self,
            "intended_change",
            _normalized_text(self.intended_change, "intended_change"),
        )
        object.__setattr__(
            self,
            "protected_recognizers",
            _normalized_text_tuple(
                self.protected_recognizers,
                "protected_recognizers",
                identifiers=True,
            ),
        )


@dataclass(frozen=True, slots=True)
class BouquetMember(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "floral_bouquet_member_v1"

    subject: FloralSubject
    role: BouquetRole
    rank: int
    requested_expressions: tuple[str, ...] = ()
    takeover_prohibited: bool = True
    exact_subtype: FloralSubtype | None = None

    def __post_init__(self) -> None:
        subject = FloralSubject(self.subject)
        if subject is FloralSubject.BOUQUET_HYBRID:
            raise ValueError("a bouquet member must be a concrete floral subject")
        object.__setattr__(self, "subject", subject)
        exact_subtype = (
            None if self.exact_subtype is None else FloralSubtype(self.exact_subtype)
        )
        if exact_subtype is not None and exact_subtype not in subtype_space_for(subject):
            raise ValueError(
                f"exact subtype {exact_subtype.value} does not belong to {subject.value}"
            )
        object.__setattr__(self, "exact_subtype", exact_subtype)
        object.__setattr__(self, "role", BouquetRole(self.role))
        if isinstance(self.rank, bool) or not isinstance(self.rank, int):
            raise TypeError("rank must be an integer")
        if self.rank < 0:
            raise ValueError("rank must be nonnegative")
        expressions = _normalized_text_tuple(
            self.requested_expressions,
            "requested_expressions",
            identifiers=True,
        )
        invalid = sorted(set(expressions) - set(expression_space_for(subject)))
        if invalid:
            raise ValueError(
                f"requested_expressions are not valid for {subject.value}: {', '.join(invalid)}"
            )
        object.__setattr__(self, "requested_expressions", expressions)
        object.__setattr__(
            self,
            "takeover_prohibited",
            _strict_bool(self.takeover_prohibited, "takeover_prohibited"),
        )

    @property
    def member_key(self) -> str:
        if self.exact_subtype is not None:
            return self.exact_subtype.value
        return self.subject.value


@dataclass(frozen=True, slots=True)
class BouquetRelation(_CanonicalRecord):
    """One explicit typed relation between exact bouquet member identities."""

    SCHEMA_VERSION: ClassVar[str] = "floral_bouquet_relation_v1"

    relation_id: str
    source_subtype: FloralSubtype
    target_subtype: FloralSubtype
    kind: BouquetRelationKind
    rationale: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "relation_id",
            _normalized_identifier(self.relation_id, "relation_id"),
        )
        source = FloralSubtype(self.source_subtype)
        target = FloralSubtype(self.target_subtype)
        if source is target:
            raise ValueError("a bouquet relation must connect two distinct exact subtypes")
        object.__setattr__(self, "source_subtype", source)
        object.__setattr__(self, "target_subtype", target)
        object.__setattr__(self, "kind", BouquetRelationKind(self.kind))
        object.__setattr__(
            self,
            "rationale",
            _normalized_text(self.rationale, "rationale"),
        )


@dataclass(frozen=True, slots=True)
class NaturalMixtureRepresentation(_CanonicalRecord):
    """Declared representation plus optional independently scoped verification."""

    SCHEMA_VERSION: ClassVar[str] = "floral_natural_mixture_representation_v2"

    mixture_id: str
    declared_treatment: NaturalMixtureTreatment
    verified_treatment: NaturalMixtureTreatment | None = None
    verification_scope: AssessmentScope | None = None
    verification_provenance_refs: tuple[ProvenanceRef, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "mixture_id",
            _normalized_identifier(self.mixture_id, "mixture_id"),
        )
        object.__setattr__(
            self,
            "declared_treatment",
            NaturalMixtureTreatment(self.declared_treatment),
        )
        verified = (
            None
            if self.verified_treatment is None
            else NaturalMixtureTreatment(self.verified_treatment)
        )
        if verified is NaturalMixtureTreatment.UNKNOWN:
            raise ValueError("verified_treatment must be concrete or None")
        object.__setattr__(self, "verified_treatment", verified)
        provenance = _merged_provenance(self.verification_provenance_refs)
        scope = self.verification_scope
        if verified is None:
            if scope is not None or provenance:
                raise ValueError(
                    "verification scope/provenance require a concrete verified_treatment"
                )
        else:
            if not isinstance(scope, AssessmentScope):
                raise TypeError(
                    "verified_treatment requires an exact AssessmentScope"
                )
            if not provenance:
                raise ValueError("verified_treatment requires provenance")
            declarative_classes = {
                EvidenceClass.HEURISTIC,
                EvidenceClass.HISTORICAL_PRIOR,
                EvidenceClass.UNKNOWN,
                EvidenceClass.USER_REPORT,
            }
            if any(item.evidence_class in declarative_classes for item in provenance):
                raise ValueError(
                    "verified_treatment requires non-declarative evidence provenance"
                )
        object.__setattr__(self, "verification_scope", scope)
        object.__setattr__(self, "verification_provenance_refs", provenance)


@dataclass(frozen=True, slots=True)
class MorphologyEvidence(_CanonicalRecord):
    """Exact-claim support supplied by a caller; no evidence class is inferred."""

    SCHEMA_VERSION: ClassVar[str] = "floral_morphology_evidence_v2"

    evidence_id: str
    claim_key: str
    scope: AssessmentScope
    lower: float
    upper: float
    provenance_refs: tuple[ProvenanceRef, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "evidence_id",
            _normalized_identifier(self.evidence_id, "evidence_id"),
        )
        object.__setattr__(
            self,
            "claim_key",
            _normalized_identifier(self.claim_key, "claim_key"),
        )
        if not isinstance(self.scope, AssessmentScope):
            raise TypeError("scope must be an AssessmentScope")
        bounds = UnitInterval(self.lower, self.upper)
        object.__setattr__(self, "lower", bounds.lower)
        object.__setattr__(self, "upper", bounds.upper)
        provenance = _merged_provenance(self.provenance_refs)
        if not provenance:
            raise ValueError("morphology evidence requires provenance")
        object.__setattr__(self, "provenance_refs", provenance)


@dataclass(frozen=True, slots=True)
class FloralCandidateSignals(_CanonicalRecord):
    """Caller-declared structural audit signals, never inferred sensory facts."""

    SCHEMA_VERSION: ClassVar[str] = "floral_candidate_signals_v1"

    generic_floral_heart_substitution: bool = False
    canned_ratio_reuse_without_target_evidence: bool = False
    white_floral_takeover: bool = False
    disconnected_fruit_citrus_foreground: bool = False
    comfort_substituted_for_development: bool = False
    anonymous_wood_musk_amber_drydown: bool = False
    petal_to_base_discontinuity: bool = False
    caricatures: tuple[FloralCaricature, ...] = ()
    declared_material_count: int | None = None
    material_count_used_as_quality_evidence: bool = False
    natural_mixtures: tuple[NaturalMixtureRepresentation, ...] = ()
    prestige_used_as_target_fit_evidence: bool = False
    persistence_evidence: PersistenceEvidence = PersistenceEvidence.NOT_CLAIMED
    persistence_claimed_as_observed_continuity: bool = False
    declared_foreground_subjects: tuple[FloralSubject, ...] = ()

    def __post_init__(self) -> None:
        for field_name in (
            "generic_floral_heart_substitution",
            "canned_ratio_reuse_without_target_evidence",
            "white_floral_takeover",
            "disconnected_fruit_citrus_foreground",
            "comfort_substituted_for_development",
            "anonymous_wood_musk_amber_drydown",
            "petal_to_base_discontinuity",
            "material_count_used_as_quality_evidence",
            "prestige_used_as_target_fit_evidence",
            "persistence_claimed_as_observed_continuity",
        ):
            object.__setattr__(
                self,
                field_name,
                _strict_bool(getattr(self, field_name), field_name),
            )
        caricatures = tuple(
            sorted({FloralCaricature(item) for item in self.caricatures}, key=lambda item: item.value)
        )
        object.__setattr__(self, "caricatures", caricatures)
        if self.declared_material_count is not None:
            if isinstance(self.declared_material_count, bool) or not isinstance(
                self.declared_material_count, int
            ):
                raise TypeError("declared_material_count must be an integer or None")
            if self.declared_material_count < 0:
                raise ValueError("declared_material_count must be nonnegative")
        mixtures = _unique_records_by_key(
            self.natural_mixtures,
            key_name="mixture_id",
            field_name="natural_mixtures",
        )
        if any(not isinstance(item, NaturalMixtureRepresentation) for item in mixtures):
            raise TypeError("natural_mixtures must contain NaturalMixtureRepresentation values")
        object.__setattr__(self, "natural_mixtures", mixtures)
        object.__setattr__(
            self,
            "persistence_evidence",
            PersistenceEvidence(self.persistence_evidence),
        )
        foreground = tuple(
            sorted(
                {FloralSubject(item) for item in self.declared_foreground_subjects},
                key=lambda item: item.value,
            )
        )
        if FloralSubject.BOUQUET_HYBRID in foreground:
            raise ValueError("declared_foreground_subjects must identify concrete subjects")
        object.__setattr__(self, "declared_foreground_subjects", foreground)

    @property
    def assessment_payload(self) -> Mapping[str, Any]:
        """Return count-invariant semantics used by assessment identity/freshness."""

        payload = self.as_dict()
        payload.pop("declared_material_count")
        return MappingProxyType(payload)

    @property
    def assessment_sha256(self) -> str:
        return sha256(_canonical_json_bytes(self.assessment_payload)).hexdigest()


@dataclass(frozen=True, slots=True)
class FloralMorphologyIntent(_CanonicalRecord):
    """Immutable target intent for one structural floral morphology assessment."""

    SCHEMA_VERSION: ClassVar[str] = "floral_morphology_intent_v2"

    flower_subject: FloralSubject
    abstraction_level: FloralAbstraction
    requested_expression: tuple[str, ...]
    protected_recognizers: tuple[str, ...]
    forbidden_drift: tuple[str, ...]
    intended_temporal_transformations: tuple[TemporalTransformation, ...]
    selected_facets: tuple[FacetSelection, ...]
    deliberate_omissions: tuple[FacetOmission, ...]
    bouquet_hierarchy: tuple[BouquetMember, ...]
    exact_subtype: FloralSubtype | None = None
    custom_expressions: tuple[CustomFloralExpression, ...] = ()
    bouquet_relations: tuple[BouquetRelation, ...] = ()

    def __post_init__(self) -> None:
        subject = FloralSubject(self.flower_subject)
        object.__setattr__(self, "flower_subject", subject)
        exact_subtype = (
            None if self.exact_subtype is None else FloralSubtype(self.exact_subtype)
        )
        if subject is FloralSubject.BOUQUET_HYBRID:
            if exact_subtype is not None:
                raise ValueError("bouquet_hybrid cannot declare one exact_subtype")
        elif exact_subtype is not None and exact_subtype not in subtype_space_for(subject):
            raise ValueError(
                f"exact subtype {exact_subtype.value} does not belong to {subject.value}"
            )
        object.__setattr__(self, "exact_subtype", exact_subtype)
        object.__setattr__(
            self,
            "abstraction_level",
            FloralAbstraction(self.abstraction_level),
        )
        custom_expressions = _unique_records_by_key(
            self.custom_expressions,
            key_name="expression_id",
            field_name="custom_expressions",
        )
        if any(
            not isinstance(item, CustomFloralExpression)
            for item in custom_expressions
        ):
            raise TypeError(
                "custom_expressions must contain CustomFloralExpression values"
            )
        object.__setattr__(self, "custom_expressions", custom_expressions)
        expressions = _normalized_text_tuple(
            self.requested_expression,
            "requested_expression",
            identifiers=True,
        )
        invalid_expressions = sorted(set(expressions) - set(expression_space_for(subject)))
        if invalid_expressions:
            raise ValueError(
                f"requested_expression is not valid for {subject.value}: "
                + ", ".join(invalid_expressions)
            )
        if not expressions and not custom_expressions:
            raise ValueError(
                "at least one requested_expression or custom_expressions entry is required"
            )
        object.__setattr__(self, "requested_expression", expressions)
        object.__setattr__(
            self,
            "protected_recognizers",
            _normalized_text_tuple(
                self.protected_recognizers,
                "protected_recognizers",
                allow_empty=False,
                identifiers=True,
            ),
        )
        object.__setattr__(
            self,
            "forbidden_drift",
            _normalized_text_tuple(
                self.forbidden_drift,
                "forbidden_drift",
                identifiers=True,
            ),
        )

        hierarchy = tuple(
            sorted(
                self.bouquet_hierarchy,
                key=lambda item: (item.rank, item.member_key, item.content_sha256),
            )
        )
        if any(not isinstance(item, BouquetMember) for item in hierarchy):
            raise TypeError("bouquet_hierarchy must contain BouquetMember values")
        member_subjects = tuple(item.subject for item in hierarchy)
        member_keys = tuple(item.member_key for item in hierarchy)
        if len(member_keys) != len(set(member_keys)):
            raise ValueError(
                "bouquet_hierarchy must contain unique exact subtype/member keys"
            )
        if subject is FloralSubject.BOUQUET_HYBRID:
            if len(hierarchy) < 2:
                raise ValueError("bouquet_hierarchy requires at least two subjects")
            primaries = tuple(item for item in hierarchy if item.role is BouquetRole.PRIMARY)
            if len(primaries) != 1:
                raise ValueError("bouquet_hierarchy requires exactly one primary subject")
            if primaries[0].rank != min(item.rank for item in hierarchy):
                raise ValueError("the primary bouquet subject must have the highest hierarchy rank")
        elif hierarchy:
            raise ValueError("bouquet_hierarchy is only valid for bouquet_hybrid targets")
        object.__setattr__(self, "bouquet_hierarchy", hierarchy)

        relations = _unique_records_by_key(
            self.bouquet_relations,
            key_name="relation_id",
            field_name="bouquet_relations",
        )
        if any(not isinstance(item, BouquetRelation) for item in relations):
            raise TypeError("bouquet_relations must contain BouquetRelation values")
        if subject is not FloralSubject.BOUQUET_HYBRID and relations:
            raise ValueError("bouquet_relations are only valid for bouquet_hybrid targets")
        known_subtypes = {
            item.exact_subtype
            for item in hierarchy
            if item.exact_subtype is not None
        }
        unresolved_subtypes = {
            endpoint
            for relation in relations
            for endpoint in (relation.source_subtype, relation.target_subtype)
            if endpoint not in known_subtypes
        }
        if unresolved_subtypes:
            names = ", ".join(sorted(item.value for item in unresolved_subtypes))
            raise ValueError(
                f"bouquet relation references unknown exact subtypes: {names}"
            )
        object.__setattr__(self, "bouquet_relations", relations)

        allowed_subjects = (
            set(member_subjects)
            if subject is FloralSubject.BOUQUET_HYBRID
            else {subject}
        )
        facets = tuple(
            sorted(
                self.selected_facets,
                key=lambda item: (
                    item.subject.value,
                    _facet_key(item.facet),
                    item.content_sha256,
                ),
            )
        )
        if any(not isinstance(item, FacetSelection) for item in facets):
            raise TypeError("selected_facets must contain FacetSelection values")
        facet_keys = tuple(item.selection_key for item in facets)
        if len(facet_keys) != len(set(facet_keys)):
            raise ValueError("selected_facets must contain unique subject/facet pairs")
        omissions = tuple(
            sorted(
                self.deliberate_omissions,
                key=lambda item: (
                    item.subject.value,
                    _facet_key(item.facet),
                    item.content_sha256,
                ),
            )
        )
        if any(not isinstance(item, FacetOmission) for item in omissions):
            raise TypeError("deliberate_omissions must contain FacetOmission values")
        omission_keys = tuple(item.omission_key for item in omissions)
        if len(omission_keys) != len(set(omission_keys)):
            raise ValueError("deliberate_omissions must contain unique subject/facet pairs")
        overlap = sorted(set(facet_keys) & set(omission_keys), key=lambda item: repr(item))
        if overlap:
            raise ValueError("a facet cannot be both selected and deliberately omitted")
        for item in facets:
            if item.subject not in allowed_subjects:
                raise ValueError(
                    f"facet subject {item.subject.value} is outside the target hierarchy"
                )
            if isinstance(item.facet, FloralFacet) and item.facet not in _SUBJECT_FACETS[item.subject]:
                raise ValueError(
                    f"facet {item.facet.value} is not target-appropriate for {item.subject.value}"
                )
        for omission in omissions:
            if omission.subject not in allowed_subjects:
                raise ValueError(
                    f"facet subject {omission.subject.value} is outside the target hierarchy"
                )
            if (
                isinstance(omission.facet, FloralFacet)
                and omission.facet not in _SUBJECT_FACETS[omission.subject]
            ):
                raise ValueError(
                    f"facet {omission.facet.value} is not target-appropriate for "
                    f"{omission.subject.value}"
                )
        object.__setattr__(self, "selected_facets", facets)
        object.__setattr__(self, "deliberate_omissions", omissions)

        transformations = _unique_records_by_key(
            self.intended_temporal_transformations,
            key_name="transformation_id",
            field_name="intended_temporal_transformations",
        )
        if any(not isinstance(item, TemporalTransformation) for item in transformations):
            raise TypeError(
                "intended_temporal_transformations must contain TemporalTransformation values"
            )
        for item in transformations:
            if item.subject not in allowed_subjects:
                raise ValueError(
                    f"temporal subject {item.subject.value} is outside the target hierarchy"
                )
        object.__setattr__(self, "intended_temporal_transformations", transformations)


def _primary_subjects(intent: FloralMorphologyIntent) -> frozenset[FloralSubject]:
    if intent.flower_subject is not FloralSubject.BOUQUET_HYBRID:
        return frozenset({intent.flower_subject})
    return frozenset(
        member.subject
        for member in intent.bouquet_hierarchy
        if member.role is BouquetRole.PRIMARY
    )


def detect_floral_failure_modes(
    intent: FloralMorphologyIntent,
    signals: FloralCandidateSignals | None = None,
) -> tuple[FloralFailureMode, ...]:
    """Detect only declared structural risks; no sensory outcome is inferred."""

    if not isinstance(intent, FloralMorphologyIntent):
        raise TypeError("intent must be a FloralMorphologyIntent")
    candidate = signals or FloralCandidateSignals()
    if not isinstance(candidate, FloralCandidateSignals):
        raise TypeError("signals must be FloralCandidateSignals or None")
    detected: set[FloralFailureMode] = set()
    if candidate.generic_floral_heart_substitution:
        detected.add(FloralFailureMode.GENERIC_FLORAL_HEART)
    if candidate.canned_ratio_reuse_without_target_evidence:
        detected.add(FloralFailureMode.CANNED_RATIO_REUSE)
    if candidate.white_floral_takeover:
        detected.add(FloralFailureMode.WHITE_FLORAL_TAKEOVER)

    primaries = _primary_subjects(intent)
    prohibited_takeover = {
        member.subject
        for member in intent.bouquet_hierarchy
        if member.takeover_prohibited
    }
    for foreground in candidate.declared_foreground_subjects:
        if foreground in _WHITE_FLORAL_SUBJECTS and foreground not in primaries:
            if intent.flower_subject is not FloralSubject.BOUQUET_HYBRID or (
                foreground in prohibited_takeover
            ):
                detected.add(FloralFailureMode.WHITE_FLORAL_TAKEOVER)
    if candidate.disconnected_fruit_citrus_foreground:
        detected.add(FloralFailureMode.DISCONNECTED_FRUIT_CITRUS)
    if candidate.comfort_substituted_for_development:
        detected.add(FloralFailureMode.COMFORT_FOR_DEVELOPMENT)
    if candidate.anonymous_wood_musk_amber_drydown:
        detected.add(FloralFailureMode.ANONYMOUS_DRYDOWN)
    if candidate.petal_to_base_discontinuity:
        detected.add(FloralFailureMode.PETAL_BASE_DISCONTINUITY)
    if candidate.caricatures:
        detected.add(FloralFailureMode.FACET_CARICATURE)
    if candidate.material_count_used_as_quality_evidence:
        detected.add(FloralFailureMode.MATERIAL_COUNT_INFLATION)
    if any(
        item.declared_treatment is NaturalMixtureTreatment.MONOMOLECULAR
        or item.verified_treatment is NaturalMixtureTreatment.MONOMOLECULAR
        for item in candidate.natural_mixtures
    ):
        detected.add(FloralFailureMode.NATURAL_MIXTURE_MONOMOLECULAR)
    if candidate.prestige_used_as_target_fit_evidence:
        detected.add(FloralFailureMode.PRESTIGE_TARGET_FIT)
    if (
        candidate.persistence_evidence is PersistenceEvidence.MODELED_ONLY
        and candidate.persistence_claimed_as_observed_continuity
    ):
        detected.add(FloralFailureMode.MODELED_PERSISTENCE_AS_OBSERVED)
    return tuple(sorted(detected, key=lambda item: item.value))


def _ontology_payload() -> Mapping[str, Any]:
    return {
        "expressions": {
            subject.value: expressions for subject, expressions in _EXPRESSION_SPACE.items()
        },
        "facets": {
            subject.value: tuple(sorted(facet.value for facet in facets))
            for subject, facets in _SUBJECT_FACETS.items()
        },
        "subtypes": {
            subject.value: tuple(subtype.value for subtype in subtypes)
            for subject, subtypes in _SUBTYPE_SPACE.items()
        },
        "bouquet_relation_kinds": tuple(
            sorted(item.value for item in BouquetRelationKind)
        ),
        "failure_modes": tuple(sorted(item.value for item in FloralFailureMode)),
    }


_ONTOLOGY_SHA256 = sha256(_canonical_json_bytes(_ontology_payload())).hexdigest()


def _request_provenance(intent: FloralMorphologyIntent) -> ProvenanceRef:
    return ProvenanceRef(
        provenance_id=f"floral-intent:{intent.content_sha256[:24]}",
        source_ref=f"request://floral-morphology/{intent.content_sha256}",
        evidence_class=EvidenceClass.USER_REPORT,
        independence_key=f"target-intent:{intent.content_sha256}",
    )


def _ontology_provenance() -> ProvenanceRef:
    return ProvenanceRef(
        provenance_id="floral-lattice:ontology-v2",
        source_ref=f"embedded://floral-lattice/ontology/{_ONTOLOGY_SHA256}",
        evidence_class=EvidenceClass.HEURISTIC,
        independence_key=f"heuristic-ontology:{_ONTOLOGY_SHA256}",
        source_sha256=_ONTOLOGY_SHA256,
    )


def _candidate_provenance(signals: FloralCandidateSignals) -> ProvenanceRef:
    return ProvenanceRef(
        provenance_id=f"floral-signals:{signals.assessment_sha256[:24]}",
        source_ref=f"input://floral-candidate-signals/{signals.assessment_sha256}",
        evidence_class=EvidenceClass.HEURISTIC,
        independence_key=f"candidate-audit:{signals.assessment_sha256}",
    )


@dataclass(frozen=True, slots=True)
class _ClaimDraft:
    claim_key: str
    claim_value: str
    claim_kind: ClaimKind
    provenance_refs: tuple[ProvenanceRef, ...]
    support_measure: SupportMeasure = SupportMeasure.DECLARATION_PRESENCE


def _claim_drafts(
    intent: FloralMorphologyIntent,
    signals: FloralCandidateSignals,
    failures: tuple[FloralFailureMode, ...],
    request_ref: ProvenanceRef,
    ontology_ref: ProvenanceRef,
    candidate_ref: ProvenanceRef,
) -> tuple[_ClaimDraft, ...]:
    drafts: list[_ClaimDraft] = [
        _ClaimDraft(
            claim_key="morphology.subject",
            claim_value=f"Declared floral subject: {intent.flower_subject.value}.",
            claim_kind=ClaimKind.REQUIREMENT,
            provenance_refs=(request_ref, ontology_ref),
        ),
        _ClaimDraft(
            claim_key="morphology.abstraction",
            claim_value=f"Declared abstraction level: {intent.abstraction_level.value}.",
            claim_kind=ClaimKind.REQUIREMENT,
            provenance_refs=(request_ref,),
        ),
    ]
    if intent.exact_subtype is not None:
        drafts.append(
            _ClaimDraft(
                claim_key=f"morphology.exact_subtype.{intent.exact_subtype.value}",
                claim_value=(
                    f"Declared exact floral subtype: {intent.exact_subtype.value} "
                    f"within {intent.flower_subject.value}."
                ),
                claim_kind=ClaimKind.REQUIREMENT,
                provenance_refs=(request_ref, ontology_ref),
            )
        )
    for expression in intent.requested_expression:
        drafts.append(
            _ClaimDraft(
                claim_key=f"morphology.expression.{_slug(expression)}",
                claim_value=(
                    f"Requested {intent.flower_subject.value} expression: {expression}."
                ),
                claim_kind=ClaimKind.REQUIREMENT,
                provenance_refs=(request_ref, ontology_ref),
            )
        )
    for custom_expression in intent.custom_expressions:
        drafts.append(
            _ClaimDraft(
                claim_key=(
                    "morphology.expression.custom."
                    f"{custom_expression.expression_id}"
                ),
                claim_value=(
                    f"Requested explicit custom {intent.flower_subject.value} expression "
                    f"{custom_expression.label}: {custom_expression.rationale}"
                ),
                claim_kind=ClaimKind.REQUIREMENT,
                provenance_refs=(request_ref,),
            )
        )
    for recognizer in intent.protected_recognizers:
        drafts.append(
            _ClaimDraft(
                claim_key=f"morphology.protected_recognizer.{_slug(recognizer)}",
                claim_value=f"Preserve declared recognizer: {recognizer}.",
                claim_kind=ClaimKind.REQUIREMENT,
                provenance_refs=(request_ref,),
            )
        )
    for drift in intent.forbidden_drift:
        drafts.append(
            _ClaimDraft(
                claim_key=f"morphology.forbidden_drift.{_slug(drift)}",
                claim_value=f"Prohibit declared target drift: {drift}.",
                claim_kind=ClaimKind.PROHIBITION,
                provenance_refs=(request_ref,),
            )
        )
    for facet in intent.selected_facets:
        facet_key = _facet_key(facet.facet)
        facet_label = _facet_label(facet.facet)
        drafts.append(
            _ClaimDraft(
                claim_key=(
                    f"morphology.facet.{facet.subject.value}.{facet_key}"
                ),
                claim_value=(
                    f"Selected optional {facet.subject.value} facet {facet_label} "
                    f"for the target-linked role {facet.role.value}: {facet.rationale}"
                ),
                claim_kind=ClaimKind.HYPOTHESIS,
                provenance_refs=(
                    (request_ref, ontology_ref)
                    if isinstance(facet.facet, FloralFacet)
                    else (request_ref,)
                ),
            )
        )
    for omission in intent.deliberate_omissions:
        facet_key = _facet_key(omission.facet)
        facet_label = _facet_label(omission.facet)
        drafts.append(
            _ClaimDraft(
                claim_key=(
                    f"morphology.omission.{omission.subject.value}.{facet_key}"
                ),
                claim_value=(
                    f"Deliberately omit {omission.subject.value} facet "
                    f"{facet_label}: {omission.rationale}"
                ),
                claim_kind=ClaimKind.PROHIBITION,
                provenance_refs=(
                    (request_ref, ontology_ref)
                    if isinstance(omission.facet, FloralFacet)
                    else (request_ref,)
                ),
            )
        )
    for transformation in intent.intended_temporal_transformations:
        protected = ", ".join(transformation.protected_recognizers) or "none declared"
        drafts.append(
            _ClaimDraft(
                claim_key=f"morphology.temporal.{transformation.transformation_id}",
                claim_value=(
                    f"Intended {transformation.subject.value} {transformation.kind.value} "
                    f"from {transformation.from_window.value} to {transformation.to_window.value}: "
                    f"{transformation.intended_change} Protected recognizers: {protected}."
                ),
                claim_kind=ClaimKind.HYPOTHESIS,
                provenance_refs=(request_ref, ontology_ref),
            )
        )
    member_subject_counts = {
        subject: sum(
            member.subject is subject for member in intent.bouquet_hierarchy
        )
        for subject in {member.subject for member in intent.bouquet_hierarchy}
    }
    for member in intent.bouquet_hierarchy:
        expressions = ", ".join(member.requested_expressions) or "unspecified"
        subtype = (
            member.exact_subtype.value
            if member.exact_subtype is not None
            else "not declared"
        )
        member_claim_key = (
            member.subject.value
            if member_subject_counts[member.subject] == 1
            else member.member_key
        )
        drafts.append(
            _ClaimDraft(
                claim_key=f"morphology.bouquet.{member_claim_key}",
                claim_value=(
                    f"Bouquet member {member.subject.value} has role {member.role.value}, "
                    f"exact subtype {subtype}, rank {member.rank}, expressions "
                    f"{expressions}, and anti-takeover "
                    f"{'on' if member.takeover_prohibited else 'off'}."
                ),
                claim_kind=ClaimKind.HYPOTHESIS,
                provenance_refs=(request_ref, ontology_ref),
            )
        )
    for relation in intent.bouquet_relations:
        drafts.append(
            _ClaimDraft(
                claim_key=f"morphology.bouquet_relation.{relation.relation_id}",
                claim_value=(
                    f"Declared {relation.kind.value} relation from exact subtype "
                    f"{relation.source_subtype.value} to "
                    f"{relation.target_subtype.value}: {relation.rationale}"
                ),
                claim_kind=ClaimKind.HYPOTHESIS,
                provenance_refs=(request_ref, ontology_ref),
            )
        )
    for mixture in signals.natural_mixtures:
        drafts.append(
            _ClaimDraft(
                claim_key=(
                    f"morphology.natural_mixture.{mixture.mixture_id}.declaration"
                ),
                claim_value=(
                    f"Natural-mixture representation {mixture.mixture_id} is declared "
                    f"{mixture.declared_treatment.value}; this declaration is not "
                    "composite verification."
                ),
                claim_kind=ClaimKind.DIAGNOSTIC,
                provenance_refs=(candidate_ref, ontology_ref),
            )
        )
        if mixture.verified_treatment is not None:
            drafts.append(
                _ClaimDraft(
                    claim_key=(
                        f"morphology.natural_mixture.{mixture.mixture_id}.verification"
                    ),
                    claim_value=(
                        f"Exact-scope evidence verifies natural-mixture representation "
                        f"{mixture.mixture_id} as {mixture.verified_treatment.value}."
                    ),
                    claim_kind=ClaimKind.OBSERVATION,
                    provenance_refs=mixture.verification_provenance_refs,
                    # The interval records that the categorical verification
                    # record exists; it is not a numeric confidence estimate.
                    support_measure=SupportMeasure.DECLARATION_PRESENCE,
                )
            )
    for failure in failures:
        details = ""
        if failure is FloralFailureMode.FACET_CARICATURE:
            details = ": " + ", ".join(item.value for item in signals.caricatures)
        drafts.append(
            _ClaimDraft(
                claim_key=f"morphology.failure.{_slug(failure.value)}",
                claim_value=f"Declared structural failure signal: {failure.value}{details}.",
                claim_kind=ClaimKind.DIAGNOSTIC,
                provenance_refs=(candidate_ref, ontology_ref),
            )
        )
    by_key: dict[str, _ClaimDraft] = {}
    for draft in drafts:
        normalized_key = _normalized_identifier(draft.claim_key, "claim_key")
        if normalized_key in by_key:
            raise ValueError(f"generated duplicate claim_key {normalized_key!r}")
        by_key[normalized_key] = draft
    return tuple(by_key[key] for key in sorted(by_key))


def _unknowns(
    intent: FloralMorphologyIntent,
    signals: FloralCandidateSignals,
    provenance_refs: tuple[ProvenanceRef, ...],
) -> tuple[UnknownFact, ...]:
    unknowns = [
        UnknownFact(
            unknown_id="unknown:morphology:target-fidelity",
            field_key="morphology.sensory_target_fidelity",
            reason="No exact-scope participant-linked sensory observation is supplied.",
            needed_evidence="Blinded target-criterion evaluation in the exact matrix and time scope.",
            provenance_refs=provenance_refs,
        ),
        UnknownFact(
            unknown_id="unknown:morphology:mixture-expression",
            field_key="morphology.mixture_expression",
            reason="Declared facets and relations do not establish mixture perception.",
            needed_evidence="Controlled omission and recombination observations at constant total.",
            provenance_refs=provenance_refs,
        ),
        UnknownFact(
            unknown_id="unknown:morphology:temporal-continuity",
            field_key="morphology.temporal_subject_continuity",
            reason="Intended transformations and modeled persistence are not observed continuity.",
            needed_evidence="Coded time-resolved observation linked to protected recognizers.",
            provenance_refs=provenance_refs,
        ),
        UnknownFact(
            unknown_id="unknown:morphology:liking",
            field_key="morphology.scoped_liking",
            reason="The morphology ontology contains no participant-linked preference evidence.",
            needed_evidence="Blinded participant- and criterion-scoped preference observations.",
            provenance_refs=provenance_refs,
        ),
    ]
    if not intent.selected_facets:
        unknowns.append(
            UnknownFact(
                unknown_id="unknown:morphology:optional-facets",
                field_key="morphology.selected_facets",
                reason="No optional target facet was selected; absence is not scored as a defect.",
                needed_evidence="A target-linked facet hypothesis only if the decision requires one.",
                provenance_refs=provenance_refs,
            )
        )
    if not intent.intended_temporal_transformations:
        unknowns.append(
            UnknownFact(
                unknown_id="unknown:morphology:intended-transformations",
                field_key="morphology.intended_temporal_transformations",
                reason="No temporal transformation was declared.",
                needed_evidence="A target-linked intended transformation before temporal testing.",
                provenance_refs=provenance_refs,
            )
        )
    if (
        intent.flower_subject in _MULTI_SUBTYPE_SUBJECTS
        and intent.exact_subtype is None
    ):
        unknowns.append(
            UnknownFact(
                unknown_id=(
                    f"unknown:morphology:exact-subtype:{intent.flower_subject.value}"
                ),
                field_key=f"morphology.exact_subtype.{intent.flower_subject.value}",
                reason=(
                    "The grouped floral subject does not identify which exact subtype "
                    "is intended."
                ),
                needed_evidence=(
                    "An explicit exact-subtype target declaration; this is not a "
                    "sensory or empirical inference."
                ),
                provenance_refs=provenance_refs,
            )
        )
    for member in intent.bouquet_hierarchy:
        if member.subject in _MULTI_SUBTYPE_SUBJECTS and member.exact_subtype is None:
            unknowns.append(
                UnknownFact(
                    unknown_id=(
                        f"unknown:morphology:bouquet-subtype:{member.member_key}"
                    ),
                    field_key=f"morphology.bouquet_subtype.{member.member_key}",
                    reason="A grouped bouquet member has no exact subtype declaration.",
                    needed_evidence="An explicit exact-subtype target declaration.",
                    provenance_refs=provenance_refs,
                )
            )
    for mixture in signals.natural_mixtures:
        if mixture.declared_treatment is NaturalMixtureTreatment.UNKNOWN:
            unknowns.append(
                UnknownFact(
                    unknown_id=f"unknown:morphology:natural:{mixture.mixture_id}",
                    field_key=f"morphology.natural_mixture.{mixture.mixture_id}",
                    reason="Natural-mixture constituent representation is unknown.",
                    needed_evidence="A provenance-bound composite constituent representation.",
                    provenance_refs=provenance_refs,
                )
            )
        if (
            mixture.declared_treatment is NaturalMixtureTreatment.COMPOSITE
            and mixture.verified_treatment is not NaturalMixtureTreatment.COMPOSITE
        ):
            unknowns.append(
                UnknownFact(
                    unknown_id=(
                        f"unknown:morphology:natural-composite:{mixture.mixture_id}"
                    ),
                    field_key=(
                        f"morphology.natural_mixture.{mixture.mixture_id}."
                        "composite_verification"
                    ),
                    reason=(
                        "Composite treatment is declared but not verified by "
                        "exact-scope non-declarative evidence."
                    ),
                    needed_evidence=(
                        "A provenance-bound composite constituent representation "
                        "with the exact assessment scope."
                    ),
                    provenance_refs=provenance_refs,
                )
            )
    return tuple(unknowns)


def _criteria(provenance_refs: tuple[ProvenanceRef, ...]) -> tuple[ParetoCriterion, ...]:
    specifications = (
        (
            "facet_nonredundancy",
            CriterionDirection.MAXIMIZE,
            "Requires controlled omission/recombination; facet count is not evidence.",
        ),
        (
            "recognizer_integrity",
            CriterionDirection.PRESERVE,
            "Requires exact-scope observation of each protected recognizer.",
        ),
        (
            "target_fidelity",
            CriterionDirection.MAXIMIZE,
            "Requires criterion-scoped target evaluation.",
        ),
        (
            "takeover_resistance",
            CriterionDirection.MAXIMIZE,
            "Requires a controlled foreground/takeover comparison.",
        ),
        (
            "temporal_subject_continuity",
            CriterionDirection.MAXIMIZE,
            "Requires time-resolved observation; modeled persistence is insufficient.",
        ),
    )
    return tuple(
        ParetoCriterion(
            criterion_id=criterion_id,
            direction=direction,
            value=CriterionValue.unknown(reason),
            unit="exact-scope evidence state",
            authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
            provenance_refs=provenance_refs,
        )
        for criterion_id, direction, reason in specifications
    )


_FAILURE_EXPERIMENTS: Mapping[FloralFailureMode, str] = MappingProxyType(
    {
        FloralFailureMode.GENERIC_FLORAL_HEART: (
            "compare the target-linked morphology with a generic floral-heart substitution"
        ),
        FloralFailureMode.CANNED_RATIO_REUSE: (
            "run a constant-total ratio sweep against the unsupported canned-ratio control"
        ),
        FloralFailureMode.WHITE_FLORAL_TAKEOVER: (
            "compare the declared hierarchy with a white-floral takeover arm"
        ),
        FloralFailureMode.DISCONNECTED_FRUIT_CITRUS: (
            "compare connected, omitted, and foreground fruit/citrus arms"
        ),
        FloralFailureMode.COMFORT_FOR_DEVELOPMENT: (
            "compare target development with the sweet/musk comfort substitution"
        ),
        FloralFailureMode.ANONYMOUS_DRYDOWN: (
            "compare protected subject residue with the anonymous wood-musk-amber arm"
        ),
        FloralFailureMode.PETAL_BASE_DISCONTINUITY: (
            "compare the declared bridge with a bridge-omission discontinuity arm"
        ),
        FloralFailureMode.FACET_CARICATURE: (
            "run omission and bounded-contrast arms for each declared caricature risk"
        ),
        FloralFailureMode.MATERIAL_COUNT_INFLATION: (
            "compare sparse and dense structurally equivalent arms without count credit"
        ),
        FloralFailureMode.NATURAL_MIXTURE_MONOMOLECULAR: (
            "audit composite representation against the invalid monomolecular baseline"
        ),
        FloralFailureMode.PRESTIGE_TARGET_FIT: (
            "blind the prestige label and compare target-linked function only"
        ),
        FloralFailureMode.MODELED_PERSISTENCE_AS_OBSERVED: (
            "compare modeled persistence with coded observed subject continuity"
        ),
    }
)


def _experiments(
    intent: FloralMorphologyIntent,
    scope: AssessmentScope,
    failures: tuple[FloralFailureMode, ...],
) -> tuple[str, ...]:
    label = intent.flower_subject.value.replace("_", " ")
    experiments = [
        (
            f"{label}: constant-total, matrix-matched comparison of the target-linked "
            "morphology against a generic floral-heart control, judged only on protected "
            "recognizers and declared drift."
        ),
        (
            f"{label}: coded time-resolved comparison across {scope.temporal_scope} to test "
            "intended subject continuity rather than modeled persistence."
        ),
    ]
    if intent.selected_facets:
        facet_labels = ", ".join(
            f"{item.subject.value}:{_facet_label(item.facet)}"
            for item in intent.selected_facets
        )
        experiments.append(
            f"{label}: constant-total omission/recombination comparison for optional facets "
            f"{facet_labels}, with protected recognizers held as separate criteria."
        )
    if intent.bouquet_hierarchy:
        experiments.append(
            f"{label}: compare the declared bouquet hierarchy with overlap, bridge-omission, "
            "and anti-takeover arms while retaining each subject criterion separately."
        )
    for failure in failures:
        experiments.append(
            f"{label}: {_FAILURE_EXPERIMENTS[failure]} at constant total and exact scope."
        )
    return tuple(experiments)


def assess_floral_morphology(
    intent: FloralMorphologyIntent,
    *,
    scope: AssessmentScope,
    evidence: Iterable[MorphologyEvidence] = (),
    candidate_signals: FloralCandidateSignals | None = None,
) -> PlaneAssessment:
    """Emit one deterministic morphology-plane packet with structural authority only.

    The function is the read-only adapter boundary for later plane synthesis.  It
    accepts explicit target intent, exact scope, optional provenance-bearing claim
    support, and caller-declared audit signals.  It does not load or mutate runtime
    state, and its result can be passed directly to ``synthesize_plane_assessments``.
    """

    if not isinstance(intent, FloralMorphologyIntent):
        raise TypeError("intent must be a FloralMorphologyIntent")
    if not isinstance(scope, AssessmentScope):
        raise TypeError("scope must be an AssessmentScope")
    signals = candidate_signals or FloralCandidateSignals()
    if not isinstance(signals, FloralCandidateSignals):
        raise TypeError("candidate_signals must be FloralCandidateSignals or None")
    evidence_records = _unique_records_by_key(
        evidence,
        key_name="evidence_id",
        field_name="evidence",
    )
    if any(not isinstance(item, MorphologyEvidence) for item in evidence_records):
        raise TypeError("evidence must contain MorphologyEvidence values")
    mismatched_evidence = tuple(
        item.evidence_id for item in evidence_records if item.scope != scope
    )
    if mismatched_evidence:
        raise ValueError(
            "morphology evidence must match the exact assessment scope: "
            + ", ".join(mismatched_evidence)
        )
    mismatched_mixtures = tuple(
        item.mixture_id
        for item in signals.natural_mixtures
        if item.verified_treatment is not None and item.verification_scope != scope
    )
    if mismatched_mixtures:
        raise ValueError(
            "natural-mixture verification must match the exact assessment scope: "
            + ", ".join(mismatched_mixtures)
        )

    request_ref = _request_provenance(intent)
    ontology_ref = _ontology_provenance()
    candidate_ref = _candidate_provenance(signals)
    failures = detect_floral_failure_modes(intent, signals)
    drafts = _claim_drafts(
        intent,
        signals,
        failures,
        request_ref,
        ontology_ref,
        candidate_ref,
    )
    draft_keys = {draft.claim_key for draft in drafts}
    unmatched = sorted(
        item.claim_key for item in evidence_records if item.claim_key not in draft_keys
    )
    if unmatched:
        raise ValueError("evidence references unknown claim_key values: " + ", ".join(unmatched))
    evidence_by_key: dict[str, list[MorphologyEvidence]] = {}
    for item in evidence_records:
        evidence_by_key.setdefault(item.claim_key, []).append(item)

    claims: list[ScopedClaim] = []
    intervals: list[SupportInterval] = []
    for draft in drafts:
        linked_evidence = tuple(evidence_by_key.get(draft.claim_key, ()))
        claim_provenance = _merged_provenance(
            (
                *draft.provenance_refs,
                *(ref for item in linked_evidence for ref in item.provenance_refs),
            )
        )
        claim_id = _stable_id(
            "floral-claim",
            {
                "key": draft.claim_key,
                "value": draft.claim_value,
                "kind": draft.claim_kind.value,
            },
        )
        claim = ScopedClaim(
            claim_id=claim_id,
            claim_key=draft.claim_key,
            claim_value=draft.claim_value,
            claim_kind=draft.claim_kind,
            authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
            provenance_refs=claim_provenance,
        )
        claims.append(claim)
        intervals.append(
            SupportInterval(
                interval_id=_stable_id(
                    "floral-native-support",
                    {
                        "claim_id": claim_id,
                        "measure": draft.support_measure.value,
                        "provenance": draft.provenance_refs,
                    },
                ),
                claim_id=claim_id,
                lower=1.0,
                upper=1.0,
                provenance_refs=draft.provenance_refs,
                support_measure=draft.support_measure,
            )
        )
        for item in linked_evidence:
            intervals.append(
                SupportInterval(
                    interval_id=_stable_id(
                        "floral-evidence-support",
                        {"claim_id": claim_id, "evidence": item.as_dict()},
                    ),
                    claim_id=claim_id,
                    lower=item.lower,
                    upper=item.upper,
                    provenance_refs=item.provenance_refs,
                    support_measure=SupportMeasure.EVIDENCE_SUPPORT,
                )
            )

    core_provenance = (request_ref, ontology_ref, candidate_ref)
    unknowns = _unknowns(intent, signals, core_provenance)
    criteria = _criteria((request_ref, ontology_ref))
    experiments = _experiments(intent, scope, failures)
    assessment_payload = {
        "scope": scope.as_dict(),
        "claims": tuple(claim.as_dict() for claim in claims),
        "support_intervals": tuple(item.as_dict() for item in intervals),
        "unknowns": tuple(item.as_dict() for item in unknowns),
        "failures": tuple(item.value for item in failures),
        "experiments": experiments,
        "criteria": tuple(item.as_dict() for item in criteria),
    }
    freshness = {
        _ONTOLOGY_SHA256,
        intent.content_sha256,
        signals.assessment_sha256,
        scope.content_sha256,
        *(item.content_sha256 for item in evidence_records),
        *(
            ref.source_sha256
            for item in signals.natural_mixtures
            for ref in item.verification_provenance_refs
            if ref.source_sha256 is not None
        ),
    }
    return PlaneAssessment(
        assessment_id=_stable_id("floral-morphology", assessment_payload),
        module_id="floral-lattice-v2",
        plane_id=PlaneId.MORPHOLOGY,
        scope=scope,
        claims=tuple(claims),
        support_intervals=tuple(intervals),
        conflicts=(),
        unknowns=unknowns,
        failure_modes=tuple(item.value for item in failures),
        proposed_experiments=experiments,
        provenance_refs=_merged_provenance(
            (
                *core_provenance,
                *(ref for item in evidence_records for ref in item.provenance_refs),
                *(
                    ref
                    for item in signals.natural_mixtures
                    for ref in item.verification_provenance_refs
                ),
            )
        ),
        authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
        freshness_hashes=tuple(sorted(freshness)),
        native_criteria=criteria,
    )


@dataclass(frozen=True, slots=True)
class FloralMorphologyPlaneAdapter:
    """Frozen read-only adapter satisfying the plane-synthesis protocol structurally."""

    intent: FloralMorphologyIntent
    scope: AssessmentScope
    evidence: tuple[MorphologyEvidence, ...] = ()
    candidate_signals: FloralCandidateSignals = FloralCandidateSignals()

    def __post_init__(self) -> None:
        if not isinstance(self.intent, FloralMorphologyIntent):
            raise TypeError("intent must be a FloralMorphologyIntent")
        if not isinstance(self.scope, AssessmentScope):
            raise TypeError("scope must be an AssessmentScope")
        evidence = _unique_records_by_key(
            self.evidence,
            key_name="evidence_id",
            field_name="evidence",
        )
        if any(not isinstance(item, MorphologyEvidence) for item in evidence):
            raise TypeError("evidence must contain MorphologyEvidence values")
        object.__setattr__(self, "evidence", evidence)
        if not isinstance(self.candidate_signals, FloralCandidateSignals):
            raise TypeError("candidate_signals must be FloralCandidateSignals")

    def to_plane_assessment(self) -> PlaneAssessment:
        """Return a fresh deterministic packet without reading or mutating runtime state."""

        return assess_floral_morphology(
            self.intent,
            scope=self.scope,
            evidence=self.evidence,
            candidate_signals=self.candidate_signals,
        )


# Explicit alias for call sites that prefer builder terminology.
build_floral_morphology_assessment = assess_floral_morphology


__all__ = [
    "BouquetMember",
    "BouquetRelation",
    "BouquetRelationKind",
    "BouquetRole",
    "CustomFloralExpression",
    "CustomFloralFacet",
    "FacetOmission",
    "FacetRole",
    "FacetSelection",
    "FloralAbstraction",
    "FloralCandidateSignals",
    "FloralCaricature",
    "FloralFacet",
    "FloralFailureMode",
    "FloralMorphologyIntent",
    "FloralMorphologyPlaneAdapter",
    "FloralSubject",
    "FloralSubtype",
    "MorphologyEvidence",
    "NaturalMixtureRepresentation",
    "NaturalMixtureTreatment",
    "PersistenceEvidence",
    "TemporalTransformation",
    "TemporalWindow",
    "TransformationKind",
    "assess_floral_morphology",
    "build_floral_morphology_assessment",
    "detect_floral_failure_modes",
    "expression_space_for",
    "facet_space_for",
    "subtype_space_for",
]
