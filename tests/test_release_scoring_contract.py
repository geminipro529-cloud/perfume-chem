from types import SimpleNamespace

from engine.pipeline.release_scoring import compute_unified_release_scores


def _formula():
    return {
        "number": 1,
        "name": "Unified Score Test",
        "ingredients_ul": {
            "Lavender EO": 700.0,
            "Hedione": 900.0,
            "Coumarin": 300.0,
            "Iso E Super": 1500.0,
        },
        "dilutions": {
            "Lavender EO": 1.0,
            "Hedione": 1.0,
            "Coumarin": 0.2,
            "Iso E Super": 1.0,
        },
    }


class _StubScorer:
    def score(self, _formula_vector, *, formula_state=None):
        del formula_state
        return {
            "total": 72.0,
            "photorealism": 99.0,
            "longevity": 60.0,
            "sillage": 55.0,
            "skin_performance": 50.0,
        }


class _PriceRegistry:
    def __init__(self, prices):
        self._prices = prices

    def get(self, name):
        if name not in self._prices:
            return None
        return SimpleNamespace(
            supplier=SimpleNamespace(
                perfumersworld_price_usd_per_g=self._prices[name]
            )
        )


def _diagnostic_formula():
    return {
        "number": 1,
        "name": "Missingness Contract Test",
        "ingredients_ul": {"Top Material": 100.0, "Base Material": 100.0},
        "dilutions": {"Top Material": 1.0, "Base Material": 1.0},
    }


def _oav_result(*, canonical_oavs=(10.0, 2.0), window_count=3):
    rows = tuple(
        SimpleNamespace(
            name=name,
            canonical_name=name,
            oav=screening_oav,
            canonical_oav=canonical_oav,
            note=note,
            odt_source="peer_reviewed:test",
            gamma_source="measured:test",
            active_ul=100.0,
        )
        for name, note, screening_oav, canonical_oav in (
            ("Top Material", "top", 10.0, canonical_oavs[0]),
            ("Base Material", "base", 2.0, canonical_oavs[1]),
        )
    )
    windows = tuple(
        SimpleNamespace(
            family_envelope={"fresh": 0.6 - index * 0.1},
            dominant_oav=[{"material": rows[index % len(rows)].name}],
        )
        for index in range(window_count)
    )
    return SimpleNamespace(
        state=object(),
        material_rows=rows,
        time_windows=windows,
        intelligence_status="SCREENING_ONLY",
        intelligence_warning_reasons=(),
        authority_rank_score=0.0,
    )


def _gate_report(*, overall_fit=0.8):
    pyramid = {} if overall_fit is None else {"overall_fit": overall_fit}
    return {
        "gates": [
            {"gate": "perfume_knowledge", "status": "PASS", "data": {"pyramid": pyramid}}
        ],
        "preflight": {"checks": []},
    }


def test_unified_release_scoring_contract_has_provenance(monkeypatch):
    monkeypatch.setattr(
        "engine.data_spine.loader.load_registry",
        lambda: _PriceRegistry({"Top Material": 1.0, "Base Material": 2.0}),
    )
    payload = compute_unified_release_scores(
        _diagnostic_formula(),
        _oav_result(),
        _gate_report(),
        scorer=_StubScorer(),
    ).as_dict()

    assert "scores" in payload
    assert "industry_10" in payload
    assert "provenance" in payload
    assert "ranking" in payload
    assert "impact" in payload["industry_10"]
    assert "authority_rank_score" in payload["provenance"]
    assert "deterministic_sources" in payload["provenance"]
    assert "authoritative_inputs_used" in payload["provenance"]
    assert "heuristic_inputs_used" in payload["provenance"]
    assert "confidence_penalties" in payload["provenance"]
    assert "repairability" in payload["provenance"]
    assert payload["science_penalty"] == 0.0
    assert (
        payload["provenance"]["formula_science_coverage"]["scope"]
        == "formula_runtime"
    )
    assert not any(
        row.get("reason") == "sparse_science_coverage"
        for row in payload["provenance"]["confidence_penalties"]
    )
    score_contract = payload["provenance"]["score_contract"]
    assert score_contract["classification"] == "HEURISTIC_DIAGNOSTIC_INDICES"
    assert score_contract["release_authority"] is False
    assert score_contract["formula_optimization_authority"] is False
    assert score_contract["eligible_as_optimizer_selection_evidence"] is False
    assert set(score_contract["measured_search_feature_denylist"]) >= {
        "scores.total",
        "industry_10.*",
        "confidence_penalties",
        "oav_balance",
        "semantic_distance",
        "descriptor_distance",
    }
    assert score_contract["release_authorized_axes"] == []
    assert (
        score_contract["axis_authority"]["longevity"]
        == "HEURISTIC_UNCALIBRATED_NOT_SKIN_LIFE"
    )
    assert (
        score_contract["axis_authority"]["sillage"]
        == "HEURISTIC_UNCALIBRATED_NOT_MEASURED_SILLAGE"
    )
    assert (
        score_contract["axis_authority"]["skin_performance"]
        == "HEURISTIC_UNVALIDATED_NOT_SKIN_OUTCOME"
    )
    assert all(
        0.0 <= value <= 100.0
        for key, value in payload["scores"].items()
        if not key.startswith("_")
    )
    assert payload["ranking"]["status"] == "WITHHELD"
    assert payload["ranking"]["value"] is None
    assert payload["ranking"]["formula_optimization_authority"] is False
    assert payload["ranking"]["admitted_axes"] == []
    assert payload["ranking"]["diagnostic_total"] == payload["scores"]["total"]


