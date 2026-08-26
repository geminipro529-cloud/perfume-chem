from engine.quantities import Concentration, ConcentrationBasis
from engine.safety_assessment import (
    ConstituentComposition,
    RestrictionDataset,
    RestrictionEntry,
    SafetyAssessmentRequest,
    SafetyAssessmentStatus,
    assess_safety,
)


def _mass_fraction(ppm: float) -> Concentration:
    return Concentration.from_ppm(
        ppm,
        basis=ConcentrationBasis.MASS_FRACTION,
        medium="finished_product",
    )


def _dataset(*entries: RestrictionEntry, covered: tuple[str, ...]) -> RestrictionDataset:
    return RestrictionDataset(
        source_name="IFRA Standards Library",
        amendment="51st Amendment",
        source_url="https://ifrafragrance.org/standards-library",
        entries=entries,
        covered_materials=frozenset(covered),
    )


def test_safety_is_unverified_without_version_category_or_coverage():
    result = assess_safety(
        SafetyAssessmentRequest(
            category="",
            concentrations={"Hydroxycitronellal": _mass_fraction(50.0)},
            dataset=None,
        )
    )

    assert result.status is SafetyAssessmentStatus.UNVERIFIED
    assert "product category" in result.unresolved_inputs
    assert "versioned restriction dataset" in result.unresolved_inputs
    assert result.evidence.classification.value == "UNKNOWN"


def test_safety_fails_when_finished_product_ppm_exceeds_category_limit():
    dataset = _dataset(
        RestrictionEntry(
            material="Hydroxycitronellal",
            category="4",
            maximum=_mass_fraction(100.0),
        ),
        covered=("Hydroxycitronellal",),
    )

    result = assess_safety(
        SafetyAssessmentRequest(
            category="4",
            concentrations={"Hydroxycitronellal": _mass_fraction(125.0)},
            dataset=dataset,
        )
    )

    assert result.status is SafetyAssessmentStatus.FAIL
    assert result.loads_ppm_w_w["Hydroxycitronellal"] == 125.0
    assert result.findings[0].maximum_ppm_w_w == 100.0
    assert result.findings[0].ratio_to_limit == 1.25
    assert result.evidence.classification.value == "LITERATURE_DERIVED"


def test_safety_pass_requires_complete_constituent_and_dataset_coverage():
    dataset = _dataset(
        RestrictionEntry(
            material="Limonene",
            category="4",
            maximum=_mass_fraction(1000.0),
        ),
        covered=("Limonene",),
    )
    incomplete = assess_safety(
        SafetyAssessmentRequest(
            category="4",
            concentrations={"Bergamot EO": _mass_fraction(1000.0)},
            dataset=dataset,
            opaque_mixtures=frozenset({"Bergamot EO"}),
            constituent_compositions={
                "Bergamot EO": ConstituentComposition(
                    fractions={"Limonene": 0.40},
                    complete=False,
                    source="supplier certificate",
                )
            },
        )
    )
    complete = assess_safety(
        SafetyAssessmentRequest(
            category="4",
            concentrations={"Bergamot EO": _mass_fraction(1000.0)},
            dataset=dataset,
            opaque_mixtures=frozenset({"Bergamot EO"}),
            constituent_compositions={
                "Bergamot EO": ConstituentComposition(
                    fractions={"Limonene": 0.40},
                    complete=True,
                    source="supplier certificate",
                )
            },
        )
    )

    assert incomplete.status is SafetyAssessmentStatus.UNVERIFIED
    assert "incomplete constituent composition: Bergamot EO" in incomplete.unresolved_inputs
    assert complete.status is SafetyAssessmentStatus.PASS
    assert complete.loads_ppm_w_w["Limonene"] == 400.0


def test_known_violation_fails_even_when_other_constituents_are_unresolved():
    dataset = _dataset(
        RestrictionEntry(
            material="Limonene",
            category="4",
            maximum=_mass_fraction(100.0),
        ),
        covered=("Limonene",),
    )

    result = assess_safety(
        SafetyAssessmentRequest(
            category="4",
            concentrations={"Bergamot EO": _mass_fraction(1000.0)},
            dataset=dataset,
            opaque_mixtures=frozenset({"Bergamot EO"}),
            constituent_compositions={
                "Bergamot EO": ConstituentComposition(
                    fractions={"Limonene": 0.20},
                    complete=False,
                    source="supplier certificate",
                )
            },
        )
    )

    assert result.status is SafetyAssessmentStatus.FAIL
    assert result.findings[0].ratio_to_limit == 2.0
    assert "incomplete constituent composition: Bergamot EO" in result.unresolved_inputs


def test_safety_rejects_unqualified_concentration_basis():
    dataset = _dataset(covered=("Hydroxycitronellal",))
    result = assess_safety(
        SafetyAssessmentRequest(
            category="4",
            concentrations={
                "Hydroxycitronellal": Concentration.from_ppm(
                    50.0,
                    basis=ConcentrationBasis.VOLUME_FRACTION,
                    medium="finished_product",
                )
            },
            dataset=dataset,
        )
    )

    assert result.status is SafetyAssessmentStatus.UNVERIFIED
    assert any("mass fraction" in item for item in result.unresolved_inputs)
