#!/usr/bin/env python3
"""Merge agent-discovered pairing rules into discovered JSON file."""

import json
from pathlib import Path

TARGET = (
    Path(__file__).resolve().parent.parent
    / "data/knowledge_graph/pairing_rules_discovered.json"
)

# Load existing
existing = json.loads(TARGET.read_text(encoding="utf-8"))

# New rules from all 5 agents (sampled from full output)
new_rules = [
    # ── Agent: Citrus-Top (33 discovered) ──
    {
        "material_a": "Bergamot FCF",
        "material_b": "Lavender EO (BONTAUX SAS)",
        "type": "synergy",
        "effect": "Classic cologne accord — shared linalool/linalyl acetate terpenoid backbone. Bergamot's citrus sparkle (VP~40 Pa) lifts lavender's floral-herbaceous heart (VP~3.5 Pa). 2:1 to 3:1 ratio.",
        "source": "agent_citrus_top_2026-05-31",
        "axis": "sillage",
    },
    {
        "material_a": "Dynascone (10%)",
        "material_b": "Triplal",
        "type": "rejection",
        "effect": "Two extreme green powerhouses with clashing textures: Dynascone's galbanum-ozone bomb vs Triplal's watery-cyclamen. Use ONE, never both.",
        "source": "agent_citrus_top_2026-05-31",
        "axis": "rejection",
    },
    {
        "material_a": "Dihydromyrcenol",
        "material_b": "Calone",
        "type": "synergy",
        "effect": "Classic aquatic fresh: DHM's high-VP projection (VP~21 Pa) carries Calone's ultra-low-ODT marine note (VP~0.05 Pa). Defined 1990s aquatic revolution (Cool Water). 100:1 to 500:1 ratio.",
        "source": "agent_citrus_top_2026-05-31",
        "axis": "sillage",
    },
    {
        "material_a": "Galbanum Resinoid (10%)",
        "material_b": "Dynascone (10%)",
        "type": "synergy",
        "effect": "Natural galbanum bitterness (VP~0.1 Pa) + synthetic galbanum projection (VP~3 Pa). Dynascone acts as 'green projector' lifting galbanum's deep resinous character. Classic green-chypre (Vent Vert).",
        "source": "agent_citrus_top_2026-05-31",
        "axis": "depth",
    },
    {
        "material_a": "Geosmin (0.1% in TEC)",
        "material_b": "Dynascone (10%)",
        "type": "synergy",
        "effect": "Petrichor accord: Geosmin's rain-on-earth (ODT~6 ppt, VP~0.01 Pa) + Dynascone's ozonic-rain lift. Dynascone's 300x higher VP carries geosmin's earth upward. Both at extreme micro-dose.",
        "source": "agent_citrus_top_2026-05-31",
        "axis": "synergy",
    },
    {
        "material_a": "Methyl Pamplemousse (10%)",
        "material_b": "Grapefruit FCF",
        "type": "synergy",
        "effect": "Natural grapefruit body + synthetic grapefruit-rhubarb amplification. Methyl Pamplemousse's sulfur-rhubarb amplifies grapefruit's nootkatone, yielding 3x diffusion and 10x persistence.",
        "source": "agent_citrus_top_2026-05-31",
        "axis": "sillage",
    },
    {
        "material_a": "Scentenal (1%)",
        "material_b": "Floralozone (10%)",
        "type": "pairing",
        "effect": "Complete ozone accord: Scentenal's metallic-green sharpness (ODT 0.53 ppb) + Floralozone's softer floral-ozone body. Near-identical ODT (~1 ppb) enables precise balance.",
        "source": "agent_citrus_top_2026-05-31",
        "axis": "sillage",
    },
    {
        "material_a": "Blood Orange oil Sicilian",
        "material_b": "Red Mandarin EO",
        "type": "synergy",
        "effect": "Unified warm red citrus: Blood orange's juicy-tart + Red Mandarin's sweet-tangerine. Shared VP (~40 Pa) co-evaporates. Richer than standard orange — 'blood orange sunset' for gourmand-citrus openings.",
        "source": "agent_citrus_top_2026-05-31",
        "axis": "hedonic",
    },
    # ── Agent: Floral-Heart (~40 discovered) ──
    {
        "material_a": "Phenethyl Alcohol",
        "material_b": "Geraniol",
        "type": "synergy",
        "effect": "Classic rose accord backbone — PEA honeyed volume (VP 0.08 Pa) + Geraniol bright rosy character (VP 1.6 Pa). PEA provides 40% of rose chord mass. Synergy Ref #11.",
        "source": "agent_floral_heart_2026-05-31",
        "axis": "hedonic",
    },
    {
        "material_a": "Rose Oxide",
        "material_b": "Damascone Beta (10%)",
        "type": "synergy",
        "effect": "Rose-sparkle: Rose Oxide metallic-lychee (VP~3 Pa) + Damascone Beta fruity-plum (VP~0.5 Pa). Rose Oxide at trace (<0.1% active) transforms flat rose into living flower. Synergy Ref #11.",
        "source": "agent_floral_heart_2026-05-31",
        "axis": "hedonic",
    },
    {
        "material_a": "Hydroxycitronellal",
        "material_b": "Bourgeonal",
        "type": "synergy",
        "effect": "Classic muguet core: HCA's sweet-lily freshness (VP 0.005 Pa) + Bourgeonal's aldehydic-cosmetic muguet. Add Mayol for the full post-Lyral triad.",
        "source": "agent_floral_heart_2026-05-31",
        "axis": "complexity",
    },
    {
        "material_a": "Farnesol",
        "material_b": "Hedione HC",
        "type": "synergy",
        "effect": "Lily-neroli depth fixative: Farnesol's sesquiterpene alcohol (VP 0.08 Pa, lowest-VP floral) + jasmonate radiance. Documented: 'synergizes with Hedione for neroli-lily depth'.",
        "source": "agent_floral_heart_2026-05-31",
        "axis": "longevity",
    },
    {
        "material_a": "Cis Jasmone",
        "material_b": "Dihydrojasmone",
        "type": "synergy",
        "effect": "Jasmine body duo: Cis Jasmone green-herbal (VP~0.8 Pa) + Dihydrojasmone warm-fatty (VP~0.3 Pa). Green=jasmine top, warm=jasmine heart. Synergy Ref #12.",
        "source": "agent_floral_heart_2026-05-31",
        "axis": "complexity",
    },
    {
        "material_a": "Indole (10%)",
        "material_b": "Benzyl Acetate",
        "type": "synergy",
        "effect": "The 'is this jasmine?' test: Indole's animalic soul + Benzyl Acetate's fruity top. 100x VP differential creates temporal evolution. Without Indole, accord reads clean-generic.",
        "source": "agent_floral_heart_2026-05-31",
        "axis": "complexity",
    },
    {
        "material_a": "DBCA",
        "material_b": "Lilyreal ND",
        "type": "synergy",
        "effect": "Cosmetic plastic floral: DBCA gardenia-rose + Lilyreal clean muguet. Creates the luxury face-cream white floral signature. Synergy Ref #8.",
        "source": "agent_floral_heart_2026-05-31",
        "axis": "texture",
    },
    {
        "material_a": "Aurantiol",
        "material_b": "Oranger Crystals (10% in DPG)",
        "type": "synergy",
        "effect": "Orange blossom Schiff base + neroli crystalline. Aurantiol's slow-release warmth + Oranger's bright grape-neroli top = 6h+ orange blossom persistence.",
        "source": "agent_floral_heart_2026-05-31",
        "axis": "longevity",
    },
    # ── Agent: Woody-Base (15 discovered) ──
    {
        "material_a": "Norlimbanol Dextro",
        "material_b": "Vetiver EO (India)",
        "type": "synergy",
        "effect": "Bone-dry woody skeleton + rooty-smoky anchor. Both ultra-low VP (0.001 vs 0.003 Pa). The skeleton+flesh ~1.2x perceived OAV amplification. Both >24h skin tenacity.",
        "source": "agent_woody_base_2026-05-31",
        "axis": "depth",
    },
    {
        "material_a": "Amberwood F",
        "material_b": "Azarbre",
        "type": "synergy",
        "effect": "Complete temporal amber spectrum (4300x VP gap): Azarbre's radiant cedar-amber (VP 4.3 Pa) blooms opening-to-heart; Amberwood F's transparent anchor (VP 0.001 Pa). ~1.3x perceived warmth amplification.",
        "source": "agent_woody_base_2026-05-31",
        "axis": "texture",
    },
    {
        "material_a": "Ebanol",
        "material_b": "Vetival",
        "type": "synergy",
        "effect": "Suede sandalwood: Ebanol creamy-milky (VP 0.89 Pa) + Vetival suede-vetiver dryness (VP 6.53 Pa). Textural polarity = ~1.25x richness amplification. Le Labo Santal 33 direction.",
        "source": "agent_woody_base_2026-05-31",
        "axis": "texture",
    },
    {
        "material_a": "Cedramber",
        "material_b": "Azarbre",
        "type": "pairing",
        "effect": "Temporal cedar-amber arc: Cedramber's veiled persistence (VP 0.35 Pa) + Azarbre's radiant opening (VP 4.3 Pa). Complete cedar-amber from first spray to final drydown.",
        "source": "agent_woody_base_2026-05-31",
        "axis": "complexity",
    },
    {
        "material_a": "Vetikon",
        "material_b": "Azarbre",
        "type": "pairing",
        "effect": "Bright warm-woody: Both near-identical VP (4.16 vs 4.3 Pa) — linear co-evaporation. Vetikon's green-fresh vetiver + Azarbre's warm cedar-amber = woody 'top notes'.",
        "source": "agent_woody_base_2026-05-31",
        "axis": "sillage",
    },
    # ── Agent: Musk-Fixative (54 discovered) ──
    {
        "material_a": "Musk Ketone",
        "material_b": "Romandolide",
        "type": "pairing",
        "effect": "Vintage powder meets modern projection: nitro musk powdery-animalic (VP~0.0003 Pa) + alicyclic diffusive clean (VP~0.009 Pa). Neither alone achieves both intimacy and radius.",
        "source": "agent_musk_fixative_2026-05-31",
        "axis": "depth+projection",
    },
    {
        "material_a": "Romandolide",
        "material_b": "Exaltolide",
        "type": "pairing",
        "effect": "Complete macrocyclic-alicyclic coverage: Romandolide projection (VP~0.009 Pa) + Exaltolide warm-creamy depth (VP~0.005 Pa). Full architecture from sillage to skin.",
        "source": "agent_musk_fixative_2026-05-31",
        "axis": "depth+projection",
    },
    {
        "material_a": "Benzyl Salicylate",
        "material_b": "Musk Ketone",
        "type": "pairing",
        "effect": "Cosmetic-powder fixative-musk base: Both share 'luxury cosmetics' texture. Vintage powder in full force — Benzyl Sal's waxy body + MK's nitro warmth.",
        "source": "agent_musk_fixative_2026-05-31",
        "axis": "character-echo",
    },
    {
        "material_a": "Ethyl Vanillin",
        "material_b": "Coumarin (20%)",
        "type": "synergy",
        "effect": "Powerful vanilla (~3x vanillin) + hay-tonka. Cross-modal olfactory-gustatory fusion: reads as 'vanilla crème brûlée' not 'vanilla extract'. Modern gourmand core.",
        "source": "agent_musk_fixative_2026-05-31",
        "axis": "hedonic",
    },
    {
        "material_a": "Evernyl",
        "material_b": "Coumarin (20%)",
        "type": "pairing",
        "effect": "Moss + hay — the chypre-fougère drydown bridge. Evernyl's oakmoss character sweetened by coumarin's tonka. Modern chypre without oakmoss allergens.",
        "source": "agent_musk_fixative_2026-05-31",
        "axis": "depth",
    },
    {
        "material_a": "Tobacco Absolute (10% in DPG)",
        "material_b": "Coumarin (20%)",
        "type": "pairing",
        "effect": "Tobacco + hay — the aromatic pipe-tobacco accord. Coumarin's tonka sweetness counters tobacco's bitter-leaf. Classic masculine tobacco-tinted fougère drydown.",
        "source": "agent_musk_fixative_2026-05-31",
        "axis": "hedonic",
    },
    # ── Agent: Spice-Aromatic (60 discovered) ──
    {
        "material_a": "Cardamom EO",
        "material_b": "Black Pepper EO",
        "type": "synergy",
        "effect": "Classic spice chord: cardamom's cineolic-cool freshness + black pepper's warm pinenic sparkle. 50x VP gap = temporal layering. Declaration aromatic masculine backbone.",
        "source": "agent_spice_aromatic_2026-05-31",
        "axis": "hedonic",
    },
    {
        "material_a": "Eugenol",
        "material_b": "Cinnamaldehyde",
        "type": "synergy",
        "effect": "Oriental spice bomb: sweet-clove phenolic + hot-cinnamon aldehyde. Both phenylpropanoids share biosynthetic origin. Perceived warmth exceeds either alone.",
        "source": "agent_spice_aromatic_2026-05-31",
        "axis": "hedonic",
    },
    {
        "material_a": "Clary Sage EO",
        "material_b": "Lavender EO (BONTAUX SAS)",
        "type": "synergy",
        "effect": "The fougère heart: shared linalool/linalyl acetate. Clary sage's green-coumarinic depth + lavender's floral-aromatic lift. Complete aromatic-fougère architecture.",
        "source": "agent_spice_aromatic_2026-05-31",
        "axis": "hedonic",
    },
    {
        "material_a": "Black Pepper EO",
        "material_b": "Iso E Super",
        "type": "synergy",
        "effect": "Pepper's terpenic sparkle rides Iso E's diffusive carrier 3-5x beyond natural pepper VP limits. Pepper gives Iso E identifiable character, preventing anosmia trap.",
        "source": "agent_spice_aromatic_2026-05-31",
        "axis": "sillage",
    },
    {
        "material_a": "Patchouli EO",
        "material_b": "Vanillin (10%)",
        "type": "pairing",
        "effect": "Earthy-gourmand bridge: patchouli's camphoraceous complexity + vanillin's creamy sweetness. Classic Angel/Borneo 1834 bohemian-luxe fusion.",
        "source": "agent_spice_aromatic_2026-05-31",
        "axis": "hedonic",
    },
    {
        "material_a": "Triplal",
        "material_b": "Dynascone (10%)",
        "type": "rejection",
        "effect": "REJECT: Two extreme green powerhouses (VP~8 and ~1 Pa) fight for same receptor space with clashing textures. Never pair; choose ONE green high-impact material.",
        "source": "agent_spice_aromatic_2026-05-31",
        "axis": "rejection",
    },
    {
        "material_a": "Ethyl Safranate",
        "material_b": "Rhodinol ex Citronella",
        "type": "synergy",
        "effect": "Saffron-rose luxury direction: ethyl safranate's spicy-leathery saffron warmed by rhodinol's rose-citronellol richness. Oud-adjacent niche luxury.",
        "source": "agent_spice_aromatic_2026-05-31",
        "axis": "hedonic",
    },
    {
        "material_a": "Juniper Berry EO",
        "material_b": "Cardamom EO",
        "type": "pairing",
        "effect": "Gin-spice: juniper's coniferous-terpenic complexity + cardamom's cineolic aromatic freshness. Complex, transparent aromatic top with shared terpene chemistry.",
        "source": "agent_spice_aromatic_2026-05-31",
        "axis": "sillage",
    },
]

# Append and save
existing.extend(new_rules)
TARGET.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Appended {len(new_rules)} rules. Total: {len(existing)}")
