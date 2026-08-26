from engine.intervention_hypotheses import (
    InterventionHypothesisRequest,
    generate_intervention_hypotheses,
)
from engine.interventions import (
    VERSIONED_FINISHED_PRODUCT_SAFETY,
    BriefConstraints,
    CandidateAddition,
    InterventionRequest,
    InventoryStock,
    rank_interventions,
)
from engine.safety_assessment import SafetyAssessmentStatus
from engine.scientific_contract import EvidenceDescriptor, ScientificClass

FORMULA_STATE_SHA256 = "a" * 64


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
    safety_authority: str | None = None,
    safety_evidence: EvidenceDescriptor | None = None,
    safety_formula_state_sha256: str | None = None,
    safety_assessed_active_ppm_w_w: float | None = None,
) -> CandidateAddition:
    if safety is SafetyAssessmentStatus.PASS:
        safety_authority = safety_authority or VERSIONED_FINISHED_PRODUCT_SAFETY
        safety_evidence = safety_evidence or EvidenceDescriptor(
            classification=ScientificClass.LITERATURE_DERIVED,
            basis="Versioned finished-product screening for the bound formula state.",
            sources=("https://ifrafragrance.org/using-the-standards",),
            limitations=(
                "Screening is not a certificate or a substitute for product safety assessment.",
            ),
        )
        safety_formula_state_sha256 = (
            safety_formula_state_sha256 or FORMULA_STATE_SHA256
        )
        if safety_assessed_active_ppm_w_w is None:
            safety_assessed_active_ppm_w_w = 1_000.0
    return CandidateAddition(
        material=material,
        requested_active_ppm_w_w=ppm,
        predicted_oav_delta=ppm / 10.0,
        desired_effects=effects,
        preserved_character_tags=preserves,
        safety_status=safety,
        safety_authority=safety_authority or "caller_declared",
        safety_evidence=safety_evidence,
        safety_formula_state_sha256=safety_formula_state_sha256 or "",
        safety_assessed_active_ppm_w_w=safety_assessed_active_ppm_w_w,
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
        formula_state_sha256=FORMULA_STATE_SHA256,
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
        formula_state_sha256=FORMULA_STATE_SHA256,
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


def test_interventions_reject_caller_declared_safety_pass():
    candidate = _candidate(
        "Alpha Irone",
        ppm=100.0,
        effects={"iris": 1.0},
        safety_authority="caller_declared",
        safety_evidence=EvidenceDescriptor(
            classification=ScientificClass.LITERATURE_DERIVED,
            basis="Unbound client claim.",
            sources=("https://ifrafragrance.org/using-the-standards",),
        ),
        safety_formula_state_sha256="b" * 64,
    )
    request = InterventionRequest(
        batch_mass_g=10.0,
        brief=BriefConstraints(name="Iris Cathedral"),
        inventory={"Alpha Irone": _stock("Alpha Irone")},
        candidates=(candidate,),
        formula_state_sha256=FORMULA_STATE_SHA256,
    )

    result = rank_interventions(request)

    assert result.ranked == ()
    reasons = result.rejected[0].reasons
    assert (
        "safety pass is caller-declared, not a versioned finished-product assessment"
        in reasons
    )
    assert "safety assessment is not bound to this formula state" in reasons


def test_interventions_accept_formula_bound_dose_covering_safety_assessment():
    request = InterventionRequest(
        batch_mass_g=10.0,
        brief=BriefConstraints(name="Iris Cathedral"),
        inventory={"Alpha Irone": _stock("Alpha Irone")},
        candidates=(
            _candidate(
                "Alpha Irone",
                ppm=100.0,
                effects={"iris": 1.0},
                safety_assessed_active_ppm_w_w=100.0,
            ),
        ),
        formula_state_sha256=FORMULA_STATE_SHA256,
    )

    result = rank_interventions(request)

    assert [item.material for item in result.ranked] == ["Alpha Irone"]
    assert result.ranked[0].safety_authority == VERSIONED_FINISHED_PRODUCT_SAFETY
    assert result.ranked[0].safety_formula_state_sha256 == FORMULA_STATE_SHA256
    assert result.ranked[0].safety_assessed_active_ppm_w_w == 100.0


def test_interventions_reject_safety_assessment_below_rounded_achieved_dose():
    request = InterventionRequest(
        batch_mass_g=10.0,
        brief=BriefConstraints(name="Iris Cathedral"),
        inventory={"Alpha Irone": _stock("Alpha Irone")},
        candidates=(
            _candidate(
                "Alpha Irone",
                ppm=100.04,
                effects={"iris": 1.0},
                safety_assessed_active_ppm_w_w=100.04,
            ),
        ),
        formula_state_sha256=FORMULA_STATE_SHA256,
    )

    result = rank_interventions(request)

    assert result.ranked == ()
    assert (
        "safety assessment does not cover the achieved active dose"
        in result.rejected[0].reasons
    )


def test_hypotheses_are_inventory_only_noncausal_and_nonquantitative():
    result = generate_intervention_hypotheses(
        InterventionHypothesisRequest(
            brief_name="Iris Cathedral",
            observations=("too woody", "unmapped bottle note"),
            family="muguet",
            mode="post_mix",
            available_materials=("Hedione", "Peonile"),
            forbidden_materials=frozenset({"Peonile"}),
        )
    )

    assert result.brief_name == "Iris Cathedral"
    assert [item.signal for item in result.diagnoses] == ["too_woody"]
    assert result.unrecognized_observations == ("unmapped_bottle_note",)
    assert result.hypotheses
    for hypothesis in result.hypotheses:
        assert hypothesis.materials == ("Hedione",)
        assert not hasattr(hypothesis, "requested_active_ppm_w_w")
        assert not hasattr(hypothesis, "predicted_oav_delta")
        assert not hasattr(hypothesis, "safety_status")
    assert result.evidence.classification.value == "HEURISTIC"
    assert any("causal" in item for item in result.evidence.limitations)
    assert any("dose" in item for item in result.evidence.limitations)


def test_hypotheses_do_not_fall_back_when_inventory_has_no_matching_material():
    result = generate_intervention_hypotheses(
        InterventionHypothesisRequest(
            brief_name="Iris Cathedral",
            observations=("too woody",),
            family="muguet",
            mode="post_mix",
            available_materials=("Not A Real Stock",),
        )
    )

    assert result.diagnoses
    assert result.hypotheses == ()
