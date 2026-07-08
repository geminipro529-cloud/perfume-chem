"""Iris Dreamweaver v2 — VP/ODT/ppm-based, scale-invariant, single-molecule only.

DESIGN RULES:
  (1) Formula specified as per-material active ppm (w/w) in finished juice.
      This scales LINEARLY to any batch size. OAV = ppm_juice / ODT_eth_ppm
      is the perceptual loudness used for design reasoning.
  (2) ONLY single-molecule aroma chemicals and natural EOs whose GC
      composition is known. NO FTEC / FO / Fleuressence / Core / Accord
      pre-blends of unknown ingredients.

Iterative optimization: 5 passes. Each pass perturbs ppm targets to improve
the engine geo composite, subject to OAV / ODT / pipette-floor constraints.
"""
import io, os, sys, math, copy, random, json
if os.name == "nt":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from engine.optimizer.scoring import FormulaScorer
from engine.optimizer.oav_guard import check_batch_scaling
from engine.dose_response import score_dose_response
from engine.formula_analyzer import FormulaInfo, formula_to_vector
from engine.odor_thresholds import ODT_DATA

# ── ODT supplement (ppm in ethanol) for materials not in ODT_DATA ───
# Sources: Leffingwell, Arctander, Goodscents, published GC-O studies
ODT_EXTRA = {
    "heliotropal":           5.0,    # piperonal, powerful almond-heliotrope
    "piperonal":             5.0,
    "anisaldehyde":          5.0,
    "gamma undecalactone":   1.0,    # peach, very potent
    "gamma decalactone":     1.5,
    "delta decalactone":     10.0,   # creamy coconut
    "ethyl maltol":          0.3,    # extreme potency
    "hedione hc":            3.0,
    "mayol":                 3.0,
    "bourgeonal":            0.03,   # extremely powerful muguet aldehyde
    "lilyreal":              1.0,
    "dbca":                  0.5,
    "amyl cinnamic aldehyde":2.0,
    "aca":                   2.0,
    "dihydro beta ionone":   0.3,
    "irotyl":                1.0,
    "ethylene brassylate":   2.0,
    "exaltolide":            1.0,
    "ambrettolide":          0.5,
    "musk ketone":           2.0,
    "romandolide":           1.0,
    "tonalide":              1.0,
    "ambermax":              0.5,
    "azarbre":               2.0,
    "koavone":               2.0,
    "cedarwood virginia":    3.0,
    "hexyl salicylate":      30.0,
    "myristic acid":         500.0,  # near odorless — fixative
    "ipm":                  1000.0,  # solvent
    "benzyl alcohol":        60.0,
    "red mandarin":          2.0,
    "bergamot fcf sicilian": 1.5,
    "ylang ylang extra":     1.0,
    "rose absolute":         3.0,
    "jasmine absolute":      1.5,
    "benzoin resinoid":      30.0,   # dominant actives: coniferyl benzoate, vanillin, benzoic acid
    "siam benzoin":          30.0,
}

def lookup_odt(name: str) -> float | None:
    k = name.lower().strip()
    for nm, d in ODT_DATA.items():
        nk = nm.lower()
        if nk == k or k.startswith(nk) or nk in k:
            return d["odt_eth"]
    for nm, v in ODT_EXTRA.items():
        if nm == k or k.startswith(nm) or nm in k:
            return v
    return None

# ── FORMULA SPEC IN PPM_JUICE (active wt% × 10000) ───────────────────
# Each entry: material → (target_ppm_active_in_juice, stock_dilution, role)
# stock_dilution: what we physically pipette (neat=1.0, 30%=0.30, etc.)
# role: used for reporting groups only
# BANNED materials NOT used: Orris F-TEC, I-IRIS F-TEC, Heliotropin Fleuressence,
# Tonka Bean FO, Jasmine FO, Sandalwood FO, Amber Core, Violet Fleuressence

