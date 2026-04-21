from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import sys; sys.path.insert(0, ".")
from engine.optimizer.models import FormulaVector
from engine.optimizer.scoring import FormulaScorer
formula = {
    "Helional": 3.0, "Cyclamal": 2.5, "Dihydromyrcenol": 4.0, "Alpha Irone 30%": 1.0,
    "Alpha Isomethyl Ionone": 8.0, "Alpha Ionone": 4.0, "Beta Ionone": 3.0,
    "Dihydro Beta Ionone": 2.5, "Orivone": 2.5, "Ultralia": 3.0, "Koavone": 2.0,
    "Hedione HC": 2.0, "Ambroxan 30%": 1.5, "Myristic Acid": 2.0,
    "Galaxolide 50%": 2.5, "Habanolide": 2.0
}
total_parts = sum(formula.values())
pct_formula = {k: (v / total_parts) * 100 for k, v in formula.items()}
dilutions = {"Alpha Irone 30%": 30, "Ambroxan 30%": 30, "Galaxolide 50%": 50}
fv = FormulaVector(ingredients=pct_formula, dilutions=dilutions)
scorer = FormulaScorer()
scores = scorer.score(fv)
print(f"Scoring: Opus V Iris Accord Pure Crystalline V1: Classic Crystal ({total_parts} parts total)")
for k in sorted(scores.keys()):
    v = scores[k]
    if isinstance(v, (int, float)):
        print(f"{k:25s}: {v:.1f}")