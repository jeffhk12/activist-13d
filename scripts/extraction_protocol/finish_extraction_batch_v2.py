"""Publish checked batches while retaining malformed failed-draft history.

Inputs: completed batch report and records, independently checked archive receipt,
frozen reporting implementation. Outputs: case notes, dispatch/draft diagnostics,
local-link check and publication hashes. No labels changed. Tier:1.
v2 reports unparseable saved attempts, without repairing or comparing their
meaning; finalized-draft normalization and all extraction gates are unchanged.
Run project Python finish_extraction_batch_v2.py --batch 15.
"""
import argparse
import json
from html import escape
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

from extraction_batches import BASE, ROOT, core, frozen
from extraction_batches_v2 import report
from publish_extraction_batches import publish
from verify_extraction_batch import verify


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.links.extend(v for k, v in attrs if k == 'href')


def q(evidence):
    return ''.join('<blockquote>' + escape(item['quote']) + '<br><small>' + escape(item['document_id']) + f' [{item["start"]},{item["end"]})</small></blockquote>' for item in evidence)


def without_offsets(value):
    if isinstance(value, dict):
        return {k: without_offsets(v) for k, v in value.items() if k not in ['start', 'end', 'run_metadata']}
    return [without_offsets(v) for v in value] if isinstance(value, list) else value


def inspect_draft_history(job_dir):
    paths = sorted((job_dir / 'draft-history').glob('*.json'))
    normalized, unparseable = [], []
    for path in paths:
        raw = path.read_bytes()
        digest = core.sha(raw)
        if path.stem != digest:
            raise ValueError('Draft history hash mismatch: ' + str(path))
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as error:
            unparseable.append({'sha256': digest, 'parse_error': str(error),
                               'status': 'preserved_unparseable_attempt_not_semantically_compared'})
        else:
            normalized.append(without_offsets(value))
    equal = bool(normalized) and all(x == normalized[0] for x in normalized)
    return {'job_id': job_dir.name, 'saved_draft_versions': len(paths),
            'parseable_draft_versions': len(normalized),
            'unparseable_draft_versions': len(unparseable),
            'unparseable_drafts': unparseable,
            'all_parseable_versions_equal_ignoring_quote_offsets_and_overwritten_metadata': equal,
            'all_saved_versions_equal_ignoring_quote_offsets_and_overwritten_metadata':
                equal and not unparseable}


