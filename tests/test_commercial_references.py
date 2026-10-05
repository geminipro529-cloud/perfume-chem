from __future__ import annotations

import socket
import time
import urllib.request

import pytest

from engine.research.commercial_references import (
    CommercialReferenceSampleV1,
    build_commercial_reference_panel,
    evaluate_reference_panel,
    load_commercial_reference_registry,
)
from engine.research.request_interpretation import (
    RequestInterpretationInputV1,
    interpret_request,
)


def test_lavender_amber_panel_is_deterministic_and_authority_bounded() -> None:
    registry = load_commercial_reference_registry()
    result = build_commercial_reference_panel(
        ("lavender", "ambrox"),
        as_of_date="2026-09-28",
        registry=registry,
    )
    assert result["status"] == "MARKET_SELECTED_REFERENCE_PANEL"
    assert [row["product_id"] for row in result["panel"]["active_members"]] == [
        "ysl-libre-edp",
        "dior-sauvage-edp",
        "prada-luna-rossa-carbon-edt",
        "burberry-goddess-edp",
    ]
    assert [row["product_id"] for row in result["panel"]["reserve_members"]] == [
        "mon-guerlain-edp"
    ]
    assert result["most_liked_claim"] is False
    assert result["best_composition_claim"] is False
    assert result["population_liking_state"] == "POPULATION_LIKING_NOT_ESTABLISHED"
    assert all(product["formula_composition_known"] is False for product in result["products"].values())
    assert registry.products["ysl-libre-edp"].market_position_authority is False
    assert registry.products["dior-sauvage-edp"].market_position_authority is False
    assert registry.evidence["lvmh-2025-sauvage-franchise"].market_scope == (
        "FRAGRANCE_FRANCHISE"
    )
    assert any(
        row["status"] == "RETRACTED_REJECTED"
        for row in registry.prohibited_sources
    )


def test_expired_market_evidence_cannot_select_a_panel() -> None:
    with pytest.raises(ValueError, match="EXPIRED"):
        build_commercial_reference_panel(
            ("lavender",),
            as_of_date="2027-09-29",
        )


def test_document_only_evaluation_returns_clues_not_a_sensory_winner() -> None:
    panel = build_commercial_reference_panel(
        ("lavender", "amber"),
        as_of_date="2026-09-28",
    )
    result = evaluate_reference_panel(
        target_snapshot_id="target-r6",
        target_snapshot_sha256="1" * 64,
        request_interpretation_sha256="2" * 64,
        reference_panel_id=panel["panel"]["panel_id"],
        reference_panel_sha256=panel["panel_sha256"],
        comparison_evidence="DOCUMENT_ONLY",
        observation_record_ids=(),
        seed=17,
        as_of_date="2026-09-28",
    )
    assert result["official_architecture_comparison"]["state"] == (
        "DOCUMENTARY_ARCHITECTURE_CLUES_ONLY"
    )
    assert result["official_architecture_comparison"]["target_sensory_distance_established"] is False
    assert result["selection"]["status"] == "DOCUMENTARY_ARCHITECTURE_CLUES_ONLY"
    assert result["selection"]["ranked_candidates"] == []
    assert result["personal_liking"]["state"] == "NOT_ESTABLISHED"


def test_non_document_mode_requires_adjudicated_observations() -> None:
    panel = build_commercial_reference_panel(("lavender",), as_of_date="2026-09-28")
    result = evaluate_reference_panel(
        target_snapshot_id="target-r6",
        target_snapshot_sha256="1" * 64,
        request_interpretation_sha256="2" * 64,
        reference_panel_id=panel["panel"]["panel_id"],
        reference_panel_sha256=panel["panel_sha256"],
        comparison_evidence="QUICK_BLIND",
        observation_record_ids=("obs-1",),
        seed=17,
        as_of_date="2026-09-28",
    )
    assert result["validation_state"] == "WITHHOLD_UNKNOWN"
    assert result["findings"] == ["OBSERVATION_RECORDS_BOUND_NOT_ADJUDICATED"]
    assert result["personal_liking"]["state"] == "NOT_ESTABLISHED"


def test_personal_sample_requires_no_photo_and_preserves_exact_edition() -> None:
    registry = load_commercial_reference_registry()
    sample = CommercialReferenceSampleV1(
        sample_identifier="quick-reference-1",
        product_id="prada-luna-rossa-carbon-edt",
        concentration="Eau de Toilette",
        edition="Eau de Toilette",
        commercial_registry_sha256=registry.registry_sha256,
    ).as_dict()
    assert sample["photograph_required"] is False
    assert sample["personal_comparison_allowed"] is True
    assert sample["evidence_admission_authorized"] is False


def test_normal_interpretation_and_local_panel_lookup_are_offline_and_fast(
    monkeypatch,
) -> None:
    def network_forbidden(*_args, **_kwargs):
        raise AssertionError("normal formula analysis must not use the network")

    monkeypatch.setattr(socket, "create_connection", network_forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", network_forbidden)
    registry = load_commercial_reference_registry()
    durations: list[float] = []
    for _index in range(25):
        started = time.perf_counter()
        interpretation = interpret_request(
            RequestInterpretationInputV1(
                original_request=(
                    "Make the lavender clearer at 30 minutes in my current bottle, "
                    "preserve dry amber, avoid sweetness, and use global crowd-pleasing mode."
                ),
                known_materials=("Lavender EO", "Ambrox Super crystals"),
                active_bottle_id="bottle-r6",
            )
        )
        panel = build_commercial_reference_panel(
            ("lavender", "amber", "ambrox"),
            as_of_date="2026-09-28",
            registry=registry,
        )
        durations.append(time.perf_counter() - started)
        assert interpretation["status"] == "REQUEST_INTERPRETATION_READY"
        assert panel["status"] == "MARKET_SELECTED_REFERENCE_PANEL"
    p95 = sorted(durations)[23]
    assert p95 < 0.5
