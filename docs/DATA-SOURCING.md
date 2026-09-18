---
title: Data Requirements and Sourcing
subtitle: Predicting Activist Campaign Duration and Outcome from Disclosed Intent
kicker: WORKING DOCUMENT
course: Advanced Machine Learning in Finance · Fall 2026
author: Jeff Lu
date: Drafted 8 September 2026
---

> [!NOTE] SCOPE
> Every variable the project consumes, where it comes from, and what has to be built rather than
> downloaded. Companion to `DESIGN-RECORD.md` (design rationale) and `PROPOSAL.md` (submission).
> The short version: almost everything comes from EDGAR and CRSP, and the work is in three joins
> plus the construction of the outcome variable.

# 1 · Requirements by stage

| Stage | Variable | Source | Status |
|---|---|---|---|
| **0** Panel | Campaign start date | 13D filing date — EDGAR metadata | Free |
| | **Disclosure delay** — filing date minus *Date of Event Which Requires Filing* | 13D cover page | Free. **Q2's treatment variable, disclosed on every filing** |
| | Stake %, shares held, percent of class | 13D cover page | Free |
| | Filer identity, reporting persons | 13D cover page + Item 2 | Free |
| | Subject company CIK and CUSIP | 13D cover page | Free |
| **1** Extraction | Item 4 *Purpose of Transaction* text | 13D primary document | Free |
| | Exhibits — board letters, presentations, agreements | Whole 13D accession | Free |
| | Escalation chain | All `SC 13D/A` for the filer × subject pair | Free |
| **2** Survival | Campaign end date and terminal cause | **Constructed — see §5** | Build |
| | Right-censoring indicator | Sample end, or last observed filing | Derived |
| **3** Causal | Market cap, book-to-market, leverage, profitability, cash, payout | Compustat | WRDS |
| | Prior returns, volatility | CRSP monthly | WRDS |
| | Industry classification | Fama–French 48/49 from SIC | Free |
| | Institutional ownership | Thomson/Refinitiv s34 | WRDS, quality caveats |
| | Governance — staggered board, poison pill | Audit Analytics / ISS | WRDS, **to confirm** |
| **4** Sizing | Daily returns, filing date → exit | CRSP daily | WRDS |
| | Dollar volume, bid-ask spread, market cap | CRSP daily | WRDS |
| | Factor benchmarks for abnormal returns | Ken French data library | Free |

# 2 · SEC EDGAR

Free, no registration, no API key. Nine form types carry the project.

| Form | What it gives you |
|---|---|
| `form.idx` (quarterly full-index) | Filing enumeration across all filers. **The spine** |
| `SC 13D` | Stake, stated intent, disclosure delay |
| `SC 13D/A` | Escalation, stake changes, exit |
| `SC 13G`, `SC 13G/A` | The passive control group |
| `DEFC14A`, `DFAN14A` | **Proxy contest identification.** An activist filing these marks the escalation endpoint |
| `8-K` Item 5.07 | Shareholder vote results — separates proxy win from proxy loss |
| `SC 14D9`, `DEFM14A`, `SC TO-T` | Takeover and tender outcomes |
| `Form ADV` | Adviser registration, AUM, strategy description. Useful for universe curation |
| `Form 4` | Insider trading around campaigns. Optional |

The proxy-contest and vote-result filings are the ones most often missed, and they are how you
separate proxy win from proxy loss without a commercial vendor.

## Endpoints

| Purpose | Endpoint | Status |
|---|---|---|
| Enumerate filings | `https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{n}/form.idx` | Stable. Use as the spine. **Not reliably fixed-width** — parse with a regex anchored on CIK / ISO date / `edgar/` path |
| Per-filer history | `https://data.sec.gov/submissions/CIK##########.json` | Officially documented |
| Fetch documents | `https://www.sec.gov/Archives/edgar/data/{cik}/{accession_nodashes}/` + `index.json` | Stable |
| Keyword search | `https://efts.sec.gov/LATEST/search-index?q=…&forms=SC+13D&dateRange=custom&startdt=&enddt=&from=` | **Undocumented** — no published schema, parameter list or deprecation policy. Targeted lookups only |

> [!WARN] ACCESS DISCIPLINE
> A declared `User-Agent` header carrying a contact email address is **mandatory and enforced** —
> requests without one are blocked. Stay under roughly **10 requests per second** aggregate across
> `www.sec.gov` and `efts.sec.gov`. Cache every fetched document to disk so the pipeline never
> re-hits the SEC while you iterate.

## The format break -- and the rename beside it

> [!WARN] THE FORM-TYPE STRING CHANGED
> `SC 13D` became **`SCHEDULE 13D`** at the same 18 December 2024 mandate. 2024 QTR4 is the
> transition quarter and carries both (445 `SC 13D`, 114 `SCHEDULE 13D`); by 2025 QTR2 the old
> spelling is down to three stragglers. **Filtering on the old string alone returns 7 filings for
> the whole of 2025 instead of ~1,100** -- it silently deletes the entire post-rule-change sample,
> which is precisely the period Q2 measures. Accept both spellings and normalise to a canonical
> label. Measured 2026-09-08; this is a third thing that changes at the December 2024 boundary.

