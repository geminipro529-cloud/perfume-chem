"""A pairing partner's name is not the material's odour (engine bias audit, 4 Nov 2026).

Profiles list the materials they blend with (``synergies``).  The composer used
to tokenise those names into each material's matching words, so Peppermint
EO matched a lavender query through "Lavender EO" in its list, and once the
sourced profiles got their own lists Grapefruit FCF topped 32 roles it does
not smell of.  The partners now count only through the pair bonus, when a
partner is already in the formula (Kenny's pick, 4 Nov 2026).

These pin scoring inputs; they make no sensory claim.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from engine.formulation_intelligence.material_capability_index import (
    _capability,
    build_material_capability_index,
    capability_role_score,
)


@pytest.fixture(scope="module")
def caps():
    by_name = {}
    for cap in build_material_capability_index().capabilities:
        if cap.design_ready:
            by_name.setdefault(cap.identity_name, cap)
    return by_name


def _with_partners(cap, partners):
    candidate = cap.candidate
    profile = replace(candidate.profile, synergies=list(partners))
    return _capability(replace(candidate, profile=profile))


def test_a_partner_name_is_not_a_matching_word(caps):
    hedione = caps["Hedione"]
    plain = _with_partners(hedione, ())
    paired = _with_partners(hedione, ("Quokka Absolute", "Hedione"))

    assert "quokka" not in paired.vocabulary
    assert paired.vocabulary == plain.vocabulary


def test_a_chosen_partner_still_earns_the_pair_bonus(caps):
    hedione, partner = caps["Hedione"], caps["Bergamot FCF Oil Sicilian"]
    alone = _with_partners(hedione, ())
    paired = _with_partners(hedione, (partner.identity_name,))
    kwargs = dict(
        query_terms=("floral", "jasmine"),
        character_weights=(),
        note="heart",
        function="modifier",
        exact_material=None,
        selected=(partner,),
    )

    assert capability_role_score(paired, **kwargs) > capability_role_score(alone, **kwargs)
