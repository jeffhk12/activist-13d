"""Predicting activist campaign duration and outcome from disclosed intent.

Pipeline stages, in dependency order:

    edgar/      enumerate, fetch and parse Schedule 13D filings
    dates       disclosure delay — Q2's treatment variable
    crosswalk   CIK / CUSIP -> PERMNO, with a reported match rate
    outcomes    the five competing terminal states
    extract/    LLM intent extraction, multi-provider, cached
    survival    competing-risks duration models
    causal      heterogeneous treatment effects
    sizing      the decision-focused position-sizing layer
    validation/ purged splits and evaluation metrics

Tier: 0
"""

__version__ = "0.1.0"
