"""Shared inventory parsing and physical-stock authority utilities.

``inventory.txt`` remains a legacy compatibility surface. Executable stock
binding uses the hash-pinned Inventory V5 ``Current Inventory Master``
snapshot, while requirement/preparation rows remain non-owned evidence.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INVENTORY_PATH = PROJECT_ROOT / "inventory.txt"
USER_COMPOUNDING_HOLDS_PATH = (
    PROJECT_ROOT / "data" / "governance" / "inventory_compounding_holds.json"
)
USER_COMPOUNDING_HOLD = "USER_COMPOUNDING_HOLD"
CURRENT_INVENTORY_SNAPSHOT_PATH = (
    PROJECT_ROOT / "data" / "governance" / "inventory_v5_current_stock_snapshot.json"
)
CURRENT_INVENTORY_ALIAS_CROSSWALK_PATH = (
    PROJECT_ROOT / "data" / "governance" / "inventory_v5_alias_crosswalk_20260811.json"
)
BASE_USER_INVENTORY_OVERLAY_PATH = (
    PROJECT_ROOT
    / "data"
    / "governance"
    / "inventory_user_authority_overlay_20260828.json"
)
PREVIOUS_USER_INVENTORY_OVERLAY_PATH = (
    PROJECT_ROOT
    / "data"
    / "governance"
    / "inventory_user_authority_overlay_20260904.json"
)
ORRIS_USER_INVENTORY_OVERLAY_PATH = (
    PROJECT_ROOT
    / "data"
    / "governance"
    / "inventory_user_authority_overlay_20260905.json"
)
NEROLI_USER_INVENTORY_OVERLAY_PATH = (
    PROJECT_ROOT
    / "data"
    / "governance"
    / "inventory_user_authority_overlay_20260906.json"
)
RECONCILED_USER_INVENTORY_OVERLAY_PATH = (
    PROJECT_ROOT / "data/governance/inventory_user_authority_overlay_20260907.json"
)
TINCTURES_USER_INVENTORY_OVERLAY_PATH = (
    PROJECT_ROOT / "data/governance/inventory_user_authority_overlay_20260908.json"
)
AHSEE_USER_INVENTORY_OVERLAY_PATH = (
    PROJECT_ROOT / "data/governance/inventory_user_authority_overlay_20260908_ahsee.json"
)
ROMANDOLIDE_USER_INVENTORY_OVERLAY_PATH = (
    PROJECT_ROOT / "data/governance/inventory_user_authority_overlay_20260908_romandolide.json"
)
FLORHYDRAL_USER_INVENTORY_OVERLAY_PATH = (
    PROJECT_ROOT / "data/governance/inventory_user_authority_overlay_20260910_florhydral.json"
)
ROMANDOLIDE_RESTOCK_USER_INVENTORY_OVERLAY_PATH = (
    PROJECT_ROOT / "data/governance/inventory_user_authority_overlay_20260910_romandolide_restocked.json"
)
STOCK_CLARIFICATIONS_USER_INVENTORY_OVERLAY_PATH = (
    PROJECT_ROOT / "data/governance/inventory_user_authority_overlay_20260910_stock_clarifications.json"
)
PINK_PEPPER_USER_INVENTORY_OVERLAY_PATH = (
    PROJECT_ROOT / "data/governance/inventory_user_authority_overlay_20260915_pink_pepper.json"
)
STOCK_FORMS_AND_TINCTURE_MODEL_USER_INVENTORY_OVERLAY_PATH = (
    PROJECT_ROOT
    / "data/governance/inventory_user_authority_overlay_20260915_stock_forms_and_tincture_model.json"
)
EVERNYL_10WW_DPG_USER_INVENTORY_OVERLAY_PATH = (
    PROJECT_ROOT
    / "data/governance/inventory_user_authority_overlay_20260915_evernyl_10w_w_dpg.json"
)
METHYL_PAMPLEMOUSSE_10WW_ETHANOL_USER_INVENTORY_OVERLAY_PATH = (
    PROJECT_ROOT
    / "data/governance/"
    "inventory_user_authority_overlay_20260915_methyl_pamplemousse_10w_w_ethanol.json"
)
R5_STOCK_CLARIFICATIONS_USER_INVENTORY_OVERLAY_PATH = (
    PROJECT_ROOT
    / "data/governance/"
    "inventory_user_authority_overlay_20260924_r5_stock_clarifications.json"
)
R5_STOCK_CLARIFICATIONS_V2_USER_INVENTORY_OVERLAY_PATH = (
    PROJECT_ROOT
    / "data/governance/"
    "inventory_user_authority_overlay_20260924_r5_stock_clarifications_v2.json"
)
R5_REMAINING_STOCK_FORMS_V3_USER_INVENTORY_OVERLAY_PATH = (
    PROJECT_ROOT
    / "data/governance/"
    "inventory_user_authority_overlay_20260924_r5_remaining_stock_forms_v3.json"
)
AIMI_IDENTITY_USER_INVENTORY_OVERLAY_PATH = (
    PROJECT_ROOT
    / "data/governance/"
    "inventory_user_authority_overlay_20260930_aimi_identity.json"
)
PW_RECEIVED_USER_INVENTORY_OVERLAY_PATH = (
    PROJECT_ROOT
    / "data/governance/inventory_user_authority_overlay_20261007_pw_received.json"
)
TOBACCO_DBCA_USER_INVENTORY_OVERLAY_PATH = (
    PROJECT_ROOT
    / "data/governance/inventory_user_authority_overlay_20261008_tobacco_dbca.json"
)
AMBRETTOLIDE_NEAT_USER_INVENTORY_OVERLAY_PATH = (
    PROJECT_ROOT
    / "data/governance/inventory_user_authority_overlay_20261008_ambrettolide_neat.json"
)
E2MB_OSMANTHUS_MIMOSA_USER_INVENTORY_OVERLAY_PATH = (
    PROJECT_ROOT
    / "data/governance/inventory_user_authority_overlay_20261008_e2mb_osmanthus_mimosa.json"
)
VERTOFIX_COEUR_USER_INVENTORY_OVERLAY_PATH = (
    PROJECT_ROOT
    / "data/governance/inventory_user_authority_overlay_20261009_vertofix_coeur.json"
)
CURRENT_USER_INVENTORY_OVERLAY_PATH = (
    PROJECT_ROOT
    / "data/governance/inventory_user_authority_overlay_20261009_vertofix_coeur_neat.json"
)
PW_RECEIVED_INVENTORY_RECEIPT_PATH = (
    PROJECT_ROOT
    / "data/inventory_receipts/perfumersworld_261004-055451ce1_received_20261007.json"
)
CURRENT_INVENTORY_WORKBOOK_SHA256 = (
    "e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331"
)
CURRENT_INVENTORY_SNAPSHOT_SHA256 = (
    "f81c7b277bb1b56d4b2045c98355754449be11fc9d6f121ce4e8de4539e35d99"
)
CURRENT_INVENTORY_ALIAS_CROSSWALK_SHA256 = (
    "4320f19e1d3dff1cca885ad3d8004c2354cef4c3964e31668a6615028bb914d6"
)
CURRENT_INVENTORY_AUTHORITY = "CURRENT_INVENTORY_MASTER_V5_EXTERNAL_SNAPSHOT"
BASE_USER_INVENTORY_OVERLAY_SHA256 = (
    "9d0f3750e897e13758a1180e158adca464449e9d6dfac176460ba18868a17564"
)
BASE_USER_INVENTORY_TEXT_SIZE_BYTES = 20256
BASE_USER_INVENTORY_TEXT_SHA256 = (
    "46b34ae73406ff3d71c60d77298a0c22f6aeafe74aa2a4c510f554e3840595bf"
)
PREVIOUS_USER_INVENTORY_OVERLAY_SHA256 = (
    "e2fe66cb8077da38142913a73b0d77acd14b6e4953f6155bb2011e1e2bb851a4"
)
PREVIOUS_USER_INVENTORY_TEXT_SIZE_BYTES = 20906
PREVIOUS_USER_INVENTORY_TEXT_SHA256 = (
    "f5c1c046f4654c76c94e0aa77c39976cae6b7bba263f9654e20b92881ecdfb14"
)
ORRIS_USER_INVENTORY_OVERLAY_SHA256 = (
    "08d0f0e41f90741200b3e915789ddd044cbbf7b0ce1b1aa266053452781bb17f"
)
ORRIS_USER_INVENTORY_TEXT_SIZE_BYTES = 20884
ORRIS_USER_INVENTORY_TEXT_SHA256 = (
    "146f74d7cd40ea7b8b8d57285625cc36c2ab84a3663309d8ef0c903860b97fbc"
)
NEROLI_USER_INVENTORY_OVERLAY_SHA256 = (
    "b06024fdef65355c354a4c5a2618d482f215df42a21c2d56aed896bbfb8c305f"
)
RECONCILED_USER_INVENTORY_OVERLAY_SHA256 = "4868678b5e742b309c929d4021530912630ef7ff172c6a7124a08baa07db7f77"
TINCTURES_USER_INVENTORY_OVERLAY_SHA256 = "1e5d1cedeeeaa7adef9116f8e4896b5e3e68e10f817fd0ce0338c30187548419"
AHSEE_USER_INVENTORY_OVERLAY_SHA256 = "dd779bd93e1e9191988b67aeb637f8362dfefb9e4696f86354ef6a371b85ee5d"
ROMANDOLIDE_USER_INVENTORY_OVERLAY_SHA256 = "7265242bd4136333d592004b4ddb9382cd0cd8a1ad364b75085e98290f1a98d8"
FLORHYDRAL_USER_INVENTORY_OVERLAY_SHA256 = "73d004a40c217c3c071b047f2fbaac6285df174d131bcfa7a394d3d18fb93205"
ROMANDOLIDE_RESTOCK_USER_INVENTORY_OVERLAY_SHA256 = "8e6e58203c50db9cb2c73c03cb0a9477127a3143807caf8e3bf849fc8fd7f9fc"
STOCK_CLARIFICATIONS_USER_INVENTORY_OVERLAY_SHA256 = "fd7a66eb6cd921be810c0b9138c22bae404e7ad81ffc715767c0b203d3fcaab8"
PINK_PEPPER_USER_INVENTORY_OVERLAY_SHA256 = "815aa21b826aa9cf6665314d3338cf68a027e4c7aaa5982f2575b10d6303d843"
STOCK_FORMS_AND_TINCTURE_MODEL_USER_INVENTORY_OVERLAY_SHA256 = "bb2a35b04e7c6e5d15911a83eea74158d4bedc372dbe322d599307d87e661eb9"
EVERNYL_10WW_DPG_USER_INVENTORY_OVERLAY_SHA256 = "f4cbe12919b2917fa0b5d968e0933ad884d50bd7c0cf64aa3340fa26f0ac4f42"
METHYL_PAMPLEMOUSSE_10WW_ETHANOL_USER_INVENTORY_OVERLAY_SHA256 = "d0ee1d77b015152c4ffc76a351a693067bf61475eb71a9bf60aecf3fcb9842a2"
R5_STOCK_CLARIFICATIONS_USER_INVENTORY_OVERLAY_SHA256 = "3f4ef634e2bd299a8463559364a03a7805b1198e14396567dce3e7f8caaf4df5"
R5_STOCK_CLARIFICATIONS_V2_USER_INVENTORY_OVERLAY_SHA256 = "9a10cd2f99af1c960a77bd0a7270c25daa24657b790707ecb76c365898b747df"
R5_REMAINING_STOCK_FORMS_V3_USER_INVENTORY_OVERLAY_SHA256 = "0bccf890ee05487b20daca94d02c65103c2a22ed4c6435ba8cb311cd041575fb"
AIMI_IDENTITY_USER_INVENTORY_OVERLAY_SHA256 = "582acaf38382b95252dcc67f01b21a2b56b96ae418c31bda1cef3d355f419ad8"
PW_RECEIVED_USER_INVENTORY_OVERLAY_SHA256 = "180e2823200162a4eaa2975aa4eef9403ad10fec33f2caa1d48a83409c9d7eac"
TOBACCO_DBCA_USER_INVENTORY_OVERLAY_SHA256 = "356a103c4908b85936831ee4593610f3c63210d05f25b0c65963ee74b8548e4c"
AMBRETTOLIDE_NEAT_USER_INVENTORY_OVERLAY_SHA256 = "0b6915b4c28536393bd13bf797b01d77a39bd371efa9d4346cede3b73a6d9a63"
E2MB_OSMANTHUS_MIMOSA_USER_INVENTORY_OVERLAY_SHA256 = "88f10b4bab667ff96822f8365d735a2e28af20e1a0feae4cc254958635c52741"
VERTOFIX_COEUR_USER_INVENTORY_OVERLAY_SHA256 = "79cc7af6442dccf7c9123f40ff535228337669d955bbf9b01351972caedb05f6"
CURRENT_USER_INVENTORY_OVERLAY_SHA256 = "8329a4804909a720d6f7d95959c6c91be56c3fb0c7dd0642cd14a08297095882"
PW_RECEIVED_INVENTORY_RECEIPT_SHA256 = "089c930e044b55e434c0e0438ee7b2c20f48d871f00a219a7237a932419fbc9a"
ROMANDOLIDE_DEPLETION_CONFIRMATION_SHA256 = "5b94ac7cf95a0ee0bb4fc0754a97bda4b0be5aae910c13c7fc4557317f823ade"
FLORHYDRAL_ADDITION_CONFIRMATION_SHA256 = "ff481e5e993f749ce6a5ee0dd8a9606b698c03a17caeac86d1c3adf85065389d"
ROMANDOLIDE_RESTOCK_CONFIRMATION_SHA256 = "42409d0d5420dd66eee3ae845fa2fc6ba701a2f72b9d53f44cda1a1beaabe53b"
STOCK_CLARIFICATIONS_CONFIRMATION_SHA256 = "b753608a05c015a1646b3b5f5c9d16f9e4566ec8ee434675b0966b027f11adc4"
PINK_PEPPER_CONFIRMATION_SHA256 = "f15b8765f18fa49f3b4174dbb6d4f52d7c0934134d4798e74750322e68aa5d9e"
STOCK_FORMS_AND_TINCTURE_MODEL_CONFIRMATION_SHA256 = "e0a2a1da95fe1d80bcdb9560efc219d5610ff2938a5b3694734743e1ef9484f1"
EVERNYL_10WW_DPG_CONFIRMATION_SHA256 = "14d2937e289e0d6bee7be76d59188c85f6761394628e8df08cd811dc30b626e4"
METHYL_PAMPLEMOUSSE_10WW_ETHANOL_CONFIRMATION_SHA256 = "3ab135684a91fdf740c07f7775420a4105d2ba795a1b8a0f8cc3be4f4c9b6925"
R5_STOCK_CLARIFICATIONS_CONFIRMATION_SHA256 = "cd993a027e2c164028dda77a048b3abc5cd1f36cbf8fb7f6712367f9a2bcc273"
R5_STOCK_CLARIFICATIONS_V2_CONFIRMATION_SHA256 = "5179974ec3c64a4c48be310b530b9670b08fa07099f663f5c480f446b0290992"
R5_REMAINING_STOCK_FORMS_V3_CONFIRMATION_SHA256 = "0b76c0480f43ae355c74abd9803850218efcc14773046102f15eab43c63f6178"
AIMI_IDENTITY_CONFIRMATION_SHA256 = "1bc5cd5ae5482343a98cecf90b58070b47cb58f26946246d157ab20d81b7bc5f"
AROMA_MORE_LAVENDER_4042_PRODUCT_RESOLUTION_SHA256 = "3a725f2337e992015878924a8a87ab1af2f846e711c615da1b70b04f4a95e435"
SUPPLIER_PRODUCT_RESOLUTION_SHA256 = "4d47136d7a5acd06fec963f5e1ced6601b227efde5de86b5f83d36af52d8d5d7"
STOCK_CLARIFICATION_RECORDS_SHA256 = "4489cddd2bcc020578c181fdd980f10ab82eafebde051a5e9854e272a181b453"
STOCK_FORMS_AND_TINCTURE_MODEL_RECORDS_SHA256 = "81c755cc7734c0ec13e30e5b2515a69cbe2ae335b74825998b50e2b615aa6844"
EVERNYL_10WW_DPG_RECORDS_SHA256 = "1c4af4f72739fb73d0434e55e1d850704f2e3bd7778e6e24b385d0b4e279ce35"
METHYL_PAMPLEMOUSSE_10WW_ETHANOL_RECORDS_SHA256 = "45bdde5eafd5e2a3302ecfe6ffd7e4a85d2b58462e4afb24f893f80f3a5ac098"
R5_STOCK_CLARIFICATIONS_RECORDS_SHA256 = "8328c91d0a1afc27a022ac8d0a8977ec0b4df361763e13bcac01c776eae1ea30"
R5_STOCK_CLARIFICATIONS_V2_RECORDS_SHA256 = "e7cb019f898652dd1a4ecca76fd4d74b8ba921db2128062144ef266c93080da6"
R5_REMAINING_STOCK_FORMS_V3_RECORDS_SHA256 = "fc2c9e9a355bb407a8d2b9d25c1c0e8b548043d1f158d3cb143b40c292470280"
AIMI_IDENTITY_RECORDS_SHA256 = "bd0eea909130035a6d02f62774ba5b47f1265e46452d9dcf9be2d40802e28962"
AHSEE_STOCK_CONFIRMATION_SHA256 = "08f165d17c3128256a4d98b3eed0762aceb5df8fb4dc728608b96355cc37afec"
CURRENT_USER_INVENTORY_AUTHORITY = "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY_20260908"
FLORHYDRAL_USER_INVENTORY_AUTHORITY = "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY_20260910"
PINK_PEPPER_USER_INVENTORY_AUTHORITY = "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY_20260903"
STOCK_FORMS_USER_INVENTORY_AUTHORITY = "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY_20260915"
R5_STOCK_CLARIFICATIONS_USER_INVENTORY_AUTHORITY = "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY_20260924"
AIMI_IDENTITY_USER_INVENTORY_AUTHORITY = "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY_20260930"
TOBACCO_DBCA_USER_INVENTORY_AUTHORITY = "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY_20261008"
# The Ambrettolide-neat successor shares the 2026-10-08 authority date.
AMBRETTOLIDE_NEAT_USER_INVENTORY_AUTHORITY = TOBACCO_DBCA_USER_INVENTORY_AUTHORITY
# So does the E2MB / Osmanthus / Mimosa successor (v22).
E2MB_OSMANTHUS_MIMOSA_USER_INVENTORY_AUTHORITY = TOBACCO_DBCA_USER_INVENTORY_AUTHORITY
# The Vertofix Coeur successor (v23) records Kenny's 2026-10-09 answer.
VERTOFIX_COEUR_USER_INVENTORY_AUTHORITY = "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY_20261009"
# So does the Vertofix-Coeur-neat successor (v24).
VERTOFIX_COEUR_NEAT_USER_INVENTORY_AUTHORITY = VERTOFIX_COEUR_USER_INVENTORY_AUTHORITY

_HEADING_RE = re.compile(r"^---\s+(.+?)\s+---$")
_BULLET_RE = re.compile(r"^[-•]\s+(.+?)\s*$")
_PERCENT_RE = re.compile(r"\(\s*~?\s*(\d+(?:\.\d+)?)\s*%(?:[^)]*)\)")

_SOLVENT_CATEGORY_TOKENS = ("solvent", "carrier")
_SOLVENT_MATERIALS = {
    "ethanol 96%",
    "dipropylene glycol",
    "dpg",
    "isopropyl myristate",
    "ipm",
    "triethyl citrate",
    "tec",
    "diethyl phthalate",
    "dep",
}


def _identity_crosswalk_key(value: object) -> str:
    """Normalize case/spacing only; never expand the exact source-label set."""

    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


@dataclass(frozen=True)
class InventoryMaterial:
    name: str
    dilution: float
    category: str
    raw_name: str
    status: str
    fraction_basis: str = "unspecified"
    carrier: str = ""
    physical_form: str = ""
    approximate: bool = False
    identity_name: str = ""
    stock_id: str = ""
    authority: str = "LEGACY_INVENTORY_TEXT"
    source_rows: tuple[int, ...] = ()
    source_ref: str = ""
    execution_ready: bool = True
    execution_hold_reason: str = ""
    nominal_property_model_ready: bool = False
    nominal_property_model_limit: str = ""
    requirement_state: str = ""
    # Personal formulation eligibility is intentionally separate from physical
    # execution authority. ``None`` inherits ``execution_ready`` for historical
    # records that predate the lightweight completion workflow.
    design_ready: bool | None = None
    design_hold_reason: str = ""
    completion_event_sha256: str = ""
    completion_source_ref: str = ""
    homogeneity: str = ""
    # V5 row words (``ROW_WIDE_UNRESOLVED_TOKENS``) found in this stock's row,
    # "|"-joined; a Stock page completion does not clear such a stock.
    row_unresolved_tokens: str = ""
    # When a Stock page completion changed the strength, basis or carrier,
    # the overlay/V5 authority's (dilution, fraction_basis, carrier) values.
    authority_facts_differ: tuple[tuple[str, Any], ...] = ()


@dataclass(frozen=True)
class InventoryRequirement:
    """One V5 requirement/demand row; never proof of physical ownership."""

    canonical_name: str
    identity_name: str
    requested_fraction: float | None
    fraction_basis: str
    carrier: str
    disposition: str
    source_row: int
    status: str
    actual_stock_text: str
    can_prepare: str
    category: str


@dataclass(frozen=True)
class CurrentInventoryMaterialization:
    """Lossless V5 authority projection split into stocks and requirements."""

    stocks: tuple[InventoryMaterial, ...]
    requirements: tuple[InventoryRequirement, ...]
    source_workbook_sha256: str
    snapshot_sha256: str
    overlay_sha256: str = ""
    completion_sha256: str = ""
    effective_inventory_sha256: str = ""


@dataclass(frozen=True)
class InventoryV5AliasContract:
    """One identity-only route into an exact, unchanged V5 source row."""

    contract_id: str
    source: str
    destination: str
    current_master_row: int
    expected_route: str
    required_witnesses: tuple[str, ...]
    native_disposition: str


@dataclass(frozen=True)
class CurrentInventoryAliasCrosswalk:
    """Hash- and row-bound V5 label crosswalk with no stock authority."""

    contracts: tuple[InventoryV5AliasContract, ...]
    crosswalk_sha256: str
    source_workbook_sha256: str
    snapshot_sha256: str

    def resolve(self, source_label: str) -> InventoryV5AliasContract | None:
        source_key = _identity_crosswalk_key(source_label)
        for contract in self.contracts:
            if _identity_crosswalk_key(contract.source) == source_key:
                return contract
        return None


class InventoryAuthorityError(ValueError):
    """Raised when the executable inventory authority is absent or drifts."""


def is_user_compounding_held(stock: InventoryMaterial) -> bool:
    return USER_COMPOUNDING_HOLD in stock.execution_hold_reason.split("|")


def load_user_compounding_holds() -> tuple[frozenset[str], str]:
    """Load exact product-label exclusions; missing/malformed policy fails closed."""
    try:
        raw = USER_COMPOUNDING_HOLDS_PATH.read_bytes()
        payload = json.loads(raw)
    except (OSError, ValueError, UnicodeError) as error:
        raise InventoryAuthorityError("user compounding hold policy is unavailable") from error
    flags = {
        "release_authority", "safety_authority", "compounding_authority",
        "evidence_admission_authorized",
    }
    if (
        not isinstance(payload, dict)
        or set(payload) != {"schema_version", "effective_date", "source", "records", *flags}
        or payload["schema_version"] != "perfume-chem-user-compounding-holds-v1"
        or not isinstance(payload["effective_date"], str)
        or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", payload["effective_date"])
        or any(payload[flag] is not False for flag in flags)
        or not isinstance(payload["source"], dict)
        or set(payload["source"]) != {"kind", "request"}
        or payload["source"]["kind"] != "DIRECT_USER_TEMPORARY_COMPOUNDING_EXCLUSION"
        or not isinstance(payload["source"]["request"], str)
        or not payload["source"]["request"].strip()
        or not isinstance(payload["records"], list)
    ):
        raise InventoryAuthorityError("user compounding hold policy is invalid")
    names: dict[str, str] = {}
    fields = {
        "record_id", "identity_name", "supplier_name", "supplier_sku",
        "state", "reason", "clearance",
    }
    for record in payload["records"]:
        if (
            not isinstance(record, dict)
            or set(record) != fields
            or any(not isinstance(value, str) or not value.strip() for value in record.values())
            or record["state"] != "ACTIVE"
            or record["clearance"] != "EXPLICIT_USER_CLEARANCE_REQUIRED"
        ):
            raise InventoryAuthorityError("user compounding hold record is invalid")
        key = record["identity_name"].strip().casefold()
        if key in names:
            raise InventoryAuthorityError("user compounding hold identity is duplicated")
        names[key] = record["identity_name"].strip()
    return frozenset(names.values()), hashlib.sha256(raw).hexdigest()


def apply_user_compounding_holds(
    stocks: tuple[InventoryMaterial, ...],
) -> tuple[tuple[InventoryMaterial, ...], str]:
    """Restrict eligibility without changing stock truth or historical receipts.

    These are exact product-label exclusions, not chemical-family or CAS aliases.
    Apply after stock-detail completions: they cannot clear an exclusion.
    """
    labels, digest = load_user_compounding_holds()
    names = {label.casefold() for label in labels}
    held_stocks = tuple(
        replace(
            stock,
            execution_ready=False,
            execution_hold_reason="|".join(dict.fromkeys(
                [USER_COMPOUNDING_HOLD, *filter(None, stock.execution_hold_reason.split("|"))]
            )),
            design_ready=False,
            design_hold_reason=USER_COMPOUNDING_HOLD,
        )
        if (stock.identity_name or stock.name).strip().casefold() in names
        else stock
        for stock in stocks
    )
    return held_stocks, digest


@dataclass(frozen=True)
class StockSpecification:
    """One declared stock fraction without pretending unlike bases are equivalent."""

    fraction: float
    fraction_basis: str
    carrier: str
    approximate: bool
    declared: bool
    raw: str

    def as_dict(self) -> dict[str, object]:
        return {
            "fraction": self.fraction,
            "fraction_basis": self.fraction_basis,
            "carrier": self.carrier,
            "approximate": self.approximate,
            "declared": self.declared,
            "raw": self.raw,
        }


def _parse_dilution(raw_name: str) -> float:
    match = _PERCENT_RE.search(raw_name)
    if not match:
        raise ValueError("stock concentration is not explicitly declared")
    return float(match.group(1)) / 100.0


def _normalize_carrier(value: str) -> str:
    value = re.sub(r"\b\d+\s*:\s*\d+\b", "", value)
    value = re.sub(r"\s+", " ", value.strip(" .,:;)-").lower())
    return value


# Build cards and formula files write the neat declaration with its supply
# form ("neat / as supplied", "NEAT / undiluted supplied product"). Only these
# whole-cell spellings count; a cell carrying more text stays undeclared.
_NEAT_AS_SUPPLIED_RE = re.compile(
    r"(?:neat|pure|undiluted)\s*(?:/|,|\(|-|\u2013|\u2014)\s*"
    r"(?:as supplied|undiluted(?: supplied product)?)\s*\)?"
)


def parse_stock_specification(
    raw: str,
    *,
    assume_neat_when_missing: bool = False,
) -> StockSpecification:
    """Parse fraction, physical basis, and carrier from inventory/formula text.

    A bare inventory entry means neat by repository convention.  A blank or dash
    in a formula does not: callers can therefore distinguish an explicit neat
    declaration from missing stock metadata.
    """

    text = str(raw or "").strip().replace("**", "").replace("`", "")
    low = text.lower()
    explicit_neat = low in {"neat", "pure", "undiluted"} or bool(
        _NEAT_AS_SUPPLIED_RE.fullmatch(low)
    )
    match = re.search(r"~?\s*(\d+(?:[.,]\d+)?)\s*%", text)
    fraction_match = re.search(
        r"\bexactly\s+(\d+)\s*/\s*(\d+)\b",
        text,
        flags=re.IGNORECASE,
    )

    if fraction_match is not None:
        numerator = int(fraction_match.group(1))
        denominator = int(fraction_match.group(2))
        if numerator <= 0 or denominator <= 0 or numerator > denominator:
            raise ValueError("stock fraction must be within (0, 1]")
        fraction = numerator / denominator
        if re.search(r"\bw\s*/\s*w\b", low):
            basis = "mass_fraction"
        elif re.search(r"\bw\s*/\s*v\b", low):
            basis = "mass_per_volume"
        elif re.search(r"\bv\s*/\s*v\b", low):
            basis = "volume_fraction"
        else:
            basis = "unspecified"
        declared = True
    elif explicit_neat or (match is None and assume_neat_when_missing):
        fraction = 1.0
        basis = "neat"
        declared = True
    elif match is not None:
        fraction = float(match.group(1).replace(",", ".")) / 100.0
        if re.search(r"\bw\s*/\s*w\b", low):
            basis = "mass_fraction"
        elif re.search(r"\bw\s*/\s*v\b", low):
            basis = "mass_per_volume"
        elif re.search(r"\bv\s*/\s*v\b", low):
            basis = "volume_fraction"
        else:
            basis = "unspecified"
        declared = True
    else:
        fraction = 1.0
        basis = "unspecified"
        declared = False

    carrier_match = re.search(r"\bin\s+([^),;#—–]+)", text, flags=re.IGNORECASE)
    carrier = _normalize_carrier(carrier_match.group(1)) if carrier_match else ""
    # A preparation statement such as "30% w/v, 3 g in 10 mL" declares a
    # concentration denominator, not the identity of a solvent. Treating
    # "10 mL" as a carrier silently fabricates finished-matrix provenance.
    if re.fullmatch(
        r"\d+(?:[.,]\d+)?\s*(?:ml|ul|µl|μl|l)",
        carrier,
        flags=re.IGNORECASE,
    ):
        carrier = ""
    approximate = bool("~" in text or re.search(r"\b(?:approx|approximately)\b", low))
    return StockSpecification(
        fraction=fraction,
        fraction_basis=basis,
        carrier=carrier,
        approximate=approximate,
        declared=declared,
        raw=text,
    )


def _parse_status(raw_name: str) -> str:
    upper = raw_name.upper()
    if "PLANNED PREPARATION" in upper or "NOT YET PREPARED" in upper:
        return "planned_preparation"
    if "DEPLETED" in upper:
        return "depleted"
    if "OUT OF STOCK" in upper:
        return "out_of_stock"
    if "RAN OUT" in upper:
        return "ran_out"
    if "DON'T HAVE" in upper or "DONT HAVE" in upper or "NOT OWNED" in upper:
        return "not_owned"
    if "NON-EXECUTABLE" in upper or "HOMOGENEITY HOLD" in upper:
        return "owned_non_executable"
    return "owned"


def _parse_execution_hold_reason(raw_name: str, status: str) -> str:
    upper = raw_name.upper()
    if (
        "QUANTITATIVE DOSING REMAINS ON HOLD" in upper
        or "NEW BOTTLE STRENGTH/CARRIER NOT STATED" in upper
    ):
        return "STOCK_FRACTION_UNSPECIFIED"
    if "STOCK FRACTION UNSPECIFIED" in upper:
        return "STOCK_FRACTION_UNSPECIFIED"
    if "CONCENTRATION BASIS AND CARRIER UNSPECIFIED" in upper:
        return "FRACTION_BASIS_AND_CARRIER_UNSPECIFIED"
    if "CONCENTRATION BASIS UNSPECIFIED" in upper:
        return "FRACTION_BASIS_UNSPECIFIED"
    if "CARRIER UNSPECIFIED" in upper:
        return "CARRIER_UNSPECIFIED"
    if status == "planned_preparation":
        return "NOT_YET_PREPARED"
    if status == "owned_non_executable":
        return "LEGACY_TEXT_CURRENT_STOCK_HOLD"
    return ""


def _strip_status(raw_name: str) -> str:
    return re.sub(r"\s*\[[^\]]+\]\s*$", "", raw_name).strip()


def _canonical_name(raw_name: str) -> str:
    clean = _strip_status(re.sub(r"\s*#.*$", "", raw_name).strip())
    # Remove trailing `# comment` before stripping parenthetical
    clean = re.sub(r"\s*#.*$", "", clean).strip()
    return re.sub(r"\s*\([^)]*\)\s*$", "", clean).strip()


def _identity_name(raw_name: str) -> str:
    """Remove stock preparation text while preserving identity-bearing variants."""

    clean = _strip_status(re.sub(r"\s*#.*$", "", raw_name).strip())
    clean = re.sub(r"\s*#.*$", "", clean).strip()
    clean = re.sub(r"\s+\d+(?:\.\d+)?\s*%(?:\s*(?:w/w|v/v|w/v))?(?:\s+in\s+.*)?$", "", clean, flags=re.IGNORECASE).strip()
    parenthetical = re.search(r"\s*\(([^)]*)\)\s*$", clean)
    if not parenthetical:
        return clean
    content = parenthetical.group(1).lower()
    stock_tokens = ("%", "w/w", "w/v", "v/v", "neat", "dilut", " in dpg", " in dep", " in tec", " in ipm")
    if any(token in content for token in stock_tokens):
        return clean[: parenthetical.start()].strip()
    return clean


def _is_solvent(record: InventoryMaterial) -> bool:
    category = record.category.lower()
    if any(token in category for token in _SOLVENT_CATEGORY_TOKENS):
        return True
    return record.name.lower() in _SOLVENT_MATERIALS


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _normalized_text_bytes(path: Path) -> bytes:
    """Return stable UTF-8 bytes independent of Git CRLF/LF checkout policy."""

    return path.read_bytes().replace(b"\r\n", b"\n")


def _normalized_text_sha256(path: Path) -> str:
    return hashlib.sha256(_normalized_text_bytes(path)).hexdigest()


def load_current_inventory_snapshot(
    path: Path | None = None,
    *,
    require_pinned_snapshot: bool = True,
) -> dict[str, Any]:
    """Load and validate the lossless Current Inventory Master projection."""

    snapshot_path = path or CURRENT_INVENTORY_SNAPSHOT_PATH
    if not snapshot_path.exists():
        raise InventoryAuthorityError(
            f"current inventory authority is missing: {snapshot_path}"
        )
    snapshot_sha = _file_sha256(snapshot_path)
    if require_pinned_snapshot and snapshot_sha != CURRENT_INVENTORY_SNAPSHOT_SHA256:
        raise InventoryAuthorityError(
            "current inventory snapshot hash drift: "
            f"expected {CURRENT_INVENTORY_SNAPSHOT_SHA256}, got {snapshot_sha}"
        )
    try:
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryAuthorityError(
            f"current inventory snapshot is unreadable: {exc}"
        ) from exc

    source = payload.get("source") or {}
    records = payload.get("records")
    expected_headers = {
        "Canonical material",
        "Status",
        "Actual stock(s)",
        "Can prepare",
        "Prior active fraction",
    }
    if payload.get("authority") != CURRENT_INVENTORY_AUTHORITY:
        raise InventoryAuthorityError("current inventory authority class is invalid")
    if source.get("sha256") != CURRENT_INVENTORY_WORKBOOK_SHA256:
        raise InventoryAuthorityError("current inventory workbook hash is not pinned V5")
    if source.get("sheet") != "Current Inventory Master":
        raise InventoryAuthorityError(
            "physical ownership must come from Current Inventory Master"
        )
    if not isinstance(records, list) or payload.get("row_count") != len(records):
        raise InventoryAuthorityError("current inventory row count is inconsistent")
    if not expected_headers.issubset(set(payload.get("headers") or [])):
        raise InventoryAuthorityError("current inventory snapshot headers are incomplete")
    return payload


def _witness_text(value: object) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(value or "").replace("\u2013", "-").replace("\u2014", "-").casefold(),
    ).strip()


def _validate_current_inventory_alias_crosswalk(
    payload: Mapping[str, Any],
    snapshot_payload: Mapping[str, Any],
    *,
    crosswalk_sha256: str,
) -> CurrentInventoryAliasCrosswalk:
    """Validate every package alias against the exact pinned V5 row evidence."""

    if payload.get("schema_version") != "perfume_chem_inventory_v5_alias_crosswalk_v1":
        raise InventoryAuthorityError("current inventory alias crosswalk schema is invalid")
    if payload.get("authority_class") != "IDENTITY_CROSSWALK_ONLY":
        raise InventoryAuthorityError("inventory alias crosswalk authority class is invalid")

    source = payload.get("source")
    if not isinstance(source, Mapping):
        raise InventoryAuthorityError("inventory alias crosswalk source receipt is missing")
    expected_source = {
        "package_sha256": "7c3951ca3266b84b1fe5376375f1ca1f5588a589370ece8e21b5ac1000f22205",
        "member_byte_size": 5003,
        "member_sha256": "edacba08056296321ae0f7987002ea18cd0c2690913ea9d79fef495a0c10913d",
        "inventory_workbook_sha256": CURRENT_INVENTORY_WORKBOOK_SHA256,
        "inventory_snapshot_sha256": CURRENT_INVENTORY_SNAPSHOT_SHA256,
    }
    for key, expected in expected_source.items():
        if source.get(key) != expected:
            raise InventoryAuthorityError(
                f"inventory alias crosswalk source binding drift: {key}"
            )

    policy = payload.get("policy")
    expected_policy = {
        "scope": "V5_CANDIDATE_LOOKUP_ONLY",
        "fuzzy_matching": False,
        "preserve_original_formula_label": True,
        "preserve_native_stock_and_requirement_state": True,
        "creates_stock": False,
        "creates_preparation": False,
        "creates_ownership": False,
        "changes_stock_fraction": False,
    }
    if policy != expected_policy:
        raise InventoryAuthorityError("inventory alias crosswalk policy is not fail closed")
    authority = payload.get("authority")
    if not isinstance(authority, Mapping) or not authority or any(
        value is not False for value in authority.values()
    ):
        raise InventoryAuthorityError("inventory alias crosswalk authority must remain false")

    raw_contracts = payload.get("contracts")
    if not isinstance(raw_contracts, list) or len(raw_contracts) != 18:
        raise InventoryAuthorityError("inventory alias crosswalk must contain 18 contracts")
    snapshot_records = snapshot_payload.get("records")
    if not isinstance(snapshot_records, list):
        raise InventoryAuthorityError("current inventory snapshot records are missing")
    rows: dict[int, Mapping[str, Any]] = {}
    for raw_row in snapshot_records:
        if not isinstance(raw_row, Mapping):
            raise InventoryAuthorityError("current inventory snapshot row is invalid")
        source_row = int(raw_row.get("_source_row") or 0)
        if source_row in rows:
            raise InventoryAuthorityError("current inventory snapshot row is duplicated")
        rows[source_row] = raw_row

    allowed_dispositions = {
        "GUARDED_ALIAS",
        "GUARDED_ALIAS_ABSTAIN_UNTIL_EXACT_STOCK",
        "GUARDED_ALIAS_GAP",
        "GUARDED_ALIAS_PREPARATION_REQUIRED",
        "GUARDED_ALIAS_PRESERVE_HOLD",
        "NATIVE_NOOP",
    }
    expected_keys = {
        "contract_id",
        "source",
        "destination",
        "current_master_row",
        "expected_route",
        "required_witnesses",
        "native_disposition",
    }
    contracts: list[InventoryV5AliasContract] = []
    seen_ids: set[str] = set()
    seen_sources: set[str] = set()
    for index, raw_contract in enumerate(raw_contracts, start=1):
        if not isinstance(raw_contract, Mapping) or set(raw_contract) != expected_keys:
            raise InventoryAuthorityError("inventory alias contract fields are invalid")
        contract_id = str(raw_contract.get("contract_id") or "")
        if contract_id != f"IDCL-{index:03d}" or contract_id in seen_ids:
            raise InventoryAuthorityError("inventory alias contract ID sequence is invalid")
        source_label = str(raw_contract.get("source") or "").strip()
        destination = str(raw_contract.get("destination") or "").strip()
        source_key = _identity_crosswalk_key(source_label)
        if not source_key or source_key in seen_sources:
            raise InventoryAuthorityError("inventory alias source is blank or duplicated")
        source_row = int(raw_contract.get("current_master_row") or 0)
        row = rows.get(source_row)
        if row is None:
            raise InventoryAuthorityError(
                f"inventory alias destination row is absent: {contract_id}"
            )
        if str(row.get("Canonical material") or "").strip() != destination:
            raise InventoryAuthorityError(
                f"inventory alias destination label drift: {contract_id}"
            )
        witnesses = raw_contract.get("required_witnesses")
        if (
            not isinstance(witnesses, list)
            or len(witnesses) != 2
            or any(not str(value).strip() for value in witnesses)
        ):
            raise InventoryAuthorityError(
                f"inventory alias witnesses are invalid: {contract_id}"
            )
        row_evidence = " | ".join(_witness_text(value) for value in row.values())
        for witness in witnesses:
            if _witness_text(witness) not in row_evidence:
                raise InventoryAuthorityError(
                    f"inventory alias row witness drift: {contract_id}"
                )
        native_disposition = str(raw_contract.get("native_disposition") or "")
        if native_disposition not in allowed_dispositions:
            raise InventoryAuthorityError(
                f"inventory alias native disposition is invalid: {contract_id}"
            )
        contracts.append(
            InventoryV5AliasContract(
                contract_id=contract_id,
                source=source_label,
                destination=destination,
                current_master_row=source_row,
                expected_route=str(raw_contract.get("expected_route") or ""),
                required_witnesses=tuple(str(value) for value in witnesses),
                native_disposition=native_disposition,
            )
        )
        seen_ids.add(contract_id)
        seen_sources.add(source_key)

    return CurrentInventoryAliasCrosswalk(
        contracts=tuple(contracts),
        crosswalk_sha256=crosswalk_sha256,
        source_workbook_sha256=CURRENT_INVENTORY_WORKBOOK_SHA256,
        snapshot_sha256=CURRENT_INVENTORY_SNAPSHOT_SHA256,
    )


def load_current_inventory_alias_crosswalk(
    path: Path | None = None,
    *,
    snapshot_path: Path | None = None,
    require_pinned_crosswalk: bool = True,
    require_pinned_snapshot: bool = True,
) -> CurrentInventoryAliasCrosswalk:
    """Load the exact V5 lookup crosswalk or abort the binding operation.

    Bypassing this optional compatibility surface can only leave a label
    unresolved. It cannot create a stock. Any caller that uses the crosswalk
    receives a fully hash-, row-, destination-, and witness-validated object.
    """

    crosswalk_path = path or CURRENT_INVENTORY_ALIAS_CROSSWALK_PATH
    if not crosswalk_path.exists():
        raise InventoryAuthorityError(
            f"current inventory alias crosswalk is missing: {crosswalk_path}"
        )
    crosswalk_sha = _file_sha256(crosswalk_path)
    if require_pinned_crosswalk and crosswalk_sha != CURRENT_INVENTORY_ALIAS_CROSSWALK_SHA256:
        raise InventoryAuthorityError(
            "current inventory alias crosswalk hash drift: "
            f"expected {CURRENT_INVENTORY_ALIAS_CROSSWALK_SHA256}, got {crosswalk_sha}"
        )
    try:
        payload = json.loads(crosswalk_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryAuthorityError(
            f"current inventory alias crosswalk is unreadable: {exc}"
        ) from exc
    snapshot_payload = load_current_inventory_snapshot(
        snapshot_path,
        require_pinned_snapshot=require_pinned_snapshot,
    )
    return _validate_current_inventory_alias_crosswalk(
        payload,
        snapshot_payload,
        crosswalk_sha256=crosswalk_sha,
    )


def _v5_identity_name(canonical_name: str) -> str:
    """Strip a requested stock suffix without stripping chemical identity text."""

    clean = re.sub(r"\s+", " ", str(canonical_name or "").strip())
    clean = re.sub(
        r"\s+~?\d+(?:[.,]\d+)?\s*%"
        r"(?:\s*(?:w\s*/\s*w|w\s*/\s*v|v\s*/\s*v))?"
        r"(?:\s+in\s+(?:dpg|dep|tec|ipm|ethanol))?\s*$",
        "",
        clean,
        flags=re.IGNORECASE,
    )
    return re.sub(r"\s+", " ", clean).strip()


def _carrier_from_stock_text(text: str, *, start: int = 0) -> str:
    tail = text[start:]
    match = re.search(
        r"\b(dpg|dipropylene glycol|dep|diethyl phthalate|tec|triethyl citrate|"
        r"ipm|isopropyl myristate|ethanol|ethyl alcohol)\b",
        tail,
        flags=re.IGNORECASE,
    )
    return _normalize_carrier(match.group(1)) if match else ""


def _actual_stock_specs(
    actual_stock_text: str,
    status: str,
) -> list[tuple[StockSpecification, str]]:
    """Extract only explicit physical concentrations from a V5 actual-stock cell."""

    actual = re.sub(r"\s+", " ", str(actual_stock_text or "").strip())
    if not actual:
        return []
    segments = [
        segment.strip()
        for segment in re.split(r"\s*;\s*|\s+\+\s+", actual)
        if segment.strip()
    ]
    extracted: list[tuple[StockSpecification, str]] = []
    seen: set[tuple[float, str, str, str]] = set()
    for segment in segments:
        low = segment.lower()
        if re.search(r"\bneat\b", low):
            spec = StockSpecification(
                fraction=1.0,
                fraction_basis="neat",
                carrier="",
                approximate=False,
                declared=True,
                raw=segment,
            )
            key = (1.0, "neat", "", low)
            if key not in seen:
                seen.add(key)
                extracted.append((spec, segment))

        for match in re.finditer(r"~?\s*(\d+(?:[.,]\d+)?)\s*%", segment):
            fraction = float(match.group(1).replace(",", ".")) / 100.0
            if not 0.0 < fraction <= 1.0:
                continue
            basis_context = segment[max(0, match.start() - 8) : match.end() + 12].lower()
            if re.search(r"\bw\s*/\s*w\b", basis_context):
                basis = "mass_fraction"
            elif re.search(r"\bw\s*/\s*v\b", basis_context):
                basis = "mass_per_volume"
            elif re.search(r"\bv\s*/\s*v\b", basis_context):
                basis = "volume_fraction"
            else:
                basis = "unspecified"
            carrier = _carrier_from_stock_text(segment, start=match.end())
            descriptor = f"{segment} [{fraction:.12g}]"
            spec = StockSpecification(
                fraction=fraction,
                fraction_basis=basis,
                carrier=carrier,
                approximate="~" in match.group(0),
                declared=True,
                raw=segment,
            )
            key = (fraction, basis, carrier, descriptor.lower())
            if key not in seen:
                seen.add(key)
                extracted.append((spec, descriptor))

    if not extracted and "NEAT" in status.upper() and actual:
        extracted.append(
            (
                StockSpecification(
                    fraction=1.0,
                    fraction_basis="neat",
                    carrier="",
                    approximate=False,
                    declared=True,
                    raw=actual,
                ),
                actual,
            )
        )
    return extracted


def _requested_stock_spec(
    row: Mapping[str, Any],
    actual_specs: list[tuple[StockSpecification, str]],
) -> StockSpecification | None:
    canonical = str(row.get("Canonical material") or "").strip()
    parsed = parse_stock_specification(canonical)
    if parsed.declared:
        return parsed
    prior = row.get("Prior active fraction")
    if isinstance(prior, (int, float)) and 0.0 < float(prior) <= 1.0:
        fraction = float(prior)
        return StockSpecification(
            fraction=fraction,
            fraction_basis="neat" if fraction == 1.0 else "unspecified",
            carrier="",
            approximate=False,
            declared=True,
            raw=f"Prior active fraction={fraction:g}",
        )
    if len(actual_specs) == 1:
        return actual_specs[0][0]
    return None


def _requirement_disposition(
    status: str,
    requested: StockSpecification | None,
    actual_specs: list[tuple[StockSpecification, str]],
    can_prepare: str,
) -> str:
    upper = status.upper()
    if any(token in upper for token in ("GAP", "DO NOT USE", "OUT OF STOCK", "BANNED")):
        return "GAP"
    if any(token in upper for token in ("CONSTRUCTIBLE", "PLANNED ACQUISITION")):
        return "PREPARATION_REQUIRED"
    if not upper.startswith("HAVE"):
        return "UNRESOLVED"
    if requested is None:
        return "OWNED" if actual_specs else "UNRESOLVED"
    if any(abs(spec.fraction - requested.fraction) <= 1e-9 for spec, _ in actual_specs):
        return "OWNED"
    if actual_specs and (
        can_prepare.strip()
        or any(token in upper for token in ("ONLY", "DIFFERENT STOCK", "PREPARE"))
    ):
        return "PREPARATION_REQUIRED"
    return "UNRESOLVED"


# V5 row words that leave the whole row unresolved whatever its strength,
# basis and carrier say, so neither the row nor a Lab app Stock page
# completion (which records only those facts) makes such a stock ready.
ROW_WIDE_UNRESOLVED_TOKENS = (
    "PRODUCT BASIS",
    "HETEROGENEOUS",
    "PHYSICAL FORM OPEN",
    "SPECIES UNRESOLVED",
    "IDENTITY KEPT SEPARATE",
    "TWO PRODUCTS",
    "MULTIPLE BENZOINS",
    "UNCONFIRMED",
)


def row_wide_unresolved_tokens(text: str) -> tuple[str, ...]:
    """Return the ``ROW_WIDE_UNRESOLVED_TOKENS`` found in a V5 row's text."""

    upper = text.upper()
    return tuple(token for token in ROW_WIDE_UNRESOLVED_TOKENS if token in upper)


