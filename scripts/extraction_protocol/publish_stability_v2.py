"""Publish a dated learning checkpoint for the completed revised extraction.

Inputs: verified v2 metrics, before/after calculations and verification receipt.
Outputs: explanatory Markdown and active project navigation; frozen runs unchanged.
Identity: displayed counts and percentages derive from the verified saved counts.
Tier: 1. Run project Python with PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8.
"""
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'research/runs/extraction-stability/20261025-v2'


def main():
    metrics=json.loads((RUN/'metrics.json').read_text())
    change=json.loads((RUN/'before-after.json').read_text())
    checks=json.loads((RUN/'verification.json').read_text())
    n,d=change['v2_threeway_equal'],change['v2_threeway_cells']
    mn,md=change['v2_same_old_subset_equal'],change['v2_same_old_subset_cells']
    full=change['v2_complete_claim_records']
    delivered=change['v2_mechanical_full_delivery_records']
    assert checks['finalized_records']==30 and d==90 and md==63
    assert checks['independent_full_delivery_records']==delivered
    assert metrics['equal_threeway_intent_cells']==n
    disagreements=d-n
    note=f'''# Extraction revision: coverage, definitions and the retest

October 26, 2026. The revised experiment began October 25. Development evidence on the same ten discovery filings; no human-reference accuracy or investment-ranking result.

The question is whether filing information can be measured consistently before using it to rank investments. We improved the reading procedure and clarified three interpretation boundaries, then reran the same ten sources with three fresh contexts per filing. Human review remains waived for these ten discovery cases at Jeff's explicit direction. The ten reserved validation sources were not supplied.

## What changed and why

1. **One filing per context.** Thirty bounded jobs replace three agents carrying all ten filings. This addresses the context-budget failures on long documents.
2. **Logged source coverage.** Readable text is served in chunks of up to 16,000 Unicode characters. The finalizer checks the union of delivered ranges and refuses a complete-review claim with gaps. A separate verifier reconstructs coverage independently. This verifies delivered text; comprehension and completeness of material exhibits remain separate questions.
3. **Transaction facts separate from objectives.** A subscription or financing closing is preserved as information without automatically becoming a capital-structure objective. An attributable request or plan to change issuer financing can still qualify as intent.
4. **Clearer category boundaries.** Disclosure of existing correspondence is distinguished from a governance-policy change. A materially missing reference can require cannot_determine for its implicated category. The schema prevents an agent from declaring a material gap while simultaneously using not_stated for that category.

## Before and after

| Measure | Original | Revised |
| --- | --- | --- |
| Finalized records | 30/30 | 30/30 |
| Claimed complete readable-source reviews | 24/30 | {full}/30 |
| Independently checked full-delivery records | Not logged in v1 | {delivered}/30 |
| Three-agent intent agreement, all ten filings | 69/90 (76.7%) | {n}/{d} ({100*n/d:.1f}%) |
| Same original seven full-review filings | 59/63 (93.7%) | {mn}/{md} ({100*mn/md:.1f}%) |

There are {disagreements} remaining category-state disagreements out of ninety filing/category cells. A cell is one objective category for one filing; the ninety cells are related within filings and are not ninety independent trials. All nine categories agree on {metrics['all_nine_labels_equal_filings']}/10 filings. The full report includes positive-objective Jaccard, category frequencies, facts, uncertainty and source-backed disagreement detail.

The same-seven comparison keeps the case IDs constant. The all-ten comparison also reflects the removal or persistence of long-source review failures. Both the context design and category rules changed after the first development run, so these results do not isolate either change's effect. Higher consistency is not evidence of higher semantic accuracy.

## Verification and limits

The independent check reconciles {checks['exact_citation_entries']} cited entries and {checks['served_unique_unicode_characters']:,}/{checks['expected_readable_unicode_characters']:,} delivered readable Unicode characters across the thirty jobs. All {checks['original_v1_files_preserved']} original-run files, the existing source-only packs and {checks['protected_paths_preserved']} protected paths remain unchanged. Fixed source, prompt, schema and implementation hashes accompany the run. Synthetic tests cover citation anchoring, overlap/gap accounting and uncertainty refusal. Local browser automation remains unavailable for file URLs; static report links are checked offline.

Delivery coverage and exact quotation are mechanical checks, not proof of correct interpretation. Unreadable binaries, unavailable referenced agreements and ambiguous attribution still need explicit treatment. The ten cases were deliberately selected and are already model-exposed development examples. Same-model contexts can share mistakes. No accuracy reference, calibrated truth probabilities, causal finding or investment edge is established.

## Next decision

Inspect the remaining disagreements and decide whether to freeze the revised extraction procedure for a separate reserved-case check. Keep the ten reserved cases unexposed until the check and its purpose are specified. No further rule tuning should use those cases while calling them untouched validation.

This work improves measurement and traceability. It has not trained a new investment model. Bloomberg historical availability/mapping and the financial-only versus LLM-only versus combined ranking comparison remain separate pending tasks. No paid API calls, financial downloads or return recomputations were made.

Readable report: `/Users/jefflu/Projects/activist-13d/research/runs/extraction-stability/20261025-v2/index.html`.

[Open revised results](../../runs/extraction-stability/20261025-v2/index.html) · [Preserved first results](../../runs/extraction-stability/20261025-v1/index.html).
'''
    note_path=ROOT/'research/docs/ranking-direction-20261025/extraction-revision-20261026.md'
    if note_path.exists() and note_path.read_text()!=note:
        raise ValueError('Preserve differing dated checkpoint')
    note_path.write_text(note)
    start=ROOT/'START-HERE.html'
    text=start.read_text()
    marker='<!-- extraction-stability-v2-current -->'
    section=f'''{marker}<section><h2>Current: revised extraction tested — October 26</h2><p>The reading workflow now gives each filing a fresh agent context and logs every delivered text range. The coding rules separate routine financing facts from stated objectives and make missing-evidence uncertainty explicit.</p><a class="button" href="research/runs/extraction-stability/20261025-v2/index.html">Revised extraction results</a><a href="research/docs/ranking-direction-20261025/extraction-revision-20261026.md">What changed, what the numbers mean, and next decision</a><p>Complete readable-review records: {full}/30; full mechanical delivery: {delivered}/30. Three-way intent agreement is {n}/{d} ({100*n/d:.1f}%) across all ten filings, and {mn}/{md} ({100*mn/md:.1f}%) on the original seven comparable cases. Agreement is repeatability, not accuracy. The reserved validation cases remain unexposed by this run, and the first experiment is preserved.</p></section>'''
    if marker not in text:
        text=text.replace('</style></head><body><main>','</style></head><body><main>\n'+section,1)
        text=text.replace('<h2>Current step: three-agent extraction consistency results</h2>','<h2>Preserved first run: three-agent extraction consistency</h2>')
        text=text.replace('<h2>Current step: start with one independent filing reading</h2>','<h2>Preserved source-only discovery pack</h2>')
        start.write_text(text)
    plan=ROOT/'research/docs/PROJECT-PLAN.md'
    text=plan.read_text()
    heading='## Revised extraction completed — October 26, 2026'
    if heading not in text:
        insertion=f'''{heading}

The [revised extraction report](../runs/extraction-stability/20261025-v2/index.html)
and [learning checkpoint](ranking-direction-20261025/extraction-revision-20261026.md)
record thirty fresh one-filing contexts, mechanical delivery logs, separate
transaction facts and refined intent/evidence rules. Complete readable review is
claimed for {full}/30 records and mechanical delivery passes for {delivered}/30.
Three-agent intent agreement is {n}/{d} ({100*n/d:.1f}%) across the same ten
discovery filings; on the original seven it is {mn}/{md} ({100*mn/md:.1f}%).
These are post-development repeatability results, not accuracy validation. The
original run and human packs are preserved. No reserved validation sources, new
financial data or predictive fitting were used. Next inspect the remaining
disagreements and freeze a procedure before specifying a separate reserved-case
check. Financial information timing/mapping and downstream ranking remain pending.

'''
        text=text.replace('# Activist 13D Machine Learning Class Project Plan\n\n','# Activist 13D Machine Learning Class Project Plan\n\n'+insertion,1)
        plan.write_text(text)
    cp=ROOT/'research/docs/ml-checkpoints.html'
    text=cp.read_text()
    marker='<!-- extraction-stability-v2-checkpoint -->'
    if marker not in text:
        text=re.sub(r'(<body><main><h1>13D machine learning learning checkpoints</h1>)<p>Updated.*?</p>',r'\1<p>Updated October 26, 2026 | Revised extraction coverage and consistency retest complete; no accuracy reference or new investment result</p>',text,count=1)
        text=text.replace('<section class="current">','<section class="history">',1)
        section=f'''{marker}<section class="current"><h2>Current checkpoint: improve measurement before modeling</h2><p>The revised extraction uses one filing per context and logged source ranges, with clearer transaction/objective and evidence-gap rules. Complete readable review is claimed for {full}/30 records; mechanical full delivery passes for {delivered}/30. Three-way agreement is {n}/{d} ({100*n/d:.1f}%) across all ten filings and {mn}/{md} ({100*mn/md:.1f}%) on the original seven.</p><p><a href="../runs/extraction-stability/20261025-v2/index.html">Revised results, source evidence and before/after comparison</a> · <a href="ranking-direction-20261025/extraction-revision-20261026.md">What changed and how to interpret it</a></p><p>Learn why complete source delivery differs from correct interpretation, and why changing rules after development does not create fresh validation. Inspect remaining disagreements before freezing a separate reserved-case check. Financial-data timing and the ranking model remain pending.</p></section>'''
        text=text.replace('<section class="history">',section+'\n<section class="history">',1)
        cp.write_text(text)
    print(json.dumps({'checkpoint':str(note_path),'intent_agreement':f'{n}/{d}',
                      'matched_original_seven':f'{mn}/{md}','full_delivery':delivered},indent=2))


if __name__=='__main__':
    main()
