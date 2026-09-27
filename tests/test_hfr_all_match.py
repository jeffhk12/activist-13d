"""Hand-pinned manager aggregation, date rules, ambiguity and deterministic replay."""
import json

from activist13d.hfr_all_match import group_managers, index_managers, match_name, prior_index


def row(n, firm, strategy='Equity Hedge', sub='Long/Short', name='Alpha Capital LLC', fund=None):
    return {'excel_row': n, 'fields': dict(Firm_ID=firm, Firm=name, Fund=fund or f'Fund {n}',
        Main_Strategy=strategy, Sub_Strategy=sub)}


def test_all_strategies_share_classes_and_missing_id():
    rows = [row(2, '001'), row(3, '001'), row(4, '2', 'Macro'),
            row(5, '3', 'Relative Value'), row(6, None)]
    managers = group_managers(rows, '2020Q1')
    assert len(managers) == 3  # Five fund rows, four with IDs, three vendor firms.
    assert managers[0]['firm_id'] == '001'
    assert managers[0]['fund_rows'] == [2, 3]
    assert not any(m['event_driven'] for m in managers)


def test_strategy_pairs_and_mixed_manager_not_single_strategy():
    rows = [row(2, '1', 'Equity Hedge', 'Activist'), row(3, '1', 'Event-Driven', 'Merger Arbitrage')]
    manager = group_managers(rows, 'q')[0]
    assert manager['event_driven'] and not manager['activist']
    rows.append(row(4, '1', 'Event-Driven', 'Activist'))
    assert group_managers(rows, 'q')[0]['activist']
    assert group_managers([row(2, 'f', 'Fund of Funds')], 'q')[0]['fund_of_funds_only']
    assert not group_managers([row(2, 'f', 'Fund of Funds'), row(3, 'f')], 'q')[0]['fund_of_funds_only']


def test_rules_and_no_fuzzy_or_identifier_guess():
    index = index_managers(group_managers([row(2, '1', fund='Alpha Offshore Fund LP')], 'q'))
    assert match_name(index, 'ALPHA CAPITAL L.L.C.') == {'1': 'normalized_firm'}
    assert match_name(index, 'Alpha Capital Ltd') == {'1': 'firm_without_legal_suffix'}
    assert match_name(index, 'ALPHA OFFSHORE FUND LP') == {'1': 'normalized_fund'}
    assert match_name(index, 'Alpha') == {}
    assert match_name(index, 'Alpha Capital Partners LLC') == {}


def test_ambiguity_preserved():
    indexes = index_managers(group_managers([row(2, '1'), row(3, '2')], 'q'))
    assert set(match_name(indexes, 'Alpha Capital LLC')) == {'1', '2'}


def test_strict_prior_no_carryforward_or_backfill():
    dates = ['2020-03-16', '2020-06-16']
    assert prior_index(dates, '2020-03-16') == -1
    assert prior_index(dates, '2020-03-17') == 0
    assert prior_index(dates, '2020-06-16') == 0
    assert prior_index(dates, '2020-06-17') == 1
    indexes = [index_managers(group_managers([row(2, '1')], 'q1')), index_managers([])]
    assert match_name(indexes[prior_index(dates, '2020-06-17')], 'Alpha Capital LLC') == {}


def test_exact_replay_and_empty_name_refusal():
    records = [row(2, '1'), row(3, '1', 'Macro')]
    a = group_managers(records, 'q')
    b = group_managers(records, 'q')
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert match_name(index_managers(a), '') == {}
