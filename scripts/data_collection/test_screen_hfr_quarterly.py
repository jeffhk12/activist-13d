"""Offline temporal and name-screen refusal contracts."""
from screen_hfr_quarterly import index_managers, match_name, prior_index


def test_strictly_prior_no_backfill_or_same_day():
    dates = ['2018-03-16', '2018-06-28']
    assert prior_index(dates, '2017-12-31') == -1
    assert prior_index(dates, '2018-03-16') == -1
    assert prior_index(dates, '2018-03-17') == 0
    assert prior_index(dates, '2018-06-28') == 0
    assert prior_index(dates, '2018-06-29') == 1


def test_name_candidates_ambiguity_and_empty_refusal():
    index = index_managers([
        {'firm_id': '1', 'names': ['Alpha Capital LLC'], 'fund_names': ['Alpha Fund']},
        {'firm_id': '2', 'names': ['Alpha Capital LP'], 'fund_names': []},
        {'firm_id': '3', 'names': ['LLC'], 'fund_names': []},
    ])
    assert match_name(index, 'Alpha Capital, L.P.') == {'1': 'firm_without_legal_suffix', '2': 'normalized_firm'}
    assert match_name(index, 'Alpha Fund') == {'1': 'normalized_fund'}
    assert match_name(index, 'Alpha') == {}
    assert match_name(index, '') == {}


def test_latest_snapshot_absence_does_not_carry_forward():
    earlier = index_managers([{'firm_id': '1', 'names': ['Alpha'], 'fund_names': []}])
    later = index_managers([])
    assert match_name(earlier, 'Alpha') == {'1': 'normalized_firm'}
    assert match_name(later, 'Alpha') == {}
