"""Hand-counted pins for larger reporting groups without changing extraction."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from extraction_reporting_groups import aggregate_summaries, build_groups  # noqa: E402


def rows(count):
    return [{'accession': f'a{i:03}', 'queue_position': i, 'batch_number': (i-1)//5+1} for i in range(1, count+1)]


def test_two_new_groups_keep_all_existing_checkpoint_boundaries():
    result = build_groups(rows(80))
    assert len(result) == 2  # 80 minus six completed5-filing checkpoints =50.
    assert result[0]['queue_positions'] == list(range(31, 56))
    assert result[0]['checkpoint_batches'] == [7, 8, 9, 10, 11]
    assert result[1]['reporting_batch'] == 8
    assert result[1]['checkpoint_batches'] == [12, 13, 14, 15, 16]
    assert result[0]['jobs'] == result[1]['jobs'] == 75


def test_full_queue_remaining_count_final_partial_and_no_overlap():
    result = build_groups(rows(627))
    assert len(result) == 24
    assert [r['filings'] for r in result] == [25]*23 + [22]
    assert result[-1]['jobs'] == 66
    assert result[-1]['checkpoint_filing_counts']['126'] == 2
    positions = [p for r in result for p in r['queue_positions']]
    assert positions == list(range(31, 628))  # 597 once each.


def test_reporting_size_must_keep_whole_checkpoints():
    with pytest.raises(ValueError, match='multiple of five'):
        build_groups(rows(80), size=12)


def test_duplicate_source_or_missing_position_refuses():
    example = rows(80)
    with pytest.raises(ValueError, match='Duplicate'):
        build_groups([*example[:-1], {**example[-1], 'accession': 'a001'}])
    with pytest.raises(ValueError, match='contiguous'):
        build_groups([r for r in example if r['queue_position'] != 40])


def test_aggregation_reconciles_denominators_and_keeps_flags():
    a = {'filings': 5, 'jobs': 15, 'intent_cells': 45, 'intent_agreement': 44,
         'eligible_experimental_intents': 44, 'critic_claims': 144, 'exact_quote_entries': 800,
         'critic_verdicts': {'supported': 143, 'insufficient_evidence': 1}}
    b = {**a, 'intent_agreement': 45, 'critic_claims': 143, 'exact_quote_entries': 847,
         'critic_verdicts': {'supported': 142, 'contradicted': 1}}
    result = aggregate_summaries([a, b])
    assert (result['filings'], result['jobs'], result['intent_cells']) == (10, 30, 90)
    assert (result['intent_agreement'], result['eligible_experimental_intents']) == (89, 88)
    assert result['critic_claims'] == 287
    assert result['critic_verdicts'] == {'supported': 285, 'insufficient_evidence': 1, 'contradicted': 1}
    assert result['exact_quote_entries'] == 1647
    assert result == aggregate_summaries([b, a])
