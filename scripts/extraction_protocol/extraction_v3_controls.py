"""Construct deterministic, source-grounded controls for extraction v3.

Inputs: invented complete fixture texts and designer-specified construction keys;
no real filings, model calls or network. Outputs: a 16-claim critic packet and
eight source-only inventory fixtures, with separate hidden keys. Identity: critic
key counts are 8 supported + 6 contradicted + 2 insufficient_evidence; inventory
keys cover 8 x 9 intent states, including 9 positive and 1 unknown state. Tier:1.
Run: project Python -m pytest tests/test_extraction_v3_controls.py.

These small constructed tests assess their stated capabilities. They are not
natural-filing accuracy, omission recall, or an independent reference sample.
"""
import hashlib
import random

SEED = 27301
CATEGORIES = (
    'board_representation', 'leadership_change', 'capital_return',
    'capital_structure', 'sale_of_company', 'asset_transaction',
    'operational_change', 'governance_change', 'other_stated_objective',
)


def _document(document_id, text):
    if not 200 <= len(text) <= 900:
        raise ValueError('Constructed source must contain 200–900 characters')
    return {
        'document_id': document_id,
        'filename': document_id + '.txt',
        'type': 'SYNTHETIC',
        'text': text,
        'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
    }


def claim_controls():
    """Return exposed bundle/candidate and a separate hidden construction key."""
    pairs = [
        (
            'Aster has signed a bid to acquire all of Orion Corporation. At the '
            'merger effective time, the merger subsidiary officers and directors '
            'will succeed the incumbents and Orion will seek delisting. These '
            'provisions apply only to consummating the merger. Aster has made no '
            'separate board-composition or leadership request.',
            'Aster states a sale-of-company objective; effective-time director '
            'succession is retained as a merger implementation fact.',
            'Aster has a separate board-representation objective because the '
            'merger provides for automatic director succession.',
            'contradicted', 'merger_implementation_vs_objective',
        ),
        (
            'Cedar Fund reports that its working capital may include margin '
            'loans under a standing facility. The filing does not identify '
            'whether any facility drawing funded the reported share acquisition. '
            'A prior manager used credit in another investment, but no current '
            'borrowing balance or draw for this acquisition is supplied.',
            'Margin borrowing is a possible source; actual use for this share '
            'acquisition is not established.',
            'Margin borrowing is confirmed to have funded this share acquisition.',
            'insufficient_evidence', 'possible_vs_confirmed_borrowing',
        ),
        (
            'Birch Trust received Orion common shares through an in-kind '
            'distribution on February 5. Two years earlier it borrowed to buy '
            'membership interests in the distributing holding company. No new '
            'loan financed this share distribution; replacing collateral did '
            'not create an additional loan or purchase of Orion shares.',
            'The share receipt is a noncash distribution; the earlier borrowing '
            'relates to acquisition of holding-company interests.',
            'A new loan financed Birch Trust\'s current acquisition of Orion shares.',
            'contradicted', 'historical_indirect_vs_current_financing',
        ),
        (
            'Aster Fund directly holds 500,000 Orion common shares, or 5% of '
            'the class. Alice Mercer controls the fund and reports deemed '
            'ownership of those same 500,000 shares. Their reporting group '
            'reports the same 5% aggregate. There are no additional shares '
            'in either Alice\'s report or the group total.',
            'The fund, controller and group reports overlap in the same 5% block.',
            'The fund and Alice together own distinct blocks totaling 10% of Orion.',
            'contradicted', 'overlapping_ownership',
        ),
        (
            'NorthStar states that its position on changing Orion voting rights '
            'is set out solely in an incorporated February 4 letter. This '
            'supplied record does not contain that letter, and neither the '
            'direction nor the current status of any request is described '
            'here. Its existing 6% common-stock ownership is separately reported.',
            'Current governance intent cannot be determined because the '
            'specifically relevant incorporated letter is unavailable.',
            'NorthStar currently requests abolition of Orion\'s classified board.',
            'insufficient_evidence', 'missing_referenced_objective',
        ),
        (
            'The agreement signed February 1 required delivery of the remaining '
            'holding-company assets as soon as practicable after February 7. '
            'An executed receipt in this filing confirms delivery on February '
            '8. The filing date is February 9. The agreement\'s earlier timetable '
            'has not been amended, and no additional delivery remains required.',
            'The delivery was completed by the February 9 filing date, according '
            'to the executed February 8 receipt.',
            'The same delivery remained pending on the February 9 filing date.',
            'contradicted', 'scheduled_date_vs_known_status',
        ),
        (
            'Aster Fund reports 7% of Orion common stock. Birch Fund separately '
            'reports a distinct 3% holding of the same class. The reporting '
            'persons do not control one another and neither attributes the '
            'other\'s shares to itself. Both bought their holdings before this '
            'filing; the purchase dates are not material to this ownership claim.',
            'Birch Fund reports a distinct 3% holding of Orion common stock.',
            'Birch Fund reports Aster\'s 7% holding as its own Orion ownership.',
            'contradicted', 'actor_attribution',
        ),
        (
            'On the disclosure date, Juniper Fund reports 750,000 Orion common '
            'shares out of 10,000,000 outstanding shares of that class. The '
            'cover page states 7.5%. A different preferred class has separate '
            'conversion provisions, but those instruments are not included in '
            'this stated common-share ownership percentage.',
            'Juniper Fund reports 7.5% of Orion common stock.',
            'Juniper Fund reports 75% of Orion common stock.',
            'contradicted', 'percentage_scale',
        ),
    ]
    rng = random.Random(SEED)
    rows = []
    for source, clean, changed, changed_verdict, error_type in pairs:
        for condition, statement, expected in [
            ('unchanged', clean, 'supported'),
            ('changed', changed, changed_verdict),
        ]:
            rows.append({
                'claim_id': f'K{rng.randrange(100000, 999999)}',
                'source': source, 'statement': statement,
                'condition': condition, 'expected_verdict': expected,
                'error_type': error_type,
            })
    if len({r['claim_id'] for r in rows}) != 16:
        raise ValueError('Opaque control IDs must be unique')
    rng.shuffle(rows)
    documents, claims, key = [], [], []
    for row in rows:
        did = 'FIXTURE-' + row['claim_id']
        documents.append(_document(did, row['source']))
        claims.append({
            'claim_id': row['claim_id'], 'kind': 'constructed_control',
            'value': {'statement': row['statement']},
            'candidate_evidence': [], 'source_document_id': did,
        })
        key.append({
            name: row[name] for name in
            ['claim_id', 'expected_verdict', 'condition', 'error_type']
        })
    return ({'accession': 'CONTROL-CRITIC-V3', 'documents': documents},
            {'claims': claims}, key)


