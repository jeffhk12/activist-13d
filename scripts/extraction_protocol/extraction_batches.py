"""Prepare and report resumable, source-only experimental extraction batches.

Inputs: frozen v3 rules, 667-row source metadata, protection/reservation identities,
local SEC bundles/receipts, and finalized built-in-agent records. Outputs: immutable
queue, five-case batch manifests, source hashes, all reader states and critic flags.
Identity: panel = excluded + queued; each completed filing has 2 readers + 1 critic;
objective eligibility = matching nonunknown states AND critic support (not truth).
Tier:1. Run project Python extraction_batches.py plan|prepare|status|report --batch 1.
No network, paid APIs, investment outcomes, Bloomberg collection or model fitting.
"""
import argparse
import gzip
import json
import re
from collections import Counter
from html import escape

import extraction_v3_io as core
from extraction_batch_io import BASE, use_batch
from extraction_v3_metrics import case_comparison

ROOT = core.ROOT
OLD = ROOT / 'research/runs/extraction-revision/20261027-v3'
STAGING = ROOT / 'research/runs/phase2-overnight/20260924-full-v1'
AUDIT = ROOT / 'research/runs/ranking-scope-audit/20261025-v2/filing-source-audit.json'
META = ROOT / 'research/runs/ml-feature-preview/20261012-v1/row-metadata.jsonl'
PROTECTION = ROOT / 'research/runs/phase1-baseline/20260924-development-v4/human-review-protection.json'
PILOT = ROOT / 'research/runs/ranking-llm-pilot/20261025-v2/sample-manifest.json'
PROTOCOL = ROOT / 'research/protocol/extraction-batches-v1.json'
SEED = '13d-extraction-batches-20261028-v1'
BATCH_SIZE = 5
CODE = ['extraction_batch_io.py', 'extraction_batches.py', 'extraction_v3_io.py',
        'extraction_v3_metrics.py', 'stability_io.py', 'stability_v2_io.py', 'audit_io.py']


