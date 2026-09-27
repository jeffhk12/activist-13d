"""Tier: 1. Reconcile event registry and publish Phase 1 feasibility handoff.

Inputs: frozen event candidates and summaries. Outputs: review queue and HTML,
sequential attrition counts, Markdown handoff, verification receipt.
Identity: each accession occurs once; every attrition stage is a subset of the
preceding stage. Candidate readiness does not establish campaign eligibility.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/report_phase1_feasibility.py
"""
import html
import json
import os
from collections import Counter
from pathlib import Path

from ingest_hfr_quarterly import ROOT, digest, encode, freeze
from phase1_event_feasibility import OUT

from activist13d.local_paths import resolve_project_path


def attrition(rows):
    stages = [('initial_filings', lambda r: True),
              ('source_verified', lambda r: r['source_status'] == 'hash_and_size_verified'),
              ('historical_security_candidate', lambda r: r['security_link']['permno'] is not None),
              ('corporate_common_screen', lambda r: r['security_screen'] == 'corporate_common_candidate'),
              ('positive_entry_open_observed', lambda r: r['entry_price_status'] == 'positive_open_observed'),
              ('basic_identity_and_date_checks', lambda r: not r['amendment_flag_conflict']
               and not r['publication_date_disagrees'] and r['cusip_check_digit_valid'] is not False
               and bool(r['candidate_group_key']) and not r['issuer_also_filing_party'])]
    output = []
    for name, predicate in stages:
        rows = [r for r in rows if predicate(r)]
        output.append({'stage': name, 'remaining': len(rows)})
    assert all(a['remaining'] >= b['remaining'] for a, b in zip(output, output[1:], strict=False))
    return output


