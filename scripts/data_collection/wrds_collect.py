"""Resumable frozen WRDS acquisition for the authorized broad research extract.

Inputs: explicit allowlisted requests, WRDS entitlement credential, cached pages.
Outputs: compressed raw JSON pages plus exact request/hash/pull-time envelopes.
Identity: downloaded rows = sum(page results); completion requires count parity.
No model APIs, economic labels, or investment calculations are involved.
Tier: 1
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python scripts/data_collection/wrds_collect.py metadata --online
"""

import argparse
import fcntl
import gzip
import hashlib
import json
import os
import shutil
import signal
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from wrds_access.client import load_token  # noqa: E402

BASE = "https://wrds-api.wharton.upenn.edu/data/"
TABLES = ("crsp.dsf", "crsp.dsi", "crsp.dsenames", "crsp.stocknames", "crsp.dsedelist",
          "crsp.ccmxpf_lnkhist", "comp.funda", "audit.feed31_shareholder_activism",
          "crsp.dsf_v2", "crsp.stocknames_v2")
CACHE = ROOT / "data/raw/wrds/bulk-v1"
OUT = ROOT / "output/data-collection/wrds"
STOP_REQUESTED = False


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2) + "\n")
    temp.replace(path)


class Refusal(RuntimeError):
    pass


class FrozenClient:
    def __init__(self, online=False, cache=CACHE):
        self.online = online
        self.cache = cache
        self.last_request = 0
        self.network_calls = 0

    def request(self, table, method="OPTIONS", params=None):
        if STOP_REQUESTED:
            raise Refusal("Graceful stop requested between pages")
        if table not in TABLES or method not in {"OPTIONS", "GET"}:
            raise Refusal("Request outside authorized table/method scope")
        request = {"url": BASE + table + "/", "method": method, "params": params or {}}
        key = sha(json.dumps(request, sort_keys=True).encode())
        path = self.cache / table / (key + ".json.gz")
        metadata_path = path.with_suffix(".meta.json")
        if path.exists() or metadata_path.exists():
            if not path.exists() or not metadata_path.exists():
                raise Refusal("Incomplete cache pair; preserve and inspect")
            meta = json.loads(metadata_path.read_text())
            raw = gzip.decompress(path.read_bytes())
            if meta["request"] != request or sha(raw) != meta["sha256"]:
                raise Refusal("Frozen cache integrity mismatch")
            return json.loads(raw), meta
        if not self.online:
            raise Refusal("Offline cache miss")
        if shutil.disk_usage(ROOT).free < 20 * 1024 ** 3:
            raise Refusal("Free disk below 20 GiB reserve")
        token = load_token()
        time.sleep(max(0, 0.5 - (time.monotonic() - self.last_request)))
        self.last_request = time.monotonic()
        try:
            with requests.Session() as session:
                session.trust_env = False
                with session.request(method, request["url"], params=request["params"],
                                     headers={"Authorization": "Token " + token, "Accept": "application/json"},
                                     timeout=(10, 60), allow_redirects=False, stream=True) as response:
                    self.network_calls += 1
                    if response.status_code != 200:
                        raise Refusal(f"{table}: HTTP {response.status_code}; response suppressed")
                    chunks, size = [], 0
                    for chunk in response.iter_content(65536):
                        size += len(chunk)
                        if size > 50_000_000:
                            raise Refusal("Page exceeds 50 MB limit")
                        chunks.append(chunk)
                    raw = b"".join(chunks)
        except requests.RequestException:
            raise Refusal("WRDS transport failure; sensitive details suppressed") from None
        if token.encode() in raw:
            raise Refusal("Credential echo; refusing to persist")
        try:
            payload = json.loads(raw)
        except ValueError:
            raise Refusal("WRDS response is not JSON") from None
        meta = {"request": request, "retrieved_at": utc(), "sha256": sha(raw),
                "raw_bytes": len(raw), "cache_path": str(path.relative_to(ROOT)),
                "python": sys.version, "requests": requests.__version__}
        path.parent.mkdir(parents=True, exist_ok=True)
        # Frozen pages never overwrite evidence; incomplete pairs refuse replay.
        with path.open("xb") as handle:
            handle.write(gzip.compress(raw, mtime=0))
        with metadata_path.open("x") as handle:
            json.dump(meta, handle, indent=2)
        return payload, meta


