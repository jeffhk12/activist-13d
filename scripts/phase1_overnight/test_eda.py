"""Pin EDA counts and nearest-rank distributions to hand-built examples.

Inputs: synthetic two-record SQLite. Outputs: assertions, no API calls.
Identity: two parsed records + one explicit failure = three processed.
Tier: 1
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python -m pytest scripts/phase1_overnight/test_eda.py
"""
import importlib.util
import json
import sqlite3
from pathlib import Path

spec = importlib.util.spec_from_file_location('overnight_eda', Path(__file__).with_name('eda.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_quantiles():
    assert m.distribution([4, 1, 3, 2]) == {'n': 4, 'min': 1, 'p25': 1, 'median': 2, 'p75': 3, 'p95': 4, 'max': 4}
    assert m.distribution([]) == {'n': 0}


def test_counts_and_replay():
    db = sqlite3.connect(':memory:')
    db.execute('CREATE TABLE records(accession TEXT, record_json TEXT)')
    db.execute('CREATE TABLE failures(error TEXT, source_json TEXT)')
    base = {'filing_date': '2020-01-03', 'form': '13D', 'subjects': [{'cik': '001'}, {'cik': '001'}], 'filers': [], 'flags': ['missing_cusip'], 'event_date': '2020-01-01'}
    db.execute('INSERT INTO records VALUES (?,?)', ('1', json.dumps(base)))
    db.execute('INSERT INTO records VALUES (?,?)', ('2', json.dumps(dict(base, form='13D/A', item4_text='abcd'))))
    db.execute('INSERT INTO failures VALUES (?,?)', ('refused', json.dumps({'filing_date': '2021-01-01'})))
    result = m.scan(db)
    assert result == m.scan(db)
    assert result['parsed_n'] + result['failures_n'] == 3
    assert result['unique_subject_ciks'] == 1 and result['top_subject_ciks_by_filing_mentions'] == [('1', 2)]
    assert result['flags']['missing_cusip'] == 2 and result['filing_minus_event_calendar_days']['median'] == 2


def test_html_escape():
    r = m.Report()
    r.para('<script>')
    assert '<script>' not in r.web[0]
