from __future__ import annotations

import hashlib
import io
import json
import zipfile
from copy import deepcopy
from pathlib import Path

from engine.calibration.hashing import stable_json_hash

ROOT = Path(__file__).resolve().parents[1]
CAPTURE_DIR = ROOT / "incoming_review" / "chatgpt" / "20260819T143426Z-hedonic-comparison-6a7c5b07"
ZIP_PATH = (
    CAPTURE_DIR
    / "Thailand_Mass_Market_Floral_1965_Target_Inventory_Formulas_Aug2026_v1_Package.zip"
)
RECIPE_PATH = (
    CAPTURE_DIR / "TH65-F01_Crystal_Peony_Rose_18pct_Current_Inventory_Mixing_Order_Recipe.md"
)
MANIFEST_PATH = CAPTURE_DIR / "source_manifest.json"
RECEIPT_PATH = (
    ROOT / "data" / "governance" / "th65_hedonic_comparison_portfolio_claim_receipt_20260819.json"
)


def _load_and_verify_semantic_receipt(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    unhashed = deepcopy(payload)
    declared_hash = unhashed.pop("receipt_sha256")
    assert stable_json_hash(unhashed) == declared_hash
    return payload


def _package_json() -> dict[str, object]:
    with zipfile.ZipFile(io.BytesIO(ZIP_PATH.read_bytes())) as archive:
        return json.loads(
            archive.read(
                "Thailand_Mass_Market_Floral_1965_Target_Inventory_Formulas_Aug2026_v1.json"
            )
        )


def test_exact_chat_zip_and_recipe_are_bound_without_hedonic_promotion() -> None:
    """Preserve the exact portfolio while withholding physical and preference authority."""

    manifest = _load_and_verify_semantic_receipt(MANIFEST_PATH)
    receipt = _load_and_verify_semantic_receipt(RECEIPT_PATH)

    assert manifest["conversation"] == {
        "conversation_id": "6a7c5b07-7000-83ec-8489-53f859a90abe",
        "project_id": "6a74ab83668081919f5cbd0dfe80eb09",
        "title": "Hedonic Comparison",
        "url": "https://chatgpt.com/c/6a7c5b07-7000-83ec-8489-53f859a90abe",
    }
    messages = {row["message_id"]: row for row in manifest["source_messages"]}
    assert messages["58ac1866-d47e-404b-bfba-af4e7f985faf"]["sha256"] == (
        "67bf707ec6ad0d55cbb75f4f1a02d76fe02601e803966d6b381fc2b46a0b925e"
    )
    assert messages["1ca832cb-5ffe-49e7-905d-fdeb820928d2"]["sha256"] == (
        "8f4b701702fd33a0d837705877fbe7cd3b80a4a8a8e4467e9a34b562947c1b47"
    )
    assert messages["2b90c5c3-d528-49bb-9483-13df72d1e6a1"]["sha256"] == (
        "0556c3880fdcc5bb4b1a5b165f77a01f7b181bfd5b18c72e48a5896a0c33aec6"
    )
    assert messages["d947cf1d-dca9-49bb-b0bb-8d264780e21e"]["sha256"] == (
        "1a79ecfbed2d6456bc119008b0074919c1dba7e7e77d64ee00cfbb60f96b7d55"
    )

    assert ZIP_PATH.stat().st_size == 156_622
    assert hashlib.sha256(ZIP_PATH.read_bytes()).hexdigest() == (
        "4ec759409e005394ed303f6d6c103c8c98e66da6782a4e060ef924b5e46a9182"
    )
    assert RECIPE_PATH.stat().st_size == 11_640
    assert hashlib.sha256(RECIPE_PATH.read_bytes()).hexdigest() == (
        "dc8ff680b0ffed6dfaf67f52f39a8aac65eec9e2da73152af0e0137806a6f052"
    )

    manifest_bytes = MANIFEST_PATH.read_bytes()
    assert receipt["parents"][0]["sha256"] == hashlib.sha256(manifest_bytes).hexdigest()
    assert receipt["parents"][0]["byte_size"] == len(manifest_bytes)
    assert receipt["source_claim"]["ranked_winner"] == "TH65-F01 Crystal Peony Rose"
    assert receipt["source_claim"]["winner_claim_state"] == "SOURCE_CLAIM_ONLY_NOT_TESTED"
    assert receipt["source_claim"]["suggested_first_screen_concentration_pct"] == 18
    assert receipt["source_claim"]["physical_batches"] == 0
    assert receipt["source_claim"]["liking_results"] == 0
    assert receipt["source_claim"]["commercial_superiority_established"] is False
    assert not any(receipt["authority"].values())


def test_complete_three_formula_complexity_is_preserved_as_quarantined_design() -> None:
    """Keep all branches and gates instead of flattening the package to its ranked recipe."""

    source = _package_json()
    assert source["package_id"] == "THAILAND-MASS-MARKET-FLORAL-1965-TARGET-V1"
    assert list(source["formulas"]) == ["CPR", "WTM", "LWM"]

    expected = {
        "CPR": {
            "formula_id": "TH65-F01",
            "name": "Crystal Peony Rose",
            "ideal_rows": 74,
            "current_rows": 71,
            "ideal_hash": "63b0d6d6698771731c4dad4e302af0fc4f8031562bc9cf4e04c62ce06d5db621",
            "current_hash": "70d319d552d236e769acda6c43621ae70228bae10bfc03806f8c07f91ec90227",
        },
        "WTM": {
            "formula_id": "TH65-F02",
            "name": "White Tea Magnolia",
            "ideal_rows": 74,
            "current_rows": 70,
            "ideal_hash": "a64af6e4d853537b5bde5429682878fccbd11616876b09cb856b04c8ccc4fec5",
            "current_hash": "86b79ec4e5c2501eb312624c7f975f806229391c9445861b84fd14adbbc528a3",
        },
        "LWM": {
            "formula_id": "TH65-F03",
            "name": "Lilac Wisteria Memory",
            "ideal_rows": 77,
            "current_rows": 73,
            "ideal_hash": "076b5f7cd93cfb74be520b504103093fe7b77625dc6a6b98718461267d8e21e2",
            "current_hash": "d8299641b11eb0f145e5f50521f2beee56878e0111a1d24e71d5dd92d38ce9d0",
        },
    }
    for key, want in expected.items():
        formula = source["formulas"][key]
        assert formula["formula_id"] == want["formula_id"]
        assert formula["name"] == want["name"]
        assert len(formula["target_ideal"]["rows"]) == want["ideal_rows"]
        assert len(formula["current_inventory_build"]["rows"]) == want["current_rows"]
        assert formula["target_ideal"]["formula_hash"] == want["ideal_hash"]
        assert formula["current_inventory_build"]["formula_hash"] == want["current_hash"]
        assert formula["target_ideal"]["state"] == "DESIGN ONLY / MISSING MATERIALS PRESENT"
        assert formula["current_inventory_build"]["state"] == (
            "COMPUTATIONAL BENCH CANDIDATE / PHYSICAL HOLD"
        )
        assert formula["consumer_release_screen"] == "16%, 18% and 20%"

    assert len(source["gate_results"]) == 45
    assert len(source["missing_chemical_impact"]) == 7
    assert len(source["preparation_queue"]) == 8
    assert len(source["controlled_test_plan"]) == 8
    assert all(row[-1] == "NOT RUN" for row in source["controlled_test_plan"])
    assert source["truth_boundary"] == {
        "formulas_created": "computational target and inventory-build hypotheses",
        "physical_batches": 0,
        "liking_results": 0,
        "broad_appeal_results": 0,
        "strict_oav": "NOT TESTED",
        "measured_headspace": "NOT TESTED",
        "stability": "NOT TESTED",
        "safety": "NOT CLEARED",
        "release": "WITHHELD",
    }

    receipt = _load_and_verify_semantic_receipt(RECEIPT_PATH)
    summary = receipt["evidence_summary"]
    assert summary["classification"] == (
        "EXACT_THREE_FORMULA_COMPUTATIONAL_HEDONIC_PORTFOLIO_PHYSICAL_PREFERENCE_"
        "SAFETY_AND_RELEASE_HOLD"
    )
    assert summary["project_formula_collision_count"] == 0
    assert summary["distinct_prior_floral_portfolio_overlap"] == "INVENTORY_PARENT_ONLY"
    assert summary["native_formula_installation_performed"] is False
    assert summary["native_runtime_change_required"] is False
    assert summary["promotion_allowed"] is False


def test_recipe_remains_nonexecuting_until_stock_safety_and_panel_gates_close() -> None:
    """Treat the exact 18% card as a candidate screen, not a compounding instruction."""

    recipe = RECIPE_PATH.read_text(encoding="utf-8")
    assert recipe.count("| OWNED |") == 64
    assert recipe.count("| PREPARE |") == 2
    assert recipe.count("| VERIFY FIRST |") == 3
    assert "OWNED: VERIFY LABEL" in recipe
    assert 'source row is titled "Cedramber 10%"' in recipe
    assert "**Physical state:** HOLD / NOT TESTED" in recipe
    assert "**Total formula concentrate** | **900.0 µL** | **5,400.0 µL**" in recipe
    assert "| **Final batch** | **5,000.0 µL** | **30,000.0 µL**" in recipe

    receipt = _load_and_verify_semantic_receipt(RECEIPT_PATH)
    assert receipt["recipe_diff"]["aromatic_additions"] == 71
    assert receipt["recipe_diff"]["ethanol_addition_number"] == 72
    assert receipt["recipe_diff"]["primary_pilot_ul"] == 5_000
    assert receipt["recipe_diff"]["scale_up_is_reference_only"] is True
    assert receipt["recipe_diff"]["cedramber_stock_basis_contradiction"] is True
    assert receipt["disposition"]["recipe_execution_allowed"] is False
    assert receipt["disposition"]["formula_or_inventory_mutated"] is False
    assert receipt["disposition"]["purchase_or_cart_mutated"] is False

    assert receipt["unlock_requirements"] == [
        "VERIFY_ALL_EIGHT_PREPARATION_OR_EXACT_STOCK_ROWS",
        "RESOLVE_CEDRAMBER_LABEL_VERSUS_EXACT_STOCK_BASIS",
        "COMPLETE_FORMULA_SPECIFIC_SAFETY_AND_SKIN_USE_REVIEW",
        "COMPOUND_CODED_16_18_20_PERCENT_MICROBATCHES_WITH_FIXED_APPLICATION_DOSE",
        "RUN_REFERENCE_FREE_TARGET_PANEL_AT_DECLARED_TIMEPOINTS",
        "REPLICATE_PREFERENCE_RANKING_ON_SECOND_DAY",
    ]
    sources = {row["source_id"]: row for row in receipt["literature_sources"]}
    assert sources["PMID:35381183"]["supports_formula_winner_without_panel"] is False
    assert sources["PMID:38863390"]["supports_target_market_winner_without_panel"] is False
    assert sources["PMID:36323760"]["supports_untested_18_percent_optimum"] is False
    assert sources["PMCID:PMC2533422"]["supports_71_component_paper_prediction"] is False
