"""Shared inventory parsing and physical-stock authority utilities.

``inventory.txt`` remains a legacy compatibility surface. Executable stock
binding uses the hash-pinned Inventory V5 ``Current Inventory Master``
snapshot, while requirement/preparation rows remain non-owned evidence.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INVENTORY_PATH = PROJECT_ROOT / "inventory.txt"
CURRENT_INVENTORY_SNAPSHOT_PATH = (
    PROJECT_ROOT / "data" / "governance" / "inventory_v5_current_stock_snapshot.json"
)
CURRENT_INVENTORY_ALIAS_CROSSWALK_PATH = (
    PROJECT_ROOT / "data" / "governance" / "inventory_v5_alias_crosswalk_20260811.json"
)
CURRENT_USER_INVENTORY_OVERLAY_PATH = (
    PROJECT_ROOT
    / "data"
    / "governance"
    / "inventory_user_authority_overlay_20260828.json"
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
CURRENT_USER_INVENTORY_OVERLAY_SHA256 = (
    "9d0f3750e897e13758a1180e158adca464449e9d6dfac176460ba18868a17564"
)
CURRENT_USER_INVENTORY_AUTHORITY = "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY_20260828"

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
    approximate: bool = False
    identity_name: str = ""
    stock_id: str = ""
    authority: str = "LEGACY_INVENTORY_TEXT"
    source_rows: tuple[int, ...] = ()
    source_ref: str = ""
    execution_ready: bool = True
    execution_hold_reason: str = ""
    requirement_state: str = ""


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
    explicit_neat = low in {"neat", "pure", "undiluted"}
    match = re.search(r"~?\s*(\d+(?:[.,]\d+)?)\s*%", text)

    if explicit_neat or (match is None and assume_neat_when_missing):
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
    if "DON'T HAVE" in upper or "DONT HAVE" in upper:
        return "not_owned"
    if "NON-EXECUTABLE" in upper or "HOMOGENEITY HOLD" in upper:
        return "owned_non_executable"
    return "owned"


def _parse_execution_hold_reason(raw_name: str, status: str) -> str:
    upper = raw_name.upper()
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
    clean = _strip_status(raw_name)
    # Remove trailing `# comment` before stripping parenthetical
    clean = re.sub(r"\s*#.*$", "", clean).strip()
    return re.sub(r"\s*\([^)]*\)\s*$", "", clean).strip()


def _identity_name(raw_name: str) -> str:
    """Remove stock preparation text while preserving identity-bearing variants."""

    clean = _strip_status(raw_name)
    clean = re.sub(r"\s*#.*$", "", clean).strip()
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


def _stock_execution_ready(
    status: str,
    spec: StockSpecification,
    descriptor: str,
) -> bool:
    context = f"{status} {descriptor}".upper()
    unresolved_tokens = (
        "CARRIER UNSTATED",
        "PRODUCT BASIS",
        "HETEROGENEOUS",
        "PHYSICAL FORM OPEN",
        "SPECIES UNRESOLVED",
        "LOT DETAIL OPEN",
        "IDENTITY KEPT SEPARATE",
        "TWO PRODUCTS",
        "MULTIPLE BENZOINS",
        "UNCONFIRMED",
    )
    if any(token in context for token in unresolved_tokens):
        return False
    if spec.fraction == 1.0:
        return spec.fraction_basis == "neat"
    return bool(spec.carrier)


def load_current_user_inventory_overlay(
    path: Path | None = None,
    *,
    require_pinned_overlay: bool = True,
) -> dict[str, Any]:
    """Load the dated user-authority overlay without mutating the V5 parent."""

    overlay_path = path or CURRENT_USER_INVENTORY_OVERLAY_PATH
    if not overlay_path.exists():
        raise InventoryAuthorityError(
            f"current user inventory overlay is missing: {overlay_path}"
        )
    overlay_sha = _normalized_text_sha256(overlay_path)
    if require_pinned_overlay and overlay_sha != CURRENT_USER_INVENTORY_OVERLAY_SHA256:
        raise InventoryAuthorityError(
            "current user inventory overlay hash drift: "
            f"expected {CURRENT_USER_INVENTORY_OVERLAY_SHA256}, got {overlay_sha}"
        )
    try:
        payload = json.loads(overlay_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryAuthorityError(
            f"current user inventory overlay is unreadable: {exc}"
        ) from exc

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
        != len(_normalized_text_bytes(INVENTORY_PATH))
        or source.get("inventory_text_sha256")
        != _normalized_text_sha256(INVENTORY_PATH)
    ):
        raise InventoryAuthorityError(
            "current user inventory overlay is not bound to the live inventory text"
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
                break
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
        stock_digest = hashlib.sha256(
            f"{CURRENT_USER_INVENTORY_OVERLAY_SHA256}|{record_id}".encode("utf-8")
        ).hexdigest()[:20]
        authority_date = record_id.split("-")[2]
        raw_fraction = stock.get("fraction")
        fraction = float(raw_fraction) if raw_fraction is not None else 0.0
        basis = str(stock["fraction_basis"])
        carrier = str(stock["carrier"])
        descriptor = (
            "neat / as supplied"
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
                approximate=False,
                identity_name=_v5_identity_name(canonical_name),
                stock_id=f"inventory:user-{authority_date}:{stock_digest}",
                authority=CURRENT_USER_INVENTORY_AUTHORITY,
                source_rows=tuple(sorted(parent_rows)),
                source_ref=(
                    "data/governance/inventory_user_authority_overlay_20260828.json"
                    f"#{record_id}"
                ),
                execution_ready=bool(stock["execution_ready"]),
                execution_hold_reason=str(stock.get("execution_hold_reason") or ""),
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


def materialize_current_inventory(
    path: Path | None = None,
    *,
    require_pinned_snapshot: bool = True,
    apply_user_overlay: bool = True,
    require_pinned_overlay: bool = True,
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
                execution_ready=_stock_execution_ready(status, spec, descriptor),
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
    if not apply_user_overlay:
        return materialized
    overlay = load_current_user_inventory_overlay(
        require_pinned_overlay=require_pinned_overlay,
    )
    return _apply_current_user_inventory_overlay(materialized, overlay)


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

    for raw_line in path.read_text(encoding="utf-8").splitlines():
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
            execution_ready=status == "owned" and not execution_hold_reason,
            execution_hold_reason=execution_hold_reason,
        )
        if not include_unavailable and record.status != "owned":
            continue
        if not include_solvents and _is_solvent(record):
            continue
        materials.append(record)

    if not unique:
        return materials

    deduped: dict[str, InventoryMaterial] = {}
    for record in materials:
        key = record.name.lower()
        existing = deduped.get(key)
        if existing is None or record.dilution > existing.dilution:
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
