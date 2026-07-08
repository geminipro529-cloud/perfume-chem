"""Iris Dreamweaver v5 — perfumery-reasoned sub-ODT two-directional layer.

REPLACES v4. v4 picked 5 trace materials without composition-specific
reasoning, and the dose sweep showed the scorer was inert across every
OAV — confirming the picks were meaningless.

v5 PRINCIPLE: every sub-ODT addition must reinforce TWO existing
directions that are already present in the v3 SPEC, so that adding the
trace deepens two separate accord vectors without declaring a third.

THE FIVE PICKS, with two-directional perfumery justification:

(1) Beta-Ionone (neat)
    DIR-A: reinforces ionone cluster (Alpha Ionone + AIMI + DBI + Alpha
           Irone) with its woody-violet facet — adds VIOLET ROUNDING
           that α-Irone's rooty-powdery facet does not carry
    DIR-B: bridges iris → woody-amber bed (Azarbre + Koavone) — β-ionone
           has a natural cedar-warm facet in its drydown
    SUB-ODT REASON: above OAV 1 it declares "violet" as a third direction
    and the synergy axis would reject it

(2) Leafovert (neat) [replaces cis-3-Hexenol — cis-3 is unlabeled
                       concentration in this workshop; Leafovert is
                       labeled neat and delivers the same cut-green
                       vector more cleanly]
    DIR-A: gives Mayol / Bourgeonal / Hydroxycitronellal muguet core
           the CUT-STEM green realism natural lily-of-the-valley has
           (Bourgeonal alone is only the "bell", Leafovert adds leaf)
    DIR-B: reinforces top freshness alongside Bergamot FCF Sicilian +
           Red Mandarin without adding a citrus
    SUB-ODT REASON: Leafovert above OAV 1 reads as sharp galbanum-grass
    and would declare a green direction that contradicts the brief

(3) Aurantiol (neat) [replaces Benzyl Acetate — BzAc has a sour-fruity
                      ester facet that pulls the accord off-white;
                      Aurantiol is creamy orange-blossom, clean-white]
    DIR-A: Hedione jasmine halo — Aurantiol's methyl-anthranilate
           backbone extends Hedione into neroli/tiare territory,
           giving the jasmine radiance a creamy-indolic body
           without introducing sour esters or indole itself
    DIR-B: reinforces Hydroxycitronellal + Bourgeonal + Mayol muguet
           axis — Aurantiol IS a Schiff base of hydroxycitronellal
           + methyl anthranilate, so it literally fuses the existing
           muguet material with orange-blossom in one molecule
    SUB-ODT REASON: above OAV 1 declares "orange blossom" as a third
    headline direction and flattens the iris-led brief

(4) Alpha Damascone (10% in DPG)
    DIR-A: bridges Orivone buttery-iris → rose-plum halo — damascones
           carry iris-adjacent rose that fuses with Orivone's warmth
    DIR-B: connects Delta Decalactone lactonic → Benzoin balsamic via
           damascone's prune-jam facet — the iris ↔ gourmand bond v3
           is structurally missing
    SUB-ODT REASON: damascones above OAV 0.5 take over; this is the
    textbook sub-ODT material in modern perfumery

(5) Isoeugenol (neat)
    DIR-A: combines with Cis Jasmone + Anisaldehyde to form a
           heliotrope-carnation halo (classic iris-gourmand pivot)
    DIR-B: eugenol family bridges to Cedarwood Virginia + Koavone
           warmth — a floral→woody lipid spice link
    SUB-ODT REASON: above OAV 1 reads as dentist-clove and declares
    a spice direction that contradicts the brief

All 5 are already in the workshop inventory.
"""
import io, os, sys, math, copy, json
if os.name == "nt":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from engine.optimizer.scoring import FormulaScorer
from engine.optimizer.oav_guard import check_batch_scaling
from engine.dose_response import score_dose_response
from engine.formula_analyzer import FormulaInfo, formula_to_vector
from engine.odor_thresholds import ODT_DATA

