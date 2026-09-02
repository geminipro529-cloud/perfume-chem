from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from engine.calibration.hashing import stable_json_hash

ROOT = Path(__file__).resolve().parents[1]
CAPTURE_DIR = ROOT / "incoming_review" / "chatgpt" / "20260819T150500Z-working-stock-dep-6a830dfe"
MANIFEST_PATH = CAPTURE_DIR / "source_manifest.json"
RECEIPT_PATH = ROOT / "data" / "governance" / "working_stock_dep_claim_receipt_20260819.json"


def _load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    unhashed = deepcopy(payload)
    declared_hash = unhashed.pop("receipt_sha256")
    assert stable_json_hash(unhashed) == declared_hash
    return payload


def test_exact_chat_is_bound_and_all_working_stock_rows_survive() -> None:
    manifest = _load(MANIFEST_PATH)
    receipt = _load(RECEIPT_PATH)

    assert manifest["conversation"]["conversation_id"] == ("6a830dfe-c4c8-83ec-bb1e-f859fa6375f9")
    messages = {row["message_id"]: row for row in manifest["source_messages"]}
    assert len(messages) == 7
    assert messages["f00e082e-2616-449a-90cb-069f327905b3"]["sha256"] == (
        "9d7d4aa47ead3702655bcf731affd6a4794db9e23b156c68cc3e187e0951d99a"
    )
    assert messages["22efe29c-edcb-4535-a9d7-9de2dba02cc3"]["sha256"] == (
        "c23419d6094a71ce0c6df74773fd5d24059c76c136a27aae90fce324dba2c8af"
    )
    assert messages["423c84e9-bd0c-4c60-8caa-c448002345c1"]["sha256"] == (
        "406c01455359bc106acd4605c80d086ee9af43cadddaacbed071534599f53622"
    )
    manifest_bytes = MANIFEST_PATH.read_bytes()
    assert receipt["parents"][0]["byte_size"] == len(manifest_bytes)
    assert receipt["parents"][0]["sha256"] == hashlib.sha256(manifest_bytes).hexdigest()

    rows = receipt["source_working_stock_recommendations"]
    assert len(rows) == 23
    by_material = {row["material"]: row for row in rows}
    assert by_material["Helvetolide"]["recommended_working_stock"] == "NEAT"
    assert by_material["Ethyl Butyrate"]["recommended_working_stock"] == "1% w/w in DEP"
    assert by_material["Orris Liquid"]["recommended_working_stock"] == (
        "30% w/w supplied-product basis in DEP"
    )
    assert by_material["Immortelle Absolute"]["secondary_stock_carrier"] == "DPG_PLUS_DEP"


def test_helvetolide_possession_and_pure_identity_remain_unverified() -> None:
    receipt = _load(RECEIPT_PATH)
    claim = receipt["helvetolide_claim"]
    assert claim["chat_reported_mass_g"] == "1.00"
    assert claim["v5_current_stock_match_count"] == 0
    assert claim["inventory_state"] == "CHAT_REPORTED_POSSESSION_UNVERIFIED"
    assert claim["fifty_percent_product_basis_arithmetic"] == {
        "source_product_g": "1.00",
        "dep_g": "1.00",
        "final_mass_g": "2.00",
        "nominal_product_basis_fraction_w_w": "0.50",
    }
    assert claim["pure_molecular_helvetolide_fraction_known"] is False
    assert claim["preparation_authorized"] is False

    identity = receipt["identity_diff"]
    assert identity["local_catalog_record"]["sku"] == "3XD17215"
    assert identity["local_catalog_record"]["price_usd_per_g"] == "1.90"
    assert identity["perfumersworld_current_coa"]["classification"] == (
        "PROPRIETARY_PERFUME_COMPOUND_COMPLEX_MIXTURE"
    )
    assert identity["dsm_firmenich_reference_material"]["cas"] == "141773-73-1"
    assert identity["catalog_product_equals_reference_molecule"] is False
    assert identity["user_bottle_equals_either_source"] is False

    assert receipt["disposition"]["classification"] == (
        "WORKING_STOCK_DESIGN_ROWS_PRESERVED_HELVETOLIDE_IDENTITY_AND_POSSESSION_RED"
    )
    assert receipt["disposition"]["native_runtime_change_required"] is False
    assert not any(receipt["authority"].values())


def test_unlock_requires_exact_bottle_and_native_stock_preparation_receipt() -> None:
    receipt = _load(RECEIPT_PATH)
    assert receipt["unlock_requirements"] == [
        "BIND_HELVETOLIDE_BOTTLE_LABEL_SUPPLIER_SKU_LOT_AND_EXACT_PRODUCT_IDENTITY",
        "BIND_PHYSICAL_MASS_AND_CURRENT_POSSESSION_RECEIPT",
        "CLASSIFY_PURE_MOLECULE_VERSUS_SUPPLIED_PRODUCT_BASIS",
        "BIND_DEP_LOT_AND_BALANCE_CALIBRATION",
        "CREATE_NATIVE_STOCK_PREPARATION_RECEIPT_WITH_PARENT_CHILD_LINEAGE",
        "COMPLETE_FINAL_FORMULA_SPECIFIC_SAFETY_REVIEW_BEFORE_SKIN_USE",
    ]
    sources = {row["source_id"]: row for row in receipt["literature_and_supplier_sources"]}
    assert sources["PW:3XD17215"]["proves_pure_molecular_helvetolide"] is False
    assert sources["DSM-FIRMENICH:947650"]["proves_user_bottle_identity"] is False
    assert sources["RIFM:CAS141773-73-1"]["authorizes_stock_preparation"] is False
    assert receipt["native_guard_diff"]["new_stock_lineage_code_needed"] is False
