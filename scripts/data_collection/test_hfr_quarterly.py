"""Offline pins for source preservation, ID counts and refusal behavior."""
import pytest
from ingest_hfr_quarterly import FIELDS, cell_text, column, freeze, manager_rows, summarize


def row(n, firm, strategy='Event-Driven', sub='Activist'):
    fields = dict.fromkeys(FIELDS)
    fields.update(Fund_ID=str(n), Firm_ID=firm, Firm='Alpha', Fund=f'Class {n}',
                  Main_Strategy=strategy, Sub_Strategy=sub)
    return {'excel_row': n + 1, 'fields': fields}


def test_counts_share_classes_and_missing_ids():
    records = [row(1, '10'), row(2, '10'), row(3, '20', sub='Merger Arbitrage'),
               row(4, '30', strategy='Equity Hedge'), row(5, None)]
    s = summarize(records)
    # Four ED rows, two known firms; three activist rows, one known firm.
    assert (s['event_driven_fund_rows'], s['event_driven_firm_ids']) == (4, 2)
    assert (s['activist_fund_rows'], s['activist_firm_ids']) == (3, 1)
    assert s['missing_firm_id_rows'] == 1
    assert [m['firm_id'] for m in manager_rows(records, '2020Q1')] == ['10', '20']


def test_no_fuzzy_strategy_or_id_rewriting():
    assert summarize([row(1, '0010', strategy='event-driven')])['event_driven_fund_rows'] == 0
    assert cell_text('0010') == '0010'
    assert cell_text(10.0) == '10'
    assert cell_text('') is None
    assert [column(n) for n in (1, 26, 27, 52, 91)] == ['A', 'Z', 'AA', 'AZ', 'CM']


def test_duplicate_fund_ids_reported():
    assert summarize([row(1, '10'), row(1, '10')])['duplicate_fund_id_excess_rows'] == 1


def test_replay_and_refusal(tmp_path):
    path = tmp_path / 'frozen.json'
    freeze(path, 'same\n')
    first = path.read_bytes()
    freeze(path, 'same\n')
    assert path.read_bytes() == first
    with pytest.raises(ValueError, match='Refusing changed'):
        freeze(path, 'different\n')
    assert path.read_bytes() == first