`SC 13D` and `SC 13G` must be filed in structured XML from **18 December 2024** (`primary_doc.xml`).
Before that date they are HTML or plain text with no fixed layout.

Two parsers, and a `parser_source` flag on every row. Extraction quality almost certainly differs
across the break, the break sits inside the sample, and Q2 straddles it — so the flag is not
housekeeping, it is a control variable.

# 2b · Measured universe (2026-09-08)

Counted from the EDGAR quarterly indices, 2013 Q1 to 2026 Q3, by
`scripts/count_universe.py`. All parties, before curation.

| | |
|---|---|
| Initial 13D filings, 2013-2026 | **17,791** |
| Amendments 13D/A | 57,969 |
| Distinct filings | 75,760 (from 150,739 index rows) |
| **Initial filings on/after 5 Feb 2024** | **2,864** |
| Top 150 CIKs appear on | **3,267 initial filings (18.4%)** |
| Distinct CIKs, either role | 22,126 |
| Index cache on disk | 2.2 GB, 56 quarterly files |

Stable at 1,100-1,557 initial filings a year across thirteen years. The scoping
assumption in `DESIGN-RECORD.md` section 4 holds without revision.

> [!WARN] EVERY FILING IS INDEXED TWICE
> A 13D appears once under the filer's CIK and once under the subject company's,
> sharing one accession -- 150,739 index rows for 75,760 filings. Counting rows
> overstates the universe by 2x. `form.idx` does not say which party is which;
> that requires the submission header (`FILED BY` / `SUBJECT COMPANY`), which is
> the next construction step.

# 3 · WRDS

Subscriptions vary substantially by institution. Verify each before assuming it.

| Dataset | Needed for | Likelihood |
|---|---|---|
| **CRSP daily + monthly stock file** | Returns, volume, shares outstanding, **delisting codes** | Near-certain |
| **CRSP/Compustat Merged (CCM)** | PERMNO ↔ GVKEY link | Included with both |
| **CRSP historical CUSIP (`NCUSIP`)** | The subject-company join. Critical | Included with CRSP |
| **Compustat Fundamentals** (annual + quarterly) | Firm characteristics for Stage 3 | Near-certain |
| **Audit Analytics** | Shareholder-activism database — the validation set | **Uncertain. Highest value item on this list** |
| **ISS / Voting Analytics** | Proxy contest outcomes, director elections, governance | Less likely |
| **Thomson/Refinitiv s34** | Institutional ownership | Likely |
| **IBES** | Analyst estimates as Stage 3 controls | Likely |
| **SEC Analytics Suite** | Pre-indexed EDGAR full text — would remove real pipeline work | Uncertain, worth asking |

> [!NOTE] ONE EMAIL SETTLES THIS
> Send the librarian this list rather than clicking through the portal. Ask specifically about
> **Audit Analytics**, **ISS / Voting Analytics** and **SEC Analytics Suite**. The answer determines
> whether Stage 0 takes two weeks or five.

Known caveat on Thomson s34: documented coverage problems including institutional ownership
exceeding 100%, missing BlackRock records, and coverage swings from 2010. Use **CRSP** shares
outstanding rather than Thomson's, and treat s34 as a secondary control rather than a primary input.

# 4 · The three joins

This is where the time goes.

## Join 1 — 13D subject company → CRSP

The cover page gives both a CIK and a CUSIP. Match in this order:

1. **CIK first.** EDGAR-native, stable, and the most reliable link.
2. **Historical CUSIP** (`NCUSIP`) as of the filing date, falling back to the 6-digit issuer within a
   date window.
3. **Hand-resolve the residual** and report the match rate in the methods section.

> [!WARN] MATCH ON HISTORICAL CUSIP, NOT CURRENT
> Companies change CUSIPs on reorganisation. Current-CUSIP matching silently drops exactly the
> targets that got restructured — which is a non-random subset of activist campaigns, and precisely
> the successful ones. This is the single most dangerous shortcut in the pipeline.

## Join 2 — Filer CIK → manager entity

One manager files under many CIKs, and 13D group filings name several reporting persons at once.
These have to be collapsed to one manager entity before any universe or fixed effect makes sense.

Name normalisation plus hand curation. **This is where LLM entity resolution genuinely earns its
place** rather than being decoration — the variants ("Starboard Value LP" / "STARBOARD VALUE L.P." /
"Starboard Value and Opportunity Master Fund Ltd") defeat regex and are trivial for a model.
Validate against a hand-labelled sample and report precision and recall.

## Join 3 — Initial 13D → its amendment chain

Match on filer × subject, ordered by filing date. Watch for:

- Filers switching between 13D and 13G mid-campaign
- Group membership changing between amendments
- Multiple distinct campaigns by the same filer against the same target, years apart

# 5 · Outcome coding is a construction task

The five competing outcomes each come from a different source. None of this is a download.

