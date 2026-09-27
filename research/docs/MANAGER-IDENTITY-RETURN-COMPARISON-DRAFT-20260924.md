# Manager identity and post-13D stock performance

Working research direction recorded 24 September 2026 at the user's request.
This is a design draft, not a frozen protocol or completed performance analysis.

## Starting sample

Broad discovery subset: 64 HFR Event-Driven Firm_IDs with dated filing candidates
plus seven externally selected manager groups = 71 candidate manager units.
Focused discovery subset: 15 dated HFR Activist Firm_IDs plus seven supplemental
groups = 22 candidate manager units. These are not yet verified unique economic
managers; historical aliases, related firms and organizational changes can alter
the count. Source counts: research/runs/hfr-quarterly/20260924-v1/sec-screen/summary.json
and research/runs/investor-identity/20260924-supplemental-v1/summary.json.

The broad set has 3,125 unique candidate accessions, including 404 initial 13Ds.
The focused set has 2,636, including 323 initial 13Ds. The 75,631-record archive
includes amendments; subtracting subset accessions does not yield independent
control events. The supplement is retrospective; the HFR screen uses dated but
unverified delivery proxies beginning in 2018. Harmonize sample dates and
information availability before estimating performance differences.

## Questions

1. Do eligible stocks disclosed by identified activist/event-driven managers
   subsequently outperform comparable stocks disclosed in other initial 13Ds?
2. Does following these public disclosures earn benchmark-adjusted returns
   after realistic entry timing and trading costs?
3. Does manager identity improve out-of-sample predictions beyond filing and
   stock characteristics? Later work adds Item 4 intent and investor participation.

## Proposed baseline

Use initial manager–issuer disclosures as the starting event candidates, with
explicit rules for joint filers, re-entry, overlapping events and amendments.
Begin with comparable operating-company common shares. Analyze closed-end funds,
other vehicles, related-party/control transactions and other security classes
separately. Failure to match a known manager means unresolved/other, not non-activist.

Compare the focused activist subset, the broader ED subset and other eligible
initial 13Ds over common calendar periods. Use matched controls or adjustment for
size, industry, liquidity, prior momentum and market conditions. Report total,
market-adjusted and appropriate factor-adjusted returns; positive raw returns
alone do not establish an edge. This remains an observational predictive study,
not proof that the disclosure or manager causes subsequent returns.

Use SEC public acceptance timestamps and a feasible subsequent execution price,
such as next-session open. Separate announcement reaction from returns achievable
by an outsider after disclosure. Proposed descriptive horizons: 1, 5, 20, 60 and
120 trading days. Choose one primary horizon before inspecting results and flag
the remaining horizons as secondary; do not select a winning horizon after testing.
Use corporate-action-adjusted total returns, delisting returns and explicit
price-link coverage. Include costs, turnover and capacity considerations in any
portfolio test. Never substitute the fund's purchase price for outsider entry.

Keep complete manager–issuer timelines together in chronological development/test
splits and prevent overlapping return windows from leaking across splits. Freeze
manager selection before future evaluation; names selected for present-day fame
cannot retrospectively establish an investable historical rule. Report uncertainty,
manager/issuer clustering, equal-manager results and leave-largest-manager-out
sensitivity so a dominant manager cannot silently determine the conclusion.

## Next concrete work

Verify identity relationships, audit dated manager coverage, classify issuer/security
eligibility and reconcile initial/amendment chains. Then link eligible event candidates
to CRSP/other approved price identifiers and report unmatched cases. Produce a
coverage/attrition table before freezing the event and return protocol. No performance
results, return downloads or backtest were generated in recording this direction.
