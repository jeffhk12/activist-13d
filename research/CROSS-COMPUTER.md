> **Current workspace (September 28, 2026):** code lives in local `Projects/activist-13d` on each computer; personal Google Drive → Workspace is the shared hub. Use [the current handoff guide](WORKSPACE-HANDOFF.md) and workspace Setup receipts for receiving readiness. The older setup notes below remain as history; do not restore competing working locations from them.

## October 15, 2026 — current ML work and handoff reconciliation

Checkpoint 3's fixed prediction comparisons are complete. Checkpoint 4 has teaching
diagrams and a proposed four-ReLU-neuron network; the neural network is not yet
implemented or trained. Resume with the forward/backward-update lesson, then verify
the implementation and freeze the experiment before fitting. The expanded professor
update is linked from `START-HERE.html`. HFR predictor additions remain proposed;
the frozen baseline still uses HFR only for diagnostic comparisons.

An unrelated browser screenshot had replaced
`research/runs/proposal-review/20260926-v4/qa/proposal-top.png`, preventing Finish
Work. The original proposal image was recovered from the September 27 preservation
archive and matched exactly to the immutable handoff hash. Both images and a repair
receipt are retained in
`research/runs/workspace-reconciliation/20261015-v1/`. The original image was restored;
no raw data, research calculations, protocols or human answers changed. The handoff
tool and previous shared manifests were not modified.

Use the normal Finish Work / Start Work routine described in
[the handoff guide](WORKSPACE-HANDOFF.md). Publication is established by a successful
Finish Work result and the shared `Handoffs/latest.json` marker, not by this note.
On Windows, allow Drive to synchronize, run Start Work, and begin editing only after
it verifies the exact source commit and research payload. Python environments and
credentials remain machine-local; Windows receiving and model-environment checks
must be completed there before training.

# Current workspace layout

Open `/Users/jefflu/Projects/activist-13d/START-HERE.html`. The completed 200-filing review is at `review/current/`. The unfinished 52-candidate pack is at `review/drafts/human-first-52/`; its workbook is pending and research remains paused. Previous `output/` runs are under `research/runs/`; previous `outputs/` packs are under `review/archive/`, except the current and draft packs. Migration records are in `maintenance/migration-20260923/records/`. The historical notes below retain paths valid when written. Windows was not reorganized by this task.

# Work on Mac and Windows

## September 23, 2026: Mac local migration verified

Use `/Users/jefflu/Projects/activist-13d` for current Mac research.
The migration verified 166,678 source files
(24,200,714,222 bytes). `data/raw` is now a local directory,
not an iCloud link. The original `Documents/GitHub-Repos/activist-13d` copy remains
intact; do not resume work there. Differing local code was retained, with incoming
versions archived under `.migration-20260923/conflicts/incoming`.

Use `.venv/bin/python` with `PYTHONNOUSERSITE=1` and `PYTHONIOENCODING=utf-8`.
All 61 original package versions match;
`requirements-mac-migration-20260923.txt` records the exact Mac environment.
The base offline suite passed 63 tests (one skipped, one network test deselected),
and 21 additional protocol/research tests passed.

Final verification rehashed every migrated file, replayed
10 pilot filings, preserved 32 blank development
records, checked 200 grouped review sources and
803 exact evidence spans, and passed the
historical SQLite integrity check. Legacy-file opens and network access were
blocked during that verification. No cloud-pointing project symlinks remain.

Review `outputs/13d-group-review-20260922/index.html` or
`outputs/13d-group-review-20260922/Grouped-13D-Review.xlsx`.
Old evidence/manifests retain their original paths as provenance; the current
research readers resolve those paths locally. Archived builders inside old output
folders are historical snapshots, not current launchers. Use scripts under
`scripts/` for new runs, always writing a new dated output directory.

Verification details: `.migration-20260923/validation.json`; source hashes:
`.migration-20260923/receipts.sqlite`; activation/conflicts:
`.migration-20260923/activation.json`. Completed at 2026-09-23T20:09:51.038283+00:00.

This completes the Mac local data/runtime migration. Windows data installation,
daily handoff, and cross-platform launchers were not verified in this session.
The 200-filing pack is a review sample, not validated activist/hedge-fund labels.

Code checkpoint prepared September 17, 2026.

Clone `https://github.com/jeffhk12/activist-13d.git` using branch `main` on each computer, into a local folder outside cloud sync. This Mac copy is at `/Users/jefflu/Projects/activist-13d`. The original source remains at `/Users/jefflu/Documents/GitHub-Repos/activist-13d`; preserve and compare any subsequent edits there before switching working copies.

Install a separate environment from the project's dependency files on each operating system. Restore the required data and local credentials separately. Fresh source snapshots and Git bundles are under `Jeff-Workspace-Backup/2026-09-17`. The verified complete data backup remains under `Jeff-Workspace-Backup/2026-09-14`; the full September 17 data refresh did not complete. Consult the backup verification files before restoring. OneDrive `Project-Transfer` is for selected travel data/results, within the 100 GB allowance.

Save and commit changes, push this branch before switching computers, and pull it on the other computer before editing. Check for uncommitted work first.

This is a code synchronization checkpoint, not proof of Windows compatibility. Existing absolute paths, native dependencies, data availability and licensed/external services still require project-specific setup and a representative test on both computers. Notebook outputs were removed in the publication copy. Binary reports, raw datasets, credentials and installed environments were omitted from new source snapshots; existing private-repository tracked files are retained.

## iCloud space cleanup, September 23

The original `data`, `output` and `outputs` directories now live at `/Users/jefflu/Archives/icloud-retired/activist-13d-20260923`, outside iCloud. Both copies matched migration hashes before the move; archived files retained their inodes and sizes. The working project is unchanged. The small historical code/environment remainder stays at the legacy location. No permanent deletion was performed. Cloud quota recovery is pending independent confirmation.
