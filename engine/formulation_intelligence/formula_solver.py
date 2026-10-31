"""Deterministic global role-to-stock assignment and exact dose allocation."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, replace
from decimal import Decimal
from functools import lru_cache
from typing import Any, Callable, Mapping, Sequence

from engine.formulation_intelligence.family_structure import family_role_words, names_family_words
from engine.formulation_intelligence.liking_tie_break import Liking, LikingLookup
from engine.formulation_intelligence.material_capability_index import (
    _DESCRIPTOR_REQUIREMENTS,
    MaterialCapability,
    MaterialCapabilityIndex,
    architecture_avoid_conflict,
    capability_role_score,
    supports_descriptor_requirement,
)
from engine.formulation_intelligence.semantic_brief_adapter import (
    ACCENT_MAX_RAW_SHARE,
    ACCENT_PROVENANCE,
    ACCORD_SUPPORT_PROVENANCE,
    LASTING_SPICE_PROVENANCE,
    LAYER_MAX_RAW_SHARE,
    LAYER_PROVENANCE,
    TODAY_SUPPORT_PLACES,
    SemanticBrief,
    SemanticRole,
    accord_lead_role_id,
    accord_support_clone,
    role_identity_requirement,
)
from engine.ifra_standards import single_material_limit_pct
from engine.research.composition_planner import (
    _MIN_RAW_TRANSFER_UL,
    ACCORD_SUPPORT_SEPARATOR,
    AMBER_CRYSTAL_IDENTITIES,
    AMBROX_CRYSTAL_MASS_BASIS,
    TRACE_STOCK_FRACTION,
    WEIGHABLE_POWDER_MIN_MG,
    Choice,
    RoleSpec,
    _allocate_capped,
    _allocation_weight,
    _avoid_candidate,
    _design_cap_ul,
    _formula_rows,
    _hard_cap_ul,
    _ifra_cap_ul,
)
from future_modules._shared_types import NoteTier, get_note_tier_from_vp


@dataclass(frozen=True, slots=True)
class SolvedAssignment:
    role: SemanticRole
    capability: MaterialCapability
    score: float
    alternatives: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FormulaSolveResult:
    status: str
    variant_id: str
    assignments: tuple[SolvedAssignment, ...]
    missing_roles: tuple[str, ...]
    rows: tuple[dict[str, Any], ...]
    separate_totals: dict[str, str]
    holds: tuple[str, ...]
    solver_receipt: dict[str, Any]


@dataclass(frozen=True, slots=True)
class _BeamState:
    assignments: tuple[tuple[SemanticRole, MaterialCapability, float], ...]
    used_identities: frozenset[str]
    group_counts: tuple[tuple[str, int], ...]
    objective: float
    # Role fit without the hash tie, and summed liking of non-exact picks.
    fit: float = 0.0
    liking: float = 0.0
    # The brief has a lasting spice role: it keeps one lasting spice.
    lasting_spice_brief: bool = False

    def groups(self) -> dict[str, int]:
        return dict(self.group_counts)


# A CAS number in parentheses names the same material, not another one:
# "Vetikon (7403-42-1)" is the owned Vetikon's design-only twin.
_CAS_IN_PARENTHESES = re.compile(r"\(\s*\d{2,7}-\d{2}-\d\s*\)")


def _chemical_identity(capability: MaterialCapability) -> str:
    """Aggregate alternate stock preparations of the same design identity."""

    return _identity_key(_CAS_IN_PARENTHESES.sub(" ", capability.identity_name))


def _identity_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", name.casefold()).strip()


def _role_spec(role: SemanticRole, *, star_note: bool = False) -> RoleSpec:
    return RoleSpec(
        role_id=role.role_id,
        label=role.label,
        note=role.note,
        function=role.function,
        share=role.share,
        preferred_materials=role.query_terms,
        descriptor_weights=role.character_weights,
        exact_preference_required=role.exact_material is not None,
        max_raw_share=role.max_raw_share,
        serves_requested_facet=_is_named_note(role),
        generic_slot=not _is_named_note(role) and role.provenance in _GENERIC_SLOT_PROVENANCE,
        star_note=star_note,
        accord=role.accord,
    )


# Generic structural roles the composer adds to bridge the requested notes.
# While a named note can still take volume, none of them may carry the formula.
_BRIDGE_PROVENANCE = frozenset({
    "FUNCTIONAL_COVERAGE",
    "MINIMUM_FUNCTIONAL_ARCHITECTURE",
    "PROMPT_REQUESTED_EXPANDED_ARCHITECTURE",
})
_BRIDGE_MAX_RAW_SHARE = .12
# Every slot the composer adds around the named notes: none may outrank the lead.
_GENERIC_SLOT_PROVENANCE = frozenset({
    *_BRIDGE_PROVENANCE,
    *LAYER_PROVENANCE.values(),
    ACCENT_PROVENANCE,
})


def _is_named_note(role: SemanticRole) -> bool:
    return (
        role.provenance in {"PROMPT_DERIVED_FACET", ACCORD_SUPPORT_PROVENANCE}
        or role.exact_material is not None
    )


def _ifra_admits_raw_share(capability: MaterialCapability, raw_share: float) -> bool:
    """False when a raw share could breach the stock's IFRA Cat 4 limit.

    Same worst case as `_ifra_binds_layer`: the concentrate is up to 30% of
    the finished perfume.  A prohibited material never qualifies.  The limit
    is the gate's own, so a natural's Annex I constituents count (rose oil's
    methyl eugenol), as they do in the planner's IFRA dose cap.
    """

    entry = single_material_limit_pct(capability.identity_name)
    if entry is None:
        return True
    status, limit = entry
    if status == "prohibited":
        return False
    if limit is None:
        return True
    fraction = float(capability.candidate.stock.dilution)
    return raw_share * _CONCENTRATE_FINISHED_FRACTION * fraction * 100 <= limit


def _ifra_safe_supports(
    assignments: Sequence[SolvedAssignment],
    choices: Sequence[Choice],
    supports: Sequence[int],
    spare_ul: float,
    liquid_total_ul: int,
) -> list[int]:
    """The supports that can take their part of the spare volume within IFRA.

    A support whose ceiling plus its part would breach its Cat 4 limit takes
    none; the rest share its part, so the check repeats until it settles.
    """

    eligible = list(supports)
    while eligible:
        share_total = sum(choices[index].role.share for index in eligible)
        safe = [
            index
            for index in eligible
            if _ifra_admits_raw_share(
                assignments[index].capability,
                (
                    (_design_cap_ul(choices[index], liquid_total_ul) or liquid_total_ul)
                    + spare_ul * choices[index].role.share / share_total
                ) / liquid_total_ul,
            )
        ]
        if safe == eligible:
            return eligible
        eligible = safe
    return eligible


def _bridge_cap_ul(
    caps: dict[int, int],
    other_capacity: int,
    liquid_total_ul: int,
) -> int | None:
    """The smallest common bridge cap (at least 12%) that still places the liquid.

    A bridge whose own cap is already smaller keeps it, so it counts at that
    capacity and the shortfall is shared over the remaining bridges.  None
    means even the bridges' own caps cannot hold the liquid total.
    """

    floor = int(liquid_total_ul * _BRIDGE_MAX_RAW_SHARE)
    if other_capacity + sum(caps.values()) < liquid_total_ul:
        return None
    if other_capacity + sum(min(cap, floor) for cap in caps.values()) >= liquid_total_ul:
        return floor
    remaining = liquid_total_ul - other_capacity
    open_count = len(caps)
    for cap in sorted(caps.values()):
        if cap * open_count >= remaining:
            break
        remaining -= cap
        open_count -= 1
    return max(floor, -(-remaining // open_count))


def _hold_hard_capped_bridges(
    choices: list[Choice],
    targets: dict[int, int],
    free: Sequence[int],
    liquid_total_ul: int,
) -> bool:
    """Hold hard-capped bridges to the bridge cap by scaling their share down.

    The planner applies a stock's hard dose cap instead of the role's raw-share
    ceiling, so for such a bridge (cis-Jasmone 10%, Methyl Laitone 1%) the
    ceiling cannot be set.  Its share is scaled instead, checked against the
    planner's own capped allocation.  Returns False if that does not settle.
    """

    for _ in range(8):
        try:
            allocated = _allocate_capped(
                liquid_total_ul,
                [
                    (index, _allocation_weight(choices[index]), _design_cap_ul(choices[index], liquid_total_ul))
                    for index in free
                ],
            )
        except ValueError:
            return False
        over = {index: allocated[index] for index, target in targets.items() if allocated[index] > target}
        if not over:
            return True
        for index, amount in over.items():
            role = choices[index].role
            choices[index] = replace(
                choices[index],
                role=replace(role, share=role.share * targets[index] / amount * .98),
            )
    return False


def _route_spare_volume(
    assignments: Sequence[SolvedAssignment],
    choices: Sequence[Choice],
    liquid_total_ul: int,
) -> tuple[Choice, ...]:
    """Keep volume a hard cap frees on the named notes, not on generic bridges.

    The planner hands volume a capped row cannot take to every open row in
    proportion to weight, so a trace-capped accord lead (Rose Oxide) would let
    the bridges carry the perfume.  The unused part of a capped lead's weight
    moves to its own accord supports instead (never past a support's IFRA
    Cat 4 limit), and a bridge is held to 12% of the liquid while a named note
    can still take volume.  The bridge cap only rises as far as needed for the
    caps to hold the whole liquid total; if no cap can, or a hard-capped
    bridge cannot be held, the planner's own choices are returned unchanged.

    The rows report these routed shares as `design_share_decimal`, so that
    field shows the share the allocation used, not the brief's original one.
    """

    free = [index for index, choice in enumerate(choices) if not choice.candidate.solid]
    weights = {index: _allocation_weight(choices[index]) for index in free}
    weight_total = sum(weights.values())
    specs = {index: choices[index].role for index in free}
    for lead in free:
        role = assignments[lead].role
        cap = _hard_cap_ul(choices[lead].candidate, liquid_total_ul)
        expected = liquid_total_ul * weights[lead] / weight_total if weight_total else 0.0
        if role.provenance != "PROMPT_DERIVED_FACET" or cap is None or cap >= expected:
            continue
        spare_ul = expected - cap
        supports = _ifra_safe_supports(
            assignments,
            choices,
            [
                index
                for index in free
                if accord_lead_role_id(assignments[index].role) == role.role_id
                and _hard_cap_ul(choices[index].candidate, liquid_total_ul) is None
            ],
            spare_ul,
            liquid_total_ul,
        )
        if not supports:
            continue
        spare_weight = weights[lead] * spare_ul / expected
        specs[lead] = replace(specs[lead], share=specs[lead].share * cap / expected)
        support_share = sum(choices[index].role.share for index in supports)
        for index in supports:
            part = choices[index].role.share / support_share
            # Shares are converted back from allocation weight, which may be
            # stock-strength compensated; the support's ceiling grows by the
            # volume it receives.
            per_share = weights[index] / max(choices[index].role.share, 0.000001)
            specs[index] = replace(
                specs[index],
                share=specs[index].share + spare_weight * part / per_share,
                max_raw_share=(
                    None
                    if specs[index].max_raw_share is None
                    else specs[index].max_raw_share + spare_ul * part / liquid_total_ul
                ),
            )

    adjusted = [
        replace(choice, role=specs[index]) if index in specs else choice
        for index, choice in enumerate(choices)
    ]
    named_open = any(
        _is_named_note(assignments[index].role)
        and _hard_cap_ul(choices[index].candidate, liquid_total_ul) is None
        for index in free
    )
    # The planner releases screening defaults (named notes first) when they
    # leave the total unfillable, so they must not raise the bridge cap.
    bridge_caps = {
        index: _design_cap_ul(adjusted[index], liquid_total_ul, screening_default=False)
        or liquid_total_ul
        for index in free
        if assignments[index].role.provenance in _BRIDGE_PROVENANCE
    }
    if not bridge_caps or not named_open:
        return tuple(adjusted)
    other_capacity = sum(
        _design_cap_ul(adjusted[index], liquid_total_ul, screening_default=False)
        or liquid_total_ul
        for index in free
        if index not in bridge_caps
    )
    # Relax rather than fail: if the other rows cannot hold what the bridges
    # give up, the bridges keep just enough to place the whole liquid total.
    bridge_cap = _bridge_cap_ul(bridge_caps, other_capacity, liquid_total_ul)
    if bridge_cap is None:
        return tuple(choices)
    hard_capped: dict[int, int] = {}
    for index, cap in bridge_caps.items():
        if cap <= bridge_cap:
            continue
        if _hard_cap_ul(adjusted[index].candidate, liquid_total_ul) is not None:
            hard_capped[index] = bridge_cap
            continue
        # Half a microlitre over, so the planner's floor lands on the cap.
        adjusted[index] = replace(
            adjusted[index],
            role=replace(adjusted[index].role, max_raw_share=(bridge_cap + .5) / liquid_total_ul),
        )
    if hard_capped and not _hold_hard_capped_bridges(adjusted, hard_capped, free, liquid_total_ul):
        return tuple(choices)
    return tuple(adjusted)


def _has_exact_material_count(interpretation: Mapping[str, Any]) -> bool:
    return any(
        row.get("kind") == "EXACT"
        for row in interpretation.get("material_count_constraints", ())
    )


def _allocation_choices(
    assignments: Sequence[SolvedAssignment],
    choices: Sequence[Choice],
    liquid_total_ul: int,
    explicit_quantities: Sequence[dict[str, Any]],
    exact_material_count: bool = False,
) -> tuple[Choice, ...]:
    """The choices the dose allocation sees; audits replay through this too."""

    if explicit_quantities or exact_material_count:
        # Exact-quantity and exact-count requests keep the planner's own
        # allocation: every row there is one the user asked to count.
        return tuple(choices)
    return _route_spare_volume(assignments, choices, liquid_total_ul)


def _allows_multiple_musks(request: str, roles: Sequence[SemanticRole]) -> bool:
    explicit_musks = sum(
        role.exact_material is not None
        and any(
            token in role.exact_material.casefold()
            for token in (
                "musk", "ambrettolide", "brassylate", "exaltolide",
                "galaxolide", "habanolide", "romandolide", "zenolide",
            )
        )
        for role in roles
    )
    if explicit_musks > 1:
        return True
    lowered = request.casefold()
    return any(
        phrase in lowered
        for phrase in (
            "multiple musks",
            "musk blend",
            "musk accord",
            "two musks",
            "three musks",
        )
    )


# The release gate's musk count limit (gates._MUSK_COUNT_LIMIT): a skin-musk
# accord may hold a second musk, never a third.
_MAX_FORMULA_MUSKS = 2
# "Not only musk but amber too" and "not the only musk" ask for more than
# musk, never for one musk.
_SINGLE_MUSK_PHRASE = re.compile(
    r"\b(?:(?<!\bnot[\s-])only[\s-]+one|(?<!\bnot[\s-])the[\s-]+only"
    r"|(?<!\bnot[\s-]only[\s-])one|single"
    r"|(?<!\bnot[\s-])(?<!\bnot[\s-]the[\s-])only)[\s-]+musk\b"
)
_MORE_MUSK_WORDS = frozenset({"another", "other", "second", "more", "extra"})


def _single_musk_requested(request: str, avoid: Sequence[str]) -> bool:
    """True when the brief asks for one musk ("the only musk") or its avoid
    list refuses another one ("add another musk")."""

    if _SINGLE_MUSK_PHRASE.search(request.casefold()):
        return True
    return any(
        any(word.startswith("musk") for word in words) and words & _MORE_MUSK_WORDS
        for words in (_words((item,)) for item in avoid)
    )


def _musk_role(capability: MaterialCapability) -> tuple[str, str] | None:
    """A musk's own recorded (role, texture), or None when its role is
    unassigned: with no data there is no proof of a distinct role."""

    profile = capability.candidate.profile
    role = str(getattr(profile, "role", "") or "").strip().casefold()
    if not role or role == "unassigned":
        return None
    return role, str(getattr(profile, "texture", "") or "").strip().casefold()


def _is_musk_accord_support(role: SemanticRole) -> bool:
    """A supporting place of an accord whose query words ask for a musk."""

    return (
        role.provenance == ACCORD_SUPPORT_PROVENANCE
        and _DESCRIPTOR_REQUIREMENTS["base_musk"][0] in _role_descriptor_groups(role)
    )


def _fixative_musk_leads(
    ranked: list[tuple[float, MaterialCapability]],
    role: SemanticRole,
    *,
    single_musk: bool,
) -> list[tuple[float, MaterialCapability]]:
    """A musk note's lead is a fixative-role musk when one may go in.

    The owner's formulas carry their largest musk in a fixative role
    (Habanolide, Ethylene Brassylate) with the character musk (Ambrettolide)
    below it as a support (_held_under_musk_lead).  A brief that asks for one
    musk keeps its one best-matched musk, and a stock the user names is
    their call.
    """

    if single_musk or role.exact_material is not None or role.provenance != "PROMPT_DERIVED_FACET":
        return ranked
    # Stand-in stocks in tests carry no group.
    if not any(
        getattr(cap, "group", None) == "musk" and _is_fixative_musk(cap) for _score, cap in ranked
    ) or _DESCRIPTOR_REQUIREMENTS["base_musk"][0] not in _role_descriptor_groups(role):
        return ranked
    return [row for row in ranked if row[1].group != "musk" or _is_fixative_musk(row[1])]


def _is_fixative_musk(capability: MaterialCapability) -> bool:
    return (_musk_role(capability) or ("",))[0] == "fixative"


def _held_under_musk_lead(
    capability: MaterialCapability,
    role: SemanticRole,
    lead: MaterialCapability,
) -> bool:
    """A second musk under a fixative-role musk lead is held at its lead's
    score instead of dropped, like a backing molecule: a character musk
    (Ambrettolide) matches the musk note better than the fixative lead does,
    yet sits below it."""

    return (
        capability.group == "musk"
        and lead.group == "musk"
        and _is_fixative_musk(lead)
        and _is_musk_accord_support(role)
    )


def _second_musk_block(
    capability: MaterialCapability,
    role: SemanticRole,
    state: "_BeamState",
    musk_count: int,
    *,
    single_musk: bool,
) -> str | None:
    """Why a musk may not join the musk(s) already placed, or None when it may.

    One musk is valid on its own (AGENTS.md); a second one goes only into a
    skin-musk accord's supporting place, and only in a role (profile role and
    texture) distinct from every musk already placed.
    """

    if musk_count >= _MAX_FORMULA_MUSKS:
        return "musk limit (two musks already)"
    if not _is_musk_accord_support(role):
        return "one-musk rule"
    if single_musk:
        return "one-musk rule (the brief asks for one musk)"
    own = _musk_role(capability)
    for _prior, placed, _score in state.assignments:
        if placed.group != "musk":
            continue
        theirs = _musk_role(placed)
        if own is None or theirs is None or own == theirs:
            return f"one-musk rule (same musk role as {placed.identity_name})"
    return None


def _family_bucket(capability: MaterialCapability) -> str | None:
    probe = capability.identity_name.casefold()
    if "root texture" in capability.knowledge_role_slots:
        return "iris"
    for family, markers in (
        ("cedar", ("cedar", "cedramber")),
        ("sandalwood", ("sandal", "javanol", "ebanol", "bacdanol")),
        ("vetiver", ("vetiver", "vetikon")),
        ("patchouli", ("patchouli", "clearwood")),
        ("lavender", ("lavender", "lavandin")),
        ("rose", ("rose", "geraniol", "citronellol")),
        ("jasmine", ("jasmine", "hedione", "jasmone")),
        ("iris", ("iris", "orris", "irone", "ionone", "irotyl")),
        ("musk", ("musk", "ambrettolide", "brassylate", "exaltolide", "habanolide", "romandolide", "zenolide", "galaxolide")),
        ("citrus", ("bergamot", "lemon", "lime", "grapefruit", "mandarin", "orange")),
    ):
        if any(marker in probe for marker in markers):
            return family
    return None


# Roles the composer adds on its own, as opposed to notes the user asked for.
# A material IFRA could limit at their dose never fills one by default.
_SUPPORTING_PROVENANCE = frozenset({
    *LAYER_PROVENANCE.values(),
    ACCENT_PROVENANCE,
    ACCORD_SUPPORT_PROVENANCE,
    "FUNCTIONAL_COVERAGE",
    "MINIMUM_FUNCTIONAL_ARCHITECTURE",
    "PROMPT_REQUESTED_EXPANDED_ARCHITECTURE",
})

# Worst case for a supporting role: its raw-share ceiling (8% unless the role
# sets a smaller one) in a concentrate that is up to 30% of the finished
# perfume (extrait strength).
_SUPPORTING_RAW_SHARE_CEILING = LAYER_MAX_RAW_SHARE
_CONCENTRATE_FINISHED_FRACTION = .30
# Requested notes: the planner's default role cap when a facet sets none, in
# the standard concentrate (6,000 uL in a 30 mL bottle).
_REQUESTED_NOTE_RAW_SHARE_CEILING = .28
_STANDARD_FINISHED_FRACTION = .20
_STANDARD_LIQUID_TOTAL_UL = 6000


@lru_cache(maxsize=None)
def _ifra_entry(identity_name: str) -> tuple[str, float | None] | None:
    from engine.ifra_safety import _IFRA_TABLE

    entry = _IFRA_TABLE.lookup(identity_name)
    if entry is None:
        return None
    return entry.status, entry.cat4_limit_pct


def _ifra_binds_layer(capability: MaterialCapability, role: SemanticRole) -> bool:
    """True when IFRA could bind at a role's dose ceiling.

    Supporting roles are judged at their raw-share ceiling in an extrait-strength
    concentrate.  A requested note named only by a descriptor ("vanilla") is
    judged at its own raw-share cap in the standard 6,000 uL-in-30 mL
    concentrate, so it keeps its core materials (neat Geraniol for a rose) but
    never reaches for one IFRA limits below that dose (Peru Balsam for
    vanilla).  The limit is the gate's own, so a natural's Annex I
    constituents count.  A stock the user names is always their call.
    """

    entry = single_material_limit_pct(capability.identity_name)
    if entry is None:
        return False
    status, limit = entry
    if status == "prohibited":
        return True
    if limit is None:
        return False
    if role.provenance == "PROMPT_DERIVED_FACET":
        ceiling = (role.max_raw_share or _REQUESTED_NOTE_RAW_SHARE_CEILING) * _STANDARD_FINISHED_FRACTION
    else:
        ceiling = (
            min(role.max_raw_share or _SUPPORTING_RAW_SHARE_CEILING, _SUPPORTING_RAW_SHARE_CEILING)
            * _CONCENTRATE_FINISHED_FRACTION
        )
    fraction = float(capability.candidate.stock.dilution)
    return ceiling * fraction * 100 > limit


def _accent_admits(capability: MaterialCapability, role: SemanticRole) -> bool:
    """A potent stock may be an accent when its own dose stays a trace.

    A trace material qualifies only from a dilution of 10% or less, and a
    material with a hard dose cap only when that cap sits inside the accent's
    own raw-share ceiling, so the cap can never hand it extra volume.
    """

    if "trace" in capability.function_terms and float(capability.candidate.stock.dilution) > .1:
        return False
    probe_total = 10_000
    cap = _hard_cap_ul(capability.candidate, probe_total)
    return cap is None or cap <= probe_total * (role.max_raw_share or ACCENT_MAX_RAW_SHARE)


def _words(terms: Sequence[str]) -> frozenset[str]:
    return frozenset(
        word for term in terms for word in re.split(r"[^a-z]+", term.casefold()) if word
    )


def _role_descriptor_groups(role: SemanticRole) -> tuple[frozenset[str], ...]:
    """Own-descriptor groups the role's query words name, in a fixed order."""

    words = _words(role.query_terms)
    return tuple(dict.fromkeys(
        group
        for groups in _DESCRIPTOR_REQUIREMENTS.values()
        for group in groups
        if group & words
    ))


