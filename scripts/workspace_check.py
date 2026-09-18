"""Verify an offline 13D pilot without overwriting historical research outputs.

Inputs: preserved raw SEC pilot and original parsed pilot records under --source.
Outputs: a new dated local verification folder and byte-equality receipt.
Identity: SHA256(replayed JSONL/audit) equals SHA256(original JSONL/audit).
Tier: 1. Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python
scripts/workspace_check.py --source PATH_TO_DATA_PROJECT.
Uses cached inputs only; never starts collection, model calls or an overnight audit.
"""
import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def verify(source, output):
    expected = source / 'data/interim/pilot'
    before = {name: digest(expected / name) for name in ['filings.jsonl', 'audit.json']}
    raw = source / 'data/raw/edgar/pilot'
    # Copy only the small cached pilot. Regular files work without Windows symlink privileges.
    shutil.copytree(raw, output / 'data/raw/edgar/pilot')
    script = ROOT / 'scripts/collect_pilot.py'
    spec = importlib.util.spec_from_file_location('workspace_offline_pilot', script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = output
    previous_args = sys.argv
    try:
        sys.argv = [str(script), '--offline']
        module.main()
    finally:
        sys.argv = previous_args
    produced = output / 'data/interim/pilot'
    after = {name: digest(produced / name) for name in before}
    if after != before:
        raise RuntimeError('Offline replay differs from the historical pilot; preserve for review.')
    if before != {name: digest(expected / name) for name in before}:
        raise RuntimeError('Original pilot changed during verification.')
    records = [json.loads(line) for line in (produced / 'filings.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(records) == len({r['accession'] for r in records}) == 10
    for record in records:
        assert digest(source / record['source_path']) == record['source_sha256']
        assert digest(output / record['source_path']) == record['source_sha256']
    # Values previously pinned against source cover pages by verify_pilot.py.
    legacy = next(r for r in records if r['accession'] == '0001104659-24-000323')
    assert legacy['cusip'] == '60743G100' and legacy['event_date'] == '2023-12-21'
    modern = next(r for r in records if r['accession'] == '0000807249-25-000003')
    assert modern['cusip'] == 'G9001E102' and modern['event_date'] == '2024-12-27'
    receipt = {'n': 10, 'output_hashes': after, 'source_hashes_verified': True,
               'historical_outputs_unchanged': True, 'network_calls': 0, 'model_calls': 0}
    (output / 'verification.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print('13D OFFLINE REPLAY PASSED:', output)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT)
    args = parser.parse_args()
    output = ROOT / 'output/workspace-validation' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output.mkdir(parents=True, exist_ok=False)
    verify(args.source.resolve(), output)


if __name__ == '__main__':
    main()
