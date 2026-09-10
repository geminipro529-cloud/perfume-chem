"""Unified ingredient catalog builder and loader."""

from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any

from engine.ingredient_intelligence import find_similar, get_profile
from engine.inventory_parser import parse_inventory
from engine.material_identity import resolve_material_identity

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "knowledge_graph" / "ingredient_catalog.json"
SHOPPING_LIST_PATH = PROJECT_ROOT / "shopping_list.md"
CHEMICAL_INVENTORY_PATH = PROJECT_ROOT / "knowledge" / "chemical_inventory.md"
MATERIAL_PROPERTIES_PATH = PROJECT_ROOT / "data" / "knowledge_graph" / "material_properties.json"
PAIRING_RULES_PATH = PROJECT_ROOT / "data" / "knowledge_graph" / "pairing_rules.json"

_GREEK_MAP = str.maketrans({
    "α": "alpha",
    "β": "beta",
    "γ": "gamma",
    "δ": "delta",
    "’": "'",
})

_TOKEN_REPLACEMENTS = {
    "aimi": "alpha isomethyl ionone",
    "ambroxide": "ambrox super",
    "cetone": "ketone",
    "dbca": "dimethyl benzyl carbinyl acetate",
    "e2mb": "ethyl 2 methylbutyrate",
    "ibq": "isobutyl quinoline",
    "i-iris": "i iris",
    "orris ftec": "orris f tec",
    "phenyl ethyl alcohol": "phenethyl alcohol",
}

_ALIASES: dict[str, list[str]] = {
    "alpha irone": ["alpha irone", "alpha-irone", "alpha irone 10", "alpha irone 10%", "alpha irone 3%"],
    "alpha isomethyl ionone": ["alpha isomethyl ionone", "alpha-isomethyl ionone", "aimi", "methyl ionone pure"],
    "alpha ionone": ["alpha ionone", "alpha-ionone", "ionone alpha"],
    "allyl ionone": ["allyl ionone", "allyl ionone ketone v", "allyl ionone cetone v", "ketone v", "cetone v"],
    "ambrox super": ["ambrox super", "ambroxide"],
    "ambrox super 33% dep/etoh": ["ambrox super 33% dep/etoh", "ambrox super 20", "ambrox super dep", "ambrox super 33"],
    "beta ionone": ["beta ionone", "beta-ionone", "ionone beta"],
    "cedramber": ["cedramber", "cedamber"],
    "hedione": ["hedione", "methyl dihydrojasmonate"],
    "i iris f tec": ["i iris f tec", "i iris ftec", "i iris", "i-iris f-tec", "i-iris ftec"],
    "labdanum absolute": ["labdanum absolute", "labdamum absolute"],
    "methyl ionone": ["methyl ionone", "methyl-ionone"],
    "orris f tec": ["orris f tec", "orris ftec", "orris f-tec"],
    "phenethyl alcohol": ["phenethyl alcohol", "phenyl ethyl alcohol", "pea"],
    "rose oxide": ["rose oxide", "rose oxide 1", "rose oxide 1%", "rose oxide 10", "rose oxide 10%"],
    "scentenal": ["scentenal", "scentenal 1", "scentenal 1%"],
}