# ── ODT supplement ──────────────────────────────────────────────────
ODT_EXTRA = {
    "heliotropal": 5.0, "piperonal": 5.0, "anisaldehyde": 5.0,
    "gamma undecalactone": 1.0, "gamma decalactone": 1.5,
    "delta decalactone": 10.0, "ethyl maltol": 0.3, "hedione hc": 3.0,
    "mayol": 3.0, "bourgeonal": 0.03, "dbca": 0.5,
    "amyl cinnamic aldehyde": 2.0, "aca": 2.0, "dihydro beta ionone": 0.3,
    "irotyl": 1.0, "ethylene brassylate": 2.0, "exaltolide": 1.0,
    "ambrettolide": 0.5, "musk ketone": 2.0, "romandolide": 1.0,
    "habanolide": 1.5, "ambermax": 0.5, "azarbre": 2.0,
    "koavone": 2.0, "cedarwood virginia": 3.0, "hexyl salicylate": 30.0,
    "myristic acid": 500.0, "red mandarin": 2.0,
    "bergamot fcf sicilian": 1.5, "benzoin resinoid": 30.0,
    "alpha isomethyl ionone": 3.0, "vanillin": 20.0,
    # v5 traces (with authoritative literature values)
    "beta ionone":     0.007,   # ppm eth; violet-woody
    "leafovert":       0.05,    # ppm eth; sharp cut-grass
    "aurantiol":       0.3,     # ppm eth; creamy orange-blossom schiff base
    "alpha damascone": 0.009,   # ppm eth; rose-plum damascone
    "isoeugenol":      0.4,     # ppm eth; carnation-clove
}

def lookup_odt(name):
    k = name.lower().strip()
    for nm, d in ODT_DATA.items():
        nk = nm.lower()
        if nk == k or k.startswith(nk) or nk in k:
            return d["odt_eth"]
    for nm, v in ODT_EXTRA.items():
        if nm == k or k.startswith(nm) or nm in k:
            return v
    return None

# ── Load v3 final SPEC as base ──────────────────────────────────────
with open("formulas/collections/Iris_Dreamweaver_v3_ppm.json", encoding="utf-8") as f:
    v3_data = json.load(f)
SPEC: dict = copy.deepcopy(v3_data["spec"])

# ── v5 two-directional trace layer ──────────────────────────────────
V5_TRACES = {
    "Beta Ionone":     {"dil": 1.00, "role": "trace_iris_wood",
                        "rationale": "Violet-woody facet; α+β ionone pair deepens iris and bridges to Azarbre/Koavone"},
    "Leafovert":       {"dil": 1.00, "role": "trace_green",
                        "rationale": "Cut-leaf green realism for Mayol/Bourgeonal muguet; lifts top without adding citrus"},
    "Aurantiol":       {"dil": 1.00, "role": "trace_white_floral",
                        "rationale": "Schiff base of hydroxycitronellal + methyl anthranilate; fuses Hedione jasmine with muguet axis as creamy orange-blossom (clean-white, not sour)"},
    "Alpha Damascone": {"dil": 0.10, "role": "trace_rose_bridge",
                        "rationale": "Iris→gourmand prune-rose bridge (Orivone↔Delta Decalactone↔Benzoin)"},
    "Isoeugenol":      {"dil": 1.00, "role": "trace_floral_wood",
                        "rationale": "Carnation halo (Cis Jasmone + Anisaldehyde) bridges to Cedar+Koavone"},
}

for name, t in V5_TRACES.items():
    odt = lookup_odt(name)
    t["odt"] = odt
    seed_oav = 0.3
    SPEC[name] = {"ppm": odt * seed_oav, "dil": t["dil"], "role": t["role"]}
    print(f"  seed {name}: ODT={odt:.4f} ppm → ppm={odt*seed_oav:.5f} "
          f"(target OAV {seed_oav})")

# ── Scoring infrastructure ──────────────────────────────────────────
AXIS_W = {
    "luxury": 1.5, "longevity": 1.5, "sillage": 1.5, "texture": 1.5,
    "stacking_depth": 1.5, "synergy": 1.5,
    "hedonic": 1.0, "skin_performance": 1.0,
    "perceptual_clarity": 0.2, "photorealism": 0.0,
}
BRIEF_AXES = [a for a, w in AXIS_W.items() if w >= 1.5]

def spec_to_ingredients(spec, batch_ml):
    batch_ul = batch_ml * 1000.0
    ing, dil = {}, {}
    for name, d in spec.items():
        active_ul = batch_ul * d["ppm"] / 1e6
        ing[name] = active_ul / d["dil"]
        dil[name] = d["dil"]
    return ing, dil