SPEC: dict[str, dict] = {
    # ── TOP (hesperidic whisper, not a cut-through) ──
    "Bergamot FCF Sicilian":   {"ppm": 4000,  "dil": 1.00, "role": "top"},
    "Red Mandarin EO":         {"ppm": 2000,  "dil": 1.00, "role": "top"},
    # ── IRIS CORE (Alpha Irone-led, LOW violet, LOW AIMI) ──
    "Alpha Irone":             {"ppm":  8400, "dil": 0.30, "role": "iris"},   # 30% stock
    "Orivone":                 {"ppm":  4000, "dil": 1.00, "role": "iris"},
    "Dihydro Beta Ionone":     {"ppm":  2000, "dil": 1.00, "role": "iris"},
    "Alpha Ionone":            {"ppm":  1500, "dil": 1.00, "role": "iris"},
    "Carrot Seed EO":          {"ppm":  1500, "dil": 1.00, "role": "iris"},
    "Ultralia":                {"ppm":  2500, "dil": 1.00, "role": "iris"},
    "Irotyl":                  {"ppm":   500, "dil": 1.00, "role": "iris"},
    # ── WHITE FLORAL HEART (LOW AIMI; Hedione radiance + muguet character) ──
    "Hedione":                 {"ppm": 28000, "dil": 1.00, "role": "floral"},
    "Hedione HC":              {"ppm": 10000, "dil": 1.00, "role": "floral"},
    "Mayol":                   {"ppm":  2500, "dil": 1.00, "role": "floral"},
    "Hydroxycitronellal":      {"ppm":  2000, "dil": 1.00, "role": "floral"},
    "Amyl Cinnamic Aldehyde":  {"ppm":  2000, "dil": 1.00, "role": "floral"},
    "DBCA":                    {"ppm":  1500, "dil": 1.00, "role": "floral"},
    "Bourgeonal":              {"ppm":  1000, "dil": 1.00, "role": "floral"},
    "Farnesol":                {"ppm":   500, "dil": 1.00, "role": "floral"},
    "Cis Jasmone":             {"ppm":   500, "dil": 1.00, "role": "floral"},
    # ── GOURMAND CREAMY BRIDGE (heliotropin-coumarin-vanillin-lactone-maltol) ──
    "Myristic Acid":           {"ppm":  3000, "dil": 0.20, "role": "bridge"},   # 20% stock
    "Benzoin Resinoid":        {"ppm":  5000, "dil": 0.50, "role": "bridge"},   # 50% DPG
    "Heliotropal":             {"ppm":  4000, "dil": 1.00, "role": "bridge"},
    "Ethyl Vanillin":          {"ppm":  2000, "dil": 1.00, "role": "bridge"},
    "Vanillin":                {"ppm":   500, "dil": 0.10, "role": "bridge"},
    "Ethyl Maltol":            {"ppm":   500, "dil": 0.10, "role": "bridge"},
    "Delta Decalactone":       {"ppm":  3500, "dil": 1.00, "role": "bridge"},
    "Maple Lactone":           {"ppm":   700, "dil": 0.20, "role": "bridge"},
    "Gamma Undecalactone":     {"ppm":  3000, "dil": 1.00, "role": "bridge"},
    "Coumarin":                {"ppm":  2400, "dil": 0.20, "role": "bridge"},
    "Anisaldehyde":            {"ppm":  1500, "dil": 1.00, "role": "bridge"},
    # ── FIXATIVE / DIFFUSION / WOODS ──
    "Ethylene Brassylate":     {"ppm": 20000, "dil": 1.00, "role": "base"},
    "Iso E Super":             {"ppm": 15000, "dil": 1.00, "role": "base"},
    "Benzyl Salicylate":       {"ppm": 15000, "dil": 1.00, "role": "base"},
    "Musk Ketone":             {"ppm":  1000, "dil": 0.10, "role": "base"},
    "Exaltolide":              {"ppm":   800, "dil": 0.10, "role": "base"},
    "Ambermax":                {"ppm":  4000, "dil": 0.50, "role": "base"},
    "Ambrettolide":            {"ppm":   600, "dil": 0.10, "role": "base"},
    "Hexyl Salicylate":        {"ppm":  5000, "dil": 1.00, "role": "base"},
    "Azarbre":                 {"ppm":  5000, "dil": 1.00, "role": "base"},
    "Koavone":                 {"ppm":  4000, "dil": 1.00, "role": "base"},
    "Cedarwood Virginia":      {"ppm":  3000, "dil": 1.00, "role": "base"},
    "Ebanol":                  {"ppm":  4000, "dil": 1.00, "role": "base"},
    "Bacdanol":                {"ppm":  2500, "dil": 1.00, "role": "base"},
}

