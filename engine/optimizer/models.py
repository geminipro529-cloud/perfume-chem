"""Data models for the formula optimizer."""

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

KG_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "knowledge_graph"
DB_PATH = Path(__file__).resolve().parent.parent.parent / "perfume_chem.db"


def _load_json(name: str) -> list | dict:
    path = KG_DIR / name
    if not path.exists():
        return [] if name != "theory_rules.json" else {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


_QUALIFIER_TOKENS = {
    "absolute", "base", "bourbon", "eo", "essential", "fcf", "fo",
    "haitian", "laotian", "nagarmotha", "oil", "plantation", "pure",
    "reconstitution", "resinoid", "sicilian", "super", "synthetic",
}
_TOKEN_NORMALIZERS = {
    "cedarwood": "cedar",
}


def _core_material_phrase(name: str) -> str:
    tokens = re.findall(r"[a-z0-9]+", name.lower())
    if not tokens:
        return ""
    filtered = [
        _TOKEN_NORMALIZERS.get(token, token)
        for token in tokens
        if token not in _QUALIFIER_TOKENS
    ]
    if not filtered:
        filtered = [_TOKEN_NORMALIZERS.get(tokens[0], tokens[0])]
    return " ".join(filtered).strip()


def _is_generic_label(name: str) -> bool:
    """Return True for broad category labels that should not fuzzy-resolve."""
    return _core_material_phrase(name) in _GENERIC_LABELS


def _material_alias_keys(name: str) -> tuple[str, ...]:
    """Generate conservative alias keys in explicit resolution priority order."""
    greek_map = str.maketrans({
        "α": "a",
        "β": "b",
        "γ": "g",
        "δ": "d",
        "’": "'",
    })
    low = name.lower().translate(greek_map)
    low = low.replace("**", "")
    low = re.sub(r"\s+", " ", low.strip())
    variants: list[str] = []
    seen: set[str] = set()

    def add_variant(value: str) -> None:
        normalized = value.strip()
        if not normalized or normalized in seen:
            return
        if len(normalized) < 3 and normalized not in _LOOKUP_ALIASES:
            return
        seen.add(normalized)
        variants.append(normalized)

    # Exact normalized spelling is authoritative. Progressively broader aliases
    # follow in deterministic order; none may outrank the exact key.
    add_variant(low)
    stripped_parens = re.sub(r"\s*\([^)]*\)\s*$", "", low).strip()
    add_variant(stripped_parens)

    if "(" in low and ")" not in low:
        add_variant(low.split("(", 1)[0])
    if "=" in low:
        add_variant(low.split("=", 1)[0])

    no_codes = re.sub(r"\bf\d{4}\b", "", low).strip()
    add_variant(no_codes)
    add_variant(no_codes.replace(" f-tec", " ftec"))
    add_variant(no_codes.replace(" ftec", " f-tec"))
    add_variant(no_codes.replace(" eo", ""))
    add_variant(no_codes.replace(" essential oil", ""))
    add_variant(no_codes.replace(" oil ", " "))
    add_variant(no_codes.replace(" oil", ""))
    add_variant(no_codes.replace("  ", " "))
    core_phrase = _core_material_phrase(no_codes)
    if core_phrase:
        add_variant(core_phrase)

    return tuple(variants)


def _profile_material_dict(profile) -> dict:
    """Build a minimal KG-like record from ingredient intelligence."""
    carles_position = {
        "top": "TOP — ingredient intelligence fallback",
        "heart": "HEART — ingredient intelligence fallback",
        "base": "BASE — ingredient intelligence fallback",
    }.get(profile.note, "HEART — ingredient intelligence fallback")
    return {
        "name": profile.name,
        "mw": profile.mw,
        "vp": profile.vp,
        "clp": profile.clogp,
        "odt": profile.odt,
        "carles_position": carles_position,
        "source": "ingredient_intelligence_fallback",
    }


def _retain_exact_synthetic_metadata(material: dict, primary: dict[str, dict]) -> dict:
    """Retain absent KG fields without overriding catalogue values or nulls.

    Exact names and molecular-formula-shaped legacy records are required. This
    preserves existing metadata, not identity, numeric, or sensory authority.
    """
    key = str(material.get("name") or "").lower().strip()
    donor = primary.get(key)
    if donor is None:
        return material
    kind = str(donor.get("material_kind") or "").upper()
    formula = unicodedata.normalize("NFKC", str(donor.get("formula_str") or ""))
    if (
        any(token in kind for token in ("MIXTURE", "OPAQUE", "BLEND"))
        or re.search(
            r"\b(?:eo|oil|absolute|resinoid|extract|tincture|base|accord|fo|ftec|f-tec|fleuressence)\b",
            key,
        )
        or formula.casefold() == "unknown"
        or re.fullmatch(r"(?:[A-Z][a-z]?\d*)+", formula) is None
    ):
        return material
    retained = {
        field: donor[field]
        for field in (
            "bp", "sar_class", "odor_family", "roudnitska_function", "jellinek_quadrant"
        )
        if field not in material and donor.get(field) is not None
    }
    if not retained:
        return material
    return {
        **retained,
        **material,
        "supplemental_field_sources": {
            field: "optimizer_primary_material_index:exact_name" for field in retained
        },
    }


def _supplement_material_index(db: dict) -> dict:
    """Add alias keys and profile-backed fallback records to the material index."""
    from ..ingredient_intelligence import _ALIASES as PROFILE_ALIASES
    from ..ingredient_intelligence import get_all_profiles
    from ..material_identity import resolve_material_identity
    try:
        from ..ingredient_catalog import load_ingredient_catalog_index
    except Exception:  # pragma: no cover - keep optimizer resilient
        load_ingredient_catalog_index = None  # type: ignore[assignment]

    seen_materials: dict[str, dict] = {}
    for value in list(db.values()):
        seen_materials[value.get("name", "").lower().strip()] = value

    # Add profile-backed fallback records for known materials that the KG/DB lacks.
    for profile_name, profile in get_all_profiles().items():
        key = profile_name.lower().strip()
        if key not in seen_materials:
            db[key] = _profile_material_dict(profile)
            seen_materials[key] = db[key]

    # Add conservative variant keys for all indexed materials.
    for material in list(seen_materials.values()):
        for key_name in (material.get("name"), material.get("alt_name")):
            if not key_name:
                continue
            for variant in _material_alias_keys(key_name):
                db.setdefault(variant, material)

    # Reuse ingredient intelligence aliases inside the KG lookup layer.
    for alias, canonical in PROFILE_ALIASES.items():
        canonical_material = db.get(canonical.lower().strip())
        if canonical_material is not None:
            db[alias.lower().strip()] = canonical_material

    # Explicit shorthand aliases used across the markdown formulas/rules.
    for alias, canonical in _LOOKUP_ALIASES.items():
        canonical_material = db.get(canonical.lower().strip())
        if canonical_material is not None:
            db[alias.lower().strip()] = canonical_material

    if load_ingredient_catalog_index is not None:
        try:
            catalog_index = load_ingredient_catalog_index()
        except Exception:
            catalog_index = {}
        for key, payload in catalog_index.items():
            material = payload.get("material")
            catalog = payload.get("catalog")
            if not isinstance(material, dict) or not isinstance(catalog, dict):
                continue
            material = _retain_exact_synthetic_metadata(material, seen_materials)
            canonical_key = catalog.get("identity_key")
            if isinstance(canonical_key, str) and canonical_key:
                db[canonical_key] = material
            db[key] = material
            for alias in catalog.get("aliases", []):
                if isinstance(alias, str) and alias.strip():
                    db[alias.lower().strip()] = material
            ground_truth = catalog.get("ground_truth_identity") or {}
            for candidate in (
                ground_truth.get("label"),
                ground_truth.get("profile_name"),
                ground_truth.get("chemistry_name"),
                *ground_truth.get("aliases", []),
            ):
                if isinstance(candidate, str) and candidate.strip():
                    db[candidate.lower().strip()] = material

    for value in list(db.values()):
        for candidate in (value.get("name"), value.get("alt_name")):
            identity = resolve_material_identity(candidate)
            if identity is None:
                continue
            for extra in (
                identity.identity_key,
                identity.profile_name,
                identity.chemistry_name,
                identity.label,
                *identity.aliases,
            ):
                db[extra.lower().strip()] = value

    return db


def _load_materials_from_db() -> dict:
    """Load materials from SQLite (synchronous for engine compatibility)."""
    import sqlite3
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM materials").fetchall()
        db: dict = {}
        for row in rows:
            m = dict(row)
            # Parse best_with from JSON string
            bw = m.get("best_with")
            if isinstance(bw, str):
                try:
                    m["best_with"] = json.loads(bw)
                except (json.JSONDecodeError, TypeError):
                    pass
            key = m["name"].lower().strip()
            db[key] = m
            if m.get("alt_name"):
                db[m["alt_name"].lower().strip()] = m
        return db
    finally:
        conn.close()


def _load_pairing_rules_from_db() -> list:
    import sqlite3
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM pairing_rules").fetchall()
        raw_rules = [
            {
                "material_a": r["material_a_name"],
                "material_b": r["material_b_name"],
                "effect": r["effect"],
                "type": r["rule_type"].lower(),
                "source": r["source"],
            }
            for r in rows
        ]
        return _normalize_loaded_rules(raw_rules)
    finally:
        conn.close()


def _load_synergy_rules_from_db() -> list:
    import sqlite3
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM synergy_rules WHERE is_corrupted = 0"
        ).fetchall()
        raw_rules = [
            {
                "material_a": r["material_a_name"],
                "material_b": r["material_b_name"],
                "effect": r["effect"],
                "ratio": r["ratio"],
                "type": r["rule_type"].lower(),
                "source": r["source"],
            }
            for r in rows
        ]
        return _normalize_loaded_rules(raw_rules)
    finally:
        conn.close()


