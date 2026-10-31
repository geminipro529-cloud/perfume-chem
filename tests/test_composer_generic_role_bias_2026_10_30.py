"""Why Clearwood and Linalool filled the generic roles of most formulas (Kenny, 30 Oct 2026).

After the 29 Oct fix, Clearwood still sat in 21 and Linalool in 20 of 34 benchmark
formulas (FAST). Two scoring artefacts, not margins of fit:

1. A wood layer charged rivals an off-brief family for the texture word "cocoon"
   (it named the resin family) and for creamy notes the layer's own character asks
   for. Cedarwoods, Timberol, Koavone and Sandalwood EO paid 8 points that
   Clearwood ("veil") did not, so Clearwood won with no word of the layer matched.
2. Coverage roles scored their function word ("bridge") twice: once as the role's
   function and again as a query word, which only six profiles carry (Linalool,
   Dihydro Beta Ionone, Coriander ...), so they won every opening and link.

These pin the scoring; they make no sensory claim.
"""
from __future__ import annotations

from types import SimpleNamespace

from engine.formulation_intelligence import formula_solver as fs
from engine.formulation_intelligence.semantic_brief_adapter import compile_semantic_brief


def _layer(**overrides):
    values = dict(
        role_id="base_wood_layer", note="base", provenance="LAYERED_BASE_ARCHITECTURE",
        query_terms=("cedarwood", "wood"), character_weights=(("woody", .8),),
        exact_material=None, descriptor_requirement=None,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def _cap(*descriptors):
    return SimpleNamespace(note="base", character_map={}, descriptor_vocabulary=frozenset(descriptors))


def test_a_texture_word_names_no_odour_family():
    cedarwood = _cap("cocoon", "sweetness", "warmth", "woody")
    assert fs._off_brief_penalty(cedarwood, _layer(), frozenset()) == 0.0
    # A real resin word still counts (half: the material also carries the layer).
    assert fs._off_brief_penalty(_cap("woody", "balsamic"), _layer(), frozenset()) == fs._OFF_BRIEF_FAMILY_PENALTY / 2


def test_a_family_the_layer_character_asks_for_is_not_off_brief():
    sandalwood = _cap("creamy", "cushion", "woody")
    creamy_layer = _layer(query_terms=("sandalwood", "wood"),
                          character_weights=(("creamy", .425), ("woody", .975)))
    assert fs._off_brief_penalty(sandalwood, creamy_layer, frozenset()) == 0.0
    # Without the creamy weight the creamy family is still off-brief.
    half = fs._OFF_BRIEF_FAMILY_PENALTY / 2
    assert fs._off_brief_penalty(sandalwood, _layer(), frozenset()) == half
    # A negative weight asks for less of it, not for it.
    dry_layer = _layer(character_weights=(("creamy", -.4), ("woody", .8)))
    trace_layer = _layer(character_weights=(("creamy", .15), ("woody", .8)))
    assert fs._off_brief_penalty(sandalwood, trace_layer, frozenset()) == half
    assert fs._off_brief_penalty(sandalwood, dry_layer, frozenset()) == half


def test_coverage_roles_do_not_query_their_function_word():
    brief = compile_semantic_brief(
        formula_name="White Musk",
        request="a clean white musk with aldehydes, bergamot and neroli",
        interpretation={"must_preserve": [], "must_avoid": [], "explicit_materials": []},
        max_materials=14,
    )
    coverage = [role for role in brief.roles if role.provenance == "FUNCTIONAL_COVERAGE"]
    assert coverage
    for role in coverage:
        assert role.function not in role.query_terms, role.role_id
    opening = next(role for role in coverage if role.role_id == "opening_articulation")
    assert opening.function == "bridge"
    assert "bergamot" in opening.query_terms
