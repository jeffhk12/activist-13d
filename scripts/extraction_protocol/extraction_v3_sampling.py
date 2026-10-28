"""Select three bounded v3 operational-check cases using metadata alone.

Inputs: reserved case-row metadata and explicit accession/group/issuer exclusions.
Outputs: three deep-copied rows and a JSON-ready selection trace; no file reads,
source release, model calls or writes. Identity: n=3, one early + one recent slot,
then gap/multiple-document/any preference; unique accession, group and issuer;
canonical_text_chars in (0,100000]. Rank by SHA256(seed + ':' + accession).
Tier: 1. Run: import select_fresh only after protocol/prompt/schema freeze, using
project Python with PYTHONNOUSERSITE=1 and PYTHONIOENCODING=utf-8. Tests:
 .venv/bin/python -m pytest tests/test_extraction_v3_sampling.py

This is an operational/measurement-consistency check, not statistical validation.
Human-reference accuracy is unestimated. Caller logs release separately and
preserves all original reserved assets; this module authorizes no full 667-case
run or paid API. Unknown earlier reading and economic affiliations remain limits.
"""
import re
from collections import Counter
from collections.abc import Mapping
from copy import deepcopy
from hashlib import sha256

SEED = 'extraction-v3-fresh-20261027'
MAX_CHARACTERS = 100000
SAMPLE_SIZE = 3
METADATA_FIELDS = (
    'accession', 'connected_group', 'issuer', 'era', 'canonical_text_chars',
    'canonical_documents', 'documents_without_text', 'source_path', 'source_sha256',
)


def _integer(value, minimum):
    return type(value) is int and value >= minimum


def _missing_or_invalid(row):
    for key in ('accession', 'connected_group', 'issuer', 'source_path'):
        if not isinstance(row.get(key), str) or not row[key].strip():
            return 'missing_' + key
    if row.get('era') not in ('early', 'recent'):
        return 'invalid_era'
    if not _integer(row.get('canonical_text_chars'), 1):
        return 'unavailable_readable_text_metadata'
    if row['canonical_text_chars'] > MAX_CHARACTERS:
        return 'above_character_cap'
    if not _integer(row.get('canonical_documents'), 1):
        return 'unavailable_document_metadata'
    missing = row.get('documents_without_text')
    if not _integer(missing, 0) or missing > row['canonical_documents']:
        return 'invalid_missing_document_metadata'
    digest = row.get('source_sha256')
    if not isinstance(digest, str) or re.fullmatch('[0-9a-fA-F]{64}', digest) is None:
        return 'unavailable_source_hash_metadata'
    return None


def _exclusions(values, name):
    if isinstance(values, (str, bytes)):
        raise ValueError(name + ' must be an iterable of identifiers, not one string')
    result = set(values)
    if any(not isinstance(value, str) or not value for value in result):
        raise ValueError(name + ' must contain nonempty strings')
    return result


def select_fresh(rows, excluded_accessions=(), *, excluded_groups=(), excluded_issuers=()):
    """Return (three row copies, trace), refusing an unfillable fixed slot.

    Inspect only METADATA_FIELDS; surplus fields never influence selection.
    Callers must provide an outcome-free metadata frame. Copying retains its
    provenance fields without interpreting them. Exclusions by group/issuer must
    include discovery relatives, since excluded accessions may be outside rows.
    Input row order is irrelevant; repeated accessions are an ambiguous frame and
    refuse rather than choosing one duplicate. There is no adaptive backtracking.
    """
    accessions = _exclusions(excluded_accessions, 'excluded_accessions')
    groups = _exclusions(excluded_groups, 'excluded_groups')
    issuers = _exclusions(excluded_issuers, 'excluded_issuers')
    materialized = list(rows)
    eligible = []
    filtered = Counter()
    seen = set()
    for row in materialized:
        if not isinstance(row, Mapping):
            raise ValueError('Each reserved metadata row must be an object')
        accession = row.get('accession')
        if isinstance(accession, str) and accession:
            if accession in seen:
                raise ValueError('Duplicate accession in metadata frame: ' + accession)
            seen.add(accession)
        reason = _missing_or_invalid(row)
        if reason:
            filtered[reason] += 1
        elif accession in accessions:
            filtered['excluded_accession'] += 1
        elif row['connected_group'] in groups:
            filtered['excluded_group'] += 1
        elif row['issuer'] in issuers:
            filtered['excluded_issuer'] += 1
        else:
            eligible.append(row)

    def rank(row):
        return sha256((SEED + ':' + row['accession']).encode()).hexdigest(), row['accession']

    eligible.sort(key=rank)
    selected = []
    selected_accessions = set()
    selected_groups = set()
    selected_issuers = set()
    slots = []
    for slot in ('early', 'recent', 'complexity'):
        available = [row for row in eligible
                     if row['accession'] not in selected_accessions
                     and row['connected_group'] not in selected_groups
                     and row['issuer'] not in selected_issuers]
        if slot in ('early', 'recent'):
            candidates = [row for row in available if row['era'] == slot]
            preference = 'era_' + slot
            preference_counts = None
        else:
            gap = [row for row in available if row['documents_without_text'] > 0]
            multiple = [row for row in available if row['canonical_documents'] >= 3]
            candidates = gap or multiple or available
            preference = ('documents_without_text' if gap else
                          'multiple_documents' if multiple else 'any')
            preference_counts = {'documents_without_text': len(gap),
                                 'multiple_documents': len(multiple), 'any': len(available)}
        if not candidates:
            raise ValueError('Unfillable frozen sampling slot: ' + slot)
        chosen = candidates[0]
        selected.append(deepcopy(dict(chosen)))
        selected_accessions.add(chosen['accession'])
        selected_groups.add(chosen['connected_group'])
        selected_issuers.add(chosen['issuer'])
        slots.append({'slot': slot, 'preference': preference,
                      'fallback_used': slot == 'complexity' and preference != 'documents_without_text',
                      'preference_counts_after_prior_slots': preference_counts,
                      'eligible_available_count': len(available), 'matching_candidate_count': len(candidates),
                      'selected_accession': chosen['accession'], 'era': chosen['era'],
                      'connected_group': chosen['connected_group'], 'issuer': chosen['issuer'],
                      'canonical_text_chars': chosen['canonical_text_chars'],
                      'seeded_tie_break_sha256': rank(chosen)[0]})
    if (len(selected) != SAMPLE_SIZE or len(selected_groups) != SAMPLE_SIZE
            or len(selected_issuers) != SAMPLE_SIZE
            or {row['era'] for row in selected} != {'early', 'recent'}):
        raise ValueError('Sampling contract failed; do not release evidence')
    trace = {'seed': SEED, 'maximum_canonical_text_characters': MAX_CHARACTERS,
             'sample_size': SAMPLE_SIZE, 'input_rows': len(materialized),
             'exclusions': {'accessions': sorted(accessions), 'connected_groups': sorted(groups),
                            'issuers': sorted(issuers)},
             'eligible_rows_before_slot_uniqueness': len(eligible),
             'filtered_reason_counts': dict(sorted(filtered.items())),
             'selection_inputs': list(METADATA_FIELDS), 'slots': slots,
             'limits': 'Three metadata-selected operational cases; not population accuracy or independent semantic validation. No source text was opened or released by this function.'}
    return selected, trace
