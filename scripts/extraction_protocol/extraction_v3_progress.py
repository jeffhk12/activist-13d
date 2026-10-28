"""Operational v3 job metadata, without comparing field labels or verdicts.

Inputs: frozen jobs and existence/metadata of final records. Outputs: progress
counts, ready critics; optional fixed-extractor candidate sealing. Identity:
complete jobs + pending jobs =42. Tier:0 orchestration; no semantic evaluation.
Run: project Python extraction_v3_progress.py [--seal-ready].
"""
import argparse
import json
from collections import Counter

from extraction_v3_io import RUN, enc, read, seal_candidate


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seal-ready',action='store_true')
    args=parser.parse_args()
    jobs=read(RUN/'jobs.json')
    completed=[]
    pending=[]
    ready_critics=[]
    for job in jobs:
        path=RUN/'jobs'/job['job_id']/'record.json'
        if path.exists():
            r=read(path)
            completed.append({'job_id':job['job_id'],'phase':job['phase'],
                              'full_delivery':r['review_delivery']['all_readable_text_delivered']})
        else:
            pending.append(job['job_id'])
            if job['role']=='critic' and (RUN/'jobs'/job['candidate_source_job']/'record.json').exists():
                if args.seal_ready:
                    seal_candidate(job)
                ready_critics.append(job['job_id'])
    result={'complete_count':len(completed),'total_jobs':len(jobs),
            'completed_by_phase':dict(Counter(r['phase'] for r in completed)),
            'complete':completed,'pending':pending,'ready_critics':ready_critics,
            'fresh_released':(RUN/'fresh-release.json').exists()}
    (RUN/'progress.json').write_bytes(enc(result))
    print(json.dumps({k:v for k,v in result.items() if k!='complete'},indent=2))


if __name__=='__main__':
    main()
