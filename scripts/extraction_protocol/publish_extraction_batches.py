"""Publish current batch status and a plain-English learning checkpoint.

Inputs: frozen queue, per-batch job statuses and completed summaries. Outputs:
mutable progress HTML/JSON, navigation with preserved pre-edit snapshots.
Identity: completed unique filings = 13 prior + completed new triplets; queue
counts remain separate from accuracy and first-model eligibility. Tier:1.
Run project Python publish_extraction_batches.py. No model or network calls.
"""
import sys
from html import escape

from extraction_batches import BASE, ROOT, core, frozen, status


def publish():
    queue = core.read(BASE / 'queue.json')
    batches = []
    for directory in sorted(BASE.glob('batch-*')):
        number = int(directory.name.split('-')[-1])
        item = status(number)
        summary_path = directory / 'summary.json'
        item['summary'] = core.read(summary_path) if summary_path.exists() else None
        batches.append(item)
    complete_filings = sum(x['summary']['filings'] for x in batches if x['summary'])
    jobs_complete = sum(x['complete_jobs'] for x in batches)
    jobs_total = sum(x['total_jobs'] for x in batches)
    capacity_errors = ['batch001_blind01', 'batch001_extractor02']
    for path in sorted(BASE.glob('batch-*/operational-retries.json')):
        for event in core.read(path)['events']:
            if event['error_type'] == 'model_capacity' and event['stage'] == 'before_source_execution':
                capacity_errors.append(event['agent_task'].rsplit('/', 1)[-1])
    payload = {'queued_filings': queue['queued_filings'], 'new_completed_filings': complete_filings,
               'prior_completed_filings': 13, 'completed_filings_total': 13 + complete_filings,
               'remaining_eligible_filings': queue['queued_filings'] - complete_filings,
               'batches': batches, 'all_fields_experimental': True,
               'capacity_errors_before_source_execution': list(dict.fromkeys(capacity_errors)),
               'operational_retries': 'Same assigned jobs, prompts and inherited model; no score-selected semantic retry.'}
    (BASE / 'progress.json').write_bytes(core.enc(payload))
    table = ''
    for item in batches:
        number = item['batch']
        if item['summary']:
            s = item['summary']
            state = f'Complete: {s["filings"]} filings, {s["intent_agreement"]}/{s["intent_cells"]} reader agreement, {s["eligible_experimental_intents"]}/{s["intent_cells"]} experimental-use cells'
            link = f'<a href="batch-{number:03}/index.html">Read batch results</a>'
            if (BASE / f'batch-{number:03}' / 'case-notes.html').exists():
                link += f' · <a href="batch-{number:03}/case-notes.html">What was extracted</a>'
        else:
            state = f'In progress: {item["complete_jobs"]}/{item["total_jobs"]} jobs finalized'
            link = f'<a href="batch-{number:03}/inventory.json">Assigned source inventory</a>'
        table += f'<tr><td>{number}</td><td>{escape(state)}</td><td>{link}</td></tr>'
    result = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>13D extraction batches</title><style>body{{font:17px/1.65 system-ui;color:#203448;background:#f4f6f8}}main{{max-width:1050px;margin:30px auto;background:white;padding:28px}}table{{border-collapse:collapse;width:100%}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #ccd5de}}a{{color:#155c99}}code{{overflow-wrap:anywhere}}</style><main><h1>13D extraction in batches</h1><p>28 October 2026 · Experimental data preparation</p><p>We are preparing to test whether an investor's stated intentions add ranking value beyond financial inputs. Extraction is now proceeding in saved batches of five filings. This stage creates measurements; it does not establish investment performance.</p><p><strong>{complete_filings} new filings completed</strong>, in addition to the 13 earlier filings. {jobs_complete}/{jobs_total} jobs are finalized across currently released batches.</p><table><tr><th>Batch</th><th>Status</th><th>Evidence</th></tr>{table}</table><h2>How the filing count reconciles</h2><p>The existing panel contains 667 filings. Thirteen already have the completed v3 workflow. Seven reserved cases and their known issuer/reporter connections exclude 27 panel filings in total; the seven are inside that 27. This leaves 627 filings in the production queue, with {627-complete_filings} still to finish. Human-reference protections were applied separately and remove no additional panel filings after these exclusions.</p><p>The queue has 593 filings at or below 100,000 canonical text characters and 34 longer filings. The shorter tier comes first, with a fixed hash order inside each tier. Longer sources remain queued without text truncation. Batch results do not estimate population accuracy.</p><h2>What a batch means</h2><p>Each filing receives two separate source-only readings and a third agent's backward review of the preassigned extractor. A completed filing means all three records pass the source-delivery, schema and exact-citation checks. For example, the readers can label a stated company-sale plan while leaving routine closing-related director succession as a contract fact.</p><p>A field passes the experimental-use filter when both readers agree on present or not stated and the critic supports the claim. We retain all three possible states, their two-reader frequencies and every uncertainty/disagreement flag. A 1/2 frequency describes two observed answers; it is not a 50% probability of truth.</p><p>Qualified funding retains its actor, financing type, certainty and current versus historical link. Its comparisons remain descriptive; the final model transformation is not yet frozen. Raw ownership facts are saved, but ownership-derived features and transaction counts stay out of the first model. Same-model agents may share mistakes. Natural-data accuracy remains unmeasured.</p><h2>What happens next</h2><p>Finish the released batch, publish all disagreements and source limitations, then release the next five after its predecessor passes the technical checks. Finalized records are cached and immutable. No new per-filing human review is requested. Bloomberg correction remains a separate pending workstream; no investment model was fitted.</p><p><a href="queue.json">Frozen queue and every exclusion</a> · <a href="protocol.json">Batch protocol</a> · <a href="progress.json">Machine-readable progress</a> · <a href="../../extraction-revision/20261027-v3/readiness.html">Earlier readiness findings</a> · <a href="../../../../START-HERE.html">Project home</a></p><details><summary>Resume commands</summary><p>From the project root, use the project Python with PYTHONNOUSERSITE=1 and PYTHONIOENCODING=utf-8.</p><p><code>.venv/bin/python scripts/extraction_protocol/extraction_batches.py status --batch 1</code></p><p><code>.venv/bin/python scripts/extraction_protocol/extraction_batches.py report --batch 1</code></p><p><code>.venv/bin/python scripts/extraction_protocol/extraction_batches.py prepare --batch 2</code></p><p>Role workers use <code>extraction_batch_io.py --batch N ACTION --job JOB</code> with a fresh one-role/one-filing context. Source-only readers do not inspect one another. The parent mechanically seals the extractor's candidate before starting the critic.</p></details></main></html>'''
    result = result.replace('extraction_batches.py report', 'extraction_batches_v2.py report').replace('extraction_batches.py prepare', 'extraction_batches_v2.py prepare')
    larger_configured = (BASE / 'reporting-25-v1/plan.json').exists()
    if larger_configured:
        sys.path.insert(0, str(ROOT / 'scripts'))
        from extraction_reporting_groups import publish_groups
        next_group = publish_groups()
        if next_group:
            section = f'<section><h2>Current reporting batch:25 filings</h2><p>Reporting batch {next_group["reporting_batch"]} covers {next_group["filings"]} filings and {next_group["jobs"]} agent jobs. It is {next_group["completed_filings"]}/{next_group["filings"]} complete, with {next_group["completed_jobs"]}/{next_group["jobs"]} records finalized. Progress saves every five filings; continuation advances through the full larger batch without asking after every checkpoint.</p><p><a href="reporting-25-v1/index.html">Larger-batch plan and progress</a></p></section>'
            result = result.replace('<h1>13D extraction in batches</h1>', '<h1>13D extraction in batches</h1>' + section, 1)
        completed_reports = []
        for summary_path in sorted((BASE / 'reporting-25-v1').glob('batch-*/summary.json')):
            if not (summary_path.parent / 'index.html').exists():
                continue
            s = core.read(summary_path)
            href = str((summary_path.parent / 'index.html').relative_to(BASE))
            completed_reports.append(f'<p><a href="{href}">Reporting batch {s["reporting_batch"]}: {s["filings"]} filings completed</a> · {s["intent_agreement"]}/{s["intent_cells"]} reader agreement · {s["eligible_experimental_intents"]}/{s["intent_cells"]} experimental-use cells</p>')
        if completed_reports:
            result = result.replace('<h1>13D extraction in batches</h1>', '<h1>13D extraction in batches</h1><section><h2>Completed larger reporting batches</h2>' + ''.join(completed_reports) + '</section>', 1)
        result = result.replace('Extraction is now proceeding in saved batches of five filings.', 'Reporting now covers25 filings at a time, with saved five-filing checkpoints.')
        result = result.replace('<table><tr><th>Batch</th>', '<h2>Saved five-filing checkpoints</h2><table><tr><th>Checkpoint</th>')
        result = result.replace('Finish the released batch, publish all disagreements and source limitations, then release the next five after its predecessor passes the technical checks.', 'Complete the25-filing reporting batch through its saved five-filing checkpoints. Publish all disagreements and source limitations; each next checkpoint opens only after its predecessor passes the technical checks.')
    (BASE / 'index.html').write_text(result)
    nav = [('START-HERE.html', '<!-- extraction-batches-current -->', f'''<section><h2>Current: 13D extraction in batches — October 28</h2><p>To prepare the financial-input versus filing-text ranking comparison, we are running five-filing batches under the frozen v3 rules. Two source-only readers and one backward critic process each filing. {complete_filings} new filings are complete; {jobs_complete}/{jobs_total} released jobs are finalized.</p><a class="button" href="research/runs/extraction-batches/20261028-v1/index.html">Batch progress, results and learning checkpoint</a><p>The production queue contains627 filings after13 completed filings and27 reserved/connected filings are set aside. Seven reserved sources remain closed. All fields remain experimental. Unknowns and critic flags stay explicit; LLM ownership-derived features and transaction counts remain excluded. No investment fitting or Bloomberg collection.</p></section>'''),
           ('research/docs/ml-checkpoints.html', '<!-- extraction-batches-current -->', f'''<section class="current"><h2>Current checkpoint: extraction in saved batches</h2><p>We are creating filing-text measurements for the later comparison against financial-only ranking. {complete_filings} new filings have completed the two-reader and backward-critic workflow;13 were completed earlier. The queue contains627 eligible new filings; seven reserved cases plus their known connections account for27 exclusions from the667-filing panel.</p><p>A batch is a small saved work unit: five filings,15 independent-role jobs. It makes interruptions resumable and lets technical failures stop release of the next batch. An objective passes the experimental-use filter only with matching nonunknown reader states and critic support. The full state frequencies and flags remain saved; agreement does not establish accuracy.</p><p>For example, a proposed whole-company acquisition can qualify as a sale objective while automatic director succession remains a contract fact. Funding keeps actual versus possible/historical financing separate. LLM ownership-derived features and transaction counts remain excluded. No new investment model was fitted.</p><p><a href="../runs/extraction-batches/20261028-v1/index.html">Batch progress, evidence and resume instructions</a></p></section>''')]
    for name, marker, section in nav:
        if larger_configured:
            section = section.replace('we are running five-filing batches under the frozen v3 rules.', 'we are using25-filing reporting batches with five-filing saved checkpoints under the frozen v3 rules.')
            section = section.replace('A batch is a small saved work unit: five filings,15 independent-role jobs.', 'A reporting batch now contains25 filings and75 role jobs, saved in five checkpoints of five filings. Each role still has a fresh filing context.')
        path = ROOT / name
        frozen(BASE / 'navigation-before' / path.name, path.read_bytes(), raw=True) if not (BASE / 'navigation-before' / path.name).exists() else None
        text = path.read_text()
        if marker in text:
            before, after = text.split(marker, 1)
            after = after[after.index('</section>') + len('</section>'):]
            text = before + marker + section + after
        else:
            token = '<body><main>' if name == 'START-HERE.html' else '<main>'
            if token not in text:
                # The checkpoint currently uses a body/main opening with attributes.
                location = text.index('>', text.index('<main')) + 1
                text = text[:location] + marker + section + text[location:]
            else:
                text = text.replace(token, token + '\n' + marker + section, 1)
        if name == 'START-HERE.html':
            text = text.replace('Current: shared-rule extraction tested — October 27', 'Completed: shared-rule extraction tested — October 27')
        else:
            text = text.replace('Current checkpoint: define the measurement before scaling extraction', 'Completed checkpoint: define the measurement before scaling extraction')
        path.write_text(text)
    plan = ROOT / 'research/docs/PROJECT-PLAN.md'
    frozen(BASE / 'navigation-before/PROJECT-PLAN.md', plan.read_bytes(), raw=True) if not (BASE / 'navigation-before/PROJECT-PLAN.md').exists() else None
    marker = '<!-- extraction-batches-current -->'
    section = f'''{marker}
## Extraction batches underway — October 28, 2026

User authorized batch continuation. The fixed queue has627 eligible new filings:
667 panel filings less13 completed filings less27 reserved/connected filings.
The seven reserved cases are included in27; human protections remain applied.
Five filings per batch receive two source-only readings and a backward critic.
Current state: {complete_filings} new filings complete, {jobs_complete}/{jobs_total} released jobs finalized.
Finalized records are cached; every next release requires previous technical checks.
All measurements remain experimental. Unknown/disagreement/critic flags are retained;
LLM ownership-derived features and transaction counts stay out of the first model.
Qualified funding remains a candidate, with no final transformation frozen yet.
No new fitting, Bloomberg collection, paid API or online source retrieval.

[Progress, results and learning checkpoint](../runs/extraction-batches/20261028-v1/index.html)

<!-- extraction-batches-current-end -->
'''
    if larger_configured:
        section = section.replace('Five filings per batch receive two source-only readings and a backward critic.', 'Reporting now covers25 filings and75 role jobs at a time, with saved five-filing checkpoints.\nEach filing retains two source-only readings and a backward critic.\nContinue through the full larger batch without asking after each checkpoint; source-release gates remain in force.')
    text = plan.read_text()
    if marker in text:
        before, after = text.split(marker, 1)
        after = after.split('<!-- extraction-batches-current-end -->', 1)[1]
        text = before + section + after
    else:
        first, rest = text.split('\n', 1)
        text = first + '\n\n' + section + rest
    plan.write_text(text)
    return payload


if __name__ == '__main__':
    result = publish()
    print(core.enc({k: v for k, v in result.items() if k != 'batches'}).decode())