_CATEGORY_CONTEXTS = {
    "citrus / top": {
        "common": [
            "top-note lift in citrus, cologne, sport, and aromatic openings",
            "polish floral and woody openings so they read brighter and more expensive",
        ],
        "niche": ["aldehydic-luxury sparkle or bitter citrus framing in niche iris, neroli, and chypre work"],
        "best_in": ["cologne", "sport", "fresh woody", "neroli floral", "chypre openings"],
        "avoid_in": ["overly sweet gourmands unless used only as contrast top"],
        "implementations": [
            ("Citrus Opening Frame", "common", "Build the first 5-20 minutes of a citrus, neroli, or aromatic opening."),
            ("Luxury Sparkle Layer", "common", "Add clean expensive lift above floral or woody hearts without changing the identity too much."),
            ("Crystal Chypre Accent", "niche", "Use at restrained dose to sharpen bitter-green, aldehydic, or mineral-chypre textures."),
        ],
    },
    "green / fresh / marine": {
        "common": [
            "inject green, ozonic, watery, or sporty freshness into the opening and upper heart",
            "open up dense florals, musks, and woods so the formula breathes",
        ],
        "niche": ["create wet-leaf, rain-on-glass, violet-leaf, or marine-mineral tension in avant-garde structures"],
        "best_in": ["sport", "transparent musk", "marine", "green floral", "fresh woody"],
        "avoid_in": ["heavy oriental or syrupy gourmand bases if used above trace"],
        "implementations": [
            ("Sport Freshness Spine", "common", "Anchor the sporty-clean axis in masculine, unisex, and office-safe formulas."),
            ("Green Air Vent", "common", "Crack open heavy floral, iris, amber, or musk bases with a green-airy vent."),
            ("Wet Mineral Effect", "niche", "Build rain, wet-stone, cucumber-metallic, or transparent marine textures."),
        ],
    },
    "floral materials": {
        "common": [
            "build the main floral heart or soften woody and amber structures with floral volume",
            "bridge citrus tops into musks, woods, and balsams so the composition reads continuous",
        ],
        "niche": ["sculpt specific floral signatures such as lipstick rose, indolic jasmine, green muguet, or tropical narcotic florals"],
        "best_in": ["floral", "floral woody", "musky floral", "oriental floral", "luxury clean"],
        "avoid_in": ["hyper-minimal dry woody formulas unless used as a hidden bridge"],
        "implementations": [
            ("Heart Builder", "common", "Give the perfume its central bloom and emotional identity through the heart."),
            ("Bridge Floral Veil", "common", "Tie citrus tops to woods, ambers, and musks with a soft floral veil."),
            ("Signature Soliflore Accent", "niche", "Push toward a recognizable rose, jasmine, orange-blossom, muguet, or exotic-floral signature."),
        ],
    },
    "iris / violet": {
        "common": [
            "build powdery cosmetic body, luxury iris texture, and violet/orris heart mass",
            "soften woods, ambers, musks, and florals with cool waxy powder and suede-like polish",
        ],
        "niche": ["construct metallic-rooty orris, lipstick powder, violet leaf iris, or DHP-style iris structures"],
        "best_in": ["iris", "powdery musk", "luxury woody floral", "lipstick floral", "suede iris"],
        "avoid_in": ["aquatic or sporty structures if the material is heavy and buttery"],
        "implementations": [
            ("Iris Core", "common", "Build the central iris-violet body in a perfume or accord."),
            ("Powdered Luxury Modifier", "common", "Apply as a cosmetic-softening layer over musks, woods, or florals."),
            ("Rooty Orris Reconstruction", "niche", "Shape metallic, earthy, buttery, and expensive orris effects in niche structures."),
        ],
    },
    "woods / amber / structure": {
        "common": [
            "supply backbone, diffusion, drydown persistence, and woody-amber architecture",
            "frame delicate florals, iris, and musks so the perfume holds shape on skin",
        ],
        "niche": ["build mineral woods, incense-amber space, modern woody skin scents, or dry abstract structure"],
        "best_in": ["woody amber", "niche woody", "musk skin scent", "incense", "modern fresh woody"],
        "avoid_in": ["delicate soliflores if overdosed"],
        "implementations": [
            ("Structural Backbone", "common", "Create the frame that keeps the formula standing from heart into drydown."),
            ("Diffusive Woody Halo", "common", "Add transparent spread and modern woody aura without a dense traditional base."),
            ("Mineral-Resonant Base", "niche", "Build incense, mineral amber, shadow woods, or abstract gallery-like space."),
        ],
    },
    "musks": {
        "common": [
            "create skin-feel, laundry-clean bloom, or soft persistence in the drydown",
            "smooth sharp transitions and make the full formula feel more cohesive and wearable",
        ],
        "niche": ["design metallic steam-clean, powdery vintage, animalic skin, or ultra-clean minimalist musk signatures"],
        "best_in": ["skin scent", "clean musk", "powdery floral", "woody amber", "fresh laundry"],
        "avoid_in": ["already-heavy dense bases if the musk is warm and bulky"],
        "implementations": [
            ("Drydown Musk Bed", "common", "Lay down the final skin cushion and persistence bed."),
            ("Projection Cohesion Layer", "common", "Hold together floral, woody, and amber materials so they project as one cloud."),
            ("Signature Musk Aura", "niche", "Push the formula toward metallic-clean, powdery-classic, or sensual-skin territory."),
        ],
    },
    "sweet / gourmand / balsamic": {
        "common": [
            "round harsh edges, sweeten the base, and extend drydown with warmth and comfort",
            "bridge florals, woods, and resins into softer edible or cosmetic territory",
        ],
        "niche": ["build lacquered benzoin, dark dessert, church resin, lipstick powder, or boozy oriental textures"],
        "best_in": ["gourmand", "oriental", "amber", "powdery floral", "comfort musk"],
        "avoid_in": ["very transparent marine or sport formulas unless used as a trace cushion"],
        "implementations": [
            ("Base Softener", "common", "Take the roughness out of woods, musks, and resins by adding warmth and cushion."),
            ("Sweet-Balsamic Bridge", "common", "Connect floral and citrus elements to the base without a hard drop-off."),
            ("Dark Resin / Dessert Accent", "niche", "Push the formula into ambered church, dessert, tobacco, or lipstick territories."),
        ],
    },
    "leather / smoky / phenolic": {
        "common": [
            "add leather, smoke, birch, ink, or phenolic bite to a base or shadow accord",
            "darken sweet, floral, or woody formulas with a more adult edge",
        ],
        "niche": ["build tarry cuir, church smoke, worn suede, or bitter green leather signatures"],
        "best_in": ["leather", "incense", "dark woody", "animalic floral", "suede iris"],
        "avoid_in": ["clean laundry, sport, and transparent ozone styles unless extremely restrained"],
        "implementations": [
            ("Leather Shadow", "common", "Cast a darker leather or smoke shadow under a floral, iris, or woody formula."),
            ("Dry Bitter Edge", "common", "Introduce adult bitterness and dryness into bases that feel too smooth or sweet."),
            ("Cuir / Incense Statement", "niche", "Turn the perfume toward tar, suede, incense smoke, or bitter-green leather."),
        ],
    },
    "spice / aromatic": {
        "common": [
            "add lift, texture, and recognizable seasoning to fresh, woody, floral, or oriental perfumes",
            "create motion between top and heart while preventing the opening from feeling flat",
        ],
        "niche": ["build sacred spice, dry saffron leather, herbal fougere tension, or aromatic-metallic sparkle"],
        "best_in": ["fougere", "oriental", "fresh woody", "spiced floral", "incense"],
        "avoid_in": ["powdery minimalist skin scents if the spice is very loud"],
        "implementations": [
            ("Seasoned Opening", "common", "Add a readable spice or aromatic signpost in the opening and upper heart."),
            ("Heart Motion Builder", "common", "Keep the perfume moving so it does not go flat between citrus top and woody base."),
            ("Saffron / Sacred Accent", "niche", "Create dry saffron, incense-herbal, or ceremonial spice effects."),
        ],
    },
    "accord bases / ftecs / other": {
        "common": [
            "speed up construction by dropping in pre-shaped facets that would take many raw materials to rebuild",
            "prototype new perfume directions quickly before deciding whether to expand into raw materials",
        ],
        "niche": ["use as modular signatures, reconstruction shortcuts, or controlled stylization tools inside an original formula"],
        "best_in": ["rapid prototyping", "module-based composition", "theme collections", "accord-driven design"],
        "avoid_in": ["high-transparency formulas if the module is too pre-colored"],
        "implementations": [
            ("Module Shortcut", "common", "Drop in a ready-made facet to speed up a formula build."),
            ("Prototype Accelerator", "common", "Sketch perfume directions quickly before expanding the module back into raw materials."),
            ("Signature Module", "niche", "Treat the accord or base as a recurring signature building block across a collection."),
        ],
    },
    "unknown": {
        "common": [
            "use as a supporting material where its specific note and pairing profile fit the formula",
            "test first as a bridge or modifier before assigning it a starring role",
        ],
        "niche": ["probe it in controlled micro-batches to discover unusual textural or bridging behavior"],
        "best_in": ["small trials", "bridge work", "modification passes"],
        "avoid_in": ["blind heavy dosing without test strips"],
        "implementations": [
            ("Bridge Trial", "common", "Trial the material first in a bridge role between top and heart or heart and base."),
            ("Texture Modifier", "common", "Use as a small modifier to observe what it does to feel, polish, and diffusion."),
            ("Micro-Batch Discovery", "niche", "Use in a controlled experimental batch to map its most distinctive use-case."),
        ],
    },
}


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.translate(_GREEK_MAP)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().replace("&", " and ").replace("/", " ")
    text = text.replace("*", " ")
    text = text.replace("—", " ").replace("–", " ").replace("-", " ")
    text = re.sub(r"\[[^\]]+\]\s*$", "", text)
    text = re.sub(r"\b\d+(?:\.\d+)?\s*%\b", " ", text)
    text = re.sub(r"\b\d+(?:\.\d+)?\s*(?:ml|ul|g)\b", " ", text)
    text = re.sub(r"\s*\([^)]*\)\s*$", "", text)
    text = re.sub(r"\((?:[^)]*?(?:dpg|ethanol|ipm|dep|tec|w/v|solution|dilution|stock|form|unknown|neat|essential oil)[^)]*)\)", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    for source, target in _TOKEN_REPLACEMENTS.items():
        text = text.replace(source, target)
    return re.sub(r"\s+", " ", text).strip()


def _identity_key(name: str) -> str:
    identity = resolve_material_identity(name)
    if identity is not None:
        return identity.identity_key
    normalized = _normalize_text(name)
    for canonical, variants in _ALIASES.items():
        if normalized == canonical or normalized in variants:
            return canonical
    return normalized


def _ground_truth_identity(*names: str) -> dict[str, Any] | None:
    for name in names:
        identity = resolve_material_identity(name)
        if identity is None:
            continue
        payload = identity.metadata()
        cas_values = payload.get("cas") or []
        payload["cas"] = cas_values[0] if len(cas_values) == 1 else cas_values
        payload["source"] = "user_confirmed_cas_override"
        payload["confidence"] = "high"
        return payload
    return None


def _prop_record_matches_ground_truth(prop_record: dict[str, Any] | None, ground_truth: dict[str, Any] | None) -> bool:
    if not prop_record or not ground_truth:
        return True
    override_cas = ground_truth.get("cas")
    if isinstance(override_cas, list):
        return any(str(cas) in str(prop_record.get("cas")) for cas in override_cas)
    if isinstance(override_cas, str):
        return override_cas in str(prop_record.get("cas"))
    return True


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        clean = re.sub(r"\s+", " ", str(value or "")).strip()
        if not clean:
            continue
        key = clean.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(clean)
    return output


def _parse_shopping_list() -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    if not SHOPPING_LIST_PATH.exists():
        return results
    current_section = ""
    in_table = False
    material_col = None
    for raw_line in SHOPPING_LIST_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            in_table = False
            material_col = None
            continue
        if stripped.startswith("## "):
            current_section = stripped[3:].strip()
            in_table = False
            material_col = None
            continue
        if current_section.lower() in {"shopping summary", "suggested suppliers"}:
            continue
        check = re.match(r"^- \[[ xX]\]\s+`?(.+?)`?\s*$", stripped)
        if check:
            name = check.group(1).strip()
            key = _identity_key(name)
            bucket = results.setdefault(key, {"names": set(), "sections": set(), "priority": set()})
            bucket["names"].add(name)
            bucket["sections"].add(current_section)
            bucket["priority"].add("Current User Buy / Restock List")
            continue
        if stripped.startswith("|"):
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if not in_table:
                lowered = [cell.lower() for cell in cells]
                if "material" in lowered:
                    material_col = lowered.index("material")
                    in_table = True
                continue
            if set("".join(cells)) <= {"-", ":"}:
                continue
            if material_col is None or material_col >= len(cells):
                continue
            name = re.sub(r"\*\*", "", cells[material_col]).strip()
            if not name or name.lower() in {"material", "materials"}:
                continue
            key = _identity_key(name)
            bucket = results.setdefault(key, {"names": set(), "sections": set(), "priority": set()})
            bucket["names"].add(name)
            bucket["sections"].add(current_section)
            bucket["priority"].add(current_section)
            continue
        in_table = False
        material_col = None
    normalized: dict[str, dict[str, Any]] = {}
    for key, data in results.items():
        normalized[key] = {
            "names": sorted(data["names"]),
            "sections": sorted(data["sections"]),
            "priority": sorted(data["priority"]),
        }
    return normalized


def _parse_chemical_inventory() -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    if not CHEMICAL_INVENTORY_PATH.exists():
        return results
    for line in CHEMICAL_INVENTORY_PATH.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or "**" not in line:
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) < 10:
            continue
        name = parts[1].replace("**", "").strip()
        if not name or name.lower() == "chemical name":
            continue
        key = _identity_key(name)
        bucket = results.setdefault(
            key,
            {
                "names": set(),
                "cas": set(),
                "forms": set(),
                "ifra": set(),
                "notes": set(),
                "dates": set(),
                "quantities": set(),
                "status_flags": set(),
            },
        )
        bucket["names"].add(name)
        if parts[2] and parts[2] != "N/A":
            bucket["cas"].add(parts[2])
        if parts[3]:
            bucket["forms"].add(parts[3])
        if parts[6]:
            bucket["ifra"].add(parts[6])
        if parts[7]:
            bucket["notes"].add(parts[7])
        if parts[8]:
            bucket["dates"].add(parts[8])
        if parts[9]:
            bucket["quantities"].add(parts[9])
        quantity_upper = parts[9].upper()
        if "RAN OUT" in quantity_upper:
            bucket["status_flags"].add("ran_out")
        elif "DON'T HAVE" in quantity_upper or "DONT HAVE" in quantity_upper:
            bucket["status_flags"].add("not_owned")
        else:
            bucket["status_flags"].add("historical_owned")
    normalized: dict[str, dict[str, Any]] = {}
    for key, data in results.items():
        normalized[key] = {
            "names": sorted(data["names"]),
            "cas": sorted(data["cas"]),
            "forms": sorted(data["forms"]),
            "ifra": sorted(data["ifra"]),
            "notes": sorted(data["notes"]),
            "dates": sorted(data["dates"]),
            "quantities": sorted(data["quantities"]),
            "status_flags": sorted(data["status_flags"]),
        }
    return normalized