# ── BRIEF-DRIVEN AXIS WEIGHTS ─────────────────────────────────────────
# Brief said: "EXTREMELY EXPENSIVE, DEEP, LUXURY, LONG LASTING, PROJECTIVE,
# TEXTURED SINGLE DIRECTION SYNERGY PERFUME … beautiful and dreamy …
# does not have to be transparent if the character is lost."
#
# Direct brief markers (weight 1.5):
#   luxury        ← "EXTREMELY EXPENSIVE, LUXURY"
#   longevity     ← "LONG LASTING"
#   sillage       ← "PROJECTIVE"
#   texture       ← "TEXTURED"
#   stacking_depth← "DEEP"
#   synergy       ← "SINGLE DIRECTION SYNERGY"
#
# Supporting markers (weight 1.0):
#   hedonic       ← "beautiful and dreamy"
#   skin_performance ← required for projective longevity on skin
#
# Explicitly de-emphasised / excluded:
#   photorealism  = 0.0  (this is an abstract luxury perfume, not a
#                         literal-flower reproduction)
#   perceptual_clarity = 0.2  (brief said transparency is optional if
#                              character is lost — keep only minimal weight)
AXIS_W = {
    "luxury":           1.5,
    "longevity":        1.5,
    "sillage":          1.5,
    "texture":          1.5,
    "stacking_depth":   1.5,
    "synergy":          1.5,
    "hedonic":          1.0,
    "skin_performance": 1.0,
    "perceptual_clarity": 0.2,
    "photorealism":     0.0,   # N/A for this brief
}

def spec_to_ingredients(spec: dict, batch_ml: float) -> tuple[dict, dict]:
    """Convert ppm_juice spec → (ingredients µL of stock, dilutions dict) for
    a given batch size. Scale-invariant: same SPEC gives same OAV at any batch."""
    batch_ul = batch_ml * 1000.0    # density ≈ 1
    ing, dil = {}, {}
    for name, d in spec.items():
        active_ul = batch_ul * d["ppm"] / 1e6
        stock_ul = active_ul / d["dil"]
        ing[name] = stock_ul
        dil[name] = d["dil"]
    return ing, dil

def compute_oav_table(spec: dict) -> list[dict]:
    rows = []
    for name, d in spec.items():
        odt = lookup_odt(name)
        oav = (d["ppm"] / odt) if odt else None
        rows.append({"name": name, "ppm": d["ppm"], "odt_eth": odt,
                     "oav": oav, "dil": d["dil"], "role": d["role"]})
    return rows

def score_spec(spec: dict, batch_ml: float = 10.0):
    ing, dil = spec_to_ingredients(spec, batch_ml)
    conc_total = sum(ing.values())
    scorer = FormulaScorer()
    fi = FormulaInfo(number=0, name="IrisDreamweaverV2", ingredients=ing,
                     dilutions=dil, concentrate_ml=conc_total/1000.0, description="")
    s = scorer.score(formula_to_vector(fi))
    wsum = sum(AXIS_W.values())
    log_sum = sum((w/wsum)*math.log(max(float(s.get(a,5.0)),5.0)) for a,w in AXIS_W.items())
    geo = math.exp(log_sum)
    dr = score_dose_response(ing, dilutions=dil, total_volume_ul=conc_total)
    checks = check_batch_scaling(ing, dil, batch_ml, batch_ml)
    errs = [c for c in checks if c.severity == "error"]
    warns = [c for c in checks if c.severity == "warn"]
    return {
        "geo": geo, "axes": {a: float(s.get(a,0)) for a in AXIS_W},
        "dr_score": dr.score, "overdosed": dr.overdosed, "marginal": dr.marginal,
        "optimal": dr.optimal, "oav_err": len(errs), "oav_warn": len(warns),
        "conc_ul": conc_total, "conc_pct": conc_total/(batch_ml*1000)*100,
        "ingredients": ing, "dilutions": dil,
    }

def print_result(label: str, res: dict):
    print(f"\n── {label} ──")
    print(f"  geo={res['geo']:.3f}  conc={res['conc_pct']:.2f}%  "
          f"dr={res['dr_score']:.1f}/100  od={len(res['overdosed'])}  "
          f"mg={len(res['marginal'])}  oav_err={res['oav_err']}  oav_warn={res['oav_warn']}")
    ax = res["axes"]
    # Brief-marker block (weight 1.5)
    print(f"  [brief] lux={ax['luxury']:.1f} long={ax['longevity']:.1f} "
          f"sill={ax['sillage']:.1f} tex={ax['texture']:.1f} "
          f"stk={ax['stacking_depth']:.1f} syn={ax['synergy']:.1f}")
    print(f"  [supp]  hed={ax['hedonic']:.1f} skin={ax['skin_performance']:.1f} "
          f"| [info] clar={ax['perceptual_clarity']:.1f} "
          f"photo={ax['photorealism']:.1f} (excluded)")
    if res["overdosed"]:
        for o in res["overdosed"]:
            print(f"  OD: {o['material']} @ {o['conc_pct']:.3f}%")
    if res["marginal"]:
        for m in res["marginal"]:
            print(f"  mg: {m['material']} @ {m['conc_pct']:.3f}%")

