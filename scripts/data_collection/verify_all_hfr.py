"""Tier: 1. Verify expanded HFR matches and prepare a non-outcome cohort overlay.

Inputs: frozen all-HFR run, supplemental accession sets, feasibility registry.
Outputs: separate checks, mutually exclusive filing groups, initial-readiness overlay.
Identities: focused + other ED + other HFR + unresolved = all 75,631 filings;
readiness exactly reproduces the preserved feasibility rule, not final eligibility.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/verify_all_hfr.py
"""
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from run_phase1_development import ROOT, digest, encode, freeze

RUN = ROOT / 'research/runs/hfr-all-managers/20260924-v1'
OUT = ROOT / 'research/runs/hfr-all-managers/20260924-verification-v1'
FEASIBILITY = ROOT / 'research/runs/phase1-baseline/20260924-feasibility-v2'


def ready(r):
    return (r['security_screen'] == 'corporate_common_candidate'
            and r['source_status'] == 'hash_and_size_verified'
            and r['entry_price_status'] == 'positive_open_observed'
            and not r['amendment_flag_conflict'] and not r['publication_date_disagrees']
            and r['cusip_check_digit_valid'] is not False
            and bool(r['candidate_group_key']) and not r['issuer_also_filing_party'])


class Links(HTMLParser):
    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key == 'href':
                url = urlsplit(value)
                if not url.scheme and url.path:
                    assert (RUN / unquote(url.path)).resolve().exists(), value


def main():
    provenance = json.loads((RUN / 'provenance.json').read_text())
    for name, expected in provenance.items():
        assert digest(RUN / name) == expected, name
    summary = json.loads((RUN / 'summary.json').read_text())
    unions = {k: set(v) for k, v in json.loads((RUN / 'accession-unions.json').read_text()).items()}
    candidates = json.loads((RUN / 'candidates.json').read_text())
    assert len(candidates) == len({r['accession'] for r in candidates}) == summary['cohorts']['all_hfr']['filings']
    assert len({h['firm_id'] for r in candidates for h in r['matches']}) == summary['matched_firm_ids']
    assert all(r['delivery_date_proxy'] < r['filing_date'] for r in candidates)
    assert unions['previous_hfr_event_driven_screen'] <= unions['all_hfr']
    assert unions['all_hfr'] | unions['supplement'] == unions['all_hfr_plus_supplement']
    # Explicit precedence makes the comparison groups mutually exclusive.
    focused = unions['manager_has_activist'] | unions['supplement']
    other_ed = unions['manager_has_event_driven'] - focused
    other_hfr = unions['all_hfr'] - focused - other_ed
    cohorts = dict(focused_activist_candidates=focused, other_event_driven_candidates=other_ed,
                   other_hfr_candidates=other_hfr,
                   other_or_unresolved=unions['other_or_unresolved_after_expansion'])
    assert sum(map(len, cohorts.values())) == len(set().union(*cohorts.values())) == 75631
    old_focused = set(json.loads((ROOT / 'research/runs/investor-identity/20260924-supplemental-v1/accession-unions.json').read_text())['hfr_activist_plus_supplement'])
    assert focused == old_focused
    path = FEASIBILITY / 'event-candidates.jsonl'
    expected = json.loads((FEASIBILITY / 'provenance.json').read_text())['event_candidates_sha256']
    assert digest(path) == expected
    records = [json.loads(line) for line in path.read_text().splitlines()]
    assert sum(ready(r) for r in records) == 7939
    assert sum(ready(r) and r['broad_manager_subset'] for r in records) == 240
    assert sum(ready(r) and r['focused_activist_subset'] for r in records) == 191
    overlay = []
    for r in records:
        group = next(k for k, ids in cohorts.items() if r['accession'] in ids)
        if group != 'other_or_unresolved':
            overlay.append(dict(accession=r['accession'], filing_date=r['filing_date'], cohort=group,
                in_all_hfr=r['accession'] in unions['all_hfr'],
                in_supplement=r['accession'] in unions['supplement'],
                basic_data_ready=ready(r), eligibility='not_validated'))
    counts = {group: dict(filings=len(ids), initials=sum(r['accession'] in ids for r in records),
        basic_ready_initials=sum(r['accession'] in ids and ready(r) for r in records))
        for group, ids in cohorts.items()}
    assert len(overlay) == summary['cohorts']['all_hfr_plus_supplement']['initials']
    for path in RUN.glob('*.html'):
        Links().feed(path.read_text())
    freeze(OUT / 'disjoint-cohorts.json', encode({k: sorted(v) for k, v in cohorts.items()}))
    freeze(OUT / 'initial-filings-overlay.json', encode(overlay))
    freeze(OUT / 'cohort-counts.json', encode(counts))
    freeze(OUT / 'verification.json', encode(dict(run_hashes_verified=True,
        prior_hfr_matches_preserved=True, focused_cohort_unchanged=True,
        accession_unions_reconciled=True, unique_candidate_accessions=True,
        snapshot_dates_precede_filing_dates=True, local_html_links_verified=True,
        legacy_readiness_counts_reproduced=True, returns_recalculated=False,
        script_sha256=digest(Path(__file__)), source_run_provenance_sha256=digest(RUN / 'provenance.json'))))
    print(encode(counts))


if __name__ == '__main__':
    main()
