"""Prepare a source-only ten-case discovery pilot and ten reserved validations.

Inputs: frozen sampling protocol, source-only metadata/audit, protection manifest,
prior review filenames, original SEC evidence and saved Bloomberg caches.
Outputs: new review/drafts pack, immutable sample/source manifest, blank reading
forms, reserved evidence bytes and ten-event financial availability worksheet.
Identity: 10+10 cases, 5 early+5 recent per split, one case per connected
issuer/header-CIK component, no selected future-return values or model answers.
Tier: 1. Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python
 scripts/extraction_protocol/build_ranking_pilot.py [--verify]
"""

import argparse
import csv
import gzip
import hashlib
import io
import json
import re
import sys
from collections import Counter, defaultdict
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts/ml_experiment'))
from audit_ranking_scope import workbook_caches  # noqa: E402

from activist13d.local_paths import resolve_project_path  # noqa: E402

PROTOCOL = ROOT / 'research/protocol/ranking-llm-pilot-v1.json'
PACK = ROOT / 'review/drafts/ranking-llm-pilot-20261025'
RUN = ROOT / 'research/runs/ranking-llm-pilot/20261025-v2'
FEATURE = ROOT / 'research/runs/ml-feature-preview/20261012-v1'
STAGING = ROOT / 'research/runs/phase2-overnight/20260924-full-v1'
SOURCE_AUDIT = ROOT / 'research/runs/ranking-scope-audit/20261025-v2/filing-source-audit.json'
PROTECTION = ROOT / 'research/runs/phase1-baseline/20260924-development-v4/human-review-protection.json'
SCRIPT = ROOT / 'scripts/extraction_protocol/ranking_human_review.js'
WORKBOOK = Path('/Users/jefflu/Downloads/13D_Bloomberg_9_Field_Extraction.xlsx')
EXPOSURE_ROOTS = ['review', 'research/runs/phase2-identity-pilot',
                  'research/runs/chat-extraction-20260923-filing01',
                  'research/runs/investor-identity', 'research/runs/extraction-prep']
STYLE = '''body{font:17px/1.6 system-ui,sans-serif;color:#203448;background:#f4f6f8;margin:0}main{max-width:1050px;margin:25px auto;padding:25px;background:white}h1{font-size:30px;line-height:1.3}h2{font-size:23px;margin-top:30px}a{color:#155c99}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:15px/1.65 ui-monospace,monospace;background:#f1f4f7;padding:18px}details{border:1px solid #ccd5de;padding:14px;margin:15px 0}summary{cursor:pointer;font-weight:600}label{display:block;margin-top:18px}textarea{box-sizing:border-box;width:100%;min-height:110px;font:16px/1.5 system-ui;padding:10px}input[type=text],select{box-sizing:border-box;padding:10px;font:16px system-ui;max-width:100%}button,.button{display:inline-block;padding:11px 15px;margin:9px 9px 9px 0;font:16px system-ui;cursor:pointer}small{overflow-wrap:anywhere}.note{border-left:4px solid #c48721;padding-left:16px}#status{background:#edf3f7;padding:12px;min-height:25px}li{margin:9px 0}table{width:100%;border-collapse:collapse}td,th{padding:9px;text-align:left;vertical-align:top;border-bottom:1px solid #dce3e9}th{background:#edf3f7}.scroll{overflow:auto}'''


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n').encode()


def page(title, body):
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{escape(title)}</title><style>{STYLE}</style></head>'
            f'<body><main><h1>{escape(title)}</h1>{body}</main></body></html>').encode()


def components(rows):
    parents = {}

    def find(x):
        parents.setdefault(x, x)
        while parents[x] != x:
            parents[x] = parents[parents[x]]
            x = parents[x]
        return x

    for r in rows:
        tokens = ['issuer:' + r['issuer']] + ['reporter:' + c for c in r['reporter_ciks']]
        for t in tokens[1:]:
            a, b = find(tokens[0]), find(t)
            parents[max(a, b)] = min(a, b)
        find(tokens[0])
    return {r['accession']: find('issuer:' + r['issuer']) for r in rows}


