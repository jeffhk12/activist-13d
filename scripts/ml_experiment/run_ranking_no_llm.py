"""Compare fixed non-LLM return/rank ridge and shallow-tree ranking models.

Inputs: frozen 667-row feature preview and exact 252/504-session saved outcomes.
Outputs: prefit snapshots, forecasts before evaluation, model/preprocessing states,
per-year ranking/quintile CSVs, matched-horizon checks and reproducibility hashes.
Identity: rank target=(average_rank(y)-.5)/n; rho=correlation of average ranks;
quintile mean=sum(w*y)/sum(w), with fractional allocation across score ties.
Tier: 2. Previously exposed chronological development, no paid endpoints or LLM.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python
 scripts/ml_experiment/run_ranking_no_llm.py --prepare | --fit | --verify
"""
import argparse
import csv
import hashlib
import io
import json
import math
import platform
import sys
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import scipy
import sklearn
from scipy.stats import rankdata, spearmanr
from sklearn.tree import DecisionTreeRegressor

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_ranking_scope import join_horizon, unique_index  # noqa: E402
from prepare_inputs import InputPreprocessor, split_rows  # noqa: E402
from run_baselines import (  # noqa: E402
    average_ranks,
    digest,
    encode,
    fit_ridge,
    predict_ridge,
    spearman,
)

RUN = ROOT / 'research/runs/ranking-no-llm/20261026-v1'
PREVIEW = ROOT / 'research/runs/ml-feature-preview/20261012-v1'
OUTCOMES = ROOT / 'research/runs/phase1-baseline/20260924-long-horizon-analysis-v1'
PROTOCOL = ROOT / 'research/protocol/ranking-no-llm-v1.json'
MODELS = ['constant', 'smaller_size', 'ridge_return', 'ridge_rank', 'tree_rank']
RIDGE_LAMBDA = 1.0
TREE_CONFIG = {'max_depth': 2, 'min_samples_leaf': 20, 'random_state': 1729}


def percentile_target(values):
    ranks = np.asarray(average_ranks(values))
    assert np.array_equal(ranks, rankdata(values, method='average'))
    return ((ranks - .5) / len(values)).tolist()


def quintiles(values, scores):
    """Fractionally allocate exact-score ties; arbitrary row order has no effect."""
    y, s = np.asarray(values, float), np.asarray(scores, float)
    if y.ndim != 1 or s.ndim != 1 or len(y) != len(s) or not len(y):
        raise ValueError('Empty or mismatched quintile vectors')
    if not np.isfinite(y).all() or not np.isfinite(s).all():
        raise ValueError('Nonfinite quintile data')
    n = len(y)
    weights = np.zeros((n, 5), float)
    order = np.argsort(s, kind='stable')
    start = 0
    while start < n:
        end = start + 1
        while end < n and s[order[end]] == s[order[start]]:
            end += 1
        for q in range(5):
            overlap = max(0., min(end, (q + 1) * n / 5) - max(start, q * n / 5))
            weights[order[start:end], q] = overlap / (end - start)
        start = end
    assert np.allclose(weights.sum(axis=1), 1, atol=1e-12)
    assert np.allclose(weights.sum(axis=0), n / 5, atol=1e-12)
    groups = [{'quintile': q + 1, 'event_weight': float(weights[:, q].sum()),
               'contributing_events': int(np.count_nonzero(weights[:, q])),
               'mean_excess': float(weights[:, q] @ y / weights[:, q].sum())}
              for q in range(5)]
    return groups, weights.tolist()


def tree_state(model):
    t = model.tree_
    return {'children_left': t.children_left.tolist(), 'children_right': t.children_right.tolist(),
            'feature': t.feature.tolist(), 'threshold': t.threshold.tolist(),
            'value': t.value[:, 0, 0].tolist(), 'n_node_samples': t.n_node_samples.tolist(),
            'n_features': model.n_features_in_, 'config': TREE_CONFIG}


