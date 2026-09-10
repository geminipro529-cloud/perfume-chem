"""Concentration-aware human mixture benchmark contracts."""

import numpy as np
import pandas as pd
import pytest

from scripts import train_odor_predictor as cli


def source_tables():
    compounds, stimuli, ratings, smiles = [], [], [], {}
    for index, structure in enumerate(['CC', 'CCC', 'CCCC', 'CCO', 'CCCO', 'CC=O']):
        smiles[str(index)] = structure
        for dose, fraction in enumerate([0.01, 0.1]):
            key = str(index * 2 + dose)
            compounds.append(dict(id=key, CID=str(index), dilution=fraction, solvent='pg'))
            stimuli.append(dict(id=key, components=key))
            ratings.append(dict(stimulus=key, Pleasantness=2 + dose * 4,
                                Intensity=3 + dose * 3))
    return pd.DataFrame(compounds), pd.DataFrame(stimuli), pd.DataFrame(ratings), smiles


def test_dose_changes_features_but_not_palette_and_equal_volume_accounting():
    assert hasattr(cli, 'dream_mixture_features')
    first = cli.dream_mixture_features([
        dict(smiles='CCO', nominal_fraction=.005), dict(smiles='CCCC', nominal_fraction=.05)])
    second = cli.dream_mixture_features([
        dict(smiles='CCCC', nominal_fraction=.005), dict(smiles='OCC', nominal_fraction=.05)])
    assert first['palette'] == second['palette']
    assert np.allclose(first['blind'], second['blind'])
    assert not np.allclose(first['aware'], second['aware'])
    c, s, r, mapping = source_tables()
    s.loc[0, 'components'] = '0;1'
    dataset = cli.prepare_dream_mixtures(c, s, r, mapping)
    assert dataset['rows'][0]['components'][0]['nominal_fraction'] == pytest.approx(.005)
    assert dataset['rows'][0]['components'][1]['nominal_fraction'] == pytest.approx(.05)


def test_palette_disjoint_models_learn_dose_without_measured_input_leakage():
    assert hasattr(cli, 'benchmark_dream_mixture')
    c, s, r, mapping = source_tables()
    result = cli.benchmark_dream_mixture(c, s, r, mapping, folds=3)
    for split in result['folds']:
        assert not set(split['train_palettes']) & set(split['test_palettes'])
    scores = result['endpoints']['Pleasantness']['models']
    assert scores['dose_aware']['rmse'] < scores['dose_blind']['rmse']
    ordering = scores['dose_aware']['same_solvent_palette_dose_ordering']
    assert ordering['n_pairs'] == 6
    assert ordering['correct'] == 6
    assert ordering['groups'] == 6
    assert len(ordering['pairs']) == 6
    assert ordering['pairs'][0]['observed_difference'] == pytest.approx(-4)
    assert scores['dose_blind']['same_solvent_palette_dose_ordering']['predicted_ties'] == 6
    prediction = cli.predict_dream_mixture(result['fitted_model'],
                                          [dict(smiles='CCO', nominal_fraction=.1)])
    assert np.isfinite(prediction['predictions']['Pleasantness'])
    assert prediction['formula_prediction_authority'] is False


def test_missing_structure_excludes_whole_mixture_not_component():
    assert hasattr(cli, 'prepare_dream_mixtures')
    c, s, r, mapping = source_tables()
    del mapping['0']
    result = cli.prepare_dream_mixtures(c, s, r, mapping)
    assert len(result['rows']) == 10
    assert len(result['excluded']) == 2


def test_missing_target_is_excluded_without_affecting_other_endpoint():
    assert hasattr(cli, 'benchmark_dream_mixture')
    c, s, r, mapping = source_tables()
    r.loc[0, 'Pleasantness'] = None
    result = cli.benchmark_dream_mixture(c, s, r, mapping, folds=3)
    assert result['endpoints']['Pleasantness']['n_observations'] == 11
    assert result['endpoints']['Intensity']['n_observations'] == 12


@pytest.mark.parametrize('fraction', [0, -1, float('nan')])
def test_invalid_nominal_fraction_rejected(fraction):
    assert hasattr(cli, 'dream_mixture_features')
    with pytest.raises(ValueError):
        cli.dream_mixture_features([dict(smiles='CCO', nominal_fraction=fraction)])
