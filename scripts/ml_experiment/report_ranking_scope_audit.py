"""Render internal reports for the October 25 ranking-scope audit.

Inputs: immutable audit JSON/manifest and incoming user handoff.
Outputs: requested reports/data_inventory.md, reports/data_quality_audit.md,
pilot proposal and preserved direction note. No dataset or model writes.
Identity: displayed counts equal audit counts; coverage=100*present/rows.
Tier: 1. Run with project Python and PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8:
 .venv/bin/python scripts/ml_experiment/report_ranking_scope_audit.py [--verify]
"""

import argparse
import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'research/runs/ranking-scope-audit/20261025-v2'
DOC = ROOT / 'research/docs/ranking-direction-20261025'


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |',
                      '| ' + ' | '.join('---' for _ in headers) + ' |',
                      *['| ' + ' | '.join(str(v).replace('|', '\\|').replace('\n', ' ') for v in row) + ' |' for row in rows]])


def build():
    a = json.loads((RUN / 'audit.json').read_text())
    inputs = json.loads((RUN / 'source-manifest.json').read_text())
    p, b = a['panel'], a['bloomberg']
    handoff = Path('/Users/jefflu/Downloads/13D_Codex_Handoff_2026-10-25.md')
    assert hashlib.sha256(handoff.read_bytes()).hexdigest() == inputs[str(handoff)]['sha256']
    sources = json.loads((RUN / 'filing-source-audit.json').read_text())
    inventory_rows = [
        ('User decisions', str(DOC.relative_to(ROOT) / handoff.name), 'Exact preserved copy', 'Planning scope confirmed; new modeling protocol still to be specified.'),
        ('Feature table', 'research/runs/ml-feature-preview/20261012-v1/features.jsonl', f'{p["rows"]} rows; 10 source fields', 'Old deterministic SEC/history/size features; not the new financial-only feature set.'),
        ('Event identities/dates', 'research/runs/ml-feature-preview/20261012-v1/row-metadata.jsonl', f'{p["distinct_accessions"]} accessions; {p["distinct_issuers"]} issuers; {p["distinct_securities_permno"]} securities', 'Stable event ID, acceptance time, entry, security, and diagnostic groups.'),
        ('Prepared target', 'research/runs/ml-feature-preview/20261012-v1/targets.jsonl', '667 two-year targets', 'Exact parity to frozen 504-session outcomes checked.'),
        ('Original filing sources', 'data/raw/edgar/bulk-v1/filings/ACCESSION/submission.txt', '667 linked files rehashed', 'Exact per-event paths and SEC URLs in filing-source-audit.json.'),
        ('Canonical texts', 'research/runs/phase2-overnight/20260924-full-v1/bundles/ACCESSION.json.gz', '667 linked bundles verified', 'Document text, hashes, accession and source URL; unreadable exhibits remain explicit.'),
        ('Mechanical extracted facts', 'research/runs/phase2-overnight/20260924-full-v1/facts/ACCESSION.json.gz', '667 records verified against receipts and citations', 'Item 3/4/5 spans and separate reporting persons; semantic completeness unverified.'),
        ('Factual selection', 'research/runs/phase2-overnight/20260924-full-v1/selection.json', '15,813 selected records in saved file', 'Separate preparation population; not a successive step from 667.'),
        ('Historical benchmark assignments', 'research/runs/phase1-baseline/20260924-long-horizon-inputs-v1/assignments.json', '667 panel assignments agree on stock identifier', 'Frozen historical snapshot/ETF assignments, not Bloomberg ticker certification.'),
        ('Stock-price/daily-return input', 'research/runs/phase1-baseline/20260924-long-horizon-inputs-v1/panel.json', f'{inputs["research/runs/phase1-baseline/20260924-long-horizon-inputs-v1/panel.json"]["bytes"]:,} bytes; SHA-256 recorded', 'Input located and fingerprinted. Full daily vendor coverage/accounting not reaudited.'),
        ('Horizon outcomes', 'research/runs/phase1-baseline/20260924-long-horizon-analysis-v1/outcomes.json', '252/378/504/756-session schedules', 'First-observed and standalone branches; audit uses exact first-observed event joins.'),
        ('Bloomberg workbook', b['path'], f'{b["event_rows"]} matched saved event rows; 4 sheets', 'Original caches read from OOXML without editing, refreshing, or recalculating.'),
        ('Bloomberg request list', 'research/runs/bloomberg-extraction-handoff/20261017-v2/event_requests.csv', '667 exact request IDs', 'Contains requested cutoff and unverified ticker seeds.'),
        ('Baseline predictions', 'research/runs/ml-baselines/20261015-v1/predictions.jsonl', 'Saved first comparison', 'Historical development output, preserved.'),
        ('Nonlinear predictions', 'research/runs/ml-nonlinear/20261019-windows-v1/predictions.jsonl', 'Saved model/seed forecasts', 'Historical development output, preserved.'),
        ('Scored predictions', 'research/runs/ml-nonlinear/20261019-windows-v1/scored-events.csv', '3,624 event/model rows from prior report', '302 investment events repeated over model outputs; not 3,624 independent events.'),
        ('Ranking results', 'research/runs/ml-nonlinear/20261019-windows-v1/evaluation.json', 'Spearman saved for 2021, 2022, 2023', 'Confirms ranking already tested under the old input/target specification.'),
    ]
    inventory = f'''# 13D data inventory for the revised ranking project

Decision date and audit: October 25, 2026. Internal preparation, no new model fitting.

The revised question is whether LLM-extracted information from initial 13D filings improves later investment ranking beyond financial features. The existing research can supply source texts and horizon outcomes. It does not yet supply a point-in-time-certified financial feature set or validated LLM features for the new comparison.

## Located files and counts

Paths are relative to `/Users/jefflu/Projects/activist-13d` unless absolute.

{table(['Role', 'Actual path', 'Observed coverage', 'Meaning and limits'], inventory_rows)}

## Scope and reconciliation

- Current panel: {p['rows']} rows and distinct event IDs, {p['distinct_accessions']} distinct accessions, {p['distinct_issuers']} issuers, and {p['distinct_securities_permno']} stock database identifiers. Duplicate event IDs: {p['duplicate_rows']}.
- Entries span 2018–2023. Annual counts: {', '.join(f'{k}: {v}' for k,v in p['entry_year_counts'].items())}.
- All {p['rows']} saved SEC header forms read SC 13D, and acceptance dates precede their entry dates. Header form does not independently validate first activism or exclude every substantively amended disclosure.
- The larger approximately 75,000-record archive was not rehashed or reparsed in full. This is a fresh direct audit of the linked 667-panel evidence and saved return schedules. Earlier archive/preparation counts retain their distinct scope.
- The incoming handoff correctly asks us to verify old results. Saved evaluation files confirm that within-year ranking was already measured. The prior negative ranking evidence remains visible.
- The old model's structured SEC/history inputs are not interchangeable with the new financial-only comparison A. New A/B/C input membership and eligibility need an explicit protocol.

## Reproduce and inspect

Machine-readable evidence: `research/runs/ranking-scope-audit/20261025-v2/audit.json`, `filing-source-audit.json`, `event-coverage.csv`, and `source-manifest.json`. The first bounded audit is preserved in v1; v2 adds range checks and exact Bloomberg request checks. Sources, per-filing evidence and the audit code have SHA-256 records.

```sh
PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/ml_experiment/audit_ranking_scope.py --output research/runs/ranking-scope-audit/20261025-v2 --verify
```

See [data quality and blocker list](data_quality_audit.md) and [proposed 10+10 filing pilot](filing_pilot_plan.md).
'''
    feature_rows = [(name, d['present'], p['rows'] - d['present'], f'{d["coverage_pct"]:.1f}%', d['mechanical_range_or_type_flags']) for name,d in a['structured_field_coverage'].items()]
    bbg_rows = [(name, d['finite'], d['missing_or_nonnumeric'], f'{d["coverage_pct"]:.1f}%', d['zero'], d['negative']) for name,d in b['field_coverage'].items()]
    horizon_rows = [(h['months_approx'], h['all_scheduled_first_observed_events'], h['all_calculable_common_labels'], h['all_valid_single_filing_labels'], h['exact_valid_labels_within_667'], h['with_nine_numeric_bbg_fields_unverified']) for h in a['horizons'].values()]
    horizon_status = '\n'.join(f'- {h["months_approx"]} months, within current panel: `{h["within_667_join_status"]}`.' for h in a['horizons'].values())
    fold_rows = [(h['months_approx'], f['prediction_year'], f['completed_training_events'], f['later_entries'], f['shared_issuers']) for h in a['horizons'].values() for f in h['annual_folds'] if f['later_entries'] > 0]
    ranking_rows = [(model, *[f'{a["prior_within_year_spearman_verified_from_saved_file"][str(y)][model]:.3f}' for y in [2021,2022,2023]]) for model in ['ridge','neural_ensemble','tree','forest','boosting']]
    gap_rows = [(s['accession'], s['source_path']) for s in sources if s['item4_spans'] == 0]
    year_bbg = [(year, p['entry_year_counts'][year], *[b['field_coverage'][f]['by_entry_year'][year]['finite'] for f in ['bs_tot_asset','SALES_REV_TURN','EBITDA']]) for year in p['entry_year_counts']]
    quality = f'''# 13D data quality audit and priorities

October 25, 2026. Offline evidence audit; no extraction model, refitting, source edits, or new investment returns.

## Investment-research takeaway

The revised financial-versus-LLM ranking study has a usable source-evidence foundation, but its final comparable sample is not established. Source files and saved return labels are traceable. Bloomberg values are substantially populated yet their historical publication dates, revisions, and security mapping remain unresolved. Text coverage is sufficient to design a small pilot; it does not certify that all relevant exhibits are supplied.

## 1. Event identity, filing text, and timing

- {p['rows']} rows; {p['distinct_accessions']} distinct initial-header accessions; {p['distinct_issuers']} issuers; {p['distinct_securities_permno']} stock IDs; {p['duplicate_rows']} duplicate event IDs. Feature/metadata/target key sets agree exactly.
- Raw files, compressed facts/bundles, canonical text hashes, source receipt links, and exact cited substrings pass for all {p['rows']} linked filings. Each source URL is present. This establishes provenance and citation integrity, not semantic accuracy.
- The parser locates Item 3 in {p['item3_candidate_span_events']}/{p['rows']}, Item 4 in {p['item4_candidate_span_events']}/{p['rows']}, and Item 5 in {p['item5_candidate_span_events']}/{p['rows']}. Missing spans need source inspection, not negative intent labels.
- {p['events_with_unresolved_references']}/{p['rows']} events contain at least one mechanically unresolved exhibit/reference. Some necessary evidence may already be embedded, and some references may be immaterial. Materiality/completeness needs review per selected case. These are not automatic exclusions.
- {p['acceptance_after_1600_et']}/{p['rows']} acceptance timestamps are later than 16:00 ET. All acceptance dates precede entry; the existing convention uses the opening of the second exchange session after public acceptance. The delay avoids same-day execution but this audit does not reconstruct exchange calendars or certify each trade's execution.
- Frozen assignments agree with panel stock identifiers in all {p['rows']} events. Assigned ETF counts: `{p['benchmark_etf_counts']}`. Agreement between saved files does not independently validate Bloomberg ticker reuse, merger history, or all corporate eligibility.
- Ownership/security parsing: `{p['ownership_security_status_counts']}`. The 14 unresolved cases remain explicitly uncertain.

Item 4 candidate-span gaps:

{table(['Accession', 'Raw source for inspection'], gap_rows)}

## 2. Existing structured fields

{table(['Field', 'Present', 'Missing', 'Coverage / 667', 'Type/range flags'], feature_rows)}

Mechanical flags apply source-field rules: finite/nonnegative counts, positive security cap, ownership percentage 0–100 and ownership-coverage fraction 0–1. Passing these checks does not validate meaning. Full per-year and per-industry counts, numerical minima/maxima, and original missingness are retained in `audit.json`.

## 3. Bloomberg: present values versus historically usable values

The workbook is byte-identical to the October 18 audited original, with SHA-256 `{b['source_sha256']}`. Its 667 raw event IDs and saved cutoff/ticker seeds match the request list. Unknown raw event IDs: {len(b['unknown_raw_event_ids'])}; duplicate raw IDs: {b['raw_event_id_duplicate_count']}; cutoff disagreements: {len(b['request_cutoff_mismatches'])}; ticker-seed disagreements: {len(b['request_ticker_seed_mismatches'])}. Matching a seed is not external validation of that seed.

{table(['Raw field', 'Finite', 'Missing/error', 'Coverage / 667', 'Zero', 'Negative'], bbg_rows)}

Nine numeric fields are present for **587/667 (88.0%)** events; 57/667 are partial and 23/667 have none. Vendor errors such as #N/A remain missing/error states rather than becoming zero. Negative equity, profits, or cash flows can be economically valid; signs are descriptive flags, not automatic errors or exclusions.

Selected completeness by entry year, not a temporal validation result:

{table(['Entry year', 'Rows', 'Assets finite', 'Revenue finite', 'EBITDA finite'], year_bbg)}

Full year/industry missingness for every field is in `audit.json`; broad distributions can be inspected before choosing imputation or exclusions. Imputation cannot repair an unknown historical publication date.

The saved debt-ratio divisor is {b['debt_ratio_divisor_saved_assumption']}. Derived-debt cache disagreements under that assumption: {len(b['debt_arithmetic_disagreements_under_saved_assumption'])}. This checks assets × ratio / saved divisor, not the vendor ratio definition or actual dollar-debt accuracy. Field definitions and percentage scale still need independent confirmation.

**Historical availability remains unresolved.** The workbook's fiscal-period rule is event calendar year minus one. It does not supply event-level release-date and revision-vintage evidence. The existing BHE row uses a January 3, 2019 cutoff and FY2018 values; the preserved company-announcement record is dated February 7, 2019. That is a concrete conflict requiring correction/recollection or documented exclusion before use. The saved record does not establish every individual field's publication history. No new external query was made in this audit.

The workbook labels financial amounts USD, but original returned currency/scale metadata and field-level period definitions are not independently certified. Operating income is not silently equated with EBIT. Book equity may be negative. Debt and profitability ratios require appropriate denominators and sector interpretation. Prior-year revenue, operating cash flow, and consolidated company market cap remain absent; the new direction explicitly avoids a large default extraction. Decide only the minimum additional checks/fields needed for the chosen financial comparison.

**The number of verified point-in-time financial-feature rows is not established.** This is not a claim that no financial information existed historically. It means the present evidence cannot certify which rows were knowable on time.

## 4. Horizon labels, exact identity, and comparable samples

Existing labels use 252/504/756 exchange sessions as approximate 12/24/36-month horizons. The revised protocol still needs to confirm these conventions, benchmark assignment, and endpoint rules. These rows are candidates, not independent campaigns.

{table(['Approx months', 'All scheduled', 'All calculable labels', 'All single-filing labels', 'Exact valid within 667', 'Also 9 numeric BBG, unverified'], horizon_rows)}

The broader scheduled and single-filing counts are inventory counts, not additional feature-ready samples. Exact within-panel joins require the same source event key, accession, issuer, security, entry date and single-filing identity. Schedules were independently formed by horizon under inherited non-overlap rules. We refuse issuer-only or first-match joins.

{horizon_status}

- Common 12/24-month exact events: **{a['common_samples']['12_24_exact_event_rows']}**; of these, **{a['common_samples']['12_24_with_nine_numeric_bbg_unverified']}** also have nine numeric Bloomberg fields.
- Common 12/24/36-month exact events: **{a['common_samples']['12_24_36_exact_event_rows']}**; **{a['common_samples']['all_horizons_with_nine_numeric_bbg_unverified']}** also have nine numeric Bloomberg fields.
- These completeness intersections are not required complete-case selection rules. Missingness treatment should be specified after validity checks.
- Financial-only versus LLM-only versus combined **model-ready common-sample counts are not established**, because financial availability and validated text-feature eligibility are unresolved.

No new returns were computed. The 667 stored two-year targets exactly match the inherited outcomes. Return handling, dividends, delisting refusal states, and missing-price behavior are inherited from frozen Phase 1 conventions, rather than independently revalidated in this audit. Earlier Aratana settlement accounting remains an open issue for funded-account work; it should not be silently converted into a simple cash liquidation or a certified complete portfolio result. Corporate actions for any newly selected target rows require explicit review before final modeling eligibility.

## 5. Chronological outcome-maturity counts

Training below requires entry and horizon-specific scheduled outcome end strictly before January 1. Later rows enter during that year. Counts are availability checks; repeated issuers and overlapping market windows prevent treating these as independent trials.

{table(['Approx months', 'Prediction year', 'Completed training', 'Later events', 'Shared issuers'], fold_rows)}

Inner tuning folds and uncertainty calculations are not frozen. A valid chronological design requires completed outcomes at every tuning origin, training-only preprocessing, specified treatment of shared entities/outcome overlap, and a declared finite model/settings budget. A random row split is not an acceptable substitute. Horizon-specific evaluations and matched cross-horizon comparisons both belong in the next protocol.

All existing outcomes were exposed in earlier research. Later predictions can be out of the fitted training sample while the research exercise remains development evidence. A new report title or metric cannot make these years untouched. Identify any truly unexposed or future evaluation separately, or label the final comparison as chronological development evidence.

## 6. Prior ranking evidence already exists

Verified directly from the saved nonlinear evaluation file:

{table(['Old model / old inputs / 24 months', '2021 Spearman', '2022', '2023'], ranking_rows)}

These are descriptive within-year rank correlations on 106, 110, and 86 events respectively. The new study's financial-versus-LLM feature comparisons have not been run. Constant zero/mean forecasts have tied ranks and undefined Spearman, not zero rank correlation. A naive financial ranking rule needs its own predeclared definition if used. Quintile boundaries, tied predictions, thin groups, and dependency-aware uncertainty also require definitions before evaluation; three annual points are insufficient for strong temporal-stability claims.

## 7. Prioritized blockers and smallest next action

1. **Financial information timing and identity:** validate a bounded set of historical mappings, release dates, field definitions, units and revisions. Preserve the workbook. Establish an inclusion rule before declaring a financial sample ready.
2. **Initial filing and evidence completeness:** review the proposed pilot's actual bodies/embedded exhibits and Item 4 gaps. A header marked initial does not prove a new campaign.
3. **Human-first extraction evaluation:** independent reference judgments precede model answers. Use about ten discovery filings and about ten separate validation filings; report the small evaluation's uncertainty and category support.
4. **New horizon/sample/validation contract:** confirm benchmark, session approximations, issuer non-overlap, as-of decision time, matched feature-set samples, annual/inner folds, ties/quintiles, finite search budget and exposed-history labels.
5. **Uncertainty and interpretation:** choose a design appropriate for overlapping outcomes and repeated entities, without implying that ordinary independent-row confidence intervals are valid.

The immediately reviewable next action is the [10+10 filing pilot proposal](filing_pilot_plan.md), alongside a bounded financial-data remediation check. The incoming handoff requests review of the audit and pilot plan before full extraction or retraining. Neither has been launched.

## Evidence and limits

Evidence directory: `research/runs/ranking-scope-audit/20261025-v2/`. The audit script includes hand-computed coverage, duplicate-refusal, exact-join, and vendor-error checks; `--verify` replays generated audit bytes. This is a targeted offline inventory/quality audit, not a new legal assessment, vendor-completeness certification, complete daily-price audit, validated semantic extraction, or evaluated investment strategy.
'''
    pilot = '''# Proposed filing discovery and validation pilot

October 25, 2026. Proposed for review. No sample selected, new extraction judgments generated, paid calls made, or models retrained.

## Question and size

Which small set of source-supported filing features can be measured consistently and might add information beyond financial inputs when ranking later investments? Begin with ten distinct-issuer initial filing candidates for discovery and approximately ten different candidates for validation. This is schema discovery and feasibility work, not a return screen or a statistically precise population-accuracy study.

## Selection before reading future outcomes

Use source metadata and mechanical document characteristics, with a recorded deterministic seed/order. Seek coverage of earlier/later entry years, several industries, reporting-party complexity, HTML/text or exhibit-heavy layouts, and parser/evidence gaps. Investor-type strata can be used only as explicitly unverified candidate groups unless independent identity validation exists. Preserve all protected review exclusions and human answers. Do not select examples by future returns or the best-known successful campaigns.

The initial 667-panel membership already reflects historical market-data/label coverage. A pilot within it is a selected development sample; disclose that inherited selection. Freeze the 20-case identity list and discovery/validation division before interpretation. Keep the validation cases separate from schema/prompt development; conservatively check issuer/reporting-party overlap and document prior exposure. Do not promise an untouched investment test from these cases.

## Discovery: ten cases

For each case, provide the original filing, same-accession canonical text, accession/acceptance time, source hash, document inventory, and embedded exhibits. Inspect Items 3, 4, and 5 as needed. Check body versus header initial/amendment clues; mark unresolved evidence rather than substituting later amendments or remembered campaign history.

Have Jeff record independent source-based observations and uncertainties before model answers for the same examples are shown. Store source passages and actor/target attribution. Preserve existing codebooks and validators; inventory reusable fields before proposing a new version. The current categories-v1 source, generated prompt/schema, and ownership/identity pilot are existing assets, not permission to overwrite them.

For each candidate feature, record source availability, deterministic versus interpretive construction, ambiguity, likely economic relevance, and overlap with financial or mechanical SEC inputs. Assess incremental information conceptually; no future outcome is used to choose categories.

Aim for a small schema: separate ownership facts and overlap; source-of-funds facts; governance/board objectives; operating/capital-allocation objectives; transaction objectives; and disclosure/evidence characteristics. These are candidate groups for inspection, not labels already assigned or a frozen final taxonomy.

## Draft schema shape for review

Each record should identify accession, source/canonical hashes, disclosure-time scope, schema/prompt version, model/settings where actually known, timestamp, and evidence inventory. Each interpretive feature needs actor, target, value(s), explicit state, and exact supporting document/Unicode-span references. Allow multiple objectives when supported.

Distinguish supported/present, not stated after adequate review, and cannot determine because of unavailable evidence or ambiguity. Preserve the existing workflow's distinctions when mapping user shorthand such as unknown/not_disclosed. A missing parser span never becomes a negative semantic label. Keep overlapping reporting-person ownership separate. Model confidence or repeated-label frequencies do not become calibrated truth probabilities.

## Validation: approximately ten separate cases

Freeze the candidate schema and prompt before model interpretation of validation cases. Record human references independently and freeze their bytes before model answers are generated or shown. Verify schema/provenance, canonical hashes, exact quotes, and actor/target attribution. Then compare semantics to the references, preserving disagreements and dated adjudications.

Report category-level supported positives, false positives/negatives where the reference is determinate, abstentions, source gaps, and claim/citation errors. Denominators matter: ten files need not supply ten examples of every objective. A category with no adequate positive evidence remains unevaluated; a small case count cannot certify population accuracy. If repeat runs are feasible under authorized access, report stability separately from accuracy. Paid APIs stay off unless separately authorized.

If the schema changes after seeing validation errors, those cases become development material for the revision. A new validation sample/protocol is needed for any later unexposed extraction claim.

## Deliverables before scaling

- Frozen sample manifest with source identities, strata, protection/exposure checks and split rationale.
- Source-only human packets with blank answers and source/canonical evidence; no suggested model labels or future returns.
- Completed independent human reference exports with evidence and timestamps.
- Proposed minimal versioned schema/codebook/prompt, category reasons and limitations.
- Model outputs, exact inputs, citations and available run metadata when execution is authorized.
- A small validation report, category support counts, errors, unresolved cases and a recommendation on whether to revise, stop, or scale a narrow supported subset.

## Decisions to review now

Confirm the ten-plus-ten design, availability of human review time, and the bounded financial-data check. Then finalize selection and the evidence packet. The initial next action can be entirely local and source-only; full batch extraction, new return calculation, and model retraining wait for the requested audit/pilot review.

After that review, a new modeling protocol should compare A financial-only, B validated LLM filing features, and C combined inputs on matched eligible events and chronological folds. Keep 12 and 24 months co-primary, 36 months exploratory, Spearman primary, quintile/spread/stability analyses supporting. Predeclare tied-rank handling and uncertainty; constants have undefined rank correlation. Preserve the old SEC-only/neural results as development history.
'''
    direction = '''# Confirmed 13D research direction received October 25, 2026

The user supplied 13D_Codex_Handoff_2026-10-25.md from Downloads and asked to continue with the new decisions. Its exact bytes are preserved beside this note. These planning decisions supersede the earlier priority of neural-network training diagnosis; frozen prior experiments remain unchanged.

The central question is whether LLM-extracted initial-filing information improves chronological ranking of later excess returns beyond conventional financial features. Twelve- and 24-month returns are co-primary; 36 months is secondary if feasible. Primary evaluation is Spearman by horizon. Supporting analyses are predicted quintiles, top-minus-bottom spread, temporal stability, sample counts and appropriate uncertainty. Compare financial-only, LLM-only and combined features under matched samples, dates and algorithms. Use simple references, ridge and constrained trees first. Neural-network revisiting is optional within the 4–5 week course window.

The workflow begins with inventory and data quality, then roughly ten discovery and ten separate validation filings. It defers dynamic rebalancing, amendment/ownership-change signals, regime models, causal attribution and a full valuation engine. No large default Bloomberg extraction is requested.

The audit confirms existing ranking metrics already exist, so the incoming uncertainty about whether ranking was tested is resolved. Old inputs contain SEC/history/size data, not validated Bloomberg fundamentals or LLM interpretations. The new A/B/C comparison remains unrun. Existing years remain exposed development evidence.

Requested review outputs are reports/data_inventory.md, reports/data_quality_audit.md and reports/filing_pilot_plan.md. Machine evidence is research/runs/ranking-scope-audit/20261025-v2/. No full extraction or retraining was launched. The handoff explicitly requests audit/pilot-plan review before those actions; it does not require permission to complete this read-only audit.
'''
    outputs = {ROOT/'reports/data_inventory.md': inventory.encode(),
               ROOT/'reports/data_quality_audit.md': quality.encode(),
               ROOT/'reports/filing_pilot_plan.md': pilot.encode(),
               DOC/'direction.md': direction.encode(), DOC/handoff.name: handoff.read_bytes()}
    html_horizons = ''.join('<tr>' + ''.join(f'<td>{html.escape(str(v))}</td>' for v in row) + '</tr>' for row in horizon_rows)
    readable = f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>13D revised ranking project: audit and next decisions</title>
