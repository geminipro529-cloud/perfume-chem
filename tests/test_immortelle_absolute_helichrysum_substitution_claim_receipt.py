from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from engine.calibration.hashing import stable_json_hash

ROOT = Path(__file__).resolve().parents[1]
CAPTURE_DIR = (
    ROOT / "incoming_review" / "chatgpt" / "20260819T141521Z-immortelle-helichrysum-6a818995"
)
MANIFEST_PATH = CAPTURE_DIR / "source_manifest.json"
RECEIPT_PATH = (
    ROOT
    / "data"
    / "governance"
    / "immortelle_absolute_helichrysum_substitution_claim_receipt_20260819.json"
)


def _load_and_verify_semantic_receipt(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    unhashed = deepcopy(payload)
    declared_hash = unhashed.pop("receipt_sha256")
    assert stable_json_hash(unhashed) == declared_hash
    return payload


def test_chat_arithmetic_is_bound_but_material_substitution_abstains() -> None:
    """Preserve the chat while blocking an unstated v/v and identity-equivalence leap."""

    manifest = _load_and_verify_semantic_receipt(MANIFEST_PATH)
    receipt = _load_and_verify_semantic_receipt(RECEIPT_PATH)

    assert manifest["conversation"] == {
        "conversation_id": "6a818995-0090-83ec-9b8e-22ad37dd42f7",
        "project_id": "6a74ab83668081919f5cbd0dfe80eb09",
        "title": "Immortelle Abs to Helichrysum",
        "url": "https://chatgpt.com/c/6a818995-0090-83ec-9b8e-22ad37dd42f7",
    }
    messages = {row["message_id"]: row for row in manifest["source_messages"]}
    assert messages["3efb0693-cf75-4770-af82-a4a900d0d470"]["sha256"] == (
        "2ea5b33e6c788283e7da06444a43cef75e1572683898d3cd40452bf309bbc21a"
    )
    assert messages["a77c6c97-381b-4627-914f-cd7e648b840c"]["sha256"] == (
        "0a8fd8155c12317ea367097db24c7a1a611078376872047a8c249e7d482428d8"
    )

    manifest_bytes = MANIFEST_PATH.read_bytes()
    assert receipt["parents"][0]["sha256"] == hashlib.sha256(manifest_bytes).hexdigest()
    assert receipt["parents"][0]["byte_size"] == len(manifest_bytes)

    claim = receipt["source_claim"]
    assert claim["source_stock_volume_ul"] == "49"
    assert claim["source_nominal_strength_pct"] == "10"
    assert claim["computed_nominal_active_volume_ul"] == "4.9"
    assert claim["calculation_requires_fraction_basis"] == "VOLUME_PER_VOLUME"
    assert claim["fraction_basis_was_stated_in_chat"] is False
    assert claim["identity_equivalence_was_established"] is False

    local = receipt["local_identity_diff"]
    assert local["immortelle_absolute_stock"] == {
        "identity": "Immortelle Absolute",
        "listed_strength": "10%",
        "carrier": "DPG",
        "inventory_state": "OWNED_AS_WORKING_STOCK",
    }
    assert local["helichrysum_eo_stock"] == {
        "identity": "Helichrysum EO",
        "botanical_context": "Helichrysum italicum",
        "listed_strength": "NEAT_AS_SUPPLIED",
        "inventory_state": "OWNED_LOT_DETAIL_OPEN",
    }
    assert local["same_inventory_identity"] is False
    assert local["exact_user_lot_density_known"] is False
    assert local["exact_user_lot_composition_known"] is False

    disposition = receipt["disposition"]
    assert disposition["classification"] == (
        "IDENTITY_AND_FRACTION_BASIS_UNRESOLVED_SUBSTITUTION_NOT_CALCULABLE"
    )
    assert disposition["substitution_volume_state"] == "ABSTAINED_NOT_CALCULABLE"
    assert disposition["nominal_vv_arithmetic_is_equivalence_authority"] is False
    assert disposition["native_runtime_change_required"] is False
    assert not any(receipt["authority"].values())


def test_unlock_requires_stock_specific_physics_and_psychophysical_calibration() -> None:
    """Require a stock- and purpose-specific comparison instead of a generic natural swap."""

    receipt = _load_and_verify_semantic_receipt(RECEIPT_PATH)
    assert receipt["unlock_requirements"] == [
        "BIND_IMMORTELLE_STOCK_FRACTION_BASIS_AND_DENSITY",
        "BIND_HELICHRYSUM_STOCK_BOTANICAL_ORIGIN_LOT_AND_DENSITY",
        "BIND_BOTH_LOT_COMPOSITIONS_OR_ANALYTICAL_PROFILES",
        "DEFINE_THE_TARGET_ODOR_ATTRIBUTE_AND_MATRIX",
        "RUN_BLINDED_DOSE_RESPONSE_OR_MATCHING_CALIBRATION",
    ]

    sources = {row["source_id"]: row for row in receipt["literature_sources"]}
    assert sources["PMCID:PMC8399527"]["supports_identity_equivalence"] is False
    assert sources["PMCID:PMC11836004"]["supports_fixed_eo_composition"] is False
    assert (
        sources["DOI:10.1080/01496395.2016.1237967"]["supports_extract_to_eo_volume_substitution"]
        is False
    )
    assert sources["SUPPLIER:PW_5NY23688"]["catalog_density_is_user_lot_density"] is False

    assert receipt["native_guard_diff"] == {
        "mass_volume_conversion_without_applicable_density": "ALREADY_REJECTED",
        "intervention_trial_without_stock_density_and_source": "ALREADY_REJECTED",
        "mixed_dimension_legacy_projection_without_density": "ALREADY_ABSTAINS",
        "new_conversion_or_substitution_code_needed": False,
    }
