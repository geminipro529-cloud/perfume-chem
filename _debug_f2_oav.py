"""Debug F2 OAV — per-material breakdown."""
import json
from engine.odor_thresholds import ODT_DATA
from engine.data_spine.loader import load_registry
from engine.thermo.trajectory import evaporate

REGISTRY = load_registry()

# Check recipe
src = json.loads(open("_F2_30mL_recipe.json").read())
rows = src["rows"]
total_ul = sum(r["uL"] for r in rows)

recipe = {}
for r in rows:
    recipe[r["mat"]] = r["uL"] * 100.0 / total_ul

# Build tables
mw_t, vp_t, odt_t = {}, {}, {}
for m in recipe:
    m_key = m.casefold()
    rec = REGISTRY.get(m)
    mw_t[m] = rec.mw_g_mol if rec else 200.0
    vp_t[m] = rec.vp_25c_pa if rec else 1.0
    odt_ppm = 0.05
    if m_key in ODT_DATA:
        odt_ppm = ODT_DATA[m_key]["odt_air"] / 1000.0
    odt_t[m] = max(odt_ppm, 1e-6)

frames = evaporate(recipe, duration_s=14400.0, n_steps=6,
                   mw_table=mw_t, vp_table=vp_t)

FAMILY = {
    "Bergamot FCF oil Sicilian": "citrus",
    "Petitgrain EO": "citrus",
    "Cedrat FCF oil Sicilian": "citrus",
    "Galbanum Resinoid": "green",
    "cis-3-Hexenol": "green",
    "Aldehyde C12 MNA": "aldehydic",
    "Triplal": "green_aldehydic",
    "Ethyl 2-Methylbutyrate": "fruity",
    "Hedione HC": "radiance", "Hedione": "radiance",
    "Amyl Cinnamic Aldehyde (ACA)": "jasmine",
    "Benzyl Acetate": "jasmine",
    "p-Cresyl Methyl Ether (PCME)": "jasmine",
    "Cis Jasmone": "jasmine",
    "Damascol": "rose", "Phenethyl Alcohol (PEA)": "rose",
    "Geraniol": "rose", "Alpha Damascone": "rose",
    "Mayol": "muguet", "Bourgeonal": "muguet",
    "Ylang Comoros Complete EO": "ylang",
    "Iso E Super": "wood", "Patchouli EO": "wood",
    "Vetiver EO": "wood", "Cedarwood oil Virginia": "wood",
    "Ambrofix": "amber", "Cashmeran": "amber",
    "Labdanum Absolute": "amber_resin",
    "Evernyl": "moss",
    "Galaxolide": "musk", "Ethylene Brassylate": "musk",
    "Ambrettolide": "musk", "Habanolide": "musk",
    "Coumarin": "coumarin", "Ebanol": "sandalwood",
    "Benzyl Salicylate": "cushion", "Hexyl Salicylate": "cushion",
}

for tgt_sec, label in [(60.0, "TOP (60s)"), (1800.0, "HEART (30min)"), (14400.0, "BASE (4h)")]:
    frame = min(frames, key=lambda f: abs(f.t_seconds - tgt_sec))
    oavs = []
    fam_sums = {}
    for n, c in frame.headspace.items():
        oav = c.vapor_ppm / max(odt_t.get(n, 0.05), 1e-6)
        oavs.append((n, oav, c.vapor_ppm, odt_t.get(n, 0.05)))
        fam = FAMILY.get(n, "default")
        fam_sums[fam] = fam_sums.get(fam, 0.0) + oav
    oavs.sort(key=lambda x: -x[1])
    print(f"\n=== {label} ===")
    for n, oav, vppm, odt in oavs[:12]:
        fam = FAMILY.get(n, "?")
        print(f"  [{fam:16s}] {n:35s} OAV={oav:8.1f}  vapor={vppm:.6f}ppm  ODT={odt:.6f}ppm")
    print(f"  --- Family sums ---")
    for f, s in sorted(fam_sums.items(), key=lambda kv: -kv[1]):
        print(f"    {f}: {s:.1f}")
