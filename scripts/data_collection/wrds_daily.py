"""Enumerate exact-date CRSP pages when vendor total/next metadata is inconsistent.

Inputs: frozen exact-date raw DSF responses, explicit increasing offsets.
Outputs: raw page provenance, empty terminal page, unique security count and flags.
Identity: n = sum(nonempty page lengths), independent of vendor reported count.
Every date and (PERMNO,date) key is checked. Vendor count discrepancies remain
explicit, never promoted to count-reconciled coverage or semantic validation.
Tier: 1
Run: imported only by scripts/data_collection/wrds_collect.py
"""

import json


def archive_daily(client, table, filters, limit, heartbeat, partition_check=False):
    """Archive a single large date slice; never claim vendor coverage completeness."""
    import hashlib

    from wrds_collect import Refusal, utc

    date_field = "dlycaldt" if table == "crsp.dsf_v2" else "date"
    if table not in {"crsp.dsf", "crsp.dsf_v2"} or set(filters) != {date_field}:
        raise Refusal("Daily archive requires an authorized table and exact date")

    def read(extra):
        payload, meta = client.request(table, "GET", {**filters, **extra, "limit": limit, "offset": 0})
        rows = payload.get("results")
        if not isinstance(rows, list) or len(rows) >= limit or payload.get("next") is not None:
            raise Refusal("Daily response may be truncated; no offset fallback permitted")
        keyed = {}
        for row in rows:
            number = row.get("permno")
            if type(number) is not int or row.get(date_field) != filters[date_field]:
                raise Refusal("Daily response violates date/security key")
            if number in keyed:
                raise Refusal("Repeated daily security key")
            if "permno__lt" in extra and number >= int(extra["permno__lt"]):
                raise Refusal("PERMNO partition filter ignored")
            if "permno__gte" in extra and number < int(extra["permno__gte"]):
                raise Refusal("PERMNO partition filter ignored")
            keyed[number] = row
        return payload, meta, keyed

    payload, meta, keyed = read({})
    parts = []
    if partition_check and keyed:
        union = {}
        for extra in ({"permno__lt": "50000"}, {"permno__gte": "50000"}):
            part_payload, part_meta, part_rows = read(extra)
            if set(union) & set(part_rows):
                raise Refusal("Daily partitions overlap")
            union.update(part_rows)
            parts.append({"filters": extra, "n": len(part_rows), "reported_count": part_payload.get("count"), "source": part_meta})
        if union != keyed:
            raise Refusal("Daily single response differs from independent partition union")
    signature = hashlib.sha256(json.dumps(keyed, sort_keys=True).encode()).hexdigest()
    heartbeat({"table": table, "filters": filters, "rows_archived": len(keyed), "quality": "vendor_count_unreconciled"})
    return {"status": "raw_downloaded_vendor_count_unreconciled", "table": table, "filters": filters,
            "n": len(keyed), "completed_at": utc(), "reported_count_discrepancy": payload.get("count") != len(keyed),
            "reported_count": payload.get("count"), "pages": [{"offset": 0, "n": len(keyed), "source": meta}],
            "partition_check_passed": bool(parts), "partition_checks": parts,
            "canonical_rows_sha256": signature,
            "limitation": "Large single response with exact date/unique PERMNO checks; vendor count/next metadata is inconsistent. Raw archived, not independently coverage-verified. Never use offset exhaustion as completeness."}


def enumerate_daily(client, filters, limit, heartbeat):
    """Diagnostic only: known unreliable when backend empties offsets after 5000."""
    # Local import avoids circular module initialization in the collector CLI.
    from wrds_collect import Refusal, utc

    if set(filters) != {"date"}:
        raise Refusal("Daily enumeration requires one exact date")
    offset, pages, securities, signatures = 0, [], set(), []
    for _ in range(100):
        payload, meta = client.request("crsp.dsf", "GET", {**filters, "limit": limit, "offset": offset})
        rows = payload.get("results")
        if not isinstance(rows, list) or len(rows) > limit:
            raise Refusal("Unexpected daily page or ignored limit")
        for row in rows:
            if row.get("date") != filters["date"] or row.get("permno") is None:
                raise Refusal("Daily page violates exact date/security key")
            key = (row["date"], str(row["permno"]))
            if key in securities:
                raise Refusal("Daily page repeats a security/date key")
            securities.add(key)
            signatures.append(json.dumps(row, sort_keys=True))
        pages.append({"offset": offset, "n": len(rows), "reported_count": payload.get("count"),
                      "reported_next": payload.get("next"), "source": meta})
        offset += len(rows)
        heartbeat({"table": "crsp.dsf", "filters": filters, "rows_verified": offset,
                   "pages_verified": len(pages), "pagination": "explicit_offsets_to_empty_page"})
        if not rows:
            discrepancy = any(p["reported_count"] != offset for p in pages)
            import hashlib
            signature = hashlib.sha256("\n".join(sorted(signatures)).encode()).hexdigest()
            return {"status": "completed_with_vendor_count_discrepancy" if discrepancy else "completed",
                    "table": "crsp.dsf", "filters": filters, "n": offset, "completed_at": utc(),
                    "pages": pages, "terminal_empty_page_verified": True,
                    "reported_count_discrepancy": discrepancy, "canonical_rows_sha256": signature,
                    "limitation": "Offset enumeration exhausted with no repeated security/date keys. Vendor count/next are retained but not trusted; no immutable snapshot or independent coverage guarantee."}
    raise Refusal("Daily pagination exceeds 100-page guard")
