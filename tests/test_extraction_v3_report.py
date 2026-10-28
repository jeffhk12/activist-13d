"""Independent v3 source-slice pin and no-partial-comparison refusal.

Inputs: invented Unicode text and an unfinished fake job manifest. Outputs:
assertions. Identity: [0,1) is one Greek character; pending jobs forbid report.
Tier:1 support. Run project Python -m pytest tests/test_extraction_v3_report.py.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0,str(Path(__file__).parents[1]/'scripts/extraction_protocol'))
import report_extraction_v3 as report  # noqa:E402


def test_independent_quote_slices_unicode_exactly():
    doc={'one':{'text':'α cash'}}
    evidence={'evidence':[{'document_id':'one','quote':'α','start':0,'end':1}]}
    assert report.quote_count(evidence,doc)==1
    evidence['evidence'][0]['end']=2
    with pytest.raises(AssertionError):
        report.quote_count(evidence,doc)


def test_report_refuses_before_all_phase_jobs_final(tmp_path,monkeypatch):
    monkeypatch.setattr(report,'RUN',tmp_path)
    files={'preparation.json':{'input_sha256':{},'control_key_sha256':{},'source_code_sha256':{}},
           'preservation-before.json':{},'jobs.json':[{'job_id':'not_final','phase':'development'}]}
    for name,value in files.items():
        (tmp_path/name).write_text(json.dumps(value))
    with pytest.raises(ValueError,match='All phase judgments must finalize'):
        report.build('development')