<style>body{{font:17px/1.65 system-ui,sans-serif;background:#f4f6f8;color:#203448;margin:0}}main{{max-width:1040px;margin:30px auto;padding:28px;background:white}}h1{{font-size:30px;line-height:1.25}}h2{{font-size:23px;margin-top:30px}}a{{color:#155c99}}table{{border-collapse:collapse;width:100%;font-size:15px}}td,th{{text-align:left;vertical-align:top;padding:10px;border-bottom:1px solid #dce3e9}}th{{background:#edf3f7}}.scroll{{overflow-x:auto}}.note{{border-left:4px solid #c48721;padding-left:18px}}li{{margin:9px 0}}</style></head><body><main>
<p><a href="../../../../START-HERE.html">Project home</a> · October 25, 2026 · Offline audit and proposed pilot</p>
<h1>Does filing language help rank investments beyond financial information?</h1>
<p>Your new direction compares financial-only, LLM filing features, and combined inputs with simple models. Twelve- and 24-month excess returns are co-primary; 36 months is secondary. Spearman measures whether higher predictions correspond to better realized outcomes. It does not require accurate forecasts of their exact return levels.</p>
<p>The audit confirms a traceable foundation: <strong>667 event records, 641 issuers and 639 securities</strong>. Their linked raw sources, canonical text and citation checks pass. These checks establish evidence integrity, not complete or correct interpretation of each filing.</p>
<h2>What changed</h2><ul><li>Ranking and incremental LLM information are now central; further neural-network tuning is optional.</li><li>Use financial-only, LLM-only and combined features on matched samples, dates, targets and algorithms.</li><li>Start with simple references, ridge and constrained trees within the 4–5 week course window.</li><li>Review data and approximately ten discovery plus ten separate validation filings before full extraction or retraining.</li></ul>
<h2>What is available</h2><p>Existing return labels allow the following exact event joins. Horizon schedules were constructed independently under the inherited non-overlap rules.</p>
<div class="scroll"><table><thead><tr><th>Approx months</th><th>All scheduled</th><th>All calculable labels</th><th>All single-filing labels</th><th>Exact valid within 667</th><th>Also nine numeric Bloomberg fields, unverified</th></tr></thead><tbody>{html_horizons}</tbody></table></div>
<p>There are <strong>662</strong> exact common events for 12/24 months and <strong>561</strong> for all three horizons. The final financial/LLM comparable modeling sample remains undetermined.</p>
<h2>Why field completeness is insufficient</h2><p>Bloomberg has nine numeric fields for 587/667 events, partial fields for 57, and none for 23. A value being present does not mean it was public when an investor had to decide. The workbook selects a fiscal year without event-level release-date and revision evidence. Its BHE January 2019 example contains an identified historical-availability conflict. Mapping, currency, scale and field definitions also need validation.</p>
<p>The filing parser locates Item 4 spans in 662/667 cases. Five need source inspection. Unresolved reference flags occur in 554/667 cases; their relevance must be checked individually. Neither a missing parser span nor an unresolved reference is itself a negative intent judgment or automatic exclusion.</p>
<h2>Prior ranking results remain evidence</h2><p>The incoming handoff asks whether ranking had been tested. Saved files confirm it had: the earlier network's within-year Spearman correlations were −0.364, −0.220 and −0.193 for 2021–2023. Those experiments used the old structured inputs and 24-month target, not the proposed financial/LLM feature comparison. Their exposed history remains development evidence.</p>
<h2>Next decisions</h2><ol><li>Review the audit and ten-plus-ten pilot proposal.</li><li>Confirm a bounded financial-data availability/mapping check and human review time.</li><li>Prepare a source-only pilot and freeze independent human references before model answers for the same cases.</li><li>Then specify new horizon/sample/feature rules, chronological folds, tied ranks/quintiles and uncertainty before fitting.</li></ol>
<p class="note">No new extraction judgments, return calculations, model fits or paid calls were made. The incoming handoff explicitly requests review of the audit and pilot plan before full extraction or retraining.</p>
<h2>Detailed reports and evidence</h2><ul><li><a href="../../../../reports/data_inventory.md">Data inventory and actual paths</a></li><li><a href="../../../../reports/data_quality_audit.md">Quality audit, missingness, maturity counts and blockers</a></li><li><a href="../../../../reports/filing_pilot_plan.md">Proposed ten-plus-ten filing pilot</a></li><li><a href="../../../docs/ranking-direction-20261025/13D_Codex_Handoff_2026-10-25.md">Preserved incoming handoff</a></li><li><a href="audit.json">Machine-readable audit</a> · <a href="filing-source-audit.json">Per-filing evidence</a> · <a href="event-coverage.csv">Event/horizon ledger</a> · <a href="source-manifest.json">Input hashes</a></li></ul>
</main></body></html>'''
    outputs[RUN/'index.html'] = readable.encode()
    assert '667 rows' in inventory and '| 24 |' in quality
    assert len(gap_rows) == p['rows'] - p['item4_candidate_span_events']
    assert 'No sample selected' in pilot and 'Spearman' in direction
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    outputs = build()
    for path, data in outputs.items():
        if args.verify:
            assert path.read_bytes() == data, path
        else:
            if path.exists() and path.read_bytes() != data:
                raise FileExistsError(f'Preserve differing existing report: {path}')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    print(f'{"Verified" if args.verify else "Created"} {len(outputs)} reports/direction artifacts.')


if __name__ == '__main__':
    main()