def _funding(kind, certainty='confirmed_actual', link='current_acquisition'):
    return {'type': kind, 'certainty': certainty, 'acquisition_link': link}


def _owner(party, percent, role='direct_or_beneficial', overlap='not_stated'):
    return {'reporting_party': party, 'percent_of_class': percent,
            'ownership_role': role, 'overlap': overlap}


def inventory_controls():
    """Return eight source-only fixtures and narrowly scoped construction keys.

    Expected categories are complete for each short fixture. Funding/ownership
    requirements are selected exact tuples, not an exhaustive full-record gold
    answer. Optional ownership tuples are checked only if their named group is
    returned; omitting an explicitly disclosed group aggregate is allowed by the
    common rules. Only S02 marks its four-field ownership tuple set exhaustive:
    its two mandatory rows plus the optional group are the permitted tuples, and
    extra or duplicate tuples must be rejected by the parent matcher. Other
    fixtures retain partial ownership criteria. Forbidden tuples prevent specified false inferences;
    timing_forbidden applies to all transaction rows within that fixture.
    No natural data is used.
    """
    fixtures = [
        {
            'case_id': 'S01',
            'source': 'Aster Merger Fund reports 600,000 Orion common shares, '
            'or 6%, directly held and bought entirely with its own net assets. '
            'Aster has now signed an agreement to acquire all of Orion. At '
            'effectiveness the merger subsidiary directors and officers will '
            'succeed the incumbents, its charter will replace Orion\'s, and '
            'Orion will be delisted. Those provisions only implement the '
            'acquisition; Aster has made no separate board, management, '
            'governance or disclosure request.',
            'positive': ['sale_of_company'],
            'funding_requirements': [_funding('fund_net_assets')],
            'ownership_requirements': [_owner('Aster Merger Fund', 6)],
        },
        {
            'case_id': 'S02',
            'source': 'Aster Governance Fund directly owns 500,000 Vela common '
            'shares, 5%, bought with its working capital. Alice Mercer controls '
            'Aster and reports deemed ownership of that same block; the Aster '
            'reporting group also reports the same 5% aggregate. These are not '
            'three separate blocks. A negotiated right lets Aster nominate two '
            'directors annually while it retains the stake, and Aster states '
            'it will nominate both at the next meeting. In a separate letter '
            'Aster asks Vela to abolish its classified board. A former investor '
            'had sought a dividend in 2018; Aster does not adopt that request.',
            'positive': ['board_representation', 'governance_change'],
            'funding_requirements': [_funding('working_capital')],
            'ownership_exhaustive': True,
            'ownership_requirements': [
                _owner('Aster Governance Fund', 5, overlap='overlapping'),
                _owner('Alice Mercer', 5, 'deemed', 'overlapping'),
            ],
            'optional_ownership_requirements': [
                _owner('Aster reporting group', 5, 'group_aggregate', 'overlapping'),
            ],
        },
        {
            'case_id': 'S03',
            'source': 'Morgan Vale directly reports 800,000 Lyra common shares, '
            '8%, purchased using personal cash already held. Vale may use '
            'margin credit for future purchases but did not use it for this '
            'acquisition. In a current letter Vale asks Lyra to pay a special '
            'dividend and, as a separate action, use another cash reserve to '
            'retire $100 million of issuer debt. Vale\'s private margin '
            'facility is not a proposal to change Lyra\'s borrowing.',
            'positive': ['capital_return', 'capital_structure'],
            'funding_requirements': [
                _funding('personal_funds'),
                _funding('borrowed_funds', 'possible', 'future_possible'),
            ],
            'forbidden_funding': [_funding('borrowed_funds')],
            'ownership_requirements': [_owner('Morgan Vale', 8)],
        },
        {
            'case_id': 'S04',
            'source': 'Aster Asset Fund directly reports 700,000 Draco common '
            'shares, or 7%, acquired entirely from the fund\'s available net '
            'assets. Its current letter asks Draco to spin off the distribution '
            'subsidiary. A separate paragraph asks management '
            'to close two loss-making manufacturing plants in the retained '
            'business. The letter describes the shares as undervalued, but '
            'does not request a sale of Draco as a whole or a change of directors.',
            'positive': ['asset_transaction', 'operational_change'],
            'funding_requirements': [_funding('fund_net_assets')],
            'ownership_requirements': [_owner('Aster Asset Fund', 7)],
        },
        {
            'case_id': 'S05',
            'source': 'Juniper Fund directly reports 900,000 Cygnus common '
            'shares, 9%, bought using investor capital contributions received '
            'for that purchase. Juniper\'s current letter asks the board to '
            'replace the chief executive and appoint a successor through an '
            'external search. In another paragraph it asks Cygnus to publish '
            'existing correspondence and records of the last shareholder '
            'meeting. It requests disclosure of those records, without a '
            'change to voting rights, governance policy or board composition.',
            'positive': ['leadership_change', 'other_stated_objective'],
            'funding_requirements': [_funding('contributions')],
            'ownership_requirements': [_owner('Juniper Fund', 9)],
        },
        {
            'case_id': 'S06',
            'source': 'Birch Family Trust reports direct ownership of 1,800,000 '
            'Pegasus common shares, 18%, received on February 5 as an in-kind '
            'distribution from its holding company. Two years earlier Birch '
            'borrowed to acquire holding-company membership interests; no new '
            'loan funded the current share distribution. The holding company '
            'was liquidated, not Pegasus. Birch states no current request to '
            'change Pegasus\'s business, capital, leadership or governance '
            'and does not propose a sale or other action by Pegasus.',
            'positive': [],
            'funding_requirements': [
                _funding('noncash_distribution'),
                _funding('borrowed_funds', 'historical_indirect', 'historical_affiliate'),
            ],
            'forbidden_funding': [_funding('borrowed_funds')],
            'ownership_requirements': [_owner('Birch Family Trust', 18)],
        },
        {
            'case_id': 'S07',
            'source': 'Aster Timeline Trust reports direct ownership of 550,000 '
            'Aquila common shares, 5.5%. The filing date is February 9. The '
            'only transaction described here is a contractual requirement '
            'for its separate holding company to deliver its remaining cash and non-Aquila '
            'assets as soon as practicable after February 7, subject to '
            'retained reserves. No delivery receipt, completion update or '
            'statement that delivery remains outstanding is supplied. This '
            'arrangement concerns the holding company; no Aquila-directed '
            'proposal is stated.',
            'positive': [],
            'funding_requirements': [],
            'ownership_requirements': [_owner('Aster Timeline Trust', 5.5)],
            'timing_forbidden': ['pending_explicit', 'completed'],
        },
        {
            'case_id': 'S08',
            'source': 'NorthStar Fund directly reports 600,000 Taurus common '
            'shares, 6%, bought with working capital. NorthStar states that '
            'its position on changing Taurus voting rights is set out solely '
            'in an incorporated February 4 letter. This supplied record '
            'does not contain the letter, and neither the direction nor '
            'current status of any request is described here. The reference '
            'concerns voting arrangements only; no other current '
            'issuer-directed proposal is stated in the supplied text.',
            'positive': [],
            'unknown': ['governance_change'],
            'funding_requirements': [_funding('working_capital')],
            'ownership_requirements': [_owner('NorthStar Fund', 6)],
        },
    ]
    documents, keys = [], []
    for fixture in fixtures:
        cid = fixture['case_id']
        documents.append(_document(cid, fixture['source']))
        states = {name: 'not_stated' for name in CATEGORIES}
        states.update({name: 'present' for name in fixture['positive']})
        states.update({name: 'cannot_determine' for name in fixture.get('unknown', [])})
        keys.append({
            'case_id': cid, 'expected_intent': states,
            'funding_requirements': fixture['funding_requirements'],
            'ownership_requirements': fixture['ownership_requirements'],
            'optional_ownership_requirements': fixture.get('optional_ownership_requirements', []),
            'ownership_exhaustive': fixture.get('ownership_exhaustive', False),
            'permitted_ownership_tuples': (
                fixture['ownership_requirements'] + fixture.get('optional_ownership_requirements', [])
                if fixture.get('ownership_exhaustive', False) else []
            ),
            'forbidden_funding': fixture.get('forbidden_funding', []),
            'timing_forbidden': fixture.get('timing_forbidden', []),
        })
    # Fixed shuffled presentation; IDs reveal no expected labels. The fixture key
    # is parent-only and must never be supplied to the source-only reader.
    random.Random(SEED).shuffle(documents)
    return {'accession': 'CONTROL-INVENTORY-V3', 'documents': documents}, keys