def choose(rows, protocol, blocked_accessions, blocked_issuers):
    groups = components(rows)
    blocked_groups = {groups[r['accession']] for r in rows
                      if r['accession'] in blocked_accessions or r['issuer'] in blocked_issuers}
    eligible = [r for r in rows if groups[r['accession']] not in blocked_groups]
    used_groups = set()
    selected = defaultdict(list)
    trace = []
    profiles = {'item4_gap': lambda r: r['item4_spans'] == 0,
                'multiple_people': lambda r: r['reporting_person_count'] >= 2,
                'single_person': lambda r: r['reporting_person_count'] == 1,
                'multiple_documents': lambda r: r['canonical_documents'] >= 2,
                'any': lambda r: True}
    for slot in range(10):
        for role in ['discovery', 'validation_reserved']:
            era, profile = protocol['slots'][role][slot]
            years = Counter(r['entry_year'] for r in selected[role])
            industries = Counter(r['industry'] for r in selected[role])
            doc_types = {tuple(r['document_types']) for r in selected[role]}
            candidates = [r for r in eligible if r['era'] == era and profiles[profile](r)
                          and groups[r['accession']] not in used_groups
                          and years[r['entry_year']] < 2 and industries[r['industry']] < 2]
            if not candidates:
                raise ValueError(f'Unfillable {role} slot {slot+1}: {era}/{profile}; no silent relaxation')

            def score(r, industries=industries, years=years, doc_types=doc_types, role=role):
                return (r['industry'] in industries, r['entry_year'] in years,
                        tuple(r['document_types']) in doc_types,
                        sha(f'{protocol["seed"]}:{role}:{r["accession"]}'.encode()))

            picked = min(candidates, key=score)
            used_groups.add(groups[picked['accession']])
            selected[role].append({**picked, 'connected_group': groups[picked['accession']],
                                   'sampling_slot': slot+1, 'slot_profile': profile})
            trace.append({'role': role, 'slot': slot+1, 'era': era, 'profile': profile,
                          'eligible_for_slot': len(candidates), 'accession': picked['accession'],
                          'tie_break_hash': score(picked)[-1]})
    return dict(selected), trace, {'candidate_rows': len(rows), 'eligible_after_known_group_exclusions': len(eligible),
                                    'excluded_connected_groups': len(blocked_groups)}


