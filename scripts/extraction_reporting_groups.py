"""Group frozen extraction checkpoints into larger user reporting batches.

Inputs: unchanged 627-filing queue, completed checkpoints1-6, existing job outputs.
Outputs: immutable 25-filing reporting plan, resumable next-checkpoint commands,
combined reports and current HTML. Identity: 597 remaining=23*25+22;75 jobs per
full reporting batch; original five-filing source-release gates remain in force.
Tier:1. Run project Python scripts/extraction_reporting_groups.py plan|status|
prepare-next|report|publish --batch 7. No model calls, outcomes or new sources.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'extraction_protocol'))
from extraction_batches import BASE, ROOT, core, frozen, status  # noqa: E402
from extraction_batches_v2 import prepare, report  # noqa: E402
from verify_extraction_batch import verify  # noqa: E402

GROUPS = BASE / 'reporting-25-v1'
POLICY = ROOT / 'research/protocol/extraction-reporting-groups-v1.json'


def build_groups(rows, completed_checkpoint=6, size=25):
    if size <= 5 or size % 5:
        raise ValueError('Larger reporting size must be a multiple of five')
    rows = sorted(rows, key=lambda r: r['queue_position'])
    if len({r['accession'] for r in rows}) != len(rows) or len({r['queue_position'] for r in rows}) != len(rows):
        raise ValueError('Duplicate source or queue position')
    if [r['queue_position'] for r in rows] != list(range(1, len(rows) + 1)):
        raise ValueError('Frozen queue must retain contiguous source order')
    remaining = [r for r in rows if r['batch_number'] > completed_checkpoint]
    result = []
    for offset in range(0, len(remaining), size):
        selected = remaining[offset:offset + size]
        checkpoints = sorted({r['batch_number'] for r in selected})
        if any([r['accession'] for r in rows if r['batch_number'] == n] != [r['accession'] for r in selected if r['batch_number'] == n] for n in checkpoints):
            raise ValueError('Reporting boundary splits an existing checkpoint')
        number = completed_checkpoint + offset // size + 1
        result.append({'reporting_batch': number, 'filings': len(selected), 'jobs': 3 * len(selected),
                       'checkpoint_batches': checkpoints, 'queue_positions': [r['queue_position'] for r in selected],
                       'checkpoint_filing_counts': {str(n): sum(r['batch_number'] == n for r in selected) for n in checkpoints},
                       'accessions': [r['accession'] for r in selected]})
    return result


def aggregate_summaries(rows):
    fields = ['filings', 'jobs', 'intent_cells', 'intent_agreement', 'eligible_experimental_intents', 'critic_claims', 'exact_quote_entries']
    return {**{key: sum(r[key] for r in rows) for key in fields},
            'critic_verdicts': dict(sum((Counter(r['critic_verdicts']) for r in rows), Counter())),
            'natural_accuracy': 'not_estimated', 'all_fields_experimental': True}


def plan():
    if (GROUPS / 'plan.json').exists():
        return core.read(GROUPS / 'plan.json')
    for number in range(1, 7):
        if not (BASE / f'batch-{number:03}/publication.json').exists():
            raise ValueError('First six checkpoints must be completed')
    if any((BASE / 'batch-007/jobs').glob('*/record.json')):
        raise ValueError('Declare larger grouping before checkpoint7 interpretations')
    queue = core.read(BASE / 'queue.json')
    groups = build_groups(queue['queue'])
    if sum(g['filings'] for g in groups) != 597:
        raise ValueError('Expected597 remaining filings')
    policy = {'version': 'extraction-reporting-groups-v1', 'created_on': '2026-10-28',
              'authority': 'User asked can we have bigger batches; use25 as the default larger reporting size.',
              'reporting_size': 25, 'internal_checkpoint_size': 5, 'roles_per_filing': 3,
              'first_reporting_batch': 7, 'first_checkpoint_batches': [7, 8, 9, 10, 11],
              'execution': 'On next continuation, complete all five internal checkpoints before ending the reporting batch. Continue through passing technical gates without asking the user to approve every five filings. Save progress at every checkpoint.',
              'release_gate': 'Keep original sequential source-release/integrity gates. Technical failure blocks the next checkpoint. Unknowns/disagreements remain flags, not a reason for forced reconciliation.',
              'semantics': 'No changes to v3 shared rules, schema, roles, candidate selection, feature-use exclusions, source order or reservation/protection policy.',
              'limits': 'Three reviews per filing and the existing three-worker concurrency are retained. Grouping reduces user check-ins; it does not inherently reduce per-filing model work or make judgments accurate.',
              'original_queue_sha256': core.sha((BASE / 'queue.json').read_bytes()),
              'original_protocol_sha256': core.sha((BASE / 'protocol.json').read_bytes())}
    frozen(POLICY, policy)
    frozen(GROUPS / 'policy.json', policy)
    preserved = {str(p.relative_to(ROOT)): core.sha(p.read_bytes())
                 for number in range(1, 8) for p in (BASE / f'batch-{number:03}').rglob('*') if p.is_file()}
    frozen(GROUPS / 'preservation-before.json', preserved)
    result = {'remaining_filings_at_switch': 597, 'prior_completed_filings': 43,
              'reporting_batches': groups, 'policy_sha256': core.sha(POLICY.read_bytes())}
    frozen(GROUPS / 'plan.json', result)
    frozen(GROUPS / 'code/extraction_reporting_groups.py', Path(__file__).read_bytes(), raw=True)
    return result


def load_group(number):
    policy = core.read(GROUPS / 'policy.json')
    manifest = core.read(GROUPS / 'plan.json')
    if core.sha(POLICY.read_bytes()) != manifest['policy_sha256'] or POLICY.read_bytes() != (GROUPS / 'policy.json').read_bytes():
        raise ValueError('Frozen grouping policy changed')
    if core.sha((BASE / 'queue.json').read_bytes()) != policy['original_queue_sha256'] or core.sha((BASE / 'protocol.json').read_bytes()) != policy['original_protocol_sha256']:
        raise ValueError('Original frozen queue/protocol changed')
    groups = manifest['reporting_batches']
    return next(g for g in groups if g['reporting_batch'] == number)


def group_status(number):
    group = load_group(number)
    rows = []
    for checkpoint in group['checkpoint_batches']:
        run = BASE / f'batch-{checkpoint:03}'
        item = status(checkpoint) if (run / 'jobs.json').exists() else {'batch': checkpoint, 'complete_jobs': 0, 'total_jobs': 3 * group['checkpoint_filing_counts'][str(checkpoint)]}
        item['published'] = (run / 'publication.json').exists()
        item['filings'] = core.read(run / 'summary.json')['filings'] if item['published'] else 0
        rows.append(item)
    return {**group, 'completed_filings': sum(r['filings'] for r in rows),
            'completed_jobs': sum(r['complete_jobs'] for r in rows), 'checkpoints': rows,
            'next_checkpoint': next((r['batch'] for r in rows if not r['published']), None),
            'complete': all(r['published'] for r in rows)}


def prepare_next(number):
    if number > 7 and not group_status(number - 1)['complete']:
        raise ValueError('Previous larger reporting batch incomplete')
    view = group_status(number)
    checkpoint = view['next_checkpoint']
    if checkpoint is None:
        return view
    for previous in view['checkpoint_batches']:
        if previous >= checkpoint:
            break
        report(previous)
        verify(previous)
    return {'reporting_batch': number, 'next_checkpoint': checkpoint,
            'checkpoint_status': prepare(checkpoint),
            'continuation': 'Use fresh role/filing agents with extraction_batch_io.py --batch CHECKPOINT. Finish via finish_extraction_batch.py, then prepare-next again. Report to user after the full larger batch.'}


def report_group(number):
    view = group_status(number)
    if not view['complete']:
        raise ValueError('All internal checkpoints must be published before larger-batch completion')
    rows = []
    comparisons, flags = [], []
    for checkpoint in view['checkpoint_batches']:
        rows.append(report(checkpoint))
        verify(checkpoint)
        run = BASE / f'batch-{checkpoint:03}'
        comparisons.extend(core.read(run / 'case-comparisons.json'))
        flags.extend(core.read(run / 'critic-flags.json'))
    result = {**aggregate_summaries(rows), 'reporting_batch': number,
              'checkpoint_batches': view['checkpoint_batches']}
    target = GROUPS / f'batch-{number:03}'
    frozen(target / 'summary.json', result)
    frozen(target / 'case-comparisons.json', comparisons)
    frozen(target / 'critic-flags.json', flags)
    return result


def publish_groups():
    if not (GROUPS / 'plan.json').exists():
        return None
    groups = core.read(GROUPS / 'plan.json')['reporting_batches']
    views = [group_status(g['reporting_batch']) for g in groups]
    next_group = next((v for v in views if not v['complete']), None)
    rows = ''.join(f'<tr><td>{v["reporting_batch"]}</td><td>{v["filings"]}</td><td>{v["completed_filings"]}/{v["filings"]}</td><td>{v["completed_jobs"]}/{v["jobs"]}</td><td>{", ".join(map(str, v["checkpoint_batches"]))}</td></tr>' for v in views)
    page = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>13D larger extraction batches</title><style>body{{font:17px/1.65 system-ui;color:#203448;background:#f4f6f8}}main{{max-width:1050px;margin:30px auto;background:white;padding:28px}}table{{border-collapse:collapse;width:100%}}td,th{{padding:9px;border-bottom:1px solid #ccd5de;text-align:left}}a{{color:#155c99}}</style><main><h1>13D extraction:25 filings per reporting batch</h1><p>28 October 2026 · Experimental data preparation</p><p>We are preparing to test whether stated intentions improve stock ranking beyond financial inputs. At your request, reporting batches now cover25 filings,75 agent jobs and225 objective decisions. Two readers and one backward critic still process every filing independently by role. Agreement and critic approval remain model judgments, not measured accuracy.</p><p>Each larger reporting batch contains five saved checkpoints of five filings. Once a continuation starts, work advances through passing checkpoints until all25 filings are done, without a new user prompt after each five. Interrupted work resumes from the saved records. Existing source-release gates, raw answers and reserved cases remain intact. The final reporting batch contains22 filings.</p><p>43 filings were complete when this grouping was declared;597 eligible filings remained. The next larger reporting batch is <strong>{next_group['reporting_batch'] if next_group else 'none remaining'}</strong>. Its completed count is <strong>{str(next_group['completed_filings'])+'/'+str(next_group['filings']) if next_group else 'all complete'}</strong>. A prepared checkpoint does not mean its agents are running.</p><p>Grouped reporting reduces check-in frequency. It does not by itself reduce tokens per filing, shorten the required source review or increase the three-worker concurrency. Ownership-derived features and transaction counts remain excluded; qualified funding and objective states stay experimental. No new investment model, paid API or online filing retrieval is part of this change.</p><table><tr><th>Reporting batch</th><th>Planned filings</th><th>Completed filings</th><th>Finalized jobs</th><th>Internal checkpoints</th></tr>{rows}</table><p><a href="plan.json">Frozen grouping and source identities</a> · <a href="policy.json">Versioned grouping policy</a> · <a href="../index.html">All historical checkpoints and results</a></p><p>Resume: use project Python <code>scripts/extraction_reporting_groups.py prepare-next --batch 7</code>. Workers continue using their assigned internal checkpoint number. Complete the checkpoint with <code>finish_extraction_batch.py</code>, advance automatically, and publish the combined report with <code>extraction_reporting_groups.py report --batch 7</code>.</p></main></html>'''
    (GROUPS / 'index.html').write_text(page)
    payload = {'reporting_size': 25, 'next_reporting_batch': next_group, 'groups': views}
    (GROUPS / 'progress.json').write_bytes(core.enc(payload))
    return next_group


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['plan', 'status', 'prepare-next', 'report', 'publish'])
    parser.add_argument('--batch', type=int, default=7)
    args = parser.parse_args()
    if args.action == 'plan':
        data = plan()
        result = {'reporting_size': 25, 'remaining_filings': data['remaining_filings_at_switch'],
                  'groups': len(data['reporting_batches']), 'next': data['reporting_batches'][0]}
    else:
        result = {'status': group_status, 'prepare-next': prepare_next, 'report': report_group,
                  'publish': lambda _: publish_groups()}[args.action](args.batch)
    print(json.dumps(result, indent=2))