def metadata(client):
    report = {"started_at": utc(), "tables": {}, "model_api_calls": 0}
    for table in TABLES:
        try:
            payload, meta = client.request(table)
            fields = payload.get("fields", {})
            report["tables"][table] = {"status": "verified_schema" if fields else "unexpected_schema",
                                       "fields": fields, "source": meta,
                                       "other_metadata": {k: v for k, v in payload.items() if k != "fields"}}
            print(json.dumps({"table": table, "columns": len(fields),
                              "filters": {k: v for k, v in fields.items() if v.get("filter_field")}}), flush=True)
        except Refusal as error:
            report["tables"][table] = {"status": "refused", "error": str(error)}
            print(str(error), flush=True)
        write_json(OUT / "metadata.json", report)
    report.update(completed_at=utc(), network_calls=client.network_calls)
    write_json(OUT / "metadata.json", report)


def validate_page(payload, filters, limit):
    rows = payload.get("results")
    if not isinstance(rows, list) or len(rows) > limit:
        raise Refusal("Unexpected results or page limit ignored")
    if type(payload.get("count")) is not int or payload["count"] < len(rows):
        raise Refusal("Invalid total count")
    for row in rows:
        if not isinstance(row, dict) or any(str(row.get(k)) != str(v) for k, v in filters.items()):
            raise Refusal("Server ignored a requested exact filter")
    return rows


def next_offset(url, table, filters, limit, offset, rows):
    if url is None:
        return None
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or parsed.netloc != "wrds-api.wharton.upenn.edu" or parsed.path != f"/data/{table}/":
        raise Refusal("Pagination target outside same WRDS table")
    params = parse_qs(parsed.query)
    expected = {k: [str(v)] for k, v in {**filters, "limit": limit, "offset": offset + rows}.items()}
    if params != expected or not rows:
        raise Refusal("Pagination lost filters, repeated a page, or skipped rows")
    # Never follow the returned HTTP URL. Construct an allowlisted HTTPS request.
    return offset + rows


def tasks():
    result = [(table, {}, 1000) for table in ("crsp.dsenames", "crsp.stocknames", "crsp.dsedelist", "crsp.ccmxpf_lnkhist", "crsp.dsi", "audit.feed31_shareholder_activism", "crsp.stocknames_v2")]
    result += [("comp.funda", {"fyear": str(year)}, 1000) for year in range(2011, 2027)]
    current, end = date(2012, 1, 1), date(2026, 9, 13)
    while current <= end:
        if current.weekday() < 5:
            result.append(("crsp.dsf_v2", {"dlycaldt": current.isoformat()}, 50000))
        current += timedelta(days=1)
    return result


def collect_task(client, table, filters, limit, heartbeat):
    schema, _ = client.request(table)
    if any(not schema["fields"].get(k, {}).get("filter_field") for k in filters):
        raise Refusal("Filter missing from schema")
    offset, total, pages, seen = 0, None, [], set()
    while True:
        payload, meta = client.request(table, "GET", {**filters, "limit": limit, "offset": offset})
        rows = validate_page(payload, filters, limit)
        if total is None:
            total = payload["count"]
        if total != payload["count"]:
            raise Refusal("Vendor count changed during frozen pagination")
        for row in rows:
            key = sha(json.dumps(row, sort_keys=True).encode())
            if key in seen:
                raise Refusal("Duplicate row across paginated extract; investigate ordering")
            seen.add(key)
        pages.append({"offset": offset, "n": len(rows), "source": meta})
        heartbeat({"table": table, "filters": filters, "rows_verified": offset + len(rows),
                   "reported_count": total, "pages_verified": len(pages)})
        upcoming = next_offset(payload.get("next"), table, filters, limit, offset, len(rows))
        if upcoming is None:
            if offset + len(rows) != total:
                raise Refusal("Final page does not reconcile to reported count")
            break
        if upcoming >= total or len(pages) > 10000:
            raise Refusal("Pagination exceeds reported count or page guard")
        offset = upcoming
    return {"status": "completed", "table": table, "filters": filters, "n": total,
            "completed_at": utc(), "pages": pages,
            "limitation": "Stable count and no exact duplicate rows checked; vendor provides no immutable snapshot token."}