def _build_material_properties_index() -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for item in _load_json(MATERIAL_PROPERTIES_PATH) or []:
        if not isinstance(item, dict):
            continue
        for name in (item.get("name"), item.get("alt_name")):
            if name:
                index.setdefault(_identity_key(name), item)
                identity = resolve_material_identity(name)
                if identity is not None:
                    for extra in (identity.profile_name, identity.chemistry_name, identity.identity_key, *identity.aliases):
                        index.setdefault(_identity_key(extra), item)
    for material in _load_data_spine_materials():
        item = {
            "name": material.canonical_name,
            "alt_name": None,
            "cas": material.cas,
            "mw": material.mw_g_mol,
            "vp": material.vp_25c_pa,
            "clp": material.logp,
            "odt": material.odt_air_ppb,
            "stock_form": material.user_stock_dilution,
        }
        for name in (material.canonical_name, *(material.aliases or [])):
            index.setdefault(_identity_key(name), item)
    return index


def _build_pairing_index() -> dict[str, dict[str, list[str]]]:
    index: dict[str, dict[str, list[str]]] = defaultdict(lambda: {"synergy": [], "conflict": []})
    for item in _load_json(PAIRING_RULES_PATH) or []:
        if not isinstance(item, dict):
            continue
        a = item.get("material_a")
        b = item.get("material_b")
        if not a or not b:
            continue
        key = _identity_key(a)
        bucket = index[key]
        if str(item.get("type") or "synergy").lower().strip() == "conflict":
            bucket["conflict"].append(str(b).strip())
        else:
            bucket["synergy"].append(str(b).strip())
    for value in index.values():
        value["synergy"] = _dedupe_keep_order(value["synergy"])
        value["conflict"] = _dedupe_keep_order(value["conflict"])
    return dict(index)


