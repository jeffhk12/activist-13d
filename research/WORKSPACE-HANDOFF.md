# Switching computers for 13D research

The project studies whether following initial 13D disclosures improves investment results under realistic trading rules. This workspace procedure preserves the evidence and human review needed for that research; it runs no collection, model calls, or investment calculations.

Use one computer at a time. Save and close review files before switching. Code stays in local Projects and the private GitHub repository. Research payloads travel as dated snapshots through the existing personal Google Drive workspace.

## Start and finish

The workspace Start Work and Finish Work launchers use `scripts/workspace_handoff.py`. The shared handoff directory is personal Google Drive → Workspace → Coding & Research → Active → 13D → Handoffs.

1. Before leaving a computer, save files and commit reviewed source changes, then run **Finish Work**. It publishes the code branch, hashes the managed files, and packages new data or changed human review files. Wait for successful completion and for Drive to finish synchronization.
2. On the receiving computer, run **Start Work**. It requires a clean source checkout, advances only to the exact published source commit, verifies the prior local files and incoming payloads, and preserves a local recovery copy before replacing a review file.
3. Begin editing only after Start Work reports success. Keep the other computer closed for this project.

If the tool stops, keep both versions and read its reason. It refuses unsaved source changes, differing local review edits, incomplete downloads, deletion of managed evidence, and replacement of saved raw data or historical output. New research should create new dated files rather than rewrite those originals. It can resume an interrupted receiving operation when the existing files and recovery copies match the recorded handoff.

## Scope and recovery

Managed directories are `data/`, `review/`, and `research/runs/`. Per-machine validation runs, OS metadata, transient locks, partial files and symbolic-link aliases are outside payload transfer. Private environment files, keys and new or changed database files are refused if encountered in these directories. The seven previously archived SQLite files may remain in the verified baseline only while their hashes are unchanged and no journal/WAL sidecars exist; they are not treated as live shared databases. Environments and credentials remain local.

The initial baseline must be verified on each computer before these routines are enabled. Older extra Windows files are recorded as local-only and preserved outside routine handoff. Their presence does not authorize deletion or replacement. Local symlink aliases require separately verified setup on Windows.

Per-computer state and pre-replacement review copies live in `.workspace-local/handoff/`. Shared snapshots are immutable directories under `Handoffs/snapshots/`; `latest.json` is published only after payload verification. Do not edit these manifests manually or run Finish Work on both computers concurrently. Drive synchronization is not a distributed lock or an independent backup.

These instructions describe the routine. The workspace Setup migration receipts record whether baseline initialization, both-computer tests and the first handoff have actually completed. Do not infer completion from this guide alone.
