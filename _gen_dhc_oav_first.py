#!/usr/bin/env python3
"""Generate DHC OAV-first formula files — Demachy mass-market targets."""

import sys
sys.path.insert(0, '.')
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name

PPM_FACTOR = 20.0  # 1e6 / 50,000

# --- Material metadata ---
def get_mat(name):
    norm = normalize_name(name)
    p = get_profile(name)
    vp = p.vp if p and p.vp else 0.0
    odt_d = ODT_DATA.get(norm, {}) or ODT_DATA.get(name.lower(), {})
    odt_air = odt_d.get('odt_air') if odt_d else None
    odt_eth = odt_d.get('odt_eth') if odt_d else None
    return vp, odt_air, odt_eth

def oav_to_active_ul(target_oav, vp, odt_air):
    return target_oav * odt_air / vp / PPM_FACTOR

def active_ul_to_oav(active, vp, odt_air):
    ppm = active * PPM_FACTOR
    return vp * ppm / odt_air

def active_ul_to_liquid_oav(active, odt_eth):
    ppm = active * PPM_FACTOR
    return ppm / odt_eth

def band(oav):
    if oav >= 50: return "DOMINANT"
    if oav >= 5: return "Strong"
    if oav >= 1: return "Active"
    return "Shadow"

# OAV targets per DHC
variants = {
    "I Bergamot": {
        "profile": "Bergamot — the reference. Cool, refined, classical.",
        "top": [
            ("Bergamot FCF Sicilian", "neat", 48.0, 10000),
            ("Linalyl Acetate", "neat", 13.0, 2700),
        ],
        "heart": [
            ("Hedione", "neat", 10000, 300),
            ("Petitgrain EO", "neat", 10000, 5800),
            ("Ethyl Linalool", "neat", 10000, 135),
            ("Paradisamide", "10%", 10000, 2.8),
            ("Hedione HC", "neat", 10000, 36),
        ],
        "base": [
            ("Romandolide", "neat", 10000, 1200),
            ("Iso E Super", "neat", 10000, 290),
            ("Ethylene Brassylate", "neat", 10000, 33),
            ("Ambrofix", "30%", 10000, 185),
            ("Ambrettolide", "10%", 10000, 0.5),
            ("Norlimbanol Dextro", "neat", 10000, 1.8),
            ("Vetival", "neat", 10000, 85),
        ],
    },
    "II Cedrat": {
        "profile": "Cedrat — the extreme. Cold, mineral, stark.",
        "top": [
            ("Cedrat FCF Sicilian", "neat", 52.4, 10800),
            ("Linalyl Acetate", "neat", 8.7, 1800),
        ],
        "heart": [
            ("Hedione", "neat", 10000, 260),
            ("Petitgrain EO", "neat", 10000, 5800),
            ("Ethyl Linalool", "neat", 10000, 115),
            ("Paradisamide", "10%", 10000, 2.8),
            ("Hedione HC", "neat", 10000, 36),
        ],
        "base": [
            ("Romandolide", "neat", 10000, 1200),
            ("Iso E Super", "neat", 10000, 290),
            ("Ethylene Brassylate", "neat", 10000, 33),
            ("Ambrofix", "30%", 10000, 185),
            ("Ambrettolide", "10%", 10000, 0.5),
            ("Norlimbanol Dextro", "neat", 10000, 1.8),
            ("Vetival", "neat", 10000, 85),
        ],
    },
    "III Grapefruit": {
        "profile": "Grapefruit — the crowd-pleaser. Bright, cheerful, botanical truth.",
        "top": [
            ("Grapefruit FCF", "neat", 53.7, 14000),
            ("Linalyl Acetate", "neat", 15.3, 4000),
        ],
        "heart": [
            ("Hedione", "neat", 10000, 280),
            ("Petitgrain EO", "neat", 10000, 5800),
            ("Ethyl Linalool", "neat", 10000, 155),
            ("Paradisamide", "10%", 10000, 2.8),
            ("Hedione HC", "neat", 10000, 36),
        ],
        "base": [
            ("Romandolide", "neat", 10000, 1200),
            ("Iso E Super", "neat", 10000, 290),
            ("Ethylene Brassylate", "neat", 10000, 33),
            ("Ambrofix", "30%", 10000, 185),
            ("Ambrettolide", "10%", 10000, 0.5),
            ("Norlimbanol Dextro", "neat", 10000, 1.8),
            ("Vetival", "neat", 10000, 85),
        ],
    },
    "IV Lime": {
        "profile": "Lime — the transparent one. Green, ethereal, grove-air.",
        "top": [
            ("Lime Distilled EO", "neat", 50.5, 10000),
            ("Linalyl Acetate", "neat", 9.1, 1800),
        ],
        "heart": [
            ("Hedione", "neat", 10000, 260),
            ("Petitgrain EO", "neat", 10000, 5800),
            ("Ethyl Linalool", "neat", 10000, 120),
            ("Paradisamide", "10%", 10000, 2.8),
            ("Hedione HC", "neat", 10000, 36),
        ],
        "base": [
            ("Romandolide", "neat", 10000, 1200),
            ("Iso E Super", "neat", 10000, 290),
            ("Ethylene Brassylate", "neat", 10000, 33),
            ("Ambrofix", "30%", 10000, 185),
            ("Ambrettolide", "10%", 10000, 0.5),
            ("Norlimbanol Dextro", "neat", 10000, 1.8),
            ("Vetival", "neat", 10000, 85),
        ],
    },
    "V Mandarin": {
        "profile": "Mandarin — the sunset finale. Warm, golden, luxurious.",
        "top": [
            ("Red Mandarin EO", "neat", 51.4, 11000),
            ("Linalyl Acetate", "neat", 11.2, 2400),
        ],
        "heart": [
            ("Hedione", "neat", 10000, 260),
            ("Petitgrain EO", "neat", 10000, 5800),
            ("Ethyl Linalool", "neat", 10000, 115),
            ("Paradisamide", "10%", 10000, 2.8),
            ("Hedione HC", "neat", 10000, 36),
        ],
        "base": [
            ("Romandolide", "neat", 10000, 1200),
            ("Iso E Super", "neat", 10000, 290),
            ("Ethylene Brassylate", "neat", 10000, 33),
            ("Ambrofix", "30%", 10000, 185),
            ("Ambrettolide", "10%", 10000, 0.5),
            ("Norlimbanol Dextro", "neat", 10000, 1.8),
            ("Vetival", "neat", 10000, 85),
        ],
    },
}

