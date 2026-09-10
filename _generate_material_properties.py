#!/usr/bin/env python3
"""Self-auditing material_properties.json generation pipeline.

Phase 1 — Merge all internal data sources (profiles, ODTs, IFRA, Hill params).
Phase 2 — PubChem live verification via CAS: auto-fill formula, flag MW/logP divergences.
Phase 3 — Compute OAV, smell strength, anosmic risk with corrected heuristics.
Phase 4 — Write material_properties.json + audit_flags.json.
Phase 5 — Print coverage / divergence report.
"""

import json
import sys
import time
from collections import OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import requests

from engine.dose_response import CHARACTER_SHIFT_DATA, HILL_PARAMS
from engine.ifra_safety import (
    BANNED_MATERIALS,
    IFRA_CAT4_LIMITS,
    IFRA_SPECIFICATION_ONLY,
    RESTRICTED_MATERIALS,
)
from engine.ingredient_intelligence import _PROFILES
from engine.inventory_parser import parse_inventory
from engine.name_utils import normalize_name
from engine.odor_thresholds import ODT_DATA

# ═══════════════════════════════════════════════════════════════════════
# Phase 1 — Indexes from internal modules
# ═══════════════════════════════════════════════════════════════════════

odt_air_index: dict[str, float | None] = {
    normalize_name(k): v.get("odt_air") for k, v in ODT_DATA.items()
}
odt_eth_index: dict[str, float | None] = {
    normalize_name(k): v.get("odt_eth") for k, v in ODT_DATA.items()
}
odt_char_index: dict[str, str | None] = {
    normalize_name(k): v.get("char") for k, v in ODT_DATA.items()
}
profile_index: dict[str, tuple[str, dict]] = {
    normalize_name(k): (k, v) for k, v in _PROFILES.items()
}
hill_index: dict[str, dict] = {normalize_name(k): v for k, v in HILL_PARAMS.items()}
charshift_index: dict[str, list] = {normalize_name(k): v for k, v in CHARACTER_SHIFT_DATA.items()}
ifra_index: dict[str, float] = {normalize_name(k): v for k, v in IFRA_CAT4_LIMITS.items()}

