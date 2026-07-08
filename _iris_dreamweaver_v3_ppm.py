"""Iris Dreamweaver v3 — ppm-based, scale-invariant, single-molecule only.

v3 CHANGES vs v2:
  (A) SPEC edits to unlock luxury + sillage:
      • Hedione 28000→22000, Hedione HC 10000→7000 (cut generic-floral overuse)
      • Ethyl Vanillin 2000→400 (remove gourmand/confectionery drag)
      • Vanillin 500→1500 (proper luxury vanilla body)
      • Alpha Irone 8400→12000 (raise the rarest, most expensive material)
      • Add AIMI (Alpha-Isomethyl Ionone) 1200 ppm — "small AIMI violet" halo
      • Add Romandolide 8000 ppm — missing projection-axis musk
      • Hexyl Salicylate 5000→9000 (sheer diffusion film)
      • Add Habanolide 3000 ppm — woody-musky halo extension
      • Myristic Acid 3000→5000 ppm — buttery orris-butter matrix (weighed
        as mg powder; represented here as 20% stock for pipette workflow)
  (B) Optimizer upgrade:
      • Passes 3/4/5 replaced with coordinate-descent gradient search
        (target axis: luxury, then sillage, then texture+stacking_depth).
        For each of 5–6 candidate materials, perturb ±15% and measure
        Δ target axis. Accept moves only if: brief-marker floor holds
        AND target axis improves AND geo does not drop > 0.3.
      • Brief-marker floor rule: no brief-weight-1.5 axis may drop below
        its baseline value minus 1.0 point. Prevents pass-3 style regression.
"""
import io, os, sys, math, copy, json
if os.name == "nt":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from engine.optimizer.scoring import FormulaScorer
from engine.optimizer.oav_guard import check_batch_scaling
from engine.dose_response import score_dose_response
from engine.formula_analyzer import FormulaInfo, formula_to_vector
from engine.odor_thresholds import ODT_DATA

# ── ODT supplement (ppm in ethanol) ─────────────────────────────────
ODT_EXTRA = {
    "heliotropal":           5.0,
    "piperonal":             5.0,
    "anisaldehyde":          5.0,
    "gamma undecalactone":   1.0,
    "gamma decalactone":     1.5,
    "delta decalactone":     10.0,
    "ethyl maltol":          0.3,
    "hedione hc":            3.0,
    "mayol":                 3.0,
    "bourgeonal":            0.03,
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
    "habanolide":            1.5,
    "tonalide":              1.0,
    "ambermax":              0.5,
    "azarbre":               2.0,
    "koavone":               2.0,
    "cedarwood virginia":    3.0,
    "hexyl salicylate":      30.0,
    "myristic acid":         500.0,
    "ipm":                  1000.0,
    "benzyl alcohol":        60.0,
    "red mandarin":          2.0,
    "bergamot fcf sicilian": 1.5,
    "ylang ylang extra":     1.0,
    "rose absolute":         3.0,
    "jasmine absolute":      1.5,
    "benzoin resinoid":      30.0,
    "siam benzoin":          30.0,
    "alpha isomethyl ionone":3.0,
    "aimi":                  3.0,
    "vanillin":              20.0,
}

def lookup_odt(name: str):
    k = name.lower().strip()
    for nm, d in ODT_DATA.items():
        nk = nm.lower()
        if nk == k or k.startswith(nk) or nk in k:
            return d["odt_eth"]
    for nm, v in ODT_EXTRA.items():
        if nm == k or k.startswith(nm) or nm in k:
            return v
    return None

