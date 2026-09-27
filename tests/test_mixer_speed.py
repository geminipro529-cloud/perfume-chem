"""Focused tests for the continuous-addition mixer protocol."""

import pytest

from engine.mixer.instructions import InstructionGenerator
from engine.mixer.sequencer import MixingRow, MixingSequencer

_FOUR_PHASE_FORMULA = {
    "Iso E Super": 40.0,
    "Hedione": 20.0,
    "Galaxolide": 10.0,
    "Linalool": 5.0,
    "Ethanol": 25.0,
}


def test_protocol_uses_one_final_homogenization_and_no_phase_rest() -> None:
    result = InstructionGenerator().generate(_FOUR_PHASE_FORMULA)
    text = result["full_text"]

    assert "Let rest 5 minutes" not in text
    assert text.count("no timed rest") == 3
    assert text.count("Final concentrate homogenization") == 1
    assert result["mixing_timing"] == {
        "occupied_non_solvent_phase_count": 4,
        "non_solvent_phase_count": 4,
        "legacy_stir_minutes": {"min": 8, "max": 12},
        "legacy_rest_minutes": 20,
        "legacy_timed_wait_minutes": {"min": 28, "max": 32},
        "optimized_final_homogenization_minutes": {"min": 2, "max": 3},
        "optimized_rest_minutes": 0,
        "homogeneity_checkpoint_count": 4,
    }


def test_continuous_path_preserves_order_and_solvent_last() -> None:
    result = MixingSequencer().sequence(_FOUR_PHASE_FORMULA)
    steps = result["steps"]

    assert [step["order"] for step in steps] == list(range(1, len(steps) + 1))
    assert [step["phase"] for step in steps] == [
        "base",
        "heart",
        "musk",
        "top",
        "solvent",
    ]
    assert steps[-1]["material"] == "Ethanol"


def test_precomputed_prebond_analysis_skips_duplicate_pair_scan(monkeypatch) -> None:
    analysis = {
        "must_prebond": [],
        "benefits": [],
        "keep_separate": [],
        "crystalline": [],
    }
    sequencer = MixingSequencer()

    def fail_if_called(_ingredients):
        raise AssertionError("prebond analysis was recomputed")

    monkeypatch.setattr(sequencer.prebonder, "analyze_formula", fail_if_called)
    result = sequencer.sequence(
        {"Iso E Super": 50.0, "Ethanol": 50.0},
        prebond_analysis=analysis,
    )

    assert result["prebond_steps"] == []
    assert [step["material"] for step in result["steps"]] == [
        "Iso E Super",
        "Ethanol",
    ]


def test_instruction_generator_forwards_precomputed_prebond_analysis(monkeypatch) -> None:
    analysis = {
        "must_prebond": [],
        "benefits": [],
        "keep_separate": [],
        "crystalline": [],
    }
    generator = InstructionGenerator()

    def fail_if_called(_ingredients):
        raise AssertionError("prebond analysis was recomputed")

    monkeypatch.setattr(generator.sequencer.prebonder, "analyze_formula", fail_if_called)
    result = generator.generate(
        {"Iso E Super": 50.0, "Ethanol": 50.0},
        prebond_analysis=analysis,
    )

    assert result["warnings"] == []
    assert "Final concentrate homogenization" in result["full_text"]


def test_dissolution_only_formula_gets_one_final_homogenization() -> None:
    result = InstructionGenerator().generate({"Vanillin": 5.0, "Ethanol": 95.0})
    text = result["full_text"]

    assert text.count("Final concentrate homogenization") == 1
    assert "Dissolve Vanillin" in text
    assert "Final concentrate homogenization" in result["phases"][0]["instructions"][-1]
    assert result["mixing_timing"] == {
        "occupied_non_solvent_phase_count": 0,
        "non_solvent_phase_count": 1,
        "legacy_stir_minutes": {"min": 0, "max": 0},
        "legacy_rest_minutes": 0,
        "legacy_timed_wait_minutes": {"min": 0, "max": 0},
        "optimized_final_homogenization_minutes": {"min": 2, "max": 3},
        "optimized_rest_minutes": 0,
        "homogeneity_checkpoint_count": 1,
    }


def test_prebond_only_formula_keeps_reaction_wait_and_gets_one_final_homogenization() -> None:
    result = InstructionGenerator().generate(
        {
            "Citral": 5.0,
            "Methyl Anthranilate": 5.0,
            "Ethanol": 90.0,
        }
    )
    text = result["full_text"]

    assert text.count("Final concentrate homogenization") == 1
    assert "Allow 30-60 minutes for reaction to proceed." in text
    assert "Final concentrate homogenization" in result["phases"][0]["instructions"][-1]
    assert result["mixing_timing"]["occupied_non_solvent_phase_count"] == 0
    assert result["mixing_timing"]["non_solvent_phase_count"] == 1
    assert result["mixing_timing"]["legacy_timed_wait_minutes"] == {
        "min": 0,
        "max": 0,
    }
    assert result["mixing_timing"]["optimized_final_homogenization_minutes"] == {
        "min": 2,
        "max": 3,
    }
    assert result["mixing_timing"]["homogeneity_checkpoint_count"] == 1


_NO_SPECIAL_CHEMISTRY = {
    "must_prebond": [],
    "benefits": [],
    "keep_separate": [],
    "crystalline": [],
}