def test_missing_industry_inputs_remain_none_with_reasons(monkeypatch):
    monkeypatch.setattr(
        "engine.data_spine.loader.load_registry", lambda: _PriceRegistry({})
    )
    payload = compute_unified_release_scores(
        _diagnostic_formula(),
        _oav_result(canonical_oavs=(None, None), window_count=2),
        _gate_report(overall_fit=None),
        scorer=_StubScorer(),
    ).as_dict()

    industry = payload["industry_10"]
    availability = payload["provenance"]["industry_10_availability"]
    assert industry["balance"] is None
    assert availability["balance"] == {
        "available": False,
        "reason_code": "PYRAMID_OVERALL_FIT_UNAVAILABLE",
    }
    assert industry["temporal_coherence"] is None
    assert availability["temporal_coherence"]["reason_code"] == (
        "INSUFFICIENT_TEMPORAL_WINDOWS"
    )
    assert availability["temporal_coherence"]["observed_windows"] == 2
    assert industry["oav_balance"] is None
    assert industry["versatility"] is None
    assert availability["oav_balance"]["reason_code"] == (
        "CANONICAL_OAV_COVERAGE_UNAVAILABLE"
    )
    assert industry["cost_efficiency"] is None
    assert availability["cost_efficiency"]["reason_code"] == (
        "SUPPLIER_PRICE_DATA_UNAVAILABLE"
    )
    assert industry["family_alignment"] is None
    assert industry["character"] is None
    assert payload["scores"]["photorealism"] == 99.0
    assert availability["family_alignment"]["reason_code"] == (
        "INDEPENDENT_FAMILY_ALIGNMENT_EVIDENCE_UNAVAILABLE"
    )
    assert payload["ranking"]["status"] == "WITHHELD"


def test_partial_price_coverage_withholds_cost_efficiency(monkeypatch):
    monkeypatch.setattr(
        "engine.data_spine.loader.load_registry",
        lambda: _PriceRegistry({"Top Material": 1.0}),
    )
    payload = compute_unified_release_scores(
        _diagnostic_formula(),
        _oav_result(),
        _gate_report(),
        scorer=_StubScorer(),
    ).as_dict()

    availability = payload["provenance"]["industry_10_availability"]
    assert payload["industry_10"]["cost_efficiency"] is None
    assert availability["cost_efficiency"]["reason_code"] == (
        "SUPPLIER_PRICE_COVERAGE_INCOMPLETE"
    )
    assert availability["cost_efficiency"]["priced_materials"] == 1
    assert availability["cost_efficiency"]["required_materials"] == 2
    assert availability["cost_efficiency"]["missing_price_materials"] == [
        "Base Material"
    ]


def test_partial_canonical_oav_coverage_withholds_balance(monkeypatch):
    monkeypatch.setattr(
        "engine.data_spine.loader.load_registry",
        lambda: _PriceRegistry({"Top Material": 1.0, "Base Material": 2.0}),
    )
    payload = compute_unified_release_scores(
        _diagnostic_formula(),
        _oav_result(canonical_oavs=(10.0, None)),
        _gate_report(),
        scorer=_StubScorer(),
    ).as_dict()

    availability = payload["provenance"]["industry_10_availability"]
    assert payload["industry_10"]["oav_balance"] is None
    assert availability["oav_balance"]["reason_code"] == (
        "CANONICAL_OAV_COVERAGE_INCOMPLETE"
    )
    assert availability["oav_balance"]["missing_canonical_oav_materials"] == [
        "Base Material"
    ]
    assert payload["industry_10"]["cost_efficiency"] is None
    assert availability["cost_efficiency"]["reason_code"] == (
        "OAV_BASIS_FOR_COST_EFFICIENCY_UNAVAILABLE"
    )


def test_complete_diagnostic_inputs_remain_numeric(monkeypatch):
    monkeypatch.setattr(
        "engine.data_spine.loader.load_registry",
        lambda: _PriceRegistry({"Top Material": 1.0, "Base Material": 2.0}),
    )
    payload = compute_unified_release_scores(
        _diagnostic_formula(),
        _oav_result(),
        _gate_report(),
        scorer=_StubScorer(),
    ).as_dict()

    industry = payload["industry_10"]
    availability = payload["provenance"]["industry_10_availability"]
    assert set(availability) == set(industry)
    for axis in ("balance", "temporal_coherence", "oav_balance", "cost_efficiency"):
        assert isinstance(industry[axis], float)
        assert availability[axis]["available"] is True
        assert availability[axis]["reason_code"] is None
    assert industry["balance"] == 80.0
    assert industry["family_alignment"] is None
    assert industry["character"] is None


def test_repairability_reports_missing_data_when_only_holds_block(monkeypatch):
    monkeypatch.setattr(
        "engine.data_spine.loader.load_registry",
        lambda: _PriceRegistry({"Top Material": 1.0, "Base Material": 2.0}),
    )
    gate_report = _gate_report()
    gate_report["gates"].append({"gate": "phase_compatibility", "status": "HOLD"})
    held = compute_unified_release_scores(
        _diagnostic_formula(), _oav_result(), gate_report, scorer=_StubScorer()
    ).as_dict()["provenance"]["repairability"]

    gate_report["gates"].append({"gate": "exact_subtotal", "status": "FAIL"})
    failed = compute_unified_release_scores(
        _diagnostic_formula(), _oav_result(), gate_report, scorer=_StubScorer()
    ).as_dict()["provenance"]["repairability"]

    assert held["status"] == "data_required"
    assert held["held_gates"] == ["phase_compatibility"]
    assert held["failed_gates"] == []
    assert failed["failed_gates"] == ["exact_subtotal"]
    assert failed["status"] not in {"data_required", "none_needed"}
