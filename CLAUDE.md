# activist-13d

Course project. Standards live in `STANDARDS.md` — read it before writing code
here rather than expecting this file to restate them. Design rationale is in
`docs/DESIGN-RECORD.md`; data sourcing in `docs/DATA-SOURCING.md`.

## The three rules that override convenience

1. **Every number traces to its calculation and its raw source.**
2. **Every model judgment carries a rationale and is flagged as a model
   judgment**, never as fact.
3. **Refuse rather than fabricate.** A missing value is cheap; a plausible
   wrong one is not.

## Environment

- Interpreter: `C:\_dev\activist-13d\.venv`. Tooling installs under `C:\_dev` —
  ThreatLocker blocks `.exe` outside that tree.
- `PYTHONNOUSERSITE=1` and `PYTHONIOENCODING=utf-8` in every terminal.
- Run `.py` files, not `python -c` or inline here-strings.
- `EDGAR_USER_AGENT` must be set to a real name and email before any fetch.

## Hard constraints

- **`data/` is gitignored deny-by-default.** Do not add exceptions without a
  written reason. `data/raw/` is append-only frozen evidence.
- **Prompts and schemas in `protocol/` are never edited in place.** A change is
  a new version file. Labels from two prompt versions are not comparable.
- **No test may reach a paid endpoint.** `tests/conftest.py` blanks every
  provider credential by assignment, not `setdefault`. Do not weaken that.
- **Only public data.** SEC filings plus university entitlements. No employer
  data, code or documents — techniques carry over, artefacts do not.
- Never bypass a certificate or hook check to install a package.

## Conventions

- Module docstring names purpose, inputs, outputs, the governing formula, the
  `Tier:`, and the run line. `Tier:` is what makes the testing obligation
  observable — see `STANDARDS.md` § 2.
- Pin estimators to **hand-computed** values, never to the implementation's own
  output. Put the arithmetic in the test.
- Every identifier join reports its match rate, and a test asserts the rate has
  not silently fallen.