def predict_tree(state, values):
    # sklearn coerces inputs to float32 but compares to a float64 threshold.
    x = np.asarray(values, dtype=np.float32)
    if x.ndim != 2 or x.shape[1] != state['n_features'] or not np.isfinite(x).all():
        raise ValueError('Invalid tree prediction input')
    predictions = []
    for row in x:
        node = 0
        while state['children_left'][node] != state['children_right'][node]:
            left = float(row[state['feature'][node]]) <= state['threshold'][node]
            node = state['children_left'][node] if left else state['children_right'][node]
        predictions.append(state['value'][node])
    return predictions


def forecast(training_x, training_y, later_x):
    """No later outcomes in this interface. The fixed 3-model budget is observable."""
    ranks = percentile_target(training_y)
    raw_state = fit_ridge(training_x, training_y, RIDGE_LAMBDA)
    rank_state = fit_ridge(training_x, ranks, RIDGE_LAMBDA)
    tree = DecisionTreeRegressor(**TREE_CONFIG).fit(training_x, ranks)
    saved_tree = tree_state(tree)
    tree_predictions = predict_tree(saved_tree, later_x)
    assert np.array_equal(tree_predictions, tree.predict(later_x))
    return {
        'ridge_return': predict_ridge(raw_state, later_x),
        'ridge_rank': predict_ridge(rank_state, later_x),
        'tree_rank': tree_predictions,
    }, {'ridge_return': raw_state, 'ridge_rank': rank_state, 'tree_rank': saved_tree,
        'training_rank_target': ranks}


