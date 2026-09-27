"""Merged-event membership, refusal, cohort accounting and hand-pinned averages."""
import pytest

from activist13d.expanded_hfr_returns import DISJOINT, summarize_groups, tag_event


def unions():
    return dict(all_hfr={'a', 'e', 'n', 'f'}, supplement={'s'},
                all_hfr_plus_supplement={'a', 'e', 'n', 'f', 's'},
                manager_has_activist={'a'}, previous_hfr_event_driven_screen={'a', 'e'},
                only_fund_of_funds_managers_matched={'f'})


def event(accessions, broad=False, focused=False, stock=.2, benchmark=.1):
    return dict(accession=accessions[0], accessions=accessions, broad=broad, focused=focused,
                issuer=accessions[0], stock_return=stock, benchmark_return=benchmark,
                excess=stock-benchmark, status='calculated_full_window')


def test_new_match_on_second_accession_counts_one_event():
    r = tag_event(event(['unknown', 'n']), unions())
    assert r['expanded_manager'] and r['disjoint_cohort'] == 'new_other_hfr'
    summary = summarize_groups([r])
    assert summary['expanded']['scheduled'] == summary['all']['scheduled'] == 1


def test_focus_precedence_and_external_supplement():
    r = tag_event(event(['n', 'a'], broad=True, focused=True), unions())
    assert r['disjoint_cohort'] == 'focused'
    s = tag_event(event(['s'], broad=True, focused=True), unions())
    assert s['expanded_manager'] and not s['hfr_only']


def test_fof_mixed_event_not_pure_fof():
    assert tag_event(event(['f']), unions())['fund_of_funds_only']
    assert not tag_event(event(['f', 'n']), unions())['fund_of_funds_only']
    assert not tag_event(event(['f', 's'], broad=True, focused=True), unions())['fund_of_funds_only']


def test_prior_group_change_refused():
    with pytest.raises(ValueError, match='Prior cohort'):
        tag_event(event(['a']), unions())
    with pytest.raises(ValueError, match='representative'):
        tag_event(dict(event(['n']), accessions=[]), unions())


def test_partition_and_mean_hand_pin_and_replay():
    rows = [tag_event(event(['a'], True, True, stock=.3), unions()),
            tag_event(event(['e'], True, stock=.1), unions()),
            tag_event(event(['n'], stock=-.1), unions()),
            tag_event(event(['unknown'], stock=-.3), unions())]
    result = summarize_groups(rows)
    assert sum(result[k]['calculated'] for k in DISJOINT) == result['all']['calculated'] == 4
    # Expanded excess: (+.20 + .00 - .20) / 3 = 0.
    assert result['expanded']['mean_excess'] == pytest.approx(0)
    assert result['expanded']['mean_stock'] == pytest.approx(.1)
    assert result == summarize_groups(rows)


def test_invalid_outcome_remains_in_scheduled_denominator():
    r = tag_event(event(['n']), unions())
    r.update(stock_return=None, excess=None, status='stock:missing_total_return')
    result = summarize_groups([r])['expanded']
    assert result['scheduled'] == 1 and result['calculated'] == 0
    assert 'mean_excess' not in result