# ── FORMULA SPEC (v3) ────────────────────────────────────────────────
SPEC: dict[str, dict] = {
    # TOP
    "Bergamot FCF Sicilian":   {"ppm": 4000,  "dil": 1.00, "role": "top"},
    "Red Mandarin EO":         {"ppm": 2000,  "dil": 1.00, "role": "top"},
    # IRIS CORE — Alpha Irone raised, AIMI trace added for violet halo
    "Alpha Irone":             {"ppm": 12000, "dil": 0.30, "role": "iris"},
    "Orivone":                 {"ppm":  4000, "dil": 1.00, "role": "iris"},
    "Dihydro Beta Ionone":     {"ppm":  2000, "dil": 1.00, "role": "iris"},
    "Alpha Ionone":            {"ppm":  1500, "dil": 1.00, "role": "iris"},
    "Alpha Isomethyl Ionone":  {"ppm":  1200, "dil": 1.00, "role": "iris"},   # AIMI trace
    "Carrot Seed EO":          {"ppm":  1500, "dil": 1.00, "role": "iris"},
    "Ultralia":                {"ppm":  2500, "dil": 1.00, "role": "iris"},
    "Irotyl":                  {"ppm":   500, "dil": 1.00, "role": "iris"},
    # WHITE FLORAL HEART — Hedione class cut back
    "Hedione":                 {"ppm": 22000, "dil": 1.00, "role": "floral"},
    "Hedione HC":              {"ppm":  7000, "dil": 1.00, "role": "floral"},
    "Mayol":                   {"ppm":  2500, "dil": 1.00, "role": "floral"},
    "Hydroxycitronellal":      {"ppm":  2000, "dil": 1.00, "role": "floral"},
    "Amyl Cinnamic Aldehyde":  {"ppm":  2000, "dil": 1.00, "role": "floral"},
    "DBCA":                    {"ppm":  1500, "dil": 1.00, "role": "floral"},
    "Bourgeonal":              {"ppm":  1000, "dil": 1.00, "role": "floral"},
    "Farnesol":                {"ppm":   500, "dil": 1.00, "role": "floral"},
    "Cis Jasmone":             {"ppm":   500, "dil": 1.00, "role": "floral"},
    # GOURMAND CREAMY BRIDGE — EV slashed, Vanillin raised, Myristic raised
    "Myristic Acid":           {"ppm":  5000, "dil": 0.20, "role": "bridge"}, # orris-butter matrix
    "Benzoin Resinoid":        {"ppm":  5000, "dil": 0.50, "role": "bridge"},
    "Heliotropal":             {"ppm":  4000, "dil": 1.00, "role": "bridge"},
    "Ethyl Vanillin":          {"ppm":   400, "dil": 0.10, "role": "bridge"}, # trace only
    "Vanillin":                {"ppm":  1500, "dil": 0.10, "role": "bridge"}, # luxury vanilla body
    "Ethyl Maltol":            {"ppm":   500, "dil": 0.10, "role": "bridge"},
    "Delta Decalactone":       {"ppm":  3500, "dil": 1.00, "role": "bridge"},
    "Maple Lactone":           {"ppm":   700, "dil": 0.20, "role": "bridge"},
    "Gamma Undecalactone":     {"ppm":  3000, "dil": 1.00, "role": "bridge"},
    "Coumarin":                {"ppm":  2400, "dil": 0.20, "role": "bridge"},
    "Anisaldehyde":            {"ppm":  1500, "dil": 1.00, "role": "bridge"},
    # FIXATIVE / DIFFUSION / WOODS — musk chord rebuilt across 3 axes
    "Ethylene Brassylate":     {"ppm": 20000, "dil": 1.00, "role": "base"},   # depth
    "Romandolide":             {"ppm":  8000, "dil": 1.00, "role": "base"},   # PROJECTION (new)
    "Habanolide":              {"ppm":  3000, "dil": 1.00, "role": "base"},   # woody-musky halo (new)
    "Musk Ketone":             {"ppm":  1000, "dil": 0.10, "role": "base"},   # powder echo
    "Exaltolide":              {"ppm":   800, "dil": 0.10, "role": "base"},
    "Ambrettolide":            {"ppm":   600, "dil": 0.10, "role": "base"},
    "Iso E Super":             {"ppm": 15000, "dil": 1.00, "role": "base"},
    "Benzyl Salicylate":       {"ppm": 15000, "dil": 1.00, "role": "base"},
    "Hexyl Salicylate":        {"ppm":  9000, "dil": 1.00, "role": "base"},   # sheer diffusion film
    "Ambermax":                {"ppm":  4000, "dil": 0.50, "role": "base"},
    "Azarbre":                 {"ppm":  5000, "dil": 1.00, "role": "base"},
    "Koavone":                 {"ppm":  4000, "dil": 1.00, "role": "base"},
    "Cedarwood Virginia":      {"ppm":  3000, "dil": 1.00, "role": "base"},
    "Ebanol":                  {"ppm":  4000, "dil": 1.00, "role": "base"},
    "Bacdanol":                {"ppm":  2500, "dil": 1.00, "role": "base"},
}

