"""Tier: 2. Hand pins, convention/refusal/join tests for outcome-blind selection.
Inputs: synthetic metadata; outputs: assertions. Identity: n=input=keep+refuse.
Run: PYTHONPATH=src .venv/bin/python -m pytest this_file
"""
import copy

from activist13d.phase1_evaluation_readiness_selection import (
    CONVENTIONS,
    REQUIRED_GATES,
    candidates,
    readiness,
)


def fixture():
    # Synthetic session strings need only chronological order for these pure tests.
    sessions = [f'2024-{1 + i // 28:02d}-{1 + i % 28:02d}' for i in range(280)]
    r = dict(accession='a', subjects=[{'cik': '1'}],
             entry_date_audit_proxy=sessions[2], acceptance_datetime_et=sessions[0],
             security_link={'permno': 1}, source_status='hash_and_size_verified',
             security_screen='corporate_common_candidate',
             entry_price_status='positive_open_observed', candidate_group_key='x',
             broad_manager_subset=True, focused_activist_subset=True,
             entry_price_evidence={'row': {'conditionaltype': 'RW',
                                          'tradingstatusflg': 'A', 'dlyvol': '1'}})
    a = {'a': {'status': 'standalone_initial_candidate',
               'campaign_status': 'first_observed_pair'}}
    return [r], a, sessions


def run(records=None, protected=None, exposed=None, permnos=None, eligibility=None, asof='2024-10-28'):
    rows, elig, sessions = fixture()
    return candidates(rows if records is None else records,
                      elig if eligibility is None else eligibility, sessions,
                      protected or set(), exposed or set(), permnos or set(), asof=asof)


def test_hand_pin_maturity_and_conventions():
    result = run()
    event = result['plans']['standalone']['126']['events'][0]
    # Entry index 2 + 126 - 1 = index 127 = month 5, day 16.
    assert event['exit'] == '2024-05-16'
    assert len(event['days']) == 126
    assert CONVENTIONS['primary_sessions'] == 126
    assert CONVENTIONS['future_return_availability_used'] is False
    assert run(asof='2024-05-15')['plans']['standalone']['126']['counts']['scheduled'] == 0


def test_protected_exposed_and_security_quarantine():
    for kwargs in ({'protected': {'1'}}, {'exposed': {'1'}}, {'permnos': {1}}):
        result = run(**kwargs)
        assert len(result['exclusions']) == 1 and not result['selected']


def test_join_and_bad_entry_refused():
    assert run(eligibility={})['exclusion_counts'] == {'missing_eligibility_join': 1}
    rows, _, sessions = fixture()
    rows[0]['entry_date_audit_proxy'] = sessions[1]
    assert run(records=rows)['exclusion_counts'] == {'entry_convention_mismatch': 1}


def test_no_replacement_on_missing_outcome_and_deterministic_replay():
    rows, _, _ = fixture()
    first = run(records=rows)
    rows[0]['future_return'] = -0.99
    rows[0]['future_outcome_available'] = False
    assert run(records=rows) == first == run(records=rows)


def test_prior_pair_and_duplicate_scheduling():
    rows, elig, _ = fixture()
    elig['a']['campaign_status'] = 'prior_observed_pair'
    result = run(records=rows, eligibility=elig)
    assert result['plans']['first_observed']['126']['counts']['before_schedule'] == 0
    b = copy.deepcopy(rows[0])
    b['accession'] = 'b'
    rows.append(b)
    elig['b'] = elig['a']
    result = run(records=rows, eligibility=elig)
    assert result['plans']['standalone']['126']['counts']['scheduled'] == 1
    assert result['plans']['standalone']['126']['events'][0]['accessions'] == ['a', 'b']


def test_gates_fail_closed():
    assert readiness({})['status'] == 'NOT READY'
    gates = dict.fromkeys(REQUIRED_GATES, True)
    assert readiness(gates)['status'] == 'READY'
    gates['exposure_provenance'] = 'unknown'
    assert readiness(gates)['failed_gates'] == ['exposure_provenance']
