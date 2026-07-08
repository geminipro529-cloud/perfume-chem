"""Diagnostic: what happens in pass 1?"""
from __future__ import annotations
import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try: sys.stdout.reconfigure(encoding="utf-8", line_buffering=True, write_through=True)
except Exception: pass

from engine.optimizer.scoring import FormulaScorer
from engine.optimizer.oav_guard import check_proportional_scaling
from engine.synergy_graph import SynergyGraph
from _scale_30mL_verify_nonlinear import score_formula, BATCH_ML
from _opt_photoreal_iris_10x import FIRST_EDITION_ING, FIRST_EDITION_DIL

sg = SynergyGraph()
scorer = FormulaScorer(synergy_graph=sg, batch_volume_ml=BATCH_ML)
base_geo, base_detail = score_formula(FIRST_EDITION_ING, FIRST_EDITION_DIL, scorer)
print(f"Baseline geo: {base_geo:.4f}")

tests = [
    ("Hedione", +240), ("Hedione", -240), ("Hedione", +480),
    ("Alpha Irone", +60), ("Alpha Irone", -60),
    ("Myristic Acid", -500), ("Myristic Acid", +500),
    ("IPM", -300), ("IPM", +300),
    ("Habanolide", +120), ("Habanolide", -120),
    ("Ebanol", +120), ("Iso E Super", +120), ("Iso E Super", -120),
    ("Ethylene Brassylate", +120), ("Benzyl Salicylate" if False else "Musk Ketone", +60),
    ("Orivone", -60), ("Koavone", +60), ("Azarbre", +60),
    ("Romandolide", +60),
]
for name, step in tests:
    if name not in FIRST_EDITION_ING: continue
    trial = dict(FIRST_EDITION_ING)
    new_val = trial[name] + step
    if new_val < 1: continue
    trial[name] = new_val
    rev = check_proportional_scaling(trial, FIRST_EDITION_DIL, BATCH_ML, 15.0)
    errs = sum(1 for c in rev if c.severity == "error")
    geo, det = score_formula(trial, FIRST_EDITION_DIL, scorer)
    flag = "ERR" if errs else "   "
    print(f"  {flag} {name:24s} {step:+5d} → geo {geo:7.4f} (Δ{geo-base_geo:+.4f}) [{errs} oav-err]")