# ── BRIEF-DRIVEN AXIS WEIGHTS (unchanged from v2 brief-aligned set) ──
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
    "photorealism":     0.0,
}
BRIEF_AXES = [a for a, w in AXIS_W.items() if w >= 1.5]

def spec_to_ingredients(spec, batch_ml):
    batch_ul = batch_ml * 1000.0
    ing, dil = {}, {}
    for name, d in spec.items():
        active_ul = batch_ul * d["ppm"] / 1e6
        stock_ul = active_ul / d["dil"]
        ing[name] = stock_ul
        dil[name] = d["dil"]
    return ing, dil

def compute_oav_table(spec):
    rows = []
    for name, d in spec.items():
        odt = lookup_odt(name)
        oav = (d["ppm"] / odt) if odt else None
        rows.append({"name": name, "ppm": d["ppm"], "odt_eth": odt,
                     "oav": oav, "dil": d["dil"], "role": d["role"]})
    return rows

def score_spec(spec, batch_ml=10.0):
    ing, dil = spec_to_ingredients(spec, batch_ml)
    conc_total = sum(ing.values())
    scorer = FormulaScorer()
    fi = FormulaInfo(number=0, name="IrisDreamweaverV3", ingredients=ing,
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

def print_result(label, res):
    print(f"\n── {label} ──")
    print(f"  geo={res['geo']:.3f}  conc={res['conc_pct']:.2f}%  "
          f"dr={res['dr_score']:.1f}/100  od={len(res['overdosed'])}  "
          f"mg={len(res['marginal'])}  oav_err={res['oav_err']}  oav_warn={res['oav_warn']}")
    ax = res["axes"]
    print(f"  [brief] lux={ax['luxury']:.1f} long={ax['longevity']:.1f} "
          f"sill={ax['sillage']:.1f} tex={ax['texture']:.1f} "
          f"stk={ax['stacking_depth']:.1f} syn={ax['synergy']:.1f}")
    print(f"  [supp]  hed={ax['hedonic']:.1f} skin={ax['skin_performance']:.1f} "
          f"| [info] clar={ax['perceptual_clarity']:.1f} "
          f"photo={ax['photorealism']:.1f} (excluded)")
    if res["overdosed"]:
        for o in res["overdosed"]:
            print(f"  OD: {o['material']} @ {o['conc_pct']:.3f}%")

# ── PASS 1/2: overdose/marginal cleanup (same as v2) ────────────────
def pass_fix_overdose(spec, res):
    s = copy.deepcopy(spec)
    for o in res["overdosed"]:
        for name in s:
            if name.lower().replace("-","").replace(" ","") == o["material"].lower().replace("-","").replace(" ",""):
                s[name]["ppm"] = max(int(s[name]["ppm"] * 0.45), 50)
                break
    return s

def pass_fix_marginal(spec, res):
    s = copy.deepcopy(spec)
    for m in res["marginal"]:
        for name in s:
            if name.lower().replace("-","").replace(" ","") == m["material"].lower().replace("-","").replace(" ",""):
                q = m.get("quality","")
                if "neutral" in q or "marginal" in q:
                    if s[name]["ppm"] > 10000:
                        s[name]["ppm"] = int(s[name]["ppm"] * 0.78)
                    else:
                        s[name]["ppm"] = int(s[name]["ppm"] * 1.30)
                break
    return s

# ── COORDINATE-DESCENT OPTIMIZER ────────────────────────────────────
# For each candidate material: try ppm × (1+step) and ppm × (1-step).
# Keep the best perturbation that (a) raises the target axis, (b) keeps
# brief-marker floor, (c) does not drop geo > tol. Iterate to fixed-point.

def brief_floor_ok(baseline_axes, candidate_axes, drop=1.0):
    for a in BRIEF_AXES:
        if candidate_axes[a] < baseline_axes[a] - drop:
            return False
    return True

def coord_descent(spec, target_axis, candidates, step=0.15, max_iters=3,
                  geo_tol=0.3, floor_drop=1.0, label=""):
    """Perturb each candidate material ±step; accept best move that
    improves target_axis AND holds brief-marker floor AND geo-drop ≤ geo_tol.
    Iterate max_iters full passes."""
    s = copy.deepcopy(spec)
    base = score_spec(s, 10.0)
    baseline_axes = dict(base["axes"])
    print(f"\n── Coord-descent: boost {target_axis} ({label}) ──")
    print(f"  start: {target_axis}={baseline_axes[target_axis]:.2f} geo={base['geo']:.3f}")
    improved_any = True
    itr = 0
    while improved_any and itr < max_iters:
        itr += 1
        improved_any = False
        for mat in candidates:
            if mat not in s:
                continue
            best_delta = 0.0
            best_mult = None
            best_res = None
            for mult in (1.0 + step, 1.0 - step):
                trial = copy.deepcopy(s)
                trial[mat]["ppm"] = max(int(trial[mat]["ppm"] * mult), 50)
                r = score_spec(trial, 10.0)
                # reject overdose additions
                if len(r["overdosed"]) > len(base["overdosed"]):
                    continue
                # reject geo drop
                if r["geo"] < base["geo"] - geo_tol:
                    continue
                # reject brief-floor violation
                if not brief_floor_ok(baseline_axes, r["axes"], floor_drop):
                    continue
                d = r["axes"][target_axis] - base["axes"][target_axis]
                if d > best_delta + 0.05:
                    best_delta = d
                    best_mult = mult
                    best_res = r
            if best_mult is not None:
                s[mat]["ppm"] = max(int(s[mat]["ppm"] * best_mult), 50)
                print(f"    iter{itr}: {mat} ×{best_mult:.2f} "
                      f"→ {target_axis} {base['axes'][target_axis]:.2f}→{best_res['axes'][target_axis]:.2f} "
                      f"(geo {base['geo']:.3f}→{best_res['geo']:.3f})")
                base = best_res
                improved_any = True
    print(f"  end:   {target_axis}={base['axes'][target_axis]:.2f} geo={base['geo']:.3f}")
    return s, base

# ── EXECUTE ──────────────────────────────────────────────────────────
print("="*72)
print(" Iris Dreamweaver v3 — ppm-based, coord-descent optimizer")
print(" Banned: FTECs, Fleuressence, FOs, Accords")
print("="*72)

spec = copy.deepcopy(SPEC)
history = []

res0 = score_spec(spec, 10.0)
print_result("Iteration 0 (v3 baseline — new SPEC)", res0)
history.append(("baseline_v3", res0["geo"], res0))
res = res0

# Pass 1: overdoses
spec_1 = pass_fix_overdose(spec, res)
r1 = score_spec(spec_1, 10.0)
print_result("Pass 1 (fix overdoses)", r1)
if r1["geo"] >= res["geo"] - 0.5:
    spec, res = spec_1, r1
history.append(("pass1_fix_overdose", r1["geo"], r1))

# Pass 2: marginals
spec_2 = pass_fix_marginal(spec, res)
r2 = score_spec(spec_2, 10.0)
print_result("Pass 2 (fix marginals)", r2)
if r2["geo"] >= res["geo"] - 0.5:
    spec, res = spec_2, r2
history.append(("pass2_fix_marginal", r2["geo"], r2))

# Pass 3: coord-descent on LUXURY
LUX_CANDIDATES = ["Alpha Irone", "Benzyl Salicylate", "Ambermax",
                  "Benzoin Resinoid", "Ethylene Brassylate", "Vanillin",
                  "Heliotropal", "Ebanol", "Myristic Acid"]
spec_3, r3 = coord_descent(spec, "luxury", LUX_CANDIDATES,
                           step=0.15, max_iters=3, label="pass 3")
print_result("Pass 3 (coord-descent luxury — final)", r3)
spec, res = spec_3, r3
history.append(("pass3_coord_luxury", r3["geo"], r3))

# Pass 4: coord-descent on SILLAGE
SIL_CANDIDATES = ["Romandolide", "Habanolide", "Hedione HC", "Hexyl Salicylate",
                  "Iso E Super", "Azarbre", "Koavone", "Ethylene Brassylate"]
spec_4, r4 = coord_descent(spec, "sillage", SIL_CANDIDATES,
                           step=0.15, max_iters=3, label="pass 4")
print_result("Pass 4 (coord-descent sillage — final)", r4)
spec, res = spec_4, r4
history.append(("pass4_coord_sillage", r4["geo"], r4))

# Pass 5: coord-descent on TEXTURE (primary), STACKING-DEPTH folded in via floor
TEX_CANDIDATES = ["Delta Decalactone", "Gamma Undecalactone", "Maple Lactone",
                  "Musk Ketone", "Irotyl", "Ultralia", "Benzoin Resinoid",
                  "Myristic Acid", "Ambrettolide", "Exaltolide"]
spec_5, r5 = coord_descent(spec, "texture", TEX_CANDIDATES,
                           step=0.15, max_iters=3, label="pass 5")
print_result("Pass 5 (coord-descent texture — final)", r5)
# safety: re-fix any newly introduced overdoses
if r5["overdosed"]:
    spec_5b = pass_fix_overdose(spec_5, r5)
    r5b = score_spec(spec_5b, 10.0)
    print_result("Pass 5b (re-fix overdoses)", r5b)
    if r5b["geo"] >= r5["geo"] - 0.3:
        spec_5, r5 = spec_5b, r5b
spec, res = spec_5, r5
history.append(("pass5_coord_texture", r5["geo"], r5))

print("\n" + "="*72)
print(" HISTORY")
print("="*72)
for tag, geo, r in history:
    ax = r["axes"]
    print(f"  {tag:30s} geo={geo:.3f}  lux={ax['luxury']:.1f}  "
          f"sill={ax['sillage']:.1f}  tex={ax['texture']:.1f}  "
          f"od={len(r['overdosed'])}")

# ── WRITE OUTPUTS ────────────────────────────────────────────────────
BATCHES = [5.0, 10.0, 30.0, 100.0]
oav_rows = compute_oav_table(spec)

md = []
md += ["# Iris Dreamweaver v3 — ppm + coord-descent", ""]
md += ["**v3 vs v2 summary:** SPEC redesigned for luxury (EV cut, Vanillin raised, AIMI trace added, Alpha Irone raised) and sillage (Romandolide projection musk + Habanolide halo + Hexyl Salicylate sheer film). Optimizer passes 3/4/5 replaced with coordinate-descent gradient search against target axis, with a brief-marker floor rule preventing regressions.", ""]
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
       f"- perceptual_clarity (weight 0.2): {ax['perceptual_clarity']:.1f}",
       f"- photorealism (weight 0.0): {ax['photorealism']:.1f} — EXCLUDED",
       ""]

