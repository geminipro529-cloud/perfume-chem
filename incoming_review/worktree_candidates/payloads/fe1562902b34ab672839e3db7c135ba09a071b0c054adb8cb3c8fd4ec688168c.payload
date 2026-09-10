from pathlib import Path
import math
import sys
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from recon import rank_prior, bounded_normalize, canonical_name, choose_stock_fraction


def test_rank_prior_total():
    values = rank_prior(range(1, 71), 4500, 0.7)
    assert math.isclose(sum(values), 4500, rel_tol=1e-12)
    assert values[0] > values[-1]


def test_bounded_normalize():
    values = bounded_normalize([10, 5, 1], [0, 2, 0], [6, 10, 10], 12)
    assert math.isclose(sum(values), 12, rel_tol=1e-12)
    assert values[0] <= 6
    assert values[1] >= 2


def test_canonical_name():
    assert canonical_name("Cedarwood Virginia Oil") == canonical_name("Cedarwood-Virginia oil")


def test_dilution_choice():
    assert choose_stock_fraction(0.05, 5, 100) in {0.01, 0.001}