| Outcome | Evidence |
|---|---|
| **Settlement** | Text in a 13D/A or an 8-K — requires extraction |
| **Proxy win** | `DEFC14A` filed, then 8-K Item 5.07 showing dissident nominees elected |
| **Proxy loss** | Same filings, opposite result |
| **Target acquired** | CRSP delisting code in the merger range, plus delisting date |
| **Quiet exit** | Final 13D/A showing under 5%, or no amendment for *N* quarters with no other terminal event |

Five heterogeneous sources plus a decision rule for ties, ambiguity and censoring. Realistically
**30–40% of Stage 0**, and it needs its own codebook alongside the intent codebook.

Underestimating this is the most likely reason the timeline slips.

# 6 · Deliberately not used

| Source | Why not |
|---|---|
| **HFR** | Licensed to a current employer, not to the student — `CAREER_PLAN.md` §6. Also a poor fit: fund-level returns do not join to position-level campaigns, and self-reporting means coverage is worst for exactly the large activists that drive campaigns |
| **Bipsync, IODL, eVestment, Morningstar-via-RF, BNY, Dundas** | Same licensing position. Techniques carry over; data, code and documents do not |
| **Analyst ratings, sell-side research** | Wrong construct for labelling intent, usually written after the 13D, and licensed for internal academic use only. Belong downstream as controls, never as labels |
| **SharkRepellent / FactSet SharkWatch** | The commercial activism standard, almost certainly unavailable. Hand-building the event list from EDGAR is the substitute, and is contribution-worthy work |
| **Bloomberg, as a pipeline dependency** | Terminal data is throttled and the licence generally bars redistribution in published work. Spot-checks and outcome validation only |

## Universe curation without a vendor

The one genuinely tempting use of a commercial database was curating the activist universe. 13D
itself does it more defensibly:

- **13D filing frequency.** Rank CIKs by number of `SC 13D` filings over 2013–2026 and take the top
  *N*. A filer with twenty campaigns is definitionally an activist.
- **The 13D-versus-13G ratio.** Crossing 5% and electing to file 13D rather than 13G *is* the
  declaration of activist intent — a behavioural classifier drawn straight from the primary data.
- **Form ADV Part 2** for strategy descriptions, free and public.

Then hand-check the resulting list. *"Activists are defined by revealed filing behaviour"* is a
stronger methods statement than *"activists are whoever a vendor tagged event-driven,"* and it
survives the obvious question about selection.

> [!WARN] FREQUENCY RANKING SURFACES THE WRONG ACTIVISTS
> Measured 2026-09-08, the top of the filing-count ranking is **closed-end-fund discount
> activists**, not corporate activists: GAMCO 231, Saba Capital 158, Brooklyn Capital 66,
> Karpus 52, Stilwell 31 — against Starboard 59, Icahn 40, Ancora 37, Elliott 34, ValueAct 31.
> A CEF discount campaign has a different horizon, demand taxonomy and terminal-state
> distribution from a corporate campaign. Pooling them without a control mixes two
> data-generating processes. See `DESIGN-RECORD.md` → Measured universe for the three options;
> the working assumption is both, with a fund-type indicator. **Decide before the codebook**,
> because the campaign-type categories differ. CEF targets are mechanically identifiable — the
> subject is a registered investment company, observable from its SEC filer type.

# 7 · Storage and provenance

| Artefact | Where | Why |
|---|---|---|
| Raw filings, whole accessions | `data/raw/edgar/{cik}/{accession}/` | Archived, never re-fetched. The paper is reproducible only if these are frozen |
| Parsed panel | `data/interim/*.parquet` | Regenerable from raw |
| WRDS extracts | `data/raw/wrds/` with the query and pull date recorded | WRDS data is revised; the pull date is part of the provenance |
| Raw LLM responses | `data/raw/llm/{provider}/{model}/{prompt_hash}/` | ~60,000 JSON documents. Makes downstream analysis deterministic and auditable |
| Codebooks, prompts, schemas | `protocol/` — versioned, hashed, never edited in place | A prompt change means a new version; v1 and v2 labels are not comparable |
| Analysis outputs | `output/` | Regenerable end to end from the above |

# 8 · Week 1 actions

1. **Email the WRDS librarian** the §3 list, flagging Audit Analytics, ISS/Voting Analytics and SEC
   Analytics Suite.
2. **Pull one quarter of `form.idx` and hand-parse ten 13D filings** — five post-December-2024 XML,
   five pre-2024 HTML. Confirm you can locate Item 4, the exhibits, the CUSIP, the CIK and the *Date
   of Event Which Requires Filing* in both formats. Ten filings will teach you more about the
   parsing work than any amount of planning.
3. ~~**Count the universe.**~~ **Done 2026-09-08** — see section 2b. 17,791 initial filings,
   3,267 on a top-150 curation, 2,864 post-rule-change. The assumption holds. Superseded by:
   **assign filer-versus-subject roles** from the submission header, and **decide the
   CEF-versus-corporate split**.
4. **Draft the outcome codebook** in parallel with the intent codebook. It is the larger of the two
   and it is currently the least specified part of the project.
