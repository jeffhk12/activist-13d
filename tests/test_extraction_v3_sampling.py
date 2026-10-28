"""Invented-metadata pins for the three-case v3 operational selection.

Inputs: fictional metadata only. Outputs: count, cap, exclusion and replay checks.
Identity: n=3 with both eras, distinct accession/group/issuer; gap preference then
explicit fallbacks. Tier:1 support. Run project Python -m pytest this file.
"""
import sys
from copy import deepcopy
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts/extraction_protocol'))
from extraction_v3_sampling import select_fresh  # noqa: E402


def row(accession, era, *, chars=1000, documents=3, missing=1, **extra):
    return {'accession': accession, 'era': era, 'connected_group': 'group-' + accession,
            'issuer': 'issuer-' + accession, 'canonical_text_chars': chars,
            'canonical_documents': documents, 'documents_without_text': missing,
            'source_path': 'fictional/' + accession + '.txt', 'source_sha256': 'a'*64,
            'reporter_ciks': ['fictional-reporter-' + accession], **extra}


def frame(*, documents=3, missing=1):
    return [row('E1', 'early', documents=documents, missing=missing),
            row('R1', 'recent', documents=documents, missing=missing),
            row('E2', 'early', documents=documents, missing=missing),
            row('R2', 'recent', documents=documents, missing=missing)]


def test_three_cases_two_eras_unique_and_gap_preferred():
    selected, trace = select_fresh(frame())
    # Three fixed slots; neither era can disappear and no entity repeats.
    assert len(selected) == 3
    assert selected[0]['era'] == 'early' and selected[1]['era'] == 'recent'
    assert len({r['accession'] for r in selected}) == 3
    assert len({r['connected_group'] for r in selected}) == 3
    assert len({r['issuer'] for r in selected}) == 3
    assert trace['slots'][2]['preference'] == 'documents_without_text'
    assert trace['slots'][2]['fallback_used'] is False


def test_seeded_selection_replays_and_does_not_mutate_or_alias_input():
    rows = frame()
    original = deepcopy(rows)
    selected, trace = select_fresh(rows)
    replay, replay_trace = select_fresh(reversed(rows))
    assert selected == replay and trace == replay_trace
    assert rows == original
    selected[0]['reporter_ciks'].append('separate-copy')
    assert rows == original


def test_explicit_multiple_document_and_any_fallbacks():
    _, multiple = select_fresh(frame(missing=0))
    assert multiple['slots'][2]['preference'] == 'multiple_documents'
    assert multiple['slots'][2]['fallback_used'] is True
    assert multiple['slots'][2]['preference_counts_after_prior_slots'] == {
        'documents_without_text': 0, 'multiple_documents': 2, 'any': 2}
    _, ordinary = select_fresh(frame(documents=1, missing=0))
    assert ordinary['slots'][2]['preference'] == 'any'
    assert ordinary['slots'][2]['fallback_used'] is True


def test_character_boundary_and_all_three_exclusion_kinds():
    rows = frame()
    rows[0]['canonical_text_chars'] = 100000
    rows.extend([row('too-long', 'early', chars=100001),
                 row('seen-accession', 'early'), row('seen-group', 'recent'),
                 row('seen-issuer', 'recent')])
    selected, trace = select_fresh(rows, ['seen-accession'],
                                   excluded_groups=['group-seen-group'],
                                   excluded_issuers=['issuer-seen-issuer'])
    assert len(selected) == 3
    assert all(r['canonical_text_chars'] <= 100000 for r in selected)
    assert not {'too-long', 'seen-accession', 'seen-group', 'seen-issuer'} & {
        r['accession'] for r in selected}
    assert trace['filtered_reason_counts'] == {'above_character_cap': 1,
        'excluded_accession': 1, 'excluded_group': 1, 'excluded_issuer': 1}


def test_duplicate_issuer_and_group_are_not_selected_twice():
    rows = frame()
    rows.extend([row('same-group', 'early', connected_group=rows[0]['connected_group']),
                 row('same-issuer', 'recent', issuer=rows[1]['issuer'])])
    selected, _ = select_fresh(rows)
    assert len({r['connected_group'] for r in selected}) == 3
    assert len({r['issuer'] for r in selected}) == 3


def test_unavailable_metadata_and_unfillable_frame_refuse():
    rows = frame()
    invalid = row('no-evidence', 'early')
    invalid.pop('source_sha256')
    selected, trace = select_fresh(rows + [invalid])
    assert len(selected) == 3
    assert trace['filtered_reason_counts'] == {'unavailable_source_hash_metadata': 1}
    with pytest.raises(ValueError, match='Unfillable'):
        select_fresh([row(str(i), 'early') for i in range(4)])
    with pytest.raises(ValueError, match='Unfillable'):
        select_fresh(rows[:2])
    with pytest.raises(ValueError, match='Duplicate accession'):
        select_fresh(rows + [deepcopy(rows[0])])
    with pytest.raises(ValueError, match='not one string'):
        select_fresh(rows, excluded_accessions='E1')


def test_surplus_invented_outcome_values_do_not_change_selection():
    rows = frame()
    selected, trace = select_fresh(rows)
    changed = [{**r, 'invented_future_return': i*999999} for i, r in enumerate(reversed(rows))]
    again, again_trace = select_fresh(changed)
    assert [r['accession'] for r in selected] == [r['accession'] for r in again]
    assert trace == again_trace
