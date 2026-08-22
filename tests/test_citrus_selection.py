from __future__ import annotations

from pathlib import Path

import pytest

from engine.perception.citrus_selection import (
    CitrusCandidate,
    CitrusInventoryState,
    CitrusSelectionRequest,
    CitrusSelectionState,
    select_citrus_architecture,
)

TARGET_AXES = ("dry", "peel", "bitter", "cold", "naturalistic")


def candidate(
    material: str,
    *,
    roles: tuple[str, ...],
    axis_matches: tuple[str, ...] = TARGET_AXES,
    axis_conflicts: tuple[str, ...] = (),
    inventory_state: CitrusInventoryState = CitrusInventoryState.OWNED,
    exact_stock_ref: str | None = None,
) -> CitrusCandidate:
    if exact_stock_ref is None and inventory_state is CitrusInventoryState.OWNED:
        exact_stock_ref = f"inventory:{material}:neat"
    return CitrusCandidate(
        material=material,
        roles=roles,
        axis_matches=axis_matches,
        axis_conflicts=axis_conflicts,
        inventory_state=inventory_state,
        exact_stock_ref=exact_stock_ref,
        transition_to_heart="hands brightness into the aromatic heart without a gap",
        evidence_refs=(f"inventory:{material}",),
    )


def citrus_request(
    *,
    primary_role: str = "DRY_BITTER_PRISM",
    support_role: str | None = None,
    candidates: tuple[CitrusCandidate, ...] | None = None,
    citrus_required: bool = True,
    non_citrus_brightness_satisfies_target: bool = False,
) -> CitrusSelectionRequest:
    if candidates is None:
        candidates = (
            candidate("Bergamot FCF Oil Sicilian", roles=("DRY_BITTER_PRISM",)),
        )
    return CitrusSelectionRequest(
        target_identity="dry bitter tea prism over an aromatic iris heart",
        target_axes=TARGET_AXES,
        primary_role=primary_role,
        support_role=support_role,
        candidates=candidates,
        citrus_required=citrus_required,
        non_citrus_brightness_satisfies_target=non_citrus_brightness_satisfies_target,
        inventory_authority_sha256="a" * 64,
    )


def test_selects_one_primary_and_one_distinct_bridge_without_count_reward() -> None:
    result = select_citrus_architecture(
        citrus_request(
            support_role="GREEN_AROMATIC_BRIDGE",
            candidates=(
                candidate(
                    "Bergamot FCF Oil Sicilian", roles=("DRY_BITTER_PRISM",)
                ),
                candidate(
                    "Petitgrain EO Paraguay", roles=("GREEN_AROMATIC_BRIDGE",)
                ),
                candidate("Blood Orange Oil Sicilian", roles=("JUICY_WARM_BODY",)),
            ),
        )
    )

    assert result.state is CitrusSelectionState.PASS
    assert result.target_primary == "Bergamot FCF Oil Sicilian"
    assert result.target_support == "Petitgrain EO Paraguay"
    assert result.current_build_primary == "Bergamot FCF Oil Sicilian"
    assert result.current_build_support == "Petitgrain EO Paraguay"
    assert "score" not in result.as_dict()


def test_returns_none_when_non_citrus_brightness_already_serves_target() -> None:
    result = select_citrus_architecture(
        citrus_request(
            citrus_required=False,
            non_citrus_brightness_satisfies_target=True,
        )
    )

    assert result.state is CitrusSelectionState.NONE
    assert result.target_primary is None
    assert result.target_support is None
    assert result.current_build_state == "NONE_REQUIRED"


def test_out_of_stock_red_mandarin_is_not_silently_replaced() -> None:
    result = select_citrus_architecture(
        citrus_request(
            primary_role="JUICY_WARM_CONTINUITY",
            candidates=(
                candidate(
                    "Red Mandarin EO",
                    roles=("JUICY_WARM_CONTINUITY",),
                    axis_matches=("juicy", "pulp", "sweet", "warm", "naturalistic"),
                    inventory_state=CitrusInventoryState.OUT_OF_STOCK,
                ),
                candidate(
                    "Blood Orange Oil Sicilian",
                    roles=("JUICY_WARM_BODY",),
                    axis_matches=("juicy", "pulp", "sweet", "warm", "naturalistic"),
                ),
            ),
        ).with_target_axes(("juicy", "pulp", "sweet", "warm", "naturalistic"))
    )

    assert result.target_primary == "Red Mandarin EO"
    assert result.current_build_primary is None
    assert result.current_build_state == "HOLD_TARGET_SPECIFIC_GAP"
    assert "TARGET_PRIMARY_OUT_OF_STOCK" in result.issue_codes
    assert result.as_dict()["current_inventory_build"]["primary"] is None


