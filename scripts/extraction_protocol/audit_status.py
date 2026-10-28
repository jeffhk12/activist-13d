"""Tier0 operational metadata only; does not analyze reviewer verdicts."""
import json
from pathlib import Path

RUN=Path(__file__).resolve().parents[2]/'research/runs/extraction-audit/20261027-v1'


def main():
    jobs=json.loads((RUN/'inputs/jobs.json').read_text())
    complete=[]
    pending=[]
    for job in jobs:
        path=RUN/'jobs'/job['job_id']/'record.json'
        if path.exists():
            r=json.loads(path.read_text())
            complete.append({'job_id':job['job_id'],
                             'full_delivery':r['review_delivery']['all_readable_text_delivered'],
                             'characters':r['review_delivery']['served_unique_characters']})
        else:
            pending.append(job['job_id'])
    out={'complete_count':len(complete),'total_jobs':len(jobs),'complete':complete,'pending':pending}
    (RUN/'progress.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps(out,indent=2))


if __name__=='__main__':
    main()
