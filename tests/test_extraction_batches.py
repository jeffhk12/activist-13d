"""Synthetic pins for production-queue exclusions, preservation and determinism."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/extraction_protocol'))
from extraction_batches import frozen, groups, make_queue  # noqa: E402
from extraction_batches_v2 import same_replayed_judgment  # noqa: E402
from verify_extraction_batch import covered_length  # noqa: E402


def row(accession, issuer, reporters=(), chars=50):
    return {'accession': accession, 'issuer': issuer, 'reporter_ciks': list(reporters),
            'source_form': 'SC 13D', 'canonical_text_chars': chars}


def test_shared_reporter_propagates_protection():
    rows = [row('a', '1', ['9']), row('b', '2', ['9']), row('c', '3')]
    result = make_queue(rows, {'a'}, set(), set(), set())
    assert result['queued_filings'] == 1
    assert result['exclusion_counts'] == {'human_protected_connected_group': 2}
    assert result['queue'][0]['accession'] == 'c'


def test_reservations_completed_and_long_sources_reconcile():
    rows = [row('a', '1'), row('b', '2'), row('c', '3', chars=100001), row('d', '4')]
    result = make_queue(rows, set(), set(), {'a'}, {'b'})
    assert result['panel_filings'] == 4
    assert result['excluded_filings'] == result['queued_filings'] == 2
    assert result['exclusion_counts'] == {'already_completed_v3': 1, 'unreleased_reserved_connected_group': 1}
    assert [r['accession'] for r in result['queue']] == ['d', 'c']
    assert result['workload_counts'] == {'regular': 1, 'long': 1}


def test_connected_components_transitive_and_input_order_independent():
    rows = [row('a', '1', ['8']), row('b', '2', ['8', '9']), row('c', '3', ['9'])]
    assert len(set(groups(rows).values())) == 1
    assert groups(rows) == groups(list(reversed(rows)))


def test_queue_replay_and_five_case_batch_boundary():
    rows = [row(str(i), str(i)) for i in range(7)]
    result = make_queue(rows, set(), set(), set(), set())
    assert result == make_queue(list(reversed(rows)), set(), set(), set(), set())
    assert Counter_for_batches(result) == {1: 5, 2: 2}


def Counter_for_batches(result):
    return {i: sum(r['batch_number'] == i for r in result['queue']) for i in [1, 2]}


def test_frozen_output_replays_and_refuses_changes(tmp_path):
    path = tmp_path / 'record.json'
    frozen(path, {'value': 3})
    original = path.read_bytes()
    frozen(path, {'value': 3})
    assert path.read_bytes() == original
    with pytest.raises(ValueError, match='Immutable output differs'):
        frozen(path, {'value': 4})


def test_missing_and_noninitial_sources_not_silently_classified():
    initial = row('a', '1', chars=0)
    amendment = {**row('b', '2'), 'source_form': 'SC 13D/A'}
    result = make_queue([initial, amendment], set(), set(), set(), set())
    assert result['queued_filings'] == 0
    assert result['exclusion_counts'] == {'no_readable_source': 1, 'not_initial_source_form': 1}


def test_independent_coverage_merges_overlap_without_double_counting():
    assert covered_length([(3, 7), (0, 4), (7, 10)], 10) == 10


def test_independent_coverage_refuses_holes_or_missing_tail():
    with pytest.raises(ValueError, match='missing source range'):
        covered_length([(0, 3), (4, 10)], 10)
    with pytest.raises(ValueError, match='tail not delivered'):
        covered_length([(0, 9)], 10)


def test_replay_ignores_overwritten_model_metadata_but_not_judgments():
    draft = {'intent': {'sale': 'present'}, 'run_metadata': {'provider': 'model_supplied'}}
    final = {'intent': {'sale': 'present'}, 'run_metadata': {'provider': 'trusted_finalizer'}}
    assert draft != {k: v for k, v in final.items() if k != 'run_metadata'}
    assert same_replayed_judgment(draft, final)
    assert not same_replayed_judgment(draft, {**final, 'intent': {'sale': 'not_stated'}})
