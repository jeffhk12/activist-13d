"""Tier: 2. Verify source-only cleanup against preserved original source bytes.
Inputs: frozen metadata/manifest and preformat sources; outputs: provenance receipt.
Identity: canonical(old selection)=canonical(new selection)=frozen candidate JSON.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/phase1_evaluation_readiness_cleanup_receipt.py
No future returns loaded; original manifest remains immutable.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

from activist13d.phase1_evaluation_readiness_selection import candidates

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'research/runs/phase1-baseline/20260924-evaluation-readiness-v1'
CLEANUP = OUT / 'receipts/source-cleanup-v1'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def events(obj):
    if isinstance(obj, dict):
        if {'issuer', 'entry', 'accession'} <= obj.keys():
            yield obj
        for value in obj.values():
            yield from events(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from events(value)


def main():
    source_paths = [ROOT / 'src/activist13d/phase1_evaluation_readiness_selection.py',
                    ROOT / 'tests/test_phase1_evaluation_readiness_selection.py']
    source_paths += [ROOT / f'scripts/data_collection/phase1_evaluation_readiness_{name}.py'
                     for name in ('audit', 'verify', 'cache_metadata')]
    mapping = {str(p.relative_to(ROOT)): {
        'original_snapshot': str((CLEANUP / 'preformat' / p.name).relative_to(ROOT)),
        'original_sha256': digest(CLEANUP / 'preformat' / p.name),
        'cleaned_sha256': digest(p)} for p in source_paths}
    manifest = json.loads((OUT / 'manifest.json').read_text())
    for path, receipt in manifest['inputs'].items():
        actual = mapping[path]['original_sha256'] if path in mapping else digest(ROOT / path)
        assert actual == receipt['sha256'], path
    for path, sha in manifest['outputs'].items():
        assert digest(OUT / path) == sha, path
    for receipt_name in ('verification.json', 'cache-metadata-supplement.json'):
        receipt = json.loads((OUT / 'receipts' / receipt_name).read_text())
        for path, sha in receipt['inputs'].items():
            actual = mapping[path]['original_sha256'] if path in mapping else digest(ROOT / path)
            assert actual == sha, path
    base = ROOT / 'research/runs/phase1-baseline'
    registry = [json.loads(line) for line in (base / '20260924-feasibility-v2/event-candidates.jsonl').read_text().splitlines()]
    eligibility = {r['accession']: r for line in (base / '20260924-universe-rebuild-v3/eligibility.jsonl').read_text().splitlines()
                   if (r := json.loads(line))}
    sessions = json.loads((base / '20260924-feasibility-v2/entry-calendar.json').read_text())
    protected = set(json.loads((base / '20260924-development-v4/human-review-protection.json').read_text())['issuers'])
    summary = json.loads((OUT / 'summary.json').read_text())
    exposed = set(summary['preview_issuers'])
    for item in summary['development_sources']:
        exposed |= {e['issuer'] for e in events(json.loads((ROOT / item['path']).read_text()))}
    args = (registry, eligibility, sessions, protected, exposed, set(summary['quarantined_permnos']))
    original_path = CLEANUP / 'preformat/phase1_evaluation_readiness_selection.py'
    spec = importlib.util.spec_from_file_location('readiness_preformat', original_path)
    original = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original)
    before, after = original.candidates(*args), candidates(*args)
    def encode(obj):
        return (json.dumps(obj, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    assert encode(before) == encode(after) == (OUT / 'candidate-selection.json').read_bytes()
    result = {'purpose': 'Source-only lint cleanup; original frozen run remains unchanged.',
              'source_hash_mapping': mapping,
              'original_manifest_verified_using_preserved_source_snapshots': True,
              'original_supplemental_receipt_inputs_verified_using_snapshots': True,
              'all_frozen_output_hashes_match': True,
              'old_new_and_frozen_candidate_json_byte_identical': True,
              'candidate_json_sha256': hashlib.sha256(encode(after)).hexdigest(),
              'cleanup': ['import spacing/order', 'removed two unused verifier reads', 'split test statements onto separate lines'],
              'replay_instruction': 'Run this cleanup-receipt verifier after source cleanup. Original manifest targets original source snapshots; do not rewrite its hashes.',
              'verifier_sha256': digest(Path(__file__))}
    path = CLEANUP / 'provenance.json'
    raw = json.dumps(result, sort_keys=True, indent=2) + '\n'
    if path.exists():
        assert path.read_text() == raw
    else:
        path.write_text(raw)
    print(json.dumps({k: v for k, v in result.items() if k != 'source_hash_mapping'}, indent=2))


if __name__ == '__main__':
    main()
