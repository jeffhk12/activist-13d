"""Build dated HFR performance panels and fund/manager peer percentiles.

Inputs: preserved 35-snapshot HFR ZIP and ingestion manifest; frozen v1 protocol.
Outputs: source-row panels, fund/manager CSVs, coverage, provenance and HTML.
Formula: geometric CAGR; sample volatility; zero-hurdle mean/stdev ratio;
monthly peak-to-trough drawdown; percentile 100*(midrank-1)/(N-1).
Tier: 2. Refuse missing months, conflicting duplicates and ambiguous source units.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python
 scripts/data_collection/build_hfr_percentiles.py --root PROJECT --out NEW_RUN
 --protocol research/protocol/hfr-percentiles-v1.md --workers 3
"""

from __future__ import annotations

import argparse
import calendar
import csv
import gzip
import hashlib
import html
import io
import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

CONTRACT = {
    "version": "hfr-percentiles-v1",
    "ror_divisor": 100,
    "horizons": [12, 36, 60],
    "minimum_peers": 8,
    "currency": "USD",
    "fee_basis": "Net of All Fees",
    "primary_metric": "cagr_36",
    "risk_free": "zero_hurdle_not_cash_adjusted",
    "cutoff": "last_month_before_min_vendor_delivery",
    "percentile": "100*(average_ascending_rank-1)/(n-1)",
    "representative": "longest_contiguous_history_then_recent_usd_assets_then_id",
}
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
FIELDS = [
    "Fund_ID",
    "Fund",
    "Firm_ID",
    "Firm",
    "Family_ID",
    "Main_Strategy",
    "Sub_Strategy",
    "Fund_Status",
    "Returns_Denomination",
    "Reporting_Style",
    "Reporting",
    "Structure",
    "Product_Class",
    "Inception",
    "Date_Added_to_DB",
    "Leverage",
    "Fund_Assets_Denomin",
    "Firm_Assets_Denomin",
    "Firm_Assets",
    "Firm_Assets_as_of",
    "Management_Fee",
    "Incentive_Fee",
    "Lockup",
    "Redemptions",
    "Regional_Investment_Focus",
    "Firm_SEC_Number",
    "Firm_IARD_CRD_Number",
    "Strategy_Description",
]


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_hash(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def freeze(path, content):
    path = Path(path)
    data = content.encode() if isinstance(content, str) else content
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"Frozen output differs: {path}")
    else:
        with path.open("xb") as handle:
            handle.write(data)


def write_csv(path, rows):
    rows = list(rows)
    fields = list(dict.fromkeys(k for row in rows for k in row))
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        clean = {
            k: json.dumps(v, ensure_ascii=False, sort_keys=True)
            if isinstance(v, (dict, list))
            else v
            for k, v in row.items()
        }
        writer.writerow(clean)
    data = buf.getvalue().encode("utf-8")
    if str(path).endswith(".gz"):
        data = gzip.compress(data, mtime=0)
    freeze(path, data)


def text(value):
    if value is None or value == "":
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def number(value):
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None


def excel_date(value, mode=0):
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value.date() if isinstance(value, datetime) else value
    n = number(value)
    if n is not None:
        if not 1 <= n <= 100000:
            return None
        base = date(1904, 1, 1) if mode else date(1899, 12, 30)
        return base + timedelta(days=int(n))
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(str(value), fmt).date()
        except ValueError:
            pass
    return None


def month_index(d):
    return d.year * 12 + d.month - 1


def month_end(index):
    year, month = divmod(index, 12)
    return date(year, month + 1, calendar.monthrange(year, month + 1)[1])


def cutoff_for(snapshot):
    stamp = min(
        date.fromisoformat(snapshot["vendor_datestamp"]),
        date.fromisoformat(snapshot["delivery_date_proxy"]),
    )
    return month_end(month_index(stamp) - 1)


