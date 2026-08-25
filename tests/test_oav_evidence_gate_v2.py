from __future__ import annotations

from dataclasses import replace

import pytest

from engine.evidence_contracts import (
    EvidenceBasis,
    EvidenceSourceRef,
    QuantitativeEvidence,
)
from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.oav_evidence import (
    OAVEvidenceRequest,
    OAVEvidenceState,
    OAVMaterialEvidenceInput,
    evaluate_oav_evidence,
    oav_evidence_request_from_formula_state,
)

FORMULA_SHA = "a" * 64
DOSE_SHA = "b" * 64


def _source(source_id: str = "source") -> EvidenceSourceRef:
    return EvidenceSourceRef(
        source_id=source_id,
        source_uri=f"https://example.test/{source_id}",
        retrieved_on="2026-08-26",
        source_sha256="c" * 64,
    )


def _quantitative(
    value: float | None,
    *,
    basis: EvidenceBasis,
    unit: str = "ppm",
    context: str = "air at 25 C",
    method: str = "GC-O",
) -> QuantitativeEvidence:
    return QuantitativeEvidence(
        value=value,
        unit=unit if basis is not EvidenceBasis.UNKNOWN else "",
        context=context if basis is not EvidenceBasis.UNKNOWN else "",
        method=method if basis is not EvidenceBasis.UNKNOWN else "",
        basis=basis,
        source=None if basis is EvidenceBasis.UNKNOWN else _source(method),
    )


def _row(
    name: str = "Hedione",
    *,
    headspace_basis: EvidenceBasis = EvidenceBasis.MEASURED,
    threshold_basis: EvidenceBasis = EvidenceBasis.MEASURED,
    headspace_value: float | None = 2.0,
    threshold_value: float | None = 1.0,
    exact_stock_ref: str | None = "stock:HEDIONE:lot-1",
    supplied_strength_fraction: float | None = 1.0,
    active_mass_g: float | None = 0.1,
    natural_or_preblend: bool = False,
    constituent_evidence: tuple[QuantitativeEvidence, ...] = (),
) -> OAVMaterialEvidenceInput:
    return OAVMaterialEvidenceInput(
        material_name=name,
        canonical_name=name,
        exact_stock_ref=exact_stock_ref,
        supplied_strength_fraction=supplied_strength_fraction,
        carrier=None,
        active_mass_g=active_mass_g,
        formula_matrix="ethanol-air at 25 C",
        headspace=_quantitative(
            headspace_value,
            basis=headspace_basis,
            method="measured headspace" if headspace_basis is EvidenceBasis.MEASURED else "model",
        ),
        threshold=_quantitative(
            threshold_value,
            basis=threshold_basis,
            method="GC-O threshold",
        ),
        natural_or_preblend=natural_or_preblend,
        constituent_evidence=constituent_evidence,
    )


def _request(
    rows: tuple[OAVMaterialEvidenceInput, ...],
) -> OAVEvidenceRequest:
    return OAVEvidenceRequest(
        formula_sha256=FORMULA_SHA,
        dose_receipt_sha256=DOSE_SHA,
        measurement_context="air at 25 C",
        rows=rows,
    )


def test_all_measured_exact_rows_are_strict_measured() -> None:
    result = evaluate_oav_evidence(_request((_row(),)))
    assert result.state is OAVEvidenceState.STRICT_MEASURED
    assert result.rows[0].oav == 2.0
    assert result.rows[0].threshold_screening == "ABOVE_OR_AT_THRESHOLD"
    assert result.rows[0].recognizable_in_mixture is None
    assert result.sensory_authority is False
    assert result.hedonic_authority is False
    assert result.release_authority is False


def test_modeled_headspace_is_a_modeled_screen_not_measurement() -> None:
    result = evaluate_oav_evidence(
        _request((_row(headspace_basis=EvidenceBasis.MODELED),))
    )
    assert result.state is OAVEvidenceState.MODELED_SCREEN
    assert result.rows[0].headspace_basis is EvidenceBasis.MODELED
    assert "prediction screen" in result.rows[0].limitations[0]


@pytest.mark.parametrize(
    "row",
    [
        _row(threshold_basis=EvidenceBasis.TRANSFERRED),
        _row(exact_stock_ref=None),
        _row(supplied_strength_fraction=None),
        _row(active_mass_g=None),
    ],
)
def test_transferred_or_missing_lineage_is_partial(
    row: OAVMaterialEvidenceInput,
) -> None:
    result = evaluate_oav_evidence(_request((row,)))
    assert result.state is OAVEvidenceState.PARTIAL
    assert result.rows[0].state is OAVEvidenceState.PARTIAL


@pytest.mark.parametrize(
    "row",
    [
        _row(
            headspace_basis=EvidenceBasis.UNKNOWN,
            headspace_value=None,
        ),
        _row(
            threshold_basis=EvidenceBasis.UNKNOWN,
            threshold_value=None,
        ),
    ],
)
def test_unknown_quantities_abstain_without_coercing_to_zero(
    row: OAVMaterialEvidenceInput,
) -> None:
    result = evaluate_oav_evidence(_request((row,)))
    assert result.state is OAVEvidenceState.ABSTAINED
    assert result.rows[0].oav is None
    assert result.rows[0].threshold_screening == "NOT_COMPUTABLE"


def test_one_missing_row_makes_an_otherwise_numeric_request_partial() -> None:
    missing = _row(
        "Unknown",
        threshold_basis=EvidenceBasis.UNKNOWN,
        threshold_value=None,
    )
    result = evaluate_oav_evidence(_request((_row(), missing)))
    assert result.state is OAVEvidenceState.PARTIAL
    assert tuple(row.state for row in result.rows) == (
        OAVEvidenceState.STRICT_MEASURED,
        OAVEvidenceState.ABSTAINED,
    )