def _load_data_spine_materials() -> list[Any]:
    try:
        from engine.data_spine.loader import load_registry
    except Exception:
        return []
    try:
        return list(load_registry().all())
    except Exception:
        return []


def _load_expensive_material_substitutes() -> dict[str, dict[str, Any]]:
    try:
        from engine.validator import EXPENSIVE_MATERIALS
    except Exception:
        return {}
    return {_identity_key(name): data for name, data in EXPENSIVE_MATERIALS.items()}


def _inventory_records() -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for record in parse_inventory(unique=True, include_solvents=True, include_unavailable=True):
        output.append(
            {
                "name": record.name,
                "raw_name": record.raw_name,
                "category": record.category,
                "status": record.status,
            }
        )
    return output


def _choose_display_name(entry: dict[str, Any]) -> str:
    def clean(name: str) -> str:
        stripped = re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()
        return stripped or name
    for source in ("inventory", "history", "shopping", "spine"):
        names = entry["source_names"].get(source) or []
        if names:
            return clean(names[0])
    aliases = entry.get("aliases") or []
    if aliases:
        return clean(aliases[0])
    return entry["identity_key"].title()


def _infer_category(entry: dict[str, Any]) -> str:
    if entry.get("category"):
        return entry["category"]
    name = entry["identity_key"]
    if any(token in name for token in ("ionone", "irone", "orris", "orivone", "iris", "violet")):
        return "IRIS / VIOLET"
    if any(
        token in name
        for token in (
            "hedione",
            "jasm",
            "ylang",
            "anthranilate",
            "aurantiol",
            "salicylate",
            "methyl benzoate",
            "p cresyl methyl ether",
            "orange blossom",
            "neroli",
        )
    ):
        return "FLORAL MATERIALS"
    if any(token in name for token in ("musk", "habanolide", "galaxolide", "romandolide", "zenolide", "ambrettolide", "brassylate", "tonalide", "macrolide")):
        return "MUSKS"
    if any(token in name for token in ("amber", "cedar", "sandal", "vetiv", "wood", "ambrox", "norlimbanol", "iso e", "kephalis")):
        return "WOODS / AMBER / STRUCTURE"
    if any(token in name for token in ("rose", "jasmine", "ylang", "lily", "floral", "muguet", "orange blossom", "neroli", "phenethyl", "citronellol", "geraniol")):
        return "FLORAL MATERIALS"
    if any(token in name for token in ("citrus", "bergamot", "grapefruit", "orange", "mandarin", "lemon", "cedrat", "pamplemousse", "petitgrain")):
        return "CITRUS / TOP"
    if any(token in name for token in ("green", "marine", "ozone", "ozonic", "floralozone", "calone", "scentenal", "hexenol", "verdox", "helional", "cyclamen")):
        return "GREEN / FRESH / MARINE"
    if any(token in name for token in ("vanillin", "maltol", "benzoin", "coumarin", "gourmand", "tonka", "heliotropin")):
        return "SWEET / GOURMAND / BALSAMIC"
    if any(token in name for token in ("leather", "birch", "tar", "smok", "phenol", "quinoline", "suederal", "cade")):
        return "LEATHER / SMOKY / PHENOLIC"
    if any(token in name for token in ("cardamom", "pepper", "ginger", "saff", "eugenol", "cinnam", "anis", "clary", "lavender")):
        return "SPICE / AROMATIC"
    if any(token in name for token in ("f tec", "ftec", "fleuressence", "concentrate", "base", "accord")):
        return "ACCORD BASES / FTECs / OTHER"
    return "UNKNOWN"