def _supports_accord(
    capability: MaterialCapability,
    role: SemanticRole,
    lead: MaterialCapability | None = None,
) -> bool:
    """A supporting accord stock sits in the lead's note and carries its odor.

    Its own annotated character must be clearly present (3 of 10 or more) on
    the role's strongest requested dimension; a synergy listing alone never
    qualifies a stock.  When the role's query words name a descriptor group
    (musk for a skin-musk accord), the stock's own descriptors must carry that
    group, and so must the lead's when the lead carries one of them: a
    sandalwood is not a musk accord's support.  Family buckets elsewhere keep
    it from repeating the lead's family.
    """

    if capability.note != role.note:
        return False
    groups = _role_descriptor_groups(role)
    if groups:
        if lead is not None:
            groups = tuple(
                group for group in groups if group & lead.descriptor_vocabulary
            ) or groups
        if not any(group & capability.descriptor_vocabulary for group in groups):
            return False
    positive = [(weight, dimension) for dimension, weight in role.character_weights if weight > 0]
    if not positive:
        return True
    _weight, dimension = max(positive)
    return capability.character_map.get(dimension, 0.0) >= 3.0


# A note led by a natural or a preblend (Lavender EO, Sandalwood EO, a vetiver
# oil) has no single-molecule detection basis: its odor rides on a composition
# the gate can only model (Rule 4).  Its supporting material may then be one of
# its own key aroma chemicals, a molecule with its own odor threshold: a major
# constituent of the lead (linalyl acetate in Lavender EO, coumarin in Tonka) or
# a molecule of the lead's note family (Javanol beside Sandalwood EO).
_BACKING_MIN_FRACTION = .05
_BACKING_BONUS = 2.0
# A stock the checks cannot score (no odor threshold of its own, e.g. an
# unassayed ethanol tincture) loses a close call to one they can (Kenny's
# pick, 15 Oct 2026: prefer Olibanum Resinoid over the frankincense tincture).
_UNSCORABLE_PENALTY = 1.0
_NOTE_TIERS = {"top": 0, "heart": 1, "base": 2}


