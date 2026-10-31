"""Owned stocks carry their own signature notes (Phase 3, step 6).

The composer reads a brief's note words against each stock's own descriptors. Six owned
stocks lacked the note they are known for (Hexyl Acetate's pear, Suederal's suede, the
lactones' peach). The reviewed knowledge pack now names those notes, each from a
manufacturer or distributor description with a bound source review. These pin the data
and its use; they make no sensory, dose or quality claim.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.formulation_intelligence.brief_self_check import carries
from engine.formulation_intelligence.formula_design_runtime import design_formula
from engine.formulation_intelligence.literature_knowledge import PACK_PATH, material_knowledge
from engine.formulation_intelligence.material_capability_index import (
    build_material_capability_index,
)
from engine.formulation_intelligence.source_review import source_record_hash

SIGNATURES = {
    "Hexyl Acetate": ("pear", "apple"),
    "Methyl Laitone": ("coconut",),
    "Suederal": ("suede", "leather"),
    "Gamma Undecalactone": ("peach", "apricot"),
    "Gamma Decalactone": ("peach", "coconut"),
    "Apritone": ("apricot", "peach"),
    # Step 7: gamma-nonalactone's coconut, on both its owned stock names.
    "Gamma Nonalactone": ("coconut",),
    "Aldehyde C-18": ("coconut",),
    # Frangipani: benzyl salicylate and nerolidol, named in two frangipani descriptions.
    "Benzyl Salicylate": ("frangipani", "plumeria"),
    "Nerolidol": ("frangipani", "plumeria"),
}
REVIEWS_PATH = Path(PACK_PATH).with_name("source_reviews_v1.json")


@pytest.mark.parametrize("stock", sorted(SIGNATURES))
def test_each_signature_note_comes_from_a_reviewed_description(stock: str) -> None:
    reviewed = material_knowledge(stock)

    assert reviewed is not None
    assert set(SIGNATURES[stock]) <= set(reviewed["vocabulary"])
    pack = json.loads(PACK_PATH.read_text(encoding="utf-8"))
    reviews = {
        row["source_id"]: row
        for row in json.loads(REVIEWS_PATH.read_text(encoding="utf-8"))["records"]
    }
    claims = {claim["claim_id"]: claim for claim in pack["claims"]}
    sources = {source["source_id"]: source for source in pack["sources"]}
    for claim_id in reviewed["claim_ids"]:
        claim = claims[claim_id]
        assert claim["kind"] == "MANUFACTURER_DESCRIPTION"
        assert claim["numeric_calibration"] is False
        for source_id in claim["source_ids"]:
            source = sources[source_id]
            assert source["url"].startswith("https://")
            assert reviews[source_id]["review_state"] == "REVIEWED_ADVISORY"
            assert reviews[source_id]["source_record_sha256"] == source_record_hash(source)


def test_every_owned_stock_of_these_materials_carries_its_notes() -> None:
    index = build_material_capability_index()
    seen = set()
    for capability in index.capabilities:
        words = SIGNATURES.get(capability.identity_name)
        if not words:
            continue
        seen.add(capability.identity_name)
        assert all(carries(capability, word) == "descriptor" for word in words), capability.stock_label
    assert seen == set(SIGNATURES)


def test_a_pear_brief_leads_its_fruit_with_a_stock_that_smells_of_pear() -> None:
    result = design_formula(idea="A pear and vanilla perfume")

    facets = {
        row["slot"]: row["identity_name"]
        for row in result["optimized_formula"]["rows"]
        if row["slot"].startswith("facet_")
    }
    # Hexyl Acetate led until 29 Oct 2026; Liffarome (green, leafy-fruity, pear in its
    # registry sentence) now does. Either way the lead's own words name pear.
    lead = facets["facet_fruit"]
    caps = [c for c in build_material_capability_index().capabilities if c.identity_name == lead]
    assert caps and all("pear" in c.descriptor_vocabulary for c in caps), lead


@pytest.mark.parametrize(
    "idea",
    [
        "Fresh frangipani on skin, creamy, soft vanilla",
        "A frangipani and amber perfume",
        "Plumeria petals over warm amber",
    ],
)
def test_a_frangipani_brief_leads_it_with_a_stock_that_names_frangipani(idea: str) -> None:
    # The note's own role may only take a stock whose reviewed description names it, or
    # the owned Frangipani Absolute itself (its floral profile names no "frangipani";
    # it arrived after this test was written), never any white floral.
    named = {
        capability.identity_name
        for capability in build_material_capability_index().capabilities
        if "frangipani" in capability.descriptor_vocabulary
    } | {"Frangipani Absolute"}
    result = design_formula(idea=idea)

    facets = {
        row["slot"]: row["identity_name"]
        for row in result["optimized_formula"]["rows"]
        if row["slot"].startswith("facet_")
    }
    assert facets["facet_frangipani"] in named
