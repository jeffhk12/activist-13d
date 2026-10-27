"""Tier 0 operational status from record metadata only; no adaptive label tuning."""
import json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'research/runs/extraction-stability/20261025-v2'


def main():
    inventory=json.loads((RUN/'inputs/inventory.json').read_text())
    completed=[]
    pending=[]
    for row in inventory:
        for agent in ['A','B','C']:
            path=RUN/'agents'/agent/'records'/f'{row["accession"]}.json'
            if path.exists():
                try:
                    record=json.loads(path.read_text())
                except json.JSONDecodeError:
                    pending.append([row['case_id'],agent,'write_in_progress'])
                    continue
                completed.append({'case_id':row['case_id'],'agent':agent,
                  'status':record['extraction_status'],
                  'full_delivery':record['review_delivery']['all_readable_text_delivered']})
            else:
                pending.append([row['case_id'],agent])
    result={'finalized':len(completed),'expected':30,
            'statuses':dict(Counter(r['status'] for r in completed)),
            'mechanical_full_delivery':sum(r['full_delivery'] for r in completed),
            'completed_jobs':completed,'pending_jobs':pending}
    (RUN/'progress.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