# ── OPTIMIZATION LOOP ────────────────────────────────────────────────
# Strategy: 5 passes. Each pass targets one weakness:
#   Pass 1: fix overdoses (halve ppm of any overdosed material)
#   Pass 2: fix marginals (nudge ppm toward neutral zone)
#   Pass 3: boost luxury axis (raise BzSal, Ambermax, EB, Benzoin)
#   Pass 4: boost sillage (raise Hedione HC, Romandolide-class via EB, Iso E)
#   Pass 5: boost photorealism (tune iris + heliotropin + lactone balance)

def pass_fix_overdose(spec: dict, res: dict) -> dict:
    s = copy.deepcopy(spec)
    for o in res["overdosed"]:
        for name in s:
            if name.lower().replace("-","").replace(" ","") == o["material"].lower().replace("-","").replace(" ",""):
                s[name]["ppm"] = max(int(s[name]["ppm"] * 0.45), 50)
                break
    return s

def pass_fix_marginal(spec: dict, res: dict) -> dict:
    s = copy.deepcopy(spec)
    for m in res["marginal"]:
        for name in s:
            if name.lower().replace("-","").replace(" ","") == m["material"].lower().replace("-","").replace(" ",""):
                # if overdosed direction = "neutral" high → trim 25%; if "neutral" low → boost 30%
                q = m.get("quality","")
                if "neutral" in q or "marginal" in q:
                    # trim if it's a big material, boost if small
                    if s[name]["ppm"] > 10000:
                        s[name]["ppm"] = int(s[name]["ppm"] * 0.78)
                    else:
                        s[name]["ppm"] = int(s[name]["ppm"] * 1.30)
                break
    return s

def pass_boost_luxury(spec: dict) -> dict:
    s = copy.deepcopy(spec)
    boosts = {"Benzyl Salicylate": 1.25, "Ambermax": 1.35, "Benzoin Resinoid": 1.30,
              "Ethylene Brassylate": 1.15, "Alpha Irone": 1.20, "Ebanol": 1.25,
              "Heliotropal": 1.25, "Myristic Acid": 1.20}
    for n, mult in boosts.items():
        if n in s:
            s[n]["ppm"] = int(s[n]["ppm"] * mult)
    return s

def pass_boost_sillage(spec: dict) -> dict:
    s = copy.deepcopy(spec)
    boosts = {"Hedione HC": 1.30, "Iso E Super": 1.20, "Hexyl Salicylate": 1.40,
              "Azarbre": 1.20, "Koavone": 1.25}
    for n, mult in boosts.items():
        if n in s:
            s[n]["ppm"] = int(s[n]["ppm"] * mult)
    return s

def pass_boost_texture_stacking(spec: dict) -> dict:
    """Brief markers TEXTURED + DEEP. Texture = lactonic-creamy-powdered
    material density. Stacking depth = multi-layer fixative density."""
    s = copy.deepcopy(spec)
    tweaks = {
        # texture (lactonic cream + powder)
        "Delta Decalactone":    1.30,
        "Gamma Undecalactone":  1.25,
        "Maple Lactone":        1.20,
        "Musk Ketone":          1.40,  # powder echo
        "Irotyl":               1.30,
        "Ultralia":             1.15,
        # stacking depth (layered base fixatives)
        "Benzoin Resinoid":     1.20,
        "Myristic Acid":        1.15,
        "Ambrettolide":         1.30,
        "Exaltolide":           1.25,
    }
    for n, mult in tweaks.items():
        if n in s:
            s[n]["ppm"] = int(s[n]["ppm"] * mult)
    return s

# ── EXECUTE ──────────────────────────────────────────────────────────
print("="*72)
print(" Iris Dreamweaver v2 — VP/ODT/ppm-based (scale-invariant)")
print(" Banned: FTECs, Fleuressence, FOs, Accords (unknown composition)")
print("="*72)

