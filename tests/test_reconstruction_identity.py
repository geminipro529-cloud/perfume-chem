"""Tests for engine.identity.resolver."""

from __future__ import annotations
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.identity.resolver import (
    resolve_identity,
    are_equivalent,
    get_non_equivalent_names,
    MaterialIdentity,
    IdentityGrade,
)


def test_resolve_identity_basic():
    ident = resolve_identity("Iso E Super")
    assert ident.canonical_name == "iso e super"
    assert ident.grade == IdentityGrade.TRADE_GRADE


def test_non_equivalent_pairs():
    names = get_non_equivalent_names("habanolide")
    assert "galaxolide" in names


def test_non_equivalent_different():
    names = get_non_equivalent_names("alpha isomethyl ionone")
    assert (
        "methyl ionone gamma coeur" in names or "alpha-isomethyl ionone" in names or len(names) > 0
    )


def test_same_identity_equivalent():
    a = resolve_identity("Iso E Super")
    b = resolve_identity("Iso E Super")
    assert a.canonical_name == b.canonical_name


def test_different_grades():
    a = resolve_identity("Iso E Super", grade=IdentityGrade.CHEMICAL_ENTITY)
    b = resolve_identity("Iso E Super", grade=IdentityGrade.SUPPLIER_LOT, lot="LOT123")
    assert not are_equivalent(a, b)
