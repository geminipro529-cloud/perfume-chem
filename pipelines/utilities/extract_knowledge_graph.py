"""
Extract structured knowledge graph from scientific reference files and knowledge docs.
Outputs:
  data/knowledge_graph/pairing_rules.json
  data/knowledge_graph/material_properties.json
  data/knowledge_graph/synergy_matrix.json
  data/knowledge_graph/theory_rules.json
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


import json
import re

ROOT = Path(__file__).parent
REF_DIR = ROOT
KNOWLEDGE_DIR = ROOT / "knowledge" / "science"
OUT_DIR = ROOT / "data" / "knowledge_graph"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Parse scientific reference files → material properties + pairing rules
# ---------------------------------------------------------------------------

# Only use combined reference files (A_B_C_D, E_F_G_H, etc.) to avoid duplicates
REF_FILES = sorted(f for f in ROOT.glob("scientific_reference_*.txt") if '_' in f.stem.replace('scientific_reference_', ''))

def parse_material_block(block: str) -> dict | None:
    """Parse a single material entry block from a scientific reference file."""
    # Extract material name from header line like "  1. ALDEHYDE C10 (Decanal)"
    header_m = re.search(r'^\s*\d+\.\s+(.+)', block, re.MULTILINE)
    if not header_m:
        return None
    raw_name = header_m.group(1).strip()
    # Clean name: remove trailing stock info
    name = re.split(r'\s*[—–-]\s*(?:neat|10%|20%|30%|50%|100%|1%)', raw_name, maxsplit=1)[0].strip()
    # Remove parenthetical alternate name for the key, but keep it
    alt_match = re.search(r'\(([^)]+)\)', name)
    alt_name = alt_match.group(1) if alt_match else None
    clean_name = re.sub(r'\s*\([^)]*\)', '', name).strip()

    props = {"name": clean_name, "alt_name": alt_name}

    # Helper to extract a field value
    def extract(pattern, text=block, group=1, default=None):
        m = re.search(pattern, text, re.IGNORECASE)
        return m.group(group).strip() if m else default

    # Chemical identity
    props["cas"] = extract(r'CAS:\s+(.+)')
    props["formula_str"] = extract(r'Formula:\s+(.+)')

    def safe_float(pattern):
        """Extract a numeric value with robust error handling."""
        raw = extract(pattern)
        if not raw:
            return None
        try:
            return float(raw)
        except ValueError:
            return None

    props["mw"] = safe_float(r'MW:\s+~?([\d.]+)')
    props["bp"] = safe_float(r'BP:\s+~?([\d.]+)')
    props["vp"] = safe_float(r'VP:\s+~?([\d.]+)')
    props["clp"] = safe_float(r'CLP:\s+~?([\d.+-]+)')
    # ODT values: handle ~prefix, scientific notation, and descriptive text
    odt_raw = extract(r'ODT:\s+.*?~?([\d.]+(?:[Ee][+-]?\d+)?)')
    props["odt"] = safe_float(r'ODT:\s+.*?~?([\d.]+(?:[Ee][+-]?\d+)?)')

    # OPK SAR
    props["sar_class"] = extract(r'SAR Class:\s+(.+)')
    props["olfactophore"] = extract(r'Olfactophore:\s+(.+)')

    # Arctander
    arc_block = re.search(r'ARCTANDER.*?(?=\n\s*[A-Z]{3,}|\n━)', block, re.S)
    if arc_block:
        props["arctander_character"] = extract(r'Character:\s+(.+)', arc_block.group())
        props["arctander_tenacity"] = extract(r'Tenacity:\s+(.+)', arc_block.group())

    # Carles
    props["carles_position"] = extract(r'Position:\s+(.+?)(?:\n|$)')
    # Multi-line pairing rule
    pairing_m = re.search(r'Pairing Rule:\s+(.+?)(?=\n\s*\n|\n\s*[A-Z]{2,})', block, re.S)
    props["carles_pairing_rule"] = ' '.join(pairing_m.group(1).split()) if pairing_m else None

    # Roudnitska
    roud_block = re.search(r'ROUDNITSKA.*?(?=\n\s*JELLINEK|\n━)', block, re.S)
    if roud_block:
        props["roudnitska_function"] = extract(r'Function:\s+(.+)', roud_block.group())
        craft_m = re.search(r'Craft Note:\s+(.+?)(?=\n\s*\n|\n\s*Key|\n\s*[A-Z]{2,})', roud_block.group(), re.S)
        props["roudnitska_craft_note"] = ' '.join(craft_m.group(1).split()) if craft_m else None

    # Jellinek
    jell_block = re.search(r'JELLINEK.*?(?=\n\s*PRACTICAL|\n━)', block, re.S)
    if jell_block:
        props["jellinek_axis"] = extract(r'Axis Position:\s+(.+)', jell_block.group())
        props["jellinek_quadrant"] = extract(r'Map Quadrant:\s+(.+)', jell_block.group())
        props["jellinek_effect"] = extract(r'Effect:\s+(.+)', jell_block.group())

    # Practical usage
    prac_block = re.search(r'PRACTICAL USAGE.*?(?=\n━|$)', block, re.S)
    if prac_block:
        pb = prac_block.group()
        typ_pct = extract(r'Typical %:\s+(.+)', pb)
        props["typical_pct_range"] = typ_pct
        max_pct = extract(r'Max safe %:\s+(.+)', pb)
        props["max_safe_pct"] = max_pct
        stock_form = extract(r'Your form:\s+(.+)', pb)
        props["stock_form"] = stock_form

        # Best with / Avoid
        best_m = re.search(r'Best with:\s+(.+)', pb)
        if best_m:
            raw = best_m.group(1).strip()
            # Split on commas, clean
            props["best_with"] = [x.strip() for x in raw.split(',') if x.strip()]
        avoid_m = re.search(r'Avoid:\s+(.+?)(?:\n|$)', pb)
        if avoid_m:
            props["avoid"] = avoid_m.group(1).strip()
        handle_m = re.search(r'Handle as:\s+(.+)', pb)
        props["handle_as"] = handle_m.group(1).strip() if handle_m else None

    return props


def split_into_material_blocks(text: str) -> list[str]:
    """Split a reference file into individual material blocks.
    Each material starts with a numbered header like '  1. ALDEHYDE C10 (Decanal)'
    and continues until the next numbered header or end of file.
    """
    # Material names are ALL CAPS (at least 2 uppercase chars in a row)
    # This avoids matching numbered lists inside content like "1. It creates..."
    headers = list(re.finditer(r'^\s{0,4}\d+\.\s+[A-Z][A-Z]', text, re.MULTILINE))
    blocks = []
    for i, h in enumerate(headers):
        start = h.start()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        blocks.append(text[start:end])
    return blocks


def extract_pairing_rules_from_material(mat: dict) -> list[dict]:
    """Generate pairing rule entries from a parsed material."""
    rules = []
    name = mat["name"]

    # From "best_with" list
    if mat.get("best_with"):
        for partner in mat["best_with"]:
            # Skip generic entries
            if partner.lower() in ("everything", "all", "nothing specific"):
                continue
            rules.append({
                "material_a": name,
                "material_b": partner,
                "effect": f"{name} pairs well with {partner}",
                "source": "scientific_reference/PRACTICAL_USAGE/Best_with",
                "type": "synergy"
            })

    # From "avoid" field
    if mat.get("avoid"):
        avoid_text = mat["avoid"]
        # Try to extract specific material names from avoid text
        rules.append({
            "material_a": name,
            "material_b": "__avoid__",
            "effect": avoid_text,
            "source": "scientific_reference/PRACTICAL_USAGE/Avoid",
            "type": "conflict"
        })

    # From Carles pairing rule
    if mat.get("carles_pairing_rule"):
        rules.append({
            "material_a": name,
            "material_b": "__carles_rule__",
            "effect": mat["carles_pairing_rule"],
            "source": "scientific_reference/CARLES/Pairing_Rule",
            "type": "neutral"
        })

    return rules


# Parse all reference files
all_materials = []
all_pairing_rules = []

for ref_file in REF_FILES:
    text = ref_file.read_text(encoding="utf-8", errors="replace")
    blocks = split_into_material_blocks(text)
    for block in blocks:
        mat = parse_material_block(block)
        if mat and mat["name"]:
            all_materials.append(mat)
            all_pairing_rules.extend(extract_pairing_rules_from_material(mat))

print(f"Parsed {len(all_materials)} materials from {len(REF_FILES)} reference files")
print(f"Extracted {len(all_pairing_rules)} pairing rules")

# ---------------------------------------------------------------------------
# 2. Parse synergy knowledge files → synergy matrix
# ---------------------------------------------------------------------------

def parse_synergy_file(filepath: Path) -> list[dict]:
    """Extract synergy/antagonism rules from knowledge/science/synergy_and_amplification.md"""
    rules = []
    text = filepath.read_text(encoding="utf-8", errors="replace")

    # Extract table rows: | Material A | Material B | Effect | Ratio |
    table_pattern = re.compile(
        r'\|\s*\*?\*?([^|*]+?)\*?\*?\s*\|\s*\*?\*?([^|*]+?)\*?\*?\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|'
    )
    for m in table_pattern.finditer(text):
        a, b, effect, ratio = m.group(1).strip(), m.group(2).strip(), m.group(3).strip(), m.group(4).strip()
        # Skip header rows
        if a.lower() in ("amplifier", "extender", "molecule a", "base formula", "---", ""):
            continue
        if "---" in a or "---" in b:
            continue
        rules.append({
            "material_a": a,
            "material_b": b,
            "effect": effect,
            "ratio": ratio,
            "source": filepath.name,
            "type": "synergy"
        })

    # Extract "Bad Pair" sections
    bad_pairs = re.finditer(
        r'Bad Pair \d+:\s*(.+?)\n\s*\*\*Why:\*\*\s*(.+?)(?:\n|$)',
        text, re.IGNORECASE
    )
    for m in bad_pairs:
        pair_desc = m.group(1).strip()
        reason = m.group(2).strip()
        # Try to split pair desc on + or "+"
        parts = re.split(r'\s*\+\s*', pair_desc)
        if len(parts) == 2:
            rules.append({
                "material_a": parts[0].strip().strip("*"),
                "material_b": parts[1].strip().strip("*").rstrip(" =").strip(),
                "effect": reason,
                "ratio": "avoid",
                "source": filepath.name,
                "type": "conflict"
            })

    # Extract specific synergistic pair sections
    pair_sections = re.finditer(
        r'Pair \d+:\s*(.+?)\n.*?Ratio:\*\*\s*(.+?)\n.*?Effect:\*\*\s*(.+?)\n',
        text, re.S | re.IGNORECASE
    )
    for m in pair_sections:
        pair_desc = m.group(1).strip().strip("*")
        ratio = m.group(2).strip()
        effect = m.group(3).strip()
        parts = re.split(r'\s*\+\s*', pair_desc)
        if len(parts) == 2:
            a = parts[0].strip().strip("*")
            b_raw = parts[1].strip().strip("*")
            b = re.split(r'\s*=\s*', b_raw)[0].strip()
            rules.append({
                "material_a": a,
                "material_b": b,
                "effect": effect,
                "ratio": ratio,
                "source": filepath.name,
                "type": "synergy"
            })

    return rules


def parse_interaction_chemistry(filepath: Path) -> list[dict]:
    """Extract rules from interaction_chemistry.md"""
    rules = []
    text = filepath.read_text(encoding="utf-8", errors="replace")

    # Extract example pairs from text
    example_pattern = re.compile(
        r'\*Example:\*\s*(.+?)\+\s*(.+?)\s*=\s*(.+?)(?:\n|$)', re.IGNORECASE
    )
    for m in example_pattern.finditer(text):
        a = m.group(1).strip().strip("*() ")
        b = m.group(2).strip().strip("*() ")
        effect = m.group(3).strip().strip("*() ")
        rules.append({
            "material_a": a,
            "material_b": b,
            "effect": effect,
            "ratio": "n/a",
            "source": filepath.name,
            "type": "synergy"
        })

    return rules


def parse_functional_group_reactivity(filepath: Path) -> list[dict]:
    """Extract reactive pair rules from functional_group_reactivity.md"""
    rules = []
    text = filepath.read_text(encoding="utf-8", errors="replace")

    # General functional group rules
    fg_rules = [
        {"group_a": "aldehyde", "group_b": "amine", "effect": "Schiff base formation — discoloration, smell change", "type": "conflict"},
        {"group_a": "aldehyde", "group_b": "oxygen", "effect": "Oxidation to carboxylic acid — sour off-note", "type": "conflict"},
        {"group_a": "phenol", "group_b": "base", "effect": "Deprotonation — discoloration", "type": "conflict"},
        {"group_a": "phenol", "group_b": "oxygen", "effect": "Quinone formation — brown color", "type": "conflict"},
        {"group_a": "ester", "group_b": "acid+water", "effect": "Hydrolysis to acid + alcohol", "type": "conflict"},
        {"group_a": "terpene", "group_b": "oxygen+light", "effect": "Oxidation to off-notes (musty, turpentine)", "type": "conflict"},
    ]

    # Specific material pairs from examples
    specific = [
        ("Citral", "amines", "Brown mess — Schiff base", "conflict"),
        ("Cinnamaldehyde", "oxygen", "Cinnamic acid — loses sweetness", "conflict"),
        ("Eugenol", "alkaline water", "Darkens", "conflict"),
        ("Vanillin", "Fe³⁺", "Purple stain", "conflict"),
        ("Linalyl acetate", "moisture", "Hydrolysis to linalool + acetic acid", "conflict"),
        ("Limonene", "oxygen", "Oxidation to carvone, limonene oxide — musty", "conflict"),
    ]

    for a, b, effect, rtype in specific:
        rules.append({
            "material_a": a,
            "material_b": b,
            "effect": effect,
            "ratio": "n/a",
            "source": filepath.name,
            "type": rtype
        })

    for r in fg_rules:
        rules.append({
            "material_a": r["group_a"],
            "material_b": r["group_b"],
            "effect": r["effect"],
            "ratio": "n/a",
            "source": filepath.name,
            "type": r["type"],
            "is_functional_group_rule": True
        })

    return rules


synergy_rules = []

synergy_file = KNOWLEDGE_DIR / "synergy_and_amplification.md"
if synergy_file.exists():
    synergy_rules.extend(parse_synergy_file(synergy_file))

interaction_file = KNOWLEDGE_DIR / "interaction_chemistry.md"
if interaction_file.exists():
    synergy_rules.extend(parse_interaction_chemistry(interaction_file))

fg_file = KNOWLEDGE_DIR / "functional_group_reactivity.md"
if fg_file.exists():
    synergy_rules.extend(parse_functional_group_reactivity(fg_file))

print(f"Extracted {len(synergy_rules)} synergy/interaction rules from knowledge files")

# ---------------------------------------------------------------------------
# 3. Build theory rules from the 5 authority frameworks
# ---------------------------------------------------------------------------

theory_rules = {
    "carles_method": {
        "description": "Jean Carles' systematic perfume construction method",
        "principle": "Systematically trial combinations of characteristic materials against base types using a grid approach",
        "note_distribution": {
            "top": {"min_pct": 10, "max_pct": 30, "ideal_pct": 20, "role": "First impression, sparkle, lift"},
            "heart": {"min_pct": 25, "max_pct": 50, "ideal_pct": 40, "role": "Theme, character, identity"},
            "base": {"min_pct": 30, "max_pct": 55, "ideal_pct": 40, "role": "Foundation, longevity, depth"}
        },
        "positions": {
            "effets": "Top note modifiers — sparkle and lift (aldehydes, citrus, green)",
            "modificateurs": "Heart note modifiers — character and theme",
            "fond": "Base note foundation — longevity and depth"
        },
        "method_steps": [
            "1. Choose a characterizing material (the star ingredient)",
            "2. Build a base accord (amber, woody, musk, or chypre)",
            "3. Trial the star against multiple bases in a grid",
            "4. Select the best combination",
            "5. Add modifiers (top note sparkle, heart bridges)",
            "6. Refine proportions iteratively"
        ]
    },
    "roudnitska_roles": {
        "description": "Edmond Roudnitska's aesthetic role taxonomy for perfume materials",
        "principle": "Every material in a composition serves an aesthetic function, not just a scent category",
        "roles": {
            "transparence": {
                "description": "Materials that give airy, lifted, abstract quality — 'open the window'",
                "examples": ["Aldehydes C10-C12", "Hedione", "Dihydromyrcenol"],
                "effect": "Prevents composition from feeling heavy or closed"
            },
            "chaleur": {
                "description": "Materials that provide warmth and comfort",
                "examples": ["Vanillin", "Benzoin", "Coumarin", "Labdanum"],
                "effect": "Creates psychological warmth and enveloping quality"
            },
            "noblesse": {
                "description": "Materials that convey quality and refinement",
                "examples": ["Alpha Irone", "Rose absolute", "Sandalwood", "Oud"],
                "effect": "Elevates composition above commodity level"
            },
            "peau": {
                "description": "Skin-like materials that create intimacy",
                "examples": ["Iso E Super", "Musks", "Cashmeran", "Ambroxan"],
                "effect": "Creates close-to-skin effect and personal aura"
            },
            "eclat": {
                "description": "Materials that create brightness and radiance",
                "examples": ["Bergamot", "Linalool", "Hedione", "Citrus oils"],
                "effect": "Projects outward, creates sillage trail"
            },
            "profondeur": {
                "description": "Materials that create depth and mystery",
                "examples": ["Patchouli", "Vetiver", "Myrrh", "Birch tar"],
                "effect": "Adds complexity and intrigue to dry-down"
            }
        }
    },
    "opk_sar": {
        "description": "Ohloff, Pickenhagen & Kraft Structure-Activity Relationship principles",
        "principle": "Molecular structure determines olfactory character — predictable patterns exist",
        "rules": [
            {
                "rule": "Chain length determines aldehyde character",
                "detail": "C8=orange, C9=rose, C10=waxy-orange, C11=clean-waxy, C12=metallic-soapy. Each CH₂ shifts from fruity→waxy→soapy→metallic.",
                "applies_to": "Linear aliphatic aldehydes"
            },
            {
                "rule": "Odd-even effect in aldehydes",
                "detail": "Odd-carbon aldehydes are more floral, even-carbon more fatty/waxy",
                "applies_to": "Linear aliphatic aldehydes"
            },
            {
                "rule": "Branching softens character",
                "detail": "Branched aldehydes (e.g., C12 MNA) are softer and less harsh than linear counterparts",
                "applies_to": "Aldehydes"
            },
            {
                "rule": "Ionone ring size determines violet vs iris",
                "detail": "Alpha-ionone = more violet-like, beta-ionone = more woody-iris. Methyl substitution adds powdery warmth.",
                "applies_to": "Ionones and irones"
            },
            {
                "rule": "Macrocyclic ring size determines musk character",
                "detail": "C14-C16 macrolides = sweet, skin-like musk. Smaller rings = sharper. Larger = weaker.",
                "applies_to": "Macrocyclic musks"
            },
            {
                "rule": "Ester hydrolysis stability",
                "detail": "Esters with bulky R groups are more stable. Linear esters hydrolyze faster.",
                "applies_to": "Esters (Hedione, linalyl acetate, benzyl acetate)"
            },
            {
                "rule": "Lipophilicity determines tenacity",
                "detail": "Higher CLP (Clog P) = more lipophilic = slower evaporation = longer lasting on skin",
                "applies_to": "All materials"
            },
            {
                "rule": "Vapor pressure determines projection",
                "detail": "Higher VP = more volatile = more projection but less longevity",
                "applies_to": "All materials"
            },
            {
                "rule": "Molecular weight correlates with note position",
                "detail": "MW < 170 = top note, 170-250 = heart, >250 = base. Exceptions exist for cyclic structures.",
                "applies_to": "All materials"
            }
        ]
    },
    "jellinek_map": {
        "description": "Paul Jellinek's psychological odor effect map with dual axes",
        "principle": "Odors affect psychology along two orthogonal axes — can map any material to a quadrant",
        "axes": {
            "x_axis": {"negative": "Narcotic (sedating, heavy)", "positive": "Stimulating (energizing, bright)"},
            "y_axis": {"negative": "Anti-erogenic (clean, clinical)", "positive": "Erogenic (sensual, warm)"}
        },
        "quadrants": {
            "upper_left": {
                "name": "Fresh-Stimulating",
                "character": "Clean, bright, attention-getting, energizing",
                "materials": ["Citrus", "Aldehydes", "Green notes", "Marine"],
                "perfume_types": ["Colognes", "Sport fragrances", "Clean/fresh"]
            },
            "upper_right": {
                "name": "Warm-Stimulating",
                "character": "Spicy, energetic, warming, assertive",
                "materials": ["Spices", "Cinnamon", "Pepper", "Ginger"],
                "perfume_types": ["Oriental-spicy", "Gourmand-spicy"]
            },
            "lower_right": {
                "name": "Warm-Narcotic",
                "character": "Sensual, heavy, enveloping, narcotic",
                "materials": ["Vanilla", "Amber", "Musks", "Resins", "Oud"],
                "perfume_types": ["Oriental", "Amber", "Oud"]
            },
            "lower_left": {
                "name": "Cool-Narcotic",
                "character": "Soft, powdery, calming, dreamy",
                "materials": ["Iris", "Violet", "Heliotrope", "Powder"],
                "perfume_types": ["Powdery", "Iris/violet", "Soft floral"]
            }
        },
        "design_principle": "A well-balanced composition should have materials spanning at least 2-3 quadrants for complexity. Monotone compositions (all in one quadrant) lack depth."
    },
    "legendary_book_principles": {
        "chemistry_of_fragrances": {
            "source": "The Chemistry of Fragrances (Sell, RSC)",
            "key_principles": [
                "Molecular geometry determines smell — small structural changes create large olfactory shifts",
                "Olfactory receptors are combinatorial — each molecule activates a unique pattern of receptors",
                "The 'perfume pyramid' is an approximation — actual temporal evolution depends on vapor pressure curves",
                "Fixation is both physical (molecular trapping) and perceptual (receptor adaptation masking base notes)"
            ]
        },
        "perfumery_principles_and_practice": {
            "source": "Perfumery: Principles and Practice (Calkin & Jellinek)",
            "key_principles": [
                "Fragrance families are defined by dominant accord, not individual materials",
                "Balance requires tension — purely harmonious compositions are boring",
                "The best perfumes have a 'twist' — one unexpected element that creates memorability",
                "Systematic grid trials (Carles method) outperform random experimentation"
            ]
        },
        "perfume_materials_natural_origin": {
            "source": "Perfume & Flavor Materials of Natural Origin (Arctander)",
            "key_principles": [
                "Natural materials are complex mixtures — a single EO can contain 200+ molecules",
                "The 'body' of a natural material comes from trace components, not the major ones",
                "Synthetic materials should reconstruct the olfactory profile, not just the chemical composition",
                "Tenacity depends on the molecular weight distribution, not just a single molecule's MW"
            ]
        }
    }
}

# ---------------------------------------------------------------------------
# 4. Build the incompatibility rules from validator.py
# ---------------------------------------------------------------------------

# These come from the existing code — encoding them in the knowledge graph too
validator_incompatibility_rules = [
    {"material_a": "animalic", "material_b": "clean_base", "effect": "FORBIDDEN — animalics create fecal/urine smell in clean bases", "type": "conflict", "source": "engine/validator.py"},
    {"material_a": "animalic", "material_b": "aquatic_base", "effect": "FORBIDDEN — animalics clash with aquatic transparency", "type": "conflict", "source": "engine/validator.py"},
    {"material_a": "animalic", "material_b": "aldehydic_base", "effect": "FORBIDDEN — animalics overpower delicate aldehydic lift", "type": "conflict", "source": "engine/validator.py"},
    {"material_a": "aldehyde", "material_b": "heavy_oriental_base", "effect": "POOR — aldehydes masked/buried under heavy resins", "type": "conflict", "source": "engine/validator.py"},
    {"material_a": "aldehyde", "material_b": "resinous_base", "effect": "POOR — aldehydes masked by heavy resins", "type": "conflict", "source": "engine/validator.py"},
    {"material_a": "fresh_green", "material_b": "heavy_oriental_base", "effect": "POOR — fresh greens clash with sweet orientals (salad in bakery)", "type": "conflict", "source": "engine/validator.py"},
    {"material_a": "marine", "material_b": "heavy_oriental_base", "effect": "POOR — marine notes clash with heavy sweetness", "type": "conflict", "source": "engine/validator.py"},
    {"material_a": "marine", "material_b": "resinous_base", "effect": "POOR — marine notes clash with heavy resins", "type": "conflict", "source": "engine/validator.py"},
]

# Combine all synergy rules with validator rules
all_synergy_rules = synergy_rules + validator_incompatibility_rules

print(f"Total synergy/interaction rules: {len(all_synergy_rules)}")

# ---------------------------------------------------------------------------
# 5. Deduplicate and clean pairing rules
# ---------------------------------------------------------------------------

def normalize_name(name: str) -> str:
    """Normalize a material name for deduplication."""
    n = name.lower().strip()
    n = re.sub(r'\s+', ' ', n)
    n = n.replace("**", "")
    return n

# Deduplicate pairing rules by (material_a, material_b) normalized
seen_pairs = set()
unique_pairing_rules = []
for rule in all_pairing_rules:
    key = (normalize_name(rule["material_a"]), normalize_name(rule["material_b"]))
    if key not in seen_pairs:
        seen_pairs.add(key)
        unique_pairing_rules.append(rule)

print(f"Unique pairing rules after dedup: {len(unique_pairing_rules)}")

# ---------------------------------------------------------------------------
# 6. Write output files
# ---------------------------------------------------------------------------

# 1. Pairing rules
with open(OUT_DIR / "pairing_rules.json", "w", encoding="utf-8") as f:
    json.dump(unique_pairing_rules, f, indent=2, ensure_ascii=False)
print(f"Wrote {len(unique_pairing_rules)} pairing rules → data/knowledge_graph/pairing_rules.json")

# 2. Material properties
with open(OUT_DIR / "material_properties.json", "w", encoding="utf-8") as f:
    json.dump(all_materials, f, indent=2, ensure_ascii=False)
print(f"Wrote {len(all_materials)} materials → data/knowledge_graph/material_properties.json")

# 3. Synergy matrix
with open(OUT_DIR / "synergy_matrix.json", "w", encoding="utf-8") as f:
    json.dump(all_synergy_rules, f, indent=2, ensure_ascii=False)
print(f"Wrote {len(all_synergy_rules)} synergy rules → data/knowledge_graph/synergy_matrix.json")

# 4. Theory rules
with open(OUT_DIR / "theory_rules.json", "w", encoding="utf-8") as f:
    json.dump(theory_rules, f, indent=2, ensure_ascii=False)
print(f"Wrote theory rules → data/knowledge_graph/theory_rules.json")

print("\n✅ Phase 1 knowledge graph extraction complete!")