OUT_DIR = "formulas/oav_balanced"
fn_map = {
    "I Bergamot":   "DHC_I__Bergamot_50mL_EdP.md",
    "II Cedrat":    "DHC_II_Cedrat_50mL_EdP.md",
    "III Grapefruit": "DHC_III_Grapefruit_50mL_EdP.md",
    "IV Lime":      "DHC_IV_Lime_50mL_EdP.md",
    "V Mandarin":   "DHC_V__Mandarin_50mL_EdP.md",
}

for label, spec in variants.items():
    # Build formula rows from OAV targets
    all_rows = []
    total_active = 0
    total_raw = 0
    total_headspace_oav = 0

    for layer_name, mats in [("TOP", spec["top"]), ("HEART", spec["heart"]), ("BASE", spec["base"])]:
        for name, dil, _, target_oav in mats:
            vp, odt_a, odt_e = get_mat(name)
            active = round(oav_to_active_ul(target_oav, vp, odt_a), 1)
            total_active += active

            # Raw uL from dilution
            dil_factor = 1.0
            if "30%" in dil: dil_factor = 0.3
            elif "10%" in dil: dil_factor = 0.1
            raw = round(active / dil_factor, 1) if dil_factor else active

            # Verify OAV
            h_oav = active_ul_to_oav(active, vp, odt_a)
            l_oav = active_ul_to_liquid_oav(active, odt_e) if odt_e else None
            total_headspace_oav += h_oav

            all_rows.append({
                "num": len(all_rows) + 1,
                "name": name,
                "dilution": dil,
                "active_ul": active,
                "raw_ul": raw,
                "h_oav": round(h_oav),
                "h_band": band(h_oav),
                "l_oav": round(l_oav) if l_oav else None,
                "layer": layer_name,
                "target_oav": target_oav,
                "vp": vp,
                "odt_air": odt_a,
                "odt_eth": odt_e,
            })
            total_raw += raw

    # Layer summaries
    top_active = sum(r["active_ul"] for r in all_rows if r["layer"] == "TOP")
    heart_active = sum(r["active_ul"] for r in all_rows if r["layer"] == "HEART")
    base_active = sum(r["active_ul"] for r in all_rows if r["layer"] == "BASE")
    conc_pct = total_active / 50000 * 100
    ethanol_ml = round(50 - total_raw / 1000, 0)

    # Headspace OAV by layer
    top_h = sum(r["h_oav"] for r in all_rows if r["layer"] == "TOP")
    heart_h = sum(r["h_oav"] for r in all_rows if r["layer"] == "HEART")
    base_h = sum(r["h_oav"] for r in all_rows if r["layer"] == "BASE")
    bt_ratio = base_h / top_h if top_h else 0

    # Liquid OAV by layer
    top_l = sum(r["l_oav"] for r in all_rows if r["layer"] == "TOP" and r["l_oav"])
    heart_l = sum(r["l_oav"] for r in all_rows if r["layer"] == "HEART" and r["l_oav"])
    base_l = sum(r["l_oav"] for r in all_rows if r["layer"] == "BASE" and r["l_oav"])
    total_l = top_l + heart_l + base_l

    # Sort headspace OAV for ranked view
    ranked = sorted(all_rows, key=lambda r: r["h_oav"], reverse=True)

    # --- Build markdown ---
    md = []
    def w(s=""): md.append(s)

    w(f"# DHC {label} — 50 mL Eau de Parfum (~{conc_pct:.0f}%) — OAV-First Demachy")
    w()
    w(f"**Profile:** {spec['profile']}")
    w(f"**Method:** OAV-first design — target headspace percentages back-calculated to uL.")
    w(f"**Batch:** 50.00 mL · ~{conc_pct:.1f}% EdP · 14 materials")
    w(f"**Maceration:** 4 weeks minimum")
    w(f"**Concentrate:** {total_raw:.0f} uL raw · {total_active:.0f} uL active")
    w(f"**Ethanol 96%:** ~{50 - total_raw/1000:.0f} mL")
    w(f"**Headspace B:T:** {bt_ratio:.2f}:1  |  T:{top_h/total_headspace_oav*100:.0f}%/H:{heart_h/total_headspace_oav*100:.0f}%/B:{base_h/total_headspace_oav*100:.0f}%")
    w()
    w("## Equipment")
    w()
    w("- 1 amber glass bottle 50 mL")
    w("- 1 graduated pipette or syringe for dosing")
    w("- Ethanol 96% (perfumer's grade)")
    w()
    w("## Mixing Guide")
    w()
    w("Pipette into bottle in order. Swirl gently between layers.")
    w()
    w("| # | Material | Dilution | Raw uL | Active uL | Headspace OAV | Band |")
    w("|--:|----------|----------|-------:|----------:|-------------:|------|")

    row_num = 0
    for layer in ["TOP", "HEART", "BASE"]:
        layer_rows = [r for r in all_rows if r["layer"] == layer]
        for r in layer_rows:
            row_num += 1
            w(f"| {row_num} | {r['name']} | {r['dilution']} | {r['raw_ul']:.1f} | {r['active_ul']:.1f} | {r['h_oav']:,} | {r['h_band']} |")
        if layer != "BASE":
            w(f"| | *— {layer.lower()} break —* | | | | | |")

    w()
    w(f"Concentrate ~{total_raw:.0f} uL. Add ethanol to 50 mL line. Invert 50x gently.")
    w()
    w("## Headspace OAV Ranking (VP x ppm / ODT_air, 32C)")
    w()
    w("| # | Material | Active uL | ppm fin | VP(Pa) | ODT(ppb) | OAV | Band |")
    w("|--:|----------|----------:|--------:|-------:|---------:|----:|------|")
    for rank, r in enumerate(ranked, 1):
        star = " <-- STAR" if rank == 1 else ""
        ppm = r["active_ul"] * PPM_FACTOR
        w(f"| {rank} | {r['name']} | {r['active_ul']:.1f} | {ppm:,.0f} | {r['vp']:.3f} | {r['odt_air']:.1f} | {r['h_oav']:,} | {r['h_band']}{star} |")
    w()
    star_r = ranked[0]
    n_dom = sum(1 for r in ranked if r["h_band"] == "DOMINANT")
    n_sub = sum(1 for r in ranked if r["h_band"] == "Shadow")
    w(f"**Total headspace OAV:** {total_headspace_oav:,.0f}  |  Dominant:{n_dom}  Subliminal:{n_sub}")
    w(f"**Star:** {star_r['name']} — OAV {star_r['h_oav']:,} ({star_r['h_oav']/total_headspace_oav*100:.0f}%)")
    w()
    w("## Liquid-Phase OAV (ppm / ODT_ethanol, in-bottle)")
    w()
    w("| # | Material | Active uL | ppm | ODT(eth) | OAV | Layer |")
    w("|--:|----------|----------:|----:|---------:|----:|-------|")
    for r in all_rows:
        ppm = r["active_ul"] * PPM_FACTOR
        if r["l_oav"]:
            w(f"| {r['num']} | {r['name']} | {r['active_ul']:.1f} | {ppm:,.0f} | {r['odt_eth']:.2f} | {r['l_oav']:,} | {r['layer']} |")
    w()
    w(f"| **TOTAL** | | | | | | |")
    w(f"| **TOP** | | | | | **{top_l:,}** | **{top_l/total_l*100:.0f}%** |")
    w(f"| **HEART** | | | | | **{heart_l:,}** | **{heart_l/total_l*100:.0f}%** |")
    w(f"| **BASE** | | | | | **{base_l:,}** | **{base_l/total_l*100:.0f}%** |")
    w(f"| **B:T** | | | | | **{base_l/top_l:.2f}:1** | |")
    w()
    w("## OAV-First Design Notes")
    w()
    w(f"- **Citrus star target:** {star_r['target_oav']:,} headspace OAV ({star_r['target_oav']/total_headspace_oav*100:.0f}% allocation)")
    w(f"- **Petitgrain always #2** at OAV 5,800 — structural citrus bridge, consistent across all DHCs")
    w(f"- **Linalyl Acetate** dosed per-citrus: more for soft/juicy citrus (Grapefruit 4,000), less for already-sharp citrus (Cedrat 1,800)")
    w(f"- **Ambrofix at OAV 185** — boosted vs prior DHCs. The Demachy crystalline-mineral signature")
    w(f"- **Romandolide at OAV 1,200** constant — clean macrocyclic projection, no variation needed")
    w(f"- **Hedione at OAV 260-300** — radiance amplifier, transparent volume without weight")
    w(f"- **No habanolide, no galaxolide** — Romandolide + EB + trace Ambrettolide = transparent musk architecture")
    w()
    w("## Allergen Declarations (EU 26)")
    w()
    w("Linalool (from citrus EO, Linalyl Acetate, Petitgrain), Geraniol (from citrus EO, Petitgrain)")

    fname = f"{OUT_DIR}/{fn_map[label]}"
    with open(fname, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print(f"Wrote {fname}")

print("\nDone. All 5 DHCs regenerated with OAV-first dosing.")