# Known CAS numbers (literature cross-referenced)
CAS_MAP: dict[str, str] = {
    "2-acetyl pyrazine": "22047-25-2",
    "adoxal": "141-13-9",
    "aldehyde c10": "112-31-2",
    "aldehyde c11": "112-44-7",
    "aldehyde c11 undecylenic": "112-45-8",
    "aldehyde c12 mna": "110-41-8",
    "aldehyde c8": "124-13-0",
    "aldehyde c9": "124-19-6",
    "allyl amyl glycolate": "67634-00-8",
    "allyl ionone": "79-78-7",
    "alpha damascone": "24720-09-0",
    "alpha ionone": "127-41-3",
    "alpha irone": "79-69-6",
    "alpha-isomethyl ionone": "127-51-5",
    "amber core": "proprietary",
    "amber xtreme": "476332-65-7",
    "ambermax": "proprietary",
    "ambrettolide": "28645-51-4",
    "ambrocenide": "211299-54-6",
    "ambrofix": "6790-58-5",
    "ambrox super": "6790-58-5",
    "amyl cinnamic aldehyde": "122-40-7",
    "amyl salicylate": "2050-08-0",
    "anisaldehyde": "123-11-5",
    "apritone": "68133-79-9",
    "aurantiol": "89-43-0",
    "azarbre": "68845-36-3",
    "bacdanol": "28219-61-6",
    "benzyl acetate": "140-11-4",
    "benzyl alcohol": "100-51-6",
    "benzyl benzoate": "120-51-4",
    "benzyl salicylate": "118-58-1",
    "benzoin resinoid": "9000-05-9",
    "benzoin sumatra resinoid": "9000-05-9",
    "bergamot fcf": "68648-33-9",
    "beta damascone": "23726-91-2",
    "beta ionone": "14901-07-6",
    "beta-pinene": "127-91-3",
    "birch tar rectified": "8001-88-5",
    "black agarwood artificial": "proprietary",
    "bourgeonal": "18127-01-0",
    "calone": "28940-11-6",
    "cardamom ftec": "proprietary",
    "cashmeran": "33704-61-9",
    "castoreum synthetic": "proprietary",
    "cedramber": "19870-74-7",
    "cedamber": "19870-74-7",
    "champignol": "3687-48-7",
    "cinnamaldehyde": "104-55-2",
    "cinnamyl alcohol": "104-54-1",
    "cis-3-hexenol": "928-96-1",
    "cis-3-hexenyl salicylate": "65405-77-8",
    "cis jasmone": "488-10-8",
    "citral": "5392-40-5",
    "citronellal": "106-23-0",
    "citronellol": "106-22-9",
    "civetone": "542-46-1",
    "clearwood": "proprietary",
    "coriander essential oil": "8008-52-4",
    "coumarin": "91-64-5",
    "cyclamen aldehyde": "103-95-7",
    "damascenone": "23696-85-7",
    "dbca": "151-05-3",
    "delta decalactone": "705-86-2",
    "dihydromyrcenol": "18479-58-8",
    "d-limonene": "5989-27-5",
    "dynascone": "56973-85-4",
    "ebanol": "67801-20-1",
    "ethyl 2-methylbutyrate": "7452-79-1",
    "ethyl linalool": "10339-55-6",
    "ethyl maltol": "4940-11-8",
    "ethyl safranate": "35044-59-8",
    "ethyl vanillin": "121-32-4",
    "ethylene brassylate": "105-95-3",
    "eugenol": "97-53-0",
    "evernyl": "4707-47-5",
    "exaltolide": "106-02-5",
    "farnesol": "4602-84-0",
    "floralozone": "67634-15-5",
    "florhydral": "125109-85-5",
    "florol": "63500-71-0",
    "galaxolide": "1222-05-5",
    "gamma decalactone": "706-14-9",
    "gamma undecalactone": "104-67-6",
    "geosmin": "19700-21-1",
    "geraniol": "106-24-1",
    "guaiacol": "90-05-1",
    "habanolide": "111879-80-2",
    "hedione": "24851-98-7",
    "helional": "1205-17-0",
    "heliotropin": "120-57-0",
    "hexyl acetate": "142-92-7",
    "hexyl salicylate": "6259-76-3",
    "hydroxycitronellal": "107-75-5",
    "indole": "120-72-9",
    "jasmine absolute": "8022-96-6",
    "iso e super": "54464-57-2",
    "isobutyl quinoline": "1333-58-0",
    "isoeugenol": "97-54-1",
    "javanol": "198404-98-7",
    "kephalis": "36306-87-3",
    "labdanum absolute": "8016-26-0",
    "leafovert": "proprietary",
    "lemonile": "61792-11-8",
    "lilial": "80-54-6",
    "lilyreal nd": "proprietary",
    "linalool": "78-70-6",
    "linalyl acetate": "115-95-7",
    "macrolide": "106-02-5",
    "maltol": "118-71-8",
    "maple lactone": "698-10-2",
    "mayol": "13828-37-0",
    "melonal": "106-72-9",
    "methyl anthranilate": "134-20-3",
    "methyl benzoate": "93-58-3",
    "methyl ionone": "1335-46-2",
    "methyl pamplemousse": "67674-46-8",
    "methyl salicylate": "119-36-8",
    "musk ketone": "81-14-1",
    "nerol": "106-25-2",
    "nirvanolide": "propietary",
    "norlimbanol": "70788-30-6",
    "norlimbanol dextro": "70788-30-6",
    "nympheal": "1637294-12-2",
    "oranger crystals": "93-08-3",
    "orivone": "16587-71-6",
    "p-cresyl methyl ether": "104-93-8",
    "paradisamide": "406488-30-0",
    "parmavert": "proprietary",
    "peonile": "10461-98-0",
    "phenethyl alcohol": "60-12-8",
    "polysantol": "107898-54-4",
    "raspberry ketone": "5471-51-2",
    "romandolide": "380009-87-8",
    "rose oxide": "16409-43-1",
    "safraleine": "54440-17-4",
    "sandalore": "65113-99-7",
    "scentenal": "86803-90-9",
    "siam benzoin": "9000-72-0",
    "skatole": "83-34-1",
    "suederal": "proprietary",
    "terpinyl acetate": "80-26-2",
    "timberol": "70788-30-6",
    "tonalide": "21145-77-7",
    "triplal": "68039-49-6",
    "undecavertol": "81782-77-6",
    "vanillin": "121-33-5",
    "verdox": "88-41-5",
    "vertofix": "32388-55-9",
    "vertofix coeur": "32388-55-9",
    "vetikon": "7403-42-1",
    "vetival": "proprietary",
    "vetiveryl acetate": "117-98-6",
    "violet leaf absolute": "8024-41-7",
    "zenolide": "proprietary",
}

# Name aliases: inventory name → canonical profile key
ALIASES = {
    "alpha isomethyl ionone": "Alpha-Isomethyl Ionone",
    "amyl cinnamic aldehyde": "ACA",
    "ambrofix crystals": "Ambrofix",
    "cardamom eo": "Cardamom EO",
    "cinnamyl alcohol 50% in dpg": "Cinnamyl Alcohol",
    "cyclimal aldehyde": "Cyclamen Aldehyde",
    "diethyl phthalate": "Diethyl Phthalate",
    "dimethyl benzyl carbinyl acetate": "DBCA",
    "dipropylene glycol": "Dipropylene Glycol",
    "ethanol 96%": "Ethanol",
    "hedione hc": "Hedione",
    "isopropyl myristate": "Isopropyl Myristate",
    "lavender eo bontaux sas": "Lavender EO",
    "lemon fcf oil sicilian": "Lemon FCF oil Sicilian",
    "nagarmortha oil": "Cypriol EO",
    "olibanum resinoid absolute": "Olibanum Resinoid",
    "p-cresyl methyl ether (pcme)": "p-Cresyl Methyl Ether",
    "patchouli essential oil": "Patchouli EO",
    "phenyl ethyl dimethyl carbinol": "PEDMC",
    "rosemary eo": "Rosemary EO (French Rosmarinus Officinalis leaf oil)",
    "triethyl citrate": "Triethyl Citrate",
    "sandalwood fragrance oil": "Sandalwood FO",
    "tonka bean fragrance oil": "Tonka Bean FO",
    "dep": "Diethyl Phthalate",
    "lavender eo (bontaux sas)": "Lavender EO",
    "vetiver eo (india)": "Vetiver EO",
    "vetiver eo india": "Vetiver EO",
    "vetiver essential oil": "Vetiver EO",
}

