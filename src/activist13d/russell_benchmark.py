"""Tier: 2. Assign lagged historical Russell segment membership to ETF proxies.

Inputs: exact matched vendor constituent rows. Outputs: ETF symbol/refusal.
Identity: Midcap -> IWR; remaining 1000 -> IWB; 2000 -> IWM, no cap guessing.
Protocol: research/protocol/phase1-russell-v1.md.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python -m pytest tests/test_russell_benchmark.py
"""
from activist13d.phase1_baseline import event_return, number

ETFS = {'IWB': 88221, 'IWM': 88222, 'IWR': 89059, 'IWV': 88223}


def assign(rows):
    if not rows:
        return None, 'no_constituent_match'
    if len(rows) != 1:
        return None, 'ambiguous_constituent_match'
    row = rows[0]
    flags = {}
    for flag, weight in [('russell1000', 'r1000_wt'), ('russell2000', 'r2000_wt'), ('russellmc', 'rmidc_wt')]:
        value = row.get(flag)
        wt = number(row.get(weight))
        if value not in {'Y', 'N'} or ((value == 'Y') != (wt is not None and wt > 0)):
            return None, 'inconsistent_membership_flags_weights'
        flags[flag] = value == 'Y'
    large, small, mid = (flags[k] for k in ['russell1000', 'russell2000', 'russellmc'])
    if (large and small) or (mid and not large):
        return None, 'conflicting_size_membership'
    if mid:
        return 'IWR', 'matched'
    if large:
        return 'IWB', 'matched'
    if small:
        return 'IWM', 'matched'
    return None, 'no_supported_segment'


def compare(event, assignment, days, panel):
    """Keep the original stock/SPY values; require a common calculable sample."""
    result = dict(event, spy_return=event['benchmark_return'], spy_excess=event['excess'],
                  original_status=event['status'], assigned_etf=assignment['etf'],
                  assignment_status=assignment['status'], russell_return=None,
                  broad_russell_return=None, benchmark_return=None, excess=None)
    if assignment['status'] != 'matched':
        result['status'] = 'assignment:' + assignment['status']
        return result
    if event['excess'] is None:
        result['status'] = 'original:' + event['status']
        return result
    chosen, status = event_return(days, panel.get(ETFS[assignment['etf']], {}))
    broad, broad_status = event_return(days, panel.get(ETFS['IWV'], {}))
    result.update(russell_return=chosen, broad_russell_return=broad,
                  russell_status=status, broad_russell_status=broad_status)
    if chosen is None or broad is None:
        result['status'] = 'etf:' + (status if chosen is None else broad_status)
        return result
    result.update(benchmark_return=chosen, excess=event['stock_return'] - chosen,
                  status='calculated_common_sample')
    return result
