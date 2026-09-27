"""Tier: 1. Reconcile quarterly HFR extraction and publish its continuation note.

Inputs: frozen import, dated screen and earlier current-snapshot name screen.
Outputs: validation JSON and readable HTML/Markdown report with source links.
Identity: filing counts are unique accessions; coverage and ambiguity are separate
from identity verification. A missing source is never treated as missing intent.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/report_hfr_quarterly.py
"""
from __future__ import annotations

import html
import json
from collections import Counter

from ingest_hfr_quarterly import OUT, ROOT, encode, freeze, summarize
from screen_hfr_quarterly import prior_index

from activist13d.local_paths import resolve_project_path


def build():
    manifest = json.loads((OUT / 'manifest.json').read_text())
    managers = json.loads((OUT / 'managers.json').read_text())
    summary = json.loads((OUT / 'sec-screen/summary.json').read_text())
    candidates = json.loads((OUT / 'sec-screen/candidates.json').read_text())
    snapshots = manifest['snapshots']
    dates = [s['delivery_date_proxy'] for s in snapshots]
    issues = []
    for snapshot in snapshots:
        data = json.loads((OUT / 'snapshots' / f'{snapshot["quarter"]}.json').read_text())
        recalculated = summarize(data['funds'])
        assert all(snapshot[k] == v for k, v in recalculated.items())
        assert snapshot['vendor_datestamp'] <= snapshot['delivery_date_proxy']
        assert snapshot['missing_fund_id_rows'] == 0
        assert snapshot['duplicate_fund_id_excess_rows'] == 0
        if snapshot['missing_firm_id_rows']:
            issues.append({'quarter': snapshot['quarter'], 'missing_firm_id_rows': snapshot['missing_firm_id_rows']})
    assert len(candidates) == len({c['accession'] for c in candidates}) == summary['candidate_accessions']
    assert summary['candidate_initials'] + summary['candidate_amendments'] == len(candidates)
    assert summary['activist_initials'] + summary['activist_amendments'] == summary['activist_candidate_accessions']
    assert summary['records_with_prior_snapshot_proxy'] + summary['no_strictly_prior_snapshot'] + summary.get('invalid_or_missing_filing_date', 0) == summary['local_13d_records']
    missing_sources, ambiguous = [], []
    activist_initials = []
    concentration = Counter()
    for c in candidates:
        assert c['delivery_date_proxy'] < c['filing_date']
        assert snapshots[prior_index(dates, c['filing_date'])]['quarter'] == c['quarter']
        if not c.get('source_path') or not resolve_project_path(c['source_path'], ROOT).is_file():
            missing_sources.append(c['accession'])
        if len({m['firm_id'] for m in c['matches']}) > 1:
            ambiguous.append(c['accession'])
        act_firms = {m['firm_id'] for m in c['matches'] if m['activist_in_selected_snapshot']}
        concentration.update(act_firms)
        if act_firms and c['form'] == '13D':
            activist_initials.append(c)
    assert len(ambiguous) == summary.get('cross_manager_ambiguous_accessions', 0)
    old = json.loads((ROOT / 'research/runs/investor-identity/20260923-hfr-event-driven-v1/matches.json').read_text())
    old_activists = {m['firm_id'] for m in old['managers'] if 'Activist' in m['substrategies']}
    recovered = []
    for firm in manifest['summary']['historical_activist_ids_outside_latest_activist']:
        obs = [m for m in managers if m['firm_id'] == firm and 'Activist' in m['substrategies']]
        recovered.append({'firm_id': firm, 'names': sorted({n for m in obs for n in m['names']}),
                          'first_observed_activist_quarter': min(m['quarter'] for m in obs),
                          'last_observed_activist_quarter': max(m['quarter'] for m in obs),
                          'activist_candidate_accessions': concentration[firm]})
    new_candidates = [m for m in summary['manager_counts'] if m['activist_candidate_accessions'] and m['firm_id'] not in old_activists]
    validation = {'quarter_count': len(snapshots), 'reconciled_fund_observations': manifest['summary']['all_fund_observations'],
                  'zero_missing_or_duplicate_fund_ids_all_snapshots': True,
                  'missing_firm_id_issues': issues, 'candidate_source_paths_missing': missing_sources,
                  'candidate_source_hashes_reverified': False,
                  'ambiguous_accessions': ambiguous,
                  'historical_activist_ids_outside_latest': recovered,
                  'candidate_activist_ids_outside_previous_current_activist_set': new_candidates,
                  'checks': 'Unique accessions, initial/amendment totals, strictly prior/latest snapshot, all snapshot counts reconciled.'}
    freeze(OUT / 'validation.json', encode(validation))
    freeze(OUT / 'sec-screen/activist-initial-candidates.json', encode(activist_initials))
    table = '\n'.join(f'| {m["firm_id"]} | {"; ".join(m["names"])} | {m["first_observed_activist_quarter"]} | {m["last_observed_activist_quarter"]} | {m["activist_candidate_accessions"]} |' for m in recovered)
    text = f'''# Quarterly HFR continuation — 24 September 2026

Active project: `/Users/jefflu/Projects/activist-13d`.
This note continues [the earlier handoff](HFR-ACTIVIST-RESEARCH-HANDOFF-20260924.md).
The earlier statement that historical HFR snapshots were not supplied is now superseded.

## Completed

Imported the user-supplied `Downloads/HFR_QuarterEnd_Excel_2018Q1-2026Q3.zip`.
The original is preserved byte-for-byte under `data/raw/hfr/2026-09-24-quarterly/`.
SHA-256: `{manifest['archive_sha256']}`.
The 35 snapshots cover every quarter from 2018 Q1 through 2026 Q3, with
{manifest['summary']['all_fund_observations']:,} fund-row observations. All nested members
were read (ZIP CRC checked) and SHA-256 inventoried, including returns and assets.
Only Fund identity/classification fields were extracted; return/asset panels were not built.
Each extracted observation retains its source row; the per-snapshot metadata retains
workbook member, sheet, field-to-column mapping and source hash. Missing columns remain null.
Source date-added values remain raw Excel serial strings, not availability dates.

Across snapshots there are **393 Event-Driven Firm_IDs and 44 Activist Firm_IDs**.
The latest snapshot has 173 and 24 respectively. Thus 220 historical ED IDs and
20 historical Activist IDs are outside the corresponding latest sets. An ID absent
from the latest strategy subset is not necessarily a closed firm or absent from all HFR.
No deduplication of legal managers across different Firm_IDs has been established.

## Dating contract

These are within-quarter vendor deliveries, mostly mid-month, not literal quarter-end
observations. Preserve vendor DATESTAMP, supplied delivery-folder date, source file
mtime and local ingest date separately. Delivery-folder dates are **unverified historical
availability proxies**. Actual historical receipt/publication timestamps are unknown.
Example: 2018 Q1 has vendor DATESTAMP 15 March and delivery-folder date 16 March.
The supplied 2018 Q4 file mtime is 20 December while its folder date is 21 December.
Do not collapse either discrepancy. No snapshots before 2018 Q1 are supplied.

The exploratory SEC screen selects the latest whole snapshot whose delivery proxy
is strictly earlier than the filing date. Same-day delivery is excluded because no
time-of-day evidence exists. Names/classifications come only from that snapshot.
Managers absent there are not carried forward from earlier snapshots. The selection
prevents later-snapshot leakage conditional on the proxy; it does not certify point-in-time availability.

## Dated SEC name screen

| Measure | Count |
|---|---:|
| Local 13D / 13D-A metadata records | {summary['local_13d_records']:,} |
| Records with a strictly prior supplied delivery proxy | {summary['records_with_prior_snapshot_proxy']:,} |
| Records without a prior snapshot | {summary['no_strictly_prior_snapshot']:,} |
| ED candidate manager IDs | {summary['candidate_firm_ids']} |
| ED candidate accessions | {summary['candidate_accessions']:,} |
| ED initials / amendments | {summary['candidate_initials']} / {summary['candidate_amendments']:,} |
| Activist candidate manager IDs | {summary['activist_candidate_firm_ids']} |
| Activist candidate accessions | {summary['activist_candidate_accessions']:,} |
| Activist initials / amendments | {summary['activist_initials']} / {summary['activist_amendments']:,} |
| Accessions matching multiple manager IDs | {len(ambiguous)} |
| Candidate raw-source paths missing after historical-path resolution | {len(missing_sources)} |
| Verified cross-database identifier links | 0 |

ED candidates represent {summary['candidate_rate_among_records_with_prior_proxy']:.2%}
of the {summary['records_with_prior_snapshot_proxy']:,} records with prior snapshot proxies.
Counts are unique accessions, not campaigns. Name rules match normalized firm names,
then legal-suffix-reduced firm names, then normalized fund names; no fuzzy/substring matches.
Cross-manager ambiguity is retained. Initial and amendment records remain separate.
These counts are not directly comparable to the old 2,011/1,482 current-snapshot counts:
the eligible dates and classification rule differ. Raw-source existence was checked;
individual filing hashes were not reverified by this screen.

## Historical Activist IDs outside the latest Activist subset

First/last below mean observed in the supplied quarterly sample, not inception/exit.

| HFR ID | Source manager names | First observed | Last observed | Dated activist candidate filings |
|---|---|---|---|---:|
{table}

## Validation and files

The targeted offline tests cover share-class counts, missing IDs, duplicate IDs,
strict-prior/same-day selection, no carry-forward, ambiguous names and frozen-output refusal.
All 35 snapshot totals reconcile; zero missing/duplicate Fund_IDs were found.
Legacy XLS files emit xlrd's `SSCS size is 0 but SSAT size is non-zero` OLE warning.
They were readable without repair or source modification; the warning remains a source-format caveat.
The legacy reader is pinned in `requirements-hfr-quarterly.txt` (`xlrd==2.0.2`).

- [Historical coverage report](../runs/hfr-quarterly/20260924-v1/index.html)
- [Manager review and candidate counts](../runs/hfr-quarterly/20260924-v1/manager-review.html)
- [Source inventory](../runs/hfr-quarterly/20260924-v1/manifest.json)
- [Validation and missing-source/ambiguity lists](../runs/hfr-quarterly/20260924-v1/validation.json)
- [160 candidate activist initial filings](../runs/hfr-quarterly/20260924-v1/sec-screen/activist-initial-candidates.json)

Full run directory: `/Users/jefflu/Projects/activist-13d/research/runs/hfr-quarterly/20260924-v1/`.
Code: `scripts/data_collection/ingest_hfr_quarterly.py`, `screen_hfr_quarterly.py`,
`report_hfr_quarterly.py`. Use the project venv and environment settings in AGENTS.md.
Re-running refuses differing frozen outputs; behavior changes require a new run directory.

## Next work

1. Verify the 15 dated activist manager candidates using dated regulatory evidence,
   preserving adviser/fund/GP distinctions. Review the ten ambiguous accessions first.
2. Reconcile unavailable raw sources, manager aliases and amendment chains before
   constructing events. Review issuer/security types and manager concentration.
3. Confirm historical delivery availability where possible. Keep the 2013–2017
   coverage gap explicit or obtain earlier snapshots. Do not backfill 2018 classifications.
4. Freeze event eligibility, timing, re-entry and evaluation rules before a price study.

Human review answers, prior runs and current review packs remain preserved.
No paid models, semantic labels, returns backtest or external identity certification was added.
'''
    freeze(ROOT / 'research/docs/HFR-QUARTERLY-HANDOFF-20260924.md', text)
    e = html.escape
    rows = ''.join(f'<tr><td>{e("; ".join(m["names_across_snapshots"]))}</td><td>{e(m["firm_id"])}</td><td>{m["unique_candidate_accessions"]}</td><td>{m["activist_candidate_accessions"]}</td></tr>' for m in sorted(summary['manager_counts'], key=lambda m: (-m['activist_candidate_accessions'], -m['unique_candidate_accessions'])))
    report = f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>Dated HFR manager candidates</title><style>body{{font:17px/1.6 system-ui;max-width:1100px;margin:40px auto;padding:20px;color:#203448}}table{{border-collapse:collapse;width:100%}}td,th{{padding:9px;text-align:left;border-bottom:1px solid #ddd}}input{{font:inherit;padding:10px;width:80%}}</style><h1>Dated HFR manager candidates</h1><p>64 Event-Driven manager IDs with name candidates; 15 have candidate filings while classified Activist. 1,750 unique candidate filings, including 1,261 Activist-subset filings and 160 Activist-subset initial 13Ds.</p><p>Latest snapshot strictly before each filing, using an unverified delivery-date proxy. No verified cross-database identity links. Names below combine observed aliases for display; matching used only the selected snapshot's names.</p><p>{len(ambiguous)} accessions match multiple manager IDs. {len(missing_sources)} candidate raw paths are unavailable after path resolution. Per-manager counts can overlap; their sum is not a unique filing count.</p><p><a href="index.html">Quarterly coverage</a> · <a href="../../../docs/HFR-QUARTERLY-HANDOFF-20260924.md">Handoff and historical additions</a> · <a href="sec-screen/candidates.json">All candidate evidence</a> · <a href="sec-screen/activist-initial-candidates.json">Initial activist candidates</a> · <a href="validation.json">Ambiguities and missing files</a></p><input aria-label="Search managers" placeholder="Search manager or HFR ID" oninput="document.querySelectorAll('tbody tr').forEach(r=>r.hidden=!r.textContent.toLowerCase().includes(this.value.toLowerCase()))"><table><thead><tr><th>Observed manager names</th><th>HFR Firm_ID</th><th>ED candidate filings</th><th>Activist candidate filings</th></tr></thead><tbody>{rows}</tbody></table></html>'''
    freeze(OUT / 'manager-review.html', report)
    print(encode({'missing_sources': len(missing_sources), 'ambiguous_accessions': len(ambiguous),
                  'new_activist_candidate_managers': new_candidates,
                  'missing_firm_id_issues': issues}))


if __name__ == '__main__':
    build()
