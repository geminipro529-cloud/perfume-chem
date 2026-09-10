from types import SimpleNamespace

import pytest

from engine.pipeline.gates import (
    ReleaseGateConfig, _apply_guideline_policy, _gate_authority_vector,
    _result, _safe_gate, _status_from_gates,
    _gate_phototoxic_furanocoumarin, _gate_receptor_saturation,
)


@pytest.mark.parametrize('name', [
    'mode_protection', 'chassis_integrity', 'concentration_basis',
    'headspace_scope', 'authority_vector', 'solvent_matrix', 'safety_phototoxic',
    'future_unclassified_contract',
])
def test_architectural_failure_survives_aggregation_and_runtime_error(name):
    result = _apply_guideline_policy(_result(name, 'FAIL', 'Prerequisite violated'))
    assert _status_from_gates([result]) == 'FAIL'

    def broken():
        raise RuntimeError('missing dependency')

    assert _safe_gate(broken, name).status == 'FAIL'


@pytest.mark.parametrize('config,status', [
    (ReleaseGateConfig(), 'WARN'),
    (ReleaseGateConfig(commercial_mode=True), 'FAIL'),
    (ReleaseGateConfig(quantitative_claim=True), 'FAIL'),
    (ReleaseGateConfig(mode='RELEASE_REVIEW'), 'FAIL'),
])
def test_absent_ledger_is_unknown_and_blocks_requested_authority(config, status):
    gate = _apply_guideline_policy(_gate_authority_vector(SimpleNamespace(), config))
    assert gate.status == status
    assert gate.data['assessment'] == 'NOT_EVALUATED'
    assert gate.data['release_authority'] is False
    assert 'identity' not in gate.data


def test_stylistic_heuristic_remains_advisory():
    assert _apply_guideline_policy(_result('literature_compliance', 'FAIL')).status == 'WARN'


@pytest.mark.parametrize('commercial,status', [(False, 'WARN'), (True, 'FAIL')])
def test_phototoxicity_cannot_clear_or_convict_fcf_from_legacy_substring_rule(commercial, status):
    state = SimpleNamespace(materials=[SimpleNamespace(name='Grapefruit FCF oil Sicilian', active_ul=320)])
    result = _apply_guideline_policy(_gate_phototoxic_furanocoumarin(state, ReleaseGateConfig(commercial_mode=commercial)))
    assert result.status == status
    assert result.data['assessment'] == 'NOT_EVALUATED'
    assert result.data['release_authority'] is False
    assert 'bergaptene 0.5' not in result.detail


def test_retired_receptor_rule_never_claims_safe_or_overdose():
    result = _gate_receptor_saturation(SimpleNamespace(), ReleaseGateConfig())
    assert result.status == 'SKIP'
    assert result.data['release_authority'] is False