def _pick_status(flags: set[str]) -> str:
    if "owned" in flags:
        return "owned"
    if "out_of_stock" in flags:
        return "out_of_stock"
    if "ran_out" in flags:
        return "ran_out"
    if "buy_list" in flags:
        return "buy_list"
    if "not_owned" in flags:
        return "not_owned"
    if "historical_owned" in flags:
        return "historical_owned"
    return "reference_only"


def _category_context(category: str) -> dict[str, Any]:
    return _CATEGORY_CONTEXTS.get(category.lower(), _CATEGORY_CONTEXTS["unknown"])


def _properties_from_sources(
    display_name: str,
    aliases: list[str],
    prop_record: dict[str, Any] | None,
    spine_material: Any | None = None,
) -> dict[str, Any]:
    ground_truth = _ground_truth_identity(display_name, *aliases)
    profile = None
    for candidate in [display_name, *aliases]:
        profile = get_profile(candidate)
        if profile is not None:
            break
    if not _prop_record_matches_ground_truth(prop_record, ground_truth):
        prop_record = None
    properties: dict[str, Any] = {
        "cas": None,
        "chemistry_name": None,
        "profile_name": None,
        "mw": None,
        "vp": None,
        "clogp": None,
        "odt": None,
        "note": None,
        "role": None,
        "texture": None,
        "dominant_character": None,
        "character_tags": [],
        "arctander_character": None,
        "carles_position": None,
        "typical_pct_range": None,
        "stock_form": None,
        "handle_as": None,
    }
    if prop_record:
        properties["cas"] = prop_record.get("cas")
        properties["mw"] = prop_record.get("mw")
        properties["vp"] = prop_record.get("vp")
        properties["clogp"] = prop_record.get("clp")
        properties["odt"] = prop_record.get("odt")
        properties["arctander_character"] = prop_record.get("arctander_character")
        properties["carles_position"] = prop_record.get("carles_position")
        properties["typical_pct_range"] = prop_record.get("typical_pct_range")
        properties["stock_form"] = prop_record.get("stock_form")
        properties["handle_as"] = prop_record.get("handle_as")
    if spine_material is not None:
        properties["cas"] = properties["cas"] or getattr(spine_material, "cas", None)
        properties["mw"] = properties["mw"] or getattr(spine_material, "mw_g_mol", None)
        properties["vp"] = properties["vp"] or getattr(spine_material, "vp_25c_pa", None)
        properties["clogp"] = properties["clogp"] or getattr(spine_material, "logp", None)
        properties["odt"] = properties["odt"] or getattr(spine_material, "odt_air_ppb", None)
        properties["stock_form"] = properties["stock_form"] or getattr(spine_material, "user_stock_dilution", None)
    if profile is not None:
        properties["mw"] = properties["mw"] or profile.mw
        properties["vp"] = properties["vp"] or profile.vp
        properties["clogp"] = properties["clogp"] or profile.clogp
        properties["odt"] = properties["odt"] or profile.odt
        properties["note"] = profile.note
        properties["role"] = profile.role
        properties["texture"] = profile.texture
        properties["character_evidence_status"] = profile.character_status.value
        properties["character_description"] = profile.character_description
        if profile.numeric_character is not None:
            properties["dominant_character"] = profile.dominant_character()
            properties["character_tags"] = profile.character_tags()
        else:
            properties["dominant_character"] = None
            properties["character_tags"] = None
    if ground_truth:
        properties["cas"] = ground_truth.get("cas") or properties["cas"]
        properties["chemistry_name"] = ground_truth.get("chemistry_name")
        properties["profile_name"] = ground_truth.get("profile_name")
    return properties