def finish(number):
    implementation = core.read(BASE / 'reporting-implementation.json')
    for name, expected in implementation['source_code_sha256'].items():
        if core.sha((ROOT / name).read_bytes()) != expected:
            raise ValueError('Reporting implementation changed')
    summary = report(number)
    archive = verify(number)
    if summary['exact_quote_entries'] != archive['independently_verified_exact_quote_entries']:
        raise ValueError('Independent quote counts differ')
    run = BASE / f'batch-{number:03}'
    blocks, draft_diagnostics, dispatch = [], [], []
    for item in core.read(run / 'inventory.json'):
        case = item['case_id'].lower()
        a, b, critic = [core.read(run / 'jobs' / (role + '_' + case) / 'record.json') for role in ['extractor', 'blind', 'critic']]
        reviews = {r['claim_id']: r for r in critic['reviews']}
        table = ''
        details = ''
        for category, first in a['intent'].items():
            second = b['intent'][category]
            review = reviews['intent.' + category]
            eligible = first['status'] == second['status'] and first['status'] != 'cannot_determine' and review['verdict'] == 'supported'
            table += f'<tr><td>{escape(category.replace("_", " "))}</td><td>{first["status"]}</td><td>{second["status"]}</td><td>{review["verdict"]}</td><td>{"Yes" if eligible else "Flagged"}</td></tr>'
            if first['status'] != 'not_stated' or second['status'] != 'not_stated' or not eligible:
                details += f'<details><summary>{escape(category.replace("_", " "))}</summary><p>Reader A: {escape(first["rationale"])}</p>{q(first["evidence"])}<p>Reader B: {escape(second["rationale"])}</p>{q(second["evidence"])}<p>Critic: {escape(review["rationale"])}</p>{q(review["evidence"])}</details>'
        funding = ''
        for label, row in [('A', a), ('B', b)]:
            components = ''.join('<li>' + escape(' · '.join([c['actor'] or 'Unresolved actor', c['type'], c['certainty'], c['acquisition_link']])) + ': ' + escape(c['description']) + q(c['evidence']) + '</li>' for c in row['funding']['components'])
            funding += f'<p><strong>Reader {label} funding:</strong> {escape(row["funding"]["status"])}. {escape(row["funding"]["summary"])}</p><ul>{components}</ul>'
        flags = [r for r in critic['reviews'] if r['verdict'] != 'supported']
        flags_html = ''.join(f'<li><strong>{escape(r["claim_id"])}: {r["verdict"]}</strong> — {escape(r["rationale"])}{q(r["evidence"])}</li>' for r in flags)
        links = ' · '.join(f'<a href="jobs/{role}_{case}/record.json">{label} complete record</a>' for role, label in [('extractor', 'Reader A'), ('blind', 'Reader B'), ('critic', 'Critic')])
        blocks.append(f'<section><h2>{escape(item["case_id"])} — {escape(a["issuer"]["name"] or "Unresolved issuer")}</h2><p>Accession {escape(item["accession"])} · accepted {escape(item["accepted_et"])}</p><table><tr><th>Objective</th><th>A</th><th>B</th><th>Critic</th><th>Experimental use</th></tr>{table}</table>{details}<h3>Qualified funding</h3>{funding}<h3>Critic flags</h3><ul>{flags_html or "<li>No non-supported claims in the preassigned candidate. This does not prove completeness or correctness.</li>"}</ul><p>{links}</p></section>')
        for role in ['extractor', 'blind', 'critic']:
            job_id = role + '_' + case
            draft_diagnostics.append(inspect_draft_history(run / 'jobs' / job_id))
            dispatch.append({'job_id': job_id, 'agent_task': f'/root/batch{number:03}_{role}{int(item["case_id"].split("_")[-1]):02}',
                             'fresh_context': True, 'fork_turns': 'none', 'model_override': None,
                             'result': 'finalized_original_answer'})
    body = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>13D batch evidence</title><style>body{font:17px/1.6 system-ui;color:#203448;background:#f4f6f8}main{max-width:1150px;margin:30px auto;padding:26px;background:white}section{border-top:2px solid #ccd5de;margin-top:28px;padding-top:15px}table{border-collapse:collapse;width:100%}td,th{padding:8px;border-bottom:1px solid #ccd5de;text-align:left}blockquote{background:#f2f5f8;padding:12px;font-size:15px;white-space:pre-wrap;overflow-wrap:anywhere}details{border:1px solid #ccd5de;margin:12px 0;padding:12px}summary{cursor:pointer;font-weight:600}a{color:#155c99}</style><main><h1>What this batch extracted</h1><p>28 October 2026 · Experimental model measurements</p><p>We are preparing filing information for a later comparison with financial-only stock ranking. These tables show both reader judgments, the critic verdict and every flagged objective. Present means a qualifying stated objective, not achievement or investment merit. Not stated concerns the reviewed source; cannot determine preserves missing material or a coding ambiguity.</p><p>Experimental use requires matching nonunknown reader states and critic support. Frequencies and flags remain in the JSON records. Funding relations retain actual, possible and historical qualifications. Ownership-derived features and transaction counts remain excluded. No investment model was fitted.</p><p><a href="index.html">Batch counts and methods</a> · <a href="../index.html">All batch progress</a></p>''' + ''.join(blocks) + '</main></html>'
    frozen(run / 'case-notes.html', body.encode(), raw=True)
    frozen(run / 'draft-repair-audit.json', draft_diagnostics)
    frozen(run / 'dispatch-history.json', dispatch)
    publish()
    checked = []
    for path in [BASE / 'index.html', run / 'index.html', run / 'case-notes.html']:
        parser = Links()
        parser.feed(path.read_text())
        for href in parser.links:
            parsed = urlsplit(href)
            if parsed.scheme or not parsed.path:
                continue
            target = (path.parent / unquote(parsed.path)).resolve()
            if not target.exists():
                raise ValueError('Broken published link: ' + href)
            checked.append({'page': str(path.relative_to(ROOT)), 'href': href})
    frozen(run / 'navigation-verification.json', {'checked_links': len(checked), 'broken_links': 0,
           'scope': 'Local target existence only, not browser rendering.', 'links': checked})
    files = ['scripts/extraction_protocol/finish_extraction_batch.py',
             'scripts/extraction_protocol/finish_extraction_batch_v2.py',
             'scripts/extraction_protocol/publish_extraction_batches.py',
             'scripts/extraction_protocol/verify_extraction_batch.py',
             'tests/test_extraction_publication_history.py']
    for name in files:
        frozen(run / 'code/publication' / name.split('/')[-1], (ROOT / name).read_bytes(), raw=True)
    frozen(run / 'publication.json', {'summary': summary, 'archive': archive, 'local_links_checked': len(checked),
            'source_code_sha256': {name: core.sha((ROOT/name).read_bytes()) for name in files},
            'outputs_sha256': {str(p.relative_to(run)): core.sha(p.read_bytes()) for p in run.iterdir() if p.is_file() and p.name != 'publication.json'},
            'all_saved_draft_versions_equal_except_mechanical_fields': all(d['all_saved_versions_equal_ignoring_quote_offsets_and_overwritten_metadata'] for d in draft_diagnostics),
            'all_parseable_draft_versions_equal_except_mechanical_fields': all(d['all_parseable_versions_equal_ignoring_quote_offsets_and_overwritten_metadata'] for d in draft_diagnostics),
            'unparseable_preserved_draft_attempts': sum(d['unparseable_draft_versions'] for d in draft_diagnostics),
            'draft_history_comparison_limit': 'Unparseable attempts are preserved and hash-checked; their meaning cannot be compared. Final records still pass original normalization replay.',
            'publication_implementation': 'finish_extraction_batch_v2',
            'status': 'batch_complete_experimental_measurements_not_accuracy_certified'})
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', type=int, required=True)
    print(core.enc(finish(parser.parse_args().batch)).decode())