@lru_cache(maxsize=None)
def _is_mixture(identity_name: str) -> bool:
    from engine.pipeline.formula_state import NATURAL_MIXTURE_TOKENS, OPAQUE_PREBLEND_TOKENS
    from engine.pipeline.natural_absolute_decomposition import get_composite_metadata

    probe = f" {identity_name.casefold()} "
    return (
        any(token in probe for token in (*NATURAL_MIXTURE_TOKENS, *OPAQUE_PREBLEND_TOKENS))
        or get_composite_metadata(identity_name) is not None
    )


def _molecule_key(name: str) -> str:
    key = " ".join(word for word in re.split(r"[^a-z0-9]+", name.casefold()) if word)
    return re.sub(r"^(?:dl|d|l) ", "", key)


@lru_cache(maxsize=None)
def _key_constituents(identity_name: str) -> frozenset[str]:
    from engine.pipeline.natural_absolute_decomposition import get_constituents

    return frozenset(
        _molecule_key(str(row[0]))
        for row in get_constituents(identity_name) or ()
        if float(row[1]) >= _BACKING_MIN_FRACTION
    )


@lru_cache(maxsize=None)
@lru_cache(maxsize=None)
def _ifra_prohibited_name(*names: str) -> bool:
    from engine.ifra_standards import load_ifra_table

    material = load_ifra_table().lookup(*names)
    return material is not None and material.status == "prohibited"


def _ifra_prohibited(capability: MaterialCapability) -> bool:
    stock = capability.candidate.stock
    return _ifra_prohibited_name(capability.identity_name, stock.name or "")


@lru_cache(maxsize=None)
def _has_own_threshold(identity_name: str) -> bool:
    """Whether the release gate can score this material's odour threshold.

    It asks the gate's own state builder for a bulk air ODT.  An exact
    ODT-table lookup missed 9 owned stocks that have one: a suffixed label
    ("Vetiver EO (Haiti)", "Allyl Amyl Glycolate (AAG)"), a registry or
    profile threshold ("Coumarin Powder", DMBCA).  They paid the unscorable
    penalty on every unnamed role.  A natural modelled only through its
    constituents (Oman Frankincense Tincture, Olibanum Oil) still counts as
    unscored: a named note it carries reads as unknown physics.  So does a
    table entry with no air value: Diethyl Malonate's entry only records the
    receipt, and it led the pear note of a brief the gate could not check.
    """
    from engine.odor_thresholds import lookup_odt_entry
    from engine.pipeline.formula_state import build_formula_state

    entry = lookup_odt_entry(identity_name)
    if entry is not None and entry.get("odt_air") is not None:
        return True
    try:
        state = build_formula_state({identity_name: 100.0}, {identity_name: 1.0})
    except (KeyError, ValueError):
        return False
    return any(material.odt_air_ppm is not None for material in state.materials)


def _backs_natural_lead(
    capability: MaterialCapability,
    role: SemanticRole,
    lead: MaterialCapability,
) -> bool:
    """A single aroma chemical that carries a natural lead's own note.

    It sits within one note tier of the role and clearly carries the role's
    strongest requested odor dimension (3 of 10 or more), so a solvent listed
    in a resinoid's composition never qualifies.
    """

    if _is_mixture(capability.identity_name) or not _is_mixture(lead.identity_name):
        return False
    if not _has_own_threshold(capability.identity_name):
        return False
    tier, role_tier = _NOTE_TIERS.get(capability.note), _NOTE_TIERS.get(role.note)
    if tier is None or role_tier is None or abs(tier - role_tier) > 1:
        return False
    family = _family_bucket(capability)
    if not (
        (family is not None and family == _family_bucket(lead))
        or _molecule_key(capability.identity_name) in _key_constituents(lead.identity_name)
    ):
        return False
    positive = [(weight, dimension) for dimension, weight in role.character_weights if weight > 0]
    if not positive:
        return True
    _weight, dimension = max(positive)
    return capability.character_map.get(dimension, 0.0) >= 3.0


def _backing(
    capability: MaterialCapability,
    role: SemanticRole,
    state: "_BeamState",
) -> bool:
    """True when this support would be its natural lead's one backing molecule."""

    if role.provenance != ACCORD_SUPPORT_PROVENANCE or role.exact_material is not None:
        return False
    lead = _accord_lead(role, state)
    if lead is None or not _backs_natural_lead(capability, role, lead[0]):
        return False
    lead_id = accord_lead_role_id(role)
    return not any(
        accord_lead_role_id(prior) == lead_id and _backs_natural_lead(prior_capability, prior, lead[0])
        for prior, prior_capability, _score in state.assignments
    )


def _accord_lead(
    role: SemanticRole,
    state: "_BeamState",
) -> tuple[MaterialCapability, float] | None:
    """The stock and stored score already chosen for this support's lead."""

    lead_id = accord_lead_role_id(role)
    if lead_id is None:
        return None
    return next(
        ((cap, score) for prior, cap, score in state.assignments if prior.role_id == lead_id),
        None,
    )


def _accord_affinity(
    capability: MaterialCapability,
    role: SemanticRole,
    state: "_BeamState",
) -> float:
    """Rank supports by declared pairing with their own lead stock."""

    lead_id = accord_lead_role_id(role)
    if lead_id is None:
        return 0.0
    lead = next(
        (cap for prior, cap, _score in state.assignments if prior.role_id == lead_id),
        None,
    )
    if lead is None:
        return 0.0
    affinity = 0.0
    own = " ".join(capability.candidate.profile.synergies).casefold()
    theirs = " ".join(lead.candidate.profile.synergies).casefold()
    if lead.identity_name.casefold() in own:
        affinity += .6
    if capability.identity_name.casefold() in theirs:
        affinity += .6
    return affinity


def _is_cited_helper(role: SemanticRole) -> bool:
    """A helper of a cited note accord: it may take only the spec's stocks."""

    accord = getattr(role, "accord", None)  # stand-in roles in tests carry none
    return accord is not None and accord.part == "helper"


_AMBER_CRYSTAL_IDENTITIES = AMBER_CRYSTAL_IDENTITIES
_AMBER_CRYSTAL_QUERY_WORDS = frozenset({"ambrox", "ambergris"})
_AMBER_CRYSTAL_FUNCTIONS = frozenset({"structure", "fixative"})


def _weighed_amber_crystal(capability: MaterialCapability, role: SemanticRole) -> bool:
    """The owned neat Ambrox Super crystals may fill this role without a mass request.

    The role is the brief's amber base (a base structure or fixative role
    asking for ambrox or ambergris), or a cited accord helper whose accord
    cites the crystals (the lavender texture helper).  The planner then weighs
    the ambroxide the owned 25% solution would have carried in that role, so
    the amber base keeps its balance.  Keyed to the identity, never to
    ``candidate.solid`` alone, which also flags tinctures and Oranger Crystals.
    """

    candidate = capability.candidate
    if not (
        getattr(candidate, "solid", False)
        and role.exact_material is None
        and float(candidate.stock.dilution) >= .999
        and capability.design_ready
        and capability.execution_ready
        and _chemical_identity(capability) in _AMBER_CRYSTAL_IDENTITIES
    ):
        return False
    if _is_cited_helper(role) and role.accord.cites(capability.identity_name, 1.0):
        return True
    return (
        getattr(role, "note", None) == "base"
        and getattr(role, "function", None) in _AMBER_CRYSTAL_FUNCTIONS
        and bool(_words(role.query_terms) & _AMBER_CRYSTAL_QUERY_WORDS)
    )


def _weighed_solid(capability: MaterialCapability, role: SemanticRole) -> bool:
    """An owned neat solid the planner weighs by rule may fill this unnamed role.

    The Ambrox Super crystals keep their amber-base rule
    (_weighed_amber_crystal).  Any other owned neat powder is weighed as the
    active its 10% solution would carry (composition_planner.
    is_rule_weighed_powder); a dose too small for Kenny's scale is held there.
    """

    candidate = capability.candidate
    if _chemical_identity(capability) in _AMBER_CRYSTAL_IDENTITIES:
        return _weighed_amber_crystal(capability, role)
    return bool(
        getattr(candidate, "solid", False)
        and role.exact_material is None
        and float(candidate.stock.dilution) >= .999
        and capability.design_ready
        and capability.execution_ready
    )


_FORM_WORDS = re.compile(r"\b(?:powder|crystals?|flakes|solid|neat)\b")


def _poured_identity(capability: MaterialCapability) -> str:
    """The material behind a stock label, without its form ("Coumarin Powder")."""

    return " ".join(_FORM_WORDS.sub(" ", _chemical_identity(capability)).split())


def _poured_identities(index: MaterialCapabilityIndex) -> frozenset[str]:
    """Materials Kenny owns as a design-ready poured stock (a solution or liquid)."""

    return frozenset(
        _poured_identity(capability) for capability in index.capabilities
        if not capability.candidate.solid and capability.design_ready
    )


def _cited_helper_ifra_block(
    capability: MaterialCapability,
    role: SemanticRole,
    liquid_total_ul: int,
) -> str | None:
    """Why IFRA keeps a cited helper's stock out, or None when it may go in.

    The cited pairing is the source's call, so a limit below the helper's
    share does not refuse it: the planner's IFRA cap
    (composition_planner._ifra_cap_ul) holds its dose inside the limit, in
    any concentrate (it is sized on at most the standard design's volume).
    A prohibited stock still refuses it, and so does a cap that leaves less
    than one pipettable transfer.
    """

    if not _ifra_binds_layer(capability, role):
        return None
    status, _limit = single_material_limit_pct(capability.identity_name)
    if status == "prohibited":
        return "IFRA prohibited"
    cap = _ifra_cap_ul(capability.candidate, liquid_total_ul)
    if cap is not None and cap < _MIN_RAW_TRANSFER_UL:
        return f"IFRA limit leaves under {_MIN_RAW_TRANSFER_UL} uL raw"
    return None


def _cited_lead_family(role: SemanticRole, state: "_BeamState") -> str | None:
    """The family bucket of a cited helper's own lead stock, when placed."""

    if not _is_cited_helper(role):
        return None
    lead = _accord_lead(role, state)
    return _family_bucket(lead[0]) if lead else None


# A spice that lasts, for a brief's lasting spice role: an owned liquid its
# own record files as a spice ("spice" as its odor family or formulation
# role, not only the "spicy" any stock with some spiciness carries from its
# character map), strongly spicy, and below the release gate's long-lasting
# vapour pressure (gates.TENACITY_LONG_LASTING_VP_25C_PA; a test pins them
# equal).  Owned today: Safraleine 10% in DPG (0.02 Pa) and Ethyl Safranate
# 10% (0.05 Pa).  Immortelle Absolute and Peru Balsam Resinoid are as spicy
# and as lasting, but filed floral and balsamic: they are not the spice.
_SPICE_CHARACTER_MIN = 5
_LASTING_VP_PA = 0.1


def _is_lasting_spice(capability: MaterialCapability) -> bool:
    return _lasting_spice_profile(
        capability.candidate.solid, capability.descriptor_vocabulary, capability.character,
        capability.candidate.profile.vp,
    )


@lru_cache(maxsize=None)
def _lasting_spice_profile(
    solid: bool, descriptors: frozenset[str], character: tuple[tuple[str, float], ...],
    vp: float | None,
) -> bool:
    return (
        not solid
        and "spice" in descriptors
        and dict(character).get("spicy", 0.0) >= _SPICE_CHARACTER_MIN
        and vp is not None
        and float(vp) < _LASTING_VP_PA
    )


