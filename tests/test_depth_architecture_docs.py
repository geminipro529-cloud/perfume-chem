from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOC_ROOT = ROOT / "docs" / "depth_architecture"
INDEX = DOC_ROOT / "README.md"
VOLUMES = (
    "01_construct_boundaries.md",
    "02_named_object_identity.md",
    "03_material_information_theory.md",
    "04_internal_anatomy_resolution.md",
    "05_relational_topology.md",
    "06_contrast_shadow_negative_space.md",
    "07_texture_materiality.md",
    "08_temporal_architecture.md",
    "09_spatial_architecture_performance.md",
    "10_hedonic_architecture.md",
    "11_nonlinear_mixture_behavior.md",
    "12_physical_chemistry_constraints.md",
    "13_family_translations.md",
    "14_comparison_benchmarking.md",
    "15_experimental_validation.md",
)
REQUIRED_SECTIONS = (
    "## Construct",
    "## Mechanisms",
    "## Material translation",
    "## Interactions",
    "## Failure modes",
    "## Observables",
    "## Controlled tests",
    "## Claim boundary",
    "## Primary literature",
)


def _substantive_words(text: str) -> list[str]:
    without_urls = re.sub(r"https?://\S+", " ", text)
    return re.findall(r"[A-Za-z][A-Za-z'-]{2,}", without_urls)


def test_depth_doctrine_index_links_every_volume_and_defines_precedence() -> None:
    text = INDEX.read_text(encoding="utf-8")

    for filename in VOLUMES:
        assert f"({filename})" in text
    assert "normative precedence" in text.casefold()
    assert "single score" in text.casefold()
    assert "NOT TESTED" in text


@pytest.mark.parametrize("filename", VOLUMES)
def test_each_depth_volume_is_substantial_and_complete(filename: str) -> None:
    path = DOC_ROOT / filename
    text = path.read_text(encoding="utf-8")

    for section in REQUIRED_SECTIONS:
        assert section in text, f"{filename} lacks {section}"
    assert len(_substantive_words(text)) >= 1000, f"{filename} is still compressed"
    assert "NOT TESTED" in text
    assert not re.search(
        r"(?im)^\s*(?:depth|perceptual depth)\s*=\s*(?:ingredient|row|material)\s*count\s*$",
        text,
    )
    assert not re.search(
        r"(?im)^\s*(?:total|overall)\s+depth\s+score\s*=",
        text,
    )


def test_floral_summary_defers_to_the_universal_depth_doctrine() -> None:
    text = (ROOT / "docs" / "floral_depth_architecture_theory.md").read_text(
        encoding="utf-8"
    )

    assert "docs/depth_architecture/README.md" in text
    assert "universal depth doctrine" in text.casefold()
    assert "normative precedence" in text.casefold()


def test_family_translation_preserves_migration_and_saturated_targets() -> None:
    text = (DOC_ROOT / "13_family_translations.md").read_text(encoding="utf-8").casefold()

    for family_name in (
        "floral",
        "woody",
        "amber",
        "leather",
        "chypre",
        "fougere",
        "gourmand",
        "citrus",
        "aromatic",
        "green",
        "fruity",
        "aquatic",
        "mineral",
        "musk",
        "incense",
        "tobacco",
        "aldehydic",
        "hybrid",
    ):
        assert f"### {family_name}" in text
    assert "temporally migratory" in text
    assert "low negative space is not a universal defect" in text


def test_experimental_validation_locks_high_risk_quality_controls() -> None:
    text = (DOC_ROOT / "15_experimental_validation.md").read_text(encoding="utf-8").casefold()

    for required_control in (
        "constant-total",
        "dilution-series",
        "olfactory adaptation",
        "maturation",
        "skin",
        "below ten microlitres",
        "stock rebasing",
        "hedonic valence",
        "hedonic complexity",
        "ties",
        "abstention",
        "not tested",
    ):
        assert required_control in text