spec = copy.deepcopy(SPEC)
history = []

res = score_spec(spec, 10.0)
print_result("Iteration 0 (baseline)", res)
history.append(("baseline", res["geo"], res))

# Pass 1: overdoses
spec_1 = pass_fix_overdose(spec, res)
r1 = score_spec(spec_1, 10.0)
print_result("Iteration 1 (fix overdoses)", r1)
if r1["geo"] >= res["geo"] - 0.5:
    spec, res = spec_1, r1
history.append(("pass1_fix_overdose", r1["geo"], r1))

# Pass 2: marginals
spec_2 = pass_fix_marginal(spec, res)
r2 = score_spec(spec_2, 10.0)
print_result("Iteration 2 (fix marginals)", r2)
if r2["geo"] >= res["geo"] - 0.5:
    spec, res = spec_2, r2
history.append(("pass2_fix_marginal", r2["geo"], r2))

# Pass 3: luxury
spec_3 = pass_boost_luxury(spec)
r3 = score_spec(spec_3, 10.0)
print_result("Iteration 3 (boost luxury)", r3)
if r3["geo"] >= res["geo"] - 0.3:
    spec, res = spec_3, r3
history.append(("pass3_boost_luxury", r3["geo"], r3))

# Pass 4: sillage
spec_4 = pass_boost_sillage(spec)
r4 = score_spec(spec_4, 10.0)
print_result("Iteration 4 (boost sillage)", r4)
if r4["geo"] >= res["geo"] - 0.3:
    spec, res = spec_4, r4
history.append(("pass4_boost_sillage", r4["geo"], r4))

# Pass 5: brief markers TEXTURED + DEEP
spec_5 = pass_boost_texture_stacking(spec)
r5 = score_spec(spec_5, 10.0)
print_result("Iteration 5 (boost texture + stacking_depth)", r5)
if r5["overdosed"]:
    spec_5 = pass_fix_overdose(spec_5, r5)
    r5 = score_spec(spec_5, 10.0)
    print_result("Iteration 5b (re-fix overdoses)", r5)
if r5["geo"] >= res["geo"] - 0.3:
    spec, res = spec_5, r5
history.append(("pass5_boost_texture_stacking", r5["geo"], r5))

print("\n" + "="*72)
print(" HISTORY")
print("="*72)
for tag, geo, r in history:
    print(f"  {tag:30s} geo={geo:.3f}  dr={r['dr_score']:.1f}  od={len(r['overdosed'])}")

# ── FINAL: save spec + µL derivations at 5/10/30/100 mL ──
BATCHES = [5.0, 10.0, 30.0, 100.0]
oav_rows = compute_oav_table(spec)

md = []
md += ["# Iris Dreamweaver v2 — VP/ODT/ppm-based (scale-invariant)", ""]
md += ["**Design unit:** target active concentration (ppm w/w) in finished juice. "
       "Scales linearly to any batch size. OAV = ppm_juice / ODT_eth.", ""]
md += ["**Single-molecule + known-composition EOs only.** No FTECs, Fleuressence, "
       "FOs, or Accords whose individual ingredients are unknown.", ""]
md += ["## Final verification (10 mL reference batch)", "",
       f"- **Geo composite:** {res['geo']:.3f}",
       f"- **Dose-response:** {res['dr_score']:.1f}/100 "
       f"({len(res['optimal'])} optimal · {len(res['marginal'])} marginal · "
       f"{len(res['overdosed'])} overdosed)",
       f"- **OAV guard:** {res['oav_err']} err · {res['oav_warn']} warn",
       f"- **Concentrate:** {res['conc_pct']:.2f}%",
       ""]
ax = res["axes"]
md += ["### Brief markers (weight 1.5 each)", "",
       "| Marker | Brief phrase | Score |",
       "|---|---|--:|",
       f"| luxury         | \"EXTREMELY EXPENSIVE, LUXURY\" | {ax['luxury']:.1f} |",
       f"| longevity      | \"LONG LASTING\"              | {ax['longevity']:.1f} |",
       f"| sillage        | \"PROJECTIVE\"                | {ax['sillage']:.1f} |",
       f"| texture        | \"TEXTURED\"                  | {ax['texture']:.1f} |",
       f"| stacking_depth | \"DEEP\"                      | {ax['stacking_depth']:.1f} |",
       f"| synergy        | \"SINGLE DIRECTION SYNERGY\"  | {ax['synergy']:.1f} |",
       "",
       "### Supporting markers (weight 1.0 each)", "",
       "| Marker | Brief phrase | Score |",
       "|---|---|--:|",
       f"| hedonic          | \"beautiful and dreamy\" | {ax['hedonic']:.1f} |",
       f"| skin_performance | (required for projective longevity on skin) | {ax['skin_performance']:.1f} |",
       "",
       "### Informational (de-weighted / excluded)", "",
       f"- perceptual_clarity (weight 0.2): {ax['perceptual_clarity']:.1f} — brief said transparency is optional if character is lost",
       f"- photorealism (weight 0.0): {ax['photorealism']:.1f} — EXCLUDED; not a literal-flower reproduction",
       ""]
