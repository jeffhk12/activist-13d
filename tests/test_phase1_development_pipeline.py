"""Offline sample-boundary, protection, page-integrity and return-path checks."""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from activist13d.phase1_baseline import event_return, schedule

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/data_collection/run_phase1_development.py'
SPEC = importlib.util.spec_from_file_location('phase1_development_runner', SCRIPT)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def candidate(**changes):
    record = dict(accession='test', subjects=[{'cik': 'issuer'}],
        entry_date_audit_proxy='2020-01-06', source_status='hash_and_size_verified',
        security_screen='corporate_common_candidate', entry_price_status='positive_open_observed',
        amendment_flag_conflict=False, publication_date_disagrees=False,
        cusip_check_digit_valid=True, candidate_group_key='issuer::manager',
        issuer_also_filing_party=False, security_link={'permno': 1},
        broad_manager_subset=False, focused_activist_subset=False,
        entry_price_evidence={'row': {'conditionaltype': 'RW', 'tradingstatusflg': 'A', 'dlyvol': 100}})
    record.update(changes)
    return record


def test_human_protection_and_development_dates():
    accepted, refused = runner.select_events([candidate()], {'issuer'})
    assert not accepted and refused[0]['reason'] == 'protected_human_review_issuer'
    accepted, refused = runner.select_events([candidate(entry_date_audit_proxy='2024-01-02')], set())
    assert not accepted and refused[0]['reason'] == 'outside_development_entry_dates'
    assert len(runner.select_events([candidate()], set())[0]) == 1


def test_outcome_window_cannot_overrun_calendar():
    event = dict(accession='a', issuer='i', permno=1, entry='2023-12-29', broad=False, focused=False)
    selected, excluded = schedule([event], ['2023-12-28', '2023-12-29'], 2)
    assert not selected and excluded[0]['reason'] == 'insufficient_calendar'


def test_source_hash_refusal_and_replay(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'ROOT', tmp_path)
    path = tmp_path / 'crsp.dsf_v2/page.json.gz'
    path.parent.mkdir()
    raw = b'{"results": []}'
    path.write_bytes(gzip.compress(raw))
    path.with_suffix('.meta.json').write_text(json.dumps(dict(
        sha256=hashlib.sha256(raw).hexdigest(), raw_bytes=len(raw),
        request={'url': 'https://example.test/crsp.dsf_v2/'})))
    first, second = {}, {}
    assert runner.read_page(path, first) == runner.read_page(path, second)
    assert first == second
    path.write_bytes(gzip.compress(b'{"results": [1]}'))
    with pytest.raises(ValueError, match='integrity'):
        runner.read_page(path, {})


def test_constant_price_path_parity():
    # No dividends/splits: compounding must equal terminal close/entry open - 1.
    rows = {
        'a': dict(dlyopen=100, dlyclose=110, dlyvol=1, conditionaltype='RW', tradingstatusflg='A', dlydelflg='N'),
        'b': dict(dlyret=.2, dlyprevdt='a', dlyretmissflg='NA', dlydelflg='N'),
        'c': dict(dlyret=-.25, dlyprevdt='b', dlyretmissflg='NA', dlydelflg='N',
                  dlyclose=99, dlyvol=1, conditionaltype='RW', tradingstatusflg='A'),
    }
    # 110 * 1.2 * .75 = 99; purchase at 100 produces -1%.
    assert event_return(['a', 'b', 'c'], rows)[0] == pytest.approx(99 / 100 - 1)


def test_offline_ledger_replay():
    day = '2020-01-06'
    events = [dict(accession='a', accessions=['a'], issuer='i', permno=1,
                   broad=True, focused=True, entry=day, exit=day, days=[day])]
    opening = dict(dlyopen=100, dlyclose=110, dlyvol=100,
                   conditionaltype='RW', tradingstatusflg='A', dlydelflg='N')
    benchmark = dict(opening, dlyclose=105)
    panel = {1: {day: opening}, 84398: {day: benchmark}}
    outcomes, summary = runner.calculate({'126': events}, panel)
    assert outcomes['126'][0]['excess'] == pytest.approx(.05)
    assert summary['126']['all']['calculated'] == 1
    assert runner.encode((outcomes, summary)) == runner.encode(runner.calculate({'126': events}, panel))
