"""Hand-pinned timing/unit comparisons and exact pilot replay.

Inputs: invented dates/amounts and optional saved ten-case evidence.
Output: assertions. Identity: USD=source amount*unit scale; never fill missing
vendor values with zero or infer same-day availability. Tier: 1 support.
Run: project Python -m pytest tests/test_bloomberg_timing.py.
"""
import importlib.util
from pathlib import Path

import pytest

PATH=Path(__file__).parents[1]/'scripts/ml_experiment/audit_bloomberg_timing.py'
SPEC=importlib.util.spec_from_file_location('bloomberg_timing',PATH)
audit=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def test_units_and_difference_hand_pinned():
    assert audit.amount_comparison(1234000,1234,1000)=={'status':'match','source_usd':1234000,'difference_usd':0}
    assert audit.amount_comparison(1234500,1234,1000)['difference_usd']==500
    assert audit.amount_comparison(-5000,-5,1000)['status']=='match'


def test_missing_vendor_result_stays_unavailable_and_zero_is_valid():
    assert audit.amount_comparison('#N/A',0)['status']=='workbook_missing_or_error'
    assert audit.amount_comparison(None,0)['difference_usd'] is None
    assert audit.amount_comparison(0,0)['status']=='match'


def test_invalid_source_units_refused():
    for value,multiplier in [(None,1),(1,0),(True,1),(1,float('inf'))]:
        with pytest.raises(ValueError):
            audit.amount_comparison(1,value,multiplier)


def test_strict_dates_and_same_day_ambiguity():
    assert audit.date_position('2019-02-07','2019-01-03')=='after'
    assert audit.date_position('2019-03-06','2019-12-10')=='before'
    assert audit.date_position('2021-05-14','2021-05-14')=='same_day_time_unverified'
    assert audit.date_position(None,'2021-05-14')=='unknown'


def test_issues_are_separate_from_whole_row_accuracy_certification():
    assert audit.ISSUES['F06']==['historical_issuer_mismatch']
    assert audit.ISSUES['F04']==['historical_revision']
    assert audit.ISSUES['F10']==['older_annual_period']
    assert audit.ISSUES['F09']==['field_definition_unresolved']


def test_optional_exact_evidence_replay():
    if not (audit.RUN/'research/group-root.json').exists():
        pytest.skip('Local source-evidence pilot absent in CI')
    first,summary=audit.build()
    second,replay=audit.build()
    assert first==second and summary==replay
    assert summary['selected_events']==10 and summary['selected_raw_field_slots']==90
    assert summary['events_with_identified_issues']==6
    assert summary['period_dates_after_cutoff']==2
    assert summary['all_nine_historical_field_certifications']==0