def csv_bytes(rows):
    out = io.StringIO(newline='')
    writer = csv.DictWriter(out, fieldnames=list(rows[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode()


def prepare():
    if RUN.exists():
        raise ValueError('New run directory required; existing preparation is preserved')
    sources = {}

    def load(path, lines=False):
        sources[str(path.relative_to(ROOT))] = digest(path)
        return ([json.loads(line) for line in path.read_text().splitlines()]
                if lines else json.loads(path.read_text()))

    protocol = load(PROTOCOL)
    assert [m['name'] for m in protocol['models']] == MODELS
    prior = load(PREVIEW / 'provenance.json')
    tables = {}
    for name in ['features.jsonl', 'targets.jsonl', 'row-metadata.jsonl', 'feature-dictionary.json']:
        path = PREVIEW / name
        tables[name] = load(path, name.endswith('jsonl'))
        assert digest(path) == prior['outputs_sha256'][name], name
    features, metadata, old_targets = [tables[n] for n in ['features.jsonl', 'row-metadata.jsonl', 'targets.jsonl']]
    ids = [r['row_id'] for r in metadata]
    assert len(ids) == len(set(ids)) == 667
    assert all([r['row_id'] for r in table] == ids for table in [features, old_targets])
    for m in metadata:
        for key in ['entry', 'label_end', 'industry_as_of', 'market_cap_as_of']:
            date.fromisoformat(m[key])
        assert m['accepted_et'][:10] < m['entry']
        assert m['industry_as_of'] < m['accepted_et'][:10]
        assert m['market_cap_as_of'] < m['accepted_et'][:10]
    feature_index = unique_index(features, 'row_id')
    original_y = unique_index(old_targets, 'row_id')
    outcomes = load(OUTCOMES / 'outcomes.json')
    outcome_provenance = load(OUTCOMES / 'provenance.json')
    assert digest(OUTCOMES / 'outcomes.json') == outcome_provenance['outputs']['outcomes.json']
    preproc = load(ROOT / 'research/protocol/ml-preprocessing-v1.json')
    old_predictions = load(ROOT / 'research/runs/ml-baselines/20261015-v1/predictions.jsonl', True)
    old_evaluation = load(ROOT / 'research/runs/ml-baselines/20261015-v1/evaluation.json')
    panels, statuses = {}, {}
    for horizon in protocol['targets']:
        mapped, statuses[horizon] = join_horizon(metadata, outcomes['first_observed'][horizon]['russell'])
        panels[horizon] = []
        for m in metadata:
            if m['row_id'] not in mapped:
                continue
            y = mapped[m['row_id']]
            date.fromisoformat(y['exit'])
            assert y['entry'] <= y['exit']
            if horizon == '504':
                assert y['exit'] == m['label_end']
                assert y['excess'] == original_y[m['row_id']]['target_russell_excess_504']
            panels[horizon].append({**m, 'label_end': y['exit'],
                                    'features': feature_index[m['row_id']]['features'],
                                    'excess': y['excess'], 'benchmark': y['assigned_etf']})
    assert {h: len(p) for h, p in panels.items()} == {'252': 662, '504': 667}
    code_paths = [Path(__file__), ROOT / 'scripts/ml_experiment/run_baselines.py',
                  ROOT / 'scripts/ml_experiment/prepare_inputs.py',
                  ROOT / 'scripts/ml_experiment/audit_ranking_scope.py',
                  ROOT / 'tests/test_ranking_no_llm.py']
    for path in code_paths:
        sources[str(path.relative_to(ROOT))] = digest(path)
    environment = {'python': platform.python_version(), 'numpy': np.__version__,
                   'scipy': scipy.__version__, 'sklearn': sklearn.__version__,
                   'platform': platform.platform()}
    RUN.mkdir(parents=True)
    (RUN / 'inputs').mkdir()
    artifacts = {
        'inputs/panels.json': encode(panels), 'inputs/protocol.json': encode(protocol),
        'inputs/preprocessing.json': encode(preproc),
        'inputs/feature-dictionary.json': encode(tables['feature-dictionary.json']),
        'inputs/old-predictions.json': encode(old_predictions),
        'inputs/old-evaluation.json': encode(old_evaluation),
        'inputs/join-status.json': encode(statuses),
    }
    for path in code_paths:
        artifacts['code/' + str(path.relative_to(ROOT))] = path.read_bytes()
    for name, payload in artifacts.items():
        target = RUN / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    manifest = {'prepared_at_utc': datetime.now(timezone.utc).isoformat(),
                'status': 'prepared_before_fitting', 'environment': environment,
                'source_sha256': sources,
                'prefit_files_sha256': {n: hashlib.sha256(v).hexdigest() for n, v in artifacts.items()},
                'LLM_features': False, 'Bloomberg_features': False, 'expected_learned_fits': 21}
    (RUN / 'prefit-manifest.json').write_bytes(encode(manifest))
    return {'prepared': str(RUN), 'panels': {h: len(p) for h, p in panels.items()}, 'fits': 21}


def score(predictions, panels):
    target = {(h, r['row_id']): r['excess'] for h, rows in panels.items() for r in rows}
    metrics, group_rows, assignments = [], [], []

    def one_sample(rows, sample):
        for h, year in sorted({(p['horizon_sessions'], p['prediction_year']) for p in rows}):
            selected = [r for r in rows if r['horizon_sessions'] == h and r['prediction_year'] == year]
            y = [target[(str(h), r['row_id'])] for r in selected]
            for model in MODELS:
                values = [r['scores'][model] for r in selected]
                rho = spearman(y, values)
                if rho is not None:
                    assert math.isclose(rho, float(spearmanr(y, values).statistic), abs_tol=1e-12)
                groups, weights = quintiles(y, values)
                metrics.append({'sample': sample, 'horizon_sessions': h, 'prediction_year': year,
                                'model': model, 'n': len(y), 'spearman': rho,
                                'distinct_scores': len(set(values)),
                                'top_minus_bottom_pp': 100 * (groups[4]['mean_excess'] - groups[0]['mean_excess']),
                                'all_event_mean_excess_pp': 100 * float(np.mean(y))})
                for g in groups:
                    group_rows.append({'sample': sample, 'horizon_sessions': h, 'prediction_year': year,
                                       'model': model, **g, 'mean_excess_pp': 100 * g['mean_excess']})
                for p, actual, w in zip(selected, y, weights, strict=True):
                    assignments.append({'sample': sample, 'horizon_sessions': h, 'prediction_year': year,
                                        'row_id': p['row_id'], 'model': model, 'score': p['scores'][model],
                                        'excess': actual, **{f'Q{i+1}_weight': v for i, v in enumerate(w)}})

    one_sample(predictions, 'horizon_specific')
    ids_by_horizon = [{r['row_id'] for r in predictions if r['horizon_sessions'] == h} for h in [252, 504]]
    common = ids_by_horizon[0] & ids_by_horizon[1]
    one_sample([r for r in predictions if r['row_id'] in common], 'common_12_24')
    temporal = []
    for sample, h, model in sorted({(r['sample'], r['horizon_sessions'], r['model']) for r in metrics}):
        rows = [r for r in metrics if (r['sample'], r['horizon_sessions'], r['model']) == (sample, h, model)]
        correlations = [r['spearman'] for r in rows if r['spearman'] is not None]
        temporal.append({'sample': sample, 'horizon_sessions': h, 'model': model,
                         'years': len(rows), 'events': sum(r['n'] for r in rows),
                         'defined_spearman_years': len(correlations),
                         'median_year_spearman': float(np.median(correlations)) if correlations else None,
                         'minimum_year_spearman': min(correlations) if correlations else None,
                         'maximum_year_spearman': max(correlations) if correlations else None,
                         'positive_years': sum(v > 0 for v in correlations)})
    return {'metrics': metrics, 'quintiles': group_rows, 'assignments': assignments,
            'temporal_summary': temporal, 'common_prediction_events_per_horizon': len(common)}


def build(writer=None):
    manifest = json.loads((RUN / 'prefit-manifest.json').read_text())
    for name, sha in manifest['source_sha256'].items():
        assert digest(ROOT / name) == sha, f'Source changed: {name}'
    for name, sha in manifest['prefit_files_sha256'].items():
        assert digest(RUN / name) == sha, f'Frozen input changed: {name}'

    def load(name):
        return json.loads((RUN / 'inputs' / name).read_text())

    protocol, panels = load('protocol.json'), load('panels.json')
    definitions, preprocessing = load('feature-dictionary.json')['features'], load('preprocessing.json')
    assert [m['name'] for m in protocol['models']] == MODELS
    assert all(m.get('lambda', RIDGE_LAMBDA) == RIDGE_LAMBDA for m in protocol['models'])
    assert all(protocol['models'][4][k] == v for k, v in TREE_CONFIG.items())
    predictions, states, folds = [], {}, []
    for horizon, config in protocol['targets'].items():
        panel = panels[horizon]
        by_id = unique_index(panel, 'row_id')
        for year, expected in zip(config['prediction_years'], config['expected_train_later'], strict=True):
            train_ids, later_ids = split_rows(panel, year)
            assert [len(train_ids), len(later_ids)] == expected
            train, later = [[by_id[key] for key in ids] for ids in [train_ids, later_ids]]
            processor = InputPreprocessor(definitions, preprocessing['log1p_columns']).fit([r['features'] for r in train])
            x_train, x_later = [processor.transform([r['features'] for r in rows]) for rows in [train, later]]
            learned, fitted = forecast(x_train, [r['excess'] for r in train], x_later)
            states[f'{horizon}/{year}'] = {'preprocessing': processor.state, 'models': fitted,
                                         'training_row_ids': train_ids, 'later_row_ids': later_ids}
            for i, row in enumerate(later):
                scores = {'constant': 0., 'smaller_size': -math.log1p(row['features']['snapshot_security_market_cap_usd']),
                          **{model: float(values[i]) for model, values in learned.items()}}
                assert all(math.isfinite(v) for v in scores.values())
                predictions.append({'row_id': row['row_id'], 'horizon_sessions': int(horizon),
                                    'prediction_year': year, 'scores': scores})
            train_issuers = {r['issuer'] for r in train}
            train_reporters = {c for r in train for c in r['header_reporter_ciks']}
            folds.append({'horizon_sessions': int(horizon), 'prediction_year': year,
                          'training_events': len(train), 'later_events': len(later),
                          'latest_training_label_end': max(r['label_end'] for r in train),
                          'encoded_columns': len(processor.state['feature_names']),
                          'shared_issuers': len(train_issuers & {r['issuer'] for r in later}),
                          'later_events_with_training_reporter': sum(bool(set(r['header_reporter_ciks']) & train_reporters) for r in later),
                          'repeated_later_issuers': len(later) - len({r['issuer'] for r in later}),
                          'later_entry_month_counts': dict(sorted(Counter(r['entry'][:7] for r in later).items()))})
    # Old 24-month prediction parity precedes scoring any later outcomes.
    old = unique_index(load('old-predictions.json'), 'row_id')
    current = [p for p in predictions if p['horizon_sessions'] == 504]
    assert len(current) == len(old) == 302
    max_difference = max(abs(p['scores']['ridge_return'] - old[p['row_id']]['predictions']['ridge']) for p in current)
    assert max_difference < 1e-10
    artifacts = {'predictions.jsonl': b''.join(encode(p) for p in predictions),
                 'fitted-states.json': encode(states), 'folds.json': encode(folds)}
    if writer:
        for name, payload in artifacts.items():
            writer(name, payload)
    evaluation = score(predictions, panels)
    old_eval = load('old-evaluation.json')
    for row in evaluation['metrics']:
        if row['sample'] == 'horizon_specific' and row['horizon_sessions'] == 504 and row['model'] == 'ridge_return':
            assert math.isclose(row['spearman'], old_eval['by_prediction_year'][str(row['prediction_year'])]['ridge']['spearman'], abs_tol=1e-12)
    assignment_rows = evaluation.pop('assignments')
    summary = {'status': 'completed_chronological_development', 'no_LLM_features': True,
               'no_Bloomberg_features': True, 'learned_fits': len(states) * 3,
               'evaluated_events_by_horizon': {str(h): sum(p['horizon_sessions'] == h for p in predictions) for h in [252, 504]},
               'common_prediction_events_per_horizon': evaluation['common_prediction_events_per_horizon'],
               'old_24_month_prediction_max_absolute_difference': max_difference,
               'temporal_summary': evaluation['temporal_summary'],
               'independent_final_test': False, 'hyperparameters_tuned': False,
               'IID_confidence_intervals': False, 'economic_portfolio_result': False}
    artifacts.update({'evaluation.json': encode(evaluation), 'summary.json': encode(summary),
                      'metrics.csv': csv_bytes(evaluation['metrics']),
                      'quintiles.csv': csv_bytes(evaluation['quintiles']),
                      'quintile-assignments.csv': csv_bytes(assignment_rows)})
    artifacts['provenance.json'] = encode({'prefit_manifest_sha256': digest(RUN / 'prefit-manifest.json'),
                                         'outputs_sha256': {n: hashlib.sha256(v).hexdigest() for n, v in artifacts.items()}})
    return artifacts, summary


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--prepare', action='store_true')
    group.add_argument('--fit', action='store_true')
    group.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    if args.prepare:
        print(json.dumps(prepare(), indent=2))
        return
    if args.fit and (RUN / 'predictions.jsonl').exists():
        raise ValueError('Preserve previous fit; use --verify or a new version')

    def write(name, payload):
        target = RUN / name
        if target.exists() and target.read_bytes() != payload:
            raise ValueError(f'Refuse overwrite: {name}')
        if not target.exists():
            target.write_bytes(payload)

    artifacts, summary = build(write if args.fit else None)
    for name, payload in artifacts.items():
        if args.verify:
            assert (RUN / name).read_bytes() == payload, f'Replay mismatch: {name}'
        else:
            write(name, payload)
    print(json.dumps({k: v for k, v in summary.items() if k != 'temporal_summary'}, indent=2))


if __name__ == '__main__':
    main()
