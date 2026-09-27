# Predicting Activist Campaign Duration and Outcome from Disclosed Intent

Open [START-HERE.html](START-HERE.html) for current work.
The active Mac project is `/Users/jefflu/Projects/activist-13d`.
The ready review is in `review/current/`; the 52-candidate draft remains paused
in `review/drafts/human-first-52/`. Follow the
[workspace standard](research/WORKSPACE-STANDARD.md) when adding or moving files.

Machine learning on Schedule 13D filings, 2013–2026.
Advanced Machine Learning in Finance, Fall 2026.

Schedule 13D discloses a stake of 5% or more **and**, in Item 4, what the filer
says they intend to do about it — within five business days since February 2024.
This project asks whether that stated intent, extracted at scale by a language
model, predicts how a campaign unfolds, and whether an outsider can act on it.

| | Question |
|---|---|
| **Q1** | Does extracted campaign intent predict campaign duration and terminal outcome? |
| **Q2** | Did the February 2024 disclosure acceleration change the premium available to an outsider? |
| **Q3** | Does conditioning position size and holding period on predicted duration beat naive following? |

Q3 is the deliverable. The output is a sizing and holding-period rule, not a
return forecast.

## Documents

Your [skill catalog](../skill-library/SKILLS.md) lists installed workflows,
descriptions, and the skills ranked for this project. Ask `$skill-catalog`
to browse, compare, recommend, or refresh them.

| File | Purpose |
|---|---|
| `research/docs/PROPOSAL.md` | The submission-shaped proposal |
| `research/docs/DESIGN-RECORD.md` | Design rationale, rejected alternatives, decisions register, annotated reading list |
| `research/docs/DATA-SOURCING.md` | Every variable, its source, and what must be built rather than downloaded |
| `STANDARDS.md` | How code here is written and what it must prove |

`research/docs/build_docx.py` renders any of the markdown documents to a styled `.docx`.
The markdown is canonical; the `.docx` are build artefacts and are gitignored.

## Layout

```
src/activist13d/
    edgar/        enumerate, fetch and parse Schedule 13D filings
    dates.py      disclosure delay — Q2's treatment variable
    crosswalk.py  CIK / CUSIP -> PERMNO, with a reported match rate
    outcomes.py   the five competing terminal states
    extract/      LLM intent extraction, multi-provider, cached
    survival.py   competing-risks duration models
    causal.py     heterogeneous treatment effects
    sizing.py     the decision-focused position-sizing layer
    validation/   purged splits and evaluation metrics
research/protocol/         versioned codebooks, prompts and schemas
data/             gitignored, deny-by-default. See data/README.md
scripts/          one-off probes and week-1 actions
tests/
```

## Setup

```powershell
# A venv under C:\_dev — ThreatLocker blocks .exe outside that tree, and
# ruff ships as a binary.
python -m venv C:\_dev\activist-13d\.venv
C:\_dev\activist-13d\.venv\Scripts\python -m pip install -r requirements.txt

$env:PYTHONNOUSERSITE = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:EDGAR_USER_AGENT = 'Your Name your.email@example.edu'   # mandatory
```

`EDGAR_USER_AGENT` is not optional. The SEC blocks requests without a declared
contact address, and enforces roughly 10 requests per second.

## Run

For the macOS SEC collection pilot, see [SEC-PILOT.md](research/docs/SEC-PILOT.md).
It collects ten complete submissions and produces source-backed JSONL records.
The first live run requires `EDGAR_USER_AGENT` with a real contact email.

```powershell
python -m ruff check .
python -m pytest -m "not network"

# Week-1 action: count the universe before building on top of it
python scripts\count_universe.py 2013 2026
```

## Status

The SEC collection pilot is working: filing enumeration, cached submission
collection with provenance checks, legacy/XML parsing, and offline replay.
Disclosure-delay computation also has pinned tests. The latest check passed
34 offline tests and lint; ten cached submissions reproduced identical parsed
outputs. Modeling and campaign construction remain unimplemented.

See [SEC-PILOT.md](research/docs/SEC-PILOT.md) for the collection checkpoint and
[pilot evidence triage](research/docs/PILOT-TRIAGE-2026-09-09.md) for the preliminary,
model-assisted review. Next: source-addressable referenced-section/exhibit
bundles, then manager resolution and amendment chains. The triage is not a
human-validated label set.

Two open items gate the design — see `research/docs/DESIGN-RECORD.md` § 9:

1. Whether the university's WRDS subscription includes Audit Analytics, which
   decides whether the validation set is a download or a three-week build.
2. Whether a ~3,000-event survival project satisfies the course's
   deep-learning emphasis.

## Data

Public SEC filings, plus university CRSP, Compustat and Audit Analytics
entitlements. No licensed or proprietary data from any employer is used.