def _own_descriptor_avoided(capability: MaterialCapability, avoid: Sequence[str]) -> bool:
    """A word the brief avoids is one of the stock's own descriptors ("no leather")."""

    for raw in avoid:
        item = _identity_key(raw)
        for prefix in ("any ", "all ", "the ", "no "):
            item = item.removeprefix(prefix)
        for suffix in (" materials", " material", " notes", " note", " accord"):
            item = item.removesuffix(suffix)
        if item in capability.descriptor_vocabulary:
            return True
    return False


def _block_reason(
    capability: MaterialCapability,
    role: SemanticRole,
    state: _BeamState,
    *,
    avoid: Sequence[str],
    allow_multiple_musks: bool,
    enforce_own_odor_avoid: bool = False,
    named_identity: tuple[str, ...] = (),
    liquid_total_ul: int = _STANDARD_LIQUID_TOTAL_UL,
    single_musk: bool = False,
) -> str | None:
    """Why ``capability`` may not fill ``role`` in ``state``, or None when it may."""

    identity = _chemical_identity(capability)
    if identity in state.used_identities:
        return "already used in this formula"
    if _avoid_candidate(capability.candidate, avoid):
        return "the brief's avoid list"
    if role.provenance == LASTING_SPICE_PROVENANCE:
        # The brief's one lasting spice: a stock the owner holds, never a
        # design-only grade (neat Safraleine), and none the brief turns down
        # by its odor.
        if not (_is_lasting_spice(capability) and capability.execution_ready):
            return "not an owned spice below the long-lasting vapour pressure"
        if _own_descriptor_avoided(capability, avoid):
            return "the brief's avoid list (its own descriptor)"
    elif (
        role.exact_material is None
        and _is_lasting_spice(capability)
        and (state.lasting_spice_brief or any(
            prior.provenance == LASTING_SPICE_PROVENANCE for prior, _cap, _score in state.assignments
        ))
        and any(_is_lasting_spice(prior_capability) for _prior, prior_capability, _score in state.assignments)
    ):
        return "one lasting spice already"
    if role.knowledge_role_slot and role.knowledge_role_slot not in capability.knowledge_role_slots:
        return "not a stock of the role's knowledge slot"
    if not supports_descriptor_requirement(capability, role.descriptor_requirement):
        return "lacks the role's own-descriptor requirement"
    if architecture_avoid_conflict(capability, role.descriptor_requirement, avoid,
                                  all_roles=enforce_own_odor_avoid):
        return "the brief's avoid list"
    groups = state.groups()
    if capability.group == "musk" and groups.get("musk", 0) >= 1:
        if not allow_multiple_musks and role.exact_material is None:
            reason = _second_musk_block(
                capability, role, state, groups["musk"], single_musk=single_musk,
            )
            if reason is not None:
                return reason
    if capability.group == "citrus" and groups.get("citrus", 0) >= 2:
        if role.exact_material is None and role.role_id != "persistent_identity":
            return "citrus limit (two citrus stocks already)"
    backing = _backing(capability, role, state)
    family = _family_bucket(capability)
    if (
        family is not None
        and family not in {"citrus", "musk"}
        and groups.get(f"family:{family}", 0) >= 1
        and role.exact_material is None
        # The cited pairing puts a helper beside its own lead: the lead
        # stock's bucket does not refuse it.  Every other bucket does.
        and family != _cited_lead_family(role, state)
        # A backing molecule shares its natural lead's family.  Besides the
        # lead and the stocks the user named, the composer adds no other
        # stock of that family.
        and not (backing and not any(
            _family_bucket(prior_capability) == family
            and prior.exact_material is None
            and prior.role_id != accord_lead_role_id(role)
            for prior, prior_capability, _score in state.assignments
        ))
    ):
        # Permit layered iris only for separately reviewed recognizer/texture
        # slots. Generic coverage still cannot accumulate family duplicates.
        family_rule = f"family-bucket rule ({family} already in the formula)"
        if family != "iris" or not role.knowledge_role_slot or groups.get("family:iris", 0) >= 3:
            return family_rule
        previous_slots = {
            prior_role.knowledge_role_slot
            for prior_role, prior_capability, _ in state.assignments
            if _family_bucket(prior_capability) == "iris"
        }
        if None in previous_slots or role.knowledge_role_slot in previous_slots:
            return family_rule
    if role.exact_material is None and _is_cited_helper(role):
        reason = _cited_helper_ifra_block(capability, role, liquid_total_ul)
        if reason is not None:
            return reason
    elif (
        role.exact_material is None
        and (
            role.provenance in _SUPPORTING_PROVENANCE
            # A reviewed recognizer slot (iris root texture) may have a single
            # eligible stock; the release gate's IFRA check judges that one.
            or (role.provenance == "PROMPT_DERIVED_FACET" and not role.knowledge_role_slot)
        )
        and _ifra_binds_layer(capability, role)
        # A stock named for the identity the brief asks for (opoponax, oud) is
        # the brief's call, like a stock the user names: the planner's IFRA cap
        # (composition_planner._ifra_cap_ul) holds its dose inside the limit.
        and not (named_identity and capability.design_ready
                 and capability.identity_vocabulary & set(named_identity))
    ):
        return "IFRA limit at the role's dose ceiling"
    # A cited accord helper carries a cited job, not the lead's odor: the
    # odor-match rule does not apply to it.
    if role.provenance == ACCORD_SUPPORT_PROVENANCE and not backing and not _is_cited_helper(role):
        lead = _accord_lead(role, state)
        if not _supports_accord(capability, role, lead[0] if lead else None):
            return "does not carry the lead's note and odor"
    if capability.candidate.solid and role.exact_material is None and not _weighed_solid(capability, role):
        # The planner weighs an owned neat solid by rule
        # (composition_planner._rule_dosed_solid_mg); a solid it cannot weigh
        # needs an explicit mass-bearing request.
        return "a solid stock needs a mass request"
    if role.provenance == ACCENT_PROVENANCE and role.exact_material is None:
        # Accents are the one supporting place for potent materials, kept to
        # a trace by _accent_admits and the accent's small raw-share ceiling.
        return None if _accent_admits(capability, role) else "too potent for an accent"
    if (
        role.exact_material is None
        and role.provenance != "PROMPT_DERIVED_FACET"
        # A cited helper's stock is the source's choice, not a prompt-word
        # match; the planner's hard cap still bounds its dose.
        and not _is_cited_helper(role)
        and (
            "trace" in capability.function_terms
            or _hard_cap_ul(capability.candidate, 10_000) is not None
        )
    ):
        # Potent trace materials belong only to a directly requested facet or
        # exact material role.  They must not become bulk opening/bridge/base
        # carriers merely because one prompt word matches their profile.
        return "potent trace material outside a requested note"
    return None


def _allowed(
    capability: MaterialCapability,
    role: SemanticRole,
    state: _BeamState,
    *,
    avoid: Sequence[str],
    allow_multiple_musks: bool,
    enforce_own_odor_avoid: bool = False,
    named_identity: tuple[str, ...] = (),
    liquid_total_ul: int = _STANDARD_LIQUID_TOTAL_UL,
    single_musk: bool = False,
) -> bool:
    return _block_reason(
        capability, role, state, avoid=avoid, allow_multiple_musks=allow_multiple_musks,
        enforce_own_odor_avoid=enforce_own_odor_avoid, named_identity=named_identity,
        liquid_total_ul=liquid_total_ul, single_musk=single_musk,
    ) is None


# Single-group layer and accent odor families an own descriptor can name.
_ODOR_FAMILIES: dict[str, frozenset[str]] = {
    key: groups[0]
    for key, groups in _DESCRIPTOR_REQUIREMENTS.items()
    if len(groups) == 1 and key.startswith(("top_", "heart_", "base_"))
}
# Per own-descriptor family a background fill brings that neither its role nor
# the brief asked for.  A ranking preference, not a filter: required coverage
# still fills when every candidate carries one.
_OFF_BRIEF_FAMILY_PENALTY = 8.0
# Coverage roles (opening articulation, links, diffusion) have generic query
# words, so a full family penalty would hand them to whatever material names
# no family at all.  There only the distinctive shadow and watery families
# are steered off-brief.
_COVERAGE_STEERED_FAMILIES = frozenset({"base_shadow", "heart_watery"})
# Profile texture words (ingredient_intelligence: skin-effect, diffusion,
# cushion, lift, cocoon, veil, halo).
_TEXTURE_WORDS = frozenset({"cocoon", "veil", "cushion", "lift", "halo", "diffusion"})
_CHARACTER_ASK_WEIGHT = .3
# A family's own facets: ambergris is animalic, musky and powdery, so an amber
# layer counted Ambrox Super's own words off-brief (4 points) while Amber
# Xtreme ("amber, woody, warm") paid none and took 10 of 12 amber layers.
_FAMILY_FACETS = {"base_amber": frozenset({"base_shadow", "base_musk", "heart_powder"})}


def _families(words: frozenset[str]) -> frozenset[str]:
    return frozenset(key for key, group in _ODOR_FAMILIES.items() if group & words)


def _single_words(terms: Sequence[str]) -> frozenset[str]:
    return frozenset(term.casefold() for term in terms if re.fullmatch(r"[A-Za-z]+", term))


# Words that name an odor family without carrying its descriptor words: an
# oud is the shadow family (smoky, leathery, animalic), so a brief asking for
# oud asks for that family and its links may carry it.
_FAMILY_NAMED_BY = {"oud": "base_shadow", "agarwood": "base_shadow"}


def _asked_families(brief: SemanticBrief) -> frozenset[str]:
    """Odor families the request words or the requested facets' own words name."""

    words = _words((brief.normalized_request,))
    for role in brief.roles:
        if role.provenance == "PROMPT_DERIVED_FACET":
            words |= _single_words(role.query_terms)
    return _families(words) | {family for word, family in _FAMILY_NAMED_BY.items() if word in words}


def _off_brief_penalty(
    capability: MaterialCapability,
    role: SemanticRole,
    asked_families: frozenset[str],
) -> float:
    """Penalise a layer or coverage fill for odor families nobody asked for.

    Accord supports are exempt: many musks carry an animalic descriptor.
    """

    if role.exact_material is not None or (
        role.provenance not in LAYER_PROVENANCE.values()
        and role.provenance != "FUNCTIONAL_COVERAGE"
    ):
        return 0.0
    own = _families(_single_words(role.query_terms))
    # The layer's own character asks for these families too: a sandalwood
    # layer weighted creamy must not count a creamy sandalwood off-brief.  A
    # trace weight a qualifier spreads over every role (floral .15) is no ask.
    own |= _families(frozenset(
        dim.casefold() for dim, weight in role.character_weights if weight >= _CHARACTER_ASK_WEIGHT
    ))
    if role.descriptor_requirement:
        own |= {role.descriptor_requirement}
    # A texture word ("cocoon") says how a material sits on skin, not what it
    # smells of, so it names no family here.  It counted as resin, which made
    # every cedarwood pay a family that Clearwood's "veil" did not.
    families = _families(capability.descriptor_vocabulary - _TEXTURE_WORDS)
    for family, facets in _FAMILY_FACETS.items():
        if family in own and family in families:
            own |= facets
    extra = families - own - asked_families
    # One off-brief family or several cost the same, so a fuller description
    # does not pay more: Jasmine Absolute (floral, green, animalic) paid 16
    # where Jasmine Sambac (floral) paid nothing.  A material that also
    # carries the brief pays half a family's worth.
    partial = _OFF_BRIEF_FAMILY_PENALTY / 2 if families - extra else _OFF_BRIEF_FAMILY_PENALTY
    if role.provenance == "FUNCTIONAL_COVERAGE":
        # A link must not carry a steered family at all, so any of them
        # costs a whole family's worth.
        return _OFF_BRIEF_FAMILY_PENALTY if extra & _COVERAGE_STEERED_FAMILIES else 0.0
    if not capability.descriptor_vocabulary:
        # No own-odor annotation (e.g. a category proxy): nothing shows the
        # layer fits, so it must not outrank annotated materials by default.
        return _OFF_BRIEF_FAMILY_PENALTY
    if getattr(capability, "registry_descriptors", False):
        # A registry sentence ("sweet, woody and persistent") names fewer
        # families than a profile entry, so it would dodge the penalty its
        # fuller-described rivals pay and win every such layer.  It pays one
        # family's worth.
        return _OFF_BRIEF_FAMILY_PENALTY
    return partial if extra else 0.0


_NOTE_TIERS = {"top": 0, "heart": 1, "base": 2}