# ═══════════════════════════════════════════════════════════════════════
# Phase 2 — PubChem verification
# ═══════════════════════════════════════════════════════════════════════

PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
PUBCHEM_TIMEOUT = 8  # seconds
PUBCHEM_RATE = 0.25  # seconds between requests (4/sec — well under 5/sec limit)
_pubchem_cache: dict[str, dict] = {}


def fetch_pubchem(cas: str) -> dict:
    """Fetch MW, formula, XLogP from PubChem by CAS. Returns {} on failure."""
    if cas in _pubchem_cache:
        return _pubchem_cache[cas]
    url = f"{PUBCHEM_BASE}/compound/name/{cas}/property/MolecularWeight,MolecularFormula,XLogP,ExactMass/JSON"
    try:
        r = requests.get(url, timeout=PUBCHEM_TIMEOUT)
        if r.status_code == 200:
            props = r.json().get("PropertyTable", {}).get("Properties", [{}])[0]
            result = {
                "mw_pubchem": float(props.get("MolecularWeight", 0)) or None,
                "formula_pubchem": props.get("MolecularFormula"),
                "logp_pubchem": props.get("XLogP"),
                "cid": props.get("CID"),
            }
        else:
            result = {}
    except Exception:
        result = {}
    _pubchem_cache[cas] = result
    time.sleep(PUBCHEM_RATE)
    return result


def check_divergence(field: str, db_val, pub_val) -> dict | None:
    """Return a flag dict if db_val diverges significantly from pub_val."""
    if db_val is None or pub_val is None:
        return None
    if field == "vp":
        # Factor-based tolerance for VP (±2×)
        lo, hi = min(db_val, pub_val), max(db_val, pub_val)
        if lo <= 0:
            lo = 1e-9
        ratio = max(db_val, pub_val) / lo
        if ratio > 2.0:
            return {
                "field": field,
                "db_value": db_val,
                "pubchem_value": pub_val,
                "ratio": round(ratio, 1),
            }
    elif field == "mw":
        if abs(db_val - pub_val) > 0.5:
            return {
                "field": field,
                "db_value": db_val,
                "pubchem_value": pub_val,
                "delta": round(abs(db_val - pub_val), 2),
            }
    elif field == "logp":
        if abs(db_val - pub_val) > 0.5:
            return {
                "field": field,
                "db_value": db_val,
                "pubchem_value": pub_val,
                "delta": round(abs(db_val - pub_val), 2),
            }
    return None


# ═══════════════════════════════════════════════════════════════════════
# Phase 3 — Heuristics: OAV, smell strength, anosmic risk
# ═══════════════════════════════════════════════════════════════════════

TYPICAL_DOSE: dict[str, float] = {
    "aldehyde c10": 0.5,
    "aldehyde c11": 0.3,
    "aldehyde c12 mna": 0.2,
    "bergamot eo": 5.0,
    "bergamot fcf": 5.0,
    "lemon eo": 3.0,
    "linalool": 3.0,
    "linalyl acetate": 4.0,
    "d-limonene": 2.0,
    "cis-3-hexenol": 0.1,
    "calone": 0.05,
    "scentenal": 0.1,
    "geosmin": 0.001,
    "triplal": 0.03,
    "hedione": 8.0,
    "rose oxide": 0.05,
    "geraniol": 2.0,
    "citronellol": 3.0,
    "phenethyl alcohol": 5.0,
    "lilial": 2.0,
    "hydroxycitronellal": 3.0,
    "indole": 0.1,
    "alpha ionone": 2.0,
    "beta ionone": 1.0,
    "alpha irone": 0.5,
    "iso e super": 15.0,
    "cashmeran": 3.0,
    "galaxolide": 10.0,
    "habanolide": 3.0,
    "vanillin": 2.0,
    "coumarin": 3.0,
    "ambrox super": 2.0,
    "patchouli eo": 3.0,
    "vetiver eo": 2.0,
    "cedarwood eo": 5.0,
    # Legacy / non-inventory entries
    "amber core accord": 5.0,
    "amber xtreme": 5.0,
    "bacdanol": 3.0,
    "benzoin resinoid": 3.0,
    "cedamber": 3.0,
    "heliotropin": 2.0,
    "jasmin abs f-tec": 3.0,
    "labdanum absolute": 3.0,
    "lavender eo (bontaux sas)": 5.0,
    "methyl ionone": 3.0,
    "molecule iris": 2.0,
    "myrrh eo": 2.0,
    "patchouli essential oil": 3.0,
    "pink pepper base": 3.0,
    "sandalwood fragrance oil": 3.0,
    "styrax ftec": 2.0,
    "tonka bean fragrance oil": 3.0,
    "vertofix coeur": 5.0,
    "vetiver eo (india)": 2.0,
    "vetiver essential oil": 2.0,
    "cocoa absolute": 3.0,
    "evernyl 50% in dpg": 6.0,
    "galbanum eo": 2.0,
    "immortelle absolute": 3.0,
    "oakmoss absolute": 2.0,
    "osmanthus absolute": 3.0,
    "petitgrain eo paraguay": 4.0,
    "phenyl ethyl acetate": 5.0,
    "rose de mai absolute": 3.0,
    "tonkarome": 4.0,
    "tuberalia base": 5.0,
    "tuberose absolute": 3.0,
    "tuberose absolute (india)": 3.0,
    # ── Inventory additions 2026-06-14 ──
    "himalayan cedarwood eo": 5.0,
    "cassis base 345b": 3.0,
    "clove eo": 3.0,
    "anise eo": 4.0,
    "basil eo": 4.0,
}


