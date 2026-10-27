"""Hand-pinned rank targets, tie-neutral groups, temporal guards and model parity.

Inputs: invented examples; optional frozen local run for exact replay.
Outputs: assertions, no external service or source-data writes.
Identity: midpoint percentile ranks, fractional tie overlap, mean-loss ridge.
Tier: 2 support. Run project Python -m pytest tests/test_ranking_no_llm.py.
"""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

PATH = Path(__file__).parents[1] / 'scripts/ml_experiment/run_ranking_no_llm.py'
SPEC = importlib.util.spec_from_file_location('ranking_no_llm', PATH)
ranking = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ranking)


def test_midpoint_rank_target_ties_and_magnitude_invariance():
    # Ranks [1.5,1.5,3,4] -> (rank-.5)/4, with mean .5.
    actual = ranking.percentile_target([10, 10, 30, 50])
    assert actual == [.25, .25, .625, .875]
    assert sum(actual) / 4 == .5
    assert ranking.percentile_target([10, 10, 30, 1_000_000]) == actual
    assert ranking.percentile_target([5, 5]) == [.5, .5]


def test_fractional_ties_have_hand_computed_group_means_and_spread():
    # Two bottom-score ties share Q1 and Q2 equally: both means (0+2)/2=1.
    groups, weights = ranking.quintiles([0, 2, 4, 6, 8], [0, 0, 1, 2, 3])
    assert [g['mean_excess'] for g in groups] == [1, 1, 4, 6, 8]
    assert weights[0] == [.5, .5, 0, 0, 0]
    assert weights[1] == weights[0]
    assert [g['event_weight'] for g in groups] == [1] * 5
    assert groups[4]['mean_excess'] - groups[0]['mean_excess'] == 7


def test_constant_forecasts_do_not_create_spurious_quintile_spreads():
    y = [-2, 0, 3, 5, 9, 15]
    groups, weights = ranking.quintiles(y, [1] * 6)
    assert [g['mean_excess'] for g in groups] == pytest.approx([5] * 5)
    assert [g['event_weight'] for g in groups] == pytest.approx([1.2] * 5)
    assert np.asarray(weights) == pytest.approx(np.full((6, 5), .2))
    assert ranking.spearman(y, [1] * 6) is None


def test_tie_order_permutation_invariance_and_thin_group_accounting():
    y, scores = [2, -1, 7, 4, 8, 9, -2], [0, 0, 1, 1, 1, 2, 3]
    groups, _ = ranking.quintiles(y, scores)
    p = [3, 1, 5, 0, 6, 4, 2]
    shuffled, _ = ranking.quintiles([y[i] for i in p], [scores[i] for i in p])
    assert [g['mean_excess'] for g in groups] == pytest.approx([g['mean_excess'] for g in shuffled])
    _, weights = ranking.quintiles([0, 10], [0, 1])
    assert np.asarray(weights).sum(axis=0) == pytest.approx([.4] * 5)


@pytest.mark.parametrize('y,s', [([], []), ([1], [1, 2]), ([float('nan')], [1]), ([1], [float('inf')])])
def test_quintile_invalid_data_refused(y, s):
    with pytest.raises(ValueError):
        ranking.quintiles(y, s)


def test_rank_target_refuses_missing_labels():
    for values in [[], [1, None], [1, float('inf')]]:
        with pytest.raises(ValueError):
            ranking.percentile_target(values)


def test_forecast_hand_pins_and_saved_tree_parity_without_later_outcomes():
    # Raw ridge: b=1,beta=.5. Rank ridge: b=.5,beta=.125.
    x, y = [[-1], [1]], [0, 2]
    scores, state = ranking.forecast(x, y, x)
    assert scores['ridge_return'] == pytest.approx([.5, 1.5])
    assert scores['ridge_rank'] == pytest.approx([.375, .625])
    assert scores['tree_rank'] == [.5, .5]  # min leaf20 precludes splitting 2 rows.
    assert ranking.predict_tree(state['tree_rank'], x) == scores['tree_rank']
    assert x == [[-1], [1]] and y == [0, 2]


def test_saved_tree_float64_threshold_is_not_rounded_to_float32():
    state = {'children_left': [1, -1, -1], 'children_right': [2, -1, -1],
             'feature': [0, -2, -2], 'threshold': [float(np.nextafter(1., 0.)), -2, -2],
             'value': [0, 10, 20], 'n_features': 1}
    assert ranking.predict_tree(state, [[1.]]) == [20]


def test_training_labels_must_be_completed_strictly_before_origin():
    rows = [{'row_id': 'done', 'entry': '2018-01-01', 'label_end': '2020-12-31'},
            {'row_id': 'cutoff', 'entry': '2019-01-01', 'label_end': '2021-01-01'},
            {'row_id': 'later', 'entry': '2021-01-04', 'label_end': '2022-01-04'}]
    assert ranking.split_rows(rows, 2021) == (['done'], ['later'])


def test_protocol_fixed_budget_and_no_unvalidated_features():
    p = json.loads(ranking.PROTOCOL.read_text())
    assert [m['name'] for m in p['models']] == ranking.MODELS
    assert p['models'][2]['lambda'] == p['models'][3]['lambda'] == 1
    assert {k: p['models'][4][k] for k in ranking.TREE_CONFIG} == ranking.TREE_CONFIG
    assert p['targets']['252']['prediction_years'] == [2020, 2021, 2022, 2023]
    assert 'No LLM labels, Bloomberg workbook' in p['inputs']
    assert 'No grid search' in p['budget']


def test_optional_real_archive_replay_and_prediction_before_scoring():
    if not (ranking.RUN / 'prefit-manifest.json').exists():
        pytest.skip('Local prefit archive absent; synthetic checks still run in CI')
    events = []
    original = ranking.score

    def wrapped(*args):
        events.append('evaluation')
        return original(*args)

    ranking.score = wrapped
    try:
        first, summary = ranking.build(lambda name, payload: events.append(name))
        second, replay = ranking.build()
    finally:
        ranking.score = original
    assert first == second and summary == replay
    assert events.index('predictions.jsonl') < events.index('evaluation')
    assert summary['learned_fits'] == 21
    assert summary['evaluated_events_by_horizon'] == {'252': 411, '504': 302}
    assert summary['old_24_month_prediction_max_absolute_difference'] < 1e-10