def _note_tier_penalty(capability: MaterialCapability, role: SemanticRole) -> float:
    """Penalise a layer or coverage fill whose material sits in the wrong note tier.

    A layer is the brief's texture at one point of the drydown, so a material
    from a later tier cannot carry it: Hedione is a heart material, not a top
    citrus layer.  A coverage link may borrow from the next tier (a heart
    material bridging into the base) but not skip one (a base material as the
    opening).  A ranking preference like the family penalty, so a role with no
    in-tier candidate still fills; an unassigned note is never penalised.
    """

    if role.exact_material is not None:
        return 0.0
    role_tier = _NOTE_TIERS.get(role.note)
    own_tier = _NOTE_TIERS.get(capability.note)
    if role_tier is None or own_tier is None:
        return 0.0
    if role.provenance in LAYER_PROVENANCE.values():
        return _OFF_BRIEF_FAMILY_PENALTY if own_tier > role_tier else 0.0
    if role.provenance == "FUNCTIONAL_COVERAGE":
        return _OFF_BRIEF_FAMILY_PENALTY if abs(own_tier - role_tier) > 1 else 0.0
    return 0.0


def _stable_tie(role_id: str, stock_id: str, variant_index: int) -> float:
    digest = hashlib.sha256(f"{variant_index}|{role_id}|{stock_id}".encode()).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF * 1e-6


# Measured over five briefs, distinct role-fit scores sit as close as 8.6e-5
# apart, too close for an additive liking weight that still beats the 1e-6
# hash tie.  So liking only orders candidates whose fit agrees to 6 dp.
_LikingFn = Callable[[str], Liking]


def _rank_key(
    row: tuple[float, MaterialCapability],
    role: SemanticRole,
    variant_index: int,
    liking: _LikingFn | None,
) -> tuple[Any, ...]:
    score, capability = row
    lead: tuple[float, ...] = ()
    if liking is not None and role.exact_material is None:
        fit = score - _stable_tie(role.role_id, capability.stock_id, variant_index)
        lead = (-round(fit, 6), -liking(capability.identity_name).value)
    return (
        *lead,
        -score,
        not capability.design_ready,
        not capability.execution_ready,
        capability.identity_name.casefold(),
        capability.stock_id,
    )


_UNARY_FRONTIER = 24


def _unary_rank_for_role(
    index: MaterialCapabilityIndex,
    role: SemanticRole,
    *,
    avoid: Sequence[str],
    previous_stock_ids: frozenset[str],
    prior_variant_stock_ids: frozenset[str],
    variant_index: int,
    enforce_own_odor_avoid: bool = False,
    asked_families: frozenset[str] | None = None,
    liking: _LikingFn | None = None,
    request: str = "",
    required_identity: tuple[str, ...] | None = None,
    frontier: int | None = _UNARY_FRONTIER,
    cardamom_brief: bool = False,
) -> list[tuple[float, MaterialCapability]]:
    ranked: list[tuple[float, MaterialCapability]] = []
    query_terms = role.query_terms
    accord = getattr(role, "accord", None)
    if accord is not None and accord.part == "lead":
        # A cited lead prefers the spec's recognizer stocks; any stock of
        # the note may still lead it.
        query_terms = tuple(dict.fromkeys((*(name for name, _ in accord.stocks), *query_terms)))
    poured = _poured_identities(index)
    for capability in index.capabilities:
        if _avoid_candidate(capability.candidate, avoid):
            continue
        if capability.candidate.solid and role.exact_material is None and not (
            _weighed_amber_crystal(capability, role)
            or (_weighed_solid(capability, role) and _poured_identity(capability) not in poured)
        ):
            # Kenny's scale cannot weigh small doses, so an owned solution of
            # a powder (Coumarin 10%) takes its roles, not the powder.
            continue
        if role.exact_material is None and capability.candidate.legacy_text_only and not capability.execution_ready:
            # An old inventory.txt line with no current stock record carries
            # the profile table's name ("Cedarwood EO"), so it outscored the
            # owned bottle and the gate then held the formula.  Only a brief
            # that names it takes it.
            continue
        if role.exact_material is None and _ifra_prohibited(capability):
            # The gate fails any dose of it (Freesia HDI carries Lilial), so an
            # unnamed role must not reach for it; a brief that names it still
            # gets the gate's refusal and reason.
            continue
        if role.knowledge_role_slot and role.knowledge_role_slot not in capability.knowledge_role_slots:
            continue
        if not supports_descriptor_requirement(capability, role.descriptor_requirement):
            continue
        if architecture_avoid_conflict(capability, role.descriptor_requirement, avoid,
                                      all_roles=enforce_own_odor_avoid):
            continue
        score = capability_role_score(
            capability,
            query_terms=query_terms,
            character_weights=role.character_weights,
            note=role.note,
            function=role.function,
            exact_material=role.exact_material,
            selected=(),
            previous_stock_ids=previous_stock_ids,
        )
        if score is None:
            continue
        if asked_families is not None:
            score -= _off_brief_penalty(capability, role, asked_families)
            score -= _note_tier_penalty(capability, role)
        if capability.stock_id in prior_variant_stock_ids and role.exact_material is None:
            score -= 1.35 + .25 * variant_index
        if role.exact_material is None and not _has_own_threshold(capability.identity_name):
            score -= _UNSCORABLE_PENALTY
        if (
            cardamom_brief and role.exact_material is None
            and "cardamom" not in capability.identity_name.casefold()
            and _cineole_camphor_fraction(capability.identity_name) >= _CINEOLE_CAMPHOR_MIN_FRACTION
        ):
            # The brief's cardamom role comes later; keep the other
            # cineole/camphor oils out of the roles before it.
            score -= _CINEOLE_STACK_PENALTY
        score += _stable_tie(role.role_id, capability.stock_id, variant_index)
        ranked.append((score, capability))
    if _is_cited_helper(role) and role.exact_material is None:
        # A cited accord helper takes one of its spec's own stocks, or none.
        ranked = [
            row for row in ranked
            if role.accord.cites(row[1].identity_name, row[1].candidate.stock.dilution)
        ]
    family_words = family_role_words(role.role_id)
    # The brief self-check's repair names the words a role's stock should
    # carry (a pepper lead that is a pepper); otherwise the brief's own rule.
    required_words = (
        required_identity if required_identity is not None
        else role_identity_requirement(role.role_id, request)
    )
    if family_words and role.exact_material is None:
        # A family material's role takes only a stock named for it, or none.
        ranked = [
            row for row in ranked
            if row[1].design_ready and names_family_words(row[1].identity_vocabulary, family_words)
        ]
    elif required_words and role.exact_material is None:
        # A requested identity (oud, iris, or a word the self-check repairs)
        # is answered by a stock whose own name carries it whenever one is
        # selectable; descriptor overlap alone
        # cannot separate orris from an ionone.  Held stocks are not design
        # ready, so they never satisfy this, and the fallback is unchanged.
        named = [
            row for row in ranked
            if row[1].design_ready and row[1].identity_vocabulary & set(required_words)
        ]
        if named:
            ranked = named
    if role.exact_material is None:
        # An admitted crystal stands for its material: the liquid grades of
        # the same identity give way to it here, so the look-ahead and the
        # helpers' kept-for reasons see the same list the search does.
        crystals = {_chemical_identity(row[1]) for row in ranked if row[1].candidate.solid}
        ranked = [
            row for row in ranked
            if row[1].candidate.solid or _chemical_identity(row[1]) not in crystals
        ]
    ranked.sort(key=lambda row: _rank_key(row, role, variant_index, liking))
    # Exact roles retain every matching stock form.  The ordinary unary
    # frontier is deliberately wider than the state frontier so global
    # constraints can still route around a stock consumed by another role.
    return ranked if role.exact_material is not None or frontier is None else ranked[:frontier]


def _pair_adjustment(
    capability: MaterialCapability,
    selected: Sequence[MaterialCapability],
) -> float:
    adjustment = 0.0
    vector = capability.character_map
    synergies = " ".join(capability.candidate.profile.synergies).casefold()
    for other in selected:
        if other.identity_name.casefold() in synergies:
            adjustment += .35
        other_vector = other.character_map
        dimensions = set(vector) | set(other_vector)
        if not dimensions:
            continue
        mean_difference = sum(
            abs(vector.get(key, 0.0) - other_vector.get(key, 0.0))
            for key in dimensions
        ) / len(dimensions)
        if mean_difference < .75 and capability.note == other.note:
            adjustment -= .55
    if any(_cineole_stack(capability, other) for other in selected):
        adjustment -= _CINEOLE_STACK_PENALTY
    return adjustment


# Cardamom beside another cineole or camphor oil reads medicinal: Kenny poured
# out a bottle of Cardamom, Rosemary, Lavender and Clary Sage (25 Oct 2026).
_CINEOLE_STACK_PENALTY = 3.0
_CINEOLE_CAMPHOR_MIN_FRACTION = .10
_CINEOLE_CAMPHOR_KEYS = frozenset({"1 8 cineole", "cineole", "eucalyptol", "camphor", "borneol", "isoborneol"})


@lru_cache(maxsize=None)
def _cineole_camphor_fraction(identity_name: str) -> float:
    from engine.pipeline.natural_absolute_decomposition import get_constituents

    return sum(
        float(row[1]) for row in get_constituents(identity_name) or ()
        if _molecule_key(str(row[0])) in _CINEOLE_CAMPHOR_KEYS
    )


def _cardamom_brief(brief: SemanticBrief) -> bool:
    """The brief holds a role only cardamom fills: a cardamom family role or a named cardamom."""

    return any(
        "cardamom" in family_role_words(role.role_id)
        or "cardamom" in (role.exact_material or "").casefold()
        for role in brief.roles
    )


def _cineole_stack(capability: MaterialCapability, other: MaterialCapability) -> bool:
    """Cardamom and another oil of 10% or more cineole and camphor in one formula."""

    names = (capability.identity_name, other.identity_name)
    if not any("cardamom" in name.casefold() for name in names) or _chemical_identity(capability) == _chemical_identity(other):
        return False
    return all(_cineole_camphor_fraction(name) >= _CINEOLE_CAMPHOR_MIN_FRACTION for name in names)


# Below this stock strength _allocation_weight (research/composition_planner.py)
# gives a stock no strength compensation, so its raw volume stays trace-scaled.
_TRACE_STOCK_FRACTION = TRACE_STOCK_FRACTION


def _is_note_lead(role: SemanticRole) -> bool:
    """A named note's lead: its facet role, or the stock the brief names."""

    return role.exact_material is not None or (
        role.provenance == "PROMPT_DERIVED_FACET" and role.role_id.startswith("facet_")
    )


def _without_trace_grades(
    ranked: Sequence[tuple[float, MaterialCapability]],
    reserved: frozenset[str] = frozenset(),
) -> list[tuple[float, MaterialCapability]]:
    """Leave out a trace-strength grade while a stronger grade of it can lead.

    A trace stock keeps a trace-scaled raw volume, so as a lead it cannot
    carry the lead's share. Role fit ignores stock strength, so grades of one
    material score within hundredths of each other, and the beam then picks
    one by synergy credit matched on name text: "Lavender EO" (the 1%
    dilution's name) is in other stocks' synergy lists, "Lavender EO (BONTAUX
    SAS)" is not. A stronger grade is a design-ready stock still selectable
    here whose name starts with the trace stock's name, word for word, and
    that no other stock the brief names is (``reserved``: "lavender eo" beside
    "Lavender EO (BONTAUX SAS)" keeps the 1% grade). A name that only contains
    those words is another material: "Spike Lavender EO" is not a grade of
    "Lavender EO". A trace stock with no stronger owned grade stays eligible,
    and so does a fast top material's (``_is_fast_top``): its weak grade is
    the dose, not a handling dilution.
    """

    strong = [
        tuple(_chemical_identity(capability).split())
        for _score, capability in ranked
        if capability.design_ready
        and float(capability.candidate.stock.dilution) >= _TRACE_STOCK_FRACTION
        and _chemical_identity(capability) not in reserved
    ]

    def has_stronger_grade(capability: MaterialCapability) -> bool:
        words = tuple(_chemical_identity(capability).split())
        return any(grade[: len(words)] == words for grade in strong)

    return [
        row for row in ranked
        if float(row[1].candidate.stock.dilution) >= _TRACE_STOCK_FRACTION
        or not has_stronger_grade(row[1])
        or _is_fast_top(row[1])
    ]