def score_spec(spec, batch_ml=10.0):
    ing, dil = spec_to_ingredients(spec, batch_ml)
    conc_total = sum(ing.values())
    scorer = FormulaScorer()
    fi = FormulaInfo(number=0, name="IrisDreamweaverV5", ingredients=ing,
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
        "oav_err": len(errs), "oav_warn": len(warns),
        "conc_pct": conc_total/(batch_ml*1000)*100, "conc_ul": conc_total,
    }

def trace_oav(spec, name):
    d = spec[name]; odt = lookup_odt(name)
    return (d["ppm"] / odt) if odt else None

def print_result(label, res, spec=None):
    print(f"\n── {label} ──")
    print(f"  geo={res['geo']:.3f}  conc={res['conc_pct']:.2f}%  "
          f"dr={res['dr_score']:.1f}/100  od={len(res['overdosed'])}  "
          f"oav_err={res['oav_err']}  oav_warn={res['oav_warn']}")
    ax = res["axes"]
    print(f"  [brief] lux={ax['luxury']:.1f} long={ax['longevity']:.1f} "
          f"sill={ax['sillage']:.1f} tex={ax['texture']:.1f} "
          f"stk={ax['stacking_depth']:.1f} syn={ax['synergy']:.1f}")
    print(f"  [supp]  hed={ax['hedonic']:.1f} skin={ax['skin_performance']:.1f} "
          f"| [info] clar={ax['perceptual_clarity']:.1f} "
          f"photo={ax['photorealism']:.1f}")
    if spec is not None:
        tr = ", ".join(f"{n}:{trace_oav(spec, n):.2f}"
                       for n in V5_TRACES if n in spec)
        print(f"  [trace OAVs] {tr}")

# ── EXECUTE ──────────────────────────────────────────────────────────
print("\n" + "="*72)
print(" Iris Dreamweaver v5 — perfumery-reasoned sub-ODT layer")
print("="*72)

v3_ax = v3_data["axes"]
print(f"\nv3 anchor:  lux={v3_ax['luxury']:.1f} long={v3_ax['longevity']:.1f} "
      f"sill={v3_ax['sillage']:.1f} tex={v3_ax['texture']:.1f} "
      f"stk={v3_ax['stacking_depth']:.1f} syn={v3_ax['synergy']:.1f}  "
      f"geo={v3_data['geo']:.3f}")

r0 = score_spec(SPEC, 10.0)
print_result("v5 baseline (v3 SPEC + 5 traces seeded @ OAV 0.3)", r0, SPEC)

# ── Per-material dose response sweep (2 directions: down and up) ────
# User guidance: sub-ODT may be added BI-DIRECTIONALLY — for synergy
# reasons AND for concrete perfumery reasons. So sweep OAV 0.0 (absent)
# → 0.1, 0.3, 0.6, 0.9 (near-ODT), and 1.2 (just over) to confirm which
# side of ODT each material pays off.
print("\n" + "="*72)
print(" PER-TRACE DOSE RESPONSE (all others held at OAV 0.3)")
print("="*72)

SWEEP_OAVS = [0.0, 0.1, 0.3, 0.6, 0.9, 1.2, 2.0]
sweep_data = {}
baseline_locked = copy.deepcopy(SPEC)
for tname in V5_TRACES:
    sweep_data[tname] = []
    for target_oav in SWEEP_OAVS:
        trial = copy.deepcopy(baseline_locked)
        if target_oav == 0.0:
            del trial[tname]
        else:
            trial[tname]["ppm"] = lookup_odt(tname) * target_oav
        r = score_spec(trial, 10.0)
        sweep_data[tname].append({
            "oav": target_oav, "lux": r["axes"]["luxury"],
            "syn": r["axes"]["synergy"], "geo": r["geo"],
            "hed": r["axes"]["hedonic"], "od": len(r["overdosed"]),
            "clar": r["axes"]["perceptual_clarity"],
        })
    print(f"\n  {tname}  ({V5_TRACES[tname]['rationale']})")
    print(f"    {'OAV':>5} {'lux':>5} {'syn':>5} {'hed':>5} {'clar':>5} "
          f"{'geo':>7} {'od':>3}")
    for row in sweep_data[tname]:
        print(f"    {row['oav']:>5.2f} {row['lux']:>5.1f} {row['syn']:>5.1f} "
              f"{row['hed']:>5.1f} {row['clar']:>5.1f} {row['geo']:>7.3f} "
              f"{row['od']:>3d}")