def _best_with(prop_record: dict[str, Any] | None, display_name: str) -> list[str]:
    results: list[str] = []
    if prop_record and prop_record.get("best_with"):
        results.extend(str(item) for item in prop_record.get("best_with") or [])
    profile = get_profile(display_name)
    if profile is not None:
        results.extend(profile.synergies)
    return _dedupe_keep_order(results)


def _avoid_list(prop_record: dict[str, Any] | None, display_name: str) -> list[str]:
    results: list[str] = []
    if prop_record and prop_record.get("avoid"):
        avoid = prop_record["avoid"]
        if isinstance(avoid, list):
            results.extend(str(item) for item in avoid)
        else:
            results.append(str(avoid))
    profile = get_profile(display_name)
    if profile is not None:
        results.extend(profile.avoid)
    return _dedupe_keep_order(results)


def _dose_guidance(properties: dict[str, Any], observed_forms: list[str]) -> str:
    if properties.get("typical_pct_range"):
        return str(properties["typical_pct_range"])
    if observed_forms:
        return f"Use from observed stock/form: {observed_forms[0]}"
    return "Test in micro-batches first and scale by odor impact."


def _common_uses(properties: dict[str, Any], category: str) -> list[str]:
    context = _category_context(category)
    results = list(context["common"])
    dominant = properties.get("dominant_character")
    handle_as = properties.get("handle_as")
    if dominant:
        results.append(f"Push the formula toward a more {dominant} profile without fully changing its family.")
    if handle_as:
        results.append(str(handle_as))
    return _dedupe_keep_order(results)[:4]


def _niche_uses(properties: dict[str, Any], category: str) -> list[str]:
    context = _category_context(category)
    results = list(context["niche"])
    tags = properties.get("character_tags") or []
    if len(tags) >= 2:
        results.append(f"Useful when you want a {tags[0]} + {tags[1]} signature effect rather than a generic support material.")
    return _dedupe_keep_order(results)[:3]


def _implementation_examples(
    properties: dict[str, Any],
    category: str,
    best_with: list[str],
    observed_forms: list[str],
) -> list[dict[str, Any]]:
    context = _category_context(category)
    dose = _dose_guidance(properties, observed_forms)
    pairings = best_with[:4]
    output: list[dict[str, Any]] = []
    for name, style, use in context["implementations"]:
        output.append(
            {
                "name": name,
                "style": style,
                "use": use,
                "dose_guidance": dose,
                "pair_with": pairings,
            }
        )
    return output[:3]


def _replacement_options(display_name: str, aliases: list[str]) -> list[str]:
    expensive = _load_expensive_material_substitutes()
    identity = _identity_key(display_name)
    if identity in expensive:
        data = expensive[identity]
        return _dedupe_keep_order([*data.get("substitutes_owned", []), *data.get("substitutes_new", [])])[:6]
    for candidate in [display_name, *aliases]:
        try:
            similar = [name for name, _distance in find_similar(candidate, n=4)]
        except Exception:
            similar = []
        if similar:
            return _dedupe_keep_order(similar)[:4]
    return []


def _pairing_note(best_with: list[str], avoid: list[str], pairings: dict[str, list[str]]) -> str:
    notes: list[str] = []
    if best_with:
        notes.append(f"Works especially well with {', '.join(best_with[:4])}.")
    if pairings.get("synergy"):
        notes.append(f"Recorded local synergies include {', '.join(pairings['synergy'][:4])}.")
    if avoid:
        notes.append(f"Watch out for {', '.join(avoid[:3])}.")
    if pairings.get("conflict"):
        notes.append(f"Local conflict rules flag {', '.join(pairings['conflict'][:3])}.")
    return " ".join(notes)


