"""Tests for engine.target.formula."""

from __future__ import annotations
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.target.formula import (
    TargetMaterial,
    TargetFormula,
    AuthorityVector,
    accept_target_version,
    create_target_from_rows,
    compute_target_hash,
    TIER_0_NOTE_INSPIRED,
    TIER_1_DOCUMENTARY_FUNCTIONAL_HYPOTHESIS,
)


def test_target_material_create():
    tm = TargetMaterial(identity="Iso E Super", active_amount_median=450.0)
    assert tm.identity == "Iso E Super"
    assert tm.active_amount_median == 450.0
    assert tm.active_amount_unit == "uL"


def test_authority_vector():
    av = AuthorityVector(identity=0.8, quantity=0.5, safety=0.9)
    d = av.as_dict()
    assert d["identity"] == 0.8
    assert d["safety"] == 0.9
    # No average
    assert "average" not in d


def test_accept_target():
    tm = TargetMaterial(identity="Iso E Super", active_amount_median=450.0)
    formula = TargetFormula(
        product_id="test_edt_2020",
        target_materials=(tm,),
        total_raw_ul=4500.0,
        total_active_ul=450.0,
    )
    accepted = accept_target_version(formula)
    assert accepted.accepted
    assert accepted.accepted_timestamp is not None


def test_create_target_from_rows():
    rows = [
        {
            "identity": "A",
            "raw_amount": 100.0,
            "concentration": 1.0,
            "concentration_basis": "w/w",
            "carrier": "",
            "functional_roles": ("character",),
            "accord_membership": (),
            "time_windows": ("opening",),
        },
        {
            "identity": "B",
            "raw_amount": 200.0,
            "concentration": 0.5,
            "concentration_basis": "v/v",
            "carrier": "DPG",
            "functional_roles": ("bridge",),
            "accord_membership": (),
            "time_windows": ("heart",),
        },
    ]
    formula = create_target_from_rows(rows)
    assert formula.total_raw_ul == 300.0
    assert len(formula.target_materials) == 2
    assert len(formula.formula_hash) == 64


def test_compute_target_hash_deterministic():
    tm = TargetMaterial(identity="A", active_amount_median=100.0)
    h1 = compute_target_hash([tm])
    h2 = compute_target_hash([tm])
    assert h1 == h2


def test_create_target_preserves_all_fields():
    rows = [
        {
            "identity": "Iso E Super",
            "raw_amount": 450.0,
            "concentration": 1.0,
            "concentration_basis": "w/w",
            "carrier": "",
            "functional_roles": ("character",),
            "accord_membership": ("woody_amber",),
            "time_windows": ("drydown",),
            "evidence_links": ("claim_001", "claim_002"),
            "identity_confidence": 0.9,
            "quantity_confidence": 0.7,
            "active_amount_p05": 400.0,
            "active_amount_p95": 500.0,
            "grade": "TRADE_GRADE",
        }
    ]
    formula = create_target_from_rows(rows)
    tm = formula.target_materials[0]
    assert tm.evidence_links == ("claim_001", "claim_002")
    assert tm.identity_confidence == 0.9
    assert tm.quantity_confidence == 0.7
    assert tm.active_amount_p05 == 400.0
    assert tm.active_amount_p95 == 500.0
    assert tm.grade == "TRADE_GRADE"


def test_tier_constants():
    assert TIER_0_NOTE_INSPIRED
    assert TIER_1_DOCUMENTARY_FUNCTIONAL_HYPOTHESIS
