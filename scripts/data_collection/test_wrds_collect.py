"""Offline pagination, scope and frozen-cache refusal contracts.

Inputs: synthetic pages, exact filters and cache bytes. Outputs: assertions.
Identity: two rows plus one row = three unique returned rows.
Tier: 1
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python -m unittest discover -s scripts/data_collection -p test_wrds_collect.py
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from wrds_collect import FrozenClient, Refusal, collect_task, next_offset, validate_page
from wrds_daily import archive_daily, enumerate_daily


class WrdsBulkTests(unittest.TestCase):
    def test_single_slice_partition_parity_and_no_coverage_claim(self):
        class Fake:
            corrupt = False
            def request(self, table, method, params):
                rows = [{"dlycaldt": "2024-01-03", "permno": 1}, {"dlycaldt": "2024-01-03", "permno": 90000}]
                if "permno__lt" in params:
                    rows = rows[:1]
                if "permno__gte" in params:
                    rows = [] if self.corrupt else rows[1:]
                return {"results": rows, "count": 1, "next": None}, {}
        client = Fake()
        result = archive_daily(client, "crsp.dsf_v2", {"dlycaldt": "2024-01-03"}, 100, lambda _: None, True)
        self.assertEqual(result["n"], 2)
        self.assertEqual(result["status"], "raw_downloaded_vendor_count_unreconciled")
        self.assertTrue(result["partition_check_passed"])
        client.corrupt = True
        with self.assertRaises(Refusal):
            archive_daily(client, "crsp.dsf_v2", {"dlycaldt": "2024-01-03"}, 100, lambda _: None, True)

    def test_incorrect_vendor_count_requires_explicit_empty_page(self):
        class Fake:
            def request(self, table, method, params):
                # API understates count and stops next links early; three real rows.
                rows = {0: [{"date": "2024-01-03", "permno": 1}, {"date": "2024-01-03", "permno": 2}],
                        2: [{"date": "2024-01-03", "permno": 3}], 3: []}[params["offset"]]
                return {"results": rows, "count": 1, "next": None}, {}
        result = enumerate_daily(Fake(), {"date": "2024-01-03"}, 2, lambda _: None)
        self.assertEqual(result["n"], 3)
        self.assertEqual([p["offset"] for p in result["pages"]], [0, 2, 3])
        self.assertTrue(result["reported_count_discrepancy"])
        with self.assertRaises(Refusal):
            validate_page({"results": [1, 2], "count": 1}, {}, 2)

    def test_exact_filter_refusal(self):
        with self.assertRaises(Refusal):
            validate_page({"results": [{"date": "2020-01-02"}], "count": 1}, {"date": "2020-01-01"}, 1)

    def test_pagination_preserves_scope(self):
        url = "http://wrds-api.wharton.upenn.edu/data/crsp.dsf/?date=2024-01-03&limit=2&offset=2"
        self.assertEqual(next_offset(url, "crsp.dsf", {"date": "2024-01-03"}, 2, 0, 2), 2)
        for bad in (url.replace("wharton.upenn.edu", "example.com"), url.replace("offset=2", "offset=0"), url.replace("2024-01-03", "2020-01-01")):
            with self.assertRaises(Refusal):
                next_offset(bad, "crsp.dsf", {"date": "2024-01-03"}, 2, 0, 2)

    def test_count_replay_and_duplicates(self):
        class Fake:
            duplicate = False
            def request(self, table, method="OPTIONS", params=None):
                if method == "OPTIONS":
                    return {"fields": {}}, {}
                rows = [{"id": 1}, {"id": 2}] if params["offset"] == 0 else [{"id": 1 if self.duplicate else 3}]
                return {"results": rows, "count": 3, "next": "http://wrds-api.wharton.upenn.edu/data/crsp.dsenames/?limit=2&offset=2" if params["offset"] == 0 else None}, {}
        client = Fake()
        first = collect_task(client, "crsp.dsenames", {}, 2, lambda _: None)
        second = collect_task(client, "crsp.dsenames", {}, 2, lambda _: None)
        self.assertEqual(first["n"], 3)
        self.assertEqual(first["pages"], second["pages"])
        client.duplicate = True
        with self.assertRaises(Refusal):
            collect_task(client, "crsp.dsenames", {}, 2, lambda _: None)

    def test_offline_never_reaches_network_or_credentials(self):
        with tempfile.TemporaryDirectory() as folder, patch("wrds_collect.load_token", side_effect=AssertionError("credential use")), patch("requests.Session", side_effect=AssertionError("network use")):
            with self.assertRaises(Refusal):
                FrozenClient(cache=Path(folder)).request("crsp.dsf")


if __name__ == "__main__":
    unittest.main()
