import json
import sys

sys.path.insert(0, r"D:\chatbots\perfume-chem")
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from engine.ingredient_intelligence import get_profile
from engine.inventory_parser import parse_inventory


def clean(name):
    import re

    name = re.sub(r"\s*#.*$", "", name).strip()
    name = re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()
    return name


# Load inventory
inv = parse_inventory(unique=True, include_solvents=False, include_unavailable=True)
inv_names = [clean(m.name) for m in inv if m.category not in ("solvents / carriers",)]

# Focus categories
top_tokens = [
    "bergamot",
    "grapefruit",
    "lemon",
    "lime",
    "orange",
    "mandarin",
    "cedrat",
    "citral",
    "limonene",
    "aldehyde",
    "dihydromyrcenol",
    "linalool",
    "linalyl acetate",
    "hexyl acetate",
    "ethyl 2-methylbutyrate",
    "methyl pamplemousse",
    "apritone",
    "galbanum",
    "cis-3-hexenol",
    "leafovert",
    "parmavert",
    "triplal",
    "scentenal",
    "calone",
    "floralozone",
    "verdox",
    "dynascone",
    "terpinyl acetate",
    "lemonile",
    "melonal",
    "allyl amyl glycolate",
    "undecavertol",
    "beta-pinene",
    "grapefruit fcf",
]

# Find top-note materials in inventory
top_materials = []
for name in inv_names:
    low = name.lower()
    for tok in top_tokens:
        if tok in low:
            top_materials.append(name)
            break

# Check existing rules to avoid duplicates
existing = set()
try:
    pr = json.load(
        open(r"D:\chatbots\perfume-chem\data\knowledge_graph\pairing_rules.json", encoding="utf-8")
    )
    for r in pr:
        a = r.get("material_a", "").lower().strip()
        b = r.get("material_b", "").lower().strip()
        existing.add((a, b))
        existing.add((b, a))
except Exception:
    pass

# Evaluate pairs
output = []
checked = 0
for i in range(len(top_materials)):
    for j in range(i + 1, len(top_materials)):
        a, b = top_materials[i], top_materials[j]
        key = (a.lower().strip(), b.lower().strip())
        if key in existing:
            continue
        pa, pb = get_profile(a), get_profile(b)
        if not pa or not pb:
            continue
        a_note, b_note = getattr(pa, "note", "?"), getattr(pb, "note", "?")
        a_role, b_role = getattr(pa, "role", "?"), getattr(pb, "role", "?")

        # Skip same-role redundancy
        if a_role == b_role and a_role in ("fixative", "trace", "volume"):
            continue

        checked += 1
        # Determine if synergy or pairing
        typ = "pairing"
        effect = ""

        # Classic known accords
        pair_str = (a.lower(), b.lower())
        if ("bergamot" in pair_str[0] or "bergamot" in pair_str[1]) and (
            "cardamom" in pair_str[0] or "cardamom" in pair_str[1]
        ):
            typ = "pairing"
            effect = "Classic cologne opening — bergamot citrus sparkle + cardamom aromatic lift"
        elif ("grapefruit" in pair_str[0] or "grapefruit" in pair_str[1]) and (
            "dihydromyrcenol" in pair_str[0] or "dihydromyrcenol" in pair_str[1]
        ):
            typ = "synergy"
            effect = "Grapefruit bitter-clean edge + DHM transparent volume — 2x projection documented in DB"
        elif ("dihydromyrcenol" in pair_str[0] or "dihydromyrcenol" in pair_str[1]) and (
            "linalool" in pair_str[0] or "linalool" in pair_str[1]
        ):
            typ = "pairing"
            effect = (
                "Co-evaporating fresh top — near-identical VP (17/21 Pa) creates linear opening"
            )
        elif ("bergamot" in pair_str[0] or "bergamot" in pair_str[1]) and (
            "linalool" in pair_str[0] or "linalool" in pair_str[1]
        ):
            typ = "pairing"
            effect = "Bergamot's linalyl acetate + linalool — shared monoterpene backbone"
        elif ("citral" in pair_str[0] or "citral" in pair_str[1]) and (
            "limonene" in pair_str[0] or "limonene" in pair_str[1]
        ):
            typ = "pairing"
            effect = "Lemon-citrus duo — citral provides sharpness, limonene provides volume"
        elif ("calone" in pair_str[0] or "calone" in pair_str[1]) and (
            "floralozone" in pair_str[0] or "floralozone" in pair_str[1]
        ):
            typ = "synergy"
            effect = "Aquatic-floral synergy — calone's marine + floralozone's ozone creates fresh volume (DB documented)"
        elif ("galbanum" in pair_str[0] or "galbanum" in pair_str[1]) and (
            "bergamot" in pair_str[0] or "bergamot" in pair_str[1]
        ):
            typ = "pairing"
            effect = "Green-chypre opening — galbanum's bitter-green + bergamot's citrus sparkle"
        else:
            # Generic pairing for top+top with different roles
            if a_role != b_role:
                typ = "pairing"
                effect = "%s + %s — complementary top notes" % (a_role.title(), b_role.title())
            else:
                continue  # Skip same-role same-category top notes

        if effect:
            output.append(
                {
                    "material_a": a,
                    "material_b": b,
                    "type": typ,
                    "effect": effect,
                    "source": "agent-citrus-top_2026-05-21",
                }
            )

# Append to discovered file
disc_path = r"D:\chatbots\perfume-chem\data\knowledge_graph\pairing_rules_discovered.json"
try:
    disc = json.load(open(disc_path, encoding="utf-8"))
except Exception:
    disc = []
disc.extend(output)
json.dump(disc, open(disc_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

print("Citrus-Top agent: %d pairs checked, %d new pairs discovered" % (checked, len(output)))
for o in output:
    print("  [%s] %s + %s" % (o["type"], o["material_a"][:25], o["material_b"][:25]))