def build():
    inputs = {}

    def read(path):
        path = Path(path)
        if path.name in {'targets.jsonl', 'outcomes.json', 'predictions.jsonl', 'evaluation.json', 'scored-events.csv'}:
            raise ValueError('Return or prediction input prohibited for pilot preparation')
        raw = path.read_bytes()
        key = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
        inputs[key] = {'sha256': sha(raw), 'bytes': len(raw)}
        return raw

    protocol_bytes = read(PROTOCOL)
    protocol = json.loads(protocol_bytes)
    protection = json.loads(read(PROTECTION))
    metadata = [json.loads(line) for line in read(FEATURE/'row-metadata.jsonl').decode().splitlines()]
    features = {r['row_id']: r['features'] for r in [json.loads(line) for line in read(FEATURE/'features.jsonl').decode().splitlines()]}
    source_audit = {r['row_id']: r for r in json.loads(read(SOURCE_AUDIT))}
    exposed = set()
    exposure_inventory = []
    for folder in EXPOSURE_ROOTS:
        for path in sorted((ROOT/folder).rglob('*')):
            if path.is_relative_to(PACK) or not path.is_file():
                continue
            ids = sorted(set(re.findall(r'\d{10}-\d{2}-\d{6}', str(path.relative_to(ROOT)))))
            if ids:
                exposed.update(ids)
                exposure_inventory.append({'path': str(path.relative_to(ROOT)), 'accessions_in_filename': ids})
    prior_files = encoded(exposure_inventory)
    protected_before = {}
    for name in protection['source_paths']:
        p = resolve_project_path(name, ROOT)
        protected_before[str(p.relative_to(ROOT))] = sha(p.read_bytes()) if p.is_file() else 'not_present_at_resolved_path'
    rows = []
    for m in metadata:
        s = source_audit[m['row_id']]
        if s['source_form'] != 'SC 13D':
            continue
        rows.append({'row_id': m['row_id'], 'accession': m['accession'], 'issuer': m['issuer'],
                     'reporter_ciks': sorted(m['header_reporter_ciks']), 'accepted_et': m['accepted_et'],
                     'entry_year': m['entry'][:4], 'era': 'early' if m['entry'][:4] <= '2020' else 'recent',
                     'industry': features[m['row_id']]['pre_disclosure_industry_sic2'],
                     'reporting_person_count': features[m['row_id']]['parsed_reporting_person_count'],
                     **{k: s[k] for k in ['source_path','source_url','source_sha256','item4_spans',
                                         'canonical_documents','canonical_text_chars','document_types',
                                         'documents_without_text','unresolved_references']}})
    selection, trace, counts = choose(rows, protocol, exposed | set(protection['accessions']), set(protection['issuers']))
    for role in selection:
        selection[role].sort(key=lambda r: (r['item4_spans'] == 0, r['documents_without_text'] > 0,
                                           r['canonical_documents'] > 1, r['canonical_text_chars'],
                                           sha((protocol['seed']+r['accession']).encode())))
        for i, r in enumerate(selection[role], 1):
            r['case_id'] = ('D' if role == 'discovery' else 'V') + f'{i:02}'
    all_cases = selection['discovery'] + selection['validation_reserved']
    assert len({r['issuer'] for r in all_cases}) == len({r['connected_group'] for r in all_cases}) == 20
    assert all(Counter(r['era'] for r in selection[role]) == {'early': 5, 'recent': 5} for role in selection)
    outputs = {}
    manifest = {'protocol': protocol['version'], 'protocol_sha256': sha(protocol_bytes),
                'stage': 'discovery_human_reading_pending_validation_reserved',
                'selection': selection, 'selection_trace': trace, 'counts': counts,
                'known_exposure_registry': 'prior-exposure-filenames.json',
                'exposure_limits': 'Filename/protection checks only; untracked reading, manager affiliation and pretrained-model knowledge unknown. Outcome history already exposed; no final investment holdout claimed.',
                'outcome_values_used': False, 'model_interpretations_created': 0}
    manifest_bytes = encoded(manifest)
    manifest_sha = sha(manifest_bytes)
    outputs[RUN/'sample-manifest.json'] = manifest_bytes
    outputs[RUN/'prior-exposure-filenames.json'] = prior_files
    outputs[RUN/'protected-assets-before.json'] = encoded(protected_before)
    script_bytes = read(SCRIPT)
    outputs[PACK/'assets/review.js'] = script_bytes
    links = []
    questions = [
        ('identities', '1. Who is reporting, and what roles or relationships does the filing establish?'),
        ('ownership', '2. What does each party report owning? Describe overlap or uncertainty without adding overlapping holdings.'),
        ('funding', '3. What source of funds does the investor disclose? Separate investor financing from proposed changes to company financing.'),
        ('objectives', '4. What current objectives or plans are actually stated? Distinguish specific proposals, generic reservations, and completed history.'),
        ('gaps', '5. What remains uncertain? Are relevant exhibits, references, or source passages missing or unreadable?'),
        ('candidate_fields', '6. Which facts or statements could become a consistently defined data field? Explain what the filing supports and where judgment would be needed.')]
    for role, cases in selection.items():
        for r in cases:
            a = r['accession']
            receipt = json.loads(read(STAGING/'receipts'/f'{a}.json'))
            bundle_raw = read(STAGING/'bundles'/f'{a}.json.gz')
            assert sha(bundle_raw) == receipt['bundle_sha256']
            raw = read(resolve_project_path(r['source_path'], ROOT))
            assert sha(raw) == r['source_sha256'] == receipt['source_sha256']
            if role == 'validation_reserved':
                # Copy verified evidence bytes without opening its substantive text.
                outputs[PACK/'validation-reserved/evidence'/f'{a}.json.gz'] = bundle_raw
                outputs[PACK/'validation-reserved/raw'/f'{a}.txt'] = raw
                continue
            bundle = json.loads(gzip.decompress(bundle_raw))
            documents = bundle['documents']
            config = {'protocol': protocol['version'], 'accession': a, 'source_sha256': r['source_sha256'],
                      'bundle_sha256': sha(bundle_raw), 'sample_manifest_sha256': manifest_sha}
            blank = {**config, 'record_type': 'ranking-human-reading-draft-v1', 'status': 'unreviewed',
                     'reviewer': '', 'independent_reading_completed': False, 'prior_model_answer_exposure': 'not_declared',
                     'answers': {key: '' for key, _ in questions}, 'evidence': [], 'reviewed_at_utc': None}
            outputs[PACK/'discovery/evidence'/f'{a}.json.gz'] = bundle_raw
            outputs[PACK/'discovery/evidence'/f'{a}.json'] = encoded(bundle)
            outputs[PACK/'discovery/raw'/f'{a}.txt'] = raw
            outputs[PACK/'discovery/blank-answers'/f'{a}.json'] = encoded(blank)
            doc_html = []
            first_text = True
            for d in documents:
                text = d.get('text')
                if text is not None:
                    assert sha(text.encode()) == d['text_sha256']
                primary = d.get('type') == 'SC 13D' and first_text
                if primary:
                    first_text = False
                text_html = (f'<pre data-document="{escape(d["document_id"], quote=True)}" data-sha="{escape(d.get("text_sha256") or "", quote=True)}">{escape(text)}</pre>'
                             if text is not None else '<p>Text unavailable for this attachment. Record material missing evidence; the original submission remains preserved.</p>')
                doc_html.append(f'<details class="source-document" {"open" if primary else ""}><summary>{escape(str(d["document_id"]))} — {escape(str(d.get("type")))} — {escape(str(d.get("filename")))}</summary><small>Canonical SHA-256: {escape(str(d.get("text_sha256")))}</small>{text_html}</details>')
            cfg = json.dumps(config, ensure_ascii=False).replace('<', '\\u003c').replace('&', '\\u0026')
            fields = ''.join(f'<label for="{key}">{escape(question)}</label><textarea id="{key}"></textarea>' for key, question in questions)
            body = f'''<p><a href="../index.html">Discovery guide and cases</a> · {r['case_id']} · Accession {a} · Filed {escape(bundle['filing_date'])}</p>
<p><strong>Independent human reading. Answers start blank.</strong> Read the original disclosure and relevant included exhibits. Record only what was available in this submission. Uncertainty is a useful answer.</p>
<p><a href="raw/{a}.txt">Preserved raw submission</a> · <a href="evidence/{a}.json">Canonical source bundle</a> · <a href="{escape(bundle['source_url'], quote=True)}" target="_blank" rel="noopener noreferrer">SEC submission</a></p>
<p class="note">The parser found {r['item4_spans']} candidate Item 4 span(s) and flagged {r['unresolved_references']} unresolved reference(s). These mechanical counts do not establish missing intent or determine whether a reference is material. Use the full source to decide.</p>
<h2>How to review this case</h2><ol><li>Read the SC 13D body and relevant exhibits. Search for Items 3, 4, and 5.</li><li>Select an exact supporting passage inside a source panel, then use Capture evidence.</li><li>Write your own observations below. Explain ambiguity instead of guessing.</li><li>Download your completed JSON. Bring it back here for source checks before a model interpretation.</li></ol>
<p>Start with one case. You can save a draft and return later. Browser storage is local to this browser and may not persist; a downloaded JSON is your durable copy.</p>
<h2>Source documents</h2><button id="expand">Expand all source documents</button>{''.join(doc_html)}
<h2>Your observations</h2><label for="reviewer">Reviewer name</label><input id="reviewer" type="text">{fields}
<h2>Supporting evidence</h2><p>Select source text first. Capture records the document, hash, exact quote and character offsets. You may inspect or correct the JSON array; its passages must match the source exactly.</p><button id="capture">Capture selected evidence</button><textarea id="evidence">[]</textarea>
<label for="prior_exposure">Have you previously seen model interpretations of this filing?</label><select id="prior_exposure"><option value="not_declared">Choose an exposure declaration</option><option value="none_known">No known prior model interpretation</option><option value="previously_seen">Yes — explain in the uncertainty observations</option><option value="uncertain">Unsure — explain in the uncertainty observations</option></select>
<label><input id="reviewed" type="checkbox"> I completed my own source reading before viewing a new model interpretation for this case.</label>
<button id="save">Save browser draft</button><button id="downloadDraft">Download draft JSON</button><button id="downloadCompleted">Download completed reading JSON</button><p id="status" role="status" aria-live="polite">No answers have been submitted.</p>
<script id="config" type="application/json">{cfg}</script><script src="../assets/review.js"></script>'''
            outputs[PACK/'discovery'/f'{a}.html'] = page(f'Discovery {r["case_id"]}: read the filing', body)
            links.append(f'<li><a href="discovery/{a}.html">{r["case_id"]} — {escape(bundle["filing_date"])} — read and record your observations</a></li>')
    outputs[PACK/'validation-reserved/index.html'] = page('Ten validation cases are reserved', '''<p><a href="../index.html">Discovery guide</a></p><p>The identities and evidence bytes are fixed in the research manifest. Source review pages have deliberately not been rendered.</p><p>First use the ten discovery cases to define the extraction rules. Once the schema and prompt are frozen, prepare separate independent human references for these reserved cases and assess prior exposure. Reservation is not a claim of an untouched investment test.</p><p>Substantive validation text has not been used to design the schema in this preparation step. These files are reserved by workflow convention, not protected by access control.</p>''')
    first = selection['discovery'][0]
    outputs[PACK/'index.html'] = page('13D filing pilot: start with one independent reading', f'''<p>October 25, 2026 · Discovery ready · Human answers pending · Ten validation cases reserved</p>
<p><strong>Can we measure useful information from an initial filing consistently?</strong> This stage creates observations to compare with model interpretations later. It does not predict returns or evaluate an investment edge.</p>
<p><a class="button" href="discovery/{first['accession']}.html">Start discovery case D01</a></p>
<h2>Why your reading comes first</h2><p>We need an independent reference. If you see a model answer first, it can influence what you notice. Read the source, record what it supports, and capture passages before comparing with a model. A statement such as “we may consider alternatives” need not mean a specific transaction is being sought. That is a general teaching example, not an interpretation of any selected filing.</p>
<h2>What to do</h2><ol><li>Begin with D01. Read the filing body and relevant exhibits; inspect Items 3, 4, and 5.</li><li>Capture supporting source passages and describe identities, ownership, funding, stated objectives, and uncertainty in your own words.</li><li>Download the completed reading JSON and bring it back to this project. You can stop after one case.</li><li>We will check source references and freeze your answer before generating a separate model interpretation. Your observations will help define a small schema: a consistent list of fields and allowed meanings.</li></ol>
<p class="note">Twenty cases were chosen from the existing covered panel using years, industries, document structure, reporting-party counts, evidence gaps and a fixed hash order. Future-return values, predictions and investor success did not select them. Each split has five 2018–2020 and five 2021–2023 cases. Known linked issuer/header-CIK groups are separated across all twenty; economic affiliation and unrecorded prior exposure remain uncertain.</p>
<h2>Ten discovery cases</h2><ol>{''.join(links)}</ol>
<h2>Validation later</h2><p><a href="validation-reserved/index.html">Ten separate cases are reserved</a>. Keep their substantive evidence out of discovery. Review them only after the schema/prompt is fixed and exposure suitability is checked.</p>
<h2>Saving your work</h2><p>The pages start blank and do not send answers anywhere. Save browser drafts for convenience; download JSON for durable work. If you are interrupted, download a draft. Existing review packs and answers remain preserved.</p>''')
    # Financial readiness is a separate review artifact, not part of the human text pack.
    wb_raw = read(WORKBOOK)
    wb = workbook_caches(WORKBOOK)
    rawcells = wb['BQL Raw Nine']['cells']
    headers = [rawcells.get(f'{chr(65+i)}1') for i in range(14)]
    raw_index = {v: int(c[1:]) for c, v in rawcells.items() if re.fullmatch(r'A[0-9]+', c) and isinstance(v, str) and '|' in v}
    bhe = '0000921895-19-000018|2019-01-08|2019-01-04'
    financial_ids = [bhe] + [r['row_id'] for r in selection['discovery'] if r['row_id'] != bhe][:9]
    assert len(set(financial_ids)) == 10
    available = {'event_rows': 10, 'field_checks': 90, 'status': 'pending_external_historical_validation',
                 'workbook_sha256': sha(wb_raw), 'debt_ratio_divisor_saved_assumption': wb['Extraction Controls']['cells'].get('B2'),
                 'known_conflict_control': bhe, 'release_dates_newly_verified': 0,
                 'event_ids': financial_ids}
    financial_rows = []
    for event_id in financial_ids:
        rowno = raw_index[event_id]
        for i in range(5,14):
            financial_rows.append({'row_id': event_id, 'workbook_sheet': 'BQL Raw Nine', 'source_cell': f'{chr(65+i)}{rowno}',
                                   'cutoff': rawcells.get(f'B{rowno}'), 'ticker_seed_unverified': rawcells.get(f'C{rowno}'),
                                   'reviewed_bbg_id_unverified': rawcells.get(f'D{rowno}'), 'candidate_fiscal_year': rawcells.get(f'E{rowno}'),
                                   'field_code': headers[i], 'cached_value': rawcells.get(f'{chr(65+i)}{rowno}'),
                                   'public_release_datetime': '', 'release_evidence_url_or_file': '',
                                   'historical_identity_evidence': '', 'returned_currency': '', 'unit_scale': '',
                                   'field_definition_evidence': '', 'revision_vintage_evidence': '',
                                   'review_status': 'unreviewed', 'reviewer': '', 'reviewed_at': '', 'notes': ''})
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(financial_rows[0]))
    writer.writeheader()
    writer.writerows(financial_rows)
    outputs[RUN/'financial-checks/field-review.csv'] = stream.getvalue().encode()
    outputs[RUN/'financial-checks/manifest.json'] = encoded(available)
    outputs[RUN/'financial-checks/index.html'] = page('Bounded financial-data check: ten events', '''<p>This is a separate financial-data readiness task. No workbook refresh, new collection, release-date verification, or model fit was performed.</p><p><a href="field-review.csv">Open the 90-row field review CSV</a>. Ten events are included: the documented BHE timing-conflict control and nine discovery events. Every field-level human validation column starts blank.</p><ol><li>Confirm the historical company/security mapping. Ticker agreement alone is insufficient.</li><li>Record evidence of when each financial item was publicly available relative to the specified cutoff. Fiscal period end is not publication time.</li><li>Verify field definition, currency, unit scale and revision vintage. In particular, the saved debt-ratio divisor of 100 is an assumption to validate.</li><li>Keep unknown items unreviewed or unresolved. Do not certify a row merely because all nine cached values are numeric.</li></ol><p>The BHE control is already documented as conflicting: its January 3, 2019 cutoff selects FY2018 figures announced February 7, 2019. This prior finding does not newly validate every field or replace the blank review checks. Only request the minimum terminal/filing evidence needed; no broad extraction is required by this worksheet.</p>''')
    protected_after = {name: sha((ROOT/name).read_bytes()) if (ROOT/name).is_file() else 'not_present_at_resolved_path'
                       for name in protected_before}
    assert protected_before == protected_after
    checks = {'discovery_cases': 10, 'reserved_validation_cases': 10, 'distinct_issuers': 20,
              'distinct_known_connected_groups': 20, 'shared_connected_groups': 0,
              'known_review_filename_accessions': len(exposed), 'source_files_and_bundles_verified': 20,
              'discovery_pages_rendered': 10, 'validation_pages_rendered': 0,
              'blank_discovery_answer_records': 10, 'human_answers_submitted': 0,
              'new_model_interpretations': 0, 'target_value_files_read': 0, 'financial_event_checks': 10,
              'protected_paths_inventoried': len(protected_before), 'protected_paths_unchanged': True,
              'limits': 'Workflow reservation and known grouping do not certify untouched evaluation or economic independence.'}
    for path in [Path(__file__), SCRIPT, ROOT/'scripts/ml_experiment/audit_ranking_scope.py']:
        raw = read(path)
        outputs[RUN/'code'/path.name] = raw
    outputs[RUN/'protocol.json'] = protocol_bytes
    outputs[RUN/'source-manifest.json'] = encoded(inputs)
    outputs[RUN/'checks.json'] = encoded(checks)
    outputs[RUN/'output-hashes.json'] = encoded({str(path.relative_to(ROOT)): sha(raw) for path, raw in outputs.items()})
    return outputs, selection, checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    outputs, selection, checks = build()
    for path, raw in outputs.items():
        if args.verify:
            if path.read_bytes() != raw:
                raise ValueError(f'Pilot replay differs: {path}')
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists() and path.read_bytes() != raw:
                raise ValueError(f'Refusing to overwrite changed pack or human work: {path}')
            path.write_bytes(raw)
    print(json.dumps({'pack': str(PACK/'index.html'), 'first_case': selection['discovery'][0]['accession'],
                      'checks': checks, 'exact_replay': args.verify}, indent=2))


if __name__ == '__main__':
    main()