def _load_theory_from_db() -> dict:
    import sqlite3
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM theory_frameworks").fetchall()
        result = {}
        for r in rows:
            rules = r["rules_json"]
            if isinstance(rules, str):
                try:
                    rules = json.loads(rules)
                except (json.JSONDecodeError, TypeError):
                    rules = {}
            result[r["name"]] = rules
        return result
    finally:
        conn.close()


def _use_db() -> bool:
    """Check if the SQLite database exists and has data."""
    if not DB_PATH.exists():
        return False
    try:
        import sqlite3
        conn = sqlite3.connect(str(DB_PATH))
        count = conn.execute("SELECT COUNT(*) FROM materials").fetchone()[0]
        conn.close()
        return count > 0
    except Exception:
        return False


_CORRUPTED_RULE_RE = re.compile(r"\.md|\.txt|_and_", re.IGNORECASE)
_RULE_HEADER_VALUES = {"goal", "amplifier", "target", "ratio", "material", "materials"}
_RULE_ABSTRACT_TERMS = {
    "aldehydes",
    "alkaline water",
    "all other musks",
    "amine",
    "amines",
    "animalic",
    "aquatic_base",
    "base",
    "cassis",
    "clean duo",
    "clean_base",
    "crystalline solids",
    "citrus",
    "dark florals",
    "depth",
    "duo",
    "earth duo",
    "ensemble player",
    "ester",
    "everything",
    "everything. musks",
    "everything — bergamot",
    "everything — invisible additive",
    "everything — the universal citrus top",
    "everything — universal enhancer",
    "fe³⁺",
    "first partner",
    "florals",
    "floral bouquets",
    "floral heart notes",
    "fresh notes",
    "fresh_green",
    "fruit amplifier",
    "fruity notes",
    "frankincense",
    "green notes",
    "heavy musks",
    "heavy_oriental_base",
    "invisible additive",
    "iris",
    "iris bridge",
    "iris materials",
    "leather notes",
    "luxury top",
    "lychee trick",
    "marine",
    "modern wood",
    "moisture",
    "musks",
    "oakmoss",
    "oxygen",
    "oxygen+light",
    "other ambers",
    "other ionones",
    "other musks",
    "other woods",
    "pear notes",
    "pepper",
    "phenol",
    "powder accords",
    "powdery accords",
    "radiance",
    "radiance duo",
    "resinous_base",
    "rose duo",
    "rose materials",
    "rum notes",
    "sacred",
    "soften",
    "spices",
    "spices — it improves all.",
    "structure",
    "tobacco",
    "transparency",
    "use as a carrier when dpg or ipm aren't suitable",
    "vanilla",
    "virtually everything",
    "volume",
    "woods",
}
_RULE_ABSTRACT_FRAGMENTS = (
    " accord",
    " accords",
    " notes",
    " materials",
    " bouquets",
    " enhancer",
    " invisible additive",
    " universal ",
)
_LOOKUP_ALIASES = {
    "ambroxide": "ambrox super",
    "ambrofix": "ambrox super",
    "methyl dihydrojasmonate": "hedione",
    "eb": "ethylene brassylate",
    "dhm": "dihydromyrcenol",
    "ambroxan": "ambrox super",
    "aimi": "alpha isomethyl ionone",
    "methyl ionone pure": "alpha isomethyl ionone",
    "alpha isomethyl ionone": "alpha isomethyl ionone",
    "alpha-isomethyl ionone": "alpha isomethyl ionone",
    "allyl ionone cetone v": "allyl ionone",
    "allyl ionone ketone v": "allyl ionone",
    "cetone v": "allyl ionone",
    "ketone v": "allyl ionone",
    "orris hexanone": "orivone",
    "orris capronate": "irotyl",
    "limonene": "d-limonene",
    "tonka": "tonka bean fo",
}
_GENERIC_LABELS = {
    "aldehydes", "animalic", "amber", "bergamot", "cassis", "citrus",
    "florals", "fresh notes", "green notes", "iris", "jasmine", "marine",
    "musks", "oakmoss", "other ambers", "other ionones", "other musks",
    "other woods", "pepper", "pear notes", "phenol", "rose", "spices",
    "tobacco", "vanilla", "vetiver", "woods",
}
_ROUDNITSKA_ROLE_KEYWORDS = {
    "transparence": ("transparenc", "proprete", "clean", "airy", "sheer", "light"),
    "chaleur": ("chaleur", "warmth", "warm", "volume", "body", "envelop"),
    "noblesse": ("noblesse", "noble", "precious", "rare", "refin"),
    "peau": ("peau", "skin", "douceur", "soft", "musk", "intimate"),
    "eclat": ("eclat", "rayonnement", "radianc", "sparkle", "bright", "ouverture"),
    "profondeur": ("profondeur", "depth", "deep", "fixat", "foundation", "anchor"),
}
_JELLINEK_QUADRANT_KEYWORDS = {
    "upper_left": ("upper-left", "upper left", "fresh-stimulating", "fresh stimulating", "intellectual"),
    "upper_right": ("upper-right", "upper right", "warm-stimulating", "warm stimulating", "aggressive"),
    "lower_right": ("lower-right", "lower right", "warm-narcotic", "warm narcotic", "erogenic"),
    "lower_left": ("lower-left", "lower left", "cool-narcotic", "cool narcotic"),
}


