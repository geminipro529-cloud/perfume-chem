"""Deterministic global role-to-stock assignment and exact dose allocation."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, replace
from functools import lru_cache
from typing import Any, Mapping, Sequence

from engine.formulation_intelligence.material_capability_index import (
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
    LAYER_MAX_RAW_SHARE,
    LAYER_PROVENANCE,
    SemanticBrief,
    SemanticRole,
    accord_lead_role_id,
)
from engine.research.composition_planner import (
    Choice,
    RoleSpec,
    _allocate_capped,
    _allocation_weight,
    _avoid_candidate,
    _design_cap_ul,
    _formula_rows,
    _hard_cap_ul,
)


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

    def groups(self) -> dict[str, int]:
        return dict(self.group_counts)


def _chemical_identity(capability: MaterialCapability) -> str:
    """Aggregate alternate stock preparations of the same design identity."""

    return re.sub(
        r"[^a-z0-9]+",
        " ",
        capability.identity_name.casefold(),
    ).strip()


def _role_spec(role: SemanticRole) -> RoleSpec:
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
    )


# Generic structural roles the composer adds to bridge the requested notes.
# While a named note can still take volume, none of them may carry the formula.
_BRIDGE_PROVENANCE = frozenset({
    "FUNCTIONAL_COVERAGE",
    "MINIMUM_FUNCTIONAL_ARCHITECTURE",
    "PROMPT_REQUESTED_EXPANDED_ARCHITECTURE",
})
_BRIDGE_MAX_RAW_SHARE = .12


def _is_named_note(role: SemanticRole) -> bool:
    return (
        role.provenance in {"PROMPT_DERIVED_FACET", ACCORD_SUPPORT_PROVENANCE}
        or role.exact_material is not None
    )


def _ifra_admits_raw_share(capability: MaterialCapability, raw_share: float) -> bool:
    """False when a raw share could breach the stock's IFRA Cat 4 limit.

    Same worst case as `_ifra_binds_layer`: the concentrate is up to 30% of
    the finished perfume.  A prohibited material never qualifies.
    """

    entry = _ifra_entry(capability.identity_name)
    if entry is None:
        return True
    status, limit = entry
    if status == "prohibited":
        return False
    if status != "restricted" or limit is None:
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
    bridge_caps = {
        index: _design_cap_ul(adjusted[index], liquid_total_ul) or liquid_total_ul
        for index in free
        if assignments[index].role.provenance in _BRIDGE_PROVENANCE
    }
    if not bridge_caps or not named_open:
        return tuple(adjusted)
    other_capacity = sum(
        _design_cap_ul(adjusted[index], liquid_total_ul) or liquid_total_ul
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
    vanilla).  A stock the user names is always their call.
    """

    entry = _ifra_entry(capability.identity_name)
    if entry is None:
        return False
    status, limit = entry
    if status == "prohibited":
        return True
    if status != "restricted" or limit is None:
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


def _supports_accord(capability: MaterialCapability, role: SemanticRole) -> bool:
    """A supporting accord stock sits in the lead's note and carries its odor.

    Its own annotated character must be clearly present (3 of 10 or more) on
    the role's strongest requested dimension; a synergy listing alone never
    qualifies a stock.  Family buckets elsewhere keep it from repeating the
    lead's family.
    """

    if capability.note != role.note:
        return False
    positive = [(weight, dimension) for dimension, weight in role.character_weights if weight > 0]
    if not positive:
        return True
    _weight, dimension = max(positive)
    return capability.character_map.get(dimension, 0.0) >= 3.0


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