def test_basket_card_orders_baskets_then_raw_ul_and_preserves_rows() -> None:
    rows = [
        {"row_id": "b2-small", "material": "Hedione", "raw_ul": 50, "basket": 2},
        {"row_id": "b1-small", "material": "Linalool", "raw_ul": 10, "basket": 1},
        {"row_id": "b2-large", "material": "Iso E Super", "raw_ul": 200, "basket": 2},
        {"row_id": "b1-large", "material": "Ambrox Super", "raw_ul": 100, "basket": 1},
    ]

    result = MixingSequencer().sequence(
        rows=rows,
        prebond_analysis=_NO_SPECIAL_CHEMISTRY,
    )

    assert result["compounding_authority"] == "WITHHELD"
    assert (
        "VERIFIED_PHYSICAL_AUTHORITY_RECEIPTS_REQUIRED"
        in result["authority_blockers"]
    )
    assert [step["row_id"] for step in result["steps"]] == [
        "b1-large",
        "b1-small",
        "b2-large",
        "b2-small",
    ]
    assert result["raw_total_ul"] == 360.0
    assert result["ordered_raw_total_ul"] == 360.0
    assert len(result["basket_checkpoints"]) == 17


def test_basket_card_honors_explicit_precharge_and_postcharge() -> None:
    rows = [
        {
            "row_id": "post",
            "material": "Ethanol",
            "raw_ul": 500,
            "basket": None,
            "operation": "POSTCHARGE",
        },
        {
            "row_id": "direct",
            "material": "Hedione",
            "raw_ul": 100,
            "basket": 7,
        },
        {
            "row_id": "pre",
            "material": "DPG",
            "raw_ul": 50,
            "basket": None,
            "operation": "PRECHARGE",
        },
    ]

    result = MixingSequencer().sequence(
        rows=rows,
        prebond_analysis=_NO_SPECIAL_CHEMISTRY,
    )

    assert result["compounding_authority"] == "WITHHELD"
    assert (
        "VERIFIED_PHYSICAL_AUTHORITY_RECEIPTS_REQUIRED"
        in result["authority_blockers"]
    )
    assert [step["row_id"] for step in result["steps"]] == [
        "pre",
        "direct",
        "post",
    ]
    assert [step["operation"] for step in result["steps"]] == [
        "PRECHARGE",
        "DIRECT_ADD",
        "POSTCHARGE",
    ]


def test_missing_basket_and_unprepared_sub_10_ul_row_withhold_card() -> None:
    result = MixingSequencer().sequence(
        rows=[
            {
                "row_id": "trace",
                "material": "Trace Material",
                "raw_ul": 5,
                "basket": None,
            }
        ],
        prebond_analysis=_NO_SPECIAL_CHEMISTRY,
    )

    assert result["compounding_authority"] == "WITHHELD"
    assert result["raw_total_ul"] == result["ordered_raw_total_ul"] == 5.0
    assert "UNASSIGNED_BASKET:trace" in result["authority_blockers"]
    assert (
        "BELOW_10_UL_WITHOUT_PREPARED_DILUTION:trace"
        in result["authority_blockers"]
    )


def test_prepared_dilution_identity_unlocks_sub_10_ul_transfer() -> None:
    result = InstructionGenerator().generate(
        rows=[
            {
                "row_id": "trace",
                "material": "Trace Material",
                "raw_ul": 5,
                "basket": 16,
                "prepared_dilution_id": "TRACE-1PCT-20260922",
            }
        ],
        prebond_analysis=_NO_SPECIAL_CHEMISTRY,
    )

    assert result["compounding_authority"] == "WITHHELD"
    assert (
        "VERIFIED_PHYSICAL_AUTHORITY_RECEIPTS_REQUIRED"
        in result["authority_blockers"]
    )
    assert result["full_text"].count("Final concentrate homogenization") == 1
    assert "5 µL raw stock" in result["full_text"]
    assert "row trace" in result["full_text"]
    assert "prepared dilution TRACE-1PCT-20260922" in result["full_text"]
    assert result["total_pct"] is None


def test_source_authority_blocker_cannot_be_lost_by_valid_rows() -> None:
    result = MixingSequencer().sequence(
        rows=[
            {
                "row_id": "one",
                "material": "Hedione",
                "raw_ul": 100,
                "basket": 7,
            }
        ],
        prebond_analysis=_NO_SPECIAL_CHEMISTRY,
        source_authority_blockers=["FORMULA_TO_PHYSICAL_ROW_MISMATCH:Hedione"],
    )

    assert result["compounding_authority"] == "WITHHELD"
    assert result["authority_blockers"] == [
        "FORMULA_TO_PHYSICAL_ROW_MISMATCH:Hedione",
        "VERIFIED_PHYSICAL_AUTHORITY_RECEIPTS_REQUIRED",
    ]


def test_postcharge_only_protocol_does_not_claim_concentrate_homogenization() -> None:
    result = InstructionGenerator().generate(
        rows=[
            {
                "row_id": "post",
                "material": "Ethanol",
                "raw_ul": 500,
                "basket": None,
                "operation": "POSTCHARGE",
            }
        ],
        prebond_analysis=_NO_SPECIAL_CHEMISTRY,
    )

    assert result["mixing_timing"]["optimized_final_homogenization_minutes"] == {
        "min": 0,
        "max": 0,
    }
    assert "Final concentrate homogenization" not in result["full_text"]


@pytest.mark.parametrize("raw_ul", [float("nan"), float("inf"), float("-inf")])
def test_mixing_row_rejects_nonfinite_raw_ul(raw_ul: float) -> None:
    with pytest.raises(ValueError, match="finite positive raw_ul"):
        MixingRow(
            row_id="invalid",
            material="Hedione",
            raw_ul=raw_ul,
            basket=7,
        )
