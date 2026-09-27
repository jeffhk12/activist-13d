"""Tier: 2. Pure development-event scheduling and gross return estimators.

Inputs: screened event dictionaries, exchange sessions, dated CRSP daily rows.
Outputs: nonoverlapping issuer events, explicit refusals, event-return summaries.
Formula: R = close_entry/open_entry * product(1 + total_return_after_entry) - 1.
Benchmark excess is R_stock - R_SPY, not a regression alpha. Delisting proceeds
earn zero thereafter. Protocol: research/protocol/phase1-development-v1.md.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python -m pytest tests/test_phase1_baseline.py
"""
import math
import random
import statistics
from collections import Counter, defaultdict


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def schedule(events, sessions, horizon):
    if horizon < 1:
        raise ValueError('Positive holding period required')
    positions = {day: i for i, day in enumerate(sessions)}
    buckets = defaultdict(list)
    for event in events:
        buckets[(event['entry'], event['issuer'])].append(event)
    selected, excluded, busy = [], [], {}
    for (entry, issuer), group in sorted(buckets.items()):
        if len({e['permno'] for e in group}) != 1:
            excluded.extend(dict(e, reason='simultaneous_multiple_securities') for e in group)
            continue
        if entry <= busy.get(issuer, ''):
            excluded.extend(dict(e, reason='overlapping_issuer_position') for e in group)
            continue
        i = positions.get(entry)
        if i is None or i + horizon > len(sessions):
            excluded.extend(dict(e, reason='insufficient_calendar') for e in group)
            continue
        event = dict(sorted(group, key=lambda e: e['accession'])[0])
        event.update(accessions=sorted(e['accession'] for e in group),
                     broad=any(e['broad'] for e in group),
                     focused=any(e['focused'] for e in group),
                     days=sessions[i:i + horizon], exit=sessions[i + horizon - 1])
        selected.append(event)
        busy[issuer] = event['exit']
    return selected, excluded


def event_return(days, rows):
    """Return (gross return or None, status); never bridge missing observations."""
    if not days:
        return None, 'empty_window'
    first = rows.get(days[0])
    if first is None:
        return None, 'missing_entry_observation'
    opening, closing = number(first.get('dlyopen')), number(first.get('dlyclose'))
    volume = number(first.get('dlyvol'))
    if opening is None or closing is None or opening <= 0 or closing <= 0:
        return None, 'invalid_entry_prices'
    if (first.get('conditionaltype') != 'RW' or first.get('tradingstatusflg') != 'A'
            or volume is None or volume <= 0 or first.get('dlydelflg') != 'N'):
        return None, 'entry_trading_conditions'
    wealth = closing / opening
    for previous, day in zip(days, days[1:], strict=False):
        row = rows.get(day)
        if row is None:
            return None, 'missing_holding_observation'
        value = number(row.get('dlyret'))
        if value is None or value < -1 or row.get('dlyretmissflg') != 'NA':
            return None, 'missing_or_invalid_total_return'
        if row.get('dlyprevdt') != previous:
            return None, 'nonconsecutive_return_duration'
        if row.get('dlydelflg') not in {'N', 'Y'}:
            return None, 'unresolved_delisting_flag'
        wealth *= 1 + value
        if row['dlydelflg'] == 'Y':
            return wealth - 1, 'calculated_delisting_then_zero_cash'
    last = rows[days[-1]]
    closing, volume = number(last.get('dlyclose')), number(last.get('dlyvol'))
    if (closing is None or closing <= 0 or volume is None or volume <= 0
            or last.get('conditionaltype') != 'RW' or last.get('tradingstatusflg') != 'A'):
        return None, 'unusable_scheduled_exit_trade'
    return wealth - 1, 'calculated_full_window'


def summarize(outcomes, seed=20260924, resamples=2000):
    valid = [r for r in outcomes if r.get('excess') is not None]
    result = {'scheduled': len(outcomes), 'calculated': len(valid),
              'statuses': dict(sorted(Counter(r['status'] for r in outcomes).items()))}
    if not valid:
        return result
    excess = [r['excess'] for r in valid]
    clusters = defaultdict(list)
    for row in valid:
        clusters[row['issuer']].append(row['excess'])
    totals = [(sum(v), len(v)) for _, v in sorted(clusters.items())]
    rng = random.Random(seed)
    means = []
    for _ in range(resamples):
        draws = rng.choices(totals, k=len(totals))
        means.append(sum(v for v, n in draws) / sum(n for v, n in draws))
    means.sort()
    result.update(unique_issuers=len(clusters),
                  mean_stock=statistics.mean(r['stock_return'] for r in valid),
                  median_stock=statistics.median(r['stock_return'] for r in valid),
                  mean_benchmark=statistics.mean(r['benchmark_return'] for r in valid),
                  mean_excess=statistics.mean(excess), median_excess=statistics.median(excess),
                  fraction_beating_benchmark=sum(v > 0 for v in excess) / len(valid),
                  issuer_bootstrap_95=[means[int(.025 * (resamples - 1))],
                                       means[int(.975 * (resamples - 1))]])
    return result