def test_unit_or_context_mismatch_is_invalid() -> None:
    unit_mismatch = replace(
        _row(),
        threshold=_quantitative(
            1.0,
            basis=EvidenceBasis.MEASURED,
            unit="ppb",
            method="GC-O threshold",
        ),
    )
    context_mismatch = replace(
        _row(),
        threshold=_quantitative(
            1.0,
            basis=EvidenceBasis.MEASURED,
            context="ethanol solution",
            method="GC-O threshold",
        ),
    )
    for row in (unit_mismatch, context_mismatch):
        result = evaluate_oav_evidence(_request((row,)))
        assert result.state is OAVEvidenceState.INVALID
        assert result.rows[0].oav is None
        assert result.blockers


def test_nonpositive_threshold_and_contradictory_natural_treatment_are_invalid() -> None:
    zero_threshold = replace(
        _row(),
        threshold=_quantitative(
            0.0,
            basis=EvidenceBasis.MEASURED,
            method="GC-O threshold",
        ),
    )
    stray_constituents = replace(
        _row(),
        constituent_evidence=(
            _quantitative(0.2, basis=EvidenceBasis.MEASURED),
        ),
    )
    for row in (zero_threshold, stray_constituents):
        result = evaluate_oav_evidence(_request((row,)))
        assert result.state is OAVEvidenceState.INVALID


def test_natural_remains_one_formula_row_with_nested_uncertainty() -> None:
    natural = _row(
        "Bergamot FCF",
        natural_or_preblend=True,
        constituent_evidence=(
            _quantitative(0.4, basis=EvidenceBasis.TRANSFERRED),
            _quantitative(0.1, basis=EvidenceBasis.TRANSFERRED),
        ),
    )
    result = evaluate_oav_evidence(_request((natural,)))
    assert len(result.rows) == 1
    assert result.rows[0].material_name == "Bergamot FCF"
    assert result.rows[0].state is OAVEvidenceState.PARTIAL
    assert result.rows[0].constituent_evidence_count == 2


def test_perceptible_count_cannot_promote_oav_evidence_state() -> None:
    one = evaluate_oav_evidence(
        _request((_row("A", headspace_basis=EvidenceBasis.MODELED),))
    )
    many = evaluate_oav_evidence(
        _request(
            tuple(
                _row(f"A-{index}", headspace_basis=EvidenceBasis.MODELED)
                for index in range(20)
            )
        )
    )
    assert one.state is OAVEvidenceState.MODELED_SCREEN
    assert many.state is OAVEvidenceState.MODELED_SCREEN
    assert not hasattr(many, "authority_rank_score")
    assert not hasattr(many, "total_oav")


def test_serialized_contract_has_no_operative_perceptual_or_hedonic_claims() -> None:
    payload = evaluate_oav_evidence(_request((_row(),))).as_dict()
    assert payload["schema_version"] == "oav_evidence_v2"
    forbidden = {
        "total_oav",
        "percent_contribution",
        "balance",
        "diffusion",
        "liking",
        "beauty",
        "synergy",
        "similarity",
        "observed_transition",
        "authority_rank_score",
    }
    assert forbidden.isdisjoint(payload)
    assert payload["authority"]["sensory"] is False
    assert payload["authority"]["hedonic"] is False
    assert payload["authority"]["release"] is False


def test_duplicate_material_rows_make_the_request_invalid() -> None:
    result = evaluate_oav_evidence(_request((_row(), _row())))
    assert result.state is OAVEvidenceState.INVALID
    assert "duplicate material row" in result.blockers[0]


def test_formula_state_adapter_labels_simulator_headspace_modeled() -> None:
    state = build_formula_state(
        {"Hedione": 1000.0},
        stock_specs={
            "Hedione": {
                "fraction": 1.0,
                "basis": "neat",
                "carrier": None,
                "declared": True,
            }
        },
    )
    request = oav_evidence_request_from_formula_state(
        state,
        formula_sha256=FORMULA_SHA,
        dose_receipt_sha256=DOSE_SHA,
        exact_stock_refs={"Hedione": "stock:HEDIONE:lot-1"},
        model_source=_source("formula-state-model"),
        threshold_sources={"Hedione": _source("odt-registry")},
    )
    assert request.rows[0].headspace.basis is EvidenceBasis.MODELED
    assert request.rows[0].threshold.basis is EvidenceBasis.TRANSFERRED
    assert evaluate_oav_evidence(request).state is OAVEvidenceState.PARTIAL


def test_formula_state_adapter_preserves_missing_odt_as_unknown() -> None:
    state = build_formula_state({"Mystery Molecule": 1000.0})
    request = oav_evidence_request_from_formula_state(
        state,
        formula_sha256=FORMULA_SHA,
        dose_receipt_sha256=DOSE_SHA,
        exact_stock_refs={},
        model_source=_source("formula-state-model"),
        threshold_sources={},
    )
    assert request.rows[0].threshold.basis is EvidenceBasis.UNKNOWN
    assert request.rows[0].threshold.value is None
    assert evaluate_oav_evidence(request).state is OAVEvidenceState.ABSTAINED


def test_request_rejects_invalid_hashes_and_empty_context() -> None:
    with pytest.raises(ValueError, match="formula_sha256"):
        OAVEvidenceRequest("bad", DOSE_SHA, "air", (_row(),))
    with pytest.raises(ValueError, match="measurement_context"):
        OAVEvidenceRequest(FORMULA_SHA, DOSE_SHA, "", (_row(),))
