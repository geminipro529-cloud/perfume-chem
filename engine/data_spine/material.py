"""Canonical Material schema.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**
- Concentrations in ppm (parts per million w/w in concentrate).
- ODT in ppm for ethanol solution (odt_eth_ppm), ppb for air (odt_air_ppb).
- OAV = concentration_ppm / ODT_ppm (dimensionless).
- Every perceptibility claim must be backed by OAV. No exceptions.

A `Material` is the single record describing one ingredient across every
science axis the simulator cares about. Most fields are optional — the
spine is fillable: missing values are explicit ``None`` (not absent
keys), so completeness audits and external-AI feedback can target
exactly the gaps that need data.

Fields are grouped by domain:

* **Identity**: canonical_name, aliases, CAS, SMILES, InChIKey
* **Physical**: MW, density, logP, functional groups, chirality
* **Vapor phase**: VP@25C, Antoine A/B/C, ΔH_vap
* **Solubility / phase**: Hansen δd/δp/δh
* **Olfactory**: ODT (air, ethanol), Stevens exponent
* **Receptor**: OR targets (gene, EC50, Hill), TRP/CT targets
* **Hedonic / regulatory**: valence, IFRA cap
* **Stock state**: dilution as held by user
* **Supplier**: PerfumersWorld SKU + price, other refs
* **Categorization**: top/heart/base, families, character blurb
* **Provenance**: per-field source-of-truth tags
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any

# ── Sub-records ────────────────────────────────────────────────────────────────


@dataclass
class Antoine:
    """Antoine vapor pressure equation: log10(P[mmHg]) = A − B / (C + T[°C]).

    Convert to Pa via ``P_pa = 133.322 * 10**(A − B / (C + T_celsius))``.
    """

    A: float | None = None
    B: float | None = None
    C: float | None = None
    T_min_c: float | None = None
    T_max_c: float | None = None
    source: str | None = None


@dataclass
class HSP:
    """Hansen Solubility Parameters (MPa^0.5)."""

    delta_d: float | None = None  # dispersion
    delta_p: float | None = None  # polar
    delta_h: float | None = None  # hydrogen-bond
    source: str | None = None


@dataclass
class ORTarget:
    """One olfactory-receptor binding record."""

    or_gene: str  # e.g. "OR5A1"
    ec50_um: float | None = None  # half-max concentration, micromolar
    hill: float | None = 1.0  # Hill coefficient, default 1
    efficacy: float | None = 1.0  # 0–1 partial-agonist scaling
    source: str | None = None  # "Mainland 2014" | "Trimmer 2019" | "homology"


@dataclass
class TRPTargets:
    """Trigeminal / chemesthetic activation flags + intensities."""

    TRPM8: float | None = None  # cold (menthol-class), 0–1
    TRPA1: float | None = None  # pungent / electrophile, 0–1
    TRPV1: float | None = None  # heat / capsaicin-class, 0–1
    TRPV3: float | None = None
    nasal_pungency: float | None = None  # composite trigeminal score 0-1


@dataclass
class SupplierRefs:
    """Cross-supplier identifiers and price snapshots."""

    perfumersworld_sku: str | None = None
    perfumersworld_price_usd_per_g: float | None = None
    perfumersworld_form: str | None = None  # "neat" | "1% in DPG" | etc.
    perfumersworld_snapshot_date: str | None = None
    other: dict[str, Any] = field(default_factory=dict)


# ── Top-level record ───────────────────────────────────────────────────────────


@dataclass
class Material:
    """One canonical aroma-chemical / natural / extract record."""

    # --- identity ---
    canonical_name: str
    aliases: list[str] = field(default_factory=list)
    cas: str | None = None
    smiles: str | None = None
    inchikey: str | None = None

    # --- physical ---
    mw_g_mol: float | None = None
    density_25c_g_ml: float | None = None
    logp: float | None = None
    functional_groups: list[str] = field(default_factory=list)
    chirality: str | None = None  # "R" | "S" | "racemic" | "achiral" | "mixture"

    # --- vapor phase ---
    vp_25c_pa: float | None = None
    # "placeholder" marks an unsourced round value; the gate reports it as estimated.
    vp_source: str | None = None
    antoine: Antoine = field(default_factory=Antoine)
    dhvap_kj_mol: float | None = None
    kaw_eff: float | None = None  # legacy effective air-water partition

    # --- solubility / phase ---
    hsp: HSP = field(default_factory=HSP)

    # --- olfactory ---
    odt_air_ppb: float | None = None
    odt_eth_ppm: float | None = None
    stevens_n: float | None = None

    # --- receptor ---
    or_targets: list[ORTarget] = field(default_factory=list)
    trp_targets: TRPTargets = field(default_factory=TRPTargets)

    # --- perception / regulatory ---
    hedonic_valence: float | None = None  # −1 .. +1
    ifra_max_pct_edp: float | None = None

    # --- inventory / supplier ---
    user_stock_dilution: str | None = None  # "neat" | "10% in DPG" | "1% in TEC" | …
    user_in_inventory: bool = False
    supplier: SupplierRefs = field(default_factory=SupplierRefs)

    # --- categorization ---
    families: list[str] = field(default_factory=list)  # ["citrus","top"]
    character: str | None = None  # short blurb
    notes: str | None = None  # freeform

    # --- provenance: per-field source tag ---
    provenance: dict[str, str] = field(default_factory=dict)

    # ------------------------------------------------------------------ helpers
    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # drop empty sub-record dicts to keep YAML tight
        for k in ("antoine", "hsp", "trp_targets", "supplier"):
            sub = d.get(k) or {}
            if all(v is None or v == {} for v in sub.values()):
                d[k] = None
        if not d.get("or_targets"):
            d["or_targets"] = []
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Material":
        data = dict(data)
        if not data.get("canonical_name") and data.get("name"):
            data["canonical_name"] = data["name"]
        if data.get("antoine") is None:
            data["antoine"] = {}
        if data.get("hsp") is None:
            data["hsp"] = {}
        if data.get("trp_targets") is None:
            data["trp_targets"] = {}
        if data.get("supplier") is None:
            data["supplier"] = {}
        data["antoine"] = Antoine(**data["antoine"])
        data["hsp"] = HSP(**data["hsp"])
        data["trp_targets"] = TRPTargets(**data["trp_targets"])
        data["supplier"] = SupplierRefs(**data["supplier"])
        data["or_targets"] = [
            ORTarget(**t) if isinstance(t, dict) else t for t in data.get("or_targets") or []
        ]
        # filter unknown keys
        keep = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in keep})

    def completeness(self) -> dict[str, bool]:
        """Per-field has-data flag for audit / external-AI feedback."""
        return {
            "cas": self.cas is not None,
            "smiles": self.smiles is not None,
            "mw": self.mw_g_mol is not None,
            "logp": self.logp is not None,
            "vp_25c": self.vp_25c_pa is not None,
            "antoine": self.antoine.A is not None,
            "dhvap": self.dhvap_kj_mol is not None,
            "hsp": self.hsp.delta_d is not None,
            "odt_air": self.odt_air_ppb is not None,
            "or_targets": bool(self.or_targets),
            "trp": any(
                getattr(self.trp_targets, k) is not None
                for k in ("TRPM8", "TRPA1", "TRPV1", "TRPV3", "nasal_pungency")
            ),
            "hedonic": self.hedonic_valence is not None,
            "ifra": self.ifra_max_pct_edp is not None,
            "supplier": self.supplier.perfumersworld_sku is not None,
        }


# ── Registry ───────────────────────────────────────────────────────────────────


class MaterialRegistry:
    """In-memory material lookup, keyed by canonical_name and aliases."""

    def __init__(self, materials: list[Material]):
        self._by_canonical: dict[str, Material] = {}
        self._by_alias: dict[str, Material] = {}
        for m in materials:
            self._by_canonical[m.canonical_name.casefold()] = m
            for a in m.aliases:
                self._by_alias[a.casefold()] = m

    def __len__(self) -> int:
        return len(self._by_canonical)

    def __contains__(self, name: str) -> bool:
        n = name.casefold()
        return n in self._by_canonical or n in self._by_alias

    def get(self, name: str) -> Material | None:
        n = name.casefold()
        return self._by_canonical.get(n) or self._by_alias.get(n)

    def all(self) -> list[Material]:
        return list(self._by_canonical.values())