def typical_dose_pct(norm_name: str, role: str | None, odt_eth: float | None) -> float:
    if norm_name in TYPICAL_DOSE:
        return TYPICAL_DOSE[norm_name]
    if odt_eth is not None:
        if odt_eth < 0.001:
            return 0.5
        elif odt_eth < 0.01:
            return 1.0
        elif odt_eth < 0.1:
            return 2.0
        elif odt_eth < 1.0:
            return 3.0
        elif odt_eth < 10.0:
            return 5.0
        elif odt_eth < 50.0:
            return 8.0
        else:
            return 10.0
    role_map = {
        "trace": 0.1,
        "modifier": 1.0,
        "character": 3.0,
        "core": 5.0,
        "radiance": 8.0,
        "fixative": 5.0,
        "bridge": 2.0,
        "volume": 4.0,
    }
    return role_map.get(role or "", 3.0)


def smell_strength(odt_eth: float | None) -> str:
    if odt_eth is None:
        return "unknown"
    if odt_eth < 0.001:
        return "ultra-strong"
    elif odt_eth < 0.01:
        return "very-strong"
    elif odt_eth < 0.1:
        return "strong"
    elif odt_eth < 1.0:
        return "moderate-strong"
    elif odt_eth < 10.0:
        return "moderate"
    elif odt_eth < 100.0:
        return "weak"
    else:
        return "very-weak"


def anosmic_risk(mw: float | None, odt_air: float | None, or_family: str | None) -> str:
    """Corrected heuristic: heavy musks/ambers (MW≥220) + high odt → true anosmia risk."""
    if mw is None:
        return "unknown"
    is_heavy = mw >= 220
    is_high_threshold = (odt_air or 999) > 10.0
    is_musk_amber = any(t in (or_family or "").lower() for t in ["musk", "amber", "macrocyclic"])
    if (is_heavy and is_high_threshold) or (is_heavy and is_musk_amber):
        return "high — specific anosmia risk (heavy musk/amber, MW≥220)"
    if (odt_air or 999) < 0.01:
        return "low threshold, dose carefully"
    return "standard"


CHAR_TO_FAMILY = {
    "citrus": "citrus",
    "freshness": "citrus",
    "green": "green",
    "herbal": "aromatic",
    "floral": "floral",
    "sweetness": "floral",
    "indolic": "floral",
    "powdery": "iris",
    "woody": "woody",
    "warmth": "amber",
    "radiance": "muguet",
    "musk": "musk",
    "creamy": "floral",
    "fatty": "floral",
    "waxy": "floral",
    "smoky": "smoky",
    "spicy": "spice",
    "earth": "earth",
    "animalic": "animalic",
    "fresh": "green",
    "ozone": "aquatic",
    "diffusion": "floral",
    "lift": "citrus",
    "depth": "woody",
    "cushion": "musk",
    "veil": "floral",
    "halo": "floral",
    "cocoon": "musk",
    "skin-effect": "musk",
}


def infer_odor_family(profile: dict | None, norm_name: str) -> str:
    if profile and profile.get("or_family"):
        return profile["or_family"]
    char = odt_char_index.get(norm_name, "")
    if char:
        for kw, family in CHAR_TO_FAMILY.items():
            if kw in char.lower():
                return family
    return "unknown"