md += ["## Optimization history", "",
       "| Pass | Geo | Luxury | Sillage | Texture | OD |",
       "|---|--:|--:|--:|--:|--:|"]
for tag, geo, r in history:
    a = r["axes"]
    md.append(f"| {tag} | {geo:.3f} | {a['luxury']:.1f} | {a['sillage']:.1f} | "
              f"{a['texture']:.1f} | {len(r['overdosed'])} |")
md += [""]

md += ["## Formula specification (ppm + OAV)", "",
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
md.append("| **Concentrate total** | | " + " | ".join(
    f"**{sum(rows_by_batch[b].values()):.1f}**" for b in BATCHES) + " |")
md.append("| **Ethanol 96% (µL)** | | " + " | ".join(
    f"**{b*1000 - sum(rows_by_batch[b].values()):.0f}**" for b in BATCHES) + " |")
md.append("| **Batch (µL)** | | " + " | ".join(f"**{b*1000:.0f}**" for b in BATCHES) + " |")
md += [""]

md += ["## Notes on Myristic Acid (orris-butter matrix)", "",
       "Myristic acid is a solid waxy powder — weigh as mg, not pipette. "
       "At 5,000 ppm in 10 mL juice that is **50 mg** of powder. The 20% stock "
       "listing is a workflow convenience: dissolve the required mg of powder "
       "in enough DPG to make a 20% solution, then pipette stock µL from that. "
       "This material anchors the iris with a lactonic-buttery coating that "
       "mimics the fatty matrix of natural Orris Butter.", ""]

out = "formulas/collections/Iris_Dreamweaver_v3_ppm.md"
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(md))

with open("formulas/collections/Iris_Dreamweaver_v3_ppm.json", "w", encoding="utf-8") as f:
    json.dump({"spec": spec, "axes": res["axes"], "geo": res["geo"],
               "history": [{"tag": t, "geo": g, "axes": r["axes"]}
                           for t, g, r in history]}, f, indent=2)

print(f"\n✓ Saved: {out}")
print(f"✓ Saved: formulas/collections/Iris_Dreamweaver_v3_ppm.json")
