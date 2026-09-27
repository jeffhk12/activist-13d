# Phase 1 current working case: Hill excluded

24 September 2026. User instructed “lets skip this one” after the OTC-data discussion.

Hill International (issuer 0001287808) is excluded across both development event definitions, all investor cohorts and all three horizons before scheduling. All 36 portfolio scenarios now complete. This is a user-selected, retrospective data-availability sensitivity; the original full-universe run and refusals are preserved. Do not pursue Hill OTC prices as a dependency for this branch. No investor-list or human-label change and no fresh evaluation.

Primary $100k mechanical first-pair six-month portfolio: +21.89% cumulative, 3.48% annualized, 74.74% mean cash, −18.61% maximum drawdown, 60 buys over 2018-03-19–2023-12-29. Twelve-month holding rule: +65.06% cumulative, 9.04% annualized, 51.15% cash, −35.15% drawdown. Six-/twelve-month gross first-pair event excess remains +0.28/+7.08 points on 54 events each because Hill was already not calculable there. These are development results, not alpha or untouched confirmation.

[Current report](../runs/phase1-baseline/20260924-skip-hill-report-v1/index.html).

Runs: 20260924-skip-hill-inputs-v1, 20260924-skip-hill-analysis-v1, 20260924-skip-hill-qa-v1, 20260924-skip-hill-report-v1 under research/runs/phase1-baseline. Protocol phase1-skip-hill-v1.md. Scripts run_phase1_skip_hill.py, verify_phase1_skip_hill.py and report_phase1_skip_hill.py. Original prices and histories retained; only this issuer's events removed. Independent QA verifies unchanged remaining event returns and exact portfolio replay. 24 targeted tests pass; 554 protected assets unchanged.

Next: finish current-issuer/current-reporter attribution or explicitly freeze conservative history-reference exclusions, verify evaluation inputs, then finalize sample/rules and evaluation exposure boundary. “Initial form” and “first observed pair” remain different definitions. Item 2 asks who filed previously, about which company and when; text about another issuer or an incorporated exhibit cannot establish prior same-company involvement. Existing ambiguous exclusions remain; this work is not ML or human intent labels.
