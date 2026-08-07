"""Tests for engine.reconstruction.rank_prior."""

from __future__ import annotations
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from engine.reconstruction.rank_prior import generate_soft_rank_prior, RankPriorConfig


def test_empty_roster_raises():
    with pytest.raises(ValueError, match="cannot be empty"):
        generate_soft_rank_prior([], RankPriorConfig(N=10, B=1000, p=0.5))
    with pytest.raises(ValueError, match="positive"):
        generate_soft_rank_prior(["A"], RankPriorConfig(N=0, B=1000, p=0.5))
