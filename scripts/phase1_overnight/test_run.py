"""Offline hand-built contracts for candidate parsing and evidence verification.

Inputs: synthetic raw SEC filing. Outputs: assertions only.
Identity: changed source bytes invalidate sidecar; missing fields stay missing.
Tier: 1
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python -m pytest scripts/phase1_overnight/test_run.py
"""
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('overnight_run', Path(__file__).with_name('run.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(m, 'ROOT', tmp_path)
    path = tmp_path / 'data/raw/edgar/example.txt'
    path.parent.mkdir(parents=True)
    raw = b'ACCESSION NUMBER: 0000000001-20-000001\nFILED AS OF DATE: 20200102\nCONFORMED SUBMISSION TYPE: SC 13D\n<DOCUMENT>\n<TYPE>SC 13D\n<FILENAME>a.htm\n<TEXT><p>Item 4. Purpose of Transaction</p><p>The reporting person is considering a change to the board of directors.</p><p>Item 5. Interest</p></TEXT>\n</DOCUMENT>'
    path.write_bytes(raw)
    row = {'accession': '0000000001-20-000001', 'storage_path': str(path.relative_to(tmp_path)), 'filing_date': '2020-01-02', 'form': '13D', 'source_url': 'https://www.sec.gov/example'}
    meta = {'sha256': m.digest(path), 'bytes': len(raw), 'url': row['source_url']}
    path.with_suffix('.txt.meta.json').write_text(json.dumps(meta))
    return row, path


def test_verified_replay(tmp_path, monkeypatch):
    row, path = fixture(tmp_path, monkeypatch)
    a = m.verify(row)
    first = m.parse_one(row, a)
    assert first == m.parse_one(row, a)
    assert first['item4_text'] == 'The reporting person is considering a change to the board of directors.'
    assert first['cusip'] is None and 'missing_cusip' in first['flags']
    assert first['intent_labels'] is None and 'text' not in first['documents'][0]


def test_refuse_changed_bytes_and_header(tmp_path, monkeypatch):
    row, path = fixture(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match='date mismatch'):
        m.verify(dict(row, filing_date='2020-01-03'))
    path.write_bytes(path.read_bytes() + b'changed')
    with pytest.raises(ValueError, match='mismatch'):
        m.verify(row)


def test_refuse_url_and_path(tmp_path, monkeypatch):
    row, path = fixture(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match='URL mismatch'):
        m.verify(dict(row, source_url='https://wrong.example/'))
    with pytest.raises(ValueError, match='outside'):
        m.verify(dict(row, storage_path='../outside.txt'))


def test_network_disabled():
    with pytest.raises(RuntimeError, match='Network disabled'):
        m.offline()
