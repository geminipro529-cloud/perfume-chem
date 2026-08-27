"""Tests for engine.reconstruction.ensembles."""

from __future__ import annotations
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.reconstruction.ensembles import (
    generate_ensemble,
    CandidateFamily,
    AuthorityVector,
    scale_uncertainty_to_ensemble,
)


def test_generate_ensemble():
    names = [f"Mat{i}" for i in range(1, 11)]
    families = generate_ensemble(names, total_budget=4500.0, N=10)
    assert len(families) >= 4
    for f in families:
        assert isinstance(f, CandidateFamily)
        assert len(f.rank_prior) == 10
        assert sum(f.rank_prior.values()) > 4000  # near 4500


def test_authority_vector_not_averaged():
    av = AuthorityVector(identity=0.8, quantity=0.3, sensory=0.9)
    d = av.as_dict()
    assert isinstance(d, dict)
    # Should NOT have an "average" key
    assert "average" not in d
    assert "combined" not in d


def test_scale_uncertainty():
    base = {"A": 100, "B": 200, "C": 300}
    uncertainties = {"A": (80, 120), "B": (150, 250)}
    variants = scale_uncertainty_to_ensemble(base, uncertainties)
    assert len(variants) == 2
    assert variants[0]["A"] < 100  # low variant
    assert variants[1]["A"] > 100  # high variant
    assert variants[0]["C"] == 300  # unchanged
