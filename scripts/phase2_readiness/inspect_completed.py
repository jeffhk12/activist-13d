"""Tier: 0. Read-only inspection of completed diagnostic artifacts for discussion.
Inputs: saved coverage, receipts, selection. Output: aggregate console summaries.
Identity: filing counts are sums of existing receipt indicators; no new model.
Run: project Python scripts/phase2_readiness/inspect_completed.py
"""
import json
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / 'research/runs/phase2-readiness/20260924-full-v1'
SOURCE = ROOT / 'research/runs/phase2-overnight/20260924-full-v1'
coverage = json.loads((AUDIT / 'field-coverage.json').read_text())
print('ALL FIELD COVERAGE')
for r in coverage:
    if r['year'] == 'all' and r['field'].split('.')[0] in {'filing_entities','issuers','filings','reporting_persons','securities','ownership'}:
        print(json.dumps(r))
print('YEARLY OWNERSHIP COVERAGE: at least one present percentage')
for r in coverage:
    if r['year'] != 'all' and r['field'] == 'ownership.percent_of_class':
        print(json.dumps(r))
rows = [json.loads(p.read_text()) for p in (AUDIT / 'receipts').glob('*.json')]
issues = Counter()
for r in rows:
    issues.update(r.get('quality_issue_types', {}))
print('ISSUE OCCURRENCES', json.dumps(issues))
print('ZERO REPORTING PERSON ROWS', sum(r.get('reporting_person_rows') == 0 for r in rows))
selection = json.loads((SOURCE / 'selection.json').read_text())
print('CAMPAIGN AUDIT', json.dumps(Counter(r['eligibility_audit_only'] for r in selection)))
history = [json.loads(s) for s in (SOURCE / 'prior-header-cik-history.jsonl').read_text().splitlines()]
print('HISTORY', json.dumps({'filings': len(history),
'with_reporter_prior_submissions': sum(any(x['prior_submission_count'] > 0 for x in r['reporter_history']) for r in history),
'with_issuer_prior_outside_current_reporter_ciks': sum(any(x['prior_reporter_ciks_outside_current_group'] > 0 for x in r['issuer_history']) for r in history),
'unique_header_reporter_ciks': len({x['cik'] for r in history for x in r['reporter_history']}),
'unique_issuer_ciks': len({x['cik'] for r in history for x in r['issuer_history']})}))
