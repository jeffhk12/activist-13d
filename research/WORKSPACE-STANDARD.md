# Workspace standard

Active project: `/Users/jefflu/Projects/activist-13d` on this Mac's internal drive.
Open `/Users/jefflu/Projects/activist-13d/START-HERE.html` to navigate.

## Where files belong

| Location | Purpose |
|---|---|
| `review/current/` | One completed review pack, including its supporting evidence |
| `review/drafts/` | Unfinished review work, clearly marked as pending |
| `review/archive/` | Earlier packs and completed exploratory previews |
| `research/docs/` | Proposals, research notes and explanatory documents |
| `research/protocol/` | Frozen definitions, codebooks, prompts and schemas |
| `research/runs/` | Historical analysis runs, audits and reports |
| `research/CROSS-COMPUTER.md` | Machine setup and handoff history |
| `data/` | Raw sources and intermediate datasets |
| `src/`, `scripts/`, `tests/`, `wrds_access/` | Implementation, tests and WRDS tools |
| `maintenance/` | Migration receipts, backups and retired one-time utilities |

The root contains the entry page, repository instructions and environment/configuration
files. Hidden `.venv`, `.git` and tool caches serve the local development environment.

## Creating and publishing work

1. Reuse an existing purpose-based location. Keep a run's logs, previews, evidence
   and provenance together inside that run. Avoid adding root-level reports or
   recreating `output/` or `outputs/`.
2. Build a new pack in `review/drafts/<descriptive-name>/`. Record its stage and
   any missing deliverables on the entry page. Use dates on archived versions.
3. Preserve the current pack and human edits before replacing it. Move the prior
   pack into `review/archive/<name>-<date>/`, then promote the verified draft to
   `review/current/`. Update historical path resolution if a frozen record refers
   to a pack that moved. Never overwrite another pack merely to reuse its name.
4. Update `START-HERE.html` when the current work or its status changes. User-facing
   handoffs include the full absolute address and a clickable link.
5. For moves, record old and new paths, verify file hashes, update active readers,
   and test local navigation. Preserve frozen source/protocol/evidence bytes and
   their historical path strings; adapt readers instead of altering provenance.

## Current state

The 200-filing pack is ready at `review/current/`. The 52-candidate human-first
subset is paused at `review/drafts/human-first-52/`; packets and CSV worksheets
exist, but its Excel workbook has not been built. No model judgments or outcomes
have been added to it. Workspace organization does not resume research processing.

The preservation archive at
`/Users/jefflu/Archives/icloud-retired/activist-13d-20260923` is outside this working
project. The small old iCloud code/environment remainder is a retired location.
Windows has a separate checkout; this reorganization has not been applied there.
