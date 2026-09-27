"""Outcome-blind candidate selection and fail-closed fresh-evaluation gates.

Inputs: frozen metadata, XNYS sessions, protected/exposed identities, gate evidence.
Outputs: calendar-mature candidate schedules, reconciled refusals, gate status.
Identity: exit_index = entry_index + horizon - 1; no outcome availability filter.
Tier: 2. Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8
.venv/bin/python -m pytest tests/test_phase1_evaluation_readiness_selection.py
"""
from bisect import bisect_right
from collections import Counter

from activist13d.phase1_baseline import number, schedule

CONVENTIONS = {
    'primary_sessions': 126, 'supporting_sessions': [63, 252],
    'entry': 'second_XNYS_session_strictly_after_acceptance_date',
    'entry_counts_as_session_one': True,
    'future_return_availability_used': False,
    'sample_status': 'historical_candidate_not_certified_fresh',
}
REQUIRED_GATES = (
    'exposure_provenance', 'protocol_and_code_frozen', 'identity_eligibility',
    'valuation_policy', 'benchmark_inputs', 'price_cash_inputs',
    'protected_issuer_integrity', 'calendar_maturity', 'selection_frozen',
)


def readiness(gates):
    """Unknown, absent, or non-boolean gate results refuse authorization."""
    failed = [key for key in REQUIRED_GATES if gates.get(key) is not True]
    return {'status': 'NOT READY' if failed else 'READY', 'failed_gates': failed}


def candidates(records, eligibility, sessions, protected, exposed_issuers,
               exposed_permnos, *, start='2024-01-01', asof='2026-09-23'):
    """Apply frozen basic screen; inspect entry facts only, never holding returns.

    Counts are a sequential funnel. Entry-price metadata was already inspected in
    feasibility; calendar maturity is not vendor-data completeness. Unknown issuer
    or security identity refuses selection, including absent eligibility joins.
    """
    selected, excluded = [], []
    for r in sorted(records, key=lambda row: row['accession']):
        accession = r['accession']
        issuers = sorted({s['cik'] for s in r.get('subjects', []) if s.get('cik')})
        entry = r.get('entry_date_audit_proxy')
        accepted = (r.get('acceptance_datetime_et') or '')[:10]
        a = eligibility.get(accession)
        permno = r.get('security_link', {}).get('permno')
        reason = None
        if not entry or not start <= entry <= asof:
            reason = 'outside_candidate_entry_window'
        elif set(issuers) & protected:
            reason = 'protected_human_review_issuer'
        elif set(issuers) & exposed_issuers or permno in exposed_permnos:
            reason = 'prior_exposure_or_conservative_quarantine'
        elif a is None:
            reason = 'missing_eligibility_join'
        elif a['status'] != 'standalone_initial_candidate':
            reason = 'not_standalone_initial'
        elif (r.get('source_status') != 'hash_and_size_verified'
              or r.get('security_screen') != 'corporate_common_candidate'
              or r.get('entry_price_status') != 'positive_open_observed'
              or r.get('amendment_flag_conflict')
              or r.get('publication_date_disagrees')
              or r.get('cusip_check_digit_valid') is False
              or not r.get('candidate_group_key')
              or r.get('issuer_also_filing_party') or len(issuers) != 1
              or permno is None):
            reason = 'fails_prior_basic_readiness'
        else:
            i = bisect_right(sessions, accepted)
            price = r.get('entry_price_evidence', {}).get('row', {})
            volume = number(price.get('dlyvol'))
            if not accepted or i + 1 >= len(sessions) or sessions[i + 1] != entry:
                reason = 'entry_convention_mismatch'
            elif (price.get('conditionaltype') != 'RW'
                  or price.get('tradingstatusflg') != 'A'
                  or volume is None or volume <= 0):
                reason = 'entry_trading_conditions'
        if reason:
            excluded.append({'accession': accession, 'reason': reason})
        else:
            selected.append(dict(accession=accession, entry=entry,
                                 issuer=issuers[0], permno=permno,
                                 broad=r['broad_manager_subset'],
                                 focused=r['focused_activist_subset'],
                                 campaign_status=a['campaign_status']))
    assert len(records) == len(selected) + len(excluded)
    plans = {}
    mature_calendar = [day for day in sessions if day <= asof]
    for branch in ('standalone', 'first_observed'):
        usable = [r for r in selected if branch == 'standalone'
                  or r['campaign_status'] == 'first_observed_pair']
        plans[branch] = {}
        for horizon in (63, 126, 252):
            kept, dropped = schedule(usable, mature_calendar, horizon)
            plans[branch][str(horizon)] = {
                'events': kept, 'exclusions': dropped,
                'counts': {'before_schedule': len(usable), 'scheduled': len(kept),
                           'focused': sum(e['focused'] for e in kept),
                           'issuers': len({e['issuer'] for e in kept}),
                           'focused_issuers': len({e['issuer'] for e in kept if e['focused']}),
                           'exclusions': dict(Counter(e['reason'] for e in dropped))},
            }
    return {'selected': selected, 'exclusions': excluded,
            'exclusion_counts': dict(Counter(r['reason'] for r in excluded)),
            'plans': plans}