def _normalize_theory_text(text: str | None) -> str:
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", str(text))
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower()
    normalized = normalized.replace("—", "-").replace("–", "-").replace("−", "-")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _normalize_rule_type(rule: dict) -> str:
    raw_type = (rule.get("type") or "").lower().strip()
    material_b = (rule.get("material_b") or "").lower().strip()
    source = (rule.get("source") or "").lower()

    if material_b.startswith("__avoid__") or "/avoid" in source:
        return "conflict"
    if material_b.startswith("__carles_rule__"):
        return "neutral"
    return raw_type or "synergy"


def _expand_rule_material_refs(name: str) -> list[str]:
    """Expand labels with explicit examples into concrete material names."""
    clean = re.sub(r"\s+", " ", name).strip().replace("**", "")
    clean = clean.strip(" -:;,.")
    if "=" in clean:
        clean = clean.split("=", 1)[0].strip()
    if "(" in clean and ")" not in clean:
        clean = clean.split("(", 1)[0].strip()
    if ")" in clean and "(" not in clean:
        clean = clean.split(")", 1)[0].strip()
    if not clean:
        return []

    match = re.match(r"(.+?)\s*\(([^)]+)\)\s*$", clean)
    if not match:
        if "/" in clean:
            parts = [
                part.strip()
                for part in clean.split("/")
                if part.strip()
            ]
            kept = [part for part in parts if part and not _rule_ref_is_invalid(part)]
            if len(kept) >= 2:
                return kept
        return [clean]

    base = match.group(1).strip()
    if base and _lookup_material(base) is not None:
        return [base]

    examples = [
        part.strip()
        for part in re.split(r",|/|;", match.group(2))
        if part.strip()
    ]
    kept = [part for part in examples if part and not _rule_ref_is_invalid(part)]
    if kept:
        return kept
    return [base or clean]


def _rule_ref_is_invalid(name: str) -> bool:
    low = name.lower().strip()
    if not low:
        return True
    if low.count("(") != low.count(")"):
        return True
    if low.startswith("__"):
        return True
    if " + " in low:
        return True
    if "=" in low:
        base = low.split("=", 1)[0].strip()
        if not base or _lookup_material(base) is None:
            return True
    if re.match(r"^[\d:+\-x ]", low):
        return True
    if low in _RULE_HEADER_VALUES:
        return True
    if low in _RULE_ABSTRACT_TERMS:
        return True
    if any(fragment in low for fragment in _RULE_ABSTRACT_FRAGMENTS):
        base = re.sub(r"\s*\([^)]*\)\s*$", "", low).strip()
        if _lookup_material(base) is None:
            return True
    if _CORRUPTED_RULE_RE.search(low):
        return True
    if len(low) > 80:
        return True
    return False


def _normalize_loaded_rules(raw_rules: list[dict]) -> list[dict]:
    """Clean rule rows from DB/JSON before downstream use."""
    cleaned: list[dict] = []
    seen: set[tuple[str, str, str, str]] = set()

    for rule in raw_rules:
        material_a = re.sub(r"\s+", " ", str(rule.get("material_a") or "")).strip()
        material_b = re.sub(r"\s+", " ", str(rule.get("material_b") or "")).strip()
        if _rule_ref_is_invalid(material_a) or _rule_ref_is_invalid(material_b):
            continue

        rule_type = _normalize_rule_type(rule)
        for expanded_b in _expand_rule_material_refs(material_b):
            if _rule_ref_is_invalid(expanded_b):
                continue
            normalized = {
                "material_a": material_a,
                "material_b": expanded_b,
                "effect": str(rule.get("effect") or "").strip(),
                "type": rule_type,
                "source": str(rule.get("source") or "").strip(),
            }
            if "axis" in rule:
                normalized["axis"] = str(rule["axis"]).strip()
            if "magnitude" in rule:
                normalized["magnitude"] = float(rule["magnitude"])
            if "ratio" in rule:
                normalized["ratio"] = str(rule.get("ratio") or "").strip()
            key = (
                normalized["material_a"].lower(),
                normalized["material_b"].lower(),
                normalized["type"],
                normalized["effect"].lower(),
            )
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(normalized)

    return cleaned


