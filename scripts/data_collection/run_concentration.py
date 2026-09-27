"""Tier: 2. Report manager/company/year concentration in focused 13D returns.
Inputs: frozen Russell development ledger and candidate identity evidence.
Outputs: immutable diagnostics, annotated event ledger, HTML and provenance.
Identity: equal-event excess decomposition; definitions in concentration-v1 protocol.
Run: PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/run_concentration.py
"""

import html
import json
from collections import defaultdict
from pathlib import Path

from run_phase1_development import ROOT, digest, encode, freeze

from activist13d.concentration import diagnostic, simple
from activist13d.phase1_baseline import summarize

BASE = ROOT / "research/runs/phase1-baseline/20260924-russell-returns-v1"
OUT = ROOT / "research/runs/phase1-baseline/20260924-concentration-v1"
HFR = ROOT / "research/runs/hfr-all-managers/20260924-v1"
SUP = ROOT / "research/runs/investor-identity/20260924-supplemental-v1"
REG = ROOT / "research/runs/phase1-baseline/20260924-feasibility-v2/event-candidates.jsonl"
PROTOCOL = ROOT / "research/protocol/phase1-concentration-v1.md"


def p(v):
    return "—" if v is None else f"{100 * v:+.2f}"


def table(headers, rows):
    return (
        '<div class="scroll"><table><tr>'
        + "".join("<th>" + html.escape(str(c)) + "</th>" for c in headers)
        + "</tr>"
        + "".join(
            "<tr>" + "".join("<td>" + html.escape(str(c)) + "</td>" for c in row) + "</tr>"
            for row in rows
        )
        + "</table></div>"
    )