def build_ingredient_catalog() -> list[dict[str, Any]]:
    shopping = _parse_shopping_list()
    history = _parse_chemical_inventory()
    properties_index = _build_material_properties_index()
    pairing_index = _build_pairing_index()
    inventory = _inventory_records()
    spine_materials = _load_data_spine_materials()
    entries: dict[str, dict[str, Any]] = {}

    def ensure(key: str) -> dict[str, Any]:
        return entries.setdefault(
            key,
            {
                "identity_key": key,
                "aliases": [],
                "category": "",
                "status_flags": set(),
                "source_names": {"inventory": [], "history": [], "shopping": [], "spine": []},
                "observed_forms": [],
                "historical_forms": [],
                "notes": [],
                "ifra_status": [],
                "dates": [],
                "quantities": [],
                "buy_list_sections": [],
                "buy_list_priority": [],
                "source_files": set(),
            },
        )

    for record in inventory:
        key = _identity_key(record["name"])
        entry = ensure(key)
        entry["category"] = entry["category"] or record["category"]
        entry["status_flags"].add(record["status"])
        entry["source_names"]["inventory"].append(record["name"])
        entry["aliases"].extend([record["name"], record["raw_name"]])
        entry["observed_forms"].append(record["raw_name"])
        entry["source_files"].add("inventory.txt")

    for key, record in history.items():
        entry = ensure(key)
        entry["status_flags"].update(record["status_flags"])
        entry["source_names"]["history"].extend(record["names"])
        entry["aliases"].extend(record["names"])
        entry["historical_forms"].extend(record["forms"])
        entry["notes"].extend(record["notes"])
        entry["ifra_status"].extend(record["ifra"])
        entry["dates"].extend(record["dates"])
        entry["quantities"].extend(record["quantities"])
        entry["source_files"].add("knowledge/chemical_inventory.md")

    for key, record in shopping.items():
        entry = ensure(key)
        entry["status_flags"].add("buy_list")
        entry["source_names"]["shopping"].extend(record["names"])
        entry["aliases"].extend(record["names"])
        entry["buy_list_sections"].extend(record["sections"])
        entry["buy_list_priority"].extend(record["priority"])
        entry["source_files"].add("shopping_list.md")

    spine_index: dict[str, Any] = {}
    for material in spine_materials:
        key = _identity_key(getattr(material, "canonical_name", ""))
        if not key:
            continue
        spine_index[key] = material
        entry = ensure(key)
        entry["source_names"]["spine"].append(material.canonical_name)
        entry["aliases"].extend([material.canonical_name, *(material.aliases or [])])
        if material.user_stock_dilution:
            entry["observed_forms"].append(material.user_stock_dilution)
        if material.character:
            entry["notes"].append(material.character)
        if material.notes:
            entry["notes"].append(material.notes)
        if material.ifra_max_pct_edp is not None:
            entry["ifra_status"].append(f"IFRA fine fragrance max {material.ifra_max_pct_edp}%")
        entry["source_files"].add("data/materials")

    catalog: list[dict[str, Any]] = []
    for key, entry in entries.items():
        aliases = _dedupe_keep_order(entry["aliases"])
        display_name = _choose_display_name({**entry, "aliases": aliases})
        ground_truth = _ground_truth_identity(display_name, *aliases)
        if ground_truth is not None:
            aliases = _dedupe_keep_order(
                [
                    *aliases,
                    ground_truth["label"],
                    ground_truth["chemistry_name"],
                    ground_truth["profile_name"],
                    *ground_truth.get("aliases", []),
                ]
            )
        category = _infer_category({**entry, "identity_key": key})
        prop_record = properties_index.get(key)
        if prop_record is None:
            for alias in aliases:
                prop_record = properties_index.get(_identity_key(alias))
                if prop_record is not None:
                    break
        spine_material = spine_index.get(key)
        if spine_material is None:
            for alias in aliases:
                spine_material = spine_index.get(_identity_key(alias))
                if spine_material is not None:
                    break
        if not _prop_record_matches_ground_truth(prop_record, ground_truth):
            prop_record = None
        properties = _properties_from_sources(display_name, aliases, prop_record, spine_material)
        best_with = _best_with(prop_record, display_name)
        avoid = _avoid_list(prop_record, display_name)
        pairings = deepcopy(pairing_index.get(key, {"synergy": [], "conflict": []}))
        bottle_labels = _dedupe_keep_order(
            [
                *entry["source_names"].get("inventory", []),
                *entry["source_names"].get("history", []),
                *entry["source_names"].get("shopping", []),
            ]
        )
        catalog.append(
            {
                "name": display_name,
                "identity_key": key,
                "bottle_labels": bottle_labels,
                "aliases": aliases,
                "ground_truth_identity": ground_truth,
                "category": category,
                "current_status": _pick_status(set(entry["status_flags"])),
                "owned_now": "owned" in entry["status_flags"],
                "was_owned": bool({"owned", "out_of_stock", "ran_out", "historical_owned"} & set(entry["status_flags"])),
                "on_buy_list": "buy_list" in entry["status_flags"],
                "status_flags": sorted(entry["status_flags"]),
                "observed_forms": _dedupe_keep_order(entry["observed_forms"] + entry["historical_forms"]),
                "notes": _dedupe_keep_order(entry["notes"]),
                "ifra_status": _dedupe_keep_order(entry["ifra_status"]),
                "dates_seen": _dedupe_keep_order(entry["dates"]),
                "quantities_seen": _dedupe_keep_order(entry["quantities"]),
                "buy_list_sections": _dedupe_keep_order(entry["buy_list_sections"]),
                "buy_list_priority": _dedupe_keep_order(entry["buy_list_priority"]),
                "properties": properties,
                "best_with": best_with[:8],
                "avoid": avoid[:6],
                "pairing_rules": {
                    "synergy": _dedupe_keep_order(pairings.get("synergy", []))[:8],
                    "conflict": _dedupe_keep_order(pairings.get("conflict", []))[:6],
                },
                "common_uses": _common_uses(properties, category),
                "niche_uses": _niche_uses(properties, category),
                "implementation_examples": _implementation_examples(properties, category, best_with, entry["observed_forms"] + entry["historical_forms"]),
                "best_in": _category_context(category)["best_in"],
                "avoid_in": _category_context(category)["avoid_in"],
                "replacement_options": _replacement_options(display_name, aliases),
                "pairing_note": _pairing_note(best_with, avoid, pairings),
                "source_files": sorted(entry["source_files"]),
            }
        )
    catalog.sort(key=lambda item: (item["current_status"] != "owned", item["category"], item["name"].lower()))
    return catalog