# Lazy-loaded caches
_MATERIALS_BY_NAME: dict | None = None
_PAIRING_RULES: list | None = None
_SYNERGY_RULES: list | None = None
_THEORY_RULES: dict | None = None
_ACCORD_LIBRARY: list | None = None
_PAIRING_INDEX: dict | None = None
_SYNERGY_INDEX: dict | None = None


def invalidate_caches():
    """Clear all lazy-loaded caches so next access reloads from source."""
    global _MATERIALS_BY_NAME, _PAIRING_RULES, _SYNERGY_RULES, _THEORY_RULES
    global _ACCORD_LIBRARY, _PAIRING_INDEX, _SYNERGY_INDEX
    _MATERIALS_BY_NAME = None
    _PAIRING_RULES = None
    _SYNERGY_RULES = None
    _THEORY_RULES = None
    _ACCORD_LIBRARY = None
    _PAIRING_INDEX = None
    _SYNERGY_INDEX = None
    for fn_name in (
        "_lookup_material",
        "resolve_material_name",
        "classify_roudnitska_roles",
        "material_roudnitska_roles",
        "canonical_jellinek_quadrant_key",
        "material_jellinek_quadrant_key",
        "material_match_keys",
        "material_identity_key",
        "materials_match",
    ):
        fn = globals().get(fn_name)
        if fn is not None and hasattr(fn, "cache_clear"):
            fn.cache_clear()


def get_materials_db() -> dict:
    """Get materials indexed by normalized name. Uses SQLite if available, falls back to JSON."""
    global _MATERIALS_BY_NAME
    if _MATERIALS_BY_NAME is None:
        if _use_db():
            _MATERIALS_BY_NAME = _load_materials_from_db()
        else:
            raw = _load_json("material_properties.json")
            _MATERIALS_BY_NAME = {}
            for m in raw:
                key = m["name"].lower().strip()
                _MATERIALS_BY_NAME[key] = m
                if m.get("alt_name"):
                    _MATERIALS_BY_NAME[m["alt_name"].lower().strip()] = m
        _MATERIALS_BY_NAME = _supplement_material_index(_MATERIALS_BY_NAME)
    return _MATERIALS_BY_NAME


def get_pairing_rules() -> list:
    global _PAIRING_RULES
    if _PAIRING_RULES is None:
        if _use_db():
            _PAIRING_RULES = _load_pairing_rules_from_db()
        else:
            _PAIRING_RULES = _normalize_loaded_rules(_load_json("pairing_rules.json"))
    return _PAIRING_RULES


def get_synergy_rules() -> list:
    global _SYNERGY_RULES
    if _SYNERGY_RULES is None:
        if _use_db():
            _SYNERGY_RULES = _load_synergy_rules_from_db()
        else:
            _SYNERGY_RULES = _normalize_loaded_rules(_load_json("synergy_matrix.json"))
    return _SYNERGY_RULES


def get_theory_rules() -> dict:
    global _THEORY_RULES
    if _THEORY_RULES is None:
        if _use_db():
            _THEORY_RULES = _load_theory_from_db()
        else:
            _THEORY_RULES = _load_json("theory_rules.json")
    return _THEORY_RULES


def _parse_accord_library() -> list[dict]:
    """Parse perfume_accord_library.txt into structured accord definitions.

    Returns list of dicts: name, ingredients {mat: pct}, roles {mat: role},
    target, use_at, smell, good_for.
    """
    lib_path = Path(__file__).resolve().parent.parent.parent / "perfume_accord_library.txt"
    if not lib_path.exists():
        return []
    with open(lib_path, encoding="utf-8") as f:
        text = f.read()

    accords = []
    # Find numbered accord titles (e.g., "  1. AMBER RADIANT BASE")
    # Leading whitespace distinguishes from numbered steps in HOW TO USE
    titles = list(re.finditer(r'^\s+(\d+)\.\s+(.+)', text, re.MULTILINE))

    for idx, match in enumerate(titles):
        name = match.group(2).strip()
        start = match.end()
        end = titles[idx + 1].start() if idx + 1 < len(titles) else len(text)
        content = text[start:end]

        if "HOW TO USE" in name.upper():
            continue

        accord = {"name": name, "ingredients": {}, "roles": {}}

        target = re.search(r'Target:\s*(.+)', content)
        if target:
            accord["target"] = target.group(1).strip()

        use_at = re.search(r'Use at:\s*(.+)', content)
        if use_at:
            accord["use_at"] = use_at.group(1).strip()

        smell = re.search(r'Smells like:\s*(.+)', content)
        if smell:
            accord["smell"] = smell.group(1).strip()

        good_for = re.search(r'Good for:\s*(.+)', content)
        if good_for:
            accord["good_for"] = good_for.group(1).strip()

        # Parse ingredient table rows: | Material — dilution | pct | Role |
        for line in content.split('\n'):
            mat_match = re.match(
                r'\|\s*(.+?)\s*\|\s*([\d.]+)\s*\|\s*(.+?)\s*\|', line
            )
            if mat_match:
                mat_name = mat_match.group(1).strip().replace('**', '')
                try:
                    pct = float(mat_match.group(2))
                except ValueError:
                    continue
                role = mat_match.group(3).strip()
                if mat_name.lower() in ('material', 'total') or '---' in mat_name:
                    continue
                accord["ingredients"][mat_name] = pct
                accord["roles"][mat_name] = role

        if accord["ingredients"]:
            accords.append(accord)

    return accords


def get_accord_library() -> list[dict]:
    """Get parsed accord library from perfume_accord_library.txt."""
    global _ACCORD_LIBRARY
    if _ACCORD_LIBRARY is None:
        _ACCORD_LIBRARY = _parse_accord_library()
    return _ACCORD_LIBRARY


def _fuzzy_name_match(a: str, b: str) -> bool:
    """Check if two material names likely refer to the same material.
    Requires substring match AND the shorter string to be at least 40% of the
    longer string's length (minimum 4 chars) to avoid false positives."""
    if a == b:
        return True
    if len(a) < 4 or len(b) < 4:
        return False
    if a in b:
        return len(a) / len(b) >= 0.4
    if b in a:
        return len(b) / len(a) >= 0.4
    return False


