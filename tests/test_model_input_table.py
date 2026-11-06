"""Hand-pinned measurement and refusal cases for the model-input snapshot.
Inputs: constructed reader/critic facts, never natural outcomes or paid endpoints.
Outputs: pytest assertions. Identity: two readers yield frequencies in {0,.5,1}.
Tier: 1. Run project Python -m pytest tests/test_model_input_table.py.
"""
import pytest
from scripts.ml_experiment.build_model_input_table import objective_measurement, funding_measurement

TYPES=['borrowed_funds','working_capital']


def component(kind='working_capital', certainty='confirmed_actual', link='current_acquisition', actor='Fund A'):
    return {'actor':actor,'type':kind,'certainty':certainty,'acquisition_link':link}


def measurement(a,b,verdicts=None):
    verdicts=verdicts or {'funding.summary':'supported', **{f'funding.component.{i:03}':'supported' for i in range(1,len(a['components'])+1)}}
    return funding_measurement(a,b,verdicts,TYPES)


def test_objective_agreement_is_a_distribution_not_probability_claim():
    observed=objective_measurement('present','present','supported')
    assert observed['eligible']
    assert observed['state_frequency']=={'present':1.0,'not_stated':0.0,'cannot_determine':0.0}
    negative=objective_measurement('not_stated','not_stated','supported')
    assert negative['eligible'] and negative['state_frequency']['present']==0


@pytest.mark.parametrize('first,second,critic,reason',[
    ('present','not_stated','supported','reader_disagreement'),
    ('cannot_determine','cannot_determine','supported','shared_unknown'),
    ('present','present','insufficient_evidence','matching_nonunknown_without_critic_support'),
    ('not_stated','not_stated','contradicted','matching_nonunknown_without_critic_support'),
])
def test_uncertain_objective_is_withheld(first,second,critic,reason):
    row=objective_measurement(first,second,critic)
    assert not row['eligible'] and row['reason']==reason
    if first!=second: assert row['state_frequency'][first]==row['state_frequency'][second]==0.5


def test_possible_borrowing_does_not_become_actual_borrowing():
    # Both readers report actual working capital AND only possible margin loans.
    a={'status':'present','components':[component(),component('borrowed_funds','possible')]}
    result=measurement(a,a)
    assert result['eligible']
    assert result['features']=={'borrowed_funds':0.0,'working_capital':1.0}


def test_historical_financing_is_not_current_acquisition_financing():
    a={'status':'present','components':[component('borrowed_funds','historical_indirect','historical_affiliate')]}
    assert measurement(a,a)['features']['borrowed_funds']==0.0


def test_duplicate_components_do_not_double_count_readers():
    a={'status':'present','components':[component(),component()]}
    assert measurement(a,a)['features']['working_capital']==1.0


def test_qualifier_disagreement_retains_raw_half_but_blocks_model_value():
    a={'status':'present','components':[component('borrowed_funds')]}
    b={'status':'present','components':[component('borrowed_funds','possible')]}
    result=measurement(a,b)
    assert result['raw_frequencies']['borrowed_funds']==0.5
    assert not result['eligible'] and result['features']['borrowed_funds'] is None


def test_critic_flag_blocks_full_funding_vector_not_only_bad_component():
    a={'status':'present','components':[component(),component('borrowed_funds','possible')]}
    result=measurement(a,a,{'funding.summary':'supported','funding.component.001':'supported','funding.component.002':'insufficient_evidence'})
    assert not result['eligible'] and all(v is None for v in result['features'].values())


def test_unknown_link_cannot_create_qualified_zero():
    a={'status':'present','components':[component(link='unknown')]}
    result=measurement(a,a)
    assert result['features']['working_capital'] is None
    assert 'unresolved_component_qualifier' in result['reasons']


def test_not_stated_is_distinct_from_unknown():
    a={'status':'not_stated','components':[]}
    b={'status':'cannot_determine','components':[]}
    assert measurement(a,a)['features']['working_capital']==0.0
    assert measurement(b,b)['features']['working_capital'] is None


def test_missing_critic_claim_is_refused():
    a={'status':'present','components':[component()]}
    with pytest.raises(ValueError,match='coverage'):
        measurement(a,a,{'funding.summary':'supported'})