def workbook_rows(data, filename):
    """Yield source sheet, row, datemode, header-keyed cells; XLS/XLSX only."""
    if filename.lower().endswith(".xls"):
        import xlrd

        book = xlrd.open_workbook(file_contents=data, on_demand=True, logfile=io.StringIO())
        if book.nsheets != 1:
            raise ValueError(f"Multiple sheets in {filename}")
        sheet = book.sheet_by_index(0)
        headers = [str(x).strip() for x in sheet.row_values(0)]
        if len(headers) != len(set(headers)):
            raise ValueError("Duplicate headers")
        try:
            for idx in range(1, sheet.nrows):
                values = sheet.row_values(idx)
                if any(x != "" for x in values):
                    yield (
                        sheet.name,
                        idx + 1,
                        book.datemode,
                        dict(zip(headers, values, strict=True)),
                    )
        finally:
            book.release_resources()
        return
    with ZipFile(io.BytesIO(data)) as book:
        wb = ET.fromstring(book.read("xl/workbook.xml"))
        sheets = wb.findall("m:sheets/m:sheet", NS)
        if len(sheets) != 1:
            raise ValueError("Multiple workbook sheets")
        prop = wb.find("m:workbookPr", NS)
        mode = int(prop is not None and prop.get("date1904") in ("1", "true"))
        sheet = sheets[0]
        rid = sheet.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        rels = ET.fromstring(book.read("xl/_rels/workbook.xml.rels"))
        target = next(r.get("Target") for r in rels if r.get("Id") == rid)
        target = target.lstrip("/") if target.startswith("/") else "xl/" + target
        shared = (
            [
                "".join(t.text or "" for t in s.iter() if t.tag.endswith("}t"))
                for s in ET.fromstring(book.read("xl/sharedStrings.xml")).findall("m:si", NS)
            ]
            if "xl/sharedStrings.xml" in book.namelist()
            else []
        )
        headers = None
        with book.open(target) as handle:
            for _, row in ET.iterparse(handle, events=["end"]):
                if row.tag != "{" + NS["m"] + "}row":
                    continue
                values = {}
                for cell in row.findall("m:c", NS):
                    if cell.find("m:f", NS) is not None:
                        raise ValueError("Unexpected formula in source workbook")
                    col = re.sub(r"\d", "", cell.get("r"))
                    node = cell.find("m:v", NS)
                    val = node.text if node is not None else None
                    if cell.get("t") == "s" and val is not None:
                        val = shared[int(val)]
                    if cell.get("t") == "inlineStr":
                        val = "".join(t.text or "" for t in cell.iter() if t.tag.endswith("}t"))
                    values[col] = val
                if headers is None:
                    headers = {c: str(v).strip() for c, v in values.items()}
                    if len(set(headers.values())) != len(headers):
                        raise ValueError("Duplicate headers")
                else:
                    yield (
                        sheet.get("name"),
                        int(row.get("r")),
                        mode,
                        {headers[c]: v for c, v in values.items() if c in headers},
                    )
                row.clear()


def put_observation(panel, key, value, source):
    if key not in panel:
        panel[key] = {"value": value, "conflict": False, "sources": [source]}
        return "new"
    old = panel[key]
    old["sources"].append(source)
    if old["value"] != value:
        old["conflict"] = True
        old["value"] = None
        return "conflict"
    return "duplicate"


def metric_values(returns):
    if not returns or any(r is None or not math.isfinite(r) or r < -1 for r in returns):
        return None
    n = len(returns)
    wealth, peak, dd = 1.0, 1.0, 0.0
    for r in returns:
        wealth *= 1 + r
        peak = max(peak, wealth)
        dd = min(dd, wealth / peak - 1)
    sigma = statistics.stdev(returns) if n > 1 else 0.0
    return {
        "cagr": wealth ** (12 / n) - 1,
        "cumulative": wealth - 1,
        "volatility": sigma * math.sqrt(12),
        "max_drawdown": dd,
        "zero_hurdle_ratio": statistics.mean(returns) / sigma * math.sqrt(12)
        if sigma > 1e-14
        else None,
        "downside_deviation": math.sqrt(sum(min(r, 0) ** 2 for r in returns) / n * 12),
        "positive_month_fraction": sum(r > 0 for r in returns) / n,
    }


def trailing_values(series, end, n):
    values = [series.get(m) for m in range(end - n + 1, end + 1)]
    return values if all(v is not None for v in values) else None


def percentiles(values, higher=True, minimum=8):
    good = [
        (k, v if higher else -v) for k, v in values.items() if v is not None and math.isfinite(v)
    ]
    n = len(good)
    if n < minimum:
        return {}, n
    ordered = sorted(v for _, v in good)
    positions = defaultdict(list)
    for idx, value in enumerate(ordered):
        positions[value].append(idx)
    return {k: 100 * statistics.mean(positions[v]) / (n - 1) for k, v in good}, n


def representative(rows):
    def key(row):
        identifier = str(row["fund_id"])
        ident = (0, int(identifier)) if identifier.isdigit() else (1, identifier)
        return (-row["contiguous_months"], -(row.get("selection_assets") or 0), ident)

    return min(rows, key=key)


def group_names(row):
    sub = row["sub_strategy"] or "Unspecified"
    return ["Event-Driven", sub]


