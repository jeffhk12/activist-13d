"""Tier: 2. Group all HFR strategies and find dated SEC name candidates.

Inputs: preserved HFR identity rows and SEC reporting-person names.
Outputs: vendor-manager groups, deterministic name evidence and prior-snapshot index.
Identity: manager unit = exact nonblank HFR Firm_ID within a snapshot. Match exact
normalized firm, firm minus trailing legal suffixes, or exact normalized fund.
No fuzzy names, CRD-to-CIK conversion, CIK propagation, or identity certification.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python -m pytest tests/test_hfr_all_match.py
"""
import bisect
import re
from collections import defaultdict


def norm(name):
    name = re.sub(r'\bL\s*\.\s*L\s*\.\s*C\b', ' LLC', name, flags=re.I)
    name = re.sub(r'\bL\s*\.\s*P\b', ' LP', name, flags=re.I)
    return ' '.join(re.findall(r'[a-z0-9]+', name.lower()))


def base(name):
    words = norm(name).split()
    while words and words[-1] in {'llc', 'lp', 'ltd', 'limited', 'inc', 'incorporated', 'corp', 'corporation', 'llp'}:
        words.pop()
    return ' '.join(words)


def prior_index(dates, day):
    return bisect.bisect_left(dates, day) - 1


def group_managers(records, quarter):
    groups = defaultdict(list)
    for row in records:
        firm_id = row['fields'].get('Firm_ID')
        if firm_id:
            groups[firm_id].append(row)
    result = []
    for firm_id, rows in sorted(groups.items()):
        def values(key, source_rows=rows):
            return sorted({r['fields'][key] for r in source_rows if r['fields'].get(key)})
        strategies = sorted({r['fields'].get('Main_Strategy') or '(missing)' for r in rows})
        result.append(dict(quarter=quarter, firm_id=firm_id, names=values('Firm'),
            fund_names=values('Fund'), fund_rows=[r['excel_row'] for r in rows],
            strategies=strategies, substrategies=values('Sub_Strategy'),
            crd=values('Firm_IARD_CRD_Number'), sec=values('Firm_SEC_Number'),
            event_driven='Event-Driven' in strategies,
            activist=any(r['fields'].get('Main_Strategy') == 'Event-Driven'
                         and r['fields'].get('Sub_Strategy') == 'Activist' for r in rows),
            fund_of_funds_only=strategies == ['Fund of Funds']))
    return result


def index_managers(managers):
    indexes = [defaultdict(set) for _ in range(3)]
    for manager in managers:
        for name in manager['names']:
            if norm(name):
                indexes[0][norm(name)].add(manager['firm_id'])
            if base(name):
                indexes[1][base(name)].add(manager['firm_id'])
        for name in manager['fund_names']:
            if norm(name):
                indexes[2][norm(name)].add(manager['firm_id'])
    return indexes


def match_name(indexes, name):
    hits = {}
    for index, key, rule in zip(indexes, [norm(name), base(name), norm(name)],
            ['normalized_firm', 'firm_without_legal_suffix', 'normalized_fund'], strict=True):
        for firm in sorted(index.get(key, set())):
            hits.setdefault(firm, rule)
    return hits