# ── Pick the optimal OAV per trace (honoring synergy floor 94.5) ────
print("\n" + "="*72)
print(" OPTIMAL OAV PER TRACE (synergy ≥ 94.5, no overdoses,")
print("                        maximize luxury+hedonic combined)")
print("="*72)
best_oavs = {}
for tname, rows in sweep_data.items():
    viable = [r for r in rows if r["syn"] >= 94.5 and r["od"] == 0]
    if not viable:
        best_oavs[tname] = 0.3
        print(f"  {tname}: no viable dose — fallback OAV=0.3")
        continue
    # maximize (lux + 0.5*hed + 0.2*clar)
    best = max(viable, key=lambda r: r["lux"] + 0.5*r["hed"] + 0.2*r["clar"])
    best_oavs[tname] = best["oav"]
    print(f"  {tname}: OAV={best['oav']}  "
          f"lux={best['lux']:.1f} hed={best['hed']:.1f} clar={best['clar']:.1f} "
          f"syn={best['syn']:.1f}  geo={best['geo']:.3f}")

# Apply combination
final = copy.deepcopy(SPEC)
for tname, t in V5_TRACES.items():
    oav = best_oavs[tname]
    if oav == 0.0:
        if tname in final: del final[tname]
    else:
        final[tname] = {"ppm": t["odt"] * oav, "dil": t["dil"], "role": t["role"]}
r_final = score_spec(final, 10.0)
print_result("v5 FINAL (combined optimal per-trace doses)", r_final, final)

# ── Honest comparison ───────────────────────────────────────────────
print("\n" + "="*72)
print(" v3 → v5 HONEST COMPARISON")
print("="*72)
print(f"  {'marker':<20} {'v3':>8} {'v5':>8} {'Δ':>7}")
for a in ["luxury","longevity","sillage","texture","stacking_depth","synergy",
          "hedonic","skin_performance","perceptual_clarity"]:
    d = r_final["axes"][a] - v3_ax[a]
    print(f"  {a:<20} {v3_ax[a]:>8.1f} {r_final['axes'][a]:>8.1f} {d:>+7.2f}")
dg = r_final["geo"] - v3_data["geo"]
print(f"  {'GEO':<20} {v3_data['geo']:>8.3f} {r_final['geo']:>8.3f} {dg:>+7.3f}")

# ── Scorer responsiveness diagnosis ─────────────────────────────────
print("\n" + "="*72)
print(" SCORER RESPONSIVENESS DIAGNOSIS")
print("="*72)
print(" A material is 'responsive' if its sweep shows ANY axis delta ≥ 0.1")
print(" between OAV 0.0 and OAV 2.0.")
print()
for tname, rows in sweep_data.items():
    r0 = next(r for r in rows if r["oav"] == 0.0)
    r2 = next(r for r in rows if r["oav"] == 2.0)
    deltas = {k: r2[k] - r0[k] for k in ("lux", "syn", "hed", "clar", "geo")}
    responsive = any(abs(v) >= 0.1 for v in deltas.values())
    flag = "RESPONSIVE" if responsive else "inert    "
    print(f"  {flag}  {tname:22s}  "
          f"Δlux={deltas['lux']:+.2f}  Δsyn={deltas['syn']:+.2f}  "
          f"Δhed={deltas['hed']:+.2f}  Δclar={deltas['clar']:+.2f}  "
          f"Δgeo={deltas['geo']:+.3f}")

# ── MD REPORT ────────────────────────────────────────────────────────
BATCHES = [5.0, 10.0, 30.0, 100.0]
md = []
md += ["# Iris Dreamweaver v5 — Two-Directional Sub-ODT Layer", ""]
md += ["## Methodology",
       "",
       "Per user guidance, every sub-ODT trace must reinforce TWO existing",
       "accord vectors in the v3 SPEC, not add a new direction. Below are the",
       "5 picks with concrete perfumery justification. Each was dose-swept",
       "0.0→2.0 OAV; the optimal dose was chosen under the hard constraints",
       "synergy ≥ 94.5 and no new overdoses, maximizing luxury + 0.5·hedonic",
       "+ 0.2·clarity.", ""]

