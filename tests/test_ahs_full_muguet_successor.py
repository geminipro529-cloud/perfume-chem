"""Exact bottle lineage and unexecuted full-muguet design checks."""

import hashlib
import json
from pathlib import Path

import pytest

from engine.pipeline.formula_state import build_formula_state
from scripts.verify_formula_workflow import parse_formula_markdown

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT / 'formulas/records/AHS_UserBottle_L360_HCA120_P60_CONFIRMED_20260907.json'
CHILD = ROOT / 'formulas/records/AHS_FullMuguet_Completion_20260907.json'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def test_confirmed_parent_keeps_every_historical_row_and_corrects_identity_explicitly():
    parent = read(PARENT)
    source = ROOT / parent['source_record_path']
    assert hashlib.sha256(source.read_bytes()).hexdigest() == parent['source_record_sha256']
    old = read(source)['nominal_recipe']['ingredients']
    rows = parent['nominal_recipe']['ingredients']
    assert rows[:len(old)] == old
    assert len(rows) == 32
    assert sum(r['raw_ul'] for r in rows) == 5740
    names = {r['material']: r for r in rows}
    assert names['Hydroxycitronellal']['raw_ul'] == 120
    assert 'Hydroxycitronellol' not in names
    assert names['Coumarin']['stock_label'] == '20% in DEP; basis unspecified'
    assert parent['bottle_engine_event_committed'] is False


def test_full_module_only_adds_exact_declared_deltas_and_preserves_all_stocks():
    parent, child = read(PARENT), read(CHILD)
    assert hashlib.sha256(PARENT.read_bytes()).hexdigest() == child['immediate_parent_record_sha256']
    old = {r['material']: r for r in parent['nominal_recipe']['ingredients']}
    new = {r['material']: r for r in child['nominal_recipe']['ingredients']}
    delta = {r['material']: r['raw_ul'] for r in child['positive_delta']}
    assert len(new) == 34
    assert sum(delta.values()) == 600
    assert sum(r['raw_ul'] for r in new.values()) == 6340
    for name, row in old.items():
        assert new[name]['raw_ul'] == row['raw_ul'] + delta.get(name, 0)
        assert new[name]['stock_label'] == row['stock_label']
    assert new['Phenethyl Alcohol']['raw_ul'] == 180
    assert new['Florol']['raw_ul'] == 420
    assert set(new) - set(old) == {'Farnesol', 'Phenyl Ethyl Dimethyl Carbinol'}
    assert 30.84 + sum(delta.values()) / 1000 == pytest.approx(31.44)
    assert 5.14 + sum(delta.values()) / 6000 == pytest.approx(5.24)
    assert min(delta.values()) / 6 >= 10
    assert child['physical_action_reported_performed'] is False
    assert child['authority']['release'] == 'HOLD'


@pytest.mark.parametrize('stem,total,count', [
    ('AHS_UserBottle_L360_HCA120_P60_CONFIRMED_20260907', 5740, 32),
    ('AHS_FullMuguet_Completion_20260907', 6340, 34),
])
def test_complete_markdown_parser_matches_canonical_rows(stem,total,count):
    records = parse_formula_markdown(ROOT / 'formulas' / (stem + '.md'))
    assert len(records) == 1
    parsed = records[0]['ingredients_ul']
    assert len(parsed) == count
    assert sum(parsed.values()) == total
    assert parsed['Hydroxycitronellal'] == 120


def test_opaque_profile_kind_prevents_lilyreal_single_molecule_oav():
    build_formula_state.cache_clear()
    state = build_formula_state({'Lilyreal ND': 360.0, 'Hedione': 670.0})
    lily = next(m for m in state.materials if m.name == 'Lilyreal ND')
    assert lily.is_opaque_preblend is True
    assert lily.oav is None
    assert lily.sources['oav_model'] == 'unknown:composite_decomposition_missing'


def test_pedmc_neat_confirmation_is_preserved_without_fabricated_execution():
    receipt = read(ROOT / 'data/governance/inventory_user_confirmation_20260907_pedmc.json')
    assert receipt['source_quote'] == 'my PEDMC is neat'
    assert receipt['stock']['fraction'] == 1.0
    assert receipt['stock']['fraction_basis'] == 'neat'
    assert receipt['authority_limits']['physical_dose_performed'] is False
    child = read(CHILD)
    row = next(r for r in child['positive_delta'] if r['material'] == 'Phenyl Ethyl Dimethyl Carbinol')
    assert row['raw_ul'] == 120
    assert row['stock_confirmation_receipt'].endswith('inventory_user_confirmation_20260907_pedmc.json')
