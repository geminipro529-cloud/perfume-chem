"""IFRA compliance & allergen safety scoring.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**
- Concentrations in ppm (parts per million w/w in concentrate).
- ODT in ppm for ethanol solution, ppb for air.
- OAV = concentration_ppm / ODT_ppm (dimensionless).
- IFRA limits (%) must be cross-checked against OAV to ensure
  perceptibility claims are consistent with concentration limits.

Implements regulatory ceiling analysis per IFRA 51st Amendment (2024)
and EU Cosmetics Regulation 1223/2009 Annex III as amended by
Regulation (EU) 2023/1545.

Category 4 = Fine Fragrance (eau de parfum, eau de toilette, cologne).
Max use levels are percentages of the FINISHED PRODUCT, not concentrate.

Scoring:
  100 = every material within IFRA limits, no undeclared allergens
  70  = minor exceedances (1.0–1.5× limit) or missing allergen declarations
  40  = moderate exceedances (1.5–3× limit)
  0   = critical exceedances (>3× limit) or banned materials

Sources:
  IFRA Standards Library 51st Amendment (2024)
  EU Regulation 1223/2009, Annex III
  SCCS/1459/11, SCCS/1564/15 opinions on fragrance allergens
  de Groot & Frosch (1997) Contact Dermatitis
  Schnuch et al. (2007) Contact Dermatitis
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from engine.ifra_standards import (
    FinishedProductRow,
    IFRAEvaluation,
    estimate_finished_product_pct_w_w,
    evaluate_ifra,
    load_ifra_table,
)
from engine.material_resolver import resolve_material
from engine.skin_compartments import skin_partition

# ═══════════════════════════════════════════════════════════════════════════════
# IFRA Maximum Use Levels — Category 4: Fine Fragrance
# Values = max % w/w in FINISHED product (not concentrate)
# ═══════════════════════════════════════════════════════════════════════════════

# Sourced from data/regulatory/ifra_cat4_51.json via engine.ifra_standards: restricted
# materials only, keyed by canonical name and every alias as written. Materials with
# no IFRA standard (e.g. Hedione, Evernyl) are deliberately absent.
_IFRA_TABLE = load_ifra_table()
IFRA_CAT4_LIMITS: dict[str, float] = dict(_IFRA_TABLE.cat4_limits())


# ═══════════════════════════════════════════════════════════════════════════════
# IFRA Version History — approximate/reconstructed from public data
# These are for STRUCTURAL TESTING, not regulatory compliance.
# All values are % of finished product (Cat4 leave-on).
# ═══════════════════════════════════════════════════════════════════════════════

IFRA_VERSION_HISTORY: dict[str, dict[str, float]] = {
    # Unsourced: the 50th/49th values below are hand-typed, not read from IFRA Standards.
    "IFRA_51st_2025": {},  # Current — read from the sourced table, see get_ifra_limit
    "IFRA_50th_2022": {
        "Coumarin": 1.6,
        "Lilial": 0.01,
        "Lyral": 0.01,
        "Eugenol": 2.5,
        "Isoeugenol": 0.02,
        "Cinnamal": 0.2,
        "Citral": 0.6,
        "Farnesol": 1.2,
        "Geraniol": 1.5,
        "Hydroxycitronellal": 1.0,
        "Linalool": 1.0,
        "Benzyl Alcohol": 1.0,
        "Benzyl Benzoate": 3.0,
        "Benzyl Cinnamate": 0.8,
        "Benzyl Salicylate": 2.0,
        "Citronellol": 1.5,
        "Hexyl Cinnamal": 1.0,
        "Limonene": 0.1,
        "Methyl 2-Octynoate": 0.01,
        "alpha-Isomethyl Ionone": 1.0,
        "Evernyl": 0.5,
        "Amyl Cinnamal": 0.1,
        "Anisyl Alcohol": 0.5,
    },
    "IFRA_49th_2019": {
        "Coumarin": 1.5,
        "Lilial": 0.02,
        "Lyral": 0.02,
        "Eugenol": 2.5,
        "Isoeugenol": 0.02,
        "Cinnamal": 0.15,
        "Citral": 0.6,
        "Farnesol": 1.2,
        "Geraniol": 1.5,
        "Hydroxycitronellal": 1.0,
        "Linalool": 1.0,
        "Benzyl Alcohol": 1.0,
        "Benzyl Benzoate": 3.5,
        "Benzyl Salicylate": 2.5,
        "Citronellol": 1.5,
        "Limonene": 0.1,
        "Methyl 2-Octynoate": 0.01,
    },
}


def get_ifra_limit(material: str, rule_set: str = "IFRA_51st_2025") -> float | None:
    """Return the IFRA Cat4 limit for a material under a specific rule set version.

    The current rule set reads the sourced table: a restricted material's limit, else None
    (prohibited, specification-only and unlisted materials have no numeric limit). Older
    rule sets read their hand-typed dicts, then fall back to the current table.
    """
    from engine.name_utils import normalize_name

    if rule_set != "IFRA_51st_2025" and rule_set in IFRA_VERSION_HISTORY:
        key = normalize_name(material)
        for k, v in IFRA_VERSION_HISTORY[rule_set].items():
            if normalize_name(k) == key:
                return v
    entry = _IFRA_TABLE.lookup(material)
    if entry is not None and entry.status == "restricted":
        return entry.cat4_limit_pct
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# EU fragrance allergens — Mandatory declaration in EU/UK
# Annex III of 1223/2009 as amended by 2023/1545.
# These must be listed on packaging if above threshold:
#   0.001% (10 ppm) in leave-on products
#   0.01%  (100 ppm) in rinse-off products
# ═══════════════════════════════════════════════════════════════════════════════

EU_FRAGRANCE_ALLERGENS: dict[str, dict[str, Any]] = {
    "Linalool": {
        "cas": "78-70-6",
        "leave_on_threshold_pct": 0.001,
        "rinse_off_threshold_pct": 0.01,
        "risk": "low",
        "note": "Sensitizer when oxidized",
    },
    "Limonene": {
        "cas": "5989-27-5",
        "leave_on_threshold_pct": 0.001,
        "rinse_off_threshold_pct": 0.01,
        "risk": "low",
        "note": "D-Limonene; sensitizer when oxidized",
    },
    "Citronellol": {
        "cas": "106-22-9",
        "leave_on_threshold_pct": 0.001,
        "rinse_off_threshold_pct": 0.01,
        "risk": "low",
    },
    "Geraniol": {
        "cas": "106-24-1",
        "leave_on_threshold_pct": 0.001,
        "rinse_off_threshold_pct": 0.01,
        "risk": "moderate",
    },
    "Citral": {
        "cas": "5392-40-5",
        "leave_on_threshold_pct": 0.001,
        "rinse_off_threshold_pct": 0.01,
        "risk": "moderate",
        "note": "Neral + geranial mixture",
    },
    "Eugenol": {
        "cas": "97-53-0",
        "leave_on_threshold_pct": 0.001,
        "rinse_off_threshold_pct": 0.01,
        "risk": "moderate",
    },
    "Isoeugenol": {
        "cas": "97-54-1",
        "leave_on_threshold_pct": 0.001,
        "rinse_off_threshold_pct": 0.01,
        "risk": "high",
        "note": "Strong sensitizer",
    },
    "Cinnamaldehyde": {
        "cas": "104-55-2",
        "leave_on_threshold_pct": 0.001,
        "rinse_off_threshold_pct": 0.01,
        "risk": "high",
        "note": "Cinnamal; potent sensitizer",
    },
    "Hydroxycitronellal": {
        "cas": "107-75-5",
        "leave_on_threshold_pct": 0.001,
        "rinse_off_threshold_pct": 0.01,
        "risk": "moderate",
    },
    "Cinnamyl Alcohol": {
        "cas": "104-54-1",
        "leave_on_threshold_pct": 0.001,
        "rinse_off_threshold_pct": 0.01,
        "risk": "moderate",
    },
    "Coumarin": {
        "cas": "91-64-5",
        "leave_on_threshold_pct": 0.001,
        "rinse_off_threshold_pct": 0.01,
        "risk": "low",
    },
    "Alpha Isomethyl Ionone": {
        "cas": "127-51-5",
        "leave_on_threshold_pct": 0.001,
        "rinse_off_threshold_pct": 0.01,
        "risk": "low",
    },
    "Benzyl Alcohol": {
        "cas": "100-51-6",
        "leave_on_threshold_pct": 0.001,
        "rinse_off_threshold_pct": 0.01,
        "risk": "low",
    },
    "Benzyl Salicylate": {
        "cas": "118-58-1",
        "leave_on_threshold_pct": 0.001,
        "rinse_off_threshold_pct": 0.01,
        "risk": "low",
    },
    "Benzyl Benzoate": {
        "cas": "120-51-4",
        "leave_on_threshold_pct": 0.001,
        "rinse_off_threshold_pct": 0.01,
        "risk": "low",
    },
    "Benzyl Cinnamate": {
        "cas": "103-41-3",
        "leave_on_threshold_pct": 0.001,
        "rinse_off_threshold_pct": 0.01,
        "risk": "low",
    },
    "Farnesol": {
        "cas": "4602-84-0",
        "leave_on_threshold_pct": 0.001,
        "rinse_off_threshold_pct": 0.01,
        "risk": "moderate",
    },
    "Methyl 2-Octynoate": {
        "cas": "111-12-6",
        "leave_on_threshold_pct": 0.001,
        "rinse_off_threshold_pct": 0.01,
        "risk": "moderate",
    },
    "Anise Alcohol": {
        "cas": "105-13-5",
        "leave_on_threshold_pct": 0.001,
        "rinse_off_threshold_pct": 0.01,
        "risk": "low",
    },
    "Amyl Cinnamal": {
        "cas": "122-40-7",
        "leave_on_threshold_pct": 0.001,
        "rinse_off_threshold_pct": 0.01,
        "risk": "moderate",
    },
    "Amylcinnamyl Alcohol": {
        "cas": "101-85-9",
        "leave_on_threshold_pct": 0.001,
        "rinse_off_threshold_pct": 0.01,
        "risk": "low",
    },
    "Hexyl Cinnamal": {
        "cas": "101-86-0",
        "leave_on_threshold_pct": 0.001,
        "rinse_off_threshold_pct": 0.01,
        "risk": "low",
    },
    "Evernia Prunastri": {
        "cas": "90028-68-5",
        "leave_on_threshold_pct": 0.001,
        "rinse_off_threshold_pct": 0.01,
        "risk": "high",
        "note": "Oakmoss extract (Evernyl substitute)",
    },
    "Evernia Furfuracea": {
        "cas": "90028-67-4",
        "leave_on_threshold_pct": 0.001,
        "rinse_off_threshold_pct": 0.01,
        "risk": "high",
        "note": "Treemoss extract",
    },
    "d-Limonene": {
        "cas": "5989-27-5",
        "leave_on_threshold_pct": 0.001,
        "rinse_off_threshold_pct": 0.01,
        "risk": "low",
        "note": "Alias for D-Limonene",
    },
    # Inventory-relevant 2023/1545 additions
    "Linalyl Acetate": {
        "cas": "115-95-7",
        "leave_on_threshold_pct": 0.001,
        "rinse_off_threshold_pct": 0.01,
        "risk": "moderate",
        "note": "Added by EU 2023/1545; prehapten via oxidation/hydrolysis",
    },
    "Methyl Salicylate": {
        "cas": "119-36-8",
        "leave_on_threshold_pct": 0.001,
        "rinse_off_threshold_pct": 0.01,
        "risk": "moderate",
        "note": "Added by EU 2023/1545",
    },
    "Hexyl Salicylate": {
        "cas": "6259-76-3",
        "leave_on_threshold_pct": 0.001,
        "rinse_off_threshold_pct": 0.01,
        "risk": "moderate",
        "note": "Added by EU 2023/1545",
    },
    "Citronellyl Acetate": {
        "cas": "150-84-5",
        "leave_on_threshold_pct": 0.001,
        "rinse_off_threshold_pct": 0.01,
        "risk": "moderate",
        "note": "Added by EU 2023/1545",
    },
    "Geranyl Acetate": {
        "cas": "105-87-3",
        "leave_on_threshold_pct": 0.001,
        "rinse_off_threshold_pct": 0.01,
        "risk": "moderate",
        "note": "Added by EU 2023/1545",
    },
    "Vanillin": {
        "cas": "121-33-5",
        "leave_on_threshold_pct": 0.001,
        "rinse_off_threshold_pct": 0.01,
        "risk": "low",
        "note": "Added by EU 2023/1545",
    },
    "Ethyl Vanillin": {
        "cas": "121-32-4",
        "leave_on_threshold_pct": 0.001,
        "rinse_off_threshold_pct": 0.01,
        "risk": "low",
        "note": "Modeled under EU 2023/1545 expanded fragrance-allergen regime",
    },
}

# Map inventory names to allergen names where they differ
class _CaseInsensitiveAllergenMap(dict):  # type: ignore[type-arg]
    """dict whose ``get`` ignores case and a trailing "(10% in DPG)" stock suffix."""

    def get(self, key: Any, default: Any = None) -> Any:
        if isinstance(key, str):
            folded = key.split("(")[0].strip().lower()
            for name, value in self.items():
                if name.lower() == folded:
                    return value
        return default


_ALLERGEN_NAME_MAP: dict[str, str] = _CaseInsensitiveAllergenMap(
    {
        "D-Limonene": "Limonene",
        "d-Limonene": "Limonene",
        "Alpha Isomethyl Ionone": "Alpha Isomethyl Ionone",
        "Benzyl Salicylate": "Benzyl Salicylate",
        "Oakmoss Absolute": "Evernia Prunastri",
        "Oakmoss": "Evernia Prunastri",
        "Oak Moss": "Evernia Prunastri",
        "Oakmoss Extract": "Evernia Prunastri",
        "Treemoss Absolute": "Evernia Furfuracea",
        "Treemoss": "Evernia Furfuracea",
        "Tree Moss": "Evernia Furfuracea",
        "Treemoss Extract": "Evernia Furfuracea",
    }
)


def _allergen_threshold_pct(allergen_data: dict[str, Any], *, leave_on: bool) -> float:
    if leave_on:
        return float(
            allergen_data.get("leave_on_threshold_pct", allergen_data.get("threshold_pct", 0.001))
        )
    return float(allergen_data.get("rinse_off_threshold_pct", 0.01))


# ═══════════════════════════════════════════════════════════════════════════════
# Sensitization Risk — material-level potency data
# EC3 values from LLNA (Local Lymph Node Assay) where available
# Lower EC3 = more potent sensitizer
# Classification: extreme (<0.1%), strong (0.1-1%), moderate (1-10%), weak (>10%)
# ═══════════════════════════════════════════════════════════════════════════════

SENSITIZATION_DATA: dict[str, dict[str, Any]] = {
    "Cinnamaldehyde": {"ec3": 1.4, "potency": "moderate", "source": "LLNA"},
    "Isoeugenol": {"ec3": 1.5, "potency": "moderate", "source": "LLNA"},
    "Hydroxycitronellal": {"ec3": 9.7, "potency": "moderate", "source": "LLNA"},
    "Citral": {"ec3": 6.1, "potency": "moderate", "source": "LLNA"},
    "Eugenol": {"ec3": 5.5, "potency": "moderate", "source": "LLNA"},
    "Geraniol": {"ec3": 7.2, "potency": "moderate", "source": "LLNA"},
    "Linalool": {
        "ec3": 30.0,
        "potency": "weak",
        "source": "LLNA",
        "note": "Sensitizes only when oxidized (hydroperoxides)",
    },
    "D-Limonene": {
        "ec3": 69.0,
        "potency": "weak",
        "source": "LLNA",
        "note": "Sensitizes only when oxidized",
    },
    "Alpha Isomethyl Ionone": {"ec3": 24.0, "potency": "weak", "source": "LLNA"},
    "Coumarin": {"ec3": 25.0, "potency": "weak", "source": "estimated"},
    "Benzyl Benzoate": {"ec3": 20.0, "potency": "weak", "source": "LLNA"},
    "Benzyl Salicylate": {"ec3": 20.0, "potency": "weak", "source": "estimated"},
    "Musk Ketone": {
        "ec3": 50.0,
        "potency": "weak",
        "source": "estimated",
        "note": "Nitro musk; environmental persistence concern",
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# Banned / Restricted Materials
# ═══════════════════════════════════════════════════════════════════════════════

# Read from the sourced table (canonical names and aliases).
BANNED_MATERIALS: set[str] = set(_IFRA_TABLE.prohibited_names())

# No IFRA standard restricts any material here by jurisdiction alone (DEP has none); the
# name stays for importers.
RESTRICTED_MATERIALS: set[str] = set()

# Materials covered by an IFRA specification standard (grade/purity), not a Cat4 % limit.
IFRA_SPECIFICATION_ONLY: set[str] = set(_IFRA_TABLE.specification_names())


# ═══════════════════════════════════════════════════════════════════════════════
# Scoring Functions
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class IFRASafetyReport:
    """Complete IFRA compliance and allergen safety report."""

    score: float  # 0-100 composite safety score
    ifra_score: float  # 0-100 IFRA compliance
    allergen_score: float  # 0-100 allergen safety
    ifra_violations: list[dict[str, Any]]  # materials exceeding limits
    ifra_warnings: list[dict[str, Any]]  # materials near limits (>70%)
    allergen_declarations: list[str]  # EU allergens requiring label declaration
    sensitizer_flags: list[dict[str, Any]]
    banned_flags: list[str]
    diagnostics: list[str]
    dermal_exposure: list[dict[str, Any]] = field(default_factory=list)
    uptake_weighted_sensitizers: list[dict[str, Any]] = field(default_factory=list)


def _resolve_physchem(name: str) -> tuple[float | None, float | None, str, str]:
    identity = resolve_material(name)
    reg_mat = identity.registry_material
    profile = identity.profile

    logp = getattr(reg_mat, "logp", None)
    logp_source = "registry:data_spine.logp"
    if logp is None:
        logp = getattr(profile, "clogp", None)
        logp_source = (
            "profile:ingredient_intelligence.clogp"
            if logp is not None
            else "default:skin_partition"
        )

    mw = getattr(reg_mat, "mw_g_mol", None)
    mw_source = "registry:data_spine.mw"
    if mw is None:
        mw = getattr(profile, "mw", None)
        mw_source = (
            "profile:ingredient_intelligence.mw" if mw is not None else "default:skin_partition"
        )

    return (
        float(logp) if logp is not None else None,
        float(mw) if mw is not None else None,
        logp_source,
        mw_source,
    )


def _severity(ratio: float) -> str:
    return "critical" if ratio > 3.0 else "moderate" if ratio > 1.5 else "minor"


def _collect_ifra_verdicts(
    evaluation: IFRAEvaluation,
    violations: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
    banned_flags: list[str],
    diagnostics: list[str],
) -> None:
    """Map an IFRA table evaluation onto the report's violation/warning/banned lists."""
    for check in evaluation.checks:
        if check.status == "restricted" and check.verdict in ("fail", "warn"):
            assert check.limit_pct is not None and check.ratio is not None
            row: dict[str, Any] = {
                "material": check.material,
                "actual_pct": round(check.pct, 4),
                "limit_pct": check.limit_pct,
            }
            if check.verdict == "fail":
                row.update(ratio=round(check.ratio, 2), severity=_severity(check.ratio))
                violations.append(row)
            else:
                row["usage_pct"] = round(check.ratio * 100, 1)
                warnings.append(row)
        elif check.status == "prohibited" and check.verdict == "fail":
            banned_flags.append(check.material)
        elif check.verdict in ("note", "hold", "warn"):
            # specification notes, unverified-limit holds, naturals without own standard
            diagnostics.append(f"ℹ IFRA {check.verdict}: {check.message}")
    for group in evaluation.group_checks:
        if group.verdict not in ("fail", "warn"):
            continue
        ratio = group.total / group.limit_pct if group.limit_pct else group.total
        # A sum-of-ratios group (phototoxic citrus) totals limit ratios, allowed up to 1.
        row = {
            "material": group.id,
            "members": dict(group.member_pcts),
            "rule": group.rule,
            "actual_pct": round(group.total, 4),
            "limit_pct": group.limit_pct if group.limit_pct is not None else 1.0,
        }
        if group.verdict == "fail":
            row.update(ratio=round(ratio, 2), severity=_severity(ratio))
            violations.append(row)
        else:
            row["usage_pct"] = round(ratio * 100, 1)
            warnings.append(row)


