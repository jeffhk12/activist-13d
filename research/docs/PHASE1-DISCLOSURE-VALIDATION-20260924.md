# The activist signal needs a tighter definition of “initial disclosure”

24 September 2026 · Outcome-aware development audit, not fresh evaluation.

**The dominant manager relationships are supported by the filings, but the
initial-event screen admitted amendments and an already established campaign.**
This materially qualifies the earlier outperformance story. The promising pattern
is not yet a validated “follow a newly disclosed activist” strategy.

[Open the audit and exposure report](../runs/phase1-baseline/20260924-disclosure-validation-v1/index.html).
Absolute address:
`/Users/jefflu/Projects/activist-13d/research/runs/phase1-baseline/20260924-disclosure-validation-v1/index.html`.

## What the disclosures establish

The audit covers **78 unique accessions** across the existing focused schedules
for all three horizons, including filings with unresolved outcomes. Raw SEC
hashes, byte counts, accession, acceptance time and subject CIKs were checked.
Canonical documents and exact supporting text locations are saved.

Two filings were treated as initial 13Ds by the metadata-based screen but explicitly
identify themselves as amendments in their document text:

| Filing | Document evidence | Implication |
|---|---|---|
| Tenneco, 3 April 2020 | Amendment No. 2; Item 4 describes a share-class conversion | Exclude from an initial-disclosure signal |
| Cloudera, 15 April 2020 | Amendment No. 7 | Exclude from an initial-disclosure signal |

The upstream screen used the form-derived amendment flag, which did not catch
these body/header discrepancies. The new detector distinguishes a numbered
amendment from a blank amendment field followed by a footnote. An unflagged
document is **not** thereby certified as a first campaign or fully eligible event.
Other numbered references are retained for review; an amendment to a contract or
a reference to an earlier filing is not automatically an amendment of this filing.

For the five largest twelve-month winners, the contemporaneous evidence supports
these specific associations:

- **Bed Bath & Beyond–Legion:** Item 2 identifies Legion as adviser to the named
  funds. Item 4 also describes a May 2019 cooperation agreement and later group
  dissolution. Its April 2020 standalone filing does not establish a new campaign.
- **CymaBay–Engine:** Item 2 identifies Engine Capital Management as investment
  manager of Engine Capital and Engine Jet.
- **Vertiv–Starboard:** Item 2 identifies Starboard Value LP as investment manager
  of the named funds and account.
- **Chefs’ Warehouse–Legion:** Item 2 identifies Legion as adviser to its named funds.
- **Tenneco–Icahn:** Item 5 identifies Icahn entities and Mr. Icahn as
  holders/controllers, but the filing is an amendment.

These are bounded, source-based assistant interpretations, recorded separately
from source facts. They do not validate the entire HFR database, prove manager
skill, establish a specific activist intervention, or create human-reference/NLP
intent labels. Full document readers and exact citations are linked in the report.

## How much does eligibility matter?

These are **fixed-schedule sensitivity checks**, not a full baseline rebuild.
Stock and benchmark returns are unchanged; excluded events receive no replacement
trades. Figures are mean excess over the assigned Russell ETF, in percentage points.

| Sample | Three months | Six months — primary | Twelve months — supporting |
|---|---:|---:|---:|
| Previous focused result | +4.26 / 68 events | +7.32 / 66 | +17.71 / 65 |
| Exclude explicit numbered amendments | +2.61 / 66 | **+5.70 / 64** | **+16.17 / 64** |
| Also exclude the April 2020 BBBY event | +0.69 / 65 | **+0.15 / 63** | **+8.81 / 63** |
| Amendment-excluded sample, excluding all 2020 entries | +1.06 / 50 | +1.35 / 48 | +6.21 / 48 |
| Amendment-excluded sample, excluding 2020Q2 entries | +1.03 / 63 | +0.48 / 61 | +7.78 / 61 |

Cloudera is in the three- and six-month samples but not the original 65-event
twelve-month sample. Thus the amendment screen removes two events at shorter
horizons and one at twelve months.