def _is_fast_top(capability: MaterialCapability) -> bool:
    """The material's vapour pressure is in the top note tier (VP_NOTE_TIERS).

    At 50 Pa or more at 25 C a material is a fast top note, owned at a weak
    grade because a little is enough: at a lead's share its 10% grade carries
    ten times or more the active volume of its 1% grade (the planner also
    weights a stronger stock's raw volume up), and a fruit facet led that
    way overdoses the opening with ester. Owned trace grades this keeps:
    Hexyl Acetate (194 Pa) and Benzaldehyde (120 Pa). A heart oil such as
    Lavender EO (3.5 Pa) or Rose Oxide (5.3 Pa) still leads on its stronger
    grade. This tier table is used rather than the profile's note field,
    which would also exempt Lemonile and Aldehyde C12 MNA (1.2 and 1.5 Pa), or
    the 2 Pa top cut-off in the science reference, which would exempt neat
    Lavender EO BONTAUX (22 Pa), the lead this rule exists for.
    """

    vp = capability.candidate.profile.vp
    return vp is not None and get_note_tier_from_vp(float(vp)) is NoteTier.TOP


# Amber-base materials move together, through the weighed-crystal rule only
# (_weighed_amber_crystal); no grade rule swaps one of them alone.
_AMBER_BASE_WORDS = ("ambrox", "ambrofix", "amber xtreme", "ambrocenide", "ambermax")
_STRONGEST_GRADE_FUNCTIONS = frozenset({"fixative", "structure"})
# An exact material named with its strength or form is the user's grade.
_NAMES_A_GRADE = re.compile(r"\d\s*%|\b(?:neat|pure|crystals?|solution|dilution|diluted)\b")


def _is_amber_base(capability: MaterialCapability) -> bool:
    identity = _chemical_identity(capability)
    return any(word in identity for word in _AMBER_BASE_WORDS)


def _takes_strongest_grade(role: SemanticRole) -> bool:
    """A role whose stock is its material's strongest owned grade.

    A note's lead, and a base, fixative or structure role, carry the
    formula's active and long-lasting material.  An accent keeps the weak
    grade it is dosed by.  Stand-in roles without a note or function keep
    only the note-lead test.
    """

    if role.provenance == ACCENT_PROVENANCE:
        return False
    return (
        _is_note_lead(role)
        or getattr(role, "note", None) == "base"
        or getattr(role, "function", None) in _STRONGEST_GRADE_FUNCTIONS
    )


def _owned_grades(
    ranked: Sequence[tuple[float, MaterialCapability]],
    role: SemanticRole,
    reserved: frozenset[str] = frozenset(),
) -> list[tuple[float, MaterialCapability]]:
    """Leave out a grade the owner's stock does better, among grades still selectable.

    Role fit ignores stock strength, so a not-owned grade used to win
    whenever it scored a hundredth higher; owning a grade (execution_ready)
    was only a late tie-break.  Two rules, each against an owned
    (design-ready and execution-ready) grade of the same chemical identity
    in ``ranked`` that no other stock the brief names claims (``reserved``):

    1. Every role leaves out a grade that is not owned: the owned neat
       Ambrettolide replaces its 10% stock, the owned Safraleine 10% the
       neat one.
    2. A role that takes the strongest grade (``_takes_strongest_grade``)
       leaves out every weaker grade, unless the stock is a fast top
       (``_is_fast_top``), whose weak grade is the dose.

    Amber-base materials are left alone (``_AMBER_BASE_WORDS``), and so is
    an exact material named with its strength or form (``_NAMES_A_GRADE``).
    """

    if role.exact_material is not None and _NAMES_A_GRADE.search(role.exact_material.casefold()):
        return list(ranked)
    owned: dict[str, float] = {}
    for _score, capability in ranked:
        identity = _chemical_identity(capability)
        if capability.design_ready and capability.execution_ready and identity not in reserved:
            owned[identity] = max(owned.get(identity, 0.0), float(capability.candidate.stock.dilution))
    strongest = _takes_strongest_grade(role)
    kept = []
    for row in ranked:
        capability = row[1]
        best = owned.get(_chemical_identity(capability))
        if best is not None and not _is_amber_base(capability):
            if not capability.execution_ready:
                continue
            if (
                strongest
                and float(capability.candidate.stock.dilution) < best
                and not _is_fast_top(capability)
            ):
                continue
        kept.append(row)
    return kept


def _rank_for_state(
    unary_ranked: Sequence[tuple[float, MaterialCapability]],
    role: SemanticRole,
    state: _BeamState,
    *,
    avoid: Sequence[str],
    allow_multiple_musks: bool,
    enforce_own_odor_avoid: bool = False,
    variant_index: int = 0,
    liking: _LikingFn | None = None,
    named_identity: tuple[str, ...] = (),
    liquid_total_ul: int = _STANDARD_LIQUID_TOTAL_UL,
    reserved_identities: frozenset[str] = frozenset(),
    single_musk: bool = False,
) -> list[tuple[float, MaterialCapability]]:
    selected = tuple(item[1] for item in state.assignments)
    ranked = [
        (
            score
            + _pair_adjustment(capability, selected)
            + _accord_affinity(capability, role, state)
            + (_BACKING_BONUS if _backing(capability, role, state) else 0.0),
            capability,
        )
        for score, capability in unary_ranked
        if _allowed(
            capability,
            role,
            state,
            avoid=avoid,
            allow_multiple_musks=allow_multiple_musks,
            enforce_own_odor_avoid=enforce_own_odor_avoid,
            named_identity=named_identity,
            liquid_total_ul=liquid_total_ul,
            single_musk=single_musk,
        )
    ]
    ranked = _owned_grades(ranked, role, reserved_identities)
    ranked = _fixative_musk_leads(ranked, role, single_musk=single_musk)
    if _is_note_lead(role):
        ranked = _without_trace_grades(ranked, reserved_identities)
    lead = _accord_lead(role, state)
    if lead is not None and role.exact_material is None:
        # A support never outscores its lead: otherwise the summed objective
        # prefers a weak lead with the strongest match demoted to support.  A
        # backing molecule, a cited helper's stock or a second musk under a
        # fixative musk lead is held at its lead's score instead of dropped.
        ranked = [
            (min(row[0], lead[1]), row[1])
            for row in ranked
            if row[0] <= lead[1] or _backing(row[1], role, state) or _is_cited_helper(role)
            or _held_under_musk_lead(row[1], role, lead[0])
        ]
    ranked.sort(key=lambda row: _rank_key(row, role, variant_index, liking))
    return ranked if role.exact_material is not None else ranked[:10]


def _state_sort_key(state: _BeamState) -> tuple[Any, ...]:
    stock_signature = tuple(
        (role.role_id, capability.stock_id)
        for role, capability, _score in state.assignments
    )
    readiness = sum(capability.design_ready for _role, capability, _score in state.assignments)
    return (
        -len(state.assignments), -round(state.fit, 6), -round(state.liking, 9),
        -round(state.objective, 9), -readiness, stock_signature,
    )


def _annotate_liking(
    rows: list[dict[str, Any]],
    assignments: Sequence[SolvedAssignment],
    liking: _LikingFn,
) -> None:
    """Record each row's tie-break liking; audits replay rows through this too."""
    exact_roles = {a.role.role_id for a in assignments if a.role.exact_material is not None}
    for row in rows:
        row["liking_tie_break"] = {
            **liking(str(row.get("identity_name") or "")).as_dict(),
            "applied": row.get("slot") not in exact_roles,
        }


def _count_groups(groups: dict[str, int], capability: MaterialCapability) -> None:
    """Count a placed stock's group and family bucket, as the beam does."""

    groups[capability.group] = groups.get(capability.group, 0) + 1
    family = _family_bucket(capability)
    if family is not None:
        key = f"family:{family}"
        groups[key] = groups.get(key, 0) + 1


def _unplaced_cited_helpers(
    brief: SemanticBrief,
    assignments: Sequence[SolvedAssignment],
    index: MaterialCapabilityIndex,
    avoid: Sequence[str],
    liquid_total_ul: int = _STANDARD_LIQUID_TOTAL_UL,
    kept_for: Mapping[tuple[str, str], SemanticRole] | None = None,
) -> list[dict[str, Any]]:
    """Each cited accord helper none of whose stocks went in, and why each could not.

    Its slot is then empty or holds today's same-query support.  A stock is
    judged against the stocks placed before its role, by the same rules the
    search applies.  When another row holds one of its cited materials,
    ``carried_by`` names that row's role, which carries the helper's job.
    """

    placed = {assignment.role.role_id for assignment in assignments if _is_cited_helper(assignment.role)}
    if not any(_is_cited_helper(role) and role.role_id not in placed for role in brief.roles):
        return []
    allow_multiple_musks = _allows_multiple_musks(brief.normalized_request, brief.roles)
    single_musk = _single_musk_requested(brief.normalized_request, avoid)
    enforce_own_odor_avoid = bool(brief.architecture_plan.get("operation"))
    unplaced: list[dict[str, Any]] = []
    for position, role in enumerate(brief.roles):
        if not _is_cited_helper(role) or role.role_id in placed:
            continue
        earlier = {prior.role_id for prior in brief.roles[:position]}
        prior = [
            (a.role, a.capability, a.score) for a in assignments if a.role.role_id in earlier
        ]
        groups: dict[str, int] = {}
        for _role, capability, _score in prior:
            _count_groups(groups, capability)
        state = _BeamState(
            assignments=tuple(prior),
            used_identities=frozenset(_chemical_identity(cap) for _role, cap, _score in prior),
            group_counts=tuple(sorted(groups.items())),
            objective=0.0,
            lasting_spice_brief=any(r.provenance == LASTING_SPICE_PROVENANCE for r in brief.roles),
        )
        # The row that already holds one of the helper's cited materials
        # carries the helper's job: one material, one row.
        cited = {_identity_key(name) for name, _fraction in role.accord.stocks}
        carrier = next((
            assignment.role for assignment in assignments
            if _chemical_identity(assignment.capability) in cited
        ), None)
        carried = {
            _chemical_identity(assignment.capability) for assignment in assignments
            if assignment.role is carrier and assignment.capability.candidate.solid
        }
        reasons = []
        for name, fraction in role.accord.stocks:
            capability = next((
                cap for cap in index.capabilities
                if cap.identity_name == name and role.accord.cites(name, cap.candidate.stock.dilution)
            ), None)
            reason = "not in the capability index" if capability is None else _block_reason(
                capability, role, state, avoid=avoid, allow_multiple_musks=allow_multiple_musks,
                enforce_own_odor_avoid=enforce_own_odor_avoid, liquid_total_ul=liquid_total_ul,
                single_musk=single_musk,
            )
            kept_by = (kept_for or {}).get((role.role_id, capability.stock_id)) if capability else None
            if reason is None and capability is not None and (
                kept_by is not None
                # A liquid grade that gave way to its admitted crystal is
                # carried by the row that holds the crystal.
                or (carrier is not None and _chemical_identity(capability) in carried)
            ):
                kept = carrier or kept_by
                reason = f"kept for the {'required ' if kept.required else ''}role {kept.label}"
            reasons.append(f"{name} at {fraction:g}: {reason or 'not kept by the search'}")
        entry = {
            "role_id": role.role_id,
            "label": role.label,
            "job": role.accord.job,
            "reasons": reasons,
        }
        if carrier is not None:
            entry["carried_by"] = carrier.role_id
        unplaced.append(entry)
    return unplaced


def _owned_lasting_spices(index: MaterialCapabilityIndex) -> list[MaterialCapability]:
    return [cap for cap in index.capabilities if cap.execution_ready and _is_lasting_spice(cap)]


def _lasting_spice_refused(capability: MaterialCapability, reason: str) -> str:
    return (
        f"LASTING_SPICE_REFUSED:{capability.identity_name} at "
        f"{float(capability.candidate.stock.dilution):g}: {reason}"
    )


def lasting_spice_refusals(
    index: MaterialCapabilityIndex, query_terms: Sequence[str], reason: str,
) -> list[str]:
    """A brief's named spice got no lasting spice, for one ``reason``.

    LASTING_SPICE_NOT_OWNED when the index holds no owned spice below the
    long-lasting vapour pressure, else one LASTING_SPICE_REFUSED line per owned
    lasting-spice stock with ``reason`` (the material limit, a curated capsule
    without a spice role).
    """

    owned = _owned_lasting_spices(index)
    if not owned:
        words = tuple(t for t in query_terms if t not in {"spice", "spicy"})
        return [
            f"LASTING_SPICE_NOT_OWNED: no owned spice stock below {_LASTING_VP_PA:g} Pa "
            f"({', '.join(words or tuple(query_terms)[:1])})"
        ]
    return [_lasting_spice_refused(capability, reason) for capability in owned]