def ranking_rows(funds, level):
    groups = defaultdict(list)
    for fund in funds:
        if fund["ranking_base_eligible"]:
            for group in group_names(fund):
                groups[group].append(fund)
    ranked, coverage = [], []
    for group, products in sorted(groups.items()):
        if level == "manager":
            firms = defaultdict(list)
            for p in products:
                firms[p["firm_id"]].append(p)
            chosen = [
                dict(representative(items), candidate_products=len(items))
                for _, items in sorted(firms.items())
            ]
        else:
            chosen = [dict(p, candidate_products=1) for p in products]
        for row in chosen:
            row["peer_group"] = group
            row["rank_level"] = level
        for horizon in CONTRACT["horizons"]:
            for metric, higher in [
                ("cagr", True),
                ("zero_hurdle_ratio", True),
                ("volatility", False),
                ("max_drawdown", True),
                ("downside_deviation", False),
            ]:
                field = f"{metric}_{horizon}"
                ranks, n = percentiles({r["fund_id"]: r.get(field) for r in chosen}, higher)
                for row in chosen:
                    row[field + "_percentile"] = ranks.get(row["fund_id"])
                    row[field + "_peer_n"] = n
        for row in chosen:
            pct = row.get("cagr_36_percentile")
            row["primary_top_quartile"] = (pct >= 75) if pct is not None else None
            row["primary_rank_status"] = (
                "ranked"
                if pct is not None
                else (
                    "incomplete_36_month_history"
                    if row.get("cagr_36") is None
                    else "fewer_than_8_peers"
                )
            )
        coverage.append(
            {
                "quarter": funds[0]["quarter"],
                "level": level,
                "peer_group": group,
                "base_eligible_products": len(products),
                "representatives_or_products": len(chosen),
                "complete_36_month": sum(r.get("cagr_36") is not None for r in chosen),
                "ranked_36_month": sum(r.get("cagr_36_percentile") is not None for r in chosen),
                "top_quartile": sum(r.get("primary_top_quartile") is True for r in chosen),
            }
        )
        ranked.extend(chosen)
    return ranked, coverage