def _allowed(
    capability: MaterialCapability,
    role: SemanticRole,
    state: _BeamState,
    *,
    avoid: Sequence[str],
    allow_multiple_musks: bool,
    enforce_own_odor_avoid: bool = False,
) -> bool:
    identity = _chemical_identity(capability)
    if identity in state.used_identities:
        return False
    if _avoid_candidate(capability.candidate, avoid):
        return False
    if role.knowledge_role_slot and role.knowledge_role_slot not in capability.knowledge_role_slots:
        return False
    if not supports_descriptor_requirement(capability, role.descriptor_requirement):
        return False
    if architecture_avoid_conflict(capability, role.descriptor_requirement, avoid,
                                  all_roles=enforce_own_odor_avoid):
        return False
    groups = state.groups()
    if capability.group == "musk" and groups.get("musk", 0) >= 1:
        if not allow_multiple_musks and role.exact_material is None:
            return False
    if capability.group == "citrus" and groups.get("citrus", 0) >= 2:
        if role.exact_material is None and role.role_id != "persistent_identity":
            return False
    family = _family_bucket(capability)
    if (
        family is not None
        and family not in {"citrus", "musk"}
        and groups.get(f"family:{family}", 0) >= 1
        and role.exact_material is None
    ):
        # Permit layered iris only for separately reviewed recognizer/texture
        # slots. Generic coverage still cannot accumulate family duplicates.
        if family != "iris" or not role.knowledge_role_slot or groups.get("family:iris", 0) >= 3:
            return False
        previous_slots = {
            prior_role.knowledge_role_slot
            for prior_role, prior_capability, _ in state.assignments
            if _family_bucket(prior_capability) == "iris"
        }
        if None in previous_slots or role.knowledge_role_slot in previous_slots:
            return False
    if (
        role.exact_material is None
        and (
            role.provenance in _SUPPORTING_PROVENANCE
            # A reviewed recognizer slot (iris root texture) may have a single
            # eligible stock; the release gate's IFRA check judges that one.
            or (role.provenance == "PROMPT_DERIVED_FACET" and not role.knowledge_role_slot)
        )
        and _ifra_binds_layer(capability, role)
    ):
        return False
    if role.provenance == ACCORD_SUPPORT_PROVENANCE and not _supports_accord(capability, role):
        return False
    if capability.candidate.solid and role.exact_material is None:
        # A solid needs an explicit mass-bearing request.  Selecting one from a
        # descriptor alone would force the solver to invent a mass operation.
        return False
    if role.provenance == ACCENT_PROVENANCE and role.exact_material is None:
        # Accents are the one supporting place for potent materials, kept to
        # a trace by _accent_admits and the accent's small raw-share ceiling.
        return _accent_admits(capability, role)
    if (
        role.exact_material is None
        and role.provenance != "PROMPT_DERIVED_FACET"
        and (
            "trace" in capability.function_terms
            or _hard_cap_ul(capability.candidate, 10_000) is not None
        )
    ):
        # Potent trace materials belong only to a directly requested facet or
        # exact material role.  They must not become bulk opening/bridge/base
        # carriers merely because one prompt word matches their profile.
        return False
    return True


def _stable_tie(role_id: str, stock_id: str, variant_index: int) -> float:
    digest = hashlib.sha256(f"{variant_index}|{role_id}|{stock_id}".encode()).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF * 1e-6


def _unary_rank_for_role(
    index: MaterialCapabilityIndex,
    role: SemanticRole,
    *,
    avoid: Sequence[str],
    previous_stock_ids: frozenset[str],
    prior_variant_stock_ids: frozenset[str],
    variant_index: int,
    enforce_own_odor_avoid: bool = False,
) -> list[tuple[float, MaterialCapability]]:
    ranked: list[tuple[float, MaterialCapability]] = []
    for capability in index.capabilities:
        if _avoid_candidate(capability.candidate, avoid):
            continue
        if capability.candidate.solid and role.exact_material is None:
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
            query_terms=role.query_terms,
            character_weights=role.character_weights,
            note=role.note,
            function=role.function,
            exact_material=role.exact_material,
            selected=(),
            previous_stock_ids=previous_stock_ids,
        )
        if score is None:
            continue
        if capability.stock_id in prior_variant_stock_ids and role.exact_material is None:
            score -= 1.35 + .25 * variant_index
        score += _stable_tie(role.role_id, capability.stock_id, variant_index)
        ranked.append((score, capability))
    ranked.sort(
        key=lambda row: (
            -row[0],
            not row[1].design_ready,
            not row[1].execution_ready,
            row[1].identity_name.casefold(),
            row[1].stock_id,
        )
    )
    # Exact roles retain every matching stock form.  The ordinary unary
    # frontier is deliberately wider than the state frontier so global
    # constraints can still route around a stock consumed by another role.
    return ranked if role.exact_material is not None else ranked[:24]


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
    return adjustment


def _rank_for_state(
    unary_ranked: Sequence[tuple[float, MaterialCapability]],
    role: SemanticRole,
    state: _BeamState,
    *,
    avoid: Sequence[str],
    allow_multiple_musks: bool,
    enforce_own_odor_avoid: bool = False,
) -> list[tuple[float, MaterialCapability]]:
    selected = tuple(item[1] for item in state.assignments)
    ranked = [
        (
            score
            + _pair_adjustment(capability, selected)
            + _accord_affinity(capability, role, state),
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
        )
    ]
    ranked.sort(
        key=lambda row: (
            -row[0],
            not row[1].design_ready,
            not row[1].execution_ready,
            row[1].identity_name.casefold(),
            row[1].stock_id,
        )
    )
    return ranked if role.exact_material is not None else ranked[:10]


def _state_sort_key(state: _BeamState) -> tuple[Any, ...]:
    stock_signature = tuple(
        (role.role_id, capability.stock_id)
        for role, capability, _score in state.assignments
    )
    readiness = sum(capability.design_ready for _role, capability, _score in state.assignments)
    return (-len(state.assignments), -round(state.objective, 9), -readiness, stock_signature)