def infer_odor_profile(profile: dict | None, odt_char: str | None, name: str) -> str:
    if profile and profile.get("character"):
        chars = profile["character"]
        if isinstance(chars, dict):
            sorted_chars = sorted(chars.items(), key=lambda x: -x[1])
            parts = [f"{k}-like ({v})" if v > 5 else k for k, v in sorted_chars[:4]]
            return ", ".join(parts) + " character."
        if isinstance(chars, str):
            return chars.strip(" .") + " character."
    if odt_char:
        return odt_char.capitalize() + "."
    return f"{name} — odor profile pending literature review."


# ═══════════════════════════════════════════════════════════════════════
# Load existing material_properties.json (preserve hand-crafted narrative)
# ═══════════════════════════════════════════════════════════════════════

def legacy_main():
    """Historical online implementation; retained for source provenance only."""
    MP_PATH = Path("data/knowledge_graph/material_properties.json")
    existing_index: dict[str, dict] = {}
    if MP_PATH.exists():
        with open(MP_PATH, "r", encoding="utf-8") as f:
            for m in json.load(f):
                existing_index[normalize_name(m["name"])] = m

    # ═══════════════════════════════════════════════════════════════════════
    # Build all entries
    # ═══════════════════════════════════════════════════════════════════════

    inventory = parse_inventory(Path("inventory.txt"))
    inventory_dilutions = {m.name: m.dilution for m in inventory}
    inventory_records = {m.name: m for m in inventory}
    inventory_names = [m.name for m in inventory]
    output = []
    audit_flags: list[dict] = []
    seen_names: set[str] = set()
    seen_dedup: set[str] = set()  # prevents duplicate entries by lowercase name

    for inv_name in sorted(inventory_names):
        norm = normalize_name(inv_name)
        canonical = ALIASES.get(norm, None)
        canonical_norm = normalize_name(canonical) if canonical else norm

        # Preserve existing rich entries, enriching with computed fields
        existing = existing_index.get(canonical_norm) or existing_index.get(norm)
        if existing:
            entry = OrderedDict(existing)
            seen_names.add(normalize_name(existing.get("name", "")))
        else:
            entry = OrderedDict()
            entry["name"] = inv_name
            entry["alt_name"] = canonical if canonical else None

        # ── Physical properties ─ ALWAYS override from profile (authoritative) ─
        profile = None
        for key in [canonical_norm, norm]:
            if key in profile_index:
                _, profile = profile_index[key]
                break

        if profile:
            # Physical chemistry: profile values are authoritative, always overwrite
            for src_field, dst_field in [
                ("mw", "mw"),
                ("vp", "vp"),
                ("clogp", "clp"),
                ("note", "note"),
                ("role", "role"),
                ("texture", "texture"),
            ]:
                val = profile.get(src_field)
                if val is not None:
                    entry[dst_field] = val
            # Synergies / or_family: prefer existing if non-empty, else fill
            if profile.get("synergies") and not entry.get("synergies"):
                entry["synergies"] = profile["synergies"]
            if profile.get("or_family") and not entry.get("or_family"):
                entry["or_family"] = profile["or_family"]
            if profile.get("activity_coef") and not entry.get("activity_coef"):
                entry["activity_coef"] = profile["activity_coef"]
            if profile.get("hedonic") and not entry.get("hedonic"):
                entry["hedonic"] = profile["hedonic"]
            if profile.get("cas") and not entry.get("cas"):
                entry["cas"] = profile["cas"]

        # ── ODT ─ profile odt/odt_ppm already enriched from ODT_DATA, override ──
        if profile:
            if profile.get("odt") is not None:
                entry["odt"] = profile["odt"]
            if profile.get("odt_ppm") is not None:
                entry["odt_ethanol_ppm"] = profile["odt_ppm"]

        odt_air = entry.get("odt")
        odt_eth = entry.get("odt_ethanol_ppm")
        # Fallback: ODT_DATA lookup for entries without profiles
        if odt_air is None:
            odt_air = odt_air_index.get(canonical_norm) or odt_air_index.get(norm)
            if odt_air is not None:
                entry["odt"] = odt_air
        if odt_eth is None:
            odt_eth = odt_eth_index.get(canonical_norm) or odt_eth_index.get(norm)
            if odt_eth is not None:
                entry["odt_ethanol_ppm"] = odt_eth

        odt_char = odt_char_index.get(canonical_norm) or odt_char_index.get(norm)

        # ── OAV / smell strength / anosmic ───────────────────────────
        mw_val = entry.get("mw")
        role_val = entry.get("role")
        or_family_val = entry.get("or_family")
        dose_pct = typical_dose_pct(norm, role_val, odt_eth or entry.get("odt_ethanol_ppm"))
        dose_ppm = dose_pct * 10000
        oav = (
            dose_ppm / (odt_eth or entry.get("odt_ethanol_ppm") or 1)
            if (odt_eth or entry.get("odt_ethanol_ppm"))
            else None
        )
        entry["oav_typical"] = round(oav, 1) if oav else None
        entry["oav_dose_pct"] = dose_pct
        entry["smell_strength"] = smell_strength(odt_eth or entry.get("odt_ethanol_ppm"))
        entry["anosmic_risk"] = anosmic_risk(mw_val, odt_air, or_family_val)

        # ── Odor family / profile ────────────────────────────────────
        entry.setdefault("odor_family", infer_odor_family(profile, norm))
        if not entry.get("odor_profile"):
            entry["odor_profile"] = infer_odor_profile(profile, odt_char, inv_name)

        # ── IFRA ─────────────────────────────────────────────────────
        ifra_limit = ifra_index.get(norm) or ifra_index.get(canonical_norm)
        entry["ifra_cat4_limit_pct"] = ifra_limit
        entry["ifra_banned"] = inv_name in BANNED_MATERIALS or (canonical or "") in BANNED_MATERIALS
        entry["ifra_restricted"] = (
            inv_name in RESTRICTED_MATERIALS or (canonical or "") in RESTRICTED_MATERIALS
        )
        # IFRA 51st — specification-only standards (not concentration limits)
        entry["ifra_standard_type"] = (
            "specification" if inv_name in IFRA_SPECIFICATION_ONLY else "restriction"
        )

        # ── Activity coefficients (UNIFAC estimates for headspace corrections) ─
        ACTIVITY_COEF_OVERRIDES = {
            "limonene": 3.2,
            "beta-pinene": 3.0,
            "d-limonene": 3.2,
            "linalool": 1.8,
            "linalyl acetate": 2.1,
            "citronellol": 1.7,
            "geraniol": 1.6,
            "benzyl acetate": 1.2,
            "hedione": 1.3,
            "calone": 1.1,
            "alpha irone": 1.5,
            "polysantol": 0.7,
            "benzyl salicylate": 0.8,
            "galaxolide": 0.7,
            "ambrox super": 0.6,
            "vanillin": 0.5,
            "coumarin": 0.7,
        }
        # Override activity_coef with UNIFAC estimate (always trust UNIFAC over II defaults)
        for key in [canonical_norm, norm]:
            if key in ACTIVITY_COEF_OVERRIDES:
                entry["activity_coef"] = ACTIVITY_COEF_OVERRIDES[key]
                break

        # ── Hill params ──────────────────────────────────────────────
        hill = hill_index.get(norm) or hill_index.get(canonical_norm)
        entry["hill_ec50"] = hill.get("EC50") if hill else None
        entry["hill_n"] = hill.get("n") if hill else None
        entry["hill_rmax"] = hill.get("Rmax", 1.0) if hill else None

        # ── Character shift ──────────────────────────────────────────
        cs = charshift_index.get(norm) or charshift_index.get(canonical_norm)
        entry["character_shift"] = []
        if cs:
            entry["character_shift"] = [
                {
                    "max_conc_pct": z.max_conc_pct,
                    "character": z.character,
                    "quality": z.quality,
                }
                for z in cs
            ]

        # ── Dilution ─────────────────────────────────────────────────
        entry["dilution_pct"] = inventory_dilutions.get(inv_name)
        entry["in_inventory"] = True
        inventory_record = inventory_records[inv_name]
        if inventory_record.dilution >= 0.999:
            entry["stock_form"] = "neat"
        else:
            stock_pct = f"{inventory_record.dilution * 100:g}%"
            carrier = inventory_record.carrier.upper()
            entry["stock_form"] = f"{stock_pct} in {carrier}" if carrier else f"{stock_pct} dilution"

        # ── Remaining fields (null if empty) ─────────────────────────
        for null_field in [
            "cas",
            "formula_str",
            "bp",
            "sar_class",
            "olfactophore",
            "arctander_character",
            "arctander_tenacity",
            "carles_position",
            "carles_pairing_rule",
            "roudnitska_function",
            "roudnitska_craft_note",
            "jellinek_axis",
            "jellinek_quadrant",
            "jellinek_effect",
            "max_safe_pct",
            "stock_form",
            "handle_as",
            "avoid",
        ]:
            entry.setdefault(null_field, None)

        # Entries from existing have best_with; auto-fill from synergies if missing
        if not entry.get("best_with") and entry.get("synergies"):
            entry["best_with"] = entry["synergies"]
        elif not entry.get("best_with"):
            entry["best_with"] = []

        if not entry.get("typical_pct_range") and dose_pct > 0:
            entry["typical_pct_range"] = (
                f"{max(0.01, dose_pct * 0.3):g}–{dose_pct * 2:g}% of concentrate"
            )
        elif not entry.get("typical_pct_range"):
            entry["typical_pct_range"] = None

        # ── CAS (try profile, then CAS_MAP, then existing) ────────
        if not entry.get("cas"):
            for key in [canonical_norm, norm]:
                if key in CAS_MAP:
                    entry["cas"] = CAS_MAP[key]
                    break

        # ── Phase 2: PubChem verification + auto-override ────────────
        entry_flags: list[dict] = []
        pc_warnings: list[str] = []
        cas_val = entry.get("cas")
        if cas_val and cas_val not in (
            "N/A (proprietary blend)",
            "Proprietary",
            "Proprietary mixture",
            "proprietary",
            None,
        ):
            # Detect useless CAS (generic proprietaries often have bogus CAS)
            if cas_val.lower().startswith("proprietary"):
                pc_warnings.append(f"CAS '{cas_val}' is proprietary — PubChem lookup skipped")
            else:
                pub = fetch_pubchem(cas_val)
                if pub:
                    entry["pubchem_cid"] = pub.get("cid")
                    if not entry.get("formula_str"):
                        entry["formula_str"] = pub.get("formula_pubchem")

                    # ── Auto-override MW from PubChem when divergence > 2% ──
                    pc_mw = pub.get("mw_pubchem")
                    db_mw = entry.get("mw")
                    if pc_mw and db_mw and pc_mw > 0 and abs(pc_mw - db_mw) / pc_mw > 0.02:
                        flag = check_divergence("mw", db_mw, pc_mw)
                        if flag:
                            flag["name"] = inv_name
                            flag["action"] = "AUTO-OVERRIDE: PubChem trusted"
                            entry_flags.append(flag)
                        entry["mw"] = round(pc_mw, 2)

                    # ── Auto-override cLogP from PubChem when divergence > 0.5 ──
                    pc_logp = pub.get("logp_pubchem")
                    db_logp = entry.get("clp")
                    if pc_logp is not None and db_logp is not None and abs(db_logp - pc_logp) > 0.5:
                        flag = check_divergence("logp", db_logp, pc_logp)
                        if flag:
                            flag["name"] = inv_name
                            flag["action"] = "AUTO-OVERRIDE: PubChem trusted"
                            entry_flags.append(flag)
                        entry["clp"] = round(pc_logp, 2)
                else:
                    # PubChem returned nothing for this CAS — log as warning
                    pc_warnings.append(f"PubChem returned null for CAS {cas_val}")

        if pc_warnings:
            entry["pubchem_warnings"] = pc_warnings
        else:
            entry["pubchem_warnings"] = []
        if entry_flags:
            audit_flags.append({"name": inv_name, "flags": entry_flags})
        entry["audit_flags"] = entry_flags

        # ── Dedup guard ─────────────────────────────────────────────
        entry_lower = entry.get("name", "").lower()
        if entry_lower in seen_dedup:
            continue  # skip duplicate (same name already written)
        seen_dedup.add(entry_lower)

        output.append(entry)


    # ═══════════════════════════════════════════════════════════════════════
    # Preserve materials in existing knowledge graph not in inventory
    # ═══════════════════════════════════════════════════════════════════════
    inventory_norms = set()
    for inv_name in inventory_names:
        n = normalize_name(inv_name)
        c = ALIASES.get(n)
        inventory_norms.add(n)
        if c:
            inventory_norms.add(normalize_name(c))

    for norm_key, mp_entry in existing_index.items():
        if (
            norm_key not in inventory_norms
            and normalize_name(mp_entry.get("name", "")) not in seen_names
        ):
            entry = mp_entry.copy()
            entry["in_inventory"] = False

            # ── Enrich non-inventory legacy entries with profile data ──
            _norm = normalize_name(entry.get("name", ""))
            _canonical = ALIASES.get(_norm)
            _canonical_norm = normalize_name(_canonical) if _canonical else _norm
            _profile = None
            for _key in [_canonical_norm, _norm]:
                if _key in profile_index:
                    _, _profile = profile_index[_key]
                    break

            if _profile:
                # Physical chemistry: profile values are authoritative, always overwrite
                for _src, _dst in [
                    ("mw", "mw"),
                    ("vp", "vp"),
                    ("clogp", "clp"),
                    ("note", "note"),
                    ("role", "role"),
                    ("texture", "texture"),
                ]:
                    if _profile.get(_src) is not None:
                        entry[_dst] = _profile[_src]
                if _profile.get("activity_coef") and entry.get("activity_coef") is None:
                    entry["activity_coef"] = _profile["activity_coef"]
                if _profile.get("or_family") and entry.get("or_family") is None:
                    entry["or_family"] = _profile["or_family"]
                if _profile.get("hedonic") and entry.get("hedonic") is None:
                    entry["hedonic"] = _profile["hedonic"]
                if _profile.get("synergies") and not entry.get("synergies"):
                    entry["synergies"] = _profile["synergies"]
                # ODT: profile values (enriched from ODT_DATA) override existing
                if _profile.get("odt") is not None:
                    entry["odt"] = _profile["odt"]
                if _profile.get("odt_ppm") is not None:
                    entry["odt_ethanol_ppm"] = _profile["odt_ppm"]

            # Recompute OAV / smell strength / anosmic risk if missing
            _odt_eth = entry.get("odt_ethanol_ppm")
            _role = entry.get("role")
            _mw = entry.get("mw")
            _or_fam = entry.get("or_family")
            if entry.get("oav_typical") is None and _odt_eth is not None and float(_odt_eth) > 0:
                _dose = typical_dose_pct(_norm, _role, _odt_eth)
                entry["oav_dose_pct"] = _dose
                entry["oav_typical"] = round(_dose * 10000 / _odt_eth, 1)
            if entry.get("smell_strength") is None:
                entry["smell_strength"] = smell_strength(_odt_eth)
            if entry.get("anosmic_risk") is None:
                entry["anosmic_risk"] = anosmic_risk(_mw, entry.get("odt"), _or_fam)
            if entry.get("odor_family") is None:
                entry["odor_family"] = infer_odor_family(_profile, _norm)
            if not entry.get("odor_profile"):
                _char = odt_char_index.get(_norm)
                entry["odor_profile"] = infer_odor_profile(_profile, _char, entry.get("name", ""))

            # IFRA standard type
            if entry.get("ifra_standard_type") is None:
                _ifra_limit = ifra_index.get(_norm)
                entry["ifra_cat4_limit_pct"] = _ifra_limit
                entry["ifra_standard_type"] = (
                    "specification"
                    if entry.get("name", "") in IFRA_SPECIFICATION_ONLY
                    else "restriction"
                )

            # Hill params / character shift
            _hill = hill_index.get(_norm)
            if _hill and entry.get("hill_ec50") is None:
                entry["hill_ec50"] = _hill.get("EC50")
                entry["hill_n"] = _hill.get("n")
                entry["hill_rmax"] = _hill.get("Rmax", 1.0)
            _cs = charshift_index.get(_norm)
            if _cs and not entry.get("character_shift"):
                entry["character_shift"] = [
                    {
                        "max_conc_pct": z.max_conc_pct,
                        "character": z.character,
                        "quality": z.quality,
                    }
                    for z in _cs
                ]

            seen_dedup.discard(entry.get("name", "").lower())  # allow non-inventory entries
            output.append(entry)

    # ═══════════════════════════════════════════════════════════════════════
    # Write output files
    # ═══════════════════════════════════════════════════════════════════════

    with open(MP_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    with open("data/knowledge_graph/audit_flags.json", "w", encoding="utf-8") as f:
        json.dump(audit_flags, f, indent=2, ensure_ascii=False)

    # ═══════════════════════════════════════════════════════════════════════
    # Phase 5 — Report
    # ═══════════════════════════════════════════════════════════════════════

    total = len(output)
    print(f"\n{'=' * 60}")
    print(f"  material_properties.json  —  {total} entries written")
    print(f"  audit_flags.json          —  {len(audit_flags)} entries flagged")
    print(f"{'=' * 60}")

    FIELDS = [
        ("odt", "ODT air (ppb)"),
        ("odt_ethanol_ppm", "ODT ethanol (ppm)"),
        ("oav_typical", "OAV (typical dose)"),
        ("smell_strength", "Smell strength"),
        ("anosmic_risk", "Anosmic risk"),
        ("mw", "Molecular weight"),
        ("vp", "Vapor pressure (Pa)"),
        ("clp", "cLogP"),
        ("synergies", "Synergies"),
        ("note", "Volatility note"),
        ("role", "Perfumery role"),
        ("texture", "Texture"),
        ("or_family", "Odor family (Raoult)"),
        ("activity_coef", "Activity coeff"),
        ("hedonic", "Hedonic score"),
        ("ifra_cat4_limit_pct", "IFRA Cat4 limit"),
        ("ifra_banned", "IFRA banned"),
        ("dilution_pct", "Inventory dilution"),
        ("hill_ec50", "Hill EC50"),
        ("character_shift", "Character shift zones"),
        ("cas", "CAS number"),
        ("formula_str", "Molecular formula"),
        ("pubchem_cid", "PubChem CID"),
        ("sar_class", "SAR class"),
        ("carles_position", "Carles position"),
        ("arctander_character", "Arctander char"),
    ]
    print(f"\n{'Field':<25} {'Coverage':>10}  {'Status'}")
    print("-" * 60)
    for f, label in FIELDS:
        count = sum(
            1
            for m in output
            if m.get(f) is not None and m.get(f) != [] and m.get(f) != "" and m.get(f) != False
        )
        pct = round(count / total * 100) if total else 0
        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
        print(f"  {label:<23} {count:>4}/{total} {bar} {pct}%")

    if audit_flags:
        print(f"\n  ⚠ {len(audit_flags)} entries have PubChem divergences → audit_flags.json")
        for a in audit_flags[:5]:
            for f in a["flags"]:
                print(f"    {a['name']}: {f['field']} db={f['db_value']} pubchem={f['pubchem_value']}")
        if len(audit_flags) > 5:
            print(f"    ... and {len(audit_flags) - 5} more")


def main():
    """Offline default: preserve narrative and bind current stocks and evidence."""
    from engine.data_spine.reconciliation import generate

    report = generate()
    print(json.dumps(report["counts"], indent=2))
    print("Authority: computational reconciliation only; unresolved evidence remains HOLD.")


if __name__ == "__main__":
    main()