# ── Activity-coefficient (γ) correction for non-ideal EtOH/water mixtures ──
# In a perfume concentrate (60-80% EtOH + aromatics) the vapor-phase partial
# pressure of material i is:   p_i = γ_i · x_i · P°_i
# where γ depends on polarity (logP).  γ=1 (Raoult) is correct only for
# materials of similar polarity to the solvent.
#
# Heuristic γ(logP) calibrated against UNIFAC data for aroma chemical families
# in 75% EtOH / 25% water at 25°C.  Accuracy: ±50%; directionally correct.
#
#  logP < 0.5  → γ ≈ 0.35  (very polar: vanillin, ethyl maltol, heliotropin)
#  logP < 1.5  → γ ≈ 0.55  (polar: coumarin, ethyl vanillin, phenols)
#  logP < 2.5  → γ ≈ 0.80  (mildly polar: linalool, geraniol, indole)
#  logP < 3.5  → γ ≈ 1.00  (balanced: hedione, benzyl acetate, iso eugenol)
#  logP < 4.5  → γ ≈ 1.50  (moderate hydrophobic: iso e super, benzyl sal.)
#  logP < 5.5  → γ ≈ 2.30  (hydrophobic: ambrox, cashmeran, habanolide)
#  logP < 6.5  → γ ≈ 3.40  (very hydrophobic: galaxolide, javanol, ambrettolide)
#  logP >= 6.5 → γ ≈ 4.80  (extreme: heavy macrocyclic musks)
#  unknown     → γ = 1.00  (neutral assumption)

def _gamma_from_logp(logp: float | None) -> float:
    """Return EtOH/water activity coefficient γ from logP."""
    if logp is None:
        return 1.0
    if logp < 0.5:
        return 0.35
    if logp < 1.5:
        return 0.55
    if logp < 2.5:
        return 0.80
    if logp < 3.5:
        return 1.00
    if logp < 4.5:
        return 1.50
    if logp < 5.5:
        return 2.30
    if logp < 6.5:
        return 3.40
    return 4.80


def _get_logp(name: str, mat: dict | None = None) -> float | None:
    """Look up logP/clogP for a material from mat dict or ingredient profile."""
    if mat is not None:
        for key in ("clp", "clogp", "logp", "log_p"):
            v = mat.get(key)
            if v is not None:
                return float(v)
    try:
        from ..ingredient_intelligence import get_profile
        profile = get_profile(name)
        if profile is not None:
            v = getattr(profile, "clogp", None)
            if v is not None:
                return float(v)
    except Exception:
        pass
    return None


@lru_cache(maxsize=4096)
def _lookup_material(name: str) -> dict | None:
    """Find a material in the knowledge graph by name match."""
    from ..material_identity import resolve_material_identity

    db = get_materials_db()
    candidates: list[str] = []
    seen: set[str] = set()

    for variant in _material_alias_keys(name):
        key = _LOOKUP_ALIASES.get(variant, variant)
        if key not in seen:
            candidates.append(key)
            seen.add(key)

    identity = resolve_material_identity(name)
    if identity is not None:
        for candidate in (
            identity.identity_key,
            identity.profile_name,
            identity.chemistry_name,
            identity.label,
            *identity.aliases,
        ):
            for key in _material_alias_keys(candidate):
                if key not in seen:
                    candidates.append(key)
                    seen.add(key)

    for key in candidates:
        if key in db:
            return db[key]

    for key in candidates:
        if key.endswith(" eo"):
            expanded = key[:-3] + " essential oil"
            if expanded in db:
                return db[expanded]

    for key in candidates:
        for k, v in db.items():
            if _fuzzy_name_match(key, k):
                return v
    return None


@lru_cache(maxsize=4096)
def resolve_material_name(name: str) -> str | None:
    """Resolve a material to a canonical display name when possible."""
    from ..material_identity import resolve_material_identity

    identity = resolve_material_identity(name)
    if identity is not None:
        return identity.profile_name

    db = get_materials_db()
    for variant in _material_alias_keys(name):
        key = _LOOKUP_ALIASES.get(variant, variant)
        if key in db and db[key].get("name"):
            return db[key]["name"]

    from ..ingredient_intelligence import get_profile

    profile = get_profile(name)
    if profile is not None:
        return profile.name

    if _is_generic_label(name):
        return None

    for variant in _material_alias_keys(name):
        for key, value in db.items():
            if _fuzzy_name_match(variant, key):
                return value.get("name") or key
    return None


@lru_cache(maxsize=4096)
def classify_roudnitska_roles(roud_text: str | None) -> tuple[str, ...]:
    """Map descriptive Roudnitska text to one or more canonical role keys."""
    norm = _normalize_theory_text(roud_text)
    roles = [
        role
        for role, keywords in _ROUDNITSKA_ROLE_KEYWORDS.items()
        if any(keyword in norm for keyword in keywords)
    ]
    return tuple(roles)


@lru_cache(maxsize=4096)
def material_roudnitska_roles(name: str) -> frozenset[str]:
    """Return canonical Roudnitska roles for a material, with safe fallback heuristics."""
    roles: set[str] = set()
    mat = _lookup_material(name)
    if mat and mat.get("roudnitska_function"):
        roles.update(classify_roudnitska_roles(mat["roudnitska_function"]))

    if roles:
        return frozenset(roles)

    # If the KG knows the material but leaves the theory role blank, treat that
    # as intentionally unknown rather than inferring new literature semantics.
    if mat and mat.get("source") != "ingredient_intelligence_fallback":
        return frozenset(roles)

    from ..ingredient_intelligence import get_profile

    profile = get_profile(name)
    if profile is None:
        return frozenset()

    c = profile.character
    role_scores = {
        "eclat": c.get("radiance", 0) * 1.2 + c.get("freshness", 0),
        "chaleur": c.get("warmth", 0) + c.get("creamy", 0),
        "peau": c.get("powdery", 0) + c.get("creamy", 0) + c.get("animalic", 0) * 0.5,
        "profondeur": c.get("woody", 0) + c.get("smoky", 0) + c.get("animalic", 0) * 0.5,
        "transparence": c.get("freshness", 0) + c.get("green", 0) + c.get("radiance", 0) * 0.5,
    }
    best_role, best_score = max(role_scores.items(), key=lambda item: item[1])
    if best_score >= 9.0:
        roles.add(best_role)
    return frozenset(roles)


@lru_cache(maxsize=4096)
def canonical_jellinek_quadrant_key(quadrant_text: str | None) -> str | None:
    """Normalize descriptive Jellinek quadrant text to a theory_rules key."""
    norm = _normalize_theory_text(quadrant_text)
    if not norm:
        return None

    theory = get_theory_rules()
    quadrants = theory.get("jellinek_map", {}).get("quadrants", {})
    for key, info in quadrants.items():
        key_norm = key.replace("_", "-")
        if key_norm in norm or key in norm:
            return key
        name_norm = _normalize_theory_text(info.get("name"))
        if name_norm and name_norm in norm:
            return key

    for key, keywords in _JELLINEK_QUADRANT_KEYWORDS.items():
        if any(keyword in norm for keyword in keywords):
            return key
    return None