def score_ifra_compliance(
    ingredients: dict[str, float],
    dilutions: dict[str, float] | None = None,
    total_volume_ml: float = 10.0,
    concentration_pct: float = 20.0,
    leave_on: bool = True,
    *,
    finished_pct_w_w: Mapping[str, float] | None = None,
    alt_names: Mapping[str, Sequence[str] | str] | None = None,
) -> IFRASafetyReport:
    """Score a formula for IFRA compliance and allergen safety.

    Every per-material percentage (IFRA, EU allergen thresholds, sensitizers, dermal
    exposure) is % w/w of the finished product.

    Args:
        ingredients: {name: amount_uL} mapping
        dilutions: {name: dilution_factor} (1.0=neat, 0.1=10%, etc.)
        total_volume_ml: total batch volume in mL
        concentration_pct: concentrate % in finished product
        finished_pct_w_w: {name: % w/w of finished product}; when given it is used as is,
            otherwise it is estimated from the stocks topped up with ethanol to
            ``total_volume_ml`` (unknown densities and carriers at 1.0 g/mL).
        alt_names: extra names per row to match against the IFRA table.

    Returns:
        IFRASafetyReport with composite score and diagnostics.
    """
    dilutions = dilutions or {}
    violations: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    allergen_decl: list[str] = []
    sensitizer_flags: list[dict[str, Any]] = []
    banned_flags: list[str] = []
    restricted_flags: list[str] = []
    dermal_exposure: list[dict[str, Any]] = []
    diagnostics: list[str] = []

    if finished_pct_w_w is None:
        estimate = estimate_finished_product_pct_w_w(
            (
                FinishedProductRow(name, amount_ul, active_fraction=dilutions.get(name, 1.0))
                for name, amount_ul in ingredients.items()
            ),
            total_volume_ml,
        )
        finished_pct_w_w = estimate.pct_w_w
    pct_by_material = {name: float(finished_pct_w_w.get(name, 0.0)) for name in ingredients}
    evaluation = evaluate_ifra(pct_by_material, table=_IFRA_TABLE, alt_names=alt_names)
    _collect_ifra_verdicts(evaluation, violations, warnings, banned_flags, diagnostics)

    for name in ingredients:
        pct_in_product = pct_by_material[name]
        logp, mw, logp_source, mw_source = _resolve_physchem(name)
        partition = skin_partition(name, logp=logp, mw_g_mol=mw)
        exposure_index = pct_in_product * partition.fraction_into_skin
        dermal_row = {
            "material": name,
            "pct_in_product": round(pct_in_product, 6),
            "logp": round(logp, 4) if logp is not None else None,
            "mw_g_mol": round(mw, 4) if mw is not None else None,
            "logp_source": logp_source,
            "mw_source": mw_source,
            "fraction_into_skin": round(partition.fraction_into_skin, 6),
            "effective_exposure_index": round(exposure_index, 6),
            "depot_tau_min": round(partition.depot_tau_s / 60.0, 3),
            "sebum_factor": round(partition.sebum_factor, 3),
        }
        dermal_exposure.append(dermal_row)

        # Check EU allergen declaration threshold
        name.lower()
        for allergen_name, allergen_data in EU_FRAGRANCE_ALLERGENS.items():
            mapped = _ALLERGEN_NAME_MAP.get(name, name)
            if mapped.lower() == allergen_name.lower() or name.lower() == allergen_name.lower():
                threshold = _allergen_threshold_pct(allergen_data, leave_on=leave_on)
                if pct_in_product > threshold:
                    if allergen_name not in allergen_decl:
                        allergen_decl.append(allergen_name)

        # Check sensitization risk
        sens_data = SENSITIZATION_DATA.get(name)
        if sens_data and pct_in_product > 0.01:
            if sens_data["potency"] in ("moderate", "strong", "extreme"):
                sensitizer_flags.append(
                    {
                        "material": name,
                        "potency": sens_data["potency"],
                        "ec3": sens_data["ec3"],
                        "pct_in_product": round(pct_in_product, 4),
                        "fraction_into_skin": dermal_row["fraction_into_skin"],
                        "effective_exposure_index": dermal_row["effective_exposure_index"],
                    }
                )

        # Legacy jurisdiction-only restrictions (prohibitions come from the IFRA table)
        if name in RESTRICTED_MATERIALS:
            restricted_flags.append(name)

    # ── Compute scores ──
    # IFRA score: start at 100, deduct per violation
    ifra_score = 100.0
    for v in violations:
        if v["severity"] == "critical":
            ifra_score -= 30
        elif v["severity"] == "moderate":
            ifra_score -= 15
        else:
            ifra_score -= 5
    for w in warnings:
        ifra_score -= 1  # minor deduction for near-limit
    ifra_score = max(0.0, ifra_score)

    # Allergen score: more allergens requiring declaration = lower score
    # Not inherently bad (most fine fragrances declare 5-10), but awareness matters
    allergen_score = max(0.0, 100.0 - len(allergen_decl) * 3.0)

    # Sensitization penalty
    sens_penalty = 0.0
    for sf in sensitizer_flags:
        if sf["potency"] == "extreme":
            sens_penalty += 20
        elif sf["potency"] == "strong":
            sens_penalty += 10
        elif sf["potency"] == "moderate":
            sens_penalty += 4

    # Banned materials = catastrophic
    if banned_flags:
        ifra_score = 0.0

    # Composite
    composite = ifra_score * 0.5 + allergen_score * 0.3 + max(0, 100 - sens_penalty) * 0.2
    dermal_exposure.sort(key=lambda row: row["effective_exposure_index"], reverse=True)
    uptake_weighted_sensitizers = sorted(
        sensitizer_flags,
        key=lambda row: row.get("effective_exposure_index", 0.0),
        reverse=True,
    )[:5]

    # Diagnostics
    if not violations and not banned_flags:
        diagnostics.insert(0, "✓ All materials within IFRA Category 4 limits")
    if allergen_decl:
        diagnostics.append(
            f"ℹ {len(allergen_decl)} EU fragrance allergen(s) require label declaration: "
            + ", ".join(sorted(allergen_decl))
        )
    if sensitizer_flags:
        names = [sf["material"] for sf in sensitizer_flags]
        diagnostics.append(f"⚠ Sensitization-active materials: {', '.join(names)}")
    if warnings:
        names = [f"{w['material']} ({w['usage_pct']}%)" for w in warnings]
        diagnostics.append(f"ℹ Near IFRA limits: {', '.join(names)}")
    if restricted_flags:
        diagnostics.append(
            "⚠ Legacy experimental materials in formula: "
            + ", ".join(sorted(set(restricted_flags)))
            + " (allowed for local bench use here; review current regulations before any commercial use)"
        )
    if uptake_weighted_sensitizers:
        names = [
            f"{row['material']} ({row['effective_exposure_index']:.4f})"
            for row in uptake_weighted_sensitizers[:3]
        ]
        diagnostics.append(
            "ℹ Dermal uptake overlay (effective exposure index): " + ", ".join(names)
        )

    return IFRASafetyReport(
        score=round(composite, 1),
        ifra_score=round(ifra_score, 1),
        allergen_score=round(allergen_score, 1),
        ifra_violations=violations,
        ifra_warnings=warnings,
        allergen_declarations=sorted(allergen_decl),
        sensitizer_flags=sensitizer_flags,
        banned_flags=banned_flags,
        dermal_exposure=dermal_exposure,
        uptake_weighted_sensitizers=uptake_weighted_sensitizers,
        diagnostics=diagnostics,
    )
