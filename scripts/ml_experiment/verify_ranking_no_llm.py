"""Audit saved non-LLM ranking predictions by independent arithmetic.

Inputs: prefit snapshots, saved states/predictions, metric and allocation CSVs.
Output: verification.json; original sources and research forecasts unchanged.
Identity: SciPy rank correlation; each tie weight from counts below/equal score;
ridge coefficients from augmented least squares rather than normal equations.
Tier: 1. Run project Python scripts/ml_experiment/verify_ranking_no_llm.py.
"""
import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import rankdata, spearmanr

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_inputs import InputPreprocessor  # noqa: E402

RUN = ROOT / 'research/runs/ranking-no-llm/20261026-v1'


def load(name):
    return json.loads((RUN / name).read_text())


def main():
    manifest = load('prefit-manifest.json')
    for name, expected in manifest['source_sha256'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    for name, expected in manifest['prefit_files_sha256'].items():
        assert hashlib.sha256((RUN / name).read_bytes()).hexdigest() == expected, name
    for name, expected in load('provenance.json')['outputs_sha256'].items():
        assert hashlib.sha256((RUN / name).read_bytes()).hexdigest() == expected, name
    panels = load('inputs/panels.json')
    lookup = {(h, r['row_id']): r for h, rows in panels.items() for r in rows}
    predictions = [json.loads(line) for line in (RUN / 'predictions.jsonl').read_text().splitlines()]
    pred = {(str(p['horizon_sessions']), p['row_id']): p for p in predictions}
    assert len(pred) == len(predictions) == 713
    states = load('fitted-states.json')
    definitions = load('inputs/feature-dictionary.json')['features']
    preprocessing = load('inputs/preprocessing.json')
    coefficient_audits = 0
    for key, fold in states.items():
        horizon, year = key.split('/')
        cutoff = f'{year}-01-01'
        train = [lookup[(horizon, rid)] for rid in fold['training_row_ids']]
        later = [lookup[(horizon, rid)] for rid in fold['later_row_ids']]
        assert all(r['entry'] < cutoff and r['label_end'] < cutoff for r in train)
        assert all(cutoff <= r['entry'] < f'{int(year)+1}-01-01' for r in later)
        assert not set(fold['training_row_ids']) & set(fold['later_row_ids'])
        processor = InputPreprocessor(definitions, preprocessing['log1p_columns'])
        processor.state = fold['preprocessing']
        tx, lx = [np.asarray(processor.transform([r['features'] for r in rows])) for rows in [train, later]]
        raw_y = np.asarray([r['excess'] for r in train])
        rank_y = (rankdata(raw_y, method='average') - .5) / len(raw_y)
        assert np.array_equal(rank_y, fold['models']['training_rank_target'])
        for model, y in [('ridge_return', raw_y), ('ridge_rank', rank_y)]:
            xc, yc = tx - tx.mean(axis=0), y - y.mean()
            augmented = np.vstack([xc, math.sqrt(len(y)) * np.eye(tx.shape[1])])
            beta, *_ = np.linalg.lstsq(augmented, np.r_[yc, np.zeros(tx.shape[1])], rcond=None)
            intercept = y.mean() - tx.mean(axis=0) @ beta
            assert np.allclose(beta, fold['models'][model]['coefficients'], atol=1e-10, rtol=1e-10)
            expected = intercept + lx @ beta
            observed = [pred[(horizon, r['row_id'])]['scores'][model] for r in later]
            assert np.allclose(expected, observed, atol=1e-10, rtol=1e-10)
            coefficient_audits += 1
        tree = fold['models']['tree_rank']
        samples = defaultdict(list)
        for row, value in zip(tx, rank_y, strict=True):
            node, depth = 0, 0
            while tree['children_left'][node] != tree['children_right'][node]:
                depth += 1
                assert depth <= 2
                feature = tree['feature'][node]
                left = float(np.float32(row[feature])) <= tree['threshold'][node]
                node = tree['children_left'][node] if left else tree['children_right'][node]
            samples[node].append(value)
        for node, values in samples.items():
            assert len(values) == tree['n_node_samples'][node]
            assert len(values) >= 20
            assert math.isclose(float(np.mean(values)), tree['value'][node], abs_tol=1e-12)

    def read_csv(name):
        with (RUN / name).open(newline='') as stream:
            return list(csv.DictReader(stream))

    allocations = defaultdict(list)
    for r in read_csv('quintile-assignments.csv'):
        allocations[(r['sample'], r['horizon_sessions'], r['prediction_year'], r['model'])].append(r)
    metric_rows = read_csv('metrics.csv')
    group_rows = read_csv('quintiles.csv')
    for metric in metric_rows:
        key = tuple(metric[k] for k in ['sample', 'horizon_sessions', 'prediction_year', 'model'])
        rows = allocations[key]
        n = len(rows)
        assert n == int(metric['n'])
        scores = np.asarray([float(r['score']) for r in rows])
        y = np.asarray([lookup[(key[1], r['row_id'])]['excess'] for r in rows])
        for r, value in zip(rows, y, strict=True):
            assert float(r['excess']) == value
            assert float(r['score']) == pred[(key[1], r['row_id'])]['scores'][key[3]]
        if np.ptp(scores) == 0 or np.ptp(y) == 0:
            assert metric['spearman'] == ''
        else:
            assert math.isclose(float(metric['spearman']), float(spearmanr(y, scores).statistic), abs_tol=1e-12)
        means = []
        for q in range(5):
            weights = []
            for row, s in zip(rows, scores, strict=True):
                below, at_most = int(sum(scores < s)), int(sum(scores <= s))
                weight = max(0., min(at_most, (q+1)*n/5) - max(below, q*n/5)) / (at_most-below)
                assert math.isclose(weight, float(row[f'Q{q+1}_weight']), abs_tol=1e-12)
                weights.append(weight)
            assert math.isclose(sum(weights), n/5, abs_tol=1e-10)
            mean = float(np.dot(weights, y) / sum(weights))
            saved = next(g for g in group_rows if tuple(g[k] for k in ['sample', 'horizon_sessions', 'prediction_year', 'model']) == key and int(g['quintile']) == q+1)
            assert math.isclose(mean, float(saved['mean_excess']), abs_tol=1e-12)
            means.append(mean)
        assert math.isclose(100*(means[4]-means[0]), float(metric['top_minus_bottom_pp']), abs_tol=1e-10)
    summary = load('summary.json')
    assert summary['common_prediction_events_per_horizon'] == 297
    assert summary['old_24_month_prediction_max_absolute_difference'] == 0
    result = {'status': 'passed', 'source_and_prefit_hashes': 'unchanged',
              'distinct_event_horizon_predictions': len(pred), 'annual_model_metric_rows': len(metric_rows),
              'quintile_rows': len(group_rows), 'independent_ridge_audits': coefficient_audits,
              'chronology_folds': len(states), 'old_24_month_prediction_parity': 'exact',
              'rank_metric_parity': 'SciPy average ranks', 'tie_weight_parity': 'independent count formula',
              'source_financial_timing_certified': False, 'investment_edge_established': False}
    target = RUN / 'verification.json'
    payload = (json.dumps(result, sort_keys=True, indent=2) + '\n').encode()
    if target.exists():
        assert target.read_bytes() == payload
    else:
        target.write_bytes(payload)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