@lru_cache(maxsize=4096)
def material_jellinek_quadrant_key(name: str) -> str | None:
    """Return the canonical Jellinek quadrant key for a material when available."""
    mat = _lookup_material(name)
    if mat and mat.get("jellinek_quadrant"):
        return canonical_jellinek_quadrant_key(mat["jellinek_quadrant"])
    return None


@lru_cache(maxsize=4096)
def material_match_keys(name: str) -> set[str]:
    """Return normalized keys that represent the same material identity."""
    from ..material_identity import resolve_material_identity

    keys: set[str] = set()

    identity = resolve_material_identity(name)
    if identity is not None:
        for candidate in (
            identity.identity_key,
            identity.profile_name,
            identity.chemistry_name,
            identity.label,
            *identity.aliases,
        ):
            keys.update(_material_alias_keys(candidate))

    for variant in _material_alias_keys(name):
        keys.add(variant)
        alias = _LOOKUP_ALIASES.get(variant)
        if alias:
            keys.update(_material_alias_keys(alias))

    mat = _lookup_material(name)
    if mat is not None:
        for candidate in (mat.get("name"), mat.get("alt_name")):
            if candidate:
                keys.update(_material_alias_keys(candidate))

    from ..ingredient_intelligence import get_profile

    profile = get_profile(name)
    if profile is not None:
        keys.update(_material_alias_keys(profile.name))

    return frozenset(key for key in keys if key)


@lru_cache(maxsize=4096)
def material_identity_key(name: str) -> str:
    """Stable lower-case key for deduplicating equivalent materials."""
    from ..material_identity import resolve_material_identity

    identity = resolve_material_identity(name)
    if identity is not None:
        return identity.identity_key

    resolved = resolve_material_name(name)
    if resolved:
        return resolved.lower().strip()

    keys = material_match_keys(name)
    if keys:
        return sorted(keys, key=lambda value: (len(value), value))[0]
    return name.lower().strip()


@lru_cache(maxsize=8192)
def materials_match(a: str, b: str) -> bool:
    """True when two names refer to the same concrete material identity."""
    if not a or not b:
        return False

    keys_a = material_match_keys(a)
    keys_b = material_match_keys(b)
    if keys_a & keys_b:
        return True

    for key_a in keys_a or {a.lower().strip()}:
        for key_b in keys_b or {b.lower().strip()}:
            if _fuzzy_name_match(key_a, key_b):
                return True
    return False


def _rule_signature(rule: dict) -> tuple[str, str, str, str]:
    return (
        str(rule.get("material_a") or "").lower().strip(),
        str(rule.get("material_b") or "").lower().strip(),
        str(rule.get("type") or "").lower().strip(),
        str(rule.get("effect") or "").lower().strip(),
    )


def _build_rule_index(rules: list[dict]) -> dict[str, list[dict]]:
    index: dict[str, list[dict]] = {}
    for rule in rules:
        # Trace the normalized source row through reverse index entries without
        # changing matching keys, deduplication, or score contributions.
        rule_id = hashlib.sha256(
            json.dumps(rule, sort_keys=True, ensure_ascii=True).encode("utf-8")
        ).hexdigest()
        traced_rule = {**rule, "_runtime_rule_id": rule_id, "_runtime_rule": dict(rule)}
        for entry in (
            traced_rule,
            {**traced_rule, "material_a": rule["material_b"], "material_b": rule["material_a"]},
        ):
            for key in sorted(material_match_keys(entry["material_a"])):
                index.setdefault(key, []).append(entry)
    return index


def get_pairing_index() -> dict[str, list[dict]]:
    global _PAIRING_INDEX
    if _PAIRING_INDEX is None:
        _PAIRING_INDEX = _build_rule_index(get_pairing_rules())
    return _PAIRING_INDEX


def get_synergy_index() -> dict[str, list[dict]]:
    global _SYNERGY_INDEX
    if _SYNERGY_INDEX is None:
        _SYNERGY_INDEX = _build_rule_index(get_synergy_rules())
    return _SYNERGY_INDEX


def _matching_rules_for_material(name: str, index: dict[str, list[dict]]) -> list[dict]:
    matches: list[dict] = []
    seen: set[tuple[str, str, str, str]] = set()
    for key in sorted(material_match_keys(name)):
        for rule in index.get(key, []):
            signature = _rule_signature(rule)
            if signature in seen:
                continue
            seen.add(signature)
            matches.append(rule)
    return sorted(
        matches,
        key=lambda rule: (
            str(rule.get("_runtime_rule_id") or ""),
            _rule_signature(rule),
        ),
    )