md += ["## The five picks (two-directional justifications)", ""]
for name, t in V5_TRACES.items():
    md.append(f"### {name}")
    md.append(f"- **Role:** {t['role']}")
    md.append(f"- **ODT (ppm in ethanol):** {t['odt']}")
    md.append(f"- **Two-directional rationale:** {t['rationale']}")
    md.append(f"- **Chosen OAV:** {best_oavs[name]}  "
              f"(ppm = {t['odt'] * best_oavs[name]:.5f})")
    md.append("")

md += ["## Per-trace dose sweep results", ""]
for tname, rows in sweep_data.items():
    md.append(f"### {tname}")
    md.append("")
    md.append("| OAV | lux | syn | hed | clar | geo | od |")
    md.append("|--:|--:|--:|--:|--:|--:|--:|")
    for r in rows:
        md.append(f"| {r['oav']:.2f} | {r['lux']:.1f} | {r['syn']:.1f} | "
                  f"{r['hed']:.1f} | {r['clar']:.1f} | {r['geo']:.3f} | {r['od']} |")
    md.append("")

md += ["## v3 → v5 brief-marker comparison", "",
       "| Marker | v3 | v5 | Δ |", "|---|--:|--:|--:|"]
for a in ["luxury","longevity","sillage","texture","stacking_depth","synergy",
          "hedonic","skin_performance","perceptual_clarity"]:
    d = r_final["axes"][a] - v3_ax[a]
    md.append(f"| {a} | {v3_ax[a]:.1f} | {r_final['axes'][a]:.1f} | {d:+.2f} |")
md.append(f"| **geo** | **{v3_data['geo']:.3f}** | **{r_final['geo']:.3f}** | "
          f"**{r_final['geo']-v3_data['geo']:+.3f}** |")
md.append("")

md += ["## Scorer responsiveness (honest finding)", "",
       "A trace is 'responsive' if the scorer shifts ≥ 0.1 on any axis",
       "between OAV 0.0 and OAV 2.0.", "",
       "| Trace | Status | Δlux | Δsyn | Δhed | Δclar | Δgeo |",
       "|---|---|--:|--:|--:|--:|--:|"]
for tname, rows in sweep_data.items():
    r0 = next(r for r in rows if r["oav"] == 0.0)
    r2 = next(r for r in rows if r["oav"] == 2.0)
    deltas = {k: r2[k] - r0[k] for k in ("lux","syn","hed","clar","geo")}
    responsive = any(abs(v) >= 0.1 for v in deltas.values())
    status = "RESPONSIVE" if responsive else "inert"
    md.append(f"| {tname} | {status} | {deltas['lux']:+.2f} | "
              f"{deltas['syn']:+.2f} | {deltas['hed']:+.2f} | "
              f"{deltas['clar']:+.2f} | {deltas['geo']:+.3f} |")
md.append("")

md += ["## Final formula — full ppm / batch table", "",
       "| Material | Role | ppm | Dilution | 5 mL µL | 10 mL µL | 30 mL µL | 100 mL µL |",
       "|---|---|--:|---|--:|--:|--:|--:|"]
rows_by_batch = {b: spec_to_ingredients(final, b)[0] for b in BATCHES}
for name, d in final.items():
    dil_s = "neat" if d["dil"] == 1.0 else f"{d['dil']*100:.1f}%"
    ppm_s = f"{d['ppm']:.5f}" if d["ppm"] < 1 else f"{d['ppm']:,.0f}"
    cells = []
    for b in BATCHES:
        v = rows_by_batch[b][name]
        cells.append(f"{v:.4f}" if v < 1 else f"{v:.2f}")
    md.append(f"| {name} | {d['role']} | {ppm_s} | {dil_s} | " + " | ".join(cells) + " |")
md.append("| **Concentrate** | | | | " + " | ".join(
    f"**{sum(rows_by_batch[b].values()):.1f}**" for b in BATCHES) + " |")
md.append("")

out = "formulas/collections/Iris_Dreamweaver_v5_ppm.md"
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(md))
with open("formulas/collections/Iris_Dreamweaver_v5_ppm.json", "w", encoding="utf-8") as f:
    json.dump({"spec": final, "axes": r_final["axes"], "geo": r_final["geo"],
               "v3_axes": v3_ax, "v3_geo": v3_data["geo"],
               "best_oavs": best_oavs, "sweep": sweep_data}, f, indent=2)
print(f"\n✓ Saved: {out}")
print(f"✓ Saved: formulas/collections/Iris_Dreamweaver_v5_ppm.json")
