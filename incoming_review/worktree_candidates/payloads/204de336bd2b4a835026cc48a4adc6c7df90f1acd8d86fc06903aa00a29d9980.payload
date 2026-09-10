"""Deterministic material-cache reconciliation; no network or formula authority.

Existing records and narrative fields are retained. Numeric presence is not
verification. Ambiguous mixtures keep model values explicitly qualified, and
missing data stay missing. This is a library used by the existing generator.
"""

from __future__ import annotations

import hashlib
import json
import math
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path

from engine.data_spine.loader import load_materials, load_registry
from engine.ingredient_intelligence import get_profile
from engine.inventory_parser import materialize_current_inventory, parse_inventory
from engine.name_utils import normalize_name
from engine.odor_thresholds import lookup_odt_entry, verify_odt

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "data/governance/ingredient_reconciliation_20260907.json"
CACHE_PATH = ROOT / "data/knowledge_graph/material_properties.json"
REPORT_PATH = ROOT / "docs/verification/INGREDIENT_SYSTEM_RECONCILIATION_20260907.json"


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def identity_key(name):
    """Use the maintained identity normalizer, never substring or CAS guessing."""
    return normalize_name(str(name))


def stock_key(name):
    """Stock identity is exact except case/spacing; scientific aliases are unsafe.

    In particular never bind Geranium Flower EO to Geranium EO, Sambac to
    unspecified Jasmine, or an HC/isomer grade to its generic model.
    """
    return " ".join(str(name).casefold().split())


def _lineage(entry, fields, reason):
    prior = {key: deepcopy(entry.get(key)) for key in fields}
    item = {"reason": reason, "fields": prior}
    history = entry.setdefault("reconciliation_lineage", [])
    if item not in history:
        history.append(item)


def _mixed(name, profile):
    kind = profile.material_kind.upper() if profile else ""
    low = name.casefold()
    return (
        kind in {"", "UNRESOLVED"}
        or any(x in kind for x in ("MIXTURE", "OPAQUE", "BLEND"))
        or any(
            x in low
            for x in (
                " eo",
                "essential oil",
                "absolute",
                "resinoid",
                "tincture",
                "fleuressence",
                "f-tec",
                "fragrance oil",
                " oil",
                " fcf",
                "artificial",
                "synthetic",
                " fo",
                "base",
            )
        )
    )