def process_snapshot(args):
    root, out, snapshot = args
    root, out = Path(root), Path(out)
    q = snapshot["quarter"]
    cutoff = cutoff_for(snapshot)
    end = month_index(cutoff)
    counters = Counter()
    members_used = []
    source_inventory = {m["member"]: m["sha256"] for m in snapshot["members"]}
    with ZipFile(
        root / "data/raw/hfr/2026-09-24-quarterly/HFR_QuarterEnd_Excel_2018Q1-2026Q3.zip"
    ) as outer:
        nested = outer.read(snapshot["archive_member"])
    if digest(nested) != snapshot["nested_sha256"]:
        raise ValueError("Nested archive hash mismatch")
    with ZipFile(io.BytesIO(nested)) as inner:

        def read(name):
            raw = inner.read(name)
            if digest(raw) != source_inventory[name]:
                raise ValueError(f"Member hash mismatch {name}")
            members_used.append({"member": name, "sha256": source_inventory[name]})
            return raw

        funds = {}
        for sheet, row, mode, cells in workbook_rows(
            read(snapshot["fund_member"]), snapshot["fund_member"]
        ):
            if text(cells.get("Main_Strategy")) != "Event-Driven":
                continue
            fid = text(cells["Fund_ID"])
            if not fid or fid in funds:
                raise ValueError("Missing/duplicate fund id")
            fields = {k: text(cells.get(k)) for k in FIELDS}
            fields.update(
                source_row=row,
                source_sheet=sheet,
                source_member=snapshot["fund_member"],
                date_mode=mode,
            )
            funds[fid] = fields
        assert len(funds) == snapshot["event_driven_fund_rows"]
        rpanel, apanel, rejected = {}, {}, []
        for name in sorted(inner.namelist()):
            kind = (
                "returns"
                if re.search(r"(Excel_Ror_\d+\.xls|HFR_HFRDB_EXCEL_Returns\.xlsx)$", name)
                else (
                    "assets"
                    if re.search(r"(Excel_Assets_\d+\.xls|HFR_HFRDB_EXCEL_Assets\.xlsx)$", name)
                    else None
                )
            )
            if kind is None:
                continue
            panel = rpanel if kind == "returns" else apanel
            for sheet, row, mode, cells in workbook_rows(read(name), name):
                counters[kind + "_all_source_rows"] += 1
                fid = text(cells.get("Fund_ID"))
                if fid not in funds:
                    continue
                counters[kind + "_ed_source_rows"] += 1
                d = excel_date(cells.get("Date"), mode)
                raw = (
                    cells.get("ROR", cells.get("Performance"))
                    if kind == "returns"
                    else cells.get("Assets")
                )
                n = number(raw)
                source = {
                    "member": name,
                    "sheet": sheet,
                    "row": row,
                    "raw_date": text(cells.get("Date")),
                    "raw_value": text(raw),
                }
                reason = None
                if d is None:
                    reason = "invalid_date"
                elif d > cutoff:
                    reason = "after_common_cutoff"
                elif kind == "returns" and d != month_end(month_index(d)):
                    reason = "not_month_end"
                elif n is None:
                    reason = "missing_or_nonfinite_value"
                elif kind == "returns" and n < -100:
                    reason = "return_below_minus_100"
                elif kind == "assets" and n < 0:
                    reason = "negative_assets"
                if reason:
                    counters[kind + "_" + reason] += 1
                    rejected.append(
                        dict(quarter=q, fund_id=fid, kind=kind, reason=reason, **source)
                    )
                    continue
                key = (fid, d.isoformat())
                status = put_observation(panel, key, n / 100 if kind == "returns" else n, source)
                counters[kind + "_" + status] += 1
    returns = defaultdict(dict)
    assets = defaultdict(dict)
    for (fid, day), obs in rpanel.items():
        if not obs["conflict"]:
            returns[fid][month_index(date.fromisoformat(day))] = obs["value"]
    for (fid, day), obs in apanel.items():
        if not obs["conflict"]:
            assets[fid][date.fromisoformat(day)] = obs["value"]
    metrics = []
    for fid, f in sorted(funds.items()):
        series = returns[fid]
        count, idx = 0, end
        while idx in series:
            count += 1
            idx -= 1
        reasons = []
        if f["Fund_Status"] != "Active":
            reasons.append("not_active")
        if f["Returns_Denomination"] != "USD":
            reasons.append("non_usd")
        if f["Reporting_Style"] != "Net of All Fees":
            reasons.append("not_net_all_fees")
        if not f["Firm_ID"]:
            reasons.append("missing_firm_id")
        reporting = (f["Reporting"] or "").lower()
        if reporting and "month" not in reporting:
            reasons.append("explicit_nonmonthly_reporting")
        if count == 0:
            reasons.append("no_valid_return_at_common_cutoff")
        a = assets[fid]
        latest = max(a) if a else None
        asset_value = a[latest] if latest else None
        age = (cutoff - latest).days if latest else None
        recent_assets = (
            asset_value
            if latest and month_index(latest) >= end - 3 and f["Fund_Assets_Denomin"] == "USD"
            else None
        )
        added = excel_date(f["Date_Added_to_DB"], f["date_mode"])
        inception = excel_date(f["Inception"], f["date_mode"])
        row = {
            "quarter": q,
            "vendor_datestamp": snapshot["vendor_datestamp"],
            "delivery_proxy": snapshot["delivery_date_proxy"],
            "availability_verified": False,
            "cutoff": cutoff.isoformat(),
            "fund_id": fid,
            "fund": f["Fund"],
            "firm_id": f["Firm_ID"],
            "firm": f["Firm"],
            "family_id": f["Family_ID"],
            "sub_strategy": f["Sub_Strategy"],
            "return_currency": f["Returns_Denomination"],
            "fee_basis": f["Reporting_Style"],
            "reporting_frequency_source": f["Reporting"],
            "contiguous_months": count,
            "total_valid_months": len(series),
            "ranking_base_eligible": not reasons,
            "exclusion_reasons": ";".join(reasons),
            "latest_assets_millions": asset_value,
            "assets_currency": f["Fund_Assets_Denomin"],
            "assets_date": latest.isoformat() if latest else None,
            "assets_age_days": age,
            "selection_assets": recent_assets,
            "inception": inception.isoformat() if inception else None,
            "date_added_to_db": added.isoformat() if added else None,
            "months_before_db_addition": sum(month_end(m) < added for m in series)
            if added
            else None,
            "source_fund_member": f["source_member"],
            "source_fund_row": f["source_row"],
            "source_fund_sheet": f["source_sheet"],
            "structure": f["Structure"],
            "product_class": f["Product_Class"],
            "leverage": f["Leverage"],
            "management_fee_raw": f["Management_Fee"],
            "incentive_fee_raw": f["Incentive_Fee"],
            "lockup": f["Lockup"],
            "redemptions": f["Redemptions"],
            "regional_focus": f["Regional_Investment_Focus"],
            "sec_number": f["Firm_SEC_Number"],
            "crd_number": f["Firm_IARD_CRD_Number"],
        }
        for horizon in CONTRACT["horizons"]:
            values = trailing_values(series, end, horizon)
            stats = metric_values(values) if values is not None else None
            for metric in (
                "cagr",
                "cumulative",
                "volatility",
                "max_drawdown",
                "zero_hurdle_ratio",
                "downside_deviation",
                "positive_month_fraction",
            ):
                row[f"{metric}_{horizon}"] = stats[metric] if stats else None
            row[f"observed_months_{horizon}"] = sum(
                m in series for m in range(end - horizon + 1, end + 1)
            )
        prior_end = month_end(end - 12)
        row["assets_growth_12"] = (
            a[cutoff] / a[prior_end] - 1 if cutoff in a and a.get(prior_end, 0) > 0 else None
        )
        prev = month_end(end - 1)
        row["approx_flow_latest_millions"] = (
            a[cutoff] - a[prev] * (1 + series[end])
            if cutoff in a
            and prev in a
            and end in series
            and f["Fund_Assets_Denomin"] == f["Returns_Denomination"]
            else None
        )
        metrics.append(row)
    outq = out / "snapshots" / q
    fundranks, fc = ranking_rows(metrics, "fund")
    managers, mc = ranking_rows(metrics, "manager")
    summary = {
        "quarter": q,
        "cutoff": cutoff.isoformat(),
        "delivery_proxy": snapshot["delivery_date_proxy"],
        "source_ed_funds": len(funds),
        "source_ed_firms": len({f["Firm_ID"] for f in funds.values() if f["Firm_ID"]}),
        "source_activist_firms": len(
            {
                f["Firm_ID"]
                for f in funds.values()
                if f["Firm_ID"] and f["Sub_Strategy"] == "Activist"
            }
        ),
        "base_eligible_funds": sum(r["ranking_base_eligible"] for r in metrics),
        "exclusion_combinations": dict(
            Counter(r["exclusion_reasons"] for r in metrics if r["exclusion_reasons"])
        ),
        "counters": dict(counters),
        "members_used": members_used,
        "return_key_count": len(rpanel),
        "asset_key_count": len(apanel),
        "peer_coverage": fc + mc,
    }
    assert summary["source_ed_firms"] == snapshot["event_driven_firm_ids"]
    assert summary["source_activist_firms"] == snapshot["activist_firm_ids"]
    for kind, panel in [("returns", rpanel), ("assets", apanel)]:
        rows = [
            dict(
                quarter=q,
                fund_id=fid,
                date=day,
                value=o["value"],
                conflict=o["conflict"],
                sources=o["sources"],
            )
            for (fid, day), o in sorted(panel.items())
        ]
        write_csv(outq / f"{kind}.csv.gz", rows)
    write_csv(outq / "rejected.csv.gz", rejected)
    freeze(outq / "fund_metadata.json", encode(funds))
    write_csv(outq / "fund_metrics.csv", metrics)
    freeze(outq / "summary.json", encode(summary))
    freeze(outq / "manager_scorecards.json", encode(managers))
    write_csv(outq / "fund_percentiles.csv", fundranks)
    return summary, managers


