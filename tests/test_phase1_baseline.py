"""Hand-computed pins, convention/refusal checks and deterministic replay."""
import pytest

from activist13d.phase1_baseline import event_return, schedule, summarize


def row(**extra):
    return dict(dlyopen=100, dlyclose=110, dlyvol=1000, conditionaltype='RW',
                tradingstatusflg='A', dlydelflg='N', **extra)


def test_open_entry_and_total_return_pin():
    # 100 -> 110 intraday, then +20% total return: 1.1*1.2-1 = 32%.
    rows = {'a': row(dlyret=9), 'b': row(dlyret=.2, dlyretmissflg='NA', dlyprevdt='a')}
    assert event_return(['a', 'b'], rows)[0] == pytest.approx(.32)
    # The entry day's close-to-close return is deliberately not used.
    assert event_return(['a'], rows)[0] == pytest.approx(.1)


def test_delisting_once_and_total_loss():
    rows = {'a': row(), 'b': {'dlyret': -.5, 'dlyretmissflg': 'NA',
                             'dlyprevdt': 'a', 'dlydelflg': 'Y'}}
    # 1.1 * .5 = .55; proceeds unchanged on c even without a stock observation.
    assert event_return(['a', 'b', 'c'], rows)[0] == pytest.approx(-.45)
    rows['b']['dlyret'] = -1
    assert event_return(['a', 'b', 'c'], rows)[0] == -1


@pytest.mark.parametrize('change,reason', [
    ({'dlyret': None}, 'missing_or_invalid_total_return'),
    ({'dlyret': -1.1}, 'missing_or_invalid_total_return'),
    ({'dlyret': 'NaN'}, 'missing_or_invalid_total_return'),
    ({'dlyprevdt': 'older'}, 'nonconsecutive_return_duration'),
    ({'dlydelflg': None}, 'unresolved_delisting_flag'),
])
def test_refuse_bad_history(change, reason):
    second = {'dlyret': .1, 'dlyretmissflg': 'NA', 'dlyprevdt': 'a', 'dlydelflg': 'N'}
    second.update(change)
    assert event_return(['a', 'b'], {'a': row(), 'b': second}) == (None, reason)


def test_no_missing_day_or_quote_price_substitution():
    assert event_return(['a', 'b'], {'a': row()})[0] is None
    first = row()
    first.update(dlyclose=None, dlyprc=-110)
    assert event_return(['a'], {'a': first}) == (None, 'invalid_entry_prices')


def test_scheduled_exit_requires_a_trade_price():
    last = row(dlyret=.1, dlyprevdt='a', dlyretmissflg='NA')
    last['dlyclose'] = None
    assert event_return(['a', 'b'], {'a': row(), 'b': last}) == (None, 'unusable_scheduled_exit_trade')


def test_merge_overlap_and_reentry_without_using_outcomes():
    def event(a, day, broad=False):
        return dict(accession=a, entry=day, issuer='i', permno=1, broad=broad, focused=False)
    selected, excluded = schedule([event('1', 'a'), event('2', 'a', True),
                                    event('3', 'b'), event('4', 'c')], list('abcd'), 2)
    assert len(selected) == 2
    assert selected[0]['accessions'] == ['1', '2']
    assert selected[0]['broad'] and selected[0]['exit'] == 'b'
    assert excluded[0]['accession'] == '3'
    assert selected[1]['entry'] == 'c'


def test_simultaneous_share_classes_refused():
    events = [dict(accession=str(i), entry='a', issuer='same', permno=i,
                   broad=False, focused=False) for i in [1, 2]]
    selected, excluded = schedule(events, list('abc'), 2)
    assert not selected and len(excluded) == 2


def test_summary_hand_pin_and_exact_replay():
    rows = [dict(issuer='a', stock_return=.3, benchmark_return=.1, excess=.2, status='ok'),
            dict(issuer='b', stock_return=-.1, benchmark_return=.1, excess=-.2, status='ok')]
    first = summarize(rows)
    assert first['mean_stock'] == pytest.approx(.1)
    assert first['mean_excess'] == 0 and first['fraction_beating_benchmark'] == .5
    assert first == summarize(rows)
    assert summarize([])['calculated'] == 0
