import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCORE_SCRIPT = """
import json
from engine.confidence import ConfidenceScorer
from engine.optimizer.models import FormulaVector
from engine.optimizer.scoring import FormulaScorer

ingredients = {
    "Iso E Super": 200.0,
    "Patchouli EO": 70.0,
    "Hedione": 250.0,
}
payload = {
    "confidence": ConfidenceScorer().score(ingredients),
    "synergy": FormulaScorer().score_synergy(FormulaVector(ingredients=ingredients)),
}
print(json.dumps(payload, sort_keys=True))
"""


def _score_with_hash_seed(seed: int) -> dict:
    env = os.environ.copy()
    env["PYTHONHASHSEED"] = str(seed)
    completed = subprocess.run(
        [sys.executable, "-c", SCORE_SCRIPT],
        cwd=PROJECT_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return json.loads(completed.stdout)


def test_confidence_resolution_is_stable_across_python_hash_seeds():
    seed_two = _score_with_hash_seed(2)
    seed_four = _score_with_hash_seed(4)

    assert seed_two == seed_four
    assert set(seed_two["confidence"]["per_material"]) == {
        "Hedione",
        "Iso E Super",
        "Patchouli EO",
    }