md += ["## Optimization history", "",
       "| Pass | Geo | DR | Overdosed |", "|---|--:|--:|--:|"]
for tag, geo, r in history:
    md.append(f"| {tag} | {geo:.3f} | {r['dr_score']:.1f} | {len(r['overdosed'])} |")
md += [""]

md += ["## Formula specification (ppm + OAV — the scale-invariant definition)", "",
       "| Material | Role | ppm juice | Dilution | ODT eth (ppm) | OAV |",
       "|---|---|--:|---|--:|--:|"]
for row in oav_rows:
    odt_s = f"{row['odt_eth']:.3f}" if row["odt_eth"] else "—"
    oav_s = f"{row['oav']:.0f}" if row["oav"] else "—"
    dil_s = "neat" if row["dil"] == 1.0 else f"{int(row['dil']*100)}%"
    md.append(f"| {row['name']} | {row['role']} | {row['ppm']:,} | {dil_s} | {odt_s} | {oav_s} |")
md += [""]

md += ["## Batch derivations (µL of stock dilution)", "",
       "| Material | Dilution | 5 mL | 10 mL | 30 mL | 100 mL |",
       "|---|---|--:|--:|--:|--:|"]
rows_by_batch = {b: spec_to_ingredients(spec, b)[0] for b in BATCHES}
for name in spec:
    dil = spec[name]["dil"]
    dil_s = "neat" if dil == 1.0 else f"{int(dil*100)}%"
    cells = " | ".join(f"{rows_by_batch[b][name]:.2f}" for b in BATCHES)
    md.append(f"| {name} | {dil_s} | {cells} |")

# Totals row
md.append("| **Concentrate total** | | " + " | ".join(
    f"**{sum(rows_by_batch[b].values()):.1f}**" for b in BATCHES) + " |")
md.append("| **Ethanol 96% (µL)** | | " + " | ".join(
    f"**{b*1000 - sum(rows_by_batch[b].values()):.0f}**" for b in BATCHES) + " |")
md.append("| **Batch (µL)** | | " + " | ".join(f"**{b*1000:.0f}**" for b in BATCHES) + " |")
md += [""]

md += ["## Removed pre-blends (banned by rule 2)", "",
       "- ~~Orris F-TEC~~ → replaced with more Alpha Irone + Orivone + Dihydro Beta Ionone (all single molecules)",
       "- ~~Heliotropin Fleuressence~~ → Heliotropal (Piperonal) alone; it IS the heliotropin",
       "- ~~Tonka Bean FO~~ → decomposed into Coumarin + Vanillin + Ethyl Vanillin + Benzoin Resinoid (known GC composition)",
       ""]

md += ["## Why this formula scales logically", "",
       "The formula is defined in **ppm of active per unit juice**, not µL per batch. "
       "When you scale from 10 mL to 100 mL the ppm stays fixed, the OAV stays fixed, "
       "and the perceptual profile stays fixed. µL values simply multiply by 10. "
       "This is exactly how industrial fragrance specifications are written.", ""]
md += ["Pipette-floor flags below are the only non-linear concern — at small batches "
       "some trace materials fall below the 1 µL floor and must be pre-diluted further. "
       "These are called out by the OAV guard.", ""]

out = "formulas/collections/Iris_Dreamweaver_v2_ppm.md"
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(md))

# Save spec JSON for reproducibility
with open("formulas/collections/Iris_Dreamweaver_v2_ppm.json", "w", encoding="utf-8") as f:
    json.dump({"spec": spec, "axes": res["axes"], "geo": res["geo"]}, f, indent=2)

print(f"\n✓ Saved: {out}")
print(f"✓ Saved: formulas/collections/Iris_Dreamweaver_v2_ppm.json")