def render(results, events, labels, company_names, paired):
    body = """<nav><a href="../../../../START-HERE.html">Project home</a> · <a href="../20260924-russell-returns-v1/index.html">Original Russell results</a></nav><h1>Is activist outperformance broad or concentrated?</h1><p>24 September 2026 · Development entries March 2018–December 2022 · Outcomes through 2023</p><section><h2>How to read this diagnostic</h2><p>We check whether the focused activist result survives removing managers, companies, entry years and the largest winners. All differences below are percentage points versus the historically assigned Russell ETF. These are gross, equally weighted event returns, not portfolio returns or established alpha.</p><p>Six months remains the primary test. Twelve months motivates this supporting investigation. These checks were specified after seeing the initial development results and cannot serve as independent confirmation.</p></section>"""
    for horizon in ["252", "126", "63"]:
        d = results[horizon]
        overall = d["overall"]
        n = overall["n"]
        managers = d["groups"]["manager"]
        years = d["groups"]["year"]
        firms = d["groups"]["issuer"]
        leave = [
            v["leave_out"]["mean"] for v in managers.values() if v["leave_out"]["mean"] is not None
        ]
        body += f"<section><h2>{ {'252': 'Twelve months — supporting', '126': 'Six months — primary', '63': 'Three months — supporting'}[horizon] }</h2><p>{n} events, {len(firms)} companies and {len(managers)} candidate manager IDs/groups. Mean excess: <strong>{p(overall['mean'])} pp</strong>; median: {p(overall['median'])} pp; {overall['win_fraction'] * 100:.1f}% of events beat their benchmark. Equal-company weighting gives {p(d['equal_company_mean'])} pp.</p><p>Removing one manager at a time leaves means between {p(min(leave))} and {p(max(leave))} pp. {sum(v['mean'] > 0 for v in years.values())} of {len(years)} entry years have a positive mean; {sum(v['mean'] > 0 for v in managers.values())} of {len(managers)} manager groups have a positive mean. Small groups are descriptive hypotheses, not manager rankings.</p>"
        body += table(
            ["Stress check", "Events remaining", "Mean excess (pp)", "Median excess (pp)"],
            [
                [
                    f"Remove top {r['removed_events']} positive events",
                    r["without_top_events"]["n"],
                    p(r["without_top_events"]["mean"]),
                    p(r["without_top_events"]["median"]),
                ]
                for r in d["removals"]
            ],
        )
        body += table(
            ["Company stress check", "Events remaining", "Mean excess (pp)"],
            [
                [
                    f"Remove top {len(r['removed_companies'])} contributing companies",
                    r["without_top_companies"]["n"],
                    p(r["without_top_companies"]["mean"]),
                ]
                for r in d["removals"]
            ],
        )
        body += "<h3>Entry years</h3>" + table(
            [
                "Entry year",
                "Events",
                "Mean excess (pp)",
                "Median (pp)",
                "Mean after removing year (pp)",
            ],
            [
                [k, v["n"], p(v["mean"]), p(v["median"]), p(v["leave_out"]["mean"])]
                for k, v in years.items()
            ],
        )
        body += (
            "<h3>Candidate managers</h3><p>Membership follows the qualifying activist/supplement evidence across all merged disclosures. Manager event counts can overlap. Contribution divides co-managed events equally and sums to the overall mean. Removing a manager removes all associated events. Candidate IDs are not verified economic manager identities.</p>"
            + table(
                [
                    "Candidate manager",
                    "Events",
                    "Mean excess (pp)",
                    "Contribution to total mean (pp)",
                    "Mean after removing manager (pp)",
                ],
                [
                    [
                        labels[k],
                        v["n"],
                        p(v["mean"]),
                        p(v["contribution"]),
                        p(v["leave_out"]["mean"]),
                    ]
                    for k, v in sorted(managers.items(), key=lambda kv: -kv[1]["contribution"])
                ],
            )
        )
        top = sorted(events[horizon], key=lambda r: (-r["excess"], r["accession"], r["entry"]))[:10]
        body += "<h3>Largest positive excess returns</h3>" + table(
            [
                "Company",
                "Entry",
                "Managers",
                "Stock return (%)",
                "Russell ETF return (%)",
                "Excess (pp)",
            ],
            [
                [
                    r["company"],
                    r["entry"],
                    ", ".join(labels[k] for k in r["managers"]),
                    p(r["stock_return"]),
                    p(r["benchmark_return"]),
                    p(r["excess"]),
                ]
                for r in top
                if r["excess"] > 0
            ],
        )
        body += f"<p>The top five positive events account for {100 * d['removals'][2]['share_positive_excess']:.1f}% of gross positive excess returns, before losing events offset them. This is an arithmetic event-contribution measure, not portfolio profit.</p>"
        body += (
            "<details><summary>Every company and removal result</summary>"
            + table(
                [
                    "Company / CIK",
                    "Events",
                    "Mean excess (pp)",
                    "Contribution (pp)",
                    "Mean excluding company (pp)",
                ],
                [
                    [
                        company_names[k] + " / " + k,
                        v["n"],
                        p(v["mean"]),
                        p(v["contribution"]),
                        p(v["leave_out"]["mean"]),
                    ]
                    for k, v in sorted(firms.items(), key=lambda kv: -kv[1]["contribution"])
                ],
            )
            + "</details></section>"
        )
    body += (
        "<section><h2>Holding periods on exactly the same events</h2><p>The intersection uses the same initial disclosure, purchase date and security. This separates the holding-period comparison from differences in sample composition. It does not establish that activism caused the longer-period result.</p>"
        + table(
            [
                "Sessions",
                "Common events",
                "Stock (%)",
                "Assigned Russell ETF (%)",
                "Excess (pp)",
                "Median excess (pp)",
            ],
            [
                [
                    h,
                    s["calculated"],
                    p(s.get("mean_stock")),
                    p(s.get("mean_benchmark")),
                    p(s.get("mean_excess")),
                    p(s.get("median_excess")),
                ]
                for h, s in paired.items()
            ],
        )
        + "</section>"
    )
    body += """<section><h2>Limits and next action</h2><p>These are realized-winner removal checks, not rules an investor could have used before investing. Small samples, overlapping market exposure and multiple checks limit inference. The positive twelve-month company-bootstrap interval from the earlier report does not resolve manager dependence, selection bias or costs.</p><p>Retain six months as primary and twelve months as supporting. Validate the dominant managers and disclosures, examine sector/year exposure, then test a frozen rule on fresh eligible data before claiming a repeatable edge. Do not tune the manager list or holding period to this table.</p><p>The sample is restricted to stocks with historical Russell membership matches and usable returns. Monthly membership is lagged, all 58 vendor snapshots have unresolved reported-count discrepancies, and nonmatches are not proven nonmembers. Candidate identities and historical HFR publication timing remain unverified. Supplemental manager selection was retrospective.</p><p>Entry is the second exchange-session open after acceptance; exit is the scheduled close after 63/126/252 sessions. Valid delisting returns are included once, then proceeds earn zero through exit. Original overlap exclusions and ETF proxies remain unchanged. ETF costs are embedded; strategy trading costs, portfolio capital constraints and cash drag are omitted. No later outcomes, human-review companies, NLP or ML are introduced.</p></section><section><details><summary>Evidence and reproducibility</summary><p><a href="diagnostics.json">All diagnostics</a> · <a href="events.json">Annotated event ledger</a> · <a href="paired-horizons.json">Same-event holding periods</a> · <a href="verification.json">Reconciliation checks</a> · <a href="provenance.json">Source/output hashes</a> · <a href="../../../protocol/phase1-concentration-v1.md">Frozen definitions</a></p></details></section>"""
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Activist return concentration</title><style>body{font:17px/1.6 system-ui;background:#f4f6f8;color:#233b50}main{max-width:1250px;margin:30px auto;padding:20px}section{background:white;padding:25px;margin:22px 0;border:1px solid #ddd;border-radius:8px}table{border-collapse:collapse;width:100%;font-size:15px}td,th{padding:10px;text-align:left;border-bottom:1px solid #ddd}th{background:#edf2f6}.scroll{overflow:auto}a{color:#155b91}summary{cursor:pointer;font-weight:bold}</style></head><body><main>'
        + body
        + "</main></body></html>"
    )


