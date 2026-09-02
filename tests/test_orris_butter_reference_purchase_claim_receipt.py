from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from engine.calibration.hashing import stable_json_hash

ROOT = Path(__file__).resolve().parents[1]
CAPTURE_DIR = ROOT / "incoming_review" / "chatgpt" / "20260819T140438Z-orris-butter-6a8050ce"
MANIFEST_PATH = CAPTURE_DIR / "source_manifest.json"
RECEIPT_PATH = ROOT / "data" / "governance" / "orris_butter_reference_claim_receipt_20260819.json"


def _load_and_verify_semantic_receipt(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    unhashed = deepcopy(payload)
    declared_hash = unhashed.pop("receipt_sha256")
    assert stable_json_hash(unhashed) == declared_hash
    return payload


def test_orris_butter_chat_is_source_bound_and_ipm_protocol_is_rejected() -> None:
    """Bind the chat claim while preventing an unsupported carrier or purchase from propagating."""

    manifest = _load_and_verify_semantic_receipt(MANIFEST_PATH)
    receipt = _load_and_verify_semantic_receipt(RECEIPT_PATH)

    assert manifest["conversation"] == {
        "conversation_id": "6a8050ce-526c-83ec-889f-36fe923bc7b8",
        "project_id": "6a74ab83668081919f5cbd0dfe80eb09",
        "title": "Perfume Chemicals List",
        "url": (
            "https://chatgpt.com/g/g-p-6a74ab83668081919f5cbd0dfe80eb09-"
            "complex-perfumery/c/6a8050ce-526c-83ec-889f-36fe923bc7b8"
        ),
    }
    messages = {row["message_id"]: row for row in manifest["source_messages"]}
    assert messages["da142564-8e99-4a91-b1f5-b06c1e278ea7"]["sha256"] == (
        "253526be76c6f2d3c2201547d5b01ae4bdcf0c2893a7a105c751e004a0d2636f"
    )
    assert messages["7d158fc2-ef05-4485-9b4f-ed21e0a848be"]["sha256"] == (
        "592a06eecc69e85a3a78752a23b298987c16c4149226543a846502b4bf17da7b"
    )
    assert messages["0cb05cb0-da98-4f5d-b0d7-7790095b4d60"]["sha256"] == (
        "a6065fd58c420e663bd5ab4d10b846fc0d6b1f7ee6298a68a2968bd5de2bd07a"
    )

    manifest_bytes = MANIFEST_PATH.read_bytes()
    assert receipt["parents"][0]["sha256"] == hashlib.sha256(manifest_bytes).hexdigest()
    assert receipt["parents"][0]["byte_size"] == len(manifest_bytes)

    identity = receipt["supplier_identity"]
    assert identity["verified_variants"] == [
        {
            "sku": "5IA07847",
            "nominal_strength": "10%",
            "carrier": "DPG",
            "availability": "IN_STOCK",
            "price_usd_per_g": "2.20",
        },
        {
            "sku": "5IA18424",
            "nominal_strength": "10%",
            "carrier": "TEC",
            "availability": "OUT_OF_STOCK",
            "price_usd_per_g": "2.05",
        },
    ]
    assert identity["ipm_variant_state"] == "NOT_VERIFIED_IN_BOUNDED_OFFICIAL_CHECK"
    assert identity["nonretrieval_is_absence"] is False
    assert identity["exact_lot_irone_fraction_known"] is False

    correction = receipt["claim_correction"]
    assert correction["trial_carrier_rule"] == (
        "MATCH_THE_EXACT_PURCHASED_STOCK_CARRIER; NEVER_DEFAULT_TO_IPM"
    )
    assert correction["givaudan_8_percent_is_pw_composition_proxy"] is False
    assert correction["irone_isomer_percentages_are_whole_butter_mass_percentages"] is False
    assert correction["ukrainian_rhizome_oil_is_universal_stock_composition"] is False

    assert receipt["disposition"]["classification"] == (
        "SPECIALIST_REFERENCE_CANDIDATE_IDENTITY_AND_CARRIER_UNRESOLVED_PURCHASE_AND_EXECUTION_HOLD"
    )
    assert receipt["disposition"]["one_gram_reference_is_conditionally_reasonable"] is True
    assert receipt["disposition"]["automatic_purchase_allowed"] is False
    assert receipt["disposition"]["trial_execution_allowed"] is False
    assert receipt["disposition"]["native_runtime_change_required"] is False
    assert not any(receipt["authority"].values())


def test_orris_literature_roles_are_not_promoted_to_supplier_lot_composition() -> None:
    """Keep source-specific oil composition and irone-fraction ratios in their proper scopes."""

    receipt = _load_and_verify_semantic_receipt(RECEIPT_PATH)
    sources = {row["source_id"]: row for row in receipt["literature_and_supplier_sources"]}

    ukraine = sources["PMCID:PMC7227901"]
    assert ukraine["role"] == "SOURCE_SPECIFIC_STEAM_DISTILLED_RHIZOME_OIL_COMPOSITION"
    assert ukraine["reported_sample_percentages"] == {
        "myristic_acid": "56.00",
        "lauric_acid": "15.42",
        "capric_acid": "14.50",
        "alpha_irone": "2.85",
    }
    assert ukraine["may_define_pw_5IA07847_composition"] is False

    isomers = sources["DOI:10.1016/S1631-0748(03)00087-0"]
    assert isomers["role"] == "BOTANICAL_SPECIES_DEPENDENT_IRONE_ISOMER_DISTRIBUTION"
    assert isomers["percent_basis"] == "NORMALIZED_IRONE_ISOMER_DISTRIBUTION_NOT_WHOLE_BUTTER"
    assert (
        round(
            sum(float(value) for value in isomers["iris_pallida_irone_distribution_pct"].values()),
            2,
        )
        == 100.04
    )

    standard = sources["ISO:18054:2004"]
    assert standard["role"] == "IRONE_CONTENT_MEASUREMENT_METHOD_CONTEXT"
    assert standard["supplies_pw_lot_result"] is False

    assert sources["SUPPLIER:GIVAUDAN_ORRIS_PALLIDA_8"]["separate_product_from_pw"] is True
    assert sources["SUPPLIER:PW_5IA07847"]["carrier"] == "DPG"
    assert sources["SUPPLIER:PW_5IA18424"]["carrier"] == "TEC"
