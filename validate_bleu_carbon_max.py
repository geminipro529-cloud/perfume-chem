"""Validate Bleu Carbon Max Performance v3 — full pipeline."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import re
from engine.optimizer.models import FormulaVector
from engine.optimizer.scoring import FormulaScorer
from engine.family_scorer import FamilyAwareScorer
from engine.pipeline.gates import gate_formula
from engine.pipeline.formula_state import build_formula_state

def parse(path_str):
    text = Path(path_str).read_text(encoding="utf-8")
    ing, dil = {}, {}
    for line in text.split("\n"):
        m = re.match(r'\|\s*(\d+)\s*\|\s*\*?\*?(.+?)\*?\*?\s*\|\s*(.+?)\s*\|\s*\*?\*?([\d,.]+)\*?\*?\s*\|', line)
        if m:
            name = m.group(2).strip().replace("**","").replace("*","")
            dil_raw = m.group(3).strip().lower()
            try: amount = float(m.group(4).replace(",",""))
            except: continue
            if any(x in name.lower() for x in ("ethanol","total","dilution","subtotal","material","---","#","role")): continue
            if not name: continue
            name = re.sub(r'\s*\(.*?\)','',name).strip()
            ing[name] = amount
            dm = re.match(r"(\d+(?:\.\d+)?)\s*%", dil_raw)
            dil[name] = float(dm.group(1))/100.0 if dm else 1.0
    total = sum(ing.values())
    pct = {n:(v/total)*100 for n,v in ing.items()}
    return ing, dil, total, pct

SEP = "=" * 80
DIV = "-" * 80

# Parse
v1_ing, v1_dil, v1_tot, v1_pct = parse("formulas/complete/Bleu_Carbon_Final_2026-05-08.md")
v3_ing, v3_dil, v3_tot, v3_pct = parse("formulas/complete/Bleu_Carbon_Max_Performance_30mL_EDP.md")

print(SEP)
print("  BLEU CARBON — v1 vs v3 MAX PERFORMANCE")
print(SEP)
print(f"  v1: {len(v1_ing)} mat, {v1_tot:.0f} uL ({v1_tot/30000*100:.1f}%)")
print(f"  v3: {len(v3_ing)} mat, {v3_tot:.0f} uL ({v3_tot/30000*100:.1f}%)")

new_mats = {n for n in v3_ing if n not in v1_ing}
boosted = {n for n in v3_ing if n in v1_ing and v3_ing[n] > v1_ing[n]}
cut = {n for n in v3_ing if n in v1_ing and v3_ing[n] < v1_ing[n]}
removed = {n for n in v1_ing if n not in v3_ing}
print(f"  New: {len(new_mats)} — {', '.join(sorted(new_mats))}")
print(f"  Boosted: {len(boosted)}, Cut: {len(cut)}, Removed: {len(removed)}")

# Score
axes = ["longevity","sillage","synergy","luxury","texture",
        "stacking_depth","skin_performance","hedonic","perceptual_clarity","photorealism"]
scorer = FormulaScorer()
fam = FamilyAwareScorer()

v1_fv = FormulaVector(ingredients=v1_pct, dilutions=v1_dil)
v3_fv = FormulaVector(ingredients=v3_pct, dilutions=v3_dil)

v1_s = scorer.score(v1_fv)
v3_s = scorer.score(v3_fv)
v1_f = fam.score(v1_fv, family="fougere")
v3_f = fam.score(v3_fv, family="fougere")

print(f"\n{DIV}")
print(f"  {'Axis':<22} {'v1 Gen':>8} {'v3 Gen':>8} {'Delta':>8} │ {'v1 Foug':>8} {'v3 Foug':>8} {'Delta':>8}")
print(f"  {'-'*22} {'-'*8} {'-'*8} {'-'*8} ┼ {'-'*8} {'-'*8} {'-'*8}")

for ax in axes:
    g1 = v1_s.get(ax,0); g3 = v3_s.get(ax,0)
    f1 = v1_f.get(ax,0); f3 = v3_f.get(ax,0)
    dg = g3-g1; df = f3-f1
    print(f"  {ax:<22} {g1:>8.1f} {g3:>8.1f} {dg:>+8.1f} │ {f1:>8.1f} {f3:>8.1f} {df:>+8.1f}")

g1t=v1_s.get("geometric_total",0); g3t=v3_s.get("geometric_total",0)
f1t=v1_f.get("geometric_total",0); f3t=v3_f.get("geometric_total",0)
print(f"\n  {'Geometric':<22} {g1t:>8.1f} {g3t:>8.1f} {g3t-g1t:>+8.1f} │ {f1t:>8.1f} {f3t:>8.1f} {f3t-f1t:>+8.1f}")

# Gates
print(f"\n{DIV}")
print("  v3 GATE REPORT")
print(DIV)
try:
    fd = {"ingredients_ul": v3_ing, "dilutions": v3_dil, "family_archetype": "aromatic_fougere.modern_mineral"}
    rep = gate_formula(fd)
    fails = [g for g in rep.gates if g.status == "FAIL"]
    warns = [g for g in rep.gates if g.status == "WARN"]
    passes = [g for g in rep.gates if g.status == "PASS"]
    print(f"  STATUS: {rep.status} ({len(passes)}P / {len(warns)}W / {len(fails)}F)")
    if fails:
        print(f"  FAILURES:")
        for g in fails: print(f"    [{g.status}] {g.gate:<30} {str(g.detail)[:100]}")
    if warns:
        print(f"  WARNINGS:")
        for g in warns: print(f"    [{g.status}] {g.gate:<30} {str(g.detail)[:100]}")
except Exception as e:
    print(f"  [ERROR] {e}")

# Headspace OAV top 10
print(f"\n{DIV}")
print("  v3 HEADSPACE OAV — TOP 10")
print(DIV)
try:
    st = build_formula_state(ingredients_ul=v3_ing, dilutions=v3_dil, temperature_K=298.15, batch_volume_ml=30.0)
    ranked = sorted([(ms.name, (ms.oav or 0)) for ms in st.materials if (ms.oav or 0) > 0], key=lambda x: -x[1])
    for i,(nm,ov) in enumerate(ranked[:10],1):
        print(f"  {i:>2}. {nm:<35} OAV={ov:>8.1f}")
    # Count
    n_perc = sum(1 for ms in st.materials if (ms.oav or 0) >= 1)
    n_sub = sum(1 for ms in st.materials if 0 < (ms.oav or 0) < 1)
    print(f"\n  {n_perc} perceptible, {n_sub} subliminal, {len(st.materials)} total")
except Exception as e:
    print(f"  [ERROR] {e}")

print(f"\n{SEP}")
print("  v3 VALIDATION COMPLETE")
print(SEP)
