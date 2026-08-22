from __future__ import annotations

import json

import pytest

from engine.perception.musk_design import (
    ClaimStatus,
    InventoryState,
    MuskCandidate,
    MuskDesignRequest,
    MuskExceptionCall,
    MuskFingerprint,
    MuskRole,
    MuskTargetBrief,
    PairwiseNonredundancy,
    evaluate_musk_design,
)


def _exception(material: str) -> MuskExceptionCall:
    return MuskExceptionCall(
        material=material,
        target_tonal_role="specific vintage powder echo",
        why_alternatives_fail=(
            "clean musks remove the requested period powder tension"
        ),
        loss_if_omitted="the dry powder-to-skin transition disappears",
        failure_mode="talc overload and dated blur",
        omission_control="same architecture with the material omitted",
        alternative_control="same architecture with Exaltolide in the same role",
    )


def _fingerprint(material: str, effect: str) -> MuskFingerprint:
    return MuskFingerprint(
        material=material,
        exact_target_effect=effect,
        temporal_window="drydown transition",
        texture_axis="skin-to-fabric texture",
        projection_axis="intimate aura",
        character_axis="clean versus warm tension",
        interaction_risks=("blur if overdosed",),
        evidence_refs=("design-hypothesis:test",),
        claim_status=ClaimStatus.PHYSICAL_TEST_REQUIRED,
    )


def _brief() -> MuskTargetBrief:
    return MuskTargetBrief(
        required_character="quiet skin aura with a dry floral echo",
        unwanted_character="laundry bloom and generic sweet blur",
        temporal_behavior="opens airy and settles into a close skin shadow",
        projection_intimacy="intimate with a narrow aura",
        texture="dry, fine, and non-fluffy",
        system_connections=("iris heart", "dry woods base"),
    )


def test_one_precise_musk_is_valid_without_forcing_a_chord() -> None:
    result = evaluate_musk_design(
        MuskDesignRequest(
            target_identity="quiet skin aura with negative space",
            candidates=(
                MuskCandidate(
                    material="Zenolide",
                    role=MuskRole.DEPTH,
                    target_function="one clean skin-depth plane without laundry bloom",
                    why_nonredundant="the architecture has no other musk plane",
                    inventory_state=InventoryState.OWNED,
                    exact_stock_ref="inventory:Zenolide:neat",
                ),
            ),
        )
    )
    assert result.state == "PASS"
    assert result.architecture_mode == "SPARSE"
    assert [item.material for item in result.selected] == ["Zenolide"]
    assert "score" not in json.dumps(result.as_dict()).casefold()


def test_layered_musks_with_the_same_role_fail_as_redundant() -> None:
    result = evaluate_musk_design(
        MuskDesignRequest(
            target_identity="transparent skin depth",
            candidates=(
                MuskCandidate(
                    "Zenolide",
                    MuskRole.DEPTH,
                    "skin depth",
                    "first depth plane",
                    InventoryState.OWNED,
                    "inventory:Zenolide:neat",
                ),
                MuskCandidate(
                    "Exaltolide",
                    MuskRole.DEPTH,
                    "more skin depth",
                    "second depth plane",
                    InventoryState.OWNED,
                    "inventory:Exaltolide:10pct",
                ),
            ),
        )
    )
    assert result.state == "HOLD"
    assert "REDUNDANT_MUSK_ROLE" in result.issue_codes


def test_distinct_role_labels_still_require_complete_pairwise_reasoning() -> None:
    candidates = (
        MuskCandidate(
            "Zenolide",
            MuskRole.DEPTH,
            "quiet skin depth",
            "owns the close skin plane",
            InventoryState.OWNED,
            "inventory:Zenolide:neat",
            fingerprint=_fingerprint("Zenolide", "close dry skin depth"),
        ),
        MuskCandidate(
            "Habanolide",
            MuskRole.PROJECTION,
            "a narrow metallic aura above the skin plane",
            "owns the controlled outward aura",
            InventoryState.OWNED,
            "inventory:Habanolide:10pct",
            fingerprint=_fingerprint("Habanolide", "narrow metallic aura"),
        ),
    )
    missing = evaluate_musk_design(
        MuskDesignRequest(
            target_identity="dry iris skin aura",
            target_brief=_brief(),
            candidates=candidates,
        )
    )
    assert missing.state == "HOLD"
    assert "PAIRWISE_NONREDUNDANCY_MISSING" in missing.issue_codes

    complete = evaluate_musk_design(
        MuskDesignRequest(
            target_identity="dry iris skin aura",
            target_brief=_brief(),
            candidates=candidates,
            pairwise_nonredundancy=(
                PairwiseNonredundancy(
                    material_a="Zenolide",
                    material_b="Habanolide",
                    distinct_function_a="close dry skin depth under the iris",
                    distinct_function_b="narrow metallic aura above the iris",
                    loss_if_a_omitted="the base becomes hollow and loses intimacy",
                    loss_if_b_omitted="the iris loses its controlled aura",
                    collision_risk="metallic cleanliness could flatten the dry skin contrast",
                    controlled_comparison=(
                        "full layer versus strongest single musk and each one-at-a-time omission"
                    ),
                ),
            ),
        )
    )
    assert complete.state == "PASS"
    assert complete.architecture_mode == "LAYERED"


@pytest.mark.parametrize("material", ["Tonalide", "Macrolide", "Musk Ketone"])
def test_exception_only_musks_are_omitted_without_a_design_call(material: str) -> None:
    result = evaluate_musk_design(
        MuskDesignRequest(
            target_identity="clean restrained musk",
            candidates=(
                MuskCandidate(
                    material,
                    MuskRole.CHARACTER_ECHO,
                    "generic musk support",
                    "no unique function supplied",
                    InventoryState.DEPLETED,
                    None,
                ),
            ),
        )
    )
    assert result.state == "HOLD"
    assert result.selected == ()
    assert result.decisions[0].disposition == "OMITTED_EXCEPTION_REQUIRED"
    assert "MUSK_EXCEPTION_REQUIRED" in result.issue_codes


def test_complete_depleted_exception_can_enter_target_but_not_build() -> None:
    result = evaluate_musk_design(
        MuskDesignRequest(
            target_identity="vintage iris powder with dry skin tension",
            candidates=(
                MuskCandidate(
                    "Musk Ketone",
                    MuskRole.CHARACTER_ECHO,
                    "echo the target's period talc register",
                    "modern clean musks change the period identity",
                    InventoryState.DEPLETED,
                    None,
                    _exception("Musk Ketone"),
                ),
            ),
        )
    )
    assert result.state == "PASS"
    assert result.target_ideal_state == "DESIGN_AVAILABLE"
    assert result.current_inventory_build_state == "HOLD_PROCUREMENT_REQUIRED"
    assert result.selected[0].material == "Musk Ketone"
    assert result.formula_authority is False
    assert result.physical_execution_authorized is False


def test_incomplete_exception_call_is_rejected() -> None:
    with pytest.raises(ValueError, match="alternative control"):
        MuskExceptionCall(
            material="Tonalide",
            target_tonal_role="warm cosmetic fabric tone",
            why_alternatives_fail="alternatives are too clean",
            loss_if_omitted="warm fabric shadow is lost",
            failure_mode="laundry sweetness and blur",
            omission_control="same formula without Tonalide",
            alternative_control="",
        )
