from engine.interventions import (
    BriefConstraints,
    CandidateAddition,
    InterventionRequest,
    InventoryStock,
    rank_interventions,
)
from engine.safety_assessment import SafetyAssessmentStatus


def _stock(material: str, available_mg: float = 1000.0) -> InventoryStock:
    return InventoryStock(
        material=material,
        available_stock_mass_mg=available_mg,
        active_mass_fraction=0.10,
        minimum_measurable_stock_mass_mg=1.0,
        dispensing_increment_mg=1.0,
    )


def _candidate(
    material: str,
    *,
    ppm: float,
    effects: dict[str, float],
    safety: SafetyAssessmentStatus = SafetyAssessmentStatus.PASS,
    preserves: frozenset[str] = frozenset({"iris", "incense"}),
) -> CandidateAddition:
    return CandidateAddition(
        material=material,
        requested_active_ppm_w_w=ppm,
        predicted_oav_delta=ppm / 10.0,
        desired_effects=effects,
        preserved_character_tags=preserves,
        safety_status=safety,
    )


def test_interventions_filter_forbidden_unavailable_unmeasurable_and_unverified():
    request = InterventionRequest(
        batch_mass_g=30.0,
        brief=BriefConstraints(
            name="Iris Cathedral",
            required_character_tags=frozenset({"iris", "incense"}),
            forbidden_materials=frozenset({"Ethyl Maltol"}),
            maximum_active_addition_ppm_w_w=500.0,
        ),
        inventory={
            "Ethyl Maltol": _stock("Ethyl Maltol"),
            "Hedione": _stock("Hedione", available_mg=0.5),
            "Alpha Irone": _stock("Alpha Irone"),
            "Olibanum Resinoid": _stock("Olibanum Resinoid"),
        },
        candidates=(
            _candidate("Ethyl Maltol", ppm=100.0, effects={"lift": 1.0}),
            _candidate("Hedione", ppm=100.0, effects={"lift": 1.0}),
            _candidate(
                "Alpha Irone",
                ppm=1.0,
                effects={"iris": 1.0},
            ),
            _candidate(
                "Olibanum Resinoid",
                ppm=100.0,
                effects={"depth": 1.0},
                safety=SafetyAssessmentStatus.UNVERIFIED,
            ),
        ),
    )

    result = rank_interventions(request)

    assert result.ranked == ()
    rejected = {item.material: item.reasons for item in result.rejected}
    assert "forbidden by brief" in rejected["Ethyl Maltol"]
    assert "insufficient stock" in rejected["Hedione"]
    assert "below measurable stock dose" in rejected["Alpha Irone"]
    assert "safety status is not pass" in rejected["Olibanum Resinoid"]


def test_interventions_preserve_brief_and_return_only_pareto_candidates():
    request = InterventionRequest(
        batch_mass_g=10.0,
        brief=BriefConstraints(
            name="Iris Cathedral",
            required_character_tags=frozenset({"iris", "incense"}),
            maximum_active_addition_ppm_w_w=500.0,
        ),
        inventory={
            "Alpha Irone": _stock("Alpha Irone"),
            "Orris Liquid": _stock("Orris Liquid"),
            "Hedione": _stock("Hedione"),
        },
        candidates=(
            _candidate("Alpha Irone", ppm=100.0, effects={"iris": 1.0, "depth": 0.8}),
            _candidate("Orris Liquid", ppm=200.0, effects={"iris": 0.5, "depth": 0.4}),
            _candidate(
                "Hedione",
                ppm=100.0,
                effects={"iris": 2.0, "depth": 2.0},
                preserves=frozenset({"iris"}),
            ),
        ),
    )

    result = rank_interventions(request)

    assert [item.material for item in result.ranked] == ["Alpha Irone"]
    assert result.ranked[0].achieved_active_ppm_w_w == 100.0
    assert result.ranked[0].predicted_oav_delta == 10.0
    assert result.evidence.classification.value == "HEURISTIC"
    assert "Iris Cathedral" in result.evidence.basis
    rejected = {item.material: item.reasons for item in result.rejected}
    assert "does not preserve required character tags: incense" in rejected["Hedione"]
    assert "Pareto-dominated" in rejected["Orris Liquid"]
