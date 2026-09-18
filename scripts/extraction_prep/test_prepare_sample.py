"""Synthetic checks for disjoint sampling, source integrity and blank packets.

Inputs: invented source bytes/rows. Outputs: assertions only.
Identity: 16 broad + 4 text + 4 CUSIP + 4 reference + 4 failure = 32 unique.
Tier: 1
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python -m pytest scripts/extraction_prep/test_prepare_sample.py
"""
import json
from collections import Counter

import pytest
from prepare_sample import BUCKETS, choose, docs, packet, sha, verify

RAW = b'ACCESSION NUMBER: 0000000001-26-000001\nFILED AS OF DATE: 20260102\nCONFORMED SUBMISSION TYPE: SC 13D\n<DOCUMENT>\n<TYPE>SC 13D\n<FILENAME>main.htm\n<TEXT><p>Some full source text.</p><script>hidden()</script></TEXT>\n</DOCUMENT>\n<DOCUMENT>\n<TYPE>EX-99\n<FILENAME>exhibit.pdf\n<TEXT>binarydata</TEXT>\n</DOCUMENT>'


def test_disjoint_replay():
    rows = []
    for lo, _hi in BUCKETS:
        for amend in (False, True):
            for n in range(8):
                rows.append({'accession': f'{lo}-{amend}-{n}', 'filing_date': f'{lo}-01-02', 'is_amendment': amend,
                             'flags': ['missing_item4_text','missing_cusip','unresolved_detected_references']})
    failures = [{'accession': f'failure-{n}'} for n in range(4)]
    first, gaps = choose(rows, failures, set())
    assert (first, gaps) == choose(list(reversed(rows)), failures, set())
    assert len(first) == len({r['accession'] for _, r in first}) == 32
    counts = Counter(s for s, r in first)
    assert counts['failure'] == counts['missing_item4'] == counts['missing_cusip'] == counts['reference_or_binary'] == 4
    assert not gaps


def test_text_boundary_and_binary():
    result = docs(RAW)
    assert len(result) == 3
    assert result[1]['filename'] == 'main.htm' and result[1]['type'] == 'SC 13D'
    assert result[1]['text'] == 'Some full source text.'
    assert result[2]['filename'] == 'exhibit.pdf' and result[2]['text'] is None
    assert all(d['source_accession'] == '0000000001-26-000001' for d in result)


def test_raw_verification_and_refusal(tmp_path):
    p = tmp_path / 'data/raw/edgar/test.txt'
    p.parent.mkdir(parents=True)
    p.write_bytes(RAW)
    m = {'storage_path': str(p.relative_to(tmp_path)), 'source_url': 'https://www.sec.gov/Archives/edgar/data/1/0000000001-26-000001.txt', 'filing_date': '2026-01-02'}
    r = {'accession': '0000000001-26-000001', 'source_sha256': sha(RAW)}
    meta = {'sha256': sha(RAW), 'bytes': len(RAW), 'url': m['source_url']}
    p.with_suffix('.txt.meta.json').write_text(json.dumps(meta))
    assert verify(r, m, tmp_path)[3] == 'SC 13D'
    assert verify(r, dict(m, source_url=None), tmp_path)[3] == 'SC 13D'
    p.write_bytes(RAW + b'changed')
    with pytest.raises(ValueError, match='SHA/size/URL'):
        verify(r, m, tmp_path)


def test_packet_excludes_technical_flags():
    bundle = {'accession': '0000000001-26-000001', 'source_form': 'SC 13D', 'filing_date': '2026-01-02',
              'source_path': '/raw/source.txt', 'source_sha256': sha(RAW), 'documents': docs(RAW),
              'stratum': 'missing_item4', 'failure_error': 'Secret technical flag'}
    result = packet(bundle)
    assert 'missing_item4' not in result and 'Secret technical flag' not in result
    assert '__________' in result and 'Some full source text.' in result