def analyze_formula_rule_coverage(ingredient_names: list[str]) -> dict[str, object]:
    """Canonical rule-match analysis for a formula's ingredient set.

    Now includes per-axis magnitude-weighted scoring.
    Every rule has 'axis' and 'magnitude' fields."""
    unique_names = sorted(
        (name for name in dict.fromkeys(ingredient_names) if name),
        key=lambda name: (material_identity_key(name), name.casefold(), name),
    )
    identities = {name: material_identity_key(name) for name in unique_names}
    positive_pairs: set[tuple[str, str]] = set()
    conflict_pairs: set[tuple[str, str]] = set()
    covered_pairs: set[tuple[str, str]] = set()
    consumed_rules: dict[str, dict] = {}
    footprint_complete = True

    # Per-axis magnitude tracking
    axis_magnitudes: dict[str, float] = {
        "depth": 0.0, "texture": 0.0, "hedonic": 0.0,
        "performance": 0.0, "sillage": 0.0, "complexity": 0.0,
    }

    indexes = (get_pairing_index(), get_synergy_index())
    for name in unique_names:
        for source_group, index in zip(("pairing_rules", "synergy_matrix"), indexes):
            for rule in _matching_rules_for_material(name, index):
                partner = rule["material_b"]
                rule_axis = rule.get("axis", "complexity")
                rule_mag = float(rule.get("magnitude", 1.0))
                rule_type = rule.get("type", "pairing")
                for other in unique_names:
                    if other == name or not materials_match(partner, other):
                        continue
                    pair = tuple(sorted((identities[name], identities[other])))
                    if pair[0] == pair[1]:
                        continue
                    # This is the scorer's actual consumption branch. Record
                    # its decision, including fuzzy matches, without promoting
                    # the matched labels to resolved chemical identities.
                    origin = rule.get("_runtime_rule")
                    origin_id = rule.get("_runtime_rule_id")
                    if not isinstance(origin, dict) or not origin_id:
                        footprint_complete = False
                    else:
                        rule_id = f"{source_group}:{origin_id}"
                        record = consumed_rules.setdefault(rule_id, {
                            "rule_id": rule_id,
                            "source_group": source_group,
                            "rule": dict(origin),
                            "consumed_bindings": [],
                        })
                        binding = {
                            "formula_material_a": name,
                            "formula_material_b": other,
                            "rule_material_a": rule["material_a"],
                            "rule_material_b": partner,
                        }
                        if binding not in record["consumed_bindings"]:
                            record["consumed_bindings"].append(binding)
                    covered_pairs.add(pair)
                    if rule_type == "synergy":
                        positive_pairs.add(pair)
                    elif rule_type == "conflict":
                        conflict_pairs.add(pair)
                    # Track by axis — only highest magnitude per pair per axis
                    if rule_axis in axis_magnitudes:
                        axis_magnitudes[rule_axis] += rule_mag

    total_pairs = len(unique_names) * (len(unique_names) - 1) // 2
    # Normalize axis magnitudes to 0-100
    max_possible = max(total_pairs * 3.0, 1.0)
    axis_scores = {
        k: min(100.0, (v / max_possible) * 100.0)
        for k, v in axis_magnitudes.items()
    }
    return {
        "positive_pairs": positive_pairs,
        "conflict_pairs": conflict_pairs,
        "covered_pairs": covered_pairs,
        "total_pairs": total_pairs,
        "axis_scores": axis_scores,
        "raw_axis_magnitudes": {k: round(v, 4) for k, v in axis_magnitudes.items()},
        "total_axis_magnitude": sum(axis_magnitudes.values()),
        "consumed_rules_complete": footprint_complete,
        "consumed_rules": [
            {
                **record,
                "consumed_bindings": sorted(
                    record["consumed_bindings"],
                    key=lambda binding: tuple(
                        str(binding.get(field, ""))
                        for field in (
                            "formula_material_a",
                            "formula_material_b",
                            "rule_material_a",
                            "rule_material_b",
                        )
                    ),
                ),
            }
            for _rule_id, record in sorted(consumed_rules.items())
        ],
    }


def find_missing_rule_partners(ingredient_names: list[str]) -> list[tuple[str, str]]:
    """Return synergy partners implied by active rules but absent from the formula."""
    unique_names = [name for name in dict.fromkeys(ingredient_names) if name]
    missing: set[tuple[str, str]] = set()
    indexes = (get_pairing_index(), get_synergy_index())

    for name in unique_names:
        for index in indexes:
            for rule in _matching_rules_for_material(name, index):
                if rule["type"] != "synergy":
                    continue
                partner = rule["material_b"]
                if any(materials_match(partner, other) for other in unique_names):
                    continue
                source_display = resolve_material_name(rule["material_a"]) or name
                partner_display = resolve_material_name(partner)
                if source_display is None:
                    source_display = rule["material_a"].strip()
                if partner_display is None:
                    if _is_generic_label(partner):
                        continue
                    partner_display = partner.strip()
                missing.add((source_display, partner_display))

    return sorted(missing)


# ── Note classification from Carles position & MW ──

# Fallback overrides for materials with missing/incomplete DB data
_KNOWN_TOP_NOTES = {
    "bergamot fcf", "bergamot eo", "neroli eo", "lemon eo", "lime eo",
    "grapefruit eo", "orange eo", "mandarin eo", "petitgrain eo",
    "citral", "citronellal", "d-limonene", "dihydromyrcenol",
    "linalool", "linalyl acetate", "melonal",
}
_KNOWN_BASE_NOTES = {
    "patchouli eo", "vetiver eo", "sandalwood eo",
    "olibanum resinoid", "benzoin sumatra resinoid", "labdanum absolute",
}


def classify_note(material_name: str) -> str:
    """Classify a material as top/heart/base using Carles position first, then MW."""
    mat = _lookup_material(material_name)
    if mat:
        pos = (mat.get("carles_position") or "").lower()
        if pos:
            has_base = "base" in pos
            has_heart = "heart" in pos or "modif" in pos
            has_top = "top" in pos or "effet" in pos or "tête" in pos
            # "Fond" means body/foundation — only treat as base if heart is absent
            if "fond" in pos and not has_heart:
                has_base = True
            # Arrow indicates transition: split by arrow for pragmatic classification
            if "\u2192" in pos or "->" in pos:
                sep = "\u2192" if "\u2192" in pos else "->"
                destination = pos.split(sep)[-1]
                source = pos.split(sep)[0]
                # If destination is base → material settles as base (longevity)
                if "base" in destination or ("fond" in destination and "heart" not in destination):
                    return "base"
                # If source is top → material provides initial lift
                if "top" in source or "effet" in source or "tête" in source:
                    return "top"
                return "heart"
            # Single note position
            if has_top and not has_heart and not has_base:
                return "top"
            if has_base and not has_top:
                return "base"
            if has_heart:
                return "heart"
        # Fallback: MW-based classification
        mw = mat.get("mw")
        if mw is not None:
            if mw < 170:
                return "top"
            if mw < 250:
                return "heart"
            return "base"
    from ..ingredient_intelligence import get_profile
    profile = get_profile(material_name)
    if profile is not None:
        return profile.note
    # Known-note overrides for materials not found or with incomplete data
    key = material_name.lower().strip()
    if key in _KNOWN_TOP_NOTES:
        return "top"
    if key in _KNOWN_BASE_NOTES:
        return "base"
    return "heart"  # default assumption


