"""Assess existing outcome coverage for an initial 13D ML experiment.

Inputs: frozen long-horizon outcomes/provenance and factual selection/receipts.
Outputs: dated coverage and candidate chronological-fold JSON/CSV, no model fits.
Identity: usable candidates = valid Russell labels with one prepared filing;
training at date d requires entry < d and scheduled exit < d. Counts are events.
Tier: 1
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python
     scripts/ml_experiment/assess_existing_labels.py --output RUN [--verify]
"""

import argparse
import csv
import hashlib
import io
import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'research/runs/phase1-baseline/20260924-long-horizon-analysis-v1'
FACTS = ROOT / 'research/runs/phase2-overnight/20260924-full-v1'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def valid_label(row):
    value = row.get('excess')
    return (row.get('status') == 'calculated_common_sample'
            and isinstance(value, (int, float)) and math.isfinite(value))


def split_at(rows, year):
    cutoff, end = f'{year}-01-01', f'{year + 1}-01-01'
    train = [r for r in rows if r['entry'] < cutoff and r['exit'] < cutoff]
    test = [r for r in rows if cutoff <= r['entry'] < end]
    return train, test


def self_checks():
    # Two older entries, but only one has a completed label on Jan 1, 2021.
    # An exit exactly at the cutoff is not known strictly before that cutoff.
    sample = [dict(entry='2018-01-01', exit='2020-12-31'),
              dict(entry='2019-01-01', exit='2021-01-01'),
              dict(entry='2021-01-04', exit='2023-01-04')]
    train, test = split_at(sample, 2021)
    assert (len(train), len(test)) == (1, 1)
    assert train[0]['entry'] == '2018-01-01'
    assert valid_label(dict(status='calculated_common_sample', excess=0.0))
    assert not valid_label(dict(status='assignment:no_constituent_match', excess=None))
    assert not valid_label(dict(status='calculated_common_sample', excess=float('nan')))


def csv_bytes(rows):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def assess():
    inputs = {}
    outcome_path = BASE / 'outcomes.json'
    provenance = json.loads((BASE / 'provenance.json').read_text())
    actual = digest(outcome_path)
    if actual != provenance['outputs']['outcomes.json']:
        raise ValueError('Frozen outcome hash mismatch')
    for path in [outcome_path, BASE / 'provenance.json', FACTS / 'selection.json',
                 FACTS / 'progress.json', Path(__file__)]:
        inputs[str(path.relative_to(ROOT))] = digest(path)
    selection = json.loads((FACTS / 'selection.json').read_text())
    selected = {r['accession']: r for r in selection}
    assert len(selected) == len(selection) == 15813
    outcomes = json.loads(outcome_path.read_text())['first_observed']
    receipt_cache = {}

    def prepared(accession):
        if accession not in selected:
            return False
        if accession not in receipt_cache:
            path = FACTS / 'receipts' / f'{accession}.json'
            receipt = json.loads(path.read_text())
            if receipt['status'] != 'processed':
                raise ValueError(f'Unprocessed receipt: {accession}')
            if receipt['source_sha256'] != selected[accession]['source_sha256']:
                raise ValueError(f'Source provenance mismatch: {accession}')
            fact_path = FACTS / 'facts' / f'{accession}.json.gz'
            fact_hash = digest(fact_path)
            if fact_hash != receipt['facts_sha256']:
                raise ValueError(f'Fact hash mismatch: {accession}')
            inputs[str(path.relative_to(ROOT))] = digest(path)
            inputs[str(fact_path.relative_to(ROOT))] = fact_hash
            receipt_cache[accession] = True
        return True

    coverage, folds, ledger = [], [], []
    for horizon in ('252', '378', '504', '756'):
        rows = outcomes[horizon]['russell']
        ids = [(r['issuer'], r['entry']) for r in rows]
        assert len(set(ids)) == len(ids)
        candidates = []
        for row in rows:
            members = row['accessions']
            assert row['accession'] in members and len(set(members)) == len(members)
            joined = sum(prepared(a) for a in members)
            valid = valid_label(row)
            single = valid and len(members) == joined == 1
            if single:
                assert selected[members[0]]['accepted'][:10] < row['entry']
                candidates.append(row)
            ledger.append(dict(horizon_sessions=int(horizon), issuer=row['issuer'],
                               entry=row['entry'], label_end=row['exit'],
                               valid_russell_label=valid, member_filings=len(members),
                               prepared_member_filings=joined, single_filing_candidate=single,
                               focused_candidate=bool(row['focused']),
                               status=row['status'], accession=row['accession']))
        valid = [r for r in rows if valid_label(r)]
        coverage.append(dict(horizon_sessions=int(horizon), scheduled_events=len(rows),
                             valid_russell_labels=len(valid),
                             single_filing_prepared_candidates=len(candidates),
                             focused_valid_labels=sum(r['focused'] for r in valid),
                             focused_single_filing_candidates=sum(r['focused'] for r in candidates),
                             merged_events_with_valid_label=sum(len(r['accessions']) > 1 for r in valid),
                             valid_label_statuses=dict(Counter(r['status'] for r in rows)),
                             entry_year_counts=dict(sorted(Counter(r['entry'][:4] for r in candidates).items()))))
        for year in range(2020, 2025):
            train, test = split_at(candidates, year)
            train_issuers = {r['issuer'] for r in train}
            test_issuers = {r['issuer'] for r in test}
            folds.append(dict(horizon_sessions=int(horizon), prediction_year=year,
                              completed_training_events=len(train), prediction_events=len(test),
                              training_issuers=len(train_issuers), prediction_issuers=len(test_issuers),
                              shared_issuers=len(train_issuers & test_issuers),
                              focused_training_events=sum(r['focused'] for r in train),
                              focused_prediction_events=sum(r['focused'] for r in test)))
    two_year = next(r for r in coverage if r['horizon_sessions'] == 504)
    assert (two_year['scheduled_events'], two_year['valid_russell_labels'],
            two_year['focused_valid_labels']) == (2107, 694, 56)
    summary = dict(status='feasibility_only_no_models_or_new_return_estimates',
                   scope='Existing first-observed issuer-entry schedules; prior examined development history',
                   prepared_filings=len(selection), horizons=coverage,
                   limitations=['Candidates are not a validated ML feature panel.',
                                'Merged filing events need an explicit feature aggregation rule.',
                                'Frozen schedules differ across horizons; horizon counts are not independent.',
                                'Fold counts precede inner validation, feature-gap filters and dependence checks.',
                                'Funded-account accounting and label-selection bias remain unresolved.'])
    blobs = {'summary.json': json.dumps(summary, indent=2, sort_keys=True).encode() + b'\n',
             'candidate-folds.csv': csv_bytes(folds), 'event-coverage.csv': csv_bytes(ledger),
             'provenance.json': json.dumps({'inputs_sha256': inputs}, indent=2, sort_keys=True).encode() + b'\n'}
    return blobs, summary, folds


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    self_checks()
    blobs, summary, folds = assess()
    if args.verify:
        for name, payload in blobs.items():
            if (args.output / name).read_bytes() != payload:
                raise ValueError(f'Replay mismatch: {name}')
        print('Verified exact offline replay of all four diagnostic artifacts.')
    else:
        args.output.mkdir(parents=True, exist_ok=False)
        for name, payload in blobs.items():
            (args.output / name).write_bytes(payload)
        print(json.dumps({'horizons': summary['horizons'],
                          'two_year_folds': [r for r in folds if r['horizon_sessions'] == 504]}, indent=2))


if __name__ == '__main__':
    main()
