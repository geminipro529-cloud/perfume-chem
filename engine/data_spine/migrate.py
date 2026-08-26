"""Migration: union all known sources into the A-Z YAML data spine.

Sources merged (in priority order — later sources override earlier
when the field is more authoritative):

1. ``engine/diffusion_model.py::DIFFUSION_DATA``      — MW, VP, Kaw
2. ``engine/odor_thresholds.py::ODT_DATA``            — ODT, Stevens-n
3. ``engine/skin_interaction.py::SKIN_PHYSCHEM``      — logP, MW
4. ``engine/trigeminal.py::TRIGEMINAL_PROFILES``      — TRP targets
5. ``engine/hedonic_model.py::HEDONIC_VALENCE``       — hedonic
6. ``inventory.txt``                                   — stock dilution
7. ``knowledge/perfumersworld_stock.md``               — supplier SKU/price

Per-field provenance is tracked so audits and external-AI feedback can
target exactly the gaps that need new data.

Run::

    python -m engine.data_spine.migrate
"""

from __future__ import annotations

import re
from pathlib import Path

from .loader import write_materials
from .material import Material
from .perfumersworld_parser import (
    index_by_base,
    parse_pw_stock,
    write_parsed_snapshot,
)

REPO = Path(__file__).resolve().parents[2]
DATA_DIR = REPO / "data" / "materials"
SOURCES_DIR = DATA_DIR / "_sources"


# ── Filtering: non-fragrance catalog noise ────────────────────────────────────

_NON_MATERIAL_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in (
        r"^amber glass bottles?\b",
        r"^clear glass bottles?\b",
        r"^aluminium bottles?\b",
        r"^aluminum bottles?\b",
        r"^plastic bottles?\b",
        r"^bottles?\b",
        r"^caps?\b",
        r"^pump\b",
        r"^sprayer\b",
        r"^atomi[sz]er\b",
        r"^pipette\b",
        r"^dropper\b",
        r"^funnel\b",
        r"^vial\b",
        r"\bdisplay kit\b",
        r"\bcustom creation\b",
        r"^7-step\b",
        r"^isniff\b",
        r"^box\b",
        r"^label\b",
        r"^card\b",
        r"^card holder\b",
        r"^carry bag\b",
        r"^accord base\b",
        r"^smelling strips?\b",
        r"^blotter\b",
        r"\bworkshop\b",
        r"\bunscented\b",
        r"shampoo base",
        r"body lotion base",
        r"cream base",
        r"\bmaterials$",     # "Black Pepper Materials" (catalog header)
    )
]


_ACRONYMS = {"EO", "FCF", "ND", "FO", "HC", "HD", "DPG", "DEP", "TEC", "MNA"}


def _fix_acronyms(name: str) -> str:
    parts = name.split()
    return " ".join(p.upper() if p.upper() in _ACRONYMS else p for p in parts)


def _is_non_material(name: str) -> bool:
    n = name.strip()
    if not n:
        return True
    if n.startswith("--") or n.startswith("==") or n.startswith("##"):
        return True
    return any(p.search(n) for p in _NON_MATERIAL_PATTERNS)


# ── Name normalization ────────────────────────────────────────────────────────

# Aliases unify variants like "DBCA" / "Dimethyl Benzyl Carbinyl Acetate",
# "Aldehyde C-10" / "Aldehyde C10", title-case vs lowercase, etc.
_CANONICAL_OVERRIDES: dict[str, str] = {
    "ibq": "Isobutyl Quinoline",
    "dbca": "DBCA",
    "aca": "Amyl Cinnamic Aldehyde",
    "pedmc": "Phenyl Ethyl Dimethyl Carbinol",
    "pea": "Phenethyl Alcohol",
    "phenethyl alcohol": "Phenethyl Alcohol",
    "phenyl ethyl alcohol": "Phenethyl Alcohol",
    "iso e super": "Iso E Super",
    "cis-3-hexenol": "cis-3-Hexenol",
    "d-limonene": "D-Limonene",
    "bergamot fcf oil sicilian": "Bergamot FCF Sicilian",
    "cedrat fcf oil sicilian": "Cedrat FCF Sicilian",
    "blood orange oil sicilian": "Blood Orange Sicilian",
    "cedarwood virginia": "Cedarwood Virginia EO",
    "cedarwood oil virginia": "Cedarwood Virginia EO",
    "cedarwood": "Cedarwood EO",
    "vetiver": "Vetiver EO",
    "lilyreal": "Lilyreal ND",
    "heliotropin": "Heliotropal",
    "piperonal": "Heliotropal",
    "methyl ionone gamma": "Methyl Ionone Pure",
    "alpha-isomethyl ionone": "Methyl Ionone Pure",
    "methyl ionone": "Methyl Ionone Pure",
    "carrot seed": "Carrot Seed EO",
    "bergamot": "Bergamot FCF",
    "bergamot eo": "Bergamot FCF",
    "vertofix": "Vertofix Coeur",
    "ylang comoros iii eo": "Ylang Comoros III EO",
}