def collect(client):
    OUT.mkdir(parents=True, exist_ok=True)
    lock = (OUT / "worker.lock").open("a+")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise Refusal("WRDS collector already running") from None
    lock.seek(0)
    lock.truncate()
    lock.write(str(os.getpid()))
    lock.flush()
    plan = tasks()
    state = {"status": "running", "pid": os.getpid(), "started_at": utc(), "tasks_total": len(plan),
             "tasks_completed": 0, "rows_completed": 0, "model_api_calls": 0, "tables": {},
             "scope": "Count-reconciled small historical names/link/delist/index/activism tables; funda fiscal 2011-2026; CIZ daily equities weekdays 2012-01-01 through 2026-09-13 archived with unresolved vendor count metadata."}
    state["vendor_count_discrepancy_tasks"] = 0
    state["daily_raw_tasks_not_coverage_verified"] = 0
    checked_years = set()
    write_json(OUT / "plan.json", {"scope": state["scope"], "tasks": [{"table": t, "filters": f, "limit": n} for t, f, n in plan],
                                   "worker_sha256": sha(Path(__file__).read_bytes()), "authorized_by": "User: lets do it; broad raw collection authorized"})

    def heartbeat(current):
        state.update(current=current, updated_at=utc(), network_calls_this_process=client.network_calls)
        write_json(OUT / "progress.json", state)

    try:
        for table, filters, limit in plan:
            if table == "crsp.dsf_v2":
                from wrds_daily import archive_daily
                year = filters["dlycaldt"][:4]
                result = archive_daily(client, table, filters, limit, heartbeat, partition_check=year not in checked_years)
                if result["partition_check_passed"]:
                    checked_years.add(year)
                state["daily_raw_tasks_not_coverage_verified"] += 1
            else:
                result = collect_task(client, table, filters, limit, heartbeat)
            task_key = sha(json.dumps({"table": table, "filters": filters}, sort_keys=True).encode())
            write_json(OUT / "tasks" / (task_key + ".json"), result)
            state["tasks_completed"] += 1
            state["rows_completed"] += result["n"]
            state["vendor_count_discrepancy_tasks"] += int(result.get("reported_count_discrepancy", False))
            state["tables"].setdefault(table, {"tasks": 0, "rows": 0})
            state["tables"][table]["tasks"] += 1
            state["tables"][table]["rows"] += result["n"]
            heartbeat({"table": table, "filters": filters, "status": "completed"})
            print(json.dumps({"completed": state["tasks_completed"], "table": table, "filters": filters, "rows": result["n"]}), flush=True)
        state["status"] = "finished_with_daily_coverage_unverified" if state["daily_raw_tasks_not_coverage_verified"] else "completed"
    except Exception as error:
        state.update(status="stopped", error=str(error) if isinstance(error, Refusal) else type(error).__name__)
        raise
    finally:
        heartbeat(state.get("current", {}))
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()


def probe(client):
    summary = {"started_at": utc(), "tables": {}, "model_api_calls": 0}
    for table in TABLES:
        filters = {"date": "2024-01-03"} if table in {"crsp.dsf", "crsp.dsi"} else {"fyear": "2023"} if table == "comp.funda" else {}
        try:
            schema, _ = client.request(table)
            if any(not schema["fields"].get(k, {}).get("filter_field") for k in filters):
                raise Refusal("Exact filter not supported by schema")
            payload, meta = client.request(table, "GET", {**filters, "limit": 1000, "offset": 0})
            rows = validate_page(payload, filters, 1000)
            summary["tables"][table] = {"status": "verified_first_page", "downloaded_rows": len(rows),
                                         "reported_count": payload["count"], "filters": filters,
                                         "next": payload.get("next"), "source": meta}
            print(json.dumps({"table": table, "rows": len(rows), "count": payload["count"], "bytes": meta["raw_bytes"]}), flush=True)
        except Refusal as error:
            summary["tables"][table] = {"status": "refused", "error": str(error)}
            print(str(error), flush=True)
        write_json(OUT / "probe.json", summary)
    summary.update(completed_at=utc(), network_calls=client.network_calls)
    write_json(OUT / "probe.json", summary)


def main():
    def stop(_signum, _frame):
        global STOP_REQUESTED
        STOP_REQUESTED = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["metadata", "probe", "collect"])
    parser.add_argument("--online", action="store_true")
    args = parser.parse_args()
    try:
        {"metadata": metadata, "probe": probe, "collect": collect}[args.mode](FrozenClient(online=args.online))
    except Refusal as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