@dataclass
class FormulaVector:
    """A formula represented as ingredient→percentage mapping with computed properties."""
    ingredients: dict[str, float] = field(default_factory=dict)
    dilutions: dict[str, float] = field(default_factory=dict)

    @property
    def total_pct(self) -> float:
        return sum(self.ingredients.values())

    @property
    def has_dilution_data(self) -> bool:
        return len(self.dilutions) > 0

    def effective_pct(self, name: str) -> float:
        """Return active percentage accounting for dilution (1.0 = neat)."""
        raw = self.ingredients.get(name, 0.0)
        dil = self.dilutions.get(name, 1.0)
        return raw * dil

    def effective_ingredients(self) -> dict[str, float]:
        """Return {name: active_pct} accounting for dilutions, renormalized to 100%.
        Falls back to raw ingredients if no dilution data."""
        if hasattr(self, '_eff_cache') and self._eff_cache is not None:
            return self._eff_cache
        if not self.has_dilution_data:
            result = dict(self.ingredients)
        else:
            active = {n: self.effective_pct(n) for n in self.ingredients}
            total = sum(active.values()) or 1.0
            raw_total = sum(self.ingredients.values()) or 1.0
            # Renormalize so active percentages sum to same total as raw
            scale = raw_total / total
            result = {n: v * scale for n, v in active.items()}
        self._eff_cache = result
        return result

    def note_distribution(self) -> dict[str, float]:
        """Return {top: %, heart: %, base: %} of the formula by active weight."""
        eff = self.effective_ingredients()
        dist = {"top": 0.0, "heart": 0.0, "base": 0.0}
        for name, pct in eff.items():
            dist[classify_note(name)] += pct
        total = sum(dist.values()) or 1.0
        return {k: round(v / total * 100, 1) for k, v in dist.items()}

    def avg_property(self, prop: str) -> float | None:
        """Weight-averaged material property using active concentrations.

        When prop=="vp", returns the γ-corrected headspace-effective VP:
            VP_eff_i = γ(logP_i) · VP_i
        where γ accounts for non-ideal EtOH/water activity (polar materials
        have γ<1 and hide in headspace; hydrophobic materials have γ>1 and
        project above their mass fraction).
        """
        eff = self.effective_ingredients()
        total_w = 0.0
        weighted = 0.0
        profile_prop_map = {
            "mw": "mw",
            "vp": "vp",
            "clp": "clogp",
            "odt": "odt",
        }
        apply_gamma = (prop == "vp")
        for name, pct in eff.items():
            mat = _lookup_material(name)
            value = None
            if mat and mat.get(prop) is not None:
                value = mat[prop]
            elif prop in profile_prop_map:
                from ..ingredient_intelligence import get_profile
                profile = get_profile(name)
                if profile is not None:
                    value = getattr(profile, profile_prop_map[prop], None)
            if value is not None:
                if apply_gamma:
                    logp = _get_logp(name, mat)
                    value = value * _gamma_from_logp(logp)
                weighted += value * pct
                total_w += pct
        return weighted / total_w if total_w > 0 else None

    def ingredient_list(self) -> list[str]:
        return list(self.ingredients.keys())

    def weighted_volatility_index(self) -> float | None:
        """Volatility index: VI = Σ(pct × γ·VP_i / √MW_i) / Σ(pct).

        Captures headspace projection better than avg VP alone:
          - lighter molecules (low MW) escape faster → VP/√MW weight
          - hydrophobic molecules (high logP) have γ>1 in EtOH/water:
            they punch above their mass fraction in the headspace
          - polar molecules (low logP) have γ<1 and hide below their %

        Uses γ(logP) heuristic from _gamma_from_logp().
        Returns None when no ingredient has both VP and MW data.
        """
        import math
        eff = self.effective_ingredients()
        total_w = 0.0
        weighted = 0.0
        for name, pct in eff.items():
            mat = _lookup_material(name)
            vp = None
            mw = None
            if mat:
                vp = mat.get("vp")
                mw = mat.get("mw")
            # Fallback to ingredient_intelligence profiles
            if vp is None or mw is None:
                try:
                    from ..ingredient_intelligence import get_profile
                    profile = get_profile(name)
                    if profile is not None:
                        if vp is None:
                            vp = getattr(profile, "vp", None)
                        if mw is None:
                            mw = getattr(profile, "mw", None)
                except ImportError:
                    pass
            if vp is not None and mw is not None and mw > 0:
                logp = _get_logp(name, mat)
                gamma = _gamma_from_logp(logp)
                weighted += pct * (gamma * vp) / math.sqrt(mw)
                total_w += pct
        return weighted / total_w if total_w > 0 else None


@dataclass
class ObjectiveWeights:
    """Weights for multi-objective scoring — 10 axes.

    7 kept axes: physics-grounded or peer-reviewed experimental data.
    3 rewritten axes: luxury (ingredient quality), texture (haptic/sensory),
    stacking_depth (intentional structural layering = craftsmanship).
    """
    longevity: float = 0.8
    sillage: float = 0.8
    synergy: float = 0.5
    luxury: float = 0.8       # Ingredient quality perception (not price)
    texture: float = 0.8      # Haptic/sensory: rounded, creamy, harsh, silky
    stacking_depth: float = 0.8  # Intentional structural layering (craftsmanship)
    # ── Science axes ──
    skin_performance: float = 0.7   # Reservoir kinetics + fabric substantivity
    hedonic: float = 0.5      # Intrinsic pleasantness (Khan 2007)
    perceptual_clarity: float = 0.6  # Mixture suppression + cross-adaptation
    photorealism: float = 0.7  # Photorealistic transparency (glass-like definition)

    def as_dict(self) -> dict[str, float]:
        return {
            "longevity": self.longevity,
            "sillage": self.sillage,
            "synergy": self.synergy,
            "luxury": self.luxury,
            "texture": self.texture,
            "stacking_depth": self.stacking_depth,
            "skin_performance": self.skin_performance,
            "hedonic": self.hedonic,
            "perceptual_clarity": self.perceptual_clarity,
            "photorealism": self.photorealism,
        }


@dataclass
class OptimizationConstraints:
    """Constraints for the optimizer."""
    max_ingredients: int = 15
    min_ingredients: int = 3
    max_total_pct: float = 100.0
    min_total_pct: float = 10.0
    # Note distribution targets (Carles method)
    target_top_pct: float = 20.0
    target_heart_pct: float = 40.0
    target_base_pct: float = 40.0
    # Tolerance for note distribution
    note_tolerance: float = 10.0
    # Only use materials the user owns
    inventory_only: bool = True
    # Available materials (populated from inventory.txt)
    available_materials: list[str] = field(default_factory=list)


@dataclass
class OptimizationResult:
    """Result from the optimizer."""
    formula: FormulaVector
    scores: dict[str, object]
    total_score: float
    suggestions: list[str]
    reasoning: list[str]
    ranking_status: str = "WITHHELD"
    formula_optimization_authority: bool = False
    selection_basis: str = "LEGACY_DIAGNOSTIC_TOTAL_NOT_ADMITTED"