def main():
    for folder, filename, key in [
        (BASE, "outcomes.json", "outputs"),
        (BASE, "summary.json", "outputs"),
    ]:
        assert (
            digest(folder / filename)
            == json.loads((folder / "provenance.json").read_text())[key][filename]
        )
    assert (
        digest(HFR / "candidates.json")
        == json.loads((HFR / "provenance.json").read_text())["candidates.json"]
    )
    freeze(OUT / "protocol.md", PROTOCOL.read_bytes())
    for source in [
        Path(__file__),
        ROOT / "src/activist13d/concentration.py",
        ROOT / "tests/test_concentration.py",
    ]:
        freeze(OUT / "code" / source.name, source.read_bytes())
    evidence = defaultdict(set)
    names = defaultdict(set)
    for r in json.loads((HFR / "candidates.json").read_text()):
        for hit in r["matches"]:
            if hit["manager_has_activist"]:
                key = "HFR:" + hit["firm_id"]
                evidence[r["accession"]].add(key)
                names[key].update(hit["hfr_names"])
    for r in json.loads((SUP / "candidates.json").read_text()):
        for hit in r["matches"]:
            key = "Supplement:" + hit["manager"]
            evidence[r["accession"]].add(key)
            names[key].add(hit["manager"])
    labels = {k: " / ".join(sorted(v)) for k, v in names.items()}
    registry = {
        r["accession"]: r for line in REG.read_text().splitlines() if (r := json.loads(line))
    }
    old = json.loads((BASE / "outcomes.json").read_text())
    summary = json.loads((BASE / "summary.json").read_text())
    protected = set(
        json.loads(
            (BASE.parent / "20260924-development-v4/human-review-protection.json").read_text()
        )["issuers"]
    )
    events = {}
    results = {}
    company_names = {}
    for horizon, rows in old.items():
        selected = []
        for r in rows:
            if not r["focused"] or r["excess"] is None:
                continue
            assert r["issuer"] not in protected and r["exit"] <= "2023-12-29"
            managers = sorted(set().union(*(evidence[a] for a in r["accessions"])))
            assert managers, r["accession"]
            companies = sorted(
                {
                    s["name"]
                    for a in r["accessions"]
                    for s in registry[a]["subjects"]
                    if s["cik"] == r["issuer"]
                }
            )
            company = " / ".join(companies) or r["issuer"]
            company_names[r["issuer"]] = company
            selected.append(dict(r, managers=managers, company=company, year=r["entry"][:4]))
        assert summarize(selected) == summary[horizon]["focused"]["russell"] | {
            "scheduled": len(selected),
            "statuses": {"calculated_common_sample": len(selected)},
        }
        events[horizon] = selected
        results[horizon] = diagnostic(selected)
        for groups in results[horizon]["groups"].values():
            assert (
                abs(
                    sum(v["contribution"] for v in groups.values())
                    - results[horizon]["overall"]["mean"]
                )
                < 1e-12
            )
        results[horizon]["source_groups"] = {
            kind: simple(
                [
                    r
                    for r in selected
                    if (
                        "mixed"
                        if any(k.startswith("HFR:") for k in r["managers"])
                        and any(k.startswith("Supplement:") for k in r["managers"])
                        else "HFR"
                        if all(k.startswith("HFR:") for k in r["managers"])
                        else "supplement"
                    )
                    == kind
                ]
            )
            for kind in ["HFR", "supplement", "mixed"]
        }
    keys = lambda r: (r["accession"], r["entry"], r["permno"])
    common = set.intersection(*({keys(r) for r in rows} for rows in events.values()))
    paired = {
        h: summarize([r for r in events[h] if keys(r) in common]) for h in ["63", "126", "252"]
    }
    for name, value in [
        ("events.json", events),
        ("diagnostics.json", results),
        ("manager-labels.json", labels),
        ("paired-horizons.json", paired),
        (
            "verification.json",
            dict(
                original_focused_statistics_reproduced=True,
                all_manager_links_present=True,
                contributions_reconcile=True,
                protected_issuers_excluded=True,
                no_outcomes_after_2023=True,
            ),
        ),
    ]:
        freeze(OUT / name, encode(value))
    freeze(OUT / "index.html", render(results, events, labels, company_names, paired))
    sources = [
        BASE / "outcomes.json",
        BASE / "summary.json",
        BASE / "provenance.json",
        HFR / "candidates.json",
        HFR / "provenance.json",
        SUP / "candidates.json",
        REG,
        PROTOCOL,
    ]
    freeze(
        OUT / "provenance.json",
        encode(
            dict(
                inputs={str(p.relative_to(ROOT)): digest(p) for p in sources},
                outputs={
                    str(p.relative_to(OUT)): digest(p)
                    for p in sorted(OUT.rglob("*"))
                    if p.is_file() and p.name != "provenance.json"
                },
            )
        ),
    )
    for h, d in results.items():
        print(h, encode({k: v for k, v in d.items() if k != "groups"}))
        for dim in ["manager", "year"]:
            print(dim, encode({labels.get(k, k): v for k, v in d["groups"][dim].items()}))
    print("PAIRED", encode(paired))


if __name__ == "__main__":
    main()
