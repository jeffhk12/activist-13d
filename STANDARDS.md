# Standards

How code in this repo is written and what it must prove. Short on purpose — a standard expensive
enough to skip will be skipped.

Three rules govern everything else:

1. **Every number traces to its calculation and its raw source.**
2. **Every model judgment carries a rationale and is flagged as a model judgment**, never as fact.
3. **Refuse rather than fabricate.** A missing value is cheap; a plausible wrong one is not.

---

## 1 · The module header

Every `.py` file that does real work opens with a docstring naming **purpose, inputs, outputs, the
governing identity or formula, the Tier, and how to run it**. This is the calculation record, and it
is what makes a script auditable a year later.

```python
"""Disclosure-delay computation for Schedule 13D filings.

Reads the cover-page event date and the EDGAR filing date; returns the delay
under the regime in force on the filing date.

Identity:  delay_bd = business days in (event_date, filing_date],
                      US federal holidays excluded          (filed >= 2024-02-05)
           delay_cd = calendar days, filing_date - event_date   (filed <  2024-02-05)

Tier: 1
Run:  set PYTHONNOUSERSITE=1, PYTHONIOENCODING=utf-8
"""
```

`Tier:` is what makes the testing obligation observable instead of guessed.

## 2 · Tiers — by blast radius, not by intent

Tier on something observable: **who reads the number, and what happens if it is wrong.**

| Tier | Trigger | Obligation |
|---|---|---|
| **0 · scratch** | Lives in `scripts/` as a one-off probe, or in a notebook | **None.** It stays there and nothing imports it |
| **1 · analysis** | Produces a number a human reads — a table, a figure, an intermediate the next stage trusts | **3–5 assertions.** Pin each estimator to a hand-computed value; one test that a re-run reproduces the output |
| **2 · reported** | Produces a figure that reaches the report or the presentation | Full suite: estimator pins, convention contract, refusal tests, parity where two paths agree, CI |

Promotion is a one-line header change, because the Tier-1 pins are exactly the tests Tier 2 wanted.

## 3 · The six test patterns

**a · Pin estimators to hand-computed values.** Never assert against the implementation's own
output — that pins the bug in place along with the behaviour. Compute the expected figure by hand
from the formula in the module header, and put the arithmetic in the test.

**b · Declare the conventions and assert them.** The choices that silently change a number go in an
explicit contract the test can read:

```python
assert survival.ESTIMATOR["time_unit"] == "calendar days"
assert survival.ESTIMATOR["censoring"] == "right, at sample end 2026-06-30"
assert survival.ESTIMATOR["tie_handling"] == "efron"
assert survival.ESTIMATOR["acquired_delisting_codes"] == range(200, 400)
```

**c · Refuse, don't fabricate.** Thin or ambiguous input yields an explicit refusal — `None`, an
empty result, `cannot_determine` — never a plausible-looking value. This is the same rule the
extraction abstention implements.

**d · Parity where two paths must agree.** Campaign end date from the filing chain versus from the
CRSP delisting date, where both exist. Extraction agreement across providers. Pre-2024 and post-2024
parsers on fields both can read.

**e · Assert the join, not just the merge.** Every identifier crosswalk reports its match rate, and
a test asserts the rate has not silently fallen. An unmatched subset is almost never random.

**f · Test the refusal path of anything that costs money.** No test may reach a paid endpoint. See
`tests/conftest.py`.

## 4 · Numbers and reporting

- **State n.** Every result carries its sample size.
- **Label small-n results as hypotheses**, not findings. A statistic is not a conclusion.
- **Report the baseline.** A predictive number without its naive or persistence baseline is not a
  result.
- **Report the match rate** wherever an identifier join sits upstream of a figure.

## 5 · Model-assisted work

- Every extracted label carries a **supporting span** from the source document and is stored with
  the accession id, model string, provider, prompt hash and timestamp.
- Extracted labels are **noisy measurements**, not ground truth. Downstream models receive the
  label distribution, not the argmax.
- **Cheap model for mechanical work, strong model for judgment.** Batch and cache everything.
- Prompts and schemas are **versioned files, hashed, never edited in place**. A prompt change means
  a new version, because labels produced under v1 and v2 are not comparable.

## 6 · Reproducibility

- Prefer a re-runnable `.py` over manual steps, so any output can be regenerated and diffed.
- **Cache every external response to disk.** The pipeline must re-run offline from `data/raw/`.
- Record the **pull date** on every vendor extract. Vendor data is revised.
- Pin the environment. Record seeds where the provider exposes them.

## 7 · Environment

- `PYTHONNOUSERSITE=1` and `PYTHONIOENCODING=utf-8` in every terminal and in CI.
- Run `.py` files, not `python -c` or inline here-strings.
- Never bypass a certificate or hook check to install a package — no `--trusted-host`, no
  `--no-verify`. Fix the trust chain instead.
- Tooling installs into a venv under `C:\_dev` (`ruff` ships as a binary and must sit inside the
  execution zone).