def add_persistence(rows):
    prior = defaultdict(list)
    last = {}
    for row in sorted(rows, key=lambda r: (r["quarter"], r["peer_group"], r["firm_id"])):
        key = (row["peer_group"], row["firm_id"])
        observations = prior[key]
        row["prior_ranked_snapshots"] = len(observations)
        row["prior_top_quartile_share"] = (
            sum(observations) / len(observations) if observations else None
        )
        row["prior_12_ranked_snapshots"] = len(observations[-12:])
        row["prior_12_top_quartile_share"] = (
            sum(observations[-12:]) / len(observations[-12:]) if observations else None
        )
        row["representative_changed_since_prior_observation"] = (
            key in last and last[key] != row["fund_id"]
        )
        last[key] = row["fund_id"]
        if row["primary_top_quartile"] is not None:
            observations.append(row["primary_top_quartile"])


def report(out, summaries, managers):
    """Self-contained local scorecard; all figures derive from saved output rows."""
    latest = max(s["quarter"] for s in summaries)
    chosen = [r for r in managers if r["quarter"] == latest]
    cards = []
    for group in ("Activist", "Event-Driven"):
        rows = [r for r in chosen if r["peer_group"] == group]
        ranked = sum(r["primary_top_quartile"] is not None for r in rows)
        top = sum(r["primary_top_quartile"] is True for r in rows)
        cards.append(
            f'<article><h3>{group}</h3><strong class="big">{ranked}</strong><p>ranked manager proxies; {top} in the top quartile.<br>{len(rows)} representative products before the three-year history requirement.</p></article>'
        )
    payload_fields = [
        "quarter",
        "cutoff",
        "peer_group",
        "firm",
        "firm_id",
        "fund",
        "fund_id",
        "candidate_products",
        "cagr_12",
        "cagr_36",
        "cagr_60",
        "cagr_36_percentile",
        "cagr_36_peer_n",
        "volatility_36",
        "volatility_36_percentile",
        "max_drawdown_36",
        "max_drawdown_36_percentile",
        "zero_hurdle_ratio_36",
        "zero_hurdle_ratio_36_percentile",
        "downside_deviation_36",
        "latest_assets_millions",
        "assets_date",
        "assets_currency",
        "contiguous_months",
        "primary_top_quartile",
        "primary_rank_status",
        "prior_ranked_snapshots",
        "prior_top_quartile_share",
        "representative_changed_since_prior_observation",
    ]
    payload = json.dumps(
        [{k: r.get(k) for k in payload_fields} for r in managers],
        ensure_ascii=False,
        allow_nan=False,
    ).replace("<", "\\u003c")
    covrows = []
    for s in summaries:
        counts = {r["peer_group"]: r for r in s["peer_coverage"] if r["level"] == "manager"}
        covrows.append(
            "<tr>"
            + "".join(
                f"<td>{html.escape(str(v))}</td>"
                for v in [
                    s["quarter"],
                    s["cutoff"],
                    s["source_ed_funds"],
                    s["source_ed_firms"],
                    s["base_eligible_funds"],
                    counts.get("Event-Driven", {}).get("ranked_36_month", 0),
                    counts.get("Activist", {}).get("ranked_36_month", 0),
                ]
            )
            + "</tr>"
        )
    body = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>HFR manager percentile scorecards</title><style>
    *{box-sizing:border-box}body{margin:0;background:#f3f4f0;color:#173341;font:16px/1.6 system-ui,sans-serif}main{max-width:1400px;margin:auto;padding:35px 25px}h1{font-size:40px;line-height:1.15}h2{margin-top:36px}a{color:#136b76}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}article,section{background:white;border:1px solid #d8e2df;padding:22px;border-radius:10px;margin:15px 0}.big{font-size:38px;color:#12685b}.note{background:#fff0d7;border-left:4px solid #aa792f;padding:18px}.small{font-size:13px;color:#526875}.controls{display:flex;gap:18px;flex-wrap:wrap}select,input,button{font:inherit;padding:8px;border:1px solid #91a8aa;border-radius:5px}label{display:flex;flex-direction:column;font-size:13px;font-weight:600}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:12px;text-align:left;border-bottom:1px solid #dce3e1;vertical-align:top}th{background:#e9efec;white-space:nowrap}td.num{text-align:right;white-space:nowrap}.top{background:#eaf5ed}.muted{color:#63727a}summary{cursor:pointer;font-weight:700}.status{padding:15px 0;font-weight:600}@media(max-width:700px){.grid{grid-template-columns:1fr}h1{font-size:31px}main{padding:20px 14px}}@media print{.controls,button{display:none}.scroll{overflow:visible}table{font-size:9px}th,td{padding:5px}section,article{break-inside:avoid}}</style></head><body><main>
    <p class="small">13D research · September 30, 2026 · Exploratory manager-selection preparation</p>
    <h1>Which managers had stronger fund track records?</h1>
    <p>These scorecards rank historically available HFR fund records within Activist and Event-Driven peer groups. They establish a reproducible candidate selection signal. They do <strong>not</strong> establish that following the managers’ subsequent 13D disclosures outperforms.</p>
    <p class="note"><strong>Research percentiles, not official HFR ratings.</strong> One representative USD, net-of-all-fees product per Firm_ID and peer group. A fund proxy is not a consolidated manager return or a verified economic-manager identity. Delivery dates are unverified availability proxies. All 35 snapshot universes contain active funds; complete dead-fund coverage is not established.</p>
    <h2>Latest supplied snapshot: LATEST</h2><p>Common return endpoint: CUTOFF. Historical snapshots and all sub-strategies are available below. The Activist group overlaps Event-Driven; do not add their counts. Current 2026 rankings must not be used retrospectively in the 2018–2025 investment tests.</p><div class="grid">CARDS</div>
    <section><h2>Manager scorecards</h2><p>100 means the best percentile. Primary rank: three-year annualized return. At least eight complete peer histories are required. Ties share a percentile, so the number above the 75th percentile can differ from exactly one quarter.</p>
    <div class="controls"><label>Snapshot<select id="quarter"></select></label><label>Peer group<select id="group"></select></label><label>Search manager or fund<input id="search" placeholder="Name or HFR ID"></label><label>Show<select id="filter"><option value="all">All representatives</option><option value="top">Top quartile</option><option value="unranked">Unranked</option></select></label></div><div id="status" class="status"></div>
    <div class="scroll"><table><thead><tr><th>Manager / representative fund</th><th>Return percentile / peers</th><th>1-year return</th><th>3-year annualized</th><th>5-year annualized</th><th>3-year volatility</th><th>3-year max drawdown</th><th>Zero-hurdle ratio</th><th>Assets ($m)</th><th>Prior top-quartile share</th></tr></thead><tbody id="rows"></tbody></table></div></section>
    <section><h2>How the manager proxy is selected</h2><ol><li>Keep active Event-Driven products reporting USD returns net of all fees, with a manager identifier and a valid return at the common endpoint. Explicit non-monthly reporters are excluded.</li><li>Within each manager and peer group, choose the longest uninterrupted monthly history, then the largest recent USD assets, then lowest Fund_ID. Return magnitude never selects the representative. Different peer groups can select different funds.</li><li>Require exactly 12, 36 or 60 consecutive month-end observations for each metric. Gaps remain gaps. No newer snapshot fills an older one.</li><li>Calculate percentiles among qualifying representatives. Separately retain product-level metrics and percentiles, where share classes can affect peer weights.</li></ol><p>Asset figures are vendor-reported millions of the stated currency; manager rankings use USD-return products. Assets displayed here can be in another currency and are then explicitly labeled. Asset dates and representative changes remain visible. Approximate flows in the fund data are not verified subscriptions or redemptions.</p></section>
    <section><h2>What the metrics mean</h2><p>Return is geometric growth. Volatility uses the sample standard deviation of monthly returns, annualized. Drawdown includes the starting value and is measured at month ends, so it can miss intramonth losses. A zero-hurdle ratio is annualized average return divided by volatility with a 0% hurdle. <strong>It is not an excess-return Sharpe ratio:</strong> no historically verified cash-rate series was applied.</p><p>Prior top-quartile share uses only earlier snapshots with a valid three-year rank. It excludes the current snapshot. Overlapping return windows and changing peers mean this is descriptive persistence, not independent evidence of skill. All metrics are fund-level returns, not the return from buying a disclosed stock.</p></section>
    <section><h2>Coverage across all supplied snapshots</h2><p>ED fund rows count products; ED firms count nonblank source Firm_IDs. Eligible products pass currency, fee, manager, reporting and endpoint checks. Ranked manager counts additionally require three-year history and enough peers.</p><div class="scroll"><table><thead><tr><th>Snapshot</th><th>Return endpoint</th><th>ED products</th><th>ED firm IDs</th><th>Eligible products</th><th>Ranked ED proxies</th><th>Ranked activist proxies</th></tr></thead><tbody>COVERAGE</tbody></table></div></section>
    <section><h2>Next investment test</h2><p>Validate manager-to-SEC links, inspect representative choices and unresolved coverage, then freeze a top-quartile following protocol. Test subsequent eligible disclosures against all-manager following under identical entry, holding, benchmark and portfolio rules. An attractive fund percentile is a proposed input; its usefulness for 13D selection remains untested. Aratana portfolio accounting remains a separate Phase 1 dependency.</p>
    <h3>Downloads and audit trail</h3><ul><li><a href="manager-scorecards.csv">All historical manager scorecards (CSV)</a></li><li><a href="latest-manager-scorecards.csv">Latest manager scorecards (CSV)</a></li><li><a href="coverage.csv">Peer coverage and denominators (CSV)</a></li><li><a href="summary.json">Run summary</a> · <a href="provenance.json">Source and calculation provenance</a> · <a href="validation.json">Validation results</a></li><li><a href="protocol.md">Frozen calculation protocol</a></li><li><a href="snapshots/">Per-snapshot return/asset panels, fund metrics, product ranks and refusal records</a></li><li><a href="../../../../START-HERE.html">Project start page</a></li></ul><p class="small">Source: your preserved HFR quarterly archive. Each normalized observation retains workbook, sheet and row; source hashes identify the exact vintage. Missing values are not zero and missing manager identities are not non-activist classifications.</p></section>
    <script type="application/json" id="data">PAYLOAD</script><script>
    const data=JSON.parse(document.getElementById('data').textContent);const q=document.getElementById('quarter'),g=document.getElementById('group'),s=document.getElementById('search'),f=document.getElementById('filter');
    const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));const pct=x=>x==null?'—':(100*x).toFixed(2)+'%';const num=x=>x==null?'—':Number(x).toFixed(2);
    for(const v of [...new Set(data.map(r=>r.quarter))].sort().reverse())q.add(new Option(v,v));for(const v of ['Activist','Event-Driven',...[...new Set(data.map(r=>r.peer_group))].filter(x=>!['Activist','Event-Driven'].includes(x)).sort()])g.add(new Option(v,v));
    function draw(){const base=data.filter(r=>r.quarter===q.value&&r.peer_group===g.value);const rows=base.filter(r=>(r.firm+' '+r.fund+' '+r.firm_id+' '+r.fund_id).toLowerCase().includes(s.value.toLowerCase())&&(f.value==='all'||(f.value==='top'?r.primary_top_quartile===true:r.cagr_36_percentile==null))).sort((a,b)=>(b.cagr_36_percentile??-1)-(a.cagr_36_percentile??-1)||String(a.firm).localeCompare(String(b.firm)));
    document.getElementById('status').textContent=rows.length+' shown / '+base.length+' representative products · '+(base[0]?.cutoff??'No eligible products')+' endpoint';
    document.getElementById('rows').innerHTML=rows.map(r=>{
      const rank = r.cagr_36_percentile == null
        ? `Unranked<br><span class="small">${esc(r.primary_rank_status.split('_').join(' '))}</span>`
        : `${num(r.cagr_36_percentile)} / ${r.cagr_36_peer_n}`;
      return `<tr class="${r.primary_top_quartile ? 'top' : ''}">
        <td><strong>${esc(r.firm)}</strong><br>${esc(r.fund)}<br><span class="small">Firm ${esc(r.firm_id)} · Fund ${esc(r.fund_id)} · ${r.contiguous_months} consecutive months${r.representative_changed_since_prior_observation ? ' · Representative changed' : ''}</span></td>
        <td class="num">${rank}</td><td class="num">${pct(r.cagr_12)}</td>
        <td class="num">${pct(r.cagr_36)}</td><td class="num">${pct(r.cagr_60)}</td>
        <td class="num">${pct(r.volatility_36)}</td><td class="num">${pct(r.max_drawdown_36)}</td>
        <td class="num">${num(r.zero_hurdle_ratio_36)}</td>
        <td class="num">${num(r.latest_assets_millions)}<br><span class="small">${esc(r.assets_currency)} ${esc(r.assets_date)}</span></td>
        <td class="num">${pct(r.prior_top_quartile_share)}<br><span class="small">${r.prior_ranked_snapshots} prior ranks</span></td></tr>`;
    }).join('');}
    [q,g,s,f].forEach(e=>e.addEventListener('input',draw));draw();</script></main></body></html>"""
    for key, value in [
        ("LATEST", latest),
        ("CUTOFF", next(s["cutoff"] for s in summaries if s["quarter"] == latest)),
        ("CARDS", "".join(cards)),
        ("COVERAGE", "".join(covrows)),
        ("PAYLOAD", payload),
    ]:
        body = body.replace(key, value)
    freeze(out / "index.html", body)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    manifest_path = args.root / "research/runs/hfr-quarterly/20260924-v1/manifest.json"
    manifest = json.loads(manifest_path.read_text())
    archive = args.root / "data/raw/hfr/2026-09-24-quarterly/HFR_QuarterEnd_Excel_2018Q1-2026Q3.zip"
    assert file_hash(archive) == manifest["archive_sha256"]
    code_hash = file_hash(Path(__file__))
    protocol_hash = file_hash(args.protocol)
    freeze(args.out / "protocol.md", args.protocol.read_bytes())
    freeze(args.out / "contract.json", encode(CONTRACT))
    freeze(
        args.out / "input-contract.json",
        encode(
            {
                "code_sha256": code_hash,
                "protocol_sha256": protocol_hash,
                "manifest_sha256": file_hash(manifest_path),
                "archive_sha256": manifest["archive_sha256"],
            }
        ),
    )
    jobs, results = [], []
    for s in manifest["snapshots"]:
        p = args.out / "snapshots" / s["quarter"]
        if (p / "manager_scorecards.json").exists() and (p / "fund_percentiles.csv").exists():
            results.append(
                (
                    json.loads((p / "summary.json").read_text()),
                    json.loads((p / "manager_scorecards.json").read_text()),
                )
            )
            print(s["quarter"], "verified-contract checkpoint", flush=True)
        else:
            jobs.append((str(args.root), str(args.out), s))
    with ProcessPoolExecutor(max_workers=max(1, min(args.workers, 3))) as pool:
        for result in pool.map(process_snapshot, jobs):
            results.append(result)
            s = result[0]
            print(
                s["quarter"],
                "complete",
                s["source_ed_funds"],
                "ED products;",
                s["base_eligible_funds"],
                "eligible",
                flush=True,
            )
    results.sort(key=lambda x: x[0]["quarter"])
    summaries = [r[0] for r in results]
    managers = [row for _, rows in results for row in rows]
    add_persistence(managers)
    write_csv(args.out / "manager-scorecards.csv", managers)
    write_csv(
        args.out / "latest-manager-scorecards.csv",
        [r for r in managers if r["quarter"] == summaries[-1]["quarter"]],
    )
    write_csv(args.out / "coverage.csv", [c for s in summaries for c in s["peer_coverage"]])
    freeze(
        args.out / "summary.json",
        encode(
            {
                "snapshots": summaries,
                "manager_scorecard_rows": len(managers),
                "unique_ed_firm_ids": len(
                    {r["firm_id"] for r in managers if r["peer_group"] == "Event-Driven"}
                ),
                "limitations": [
                    "unverified_delivery_proxies",
                    "active_snapshot_universes_not_complete_dead_database",
                    "representative_fund_not_consolidated_manager",
                    "zero_hurdle_not_cash_adjusted_sharpe",
                    "no_13d_following_test",
                ],
            }
        ),
    )
    freeze(
        args.out / "provenance.json",
        encode(
            {
                "code_sha256": code_hash,
                "protocol_sha256": protocol_hash,
                "archive_sha256": manifest["archive_sha256"],
                "manifest_sha256": file_hash(manifest_path),
                "python": sys.version,
                "contract": CONTRACT,
                "definition_url": "https://www.hfr.com/database/hfr-database/dead-funds-database-field-definitions/",
                "definition_access_date": "2026-09-30",
            }
        ),
    )
    report(args.out, summaries, managers)
    print(
        "COMPLETE",
        len(summaries),
        "snapshots;",
        len(managers),
        "manager peer observations",
        flush=True,
    )


if __name__ == "__main__":
    main()
