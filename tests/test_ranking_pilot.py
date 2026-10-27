"""Tier 1 pins for outcome-blind pilot sampling and source-only deliverables."""
import importlib.util
import json
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ranking_pilot', ROOT/'scripts/extraction_protocol/build_ranking_pilot.py')
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


def fixture_rows():
    rows = []
    for era, years in [('early', ['2018','2019','2020']), ('recent', ['2021','2022','2023'])]:
        for i in range(30):
            rows.append({'accession': f'{era}-{i}', 'issuer': f'{era}-issuer-{i}',
                         'reporter_ciks': [f'{era}-reporter-{i}'], 'era': era,
                         'entry_year': years[i % 3], 'industry': f'{i:02}',
                         'document_types': ['SC 13D'] if i % 2 else ['SC 13D','EX-99'],
                         'item4_spans': 0 if i < 4 else 1, 'reporting_person_count': 1 if i % 2 else 3,
                         'canonical_documents': 1 if i % 2 else 2})
    return rows


def test_connected_groups_include_transitive_issuer_and_reporter_links():
    rows = [{'accession':'A','issuer':'I1','reporter_ciks':['R1']},
            {'accession':'B','issuer':'I2','reporter_ciks':['R1']},
            {'accession':'C','issuer':'I2','reporter_ciks':['R2']},
            {'accession':'D','issuer':'I3','reporter_ciks':['R3']}]
    groups = pilot.components(rows)
    assert groups['A'] == groups['B'] == groups['C']
    assert groups['D'] != groups['A']


def test_selection_ignores_input_order_and_invented_outcomes():
    protocol = json.loads(pilot.PROTOCOL.read_text())
    rows = fixture_rows()
    selected, trace, _ = pilot.choose(rows, protocol, set(), set())
    modified = [{**r, 'future_return': (-1 if i % 2 else 1)*999999} for i,r in enumerate(reversed(rows))]
    again, trace_again, _ = pilot.choose(modified, protocol, set(), set())
    assert [[r['accession'] for r in selected[k]] for k in selected] == [[r['accession'] for r in again[k]] for k in again]
    assert trace == trace_again
    assert all(Counter(r['era'] for r in cases) == {'early':5,'recent':5} for cases in selected.values())


def test_exposure_blocks_connected_component_and_unfillable_slots_refuse():
    protocol = json.loads(pilot.PROTOCOL.read_text())
    rows = fixture_rows()
    rows[1]['reporter_ciks'] = rows[0]['reporter_ciks']
    selected, _, _ = pilot.choose(rows, protocol, {rows[0]['accession']}, set())
    assert not {rows[0]['accession'],rows[1]['accession']} & {r['accession'] for cases in selected.values() for r in cases}
    with pytest.raises(ValueError, match='Unfillable'):
        pilot.choose(rows[:1], protocol, set(), set())


def test_prepared_human_pack_has_blank_answers_and_validation_stays_reserved():
    manifest = json.loads((pilot.RUN/'sample-manifest.json').read_text())
    cases = manifest['selection']['discovery'] + manifest['selection']['validation_reserved']
    assert len(cases) == len({r['issuer'] for r in cases}) == len({r['connected_group'] for r in cases}) == 20
    for r in manifest['selection']['discovery']:
        blank = json.loads((pilot.PACK/'discovery/blank-answers'/f'{r["accession"]}.json').read_text())
        assert all(v == '' for v in blank['answers'].values())
        assert blank['evidence'] == [] and blank['reviewed_at_utc'] is None
        assert blank['independent_reading_completed'] is False
    assert not list((pilot.PACK/'validation-reserved').glob('0*.html'))
    assert len(list((pilot.PACK/'validation-reserved/evidence').glob('*.json.gz'))) == 10
