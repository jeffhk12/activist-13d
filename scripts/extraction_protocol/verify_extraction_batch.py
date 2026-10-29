"""Independently audit one completed batch's original sources and interval unions.

Inputs: immutable batch inventory, local raw submissions, staging receipts, served
range receipts, records and sealed candidates. Output: immutable archive receipt.
Identity: sum of merged disjoint ranges = each document's Unicode length; original
gzip bytes = released copy; exact quoted slices equal stored quotes. Tier:1.
Run project Python verify_extraction_batch.py --batch 1. No network/model calls.
"""
import argparse
import gzip
import json

from extraction_batches import BASE, ROOT, STAGING, core, frozen


def covered_length(ranges, expected):
    cursor = 0
    for start, end in sorted(ranges):
        if not 0 <= start < end <= expected or start > cursor:
            raise ValueError('Invalid or missing source range')
        cursor = max(cursor, end)
    if cursor != expected:
        raise ValueError('Source tail not delivered')
    return cursor


def verify(number):
    run = BASE / f'batch-{number:03}'
    documents, characters, quotes = 0, 0, 0
    queue = core.read(BASE / 'queue.json')
    reserved = set(queue['reserved_accessions'])
    expected = [r['accession'] for r in queue['queue'] if r['batch_number'] == number]
    inventory = core.read(run / 'inventory.json')
    if expected != [r['accession'] for r in inventory] or reserved.intersection(expected):
        raise ValueError('Queue identity/reservation mismatch')
    for case in inventory:
        raw = (ROOT / case['source_path']).read_bytes()
        if core.sha(raw) != case['source_sha256']:
            raise ValueError('Original raw source changed')
        source_copy = (STAGING / 'bundles' / f'{case["accession"]}.json.gz').read_bytes()
        receipt = core.read(STAGING / 'receipts' / f'{case["accession"]}.json')
        bundle_raw = (run / case['bundle']).read_bytes()
        if source_copy != bundle_raw or core.sha(bundle_raw) != receipt['bundle_sha256'] or receipt['source_sha256'] != core.sha(raw):
            raise ValueError('Source-copy/receipt identity mismatch')
        bundle = json.loads(gzip.decompress(bundle_raw))
        docs = {d['document_id']: d for d in bundle['documents'] if d.get('text')}
        for doc in docs.values():
            if core.sha(doc['text'].encode()) != doc['text_sha256']:
                raise ValueError('Canonical source hash mismatch')
        for role in ['extractor', 'blind', 'critic']:
            job_id = role + '_' + case['case_id'].lower()
            own = run / 'jobs' / job_id
            ranges = {key: [] for key in docs}
            for path in (own / 'delivery').glob('*.json'):
                delivery = core.read(path)
                did = delivery['document_id']
                start, end = delivery['start'], delivery['end']
                if delivery['job_id'] != job_id or delivery['text_sha256'] != docs[did]['text_sha256'] or end-start > 16000 or core.sha(docs[did]['text'][start:end].encode()) != delivery['chunk_sha256']:
                    raise ValueError('Range source identity mismatch')
                ranges[did].append((start, end))
            characters += sum(covered_length(ranges[did], len(doc['text'])) for did, doc in docs.items())
            documents += len(docs)
            record = core.read(own / 'record.json')
            if set(record['reviewed_document_ids']) != set(docs) or record.get('review_status', record.get('extraction_status')) != 'complete_readable_bundle':
                raise ValueError('Incomplete review attestation')

            def check(value, docs=docs):
                count = 0
                if isinstance(value, dict):
                    if 'quote' in value:
                        text = docs[value['document_id']]['text']
                        if text[value['start']:value['end']] != value['quote']:
                            raise ValueError('Quote mismatch')
                        count += 1
                    count += sum(check(v) for v in value.values())
                elif isinstance(value, list):
                    count += sum(check(v) for v in value)
                return count

            quotes += check(record)
            if role == 'critic':
                candidate = core.read(run / 'candidates' / f'{job_id}.json')
                seal = core.read(run / 'candidates' / f'{job_id}.seal.json')
                original = own.parent / ('extractor_' + case['case_id'].lower()) / 'record.json'
                if core.sha(original.read_bytes()) != seal['original_record_sha256'] or core.sha((run / 'candidates' / f'{job_id}.json').read_bytes()) != seal['candidate_sha256']:
                    raise ValueError('Candidate seal mismatch')
                claims = [c['claim_id'] for c in candidate['claims']]
                reviewed = [c['claim_id'] for c in record['reviews']]
                if sorted(claims) != sorted(reviewed) or len(reviewed) != len(set(reviewed)):
                    raise ValueError('Claim coverage mismatch')
    result = {'batch': number, 'filings': len(inventory), 'role_document_reviews': documents,
              'independently_verified_delivered_characters': characters,
              'independently_verified_exact_quote_entries': quotes,
              'raw_gzip_receipts_canonical_text_and_candidate_seals': 'passed',
              'remaining_reserved_accessions_released': 0,
              'limit': 'Source integrity and delivery, not comprehension or semantic accuracy.'}
    frozen(run / 'archive-verification.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', type=int, required=True)
    print(json.dumps(verify(parser.parse_args().batch), indent=2))
