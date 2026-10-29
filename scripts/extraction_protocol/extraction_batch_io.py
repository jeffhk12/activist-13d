"""Serve one batch job using unchanged extraction-v3 semantics and validation.

Inputs: --batch integer and frozen job/source/draft. Outputs: existing v3 delivery,
draft history, sealed candidates and immutable records in the selected batch.
Identity: batch root changes; common rules/schema/normalizer remain byte-identical.
Tier:1. Run project Python extraction_batch_io.py --batch 1 ACTION --job JOB.
"""
import argparse
import sys

import extraction_v3_io as core

BASE = core.ROOT / 'research/runs/extraction-batches/20261028-v1'


def use_batch(number):
    if number < 1:
        raise ValueError('Positive batch number required')
    core.RUN = BASE / f'batch-{number:03}'
    preparation = core.read(core.RUN / 'preparation.json')
    for name, expected in preparation['source_code_sha256'].items():
        if core.sha((core.ROOT / name).read_bytes()) != expected:
            raise ValueError('Frozen implementation changed: ' + name)
    return core.RUN


if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--batch', type=int, required=True)
    args, rest = parser.parse_known_args()
    use_batch(args.batch)
    sys.argv = [sys.argv[0], *rest]
    core.main()