def main():
    summary = json.loads((OUT / 'summary.json').read_text())
    provenance = json.loads((OUT / 'provenance.json').read_text())
    assert digest(OUT / 'event-candidates.jsonl') == provenance['event_candidates_sha256']
    assert digest(OUT / 'source-inventory.json') == provenance['source_inventory_sha256']
    records = [json.loads(line) for line in (OUT / 'event-candidates.jsonl').read_text().splitlines()]
    assert len(records) == len({r['accession'] for r in records})
    broad = [r for r in records if r['broad_manager_subset']]
    focused = [r for r in records if r['focused_activist_subset']]
    cohorts = {'all_initials': records, 'broad_manager_subset': broad, 'focused_activist_subset': focused,
               'other_or_unresolved': [r for r in records if not r['broad_manager_subset']]}
    for name, rows in cohorts.items():
        assert len(rows) == summary['groups'][name]['initial_filings']
        assert attrition(rows)[-1]['remaining'] == summary['groups'][name]['preliminary_data_ready_candidates']
    assert set(r['accession'] for r in focused) <= set(r['accession'] for r in broad)
    stages = {name: attrition(rows) for name, rows in cohorts.items()}
    freeze(OUT / 'attrition.json', encode(stages))
    queue = []
    for r in records:
        reasons = []
        if r['source_status'] != 'hash_and_size_verified':
            reasons.append(r['source_status'])
        if r['security_screen'] != 'corporate_common_candidate':
            reasons.append(r['security_screen'])
        if r['entry_price_status'] != 'positive_open_observed':
            reasons.append(r['entry_price_status'])
        if r['cusip_check_digit_valid'] is False:
            reasons.append('cusip_check_digit_failure')
        if r['issuer_also_filing_party']:
            reasons.append('issuer_also_filing_party')
        if r['initials_with_same_exact_party_issuer_key'] > 1:
            reasons.append('repeated_initial_same_exact_group')
        if r['initials_same_security_filing_date'] > 1:
            reasons.append('multiple_initials_same_security_date')
        if r['publication_date_disagrees'] or r['amendment_flag_conflict']:
            reasons.append('date_or_form_conflict')
        if reasons:
            queue.append({'accession': r['accession'], 'broad_manager_subset': r['broad_manager_subset'],
                          'reasons': sorted(set(reasons))})
    freeze(OUT / 'review-queue.json', encode(queue))
    e = html.escape
    rows = []
    for r in sorted(broad, key=lambda r: (r['filing_date'], r['accession'])):
        source = resolve_project_path(r['source_path'], ROOT)
        label = e(r['accession'])
        if source.is_file():
            label = f'<a href="{e(os.path.relpath(source, OUT))}">{label}</a>'
        issuer = '; '.join(x.get('name', '') for x in r['subjects'])
        filers = '; '.join(x.get('name', '') for x in r['filers'])
        rows.append(f'<tr><td>{label}<br>{e(r["filing_date"])}</td><td>{e(issuer)}</td><td>{e(filers)}</td><td>{r["security_link"]["permno"] or "unresolved"}<br>{e(r["security_screen"])}</td><td>{e(r["entry_date_audit_proxy"] or "unavailable")}<br>{e(r["entry_price_status"])}</td></tr>')
    freeze(OUT / 'initial-manager-review.html', '''<!doctype html><html lang="en"><meta charset="utf-8"><title>Initial manager filings: feasibility</title><style>body{font:15px/1.5 system-ui;color:#243647;margin:30px}td,th{padding:10px;border-bottom:1px solid #ddd;vertical-align:top;text-align:left}table{border-collapse:collapse;width:100%}input{font:inherit;padding:12px;width:70%}a{color:#145b92}</style><h1>404 initial manager-subset filings</h1><p>Candidate identities and price availability. No investment intent labels or future returns. Security types and entry dates are feasibility screens, not final eligibility or trading instructions.</p><p><a href="index.html">Coverage summary</a> · <a href="review-queue.json">All issues</a> · <a href="HANDOFF.md">Handoff</a></p><input aria-label="Search initial filings" placeholder="Search investor, issuer, date or security status" oninput="document.querySelectorAll('tbody tr').forEach(r=>r.hidden=!r.textContent.toLowerCase().includes(this.value.toLowerCase()))"><table><thead><tr><th>Filing</th><th>Issuer</th><th>Reporting entities</th><th>Security link/screen</th><th>Entry availability proxy</th></tr></thead><tbody>''' + ''.join(rows) + '</tbody></table></html>')
    group_table = '\n'.join(f'| {name} | {v["initial_filings"]:,} | {v["historical_security_candidates"]:,} | {v["security_screen"].get("corporate_common_candidate",0):,} | {v["corporate_common_with_positive_open"]:,} | {v["preliminary_data_ready_candidates"]:,} |' for name,v in summary['groups'].items())
    b = summary['groups']['broad_manager_subset']
    all_counts = summary['groups']['all_initials']
    freeze(OUT / 'HANDOFF.md', f'''# Phase 1 started: initial-disclosure feasibility — 24 September 2026

Active project: `/Users/jefflu/Projects/activist-13d`.
Run: `/Users/jefflu/Projects/activist-13d/research/runs/phase1-baseline/20260924-feasibility-v2/`.
[Coverage](index.html) · [404 manager initial filings](initial-manager-review.html).

## Completed work

Created an accession-level registry for all parsed initial 13Ds in the local
75,631-record archive. Preserved every candidate and its source/hash status;
no amendment was promoted to an initial event. Applied dated historical CUSIP
matching to cached CIZ name records and preserved all matching evidence.
Compared with frozen legacy links, flagged repeated exact party/issuer groups
and simultaneous security/date initials, and tested actual cached opening-price
availability. No performance comparison or future return values were analyzed.

| Group | Initial filings | CIZ security links | Corporate common candidates | Corporate common + positive open | Preliminary data-ready candidates |
|---|---:|---:|---:|---:|---:|
{group_table}

These columns are parallel diagnostics except the final readiness count; use
`attrition.json` for sequential exclusions. Focused is within broad; other/unresolved
is the broad complement. Counts remain filings, not independent campaigns.
Readiness requires verified source bytes/hash, a unique historical security link,
the corporate-common screen, positive opening price, basic date/form/party checks,
and no failed CUSIP check digit. It does not certify investor identity, source
parser accuracy, operating-company status, tradability or event independence.

## Material findings

- The legacy link file used name records ending in 2024 and had no matches for
  2025/2026. CIZ matching recovered {all_counts['new_ciz_matches_without_legacy']:,}
  initial security candidates without legacy matches, including {b['new_ciz_matches_without_legacy']}
  in the manager subset. Full year-specific coverage is in summary.json.
- Legacy/CIZ PERMNO disagreements among doubly matched initials:
  {all_counts['legacy_ciz_permno_disagreements']}. No disagreement is silently resolved.
- Cached CRSP index sessions end {summary['cached_index_calendar']['last']}.
  The earlier daily-cache audit has no 2026 price observations. Recent filings
  remain flagged; their absence from price-ready counts is not an outcome.
- Source statuses across initials: `{json.dumps(all_counts['source_status'], sort_keys=True)}`.
- Manager-subset security screens: `{json.dumps(b['security_screen'], sort_keys=True)}`.

## Conventions and limitations

CIZ historical `cusip` is used; `hdrcusip` is not substituted. Inclusive name
intervals must contain the filing date; no interval is extended beyond its end.
Multiple PERMNOs are refused, and conflicting security codes are flagged.
The provisional corporate-common screen is EQTY/COM/NS and CORP or ACOR.
US incorporation remains recorded rather than silently restricting geography.
Funds, REITs, ADRs and other classes are separately flagged, not deleted.

Entry-date audit proxy is the second XNYS session strictly after
the acceptance date, conservatively leaving a full intervening session. This
supports feasibility and does not freeze intraday timing. The calendar uses
exchange-calendars 4.13.2; its dates are preserved in entry-calendar.json and
compared with the overlapping cached index dates. Final exact execution rules
and security-specific calendar applicability remain to be specified. A
positive opening price does not prove liquidity, price quality or achievable fills.
The audit reads entry-date pages, not holding-window returns. Corporate actions,
delisting conventions and independent vendor coverage reconciliation remain open.

HFR membership is based on unverified historical delivery proxies. The supplemental
managers are retrospectively selected and search a wider period. `common_hfr_period`
in summary.json reports counts after the first supplied snapshot, not certified
historical investability. Missing manager matches are other/unresolved, not passive.

The registry still uses the archived pilot-v1 extraction fields, not the enhanced
52-filing deterministic parser across the full archive. Null/invalid CUSIPs need
source review or a separately versioned reparse, never a fuzzy stock-name fill.
Any known human-development material stays separate from future NLP holdout selection.

This v2 run supersedes the preserved v1 feasibility run, which was limited by
the legacy index calendar ending in 2024. Version 2 uses an independent calendar
through 2026 to check available 2025 prices without extending the legacy data.
Acceptance-date versus filing-date differences are review flags, not necessarily
SEC errors (an after-hours submission can receive a later official filing date).

## Next work before a return comparison

1. Review manager-subset source, identifier and security-type issues in
   `initial-manager-review.html` and `review-queue.json`; verify manager relationships.
2. Resolve missing CUSIPs and compare issuer identities with linked securities.
   Define joint filings, re-entry and overlapping issuer entries; repeated exact
   group keys are diagnostics, not a completed amendment/event chain.
3. Reconcile daily-cache coverage and return/price conventions; decide whether to
   obtain 2026 data or make the first historical comparison end earlier explicitly.
4. Review the primary horizon, benchmark and event/security eligibility choices,
   then freeze the execution and evaluation specification before viewing results.
5. Build fixed-horizon outcomes and the cost-aware portfolio ledger only after those gates.

## Reproducibility

Implementation: `scripts/data_collection/phase1_event_feasibility.py` and
`report_phase1_feasibility.py`; focused tests in `test_phase1_event_feasibility.py`.
Use project `.venv/bin/python` with `PYTHONPATH=src`, `PYTHONNOUSERSITE=1` and
`PYTHONIOENCODING=utf-8`. Original sources and prior outputs are unchanged.
Vendor pages used here were checked against frozen uncompressed hashes and byte
counts; raw initial submissions were checked against their archived size/hash.
Frozen outputs refuse differing replay content. Provenance records inputs and code.

Official code references checked 24 September 2026:
- [CRSP share-code mapping](https://www.crsp.org/wp-content/uploads/ShareCode.html)
- [WRDS CIZ-to-SIZ mapping](https://wrds-www.wharton.upenn.edu/pages/wrds-research/macros/crsp-ciztosiz-macro/)

No paid models, new vendor-data collection, NLP labels, fitted models or backtest
were run. Phase 1 is underway; its completed milestone is the feasibility registry,
not a performance finding.
''')
    receipt = {'registry_sha256_verified': True, 'cohort_counts_reconciled': True,
               'attrition_monotone_and_reconciled': True, 'unique_initial_accessions': len(records),
               'review_queue_filings': len(queue), 'report_script_sha256': digest(Path(__file__)),
               'broad_review_queue_reason_counts': dict(Counter(reason for item in queue if item['broad_manager_subset'] for reason in item['reasons']))}
    freeze(OUT / 'verification.json', encode(receipt))
    print(encode(receipt))


if __name__ == '__main__':
    main()
