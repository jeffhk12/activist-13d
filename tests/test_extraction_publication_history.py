"""Preserved failed drafts must remain visible without blocking publication."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts' / 'extraction_protocol'))
from finish_extraction_batch_v2 import inspect_draft_history  # noqa: E402


def save(job, raw):
    directory = job / 'draft-history'
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (hashlib.sha256(raw).hexdigest() + '.json')
    path.write_bytes(raw)
    return path


def test_malformed_failed_draft_is_preserved_and_reported(tmp_path):
    job = tmp_path / 'extractor_case'
    bad = save(job, b'{"intent": "present" "evidence": []}')
    good = save(job, b'{"intent": "present", "evidence": []}')
    before = {p.name: p.read_bytes() for p in (bad, good)}
    result = inspect_draft_history(job)
    assert result['saved_draft_versions'] == 2
    assert result['parseable_draft_versions'] == 1
    assert result['unparseable_draft_versions'] == 1
    assert result['unparseable_drafts'][0]['sha256'] == bad.stem
    assert result['unparseable_drafts'][0]['parse_error']
    assert result['all_parseable_versions_equal_ignoring_quote_offsets_and_overwritten_metadata']
    assert not result['all_saved_versions_equal_ignoring_quote_offsets_and_overwritten_metadata']
    assert before == {p.name: p.read_bytes() for p in (bad, good)}


def test_parseable_judgment_change_is_not_hidden(tmp_path):
    job = tmp_path / 'extractor_case'
    save(job, json.dumps({'intent': 'present', 'start': 1}).encode())
    save(job, json.dumps({'intent': 'not_stated', 'start': 2}).encode())
    result = inspect_draft_history(job)
    assert not result['all_parseable_versions_equal_ignoring_quote_offsets_and_overwritten_metadata']
    assert not result['all_saved_versions_equal_ignoring_quote_offsets_and_overwritten_metadata']


def test_history_hash_mismatch_still_fails(tmp_path):
    job = tmp_path / 'extractor_case'
    path = save(job, b'{"intent": "present"}')
    path.write_bytes(b'{"intent": "not_stated"}')
    with pytest.raises(ValueError, match='history hash'):
        inspect_draft_history(job)
