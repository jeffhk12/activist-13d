"""Tier: 2. Tag existing event outcomes with expanded HFR candidate membership.

Inputs: immutable event dictionaries and dated accession union sets.
Outputs: event tags and overlapping aggregate/mutually exclusive group summaries.
Identity: membership is any merged accession; each event counted once per group.
Means/bootstrap follow activist13d.phase1_baseline.summarize unchanged.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python -m pytest tests/test_expanded_hfr_returns.py
"""
from activist13d.phase1_baseline import summarize

LABELS = {
    'all': 'All screened initial disclosures',
    'expanded': 'All HFR + seven supplemental groups',
    'hfr_only': 'HFR-listed managers only',
    'focused': 'Focused activist candidates',
    'other_event_driven': 'Other Event-Driven candidates',
    'new_other_hfr': 'Newly recognized other HFR candidates',
    'other_unresolved': 'Other or unresolved filers',
    'previous_broad': 'Previous Event-Driven + supplement group',
    'fund_of_funds_only': 'Fund-of-funds-only candidate events',
}
DISJOINT = ('focused', 'other_event_driven', 'new_other_hfr', 'other_unresolved')


def tag_event(event, unions):
    accessions = set(event['accessions'])
    if not accessions or event['accession'] not in accessions:
        raise ValueError('Missing representative or merged accessions')
    hfr_hits = accessions & unions['all_hfr']
    supplement_hits = accessions & unions['supplement']
    broad = bool(accessions & (unions['previous_hfr_event_driven_screen'] | unions['supplement']))
    focused = bool(accessions & (unions['manager_has_activist'] | unions['supplement']))
    expanded = bool(accessions & unions['all_hfr_plus_supplement'])
    if broad != event['broad'] or focused != event['focused']:
        raise ValueError('Prior cohort changed unexpectedly')
    if (broad and not expanded) or (focused and not broad):
        raise ValueError('Invalid cohort nesting')
    cohort = ('focused' if focused else 'other_event_driven' if broad else
              'new_other_hfr' if expanded else 'other_unresolved')
    fof = bool(hfr_hits and not supplement_hits and
               hfr_hits <= unions.get('only_fund_of_funds_managers_matched', set()))
    return dict(event, expanded_manager=expanded, hfr_only=bool(hfr_hits),
                disjoint_cohort=cohort, fund_of_funds_only=fof)


def summarize_groups(events):
    groups = dict(all=events,
        expanded=[e for e in events if e['expanded_manager']],
        hfr_only=[e for e in events if e['hfr_only']],
        **{k: [e for e in events if e['disjoint_cohort'] == k] for k in DISJOINT},
        previous_broad=[e for e in events if e['broad']],
        fund_of_funds_only=[e for e in events if e['fund_of_funds_only']])
    return {key: summarize(rows) for key, rows in groups.items()}
