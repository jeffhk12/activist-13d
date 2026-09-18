"""Offline hand-built evidence-audit contracts. Tier: 1.

Inputs: synthetic bytes and records. Outputs: refusal/replay assertions.
Identity: matching hash and byte count verify one file, not its semantics.
Run: .venv/bin/python -m unittest discover -s scripts/phase1_prep
"""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from run import candidate_key, packet, verify


class AuditTests(unittest.TestCase):
    def test_integrity_and_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "source.txt"
            path.write_bytes(b"abc")
            expected = hashlib.sha256(b"abc").hexdigest()
            path.with_suffix(".txt.meta.json").write_text(json.dumps({"sha256": expected, "bytes": 3}))
            self.assertEqual(verify(path, expected)["status"], "verified")
            self.assertEqual(verify(path, expected), verify(path, expected))
            path.write_bytes(b"abd")
            self.assertEqual(verify(path, expected)["status"], "integrity_failure")

    def test_missing_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(verify(Path(folder) / "missing")["status"], "missing_source_or_sidecar")

    def test_candidate_key_not_issuer_only(self):
        self.assertIsNone(candidate_key({"subjects": [{"cik": "001"}]}))
        self.assertNotEqual(candidate_key({"subjects": [{"cik": "001"}], "filers": [{"cik": "002"}]}), candidate_key({"subjects": [{"cik": "001"}], "filers": [{"cik": "003"}]}))

    def test_packet_escapes_source_and_preserves_text(self):
        text = "<script>alert(1)</script>" + "long" * 20000
        record = {"accession": "x", "filers": [], "subjects": [], "evidence_bundle": {}, "documents": [{"text": text}]}
        inventory = {"source_path": "raw", "source_sha256": "hash", "filing_date": None, "form": None, "flags": []}
        result = packet(record, inventory)
        self.assertNotIn("<script>", result)
        self.assertIn("&lt;script&gt;", result)
        self.assertIn("long" * 20000, result)


if __name__ == "__main__":
    unittest.main()
