"""Hand-computed identifier readiness and cached provenance contracts.

Inputs: synthetic filing records and cache envelopes. Outputs: assertions.
Identity: one syntactic identifier / three filings = 1/3; no match inferred.
Tier: 1
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python -m unittest discover -s scripts/phase1_prep
"""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from feasibility import directory_candidates, envelope, readiness


class FeasibilityTests(unittest.TestCase):
    def test_counts_and_replay(self):
        records = [{"accession": "a", "cusip": "123456789", "subjects": [{"cik": "1"}]},
                   {"accession": "b", "cusip": "123", "subjects": [{"cik": "1"}]},
                   {"accession": "c", "cusip": None}]
        summary, rows = readiness(records)
        self.assertEqual((summary["n_filings"], summary["cusip_present"], summary["cusip_missing"]), (3, 2, 1))
        self.assertEqual(summary["cusip_syntactic_rate"], 1 / 3)
        self.assertEqual(summary["distinct_issuer_ciks"], 1)
        self.assertIsNone(summary["historical_match_rate"])
        self.assertEqual(rows[1]["cusip"], "123")
        self.assertEqual(readiness(records), readiness(records))

    def test_empty_is_not_zero_match_rate(self):
        summary, _ = readiness([])
        self.assertIsNone(summary["cusip_syntactic_rate"])
        self.assertIsNone(summary["historical_match_rate"])

    def test_cache_hash_refusal(self):
        with tempfile.TemporaryDirectory() as folder:
            request = {"method": "OPTIONS", "url": "example", "params": {}}
            key = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
            path = Path(folder) / (key + ".json")
            data = {"request": request, "raw_response": "{}", "sha256": hashlib.sha256(b"{}").hexdigest()}
            path.write_text(json.dumps(data))
            self.assertEqual(envelope(path)[1], {})
            data["raw_response"] = "[]"
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                envelope(path)

    def test_directory_presence_does_not_assert_access(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "directory.response"
            path.write_text('{"crsp.dsenames": "unused"}')
            meta = path.with_suffix(".json")
            meta.write_text(json.dumps({"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                        "status": 200, "retrieved_at": "synthetic"}))
            result = directory_candidates(path, meta)
            self.assertEqual(sum(r["listed_in_cached_directory"] for r in result["tables"]), 1)
            self.assertTrue(all(r["schema_access"] == "not_tested" for r in result["tables"]))
            path.write_text("{}")
            with self.assertRaises(ValueError):
                directory_candidates(path, meta)


if __name__ == "__main__":
    unittest.main()
