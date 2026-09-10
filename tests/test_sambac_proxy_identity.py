"""Jasmine Sambac resolves through an explicit proxy; generic Jasmine stays distinct."""

from __future__ import annotations

from engine.pipeline.natural_absolute_decomposition import (
    get_composite_metadata,
    get_constituents,
)


def test_sambac_absolute_uses_the_explicit_literature_proxy() -> None:
    metadata = get_composite_metadata("Jasmine Sambac Absolute")

    assert metadata is not None
    assert metadata.profile_key == "jasmine sambac"
    assert metadata.resolution == "literature_proxy"
    assert metadata.composition_authority == "LITERATURE_PARTIAL_PROXY"
    assert metadata.batch_specific is False
    assert 0.0 < metadata.characterized_fraction <= 1.0
    assert get_constituents("Jasmine Sambac Absolute")
    assert any(
        "not a supplier-batch GC-MS or GC-O assay" in limitation
        for limitation in metadata.limitations
    )


def test_generic_jasmine_absolute_is_not_collapsed_into_sambac() -> None:
    generic = get_composite_metadata("Jasmine Absolute")
    sambac = get_composite_metadata("Jasmine Sambac Absolute")

    assert generic is not None
    assert sambac is not None
    assert generic.profile_key != sambac.profile_key
    assert generic.resolution != "literature_proxy"