def _lasting_spice_limitations(
    brief: SemanticBrief,
    assignments: Sequence[SolvedAssignment],
    index: MaterialCapabilityIndex,
    avoid: Sequence[str],
    liquid_total_ul: int = _STANDARD_LIQUID_TOTAL_UL,
) -> list[str]:
    """Why the brief's lasting spice role holds no lasting spice; [] when one went in.

    LASTING_SPICE_NOT_OWNED only when the index holds no owned spice below the
    long-lasting vapour pressure.  Otherwise one LASTING_SPICE_REFUSED line per
    owned lasting-spice stock, with the reason the search's own rules give
    against the stocks placed before the role (the avoid list, as with
    "no leather" and Safraleine), or the material limit when the brief had no
    room for the role.
    """

    if any(_is_lasting_spice(a.capability) for a in assignments):
        return []
    position, role = next(
        ((i, r) for i, r in enumerate(brief.roles) if getattr(r, "provenance", None) == LASTING_SPICE_PROVENANCE),
        (None, None),
    )
    if role is None:
        over_limit = tuple(getattr(brief, "lasting_spice_over_limit", ()))
        return lasting_spice_refusals(index, over_limit, "the material limit") if over_limit else []
    owned = _owned_lasting_spices(index)
    if not owned:
        return lasting_spice_refusals(index, role.query_terms, "")
    earlier = {prior.role_id for prior in brief.roles[:position]}
    prior = [(a.role, a.capability, a.score) for a in assignments if a.role.role_id in earlier]
    groups: dict[str, int] = {}
    for _role, capability, _score in prior:
        _count_groups(groups, capability)
    state = _BeamState(
        assignments=tuple(prior),
        used_identities=frozenset(_chemical_identity(cap) for _role, cap, _score in prior),
        group_counts=tuple(sorted(groups.items())),
        objective=0.0,
        lasting_spice_brief=True,
    )
    allow_multiple_musks = _allows_multiple_musks(brief.normalized_request, brief.roles)
    single_musk = _single_musk_requested(brief.normalized_request, avoid)
    enforce_own_odor_avoid = bool(brief.architecture_plan.get("operation"))
    lines = []
    for capability in owned:
        reason = _block_reason(
            capability, role, state, avoid=avoid, allow_multiple_musks=allow_multiple_musks,
            enforce_own_odor_avoid=enforce_own_odor_avoid, liquid_total_ul=liquid_total_ul,
            single_musk=single_musk,
        )
        lines.append(_lasting_spice_refused(capability, reason or "not kept by the search"))
    return lines


def _solve_assignments(
    *,
    brief: SemanticBrief,
    index: MaterialCapabilityIndex,
    avoid: Sequence[str],
    previous_stock_ids: frozenset[str],
    prior_variant_stock_ids: frozenset[str],
    variant_index: int,
    beam_width: int,
    liking: _LikingFn | None = None,
    identity_words: Mapping[str, tuple[str, ...]] | None = None,
    unary_cache: dict[tuple[Any, ...], list[tuple[float, MaterialCapability]]] | None = None,
    liquid_total_ul: int = _STANDARD_LIQUID_TOTAL_UL,
    kept_for: dict[tuple[str, str], SemanticRole] | None = None,
    frontier: int | None = _UNARY_FRONTIER,
) -> tuple[tuple[SolvedAssignment, ...], tuple[str, ...]]:
    """The beam search.  ``kept_for`` collects, per (cited helper role id,
    stock id), the later role that helper's stock was kept for: a required
    role it would leave with no stock, or a role of the brief that would
    place it first."""

    states: tuple[_BeamState, ...] = (
        _BeamState(
            assignments=(),
            used_identities=frozenset(),
            group_counts=(),
            objective=0.0,
            lasting_spice_brief=any(r.provenance == LASTING_SPICE_PROVENANCE for r in brief.roles),
        ),
    )
    missing: list[str] = []
    allow_multiple_musks = _allows_multiple_musks(brief.normalized_request, brief.roles)
    single_musk = _single_musk_requested(brief.normalized_request, avoid)
    # v5 applies explicit own-odor exclusions to the entire comparison, not
    # only the added/refined role. Historical controls keep their replay path.
    enforce_own_odor_avoid = bool(brief.architecture_plan.get("operation"))
    asked_families = _asked_families(brief)
    identity_words = identity_words or {}
    cardamom_brief = _cardamom_brief(brief)

    def unary(role: SemanticRole, cache_id: str | None = None) -> list[tuple[float, MaterialCapability]]:
        # A cache shared by solves of one brief with the same inputs: only a
        # role whose identity words differ is ranked again.
        key = (cache_id or role.role_id, identity_words.get(role.role_id))
        if frontier != _UNARY_FRONTIER:
            key = (*key, frontier)
        if unary_cache is not None and key in unary_cache:
            return unary_cache[key]
        ranked = _unary_rank_for_role(
            index,
            role,
            avoid=avoid,
            previous_stock_ids=previous_stock_ids,
            prior_variant_stock_ids=prior_variant_stock_ids,
            variant_index=variant_index,
            enforce_own_odor_avoid=enforce_own_odor_avoid,
            asked_families=asked_families,
            liking=liking,
            request=brief.normalized_request,
            required_identity=identity_words.get(role.role_id),
            frontier=frontier,
            cardamom_brief=cardamom_brief,
        )
        if unary_cache is not None:
            unary_cache[key] = ranked
        return ranked

    unary_rankings = {role.role_id: unary(role) for role in brief.roles}
    # The identity words each role's stock should carry, as the unary ranking
    # reads them: the self-check's repair words, else the brief's own rule.
    named_identities = {
        role.role_id: (
            identity_words[role.role_id] if role.role_id in identity_words
            else role_identity_requirement(role.role_id, brief.normalized_request)
        )
        for role in brief.roles
    }
    # A cited helper none of whose stocks can go in keeps today's same-query
    # support for its slot (the brief's exclusions and every rule still
    # apply to it); the receipt still lists the helper as unplaced. A helper
    # in a place beyond today's supports has none, so its slot stays empty;
    # a stock the brief names has one support today, which stays in place.
    leads_by_id = {role.role_id: role for role in brief.roles}
    fallbacks = {
        role.role_id: accord_support_clone(leads_by_id[accord_lead_role_id(role)], place)
        for role in brief.roles
        if _is_cited_helper(role) and role.exact_material is None
        and accord_lead_role_id(role) in leads_by_id
        and leads_by_id[accord_lead_role_id(role)].exact_material is None
        and (place := int(role.role_id.rsplit(ACCORD_SUPPORT_SEPARATOR, 1)[1])) <= TODAY_SUPPORT_PLACES
    }
    fallback_rankings = {
        role_id: unary(clone, f"{role_id} (today's support)") for role_id, clone in fallbacks.items()
    }

    def starved_role(
        capability: MaterialCapability,
        role: SemanticRole,
        state: _BeamState,
        later_required: Sequence[SemanticRole],
    ) -> SemanticRole | None:
        """A later required role this optional helper's stock would leave with no stock."""

        groups = state.groups()
        _count_groups(groups, capability)
        taken = _BeamState(
            assignments=(*state.assignments, (role, capability, 0.0)),
            used_identities=state.used_identities | {_chemical_identity(capability)},
            group_counts=tuple(sorted(groups.items())),
            objective=state.objective,
            lasting_spice_brief=state.lasting_spice_brief,
        )

        def admits(future: SemanticRole, candidate_state: _BeamState) -> bool:
            return any(_allowed(
                cap, future, candidate_state, avoid=avoid, allow_multiple_musks=allow_multiple_musks,
                enforce_own_odor_avoid=enforce_own_odor_avoid,
                named_identity=named_identities[future.role_id], liquid_total_ul=liquid_total_ul,
                single_musk=single_musk,
            ) for _, cap in unary_rankings[future.role_id])

        return next((
            future for future in later_required
            if not admits(future, taken) and admits(future, state)
        ), None)

    # The stocks the brief names, each kept for its own role: a stronger grade
    # one of them names cannot stand in for another role's trace grade.
    named_stocks = {
        role.role_id: _identity_key(role.exact_material)
        for role in brief.roles
        if role.exact_material is not None
    }

    def reserved_for(role: SemanticRole) -> frozenset[str]:
        return frozenset(
            key for role_id, key in named_stocks.items()
            if role_id != role.role_id and key != named_stocks.get(role.role_id)
        )

    frontier_identities = {
        role_id: frozenset(_chemical_identity(capability) for _score, capability in ranked)
        for role_id, ranked in unary_rankings.items()
    }

    def first_choices(state: _BeamState, later_structure: Sequence[SemanticRole]) -> dict[str, SemanticRole]:
        """The material each later structural role would place first in
        ``state``, ranked as the search ranks it there; the earliest role
        holds a material two of them would place."""

        firsts: dict[str, SemanticRole] = {}
        for future in later_structure:
            ranked = _rank_for_state(
                unary_rankings[future.role_id], future, state, avoid=avoid,
                allow_multiple_musks=allow_multiple_musks, enforce_own_odor_avoid=enforce_own_odor_avoid,
                variant_index=variant_index, liking=liking, named_identity=named_identities[future.role_id],
                liquid_total_ul=liquid_total_ul, reserved_identities=reserved_for(future),
                single_musk=single_musk,
            )
            if ranked:
                firsts.setdefault(_chemical_identity(ranked[0][1]), future)
        return firsts

    for position, role in enumerate(brief.roles):
        expanded: list[_BeamState] = []
        role_has_candidate = False
        later_required = (
            tuple(r for r in brief.roles[position + 1:] if r.required) if role.role_id in fallbacks else ()
        )
        # The brief's own later roles (not accord supports) whose frontier
        # holds one of this cited helper's stocks.
        later_structure = (
            tuple(
                r for r in brief.roles[position + 1:]
                if r.provenance != ACCORD_SUPPORT_PROVENANCE
                and frontier_identities[r.role_id] & frontier_identities[role.role_id]
            )
            if _is_cited_helper(role) and role.exact_material is None else ()
        )
        reserved = reserved_for(role)
        for state in states:
            if role.provenance == LASTING_SPICE_PROVENANCE and any(
                _is_lasting_spice(capability) for _role, capability, _score in state.assignments
            ):
                # A stock the brief names, or a note's own stock, is already
                # the lasting spice: the state goes on with no second one.
                expanded.append(state)
                continue
            rank_kwargs = dict(
                avoid=avoid,
                allow_multiple_musks=allow_multiple_musks,
                enforce_own_odor_avoid=enforce_own_odor_avoid,
                variant_index=variant_index,
                liking=liking,
                named_identity=named_identities[role.role_id],
                liquid_total_ul=liquid_total_ul,
                reserved_identities=reserved,
                single_musk=single_musk,
            )
            placed_role = role
            ranked = _rank_for_state(unary_rankings[role.role_id], role, state, **rank_kwargs)
            if later_required:
                # An optional helper never takes the one stock a later
                # required role could still use (a reviewed iris root
                # texture slot that only Orivone fills).
                kept = []
                for row in ranked:
                    starved = starved_role(row[1], role, state, later_required)
                    if starved is None:
                        kept.append(row)
                    elif kept_for is not None:
                        kept_for[(role.role_id, row[1].stock_id)] = starved
                ranked = kept
            if later_structure:
                # Nor does a cited helper take the material a later role of
                # the brief would place first (Ambrox Super for an amber
                # facet): that row carries it at its own dose, never a second,
                # smaller row capped under the helper's lead.  The helper's
                # slot then falls back like any helper whose stocks cannot go in.
                firsts = first_choices(state, later_structure)
                kept = []
                for row in ranked:
                    owner = firsts.get(_chemical_identity(row[1]))
                    if owner is None:
                        kept.append(row)
                    elif kept_for is not None:
                        kept_for[(role.role_id, row[1].stock_id)] = owner
                ranked = kept
            if not role.required and role.exact_material is None:
                # An optional role never stacks cardamom with another
                # cineole or camphor oil (Kenny poured out the medicinal
                # cardamom, rosemary and lavender trials, 25 Oct): the
                # pair penalty cannot turn a family role whose stocks are
                # all named for its word.
                ranked = [
                    row for row in ranked
                    if not any(_cineole_stack(row[1], capability) for _role, capability, _score in state.assignments)
                ]
            if not ranked and role.role_id in fallbacks:
                placed_role = fallbacks[role.role_id]
                ranked = _rank_for_state(fallback_rankings[role.role_id], placed_role, state, **rank_kwargs)
            role_has_candidate = role_has_candidate or bool(ranked)
            for score, capability in ranked:
                groups = state.groups()
                _count_groups(groups, capability)
                liked = (
                    liking(capability.identity_name).value
                    if liking is not None and role.exact_material is None else 0.0
                )
                expanded.append(
                    _BeamState(
                        assignments=(*state.assignments, (placed_role, capability, score)),
                        used_identities=state.used_identities
                        | {_chemical_identity(capability)},
                        group_counts=tuple(sorted(groups.items())),
                        objective=state.objective + score,
                        fit=state.fit + score
                        - _stable_tie(role.role_id, capability.stock_id, variant_index),
                        liking=state.liking + liked,
                        lasting_spice_brief=state.lasting_spice_brief,
                    )
                )
        if not role_has_candidate:
            if role.required:
                missing.append(role.label)
            continue
        if not expanded:
            if role.required:
                missing.append(role.label)
            continue
        future_constrained = tuple(
            r for r in brief.roles[position + 1:] if r.required and r.descriptor_requirement
        )

        def forward_key(state: _BeamState) -> tuple[Any, ...]:
            # Preserve candidates for a later constrained role before pruning
            # the beam. This is bounded look-ahead, not an infeasibility proof:
            # pools are the existing unary frontiers and no state is discarded
            # solely for a missing future match. All hard gates still apply.
            blocked = sum(
                not any(_allowed(
                    cap, future, state, avoid=avoid, allow_multiple_musks=allow_multiple_musks,
                    enforce_own_odor_avoid=enforce_own_odor_avoid,
                    named_identity=named_identities[future.role_id],
                    liquid_total_ul=liquid_total_ul,
                    single_musk=single_musk,
                ) for _, cap in unary_rankings[future.role_id])
                for future in future_constrained
            )
            return (blocked, *_state_sort_key(state))

        expanded.sort(key=forward_key if future_constrained else _state_sort_key)
        states = tuple(expanded[:beam_width])

    if not states:
        return (), tuple(dict.fromkeys(missing))
    winner = min(states, key=_state_sort_key)
    assignments: list[SolvedAssignment] = []
    for role, capability, score in winner.assignments:
        alternatives = (
            fallback_rankings[role.role_id] if role is fallbacks.get(role.role_id)
            else unary_rankings[role.role_id]
        )
        alternatives_names = tuple(
            item.identity_name
            for _alt_score, item in alternatives
            if item.stock_id != capability.stock_id
        )[:3]
        assignments.append(
            SolvedAssignment(
                role=role,
                capability=capability,
                score=score,
                alternatives=alternatives_names,
            )
        )
    return tuple(assignments), tuple(dict.fromkeys(missing))