def _stock_execution_ready(
    status: str,
    spec: StockSpecification,
    descriptor: str,
    *,
    stock_count: int = 1,
) -> bool:
    row_context = status.upper()
    descriptor_context = descriptor.upper()
    context = f"{row_context} {descriptor_context}"
    # The V5 rows marked LOT DETAIL OPEN still authorize use at their listed
    # neat/as-supplied strength. Missing supplier/lot data limits batch-specific
    # modeling and release claims; it does not make that raw stock volume unknown.
    if row_wide_unresolved_tokens(context):
        return False
    if (
        "CARRIER UNSTATED" in descriptor_context
        or "CARRIER NOT STATED" in descriptor_context
        or (stock_count == 1 and "CARRIER UNSTATED" in row_context)
    ):
        return False
    if spec.fraction == 1.0:
        return spec.fraction_basis == "neat"
    return bool(spec.carrier)


def _load_20260904_user_inventory_successor(
    successor: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate the dated two-record successor and merge its immutable base."""

    predecessor = successor.get("predecessor")
    source = successor.get("source")
    policy = successor.get("policy")
    head_records = successor.get("records")
    if (
        successor.get("schema_version")
        != "perfume_chem_user_inventory_authority_successor_overlay_v1"
        or successor.get("authority")
        != "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY"
        or successor.get("effective_date") != "2026-09-04"
        or not isinstance(predecessor, Mapping)
        or not isinstance(source, Mapping)
        or not isinstance(policy, Mapping)
        or not isinstance(head_records, list)
    ):
        raise InventoryAuthorityError(
            "2026-09-04 user inventory successor metadata is invalid"
        )

    expected_predecessor = {
        "kind": "USER_AUTHORITY_OVERLAY",
        "authority": "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY",
        "effective_date": "2026-08-28",
        "path": "data/governance/inventory_user_authority_overlay_20260828.json",
        "normalized_text_sha256": BASE_USER_INVENTORY_OVERLAY_SHA256,
    }
    if dict(predecessor) != expected_predecessor:
        raise InventoryAuthorityError(
            "2026-09-04 inventory successor predecessor pin drift"
        )
    if (
        _normalized_text_sha256(BASE_USER_INVENTORY_OVERLAY_PATH)
        != BASE_USER_INVENTORY_OVERLAY_SHA256
    ):
        raise InventoryAuthorityError(
            "2026-09-04 inventory successor predecessor bytes drift"
        )

    expected_source = {
        "kind": "DIRECT_USER_CURRENT_STOCK_CORRECTION",
        "asserted_date": "2026-09-04",
        "inventory_text_path": "inventory.txt",
        "inventory_text_size_bytes": PREVIOUS_USER_INVENTORY_TEXT_SIZE_BYTES,
        "inventory_text_sha256": PREVIOUS_USER_INVENTORY_TEXT_SHA256,
    }
    if dict(source) != expected_source:
        raise InventoryAuthorityError(
            "2026-09-04 inventory successor historical source binding drift"
        )

    expected_policy = {
        "inherit_predecessor_policy": True,
        "predecessor_overlay_immutable": True,
        "merge_other_task_branch": False,
        "formula_rebase_authorized": False,
        "general_substitution_authorized": False,
        "unknown_metadata_fails_closed": True,
        "raw_volume_transfer_does_not_establish_exact_mass_or_volume_conversion": (
            True
        ),
    }
    if dict(policy) != expected_policy:
        raise InventoryAuthorityError("2026-09-04 inventory successor policy drift")

    by_id = {
        str(record.get("record_id") or ""): record
        for record in head_records
        if isinstance(record, Mapping)
    }
    expected_ids = {
        "INV-USER-20260901-001",
        "INV-USER-20260901-002",
        "INV-USER-20260901-003",
        "INV-USER-20260902-001",
        "INV-USER-20260902-002",
        "INV-USER-20260904-001",
        "INV-USER-20260904-002",
        "INV-USER-20260904-003",
        "INV-USER-20260904-004",
    }
    if len(by_id) != len(head_records) or set(by_id) != expected_ids:
        raise InventoryAuthorityError(
            "2026-09-04 inventory successor record set drift"
        )

    shared_limits = {
        "availability_confirmed": True,
        "stock_fraction_known": True,
        "fraction_basis_known": True,
        "carrier_known": True,
        "homogeneous_confirmed": True,
        "clear_confirmed": True,
        "pipetteable_confirmed": True,
        "raw_stock_volume_transfer_ready": True,
        "remaining_quantity_asserted": False,
        "stock_solution_density_asserted": False,
        "exact_active_mass_from_raw_volume_authorized": False,
        "literal_active_volume_asserted": False,
        "carrier_displacement_volume_authorized": False,
        "exact_active_ppm_oav_math_authorized": False,
        "formula_rebase_authorized": False,
        "procurement_authorized": False,
        "formula_compounding_authorized": False,
        "safety_asserted": False,
        "stability_asserted": False,
        "sensory_equivalence_asserted": False,
        "release_success_asserted": False,
    }
    ambrettolide = by_id["INV-USER-20260904-001"]
    tonkarome = by_id["INV-USER-20260904-002"]
    expected_ambrettolide_stock = {
        "fraction": 0.1,
        "fraction_basis": "mass_fraction",
        "carrier": "dpg",
        "fraction_authority": "EXPLICIT_USER_ASSERTION",
        "execution_ready": True,
        "execution_scope": "RAW_STOCK_VOLUME_TRANSFER_ONLY",
        "execution_basis": "USER_CONFIRMED_HOMOGENEOUS_CLEAR_PIPETTABLE_20260904",
    }
    expected_ambrettolide_overrides = [
        {
            "source_row": 27,
            "disposition": "OWNED",
            "status": (
                "HAVE - USER-CONFIRMED 10% W/W IN DPG; RAW-VOLUME EXECUTABLE"
            ),
            "actual_stock_text": (
                "Ambrettolide 10% w/w in DPG; homogeneous, clear, pipetteable, "
                "and raw-volume executable"
            ),
            "can_prepare": "",
        },
        {
            "source_row": 28,
            "disposition": "OWNED",
            "status": (
                "DUPLICATE REQUIREMENT ROW - SAME OWNED 10% W/W IN DPG STOCK; "
                "COUNT ONCE"
            ),
            "actual_stock_text": (
                "Ambrettolide 10% w/w in DPG; homogeneous, clear, pipetteable, "
                "and raw-volume executable"
            ),
            "can_prepare": "",
        },
    ]
    if (
        ambrettolide.get("canonical_name") != "Ambrettolide"
        or ambrettolide.get("aliases")
        != [
            "Ambrettolide 10%",
            "Ambrettolide 10% in DPG",
            "Ambrettolide 10% w/w in DPG",
        ]
        or ambrettolide.get("state") != "OWNED"
        or ambrettolide.get("category") != "musk"
        or ambrettolide.get("stock") != expected_ambrettolide_stock
        or ambrettolide.get("supersedes_parent_stocks") != []
        or ambrettolide.get("requirement_overrides")
        != expected_ambrettolide_overrides
        or ambrettolide.get("effective_date") != "2026-09-04"
        or ambrettolide.get("source_kind")
        != "DIRECT_USER_CURRENT_STOCK_CORRECTION"
        or ambrettolide.get("authority_limits") != shared_limits
    ):
        raise InventoryAuthorityError("Ambrettolide successor contract drift")

    expected_tonkarome_stock = {
        "fraction": 0.2,
        "fraction_basis": "mass_fraction",
        "carrier": "tec",
        "fraction_authority": "EXPLICIT_USER_ASSERTION",
        "execution_ready": True,
        "execution_scope": "RAW_STOCK_VOLUME_TRANSFER_ONLY",
        "execution_basis": "USER_CONFIRMED_HOMOGENEOUS_CLEAR_PIPETTABLE_20260904",
    }
    expected_tonkarome_overrides = [
        {
            "source_row": 264,
            "disposition": "OWNED",
            "status": (
                "HAVE - USER-CONFIRMED 20% W/W IN TEC; RAW-VOLUME EXECUTABLE"
            ),
            "actual_stock_text": (
                "Tonkarome 20% w/w in TEC; homogeneous, clear, pipetteable, and "
                "raw-volume executable"
            ),
            "can_prepare": "",
        }
    ]
    if (
        tonkarome.get("canonical_name") != "Tonkarome"
        or tonkarome.get("aliases")
        != ["Tonkarome 20%", "Tonkarome 20% w/w in TEC"]
        or tonkarome.get("state") != "OWNED"
        or tonkarome.get("category") != "tonka / powder"
        or tonkarome.get("stock") != expected_tonkarome_stock
        or tonkarome.get("supersedes_parent_stocks")
        != [{"source_row": 264, "fraction": 0.2}]
        or tonkarome.get("requirement_overrides") != expected_tonkarome_overrides
        or tonkarome.get("effective_date") != "2026-09-04"
        or tonkarome.get("source_kind")
        != "DIRECT_USER_CURRENT_STOCK_CORRECTION"
        or tonkarome.get("authority_limits") != shared_limits
    ):
        raise InventoryAuthorityError("Tonkarome successor contract drift")

    expected_signatures = {
        "INV-USER-20260901-001": (
            "Bacdanol",
            "OWNED",
            1.0,
            "neat",
            "",
            True,
            (),
            (),
        ),
        "INV-USER-20260901-002": (
            "Guaiacwood EO",
            "OWNED",
            1.0 / 3.0,
            "mass_fraction",
            "ethanol + dep",
            True,
            (),
            (125,),
        ),
        "INV-USER-20260901-003": (
            "Benzyl Salicylate",
            "OWNED",
            1.0,
            "neat",
            "",
            True,
            (41,),
            (41,),
        ),
        "INV-USER-20260902-001": (
            "Galbanum EO",
            "UNAVAILABLE",
            None,
            None,
            None,
            None,
            (114,),
            (114,),
        ),
        "INV-USER-20260902-002": (
            "Ambrox Super",
            "OWNED",
            0.25,
            "mass_fraction",
            "dpg + ipm + ethanol",
            True,
            (30,),
            (30,),
        ),
        "INV-USER-20260904-003": (
            "Givaudan AIMI",
            "OWNED",
            1.0,
            "neat",
            "",
            True,
            (21,),
            (21,),
        ),
        "INV-USER-20260904-004": (
            "Vetiver EO (India)",
            "OWNED",
            1.0,
            "neat",
            "",
            True,
            (245,),
            (245,),
        ),
    }
    for record_id, signature in expected_signatures.items():
        record = by_id[record_id]
        stock = record.get("stock")
        selector_rows = tuple(
            int(selector["source_row"])
            for selector in record.get("supersedes_parent_stocks", [])
        )
        override_rows = tuple(
            int(override["source_row"])
            for override in record.get("requirement_overrides", [])
        )
        observed = (
            record.get("canonical_name"),
            record.get("state"),
            stock.get("fraction") if isinstance(stock, Mapping) else None,
            stock.get("fraction_basis") if isinstance(stock, Mapping) else None,
            stock.get("carrier") if isinstance(stock, Mapping) else None,
            stock.get("execution_ready") if isinstance(stock, Mapping) else None,
            selector_rows,
            override_rows,
        )
        if observed != signature:
            raise InventoryAuthorityError(
                f"{record_id} inventory successor contract drift"
            )

    base = load_current_user_inventory_overlay(
        BASE_USER_INVENTORY_OVERLAY_PATH,
        require_pinned_overlay=True,
    )
    base_records = base.get("records")
    if not isinstance(base_records, list):
        raise InventoryAuthorityError("base inventory overlay record set is invalid")
    replacement_names = {"bacdanol", "givaudan aimi", "guaiacwood eo"}
    retained_base_records = [
        record
        for record in base_records
        if isinstance(record, Mapping)
        and str(record.get("canonical_name") or "").casefold()
        not in replacement_names
    ]
    base_ids = {
        str(record.get("record_id") or "")
        for record in retained_base_records
        if isinstance(record, Mapping)
    }
    base_names = {
        str(record.get("canonical_name") or "").casefold()
        for record in retained_base_records
        if isinstance(record, Mapping)
    }
    head_names = {
        str(record.get("canonical_name") or "").casefold()
        for record in head_records
        if isinstance(record, Mapping)
    }
    if base_ids.intersection(expected_ids) or base_names.intersection(head_names):
        raise InventoryAuthorityError(
            "2026-09-04 inventory successor collides with predecessor records"
        )
    base_override_rows = {
        int(override["source_row"])
        for record in retained_base_records
        if isinstance(record, Mapping)
        for override in record.get("requirement_overrides", [])
    }
    if base_override_rows.intersection({27, 28, 264}):
        raise InventoryAuthorityError(
            "2026-09-04 inventory successor duplicates predecessor overrides"
        )

    consolidated = dict(successor)
    consolidated["head_policy"] = dict(policy)
    consolidated["parent"] = dict(base["parent"])
    consolidated["base_policy"] = dict(base["policy"])
    consolidated["policy"] = {**dict(base["policy"]), **dict(policy)}
    consolidated["delta_records"] = list(head_records)
    consolidated["records"] = [*retained_base_records, *head_records]
    return consolidated


def _load_20260905_user_inventory_successor(
    successor: Mapping[str, Any],
) -> dict[str, Any]:
    """Add the confirmed Orris working stock without rebasing prior records."""

    if (
        successor.get("schema_version")
        != "perfume_chem_user_inventory_authority_successor_overlay_v2"
        or successor.get("authority") != "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY"
        or successor.get("effective_date") != "2026-09-05"
    ):
        raise InventoryAuthorityError("2026-09-05 inventory successor metadata drift")
    expected_predecessor = {
        "kind": "USER_AUTHORITY_OVERLAY",
        "authority": "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY",
        "effective_date": "2026-09-04",
        "path": "data/governance/inventory_user_authority_overlay_20260904.json",
        "normalized_text_sha256": PREVIOUS_USER_INVENTORY_OVERLAY_SHA256,
    }
    if successor.get("predecessor") != expected_predecessor:
        raise InventoryAuthorityError("2026-09-05 inventory predecessor pin drift")
    expected_source = {
        "kind": "DIRECT_USER_CURRENT_STOCK_CORRECTION",
        "asserted_date": "2026-09-05",
        "inventory_text_path": "inventory.txt",
        "inventory_text_size_bytes": ORRIS_USER_INVENTORY_TEXT_SIZE_BYTES,
        "inventory_text_sha256": ORRIS_USER_INVENTORY_TEXT_SHA256,
    }
    if successor.get("source") != expected_source:
        raise InventoryAuthorityError(
            "2026-09-05 inventory successor historical text receipt drift"
        )
    expected_policy = {
        "inherit_predecessor_policy": True,
        "predecessor_overlay_immutable": True,
        "preserve_inherited_stock_ids": True,
        "formula_rebase_authorized": False,
        "general_substitution_authorized": False,
        "unknown_metadata_fails_closed": True,
        "raw_volume_transfer_does_not_establish_exact_mass_or_volume_conversion": True,
    }
    if successor.get("policy") != expected_policy:
        raise InventoryAuthorityError("2026-09-05 inventory successor policy drift")
    records = successor.get("records")
    if not isinstance(records, list) or len(records) != 1:
        raise InventoryAuthorityError("2026-09-05 inventory successor record set drift")
    record = records[0]
    expected_stock = {
        "fraction": 0.09,
        "fraction_basis": "mass_fraction",
        "carrier": "dep",
        "fraction_authority": "EXPLICIT_USER_CURRENT_STOCK_CORRECTION",
        "execution_ready": True,
        "execution_scope": "STOCK_IDENTITY_AND_FRACTION_BINDING_ONLY",
        "execution_hold_reason": "",
    }
    expected_override = {
        "source_row": 195,
        "disposition": "OWNED",
        "status": "HAVE - USER-CONFIRMED ORRIS LIQUID PRODUCT AT 9% W/W IN DEP",
        "actual_stock_text": (
            "Orris Liquid (PerfumersWorld product) 9% w/w in DEP; "
            "product mass fraction, not pure irone content"
        ),
        "can_prepare": "",
    }
    expected_limits = {
        "availability_confirmed": True,
        "stock_fraction_known": True,
        "fraction_basis_known": True,
        "carrier_known": True,
        "product_mass_from_weighed_stock_known": True,
        "stock_solution_density_asserted": False,
        "exact_active_mass_from_raw_volume_authorized": False,
        "literal_active_volume_asserted": False,
        "carrier_displacement_volume_authorized": False,
        "pure_irone_assay_asserted": False,
        "formula_rebase_authorized": False,
        "formula_compounding_authorized": False,
        "safety_asserted": False,
        "stability_asserted": False,
        "sensory_equivalence_asserted": False,
        "release_success_asserted": False,
    }
    if (
        not isinstance(record, Mapping)
        or record.get("record_id") != "INV-USER-20260905-001"
        or record.get("canonical_name") != "Orris Liquid"
        or record.get("state") != "OWNED"
        or record.get("category") != "orris_violet"
        or record.get("stock") != expected_stock
        or record.get("supersedes_parent_stocks") != []
        or record.get("requirement_overrides") != [expected_override]
        or record.get("authority_limits") != expected_limits
        or record.get("effective_date") != "2026-09-05"
        or record.get("source_kind") != "DIRECT_USER_CURRENT_STOCK_CORRECTION"
    ):
        raise InventoryAuthorityError("2026-09-05 Orris stock contract drift")

    previous = load_current_user_inventory_overlay(PREVIOUS_USER_INVENTORY_OVERLAY_PATH)
    inherited = previous["records"]
    if any(
        row.get("canonical_name") == "Orris Liquid"
        or any(item["source_row"] == 195 for item in row["requirement_overrides"])
        for row in inherited
    ):
        raise InventoryAuthorityError("2026-09-05 Orris successor collision")
    previous_head_ids = {row["record_id"] for row in previous["delta_records"]}
    origins = {
        row["record_id"]: {
            "path": (
                expected_predecessor["path"]
                if row["record_id"] in previous_head_ids
                else "data/governance/inventory_user_authority_overlay_20260828.json"
            ),
            "sha256": (
                PREVIOUS_USER_INVENTORY_OVERLAY_SHA256
                if row["record_id"] in previous_head_ids
                else BASE_USER_INVENTORY_OVERLAY_SHA256
            ),
        }
        for row in inherited
    }
    origins[record["record_id"]] = {
        "path": "data/governance/inventory_user_authority_overlay_20260905.json",
        "sha256": ORRIS_USER_INVENTORY_OVERLAY_SHA256,
    }
    return {
        **dict(successor),
        "parent": dict(previous["parent"]),
        "base_policy": dict(previous["base_policy"]),
        "head_policy": dict(expected_policy),
        "policy": {**dict(previous["policy"]), **expected_policy},
        "delta_records": records,
        "records": [*inherited, record],
        "record_origins": origins,
    }


def _load_20260906_user_inventory_successor(
    successor: Mapping[str, Any],
) -> dict[str, Any]:
    """Retire the old Neroli dilution while preserving every inherited record."""

    if (
        successor.get("schema_version")
        != "perfume_chem_user_inventory_authority_successor_overlay_v3"
        or successor.get("authority") != "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY"
        or successor.get("effective_date") != "2026-09-06"
    ):
        raise InventoryAuthorityError("2026-09-06 inventory successor metadata drift")
    expected_predecessor = {
        "kind": "USER_AUTHORITY_OVERLAY",
        "authority": "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY",
        "effective_date": "2026-09-05",
        "path": "data/governance/inventory_user_authority_overlay_20260905.json",
        "normalized_text_sha256": ORRIS_USER_INVENTORY_OVERLAY_SHA256,
    }
    if successor.get("predecessor") != expected_predecessor:
        raise InventoryAuthorityError("2026-09-06 inventory predecessor pin drift")
    expected_source = {
        "kind": "DIRECT_USER_CURRENT_STOCK_CORRECTION",
        "asserted_date": "2026-09-06",
        "inventory_text_path": "inventory.txt",
        "inventory_text_size_bytes": 20904,
        "inventory_text_sha256": "214b2ef6bc84a04ae2e3318088a8d5d0f559bdee3dcd7afcc95ff272ff480243",
    }
    if successor.get("source") != expected_source:
        raise InventoryAuthorityError(
            "2026-09-06 inventory successor is historical inventory binding drift"
        )
    expected_policy = {
        "inherit_predecessor_policy": True,
        "predecessor_overlay_immutable": True,
        "preserve_inherited_stock_ids": True,
        "formula_rebase_authorized": False,
        "general_substitution_authorized": False,
        "unknown_metadata_fails_closed": True,
        "raw_volume_transfer_does_not_establish_exact_mass_or_volume_conversion": True,
    }
    if successor.get("policy") != expected_policy:
        raise InventoryAuthorityError("2026-09-06 inventory successor policy drift")
    records = successor.get("records")
    if not isinstance(records, list) or len(records) != 1:
        raise InventoryAuthorityError("2026-09-06 inventory successor record set drift")
    record = records[0]
    expected_stock = {
        "fraction": 1.0,
        "fraction_basis": "neat",
        "carrier": "",
        "fraction_authority": "EXPLICIT_USER_CURRENT_STOCK_CORRECTION",
        "execution_ready": True,
        "execution_scope": "STOCK_IDENTITY_AND_FRACTION_BINDING_ONLY",
        "execution_hold_reason": "",
    }
    expected_override = {
        "source_row": 180,
        "disposition": "OWNED",
        "status": "HAVE - USER-CONFIRMED NEROLI EO NEAT ONLY",
        "actual_stock_text": (
            "Neroli EO neat / as supplied; prior 10% in DPG stock no longer owned"
        ),
        "can_prepare": "",
    }
    expected_limits = {
        "availability_confirmed": True,
        "stock_fraction_known": True,
        "fraction_basis_known": True,
        "carrier_known": True,
        "stock_solution_density_asserted": False,
        "exact_active_mass_from_raw_volume_authorized": False,
        "chemical_purity_assay_asserted": False,
        "formula_rebase_authorized": False,
        "formula_compounding_authorized": False,
        "safety_asserted": False,
        "stability_asserted": False,
        "sensory_equivalence_asserted": False,
        "release_success_asserted": False,
    }
    if (
        not isinstance(record, Mapping)
        or record.get("record_id") != "INV-USER-20260906-001"
        or record.get("canonical_name") != "Neroli EO"
        or record.get("state") != "OWNED"
        or record.get("category") != "air_floral"
        or record.get("stock") != expected_stock
        or record.get("supersedes_parent_stocks") != [{"source_row": 180, "fraction": 0.1}]
        or record.get("requirement_overrides") != [expected_override]
        or record.get("authority_limits") != expected_limits
        or record.get("effective_date") != "2026-09-06"
        or record.get("source_kind") != "DIRECT_USER_CURRENT_STOCK_CORRECTION"
        or record.get("source_quote") != "I only have neroli EO neat"
    ):
        raise InventoryAuthorityError("2026-09-06 Neroli stock contract drift")

    previous = load_current_user_inventory_overlay(ORRIS_USER_INVENTORY_OVERLAY_PATH)
    inherited = previous["records"]
    if any(
        row.get("canonical_name") == "Neroli EO"
        or any(item["source_row"] == 180 for item in row["requirement_overrides"])
        for row in inherited
    ):
        raise InventoryAuthorityError("2026-09-06 Neroli successor collision")
    origins = {key: dict(value) for key, value in previous["record_origins"].items()}
    origins[record["record_id"]] = {
        "path": "data/governance/inventory_user_authority_overlay_20260906.json",
        "sha256": NEROLI_USER_INVENTORY_OVERLAY_SHA256,
    }
    return {
        **dict(successor),
        "parent": dict(previous["parent"]),
        "base_policy": dict(previous["base_policy"]),
        "head_policy": dict(expected_policy),
        "policy": {**dict(previous["policy"]), **expected_policy},
        "delta_records": records,
        "records": [*inherited, record],
        "record_origins": origins,
    }


def _load_20260907_user_inventory_successor(
    successor: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply a pinned, source-bound delta; never rewrite predecessor records."""
    if successor.get("effective_date") != "2026-09-07" or successor.get("authority") != "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY":
        raise InventoryAuthorityError("2026-09-07 successor metadata drift")
    if successor.get("predecessor") != {
        "path": "data/governance/inventory_user_authority_overlay_20260906.json",
        "normalized_text_sha256": NEROLI_USER_INVENTORY_OVERLAY_SHA256,
    }:
        raise InventoryAuthorityError("2026-09-07 predecessor pin drift")
    source = successor.get("source", {})
    # This immutable predecessor now describes its September 7 inventory snapshot.
    # The September 8 head separately requires an exact binding to live text.
    if (source.get("inventory_text_path") != "inventory.txt"
        or source.get("inventory_text_size_bytes") != 21331
        or source.get("inventory_text_sha256") != "d2c2c405625aa01b2d77069a7907222db40a6156e3971844376100b58c300066"):
        raise InventoryAuthorityError("2026-09-07 historical inventory binding drift")
    previous = load_current_user_inventory_overlay(NEROLI_USER_INVENTORY_OVERLAY_PATH)
    retired = successor.get("superseded_record_ids")
    if retired != ["INV-USER-20260829-001"]:
        raise InventoryAuthorityError("2026-09-07 retired record set drift")
    inherited = [row for row in previous["records"] if row["record_id"] not in retired]
    records = successor.get("records", [])
    if len(records) != 14 or len({r["record_id"] for r in records}) != len(records):
        raise InventoryAuthorityError("2026-09-07 successor record set drift")
    for record in records:
        if record["state"] not in {"OWNED", "NOT_OWNED"}:
            raise InventoryAuthorityError("2026-09-07 invalid stock state")
        if record["state"] == "OWNED":
            stock = record["stock"]
            if not 0 < stock["fraction"] <= 1:
                raise InventoryAuthorityError("2026-09-07 invalid stock fraction")
            if stock["execution_ready"] and stock["fraction"] < 1 and (
                stock["fraction_basis"] == "unspecified" or not stock["carrier"]
            ):
                raise InventoryAuthorityError("2026-09-07 ambiguous executable stock")
    origins = {key: dict(value) for key, value in previous["record_origins"].items()}
    origins.update({row["record_id"]: {
        "path": "data/governance/inventory_user_authority_overlay_20260907.json",
        "sha256": RECONCILED_USER_INVENTORY_OVERLAY_SHA256,
    } for row in records})
    return {
        **dict(successor), "parent": dict(previous["parent"]),
        "base_policy": dict(previous["base_policy"]),
        "policy": {**dict(previous["policy"]), **dict(successor["policy"])},
        "delta_records": records, "records": [*inherited, *records],
        "record_origins": origins,
        "retired_records": [r for r in previous["records"] if r["record_id"] in retired],
    }


def _load_20260908_user_inventory_successor(
    successor: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply four current tinctures and one removal without rebasing old stocks."""
    if (successor.get("effective_date") != "2026-09-08"
        or successor.get("authority") != "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY"
        or successor.get("predecessor") != {
            "path": "data/governance/inventory_user_authority_overlay_20260907.json",
            "normalized_text_sha256": RECONCILED_USER_INVENTORY_OVERLAY_SHA256,
        }):
        raise InventoryAuthorityError("2026-09-08 successor metadata drift")
    source = successor.get("source", {})
    if (source.get("inventory_text_path") != "inventory.txt"
        or source.get("inventory_text_size_bytes") != 22172
        or source.get("inventory_text_sha256") != "0615da4d06418a7c58b9cfa6e387f7529c10dc8f97b9820862aaaf2ee811471b"):
        raise InventoryAuthorityError("2026-09-08 historical inventory binding drift")
    retired = ["INV-USER-20260828-014", "INV-USER-20260828-015", "INV-USER-20260830-005"]
    if successor.get("superseded_record_ids") != retired:
        raise InventoryAuthorityError("2026-09-08 retired record set drift")
    records = successor.get("records", [])
    if len(records) != 5 or [r.get("record_id") for r in records] != [
        f"INV-USER-20260908-00{i}" for i in range(1, 6)
    ]:
        raise InventoryAuthorityError("2026-09-08 successor record set drift")
    expected = [
        ("Turkish Storax Tincture", 0.2, [{"source_row": 236}], 236),
        ("Vietnamese Benzoin Tincture", 0.4, [{"source_row": 222, "fraction": 0.2}, {"source_row": 246}], 246),
        ("Kenyan Myrrh Ethanol Tincture", 0.2, [], None),
        ("Oman Frankincense Ethanol Tincture", 0.33, [], None),
    ]
    for record, (name, fraction, selectors, requirement_row) in zip(records[:4], expected):
        stock = record.get("stock", {})
        overrides = record.get("requirement_overrides", [])
        if (record.get("canonical_name") != name or record.get("state") != "OWNED"
            or record.get("supersedes_parent_stocks") != selectors
            or stock.get("fraction") != fraction
            or stock.get("fraction_basis") != "unspecified"
            or stock.get("carrier") != "ethanol"
            or stock.get("execution_ready") is not False
            or stock.get("execution_hold_reason") != "TINCTURE_PERCENTAGE_BASIS_AND_EXTRACTED_SOLIDS_UNSPECIFIED"
            or [o.get("source_row") for o in overrides] != ([] if requirement_row is None else [requirement_row])
            or any(o.get("disposition") != "OWNED" for o in overrides)):
            raise InventoryAuthorityError("2026-09-08 tincture stock contract drift")
    lavender = records[4]
    if (lavender.get("canonical_name") != "Lavender EO High Altitude"
        or lavender.get("state") != "NOT_OWNED" or lavender.get("stock") is not None
        or lavender.get("supersedes_parent_stocks") != [{"source_row": 156}]
        or len(lavender.get("requirement_overrides", [])) != 1
        or lavender["requirement_overrides"][0].get("source_row") != 156
        or lavender["requirement_overrides"][0].get("disposition") != "GAP"):
        raise InventoryAuthorityError("2026-09-08 lavender removal contract drift")
    previous = load_current_user_inventory_overlay(RECONCILED_USER_INVENTORY_OVERLAY_PATH)
    if {r["record_id"] for r in previous["records"] if r["record_id"] in retired} != set(retired):
        raise InventoryAuthorityError("2026-09-08 predecessor stock selectors drift")
    inherited = [r for r in previous["records"] if r["record_id"] not in retired]
    origins = {key: dict(value) for key, value in previous["record_origins"].items()}
    origins.update({r["record_id"]: {
        "path": "data/governance/inventory_user_authority_overlay_20260908.json",
        "sha256": TINCTURES_USER_INVENTORY_OVERLAY_SHA256,
    } for r in records})
    return {
        **dict(successor), "parent": dict(previous["parent"]),
        "base_policy": dict(previous["base_policy"]),
        "policy": {**dict(previous["policy"]), **dict(successor["policy"])},
        "delta_records": records, "records": [*inherited, *records],
        "record_origins": origins,
        "retired_records": [*previous.get("retired_records", []),
                            *(r for r in previous["records"] if r["record_id"] in retired)],
    }


def _load_20260908_ahsee_inventory_successor(
    successor: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind ten source-declared stocks without changing scientific authority."""
    expected_policy = {
        "predecessor_overlay_immutable": True,
        "preserve_inherited_stock_ids": True,
        "formula_rebase_authorized": False,
        "general_substitution_authorized": False,
        "unknown_metadata_fails_closed": True,
        "bind_only_source_declared_stock_facts": True,
        "stock_solution_density_assumed": False,
        "safety_or_release_asserted": False,
    }
    if (successor.get("effective_date") != "2026-09-08"
        or successor.get("authority") != "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY"
        or successor.get("predecessor") != {
            "path": "data/governance/inventory_user_authority_overlay_20260908.json",
            "normalized_text_sha256": TINCTURES_USER_INVENTORY_OVERLAY_SHA256,
        }
        or successor.get("policy") != expected_policy
        or successor.get("superseded_record_ids") != []):
        raise InventoryAuthorityError("AHSEE stock successor metadata drift")
    source = successor.get("source", {})
    # Immutable AHSEE predecessor retains its reviewed September 8 text receipt.
    # The Romandolide successor independently binds the changed live inventory.
    if (source.get("inventory_text_path") != "inventory.txt"
        or source.get("inventory_text_size_bytes") != 23705
        or source.get("inventory_text_sha256") != "216bd300c709b453d9e9786bf8cfff1c6a62aca65203013b47782891d9f3269c"):
        raise InventoryAuthorityError("AHSEE historical inventory binding drift")
    receipt_path = PROJECT_ROOT / "data/governance/inventory_user_confirmation_20260908_ahsee_stocks.json"
    if (source.get("confirmed_receipt") != receipt_path.relative_to(PROJECT_ROOT).as_posix()
        or source.get("confirmed_receipt_sha256") != AHSEE_STOCK_CONFIRMATION_SHA256
        or not receipt_path.is_file()
        or _file_sha256(receipt_path) != AHSEE_STOCK_CONFIRMATION_SHA256):
        raise InventoryAuthorityError("AHSEE stock confirmation receipt drift")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryAuthorityError("AHSEE stock receipt is unreadable") from exc
    if receipt.get("new_direct_confirmation") != {
        "question": "For the stock check: have you prepared the separate 10% v/v ethanol working stocks of neroli and peppermint, and is your neat PEDMC currently a clear liquid? Please say which are ready.",
        "answer": "yes all",
    }:
        raise InventoryAuthorityError("AHSEE direct confirmation scope drift")
    if receipt.get("identity_confirmation") != {
        "question": "Your inventory currently treats “Givaudan AIMI” and “Alpha Isomethyl Ionone / Methyl Ionone Pure” as one bottle. Do you have one bottle or two separate bottles? This determines which stock the 60 µL row should name.",
        "answer": "i only have gividuan AIMI now",
        "canonical_current_label": "Givaudan AIMI",
        "existing_stock_id": "inventory:user-20260904:a45ff6250b56cec5bbad",
        "new_stock_or_chemical_equivalence_asserted": False,
    }:
        raise InventoryAuthorityError("AHSEE AIMI ownership confirmation drift")
    for entry in receipt.get("source_files", []):
        path = (PROJECT_ROOT / entry["path"]).resolve()
        if (not path.is_relative_to(PROJECT_ROOT.resolve()) or not path.is_file()
            or _file_sha256(path) != entry["sha256"]):
            raise InventoryAuthorityError("AHSEE historical source receipt drift")
    convention = "USER_NOMINAL_VOLUMETRIC_CONVENTION_NOT_MEASURED_STOCK_DENSITY"
    expected = [
        ("Phenyl Ethyl Dimethyl Carbinol", 1.0, "neat", "", None, None,
         "DIRECT_USER_NEAT_CONFIRMATION", ["PEDMC_NEAT_20260907", "PREPARATIONS_AND_PEDMC_PHASE_20260908"]),
        ("Neroli EO", 0.1, "volume_fraction", "ethanol", None, None,
         "DIRECT_USER_PREPARED_STOCK_CONFIRMATION", ["PREPARATIONS_AND_PEDMC_PHASE_20260908"]),
        ("Peppermint EO", 0.1, "volume_fraction", "ethanol", None, None,
         "DIRECT_USER_PREPARED_STOCK_CONFIRMATION", ["PREPARATIONS_AND_PEDMC_PHASE_20260908"]),
        ("Lilyreal ND", 1.0, "neat", "", None, 160,
         "USER_REPORTED_AS_SUPPLIED_PRODUCT_TRANSFER", ["AHS_LILYREAL_USER_TRANSFER_20260907"]),
        ("Nympheal", 1.0, "neat", "", None, 185,
         "USER_REPORTED_NEAT_AS_SUPPLIED_TRANSFER", ["AHS_NYMPHEAL_USER_TRANSFER_20260907"]),
        ("Lavender EO (BONTAUX SAS)", 1.0, "neat", "", None, None,
         "BARE_INVENTORY_ROW_NEAT_CONVENTION_NOT_DIRECT_NEAT_QUOTE", ["BONTAX_CURRENT_INVENTORY_BARE_ROW"]),
        ("Tonka Bean Absolute", 0.1, "volume_fraction", "dpg", 232, 232,
         convention, ["NOMINAL_VOLUME_CONVENTION", "TONKA_CURRENT_INVENTORY_DPG"]),
        ("Vanillin", 0.1, "volume_fraction", "ethanol", 239, 239,
         convention, ["NOMINAL_VOLUME_CONVENTION", "UNKNOWN_CARRIER_ETHANOL_DEFAULT", "VANILLIN_CURRENT_INVENTORY"]),
        ("Aldehyde C10", 0.01, "volume_fraction", "ethanol", 9, 9,
         convention, ["NOMINAL_VOLUME_CONVENTION", "UNKNOWN_CARRIER_ETHANOL_DEFAULT", "C10_CURRENT_INVENTORY"]),
        ("Aldehyde C12 MNA", 0.01, "volume_fraction", "ethanol", 13, 13,
         convention, ["NOMINAL_VOLUME_CONVENTION", "UNKNOWN_CARRIER_ETHANOL_DEFAULT", "C12_CURRENT_INVENTORY"]),
    ]
    limits = {key: False for key in (
        "density_asserted", "assay_asserted", "exact_active_mass_from_raw_volume_authorized",
        "physical_dose_performed", "formula_rebase_authorized", "safety_asserted",
        "stability_asserted", "sensory_equivalence_asserted", "release_authorized",
    )}
    records = successor.get("records", [])
    if len(records) != len(expected):
        raise InventoryAuthorityError("AHSEE exact stock record set drift")
    for index, (record, contract) in enumerate(zip(records, expected), 1):
        name, fraction, basis, carrier, selector_row, requirement_row, authority, evidence = contract
        expected_stock = {
            "fraction": fraction, "fraction_basis": basis, "carrier": carrier,
            "fraction_authority": authority, "density_g_ml": None,
            "execution_ready": True,
            "execution_scope": "DECLARED_RAW_STOCK_TRANSFER_BINDING_ONLY",
            "execution_hold_reason": "",
        }
        if name == "Phenyl Ethyl Dimethyl Carbinol":
            expected_stock["phase"] = "USER_CONFIRMED_CLEAR_LIQUID"
        if name == "Lilyreal ND":
            expected_stock.update({
                "fraction_meaning": "UNDILUTED_SUPPLIED_PRODUCT_NOT_IDENTIFIED_ODORANT_PURITY",
                "material_kind": "OPAQUE_PREBLEND", "constituent_fractions": None,
                "monomolecular_oav_authority": False,
            })
        selectors = [] if selector_row is None else [{"source_row": selector_row, "fraction": fraction}]
        overrides = record.get("requirement_overrides", [])
        expected_rows = [] if requirement_row is None else [requirement_row]
        if (record.get("record_id") != f"INV-USER-20260908-AHSEE-{index:03d}"
            or record.get("canonical_name") != name or record.get("state") != "OWNED"
            or record.get("stock") != expected_stock
            or record.get("supersedes_parent_stocks") != selectors
            or record.get("evidence_refs") != evidence
            or any(ref not in receipt.get("evidence", {}) for ref in evidence)
            or record.get("authority_limits") != limits
            or [r.get("source_row") for r in overrides] != expected_rows
            or any(r.get("disposition") != "OWNED" for r in overrides)):
            raise InventoryAuthorityError(f"AHSEE stock declaration drift: {name}")
    previous = load_current_user_inventory_overlay(TINCTURES_USER_INVENTORY_OVERLAY_PATH)
    origins = {key: dict(value) for key, value in previous["record_origins"].items()}
    origins.update({r["record_id"]: {
        "path": "data/governance/inventory_user_authority_overlay_20260908_ahsee.json",
        "sha256": AHSEE_USER_INVENTORY_OVERLAY_SHA256,
    } for r in records})
    return {
        **dict(successor), "parent": dict(previous["parent"]),
        "base_policy": dict(previous["base_policy"]),
        "policy": {**dict(previous["policy"]), **expected_policy},
        "delta_records": records, "records": [*previous["records"], *records],
        "record_origins": origins,
        "retired_records": list(previous.get("retired_records", [])),
    }


def _load_20260908_romandolide_inventory_successor(
    successor: Mapping[str, Any],
    *,
    require_live_inventory_binding: bool = True,
) -> dict[str, Any]:
    """Retire only the source-confirmed depleted Romandolide physical stock."""
    expected_policy = {
        "predecessor_overlay_immutable": True,
        "preserve_inherited_stock_ids": True,
        "formula_rebase_authorized": False,
        "general_substitution_authorized": False,
        "unknown_metadata_fails_closed": True,
        "bind_only_source_declared_stock_facts": True,
        "stock_solution_density_assumed": False,
        "safety_or_release_asserted": False,
    }
    if (successor.get("schema_version") != "perfume_chem_user_inventory_authority_successor_overlay_v7"
        or successor.get("effective_date") != "2026-09-08"
        or successor.get("authority") != "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY"
        or successor.get("predecessor") != {
            "path": "data/governance/inventory_user_authority_overlay_20260908_ahsee.json",
            "normalized_text_sha256": AHSEE_USER_INVENTORY_OVERLAY_SHA256,
        }
        or successor.get("policy") != expected_policy
        or successor.get("superseded_record_ids") != []):
        raise InventoryAuthorityError("Romandolide depletion successor metadata drift")
    source = successor.get("source", {})
    if (
        not isinstance(source, Mapping)
        or source.get("inventory_text_path") != "inventory.txt"
        or (
            require_live_inventory_binding
            and (
                source.get("inventory_text_size_bytes")
                != len(_normalized_text_bytes(INVENTORY_PATH))
                or source.get("inventory_text_sha256")
                != _normalized_text_sha256(INVENTORY_PATH)
            )
        )
    ):
        raise InventoryAuthorityError("Romandolide successor is not bound to live inventory text")
    receipt_path = PROJECT_ROOT / "data/governance/inventory_user_confirmation_20260908_romandolide_depleted.json"
    if (source.get("confirmed_receipt") != receipt_path.relative_to(PROJECT_ROOT).as_posix()
        or source.get("confirmed_receipt_sha256") != ROMANDOLIDE_DEPLETION_CONFIRMATION_SHA256
        or not receipt_path.is_file()
        or _file_sha256(receipt_path) != ROMANDOLIDE_DEPLETION_CONFIRMATION_SHA256):
        raise InventoryAuthorityError("Romandolide depletion confirmation receipt drift")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryAuthorityError("Romandolide depletion receipt is unreadable") from exc
    if receipt != {
        "schema_version": "perfume_chem_direct_stock_depletion_receipt_v1",
        "effective_date": "2026-09-08",
        "source_kind": "DIRECT_USER_MESSAGE",
        "verbatim_user_message": "im out of romandolide",
        "canonical_name": "Romandolide",
        "disposition": "DEPLETED",
        "retired_stock_id": "inventory:v5:caba57d5d5c78d414d5c",
        "retired_source_row": 211,
        "retired_stock_fraction": 1.0,
        "prior_ownership_is_historical": True,
        "authority_limits": {
            "new_stock_or_substitute_confirmed": False,
            "density_or_assay_asserted": False,
            "physical_compounding_performed": False,
            "safety_or_release_asserted": False,
        },
    }:
        raise InventoryAuthorityError("Romandolide direct depletion confirmation scope drift")
    expected_record = {
        "record_id": "INV-USER-20260908-ROMANDOLIDE-001",
        "canonical_name": "Romandolide",
        "aliases": [],
        "state": "NOT_OWNED",
        "category": "musk",
        "stock": None,
        "supersedes_parent_stocks": [{"source_row": 211, "fraction": 1.0}],
        "requirement_overrides": [{
            "source_row": 211,
            "disposition": "GAP",
            "status": "DEPLETED - USER CONFIRMED 2026-09-08",
            "actual_stock_text": "No Romandolide remains",
            "can_prepare": "",
        }],
        "effective_date": "2026-09-08",
        "source_kind": "DIRECT_USER_DEPLETION_CONFIRMATION",
        "evidence_refs": ["ROMANDOLIDE_DEPLETED_20260908"],
        "authority_limits": {
            "formula_rebase_authorized": False,
            "substitute_identity_or_stock_asserted": False,
            "safety_or_release_asserted": False,
        },
    }
    records = successor.get("records", [])
    if records != [expected_record]:
        raise InventoryAuthorityError("Romandolide exact depletion record drift")
    previous = load_current_user_inventory_overlay(AHSEE_USER_INVENTORY_OVERLAY_PATH)
    origins = {key: dict(value) for key, value in previous["record_origins"].items()}
    origins[expected_record["record_id"]] = {
        "path": "data/governance/inventory_user_authority_overlay_20260908_romandolide.json",
        "sha256": ROMANDOLIDE_USER_INVENTORY_OVERLAY_SHA256,
    }
    return {
        **dict(successor), "parent": dict(previous["parent"]),
        "base_policy": dict(previous["base_policy"]),
        "policy": {**dict(previous["policy"]), **expected_policy},
        "delta_records": records, "records": [*previous["records"], *records],
        "record_origins": origins,
        "retired_records": list(previous.get("retired_records", [])),
    }


def _load_20260910_florhydral_inventory_successor(
    successor: Mapping[str, Any],
    *,
    require_live_inventory_binding: bool = True,
) -> dict[str, Any]:
    """Add only the user-confirmed neat Simple Scents DIY Florhydral stock."""
    expected_policy = {
        "predecessor_overlay_immutable": True,
        "preserve_inherited_stock_ids": True,
        "formula_rebase_authorized": False,
        "general_substitution_authorized": False,
        "unknown_metadata_fails_closed": True,
        "bind_only_source_declared_stock_facts": True,
        "stock_solution_density_assumed": False,
        "safety_or_release_asserted": False,
    }
    if (
        successor.get("schema_version")
        != "perfume_chem_user_inventory_authority_successor_overlay_v8"
        or successor.get("effective_date") != "2026-09-10"
        or successor.get("authority") != "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY"
        or successor.get("predecessor")
        != {
            "path": "data/governance/inventory_user_authority_overlay_20260908_romandolide.json",
            "normalized_text_sha256": ROMANDOLIDE_USER_INVENTORY_OVERLAY_SHA256,
        }
        or successor.get("policy") != expected_policy
        or successor.get("superseded_record_ids") != []
    ):
        raise InventoryAuthorityError("Florhydral stock successor metadata drift")

    source = successor.get("source", {})
    if (
        not isinstance(source, Mapping)
        or source.get("inventory_text_path") != "inventory.txt"
        or (
            require_live_inventory_binding
            and (
                source.get("inventory_text_size_bytes")
                != len(_normalized_text_bytes(INVENTORY_PATH))
                or source.get("inventory_text_sha256")
                != _normalized_text_sha256(INVENTORY_PATH)
            )
        )
    ):
        raise InventoryAuthorityError("Florhydral successor is not bound to live inventory text")

    receipt_path = (
        PROJECT_ROOT
        / "data/governance/inventory_user_confirmation_20260910_florhydral.json"
    )
    if (
        source.get("confirmed_receipt") != receipt_path.relative_to(PROJECT_ROOT).as_posix()
        or source.get("confirmed_receipt_sha256")
        != FLORHYDRAL_ADDITION_CONFIRMATION_SHA256
        or not receipt_path.is_file()
        or _file_sha256(receipt_path) != FLORHYDRAL_ADDITION_CONFIRMATION_SHA256
    ):
        raise InventoryAuthorityError("Florhydral addition confirmation receipt drift")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryAuthorityError("Florhydral addition receipt is unreadable") from exc

    expected_receipt = {
        "schema_version": "perfume_chem_direct_stock_addition_receipt_v1",
        "effective_date": "2026-09-10",
        "source_kind": "DIRECT_USER_MESSAGES",
        "verbatim_user_messages": [
            "Also, add Florhydral to inventory",
            "it is from simplescentsdiy",
            "neat",
        ],
        "canonical_name": "Florhydral",
        "disposition": "OWNED",
        "supplier": {
            "name": "Simple Scents DIY",
            "sku": "8F3094005319",
            "package": "5 mL",
            "product_url": "https://www.simplescentsdiy.com/product/35447-34947/florhydral",
        },
        "stock": {
            "fraction": 1.0,
            "fraction_basis": "neat",
            "carrier": "",
            "stock_form_authority": "DIRECT_USER_CONFIRMATION",
        },
        "authority_limits": {
            "availability_confirmed": True,
            "supplier_confirmed": True,
            "stock_form_confirmed": True,
            "analytical_purity_asserted": False,
            "lot_assay_asserted": False,
            "density_asserted": False,
            "formula_use_authorized": False,
            "historical_formula_rebase_authorized": False,
            "physical_compounding_performed": False,
            "safety_or_release_asserted": False,
        },
    }
    if receipt != expected_receipt:
        raise InventoryAuthorityError("Florhydral direct addition confirmation scope drift")

    expected_record = {
        "record_id": "INV-USER-20260910-FLORHYDRAL-001",
        "canonical_name": "Florhydral",
        "aliases": ["Florhydral(TM)"],
        "state": "OWNED",
        "category": "floral materials",
        "stock": {
            "fraction": 1.0,
            "fraction_basis": "neat",
            "carrier": "",
            "fraction_authority": "DIRECT_USER_CONFIRMATION",
            "execution_ready": True,
        },
        "supersedes_parent_stocks": [],
        "requirement_overrides": [],
        "effective_date": "2026-09-10",
        "source_kind": "DIRECT_USER_CURRENT_STOCK_ADDITION_WITH_SUPPLIER_IDENTITY",
        "source_quotes": [
            "Also, add Florhydral to inventory",
            "it is from simplescentsdiy",
            "neat",
        ],
        "supplier": {
            "name": "Simple Scents DIY",
            "sku": "8F3094005319",
            "package": "5 mL",
            "product_url": "https://www.simplescentsdiy.com/product/35447-34947/florhydral",
        },
        "evidence_refs": ["FLORHYDRAL_CURRENT_STOCK_20260910"],
        "authority_limits": {
            "availability_confirmed": True,
            "supplier_confirmed": True,
            "stock_form_confirmed": True,
            "formulation_selection_ready": True,
            "analytical_purity_asserted": False,
            "lot_assay_asserted": False,
            "density_asserted": False,
            "specific_formula_addition_directed": False,
            "historical_formula_rebase_authorized": False,
            "physical_compounding_performed": False,
            "safety_or_release_asserted": False,
        },
    }
    records = successor.get("records", [])
    if records != [expected_record]:
        raise InventoryAuthorityError("Florhydral exact addition record drift")

    if (
        _normalized_text_sha256(ROMANDOLIDE_USER_INVENTORY_OVERLAY_PATH)
        != ROMANDOLIDE_USER_INVENTORY_OVERLAY_SHA256
    ):
        raise InventoryAuthorityError("Florhydral predecessor overlay hash drift")
    try:
        predecessor_payload = json.loads(
            ROMANDOLIDE_USER_INVENTORY_OVERLAY_PATH.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryAuthorityError("Florhydral predecessor overlay is unreadable") from exc
    previous = _load_20260908_romandolide_inventory_successor(
        predecessor_payload,
        require_live_inventory_binding=False,
    )
    origins = {key: dict(value) for key, value in previous["record_origins"].items()}
    origins[expected_record["record_id"]] = {
        "path": "data/governance/inventory_user_authority_overlay_20260910_florhydral.json",
        "sha256": FLORHYDRAL_USER_INVENTORY_OVERLAY_SHA256,
    }
    return {
        **dict(successor),
        "parent": dict(previous["parent"]),
        "base_policy": dict(previous["base_policy"]),
        "policy": {**dict(previous["policy"]), **expected_policy},
        "delta_records": records,
        "records": [*previous["records"], *records],
        "record_origins": origins,
        "retired_records": list(previous.get("retired_records", [])),
    }


def _load_20260910_romandolide_restock_inventory_successor(
    successor: Mapping[str, Any],
    *,
    require_live_inventory_binding: bool = True,
) -> dict[str, Any]:
    """Restore Romandolide availability without inheriting the old bottle form."""
    expected_policy = {
        "predecessor_overlay_immutable": True,
        "preserve_inherited_stock_ids": True,
        "formula_rebase_authorized": False,
        "general_substitution_authorized": False,
        "unknown_metadata_fails_closed": True,
        "bind_only_source_declared_stock_facts": True,
        "stock_solution_density_assumed": False,
        "safety_or_release_asserted": False,
    }
    expected_predecessor = {
        "path": "data/governance/inventory_user_authority_overlay_20260910_florhydral.json",
        "normalized_text_sha256": FLORHYDRAL_USER_INVENTORY_OVERLAY_SHA256,
    }
    if (
        successor.get("schema_version")
        != "perfume_chem_user_inventory_authority_successor_overlay_v9"
        or successor.get("effective_date") != "2026-09-10"
        or successor.get("authority") != "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY"
        or successor.get("predecessor") != expected_predecessor
        or successor.get("policy") != expected_policy
        or successor.get("superseded_record_ids")
        != ["INV-USER-20260908-ROMANDOLIDE-001"]
    ):
        raise InventoryAuthorityError("Romandolide restock successor metadata drift")

    source = successor.get("source", {})
    if (
        not isinstance(source, Mapping)
        or source.get("inventory_text_path") != "inventory.txt"
        or (
            require_live_inventory_binding
            and (
                source.get("inventory_text_size_bytes")
                != len(_normalized_text_bytes(INVENTORY_PATH))
                or source.get("inventory_text_sha256")
                != _normalized_text_sha256(INVENTORY_PATH)
            )
        )
    ):
        raise InventoryAuthorityError("Romandolide restock is not bound to live inventory text")

    receipt_path = (
        PROJECT_ROOT
        / "data/governance/inventory_user_confirmation_20260910_romandolide_restocked.json"
    )
    if (
        source.get("confirmed_receipt") != receipt_path.relative_to(PROJECT_ROOT).as_posix()
        or source.get("confirmed_receipt_sha256")
        != ROMANDOLIDE_RESTOCK_CONFIRMATION_SHA256
        or not receipt_path.is_file()
        or _file_sha256(receipt_path) != ROMANDOLIDE_RESTOCK_CONFIRMATION_SHA256
    ):
        raise InventoryAuthorityError("Romandolide restock confirmation receipt drift")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryAuthorityError("Romandolide restock receipt is unreadable") from exc
    if (
        receipt.get("verbatim_user_message") != "romandolide is stocked again"
        or receipt.get("canonical_name") != "Romandolide"
        or receipt.get("disposition") != "OWNED"
        or receipt.get("stock")
        != {
            "fraction": None,
            "fraction_basis": "unspecified",
            "carrier": "",
            "stock_form_authority": "NOT_STATED_FOR_RESTOCKED_BOTTLE",
        }
        or receipt.get("authority_limits", {}).get("quantitative_dosing_ready")
        is not False
        or receipt.get("authority_limits", {}).get("prior_neat_stock_form_inherited")
        is not False
    ):
        raise InventoryAuthorityError("Romandolide restock confirmation scope drift")

    records = successor.get("records", [])
    if len(records) != 1 or not isinstance(records[0], Mapping):
        raise InventoryAuthorityError("Romandolide restock record count drift")
    record = records[0]
    expected_stock = {
        "fraction": None,
        "fraction_basis": "unspecified",
        "carrier": "",
        "fraction_authority": "NOT_STATED_FOR_RESTOCKED_BOTTLE",
        "execution_ready": False,
        "execution_scope": "AVAILABILITY_ONLY",
        "execution_hold_reason": "RESTOCKED_BOTTLE_STRENGTH_AND_CARRIER_NOT_STATED",
    }
    expected_override = {
        "source_row": 211,
        "disposition": "OWNED",
        "status": "HAVE - RESTOCKED; STOCK FORM UNCONFIRMED",
        "actual_stock_text": (
            "Romandolide is stocked again; new bottle strength and carrier were not stated"
        ),
        "can_prepare": "",
    }
    if (
        record.get("record_id") != "INV-USER-20260910-ROMANDOLIDE-RESTOCK-001"
        or record.get("canonical_name") != "Romandolide"
        or record.get("aliases") != []
        or record.get("state") != "OWNED"
        or record.get("category") != "musk"
        or record.get("stock") != expected_stock
        or record.get("supersedes_parent_stocks")
        != [{"source_row": 211, "fraction": 1.0}]
        or record.get("requirement_overrides") != [expected_override]
        or record.get("source_quote") != "romandolide is stocked again"
        or record.get("evidence_refs") != ["ROMANDOLIDE_RESTOCKED_20260910"]
        or record.get("authority_limits", {}).get("quantitative_dosing_ready")
        is not False
        or record.get("authority_limits", {}).get("prior_neat_stock_form_inherited")
        is not False
    ):
        raise InventoryAuthorityError("Romandolide exact restock record drift")

    if (
        _normalized_text_sha256(FLORHYDRAL_USER_INVENTORY_OVERLAY_PATH)
        != FLORHYDRAL_USER_INVENTORY_OVERLAY_SHA256
    ):
        raise InventoryAuthorityError("Romandolide restock predecessor overlay hash drift")
    try:
        predecessor_payload = json.loads(
            FLORHYDRAL_USER_INVENTORY_OVERLAY_PATH.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryAuthorityError(
            "Romandolide restock predecessor overlay is unreadable"
        ) from exc
    previous = _load_20260910_florhydral_inventory_successor(
        predecessor_payload,
        require_live_inventory_binding=False,
    )
    retired_ids = set(successor["superseded_record_ids"])
    inherited = [
        row for row in previous["records"] if row["record_id"] not in retired_ids
    ]
    origins = {
        key: dict(value)
        for key, value in previous["record_origins"].items()
        if key not in retired_ids
    }
    origins[str(record["record_id"])] = {
        "path": "data/governance/inventory_user_authority_overlay_20260910_romandolide_restocked.json",
        "sha256": ROMANDOLIDE_RESTOCK_USER_INVENTORY_OVERLAY_SHA256,
    }
    return {
        **dict(successor),
        "parent": dict(previous["parent"]),
        "base_policy": dict(previous["base_policy"]),
        "policy": {**dict(previous["policy"]), **expected_policy},
        "delta_records": records,
        "records": [*inherited, *records],
        "record_origins": origins,
        "retired_records": [
            *previous.get("retired_records", []),
            *(row for row in previous["records"] if row["record_id"] in retired_ids),
        ],
    }


def _load_20260910_stock_clarification_inventory_successor(
    successor: Mapping[str, Any],
    *,
    require_live_inventory_binding: bool = True,
) -> dict[str, Any]:
    """Bind only the stock facts the user clarified on 2026-09-10."""

    expected_policy = {
        "predecessor_overlay_immutable": True,
        "preserve_inherited_stock_ids": True,
        "formula_rebase_authorized": False,
        "general_substitution_authorized": False,
        "unknown_metadata_fails_closed": True,
        "bind_only_source_declared_stock_facts": True,
        "stock_solution_density_assumed": False,
        "safety_or_release_asserted": False,
    }
    expected_superseded = [
        "INV-USER-20260904-004",
        "INV-USER-20260908-001",
        "INV-USER-20260908-002",
        "INV-USER-20260908-003",
        "INV-USER-20260908-004",
    ]
    if (
        successor.get("schema_version")
        != "perfume_chem_user_inventory_authority_successor_overlay_v10"
        or successor.get("effective_date") != "2026-09-10"
        or successor.get("authority") != "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY"
        or successor.get("predecessor")
        != {
            "path": "data/governance/inventory_user_authority_overlay_20260910_romandolide_restocked.json",
            "normalized_text_sha256": ROMANDOLIDE_RESTOCK_USER_INVENTORY_OVERLAY_SHA256,
        }
        or successor.get("policy") != expected_policy
        or successor.get("superseded_record_ids") != expected_superseded
    ):
        raise InventoryAuthorityError("Stock clarification successor metadata drift")

    source = successor.get("source", {})
    if (
        not isinstance(source, Mapping)
        or source.get("inventory_text_path") != "inventory.txt"
        or (
            require_live_inventory_binding
            and (
                source.get("inventory_text_size_bytes")
                != len(_normalized_text_bytes(INVENTORY_PATH))
                or source.get("inventory_text_sha256")
                != _normalized_text_sha256(INVENTORY_PATH)
            )
        )
    ):
        raise InventoryAuthorityError(
            "Stock clarification successor is not bound to live inventory text"
        )

    confirmation_path = (
        PROJECT_ROOT
        / "data/governance/inventory_user_confirmation_20260910_stock_clarifications.json"
    )
    supplier_path = (
        PROJECT_ROOT
        / "data/governance/inventory_supplier_product_resolution_20260910_liffarome_methyl_laitone.json"
    )
    receipt_specs = (
        (
            confirmation_path,
            "confirmed_receipt",
            "confirmed_receipt_sha256",
            STOCK_CLARIFICATIONS_CONFIRMATION_SHA256,
        ),
        (
            supplier_path,
            "supplier_resolution_receipt",
            "supplier_resolution_receipt_sha256",
            SUPPLIER_PRODUCT_RESOLUTION_SHA256,
        ),
    )
    receipts: list[dict[str, Any]] = []
    for receipt_path, path_key, sha_key, expected_sha in receipt_specs:
        if (
            source.get(path_key) != receipt_path.relative_to(PROJECT_ROOT).as_posix()
            or source.get(sha_key) != expected_sha
            or not receipt_path.is_file()
            or _file_sha256(receipt_path) != expected_sha
        ):
            raise InventoryAuthorityError(f"{path_key} receipt drift")
        try:
            receipt_payload = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise InventoryAuthorityError(f"{path_key} receipt is unreadable") from exc
        if not isinstance(receipt_payload, dict):
            raise InventoryAuthorityError(f"{path_key} receipt shape drift")
        receipts.append(receipt_payload)

    confirmation, supplier_resolution = receipts
    confirmation_limits = confirmation.get("authority_limits", {})
    if (
        confirmation.get("schema_version")
        != "perfume_chem_direct_stock_clarifications_v1"
        or confirmation.get("effective_date") != "2026-09-10"
        or confirmation.get("source_kind") != "DIRECT_USER_MESSAGES"
        or confirmation_limits.get("working_stock_fraction_basis_and_carrier_confirmed")
        is not True
        or confirmation_limits.get("tincture_final_dissolved_solids_fraction_confirmed")
        is not False
        or confirmation_limits.get("oman_frankincense_species_confirmed") is not False
        or confirmation_limits.get("haitian_vetiver_origin_confirmed") is not True
        or confirmation_limits.get("formula_rebase_authorized") is not False
    ):
        raise InventoryAuthorityError("Stock clarification confirmation scope drift")

    supplier_limits = supplier_resolution.get("authority_limits", {})
    products = {
        str(row.get("inventory_name")): row
        for row in supplier_resolution.get("products", [])
        if isinstance(row, Mapping)
    }
    if (
        supplier_resolution.get("schema_version")
        != "perfume_chem_supplier_product_identity_resolution_v1"
        or supplier_resolution.get("supplier") != "PerfumersWorld"
        or set(products) != {"Liffarome", "Methyl Laitone"}
        or products["Liffarome"].get("sku") != "4GI24147"
        or products["Liffarome"].get("active_cas") != "67633-96-9"
        or products["Liffarome"].get("user_stock_binding", {}).get("execution_ready")
        is not False
        or products["Methyl Laitone"].get("sku") != "5VD10871"
        or products["Methyl Laitone"].get("supplier_product_form") != "10% in DPG"
        or products["Methyl Laitone"].get("user_stock_binding", {}).get("execution_ready")
        is not False
        or supplier_limits.get("physical_compounding_performed") is not False
        or supplier_limits.get("safety_or_release_asserted") is not False
    ):
        raise InventoryAuthorityError("Supplier product resolution scope drift")

    records = successor.get("records", [])
    if not isinstance(records, list) or len(records) != 11:
        raise InventoryAuthorityError("Stock clarification record count drift")
    records_sha = hashlib.sha256(
        json.dumps(
            records,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    if records_sha != STOCK_CLARIFICATION_RECORDS_SHA256:
        raise InventoryAuthorityError("Stock clarification exact records drift")
    records_by_id = {
        str(record.get("record_id")): record
        for record in records
        if isinstance(record, Mapping)
    }
    expected_ids = {
        f"INV-USER-20260910-CLARIFY-{index:03d}" for index in range(1, 12)
    }
    if set(records_by_id) != expected_ids:
        raise InventoryAuthorityError("Stock clarification record identifiers drift")

    volume_stocks = {
        "INV-USER-20260910-CLARIFY-001": (
            "Anisaldehyde 10%", 0.1, "ethanol", 32
        ),
        "INV-USER-20260910-CLARIFY-002": (
            "Ethyl Maltol 1%", 0.01, "ethanol", 266
        ),
        "INV-USER-20260910-CLARIFY-003": (
            "Hexyl Acetate 1%", 0.01, "dpg", 274
        ),
        "INV-USER-20260910-CLARIFY-004": (
            "Helional 10%", 0.1, "ethanol", 130
        ),
    }
    for record_id, (name, fraction, carrier, source_row) in volume_stocks.items():
        record = records_by_id[record_id]
        stock = record.get("stock", {})
        if (
            record.get("canonical_name") != name
            or stock.get("fraction") != fraction
            or stock.get("fraction_basis") != "volume_fraction"
            or stock.get("carrier") != carrier
            or stock.get("execution_ready") is not True
            or record.get("supersedes_parent_stocks")
            != [{"source_row": source_row, "fraction": fraction}]
            or not record.get("requirement_overrides")
            or record["requirement_overrides"][0].get("actual_stock_text") is None
        ):
            raise InventoryAuthorityError(f"{name} exact stock record drift")

    tinctures = {
        "INV-USER-20260910-CLARIFY-005": ("Turkish Storax Tincture", 0.2),
        "INV-USER-20260910-CLARIFY-006": ("Vietnamese Benzoin Tincture", 0.4),
        "INV-USER-20260910-CLARIFY-007": ("Kenyan Myrrh Ethanol Tincture", 0.2),
        "INV-USER-20260910-CLARIFY-008": ("Oman Frankincense Ethanol Tincture", 0.33),
    }
    for record_id, (name, fraction) in tinctures.items():
        record = records_by_id[record_id]
        stock = record.get("stock", {})
        if (
            record.get("canonical_name") != name
            or stock.get("fraction") != fraction
            or stock.get("fraction_basis") != "mass_fraction_starting_charge"
            or stock.get("carrier") != "ethanol"
            or stock.get("execution_ready") is not False
            or stock.get("execution_hold_reason")
            != "FILTERED_TINCTURE_FINAL_DISSOLVED_FRACTION_UNKNOWN"
        ):
            raise InventoryAuthorityError(f"{name} exact tincture record drift")

    haitian = records_by_id["INV-USER-20260910-CLARIFY-009"]
    if (
        haitian.get("canonical_name") != "Vetiver EO (Haiti)"
        or haitian.get("stock")
        != {
            "fraction": 1.0,
            "fraction_basis": "neat",
            "carrier": "",
            "fraction_authority": "DIRECT_USER_ORIGIN_CORRECTION",
            "execution_ready": True,
            "execution_scope": "RAW_STOCK_VOLUME_TRANSFER_ONLY",
        }
        or haitian.get("supersedes_parent_stocks")
        != [{"source_row": 245, "fraction": 1.0}]
    ):
        raise InventoryAuthorityError("Haitian vetiver exact stock record drift")

    coriander = records_by_id["INV-USER-20260910-CLARIFY-010"]
    if (
        coriander.get("canonical_name") != "Coriander Essential Oil"
        or coriander.get("stock")
        != {
            "fraction": 1.0,
            "fraction_basis": "neat",
            "carrier": "",
            "fraction_authority": "DIRECT_USER_SUPPLIER_PRODUCT_CORRECTION",
            "execution_ready": True,
            "execution_scope": "RAW_STOCK_VOLUME_TRANSFER_ONLY",
        }
        or coriander.get("supersedes_parent_stocks")
        != [{"source_row": 83, "fraction": 1.0}]
    ):
        raise InventoryAuthorityError("Coriander exact supplier stock record drift")

    cinnamyl_alcohol = records_by_id["INV-USER-20260910-CLARIFY-011"]
    if (
        cinnamyl_alcohol.get("canonical_name") != "Cinnamyl Alcohol"
        or cinnamyl_alcohol.get("stock")
        != {
            "fraction": 0.5,
            "fraction_basis": "mass_fraction",
            "carrier": "dpg",
            "fraction_authority": "DIRECT_USER_CONFIRMATION",
            "execution_ready": True,
            "execution_scope": "RAW_STOCK_VOLUME_TRANSFER_ONLY",
            "execution_limit": "EXACT_ACTIVE_MASS_FROM_VOLUME_REQUIRES_STOCK_DENSITY",
        }
        or cinnamyl_alcohol.get("supersedes_parent_stocks") != []
        or cinnamyl_alcohol.get("requirement_overrides") != []
    ):
        raise InventoryAuthorityError("Cinnamyl Alcohol exact stock record drift")

    if (
        _normalized_text_sha256(ROMANDOLIDE_RESTOCK_USER_INVENTORY_OVERLAY_PATH)
        != ROMANDOLIDE_RESTOCK_USER_INVENTORY_OVERLAY_SHA256
    ):
        raise InventoryAuthorityError("Stock clarification predecessor overlay hash drift")
    try:
        predecessor_payload = json.loads(
            ROMANDOLIDE_RESTOCK_USER_INVENTORY_OVERLAY_PATH.read_text(
                encoding="utf-8"
            )
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryAuthorityError(
            "Stock clarification predecessor overlay is unreadable"
        ) from exc
    previous = _load_20260910_romandolide_restock_inventory_successor(
        predecessor_payload,
        require_live_inventory_binding=False,
    )
    retired_ids = set(expected_superseded)
    inherited = [
        record for record in previous["records"] if record["record_id"] not in retired_ids
    ]
    origins = {
        key: dict(value)
        for key, value in previous["record_origins"].items()
        if key not in retired_ids
    }
    for record in records:
        origins[str(record["record_id"])] = {
            "path": "data/governance/inventory_user_authority_overlay_20260910_stock_clarifications.json",
            "sha256": STOCK_CLARIFICATIONS_USER_INVENTORY_OVERLAY_SHA256,
        }
    return {
        **dict(successor),
        "parent": dict(previous["parent"]),
        "base_policy": dict(previous["base_policy"]),
        "policy": {**dict(previous["policy"]), **expected_policy},
        "delta_records": records,
        "records": [*inherited, *records],
        "record_origins": origins,
        "retired_records": [
            *previous.get("retired_records", []),
            *(record for record in previous["records"] if record["record_id"] in retired_ids),
        ],
    }


def _load_20260915_pink_pepper_inventory_successor(
    successor: Mapping[str, Any],
    *,
    require_live_inventory_binding: bool = True,
) -> dict[str, Any]:
    """Add the user-confirmed neat Schinus molle EO without closing the CO2 gap."""

    expected_policy = {
        "predecessor_overlay_immutable": True,
        "preserve_inherited_stock_ids": True,
        "formula_rebase_authorized": False,
        "general_substitution_authorized": False,
        "unknown_metadata_fails_closed": True,
        "bind_only_source_declared_stock_facts": True,
        "stock_solution_density_assumed": False,
        "safety_or_release_asserted": False,
    }
    expected_predecessor = {
        "path": "data/governance/inventory_user_authority_overlay_20260910_stock_clarifications.json",
        "normalized_text_sha256": STOCK_CLARIFICATIONS_USER_INVENTORY_OVERLAY_SHA256,
    }
    if (
        successor.get("schema_version")
        != "perfume_chem_user_inventory_authority_successor_overlay_v11"
        or successor.get("effective_date") != "2026-09-15"
        or successor.get("authority") != "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY"
        or successor.get("predecessor") != expected_predecessor
        or successor.get("policy") != expected_policy
        or successor.get("superseded_record_ids") != []
    ):
        raise InventoryAuthorityError("Pink Pepper successor metadata drift")

    source = successor.get("source", {})
    expected_inventory_size = 25316
    expected_inventory_sha = (
        "575f0b2832683341bb5759720f2a1a566eb20bd23cd62cf9e1cc08b4edf0f327"
    )
    confirmation_path = (
        PROJECT_ROOT
        / "data/governance/inventory_user_confirmation_20260915_pink_pepper.json"
    )
    if (
        not isinstance(source, Mapping)
        or source.get("inventory_text_path") != "inventory.txt"
        or source.get("inventory_text_size_bytes") != expected_inventory_size
        or source.get("inventory_text_sha256") != expected_inventory_sha
        or source.get("confirmed_receipt")
        != confirmation_path.relative_to(PROJECT_ROOT).as_posix()
        or source.get("confirmed_receipt_sha256") != PINK_PEPPER_CONFIRMATION_SHA256
    ):
        raise InventoryAuthorityError("Pink Pepper successor source drift")
    if require_live_inventory_binding and (
        len(_normalized_text_bytes(INVENTORY_PATH)) != expected_inventory_size
        or _normalized_text_sha256(INVENTORY_PATH) != expected_inventory_sha
    ):
        raise InventoryAuthorityError(
            "Pink Pepper successor is not bound to live inventory text"
        )
    if (
        not confirmation_path.is_file()
        or _file_sha256(confirmation_path) != PINK_PEPPER_CONFIRMATION_SHA256
    ):
        raise InventoryAuthorityError("Pink Pepper confirmation receipt drift")
    try:
        confirmation = json.loads(confirmation_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryAuthorityError(
            "Pink Pepper confirmation receipt is unreadable"
        ) from exc
    limits = confirmation.get("authority_limits", {})
    supplier = confirmation.get("supplier_product", {})
    binding = confirmation.get("stock_binding", {})
    if (
        confirmation.get("schema_version")
        != "perfume_chem_direct_pink_pepper_stock_confirmation_v1"
        or confirmation.get("effective_date") != "2026-09-03"
        or confirmation.get("recorded_date") != "2026-09-15"
        or confirmation.get("source_thread_id")
        != "01a06205-e164-7620-9774-836590cecea0"
        or supplier.get("supplier") != "Aroma&More"
        or supplier.get("product_name") != "Pink Pepper Essential oil, Peru"
        or supplier.get("reference") != "PinPP0324P"
        or supplier.get("botanical_name") != "Schinus molle"
        or supplier.get("origin") != "Peru"
        or binding.get("canonical_name") != "Pink Pepper EO"
        or binding.get("fraction") != 1.0
        or binding.get("fraction_basis") != "neat"
        or binding.get("carrier") != ""
        or binding.get("execution_ready") is not True
        or limits.get("physical_stock_ownership_confirmed") is not True
        or limits.get("stock_strength_confirmed") is not True
        or limits.get("supplier_product_identity_confirmed") is not True
        or limits.get("supplier_lot_gc_ms_or_gc_o_confirmed") is not False
        or limits.get("density_confirmed") is not False
        or limits.get("co2_extract_ownership_confirmed") is not False
        or limits.get("formula_rebase_authorized") is not False
        or limits.get("safety_or_release_asserted") is not False
    ):
        raise InventoryAuthorityError("Pink Pepper confirmation scope drift")

    expected_record = {
        "record_id": "INV-USER-20260903-001",
        "canonical_name": "Pink Pepper EO",
        "aliases": [
            "Pink Pepper EO (Schinus molle)",
            "Pink Pepper EO (Schinus molle; neat / as supplied)",
            "Schinus molle EO",
        ],
        "state": "OWNED",
        "category": "spice",
        "stock": {
            "fraction": 1.0,
            "fraction_basis": "neat",
            "carrier": "",
            "fraction_authority": "DIRECT_USER_CONFIRMATION",
            "execution_ready": True,
            "execution_scope": "RAW_STOCK_VOLUME_TRANSFER_ONLY",
        },
        "supersedes_parent_stocks": [],
        "requirement_overrides": [],
        "effective_date": "2026-09-03",
        "source_kind": "DIRECT_USER_CURRENT_STOCK_ADDITION_WITH_SUPPLIER_IDENTITY",
    }
    records = successor.get("records", [])
    if records != [expected_record]:
        raise InventoryAuthorityError("Pink Pepper exact stock record drift")

    if (
        _normalized_text_sha256(STOCK_CLARIFICATIONS_USER_INVENTORY_OVERLAY_PATH)
        != STOCK_CLARIFICATIONS_USER_INVENTORY_OVERLAY_SHA256
    ):
        raise InventoryAuthorityError("Pink Pepper predecessor overlay hash drift")
    try:
        predecessor_payload = json.loads(
            STOCK_CLARIFICATIONS_USER_INVENTORY_OVERLAY_PATH.read_text(
                encoding="utf-8"
            )
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryAuthorityError(
            "Pink Pepper predecessor overlay is unreadable"
        ) from exc
    previous = _load_20260910_stock_clarification_inventory_successor(
        predecessor_payload,
        require_live_inventory_binding=False,
    )
    if any(record["record_id"] == expected_record["record_id"] for record in previous["records"]):
        raise InventoryAuthorityError("Pink Pepper record identifier already exists")
    origins = {
        key: dict(value) for key, value in previous["record_origins"].items()
    }
    origins[expected_record["record_id"]] = {
        "path": "data/governance/inventory_user_authority_overlay_20260915_pink_pepper.json",
        "sha256": PINK_PEPPER_USER_INVENTORY_OVERLAY_SHA256,
    }
    return {
        **dict(successor),
        "parent": dict(previous["parent"]),
        "base_policy": dict(previous["base_policy"]),
        "policy": {**dict(previous["policy"]), **expected_policy},
        "delta_records": records,
        "records": [*previous["records"], *records],
        "record_origins": origins,
        "retired_records": list(previous.get("retired_records", [])),
    }


def _load_20260915_stock_forms_and_tincture_model_successor(
    successor: Mapping[str, Any],
    *,
    require_live_inventory_binding: bool = True,
) -> dict[str, Any]:
    """Apply direct stock forms and a nominal-only tincture model convention."""

    expected_policy = {
        "predecessor_overlay_immutable": True,
        "preserve_inherited_stock_ids": True,
        "formula_rebase_authorized": False,
        "general_substitution_authorized": False,
        "unknown_metadata_fails_closed": True,
        "bind_only_source_declared_stock_facts": True,
        "stock_solution_density_assumed": False,
        "tincture_nominal_property_model_is_not_assay": True,
        "safety_or_release_asserted": False,
    }
    expected_predecessor = {
        "path": "data/governance/inventory_user_authority_overlay_20260915_pink_pepper.json",
        "normalized_text_sha256": PINK_PEPPER_USER_INVENTORY_OVERLAY_SHA256,
    }
    expected_superseded = [
        "INV-USER-20260830-008",
        "INV-USER-20260830-011",
        "INV-USER-20260907-003",
        "INV-USER-20260907-004",
        "INV-USER-20260907-006",
        "INV-USER-20260910-ROMANDOLIDE-RESTOCK-001",
        "INV-USER-20260910-CLARIFY-005",
        "INV-USER-20260910-CLARIFY-006",
        "INV-USER-20260910-CLARIFY-007",
        "INV-USER-20260910-CLARIFY-008",
    ]
    if (
        successor.get("schema_version")
        != "perfume_chem_user_inventory_authority_successor_overlay_v12"
        or successor.get("effective_date") != "2026-09-15"
        or successor.get("authority") != "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY"
        or successor.get("predecessor") != expected_predecessor
        or successor.get("policy") != expected_policy
        or successor.get("superseded_record_ids") != expected_superseded
    ):
        raise InventoryAuthorityError("Stock-form successor metadata drift")

    source = successor.get("source", {})
    expected_inventory_size = 26001
    expected_inventory_sha = (
        "0107c74bec904092b19a751765203ac6108921a739820eb3dc7e29417a7d5914"
    )
    confirmation_path = (
        PROJECT_ROOT
        / "data/governance/inventory_user_confirmation_20260915_stock_forms_and_tincture_model.json"
    )
    if (
        not isinstance(source, Mapping)
        or source.get("inventory_text_path") != "inventory.txt"
        or source.get("inventory_text_size_bytes") != expected_inventory_size
        or source.get("inventory_text_sha256") != expected_inventory_sha
        or source.get("confirmed_receipt")
        != confirmation_path.relative_to(PROJECT_ROOT).as_posix()
        or source.get("confirmed_receipt_sha256")
        != STOCK_FORMS_AND_TINCTURE_MODEL_CONFIRMATION_SHA256
    ):
        raise InventoryAuthorityError("Stock-form successor source drift")
    if require_live_inventory_binding and (
        len(_normalized_text_bytes(INVENTORY_PATH)) != expected_inventory_size
        or _normalized_text_sha256(INVENTORY_PATH) != expected_inventory_sha
    ):
        raise InventoryAuthorityError(
            "Stock-form successor is not bound to live inventory text"
        )
    if (
        not confirmation_path.is_file()
        or _file_sha256(confirmation_path)
        != STOCK_FORMS_AND_TINCTURE_MODEL_CONFIRMATION_SHA256
    ):
        raise InventoryAuthorityError("Stock-form confirmation receipt drift")
    try:
        confirmation = json.loads(confirmation_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryAuthorityError(
            "Stock-form confirmation receipt is unreadable"
        ) from exc
    limits = confirmation.get("authority_limits", {})
    tincture_model = confirmation.get("tincture_property_model", {})
    clarification_names = {
        str(row.get("canonical_name"))
        for row in confirmation.get("stock_clarifications", [])
        if isinstance(row, Mapping)
    }
    expected_clarification_names = {
        "Romandolide",
        "Liffarome",
        "Methyl Laitone",
        "Evernyl",
        "2-Acetyl Pyrazine",
        "Skatole",
        "Maple Lactone",
        "Castoreum Synthetic",
        "Siam Benzoin",
        "Peru Balsam Resinoid",
        "Methyl Pamplemousse",
        "Gamma Nonalactone",
    }
    expected_tinctures = {
        "Turkish Storax Tincture": 0.2,
        "Vietnamese Benzoin Tincture": 0.4,
        "Kenyan Myrrh Ethanol Tincture": 0.2,
        "Oman Frankincense Ethanol Tincture": 0.33,
    }
    observed_tinctures = {
        str(row.get("canonical_name")): row.get("nominal_fraction")
        for row in tincture_model.get("stocks", [])
        if isinstance(row, Mapping)
    }
    if (
        confirmation.get("schema_version")
        != "perfume_chem_direct_stock_forms_and_tincture_model_v1"
        or confirmation.get("effective_date") != "2026-09-15"
        or confirmation.get("source_kind") != "DIRECT_USER_MESSAGE"
        or clarification_names != expected_clarification_names
        or observed_tinctures != expected_tinctures
        or tincture_model.get("nominal_property_model_ready") is not True
        or tincture_model.get("final_dissolved_solids_fraction_measured") is not False
        or tincture_model.get("quantitative_active_mass_ready") is not False
        or limits.get("physical_stock_forms_confirmed_as_listed") is not True
        or limits.get("maple_lactone_current_ownership") is not False
        or limits.get("unstated_fraction_bases_inferred") is not False
        or limits.get("tincture_nominal_property_model_authorized") is not True
        or limits.get("tincture_final_dissolved_fraction_assayed") is not False
        or limits.get("formula_rebase_authorized") is not False
        or limits.get("safety_or_release_asserted") is not False
    ):
        raise InventoryAuthorityError("Stock-form confirmation scope drift")

    records = successor.get("records", [])
    if not isinstance(records, list) or len(records) != 16:
        raise InventoryAuthorityError("Stock-form successor record count drift")
    records_sha = hashlib.sha256(
        json.dumps(
            records,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    if records_sha != STOCK_FORMS_AND_TINCTURE_MODEL_RECORDS_SHA256:
        raise InventoryAuthorityError("Stock-form successor exact records drift")
    records_by_id = {
        str(record.get("record_id")): record
        for record in records
        if isinstance(record, Mapping)
    }
    expected_ids = {
        f"INV-USER-20260915-STOCK-{index:03d}" for index in range(1, 17)
    }
    if set(records_by_id) != expected_ids:
        raise InventoryAuthorityError("Stock-form successor record identifiers drift")

    expected_stock_specs = {
        "INV-USER-20260915-STOCK-001": (
            "Romandolide", 1.0, "neat", "", True, "", False, False
        ),
        "INV-USER-20260915-STOCK-002": (
            "Liffarome", 0.1, "mass_fraction", "dep", True, "", False, False
        ),
        "INV-USER-20260915-STOCK-003": (
            "Methyl Laitone", 0.2, "volume_fraction", "ethanol", True, "", False, False
        ),
        "INV-USER-20260915-STOCK-004": (
            "Evernyl", 0.1, "unspecified", "dpg", False,
            "FRACTION_BASIS_AND_HOMOGENEITY_NOT_CONFIRMED", False, False
        ),
        "INV-USER-20260915-STOCK-005": (
            "2-Acetyl Pyrazine", 0.01, "unspecified", "dpg", False,
            "FRACTION_BASIS_UNSPECIFIED", False, False
        ),
        "INV-USER-20260915-STOCK-006": (
            "Skatole", 0.01, "unspecified", "dpg", False,
            "FRACTION_BASIS_UNSPECIFIED", False, False
        ),
        "INV-USER-20260915-STOCK-008": (
            "Castoreum Synthetic", 0.1, "mass_fraction", "dep", True, "", False, False
        ),
        "INV-USER-20260915-STOCK-009": (
            "Siam Benzoin", 0.5, "mass_fraction", "dpg", True, "", False, False
        ),
        "INV-USER-20260915-STOCK-010": (
            "Peru Balsam Resinoid", 0.5, "mass_fraction", "dep", True, "", False, False
        ),
        "INV-USER-20260915-STOCK-011": (
            "Methyl Pamplemousse", 0.1, "unspecified", "ethanol", False,
            "FRACTION_BASIS_UNSPECIFIED", False, False
        ),
        "INV-USER-20260915-STOCK-012": (
            "Gamma Nonalactone", 0.1, "unspecified", "ethanol", False,
            "FRACTION_BASIS_UNSPECIFIED", False, False
        ),
        "INV-USER-20260915-STOCK-013": (
            "Turkish Storax Tincture", 0.2, "mass_fraction_starting_charge",
            "ethanol", False, "FINAL_DISSOLVED_FRACTION_UNMEASURED", True, True
        ),
        "INV-USER-20260915-STOCK-014": (
            "Vietnamese Benzoin Tincture", 0.4, "mass_fraction_starting_charge",
            "ethanol", False, "FINAL_DISSOLVED_FRACTION_UNMEASURED", True, True
        ),
        "INV-USER-20260915-STOCK-015": (
            "Kenyan Myrrh Ethanol Tincture", 0.2, "mass_fraction_starting_charge",
            "ethanol", False, "FINAL_DISSOLVED_FRACTION_UNMEASURED", True, True
        ),
        "INV-USER-20260915-STOCK-016": (
            "Oman Frankincense Ethanol Tincture", 0.33,
            "mass_fraction_starting_charge", "ethanol", False,
            "FINAL_DISSOLVED_FRACTION_UNMEASURED", True, True
        ),
    }
    for record_id, expected in expected_stock_specs.items():
        record = records_by_id[record_id]
        stock = record.get("stock", {})
        observed = (
            record.get("canonical_name"),
            stock.get("fraction"),
            stock.get("fraction_basis"),
            stock.get("carrier"),
            stock.get("execution_ready"),
            str(stock.get("execution_hold_reason") or ""),
            bool(stock.get("nominal_property_model_ready", False)),
            bool(stock.get("approximate", False)),
        )
        if record.get("state") != "OWNED" or observed != expected:
            raise InventoryAuthorityError(
                f"{record.get('canonical_name')} exact stock record drift"
            )
    maple = records_by_id["INV-USER-20260915-STOCK-007"]
    if (
        maple.get("canonical_name") != "Maple Lactone"
        or maple.get("state") != "NOT_OWNED"
        or maple.get("stock") is not None
        or maple.get("supersedes_parent_stocks")
        != [{"source_row": 271, "fraction": 0.2}]
        or len(maple.get("requirement_overrides", [])) != 1
        or maple["requirement_overrides"][0].get("disposition") != "GAP"
    ):
        raise InventoryAuthorityError("Maple Lactone removal record drift")

    if (
        _normalized_text_sha256(PINK_PEPPER_USER_INVENTORY_OVERLAY_PATH)
        != PINK_PEPPER_USER_INVENTORY_OVERLAY_SHA256
    ):
        raise InventoryAuthorityError("Stock-form predecessor overlay hash drift")
    try:
        predecessor_payload = json.loads(
            PINK_PEPPER_USER_INVENTORY_OVERLAY_PATH.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryAuthorityError(
            "Stock-form predecessor overlay is unreadable"
        ) from exc
    previous = _load_20260915_pink_pepper_inventory_successor(
        predecessor_payload,
        require_live_inventory_binding=False,
    )
    previous_by_id = {
        str(record["record_id"]): record for record in previous["records"]
    }
    retired_ids = set(expected_superseded)
    if not retired_ids <= set(previous_by_id):
        raise InventoryAuthorityError("Stock-form predecessor record set drift")
    inherited = [
        record
        for record in previous["records"]
        if record["record_id"] not in retired_ids
    ]
    origins = {
        key: dict(value)
        for key, value in previous["record_origins"].items()
        if key not in retired_ids
    }
    for record in records:
        origins[str(record["record_id"])] = {
            "path": (
                "data/governance/"
                "inventory_user_authority_overlay_20260915_stock_forms_and_tincture_model.json"
            ),
            "sha256": STOCK_FORMS_AND_TINCTURE_MODEL_USER_INVENTORY_OVERLAY_SHA256,
        }
    return {
        **dict(successor),
        "parent": dict(previous["parent"]),
        "base_policy": dict(previous["base_policy"]),
        "policy": {**dict(previous["policy"]), **expected_policy},
        "delta_records": records,
        "records": [*inherited, *records],
        "record_origins": origins,
        "retired_records": [
            *previous.get("retired_records", []),
            *(previous_by_id[record_id] for record_id in expected_superseded),
        ],
    }


def _load_20260915_evernyl_10ww_dpg_successor(
    successor: Mapping[str, Any],
    *,
    require_live_inventory_binding: bool = True,
) -> dict[str, Any]:
    """Promote the fully dissolved Evernyl 10% w/w DPG stock."""

    expected_policy = {
        "predecessor_overlay_immutable": True,
        "preserve_inherited_stock_ids": True,
        "formula_rebase_authorized": False,
        "general_substitution_authorized": False,
        "unknown_metadata_fails_closed": True,
        "bind_only_source_declared_stock_facts": True,
        "stock_solution_density_assumed": False,
        "tincture_nominal_property_model_is_not_assay": True,
        "safety_or_release_asserted": False,
    }
    expected_predecessor = {
        "path": (
            "data/governance/"
            "inventory_user_authority_overlay_20260915_stock_forms_and_tincture_model.json"
        ),
        "normalized_text_sha256": (
            STOCK_FORMS_AND_TINCTURE_MODEL_USER_INVENTORY_OVERLAY_SHA256
        ),
    }
    expected_superseded = ["INV-USER-20260915-STOCK-004"]
    if (
        successor.get("schema_version")
        != "perfume_chem_user_inventory_authority_successor_overlay_v13"
        or successor.get("effective_date") != "2026-09-15"
        or successor.get("authority") != "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY"
        or successor.get("predecessor") != expected_predecessor
        or successor.get("policy") != expected_policy
        or successor.get("superseded_record_ids") != expected_superseded
    ):
        raise InventoryAuthorityError("Evernyl successor metadata drift")

    source = successor.get("source", {})
    expected_inventory_size = 25989
    expected_inventory_sha = (
        "7256fbb698bc96c548d727b74b37d27f7bfa5223778dbeb0f3f1a6f3c446f526"
    )
    confirmation_path = (
        PROJECT_ROOT
        / "data/governance/inventory_user_confirmation_20260915_evernyl_10w_w_dpg.json"
    )
    if (
        not isinstance(source, Mapping)
        or source.get("inventory_text_path") != "inventory.txt"
        or source.get("inventory_text_size_bytes") != expected_inventory_size
        or source.get("inventory_text_sha256") != expected_inventory_sha
        or source.get("confirmed_receipt")
        != confirmation_path.relative_to(PROJECT_ROOT).as_posix()
        or source.get("confirmed_receipt_sha256")
        != EVERNYL_10WW_DPG_CONFIRMATION_SHA256
    ):
        raise InventoryAuthorityError("Evernyl successor source drift")
    if require_live_inventory_binding and (
        len(_normalized_text_bytes(INVENTORY_PATH)) != expected_inventory_size
        or _normalized_text_sha256(INVENTORY_PATH) != expected_inventory_sha
    ):
        raise InventoryAuthorityError(
            "Evernyl successor is not bound to live inventory text"
        )
    if (
        not confirmation_path.is_file()
        or _file_sha256(confirmation_path) != EVERNYL_10WW_DPG_CONFIRMATION_SHA256
    ):
        raise InventoryAuthorityError("Evernyl confirmation receipt drift")
    try:
        confirmation = json.loads(confirmation_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryAuthorityError(
            "Evernyl confirmation receipt is unreadable"
        ) from exc
    expected_fact = {
        "canonical_name": "Evernyl",
        "fraction": 0.1,
        "fraction_basis": "mass_fraction",
        "carrier": "dpg",
        "homogeneity": "FULLY_DISSOLVED",
        "execution_ready": True,
        "execution_scope": "RAW_STOCK_VOLUME_TRANSFER_ONLY",
    }
    expected_limits = {
        "physical_stock_fraction_basis_confirmed": True,
        "physical_stock_carrier_confirmed": True,
        "physical_stock_homogeneity_confirmed": True,
        "stock_solution_density_measured": False,
        "exact_active_mass_from_volume_asserted": False,
        "formula_rebase_authorized": False,
        "safety_or_release_asserted": False,
    }
    if (
        confirmation.get("schema_version")
        != "perfume_chem_direct_evernyl_stock_confirmation_v1"
        or confirmation.get("effective_date") != "2026-09-15"
        or confirmation.get("source_kind") != "DIRECT_USER_MESSAGES"
        or confirmation.get("messages")
        != [
            "When will the citrususes and evernyl 10% w/w be covered",
            "It’s fully dissolved",
        ]
        or confirmation.get("normalized_stock_fact") != expected_fact
        or confirmation.get("authority_limits") != expected_limits
    ):
        raise InventoryAuthorityError("Evernyl confirmation scope drift")

    records = successor.get("records", [])
    if not isinstance(records, list) or len(records) != 1:
        raise InventoryAuthorityError("Evernyl successor record count drift")
    records_sha = hashlib.sha256(
        json.dumps(
            records,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    if records_sha != EVERNYL_10WW_DPG_RECORDS_SHA256:
        raise InventoryAuthorityError("Evernyl successor exact records drift")
    record = records[0]
    stock = record.get("stock", {})
    if (
        record.get("record_id") != "INV-USER-20260915-EVERNYL-10WW-001"
        or record.get("canonical_name") != "Evernyl"
        or record.get("aliases") != ["Evernyl 10% w/w in DPG"]
        or record.get("state") != "OWNED"
        or stock.get("fraction") != 0.1
        or stock.get("fraction_basis") != "mass_fraction"
        or stock.get("carrier") != "dpg"
        or stock.get("homogeneity") != "FULLY_DISSOLVED"
        or stock.get("execution_ready") is not True
        or stock.get("execution_scope") != "RAW_STOCK_VOLUME_TRANSFER_ONLY"
        or stock.get("execution_limit")
        != "EXACT_ACTIVE_MASS_FROM_VOLUME_REQUIRES_STOCK_DENSITY"
        or record.get("supersedes_parent_stocks")
        != [{"source_row": 105, "fraction": 0.2}]
        or len(record.get("requirement_overrides", [])) != 1
        or record["requirement_overrides"][0].get("disposition")
        != "PREPARATION_REQUIRED"
    ):
        raise InventoryAuthorityError("Evernyl exact stock record drift")

    predecessor_path = STOCK_FORMS_AND_TINCTURE_MODEL_USER_INVENTORY_OVERLAY_PATH
    if (
        _normalized_text_sha256(predecessor_path)
        != STOCK_FORMS_AND_TINCTURE_MODEL_USER_INVENTORY_OVERLAY_SHA256
    ):
        raise InventoryAuthorityError("Evernyl predecessor overlay hash drift")
    try:
        predecessor_payload = json.loads(predecessor_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryAuthorityError(
            "Evernyl predecessor overlay is unreadable"
        ) from exc
    previous = _load_20260915_stock_forms_and_tincture_model_successor(
        predecessor_payload,
        require_live_inventory_binding=False,
    )
    previous_by_id = {
        str(previous_record["record_id"]): previous_record
        for previous_record in previous["records"]
    }
    superseded_id = expected_superseded[0]
    if superseded_id not in previous_by_id:
        raise InventoryAuthorityError("Evernyl predecessor record missing")
    inherited = [
        previous_record
        for previous_record in previous["records"]
        if previous_record["record_id"] != superseded_id
    ]
    origins = {
        key: dict(value)
        for key, value in previous["record_origins"].items()
        if key != superseded_id
    }
    origins[str(record["record_id"])] = {
        "path": (
            "data/governance/"
            "inventory_user_authority_overlay_20260915_evernyl_10w_w_dpg.json"
        ),
        "sha256": EVERNYL_10WW_DPG_USER_INVENTORY_OVERLAY_SHA256,
    }
    return {
        **dict(successor),
        "parent": dict(previous["parent"]),
        "base_policy": dict(previous["base_policy"]),
        "policy": {**dict(previous["policy"]), **expected_policy},
        "delta_records": records,
        "records": [*inherited, *records],
        "record_origins": origins,
        "retired_records": [
            *previous.get("retired_records", []),
            previous_by_id[superseded_id],
        ],
    }


def _load_20260915_methyl_pamplemousse_10ww_ethanol_successor(
    successor: Mapping[str, Any],
    *,
    require_live_inventory_binding: bool = True,
) -> dict[str, Any]:
    """Promote the user-confirmed Methyl Pamplemousse 10% w/w stock."""

    expected_policy = {
        "predecessor_overlay_immutable": True,
        "preserve_inherited_stock_ids": True,
        "formula_rebase_authorized": False,
        "general_substitution_authorized": False,
        "unknown_metadata_fails_closed": True,
        "bind_only_source_declared_stock_facts": True,
        "stock_solution_density_assumed": False,
        "tincture_nominal_property_model_is_not_assay": True,
        "safety_or_release_asserted": False,
    }
    expected_predecessor = {
        "path": (
            "data/governance/"
            "inventory_user_authority_overlay_20260915_evernyl_10w_w_dpg.json"
        ),
        "normalized_text_sha256": (
            EVERNYL_10WW_DPG_USER_INVENTORY_OVERLAY_SHA256
        ),
    }
    expected_superseded = ["INV-USER-20260915-STOCK-011"]
    if (
        successor.get("schema_version")
        != "perfume_chem_user_inventory_authority_successor_overlay_v14"
        or successor.get("effective_date") != "2026-09-15"
        or successor.get("authority") != "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY"
        or successor.get("predecessor") != expected_predecessor
        or successor.get("policy") != expected_policy
        or successor.get("superseded_record_ids") != expected_superseded
    ):
        raise InventoryAuthorityError("Methyl Pamplemousse successor metadata drift")

    source = successor.get("source", {})
    expected_inventory_size = 26015
    expected_inventory_sha = (
        "80bba680df969c0ca9d51bb74e81c417ff6b9734357c58ed5321b9b4d847060e"
    )
    confirmation_path = (
        PROJECT_ROOT
        / "data/governance/"
        "inventory_user_confirmation_20260915_methyl_pamplemousse_10w_w_ethanol.json"
    )
    if (
        not isinstance(source, Mapping)
        or source.get("inventory_text_path") != "inventory.txt"
        or source.get("inventory_text_size_bytes") != expected_inventory_size
        or source.get("inventory_text_sha256") != expected_inventory_sha
        or source.get("confirmed_receipt")
        != confirmation_path.relative_to(PROJECT_ROOT).as_posix()
        or source.get("confirmed_receipt_sha256")
        != METHYL_PAMPLEMOUSSE_10WW_ETHANOL_CONFIRMATION_SHA256
    ):
        raise InventoryAuthorityError("Methyl Pamplemousse successor source drift")
    if require_live_inventory_binding and (
        len(_normalized_text_bytes(INVENTORY_PATH)) != expected_inventory_size
        or _normalized_text_sha256(INVENTORY_PATH) != expected_inventory_sha
    ):
        raise InventoryAuthorityError(
            "Methyl Pamplemousse successor is not bound to live inventory text"
        )
    if (
        not confirmation_path.is_file()
        or _file_sha256(confirmation_path)
        != METHYL_PAMPLEMOUSSE_10WW_ETHANOL_CONFIRMATION_SHA256
    ):
        raise InventoryAuthorityError("Methyl Pamplemousse confirmation receipt drift")
    try:
        confirmation = json.loads(confirmation_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryAuthorityError(
            "Methyl Pamplemousse confirmation receipt is unreadable"
        ) from exc
    expected_fact = {
        "canonical_name": "Methyl Pamplemousse",
        "fraction": 0.1,
        "fraction_basis": "mass_fraction",
        "carrier": "ethanol",
        "execution_ready": True,
        "execution_scope": "RAW_STOCK_VOLUME_TRANSFER_ONLY",
    }
    expected_limits = {
        "physical_stock_fraction_basis_confirmed": True,
        "physical_stock_carrier_confirmed": True,
        "stock_solution_density_measured": False,
        "exact_active_mass_from_volume_asserted": False,
        "formula_rebase_authorized": False,
        "safety_or_release_asserted": False,
    }
    if (
        confirmation.get("schema_version")
        != "perfume_chem_direct_methyl_pamplemousse_stock_confirmation_v1"
        or confirmation.get("effective_date") != "2026-09-15"
        or confirmation.get("source_kind") != "DIRECT_USER_MESSAGE"
        or confirmation.get("message") != "It is in W/W"
        or confirmation.get("context")
        != "Methyl Pamplemousse 10% in ethanol percentage basis"
        or confirmation.get("normalized_stock_fact") != expected_fact
        or confirmation.get("authority_limits") != expected_limits
    ):
        raise InventoryAuthorityError("Methyl Pamplemousse confirmation scope drift")

    records = successor.get("records", [])
    if not isinstance(records, list) or len(records) != 1:
        raise InventoryAuthorityError(
            "Methyl Pamplemousse successor record count drift"
        )
    records_sha = hashlib.sha256(
        json.dumps(
            records,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    if records_sha != METHYL_PAMPLEMOUSSE_10WW_ETHANOL_RECORDS_SHA256:
        raise InventoryAuthorityError("Methyl Pamplemousse successor exact records drift")
    record = records[0]
    stock = record.get("stock", {})
    expected_override = {
        "source_row": 259,
        "disposition": "OWNED",
        "status": "HAVE - 10% W/W IN ETHANOL",
        "actual_stock_text": "Methyl Pamplemousse 10% w/w in ethanol",
        "can_prepare": "",
    }
    if (
        record.get("record_id")
        != "INV-USER-20260915-METHYL-PAMPLEMOUSSE-10WW-001"
        or record.get("canonical_name") != "Methyl Pamplemousse"
        or record.get("aliases")
        != ["Methyl Pamplemousse 10% w/w in ethanol"]
        or record.get("state") != "OWNED"
        or record.get("category") != "citrus_grapefruit"
        or stock.get("fraction") != 0.1
        or stock.get("fraction_basis") != "mass_fraction"
        or stock.get("carrier") != "ethanol"
        or stock.get("fraction_authority") != "DIRECT_USER_BASIS_CONFIRMATION"
        or stock.get("execution_ready") is not True
        or stock.get("execution_scope") != "RAW_STOCK_VOLUME_TRANSFER_ONLY"
        or stock.get("execution_limit")
        != "EXACT_ACTIVE_MASS_FROM_VOLUME_REQUIRES_STOCK_DENSITY"
        or record.get("supersedes_parent_stocks")
        != [{"source_row": 259, "fraction": 0.1}]
        or record.get("requirement_overrides") != [expected_override]
        or record.get("effective_date") != "2026-09-15"
        or record.get("source_kind")
        != "DIRECT_USER_CURRENT_STOCK_BASIS_CONFIRMATION"
    ):
        raise InventoryAuthorityError("Methyl Pamplemousse exact stock record drift")

    predecessor_path = EVERNYL_10WW_DPG_USER_INVENTORY_OVERLAY_PATH
    if (
        _normalized_text_sha256(predecessor_path)
        != EVERNYL_10WW_DPG_USER_INVENTORY_OVERLAY_SHA256
    ):
        raise InventoryAuthorityError(
            "Methyl Pamplemousse predecessor overlay hash drift"
        )
    try:
        predecessor_payload = json.loads(predecessor_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryAuthorityError(
            "Methyl Pamplemousse predecessor overlay is unreadable"
        ) from exc
    previous = _load_20260915_evernyl_10ww_dpg_successor(
        predecessor_payload,
        require_live_inventory_binding=False,
    )
    previous_by_id = {
        str(previous_record["record_id"]): previous_record
        for previous_record in previous["records"]
    }
    superseded_id = expected_superseded[0]
    if superseded_id not in previous_by_id:
        raise InventoryAuthorityError("Methyl Pamplemousse predecessor record missing")
    inherited = [
        previous_record
        for previous_record in previous["records"]
        if previous_record["record_id"] != superseded_id
    ]
    origins = {
        key: dict(value)
        for key, value in previous["record_origins"].items()
        if key != superseded_id
    }
    origins[str(record["record_id"])] = {
        "path": (
            "data/governance/"
            "inventory_user_authority_overlay_20260915_"
            "methyl_pamplemousse_10w_w_ethanol.json"
        ),
        "sha256": METHYL_PAMPLEMOUSSE_10WW_ETHANOL_USER_INVENTORY_OVERLAY_SHA256,
    }
    return {
        **dict(successor),
        "parent": dict(previous["parent"]),
        "base_policy": dict(previous["base_policy"]),
        "policy": {**dict(previous["policy"]), **expected_policy},
        "delta_records": records,
        "records": [*inherited, *records],
        "record_origins": origins,
        "retired_records": [
            *previous.get("retired_records", []),
            previous_by_id[superseded_id],
        ],
    }


def _load_20260924_r5_stock_clarifications_successor(
    successor: Mapping[str, Any],
    *,
    require_live_inventory_binding: bool = True,
) -> dict[str, Any]:
    """Apply the user's R5 stock-form corrections without widening authority."""

    expected_policy = {
        "predecessor_overlay_immutable": True,
        "preserve_inherited_stock_ids": True,
        "formula_rebase_authorized": False,
        "general_substitution_authorized": False,
        "unknown_metadata_fails_closed": True,
        "bind_only_source_declared_stock_facts": True,
        "stock_solution_density_assumed": False,
        "tincture_nominal_property_model_is_not_assay": True,
        "supplier_identity_does_not_prove_physical_ownership": True,
        "safety_or_release_asserted": False,
    }
    expected_predecessor = {
        "path": (
            "data/governance/"
            "inventory_user_authority_overlay_20260915_"
            "methyl_pamplemousse_10w_w_ethanol.json"
        ),
        "normalized_text_sha256": (
            METHYL_PAMPLEMOUSSE_10WW_ETHANOL_USER_INVENTORY_OVERLAY_SHA256
        ),
    }
    expected_superseded = ["INV-USER-20260907-002"]
    if (
        successor.get("schema_version")
        != "perfume_chem_user_inventory_authority_successor_overlay_v15"
        or successor.get("effective_date") != "2026-09-24"
        or successor.get("authority")
        != "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY"
        or successor.get("predecessor") != expected_predecessor
        or successor.get("policy") != expected_policy
        or successor.get("superseded_record_ids") != expected_superseded
    ):
        raise InventoryAuthorityError("R5 stock clarification successor metadata drift")

    source = successor.get("source", {})
    expected_inventory_size = 26533
    expected_inventory_sha = (
        "b9b245148011cefafc926d617d9f7559ca3d7a01901491c1f7de2fb3d43dce51"
    )
    confirmation_path = (
        PROJECT_ROOT
        / "data/governance/"
        "inventory_user_confirmation_20260924_r5_stock_clarifications.json"
    )
    supplier_resolution_path = (
        PROJECT_ROOT
        / "data/governance/"
        "inventory_supplier_product_resolution_20260924_"
        "aroma_more_lavender_4042.json"
    )
    if (
        not isinstance(source, Mapping)
        or source.get("inventory_text_path") != "inventory.txt"
        or source.get("inventory_text_size_bytes") != expected_inventory_size
        or source.get("inventory_text_sha256") != expected_inventory_sha
        or source.get("confirmed_receipt")
        != confirmation_path.relative_to(PROJECT_ROOT).as_posix()
        or source.get("confirmed_receipt_sha256")
        != R5_STOCK_CLARIFICATIONS_CONFIRMATION_SHA256
        or source.get("supplier_product_resolution")
        != supplier_resolution_path.relative_to(PROJECT_ROOT).as_posix()
        or source.get("supplier_product_resolution_sha256")
        != AROMA_MORE_LAVENDER_4042_PRODUCT_RESOLUTION_SHA256
    ):
        raise InventoryAuthorityError("R5 stock clarification successor source drift")
    if require_live_inventory_binding and (
        len(_normalized_text_bytes(INVENTORY_PATH)) != expected_inventory_size
        or _normalized_text_sha256(INVENTORY_PATH) != expected_inventory_sha
    ):
        raise InventoryAuthorityError(
            "R5 stock clarification successor is not bound to live inventory text"
        )

    for evidence_path, expected_sha, label in (
        (
            confirmation_path,
            R5_STOCK_CLARIFICATIONS_CONFIRMATION_SHA256,
            "R5 stock confirmation",
        ),
        (
            supplier_resolution_path,
            AROMA_MORE_LAVENDER_4042_PRODUCT_RESOLUTION_SHA256,
            "Aroma & More supplier resolution",
        ),
    ):
        if not evidence_path.is_file() or _file_sha256(evidence_path) != expected_sha:
            raise InventoryAuthorityError(f"{label} receipt drift")

    try:
        confirmation = json.loads(confirmation_path.read_text(encoding="utf-8"))
        supplier_resolution = json.loads(
            supplier_resolution_path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryAuthorityError(
            "R5 stock clarification evidence is unreadable"
        ) from exc
    confirmation_limits = confirmation.get("authority_limits", {})
    supplier_limits = supplier_resolution.get("authority_limits", {})
    if (
        confirmation.get("schema_version")
        != "perfume_chem_direct_r5_stock_clarifications_confirmation_v1"
        or confirmation.get("effective_date") != "2026-09-24"
        or confirmation.get("source_kind") != "DIRECT_USER_MESSAGE"
        or len(confirmation.get("normalized_stock_facts", [])) != 4
        or confirmation_limits.get("formula_rebase_authorized") is not False
        or confirmation_limits.get("physical_compounding_authorized") is not False
        or confirmation_limits.get("safety_or_release_asserted") is not False
        or supplier_resolution.get("resolution_state")
        != "EXACT_CATALOG_PRODUCT_IDENTIFIED_PHYSICAL_STOCK_UNBOUND"
        or supplier_limits.get("catalog_identity_resolved") is not True
        or supplier_limits.get("physical_ownership_confirmed") is not False
        or supplier_limits.get("inventory_mutation_authorized") is not False
        or supplier_limits.get("purchase_authorized") is not False
    ):
        raise InventoryAuthorityError("R5 stock clarification evidence scope drift")

    records = successor.get("records", [])
    if not isinstance(records, list) or len(records) != 4:
        raise InventoryAuthorityError("R5 stock clarification record count drift")
    records_sha = hashlib.sha256(
        json.dumps(
            records,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    if records_sha != R5_STOCK_CLARIFICATIONS_RECORDS_SHA256:
        raise InventoryAuthorityError("R5 stock clarification exact records drift")

    predecessor_path = (
        METHYL_PAMPLEMOUSSE_10WW_ETHANOL_USER_INVENTORY_OVERLAY_PATH
    )
    if (
        _normalized_text_sha256(predecessor_path)
        != METHYL_PAMPLEMOUSSE_10WW_ETHANOL_USER_INVENTORY_OVERLAY_SHA256
    ):
        raise InventoryAuthorityError("R5 stock clarification predecessor drift")
    try:
        predecessor_payload = json.loads(
            predecessor_path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryAuthorityError(
            "R5 stock clarification predecessor is unreadable"
        ) from exc
    previous = _load_20260915_methyl_pamplemousse_10ww_ethanol_successor(
        predecessor_payload,
        require_live_inventory_binding=False,
    )
    previous_by_id = {
        str(previous_record["record_id"]): previous_record
        for previous_record in previous["records"]
    }
    superseded_id = expected_superseded[0]
    if superseded_id not in previous_by_id:
        raise InventoryAuthorityError(
            "R5 stock clarification superseded Vetiveryl record missing"
        )
    inherited = [
        previous_record
        for previous_record in previous["records"]
        if previous_record["record_id"] != superseded_id
    ]
    origins = {
        key: dict(value)
        for key, value in previous["record_origins"].items()
        if key != superseded_id
    }
    origin = {
        "path": (
            "data/governance/"
            "inventory_user_authority_overlay_20260924_"
            "r5_stock_clarifications.json"
        ),
        "sha256": R5_STOCK_CLARIFICATIONS_USER_INVENTORY_OVERLAY_SHA256,
    }
    for record in records:
        origins[str(record["record_id"])] = dict(origin)
    return {
        **dict(successor),
        "parent": dict(previous["parent"]),
        "base_policy": dict(previous["base_policy"]),
        "policy": {**dict(previous["policy"]), **expected_policy},
        "delta_records": records,
        "records": [*inherited, *records],
        "record_origins": origins,
        "retired_records": [
            *previous.get("retired_records", []),
            previous_by_id[superseded_id],
        ],
    }


def _load_20260924_r5_stock_clarifications_v2_successor(
    successor: Mapping[str, Any],
    *,
    require_live_inventory_binding: bool = True,
) -> dict[str, Any]:
    """Apply the user's basis and ownership clarifications without build authority."""

    expected_policy = {
        "predecessor_overlay_immutable": True,
        "preserve_inherited_stock_ids": True,
        "formula_rebase_authorized": False,
        "general_substitution_authorized": False,
        "unknown_metadata_fails_closed": True,
        "bind_only_source_declared_stock_facts": True,
        "stock_solution_density_assumed": False,
        "tincture_nominal_property_model_is_not_assay": True,
        "supplier_identity_alone_does_not_prove_physical_ownership": True,
        "direct_user_ownership_can_bind_catalog_identity": True,
        "physical_lineage_receipt_required_for_build_execution": True,
        "r5_norlimbanol_dpg_requirement_update_authorized": True,
        "safety_or_release_asserted": False,
    }
    expected_predecessor = {
        "path": (
            "data/governance/"
            "inventory_user_authority_overlay_20260924_"
            "r5_stock_clarifications.json"
        ),
        "normalized_text_sha256": (
            R5_STOCK_CLARIFICATIONS_USER_INVENTORY_OVERLAY_SHA256
        ),
    }
    expected_superseded = [
        "INV-USER-20260924-R5-003",
        "INV-USER-20260924-R5-004",
    ]
    if (
        successor.get("schema_version")
        != "perfume_chem_user_inventory_authority_successor_overlay_v16"
        or successor.get("effective_date") != "2026-09-24"
        or successor.get("authority")
        != "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY"
        or successor.get("predecessor") != expected_predecessor
        or successor.get("policy") != expected_policy
        or successor.get("superseded_record_ids") != expected_superseded
    ):
        raise InventoryAuthorityError(
            "R5 stock clarification v2 successor metadata drift"
        )

    expected_inventory_size = 26830
    expected_inventory_sha = (
        "f71ae446e081e1132b5226796ec596e1a376c31f7d96f34f25db49dd89caae36"
    )
    confirmation_path = (
        PROJECT_ROOT
        / "data/governance/"
        "inventory_user_confirmation_20260924_r5_stock_clarifications_v2.json"
    )
    supplier_resolution_path = (
        PROJECT_ROOT
        / "data/governance/"
        "inventory_supplier_product_resolution_20260924_"
        "aroma_more_lavender_4042.json"
    )
    source = successor.get("source", {})
    if (
        not isinstance(source, Mapping)
        or source.get("inventory_text_path") != "inventory.txt"
        or source.get("inventory_text_size_bytes") != expected_inventory_size
        or source.get("inventory_text_sha256") != expected_inventory_sha
        or source.get("confirmed_receipt")
        != confirmation_path.relative_to(PROJECT_ROOT).as_posix()
        or source.get("confirmed_receipt_sha256")
        != R5_STOCK_CLARIFICATIONS_V2_CONFIRMATION_SHA256
        or source.get("supplier_product_resolution")
        != supplier_resolution_path.relative_to(PROJECT_ROOT).as_posix()
        or source.get("supplier_product_resolution_sha256")
        != AROMA_MORE_LAVENDER_4042_PRODUCT_RESOLUTION_SHA256
    ):
        raise InventoryAuthorityError(
            "R5 stock clarification v2 successor source drift"
        )
    if require_live_inventory_binding and (
        len(_normalized_text_bytes(INVENTORY_PATH)) != expected_inventory_size
        or _normalized_text_sha256(INVENTORY_PATH) != expected_inventory_sha
    ):
        raise InventoryAuthorityError(
            "R5 stock clarification v2 successor is not bound to live inventory text"
        )

    for evidence_path, expected_sha, label in (
        (
            confirmation_path,
            R5_STOCK_CLARIFICATIONS_V2_CONFIRMATION_SHA256,
            "R5 stock confirmation v2",
        ),
        (
            supplier_resolution_path,
            AROMA_MORE_LAVENDER_4042_PRODUCT_RESOLUTION_SHA256,
            "Aroma & More supplier resolution",
        ),
    ):
        if not evidence_path.is_file() or _file_sha256(evidence_path) != expected_sha:
            raise InventoryAuthorityError(f"{label} receipt drift")

    try:
        confirmation = json.loads(confirmation_path.read_text(encoding="utf-8"))
        supplier_resolution = json.loads(
            supplier_resolution_path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryAuthorityError(
            "R5 stock clarification v2 evidence is unreadable"
        ) from exc
    confirmation_limits = confirmation.get("authority_limits", {})
    design_decisions = confirmation.get("r5_design_decisions", {})
    supplier_limits = supplier_resolution.get("authority_limits", {})
    if (
        confirmation.get("schema_version")
        != "perfume_chem_direct_r5_stock_clarifications_confirmation_v2"
        or confirmation.get("effective_date") != "2026-09-24"
        or confirmation.get("source_kind") != "DIRECT_USER_MESSAGE"
        or confirmation.get("predecessor")
        != {
            "path": (
                "data/governance/"
                "inventory_user_confirmation_20260924_"
                "r5_stock_clarifications.json"
            ),
            "sha256": R5_STOCK_CLARIFICATIONS_CONFIRMATION_SHA256,
        }
        or len(confirmation.get("normalized_stock_facts", [])) != 3
        or design_decisions.get("norlimbanol_dpg_carrier_accepted") is not True
        or design_decisions.get("common_total_basis_selected") != "active_mass_g"
        or design_decisions.get("conversion_inputs_complete") is not False
        or confirmation_limits.get("inventory_fact_update_authorized") is not True
        or confirmation_limits.get("physical_compounding_authorized") is not False
        or confirmation_limits.get("build_plan_binding_authorized") is not False
        or confirmation_limits.get("safety_or_release_asserted") is not False
        or supplier_resolution.get("resolution_state")
        != "EXACT_CATALOG_PRODUCT_IDENTIFIED_PHYSICAL_STOCK_UNBOUND"
        or supplier_limits.get("catalog_identity_resolved") is not True
        or supplier_limits.get("inventory_mutation_authorized") is not False
    ):
        raise InventoryAuthorityError(
            "R5 stock clarification v2 evidence scope drift"
        )

    records = successor.get("records", [])
    if not isinstance(records, list) or len(records) != 3:
        raise InventoryAuthorityError(
            "R5 stock clarification v2 record count drift"
        )
    records_sha = hashlib.sha256(
        json.dumps(
            records,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    if records_sha != R5_STOCK_CLARIFICATIONS_V2_RECORDS_SHA256:
        raise InventoryAuthorityError(
            "R5 stock clarification v2 exact records drift"
        )

    predecessor_path = R5_STOCK_CLARIFICATIONS_USER_INVENTORY_OVERLAY_PATH
    if (
        _normalized_text_sha256(predecessor_path)
        != R5_STOCK_CLARIFICATIONS_USER_INVENTORY_OVERLAY_SHA256
    ):
        raise InventoryAuthorityError(
            "R5 stock clarification v2 predecessor drift"
        )
    try:
        predecessor_payload = json.loads(
            predecessor_path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryAuthorityError(
            "R5 stock clarification v2 predecessor is unreadable"
        ) from exc
    previous = _load_20260924_r5_stock_clarifications_successor(
        predecessor_payload,
        require_live_inventory_binding=False,
    )
    previous_by_id = {
        str(previous_record["record_id"]): previous_record
        for previous_record in previous["records"]
    }
    missing_superseded = set(expected_superseded) - set(previous_by_id)
    if missing_superseded:
        raise InventoryAuthorityError(
            "R5 stock clarification v2 superseded records are missing"
        )
    inherited = [
        previous_record
        for previous_record in previous["records"]
        if previous_record["record_id"] not in expected_superseded
    ]
    origins = {
        key: dict(value)
        for key, value in previous["record_origins"].items()
        if key not in expected_superseded
    }
    origin = {
        "path": (
            "data/governance/"
            "inventory_user_authority_overlay_20260924_"
            "r5_stock_clarifications_v2.json"
        ),
        "sha256": R5_STOCK_CLARIFICATIONS_V2_USER_INVENTORY_OVERLAY_SHA256,
    }
    for record in records:
        origins[str(record["record_id"])] = dict(origin)
    return {
        **dict(successor),
        "parent": dict(previous["parent"]),
        "base_policy": dict(previous["base_policy"]),
        "policy": {**dict(previous["policy"]), **expected_policy},
        "delta_records": records,
        "records": [*inherited, *records],
        "record_origins": origins,
        "retired_records": [
            *previous.get("retired_records", []),
            *(previous_by_id[record_id] for record_id in expected_superseded),
        ],
    }


def _load_20260924_r5_remaining_stock_forms_v3_successor(
    successor: Mapping[str, Any],
    *,
    require_live_inventory_binding: bool = True,
) -> dict[str, Any]:
    """Apply the remaining R5 stock facts without inventing missing bases."""

    expected_policy = {
        "predecessor_overlay_immutable": True,
        "preserve_inherited_stock_ids": True,
        "formula_rebase_authorized": False,
        "general_substitution_authorized": False,
        "unknown_metadata_fails_closed": True,
        "bind_only_source_declared_stock_facts": True,
        "stock_solution_density_assumed": False,
        "user_reported_ready_does_not_supply_fraction_basis": True,
        "user_reported_ready_does_not_supply_physical_lineage": True,
        "neat_parent_does_not_equal_required_working_dilution": True,
        "depleted_stock_not_substitutable": True,
        "physical_lineage_receipt_required_for_build_execution": True,
        "safety_or_release_asserted": False,
    }
    expected_predecessor = {
        "path": (
            "data/governance/"
            "inventory_user_authority_overlay_20260924_"
            "r5_stock_clarifications_v2.json"
        ),
        "normalized_text_sha256": (
            R5_STOCK_CLARIFICATIONS_V2_USER_INVENTORY_OVERLAY_SHA256
        ),
    }
    expected_superseded = [
        "INV-USER-20260828-004",
        "INV-USER-20260908-AHSEE-007",
    ]
    if (
        successor.get("schema_version")
        != "perfume_chem_user_inventory_authority_successor_overlay_v17"
        or successor.get("effective_date") != "2026-09-24"
        or successor.get("authority")
        != "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY"
        or successor.get("predecessor") != expected_predecessor
        or successor.get("policy") != expected_policy
        or successor.get("superseded_record_ids") != expected_superseded
    ):
        raise InventoryAuthorityError(
            "R5 remaining stock forms v3 successor metadata drift"
        )

    expected_inventory_size = 28251
    expected_inventory_sha = (
        "1b4324da5a35cebe8c59959e58276d84ac8f2f0e0e6f3239fdef0a4250d8df71"
    )
    confirmation_path = (
        PROJECT_ROOT
        / "data/governance/"
        "inventory_user_confirmation_20260924_r5_remaining_stock_forms_v3.json"
    )
    source = successor.get("source", {})
    if (
        not isinstance(source, Mapping)
        or source.get("inventory_text_path") != "inventory.txt"
        or source.get("inventory_text_size_bytes") != expected_inventory_size
        or source.get("inventory_text_sha256") != expected_inventory_sha
        or source.get("confirmed_receipt")
        != confirmation_path.relative_to(PROJECT_ROOT).as_posix()
        or source.get("confirmed_receipt_sha256")
        != R5_REMAINING_STOCK_FORMS_V3_CONFIRMATION_SHA256
    ):
        raise InventoryAuthorityError(
            "R5 remaining stock forms v3 successor source drift"
        )
    if require_live_inventory_binding and (
        len(_normalized_text_bytes(INVENTORY_PATH)) != expected_inventory_size
        or _normalized_text_sha256(INVENTORY_PATH) != expected_inventory_sha
    ):
        raise InventoryAuthorityError(
            "R5 remaining stock forms v3 successor is not bound to live inventory text"
        )
    if (
        not confirmation_path.is_file()
        or _file_sha256(confirmation_path)
        != R5_REMAINING_STOCK_FORMS_V3_CONFIRMATION_SHA256
    ):
        raise InventoryAuthorityError(
            "R5 remaining stock forms v3 confirmation receipt drift"
        )
    try:
        confirmation = json.loads(confirmation_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryAuthorityError(
            "R5 remaining stock forms v3 confirmation is unreadable"
        ) from exc
    confirmation_limits = confirmation.get("authority_limits", {})
    normalization = confirmation.get("normalization_rules", {})
    if (
        confirmation.get("schema_version")
        != "perfume_chem_direct_r5_remaining_stock_forms_confirmation_v3"
        or confirmation.get("effective_date") != "2026-09-24"
        or confirmation.get("source_kind") != "DIRECT_USER_MESSAGE"
        or confirmation.get("predecessor")
        != {
            "path": (
                "data/governance/"
                "inventory_user_confirmation_20260924_"
                "r5_stock_clarifications_v2.json"
            ),
            "sha256": R5_STOCK_CLARIFICATIONS_V2_CONFIRMATION_SHA256,
        }
        or len(confirmation.get("message_facts", [])) != 15
        or normalization.get(
            "correct_form_and_ready_does_not_supply_missing_fraction_basis"
        )
        is not True
        or normalization.get("neat_parent_stock_does_not_equal_required_working_dilution")
        is not True
        or confirmation_limits.get("inventory_fact_update_authorized") is not True
        or confirmation_limits.get("physical_compounding_authorized") is not False
        or confirmation_limits.get("working_stock_preparation_authorized") is not False
        or confirmation_limits.get("formula_substitution_authorized") is not False
        or confirmation_limits.get("safety_or_release_asserted") is not False
    ):
        raise InventoryAuthorityError(
            "R5 remaining stock forms v3 evidence scope drift"
        )

    records = successor.get("records", [])
    if not isinstance(records, list) or len(records) != 12:
        raise InventoryAuthorityError(
            "R5 remaining stock forms v3 record count drift"
        )
    records_sha = hashlib.sha256(
        json.dumps(
            records,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    if records_sha != R5_REMAINING_STOCK_FORMS_V3_RECORDS_SHA256:
        raise InventoryAuthorityError(
            "R5 remaining stock forms v3 exact records drift"
        )

    predecessor_path = R5_STOCK_CLARIFICATIONS_V2_USER_INVENTORY_OVERLAY_PATH
    if (
        _normalized_text_sha256(predecessor_path)
        != R5_STOCK_CLARIFICATIONS_V2_USER_INVENTORY_OVERLAY_SHA256
    ):
        raise InventoryAuthorityError(
            "R5 remaining stock forms v3 predecessor drift"
        )
    try:
        predecessor_payload = json.loads(
            predecessor_path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryAuthorityError(
            "R5 remaining stock forms v3 predecessor is unreadable"
        ) from exc
    previous = _load_20260924_r5_stock_clarifications_v2_successor(
        predecessor_payload,
        require_live_inventory_binding=False,
    )
    previous_by_id = {
        str(previous_record["record_id"]): previous_record
        for previous_record in previous["records"]
    }
    missing_superseded = set(expected_superseded).difference(previous_by_id)
    if missing_superseded:
        raise InventoryAuthorityError(
            "R5 remaining stock forms v3 superseded records are missing: "
            + ", ".join(sorted(missing_superseded))
        )
    inherited = [
        previous_record
        for previous_record in previous["records"]
        if previous_record["record_id"] not in expected_superseded
    ]
    origins = {
        key: dict(value)
        for key, value in previous["record_origins"].items()
        if key not in expected_superseded
    }
    origin = {
        "path": (
            "data/governance/"
            "inventory_user_authority_overlay_20260924_"
            "r5_remaining_stock_forms_v3.json"
        ),
        "sha256": R5_REMAINING_STOCK_FORMS_V3_USER_INVENTORY_OVERLAY_SHA256,
    }
    for record in records:
        origins[str(record["record_id"])] = dict(origin)
    return {
        **dict(successor),
        "parent": dict(previous["parent"]),
        "base_policy": dict(previous["base_policy"]),
        "policy": {**dict(previous["policy"]), **expected_policy},
        "delta_records": records,
        "records": [*inherited, *records],
        "record_origins": origins,
        "retired_records": [
            *previous.get("retired_records", []),
            *(previous_by_id[record_id] for record_id in expected_superseded),
        ],
    }


def _load_20260930_aimi_identity_successor(
    successor: Mapping[str, Any],
    *,
    require_live_inventory_binding: bool = True,
) -> dict[str, Any]:
    """Resolve the owned AIMI bottle to the exact PerfumersWorld identity."""

    expected_policy = {
        "predecessor_overlay_immutable": True,
        "preserve_inherited_stock_ids": True,
        "formula_rebase_authorized": False,
        "general_substitution_authorized": False,
        "unknown_metadata_fails_closed": True,
        "bind_only_source_declared_stock_facts": True,
        "supplier_product_identity_does_not_assert_user_lot_assay": True,
        "supplier_product_identity_does_not_assert_density": True,
        "historical_givaudan_aimi_label_is_alias_only": True,
        "one_physical_bottle_only": True,
        "methyl_ionone_gamma_coeur_remains_distinct": True,
        "depleted_stock_not_substitutable": True,
        "safety_or_release_asserted": False,
    }
    expected_predecessor = {
        "path": (
            "data/governance/"
            "inventory_user_authority_overlay_20260924_"
            "r5_remaining_stock_forms_v3.json"
        ),
        "normalized_text_sha256": (
            R5_REMAINING_STOCK_FORMS_V3_USER_INVENTORY_OVERLAY_SHA256
        ),
    }
    expected_superseded = ["INV-USER-20260904-003"]
    if (
        successor.get("schema_version")
        != "perfume_chem_user_inventory_authority_successor_overlay_v18"
        or successor.get("effective_date") != "2026-09-30"
        or successor.get("authority")
        != "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY"
        or successor.get("predecessor") != expected_predecessor
        or successor.get("policy") != expected_policy
        or successor.get("superseded_record_ids") != expected_superseded
    ):
        raise InventoryAuthorityError("AIMI identity successor metadata drift")

    expected_inventory_size = 28082
    expected_inventory_sha = (
        "6b11f3aa198b9483f9f7f9567e362f987a8447b47915853ea22fada66ff3cbe3"
    )
    confirmation_path = (
        PROJECT_ROOT
        / "data/governance/"
        "inventory_user_confirmation_20260930_aimi_identity.json"
    )
    source = successor.get("source", {})
    if (
        not isinstance(source, Mapping)
        or source.get("inventory_text_path") != "inventory.txt"
        or source.get("inventory_text_size_bytes") != expected_inventory_size
        or source.get("inventory_text_sha256") != expected_inventory_sha
        or source.get("confirmed_receipt")
        != confirmation_path.relative_to(PROJECT_ROOT).as_posix()
        or source.get("confirmed_receipt_sha256")
        != AIMI_IDENTITY_CONFIRMATION_SHA256
    ):
        raise InventoryAuthorityError("AIMI identity successor source drift")
    if require_live_inventory_binding and (
        len(_normalized_text_bytes(INVENTORY_PATH)) != expected_inventory_size
        or _normalized_text_sha256(INVENTORY_PATH) != expected_inventory_sha
    ):
        raise InventoryAuthorityError(
            "AIMI identity successor is not bound to live inventory text"
        )
    if (
        not confirmation_path.is_file()
        or _file_sha256(confirmation_path) != AIMI_IDENTITY_CONFIRMATION_SHA256
    ):
        raise InventoryAuthorityError("AIMI identity confirmation receipt drift")
    try:
        confirmation = json.loads(confirmation_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryAuthorityError(
            "AIMI identity confirmation is unreadable"
        ) from exc
    identity = confirmation.get("identity_confirmation", {})
    limits = confirmation.get("authority_limits", {})
    normalization = confirmation.get("normalization_rules", {})
    if (
        confirmation.get("schema_version")
        != "perfume_chem_direct_aimi_identity_confirmation_v1"
        or confirmation.get("effective_date") != "2026-09-30"
        or confirmation.get("source_kind")
        != "DIRECT_USER_MESSAGE_PLUS_OFFICIAL_SUPPLIER_IDENTITY"
        or identity.get("canonical_product_name") != "Alpha Isomethyl Ionone"
        or identity.get("supplier") != "PerfumersWorld"
        or identity.get("supplier_sku") != "3IW00300"
        or identity.get("cas") != "127-51-5"
        or identity.get("owned") is not True
        or identity.get("physical_bottle_count_asserted") != 1
        or normalization.get("methyl_ionone_gamma_coeur_remains_distinct")
        is not True
        or limits.get("inventory_identity_update_authorized") is not True
        or limits.get("ownership_update_authorized") is not True
        or limits.get("exact_user_lot_assay_asserted") is not False
        or limits.get("density_asserted") is not False
        or limits.get("physical_compounding_authorized") is not False
        or limits.get("safety_or_release_asserted") is not False
    ):
        raise InventoryAuthorityError("AIMI identity evidence scope drift")

    records = successor.get("records", [])
    if not isinstance(records, list) or len(records) != 1:
        raise InventoryAuthorityError("AIMI identity record count drift")
    records_sha = hashlib.sha256(
        json.dumps(
            records,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    if records_sha != AIMI_IDENTITY_RECORDS_SHA256:
        raise InventoryAuthorityError("AIMI identity exact records drift")

    predecessor_path = R5_REMAINING_STOCK_FORMS_V3_USER_INVENTORY_OVERLAY_PATH
    if (
        _normalized_text_sha256(predecessor_path)
        != R5_REMAINING_STOCK_FORMS_V3_USER_INVENTORY_OVERLAY_SHA256
    ):
        raise InventoryAuthorityError("AIMI identity predecessor drift")
    try:
        predecessor_payload = json.loads(
            predecessor_path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryAuthorityError("AIMI identity predecessor is unreadable") from exc
    previous = _load_20260924_r5_remaining_stock_forms_v3_successor(
        predecessor_payload,
        require_live_inventory_binding=False,
    )
    previous_by_id = {
        str(previous_record["record_id"]): previous_record
        for previous_record in previous["records"]
    }
    missing_superseded = set(expected_superseded).difference(previous_by_id)
    if missing_superseded:
        raise InventoryAuthorityError(
            "AIMI identity superseded records are missing: "
            + ", ".join(sorted(missing_superseded))
        )
    inherited = [
        previous_record
        for previous_record in previous["records"]
        if previous_record["record_id"] not in expected_superseded
    ]
    origins = {
        key: dict(value)
        for key, value in previous["record_origins"].items()
        if key not in expected_superseded
    }
    origin = {
        "path": (
            "data/governance/"
            "inventory_user_authority_overlay_20260930_aimi_identity.json"
        ),
        "sha256": AIMI_IDENTITY_USER_INVENTORY_OVERLAY_SHA256,
    }
    for record in records:
        origins[str(record["record_id"])] = dict(origin)
    return {
        **dict(successor),
        "parent": dict(previous["parent"]),
        "base_policy": dict(previous["base_policy"]),
        "policy": {**dict(previous["policy"]), **expected_policy},
        "delta_records": records,
        "records": [*inherited, *records],
        "record_origins": origins,
        "retired_records": [
            *previous.get("retired_records", []),
            *(previous_by_id[record_id] for record_id in expected_superseded),
        ],
    }


def _load_20261007_pw_received_successor(
    successor: Mapping[str, Any],
    *,
    require_live_inventory_binding: bool = True,
) -> dict[str, Any]:
    """Bind the received order while retaining predecessor stock identities."""

    encoded = (json.dumps(dict(successor), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if hashlib.sha256(encoded).hexdigest() != PW_RECEIVED_USER_INVENTORY_OVERLAY_SHA256:
        raise InventoryAuthorityError("PW received successor exact metadata drift")
    source = successor["source"]
    if require_live_inventory_binding and (
        len(_normalized_text_bytes(INVENTORY_PATH)) != source["inventory_text_size_bytes"]
        or _normalized_text_sha256(INVENTORY_PATH) != source["inventory_text_sha256"]
    ):
        raise InventoryAuthorityError("PW received successor is not bound to live inventory text")
    receipt_path = PW_RECEIVED_INVENTORY_RECEIPT_PATH
    if not receipt_path.is_file() or _file_sha256(receipt_path) != PW_RECEIVED_INVENTORY_RECEIPT_SHA256:
        raise InventoryAuthorityError("PW received inventory receipt drift")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryAuthorityError("PW received inventory receipt is unreadable") from exc
    receipt_rows = {row["line"]: row for row in receipt["records"]}
    if (
        len(receipt_rows) != 53
        or receipt["authority"]["ownership_confirmed"] is not True
        or receipt["authority"]["quantity_unit_confirmed"] != "g"
        or sum(int(row["received_quantity_g"]) for row in receipt_rows.values()) != 133
    ):
        raise InventoryAuthorityError("PW received inventory confirmation drift")
    records = successor["records"]
    for record in records:
        row = receipt_rows[record["receipt_line"]]
        stock = record["stock"]
        if (
            record["canonical_name"] != row["inventory_identity"]
            or record["supplier_product"]["sku"] != row["supplier_sku"]
            or record["received_quantity_g"] != row["received_quantity_g"]
            or stock["fraction"] != float(row["stock_fraction_decimal"])
            or stock["fraction_basis"] != row["fraction_basis"]
            or stock["carrier"].casefold() != row["carrier"].casefold()
            or stock["execution_ready"] is not False
        ):
            raise InventoryAuthorityError("PW received stock disagrees with source receipt")
    predecessor_path = AIMI_IDENTITY_USER_INVENTORY_OVERLAY_PATH
    if _normalized_text_sha256(predecessor_path) != AIMI_IDENTITY_USER_INVENTORY_OVERLAY_SHA256:
        raise InventoryAuthorityError("PW received inventory predecessor drift")
    previous = _load_20260930_aimi_identity_successor(
        json.loads(predecessor_path.read_text(encoding="utf-8")),
        require_live_inventory_binding=False,
    )
    superseded = set(successor["superseded_record_ids"])
    previous_by_id = {record["record_id"]: record for record in previous["records"]}
    if not superseded.issubset(previous_by_id):
        raise InventoryAuthorityError("PW received inventory superseded record missing")
    origins = {
        key: dict(value)
        for key, value in previous["record_origins"].items()
        if key not in superseded
    }
    origin = {
        "path": PW_RECEIVED_USER_INVENTORY_OVERLAY_PATH.relative_to(PROJECT_ROOT).as_posix(),
        "sha256": PW_RECEIVED_USER_INVENTORY_OVERLAY_SHA256,
    }
    for record in records:
        origins[record["record_id"]] = dict(origin)
    return {
        **dict(successor),
        "parent": dict(previous["parent"]),
        "base_policy": dict(previous["base_policy"]),
        "policy": {**dict(previous["policy"]), **dict(successor["policy"])},
        "delta_records": records,
        "records": [
            *(record for record in previous["records"] if record["record_id"] not in superseded),
            *records,
        ],
        "record_origins": origins,
        "retired_records": [
            *previous.get("retired_records", []),
            *(previous_by_id[record_id] for record_id in sorted(superseded)),
        ],
    }


def _load_20261008_tobacco_dbca_successor(
    successor: Mapping[str, Any],
    *,
    require_live_inventory_binding: bool = True,
) -> dict[str, Any]:
    """Retire the duplicate Tobacco row and bind DBCA's supplier identity."""

    encoded = (json.dumps(dict(successor), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if hashlib.sha256(encoded).hexdigest() != TOBACCO_DBCA_USER_INVENTORY_OVERLAY_SHA256:
        raise InventoryAuthorityError("Tobacco/DBCA successor exact metadata drift")
    source = successor["source"]
    if require_live_inventory_binding and (
        len(_normalized_text_bytes(INVENTORY_PATH)) != source["inventory_text_size_bytes"]
        or _normalized_text_sha256(INVENTORY_PATH) != source["inventory_text_sha256"]
    ):
        raise InventoryAuthorityError("Tobacco/DBCA successor is not bound to live inventory text")
    predecessor_path = PW_RECEIVED_USER_INVENTORY_OVERLAY_PATH
    if _normalized_text_sha256(predecessor_path) != PW_RECEIVED_USER_INVENTORY_OVERLAY_SHA256:
        raise InventoryAuthorityError("Tobacco/DBCA successor predecessor drift")
    previous = _load_20261007_pw_received_successor(
        json.loads(predecessor_path.read_text(encoding="utf-8")),
        require_live_inventory_binding=False,
    )
    records = successor["records"]
    origins = {key: dict(value) for key, value in previous["record_origins"].items()}
    origin = {
        "path": TOBACCO_DBCA_USER_INVENTORY_OVERLAY_PATH.relative_to(PROJECT_ROOT).as_posix(),
        "sha256": TOBACCO_DBCA_USER_INVENTORY_OVERLAY_SHA256,
    }
    for record in records:
        origins[record["record_id"]] = dict(origin)
    return {
        **dict(successor),
        "parent": dict(previous["parent"]),
        "base_policy": dict(previous["base_policy"]),
        "policy": {**dict(previous["policy"]), **dict(successor["policy"])},
        "delta_records": records,
        "records": [*previous["records"], *records],
        "record_origins": origins,
        "retired_records": list(previous.get("retired_records", [])),
    }


def _load_20261008_ambrettolide_neat_successor(
    successor: Mapping[str, Any],
    *,
    require_live_inventory_binding: bool = True,
) -> dict[str, Any]:
    """Replace the 10% w/w DPG Ambrettolide record with the owner's neat stock."""

    encoded = (json.dumps(dict(successor), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if hashlib.sha256(encoded).hexdigest() != AMBRETTOLIDE_NEAT_USER_INVENTORY_OVERLAY_SHA256:
        raise InventoryAuthorityError("Ambrettolide-neat successor exact metadata drift")
    source = successor["source"]
    if require_live_inventory_binding and (
        len(_normalized_text_bytes(INVENTORY_PATH)) != source["inventory_text_size_bytes"]
        or _normalized_text_sha256(INVENTORY_PATH) != source["inventory_text_sha256"]
    ):
        raise InventoryAuthorityError("Ambrettolide-neat successor is not bound to live inventory text")
    predecessor_path = TOBACCO_DBCA_USER_INVENTORY_OVERLAY_PATH
    if _normalized_text_sha256(predecessor_path) != TOBACCO_DBCA_USER_INVENTORY_OVERLAY_SHA256:
        raise InventoryAuthorityError("Ambrettolide-neat successor predecessor drift")
    previous = _load_20261008_tobacco_dbca_successor(
        json.loads(predecessor_path.read_text(encoding="utf-8")),
        require_live_inventory_binding=False,
    )
    superseded = set(successor["superseded_record_ids"])
    previous_by_id = {record["record_id"]: record for record in previous["records"]}
    if not superseded.issubset(previous_by_id):
        raise InventoryAuthorityError("Ambrettolide-neat successor superseded record missing")
    records = successor["records"]
    origins = {
        key: dict(value)
        for key, value in previous["record_origins"].items()
        if key not in superseded
    }
    origin = {
        "path": AMBRETTOLIDE_NEAT_USER_INVENTORY_OVERLAY_PATH.relative_to(PROJECT_ROOT).as_posix(),
        "sha256": AMBRETTOLIDE_NEAT_USER_INVENTORY_OVERLAY_SHA256,
    }
    for record in records:
        origins[record["record_id"]] = dict(origin)
    return {
        **dict(successor),
        "parent": dict(previous["parent"]),
        "base_policy": dict(previous["base_policy"]),
        "policy": {**dict(previous["policy"]), **dict(successor["policy"])},
        "delta_records": records,
        "records": [
            *(record for record in previous["records"] if record["record_id"] not in superseded),
            *records,
        ],
        "record_origins": origins,
        "retired_records": [
            *previous.get("retired_records", []),
            *(previous_by_id[record_id] for record_id in sorted(superseded)),
        ],
    }


def _load_20261008_e2mb_osmanthus_mimosa_successor(
    successor: Mapping[str, Any],
    *,
    require_live_inventory_binding: bool = True,
) -> dict[str, Any]:
    """Declare Osmanthus as w/w, keep Mimosa for use, and add the new E2MB solutions."""

    encoded = (json.dumps(dict(successor), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if hashlib.sha256(encoded).hexdigest() != E2MB_OSMANTHUS_MIMOSA_USER_INVENTORY_OVERLAY_SHA256:
        raise InventoryAuthorityError("E2MB/Osmanthus/Mimosa successor exact metadata drift")
    source = successor["source"]
    if require_live_inventory_binding and (
        len(_normalized_text_bytes(INVENTORY_PATH)) != source["inventory_text_size_bytes"]
        or _normalized_text_sha256(INVENTORY_PATH) != source["inventory_text_sha256"]
    ):
        raise InventoryAuthorityError(
            "E2MB/Osmanthus/Mimosa successor is not bound to live inventory text"
        )
    predecessor_path = AMBRETTOLIDE_NEAT_USER_INVENTORY_OVERLAY_PATH
    if _normalized_text_sha256(predecessor_path) != AMBRETTOLIDE_NEAT_USER_INVENTORY_OVERLAY_SHA256:
        raise InventoryAuthorityError("E2MB/Osmanthus/Mimosa successor predecessor drift")
    previous = _load_20261008_ambrettolide_neat_successor(
        json.loads(predecessor_path.read_text(encoding="utf-8")),
        require_live_inventory_binding=False,
    )
    superseded = set(successor["superseded_record_ids"])
    previous_by_id = {record["record_id"]: record for record in previous["records"]}
    if not superseded.issubset(previous_by_id):
        raise InventoryAuthorityError("E2MB/Osmanthus/Mimosa successor superseded record missing")
    records = successor["records"]
    origins = {
        key: dict(value)
        for key, value in previous["record_origins"].items()
        if key not in superseded
    }
    origin = {
        "path": E2MB_OSMANTHUS_MIMOSA_USER_INVENTORY_OVERLAY_PATH.relative_to(PROJECT_ROOT).as_posix(),
        "sha256": E2MB_OSMANTHUS_MIMOSA_USER_INVENTORY_OVERLAY_SHA256,
    }
    for record in records:
        origins[record["record_id"]] = dict(origin)
    return {
        **dict(successor),
        "parent": dict(previous["parent"]),
        "base_policy": dict(previous["base_policy"]),
        "policy": {**dict(previous["policy"]), **dict(successor["policy"])},
        "delta_records": records,
        "records": [
            *(record for record in previous["records"] if record["record_id"] not in superseded),
            *records,
        ],
        "record_origins": origins,
        "retired_records": [
            *previous.get("retired_records", []),
            *(previous_by_id[record_id] for record_id in sorted(superseded)),
        ],
    }


def _load_20261009_vertofix_coeur_successor(
    successor: Mapping[str, Any],
    *,
    require_live_inventory_binding: bool = True,
) -> dict[str, Any]:
    """Add the PW Vertofix Coeur bottle as its own stock beside the plain V5 Vertofix.

    The 2026-10-07 receipt mapped its line 7 ("Vertofix Couer") onto the V5 row
    242 Vertofix stock. Kenny owns both, so the line now belongs to this record.
    """

    encoded = (json.dumps(dict(successor), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if hashlib.sha256(encoded).hexdigest() != VERTOFIX_COEUR_USER_INVENTORY_OVERLAY_SHA256:
        raise InventoryAuthorityError("Vertofix Coeur successor exact metadata drift")
    source = successor["source"]
    if require_live_inventory_binding and (
        len(_normalized_text_bytes(INVENTORY_PATH)) != source["inventory_text_size_bytes"]
        or _normalized_text_sha256(INVENTORY_PATH) != source["inventory_text_sha256"]
    ):
        raise InventoryAuthorityError("Vertofix Coeur successor is not bound to live inventory text")
    predecessor_path = E2MB_OSMANTHUS_MIMOSA_USER_INVENTORY_OVERLAY_PATH
    if (
        _normalized_text_sha256(predecessor_path)
        != E2MB_OSMANTHUS_MIMOSA_USER_INVENTORY_OVERLAY_SHA256
    ):
        raise InventoryAuthorityError("Vertofix Coeur successor predecessor drift")
    previous = _load_20261008_e2mb_osmanthus_mimosa_successor(
        json.loads(predecessor_path.read_text(encoding="utf-8")),
        require_live_inventory_binding=False,
    )
    superseded = set(successor["superseded_record_ids"])
    previous_by_id = {record["record_id"]: record for record in previous["records"]}
    if not superseded.issubset(previous_by_id):
        raise InventoryAuthorityError("Vertofix Coeur successor superseded record missing")
    receipt_path = PW_RECEIVED_INVENTORY_RECEIPT_PATH
    if not receipt_path.is_file() or _file_sha256(receipt_path) != PW_RECEIVED_INVENTORY_RECEIPT_SHA256:
        raise InventoryAuthorityError("PW received inventory receipt drift")
    receipt_rows = {
        row["line"]: row
        for row in json.loads(receipt_path.read_text(encoding="utf-8"))["records"]
    }
    records = successor["records"]
    for record in records:
        row = receipt_rows.get(record.get("receipt_line"))
        stock = record["stock"]
        if (
            row is None
            or record["supplier_product"]["product_name"] != row["supplier_product_name"]
            or record["supplier_product"]["sku"] != row["supplier_sku"]
            or record["received_quantity_g"] != row["received_quantity_g"]
            or stock["fraction"] != float(row["stock_fraction_decimal"])
            or stock["fraction_basis"] != row["fraction_basis"]
            or stock["carrier"].casefold() != row["carrier"].casefold()
        ):
            raise InventoryAuthorityError("Vertofix Coeur stock disagrees with source receipt")
    origins = {
        key: dict(value)
        for key, value in previous["record_origins"].items()
        if key not in superseded
    }
    origin = {
        "path": VERTOFIX_COEUR_USER_INVENTORY_OVERLAY_PATH.relative_to(PROJECT_ROOT).as_posix(),
        "sha256": VERTOFIX_COEUR_USER_INVENTORY_OVERLAY_SHA256,
    }
    for record in records:
        origins[record["record_id"]] = dict(origin)
    return {
        **dict(successor),
        "parent": dict(previous["parent"]),
        "base_policy": dict(previous["base_policy"]),
        "policy": {**dict(previous["policy"]), **dict(successor["policy"])},
        "delta_records": records,
        "records": [
            *(record for record in previous["records"] if record["record_id"] not in superseded),
            *records,
        ],
        "record_origins": origins,
        "retired_records": [
            *previous.get("retired_records", []),
            *(previous_by_id[record_id] for record_id in sorted(superseded)),
        ],
    }


def _load_20261009_vertofix_coeur_neat_successor(
    successor: Mapping[str, Any],
    *,
    require_live_inventory_binding: bool = True,
) -> dict[str, Any]:
    """Clear the Vertofix Coeur intake hold: Kenny confirmed the bottle is neat as supplied.

    The v23 record held the PW receipt line 7 bottle for intake. Its successor
    record keeps the same identity and receipt facts and is execution-ready for
    raw-stock volume transfer. The plain V5 row 242 Vertofix is untouched.
    """

    encoded = (json.dumps(dict(successor), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if hashlib.sha256(encoded).hexdigest() != CURRENT_USER_INVENTORY_OVERLAY_SHA256:
        raise InventoryAuthorityError("Vertofix Coeur neat successor exact metadata drift")
    source = successor["source"]
    if require_live_inventory_binding and (
        len(_normalized_text_bytes(INVENTORY_PATH)) != source["inventory_text_size_bytes"]
        or _normalized_text_sha256(INVENTORY_PATH) != source["inventory_text_sha256"]
    ):
        raise InventoryAuthorityError("Vertofix Coeur neat successor is not bound to live inventory text")
    predecessor_path = VERTOFIX_COEUR_USER_INVENTORY_OVERLAY_PATH
    if _normalized_text_sha256(predecessor_path) != VERTOFIX_COEUR_USER_INVENTORY_OVERLAY_SHA256:
        raise InventoryAuthorityError("Vertofix Coeur neat successor predecessor drift")
    previous = _load_20261009_vertofix_coeur_successor(
        json.loads(predecessor_path.read_text(encoding="utf-8")),
        require_live_inventory_binding=False,
    )
    superseded = set(successor["superseded_record_ids"])
    previous_by_id = {record["record_id"]: record for record in previous["records"]}
    if not superseded.issubset(previous_by_id):
        raise InventoryAuthorityError("Vertofix Coeur neat successor superseded record missing")
    receipt_path = PW_RECEIVED_INVENTORY_RECEIPT_PATH
    if not receipt_path.is_file() or _file_sha256(receipt_path) != PW_RECEIVED_INVENTORY_RECEIPT_SHA256:
        raise InventoryAuthorityError("PW received inventory receipt drift")
    receipt_rows = {
        row["line"]: row
        for row in json.loads(receipt_path.read_text(encoding="utf-8"))["records"]
    }
    records = successor["records"]
    for record in records:
        row = receipt_rows.get(record.get("receipt_line"))
        stock = record["stock"]
        if (
            row is None
            or record["supplier_product"]["product_name"] != row["supplier_product_name"]
            or record["supplier_product"]["sku"] != row["supplier_sku"]
            or record["received_quantity_g"] != row["received_quantity_g"]
            or stock["fraction"] != float(row["stock_fraction_decimal"])
            or stock["fraction_basis"] != row["fraction_basis"]
            or stock["carrier"].casefold() != row["carrier"].casefold()
        ):
            raise InventoryAuthorityError("Vertofix Coeur neat stock disagrees with source receipt")
    origins = {
        key: dict(value)
        for key, value in previous["record_origins"].items()
        if key not in superseded
    }
    origin = {
        "path": CURRENT_USER_INVENTORY_OVERLAY_PATH.relative_to(PROJECT_ROOT).as_posix(),
        "sha256": CURRENT_USER_INVENTORY_OVERLAY_SHA256,
    }
    for record in records:
        origins[record["record_id"]] = dict(origin)
    return {
        **dict(successor),
        "parent": dict(previous["parent"]),
        "base_policy": dict(previous["base_policy"]),
        "policy": {**dict(previous["policy"]), **dict(successor["policy"])},
        "delta_records": records,
        "records": [
            *(record for record in previous["records"] if record["record_id"] not in superseded),
            *records,
        ],
        "record_origins": origins,
        "retired_records": [
            *previous.get("retired_records", []),
            *(previous_by_id[record_id] for record_id in sorted(superseded)),
        ],
    }


def live_inventory_text_binding() -> dict[str, Any]:
    """Report whether ``inventory.txt`` still matches the current overlay's source text.

    The gate's stock comes from the V5 workbook plus the dated overlays, so this
    binding is a consistency check between the hand-kept list and the structured
    authority. It reports drift; it never raises on it.
    """

    overlay = json.loads(CURRENT_USER_INVENTORY_OVERLAY_PATH.read_text(encoding="utf-8"))
    source = overlay["source"]
    actual_size = len(_normalized_text_bytes(INVENTORY_PATH))
    actual_sha = _normalized_text_sha256(INVENTORY_PATH)
    try:
        inventory_path = INVENTORY_PATH.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        inventory_path = INVENTORY_PATH.as_posix()
    return {
        "bound": (
            actual_size == source["inventory_text_size_bytes"]
            and actual_sha == source["inventory_text_sha256"]
        ),
        "inventory_path": inventory_path,
        "overlay_path": CURRENT_USER_INVENTORY_OVERLAY_PATH.relative_to(PROJECT_ROOT).as_posix(),
        "overlay_effective_date": overlay.get("effective_date"),
        "expected_size_bytes": source["inventory_text_size_bytes"],
        "actual_size_bytes": actual_size,
        "expected_sha256": source["inventory_text_sha256"],
        "actual_sha256": actual_sha,
    }


def load_current_user_inventory_overlay(
    path: Path | None = None,
    *,
    require_pinned_overlay: bool = True,
    require_live_inventory_binding: bool = False,
) -> dict[str, Any]:
    """Load the dated user-authority overlay without mutating the V5 parent.

    By default a hand edit to ``inventory.txt`` does not block the load; use
    :func:`live_inventory_text_binding` to report that drift.  Pass
    ``require_live_inventory_binding=True`` to reject it, as the current
    overlay's own loader does.  Overlay hash pins, predecessor drift and
    metadata drift always raise.
    """

    overlay_path = path or CURRENT_USER_INVENTORY_OVERLAY_PATH
    if not overlay_path.exists():
        raise InventoryAuthorityError(
            f"current user inventory overlay is missing: {overlay_path}"
        )
    overlay_sha = _normalized_text_sha256(overlay_path)
    pinned_overlays = {
        BASE_USER_INVENTORY_OVERLAY_PATH.resolve(): BASE_USER_INVENTORY_OVERLAY_SHA256,
        PREVIOUS_USER_INVENTORY_OVERLAY_PATH.resolve(): PREVIOUS_USER_INVENTORY_OVERLAY_SHA256,
        ORRIS_USER_INVENTORY_OVERLAY_PATH.resolve(): ORRIS_USER_INVENTORY_OVERLAY_SHA256,
        NEROLI_USER_INVENTORY_OVERLAY_PATH.resolve(): NEROLI_USER_INVENTORY_OVERLAY_SHA256,
        RECONCILED_USER_INVENTORY_OVERLAY_PATH.resolve(): RECONCILED_USER_INVENTORY_OVERLAY_SHA256,
        TINCTURES_USER_INVENTORY_OVERLAY_PATH.resolve(): TINCTURES_USER_INVENTORY_OVERLAY_SHA256,
        AHSEE_USER_INVENTORY_OVERLAY_PATH.resolve(): AHSEE_USER_INVENTORY_OVERLAY_SHA256,
        ROMANDOLIDE_USER_INVENTORY_OVERLAY_PATH.resolve(): ROMANDOLIDE_USER_INVENTORY_OVERLAY_SHA256,
        FLORHYDRAL_USER_INVENTORY_OVERLAY_PATH.resolve(): FLORHYDRAL_USER_INVENTORY_OVERLAY_SHA256,
        ROMANDOLIDE_RESTOCK_USER_INVENTORY_OVERLAY_PATH.resolve(): ROMANDOLIDE_RESTOCK_USER_INVENTORY_OVERLAY_SHA256,
        STOCK_CLARIFICATIONS_USER_INVENTORY_OVERLAY_PATH.resolve(): STOCK_CLARIFICATIONS_USER_INVENTORY_OVERLAY_SHA256,
        PINK_PEPPER_USER_INVENTORY_OVERLAY_PATH.resolve(): PINK_PEPPER_USER_INVENTORY_OVERLAY_SHA256,
        STOCK_FORMS_AND_TINCTURE_MODEL_USER_INVENTORY_OVERLAY_PATH.resolve(): (
            STOCK_FORMS_AND_TINCTURE_MODEL_USER_INVENTORY_OVERLAY_SHA256
        ),
        EVERNYL_10WW_DPG_USER_INVENTORY_OVERLAY_PATH.resolve(): (
            EVERNYL_10WW_DPG_USER_INVENTORY_OVERLAY_SHA256
        ),
        METHYL_PAMPLEMOUSSE_10WW_ETHANOL_USER_INVENTORY_OVERLAY_PATH.resolve(): (
            METHYL_PAMPLEMOUSSE_10WW_ETHANOL_USER_INVENTORY_OVERLAY_SHA256
        ),
        R5_STOCK_CLARIFICATIONS_USER_INVENTORY_OVERLAY_PATH.resolve(): (
            R5_STOCK_CLARIFICATIONS_USER_INVENTORY_OVERLAY_SHA256
        ),
        R5_STOCK_CLARIFICATIONS_V2_USER_INVENTORY_OVERLAY_PATH.resolve(): (
            R5_STOCK_CLARIFICATIONS_V2_USER_INVENTORY_OVERLAY_SHA256
        ),
        R5_REMAINING_STOCK_FORMS_V3_USER_INVENTORY_OVERLAY_PATH.resolve(): (
            R5_REMAINING_STOCK_FORMS_V3_USER_INVENTORY_OVERLAY_SHA256
        ),
        AIMI_IDENTITY_USER_INVENTORY_OVERLAY_PATH.resolve(): AIMI_IDENTITY_USER_INVENTORY_OVERLAY_SHA256,
        PW_RECEIVED_USER_INVENTORY_OVERLAY_PATH.resolve(): PW_RECEIVED_USER_INVENTORY_OVERLAY_SHA256,
        TOBACCO_DBCA_USER_INVENTORY_OVERLAY_PATH.resolve(): TOBACCO_DBCA_USER_INVENTORY_OVERLAY_SHA256,
        AMBRETTOLIDE_NEAT_USER_INVENTORY_OVERLAY_PATH.resolve(): AMBRETTOLIDE_NEAT_USER_INVENTORY_OVERLAY_SHA256,
        E2MB_OSMANTHUS_MIMOSA_USER_INVENTORY_OVERLAY_PATH.resolve(): (
            E2MB_OSMANTHUS_MIMOSA_USER_INVENTORY_OVERLAY_SHA256
        ),
        VERTOFIX_COEUR_USER_INVENTORY_OVERLAY_PATH.resolve(): VERTOFIX_COEUR_USER_INVENTORY_OVERLAY_SHA256,
        CURRENT_USER_INVENTORY_OVERLAY_PATH.resolve(): CURRENT_USER_INVENTORY_OVERLAY_SHA256,
    }
    expected_overlay_sha = pinned_overlays.get(overlay_path.resolve(), CURRENT_USER_INVENTORY_OVERLAY_SHA256)
    if require_pinned_overlay and overlay_sha != expected_overlay_sha:
        raise InventoryAuthorityError(
            "current user inventory overlay hash drift: "
            f"expected {expected_overlay_sha}, got {overlay_sha}"
        )
    try:
        payload = json.loads(overlay_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryAuthorityError(
            f"current user inventory overlay is unreadable: {exc}"
        ) from exc

    bind_live_text = require_live_inventory_binding and (
        overlay_path.resolve() == CURRENT_USER_INVENTORY_OVERLAY_PATH.resolve()
    )
    if payload.get("schema_version") == "perfume_chem_user_inventory_authority_successor_overlay_v24":
        return _load_20261009_vertofix_coeur_neat_successor(
            payload,
            require_live_inventory_binding=bind_live_text,
        )
    if payload.get("schema_version") == "perfume_chem_user_inventory_authority_successor_overlay_v23":
        return _load_20261009_vertofix_coeur_successor(
            payload,
            require_live_inventory_binding=bind_live_text,
        )
    if payload.get("schema_version") == "perfume_chem_user_inventory_authority_successor_overlay_v22":
        return _load_20261008_e2mb_osmanthus_mimosa_successor(
            payload,
            require_live_inventory_binding=bind_live_text,
        )
    if payload.get("schema_version") == "perfume_chem_user_inventory_authority_successor_overlay_v21":
        return _load_20261008_ambrettolide_neat_successor(
            payload,
            require_live_inventory_binding=bind_live_text,
        )
    if payload.get("schema_version") == "perfume_chem_user_inventory_authority_successor_overlay_v20":
        return _load_20261008_tobacco_dbca_successor(
            payload,
            require_live_inventory_binding=bind_live_text,
        )
    if payload.get("schema_version") == "perfume_chem_user_inventory_authority_successor_overlay_v19":
        return _load_20261007_pw_received_successor(
            payload,
            require_live_inventory_binding=bind_live_text,
        )
    if (
        payload.get("schema_version")
        == "perfume_chem_user_inventory_authority_successor_overlay_v18"
    ):
        return _load_20260930_aimi_identity_successor(
            payload,
            require_live_inventory_binding=bind_live_text,
        )
    if (
        payload.get("schema_version")
        == "perfume_chem_user_inventory_authority_successor_overlay_v17"
    ):
        return _load_20260924_r5_remaining_stock_forms_v3_successor(
            payload,
            require_live_inventory_binding=bind_live_text,
        )
    if (
        payload.get("schema_version")
        == "perfume_chem_user_inventory_authority_successor_overlay_v16"
    ):
        return _load_20260924_r5_stock_clarifications_v2_successor(
            payload,
            require_live_inventory_binding=bind_live_text,
        )
    if (
        payload.get("schema_version")
        == "perfume_chem_user_inventory_authority_successor_overlay_v15"
    ):
        return _load_20260924_r5_stock_clarifications_successor(
            payload,
            require_live_inventory_binding=bind_live_text,
        )
    if (
        payload.get("schema_version")
        == "perfume_chem_user_inventory_authority_successor_overlay_v14"
    ):
        return _load_20260915_methyl_pamplemousse_10ww_ethanol_successor(
            payload,
            require_live_inventory_binding=bind_live_text,
        )
    if payload.get("schema_version") == "perfume_chem_user_inventory_authority_successor_overlay_v13":
        return _load_20260915_evernyl_10ww_dpg_successor(
            payload,
            require_live_inventory_binding=bind_live_text,
        )
    if payload.get("schema_version") == "perfume_chem_user_inventory_authority_successor_overlay_v12":
        return _load_20260915_stock_forms_and_tincture_model_successor(
            payload,
            require_live_inventory_binding=bind_live_text,
        )
    if payload.get("schema_version") == "perfume_chem_user_inventory_authority_successor_overlay_v11":
        return _load_20260915_pink_pepper_inventory_successor(
            payload,
            require_live_inventory_binding=bind_live_text,
        )
    if payload.get("schema_version") == "perfume_chem_user_inventory_authority_successor_overlay_v10":
        return _load_20260910_stock_clarification_inventory_successor(payload)
    if payload.get("schema_version") == "perfume_chem_user_inventory_authority_successor_overlay_v9":
        return _load_20260910_romandolide_restock_inventory_successor(payload)
    if payload.get("schema_version") == "perfume_chem_user_inventory_authority_successor_overlay_v8":
        return _load_20260910_florhydral_inventory_successor(payload)
    if payload.get("schema_version") == "perfume_chem_user_inventory_authority_successor_overlay_v7":
        return _load_20260908_romandolide_inventory_successor(payload)
    if payload.get("schema_version") == "perfume_chem_user_inventory_authority_successor_overlay_v6":
        return _load_20260908_ahsee_inventory_successor(payload)
    if payload.get("schema_version") == "perfume_chem_user_inventory_authority_successor_overlay_v5":
        return _load_20260908_user_inventory_successor(payload)
    if payload.get("schema_version") == "perfume_chem_user_inventory_authority_successor_overlay_v4":
        return _load_20260907_user_inventory_successor(payload)
    if (
        payload.get("schema_version")
        == "perfume_chem_user_inventory_authority_successor_overlay_v3"
    ):
        return _load_20260906_user_inventory_successor(payload)
    if (
        payload.get("schema_version")
        == "perfume_chem_user_inventory_authority_successor_overlay_v2"
    ):
        return _load_20260905_user_inventory_successor(payload)
    if (
        payload.get("schema_version")
        == "perfume_chem_user_inventory_authority_successor_overlay_v1"
    ):
        return _load_20260904_user_inventory_successor(payload)

    parent = payload.get("parent")
    source = payload.get("source")
    policy = payload.get("policy")
    records = payload.get("records")
    if (
        payload.get("schema_version")
        != "perfume_chem_user_inventory_authority_overlay_v1"
        or payload.get("authority") != "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY"
        or payload.get("effective_date") != "2026-08-28"
        or not isinstance(parent, Mapping)
        or not isinstance(source, Mapping)
        or not isinstance(policy, Mapping)
        or not isinstance(records, list)
    ):
        raise InventoryAuthorityError("current user inventory overlay metadata is invalid")
    expected_parent = {
        "authority": CURRENT_INVENTORY_AUTHORITY,
        "workbook_sha256": CURRENT_INVENTORY_WORKBOOK_SHA256,
        "snapshot_sha256": CURRENT_INVENTORY_SNAPSHOT_SHA256,
    }
    if dict(parent) != expected_parent:
        raise InventoryAuthorityError("current user inventory overlay parent pin is invalid")
    if (
        source.get("kind") != "USER_AUTHORITATIVE_CROSS_TASK_HANDOFF"
        or source.get("source_thread_id")
        != "01a03ee5-7db4-7083-a396-fb1207225757"
        or source.get("inventory_text_path") != "inventory.txt"
        or source.get("inventory_text_size_bytes")
        != BASE_USER_INVENTORY_TEXT_SIZE_BYTES
        or source.get("inventory_text_sha256") != BASE_USER_INVENTORY_TEXT_SHA256
    ):
        raise InventoryAuthorityError(
            "base user inventory overlay historical source binding is invalid"
        )
    expected_policy = {
        "parent_snapshot_immutable": True,
        "merge_other_task_branch": False,
        "formula_rebase_authorized": False,
        "general_substitution_authorized": False,
        "preserve_exact_ap_t1_cinnamon_substitution": True,
        "require_sub_10_ul_working_stock": True,
        "unknown_fraction_fails_closed": True,
        "unlisted_tinctures_available": False,
    }
    if dict(policy) != expected_policy:
        raise InventoryAuthorityError("current user inventory overlay policy drift")

    expected_ids = {
        *(f"INV-USER-20260828-{index:03d}" for index in range(1, 16)),
        "INV-USER-20260829-001",
        "INV-USER-20260829-002",
        "INV-USER-20260829-003",
        *(f"INV-USER-20260830-{index:03d}" for index in range(1, 12)),
    }
    observed_ids: set[str] = set()
    observed_names: set[str] = set()
    allowed_states = {"OWNED", "UNAVAILABLE", "IDENTITY_ALIAS"}
    allowed_bases = {"neat", "mass_fraction", "volume_fraction", "mass_per_volume", "unspecified"}
    for record in records:
        if not isinstance(record, Mapping):
            raise InventoryAuthorityError("current user inventory overlay record is invalid")
        record_id = str(record.get("record_id") or "")
        canonical_name = str(record.get("canonical_name") or "").strip()
        state = str(record.get("state") or "")
        aliases = record.get("aliases")
        selectors = record.get("supersedes_parent_stocks")
        overrides = record.get("requirement_overrides")
        if (
            not record_id
            or not canonical_name
            or record_id in observed_ids
            or canonical_name.casefold() in observed_names
            or state not in allowed_states
            or not isinstance(aliases, list)
            or not isinstance(selectors, list)
            or not isinstance(overrides, list)
        ):
            raise InventoryAuthorityError("current user inventory overlay record shape is invalid")
        stock = record.get("stock")
        if state == "OWNED":
            if not isinstance(stock, Mapping):
                raise InventoryAuthorityError("owned overlay record requires one stock")
            fraction = stock.get("fraction")
            if (
                (
                    fraction is not None
                    and (
                        not isinstance(fraction, (int, float))
                        or not 0.0 < float(fraction) <= 1.0
                    )
                )
                or (fraction is None and stock.get("execution_ready") is not False)
                or stock.get("fraction_basis") not in allowed_bases
                or not isinstance(stock.get("carrier"), str)
                or not isinstance(stock.get("fraction_authority"), str)
                or not isinstance(stock.get("execution_ready"), bool)
                or (
                    stock.get("execution_ready") is False
                    and not str(stock.get("execution_hold_reason") or "").strip()
                )
            ):
                raise InventoryAuthorityError("owned overlay stock declaration is invalid")
        elif stock is not None:
            raise InventoryAuthorityError("non-stock overlay record cannot declare a stock")
        for selector in selectors:
            if (
                not isinstance(selector, Mapping)
                or not isinstance(selector.get("source_row"), int)
                or int(selector["source_row"]) <= 0
                or (
                    "fraction" in selector
                    and (
                        not isinstance(selector["fraction"], (int, float))
                        or not 0.0 < float(selector["fraction"]) <= 1.0
                    )
                )
            ):
                raise InventoryAuthorityError("overlay parent-stock selector is invalid")
        for override in overrides:
            if (
                not isinstance(override, Mapping)
                or set(override)
                != {
                    "source_row",
                    "disposition",
                    "status",
                    "actual_stock_text",
                    "can_prepare",
                }
                or not isinstance(override.get("source_row"), int)
                or int(override["source_row"]) <= 0
                or override.get("disposition")
                not in {"OWNED", "GAP", "PREPARATION_REQUIRED", "UNRESOLVED"}
            ):
                raise InventoryAuthorityError("overlay requirement override is invalid")
        observed_ids.add(record_id)
        observed_names.add(canonical_name.casefold())
    if observed_ids != expected_ids:
        raise InventoryAuthorityError("current user inventory overlay record set is incomplete")

    ambrofix = next(
        (record for record in records if record.get("record_id") == "INV-USER-20260829-001"),
        None,
    )
    expected_mass_balance = {
        "empty_bottle_g": 11.45,
        "final_bottle_g": 14.09,
        "contents_g": 2.64,
        "added_ethanol_g": 2.0,
        "original_30pct_stock_g": 0.64,
        "ambrofix_g": 0.192,
        "dep_g": 0.448,
        "ethanol_g": 2.0,
        "nominal_whole_bottle_mass_fraction": 0.07272727272727272,
        "prior_withdrawal": False,
    }
    expected_authority_limits = {
        "whole_bottle_including_solid_only": True,
        "liquid_phase_strength_known": False,
        "active_ul_ppm_oav_math_authorized": False,
        "volume_dose_math_authorized": False,
        "formula_rebase_authorized": False,
        "procurement_authorized": False,
        "stock_preparation_authorized": False,
        "compounding_authorized": False,
        "sensory_tested": False,
        "performance_tested": False,
        "safety_tested": False,
        "stability_tested": False,
        "release_authorized": False,
    }
    if (
        not isinstance(ambrofix, Mapping)
        or ambrofix.get("effective_date") != "2026-08-29"
        or ambrofix.get("source_thread_id")
        != "01a04493-752a-79e1-99ff-26f0a47fd079"
        or ambrofix.get("mass_balance") != expected_mass_balance
        or ambrofix.get("authority_limits") != expected_authority_limits
        or ambrofix.get("stock", {}).get("fraction")
        != expected_mass_balance["nominal_whole_bottle_mass_fraction"]
        or ambrofix.get("stock", {}).get("fraction_basis") != "mass_fraction"
        or ambrofix.get("stock", {}).get("carrier") != "dep + ethanol"
        or ambrofix.get("stock", {}).get("execution_ready") is not False
        or ambrofix.get("stock", {}).get("execution_hold_reason")
        != "VISIBLE_CRYSTALS_LIQUID_PHASE_STRENGTH_UNKNOWN"
    ):
        raise InventoryAuthorityError("Ambrofix current-stock authority contract drift")

    bacdanol = next(
        (record for record in records if record.get("record_id") == "INV-USER-20260829-002"),
        None,
    )
    expected_bacdanol_limits = {
        "availability_confirmed": True,
        "formulation_selection_ready": True,
        "stock_fraction_known": False,
        "fraction_basis_known": False,
        "carrier_known": False,
        "quantitative_dosing_ready": False,
        "supplier_asserted": False,
        "purity_asserted": False,
        "density_asserted": False,
        "safety_asserted": False,
        "sensory_equivalence_asserted": False,
    }
    if (
        not isinstance(bacdanol, Mapping)
        or bacdanol.get("canonical_name") != "Bacdanol"
        or bacdanol.get("aliases") != ["Bacnadol"]
        or bacdanol.get("effective_date") != "2026-08-29"
        or bacdanol.get("source_thread_id")
        != "01a041bd-477c-75e3-be6b-7e3136bf5990"
        or bacdanol.get("authority_limits") != expected_bacdanol_limits
        or bacdanol.get("stock", {}).get("fraction") is not None
        or bacdanol.get("stock", {}).get("fraction_basis") != "unspecified"
        or bacdanol.get("stock", {}).get("carrier") != ""
        or bacdanol.get("stock", {}).get("execution_ready") is not False
        or bacdanol.get("stock", {}).get("execution_hold_reason")
        != "STOCK_FRACTION_UNSPECIFIED"
    ):
        raise InventoryAuthorityError("Bacdanol current-stock authority contract drift")

    guaiacwood = next(
        (record for record in records if record.get("record_id") == "INV-USER-20260829-003"),
        None,
    )
    expected_guaiacwood_limits = {
        "availability_confirmed": True,
        "formulation_selection_ready": True,
        "stock_fraction_known": True,
        "fraction_basis_known": False,
        "carrier_known": False,
        "quantitative_dosing_ready": False,
        "supplier_asserted": False,
        "purity_asserted": False,
        "density_asserted": False,
        "safety_asserted": False,
        "stability_asserted": False,
        "sensory_equivalence_asserted": False,
        "release_success_asserted": False,
    }
    if (
        not isinstance(guaiacwood, Mapping)
        or guaiacwood.get("canonical_name") != "Guaiacwood EO"
        or guaiacwood.get("effective_date") != "2026-08-29"
        or guaiacwood.get("source_thread_id")
        != "01a041bd-477c-75e3-be6b-7e3136bf5990"
        or guaiacwood.get("authority_limits") != expected_guaiacwood_limits
        or guaiacwood.get("stock", {}).get("fraction") != 0.33
        or guaiacwood.get("stock", {}).get("fraction_basis") != "unspecified"
        or guaiacwood.get("stock", {}).get("carrier") != ""
        or guaiacwood.get("stock", {}).get("execution_ready") is not False
        or guaiacwood.get("stock", {}).get("execution_hold_reason")
        != "FRACTION_BASIS_AND_CARRIER_UNSPECIFIED"
    ):
        raise InventoryAuthorityError("Guaiacwood EO current-stock authority contract drift")

    expected_v7_recovered_stocks = {
        "INV-USER-20260830-008": ("Liffarome", [], 0.1),
        "INV-USER-20260830-009": (
            "Cis-3-Hexenyl Salicylate",
            ["Cis-3 Hexenyl Salicylate"],
            0.2,
        ),
        "INV-USER-20260830-010": ("Caryophyllene Acetate", [], 0.2),
    }
    expected_v7_recovered_limits = {
        "availability_confirmed": True,
        "formulation_selection_ready": True,
        "only_current_working_concentration_confirmed": True,
        "neat_current_stock_owned": False,
        "parallel_current_stock_authorized": False,
        "stock_fraction_known": True,
        "fraction_basis_known": True,
        "carrier_known": False,
        "quantitative_dosing_ready": False,
        "supplier_asserted": False,
        "purity_asserted": False,
        "density_asserted": False,
        "safety_asserted": False,
        "stability_asserted": False,
        "sensory_equivalence_asserted": False,
        "release_success_asserted": False,
        "historical_formula_rebase_authorized": False,
    }
    records_by_id = {str(record.get("record_id")): record for record in records}
    for record_id, (canonical_name, aliases, fraction) in expected_v7_recovered_stocks.items():
        recovered = records_by_id.get(record_id)
        if (
            not isinstance(recovered, Mapping)
            or recovered.get("canonical_name") != canonical_name
            or recovered.get("aliases") != aliases
            or recovered.get("state") != "OWNED"
            or recovered.get("effective_date") != "2026-08-30"
            or recovered.get("source_conversation_id")
            != "6a8b30b9-0a2c-83ec-b485-fcb1aabc6790"
            or recovered.get("authority_limits") != expected_v7_recovered_limits
            or recovered.get("stock", {}).get("fraction") != fraction
            or recovered.get("stock", {}).get("fraction_basis") != "mass_fraction"
            or recovered.get("stock", {}).get("carrier") != ""
            or recovered.get("stock", {}).get("fraction_authority")
            != "EXPLICIT_USER_ASSERTION"
            or recovered.get("stock", {}).get("execution_ready") is not False
            or recovered.get("stock", {}).get("execution_hold_reason")
            != "CARRIER_UNSPECIFIED"
        ):
            raise InventoryAuthorityError(
                f"{canonical_name} recovered V7 current-stock authority contract drift"
            )

    clearwood = next(
        (record for record in records if record.get("record_id") == "INV-USER-20260828-009"),
        None,
    )
    expected_clearwood_limits = {
        "availability_confirmed": True,
        "formulation_selection_ready": True,
        "stock_fraction_known": True,
        "fraction_basis_known": True,
        "carrier_required": False,
        "quantitative_dosing_ready": True,
        "supplier_asserted": False,
        "purity_asserted": False,
        "density_asserted": False,
        "safety_asserted": False,
        "stability_asserted": False,
        "sensory_equivalence_asserted": False,
        "release_success_asserted": False,
    }
    if (
        not isinstance(clearwood, Mapping)
        or clearwood.get("canonical_name") != "Clearwood"
        or clearwood.get("state") != "OWNED"
        or clearwood.get("effective_date") != "2026-08-29"
        or clearwood.get("source_thread_id")
        != "01a041bd-477c-75e3-be6b-7e3136bf5990"
        or clearwood.get("authority_limits") != expected_clearwood_limits
        or clearwood.get("stock")
        != {
            "fraction": 1.0,
            "fraction_basis": "neat",
            "carrier": "",
            "fraction_authority": "EXPLICIT_USER_ASSERTION",
            "execution_ready": True,
        }
    ):
        raise InventoryAuthorityError("Clearwood current-stock authority contract drift")
    return payload


def _overlay_selector_matches(
    record: InventoryMaterial,
    selector: Mapping[str, Any],
) -> bool:
    if int(selector["source_row"]) not in record.source_rows:
        return False
    if "fraction" not in selector:
        return True
    return abs(record.dilution - float(selector["fraction"])) <= 1e-12


def _apply_current_user_inventory_overlay(
    materialized: CurrentInventoryMaterialization,
    payload: Mapping[str, Any],
) -> CurrentInventoryMaterialization:
    """Apply exact stock selectors and additions from the validated overlay."""

    records = list(payload["records"])
    head_record_ids = {
        str(record.get("record_id") or "")
        for record in payload.get("delta_records", [])
        if isinstance(record, Mapping)
    }
    selectors = [
        selector
        for record in records
        for selector in record["supersedes_parent_stocks"]
    ]
    removed_selectors: set[tuple[int, float | None]] = set()
    retained_stocks: list[InventoryMaterial] = []
    for stock in materialized.stocks:
        matched = False
        for selector in selectors:
            if _overlay_selector_matches(stock, selector):
                removed_selectors.add(
                    (
                        int(selector["source_row"]),
                        float(selector["fraction"])
                        if "fraction" in selector
                        else None,
                    )
                )
                matched = True
                # A broad row selector and an exact-fraction selector can both
                # describe a retired stock. Record every real match so dated
                # successor order cannot hide one of the validated selectors.
        if not matched:
            retained_stocks.append(stock)

    expected_selectors = {
        (
            int(selector["source_row"]),
            float(selector["fraction"]) if "fraction" in selector else None,
        )
        for selector in selectors
    }
    if removed_selectors != expected_selectors:
        raise InventoryAuthorityError(
            "current user inventory overlay no longer matches every parent-stock selector"
        )

    overrides_by_row = {
        int(override["source_row"]): override
        for record in records
        for override in record["requirement_overrides"]
    }
    if len(overrides_by_row) != sum(
        len(record["requirement_overrides"]) for record in records
    ):
        raise InventoryAuthorityError("overlay requirement rows are duplicated")
    observed_override_rows: set[int] = set()
    requirements: list[InventoryRequirement] = []
    for requirement in materialized.requirements:
        override = overrides_by_row.get(requirement.source_row)
        if override is None:
            requirements.append(requirement)
            continue
        observed_override_rows.add(requirement.source_row)
        requirements.append(
            replace(
                requirement,
                disposition=str(override["disposition"]),
                status=str(override["status"]),
                actual_stock_text=str(override["actual_stock_text"]),
                can_prepare=str(override["can_prepare"]),
            )
        )
    if observed_override_rows != set(overrides_by_row):
        raise InventoryAuthorityError(
            "current user inventory overlay no longer matches every parent requirement row"
        )

    for record in records:
        if record["state"] != "OWNED":
            continue
        stock = record["stock"]
        record_id = str(record["record_id"])
        canonical_name = str(record["canonical_name"])
        parent_rows = {
            int(selector["source_row"])
            for selector in record["supersedes_parent_stocks"]
        } | {
            int(override["source_row"])
            for override in record["requirement_overrides"]
        }
        origin_overlay_sha256 = (
            PREVIOUS_USER_INVENTORY_OVERLAY_SHA256
            if record_id in head_record_ids
            else BASE_USER_INVENTORY_OVERLAY_SHA256
        )
        origin_path = (
            "data/governance/inventory_user_authority_overlay_20260904.json"
            if record_id in head_record_ids
            else "data/governance/inventory_user_authority_overlay_20260828.json"
        )
        origin = payload.get("record_origins", {}).get(record_id)
        if origin is not None:
            origin_overlay_sha256 = str(origin["sha256"])
            origin_path = str(origin["path"])
        stock_digest = hashlib.sha256(
            f"{origin_overlay_sha256}|{record_id}".encode("utf-8")
        ).hexdigest()[:20]
        authority_date = record_id.split("-")[2]
        raw_fraction = stock.get("fraction")
        fraction = float(raw_fraction) if raw_fraction is not None else 0.0
        basis = str(stock["fraction_basis"])
        carrier = str(stock["carrier"])
        physical_form = str(stock.get("physical_form") or "")
        descriptor = (
            "crystals / neat / as supplied"
            if physical_form == "crystals"
            else "neat / as supplied"
            if fraction == 1.0
            else (
                "owned / stock fraction unspecified"
                if raw_fraction is None
                else f"{fraction * 100:g}% in {carrier.upper() or 'carrier unstated'}"
            )
        )
        retained_stocks.append(
            InventoryMaterial(
                name=canonical_name,
                dilution=fraction,
                category=str(record["category"]),
                raw_name=descriptor,
                status="owned",
                fraction_basis=basis,
                carrier=carrier,
                physical_form=physical_form,
                approximate=bool(stock.get("approximate", False)),
                identity_name=_v5_identity_name(canonical_name),
                stock_id=f"inventory:user-{authority_date}:{stock_digest}",
                authority=(
                    VERTOFIX_COEUR_USER_INVENTORY_AUTHORITY
                    if authority_date == "20261009"
                    else TOBACCO_DBCA_USER_INVENTORY_AUTHORITY
                    if authority_date == "20261008"
                    else "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY_20261007"
                    if authority_date == "20261007"
                    else AIMI_IDENTITY_USER_INVENTORY_AUTHORITY
                    if authority_date == "20260930"
                    else R5_STOCK_CLARIFICATIONS_USER_INVENTORY_AUTHORITY
                    if authority_date == "20260924"
                    else
                    STOCK_FORMS_USER_INVENTORY_AUTHORITY
                    if authority_date == "20260915"
                    else
                    PINK_PEPPER_USER_INVENTORY_AUTHORITY
                    if authority_date == "20260903"
                    else FLORHYDRAL_USER_INVENTORY_AUTHORITY
                    if authority_date == "20260910"
                    else CURRENT_USER_INVENTORY_AUTHORITY
                    if authority_date == "20260908"
                    else "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY_20260907"
                ),
                source_rows=tuple(sorted(parent_rows)),
                source_ref=f"{origin_path}#{record_id}",
                execution_ready=bool(stock["execution_ready"]),
                execution_hold_reason=str(stock.get("execution_hold_reason") or ""),
                nominal_property_model_ready=bool(
                    stock.get("nominal_property_model_ready", False)
                ),
                nominal_property_model_limit=str(
                    stock.get("nominal_property_model_limit") or ""
                ),
            )
        )

    return CurrentInventoryMaterialization(
        stocks=tuple(
            sorted(
                retained_stocks,
                key=lambda stock: (
                    stock.source_rows,
                    stock.identity_name.lower(),
                    stock.stock_id,
                ),
            )
        ),
        requirements=tuple(requirements),
        source_workbook_sha256=materialized.source_workbook_sha256,
        snapshot_sha256=materialized.snapshot_sha256,
        overlay_sha256=CURRENT_USER_INVENTORY_OVERLAY_SHA256,
    )


def _materialize_current_inventory_uncached(
    path: Path | None = None,
    *,
    require_pinned_snapshot: bool = True,
    apply_user_overlay: bool = True,
    require_pinned_overlay: bool = True,
    apply_user_completions: bool = True,
    dilution_path: Path | None = None,
) -> CurrentInventoryMaterialization:
    """Materialize immutable V5 stocks plus the pinned user successor overlay."""

    snapshot_path = path or CURRENT_INVENTORY_SNAPSHOT_PATH
    payload = load_current_inventory_snapshot(
        snapshot_path,
        require_pinned_snapshot=require_pinned_snapshot,
    )
    stock_by_fingerprint: dict[tuple[str, float, str, str, str], InventoryMaterial] = {}
    requirements: list[InventoryRequirement] = []
    for raw_row in payload["records"]:
        row = dict(raw_row)
        source_row = int(row.get("_source_row") or 0)
        canonical = str(row.get("Canonical material") or "").strip()
        if not canonical or source_row <= 0:
            continue
        identity = _v5_identity_name(canonical)
        status = str(row.get("Status") or "").strip()
        actual = str(row.get("Actual stock(s)") or "").strip()
        can_prepare = str(row.get("Can prepare") or "").strip()
        category = str(row.get("Family") or "").strip().lower()
        actual_specs = _actual_stock_specs(actual, status)
        requested = _requested_stock_spec(row, actual_specs)
        disposition = _requirement_disposition(
            status,
            requested,
            actual_specs,
            can_prepare,
        )
        requirements.append(
            InventoryRequirement(
                canonical_name=canonical,
                identity_name=identity,
                requested_fraction=requested.fraction if requested else None,
                fraction_basis=requested.fraction_basis if requested else "unspecified",
                carrier=requested.carrier if requested else "",
                disposition=disposition,
                source_row=source_row,
                status=status,
                actual_stock_text=actual,
                can_prepare=can_prepare,
                category=category,
            )
        )

        upper = status.upper()
        if not upper.startswith("HAVE") or any(
            token in upper for token in ("DIFFERENT MATERIAL", "VIA NAGARMOTHA")
        ):
            continue
        for spec, descriptor in actual_specs:
            descriptor_key = re.sub(r"\s+", " ", descriptor.strip().lower())
            distinct_stock_marker = descriptor_key if any(
                token in upper
                for token in (
                    "MULTIPLE",
                    "TWO PRODUCTS",
                    "LOT",
                    "IDENTITY KEPT SEPARATE",
                )
            ) else ""
            fingerprint = (
                identity.lower(),
                round(spec.fraction, 12),
                spec.fraction_basis,
                spec.carrier,
                distinct_stock_marker,
            )
            existing = stock_by_fingerprint.get(fingerprint)
            if existing is not None:
                stock_by_fingerprint[fingerprint] = replace(
                    existing,
                    source_rows=tuple(sorted(set(existing.source_rows) | {source_row})),
                )
                continue
            stock_digest = hashlib.sha256(
                (
                    f"{CURRENT_INVENTORY_WORKBOOK_SHA256}|{identity.lower()}|"
                    f"{spec.fraction:.12g}|{spec.fraction_basis}|{spec.carrier}|"
                    f"{distinct_stock_marker}"
                ).encode("utf-8")
            ).hexdigest()[:20]
            stock_by_fingerprint[fingerprint] = InventoryMaterial(
                name=canonical,
                dilution=spec.fraction,
                category=category,
                raw_name=descriptor,
                status="owned",
                fraction_basis=spec.fraction_basis,
                carrier=spec.carrier,
                approximate=spec.approximate,
                identity_name=identity,
                stock_id=f"inventory:v5:{stock_digest}",
                authority=CURRENT_INVENTORY_AUTHORITY,
                source_rows=(source_row,),
                source_ref=f"Current Inventory Master!A{source_row}:N{source_row}",
                execution_ready=_stock_execution_ready(
                    status,
                    spec,
                    descriptor,
                    stock_count=len(actual_specs),
                ),
                row_unresolved_tokens="|".join(
                    row_wide_unresolved_tokens(f"{status} {descriptor}")
                ),
            )

    stocks = tuple(
        sorted(
            stock_by_fingerprint.values(),
            key=lambda record: (record.source_rows, record.identity_name.lower(), record.stock_id),
        )
    )
    materialized = CurrentInventoryMaterialization(
        stocks=stocks,
        requirements=tuple(requirements),
        source_workbook_sha256=str(payload["source"]["sha256"]),
        snapshot_sha256=_file_sha256(snapshot_path),
    )
    if apply_user_overlay:
        overlay = load_current_user_inventory_overlay(
            require_pinned_overlay=require_pinned_overlay,
        )
        materialized = _apply_current_user_inventory_overlay(materialized, overlay)
    if apply_user_completions:
        from engine.inventory_completions import apply_inventory_completion_events

        materialized = apply_inventory_completion_events(materialized)
        from engine.inventory_dilutions import apply_prepared_dilution_events

        materialized = apply_prepared_dilution_events(materialized, dilution_path)
    elif not materialized.effective_inventory_sha256:
        materialized = replace(
            materialized,
            effective_inventory_sha256=hashlib.sha256(
                f"{materialized.snapshot_sha256}|{materialized.overlay_sha256}|".encode(
                    "utf-8"
                )
            ).hexdigest(),
        )
    if apply_user_overlay:
        stocks, hold_sha = apply_user_compounding_holds(materialized.stocks)
        materialized = replace(
            materialized,
            stocks=stocks,
            effective_inventory_sha256=hashlib.sha256(
                f"{materialized.effective_inventory_sha256}|{hold_sha}".encode("utf-8")
            ).hexdigest(),
        )
    return replace(materialized, stocks=_strength_display_names(materialized.stocks))


_NAME_PERCENT_RE = re.compile(r"(?<![\d.,])(\d+(?:[.,]\d+)?)\s*%")
_TRAILING_STRENGTHS_RE = re.compile(
    r"(?:\s*(?:\+|&|\band\b|~?\d+(?:[.,]\d+)?\s*%))+\s*$", re.IGNORECASE
)


def _strength_label(dilution: float) -> str:
    if dilution >= 1.0:
        return "(neat)"
    return f"{dilution * 100:.6g}%"


def _strength_display_names(
    stocks: tuple[InventoryMaterial, ...],
) -> tuple[InventoryMaterial, ...]:
    """Rename stocks whose name states a wrong strength or names another bottle.

    Only ``name`` changes. A name keeps its text when every percentage in it
    equals the stored dilution and no other stock carries the same name;
    otherwise it becomes ``<identity> <stored strength>`` (carrier added only
    when that still collides), so one name always means one bottle.
    """

    counts = Counter(stock.name.casefold() for stock in stocks)

    def truthful(stock: InventoryMaterial) -> bool:
        return all(
            abs(float(value.replace(",", ".")) / 100.0 - float(stock.dilution)) <= 1e-9
            for value in _NAME_PERCENT_RE.findall(stock.name)
        )

    def derived(stock: InventoryMaterial, *, with_carrier: bool) -> str:
        base = _TRAILING_STRENGTHS_RE.sub("", stock.identity_name or stock.name).strip()
        label = f"{base} {_strength_label(float(stock.dilution))}"
        if with_carrier and stock.carrier:
            label += f" in {stock.carrier.upper()}"
        return label

    keep = {
        index
        for index, stock in enumerate(stocks)
        if counts[stock.name.casefold()] == 1 and truthful(stock)
    }
    taken = {stocks[index].name.casefold() for index in keep}
    renamed: list[InventoryMaterial] = []
    for index, stock in enumerate(stocks):
        if index in keep:
            renamed.append(stock)
            continue
        siblings = [
            other
            for position, other in enumerate(stocks)
            if position != index
            and position not in keep
            and derived(other, with_carrier=False).casefold()
            == derived(stock, with_carrier=False).casefold()
        ]
        name = derived(stock, with_carrier=bool(siblings))
        if name.casefold() in taken:
            raise ValueError(f"inventory display name is not unique: {name!r}")
        taken.add(name.casefold())
        renamed.append(replace(stock, name=name))
    return tuple(renamed)


_USER_OVERLAY_CHAIN_PATHS = (
    BASE_USER_INVENTORY_OVERLAY_PATH,
    PREVIOUS_USER_INVENTORY_OVERLAY_PATH,
    ORRIS_USER_INVENTORY_OVERLAY_PATH,
    NEROLI_USER_INVENTORY_OVERLAY_PATH,
    RECONCILED_USER_INVENTORY_OVERLAY_PATH,
    TINCTURES_USER_INVENTORY_OVERLAY_PATH,
    AHSEE_USER_INVENTORY_OVERLAY_PATH,
    ROMANDOLIDE_USER_INVENTORY_OVERLAY_PATH,
    FLORHYDRAL_USER_INVENTORY_OVERLAY_PATH,
    ROMANDOLIDE_RESTOCK_USER_INVENTORY_OVERLAY_PATH,
    STOCK_CLARIFICATIONS_USER_INVENTORY_OVERLAY_PATH,
    PINK_PEPPER_USER_INVENTORY_OVERLAY_PATH,
    STOCK_FORMS_AND_TINCTURE_MODEL_USER_INVENTORY_OVERLAY_PATH,
    EVERNYL_10WW_DPG_USER_INVENTORY_OVERLAY_PATH,
    METHYL_PAMPLEMOUSSE_10WW_ETHANOL_USER_INVENTORY_OVERLAY_PATH,
    R5_STOCK_CLARIFICATIONS_USER_INVENTORY_OVERLAY_PATH,
    R5_STOCK_CLARIFICATIONS_V2_USER_INVENTORY_OVERLAY_PATH,
    R5_REMAINING_STOCK_FORMS_V3_USER_INVENTORY_OVERLAY_PATH,
    AIMI_IDENTITY_USER_INVENTORY_OVERLAY_PATH,
    PW_RECEIVED_USER_INVENTORY_OVERLAY_PATH,
    TOBACCO_DBCA_USER_INVENTORY_OVERLAY_PATH,
    AMBRETTOLIDE_NEAT_USER_INVENTORY_OVERLAY_PATH,
    E2MB_OSMANTHUS_MIMOSA_USER_INVENTORY_OVERLAY_PATH,
    VERTOFIX_COEUR_USER_INVENTORY_OVERLAY_PATH,
    CURRENT_USER_INVENTORY_OVERLAY_PATH,
    PW_RECEIVED_INVENTORY_RECEIPT_PATH,
)


def _inventory_materialization_fingerprint(
    snapshot_path: Path,
    *,
    apply_user_overlay: bool,
    apply_user_completions: bool,
    dilution_path: Path | None = None,
) -> tuple[tuple[str, int, int], ...]:
    paths = [snapshot_path]
    if apply_user_overlay:
        paths.extend((*_USER_OVERLAY_CHAIN_PATHS, INVENTORY_PATH, USER_COMPOUNDING_HOLDS_PATH))
    if apply_user_completions:
        from engine.inventory_completions import completion_log_path
        from engine.inventory_dilutions import dilution_log_path

        paths.extend((completion_log_path(), dilution_log_path(dilution_path)))
    records: list[tuple[str, int, int]] = []
    for source in paths:
        resolved = source.resolve()
        try:
            stat = resolved.stat()
        except OSError:
            records.append((str(resolved), -1, -1))
        else:
            records.append(
                (str(resolved), int(stat.st_mtime_ns), int(stat.st_size))
            )
    return tuple(records)


@lru_cache(maxsize=32)
def _cached_current_inventory_materialization(
    snapshot_path_text: str,
    source_fingerprint: tuple[tuple[str, int, int], ...],
    require_pinned_snapshot: bool,
    apply_user_overlay: bool,
    require_pinned_overlay: bool,
    apply_user_completions: bool,
    dilution_path_text: str = "",
) -> CurrentInventoryMaterialization:
    del source_fingerprint
    return _materialize_current_inventory_uncached(
        Path(snapshot_path_text),
        require_pinned_snapshot=require_pinned_snapshot,
        apply_user_overlay=apply_user_overlay,
        require_pinned_overlay=require_pinned_overlay,
        apply_user_completions=apply_user_completions,
        dilution_path=Path(dilution_path_text) if dilution_path_text else None,
    )


def materialize_current_inventory(
    path: Path | None = None,
    *,
    require_pinned_snapshot: bool = True,
    apply_user_overlay: bool = True,
    require_pinned_overlay: bool = True,
    apply_user_completions: bool = True,
    dilution_path: Path | None = None,
) -> CurrentInventoryMaterialization:
    """Materialize source-bound stock truth with drift-sensitive local reuse.

    ``dilution_path`` reads prepared dilutions from that log instead of the
    default one (``record_prepared_dilution(path=...)``).
    """

    snapshot_path = (path or CURRENT_INVENTORY_SNAPSHOT_PATH).resolve()
    return _cached_current_inventory_materialization(
        str(snapshot_path),
        _inventory_materialization_fingerprint(
            snapshot_path,
            apply_user_overlay=apply_user_overlay,
            apply_user_completions=apply_user_completions,
            dilution_path=dilution_path,
        ),
        require_pinned_snapshot,
        apply_user_overlay,
        require_pinned_overlay,
        apply_user_completions,
        str(dilution_path.resolve()) if dilution_path is not None else "",
    )


def parse_current_inventory(
    path: Path | None = None,
    *,
    unique: bool = True,
    include_solvents: bool = True,
    include_unavailable: bool = True,
    require_pinned_snapshot: bool = True,
) -> list[InventoryMaterial]:
    """Return V5 physical stocks plus explicit non-owned requirement states.

    ``unique=True`` deduplicates stable stock/requirement IDs, never material
    names or concentrations. Multiple real stocks therefore remain separate.
    """

    materialized = materialize_current_inventory(
        path,
        require_pinned_snapshot=require_pinned_snapshot,
    )
    records = list(materialized.stocks)
    if include_unavailable:
        for requirement in materialized.requirements:
            if requirement.disposition == "OWNED":
                continue
            records.append(
                InventoryMaterial(
                    name=requirement.canonical_name,
                    dilution=requirement.requested_fraction or 0.0,
                    category=requirement.category,
                    raw_name=f"{requirement.canonical_name} [{requirement.status}]",
                    status=requirement.disposition.lower(),
                    fraction_basis=requirement.fraction_basis,
                    carrier=requirement.carrier,
                    identity_name=requirement.identity_name,
                    stock_id=f"requirement:v5:r{requirement.source_row}",
                    authority=CURRENT_INVENTORY_AUTHORITY,
                    source_rows=(requirement.source_row,),
                    source_ref=(
                        f"Current Inventory Master!A{requirement.source_row}:"
                        f"N{requirement.source_row}"
                    ),
                    execution_ready=False,
                    requirement_state=requirement.disposition,
                )
            )
    if not include_solvents:
        records = [record for record in records if not _is_solvent(record)]
    if unique:
        by_id: dict[str, InventoryMaterial] = {}
        for record in records:
            key = record.stock_id or (
                f"legacy:{record.identity_name.lower()}:{record.dilution:.12g}:"
                f"{record.fraction_basis}:{record.carrier}"
            )
            by_id.setdefault(key, record)
        records = list(by_id.values())
    return sorted(
        records,
        key=lambda record: (record.source_rows, record.identity_name.lower(), record.stock_id),
    )


def parse_inventory(
    path: Path | None = None,
    *,
    unique: bool = True,
    include_solvents: bool = True,
    include_unavailable: bool = True,
) -> list[InventoryMaterial]:
    """Parse inventory.txt into normalized material records.

    When `unique=True`, duplicate canonical materials are collapsed by keeping
    the highest-available dilution entry.
    """
    path = path or INVENTORY_PATH
    if not path.exists():
        return []

    materials: list[InventoryMaterial] = []
    current_category = ""

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue

        heading_match = _HEADING_RE.match(line)
        if heading_match:
            current_category = heading_match.group(1).strip().lower()
            continue

        bullet_match = _BULLET_RE.match(line)
        if not bullet_match:
            continue

        raw_name = bullet_match.group(1).strip()
        stock_source = re.sub(r"\s*#.*$", "", raw_name).strip()
        status = _parse_status(raw_name)
        execution_hold_reason = _parse_execution_hold_reason(raw_name, status)
        stock = parse_stock_specification(
            stock_source,
            assume_neat_when_missing=execution_hold_reason != "STOCK_FRACTION_UNSPECIFIED",
        )
        if not execution_hold_reason and status == "owned":
            if stock.approximate:
                execution_hold_reason = "APPROXIMATE_STOCK_FRACTION"
            elif stock.fraction < 1 and (stock.fraction_basis == "unspecified" or not stock.carrier):
                execution_hold_reason = "FRACTION_BASIS_OR_CARRIER_UNSPECIFIED"
        record = InventoryMaterial(
            name=_canonical_name(raw_name),
            dilution=(
                0.0
                if execution_hold_reason == "STOCK_FRACTION_UNSPECIFIED"
                else stock.fraction
            ),
            category=current_category,
            raw_name=raw_name,
            status=status,
            fraction_basis=stock.fraction_basis,
            carrier=stock.carrier,
            approximate=stock.approximate,
            identity_name=_identity_name(raw_name),
            source_rows=(line_number,),
            source_ref=f"{path.name}:{line_number}",
            stock_id="inventory:text:" + hashlib.sha256(
                f"{current_category}|{raw_name}".encode("utf-8")
            ).hexdigest()[:20],
            execution_ready=status == "owned" and not execution_hold_reason,
            execution_hold_reason=execution_hold_reason,
        )
        if not include_unavailable and record.status != "owned":
            continue
        if not include_solvents and _is_solvent(record):
            continue
        materials.append(record)

    materials = list(apply_user_compounding_holds(tuple(materials))[0])
    if not unique:
        return materials

    deduped: dict[str, InventoryMaterial] = {}
    for record in materials:
        key = record.name.lower()
        existing = deduped.get(key)
        if existing is None or (record.status == "owned", record.dilution) > (
            existing.status == "owned", existing.dilution
        ):
            deduped[key] = record

    return list(deduped.values())


def inventory_names(
    path: Path | None = None,
    *,
    unique: bool = True,
    include_solvents: bool = True,
    include_unavailable: bool = True,
) -> list[str]:
    return [
        record.name
        for record in parse_inventory(
            path,
            unique=unique,
            include_solvents=include_solvents,
            include_unavailable=include_unavailable,
        )
    ]


def inventory_counts(path: Path | None = None) -> dict[str, int]:
    """Return raw and normalized inventory counts for reporting."""
    path = path or INVENTORY_PATH
    raw = parse_inventory(path, unique=False, include_solvents=True)
    unique_all = parse_inventory(path, unique=True, include_solvents=True)
    unique_fragrance = parse_inventory(path, unique=True, include_solvents=False)
    return {
        "raw_entries": len(raw),
        "unique_normalized": len(unique_all),
        "unique_fragrance": len(unique_fragrance),
        "solvent_or_carrier": len(unique_all) - len(unique_fragrance),
        "duplicate_canonical_entries": len(raw) - len(unique_all),
    }