The BBBY row separately asks whether the result depends on following an existing
campaign. It removes only the April 2020 event, not every BBBY observation, and
does not claim the standalone filing is legally an amendment. The earlier 2019
BBBY event remains. Defining first manager–issuer campaigns requires a complete
history and cannot be inferred from the filing form alone.

## Industry and entry-period exposure

Historical pre-disclosure SIC fields are available for all **64** events in the
amendment-excluded twelve-month sample. We use two-digit industry groups, not GICS
sectors. This is descriptive exposure analysis, **not industry-adjusted alpha**.

- **2020 entries:** 16 events contribute **11.51 points** of the +16.17-point mean.
  Excluding that entry year leaves +6.21 points across 48 events.
- **2020Q2 entries:** three events—BBBY, Chefs’ Warehouse and CommVault—contribute
  **8.75 points**. Excluding them leaves +7.78 points across 61 events.
- **SIC 57, home furnishings/equipment retail:** two observations, both BBBY at
  different entry dates, contribute **6.74 points**. Excluding the group leaves
  +9.73 points across 62 events. This is effectively company concentration in
  this sample, not broad evidence about retail-sector performance.
- **SIC 28, chemicals and allied products:** seven events contribute 3.42 points.
  **SIC 36, electrical/electronic equipment:** three contribute 3.17 points.
  All groups, including negative contributors, appear in the report.

SIC group definitions follow the [official SIC manual](https://www.osha.gov/data/sic-manual).
The pre-disclosure classifications come from saved historical CRSP observations.
Entry-year and quarter groups have overlapping holding windows; they are not
independent calendar-year portfolio returns. These checks show concentration but
cannot establish whether industry or a market rebound caused the gains.

## Implication for the project

Identity is useful, but it is not enough. We need to distinguish:

1. A manager's association with a disclosed position.
2. An initial form versus an amendment despite conflicting metadata.
3. A newly initiated manager–issuer campaign versus continued or reconstituted
   reporting of an existing campaign.

The next baseline revision must apply these eligibility rules across the full
universe, resolve prior disclosures and rebuild schedules consistently. The
current audit adds a tested cover-amendment detector and source evidence, but does
not retrospectively rewrite the 75,631-record registry or certify every campaign.
Industry/time-matched comparisons and funded portfolio accounting follow that
eligibility correction. No manager list or horizon has been optimized here.

Six months remains primary, twelve months supporting. Earlier reports remain
preserved but their “initial disclosure” interpretation is provisional. Later
evaluation outcomes and human-reference packets remain untouched.

## Evidence and limitations

- [All filing audits and exact amendment spans](../runs/phase1-baseline/20260924-disclosure-validation-v1/filing-audit.json)
- [Relationship citations and assistant interpretations](../runs/phase1-baseline/20260924-disclosure-validation-v1/relationship-reviews.json)
- [Sensitivity statistics and uncertainty intervals](../runs/phase1-baseline/20260924-disclosure-validation-v1/sensitivity.json)
- [Industry/year/quarter calculations](../runs/phase1-baseline/20260924-disclosure-validation-v1/exposures.json)
- [Protocol](../protocol/phase1-disclosure-validation-v1.md)
- [Independent checks](../runs/phase1-baseline/20260924-disclosure-verification-v1/verification.json)

All 36 relevant tests passed and offline replay reproduced the results. Verification
checks raw source URLs/hashes, acceptance times, issuer IDs, exact canonical
citations, sensitivity arithmetic, contribution totals and local links.

These remain gross, equal-event returns: entries March 2018–December 2022,
follow-up through 2023. Purchase at the second exchange-session open after
acceptance and exit at the 63/126/252-session scheduled close. Original overlap,
delisting and missing-return conventions remain unchanged. ETF expenses are
embedded, but strategy costs, cash drag and capital constraints are omitted.
Russell coverage is selective, membership is lagged monthly, vendor count
discrepancies remain, and HFR availability and supplemental-manager selection
retain their prior limitations. No causal or repeatable-alpha claim follows.