def _canonical(name: str) -> str:
    """Normalise a name to its canonical form used as the spine key.

    Merges by case-fold so 'Aldehyde C10' and 'aldehyde c10' point to
    the same record. Title-cases the canonical display form.
    """
    raw = name.strip()
    key = raw.casefold()
    if key in _CANONICAL_OVERRIDES:
        return _CANONICAL_OVERRIDES[key]
    # smart title-case: keep small particles, hyphens, and roman numerals as-is
    parts = raw.split()
    out: list[str] = []
    for p in parts:
        if p.isupper() and len(p) <= 5:        # acronym (DBCA, EO, FCF, ND, HC)
            out.append(p)
        elif re.fullmatch(r"[ivxIVX]+", p):    # roman numeral
            out.append(p.upper())
        elif "-" in p:                          # cis-3-Hexenol style
            sub = p.split("-")
            out.append("-".join(s.capitalize() if not s.isupper() else s for s in sub))
        else:
            out.append(p.capitalize())
    return _fix_acronyms(" ".join(out))


def _key(name: str) -> str:
    """Casefolded merge key — guarantees no duplicates by case."""
    return _canonical(name).casefold()


def _get_or_create(reg: dict[str, Material], raw_name: str) -> Material | None:
    if _is_non_material(raw_name):
        return None
    canon = _canonical(raw_name)
    k = canon.casefold()
    m = reg.get(k)
    if m is None:
        m = Material(canonical_name=canon)
        reg[k] = m
    if raw_name != canon and raw_name not in m.aliases:
        m.aliases.append(raw_name)
    return m


def _set(mat: Material, attr: str, value, source: str) -> None:
    """Assign a field only if not already set; record provenance."""
    cur = getattr(mat, attr)
    if cur is None or cur == [] or cur == "":
        setattr(mat, attr, value)
        mat.provenance[attr] = source


# ── Source ingestion ──────────────────────────────────────────────────────────


def _ingest_diffusion(reg: dict[str, Material]) -> None:
    from engine.diffusion_model import DIFFUSION_DATA
    for name, vals in DIFFUSION_DATA.items():
        m = _get_or_create(reg, name)
        if m is None:
            continue
        _set(m, "mw_g_mol", vals.get("MW"), "engine.diffusion_model")
        _set(m, "vp_25c_pa", vals.get("VP_25"), "engine.diffusion_model")
        _set(m, "kaw_eff", vals.get("Kaw_eff"), "engine.diffusion_model")


def _ingest_odt(reg: dict[str, Material]) -> None:
    try:
        from engine.odor_thresholds import ODT_DATA
    except Exception:  # noqa: BLE001
        return
    for name, vals in ODT_DATA.items():
        m = _get_or_create(reg, name)
        if m is None:
            continue
        if isinstance(vals, dict):
            _set(m, "odt_air_ppb", vals.get("ODT_air_ppb") or vals.get("odt_air_ppb"),
                 "engine.odor_thresholds")
            _set(m, "odt_eth_ppm", vals.get("ODT_eth_ppm") or vals.get("odt_eth_ppm"),
                 "engine.odor_thresholds")
            _set(m, "stevens_n", vals.get("Stevens_n") or vals.get("stevens_n"),
                 "engine.odor_thresholds")
            char = vals.get("character") or vals.get("descriptor")
            if char:
                _set(m, "character", char, "engine.odor_thresholds")
        elif isinstance(vals, (int, float)):
            _set(m, "odt_air_ppb", float(vals), "engine.odor_thresholds")


def _ingest_skin(reg: dict[str, Material]) -> None:
    try:
        from engine.skin_interaction import SKIN_PHYSCHEM
    except Exception:  # noqa: BLE001
        return
    for name, vals in SKIN_PHYSCHEM.items():
        m = _get_or_create(reg, name)
        if m is None or not isinstance(vals, dict):
            continue
        _set(m, "mw_g_mol", vals.get("MW") or vals.get("mw"), "engine.skin_interaction")
        _set(m, "logp", vals.get("logP") or vals.get("logp"), "engine.skin_interaction")


def _ingest_trigeminal(reg: dict[str, Material]) -> None:
    try:
        from engine.trigeminal import TRIGEMINAL_PROFILES
    except Exception:  # noqa: BLE001
        return
    for name, vals in TRIGEMINAL_PROFILES.items():
        m = _get_or_create(reg, name)
        if m is None or not isinstance(vals, dict):
            continue
        for key, dst in (
            ("TRPM8", "TRPM8"),
            ("TRPA1", "TRPA1"),
            ("TRPV1", "TRPV1"),
            ("TRPV3", "TRPV3"),
            ("nasal_pungency", "nasal_pungency"),
        ):
            v = vals.get(key)
            if v is not None and getattr(m.trp_targets, dst) is None:
                setattr(m.trp_targets, dst, float(v) if isinstance(v, (int, float, bool)) else v)
                m.provenance[f"trp.{dst}"] = "engine.trigeminal"