def reconcile(existing):
    """Return a rebuilt list plus row-level diagnostics; input is never mutated."""
    contracts = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    identities = {identity_key(k): v for k, v in contracts["identity_corrections"].items()}
    current = materialize_current_inventory()
    inventory = parse_inventory(unique=False)
    registry = load_registry()
    stocks = {}
    for stock in current.stocks:
        stocks.setdefault(stock_key(stock.identity_name), []).append(asdict(stock))
    text_by_identity = {}
    for row in inventory:
        text_by_identity.setdefault(stock_key(row.identity_name or row.name), []).append(
            asdict(row)
        )

    output = deepcopy(existing)
    existing_keys = {stock_key(row["name"]) for row in output}
    # Preserve all original names, including duplicate aliases. Add exact text
    # identities and authority-only physical forms without collapsing history.
    for name in sorted(
        {r.identity_name or r.name for r in inventory} | {r.identity_name for r in current.stocks},
        key=str.casefold,
    ):
        if stock_key(name) not in existing_keys:
            output.append({"name": name, "alt_name": None})
            existing_keys.add(stock_key(name))

    for entry in output:
        name = entry["name"]
        key = identity_key(name)
        profile = get_profile(name)
        material = registry.get(name)
        correction = identities.get(key)
        if correction:
            fields = correction["fields"]
            if any(entry.get(k) != v for k, v in fields.items()):
                _lineage(entry, fields, "SOURCE_BOUND_IDENTITY_REPAIR_20260907")
                entry.update(deepcopy(fields))
            entry["identity_evidence"] = {k: v for k, v in correction.items() if k != "fields"}
        # Refresh model fields, including formerly stale non-inventory records.
        # Evidence labels travel with values; registry disagreements remain in report.
        if profile:
            values = {
                "mw": profile.mw,
                "vp": profile.vp,
                "clp": profile.clogp,
                "note": profile.note,
                "role": profile.role,
                "texture": profile.texture,
                "or_family": profile.or_family,
                "activity_coef": profile.activity_coef,
                "hedonic": profile.hedonic,
            }
            if correction:
                values.update({k: v for k, v in correction["fields"].items() if k in values})
            changed = [k for k, v in values.items() if entry.get(k) != v]
            if changed:
                _lineage(entry, changed, "CURRENT_PROFILE_MODEL_SYNCHRONIZATION_20260907")
            entry.update(values)
            entry["material_kind"] = profile.material_kind
            entry["formulation_roles"] = list(profile.formulation_roles)
            entry["field_evidence"] = deepcopy(profile.evidence)
            entry["synergies"] = list(profile.synergies)
            if not entry.get("odor_profile"):
                entry["odor_profile"] = profile.odor_description
        else:
            entry["field_evidence"] = {
                k: {"status": "UNVERIFIED_LEGACY_VALUE" if entry.get(k) is not None else "UNKNOWN"}
                for k in ("mw", "vp", "clp", "activity_coef", "hedonic")
            }
        odt = lookup_odt_entry(name)
        if odt:
            entry["odt"] = odt.get("odt_air")
            entry["odt_ethanol_ppm"] = odt.get("odt_eth")
        else:
            entry["odt"] = profile.odt if profile else None
            entry["odt_ethanol_ppm"] = profile.odt_ppm if profile else None
        entry["odt_evidence"] = verify_odt(name) or {
            "vfy": "UNVERIFIED",
            "reason": "No identity-bound metadata",
        }
        entry["current_stocks"] = stocks.get(stock_key(name), [])
        entry["inventory_text_records"] = text_by_identity.get(stock_key(name), [])
        # A catalog or text row is not an executable stock. Preserve the difference.
        entry["in_inventory"] = bool(entry["current_stocks"])
        entry["stock_authority"] = current.overlay_sha256
        entry["inventory_status"] = (
            "BOUND_CURRENT_STOCK"
            if entry["current_stocks"]
            else "TEXT_ONLY_UNBOUND"
            if any(r["status"] == "owned" for r in entry["inventory_text_records"])
            else "NOT_CURRENTLY_OWNED_OR_CATALOG_ONLY"
        )
        specifications = {
            (
                s["dilution"],
                s["fraction_basis"],
                s["carrier"],
                s["execution_ready"],
                s["execution_hold_reason"],
            )
            for s in entry["current_stocks"]
        }
        entry["dilution_pct"] = next(iter(specifications))[0] if len(specifications) == 1 else None
        entry["stock_form"] = " | ".join(s["raw_name"] for s in entry["current_stocks"]) or None
        entry["quantitative_stock_ready"] = len(specifications) == 1 and all(
            s["execution_ready"] for s in entry["current_stocks"]
        )
        entry["stock_selection_status"] = (
            "AMBIGUOUS_SELECT_STOCK_ID" if len(specifications) > 1 else entry["inventory_status"]
        )
        mixture = _mixed(name, profile)
        entry["quantitative_model_status"] = (
            "COMPOSITE_OR_PRODUCT_MODEL_REQUIRED"
            if mixture
            else "MISSING_PHYSICS"
            if not all(_number(entry.get(k)) and entry[k] > 0 for k in ("mw", "vp", "odt"))
            else "UNVERIFIED_SCREENING_MODEL"
        )
        # This is concentration OAV, not headspace, perceived proportion or liking.
        dose, threshold = entry.get("oav_dose_pct"), entry.get("odt_ethanol_ppm")
        old_oav = entry.get("oav_typical")
        new_oav = (
            dose * 10000 / threshold
            if not mixture and _number(dose) and _number(threshold) and dose >= 0 and threshold > 0
            else None
        )
        if old_oav != new_oav:
            _lineage(entry, ["oav_typical"], "DERIVED_OAV_RECOMPUTATION_20260907")
        entry["oav_typical"] = new_oav
        # These are old computed labels, not hand-authored odor descriptions.
        stale = [k for k in ("smell_strength", "anosmic_risk") if entry.get(k) is not None]
        if stale:
            _lineage(entry, stale, "LEGACY_DERIVED_CLASSIFICATION_WITHHELD_20260907")
        entry["smell_strength"] = None
        entry["anosmic_risk"] = None
        if profile and profile.or_family:
            if entry.get("odor_family") != profile.or_family:
                _lineage(entry, ["odor_family"], "CURRENT_PROFILE_FAMILY_SYNCHRONIZATION_20260907")
            entry["odor_family"] = profile.or_family
        entry["odor_family_evidence"] = "DESCRIPTIVE_MODEL_NOT_MEASURED_RECEPTOR_OR_LIKING"
        entry["oav_evidence"] = {
            "status": "SCREENING_ONLY" if new_oav is not None else "NOT_COMPUTED",
            "equation": "concentrate_ppm_w_w / odt_ethanol_ppm",
            "not_headspace_or_observed_intensity": True,
        }
        entry["hedonic_evidence"] = "HEURISTIC_NOT_MEASURED_LIKING"
        entry["release_authority"] = "NOT_TESTED_HOLD"

    rows = []
    fields = (
        ("mw", "mw_g_mol"),
        ("vp", "vp_25c_pa"),
        ("clogp", "logp"),
        ("odt", "odt_air_ppb"),
        ("odt_ppm", "odt_eth_ppm"),
    )
    for row in inventory:
        name = row.identity_name or row.name
        profile = get_profile(name)
        material = registry.get(name)
        if material is None:
            material = registry.get(row.name)
        disagreements = {}
        missing = []
        for pf, yf in fields:
            pv = getattr(profile, pf, None)
            yv = getattr(material, yf, None)
            if not _number(pv) and not _number(yv):
                missing.append(pf)
            if (
                _number(pv)
                and _number(yv)
                and not math.isclose(pv, yv, rel_tol=0.01, abs_tol=1e-12)
            ):
                disagreements[pf] = {"profile": pv, "registry": yv}
        rows.append(
            {
                "source_rows": list(row.source_rows),
                "raw_name": row.raw_name,
                "identity": name,
                "text_status": row.status,
                "registry_name": material.canonical_name if material else None,
                "profile_name": profile.name if profile else None,
                "current_stock_ids": [s["stock_id"] for s in stocks.get(stock_key(name), [])],
                "odt_present": lookup_odt_entry(name) is not None,
                "missing_numeric_fields": missing,
                "unresolved_scalar_disagreements": disagreements,
            }
        )
    inputs = [
        ROOT / "inventory.txt",
        ROOT / "engine/ingredient_intelligence.py",
        ROOT / "engine/inventory_parser.py",
        ROOT / "engine/odor_thresholds.py",
        ROOT / "engine/name_utils.py",
        ROOT / "engine/material_identity.py",
        ROOT / "engine/data_spine/loader.py",
        ROOT / "engine/data_spine/material.py",
        CONTRACT_PATH,
        Path(__file__),
        *sorted((ROOT / "data/materials").glob("*.yaml")),
    ]
    report = {
        "schema_version": "ingredient_system_reconciliation_v1",
        "authority": "COMPUTATIONAL_DATA_RECONCILIATION_NOT_RELEASE",
        "input_sha256": {
            p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in inputs
        },
        "inventory_overlay_sha256": current.overlay_sha256,
        "inventory_snapshot_sha256": current.snapshot_sha256,
        "inventory_workbook_sha256": current.source_workbook_sha256,
        "counts": {
            "original_cache_records": len(existing),
            "rebuilt_cache_records": len(output),
            "all_original_names_preserved": [x["name"] for x in output[: len(existing)]]
            == [x["name"] for x in existing],
            "inventory_text_rows": len(rows),
            "historical_requirement_rows": len(current.requirements),
            "current_physical_stocks": len(current.stocks),
            "registry_records": len(load_materials()),
            "rows_with_profile": sum(bool(r["profile_name"]) for r in rows),
            "rows_with_registry": sum(bool(r["registry_name"]) for r in rows),
            "rows_with_odt": sum(r["odt_present"] for r in rows),
            "rows_with_unresolved_scalar_disagreements": sum(
                bool(r["unresolved_scalar_disagreements"]) for r in rows
            ),
        },
        "rows": rows,
        "remaining_authority_limits": [
            "Internal synchronization does not verify all 25C VP, density, ODT or supplier-grade composition.",
            "Legacy quantitative proxies remain explicitly unverified; no observed liking, safety, stability or release claim.",
            "Historical formulas and embedded diagnostics were not regenerated.",
        ],
    }
    return output, report


def generate():
    """Explicit write entry point; imports and reconciliation itself are read-only."""
    source_bytes = CACHE_PATH.read_bytes()
    existing = json.loads(source_bytes)
    output, report = reconcile(existing)
    cache_bytes = (json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode(
        "utf-8"
    )
    report["output_sha256"] = hashlib.sha256(cache_bytes).hexdigest()
    report["input_cache_sha256"] = hashlib.sha256(source_bytes).hexdigest()
    CACHE_PATH.write_bytes(cache_bytes)
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return report