def _solve_assignments(
    *,
    brief: SemanticBrief,
    index: MaterialCapabilityIndex,
    avoid: Sequence[str],
    previous_stock_ids: frozenset[str],
    prior_variant_stock_ids: frozenset[str],
    variant_index: int,
    beam_width: int,
) -> tuple[tuple[SolvedAssignment, ...], tuple[str, ...]]:
    states: tuple[_BeamState, ...] = (
        _BeamState(
            assignments=(),
            used_identities=frozenset(),
            group_counts=(),
            objective=0.0,
        ),
    )
    missing: list[str] = []
    allow_multiple_musks = _allows_multiple_musks(brief.normalized_request, brief.roles)
    # v5 applies explicit own-odor exclusions to the entire comparison, not
    # only the added/refined role. Historical controls keep their replay path.
    enforce_own_odor_avoid = bool(brief.architecture_plan.get("operation"))
    unary_rankings = {
        role.role_id: _unary_rank_for_role(
            index,
            role,
            avoid=avoid,
            previous_stock_ids=previous_stock_ids,
            prior_variant_stock_ids=prior_variant_stock_ids,
            variant_index=variant_index,
            enforce_own_odor_avoid=enforce_own_odor_avoid,
        )
        for role in brief.roles
    }
    for position, role in enumerate(brief.roles):
        expanded: list[_BeamState] = []
        role_has_candidate = False
        for state in states:
            ranked = _rank_for_state(
                unary_rankings[role.role_id],
                role,
                state,
                avoid=avoid,
                allow_multiple_musks=allow_multiple_musks,
                enforce_own_odor_avoid=enforce_own_odor_avoid,
            )
            role_has_candidate = role_has_candidate or bool(ranked)
            for score, capability in ranked:
                groups = state.groups()
                groups[capability.group] = groups.get(capability.group, 0) + 1
                family = _family_bucket(capability)
                if family is not None:
                    key = f"family:{family}"
                    groups[key] = groups.get(key, 0) + 1
                expanded.append(
                    _BeamState(
                        assignments=(*state.assignments, (role, capability, score)),
                        used_identities=state.used_identities
                        | {_chemical_identity(capability)},
                        group_counts=tuple(sorted(groups.items())),
                        objective=state.objective + score,
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
        alternatives = unary_rankings[role.role_id]
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
) -> FormulaSolveResult:
    if liquid_total_ul <= 0:
        raise ValueError("liquid_total_ul must be positive")
    if not 0 <= variant_index <= 2:
        raise ValueError("variant_index must be from zero to two")
    solve_kwargs = dict(
        brief=brief,
        index=index,
        avoid=avoid,
        previous_stock_ids=frozenset(previous_stock_ids),
        prior_variant_stock_ids=frozenset(prior_variant_stock_ids),
        variant_index=variant_index,
    )
    assignments, missing = _solve_assignments(**solve_kwargs, beam_width=beam_width)
    if missing and _missing_role_has_candidates(missing, **solve_kwargs):
        # The beam keeps only the best partial states, so it can prune away the
        # one path that still fills every required role. Before withholding a
        # variant, search once more with a wider beam; a result that already
        # covers every role is never re-solved, so it cannot change, and a
        # role no stock can fill at all is not retried.
        wider, wider_missing = _solve_assignments(
            **solve_kwargs, beam_width=beam_width * _INCOMPLETE_RETRY_BEAM_FACTOR
        )
        if len(wider_missing) < len(missing):
            assignments, missing = wider, wider_missing
    choices = tuple(
        Choice(
            role=_role_spec(assignment.role),
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
        except ValueError as exc:
            status = "WITHHELD_DOSE_ALLOCATION_INFEASIBLE"
            holds.append(f"DOSE_ALLOCATION_INFEASIBLE:{exc}")

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
            "prefer design-ready exact stock bindings",
            "minimize same-note profile redundancy",
            "deterministic stock identity tie-break",
        ],
        "prohibited_objectives_used": [],
        "ingredient_count_is_objective": False,
        "pleasantness_claimed": False,
        "architecture_plan": brief.architecture_plan,
        "descriptor_eligibility_policy": "OWN_MATERIAL_DESCRIPTOR_NOT_NAME_OR_CATEGORY_V1",
        "future_role_policy": "BOUNDED_REQUIRED_DESCRIPTOR_FORWARD_CHECK_V1",
        "named_fruit_recognition": {name: "NOT_SENSORY_VALIDATED" for name in brief.requested_fruits},
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


__all__ = ["FormulaSolveResult", "SolvedAssignment", "solve_formula"]