def _ingest_hedonic(reg: dict[str, Material]) -> None:
    try:
        from engine.hedonic_model import HEDONIC_VALENCE
    except Exception:  # noqa: BLE001
        return
    for name, val in HEDONIC_VALENCE.items():
        m = _get_or_create(reg, name)
        if m is None:
            continue
        if isinstance(val, dict):
            v = val.get("valence") or val.get("hedonic")
        else:
            v = val
        if isinstance(v, (int, float)):
            _set(m, "hedonic_valence", float(v), "engine.hedonic_model")


_INV_SECTION_RE = re.compile(r"^---\s*([A-Z /]+?)\s*---\s*$")
_INV_LINE_RE = re.compile(
    r"^-\s*(?P<name>[^()#]+?)(?:\s*\((?P<dil>[^)]+)\))?\s*(?:#.*)?$"
)


def _ingest_inventory(reg: dict[str, Material], path: Path) -> None:
    """Mark user_in_inventory + user_stock_dilution from inventory.txt."""
    if not path.exists():
        return
    current_section: str | None = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        m = _INV_SECTION_RE.match(s)
        if m:
            current_section = m.group(1).strip()
            continue
        if not s.startswith("-"):
            continue
        mm = _INV_LINE_RE.match(s)
        if not mm:
            continue
        raw_name = mm.group("name").strip()
        dil = (mm.group("dil") or "").strip() or None
        m = _get_or_create(reg, raw_name)
        if m is None:
            continue
        m.user_in_inventory = True
        m.provenance["user_in_inventory"] = "inventory.txt"
        if dil and not m.user_stock_dilution:
            m.user_stock_dilution = dil
            m.provenance["user_stock_dilution"] = "inventory.txt"
        if current_section and current_section.lower() not in (
            f.lower() for f in m.families
        ):
            m.families.append(current_section.lower())


def _ingest_perfumersworld(reg: dict[str, Material], stock_path: Path) -> None:
    """Attach PerfumersWorld SKU + price for every parent (neat) entry,
    and record dilutions in supplier.other['dilutions'].
    """
    if not stock_path.exists():
        return
    entries = parse_pw_stock(stock_path)
    write_parsed_snapshot(entries, SOURCES_DIR / "perfumersworld_stock.parsed.json")
    by_base = index_by_base(entries)
    for base_name, items in by_base.items():
        m = _get_or_create(reg, base_name)
        if m is None:
            continue
        # flag pre-blended supplier products (FTEC, Fleuressence, F-TEC, Accord,
        # FO, Core) so the optimizer can skip them per user formula rules.
        low = base_name.lower()
        if any(tag in low for tag in (
            "ftec", "f-tec", "fleuressence", "accord", " fo", " core", "isniff",
        )) and "pre-blended" not in m.families:
            m.families.append("pre-blended")
        # neat entry — pick lowest dilution_pct (None = neat)
        neat = next(
            (e for e in items if e.dilution_pct is None),
            min(items, key=lambda e: (e.dilution_pct or 0.0)),
        )
        if not m.supplier.perfumersworld_sku:
            m.supplier.perfumersworld_sku = neat.sku
            m.supplier.perfumersworld_price_usd_per_g = neat.price_usd
            m.supplier.perfumersworld_form = (
                "neat" if neat.dilution_pct is None
                else f"{neat.dilution_pct}% in {neat.dilution_solvent}"
            )
            m.supplier.perfumersworld_snapshot_date = "2026-04-11"
            m.provenance["supplier.perfumersworld"] = "knowledge/perfumersworld_stock.md"
        # any other dilutions stored as alternate forms
        alt = []
        for e in items:
            if e is neat:
                continue
            alt.append({
                "form": (
                    "neat" if e.dilution_pct is None
                    else f"{e.dilution_pct}% in {e.dilution_solvent}"
                ),
                "sku": e.sku,
                "price_usd_per_g": e.price_usd,
            })
        if alt:
            m.supplier.other["pw_alternate_forms"] = alt


# ── Driver ────────────────────────────────────────────────────────────────────


def build_registry() -> dict[str, Material]:
    reg: dict[str, Material] = {}
    _ingest_diffusion(reg)
    _ingest_odt(reg)
    _ingest_skin(reg)
    _ingest_trigeminal(reg)
    _ingest_hedonic(reg)
    _ingest_inventory(reg, REPO / "inventory.txt")
    _ingest_perfumersworld(reg, REPO / "knowledge" / "perfumersworld_stock.md")
    return reg


def main() -> None:
    print("[migrate] building registry…")
    reg = build_registry()
    print(f"[migrate] {len(reg)} canonical materials")
    # remove stale A-Z files so deletions/merges don't leave orphans
    if DATA_DIR.exists():
        for stale in DATA_DIR.glob("*.yaml"):
            stale.unlink()
    counts = write_materials(reg.values(), DATA_DIR)
    for letter in sorted(counts):
        print(f"  {letter}: {counts[letter]}")
    total_inv = sum(1 for m in reg.values() if m.user_in_inventory)
    total_pw = sum(1 for m in reg.values() if m.supplier.perfumersworld_sku)
    print(f"[migrate] in user inventory: {total_inv}")
    print(f"[migrate] with PerfumersWorld SKU: {total_pw}")
    print(f"[migrate] data → {DATA_DIR}")


if __name__ == "__main__":
    main()