def frozen(path, value, raw=False):
    payload = value if raw else core.enc(value)
    if path.exists() and path.read_bytes() != payload:
        raise ValueError('Immutable output differs: ' + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(payload)


def groups(rows):
    parents = {}

    def find(token):
        parents.setdefault(token, token)
        if parents[token] != token:
            parents[token] = find(parents[token])
        return parents[token]

    for row in rows:
        tokens = ['issuer:' + row['issuer']] + ['reporter:' + x for x in row['reporter_ciks']]
        for token in tokens:
            a, b = find(tokens[0]), find(token)
            parents[max(a, b)] = min(a, b)
    return {row['accession']: find('issuer:' + row['issuer']) for row in rows}


def make_queue(rows, protected, protected_issuers, reserved, completed):
    connected = groups(rows)
    protected_groups = {connected[r['accession']] for r in rows
                        if r['accession'] in protected or r['issuer'] in protected_issuers}
    reserved_groups = {connected[r['accession']] for r in rows if r['accession'] in reserved}
    queue, excluded = [], []
    for row in rows:
        accession = row['accession']
        group = connected[accession]
        if accession in completed:
            reason = 'already_completed_v3'
        elif group in protected_groups:
            reason = 'human_protected_connected_group'
        elif group in reserved_groups:
            reason = 'unreleased_reserved_connected_group'
        elif row['source_form'] != 'SC 13D':
            reason = 'not_initial_source_form'
        elif row['canonical_text_chars'] <= 0:
            reason = 'no_readable_source'
        else:
            reason = None
        item = {**row, 'connected_group': group}
        if reason:
            excluded.append({**item, 'reason': reason})
        else:
            queue.append({**item, 'workload': 'regular' if row['canonical_text_chars'] <= 100000 else 'long',
                          'order_sha256': core.sha((SEED + ':' + accession).encode())})
    queue.sort(key=lambda r: (r['workload'] == 'long', r['order_sha256']))
    for i, row in enumerate(queue, 1):
        row['queue_position'] = i
        row['batch_number'] = (i - 1) // BATCH_SIZE + 1
    return {'panel_filings': len(rows), 'queued_filings': len(queue), 'excluded_filings': len(excluded),
            'exclusion_counts': dict(Counter(r['reason'] for r in excluded)),
            'workload_counts': dict(Counter(r['workload'] for r in queue)),
            'queue': queue, 'excluded': excluded, 'reserved_accessions': sorted(reserved),
            'limits': 'Production queue, not an independent accuracy sample. Known CIK links do not certify economic independence.'}


def policy():
    return {'version': 'extraction-batches-v1', 'created_on': '2026-10-28',
            'authority': 'User said okay lets work in batches now after the completed four-step automated agent experiment.',
            'question': 'Can initial-13D objective and qualified-funding measurements later improve ranking beyond financial inputs?',
            'scope': 'Process eligible local initial filings from the existing 667-event panel in resumable batches of five. Complete batch 1 first; record each later batch separately. Preserve human-protected and seven unreleased reserved cases and known connected groups.',
            'semantics': 'Unchanged extraction-v3 common rules, categories, schema and three roles. No new objective definitions. Full raw records retained; ownership-derived features and transaction counts excluded from first model.',
            'agents': 'One fresh role/one filing context; two source-only readers plus critic of always-preassigned extractor claims, never best-of-two. Built-in subscription agents, same inherited model, exact settings unavailable. Shared-filesystem procedural blinding only.',
            'queue': 'Source metadata only; exclude completed13 exact accessions, protected and reserved connected groups, noninitial or unreadable sources. SHA256(seed:accession) within workload tiers <=100000 canonical chars first, longer filings later without truncation. Queue frozen before source release; no outcome or inferred objective selection.',
            'seed': SEED, 'batch_size': BATCH_SIZE,
            'eligibility': 'Matching nonunknown objective readings plus critic support. Save both states and count/2 frequencies, unknown/disagreement/critic flags; never silently zero. Qualified funding tuples compared descriptively with all component qualifiers retained; no certified feature mapping yet.',
            'gates': 'Each next batch requires preceding batch complete, full readable review/delivery, exact schema/quotes/source hashes, every candidate claim reviewed once and preserved inputs intact. No intent-agreement threshold or forced reconciliation. Technical failure blocks next release; semantic changes require new protocol/run.',
            'interpretation': 'All natural data remain experimental. Earlier human-reference accuracy gates unmet. Agreement and same-model critic approval are not precision, recall or accuracy. Workload-first batches are not representative.',
            'prohibitions': 'No paid APIs, internet filing retrieval, future amendments, outcomes, Bloomberg collection, fitting or overwriting prior records. User-approved automation does not alter blank human references.',
            'feature_use_policy_sha256': core.sha((OLD / 'feature-use-policy.json').read_bytes()),
            'common_rules_sha256': core.sha((OLD / 'inputs/common-rules.md').read_bytes())}


def plan():
    if (BASE / 'queue.json').exists():
        return core.read(BASE / 'queue.json')
    frozen(PROTOCOL, policy())
    meta = [json.loads(line) for line in META.read_text().splitlines()]
    metadata = {r['row_id']: r for r in meta}
    fields = ['row_id', 'accession', 'issuer', 'accepted_et', 'source_form', 'source_path',
              'source_sha256', 'source_url', 'canonical_documents', 'canonical_text_chars',
              'documents_without_text', 'unresolved_references', 'item4_spans']
    rows = [{**{k: r[k] for k in fields}, 'reporter_ciks': sorted(metadata[r['row_id']]['header_reporter_ciks'])}
            for r in core.read(AUDIT)]
    if len(rows) != 667 or len({r['accession'] for r in rows}) != len(rows):
        raise ValueError('Expected unique 667-filing panel')
    protection = core.read(PROTECTION)
    extra_files = [p for folder in ['review/current', 'review/drafts/human-first-52', 'research/runs/extraction-prep']
                   for p in (ROOT / folder).rglob('*') if p.is_file()]
    protected = set(protection['accessions'])
    for name in [*protection['source_paths'], *map(str, extra_files)]:
        protected.update(re.findall(r'\d{10}-\d{2}-\d{6}', name))
    released = {r['accession'] for r in core.read(OLD / 'selection.json')['selected']}
    reserved = {r['accession'] for r in core.read(PILOT)['selection']['validation_reserved']} - released
    completed = {r['accession'] for r in core.read(OLD / 'inventory.json')}
    if len(reserved) != 7 or len(completed) != 13:
        raise ValueError('Reservation/completion inventory changed')
    queue = make_queue(rows, protected, set(protection['issuers']), reserved, completed)
    frozen(BASE / 'protocol.json', PROTOCOL.read_bytes(), raw=True)
    frozen(BASE / 'queue.json', queue)
    preserved = core.read(OLD / 'preservation-before.json')
    for p in [*OLD.rglob('*'), *extra_files]:
        if p.is_file():
            preserved[str(p.relative_to(ROOT))] = core.sha(p.read_bytes())
    frozen(BASE / 'preservation-before.json', preserved)
    frozen(BASE / 'plan-inputs.json', {str(p.relative_to(ROOT)): core.sha(p.read_bytes())
           for p in [AUDIT, META, PROTECTION, PILOT, PROTOCOL, OLD / 'feature-use-policy.json']})
    return queue


def prepare(number):
    queue = core.read(BASE / 'queue.json')
    run = BASE / f'batch-{number:03}'
    if (run / 'preparation.json').exists():
        return status(number)
    if number > 1:
        report(number - 1)
    selected = [r for r in queue['queue'] if r['batch_number'] == number]
    if not selected:
        raise ValueError('No queued cases for batch')
    inputs = run / 'inputs'
    inputs.mkdir(parents=True, exist_ok=True)
    for name in ['common-rules.md', 'schema.json', 'categories.json', 'role-extractor.txt', 'role-blind.txt', 'role-critic.txt']:
        frozen(inputs / name, (OLD / 'inputs' / name).read_bytes(), raw=True)
    frozen(inputs / 'protocol.json', (BASE / 'protocol.json').read_bytes(), raw=True)
    jobs, inventory = [], []
    for i, row in enumerate(selected, 1):
        accession = row['accession']
        receipt = core.read(STAGING / 'receipts' / f'{accession}.json')
        raw = (STAGING / 'bundles' / f'{accession}.json.gz').read_bytes()
        if core.sha(raw) != receipt['bundle_sha256'] or core.sha((ROOT / row['source_path']).read_bytes()) != row['source_sha256'] or receipt['source_sha256'] != row['source_sha256']:
            raise ValueError('Frozen source/receipt mismatch')
        bundle = json.loads(gzip.decompress(raw))
        if bundle['accession'] != accession or bundle['source_sha256'] != row['source_sha256']:
            raise ValueError('Wrong source identity')
        for doc in bundle['documents']:
            if isinstance(doc.get('text'), str) and core.sha(doc['text'].encode()) != doc['text_sha256']:
                raise ValueError('Canonical text hash mismatch')
        case = f'B{number:03}_{i:02}'
        name = f'inputs/cases/{case}/bundle.json.gz'
        frozen(run / name, raw, raw=True)
        inventory.append({**row, 'case_id': case, 'bundle': name, 'bundle_sha256': core.sha(raw),
                          'readable_characters': sum(len(d.get('text') or '') for d in bundle['documents'])})
        for role in ['extractor', 'blind', 'critic']:
            job = f'{role}_{case.lower()}'
            jobs.append({'job_id': job, 'role': role, 'phase': 'batch', 'case_id': case,
                         'accession': accession, 'bundle': name,
                         'candidate_source_job': f'extractor_{case.lower()}' if role == 'critic' else None})
            for sub in ['drafts', 'draft-history', 'delivery']:
                (run / 'jobs' / job / sub).mkdir(parents=True, exist_ok=True)
    (run / 'candidates').mkdir(exist_ok=True)
    frozen(run / 'jobs.json', jobs)
    frozen(run / 'inventory.json', inventory)
    code_hashes = {}
    for name in CODE:
        p = ROOT / 'scripts/extraction_protocol' / name
        code_hashes[str(p.relative_to(ROOT))] = core.sha(p.read_bytes())
        frozen(run / 'code' / name, p.read_bytes(), raw=True)
    frozen(run / 'preparation.json', {'jobs': len(jobs), 'batch_number': number,
           'source_code_sha256': code_hashes,
           'input_sha256': {str(p.relative_to(run)): core.sha(p.read_bytes()) for p in [run / 'jobs.json', run / 'inventory.json', *inputs.rglob('*')] if p.is_file()},
           'queue_sha256': core.sha((BASE / 'queue.json').read_bytes()),
           'protocol_sha256': core.sha((BASE / 'protocol.json').read_bytes()),
           'status': 'experimental_production_sources_released_no_accuracy_claim'})
    return status(number)


def status(number):
    run = BASE / f'batch-{number:03}'
    jobs = core.read(run / 'jobs.json')
    done = [j['job_id'] for j in jobs if (run / 'jobs' / j['job_id'] / 'record.json').exists()]
    return {'batch': number, 'complete_jobs': len(done), 'total_jobs': len(jobs),
            'complete': done, 'pending': [j['job_id'] for j in jobs if j['job_id'] not in done]}


def report(number):
    run = use_batch(number)
    preparation = core.read(run / 'preparation.json')
    for name, expected in preparation['input_sha256'].items():
        if core.sha((run / name).read_bytes()) != expected:
            raise ValueError('Changed input: ' + name)
    if core.sha((BASE / 'queue.json').read_bytes()) != preparation['queue_sha256'] or core.sha((BASE / 'protocol.json').read_bytes()) != preparation['protocol_sha256']:
        raise ValueError('Queue/protocol changed')
    preserved = core.read(BASE / 'preservation-before.json')
    for name, expected in preserved.items():
        if core.sha((ROOT / name).read_bytes()) != expected:
            raise ValueError('Preserved asset changed: ' + name)
    records, record_hashes = {}, {}
    quote_count = 0

    def quotes(value):
        if isinstance(value, dict):
            return int('quote' in value) + sum(quotes(v) for v in value.values())
        return sum(quotes(v) for v in value) if isinstance(value, list) else 0

    for job in core.read(run / 'jobs.json'):
        path = run / 'jobs' / job['job_id'] / 'record.json'
        row = core.read(path)
        _, bundle, candidate = core.load_job(job['job_id'])
        covered = core.delivery(job, bundle)
        readable = {d['document_id'] for d in bundle['documents'] if d.get('text')}
        if not covered['all_readable_text_delivered'] or row.get('extraction_status', row.get('review_status')) != 'complete_readable_bundle' or set(row['reviewed_document_ids']) != readable:
            raise ValueError('Incomplete source delivery/review: ' + job['job_id'])
        raw = core.read(run / 'jobs' / job['job_id'] / 'draft-history' / (row['run_metadata']['raw_draft_sha256'] + '.json'))
        normalized = core.normalize(raw, job, bundle, candidate, covered)
        if normalized != {k: v for k, v in row.items() if k != 'run_metadata'}:
            raise ValueError('Record normalization replay differs')
        records[job['job_id']] = row
        record_hashes[str(path.relative_to(run))] = core.sha(path.read_bytes())
        quote_count += quotes(row)
    comparisons, flags = [], []
    for item in core.read(run / 'inventory.json'):
        cid = item['case_id'].lower()
        a, b, critic = [records[r + '_' + cid] for r in ['extractor', 'blind', 'critic']]
        comparison = case_comparison(a, b, critic)
        comparisons.append({**comparison, 'case_id': item['case_id'], 'issuer': a['issuer']['name']})
        flags.extend({'case_id': item['case_id'], **r} for r in critic['reviews'] if r['verdict'] != 'supported')
    result = {'batch': number, 'filings': len(comparisons), 'jobs': len(records),
              'intent_cells': sum(c['intent_cells'] for c in comparisons),
              'intent_agreement': sum(c['intent_agreement'] for c in comparisons),
              'eligible_experimental_intents': sum(c['eligible_experimental_intents'] for c in comparisons),
              'critic_claims': sum(c['critic_claims'] for c in comparisons),
              'critic_verdicts': dict(sum((Counter(c['critic_verdicts']) for c in comparisons), Counter())),
              'exact_quote_entries': quote_count, 'preserved_files': len(preserved),
              'natural_accuracy': 'not_estimated', 'all_fields_experimental': True,
              'ownership_features_and_transaction_counts_excluded': True,
              'all_readable_delivery_schema_quotes_and_normalization_replay': 'passed'}
    frozen(run / 'summary.json', result)
    frozen(run / 'case-comparisons.json', comparisons)
    frozen(run / 'critic-flags.json', flags)
    frozen(run / 'verification.json', {'record_sha256': record_hashes, 'preserved_files': len(preserved), 'source_and_records': 'passed'})
    rows = ''.join(f'<tr><td>{escape(c["case_id"])}</td><td>{escape(c["issuer"] or "Unknown")}</td><td>{c["intent_agreement"]}/9</td><td>{c["eligible_experimental_intents"]}/9</td><td>{c["critic_verdicts"].get("supported", 0)}/{c["critic_claims"]}</td></tr>' for c in comparisons)
    body = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>13D extraction batch {number}</title><style>body{{font:17px/1.6 system-ui;color:#203448;background:#f4f6f8}}main{{max-width:1050px;margin:30px auto;background:white;padding:28px}}table{{border-collapse:collapse;width:100%}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #ccd5de}}a{{color:#155c99}}pre{{white-space:pre-wrap}}</style><main><h1>13D extraction: batch {number}</h1><p>28 October 2026 · Experimental data preparation</p><p>We are preparing to test whether stated intentions improve stock ranking beyond financial data. This batch adds {len(comparisons)} filings using the same frozen rules. No investment model was fitted and no accuracy or investment edge is established.</p><p>The two readers agree on {result['intent_agreement']}/{result['intent_cells']} objective states. {result['eligible_experimental_intents']}/{result['intent_cells']} match on a nonunknown state and receive critic support. This is an experimental-use rule, not measured correctness.</p><table><tr><th>Case</th><th>Issuer</th><th>Reader agreement</th><th>Experimental-use cells</th><th>Critic supported claims</th></tr>{rows}</table><h2>What the workflow does</h2><p>Two fresh agents independently read each complete readable filing. A third works backward from the preassigned extractor's claims to the original source. For example, routine merger succession stays a contract fact rather than automatically becoming a board objective. Matching answers may share errors.</p><p>Unknowns, disagreements and critic objections remain in the records and are not changed to negative labels. Qualified funding retains actual, possible and historical links; its tuple comparison remains descriptive. Raw ownership-derived features and transaction counts stay out of the first model. Seven reserved sources and human reference assets remain closed and unchanged. Workload-first queue order makes this batch unrepresentative.</p><p>Every job passed source delivery, exact quotes, schema and normalization replay. Missing exhibits still limit substantive completeness. The next batch can resume from the frozen queue without repeating these records.</p><p><a href="case-comparisons.json">All reader states and funding/ownership tuple differences</a> · <a href="critic-flags.json">Every critic flag</a> · <a href="summary.json">Counts</a> · <a href="verification.json">Integrity receipt</a> · <a href="inventory.json">Source inventory</a> · <a href="../queue.json">Full queue and exclusions</a> · <a href="../../../extraction-revision/20261027-v3/readiness.html">Prior readiness report</a></p></main></html>'''
    frozen(run / 'index.html', body.encode(), raw=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['plan', 'prepare', 'status', 'report'])
    parser.add_argument('--batch', type=int, default=1)
    args = parser.parse_args()
    if args.action == 'plan':
        result = plan()
        result = {k: v for k, v in result.items() if k not in ['queue', 'excluded']}
    else:
        result = {'prepare': prepare, 'status': status, 'report': report}[args.action](args.batch)
    print(json.dumps(result, indent=2))