_INCOMPLETE_RETRY_BEAM_FACTOR = 4


def _pour_unweighable_crystals(
    assignments: Sequence[SolvedAssignment],
    choices: Sequence[Choice],
    rows: Sequence[dict[str, Any]],
    index: MaterialCapabilityIndex,
) -> tuple[tuple[SolvedAssignment, ...], tuple[Choice, ...]] | None:
    """Swap a rule-weighed Ambrox Super crystal row under 100 mg for the owned solution.

    Kenny's scale cannot weigh tens of mg (30 Oct 2026), so a small crystal
    row pours his strongest owned liquid grade of it (Ambrox Super 25%)
    instead.  A requested mass is his call and stays.  None when no row moves.
    """

    light = {
        row["slot"] for row in rows
        if row.get("mass_basis") == AMBROX_CRYSTAL_MASS_BASIS
        and Decimal(row["amount_decimal"]) < WEIGHABLE_POWDER_MIN_MG
    }
    if not light:
        return None
    new_assignments, new_choices = list(assignments), list(choices)
    for position, choice in enumerate(choices):
        if choice.role.role_id not in light:
            continue
        crystal = assignments[position].capability
        grades = [
            capability for capability in index.capabilities
            if _chemical_identity(capability) == _chemical_identity(crystal)
            and not capability.candidate.solid and capability.design_ready and capability.execution_ready
        ]
        if not grades:
            continue
        grade = max(grades, key=lambda capability: (float(capability.candidate.stock.dilution), capability.stock_id))
        new_assignments[position] = replace(assignments[position], capability=grade)
        new_choices[position] = replace(choice, candidate=grade.candidate)
    if new_choices == list(choices):
        return None
    return tuple(new_assignments), tuple(new_choices)


def _missing_role_has_candidates(
    missing: Sequence[str],
    *,
    brief: SemanticBrief,
    index: MaterialCapabilityIndex,
    avoid: Sequence[str],
    previous_stock_ids: frozenset[str],
    prior_variant_stock_ids: frozenset[str],
    variant_index: int,
) -> bool:
    """True when some missing role has at least one admissible stock.

    A role with no candidate in the whole index stays missing however wide the
    beam is, so only a role that has candidates is worth a wider search.
    """

    labels = set(missing)
    enforce_own_odor_avoid = bool(brief.architecture_plan.get("operation"))
    return any(
        _unary_rank_for_role(
            index,
            role,
            avoid=avoid,
            previous_stock_ids=previous_stock_ids,
            prior_variant_stock_ids=prior_variant_stock_ids,
            variant_index=variant_index,
            enforce_own_odor_avoid=enforce_own_odor_avoid,
        )
        for role in brief.roles
        if role.label in labels
    )


def solve_formula(
    *,
    brief: SemanticBrief,
    index: MaterialCapabilityIndex,
    liquid_total_ul: int,
    explicit_quantities: Sequence[dict[str, Any]],
    avoid: Sequence[str],
    previous_stock_ids: Sequence[str] = (),
    prior_variant_stock_ids: Sequence[str] = (),
    variant_index: int = 0,
    beam_width: int = 48,
    exact_material_count: bool = False,
    identity_words: Mapping[str, tuple[str, ...]] | None = None,
    unary_cache: dict[tuple[Any, ...], list[tuple[float, MaterialCapability]]] | None = None,
) -> FormulaSolveResult:
    """Assign one stock per role and allocate doses.

    ``identity_words`` maps a role id to words its stock's own name should
    carry when a design-ready stock does (the brief self-check's repair);
    ``unary_cache`` lets solves of the same brief and inputs share rankings.
    """
    if liquid_total_ul <= 0:
        raise ValueError("liquid_total_ul must be positive")
    if not 0 <= variant_index <= 2:
        raise ValueError("variant_index must be from zero to two")
    liking = _liking_lookup()
    solve_kwargs = dict(
        brief=brief,
        index=index,
        avoid=avoid,
        previous_stock_ids=frozenset(previous_stock_ids),
        prior_variant_stock_ids=frozenset(prior_variant_stock_ids),
        variant_index=variant_index,
    )
    kept_for: dict[tuple[str, str], SemanticRole] = {}
    search_kwargs = dict(liking=liking, identity_words=identity_words, unary_cache=unary_cache,
                         liquid_total_ul=liquid_total_ul, kept_for=kept_for)
    assignments, missing = _solve_assignments(**solve_kwargs, beam_width=beam_width, **search_kwargs)
    if missing and _missing_role_has_candidates(missing, **solve_kwargs):
        # The beam keeps only the best partial states, so it can prune away the
        # one path that still fills every required role. Before withholding a
        # variant, search once more with a wider beam; a result that already
        # covers every role is never re-solved, so it cannot change, and a
        # role no stock can fill at all is not retried.
        wider, wider_missing = _solve_assignments(
            **solve_kwargs,
            beam_width=beam_width * _INCOMPLETE_RETRY_BEAM_FACTOR,
            **search_kwargs,
        )
        if len(wider_missing) < len(missing):
            assignments, missing = wider, wider_missing
    if missing and _missing_role_has_candidates(missing, **solve_kwargs):
        # A long brief can use up every stock of a role's ranked frontier
        # (the 60-material chypre's heart contrast: each rose stock it ranks
        # is placed or held by the rose family rule).  Search once more with
        # every stock each role admits.
        full, full_missing = _solve_assignments(
            **solve_kwargs,
            beam_width=beam_width * _INCOMPLETE_RETRY_BEAM_FACTOR,
            **search_kwargs,
            frontier=None,
        )
        if len(full_missing) < len(missing):
            assignments, missing = full, full_missing
    choices = tuple(
        Choice(
            role=_role_spec(
                assignment.role,
                star_note=assignment.role.role_id in brief.star_role_ids,
            ),
            candidate=assignment.capability.candidate,
            score=assignment.score,
            alternatives=assignment.alternatives,
        )
        for assignment in assignments
    )
    choices = _allocation_choices(
        assignments, choices, liquid_total_ul, explicit_quantities, exact_material_count,
    )
    rows: list[dict[str, Any]] = []
    totals = {"liquid_total_ul": "0", "mass_total_mg": "0"}
    holds: list[str] = []
    status = "SOLVED"
    if missing or len(choices) < min(6, len(brief.roles)):
        status = "WITHHELD_CONCEPT_COVERAGE_INCOMPLETE"
    else:
        try:
            rows, totals, holds = _formula_rows(
                choices,
                liquid_total_ul=liquid_total_ul,
                quantities=explicit_quantities,
            )
            poured = _pour_unweighable_crystals(assignments, choices, rows, index)
            if poured is not None:
                assignments, choices = poured
                rows, totals, holds = _formula_rows(
                    choices,
                    liquid_total_ul=liquid_total_ul,
                    quantities=explicit_quantities,
                )
        except ValueError as exc:
            status = "WITHHELD_DOSE_ALLOCATION_INFEASIBLE"
            holds.append(f"DOSE_ALLOCATION_INFEASIBLE:{exc}")
    _annotate_liking(rows, assignments, liking)

    role_scores = {
        assignment.role.role_id: format(assignment.score, ".6f")
        for assignment in assignments
    }
    selected_ids = [assignment.capability.stock_id for assignment in assignments]
    receipt = {
        "schema_version": "formula-constraint-solver-receipt-v1",
        "algorithm": "DETERMINISTIC_BEAM_BRANCH_AND_BOUND",
        "beam_width": beam_width,
        "variant_index": variant_index,
        "role_count": len(brief.roles),
        "assigned_role_count": len(assignments),
        "missing_roles": list(missing),
        "selected_stock_ids": selected_ids,
        "role_fit_diagnostics": role_scores,
        "objective_lexicography": [
            "fill every required role",
            "satisfy exact material and exclusion constraints",
            "maximize structural capability fit",
            "between fits equal to 6 dp only, prefer higher liking (personal, else crowd guess)",
            "prefer design-ready exact stock bindings",
            "minimize same-note profile redundancy",
            "deterministic stock identity tie-break",
        ],
        "prohibited_objectives_used": [],
        "ingredient_count_is_objective": False,
        "pleasantness_claimed": False,
        "liking_tie_break": liking.receipt(),
        "architecture_plan": brief.architecture_plan,
        "descriptor_eligibility_policy": "OWN_MATERIAL_DESCRIPTOR_NOT_NAME_OR_CATEGORY_V1",
        "future_role_policy": "BOUNDED_REQUIRED_DESCRIPTOR_FORWARD_CHECK_V1",
        "named_fruit_recognition": {name: "NOT_SENSORY_VALIDATED" for name in brief.requested_fruits},
    }
    unplaced_helpers = _unplaced_cited_helpers(brief, assignments, index, avoid, liquid_total_ul, kept_for)
    if unplaced_helpers:
        # Optional roles, so they never withhold the formula: recorded beside
        # missing_roles with the reason each cited stock could not go in.
        receipt["unplaced_accord_helpers"] = unplaced_helpers
    lasting_limitations = _lasting_spice_limitations(brief, assignments, index, avoid, liquid_total_ul)
    if lasting_limitations:
        # An optional role, so the formula is not withheld: the receipt says
        # the brief's spice will not last, and why.
        receipt["limitations"] = lasting_limitations
    if identity_words:
        receipt["identity_requirements"] = {
            role_id: list(words) for role_id, words in sorted(identity_words.items())
        }
    signature = hashlib.sha256(
        "|".join(f"{row.role.role_id}:{row.capability.stock_id}" for row in assignments).encode()
    ).hexdigest()[:16]
    return FormulaSolveResult(
        status=status,
        variant_id=f"semantic-variant-{variant_index + 1}-{signature}",
        assignments=assignments,
        missing_roles=missing,
        rows=tuple(rows),
        separate_totals=totals,
        holds=tuple(sorted(set(holds))),
        solver_receipt=receipt,
    )


# Factory seam: tests point it at temporary personal files.
_liking_lookup = LikingLookup


__all__ = ["FormulaSolveResult", "SolvedAssignment", "lasting_spice_refusals", "solve_formula"]