def write_ingredient_catalog(path: Path | None = None) -> Path:
    target = path or DEFAULT_OUTPUT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    catalog = build_ingredient_catalog()
    payload = {
        "_meta": {
            "description": "Merged ingredient universe from live inventory, historical inventory, and buy list.",
            "generated_from": [
                "inventory.txt",
                "knowledge/chemical_inventory.md",
                "shopping_list.md",
                "data/knowledge_graph/material_properties.json",
                "data/knowledge_graph/pairing_rules.json",
                "engine/ingredient_intelligence.py",
                "engine/validator.py",
            ],
            "entry_count": len(catalog),
        },
        "ingredients": catalog,
    }
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return target


_CATALOG_CACHE: list[dict[str, Any]] | None = None
_CATALOG_CACHE_PATH: Path | None = None


def load_ingredient_catalog(path: Path | None = None, *, refresh: bool = False) -> list[dict[str, Any]]:
    global _CATALOG_CACHE, _CATALOG_CACHE_PATH
    target = path or DEFAULT_OUTPUT_PATH
    if refresh or not target.exists():
        try:
            write_ingredient_catalog(target)
            # Invalidate cache on refresh/rebuild
            _CATALOG_CACHE = None
        except PermissionError:
            result = build_ingredient_catalog()
            _CATALOG_CACHE = result
            _CATALOG_CACHE_PATH = target
            return result
    if _CATALOG_CACHE is not None and _CATALOG_CACHE_PATH == target:
        return _CATALOG_CACHE
    payload = _load_json(target) or {}
    result = list(payload.get("ingredients", []))
    _CATALOG_CACHE = result
    _CATALOG_CACHE_PATH = target
    return result


_INDEX_CACHE: dict[str, dict[str, Any]] | None = None
_INDEX_CACHE_PATH: Path | None = None


def load_ingredient_catalog_index(path: Path | None = None, *, refresh: bool = False) -> dict[str, dict[str, Any]]:
    global _INDEX_CACHE, _INDEX_CACHE_PATH
    target = path or DEFAULT_OUTPUT_PATH
    if _INDEX_CACHE is not None and _INDEX_CACHE_PATH == target and not refresh:
        return _INDEX_CACHE
    index: dict[str, dict[str, Any]] = {}
    for item in load_ingredient_catalog(path, refresh=refresh):
        ground_truth = item.get("ground_truth_identity") or {}
        canonical_name = ground_truth.get("label") or ground_truth.get("chemistry_name") or item["name"]
        material_record = {
            "name": canonical_name,
            "alt_name": item["name"],
            "best_with": item.get("best_with", []),
            "avoid": item.get("avoid", []),
            "mw": item.get("properties", {}).get("mw"),
            "vp": item.get("properties", {}).get("vp"),
            "clp": item.get("properties", {}).get("clogp"),
            "odt": item.get("properties", {}).get("odt"),
            "carles_position": item.get("properties", {}).get("carles_position"),
            "source": "ingredient_catalog",
        }
        index[item["identity_key"]] = {"catalog": item, "material": material_record}
        for alias in item.get("aliases", []):
            index.setdefault(_identity_key(alias), {"catalog": item, "material": material_record})
        if ground_truth.get("chemistry_name"):
            index[_identity_key(ground_truth["chemistry_name"])] = {"catalog": item, "material": material_record}
    _INDEX_CACHE = index
    _INDEX_CACHE_PATH = target
    return index


def find_ingredient(name: str, *, refresh: bool = False) -> dict[str, Any] | None:
    return load_ingredient_catalog_index(refresh=refresh).get(_identity_key(name), {}).get("catalog")