def test_out_of_stock_cedrat_remains_target_ideal_without_substitution() -> None:
    result = select_citrus_architecture(
        citrus_request(
            primary_role="DRY_CITRON_PITH",
            candidates=(
                candidate(
                    "Cedrat FCF Oil Sicilian",
                    roles=("DRY_CITRON_PITH",),
                    inventory_state=CitrusInventoryState.OUT_OF_STOCK,
                ),
                candidate("Lemon FCF Oil Sicilian", roles=("LEMON_PEEL_FLASH",)),
            ),
        )
    )

    assert result.target_primary == "Cedrat FCF Oil Sicilian"
    assert result.current_build_primary is None
    assert result.current_build_state == "HOLD_TARGET_SPECIFIC_GAP"


def test_ambiguous_strongest_single_candidates_hold_instead_of_scoring() -> None:
    result = select_citrus_architecture(
        citrus_request(
            candidates=(
                candidate("Bergamot FCF Oil Sicilian", roles=("DRY_BITTER_PRISM",)),
                candidate("Grapefruit FCF Oil Sicilian", roles=("DRY_BITTER_PRISM",)),
            )
        )
    )

    assert result.state is CitrusSelectionState.HOLD
    assert result.target_primary is None
    assert "STRONGEST_SINGLE_UNRESOLVED" in result.issue_codes


def test_axis_conflict_blocks_an_otherwise_role_matching_candidate() -> None:
    result = select_citrus_architecture(
        citrus_request(
            candidates=(
                candidate(
                    "Orange Peel EO",
                    roles=("DRY_BITTER_PRISM",),
                    axis_conflicts=("warm", "sweet"),
                ),
            )
        )
    )

    assert result.state is CitrusSelectionState.HOLD
    assert "NO_TARGET_FIT_PRIMARY" in result.issue_codes


def test_overlapping_support_role_is_rejected_in_favor_of_primary_only() -> None:
    result = select_citrus_architecture(
        citrus_request(
            support_role="GREEN_AROMATIC_BRIDGE",
            candidates=(
                candidate(
                    "Bergamot FCF Oil Sicilian",
                    roles=("DRY_BITTER_PRISM", "GREEN_AROMATIC_BRIDGE"),
                ),
                candidate(
                    "Petitgrain EO Paraguay",
                    roles=("GREEN_AROMATIC_BRIDGE",),
                ),
            ),
        )
    )

    assert result.state is CitrusSelectionState.PASS
    assert result.target_primary == "Bergamot FCF Oil Sicilian"
    assert result.target_support is None
    assert "SUPPORT_NOT_DISTINCT" in result.issue_codes


def test_owned_material_without_exact_stock_ref_holds_current_build() -> None:
    result = select_citrus_architecture(
        citrus_request(
            candidates=(
                candidate(
                    "Bergamot FCF Oil Sicilian",
                    roles=("DRY_BITTER_PRISM",),
                    inventory_state=CitrusInventoryState.VERIFY_FIRST,
                    exact_stock_ref=None,
                ),
            )
        )
    )

    assert result.target_primary == "Bergamot FCF Oil Sicilian"
    assert result.current_build_primary is None
    assert result.current_build_state == "HOLD_VERIFY_EXACT_STOCK"


def test_selector_is_pure_and_does_not_require_legacy_citrus_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        Path,
        "read_text",
        lambda self, *args, **kwargs: (_ for _ in ()).throw(
            AssertionError(f"unexpected file read: {self}")
        ),
    )

    result = select_citrus_architecture(citrus_request())

    assert result.state is CitrusSelectionState.PASS
    assert result.result_sha256


def test_request_rejects_duplicate_materials_and_incomplete_axis_identity() -> None:
    bergamot = candidate("Bergamot FCF Oil Sicilian", roles=("DRY_BITTER_PRISM",))
    with pytest.raises(ValueError, match="unique"):
        citrus_request(candidates=(bergamot, bergamot))
    with pytest.raises(ValueError, match="five target axes"):
        citrus_request().with_target_axes(("dry", "peel"))
